"""
Permission model for the Virtux virtual filesystem.

Implements Linux-style rwx permission checking with owner/group/other
semantics, octal and symbolic mode parsing, and umask support.
"""

from __future__ import annotations

import re


S_IRUSR = 0o400
S_IWUSR = 0o200
S_IXUSR = 0o100
S_IRGRP = 0o040
S_IWGRP = 0o020
S_IXGRP = 0o010
S_IROTH = 0o004
S_IWOTH = 0o002
S_IXOTH = 0o001
S_ISUID = 0o4000
S_ISGID = 0o2000
S_ISVTX = 0o1000

PERM_FILE_DEFAULT = 0o644
PERM_DIR_DEFAULT = 0o755
PERM_EXEC_DEFAULT = 0o755
PERM_PRIVATE = 0o700
PERM_ALL = 0o777

PERM_CHARS = "rwx"


def format_permissions(mode: int, node_type: str = "file") -> str:
    """Format permissions as a Linux-style string like 'drwxr-xr-x'.

    Args:
        mode: Permission value, may include setuid/setgid/sticky bits.
        node_type: One of 'file', 'dir', 'symlink'.

    Returns:
        10-character permission string.
    """
    prefix = {
        "dir": "d",
        "symlink": "l",
        "file": "-",
    }.get(node_type, "-")

    perms = ""
    for i in range(8, -1, -1):
        if mode & (1 << i):
            perms += PERM_CHARS[(8 - i) % 3]
        else:
            perms += "-"

    perms_list = list(perms)
    if mode & S_ISUID:
        perms_list[2] = "s" if perms_list[2] == "x" else "S"
    if mode & S_ISGID:
        perms_list[5] = "s" if perms_list[5] == "x" else "S"
    if mode & S_ISVTX:
        perms_list[8] = "t" if perms_list[8] == "x" else "T"

    return prefix + "".join(perms_list)


def parse_symbolic_mode(mode_str: str, current_mode: int) -> int:
    """Parse symbolic chmod notation like 'u+x', 'go-w', 'a=rx', '+t', 'u+s'.

    Args:
        mode_str: Symbolic mode string.
        current_mode: Current permission value to modify.

    Returns:
        New permission value.

    Raises:
        ValueError: If the mode string is invalid.
    """
    pattern = re.compile(r'^([ugoa]*)([\+\-=])([rwxXst]*)$')
    new_mode = current_mode

    for part in mode_str.split(","):
        match = pattern.match(part.strip())
        if not match:
            raise ValueError(f"Invalid symbolic mode: '{part}'")

        who, op, perms = match.groups()

        if not who:
            who = "a"

        perm_bits = 0
        if "r" in perms:
            perm_bits |= 0o4
        if "w" in perms:
            perm_bits |= 0o2
        if "x" in perms:
            perm_bits |= 0o1
        if "X" in perms:
            is_dir_or_exec = bool(current_mode & 0o111)
            if is_dir_or_exec:
                perm_bits |= 0o1

        mask = 0
        if "u" in who or "a" in who:
            mask |= perm_bits << 6
        if "g" in who or "a" in who:
            mask |= perm_bits << 3
        if "o" in who or "a" in who:
            mask |= perm_bits

        special_mask = 0
        if "s" in perms:
            if "u" in who or "a" in who:
                special_mask |= S_ISUID
            if "g" in who or "a" in who:
                special_mask |= S_ISGID
        if "t" in perms:
            special_mask |= S_ISVTX

        if op == "+":
            new_mode |= mask | special_mask
        elif op == "-":
            new_mode &= ~(mask | special_mask)
        elif op == "=":
            clear_mask = 0
            if "u" in who or "a" in who:
                clear_mask |= 0o700 | S_ISUID
            if "g" in who or "a" in who:
                clear_mask |= 0o070 | S_ISGID
            if "o" in who or "a" in who:
                clear_mask |= 0o007
            if who == "a" and "t" not in perms:
                clear_mask |= S_ISVTX
            new_mode = (new_mode & ~clear_mask) | mask | special_mask

    return new_mode


def parse_octal_mode(mode_str: str) -> int:
    """Parse an octal permission string like '755' or '1777'.

    Args:
        mode_str: Octal string (3 or 4 digits).

    Returns:
        Permission value as integer.

    Raises:
        ValueError: If the string is not valid octal.
    """
    if not re.match(r'^[0-7]{3,4}$', mode_str):
        raise ValueError(f"Invalid octal mode: '{mode_str}'")
    return int(mode_str, 8)


def parse_mode(mode_str: str, current_mode: int = 0o644) -> int:
    """Parse a chmod mode string - either octal or symbolic.

    Args:
        mode_str: Mode string like '755', '1777', or 'u+x'.
        current_mode: Current permissions (used for symbolic mode).

    Returns:
        New permission value.
    """
    if re.match(r'^[0-7]{3,4}$', mode_str):
        return parse_octal_mode(mode_str)
    return parse_symbolic_mode(mode_str, current_mode)


def check_permission(
    mode: int,
    owner: str,
    group: str,
    current_user: str,
    current_groups: list[str],
    action: str,
) -> bool:
    """Check if the current user has the specified permission.

    Args:
        mode: File/directory permission bits.
        owner: Owner of the file.
        group: Group of the file.
        current_user: Username of the current user.
        current_groups: Groups the current user belongs to.
        action: One of 'read', 'write', 'execute'.

    Returns:
        True if the user has the specified permission.
    """
    if current_user == "root":
        return True

    perm_bit = {"read": 0o4, "write": 0o2, "execute": 0o1}.get(action, 0)

    if current_user == owner:
        return bool(mode & (perm_bit << 6))
    elif group and group in current_groups:
        return bool(mode & (perm_bit << 3))
    else:
        return bool(mode & perm_bit)


def apply_umask(mode: int, umask_val: int) -> int:
    """Apply umask to a permission value.

    Args:
        mode: Default permission value.
        umask_val: Current umask value.

    Returns:
        Permission value with umask applied.
    """
    return mode & ~umask_val