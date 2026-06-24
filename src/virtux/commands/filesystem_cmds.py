from __future__ import annotations

import time
import fnmatch
from typing import List

from virtux.core.registry import register, BaseCommand, ExecutionContext


@register
class Ls(BaseCommand):
    name = "ls"
    description = "List directory contents"
    usage = "ls [-la] [PATH...]"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        opts: set[str] = set()
        paths = []
        for a in args[1:]:
            if a.startswith("-"):
                opts.update(a[1:])
            else:
                paths.append(a)

        if not paths:
            paths = [ctx.env.cwd]

        show_all = "a" in opts
        long_fmt = "l" in opts
        classify = "F" in opts

        exit_code = 0

        for i, raw_path in enumerate(paths):
            path = ctx.fs.normalize(raw_path, ctx.env.cwd)
            if not ctx.fs.exists(path):
                ctx.error(f"ls: cannot access '{raw_path}': No such file or directory")
                exit_code = 2
                continue

            if len(paths) > 1:
                ctx.writeln(f"{raw_path}:")

            if ctx.fs.is_file(path):
                node = ctx.fs.get_node(path)
                entries = [(node.name, node)]
            else:
                names = ctx.fs.listdir(path)
                if show_all:
                    names = [".", ".."] + names
                entries = []
                for n in names:
                    if not show_all and n.startswith("."):
                        continue
                    child_path = path.rstrip("/") + "/" + n if path != "/" else "/" + n
                    if n == ".":
                        node = ctx.fs.get_node(path)
                    elif n == "..":
                        parent = "/".join(path.rstrip("/").split("/")[:-1]) or "/"
                        node = ctx.fs.get_node(parent)
                    else:
                        node = ctx.fs.get_node(child_path) or ctx.fs.get_node(path)
                    entries.append((n, node))

            if long_fmt:
                self._long_format(entries, ctx)
            else:
                self._short_format(entries, classify, ctx)

            if i < len(paths) - 1:
                ctx.writeln()

        return exit_code

    def _long_format(self, entries, ctx):
        for name, node in entries:
            if node is None:
                continue
            ts = time.strftime("%b %d %H:%M", time.localtime(node.modified_at))
            if node.is_dir:
                display_name = f"\033[1;34m{name}\033[0m"
            elif node.is_symlink:
                target = getattr(node, "symlink_target", "")
                display_name = f"\033[1;36m{name}\033[0m -> {target}" if target else f"\033[1;36m{name}\033[0m"
            elif node.permissions & 0o111:
                display_name = f"\033[1;32m{name}\033[0m"
            else:
                display_name = name
            suffix = "/" if node.is_dir and not display_name.endswith("/") else ""
            ctx.writeln(
                f"{node.mode_string()} 1 {node.owner:8} {node.group:8} "
                f"{node.size:8} {ts} {display_name}{suffix}"
            )

    def _short_format(self, entries, classify, ctx):
        from virtux.utils import columnize
        names = []
        for name, node in entries:
            if node is None:
                continue
            if node.is_dir:
                display_name = f"\033[1;34m{name}\033[0m"
                suffix = "/" if classify else ""
            elif node.is_symlink:
                display_name = f"\033[1;36m{name}\033[0m"
                suffix = "@" if classify else ""
            elif node.permissions & 0o111:
                display_name = f"\033[1;32m{name}\033[0m"
                suffix = "*" if classify else ""
            else:
                display_name = name
                suffix = ""
            names.append(display_name + suffix)
        ctx.writeln(columnize(names))


@register
class Cd(BaseCommand):
    name = "cd"
    description = "Change the current directory"
    usage = "cd [DIRECTORY]"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        if len(args) < 2 or args[1] == "~":
            target = ctx.env.home
        elif args[1] == "-":
            target = ctx.env.previous_dir or ctx.env.cwd
        else:
            target = ctx.fs.normalize(args[1], ctx.env.cwd)

        label = args[1] if len(args) > 1 else "~"
        if not ctx.fs.exists(target):
            ctx.error(f"cd: {label}: No such file or directory")
            return 1
        if not ctx.fs.is_dir(target):
            ctx.error(f"cd: {label}: Not a directory")
            return 1

        ctx.env.chdir(target)
        return 0


