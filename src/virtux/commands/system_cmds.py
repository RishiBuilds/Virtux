"""
System information commands for the Virtux shell.

Implements: whoami, uname, hostname, date, cal, uptime, env, export,
unset, alias, unalias, history, clear, exit, man, help, which, type
"""

from __future__ import annotations
from virtux.commands import register

import calendar
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtux.registry import CommandContext



@register(
    "whoami",
    help_text="Print the current user name.",
    usage="whoami",
    category="system",
)
def cmd_whoami(ctx: CommandContext) -> int:
    ctx.writeln(ctx.users.current_user)
    return 0

@register(
    "uname",
    help_text="Print system information.",
    usage="uname [-a] [-s] [-r] [-m] [-n] [-o]",
    category="system",
)
def cmd_uname(ctx: CommandContext) -> int:
    show_all = "-a" in ctx.args
    show_kernel = "-s" in ctx.args or not ctx.args
    show_release = "-r" in ctx.args
    show_machine = "-m" in ctx.args
    show_nodename = "-n" in ctx.args
    show_os = "-o" in ctx.args

    if show_all:
        ctx.writeln("Linux virtux 6.1.0-virtux #1 SMP PREEMPT_DYNAMIC x86_64 GNU/Linux")
        return 0

    parts = []
    if show_kernel:
        parts.append("Linux")
    if show_nodename:
        parts.append(ctx.env.hostname)
    if show_release:
        parts.append("6.1.0-virtux")
    if show_machine:
        parts.append("x86_64")
    if show_os:
        parts.append("GNU/Linux")

    ctx.writeln(" ".join(parts) if parts else "Linux")
    return 0

@register(
    "hostname",
    help_text="Show or set the system hostname.",
    usage="hostname",
    category="system",
)
def cmd_hostname(ctx: CommandContext) -> int:
    ctx.writeln(ctx.env.hostname)
    return 0

@register(
    "date",
    help_text="Display the current date and time.",
    usage="date [+format]",
    category="system",
)
def cmd_date(ctx: CommandContext) -> int:
    now = datetime.now()
    if ctx.args and ctx.args[0].startswith("+"):
        fmt = ctx.args[0][1:]
        fmt = fmt.replace("%Y", now.strftime("%Y"))
        ctx.writeln(now.strftime(fmt))
    else:
        ctx.writeln(now.strftime("%a %b %d %H:%M:%S UTC %Y"))
    return 0

@register(
    "cal",
    help_text="Display a calendar.",
    usage="cal [month] [year]",
    category="system",
)
def cmd_cal(ctx: CommandContext) -> int:
    now = datetime.now()
    month = now.month
    year = now.year

    non_flags = [a for a in ctx.args if not a.startswith("-")]
    if len(non_flags) >= 2:
        try:
            month = int(non_flags[0])
            year = int(non_flags[1])
        except ValueError:
            ctx.error("cal: invalid arguments")
            return 1
    elif len(non_flags) == 1:
        try:
            year = int(non_flags[0])
            if 1 <= year <= 12:
                month = year
                year = now.year
        except ValueError:
            ctx.error("cal: invalid argument")
            return 1

    cal_output = calendar.TextCalendar().formatmonth(year, month)
    ctx.write(cal_output)
    return 0

@register(
    "uptime",
    help_text="Tell how long the system has been running.",
    usage="uptime",
    category="system",
)
def cmd_uptime(ctx: CommandContext) -> int:
    now = datetime.now()
    uptime_secs = 86400 
    hours = uptime_secs // 3600
    mins = (uptime_secs % 3600) // 60

    ctx.writeln(
        f" {now.strftime('%H:%M:%S')} up {hours // 24} day(s), "
        f"{hours % 24}:{mins:02d},  1 user,  load average: 0.15, 0.10, 0.05"
    )
    return 0

@register(
    "env",
    help_text="Display or set environment variables.",
    usage="env",
    category="system",
)
def cmd_env(ctx: CommandContext) -> int:
    for key, value in sorted(ctx.env.get_all().items()):
        ctx.writeln(f"{key}={value}")
    return 0

@register(
    "export",
    help_text="Set environment variables.",
    usage="export NAME=VALUE",
    category="system",
)
def cmd_export(ctx: CommandContext) -> int:
    if not ctx.args:
        for key, value in sorted(ctx.env.get_all().items()):
            ctx.writeln(f'declare -x {key}="{value}"')
        return 0

    for arg in ctx.args:
        if "=" in arg:
            name, value = arg.split("=", 1)
            ctx.env.set(name, value)
        else:
            if not ctx.env.has(arg):
                ctx.env.set(arg, "")
    return 0

