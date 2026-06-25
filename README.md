<p align="center">
  <br>
  <strong style="font-size: 2em;">🐧 Virtux</strong>
  <br>
  <em>A cross-platform Linux shell simulator - practice real shell syntax anywhere Python runs.</em>
  <br><br>
  <a href="https://pypi.org/project/virtux/"><img src="https://img.shields.io/pypi/v/virtux.svg?style=flat-square&color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/virtux/"><img src="https://img.shields.io/pypi/pyversions/virtux.svg?style=flat-square" alt="Python versions"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT"></a>
</p>

---

Virtux is a **sandboxed Linux shell simulator** written in pure Python. It is built for learners, educators, and developers who want to practice real shell syntax - pipes, redirection, exit codes, permissions, and scripting - without installing WSL, Docker, or a Linux VM.

Everything runs in a sandboxed in-memory (or optionally persisted) virtual filesystem, so mistyped `rm` commands **cannot touch your real files**.

```bash
pip install virtux
```

---

## Table of Contents

- [Quick Start](#-quick-start)
- [Example Session](#-example-session)
- [Features](#-features)
- [Supported Commands](#-supported-commands)
- [Usage Modes](#-usage-modes)
- [Configuration & Persistence](#%EF%B8%8F-configuration--persistence)
- [Python API](#-python-api)
- [Testing with Virtux](#-testing-with-virtux)
- [Architecture](#-architecture)
- [Plugin System](#-plugin-system)
- [Limitations](#-limitations)
- [Contributing](#-contributing)
- [License](#-license)

---

## Quick Start

**Requirements:** Python 3.9+

### Launch the interactive REPL

```bash
virtux
```

### Run a single command and exit

The command's exit code propagates to your host shell, making Virtux usable in CI pipelines and scripts:

```bash
virtux -c "ls /etc"
```

### Run a script file

Execute a sequence of commands from a file (supports both VFS paths and host filesystem paths):

```bash
virtux script.sh
```

### Run without persistence

Start an ephemeral session - nothing is loaded or saved on exit:

```bash
virtux --no-persist -c "echo hello"
```

### Check the version

```bash
virtux --version
# or
python -m virtux --version
```

### Reset to defaults

Wipe all persisted filesystem state and start fresh:

```bash
virtux --reset
```

> **Dependencies:** `prompt_toolkit`, `rich`, and `platformdirs`. The REPL itself uses stdlib `input()` plus optional GNU readline when available.

---

## Example Session

The interactive prompt follows `user@hostname:path$` format (with `~` for your home directory). After a failing command, a `✗` marker appears before `$`:

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
| **Sandboxed Virtual Filesystem** | Hierarchical tree (`/home`, `/etc`, `/tmp`, `/var`, …) stored in memory or persisted to JSON on disk. Your real files are never touched.                   |
| **Real Shell Syntax**            | Pipes (`\|`), redirection (`>`, `>>`, `<`, `2>`, `2>>`, `&>`), command lists (`;`, `&&`, `\|\|`), background (`&`), variable expansion (`$VAR`, `${VAR}`). |
| **75 Built-in Commands**         | File tools, text processing, permissions, simulated network & process commands, and more.                                                                  |
| **Permission Model**             | `chmod`, `chown`, `umask`, `sudo`, and `su` with rwx checks enforced at the filesystem layer. Root bypasses permission checks.                             |
| **Cross-Platform**               | Identical behaviour on Windows, macOS, and Linux. No host shell or system dependencies required.                                                           |
| **Embeddable Python API**        | Drive sessions from Python or `pytest`. Capture stdout, stderr, and exit codes. Reset state between tests.                                                 |
| **Optional Persistence**         | Save filesystem + environment to `~/.virtux/virtux_state.json`. Override with `VIRTUX_HOME`.                                                               |
| **Plugin System**                | Register extra commands via Python entry points.                                                                                                           |
| **Tab Completion**               | GNU readline completion when `readline` (or `pyreadline3` on Windows) is available.                                                                        |
| **Colourised Prompt**            | ANSI-coloured user/host/path with red prompt for root and `✗` indicator after failed commands.                                                             |

---

## Supported Commands

Virtux ships with **75 unique commands** plus aliases (e.g., `ll` → `ls -la`, `la` → `ls -a`).

<details>
<summary><strong>Filesystem (15 commands)</strong></summary>

`ls` · `cd` · `pwd` · `mkdir` · `rmdir` · `rm` · `cp` · `mv` · `touch` · `ln` · `find` · `stat` · `du` · `df` · `tree`

</details>

<details>
<summary><strong>Text Processing (13 commands)</strong></summary>

`cat` · `head` · `tail` · `grep` · `wc` · `sort` · `uniq` · `cut` · `sed` · `awk` · `echo` · `tee` · `diff`

</details>

<details>
<summary><strong>System & Shell (23 commands)</strong></summary>

`whoami` · `uname` · `hostname` · `date` · `cal` · `uptime` · `env` · `export` · `unset` · `alias` · `unalias` · `history` · `clear` · `exit` · `man` · `help` · `which` · `type` · `id` · `printenv` · `true` · `false` · `sleep`

</details>

<details>
<summary><strong>Permissions & Shell Builtins (9 commands)</strong></summary>

`chmod` · `chown` · `chgrp` · `umask` · `sudo` · `su` · `source` · `bash` · `sh`

</details>

<details>
<summary><strong>Network - simulated (6 commands)</strong></summary>

`ping` · `ifconfig` · `ip` · `curl` · `wget` · `ssh`

</details>

<details>
<summary><strong>Archives (5 commands)</strong></summary>

`tar` · `gzip` · `gunzip` · `zip` · `unzip`

</details>

<details>
<summary><strong>Processes - simulated (4 commands)</strong></summary>

`ps` · `top` · `kill` · `jobs`

</details>

> Run `help` or `man <command>` inside the shell for per-command usage details.

---

## 🎮 Usage Modes

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

### Data Directory

| Setting        | Default      | Description                                         |
| :------------- | :----------- | :-------------------------------------------------- |
| Data directory | `~/.virtux/` | Contains `virtux_state.json` and readline `history` |
| `VIRTUX_HOME`  | -            | Override the data directory path                    |

### CLI Flags

| Flag              | Description                                             |
| :---------------- | :------------------------------------------------------ |
| `--no-persist`    | Skip loading and saving state; no readline history file |
| `--reset`         | Reset virtual filesystem to factory defaults            |
| `-c "cmd"`        | Execute a single command and exit                       |
| `-V`, `--version` | Print version and exit                                  |

### Environment Variables

| Variable         | Description                                            |
| :--------------- | :----------------------------------------------------- |
| `VIRTUX_HOME`    | Override the default data directory                    |
| `VIRTUX_DEBUG=1` | Show full Python tracebacks for command handler errors |

### How Persistence Works

- Session state is serialised as JSON (`json.dump` / `json.load` only - no `eval` or `pickle`)
- State includes: the full virtual filesystem tree + environment variables + aliases
- Malformed state files produce a warning and Virtux starts from defaults
- On Windows, ANSI colours are enabled when possible; readline tab completion works with `pyreadline3`

---

## Python API

Virtux can be embedded in any Python application. The primary entry point is `VirtuxShell`:

### Basic Usage

```python
from virtux import VirtuxShell

shell = VirtuxShell(persist=False)

output = shell.execute("echo Hello from Virtux")
print(output)

print(shell.executor.last_exit_code)
```

### Structured Output with `run()`

The `run()` method returns a `ShellResult` dataclass with separate stdout, stderr, and exit code:

```python
from virtux import VirtuxShell

shell = VirtuxShell(persist=False)

result = shell.run("ls /nonexistent")
print(result.stdout)
print(result.stderr)
print(result.exit_code)
```

### Getting Output + Exit Code Together

```python
output, code = shell.execute_with_code("cat /etc/passwd")
print(f"Exit code: {code}")
print(output)
```

### Pre-seeding the Virtual Filesystem

```python
shell = VirtuxShell(persist=False)

shell.fs.write_file("/etc/myapp.conf", "debug=true\nlog_level=INFO\n")
shell.fs.write_file("/home/user/script.sh", "#!/bin/bash\necho 'hello'\n")

output = shell.execute("cat /etc/myapp.conf")
print(output)

```

### Resetting State

```python
shell = VirtuxShell(persist=False)
shell.execute("touch /tmp/temp_file.txt")

shell.reset()

output = shell.execute("ls /tmp")
assert "temp_file.txt" not in output
```

### API Reference

| Class / Method                             | Description                                                                                       |
| :----------------------------------------- | :------------------------------------------------------------------------------------------------ |
| `VirtuxShell(persist=True, data_dir=None)` | Create a new shell instance. Set `persist=False` for ephemeral sessions.                          |
| `.execute(command) → str`                  | Run a command, return combined stdout+stderr. Exit code available via `.executor.last_exit_code`. |
| `.execute_with_code(command) → (str, int)` | Like `execute()`, but returns a `(output, exit_code)` tuple.                                      |
| `.run(command) → ShellResult`              | Run a command, return a `ShellResult(stdout, stderr, exit_code)` dataclass.                       |
| `.run()` (no args)                         | Start the interactive REPL loop. Returns `None`.                                                  |
| `.reset()`                                 | Reset all state (filesystem, environment, history) to defaults.                                   |
| `.fs`                                      | Direct access to the `VirtualFileSystem` instance.                                                |
| `.env`                                     | Direct access to the `Environment` instance (variables, aliases, cwd).                            |
| `.executor`                                | Direct access to the `Executor` instance.                                                         |

---

## Testing with Virtux

Virtux is designed to be test-friendly. Use `VirtuxShell(persist=False)` in your test fixtures to get a clean, isolated environment for every test:

### pytest Fixture

```python
import pytest
from virtux import VirtuxShell

@pytest.fixture
def shell(tmp_path):
    """Create a non-persistent shell for testing."""
    return VirtuxShell(persist=False, data_dir=str(tmp_path / ".virtux"))
```

### Example Tests

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

### Running the Test Suite

```bash
pip install -e ".[dev]"
python -m pytest
python -m pytest -v
python -m pytest --cov=virtux
```

---

## Architecture

Virtux is organised into a layered architecture:

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

### Key Modules

| Module                    | Responsibility                                                             |
| :------------------------ | :------------------------------------------------------------------------- |
| `virtux.cli`              | CLI entry point, argument parsing, mode dispatch                           |
| `virtux.shell`            | `VirtuxShell` - the public-facing API with `execute()`, `run()`, `reset()` |
| `virtux.core.shell`       | `Shell` - base REPL with readline, state persistence, tab completion       |
| `virtux.core.parser`      | Tokeniser and AST builder - handles pipes, redirects, `&&`/`\|\|`/`;`      |
| `virtux.core.executor`    | Pipeline runner - wires commands together with I/O redirection             |
| `virtux.core.filesystem`  | `VirtualFileSystem` - in-memory hierarchical filesystem with permissions   |
| `virtux.core.environment` | `Environment` - env vars, aliases, cwd, prompt, variable expansion         |
| `virtux.users`            | `UserManager` - user/group management, sudo/su simulation                  |
| `virtux.registry`         | `CommandRegistry` - command registration, lookup, help text, categories    |
| `virtux.plugins`          | Entry-point-based plugin discovery and loading                             |
| `virtux.commands.*`       | 7 command modules with 75 command implementations                          |

---

## 🔌 Plugin System

Plugins register commands through the `virtux.plugins` entry-point group. This lets third-party packages extend Virtux with new commands.

### Creating a Plugin

**Step 1:** Write a registration function that accepts a `CommandRegistry`:

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

**Step 2:** Declare the entry point in your `pyproject.toml`:

```toml
[project.entry-points."virtux.plugins"]
my_plugin = "my_plugin.register:register"
```

**Step 3:** Install your plugin package and Virtux will auto-discover it on startup:

```bash
pip install my-virtux-plugin
virtux
# user@virtux:~$ greet Rishi
# Hello, Rishi!
```

### Plugin API - CommandContext

Every command handler receives a `CommandContext` with these attributes and helpers:

| Attribute / Method       | Type                | Description                                    |
| :----------------------- | :------------------ | :--------------------------------------------- |
| `ctx.args`               | `list[str]`         | Command arguments (excluding the command name) |
| `ctx.fs`                 | `VirtualFileSystem` | The virtual filesystem                         |
| `ctx.env`                | `Environment`       | Environment variables, aliases, cwd            |
| `ctx.users`              | `UserManager`       | User/group management                          |
| `ctx.cwd`                | `str`               | Current working directory                      |
| `ctx.write(text)`        | -                   | Write to stdout (no newline)                   |
| `ctx.writeln(text)`      | -                   | Write to stdout with newline                   |
| `ctx.error(text)`        | -                   | Write to stderr with newline                   |
| `ctx.read_stdin()`       | `str`               | Read all stdin (supports piped input)          |
| `ctx.read_stdin_lines()` | `list[str]`         | Read stdin as lines                            |
| `ctx.resolve_path(path)` | `str`               | Resolve a relative/`~` path to absolute        |
| `ctx.home`               | `str`               | User's home directory                          |
| `ctx.user`               | `str`               | Current username                               |

### Security Notice

> **Trust boundary:** Installing a third-party Virtux plugin grants it the same power as a built-in command - it can register handlers on the live command registry and access the virtual filesystem and environment. Only install plugins you trust, just as you would with shell functions sourced from untrusted scripts.

---

## Limitations

Virtux is a **teaching sandbox**, not a production shell. Keep these constraints in mind:

| Limitation                 | Details                                                                                     |
| :------------------------- | :------------------------------------------------------------------------------------------ |
| **No real binaries**       | Commands are Python implementations; no actual `gcc`, `apt`, or system binaries             |
| **No real I/O**            | Network commands (`ping`, `curl`, `ssh`) produce simulated output only                      |
| **Simulated users**        | `sudo`/`su` switch UIDs inside the virtual environment - no real privilege escalation       |
| **Simplified permissions** | rwx checks apply to filesystem operations; ACLs, capabilities, and SELinux are not modelled |
| **No async jobs**          | Background (`&`) is parsed but jobs are not scheduled as async tasks                        |
| **Partial shell features** | Subshells, `$()` command substitution, and advanced job control may be partial or absent    |

> For real Linux behaviour (actual `gcc`, sockets, containers), use WSL or a VM. For zero-setup CLI practice anywhere Python runs, Virtux is the lightweight option.

---

## Contributing

Contributions are welcome! Issues and pull requests can be submitted at [github.com/RishiBuilds/Virtux](https://github.com/RishiBuilds/Virtux).

### Getting Started

```bash
# Clone the repository
git clone https://github.com/RishiBuilds/Virtux.git
cd Virtux
pip install -e ".[dev]"
python -m pytest
python -m ruff check src tests
python -m mypy src
```

### Guidelines

- **Add tests** under `tests/` for new commands or behaviour changes
- **Follow existing patterns** - see `virtux/commands/` for command implementation examples
- **Use type hints** - the project uses mypy for static type checking
- **Keep it cross-platform** - avoid host OS dependencies; everything should work on Windows, macOS, and Linux

### Project Structure

```
Virtux/
├── src/virtux/
│   ├── __init__.py          # Package root, public exports
│   ├── cli.py               # CLI entry point
│   ├── shell.py             # VirtuxShell public API
│   ├── plugins.py           # Plugin discovery
│   ├── registry.py          # Command registry
│   ├── users.py             # User/group management
│   ├── permissions.py       # Permission checks
│   ├── utils.py             # Path normalisation, helpers
│   ├── core/
│   │   ├── shell.py         # Base Shell + REPL
│   │   ├── executor.py      # Pipeline execution engine
│   │   ├── parser.py        # Tokeniser and AST
│   │   ├── filesystem.py    # Virtual filesystem
│   │   ├── environment.py   # Env vars, aliases, prompt
│   │   └── registry.py      # Core command registry
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

MIT License - see [LICENSE](LICENSE).

Copyright © 2026 [RishiBuilds](https://github.com/RishiBuilds)
