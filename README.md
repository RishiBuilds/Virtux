# 🐧 Virtux

**A realistic Linux terminal, simulated entirely in Python - runs anywhere Python runs.**

[![PyPI version](https://img.shields.io/pypi/v/virtux.svg)](https://pypi.org/project/virtux/)
[![Python versions](https://img.shields.io/pypi/pyversions/virtux.svg)](https://pypi.org/project/virtux/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Downloads](https://img.shields.io/pypi/dm/virtux.svg)](https://pypi.org/project/virtux/)

Virtux gives you a full Linux shell experience - filesystem, permissions, piping, 75+ coreutils-style commands - without a VM, container, Docker daemon, or WSL install. It's pure Python, starts in milliseconds, and behaves close enough to a real shell that it's genuinely useful for teaching, testing, and sandboxed scripting.

```bash
pip install virtux
```

```
user@virtux:~$ mkdir -p projects/my-app && cd projects/my-app
user@virtux:~/projects/my-app$ echo "Hello World!" > README.md
user@virtux:~/projects/my-app$ cat README.md | grep Hello
Hello World!
```

---

## Table of Contents

- [Why Virtux?](#why-virtux)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage Modes](#usage-modes)
- [Command Reference](#command-reference)
- [Python API](#python-api)
- [Plugin System](#plugin-system)
- [Configuration](#configuration)
- [How It Compares](#how-it-compares)
- [FAQ](#faq)
- [Contributing](#contributing)
- [License](#license)

---

## Why Virtux?

Most "learn Linux" tools fall into two camps: a real VM/container (heavy, slow to spin up, needs admin rights) or a toy JS terminal in a browser (not scriptable, no real Python integration). Virtux sits in between:

| Need                                  | Virtux | Real VM / Docker | Browser sandbox |
| ------------------------------------- | ------ | ---------------- | --------------- |
| Works on Windows without WSL          | ✅     | ❌               | ✅              |
| Starts in under a second              | ✅     | ❌               | ✅              |
| Real piping, redirection, exit codes  | ✅     | ✅               | ⚠️ limited      |
| Embeddable in a Python app/test suite | ✅     | ⚠️ awkward       | ❌              |
| Zero system dependencies              | ✅     | ❌               | ✅              |
| Persistent state between runs         | ✅     | ✅               | ⚠️ varies       |

If you need to **teach** shell basics, **test** CLI tools without touching the real filesystem, or **embed** a sandboxed shell inside another Python app, Virtux is built for exactly that.

## Features

- 🖥️ **Realistic shell** - colorized prompt, tab completion, reverse-search history (`Ctrl+R`), multi-line editing
- 📁 **Virtual filesystem** - a full hierarchical tree (`/home`, `/etc`, `/tmp`, `/var`, …) backed by an in-memory or on-disk store
- 🔗 **Real piping & redirection** - `|`, `>`, `>>`, `<`, `2>`, `&>`, `&&`, `||`, `;`, subshells with `()`
- 🔒 **Users & permissions** - `chmod`, `chown`, `chgrp`, `umask`, `sudo`, `su`, full rwx + octal permission model with enforcement
- 📝 **75+ built-in commands** - see the [full reference](#command-reference) below
- 💾 **Persistent sessions** - your virtual filesystem and history survive across runs (stored in `~/.virtux/`)
- 🔌 **Plugin system** - add your own commands via Python entry points, no fork required
- 🛡️ **Fully sandboxed** - nothing Virtux does ever touches your real filesystem, network, or processes
- 🧪 **Scriptable & testable** - drive it from `pytest`, assert on output/exit codes, reset state between tests
- 🌍 **Cross-platform** - identical behavior on Windows, macOS, and Linux since it isn't backed by the host shell

## Installation

```bash
pip install virtux
```

Requires **Python 3.9+**. No compiled extensions, no system packages, no admin/root access needed.

To verify:

```bash
virtux --version
```

## Quick Start

### Interactive Shell

```bash
virtux
```

```
 ╦  ╦╦╦═╗╔╦╗╦ ╦═╗ ╦
 ╚╗╔╝║╠╦╝ ║ ║ ║╔╩╦╝
  ╚╝ ╩╩╚═ ╩ ╚═╝╩ ╚═
  Linux Terminal Emulator v0.1.0

user@virtux:~$ mkdir -p projects/my-app
user@virtux:~$ echo "Hello World!" > projects/my-app/README.md
user@virtux:~$ cat projects/my-app/README.md
Hello World!
user@virtux:~$ ls -la projects/
drwxr-xr-x  2 user user  4096 Jun 23 12:00 my-app
user@virtux:~$ find / -name "*.md"
/home/user/projects/my-app/README.md
user@virtux:~$ chmod 600 projects/my-app/README.md && ls -l projects/my-app/
-rw-------  1 user user  13 Jun 23 12:00 README.md
```

### One-Off Command

Run a single command and exit - handy for quick checks or shell scripts:

```bash
virtux -c "ls -la /etc"
```

### Script Execution

Run a `.sh` file just like `bash script.sh` would:

```bash
virtux script.sh
```

```bash
# script.sh
#!/usr/bin/env virtux
mkdir -p /tmp/build
for f in *.txt; do
  cp "$f" /tmp/build/
done
echo "Build staged: $(ls /tmp/build | wc -l) files"
```

## Usage Modes

| Mode         | Command                          | Best for                                 |
| ------------ | -------------------------------- | ---------------------------------------- |
| Interactive  | `virtux`                         | Learning, exploring, manual testing      |
| One-shot     | `virtux -c "cmd"`                | Scripts, CI checks, quick lookups        |
| Script file  | `virtux script.sh`               | Reusable automation, classroom exercises |
| Embedded API | `from virtux import VirtuxShell` | Apps, test suites, custom tooling        |

## Command Reference

<details>
<summary><strong>📁 Filesystem</strong> (15 commands)</summary>

`ls` `cd` `pwd` `mkdir` `rmdir` `rm` `cp` `mv` `touch` `ln` `find` `stat` `du` `df` `tree`

</details>

<details>
<summary><strong>📝 Text processing</strong> (13 commands)</summary>

`cat` `head` `tail` `grep` `wc` `sort` `uniq` `cut` `sed` `awk` `echo` `tee` `diff`

</details>

<details>
<summary><strong>⚙️ System</strong> (23 commands)</summary>

`whoami` `uname` `hostname` `date` `cal` `uptime` `env` `export` `unset` `alias` `unalias` `history` `clear` `exit` `man` `help` `which` `type` `id` `printenv` `true` `false` `sleep`

</details>

<details>
<summary><strong>🔒 Shell & permissions</strong> (9 commands)</summary>

`chmod` `chown` `chgrp` `umask` `sudo` `su` `source` `bash` `sh`

</details>

<details>
<summary><strong>🌐 Network</strong> (6 commands, simulated)</summary>

`ping` `ifconfig` `ip` `curl` `wget` `ssh`

> Network commands return realistic, deterministic output but never make real network calls - safe to script against without side effects.

</details>

<details>
<summary><strong>📦 Archives & compression</strong> (5 commands)</summary>

`tar` `gzip` `gunzip` `zip` `unzip`

</details>

<details>
<summary><strong>📊 Process management</strong> (4 commands, simulated)</summary>

`ps` `top` `kill` `jobs`

</details>

Run `man <command>` or `help` inside the shell for full usage and flags for any of the above.

## Python API

Embed Virtux directly in your own application or test suite:

```python
from virtux import VirtuxShell

shell = VirtuxShell()
output = shell.execute("echo 'Hello from Python!'")
print(output)  # Hello from Python!
```

### Capturing exit codes and errors

```python
result = shell.run("ls /nonexistent")
print(result.stdout)      # ""
print(result.stderr)      # "ls: /nonexistent: No such file or directory"
print(result.exit_code)   # 2
```

### Resetting state between tests

```python
import pytest
from virtux import VirtuxShell

@pytest.fixture
def shell():
    s = VirtuxShell(persist=False)  # fresh, in-memory filesystem
    yield s
    s.reset()

def test_mkdir_creates_directory(shell):
    shell.execute("mkdir /tmp/demo")
    assert shell.execute("test -d /tmp/demo && echo yes") == "yes\n"
```

### Pre-seeding a virtual filesystem

```python
shell = VirtuxShell()
shell.fs.write_file("/etc/myapp.conf", "debug=true\n")
shell.execute("cat /etc/myapp.conf")  # debug=true
```

## Plugin System

Add custom commands without forking the project, using standard Python entry points:

```python
# my_virtux_plugin/plugin.py
def register(registry):
    @registry.register("mycommand", help_text="My custom command")
    def cmd_mycommand(ctx):
        ctx.writeln("Hello from my plugin!")
        return 0
```

```toml
# pyproject.toml
[project.entry-points."virtux.plugins"]
my_plugin = "my_virtux_plugin.plugin:register"
```

Once installed (`pip install .` or `pip install my-virtux-plugin`), `mycommand` is available automatically in every Virtux session - no extra registration step needed.

**`ctx` gives plugin authors access to:**

| Member                                  | Purpose                       |
| --------------------------------------- | ----------------------------- |
| `ctx.writeln(text)` / `ctx.write(text)` | Write to stdout               |
| `ctx.error(text)`                       | Write to stderr               |
| `ctx.args`                              | Parsed argument list          |
| `ctx.fs`                                | Virtual filesystem handle     |
| `ctx.env`                               | Current environment variables |
| `ctx.cwd`                               | Current working directory     |

## Configuration

| CLI flag              | Effect                                                 |
| --------------------- | ------------------------------------------------------ |
| `virtux`              | Launch interactive shell                               |
| `virtux -c "command"` | Execute a single command and exit                      |
| `virtux script.sh`    | Run a script file                                      |
| `virtux --reset`      | Wipe the persisted virtual filesystem and start clean  |
| `virtux --no-persist` | Run with an in-memory filesystem that discards on exit |
| `virtux --version`    | Print the installed version                            |

By default, session state (filesystem + history) is stored at `~/.virtux/`. Override with the `VIRTUX_HOME` environment variable:

```bash
export VIRTUX_HOME=/tmp/my-virtux-sandbox
virtux
```

## How It Compares

|                               | Virtux               | WSL             | Docker container        | xterm.js + node-pty              |
| ----------------------------- | -------------------- | --------------- | ----------------------- | -------------------------------- |
| Install footprint             | `pip install`        | OS feature, GBs | Docker daemon required  | Node + native pty bindings       |
| Cold start                    | Milliseconds         | Seconds–minutes | Seconds                 | Seconds                          |
| Cross-platform parity         | Identical everywhere | Windows-only    | Needs Docker Desktop    | Needs a real OS shell underneath |
| Touches real filesystem       | Never                | Yes             | Yes (namespaced)        | Yes                              |
| Embeds in a Python test suite | Native               | Awkward         | Possible via SDK, heavy | Not applicable                   |

Virtux isn't a replacement for a real Linux box when you need actual binaries, real networking, or kernel-level behavior - it's a lightweight, safe stand-in for teaching, prototyping, and testing shell-driven workflows.

## FAQ

**Does Virtux run real binaries?**
No. Every command is a Python implementation that mimics real Linux behavior closely enough for scripting, teaching, and testing - but nothing is shelled out to your OS.

**Can it break my actual files?**
No. The virtual filesystem is fully isolated, whether it's in-memory (`--no-persist`) or persisted under `~/.virtux/`.

**Does `sudo`/`su` do anything real?**
They simulate the permission model (UID/GID switching, permission checks) within the virtual filesystem only - there's no real privilege escalation possible.

**Can I use it in CI?**
Yes - `virtux --no-persist -c "..."` is ideal for CI: deterministic, no host side effects, no setup steps.

## Contributing

Issues and PRs are welcome. Before opening a PR:

```bash
git clone https://github.com/RishiBuilds/Virtux.git
cd Virtux
pip install -e ".[dev]"
pytest
```

Please include tests for new commands or behavior changes - see `tests/` for examples of the expected style.

## License

MIT License - see [LICENSE](LICENSE) for details.
