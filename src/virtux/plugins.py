"""
Plugin discovery and loading for the Virtux shell.

Uses Python entry points to discover and load third-party
command plugins that extend the shell with new commands.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virtux.registry import CommandRegistry


PLUGIN_GROUP = "virtux.plugins"


def discover_plugins(registry: "CommandRegistry") -> list[str]:
    """Discover and load all installed Virtux plugins.

    Plugins register via entry points in their pyproject.toml:
        [project.entry-points."virtux.plugins"]
        my_plugin = "my_plugin:register"

    The entry point must be a function that accepts a CommandRegistry.

    Args:
        registry: The command registry to register commands into.

    Returns:
        List of successfully loaded plugin names.
    """
    loaded: list[str] = []

    try:
        from importlib.metadata import entry_points
    except ImportError as e:
        print(f"virtux: plugin discovery unavailable: {e}", file=sys.stderr)
        return loaded

    try:
        if sys.version_info >= (3, 10):
            eps = entry_points(group=PLUGIN_GROUP)
        else:
            eps = entry_points().get(PLUGIN_GROUP, [])
    except Exception as e:
        print(f"virtux: failed to enumerate plugins: {e}", file=sys.stderr)
        return loaded

    for ep in eps:
        try:
            register_func = ep.load()
        except Exception as e:
            print(f"virtux: plugin '{ep.name}' failed to import: {e}", file=sys.stderr)
            continue

        if not callable(register_func):
            print(
                f"virtux: plugin '{ep.name}' entry point is not callable "
                f"(got {type(register_func).__name__})",
                file=sys.stderr,
            )
            continue

        try:
            register_func(registry)
        except Exception as e:
            print(
                f"virtux: plugin '{ep.name}' raised during registration "
                f"(some commands may be partially registered): {e}",
                file=sys.stderr,
            )
            continue

        loaded.append(ep.name)

    return loaded