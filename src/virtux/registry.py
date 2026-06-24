"""
Command registry and execution context for the Virtux shell.

Provides the CommandContext that all commands receive, and the
CommandRegistry for registering/discovering command handlers.

NOTE: CommandContext is actively used - it's constructed by the
function-based @register decorator in virtux.registry to adapt the
modern ExecutionContext into the shape legacy command functions expect.
CommandRegistry below appears to be a separate, currently-unused
registration path; confirm before relying on it, since command dispatch
in practice goes through virtux.registry's module-level _REGISTRY.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from virtux.core.filesystem import VirtualFileSystem
    from virtux.core.environment import Environment
    from virtux.users import UserManager


CommandHandler = Callable[["CommandContext"], int]


@dataclass
class CommandInfo:
    """Metadata about a registered command."""
    name: str
    handler: CommandHandler
    help_text: str = ""
    usage: str = ""
    category: str = "general"
    aliases: list[str] = field(default_factory=list)


@dataclass
class CommandContext:
    """Execution context passed to every command handler."""
    fs: "VirtualFileSystem"
    env: "Environment"
    users: "UserManager"
    stdin: Any
    stdout: Any
    stderr: Any
    args: list[str]
    cwd: str
    last_exit_code: int = 0
    registry: Optional["CommandRegistry"] = None

    def write(self, text: str) -> None:
        self.stdout.write(text)

    def writeln(self, text: str = "") -> None:
        self.stdout.write(text + "\n")

    def error(self, text: str) -> None:
        self.stderr.write(text + "\n")

    def read_stdin(self) -> str:
        """Read all available stdin. Consumes the stream."""
        return str(self.stdin.read())

    def read_stdin_lines(self) -> list[str]:
        """Read stdin as lines. Consumes the stream."""
        content = self.stdin.read()
        if content:
            return list(content.splitlines(keepends=True))
        return []

    @property
    def home(self) -> str:
        return str(self.env.home)

    @property
    def user(self) -> str:
        return self.users.current_user

    def resolve_path(self, path: str) -> str:
        from virtux.utils import normalize_path
        if path.startswith("~"):
            path = self.home + path[1:]
        return normalize_path(path, self.cwd)


class CommandRegistry:
    """Registry for command handlers."""

    def __init__(self) -> None:
        self._commands: dict[str, CommandInfo] = {}
        self._alias_map: dict[str, str] = {}

    def register(
        self,
        name: str,
        help_text: str = "",
        usage: str = "",
        category: str = "general",
        aliases: Optional[list[str]] = None,
    ) -> Callable[[CommandHandler], CommandHandler]:
        def decorator(func: CommandHandler) -> CommandHandler:
            self._register(name, func, help_text, usage, category, aliases)
            return func
        return decorator

    def register_handler(
        self,
        name: str,
        handler: CommandHandler,
        help_text: str = "",
        usage: str = "",
        category: str = "general",
        aliases: Optional[list[str]] = None,
    ) -> None:
        self._register(name, handler, help_text, usage, category, aliases)

    def _register(self, name, handler, help_text, usage, category, aliases) -> None:
        if name in self._commands:
            print(f"virtux: warning: command '{name}' is being redefined", file=sys.stderr)
        info = CommandInfo(
            name=name, handler=handler, help_text=help_text,
            usage=usage, category=category, aliases=aliases or [],
        )
        self._commands[name] = info
        for alias in info.aliases:
            if alias in self._commands:
                print(f"virtux: warning: alias '{alias}' shadows command '{alias}'", file=sys.stderr)
            self._alias_map[alias] = name

    def get(self, name: str) -> Optional[CommandInfo]:
        if name in self._commands:
            return self._commands[name]
        canonical = self._alias_map.get(name)
        return self._commands.get(canonical) if canonical else None

    def has(self, name: str) -> bool:
        return name in self._commands or name in self._alias_map

    def list_commands(self) -> list[str]:
        return sorted(self._commands.keys())

    def list_by_category(self) -> dict[str, list[CommandInfo]]:
        categories: dict[str, list[CommandInfo]] = {}
        for info in self._commands.values():
            categories.setdefault(info.category, []).append(info)
        for cat in categories:
            categories[cat].sort(key=lambda c: c.name)
        return categories

    def get_help(self, name: str) -> Optional[str]:
        info = self.get(name)
        return info.help_text if info else None

    def get_usage(self, name: str) -> Optional[str]:
        info = self.get(name)
        return info.usage if info else None

    def execute(self, name: str, ctx: CommandContext) -> int:
        info = self.get(name)
        if info is None:
            ctx.error(f"virtux: command not found: {name}")
            return 127
        try:
            return info.handler(ctx)
        except Exception as e:
            if getattr(ctx.env, "get_var", lambda *_: "")("VIRTUX_DEBUG"):
                import traceback
                ctx.error(f"{name}: {e}\n{traceback.format_exc()}")
            else:
                ctx.error(f"{name}: {e}")
            return 1