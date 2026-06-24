"""
Shell executor - wires up pipelines, handles redirection, and dispatches
parsed commands to the command registry.
"""

import io
import sys
import traceback
from typing import List, Any

from virtux.core.parser import Pipeline, Command, Redirect, parse, ParseError
from virtux.core.registry import get_command, ExecutionContext

_plugins_loaded = False


class Executor:
    """Executes a list of Pipelines produced by the parser."""
    fs: Any
    env: Any
    registry: Any
    users: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        fs = None
        env = None
        registry = None
        users = None

        if len(args) == 4:
            registry = args[0]
            fs = args[1]
            env = args[2]
            users = args[3]
        elif len(args) == 2:
            fs = args[0]
            env = args[1]
        else:
            fs = kwargs.get("fs")
            env = kwargs.get("env")
            registry = kwargs.get("registry")
            users = kwargs.get("users")
            if fs is None and len(args) > 0:
                fs = args[0]
            if env is None and len(args) > 1:
                env = args[1]

        self.fs = fs
        self.env = env

        if registry is None:
            from virtux.registry import CommandRegistry
            from virtux.commands import register_all_commands
            from virtux.plugins import discover_plugins

            global _plugins_loaded
            registry = CommandRegistry()
            register_all_commands(registry)
            if not _plugins_loaded:
                discover_plugins(registry)
                _plugins_loaded = True
        self.registry = registry

        if users is None:
            from virtux.users import UserManager
            users = UserManager()
        self.users = users

    @property
    def last_exit_code(self) -> int:
        return getattr(self.env, "last_exit_code", 0)

    def run_line(self, line: str) -> int:
        stripped = line.strip()
        if stripped and hasattr(self.env, "add_history"):
            self.env.add_history(stripped)
        try:
            pipelines = parse(line, env=self.env, fs=self.fs)
        except ParseError as e:
            sys.stderr.write(f"virtux: parse error: {e}\n")
            return 1

        last_code = 0
        for pipeline in pipelines:
            if pipeline.operator == "&&" and last_code != 0:
                continue
            if pipeline.operator == "||" and last_code == 0:
                continue
            last_code = self._run_pipeline(pipeline)

        self.env.last_exit_code = last_code
        return last_code

    def execute(self, cmd_list, stdin=None, stdout=None, stderr=None) -> int:
        """Legacy compatibility entry point. Executes a parsed CommandList AST."""
        if stdin is None:
            stdin = sys.stdin
        if stdout is None:
            stdout = sys.stdout
        if stderr is None:
            stderr = sys.stderr

        new_pipelines = []
        for i, legacy_pipe in enumerate(cmd_list.pipelines):
            operator = ";"
            if i > 0 and i - 1 < len(cmd_list.operators):
                operator = cmd_list.operators[i - 1]

            new_pipe = Pipeline()
            new_pipe.operator = operator

            for legacy_cmd in legacy_pipe.commands:
                new_cmd = Command()
                new_cmd.args = [self.env.expand_vars(arg) for arg in legacy_cmd.full_args]
                new_cmd.background = legacy_pipe.background
                for legacy_redir in legacy_cmd.redirects:
                    new_cmd.redirects.append(Redirect(
                        kind=legacy_redir.type,
                        target=self.env.expand_vars(legacy_redir.target)
                    ))
                new_pipe.commands.append(new_cmd)
            new_pipelines.append(new_pipe)

        last_code = 0
        for pipeline in new_pipelines:
            if pipeline.operator == "&&" and last_code != 0:
                continue
            if pipeline.operator == "||" and last_code == 0:
                continue
            last_code = self._run_pipeline(pipeline, stdin=stdin, stdout=stdout, stderr=stderr)

        if hasattr(self.env, "last_exit_code"):
            self.env.last_exit_code = last_code
        return last_code

    def _run_pipeline(self, pipeline: Pipeline, stdin=None, stdout=None, stderr=None) -> int:
        if stdin is None:
            stdin = sys.stdin
        if stdout is None:
            stdout = sys.stdout
        if stderr is None:
            stderr = sys.stderr

        cmds = pipeline.commands
        if not cmds:
            return 0

        if len(cmds) == 1:
            return self._run_command(cmds[0], stdin=stdin, stdout=stdout, stderr=stderr)

        buffers = [io.StringIO() for _ in range(len(cmds) - 1)]
        exit_code = 0

        for idx, cmd in enumerate(cmds):
            cmd_stdin = buffers[idx - 1] if idx > 0 else stdin
            if idx > 0:
                buffers[idx - 1].seek(0)

            is_last = idx == len(cmds) - 1
            cmd_stdout = stdout if is_last else buffers[idx]
            exit_code = self._run_command(cmd, stdin=cmd_stdin, stdout=cmd_stdout, stderr=stderr)

        return exit_code

    def _run_command(self, cmd: Command, stdin, stdout, stderr=None) -> int:
        if stderr is None:
            stderr = sys.stderr
        if not cmd.args:
            return 0

        stdin_stream, stdout_stream, stderr_stream, open_files = \
            self._apply_redirects(cmd.redirects, stdin, stdout, stderr)

        ctx = ExecutionContext(
            fs=self.fs,
            env=self.env,
            stdin=stdin_stream,
            stdout=stdout_stream,
            stderr=stderr_stream,
        )
        ctx.registry = self.registry
        ctx.users = self.users

        if hasattr(self.fs, "set_access_context"):
            self.fs.set_access_context(
                self.users.current_user,
                self.users.get_user_groups(),
            )

        try:
            return self._dispatch(cmd.args, ctx, real_stderr=stderr)
        finally:
            if isinstance(stdout_stream, io.StringIO) and stdout_stream is not stdout:
                stdout_stream.seek(0)
                stdout.write(stdout_stream.read())
            for f in open_files:
                f.close(real_stderr=stderr)

    def _dispatch(self, args: List[str], ctx: ExecutionContext, real_stderr=None) -> int:
        name = args[0]

        if not name:
            return 0

        if "=" in name and not name.startswith("-") and name.split("=", 1)[0].isidentifier():
            key, _, value = name.partition("=")
            self.env.set_var(key, value)
            return 0

        cmd_cls = get_command(name)
        if cmd_cls is not None:
            try:
                code = cmd_cls().execute(args, ctx)
                _flush_stderr(ctx, real_stderr=real_stderr)
                return code if code is not None else 0
            except KeyboardInterrupt:
                ctx.error("")
                return 130
            except Exception as exc:
                if "--debug" in args or self._debug_enabled():
                    ctx.error(f"virtux: {name}: {exc}\n{traceback.format_exc()}")
                else:
                    ctx.error(f"virtux: {name}: {exc}")
                _flush_stderr(ctx, real_stderr=real_stderr)
                return 1

        if self.registry is not None and hasattr(self.registry, "execute"):
            from virtux.registry import CommandContext

            legacy_ctx = CommandContext(
                fs=ctx.fs,
                env=ctx.env,
                users=ctx.users,
                stdin=ctx.stdin,
                stdout=ctx.stdout,
                stderr=ctx.stderr,
                args=args[1:],
                cwd=getattr(ctx, "cwd", None) or ctx.env.cwd,
                last_exit_code=getattr(ctx, "last_exit_code", 0),
                registry=self.registry,
            )
            try:
                code = self.registry.execute(name, legacy_ctx)
                _flush_stderr(ctx, real_stderr=real_stderr)
                return int(code)
            except KeyboardInterrupt:
                ctx.error("")
                return 130
            except Exception as exc:
                if self._debug_enabled():
                    ctx.error(f"virtux: {name}: {exc}\n{traceback.format_exc()}")
                else:
                    ctx.error(f"virtux: {name}: {exc}")
                _flush_stderr(ctx, real_stderr=real_stderr)
                return 1

        ctx.error(f"virtux: {name}: command not found")
        _flush_stderr(ctx, real_stderr=real_stderr)
        return 127

    def _debug_enabled(self) -> bool:
        return bool(getattr(self.env, "get_var", lambda *_: "")("VIRTUX_DEBUG"))

    def _apply_redirects(self, redirects: List[Redirect], default_stdin, default_stdout, default_stderr=None):
        if default_stderr is None:
            default_stderr = sys.stderr
        stdin_stream = default_stdin
        stdout_stream = default_stdout
        stderr_stream = default_stderr
        open_files = []

        for redir in redirects:
            path = self.fs.normalize(redir.target, self.env.cwd)
            if redir.kind == "in":
                try:
                    data = self.fs.read_file(path).decode("utf-8", errors="replace")
                    stdin_stream = io.StringIO(data)
                except Exception as e:
                    default_stderr.write(f"virtux: {redir.target}: {e}\n")
            elif redir.kind in ("out", "append"):
                buf = _VFSWriteBuffer(self.fs, path, append=(redir.kind == "append"))
                stdout_stream = buf
                open_files.append(buf)
            elif redir.kind in ("err", "err_append"):
                buf = _VFSWriteBuffer(
                    self.fs, path, append=(redir.kind == "err_append")
                )
                stderr_stream = buf
                open_files.append(buf)

        return stdin_stream, stdout_stream, stderr_stream, open_files


