from __future__ import annotations
from virtux.commands import register

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtux.registry import CommandContext


@register(
    "chown",
    help_text="Change file owner and group.",
    usage="chown [-R] owner[:group] file ...",
    category="shell",
)
def cmd_chown(ctx: CommandContext) -> int:
    if not ctx.users.is_root:
        ctx.error("chown: Operation not permitted (must be root)")
        return 1

    recursive = "-R" in ctx.args
    non_flags = [a for a in ctx.args if not a.startswith("-")]

    if len(non_flags) < 2:
        ctx.error("chown: missing operand")
        return 1

    owner_spec = non_flags[0]
    files = non_flags[1:]
    owner = None
    group = None

    if ":" in owner_spec:
        parts = owner_spec.split(":", 1)
        owner = parts[0] if parts[0] else None
        group = parts[1] if parts[1] else None
    else:
        owner = owner_spec

    for f in files:
        path = ctx.resolve_path(f)
        try:
            ctx.fs.chown(path, owner=owner, group=group)
            if recursive and ctx.fs.is_dir(path):
                _chown_recursive(ctx, path, owner, group)
        except Exception as e:
            ctx.error(f"chown: cannot access '{f}': {e}")
            return 1
    return 0


@register(
    "chgrp",
    help_text="Change group ownership.",
    usage="chgrp [-R] group file ...",
    category="shell",
)
def cmd_chgrp(ctx: CommandContext) -> int:
    if not ctx.users.is_root:
        ctx.error("chgrp: Operation not permitted (must be root)")
        return 1

    recursive = "-R" in ctx.args
    non_flags = [a for a in ctx.args if not a.startswith("-")]

    if len(non_flags) < 2:
        ctx.error("chgrp: missing operand")
        return 1

    group = non_flags[0]
    files = non_flags[1:]

    for f in files:
        path = ctx.resolve_path(f)
        try:
            ctx.fs.chown(path, group=group)
            if recursive and ctx.fs.is_dir(path):
                _chown_recursive(ctx, path, None, group)
        except Exception as e:
            ctx.error(f"chgrp: cannot access '{f}': {e}")
            return 1
    return 0


@register(
    "umask",
    help_text="Display or set the file mode creation mask.",
    usage="umask [mode]",
    category="shell",
)
def cmd_umask(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.writeln(f"{oct(ctx.fs.umask)[2:]:>04}")
        return 0

    try:
        mode = int(ctx.args[0], 8)
        ctx.fs.umask = mode
    except ValueError:
        ctx.error(f"umask: '{ctx.args[0]}': invalid octal number")
        return 1
    return 0


@register(
    "sudo",
    help_text="Execute a command as root.",
    usage="sudo [-u user] command [args ...]",
    category="shell",
)
def cmd_sudo(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("sudo: missing command")
        return 1

    user_groups = ctx.users.get_user_groups()
    if "sudo" not in user_groups and not ctx.users.is_root:
        ctx.error(f"{ctx.users.current_user} is not in the sudoers file. This incident will be reported.")
        return 1

    target_user = "root"
    args = list(ctx.args)

    if args[0] == "-u" and len(args) > 1:
        target_user = args[1]
        args = args[2:]

    if args[0] == "su":
        ctx.users.switch_user(target_user)
        ctx.env.update_user(target_user)
        return 0

    original_user = ctx.users.current_user
    ctx.users.switch_user(target_user)
    ctx.env.update_user(target_user)

    from virtux.registry import CommandContext as CC

    if not ctx.registry:
        ctx.error("Registry not available")
        return 1

    sub_ctx = CC(
        fs=ctx.fs,
        env=ctx.env,
        users=ctx.users,
        stdin=ctx.stdin,
        stdout=ctx.stdout,
        stderr=ctx.stderr,
        args=args[1:] if len(args) > 1 else [],
        cwd=ctx.cwd,
        registry=ctx.registry,
    )
    exit_code = ctx.registry.execute(args[0], sub_ctx)

    ctx.users.switch_user(original_user)
    ctx.env.update_user(original_user)

    return exit_code


@register(
    "su",
    help_text="Switch user.",
    usage="su [username]",
    category="shell",
)
def cmd_su(ctx: CommandContext) -> int:
    target = ctx.args[0] if ctx.args else "root"

    if not ctx.users.user_exists(target):
        ctx.error(f"su: user {target} does not exist")
        return 1

    ctx.users.switch_user(target)
    ctx.env.update_user(target)
    ctx.env.cwd = ctx.users.current_home
    return 0


@register(
    "source",
    help_text="Execute commands from a file in the current shell.",
    usage="source filename",
    category="shell",
    aliases=["."],
)
def cmd_source(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("source: missing filename")
        return 1

    path = ctx.resolve_path(ctx.args[0])
    try:
        content = ctx.fs.read_text(path)
    except Exception as e:
        ctx.error(f"source: {ctx.args[0]}: {e}")
        return 1

    from virtux.parser import parse_command_line
    from virtux.executor import Executor

    if not ctx.registry:
        ctx.error("Registry not available")
        return 1

    executor = Executor(ctx.registry, ctx.fs, ctx.env, ctx.users)
    exit_code = 0

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        exit_code = executor.execute(parse_command_line(line), ctx.stdin, ctx.stdout, ctx.stderr)

    return exit_code


@register(
    "bash",
    help_text="Execute a bash script.",
    usage="bash [script_file]",
    category="shell",
)
def cmd_bash(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.writeln("virtux: entering sub-shell (type 'exit' to return)")
        return 0

    path = ctx.resolve_path(ctx.args[0])
    try:
        content = ctx.fs.read_text(path)
    except Exception as e:
        ctx.error(f"bash: {ctx.args[0]}: {e}")
        return 1

    from virtux.parser import parse_command_line
    from virtux.executor import Executor

    if not ctx.registry:
        ctx.error("Registry not available")
        return 1

    executor = Executor(ctx.registry, ctx.fs, ctx.env, ctx.users)
    exit_code = 0

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        exit_code = executor.execute(parse_command_line(line), ctx.stdin, ctx.stdout, ctx.stderr)

    return exit_code


@register(
    "sh",
    help_text="Execute a shell script.",
    usage="sh [script_file]",
    category="shell",
    aliases=["dash"],
)
def cmd_sh(ctx: CommandContext) -> int:
    return cmd_bash(ctx)


def _chown_recursive(
    ctx: CommandContext,
    path: str,
    owner: str | None,
    group: str | None,
) -> None:
    from virtux.utils import normalize_path

    try:
        for name in ctx.fs.listdir(path):
            child_path = normalize_path(name, path)
            try:
                ctx.fs.chown(child_path, owner=owner, group=group)
                if ctx.fs.is_dir(child_path):
                    _chown_recursive(ctx, child_path, owner, group)
            except Exception:
                pass
    except Exception:
        pass