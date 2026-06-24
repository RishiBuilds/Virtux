"""
Virtux Shell - legacy compatibility wrapper for VirtuxShell.
"""

from __future__ import annotations

import os
import io
import sys
import json
import contextlib
from typing import Optional

from virtux.core.shell import Shell, ShellResult
from virtux.core.executor import Executor
from virtux.core.filesystem import VirtualFileSystem
from virtux.core.environment import Environment
from virtux.users import UserManager
from virtux.registry import CommandRegistry
from virtux.commands import register_all_commands
from virtux.plugins import discover_plugins


class VirtuxShell(Shell):
    """Legacy compatibility wrapper for VirtuxShell."""

    def __init__(
        self,
        persist: bool = True,
        data_dir: Optional[str] = None,
    ) -> None:
        from virtux.utils import get_data_dir

        self._persist = persist
        self._data_dir = data_dir or get_data_dir()
        self._fs_path = os.path.join(self._data_dir, "filesystem.json")
        self._history_path = os.path.join(self._data_dir, "history")
        self._env_path = os.path.join(self._data_dir, "env.json")

        persist_path = os.path.join(self._data_dir, "virtux_state.json")

        self._users = UserManager()
        self._env = Environment(
            user=self._users.current_user,
            hostname="virtux",
        )
        self._fs = VirtualFileSystem()

        self._fs.setup_user_home(
            self._users.current_user,
            self._users.get_primary_group_name(),
        )

        self._fs.write_file("/etc/passwd", self._users.generate_passwd_content())
        self._fs.write_file("/etc/group", self._users.generate_group_content())

        self._registry = CommandRegistry()
        register_all_commands(self._registry)

        self._loaded_plugins = discover_plugins(self._registry)

        self._executor = Executor(self._fs, self._env)

        self._history: list[str] = []

        super().__init__(
            persist_path=persist_path if persist else None,
            fs=self._fs,
            env=self._env,
            executor=self._executor,
        )

    def reset(self) -> None:
        """Reset all state to defaults."""
        self.fs.reset()
        self.fs.setup_user_home(
            self._users.current_user,
            self._users.get_primary_group_name(),
        )

        self.env = Environment(
            user=self._users.current_user,
            hostname="virtux",
        )
        self._env = self.env

        self.executor = Executor(self.fs, self.env)
        self._executor = self.executor

        self._history.clear()

        for f in [self._fs_path, self._env_path, self._history_path, self.persist_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception as e:
                    print(f"virtux: warning: could not remove '{f}': {e}", file=sys.stderr)

    def execute(self, command: str) -> str:
        """Execute a command and return its combined stdout+stderr output.

        Useful for programmatic usage. The exit code is available
        immediately afterward via self.executor.last_exit_code.
        """
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            self.executor.run_line(command)

        result = stdout_capture.getvalue()
        err = stderr_capture.getvalue()
        if err:
            result += err
        return result

    def execute_with_code(self, command: str) -> tuple[str, int]:
        """Like execute(), but also returns the exit code."""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
            code = self.executor.run_line(command)

        result = stdout_capture.getvalue()
        err = stderr_capture.getvalue()
        if err:
            result += err
        return result, code

    def run(self, command: Optional[str] = None) -> Optional[ShellResult]:
        """Start the interactive REPL loop, or execute a command and return its result."""
        if command is not None:
            stdout_capture = io.StringIO()
            stderr_capture = io.StringIO()
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                code = self.executor.run_line(command)
            return ShellResult(
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                exit_code=code,
            )

        from virtux.core.shell import BANNER
        print(BANNER)
        while True:
            try:
                prompt_str = self.env.get_prompt()
                user_input = input(prompt_str)
                if not user_input.strip():
                    continue
                self._execute_line(user_input)
            except KeyboardInterrupt:
                print()
                continue
            except EOFError:
                print("logout")
                break
            except SystemExit:
                break
        return None

    def _execute_line(self, line: str) -> None:
        """Execute a line of input, recording it to history."""
        self.env.add_history(line)
        self._history.append(line)
        self._append_to_history_file(line)
        self.executor.run_line(line)

    def _append_to_history_file(self, line: str) -> None:
        hist_file = self.env.get("HISTFILE", "")
        if hist_file:
            try:
                self.fs.append_file(hist_file, line + "\n")
            except Exception as e:
                print(f"virtux: warning: could not write to HISTFILE: {e}", file=sys.stderr)

    def _load_state(self) -> None:
        """Load state using either the single-file or legacy files."""
        if self.persist_path and os.path.exists(self.persist_path):
            super()._load_state()
            return

        try:
            if os.path.exists(self._fs_path):
                self.fs.load(self._fs_path)
            if os.path.exists(self._env_path):
                with open(self._env_path, encoding="utf-8") as f:
                    data = json.load(f)
                if "env" in data:
                    self.env.from_dict(data["env"])
                if "users" in data:
                    self._users.from_dict(data["users"])
        except Exception as e:
            print(f"virtux: warning: could not load legacy session state: {e}", file=sys.stderr)

    def _save_state(self) -> None:
        """Save state using the new single-file format."""
        if self._persist:
            super()._save_state()