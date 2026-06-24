from __future__ import annotations

import json
from typing import TYPE_CHECKING

from virtux.commands import register
from virtux.utils import normalize_path

if TYPE_CHECKING:
    from virtux.registry import CommandContext


@register(
    "tar",
    help_text="Archive utility.",
    usage="tar [-c|-x|-t] [-f archive] [-v] [-z] [files ...]",
    category="archive",
)
def cmd_tar(ctx: CommandContext) -> int:
    def has_flag(flag: str) -> bool:
        return any(flag in a for a in ctx.args if a.startswith("-") and a != "-f")

    create = has_flag("c")
    extract = has_flag("x")
    list_mode = has_flag("t")
    verbose = has_flag("v")
    archive_file = None
    files: list[str] = []

    i = 0
    while i < len(ctx.args):
        if ctx.args[i] == "-f" and i + 1 < len(ctx.args):
            archive_file = ctx.args[i + 1]
            i += 2
        elif ctx.args[i].startswith("-"):
            if "f" in ctx.args[i] and archive_file is None and i + 1 < len(ctx.args):
                archive_file = ctx.args[i + 1]
                i += 2
            else:
                i += 1
        else:
            files.append(ctx.args[i])
            i += 1

    if not archive_file:
        ctx.error("tar: you must specify an archive file with -f")
        return 1

    archive_path = ctx.resolve_path(archive_file)

    if create:
        if not files:
            ctx.error("tar: cowardly refusing to create an empty archive")
            return 1
        archive_data: dict = {"files": {}}
        for f in files:
            path = ctx.resolve_path(f)
            try:
                _collect_files(ctx, path, path, archive_data["files"], verbose)
            except Exception as e:
                ctx.error(f"tar: {f}: {e}")
                return 1
        ctx.fs.write_file(archive_path, json.dumps(archive_data))
        return 0

    elif extract:
        try:
            archive_data = json.loads(ctx.fs.read_text(archive_path))
        except Exception as e:
            ctx.error(f"tar: {archive_file}: {e}")
            return 1
        for rel_path, file_content in archive_data.get("files", {}).items():
            target = ctx.resolve_path(rel_path)
            group = ctx.users.get_primary_group_name()
            if file_content is None:
                try:
                    ctx.fs.mkdir(target, parents=True, owner=ctx.user, group=group)
                except Exception:
                    pass
            else:
                parent = target.rsplit("/", 1)[0] if "/" in target else "/"
                try:
                    ctx.fs.mkdir(parent, parents=True, owner=ctx.user, group=group)
                except Exception:
                    pass
                ctx.fs.write_file(target, file_content)
            if verbose:
                ctx.writeln(rel_path)
        return 0

    elif list_mode:
        try:
            archive_data = json.loads(ctx.fs.read_text(archive_path))
        except Exception as e:
            ctx.error(f"tar: {archive_file}: {e}")
            return 1
        for rel_path in archive_data.get("files", {}):
            ctx.writeln(rel_path)
        return 0

    ctx.error("tar: you must specify one of -c, -x, -t")
    return 1


@register(
    "gzip",
    help_text="Compress files (simulated).",
    usage="gzip [-d] file ...",
    category="archive",
)
def cmd_gzip(ctx: CommandContext) -> int:
    decompress = "-d" in ctx.args
    files = [a for a in ctx.args if not a.startswith("-")]
    if not files:
        ctx.error("gzip: missing file operand")
        return 1
    for f in files:
        path = ctx.resolve_path(f)
        try:
            content = ctx.fs.read_text(path)
            if decompress:
                if not path.endswith(".gz"):
                    ctx.error(f"gzip: {f}: unknown suffix -- ignored")
                    continue
                ctx.fs.write_file(path[:-3], content)
                ctx.fs.remove(path)
            else:
                ctx.fs.write_file(path + ".gz", f"[gzip compressed] {content}")
                ctx.fs.remove(path)
        except Exception as e:
            ctx.error(f"gzip: {f}: {e}")
            return 1
    return 0


@register(
    "gunzip",
    help_text="Decompress files (simulated).",
    usage="gunzip file ...",
    category="archive",
)
def cmd_gunzip(ctx: CommandContext) -> int:
    files = [a for a in ctx.args if not a.startswith("-")]
    if not files:
        ctx.error("gunzip: missing file operand")
        return 1
    for f in files:
        path = ctx.resolve_path(f)
        if not path.endswith(".gz"):
            ctx.error(f"gunzip: {f}: unknown suffix -- ignored")
            continue
        try:
            content = ctx.fs.read_text(path)
            if content.startswith("[gzip compressed] "):
                content = content[len("[gzip compressed] "):]
            ctx.fs.write_file(path[:-3], content)
            ctx.fs.remove(path)
        except Exception as e:
            ctx.error(f"gunzip: {f}: {e}")
            return 1
    return 0


@register(
    "zip",
    help_text="Package and compress files (simulated).",
    usage="zip archive.zip file ...",
    category="archive",
)
def cmd_zip(ctx: CommandContext) -> int:
    files = [a for a in ctx.args if not a.startswith("-")]
    if len(files) < 2:
        ctx.error("zip: missing archive or file operand")
        return 1
    archive_path = ctx.resolve_path(files[0])
    archive_data: dict = {"files": {}}
    for f in files[1:]:
        path = ctx.resolve_path(f)
        try:
            archive_data["files"][f] = ctx.fs.read_text(path)
            ctx.writeln(f"  adding: {f}")
        except Exception as e:
            ctx.error(f"zip: {f}: {e}")
            return 1
    ctx.fs.write_file(archive_path, json.dumps(archive_data))
    return 0


@register(
    "unzip",
    help_text="Extract compressed files (simulated).",
    usage="unzip archive.zip [-d directory]",
    category="archive",
)
def cmd_unzip(ctx: CommandContext) -> int:
    archive = None
    dest_dir = ctx.cwd
    i = 0
    while i < len(ctx.args):
        if ctx.args[i] == "-d" and i + 1 < len(ctx.args):
            dest_dir = ctx.resolve_path(ctx.args[i + 1])
            i += 2
        elif not ctx.args[i].startswith("-"):
            archive = ctx.args[i]
            i += 1
        else:
            i += 1
    if not archive:
        ctx.error("unzip: missing archive operand")
        return 1
    archive_path = ctx.resolve_path(archive)
    try:
        archive_data = json.loads(ctx.fs.read_text(archive_path))
    except Exception as e:
        ctx.error(f"unzip: {archive}: {e}")
        return 1
    ctx.writeln(f"Archive:  {archive}")
    for rel_path, file_content in archive_data.get("files", {}).items():
        ctx.fs.write_file(normalize_path(rel_path, dest_dir), file_content)
        ctx.writeln(f"  inflating: {rel_path}")
    return 0


def _collect_files(
    ctx: CommandContext,
    base_path: str,
    current_path: str,
    files_dict: dict,
    verbose: bool,
) -> None:
    from virtux.utils import split_path

    if ctx.fs.is_file(current_path):
        _, name = split_path(current_path)
        files_dict[name] = ctx.fs.read_text(current_path)
        if verbose:
            ctx.writeln(name)
    elif ctx.fs.is_dir(current_path):
        _, dir_name = split_path(current_path)
        files_dict[dir_name + "/"] = None
        if verbose:
            ctx.writeln(dir_name + "/")
        for entry in ctx.fs.listdir(current_path):
            _collect_files(ctx, base_path, normalize_path(entry, current_path), files_dict, verbose)