@register
class Pwd(BaseCommand):
    name = "pwd"
    description = "Print current working directory"
    usage = "pwd"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        ctx.writeln(ctx.env.cwd)
        return 0


@register
class Mkdir(BaseCommand):
    name = "mkdir"
    description = "Create directories"
    usage = "mkdir [-p] DIRECTORY..."

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        parents = False
        dirs = []
        for a in args[1:]:
            if a == "-p":
                parents = True
            elif a.startswith("-"):
                ctx.error(f"mkdir: invalid option -- '{a[1:]}'")
                return 1
            else:
                dirs.append(a)

        if not dirs:
            ctx.error("mkdir: missing operand")
            return 1

        rc = 0
        for d in dirs:
            path = ctx.fs.normalize(d, ctx.env.cwd)
            try:
                if parents:
                    ctx.fs.makedirs(path, owner=ctx.env.user)
                else:
                    ctx.fs.mkdir(path, owner=ctx.env.user)
            except FileExistsError:
                if not parents:
                    ctx.error(f"mkdir: cannot create directory '{d}': File exists")
                    rc = 1
            except Exception as e:
                ctx.error(f"mkdir: {d}: {e}")
                rc = 1
        return rc


@register
class Rmdir(BaseCommand):
    name = "rmdir"
    description = "Remove empty directories"
    usage = "rmdir DIRECTORY..."

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        if len(args) < 2:
            ctx.error("rmdir: missing operand")
            return 1
        rc = 0
        for d in args[1:]:
            path = ctx.fs.normalize(d, ctx.env.cwd)
            try:
                ctx.fs.rmdir(path)
            except Exception as e:
                ctx.error(f"rmdir: failed to remove '{d}': {e}")
                rc = 1
        return rc


@register
class Rm(BaseCommand):
    name = "rm"
    description = "Remove files or directories"
    usage = "rm [-rf] FILE..."

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        recursive = False
        force = False
        targets = []
        for a in args[1:]:
            if a.startswith("-"):
                if "r" in a or "R" in a:
                    recursive = True
                if "f" in a:
                    force = True
            else:
                targets.append(a)

        if not targets:
            if not force:
                ctx.error("rm: missing operand")
            return 0 if force else 1

        rc = 0
        for t in targets:
            path = ctx.fs.normalize(t, ctx.env.cwd)
            if not ctx.fs.exists(path):
                if not force:
                    ctx.error(f"rm: cannot remove '{t}': No such file or directory")
                    rc = 1
                continue
            try:
                if ctx.fs.is_dir(path):
                    if recursive:
                        ctx.fs.rmdir(path, recursive=True)
                    else:
                        ctx.error(f"rm: cannot remove '{t}': Is a directory")
                        rc = 1
                else:
                    ctx.fs.remove(path)
            except Exception as e:
                ctx.error(f"rm: {t}: {e}")
                rc = 1
        return rc


@register
class Cp(BaseCommand):
    name = "cp"
    description = "Copy files"
    usage = "cp [-r] SOURCE DEST"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        recursive = False
        files = []
        for a in args[1:]:
            if a in ("-r", "-R", "-a"):
                recursive = True
            elif not a.startswith("-"):
                files.append(a)

        if len(files) < 2:
            ctx.error("cp: missing file operand")
            return 1

        src = ctx.fs.normalize(files[0], ctx.env.cwd)
        dst = ctx.fs.normalize(files[1], ctx.env.cwd)

        if not ctx.fs.exists(src):
            ctx.error(f"cp: '{files[0]}': No such file or directory")
            return 1

        try:
            if ctx.fs.is_file(src):
                if ctx.fs.is_dir(dst):
                    dst = dst.rstrip("/") + "/" + src.split("/")[-1]
                ctx.fs.copy(src, dst)
            else:
                if not recursive:
                    ctx.error(f"cp: -r not specified; omitting directory '{files[0]}'")
                    return 1
                ctx.fs.copy(src, dst, recursive=True)
        except Exception as e:
            ctx.error(f"cp: {e}")
            return 1
        return 0


