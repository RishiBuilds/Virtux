"""
Virtux Shell - the main REPL that users interact with.
"""

from __future__ import annotations

import os
import sys
import json
import atexit
from dataclasses import dataclass


try:
    import readline
except ImportError:
    try:
        import pyreadline3 as readline  # type: ignore
    except ImportError:
        readline = None  # type: ignore

from virtux.core.filesystem import VirtualFileSystem, FSNode
from virtux.core.environment import Environment
from virtux.core.executor import Executor

import virtux.commands  # noqa: F401

BANNER = r"""
 __   __ _      _
 \ \ / /(_)_ _| |_ _  ___ __
  \ V / | | '_|  _| || \ \ /
   \_/  |_|_|  \__|\_,_/_\_\

  A portable Linux shell simulator - type 'help' to begin.
"""


@dataclass
class ShellResult:
    """Result of running a command via VirtuxShell.run(command)."""
    stdout: str
    stderr: str
    exit_code: int


class _UseDefaultPersistPath:
    """Sentinel: use the platform default persist file path."""


_USE_DEFAULT_PERSIST = _UseDefaultPersistPath()


class Shell:
    """Interactive shell REPL using readline."""

    def __init__(
        self,
        persist_path: str | None | _UseDefaultPersistPath = _USE_DEFAULT_PERSIST,
        fs: VirtualFileSystem | None = None,
        env: Environment | None = None,
        executor: Executor | None = None,
    ):
        self.fs = fs if fs is not None else VirtualFileSystem()
        self.env = env if env is not None else Environment()
        self.executor = executor if executor is not None else Executor(self.fs, self.env)
        from virtux.utils import get_data_dir
        self._persist_enabled: bool
        resolved_persist: str | None
        if persist_path is _USE_DEFAULT_PERSIST:
            self._persist_enabled = True
            resolved_persist = os.path.join(get_data_dir(), "virtux_state.json")
        elif persist_path is None:
            self._persist_enabled = False
            resolved_persist = None
        else:
            assert isinstance(persist_path, str)
            self._persist_enabled = True
            resolved_persist = persist_path
        self.persist_path = resolved_persist
        self.history_path: str | None
        if resolved_persist:
            self.history_path = os.path.join(
                os.path.dirname(resolved_persist) or ".", "history"
            )
        else:
            self.history_path = None
        self._setup_readline()
        if self._persist_enabled:
            self._load_state()
        self._load_readline_history()
        atexit.register(self._on_exit)

    def _setup_readline(self) -> None:
        if readline is None:
            return
        try:
            readline.set_completer(self._completer)  # type: ignore
            readline.parse_and_bind("tab: complete")  # type: ignore
            readline.set_completer_delims(" \t\n\"'")  # type: ignore
        except Exception as e:
            print(f"virtux: warning: readline setup failed: {e}", file=sys.stderr)

    def _load_readline_history(self) -> None:
        if readline is None or not self.history_path:
            return
        try:
            if os.path.exists(self.history_path):
                readline.read_history_file(self.history_path)  # type: ignore
        except Exception as e:
            print(f"virtux: warning: could not load history: {e}", file=sys.stderr)

    def _save_readline_history(self) -> None:
        if readline is None or not self.history_path:
            return
        try:
            os.makedirs(os.path.dirname(self.history_path) or ".", exist_ok=True)
            readline.write_history_file(self.history_path)  # type: ignore
        except Exception as e:
            print(f"virtux: warning: could not save history: {e}", file=sys.stderr)

    def _on_exit(self) -> None:
        if self._persist_enabled:
            self._save_state()
        self._save_readline_history()

    def _completer(self, text: str, state: int) -> str | None:
        if readline is None:
            return None
        buffer = readline.get_line_buffer()  # type: ignore
        stripped = buffer.lstrip()
        boundary_suffixes = ("| ", "&& ", "|| ", "; ", "& ")
        is_cmd = " " not in stripped or buffer.endswith(boundary_suffixes)

        if is_cmd:
            from virtux.core.registry import all_commands
            cmds = list(all_commands().keys())
            aliases = list(self.env.aliases.keys()) if hasattr(self.env, "aliases") else []
            matches = [c for c in (cmds + aliases) if c.startswith(text)]
        else:
            matches = []
            try:
                if "/" in text:
                    dir_part, prefix = text.rsplit("/", 1)
                else:
                    dir_part, prefix = ".", text

                resolved_dir = dir_part
                if resolved_dir.startswith("~"):
                    resolved_dir = self.env.home + resolved_dir[1:]
                if not resolved_dir.startswith("/"):
                    from virtux.utils import normalize_path
                    resolved_dir = normalize_path(resolved_dir, self.env.cwd)

                if self.fs.is_dir(resolved_dir):
                    entries = self.fs.listdir(resolved_dir)
                    for entry in entries:
                        if entry.startswith(prefix):
                            match_path = (dir_part + "/" + entry) if dir_part != "." else entry
                            full_match_path = resolved_dir + "/" + entry
                            if self.fs.is_dir(full_match_path):
                                match_path += "/"
                            matches.append(match_path)
            except Exception:
                pass

        if state < len(matches):
            return matches[state]
        return None

    def run(self, command: str | None = None) -> ShellResult | None:
        """Start the interactive REPL loop, or execute a command and return its result."""
        if command is not None:
            import io
            import contextlib
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                code = self.executor.run_line(command)
            return ShellResult(
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                exit_code=code,
            )

        print(BANNER)
        while True:
            try:
                prompt_str = self.env.get_prompt()
                user_input = input(prompt_str)
                if not user_input.strip():
                    continue

                self.env.add_history(user_input)
                self.executor.run_line(user_input)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print("logout")
                break
            except SystemExit:
                break
        return None


    def _save_state(self) -> None:
        """Save filesystem and environment to the single persist JSON file."""
        if not self._persist_enabled or not self.persist_path:
            return
        try:
            fs_node = getattr(self.fs, "root", getattr(self.fs, "_root", None))
            fs_data = fs_node.to_dict() if fs_node else {}
            env_data = self.env.to_dict()

            state = {
                "fs": fs_data,
                "env": env_data,
            }

            dirname = os.path.dirname(self.persist_path)
            if dirname:
                os.makedirs(dirname, exist_ok=True)
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"virtux: warning: could not save session state: {e}", file=sys.stderr)

    def _load_state(self) -> None:
        """Load filesystem and environment from the single persist JSON file."""
        if not self._persist_enabled or not self.persist_path:
            return
        try:
            if os.path.exists(self.persist_path):
                with open(self.persist_path, "r", encoding="utf-8") as f:
                    state = json.load(f)

                if "fs" in state:
                    fs_node = FSNode.from_dict(state["fs"])
                    set_successful = False
                    for attr in ("root", "_root"):
                        try:
                            setattr(self.fs, attr, fs_node)
                            set_successful = True
                            break
                        except AttributeError:
                            try:
                                object.__setattr__(self.fs, attr, fs_node)
                                set_successful = True
                                break
                            except AttributeError:
                                pass
                    if not set_successful:
                        try:
                            self.fs.__dict__["root"] = fs_node
                        except Exception:
                            pass
                if "env" in state:
                    self.env.from_dict(state["env"])
        except Exception as e:
            print(f"virtux: warning: could not load saved session state: {e}", file=sys.stderr)