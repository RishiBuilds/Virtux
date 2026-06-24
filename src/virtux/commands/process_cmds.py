from __future__ import annotations

import random
import time
from typing import Any, TYPE_CHECKING

from virtux.commands import register

if TYPE_CHECKING:
    from virtux.registry import CommandContext


_SIMULATED_PROCESSES: list[dict[str, Any]] = [
    {"pid": 1,   "user": "root", "cpu": 0.0, "mem": 0.1, "vsz": 16960, "rss": 3400, "tty": "?", "stat": "Ss",  "start": "00:00", "time": "0:01", "command": "/sbin/init"},
    {"pid": 2,   "user": "root", "cpu": 0.0, "mem": 0.0, "vsz": 0,     "rss": 0,    "tty": "?", "stat": "S",   "start": "00:00", "time": "0:00", "command": "[kthreadd]"},
    {"pid": 234, "user": "root", "cpu": 0.1, "mem": 0.3, "vsz": 24580, "rss": 5200, "tty": "?", "stat": "Ssl", "start": "00:00", "time": "0:05", "command": "/usr/sbin/sshd"},
    {"pid": 567, "user": "root", "cpu": 0.0, "mem": 0.2, "vsz": 18432, "rss": 3800, "tty": "?", "stat": "Ss",  "start": "00:00", "time": "0:00", "command": "/usr/sbin/cron"},
    {"pid": 890, "user": "root", "cpu": 0.0, "mem": 0.4, "vsz": 65432, "rss": 8192, "tty": "?", "stat": "Ss",  "start": "00:00", "time": "0:02", "command": "/usr/sbin/rsyslogd"},
]

_SIGNAL_MAP = {"9": "KILL", "15": "TERM", "1": "HUP", "2": "INT"}


@register(
    "ps",
    help_text="Report a snapshot of current processes.",
    usage="ps [aux] [-e] [-f]",
    category="process",
)
def cmd_ps(ctx: CommandContext) -> int:
    show_all = "aux" in ctx.args or "-e" in ctx.args or "-ef" in ctx.args
    full_format = "-f" in ctx.args or "-ef" in ctx.args or "aux" in ctx.args

    shell_pid = random.randint(1000, 9999)
    processes = list(_SIMULATED_PROCESSES) + [
        {
            "pid": shell_pid, "user": ctx.users.current_user,
            "cpu": 0.2, "mem": 0.5, "vsz": 32768, "rss": 6144,
            "tty": "pts/0", "stat": "Ss", "start": "12:00",
            "time": "0:00", "command": "/usr/bin/virtux",
        },
        {
            "pid": shell_pid + 1, "user": ctx.users.current_user,
            "cpu": 0.0, "mem": 0.1, "vsz": 8192, "rss": 2048,
            "tty": "pts/0", "stat": "R+", "start": time.strftime("%H:%M"),
            "time": "0:00", "command": "ps aux" if show_all else "ps",
        },
    ]

    if show_all and full_format:
        ctx.writeln(f"{'USER':<10} {'PID':>5} {'%CPU':>5} {'%MEM':>5} {'VSZ':>7} {'RSS':>5} {'TTY':<6} {'STAT':<4} {'START':<5} {'TIME':<5} COMMAND")
        for p in processes:
            ctx.writeln(
                f"{p['user']:<10} {p['pid']:>5} {p['cpu']:>5.1f} {p['mem']:>5.1f} "
                f"{p['vsz']:>7} {p['rss']:>5} {p['tty']:<6} {p['stat']:<4} "
                f"{p['start']:<5} {p['time']:<5} {p['command']}"
            )
    else:
        ctx.writeln(f"  {'PID':>5} {'TTY':<8} {'TIME':<8} CMD")
        for p in processes:
            if p["user"] == ctx.users.current_user:
                ctx.writeln(f"  {p['pid']:>5} {p['tty']:<8} {p['time']:<8} {p['command']}")

    return 0


@register(
    "top",
    help_text="Display Linux tasks (simulated snapshot).",
    usage="top [-n 1]",
    category="process",
)
def cmd_top(ctx: CommandContext) -> int:
    ctx.writeln(f"top - {time.strftime('%H:%M:%S')} up 1 day,  0:00,  1 user,  load average: 0.15, 0.10, 0.05")
    ctx.writeln("Tasks:   7 total,   1 running,   6 sleeping,   0 stopped,   0 zombie")
    ctx.writeln("%Cpu(s):  2.3 us,  1.0 sy,  0.0 ni, 96.5 id,  0.2 wa,  0.0 hi,  0.0 si,  0.0 st")
    ctx.writeln("MiB Mem :   8000.0 total,   4000.0 free,   2500.0 used,   1500.0 buff/cache")
    ctx.writeln("MiB Swap:   2000.0 total,   2000.0 free,      0.0 used.   5000.0 avail Mem")
    ctx.writeln()
    ctx.writeln(f"  {'PID':>5} {'USER':<10} {'PR':>3} {'NI':>3} {'VIRT':>7} {'RES':>5} {'SHR':>5} {'S':<1} {'%CPU':>5} {'%MEM':>5} {'TIME+':>9} COMMAND")
    for p in _SIMULATED_PROCESSES:
        ctx.writeln(
            f"  {p['pid']:>5} {p['user']:<10} {'20':>3} {'0':>3} "
            f"{p['vsz']:>7} {p['rss']:>5} {p['rss'] // 2:>5} "
            f"{'S':<1} {p['cpu']:>5.1f} {p['mem']:>5.1f} "
            f"{'0:00.00':>9} {p['command'].split('/')[-1]}"
        )
    ctx.writeln(
        f"  {random.randint(1000, 9999):>5} {ctx.users.current_user:<10} {'20':>3} {'0':>3} "
        f"{'32768':>7} {'6144':>5} {'3072':>5} "
        f"{'R':<1} {'0.2':>5} {'0.5':>5} "
        f"{'0:00.01':>9} virtux"
    )
    return 0


@register(
    "kill",
    help_text="Send a signal to a process (simulated).",
    usage="kill [-signal] pid ...",
    category="process",
)
def cmd_kill(ctx: CommandContext) -> int:
    signal = "TERM"
    pids: list[str] = []

    for arg in ctx.args:
        if arg.startswith("-"):
            raw = arg[1:].upper()
            signal = _SIGNAL_MAP.get(raw, raw)
        else:
            pids.append(arg)

    if not pids:
        ctx.error("kill: missing pid")
        return 1

    known_pids = {str(p["pid"]) for p in _SIMULATED_PROCESSES}
    for pid in pids:
        if pid in known_pids:
            ctx.writeln(f"[simulated] Sent SIG{signal} to process {pid}")
        else:
            ctx.error(f"kill: ({pid}) - No such process")
            return 1

    return 0


@register(
    "jobs",
    help_text="List background jobs.",
    usage="jobs",
    category="process",
)
def cmd_jobs(ctx: CommandContext) -> int:
    ctx.writeln("(no background jobs)")
    return 0