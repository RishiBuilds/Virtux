"""
Virtual Filesystem for Virtux.
Simulates a Linux-like filesystem entirely in memory (with optional persistence).
"""

from __future__ import annotations

import json
import time
import fnmatch
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field


class VirtualFileSystemError(OSError):
    """Base exception for filesystem errors."""
    pass

VirtualFSError = VirtualFileSystemError

class FileNotFoundError_(FileNotFoundError, VirtualFileSystemError):
    pass

class FileExistsError_(FileExistsError, VirtualFileSystemError):
    pass

class NotADirectoryError_(NotADirectoryError, VirtualFileSystemError):
    pass

class IsADirectoryError_(IsADirectoryError, VirtualFileSystemError):
    pass

class PermissionError_(PermissionError, VirtualFileSystemError):
    pass

class DirectoryNotEmptyError_(VirtualFileSystemError):
    pass

class SymlinkLoopError_(VirtualFileSystemError):
    """Too many levels of symbolic links."""
    pass


@dataclass
class FSNode:
    """Represents a node (file or directory) in the virtual filesystem."""
    name: str
    is_dir: bool
    content: bytes = field(default_factory=bytes)
    children: Dict[str, "FSNode"] = field(default_factory=dict)
    permissions: int = 0o644
    owner: str = "user"
    group: str = "user"
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    symlink_target: Optional[str] = None

    def __post_init__(self):
        if self.is_dir:
            self.permissions = 0o755

    @property
    def size(self) -> int:
        if self.is_dir:
            return 4096
        return len(self.content)

    @property
    def is_symlink(self) -> bool:
        return self.symlink_target is not None

    def mode_string(self) -> str:
        if self.is_symlink:
            prefix = "l"
        elif self.is_dir:
            prefix = "d"
        else:
            prefix = "-"

        def bits(val, read="r", write="w", exec_="x"):
            return (
                (read if val & 4 else "-") +
                (write if val & 2 else "-") +
                (exec_ if val & 1 else "-")
            )

        p = self.permissions
        owner_bits = bits((p >> 6) & 7)
        group_bits = bits((p >> 3) & 7)
        other_bits = bits(p & 7)
        return f"{prefix}{owner_bits}{group_bits}{other_bits}"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "is_dir": self.is_dir,
            "content": self.content.decode("utf-8", errors="replace") if not self.is_dir else "",
            "children": {k: v.to_dict() for k, v in self.children.items()},
            "permissions": self.permissions,
            "owner": self.owner,
            "group": self.group,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "symlink_target": self.symlink_target,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FSNode":
        node = cls(
            name=d["name"],
            is_dir=d["is_dir"],
            content=d.get("content", "").encode("utf-8") if not d["is_dir"] else b"",
            permissions=d.get("permissions", 0o644),
            owner=d.get("owner", "user"),
            group=d.get("group", "user"),
            created_at=d.get("created_at", time.time()),
            modified_at=d.get("modified_at", time.time()),
            symlink_target=d.get("symlink_target"),
        )
        for k, v in d.get("children", {}).items():
            node.children[k] = FSNode.from_dict(v)
        return node