@register
class Mv(BaseCommand):
    name = "mv"
    description = "Move or rename files"
    usage = "mv SOURCE DEST"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        files = [a for a in args[1:] if not a.startswith("-")]
        if len(files) < 2:
            ctx.error("mv: missing file operand")
            return 1

        src = ctx.fs.normalize(files[0], ctx.env.cwd)
        dst = ctx.fs.normalize(files[1], ctx.env.cwd)

        if not ctx.fs.exists(src):
            ctx.error(f"mv: '{files[0]}': No such file or directory")
            return 1

        if ctx.fs.is_dir(dst):
            dst = dst.rstrip("/") + "/" + src.split("/")[-1]

        try:
            ctx.fs.rename(src, dst)
        except Exception as e:
            ctx.error(f"mv: {e}")
            return 1
        return 0


@register
class Touch(BaseCommand):
    name = "touch"
    description = "Update file timestamps or create empty files"
    usage = "touch FILE..."

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        files = [a for a in args[1:] if not a.startswith("-")]
        if not files:
            ctx.error("touch: missing file operand")
            return 1
        for f in files:
            ctx.fs.touch(ctx.fs.normalize(f, ctx.env.cwd))
        return 0


@register
class Chmod(BaseCommand):
    name = "chmod"
    description = "Change file permissions"
    usage = "chmod [-R] MODE FILE..."

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        from virtux.permissions import parse_mode
        recursive = "-R" in args
        real_args = [a for a in args[1:] if not a.startswith("-")]
        if len(real_args) < 2:
            ctx.error("chmod: missing operand")
            return 1
        mode_str, *targets = real_args
        for t in targets:
            path = ctx.fs.normalize(t, ctx.env.cwd)
            if not ctx.fs.exists(path):
                ctx.error(f"chmod: cannot access '{t}': No such file or directory")
                continue
            try:
                node = ctx.fs.get_node(path)
                ctx.fs.chmod(path, parse_mode(mode_str, node.permissions))
                if recursive and node.is_dir:
                    self._chmod_recursive(path, mode_str, ctx)
            except Exception as e:
                ctx.error(f"chmod: {t}: {e}")
                return 1
        return 0

    def _chmod_recursive(self, path: str, mode_str: str, ctx: ExecutionContext) -> None:
        from virtux.permissions import parse_mode
        try:
            for name in ctx.fs.listdir(path):
                child_path = path.rstrip("/") + "/" + name if path != "/" else "/" + name
                try:
                    node = ctx.fs.get_node(child_path)
                    ctx.fs.chmod(child_path, parse_mode(mode_str, node.permissions))
                    if node.is_dir:
                        self._chmod_recursive(child_path, mode_str, ctx)
                except Exception:
                    pass
        except Exception:
            pass


@register
class Ln(BaseCommand):
    name = "ln"
    description = "Create symbolic or hard links"
    usage = "ln [-s] TARGET LINK_NAME"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        symbolic = "-s" in args
        real_args = [a for a in args[1:] if not a.startswith("-")]
        if len(real_args) < 2:
            ctx.error("ln: missing file operand")
            return 1
        target, link = real_args[0], real_args[1]
        link_path = ctx.fs.normalize(link, ctx.env.cwd)
        if symbolic:
            ctx.fs.symlink(target, link_path)
        else:
            ctx.fs.copy(ctx.fs.normalize(target, ctx.env.cwd), link_path)
        return 0


@register
class Stat(BaseCommand):
    name = "stat"
    description = "Display file status"
    usage = "stat FILE..."

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        files = [a for a in args[1:] if not a.startswith("-")]
        if not files:
            ctx.error("stat: missing operand")
            return 1
        for f in files:
            node = ctx.fs.get_node(ctx.fs.normalize(f, ctx.env.cwd))
            if node is None:
                ctx.error(f"stat: cannot statx '{f}': No such file or directory")
                continue
            ftype = "directory" if node.is_dir else "regular file"
            ctx.writeln(f"  File: {f}")
            ctx.writeln(f"  Size: {node.size}\tBlocks: {node.size // 512}\t{ftype}")
            ctx.writeln(f" Owner: {node.owner}  Group: {node.group}")
            ctx.writeln(f"Access: {node.mode_string()}  Octal: {oct(node.permissions)}")
            ctx.writeln(f"Modify: {time.ctime(node.modified_at)}")
        return 0


