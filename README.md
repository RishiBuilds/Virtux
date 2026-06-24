# 🐧 Virtux

Virtux is a cross-platform Linux shell simulator written in pure Python. It is built for learners, educators, and developers who want to practice real shell syntax—pipes, redirection, exit codes, permissions, and scripting—without installing WSL, Docker, or a Linux VM. Everything runs in a sandboxed in-memory (or optionally persisted) virtual filesystem, so mistyped `rm` commands cannot touch your real files.

[![PyPI version](https://img.shields.io/pypi/v/virtux.svg)](https://pypi.org/project/virtux/)
[![Python versions](https://img.shields.io/pypi/pyversions/virtux.svg)](https://pypi.org/project/virtux/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

```bash
pip install virtux
```

## Table of Contents

- [Quick start](#quick-start)
- [Example session](#example-session)
- [Features](#features)
- [Supported commands](#supported-commands)
- [Usage modes](#usage-modes)
- [Configuration & persistence](#configuration--persistence)
- [Python API](#python-api)
- [Plugin system](#plugin-system)
- [Limitations](#limitations)
- [Contributing](#contributing)
- [License](#license)

## Quick start

Launch the interactive REPL:

```bash
virtux
```

Run one command and exit (propagates the command's exit code):

```bash
virtux -c "ls /etc"
```

Run without saving or loading session state:

```bash
virtux --no-persist -c "echo hello"
```

Check the version:

```bash
virtux --version
# or
python -m virtux --version
```

Requires **Python 3.9+**. Dependencies: `prompt_toolkit`, `rich`, and `platformdirs` (used by supporting utilities; the REPL itself uses stdlib `input()` plus optional GNU readline when available).

## Example session

The interactive prompt follows `user@hostname:path$` (with `~` for your home directory). After a failing command, a `✗` marker appears before `$`, matching `Environment.get_prompt()`:

```console
 __   __ _      _
 \ \ / /(_)_ _| |_ _  ___ __
  \ V / | | '_|  _| || \ \ /
   \_/  |_|_|  \__|\_,_/_\_\

  A portable Linux shell simulator - type 'help' to begin.

user@virtux:~$ mkdir -p demo && cd demo
user@virtux:~/demo$ echo hello > msg.txt && cat msg.txt
hello
user@virtux:~/demo$ ls -la
total 8
drwxr-xr-x 1 user user     4096 Jan  1 12:00 .
drwxr-xr-x 1 user user     4096 Jan  1 12:00 ..
-rw-r--r-- 1 user user        6 Jan  1 12:00 msg.txt
user@virtux:~/demo$ false && echo skipped
user@virtux:~/demo$ ✗ ls /nope
ls: cannot access '/nope': No such file or directory
user@virtux:~/demo$ help cat
cat: cat [-n] [file ...]
    Concatenate files and print on the standard output.
```

## Features

- **Sandboxed virtual filesystem** — hierarchical tree (`/home`, `/etc`, `/tmp`, `/var`, …) stored in memory or JSON on disk
- **Real shell syntax** — pipes (`|`), redirection (`>`, `>>`, `<`, `2>`, `2>>`, `&>`), lists (`;`, `&&`, `||`), and background (`&`)
- **75 built-in commands** — file tools, text processing, permissions, simulated network/process commands, and more
- **Permission model** — `chmod`, `chown`, `umask`, `sudo`, and `su` with rwx checks enforced at the filesystem layer (root bypasses checks)
- **Cross-platform** — identical behaviour on Windows, macOS, and Linux; no host shell required
- **Embeddable** — drive sessions from Python or `pytest`, capture stdout/stderr/exit codes, reset between tests
- **Optional persistence** — save filesystem + environment to `~/.virtux/virtux_state.json` (override with `VIRTUX_HOME`)
- **Plugins** — register extra commands via Python entry points (see below)
- **Tab completion** — GNU readline completion when readline (or `pyreadline3` on Windows) is available

## Supported commands

Virtux registers **75 unique commands** (plus aliases such as `ll` → `ls -la`):

| Category | Commands |
| -------- | -------- |
| Filesystem | `ls`, `cd`, `pwd`, `mkdir`, `rmdir`, `rm`, `cp`, `mv`, `touch`, `ln`, `find`, `stat`, `du`, `df`, `tree` |
| Text | `cat`, `head`, `tail`, `grep`, `wc`, `sort`, `uniq`, `cut`, `sed`, `awk`, `echo`, `tee`, `diff` |
| System | `whoami`, `uname`, `hostname`, `date`, `cal`, `uptime`, `env`, `export`, `unset`, `alias`, `unalias`, `history`, `clear`, `exit`, `man`, `help`, `which`, `type`, `id`, `printenv`, `true`, `false`, `sleep` |
| Permissions / shell | `chmod`, `chown`, `chgrp`, `umask`, `sudo`, `su`, `source`, `bash`, `sh` |
| Network (simulated) | `ping`, `ifconfig`, `ip`, `curl`, `wget`, `ssh` |
| Archives | `tar`, `gzip`, `gunzip`, `zip`, `unzip` |
| Processes (simulated) | `ps`, `top`, `kill`, `jobs` |

Run `help` or `man <command>` inside the shell for usage details.

## Usage modes

| Mode | Command | Use case |
| ---- | ------- | -------- |
| Interactive | `virtux` | Learning, exploring, manual testing |
| One-shot | `virtux -c "cmd"` | Scripts, CI checks, quick lookups |
| Script file | `virtux script.sh` | Batch commands (VFS paths or host paths) |
| Embedded API | `from virtux import VirtuxShell` | Apps, test suites, tooling |
| Reset state | `virtux --reset` | Wipe persisted filesystem to defaults |
| Ephemeral | `virtux --no-persist` | In-memory session; nothing written on exit |

## Configuration & persistence

| Setting | Effect |
| ------- | ------ |
| Default data dir | `~/.virtux/` (contains `virtux_state.json` and readline `history` when persistence is on) |
| `VIRTUX_HOME` | Override the data directory |
| `--no-persist` | Skip loading and saving state; no readline history file |
| `VIRTUX_DEBUG=1` | Show full tracebacks for command handler errors |

Session state is stored as JSON (`json.dump` / `json.load` only—no `eval` or `pickle`). Malformed state files produce a warning and start from defaults.

On Windows, ANSI colours are enabled when possible; readline tab completion works if `pyreadline3` is installed, otherwise basic line editing is used.

## Python API

```python
from virtux import VirtuxShell

shell = VirtuxShell(persist=False)
print(shell.execute("echo Hello"))          # capture combined output
print(shell.executor.last_exit_code)        # 0

result = shell.run("ls /etc")
print(result.stdout, result.stderr, result.exit_code)
```

Pre-seed the virtual filesystem:

```python
shell = VirtuxShell()
shell.fs.write_file("/etc/myapp.conf", "debug=true\n")
shell.execute("cat /etc/myapp.conf")
```

## Plugin system

Plugins register commands through the `virtux.plugins` entry-point group:

```python
# my_plugin/register.py
def register(registry):
    @registry.register("greet", help_text="Say hello")
    def cmd_greet(ctx):
        ctx.writeln("Hello from a plugin!")
        return 0
```

```toml
[project.entry-points."virtux.plugins"]
my_plugin = "my_plugin.register:register"
```

**Trust boundary:** installing a third-party Virtux plugin grants it the same power as a built-in command—it can register handlers on the live command registry and access the virtual filesystem and environment. Only install plugins you trust, just as you would with shell functions sourced from untrusted scripts.

## Limitations

Virtux is a teaching sandbox, not a production shell:

- Commands are Python implementations; no real binaries, kernel, or network I/O
- `sudo`/`su` simulate UID switching inside the virtual environment only
- Permission checks apply to filesystem operations; they do not model every Linux edge case (ACLs, capabilities, etc.)
- Background jobs (`&`) are parsed but not scheduled as asynchronous tasks
- Some README-era bash features (subshells, `$()`, advanced job control) may be partial or absent—check `help` for what is implemented

For real Linux behaviour (actual `gcc`, sockets, containers), use WSL or a VM. For zero-setup CLI practice anywhere Python runs, Virtux is the lightweight option.

## Contributing

Issues and pull requests are welcome at [github.com/RishiBuilds/Virtux](https://github.com/RishiBuilds/Virtux).

```bash
git clone https://github.com/RishiBuilds/Virtux.git
cd Virtux
pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
python -m mypy src
```

Please add tests under `tests/` for new commands or behaviour changes.

## License

MIT License — see [LICENSE](LICENSE).