class VirtualFileSystem:
    """
    A simulated Linux filesystem.
    Stores everything in memory; can be serialized to/from JSON for persistence.
    """

    _MAX_SYMLINK_DEPTH = 40

    def __init__(self, owner: str = "root", group: str = "root", umask: int = 0o022, **kwargs: Any):
        self._umask = umask & 0o777
        self._default_owner = owner
        self._default_group = group
        self.root = FSNode(name="/", is_dir=True, permissions=0o755, owner="root", group="root")
        self._build_default_tree()

    @property
    def umask(self) -> int:
        return getattr(self, "_umask", 0o022)

    @umask.setter
    def umask(self, value: int) -> None:
        self._umask = value & 0o777

    def _apply_umask(self, permissions: int) -> int:
        return permissions & ~self._umask & 0o777

    def _build_default_tree(self):
        """Create the standard Linux directory hierarchy."""
        dirs = [
            ("bin", "root", 0o755),
            ("etc", "root", 0o755),
            ("home", "root", 0o755),
            ("home/user", "user", 0o700),
            ("tmp", "root", 0o1777),
            ("usr", "root", 0o755),
            ("usr/bin", "root", 0o755),
            ("usr/local", "root", 0o755),
            ("usr/local/bin", "root", 0o755),
            ("var", "root", 0o755),
            ("var/log", "root", 0o755),
            ("dev", "root", 0o755),
            ("proc", "root", 0o555),
            ("sys", "root", 0o555),
        ]
        for path, owner, perms in dirs:
            self.makedirs("/" + path, owner=owner, permissions=perms)

        self.write_file("/etc/hostname", b"virtux\n")
        self.write_file("/etc/os-release", (
            b'NAME="Virtux"\n'
            b'VERSION="0.1.0"\n'
            b'ID=virtux\n'
            b'PRETTY_NAME="Virtux Linux Simulator 0.1.0"\n'
        ))
        self.write_file("/etc/shells", b"/bin/sh\n/bin/bash\n")
        self.write_file("/etc/passwd", b"root:x:0:0:root:/root:/bin/bash\nuser:x:1000:1000:user:/home/user:/bin/bash\n")
        self.write_file("/home/user/.bashrc", b"# .bashrc\nexport PS1='user@virtux:~$ '\n")
        self.write_file("/home/user/README.txt", (
            b"Welcome to Virtux!\n"
            b"This is a simulated Linux environment.\n"
            b"Type 'help' to see available commands.\n"
        ))
        self.write_file("/var/log/syslog", b"")
        self.write_file("/tmp/.keep", b"")

    def normalize(self, path: str, cwd: str = "/") -> str:
        """Resolve a path (possibly relative) to an absolute POSIX path."""
        if not path.startswith("/"):
            path = cwd.rstrip("/") + "/" + path
        parts: List[str] = []
        for part in path.split("/"):
            if part in ("", "."):
                continue
            elif part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)
        return "/" + "/".join(parts)

    def _traverse(self, path: str, follow_symlinks: bool = True, _depth: int = 0) -> Optional[FSNode]:
        """Return the FSNode at the given absolute path, or None."""
        if _depth > self._MAX_SYMLINK_DEPTH:
            raise SymlinkLoopError_(f"Too many levels of symbolic links: {path}")
        if path == "/":
            return self.root
        parts = [p for p in path.split("/") if p]
        node = self.root
        for i, part in enumerate(parts):
            if not node.is_dir or part not in node.children:
                return None
            child = node.children[part]
            is_last = (i == len(parts) - 1)
            if child.is_symlink and (not is_last or follow_symlinks):
                target = self.normalize(child.symlink_target or "")
                child_node = self._traverse(target, follow_symlinks, _depth + 1)
                if child_node is None:
                    return None
                child = child_node
            node = child
        return node

    def _parent_and_name(self, path: str) -> Tuple[Optional[FSNode], str]:
        parts = [p for p in path.split("/") if p]
        if not parts:
            return None, ""
        name = parts[-1]
        parent_path = "/" + "/".join(parts[:-1])
        return self._traverse(parent_path), name

    def exists(self, path: str) -> bool:
        return self._traverse(path) is not None

    def is_dir(self, path: str) -> bool:
        node = self._traverse(path)
        return node is not None and node.is_dir

    def is_file(self, path: str) -> bool:
        node = self._traverse(path)
        return node is not None and not node.is_dir

    def is_symlink(self, path: str) -> bool:
        node = self._traverse(path, follow_symlinks=False)
        return node is not None and node.is_symlink

    def listdir(self, path: str) -> List[str]:
        node = self._traverse(path)
        if node is None or not node.is_dir:
            raise FileNotFoundError_(f"No such directory: {path}")
        return sorted(node.children.keys())

    def get_node(self, path: str) -> Optional[FSNode]:
        return self._traverse(path)

    def makedirs(self, path: str, owner: str = "user", permissions: int = 0o755, **kwargs: Any) -> None:
        group = kwargs.get("group", owner)
        parts = [p for p in path.split("/") if p]
        node = self.root
        for part in parts:
            if part not in node.children:
                new_node = FSNode(name=part, is_dir=True, owner=owner,
                                  group=group, permissions=permissions)
                node.children[part] = new_node
            node = node.children[part]

    def mkdir(self, path: str, owner: str = "user", permissions: int = 0o755, parents: bool = False, **kwargs: Any) -> None:
        if parents:
            self.makedirs(path, owner=owner, permissions=permissions, **kwargs)
            return
        group = kwargs.get("group", owner)
        parent, name = self._parent_and_name(path)
        if parent is None:
            raise FileNotFoundError_(f"Parent directory does not exist: {path}")
        if not parent.is_dir:
            raise NotADirectoryError_(f"Not a directory: {path}")
        if name in parent.children:
            raise FileExistsError_(f"Already exists: {path}")
        parent.children[name] = FSNode(name=name, is_dir=True,
                                       owner=owner, group=group, permissions=permissions)

    def read_file(self, path: str) -> bytes:
        node = self._traverse(path)
        if node is None:
            raise FileNotFoundError_(f"No such file: {path}")
        if node.is_dir:
            raise IsADirectoryError_(f"Is a directory: {path}")
        return node.content

    def write_file(self, path: str, content: bytes | str, owner: Optional[str] = None,
                   permissions: Optional[int] = None, append: bool = False, **kwargs: Any) -> None:
        if isinstance(content, str):
            content = content.encode("utf-8")
        parent, name = self._parent_and_name(path)
        if parent is None:
            raise FileNotFoundError_(f"Parent directory not found: {path}")
        if not parent.is_dir:
            raise NotADirectoryError_("Not a directory")
        if name in parent.children and parent.children[name].is_dir:
            raise IsADirectoryError_(f"Is a directory: {path}")

        existing = parent.children.get(name)
        if existing and append:
            content = existing.content + content

        if existing:
            resolved_owner = owner if owner is not None else existing.owner
            resolved_group = kwargs.get("group", existing.group)
            resolved_perms = permissions if permissions is not None else existing.permissions
        else:
            resolved_owner = owner if owner is not None else "user"
            resolved_group = kwargs.get("group", resolved_owner)
            resolved_perms = permissions if permissions is not None else self._apply_umask(0o666)

        node = FSNode(name=name, is_dir=False, content=content,
                      owner=resolved_owner, group=resolved_group, permissions=resolved_perms)
        if existing:
            node.created_at = existing.created_at
        parent.children[name] = node

    def remove(self, path: str, recursive: bool = False) -> None:
        parent, name = self._parent_and_name(path)
        if parent is None or name not in parent.children:
            raise FileNotFoundError_(f"No such file: {path}")
        node = parent.children[name]
        if node.is_dir and not recursive:
            raise IsADirectoryError_(f"Is a directory: {path}")
        del parent.children[name]

    def rmdir(self, path: str, recursive: bool = False) -> None:
        parent, name = self._parent_and_name(path)
        if parent is None or name not in parent.children:
            raise FileNotFoundError_(f"No such directory: {path}")
        node = parent.children[name]
        if not node.is_dir:
            raise NotADirectoryError_(f"Not a directory: {path}")
        if node.children and not recursive:
            raise DirectoryNotEmptyError_(f"Directory not empty: {path}")
        del parent.children[name]

    def move(self, src: str, dst: str) -> None:
        self.rename(src, dst)

    def rename(self, src: str, dst: str) -> None:
        src_parent, src_name = self._parent_and_name(src)
        if src_parent is None or src_name not in src_parent.children:
            raise FileNotFoundError_(f"No such file or directory: {src}")

        dst_node = self._traverse(dst)
        if dst_node is not None and dst_node.is_dir:
            dst = dst.rstrip("/") + "/" + src_name

        dst_parent, dst_name = self._parent_and_name(dst)
        if dst_parent is None:
            raise FileNotFoundError_(f"No such directory for destination: {dst}")

        if dst_name in dst_parent.children:
            target = dst_parent.children[dst_name]
            if target.is_dir and target.children:
                raise DirectoryNotEmptyError_(f"Cannot overwrite non-empty directory: {dst}")

        node = src_parent.children.pop(src_name)
        node.name = dst_name
        dst_parent.children[dst_name] = node

    def copy(self, src: str, dst: str, recursive: bool = False) -> None:
        src_node = self._traverse(src)
        if src_node is None:
            raise FileNotFoundError_(f"No such file or directory: {src}")

        if src_node.is_dir:
            if not recursive:
                raise IsADirectoryError_(f"Is a directory: {src}")
            dst_node = self._traverse(dst)
            if dst_node and dst_node.is_dir:
                _, src_name = self._parent_and_name(src)
                dst = dst.rstrip("/") + "/" + src_name
            self._copy_recursive(src_node, dst)
        else:
            dst_node = self._traverse(dst)
            if dst_node and dst_node.is_dir:
                _, src_name = self._parent_and_name(src)
                dst = dst.rstrip("/") + "/" + src_name
            self.write_file(dst, src_node.content, owner=src_node.owner,
                            permissions=src_node.permissions)

    def _copy_recursive(self, src_node: FSNode, dst_path: str) -> None:
        self.makedirs(dst_path, owner=src_node.owner, permissions=src_node.permissions)
        for child_name, child_node in src_node.children.items():
            child_dst = dst_path.rstrip("/") + "/" + child_name
            if child_node.is_dir:
                self._copy_recursive(child_node, child_dst)
            elif child_node.is_symlink:
                self.symlink(child_node.symlink_target or "", child_dst)
            else:
                self.write_file(child_dst, child_node.content, owner=child_node.owner,
                                permissions=child_node.permissions)

    def symlink(self, target: str, link_path: str) -> None:
        parent, name = self._parent_and_name(link_path)
        if parent is None:
            raise FileNotFoundError_(f"Parent not found: {link_path}")
        if name in parent.children:
            raise FileExistsError_(f"Already exists: {link_path}")
        node = FSNode(name=name, is_dir=False, symlink_target=target)
        parent.children[name] = node

    def chmod(self, path: str, permissions: int) -> None:
        node = self._traverse(path)
        if node is None:
            raise FileNotFoundError_(f"No such file: {path}")
        node.permissions = permissions
        node.modified_at = time.time()

    def chown(self, path: str, owner: Optional[str] = None, group: Optional[str] = None) -> None:
        node = self._traverse(path)
        if node is None:
            raise FileNotFoundError_(f"No such file or directory: {path}")
        if owner is not None:
            node.owner = owner
        if group is not None:
            node.group = group

    def touch(self, path: str) -> None:
        if not self.exists(path):
            self.write_file(path, b"")
        else:
            node = self._traverse(path)
            if node:
                node.modified_at = time.time()

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        return self.read_file(path).decode(encoding)

    def append_file(self, path: str, content: bytes | str) -> None:
        if isinstance(content, str):
            content = content.encode("utf-8")
        self.write_file(path, content, append=True)

    def reset(self) -> None:
        self.root = FSNode(name="/", is_dir=True, permissions=0o755, owner="root", group="root")
        self._build_default_tree()

    def setup_user_home(self, username: str, group: str) -> None:
        """Create the home directory for a user with standard dotfiles."""
        home = f"/home/{username}"
        self.makedirs(home, owner=username)

        bashrc_content = (
            "# ~/.bashrc: executed by bash for non-login shells.\n\n"
            "# If not running interactively, don't do anything\n"
            "case $- in\n"
            "    *i*) ;;\n"
            "      *) return;;\n"
            "esac\n\n"
            "# Alias definitions\n"
            "alias ll='ls -alF'\n"
            "alias la='ls -a'\n"
            "alias l='ls -CF'\n"
        )
        self.write_file(f"{home}/.bashrc", bashrc_content.encode("utf-8"), owner=username)
        self.write_file(f"{home}/.profile", (
            "# ~/.profile: executed by the command interpreter for login shells.\n\n"
            'if [ -f "$HOME/.bashrc" ]; then\n'
            '    . "$HOME/.bashrc"\n'
            "fi\n\n"
            'PATH="$HOME/bin:$HOME/.local/bin:$PATH"\n'
        ).encode("utf-8"), owner=username)
        self.write_file(f"{home}/.bash_history", b"", owner=username)
        self.write_file(f"{home}/.bash_logout", (
            "# ~/.bash_logout: executed by bash when login shell exits.\n"
        ).encode("utf-8"), owner=username)

        for subdir in ["Documents", "Downloads", "Desktop", ".local", ".config"]:
            self.makedirs(f"{home}/{subdir}", owner=username)

    def find(
        self,
        start_path: str,
        name_pattern: Optional[str] = None,
        node_type: Optional[str] = None,
        max_depth: int = -1,
    ) -> List[str]:
        """Search for files matching criteria."""
        results: List[str] = []
        self._find_recursive(start_path, name_pattern, node_type, max_depth, 0, results)
        return results

    def _find_recursive(
        self,
        current_path: str,
        name_pattern: Optional[str],
        node_type: Optional[str],
        max_depth: int,
        current_depth: int,
        results: List[str],
    ) -> None:
        node = self._traverse(current_path, follow_symlinks=False)
        if node is None:
            return

        matches = True
        if name_pattern and not fnmatch.fnmatch(node.name, name_pattern):
            matches = False
        if node_type:
            if node_type == "dir" and not node.is_dir:
                matches = False
            elif node_type == "file" and (node.is_dir or node.is_symlink):
                matches = False
            elif node_type == "symlink" and not node.is_symlink:
                matches = False

        if matches and current_path != "/":
            results.append(current_path)

        if node.is_dir and (max_depth == -1 or current_depth < max_depth):
            for child_name in sorted(node.children.keys()):
                child_path = current_path.rstrip("/") + "/" + child_name
                self._find_recursive(
                    child_path, name_pattern, node_type,
                    max_depth, current_depth + 1, results
                )

    def save(self, filepath: str) -> None:
        with open(filepath, "w") as f:
            json.dump(self.root.to_dict(), f, indent=2)

    def load(self, filepath: str) -> None:
        with open(filepath) as f:
            data = json.load(f)
        self.root = FSNode.from_dict(data)