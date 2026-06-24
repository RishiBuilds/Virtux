"""
Shared utility functions for the Virtux package.

Provides glob matching, human-readable size formatting, color helpers,
path normalization, and other cross-cutting utilities.
"""

from __future__ import annotations

import fnmatch
import re
import time
from typing import Optional


def human_readable_size(size_bytes: int) -> str:
    """Convert bytes to human-readable format (e.g. '4.0K', '1.2M')."""
    if size_bytes < 1024:
        return str(size_bytes)
    size = float(size_bytes)
    for unit in ['K', 'M', 'G', 'T', 'P']:
        size /= 1024.0
        if size < 1024.0:
            return f"{size:.1f}{unit}"
    return f"{size:.1f}E"


def format_timestamp(ts: float, fmt: str = "%b %d %H:%M") -> str:
    """Format a Unix timestamp for display."""
    return time.strftime(fmt, time.localtime(ts))


def normalize_path(path: str, cwd: str = "/") -> str:
    """Normalize a path, resolving '.', '..', and making it absolute."""
    if not path:
        return cwd

    if not path.startswith("/"):
        if cwd == "/":
            path = "/" + path
        else:
            path = cwd + "/" + path

    parts = path.split("/")
    resolved: list[str] = []

    for part in parts:
        if part == "" or part == ".":
            continue
        elif part == "..":
            if resolved:
                resolved.pop()
        else:
            resolved.append(part)

    return "/" + "/".join(resolved)


def split_path(path: str) -> tuple[str, str]:
    """Split a path into (parent_dir, basename)."""
    if path == "/":
        return "/", ""
    path = path.rstrip("/")
    last_slash = path.rfind("/")
    if last_slash == 0:
        return "/", path[1:]
    elif last_slash == -1:
        return "/", path
    else:
        return path[:last_slash], path[last_slash + 1:]


def match_glob(pattern: str, name: str) -> bool:
    """Match a name against a glob pattern."""
    return fnmatch.fnmatch(name, pattern)


def parse_size_spec(spec: str) -> Optional[int]:
    """Parse a size specification like '100k', '1M', '500'.

    Unit suffixes (case-insensitive):
        (none) - raw bytes
        b      - 512-byte blocks (matches `find -size` convention, NOT bytes)
        k      - kibibytes (1024 bytes)
        m      - mebibytes
        g      - gibibytes

    Returns:
        Size in bytes, or None if invalid.
    """
    match = re.match(r'^(\d+)([bBkKmMgG]?)$', spec)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2).lower()

    multipliers = {
        '': 1,
        'b': 512,
        'k': 1024,
        'm': 1024 * 1024,
        'g': 1024 * 1024 * 1024,
    }

    return value * multipliers.get(unit, 1)


def columnize(items: list[str], terminal_width: int = 80) -> str:
    """Arrange items in columns for display (like ls without -l)."""
    if not items:
        return ""

    max_width = max(len(item) for item in items) + 2
    num_cols = max(1, terminal_width // max_width)
    num_rows = (len(items) + num_cols - 1) // num_cols

    lines = []
    for row in range(num_rows):
        line_parts = []
        for col in range(num_cols):
            idx = row + col * num_rows
            if idx < len(items):
                line_parts.append(items[idx].ljust(max_width))
        lines.append("".join(line_parts).rstrip())

    return "\n".join(lines)


def escape_string(s: str) -> str:
    """Process escape sequences in a string (for echo -e).

    Handles: \\n, \\t, \\\\, \\a, \\b, \\r, \\0nnn (octal, up to 3 digits
    after the leading 0, matching bash's `echo -e` convention).
    """
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            c = s[i + 1]
            if c == 'n':
                result.append('\n')
                i += 2
            elif c == 't':
                result.append('\t')
                i += 2
            elif c == '\\':
                result.append('\\')
                i += 2
            elif c == 'a':
                result.append('\a')
                i += 2
            elif c == 'b':
                result.append('\b')
                i += 2
            elif c == 'r':
                result.append('\r')
                i += 2
            elif c == '0':
                octal = ""
                j = i + 2
                while j < len(s) and len(octal) < 3 and s[j] in '01234567':
                    octal += s[j]
                    j += 1
                if octal:
                    result.append(chr(int(octal, 8)))
                else:
                    result.append('\0')
                i = j
            else:
                result.append('\\')
                result.append(c)
                i += 2
        else:
            result.append(s[i])
            i += 1

    return "".join(result)


def get_data_dir() -> str:
    """Get the base data directory for Virtux storage, respecting VIRTUX_HOME."""
    import os
    from pathlib import Path
    virtux_home = os.environ.get("VIRTUX_HOME")
    if virtux_home:
        return virtux_home
    return os.path.join(Path.home(), ".virtux")