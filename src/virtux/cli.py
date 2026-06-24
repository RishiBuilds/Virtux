"""
CLI entry point for the Virtux terminal emulator.

Handles command-line argument parsing and dispatches to:
- Interactive shell mode
- Single command execution (-c)
- Script execution (positional file argument)
- Reset and version display
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> None:
    """Main entry point for the `virtux` command."""
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            kernel32 = ctypes.windll.kernel32
            h = kernel32.GetStdHandle(-11)
            mode = wintypes.DWORD()
            if kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                kernel32.SetConsoleMode(h, mode.value | 0x0004)
        except Exception:
            pass
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="virtux",
        description="Virtux - Cross-platform Linux terminal emulator for Python.",
        epilog="Launch without arguments to enter interactive shell mode.",
    )
    parser.add_argument(
        "-c", "--command",
        help="Execute a single command and exit.",
        metavar="COMMAND",
    )
    parser.add_argument(
        "script",
        nargs="?",
        help="Path to a shell script file to execute.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the virtual filesystem to its default state.",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Run without saving or loading state.",
    )
    parser.add_argument(
        "-V", "--version",
        action="store_true",
        help="Show version and exit.",
    )

    args = parser.parse_args()

    if args.version:
        from virtux import __version__
        print(f"virtux {__version__}")
        return

    from virtux.core.shell import Shell

    persist_path = None if args.no_persist else _default_persist_path()

    if args.reset:
        shell = Shell(persist_path=persist_path)
        shell.fs.reset()
        print("Virtux: filesystem has been reset to defaults.")
        if persist_path:
            shell._save_state()
        return

    if args.command:
        shell = Shell(persist_path=persist_path)
        code = shell.executor.run_line(args.command)
        if persist_path:
            shell._save_state()
        sys.exit(code)

    if args.script:
        shell = Shell(persist_path=persist_path)
        script_path = args.script

        resolved = (
            script_path if script_path.startswith("/")
            else shell.env.cwd.rstrip("/") + "/" + script_path
        )

        if shell.fs.exists(resolved):
            content = shell.fs.read_text(resolved)
        elif os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                content = f.read()
        else:
            print(f"virtux: {script_path}: No such file or directory", file=sys.stderr)
            sys.exit(1)

        last_code = 0
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            last_code = shell.executor.run_line(line)

        if persist_path:
            shell._save_state()
        sys.exit(last_code)

    shell = Shell(persist_path=persist_path)
    shell.run()


def _default_persist_path() -> str:
    from virtux.utils import get_data_dir
    return os.path.join(get_data_dir(), "virtux_state.json")



if __name__ == "__main__":
    main()