@register(
    "unset",
    help_text="Remove environment variables.",
    usage="unset NAME ...",
    category="system",
)
def cmd_unset(ctx: CommandContext) -> int:
    for name in ctx.args:
        ctx.env.unset(name)
    return 0

@register(
    "alias",
    help_text="Define or display aliases.",
    usage="alias [name='value']",
    category="system",
)
def cmd_alias(ctx: CommandContext) -> int:
    if not ctx.args:
        for name, value in sorted(ctx.env.get_all_aliases().items()):
            ctx.writeln(f"alias {name}='{value}'")
        return 0

    for arg in ctx.args:
        if "=" in arg:
            name, value = arg.split("=", 1)
            value = value.strip("'\"")
            ctx.env.set_alias(name, value)
        else:
            alias_val = ctx.env.get_alias(arg)
            if alias_val:
                ctx.writeln(f"alias {arg}='{alias_val}'")
            else:
                ctx.error(f"alias: {arg}: not found")
                return 1
    return 0

@register(
    "unalias",
    help_text="Remove aliases.",
    usage="unalias name ...",
    category="system",
)
def cmd_unalias(ctx: CommandContext) -> int:
    for name in ctx.args:
        if not ctx.env.unset_alias(name):
            ctx.error(f"unalias: {name}: not found")
            return 1
    return 0

@register(
    "history",
    help_text="Display command history.",
    usage="history [n]",
    category="system",
)
def cmd_history(ctx: CommandContext) -> int:
    try:
        hist_file = ctx.env.get("HISTFILE", "")
        if hist_file and ctx.fs.exists(hist_file):
            content = ctx.fs.read_text(hist_file)
            lines = content.splitlines()
            count = len(lines)
            if ctx.args:
                try:
                    count = int(ctx.args[0])
                    lines = lines[-count:]
                except ValueError:
                    pass

            start = max(1, len(content.splitlines()) - len(lines) + 1)
            for i, line in enumerate(lines, start):
                ctx.writeln(f"  {i:>4}  {line}")
        else:
            ctx.writeln("  (no history)")
    except Exception:
        ctx.writeln("  (no history)")
    return 0

@register(
    "clear",
    help_text="Clear the terminal screen.",
    usage="clear",
    category="system",
)
def cmd_clear(ctx: CommandContext) -> int:
    ctx.write("\033[2J\033[H")
    return 0

@register(
    "exit",
    help_text="Exit the shell.",
    usage="exit [code]",
    category="system",
    aliases=["logout", "quit"],
)
def cmd_exit(ctx: CommandContext) -> int:
    code = 0
    if ctx.args:
        try:
            code = int(ctx.args[0])
        except ValueError:
            pass
    raise SystemExit(code)