@register
class Find(BaseCommand):
    name = "find"
    description = "Search for files in a directory hierarchy"
    usage = "find [PATH] [-name PATTERN] [-type f|d]"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        start = ctx.env.cwd
        name_pattern = None
        type_filter = None

        i = 1
        while i < len(args):
            a = args[i]
            if a == "-name" and i + 1 < len(args):
                name_pattern = args[i + 1]
                i += 2
            elif a == "-type" and i + 1 < len(args):
                type_filter = args[i + 1]
                i += 2
            elif not a.startswith("-"):
                start = ctx.fs.normalize(a, ctx.env.cwd)
                i += 1
            else:
                i += 1

        self._walk(start, name_pattern, type_filter, ctx)
        return 0

    def _walk(self, path, name_pat, type_filter, ctx):
        node = ctx.fs.get_node(path)
        if node is None:
            return
        type_ok = (not type_filter) or (type_filter == "f" and not node.is_dir) or (type_filter == "d" and node.is_dir)
        name_ok = (not name_pat) or fnmatch.fnmatch(node.name, name_pat)
        if type_ok and name_ok:
            ctx.writeln(path)
        if node.is_dir:
            for child_name in ctx.fs.listdir(path):
                child_path = path.rstrip("/") + "/" + child_name if path != "/" else "/" + child_name
                self._walk(child_path, name_pat, type_filter, ctx)


@register
class Du(BaseCommand):
    name = "du"
    description = "Estimate file space usage"
    usage = "du [-sh] [PATH...]"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        human = "-h" in args
        paths = [a for a in args[1:] if not a.startswith("-")] or [ctx.env.cwd]
        for raw in paths:
            total = self._size(ctx.fs.normalize(raw, ctx.env.cwd), ctx)
            ctx.writeln(f"{self._fmt(total, human)}\t{raw}")
        return 0

    def _size(self, path, ctx):
        node = ctx.fs.get_node(path)
        if node is None:
            return 0
        if not node.is_dir:
            return node.size
        total = 4096
        for name in ctx.fs.listdir(path):
            child = path.rstrip("/") + "/" + name if path != "/" else "/" + name
            total += self._size(child, ctx)
        return total

    def _fmt(self, size, human):
        if not human:
            return str(size // 1024 or 1)
        for unit in ("B", "K", "M", "G"):
            if size < 1024:
                return f"{size:.0f}{unit}"
            size /= 1024
        return f"{size:.0f}T"


@register
class Df(BaseCommand):
    name = "df"
    description = "Report disk space usage"
    usage = "df [-h]"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        ctx.writeln("Filesystem      Size  Used Avail Use% Mounted on")
        ctx.writeln("virtuxfs        10G   256M  9.8G   3% /")
        return 0


@register
class Tree(BaseCommand):
    name = "tree"
    description = "Display directory structure as a tree"
    usage = "tree [PATH]"

    def execute(self, args: List[str], ctx: ExecutionContext) -> int:
        real_args = [a for a in args[1:] if not a.startswith("-")]
        start = ctx.fs.normalize(real_args[0], ctx.env.cwd) if real_args else ctx.env.cwd
        if not ctx.fs.exists(start):
            ctx.error(f"tree: {start}: No such file or directory")
            return 1
        ctx.writeln(start)
        self._tree(start, "", ctx)
        return 0

    def _tree(self, path, prefix, ctx):
        names = ctx.fs.listdir(path)
        for i, name in enumerate(names):
            is_last = i == len(names) - 1
            connector = "└── " if is_last else "├── "
            child_path = path.rstrip("/") + "/" + name if path != "/" else "/" + name
            node = ctx.fs.get_node(child_path)
            display_name = f"\033[1;34m{name}\033[0m" if (node and node.is_dir) else name
            suffix = "/" if (node and node.is_dir) else ""
            ctx.writeln(f"{prefix}{connector}{display_name}{suffix}")
            if node and node.is_dir:
                self._tree(child_path, prefix + ("    " if is_last else "│   "), ctx)