def _flush_stderr(ctx: ExecutionContext, real_stderr=None):
    if real_stderr is None:
        real_stderr = sys.stderr

    if isinstance(ctx.stderr, _VFSWriteBuffer):
        return

    if ctx.stderr is real_stderr:
        if hasattr(real_stderr, "flush"):
            real_stderr.flush()
    else:
        if isinstance(ctx.stderr, io.StringIO):
            ctx.stderr.seek(0)
            content = ctx.stderr.read()
            if content:
                real_stderr.write(content)
                if hasattr(real_stderr, "flush"):
                    real_stderr.flush()
        elif hasattr(ctx.stderr, "flush"):
            ctx.stderr.flush()


class _VFSWriteBuffer(io.StringIO):
    """A StringIO that flushes its contents to the VFS on close."""

    def __init__(self, fs, path: str, append: bool = False):
        super().__init__()
        self._fs = fs
        self._path = path
        self._append = append

    def close(self, real_stderr=None):
        self.seek(0)
        data = self.read().encode("utf-8")
        if not data:
            super().close()
            return
        try:
            if self._append and self._fs.is_file(self._path):
                self._fs.append_file(self._path, data.decode("utf-8"))
            else:
                self._fs.write_file(self._path, data)
        except Exception as e:
            target = real_stderr if real_stderr is not None else sys.stderr
            target.write(f"virtux: {self._path}: write failed: {e}\n")
        super().close()