from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtux.registry import CommandRegistry

from virtux.core.registry import register as register  # noqa: F401

from virtux.commands import (
    filesystem_cmds as filesystem_cmds,
    text_cmds as text_cmds,
    shell_cmds as shell_cmds,
    system_cmds as system_cmds,
    network_cmds as network_cmds,
    archive_cmds as archive_cmds,
    process_cmds as process_cmds,
)


def register_all_commands(registry: CommandRegistry) -> None:
    from virtux.core.registry import unique_commands, ExecutionContext

    for cmd_cls in unique_commands():
        def make_handler(cls):
            return lambda ctx: cls().execute([cls.name] + ctx.args, ExecutionContext(
                fs=ctx.fs,
                env=ctx.env,
                stdin=ctx.stdin,
                stdout=ctx.stdout,
                stderr=ctx.stderr,
            ))

        if "category" in cmd_cls.__dict__ or getattr(cmd_cls, "category", "general") != "general":
            category = cmd_cls.category
        else:
            module_name = cmd_cls.__module__
            category_map = {
                "filesystem_cmds": "filesystem",
                "text_cmds": "text",
                "system_cmds": "system",
                "shell_cmds": "shell",
                "network_cmds": "network",
                "archive_cmds": "archive",
                "process_cmds": "process",
            }
            category = next((v for k, v in category_map.items() if k in module_name), "general")

        registry.register_handler(
            name=cmd_cls.name,
            handler=make_handler(cmd_cls),
            help_text=cmd_cls.description,
            usage=cmd_cls.usage,
            category=category,
            aliases=cmd_cls.aliases,
        )