"""
Environment module - tracks shell state: CWD, env vars, aliases, history.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Any


class Environment:
    """Holds all session state for a Virtux shell instance."""

    def __init__(self, home: Optional[str] = None, user: str = "user", hostname: str = "virtux", **kwargs: Any):
        username = kwargs.get("username", user)
        if home is None:
            home = f"/home/{username}" if username != "root" else "/root"

        self.home = home
        self.user = username
        self.hostname = hostname
        self.cwd = home
        self.previous_dir: Optional[str] = None

        self.variables: Dict[str, str] = {
            "HOME": home,
            "USER": username,
            "LOGNAME": username,
            "SHELL": "/bin/bash",
            "HOSTNAME": hostname,
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "TERM": "xterm-256color",
            "LANG": "en_US.UTF-8",
            "PWD": home,
            "OLDPWD": "",
            "PS1": self._default_ps1(),
        }

        self.aliases: Dict[str, str] = {
            "ll": "ls -la",
            "la": "ls -a",
            "l": "ls -CF",
            "..": "cd ..",
            "...": "cd ../..",
        }

        self.history: List[str] = []
        self.last_exit_code: int = 0

    def _default_ps1(self) -> str:
        return f"{self.user}@{self.hostname}:~$ "

    def get_prompt(self) -> str:
        """Return a coloured, dynamic shell prompt."""
        custom_ps1 = self.variables.get("PS1", "")
        if custom_ps1 and custom_ps1 != self._default_ps1():
            return self.expand_vars(custom_ps1)

        cwd_display = self.cwd
        if cwd_display.startswith(self.home):
            cwd_display = "~" + cwd_display[len(self.home):]

        reset = "\033[0m"
        green = "\033[1;32m"
        blue = "\033[1;34m"
        red = "\033[1;31m"
        error_color = "\033[1;91m"

        user_color = red if self.user == "root" else green
        exit_indicator = "✗ " if self.last_exit_code != 0 else ""

        return (
            f"{user_color}{self.user}@{self.hostname}{reset}:"
            f"{blue}{cwd_display}{reset}"
            f"{error_color}{exit_indicator}{reset}$ "
        )

    def expand_vars(self, text: str) -> str:
        """Expand $VAR and ${VAR} references."""

        def replacer(m: re.Match[str]) -> str:
            key = m.group(1) or m.group(2)
            if key == "?":
                return str(self.last_exit_code)
            return self.variables.get(key, "")

        return re.sub(r'\$\{(\w+)\}|\$(\w+)', replacer, text)

    def set_var(self, key: str, value: str) -> None:
        self.variables[key] = value
        if key == "PWD":
            self.cwd = value

    def get_var(self, key: str, default: str = "") -> str:
        return self.variables.get(key, default)

    def chdir(self, new_path: str) -> None:
        self.previous_dir = self.cwd
        self.cwd = new_path
        self.variables["OLDPWD"] = self.previous_dir or ""
        self.variables["PWD"] = new_path

    def add_history(self, command: str) -> None:
        if command.strip():
            self.history.append(command)

    set_var_legacy = set_var
    get_var_legacy = get_var

    def get(self, key: str, default: Any = None) -> Any:
        return self.variables.get(key, default)

    def get_all(self) -> Dict[str, str]:
        return self.variables

    def set(self, key: str, value: str) -> None:
        self.set_var(key, value)

    def unset(self, key: str) -> None:
        if key in self.variables:
            del self.variables[key]

    def has(self, key: str) -> bool:
        return key in self.variables

    def get_all_aliases(self) -> Dict[str, str]:
        return self.aliases

    def set_alias(self, name: str, value: str) -> None:
        self.aliases[name] = value

    def get_alias(self, name: str) -> Optional[str]:
        return self.aliases.get(name)

    def unset_alias(self, name: str) -> bool:
        if name in self.aliases:
            del self.aliases[name]
            return True
        return False

    def update_user(self, username: str) -> None:
        self.user = username
        self.variables["USER"] = username
        self.variables["LOGNAME"] = username
        home = f"/home/{username}" if username != "root" else "/root"
        self.home = home
        self.variables["HOME"] = home

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for persistence."""
        return {
            "vars": dict(self.variables),
            "aliases": dict(self.aliases),
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restore from persistence."""
        if "vars" in data:
            self.variables.update(data["vars"])
        if "aliases" in data:
            self.aliases.update(data["aliases"])