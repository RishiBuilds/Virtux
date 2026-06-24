"""
Command registry - auto-discovery and execution of built-in commands.
Each command is a subclass of BaseCommand registered via @register.
"""

import io
from typing import Dict, Type, Optional, List, Any, Callable


class ExecutionContext:
    """Everything a command needs: filesystem, env, and I/O streams."""
    registry: Any = None
    users: Any = None

    def __init__(self, fs, env, stdin=None, stdout=None, stderr=None):
        self.fs = fs
        self.env = env
        self.stdin: Any = stdin or io.StringIO()
        self.stdout: Any = stdout or io.StringIO()
        self.stderr: Any = stderr or io.StringIO()
        self.exit_code: int = 0

    def write(self, text: str) -> None:
        self.stdout.write(text)

    def writeln(self, text: str = "") -> None:
        self.stdout.write(text + "\n")

    def error(self, text: str) -> None:
        self.stderr.write(text + "\n")

    def read_input(self) -> str:
        return str(self.stdin.read())


class BaseCommand:
    """All built-in commands inherit from this."""

    name: str = ""
    aliases: List[str] = []
    description: str = ""
    usage: str = ""
    category: str = "general"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        """
        Run the command.
        args[0] is the command name; args[1:] are the arguments.
        Return exit code (0 = success).
        """
        raise NotImplementedError


_REGISTRY: Dict[str, Type[BaseCommand]] = {}


def register(arg: Any = None, **kwargs: Any) -> Any:
    """Polymorphic decorator supporting both class-based and function-based registration."""
    if arg is not None and isinstance(arg, type) and issubclass(arg, BaseCommand):
        cls = arg
        _REGISTRY[cls.name] = cls
        for alias in cls.aliases:
            _REGISTRY[alias] = cls
        return cls

    reg_name: str = str(arg or "")
    reg_aliases: List[str] = [str(a) for a in kwargs.get("aliases", [])]
    reg_description: str = str(kwargs.get("help_text", ""))
    reg_usage: str = str(kwargs.get("usage", ""))
    reg_category: str = str(kwargs.get("category", "general"))

    def decorator(func: Callable[..., int]) -> Callable[..., int]:

        def execute(self, args: List[str], ctx: ExecutionContext) -> int:
            from virtux.registry import CommandContext
            from virtux.users import UserManager
            users = getattr(ctx, "users", None)
            if users is None:
                users = UserManager()
            legacy_ctx = CommandContext(
                fs=ctx.fs,
                env=ctx.env,
                users=users,
                stdin=ctx.stdin,  # type: ignore
                stdout=ctx.stdout,  # type: ignore
                stderr=ctx.stderr,  # type: ignore
                args=args[1:],
                cwd=getattr(ctx, "cwd", None) or ctx.env.cwd,
                last_exit_code=getattr(ctx, "last_exit_code", 0),
                registry=getattr(ctx, "registry", None),
            )
            return func(legacy_ctx)

        FunctionCommand = type(
            f"FunctionCommand_{reg_name or func.__name__}",
            (BaseCommand,),
            {
                "name": reg_name,
                "aliases": list(reg_aliases),
                "description": reg_description,
                "usage": reg_usage,
                "category": reg_category,
                "execute": execute,
            },
        )

        if reg_name:
            _REGISTRY[reg_name] = FunctionCommand
            for alias in reg_aliases:
                _REGISTRY[alias] = FunctionCommand

        return func

    return decorator


def get_command(name: str) -> Optional[Type[BaseCommand]]:
    return _REGISTRY.get(name)


def all_commands() -> Dict[str, Type[BaseCommand]]:
    """Return the full registry (including aliases)."""
    return dict(_REGISTRY)


def unique_commands() -> List[Type[BaseCommand]]:
    """Return one entry per command class (deduplicated)."""
    seen = set()
    result = []
    for cls in _REGISTRY.values():
        if cls not in seen:
            seen.add(cls)
            result.append(cls)
    return sorted(result, key=lambda c: c.name)