@register(
    "man",
    help_text="Display manual pages for commands.",
    usage="man command",
    category="system",
)
def cmd_man(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("What manual page do you want?")
        return 1

    cmd_name = ctx.args[0]
    if not ctx.registry:
        ctx.error("Registry not available")
        return 1
    info = ctx.registry.get(cmd_name)
    if info is None:
        ctx.error(f"No manual entry for {cmd_name}")
        return 1

    ctx.writeln(f"\033[1m{cmd_name.upper()}\033[0m(1){'':>20}User Commands{'':>20}\033[1m{cmd_name.upper()}\033[0m(1)")
    ctx.writeln()
    ctx.writeln("\033[1mNAME\033[0m")
    ctx.writeln(f"       {cmd_name} - {info.help_text}")
    ctx.writeln()
    ctx.writeln("\033[1mSYNOPSIS\033[0m")
    ctx.writeln(f"       {info.usage}")
    ctx.writeln()
    ctx.writeln("\033[1mDESCRIPTION\033[0m")
    ctx.writeln(f"       {info.help_text}")
    if info.aliases:
        ctx.writeln()
        ctx.writeln("\033[1mALIASES\033[0m")
        ctx.writeln(f"       {', '.join(info.aliases)}")
    ctx.writeln()
    ctx.writeln(f"Virtux 0.1.0{'':>30}VIRTUX{'':>30}{cmd_name.upper()}(1)")
    return 0

@register(
    "help",
    help_text="Display information about built-in commands.",
    usage="help [command]",
    category="system",
)
def cmd_help(ctx: CommandContext) -> int:
    if not ctx.registry:
        ctx.error("Registry not available")
        return 1

    if ctx.args:
        cmd_name = ctx.args[0]
        info = ctx.registry.get(cmd_name)
        if info:
            ctx.writeln(f"{cmd_name}: {info.usage}")
            ctx.writeln(f"    {info.help_text}")
            return 0
        else:
            ctx.error(f"help: no help topics match '{cmd_name}'")
            return 1

    ctx.writeln("\033[1mVirtux Shell - Built-in Commands\033[0m")
    ctx.writeln("=" * 50)
    ctx.writeln()

    categories = ctx.registry.list_by_category()
    category_names = {
        "filesystem": "[FS] File System",
        "text": "[TXT] Text Processing",
        "system": "[SYS] System",
        "shell": "[SH] Shell & Permissions",
        "network": "[NET] Network (Simulated)",
        "archive": "[ARC] Archive & Compression",
        "process": "[PS] Process Management",
    }

    for cat_key, cat_label in category_names.items():
        cmds = categories.get(cat_key, [])
        if cmds:
            ctx.writeln(f"\033[1;33m{cat_label}\033[0m")
            for info in cmds:
                aliases = f" ({', '.join(info.aliases)})" if info.aliases else ""
                ctx.writeln(f"  \033[1;32m{info.name:<14}\033[0m {info.help_text}{aliases}")
            ctx.writeln()

    ctx.writeln("Type 'man <command>' for detailed help on a specific command.")
    return 0

@register(
    "which",
    help_text="Locate a command.",
    usage="which command ...",
    category="system",
)
def cmd_which(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("which: missing argument")
        return 1

    if not ctx.registry:
        ctx.error("Registry not available")
        return 1

    for name in ctx.args:
        if ctx.registry.has(name):
            ctx.writeln(f"/usr/bin/{name}")
        else:
            ctx.error(f"which: no {name} in ({ctx.env.get('PATH', '')})")
            return 1
    return 0

@register(
    "type",
    help_text="Describe a command.",
    usage="type command ...",
    category="system",
)
def cmd_type(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("type: missing argument")
        return 1

    for name in ctx.args:
        alias = ctx.env.get_alias(name)
        if alias:
            ctx.writeln(f"{name} is aliased to '{alias}'")
        elif ctx.registry and ctx.registry.has(name):
            ctx.writeln(f"{name} is /usr/bin/{name}")
        else:
            ctx.error(f"-bash: type: {name}: not found")
            return 1
    return 0

@register(
    "id",
    help_text="Print user and group IDs.",
    usage="id [username]",
    category="system",
)
def cmd_id(ctx: CommandContext) -> int:
    username = ctx.args[0] if ctx.args else ctx.users.current_user
    user = ctx.users.get_user(username)
    if not user:
        ctx.error(f"id: '{username}': no such user")
        return 1

    groups = ctx.users.get_user_groups(username)
    group_strs = []
    for g in groups:
        grp = ctx.users.get_group(g)
        if grp:
            group_strs.append(f"{grp.gid}({grp.name})")

    primary_group = ctx.users.get_primary_group_name(username)
    primary_gid = user.gid

    ctx.writeln(
        f"uid={user.uid}({user.username}) "
        f"gid={primary_gid}({primary_group}) "
        f"groups={','.join(group_strs)}"
    )
    return 0

@register(
    "printenv",
    help_text="Print environment variables.",
    usage="printenv [NAME ...]",
    category="system",
)
def cmd_printenv(ctx: CommandContext) -> int:
    if not ctx.args:
        for key, value in sorted(ctx.env.get_all().items()):
            ctx.writeln(f"{key}={value}")
    else:
        for name in ctx.args:
            val = ctx.env.get(name)
            if val is not None:
                ctx.writeln(val)
            else:
                return 1
    return 0

@register(
    "true",
    help_text="Do nothing, successfully.",
    usage="true",
    category="system",
)
def cmd_true(ctx: CommandContext) -> int:
    return 0

@register(
    "false",
    help_text="Do nothing, unsuccessfully.",
    usage="false",
    category="system",
)
def cmd_false(ctx: CommandContext) -> int:
    return 1

@register(
    "sleep",
    help_text="Delay for a specified time (simulated).",
    usage="sleep seconds",
    category="system",
)
def cmd_sleep(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("sleep: missing operand")
        return 1
    try:
        secs = float(ctx.args[0])
        if secs > 0:
            import time as _time
            _time.sleep(min(secs, 2.0))  
    except ValueError:
        ctx.error(f"sleep: invalid time interval '{ctx.args[0]}'")
        return 1
    return 0
