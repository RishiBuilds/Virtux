<p align="center">
  <br>
  <strong style="font-size: 2em;">🐧 Virtux</strong>
  <br>
  <em>A sandboxed Linux shell simulator, written in pure Python.</em>
  <br><br>
  <a href="https://pypi.org/project/virtux/"><img src="https://img.shields.io/pypi/v/virtux.svg?style=flat-square&color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/virtux/"><img src="https://img.shields.io/pypi/pyversions/virtux.svg?style=flat-square" alt="Python versions"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT"></a>
</p>

---

Practice real shell syntax, pipes, redirection, exit codes, permissions, scripting, without WSL, Docker, or a Linux VM. Virtux runs an in-memory (or optionally persisted) virtual filesystem, so a mistyped `rm -rf` can't touch a single real file on your machine.

```bash
pip install virtux
```

```console
user@virtux:~$ mkdir -p demo && cd demo
user@virtux:~/demo$ echo hello > msg.txt && cat msg.txt
hello
user@virtux:~/demo$ cat msg.txt | grep -c hello
1
```

---

## Table of Contents

- [Quick Start](#quick-start)
- [Example Session](#example-session)
- [Features](#features)
- [Supported Commands](#supported-commands)
- [Usage Modes](#usage-modes)
- [Configuration & Persistence](#configuration--persistence)
- [Python API](#python-api)
- [Testing with Virtux](#testing-with-virtux)
- [Architecture](#architecture)
- [Plugin System](#plugin-system)
- [Limitations](#limitations)
- [Contributing](#contributing)
- [License](#license)

---

## Quick Start

**Requirements:** Python 3.9+

Launch the interactive REPL:

```bash
virtux
```

Run a single command and exit. The exit code propagates to your host shell, so this is usable in CI pipelines and scripts:

```bash
virtux -c "ls /etc"
```

Run a script file. Accepts VFS paths or host filesystem paths:

```bash
virtux script.sh
```

Run an ephemeral session, nothing loaded or saved on exit:

```bash
virtux --no-persist -c "echo hello"
```

Check the version:

```bash
virtux --version
python -m virtux --version
```

Wipe persisted state and start fresh:

```bash
virtux --reset
```

> **Dependencies:** `prompt_toolkit`, `rich`, and `platformdirs`. The REPL uses stdlib `input()` plus optional GNU readline when available.

---

## Example Session

The prompt follows `user@hostname:path$` (with `~` for home). A `✗` marker appears before `$` after a failing command:

```console
 __   __ _      _
 \ \ / /(_)_ _| |_ _  ___ __
  \ V / | | '_|  _| || \ \ /
   \_/  |_|_|  \__|\\_,_/_\_\

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
user@virtux:~/demo$ cat msg.txt | grep -c hello
1
user@virtux:~/demo$ help cat
cat: cat [-n] [file ...]
    Concatenate files and print on the standard output.
```

---

## Features

| Feature                          | Description                                                                                                                                                |
| :------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sandboxed virtual filesystem** | Hierarchical tree (`/home`, `/etc`, `/tmp`, `/var`, ...) stored in memory or persisted to JSON. Your real files are never touched.                         |
| **Real shell syntax**            | Pipes (`\|`), redirection (`>`, `>>`, `<`, `2>`, `2>>`, `&>`), command lists (`;`, `&&`, `\|\|`), background (`&`), variable expansion (`$VAR`, `${VAR}`). |
| **75 built-in commands**         | File tools, text processing, permissions, simulated network and process commands, and more.                                                                |
| **Permission model**             | `chmod`, `chown`, `umask`, `sudo`, and `su` with rwx checks enforced at the filesystem layer. Root bypasses permission checks.                             |
| **Cross-platform**               | Identical behavior on Windows, macOS, and Linux. No host shell or system dependencies required.                                                            |
| **Embeddable Python API**        | Drive sessions from Python or `pytest`. Capture stdout, stderr, and exit codes. Reset state between tests.                                                 |
| **Optional persistence**         | Save filesystem and environment state to `~/.virtux/virtux_state.json`. Override with `VIRTUX_HOME`.                                                       |
| **Plugin system**                | Register extra commands via Python entry points.                                                                                                           |
| **Tab completion**               | GNU readline completion when `readline` (or `pyreadline3` on Windows) is available.                                                                        |
| **Colorized prompt**             | ANSI-colored user/host/path, red prompt for root, `✗` indicator after failed commands.                                                                     |

---

## Supported Commands

75 unique commands, plus aliases (`ll` → `ls -la`, `la` → `ls -a`). Run `help` or `man <command>` inside the shell for usage details on any of them.

| Category                       | Commands                                                                                                                                                                               |
| :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Filesystem** (15)            | `ls` `cd` `pwd` `mkdir` `rmdir` `rm` `cp` `mv` `touch` `ln` `find` `stat` `du` `df` `tree`                                                                                             |
| **Text processing** (13)       | `cat` `head` `tail` `grep` `wc` `sort` `uniq` `cut` `sed` `awk` `echo` `tee` `diff`                                                                                                    |
| **System & shell** (23)        | `whoami` `uname` `hostname` `date` `cal` `uptime` `env` `export` `unset` `alias` `unalias` `history` `clear` `exit` `man` `help` `which` `type` `id` `printenv` `true` `false` `sleep` |
| **Permissions & builtins** (9) | `chmod` `chown` `chgrp` `umask` `sudo` `su` `source` `bash` `sh`                                                                                                                       |
| **Network** (6, simulated)     | `ping` `ifconfig` `ip` `curl` `wget` `ssh`                                                                                                                                             |
| **Archives** (5)               | `tar` `gzip` `gunzip` `zip` `unzip`                                                                                                                                                    |
| **Processes** (4, simulated)   | `ps` `top` `kill` `jobs`                                                                                                                                                               |

---

## Usage Modes

| Mode             | Command                          | Use Case                                   |
| :--------------- | :------------------------------- | :----------------------------------------- |
| **Interactive**  | `virtux`                         | Learning, exploring, manual testing        |
| **One-shot**     | `virtux -c "cmd"`                | Scripts, CI checks, quick lookups          |
| **Script file**  | `virtux script.sh`               | Batch commands (VFS or host paths)         |
| **Embedded API** | `from virtux import VirtuxShell` | Apps, test suites, custom tooling          |
| **Reset**        | `virtux --reset`                 | Wipe persisted filesystem to defaults      |
| **Ephemeral**    | `virtux --no-persist`            | In-memory session; nothing written on exit |

---

## Configuration & Persistence

**Data directory:** `~/.virtux/` by default, containing `virtux_state.json` and the readline `history` file. Override with the `VIRTUX_HOME` environment variable.

**CLI flags:**

| Flag              | Description                                             |
| :---------------- | :------------------------------------------------------ |
| `--no-persist`    | Skip loading and saving state; no readline history file |
| `--reset`         | Reset virtual filesystem to factory defaults            |
| `-c "cmd"`        | Execute a single command and exit                       |
| `-V`, `--version` | Print version and exit                                  |

**Environment variables:**

| Variable         | Description                                            |
| :--------------- | :----------------------------------------------------- |
| `VIRTUX_HOME`    | Override the default data directory                    |
| `VIRTUX_DEBUG=1` | Show full Python tracebacks for command handler errors |

**How persistence works:**

- Session state is serialized as JSON (`json.dump` / `json.load` only, never `eval` or `pickle`).
- State includes the full virtual filesystem tree, environment variables, and aliases.
- A malformed state file produces a warning and Virtux starts from defaults instead of crashing.
- On Windows, ANSI colors are enabled when possible, and tab completion works via `pyreadline3`.

---

## Python API

Virtux embeds cleanly into any Python application. The entry point is `VirtuxShell`.

**Basic usage:**

```python
from virtux import VirtuxShell

shell = VirtuxShell(persist=False)

output = shell.execute("echo Hello from Virtux")
print(output)
print(shell.executor.last_exit_code)
```

**Structured output with `run()`.** Returns a `ShellResult` dataclass with separate stdout, stderr, and exit code:

```python
result = shell.run("ls /nonexistent")
print(result.stdout)
print(result.stderr)
print(result.exit_code)
```

**Output and exit code together:**

```python
output, code = shell.execute_with_code("cat /etc/passwd")
print(f"Exit code: {code}")
print(output)
```

**Pre-seeding the virtual filesystem:**

```python
shell = VirtuxShell(persist=False)
shell.fs.write_file("/etc/myapp.conf", "debug=true\nlog_level=INFO\n")
shell.fs.write_file("/home/user/script.sh", "#!/bin/bash\necho 'hello'\n")

output = shell.execute("cat /etc/myapp.conf")
print(output)
```

**Resetting state:**

```python
shell = VirtuxShell(persist=False)
shell.execute("touch /tmp/temp_file.txt")
shell.reset()

output = shell.execute("ls /tmp")
assert "temp_file.txt" not in output
```

**API reference:**

| Class / Method                             | Description                                                                                       |
| :----------------------------------------- | :------------------------------------------------------------------------------------------------ |
| `VirtuxShell(persist=True, data_dir=None)` | Create a new shell instance. Set `persist=False` for ephemeral sessions.                          |
| `.execute(command) → str`                  | Run a command, return combined stdout+stderr. Exit code available via `.executor.last_exit_code`. |
| `.execute_with_code(command) → (str, int)` | Like `execute()`, but returns a `(output, exit_code)` tuple.                                      |
| `.run(command) → ShellResult`              | Run a command, return a `ShellResult(stdout, stderr, exit_code)` dataclass.                       |
| `.run()` _(no args)_                       | Start the interactive REPL loop. Returns `None`.                                                  |
| `.reset()`                                 | Reset all state (filesystem, environment, history) to defaults.                                   |
| `.fs`                                      | Direct access to the `VirtualFileSystem` instance.                                                |
| `.env`                                     | Direct access to the `Environment` instance (variables, aliases, cwd).                            |
| `.executor`                                | Direct access to the `Executor` instance.                                                         |

---

## Testing with Virtux

Use `VirtuxShell(persist=False)` in test fixtures for a clean, isolated environment per test.

**pytest fixture:**

```python
import pytest
from virtux import VirtuxShell

@pytest.fixture
def shell(tmp_path):
    """Create a non-persistent shell for testing."""
    return VirtuxShell(persist=False, data_dir=str(tmp_path / ".virtux"))
```

**Example tests:**

```python
class TestMyCommands:
    def test_file_creation(self, shell):
        shell.execute("echo 'hello world' > /tmp/test.txt")
        output = shell.execute("cat /tmp/test.txt")
        assert "hello world" in output

    def test_pipeline(self, shell):
        shell.execute("echo 'line1\nline2\nline3' > /tmp/data.txt")
        output = shell.execute("cat /tmp/data.txt | grep line2")
        assert "line2" in output

    def test_exit_codes(self, shell):
        result = shell.run("ls /nonexistent")
        assert result.exit_code != 0
        assert "No such file or directory" in result.stderr

    def test_persistence(self, tmp_path):
        data_dir = str(tmp_path / ".virtux")

        shell1 = VirtuxShell(persist=True, data_dir=data_dir)
        shell1.execute("echo persisted > /tmp/data.txt")
        shell1._save_state()

        shell2 = VirtuxShell(persist=True, data_dir=data_dir)
        output = shell2.execute("cat /tmp/data.txt")
        assert "persisted" in output
```

**Running the test suite:**

```bash
pip install -e ".[dev]"
python -m pytest
python -m pytest -v
python -m pytest --cov=virtux
```

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                    CLI / REPL                    │
│                   (cli.py)                       │
├──────────────────────────────────────────────────┤
│                  VirtuxShell                     │
│          (shell.py - public API)                 │
├──────────┬──────────┬──────────┬─────────────────┤
│  Parser  │ Executor │ Registry │    Plugins      │
│          │          │          │                  │
│ Tokenise │ Pipes,   │ Command  │ Entry-point     │
│ & build  │ redirect,│ lookup & │ discovery       │
│ pipeline │ dispatch │ metadata │                  │
│ AST      │          │          │                  │
├──────────┴──────────┴──────────┴─────────────────┤
│              Core Infrastructure                 │
│                                                  │
│  VirtualFileSystem   Environment   UserManager   │
│  (in-memory tree)    (vars, cwd,   (uid/gid,     │
│                       aliases)      sudo/su)      │
├──────────────────────────────────────────────────┤
│                   Commands                       │
│                                                  │
│  filesystem_cmds  text_cmds  system_cmds         │
│  shell_cmds  network_cmds  archive_cmds          │
│  process_cmds                                    │
└──────────────────────────────────────────────────┘
```

**Key modules:**

| Module                    | Responsibility                                                            |
| :------------------------ | :------------------------------------------------------------------------ |
| `virtux.cli`              | CLI entry point, argument parsing, mode dispatch                          |
| `virtux.shell`            | `VirtuxShell`, the public-facing API with `execute()`, `run()`, `reset()` |
| `virtux.core.shell`       | `Shell`, base REPL with readline, state persistence, tab completion       |
| `virtux.core.parser`      | Tokenizer and AST builder. Handles pipes, redirects, `&&`/`\|\|`/`;`      |
| `virtux.core.executor`    | Pipeline runner. Wires commands together with I/O redirection             |
| `virtux.core.filesystem`  | `VirtualFileSystem`, in-memory hierarchical filesystem with permissions   |
| `virtux.core.environment` | `Environment`, env vars, aliases, cwd, prompt, variable expansion         |
| `virtux.users`            | `UserManager`, user/group management, sudo/su simulation                  |
| `virtux.registry`         | `CommandRegistry`, command registration, lookup, help text, categories    |
| `virtux.plugins`          | Entry-point-based plugin discovery and loading                            |
| `virtux.commands.*`       | 7 command modules with 75 command implementations                         |

---

## Plugin System

Plugins register commands through the `virtux.plugins` entry-point group, letting third-party packages extend Virtux with new commands.

**1. Write a registration function** that accepts a `CommandRegistry`:

```python
def register(registry):
    @registry.register("greet", help_text="Say hello", category="custom")
    def cmd_greet(ctx):
        name = ctx.args[0] if ctx.args else "world"
        ctx.writeln(f"Hello, {name}!")
        return 0

    @registry.register("farewell", help_text="Say goodbye", category="custom")
    def cmd_farewell(ctx):
        ctx.writeln("Goodbye!")
        return 0
```

**2. Declare the entry point** in `pyproject.toml`:

```toml
[project.entry-points."virtux.plugins"]
my_plugin = "my_plugin.register:register"
```

**3. Install and go.** Virtux auto-discovers the plugin on startup:

```bash
pip install my-virtux-plugin
virtux
```

```console
user@virtux:~$ greet Rishi
Hello, Rishi!
```

**`CommandContext` reference.** Every command handler receives one:

| Attribute / Method       | Type                | Description                                    |
| :----------------------- | :------------------ | :--------------------------------------------- |
| `ctx.args`               | `list[str]`         | Command arguments (excluding the command name) |
| `ctx.fs`                 | `VirtualFileSystem` | The virtual filesystem                         |
| `ctx.env`                | `Environment`       | Environment variables, aliases, cwd            |
| `ctx.users`              | `UserManager`       | User/group management                          |
| `ctx.cwd`                | `str`               | Current working directory                      |
| `ctx.write(text)`        | n/a                 | Write to stdout (no newline)                   |
| `ctx.writeln(text)`      | n/a                 | Write to stdout with newline                   |
| `ctx.error(text)`        | n/a                 | Write to stderr with newline                   |
| `ctx.read_stdin()`       | `str`               | Read all stdin (supports piped input)          |
| `ctx.read_stdin_lines()` | `list[str]`         | Read stdin as lines                            |
| `ctx.resolve_path(path)` | `str`               | Resolve a relative/`~` path to absolute        |
| `ctx.home`               | `str`               | User's home directory                          |
| `ctx.user`               | `str`               | Current username                               |

> **Trust boundary:** installing a third-party plugin grants it the same power as a built-in command. It can register handlers on the live registry and access the virtual filesystem and environment. Only install plugins you trust, the same way you'd vet shell functions sourced from an untrusted script.

---

## Limitations

Virtux is a **teaching sandbox**, not a production shell.

| Limitation                 | Details                                                                                   |
| :------------------------- | :---------------------------------------------------------------------------------------- |
| **No real binaries**       | Commands are Python implementations. No actual `gcc`, `apt`, or system binaries           |
| **No real I/O**            | Network commands (`ping`, `curl`, `ssh`) produce simulated output only                    |
| **Simulated users**        | `sudo`/`su` switch UIDs inside the virtual environment. No real privilege escalation      |
| **Simplified permissions** | rwx checks apply to filesystem operations; ACLs, capabilities, and SELinux aren't modeled |
| **No async jobs**          | Background (`&`) is parsed but jobs aren't scheduled as async tasks                       |
| **Partial shell features** | Subshells, `$()` command substitution, and advanced job control may be partial or absent  |

For real Linux behavior (actual `gcc`, sockets, containers), use WSL or a VM. For zero-setup CLI practice anywhere Python runs, Virtux is the lightweight option.

---

## Contributing

Contributions are welcome! Open an issue or PR at [github.com/RishiBuilds/Virtux](https://github.com/RishiBuilds/Virtux).

```bash
git clone https://github.com/RishiBuilds/Virtux.git
cd Virtux
pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
python -m mypy src
```

**Guidelines:**

- Add tests under `tests/` for new commands or behavior changes.
- Follow existing patterns. See `virtux/commands/` for command implementation examples.
- Use type hints. The project uses mypy for static type checking.
- Keep it cross-platform. Avoid host OS dependencies; everything should work on Windows, macOS, and Linux.

**Project structure:**

```
Virtux/
├── src/virtux/
│   ├── __init__.py
│   ├── cli.py
│   ├── shell.py
│   ├── plugins.py
│   ├── registry.py
│   ├── users.py
│   ├── permissions.py
│   ├── utils.py
│   ├── core/
│   │   ├── shell.py
│   │   ├── executor.py
│   │   ├── parser.py
│   │   ├── filesystem.py
│   │   ├── environment.py
│   │   └── registry.py
│   └── commands/
│       ├── filesystem_cmds.py
│       ├── text_cmds.py
│       ├── system_cmds.py
│       ├── shell_cmds.py
│       ├── network_cmds.py
│       ├── archive_cmds.py
│       └── process_cmds.py
├── tests/
│   ├── test_commands.py
│   ├── test_executor.py
│   ├── test_filesystem.py
│   ├── test_parser.py
│   ├── test_shell.py
│   └── test_audit_regressions.py
├── pyproject.toml
├── LICENSE
└── README.md
```

---

## License

MIT License. See [LICENSE](LICENSE).

Copyright © 2026 [RishiBuilds](https://github.com/RishiBuilds)
