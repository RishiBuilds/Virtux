"""
User and group management for the Virtux virtual environment.

Simulates Linux users and groups including root, regular users,
user switching (su/sudo), and /etc/passwd + /etc/group integration.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from typing import Optional
import getpass


def _sanitize_username(name: str) -> str:
    """Coerce an arbitrary OS username into a valid Linux-style username."""
    sanitized = re.sub(r'[^a-zA-Z0-9_.-]', "_", name).lower()
    sanitized = sanitized.lstrip("-")
    return sanitized or "user"


@dataclass
class User:
    """Represents a Linux user."""
    username: str
    uid: int
    gid: int
    home: str
    shell: str
    gecos: str = ""
    password: str = ""

    def to_passwd_line(self) -> str:
        """Format as /etc/passwd entry."""
        gecos = self.gecos.replace(":", " ")
        return f"{self.username}:x:{self.uid}:{self.gid}:{gecos}:{self.home}:{self.shell}"


@dataclass
class Group:
    """Represents a Linux group."""
    name: str
    gid: int
    members: list[str] = field(default_factory=list)

    def to_group_line(self) -> str:
        """Format as /etc/group entry."""
        members_str = ",".join(self.members)
        return f"{self.name}:x:{self.gid}:{members_str}"


_RESERVED_USERS = {
    "root": (0, 0, "/root", "root"),
    "nobody": (65534, 65534, "/nonexistent", "nobody"),
    "daemon": (1, 1, "/usr/sbin", "daemon"),
    "www-data": (33, 33, "/var/www", "www-data"),
}

_RESERVED_GROUPS = {
    "root": (0, ["root"]),
    "sudo": (27, []),
    "adm": (4, []),
    "users": (100, []),
    "nogroup": (65534, []),
    "daemon": (1, ["daemon"]),
    "www-data": (33, ["www-data"]),
}


class UserManager:
    """Manages virtual Linux users and groups.

    Provides user switching, group membership, and integration
    with the virtual /etc/passwd and /etc/group files.
    """

    def __init__(self, default_username: Optional[str] = None) -> None:
        if default_username is None:
            try:
                default_username = getpass.getuser()
            except Exception:
                default_username = "user"

        default_username = _sanitize_username(default_username)

        if default_username in _RESERVED_USERS:
            print(
                f"virtux: warning: detected username '{default_username}' collides "
                f"with a reserved system account; using 'user' instead",
                file=sys.stderr,
            )
            default_username = "user"

        self._users: dict[str, User] = {}
        self._groups: dict[str, Group] = {}
        self._current_user: str = default_username
        self._original_user: str = default_username
        self._is_sudo: bool = False

        self._create_default_users(default_username)
        self._create_default_groups(default_username)

    def _create_default_users(self, username: str) -> None:
        """Set up default Linux users."""
        for name, (uid, gid, home, gecos) in _RESERVED_USERS.items():
            self._users[name] = User(
                username=name, uid=uid, gid=gid, home=home,
                shell="/usr/sbin/nologin" if name != "root" else "/bin/bash",
                gecos=gecos,
            )

        self._users[username] = User(
            username=username,
            uid=1000,
            gid=1000,
            home=f"/home/{username}",
            shell="/bin/bash",
            gecos=username.capitalize(),
        )

    def _create_default_groups(self, username: str) -> None:
        """Set up default Linux groups."""
        for name, (gid, members) in _RESERVED_GROUPS.items():
            self._groups[name] = Group(name=name, gid=gid, members=list(members))

        self._groups[username] = Group(name=username, gid=1000, members=[username])

        for gname in ("sudo", "adm", "users"):
            if username not in self._groups[gname].members:
                self._groups[gname].members.append(username)

    @property
    def current_user(self) -> str:
        return self._current_user

    @property
    def current_uid(self) -> int:
        return self._users[self._current_user].uid

    @property
    def current_gid(self) -> int:
        return self._users[self._current_user].gid

    @property
    def current_home(self) -> str:
        return self._users[self._current_user].home

    @property
    def current_shell(self) -> str:
        return self._users[self._current_user].shell

    @property
    def is_root(self) -> bool:
        return self._current_user == "root"

    @property
    def is_sudo(self) -> bool:
        return self._is_sudo

    def get_user(self, username: str) -> Optional[User]:
        return self._users.get(username)

    def get_group(self, name: str) -> Optional[Group]:
        return self._groups.get(name)

    def get_user_groups(self, username: Optional[str] = None) -> list[str]:
        """Get all groups a user belongs to."""
        if username is None:
            username = self._current_user
        groups = [gname for gname, group in self._groups.items() if username in group.members]

        user = self._users.get(username)
        if user:
            for gname, group in self._groups.items():
                if group.gid == user.gid and gname not in groups:
                    groups.append(gname)
        return groups

    def get_primary_group_name(self, username: Optional[str] = None) -> str:
        if username is None:
            username = self._current_user
        user = self._users.get(username)
        if not user:
            return "nogroup"
        for gname, group in self._groups.items():
            if group.gid == user.gid:
                return gname
        return "nogroup"

    def switch_user(self, username: str) -> bool:
        """Switch to a different user (su).

        Returns True if successful, False if user doesn't exist.
        Refuses to switch while an active sudo session would be silently
        dropped without an explicit sudo_drop(); call sudo_drop() first.
        """
        if username not in self._users:
            return False
        if self._is_sudo:
            return False
        self._original_user = self._current_user
        self._current_user = username
        return True

    def sudo_elevate(self) -> None:
        """Elevate to root via sudo."""
        if self._is_sudo:
            return
        self._original_user = self._current_user
        self._current_user = "root"
        self._is_sudo = True

    def sudo_drop(self) -> None:
        """Drop sudo privileges."""
        if self._is_sudo:
            self._current_user = self._original_user
            self._is_sudo = False

    def user_exists(self, username: str) -> bool:
        return username in self._users

    def group_exists(self, name: str) -> bool:
        return name in self._groups

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def list_groups(self) -> list[Group]:
        return list(self._groups.values())

    def generate_passwd_content(self) -> str:
        lines = [u.to_passwd_line() for u in self._users.values()]
        return "\n".join(lines) + "\n"

    def generate_group_content(self) -> str:
        lines = [g.to_group_line() for g in self._groups.values()]
        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict:
        return {
            "current_user": self._current_user,
            "original_user": self._original_user,
            "is_sudo": self._is_sudo,
        }

    def from_dict(self, data: dict) -> None:
        if "current_user" in data and data["current_user"] in self._users:
            self._current_user = data["current_user"]
        if "original_user" in data and data["original_user"] in self._users:
            self._original_user = data["original_user"]
        self._is_sudo = data.get("is_sudo", False)