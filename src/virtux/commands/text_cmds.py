from __future__ import annotations
from virtux.commands import register

import re
from typing import TYPE_CHECKING, Any

from virtux.utils import escape_string

if TYPE_CHECKING:
    from virtux.registry import CommandContext


@register(
    "cat",
    help_text="Concatenate files and print on the standard output.",
    usage="cat [-n] [file ...]",
    category="text",
)
def cmd_cat(ctx: CommandContext) -> int:
    show_numbers = "-n" in ctx.args
    files = [a for a in ctx.args if not a.startswith("-")]

    if not files:
        content = ctx.read_stdin()
        if content:
            if show_numbers:
                _print_numbered(ctx, content)
            else:
                ctx.write(content)
        return 0

    for f in files:
        path = ctx.resolve_path(f)
        try:
            content = ctx.fs.read_text(path)
            if show_numbers:
                _print_numbered(ctx, content)
            else:
                ctx.write(content)
        except Exception as e:
            ctx.error(f"cat: {f}: {e}")
            return 1
    return 0


@register(
    "head",
    help_text="Output the first part of files.",
    usage="head [-n count] [file ...]",
    category="text",
)
def cmd_head(ctx: CommandContext) -> int:
    count = 10
    files: list[str] = []

    i = 0
    while i < len(ctx.args):
        if ctx.args[i] == "-n" and i + 1 < len(ctx.args):
            try:
                count = int(ctx.args[i + 1])
            except ValueError:
                ctx.error(f"head: invalid number of lines: '{ctx.args[i + 1]}'")
                return 1
            i += 2
        elif ctx.args[i].startswith("-") and ctx.args[i][1:].isdigit():
            count = int(ctx.args[i][1:])
            i += 1
        elif not ctx.args[i].startswith("-"):
            files.append(ctx.args[i])
            i += 1
        else:
            i += 1

    if not files:
        content = ctx.read_stdin()
        lines = content.splitlines(keepends=True)
        ctx.write("".join(lines[:count]))
        return 0

    for f in files:
        path = ctx.resolve_path(f)
        try:
            content = ctx.fs.read_text(path)
            if len(files) > 1:
                ctx.writeln(f"==> {f} <==")
            lines = content.splitlines(keepends=True)
            ctx.write("".join(lines[:count]))
        except Exception as e:
            ctx.error(f"head: {e}")
            return 1
    return 0


@register(
    "tail",
    help_text="Output the last part of files.",
    usage="tail [-n count] [file ...]",
    category="text",
)
def cmd_tail(ctx: CommandContext) -> int:
    count = 10
    files: list[str] = []

    i = 0
    while i < len(ctx.args):
        if ctx.args[i] == "-n" and i + 1 < len(ctx.args):
            try:
                count = int(ctx.args[i + 1])
            except ValueError:
                ctx.error(f"tail: invalid number of lines: '{ctx.args[i + 1]}'")
                return 1
            i += 2
        elif not ctx.args[i].startswith("-"):
            files.append(ctx.args[i])
            i += 1
        else:
            i += 1

    if not files:
        content = ctx.read_stdin()
        lines = content.splitlines(keepends=True)
        ctx.write("".join(lines[-count:]))
        return 0

    for f in files:
        path = ctx.resolve_path(f)
        try:
            content = ctx.fs.read_text(path)
            if len(files) > 1:
                ctx.writeln(f"==> {f} <==")
            lines = content.splitlines(keepends=True)
            ctx.write("".join(lines[-count:]))
        except Exception as e:
            ctx.error(f"tail: {e}")
            return 1
    return 0


@register(
    "grep",
    help_text="Print lines that match patterns.",
    usage="grep [-i] [-r] [-n] [-v] [-c] pattern [file ...]",
    category="text",
)
def cmd_grep(ctx: CommandContext) -> int:
    ignore_case = "-i" in ctx.args
    recursive = "-r" in ctx.args or "-R" in ctx.args
    show_numbers = "-n" in ctx.args
    invert = "-v" in ctx.args
    count_only = "-c" in ctx.args

    non_flag_args = [a for a in ctx.args if not a.startswith("-")]

    if not non_flag_args:
        ctx.error("grep: missing pattern")
        return 2

    pattern = non_flag_args[0]
    files = non_flag_args[1:]

    flags = re.IGNORECASE if ignore_case else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        ctx.error(f"grep: invalid pattern '{pattern}': {e}")
        return 2

    if not files:
        content = ctx.read_stdin()
        match_count = 0
        for i, line in enumerate(content.splitlines(), 1):
            matched = bool(regex.search(line))
            if invert:
                matched = not matched
            if matched:
                match_count += 1
                if not count_only:
                    if show_numbers:
                        ctx.writeln(f"{i}:{line}")
                    else:
                        ctx.writeln(line)
        if count_only:
            ctx.writeln(str(match_count))
        return 0 if match_count > 0 else 1

    total_matches = 0
    show_filename = len(files) > 1 or recursive

    for f in files:
        path = ctx.resolve_path(f)

        if recursive and ctx.fs.is_dir(path):
            found = ctx.fs.find(path, node_type="file")
            for fp in found:
                total_matches += _grep_file(
                    ctx, fp, regex, invert, show_numbers,
                    count_only, True
                )
        else:
            total_matches += _grep_file(
                ctx, path, regex, invert, show_numbers,
                count_only, show_filename
            )

    return 0 if total_matches > 0 else 1


@register(
    "wc",
    help_text="Print newline, word, and byte counts for each file.",
    usage="wc [-l] [-w] [-c] [file ...]",
    category="text",
)
def cmd_wc(ctx: CommandContext) -> int:
    count_lines = "-l" in ctx.args
    count_words = "-w" in ctx.args
    count_bytes = "-c" in ctx.args
    files = [a for a in ctx.args if not a.startswith("-")]

    if not count_lines and not count_words and not count_bytes:
        count_lines = count_words = count_bytes = True

    def format_counts(lines: int, words: int, nbytes: int, name: str) -> str:
        parts = []
        if count_lines:
            parts.append(f"{lines:>7}")
        if count_words:
            parts.append(f"{words:>7}")
        if count_bytes:
            parts.append(f"{nbytes:>7}")
        parts.append(f" {name}")
        return " ".join(parts)

    if not files:
        content = ctx.read_stdin()
        lines = content.count("\n")
        words = len(content.split())
        nbytes = len(content.encode("utf-8"))
        ctx.writeln(format_counts(lines, words, nbytes, ""))
        return 0

    total_lines = total_words = total_bytes = 0
    for f in files:
        path = ctx.resolve_path(f)
        try:
            content = ctx.fs.read_text(path)
            lines = content.count("\n")
            words = len(content.split())
            nbytes = len(content.encode("utf-8"))
            total_lines += lines
            total_words += words
            total_bytes += nbytes
            ctx.writeln(format_counts(lines, words, nbytes, f))
        except Exception as e:
            ctx.error(f"wc: {f}: {e}")
            return 1

    if len(files) > 1:
        ctx.writeln(format_counts(total_lines, total_words, total_bytes, "total"))
    return 0


@register(
    "sort",
    help_text="Sort lines of text files.",
    usage="sort [-r] [-n] [-k field] [file ...]",
    category="text",
)
def cmd_sort(ctx: CommandContext) -> int:
    reverse = "-r" in ctx.args
    numeric = "-n" in ctx.args
    key_field = None
    files: list[str] = []

    i = 0
    while i < len(ctx.args):
        if ctx.args[i] == "-k" and i + 1 < len(ctx.args):
            try:
                key_field = int(ctx.args[i + 1]) - 1
            except ValueError:
                pass
            i += 2
        elif not ctx.args[i].startswith("-"):
            files.append(ctx.args[i])
            i += 1
        else:
            i += 1

    if files:
        lines_list: list[str] = []
        for f in files:
            path = ctx.resolve_path(f)
            try:
                content = ctx.fs.read_text(path)
                lines_list.extend(content.splitlines())
            except Exception as e:
                ctx.error(f"sort: {e}")
                return 1
    else:
        content = ctx.read_stdin()
        lines_list = content.splitlines()

    def sort_key(line: str) -> Any:
        if key_field is not None:
            fields = line.split()
            val = fields[key_field] if key_field < len(fields) else ""
        else:
            val = line

        if numeric:
            try:
                return float(val)
            except ValueError:
                return 0.0
        return val

    lines_list.sort(key=sort_key, reverse=reverse)
    for line in lines_list:
        ctx.writeln(line)
    return 0


@register(
    "uniq",
    help_text="Report or omit repeated lines.",
    usage="uniq [-c] [-d] [file]",
    category="text",
)
def cmd_uniq(ctx: CommandContext) -> int:
    show_count = "-c" in ctx.args
    only_dups = "-d" in ctx.args
    files = [a for a in ctx.args if not a.startswith("-")]

    if files:
        path = ctx.resolve_path(files[0])
        try:
            content = ctx.fs.read_text(path)
        except Exception as e:
            ctx.error(f"uniq: {e}")
            return 1
    else:
        content = ctx.read_stdin()

    lines = content.splitlines()
    prev = None
    count = 0

    def emit(value: str, n: int) -> None:
        if not only_dups or n > 1:
            if show_count:
                ctx.writeln(f"{n:>7} {value}")
            else:
                ctx.writeln(value)

    for line in lines:
        if line == prev:
            count += 1
        else:
            if prev is not None:
                emit(prev, count)
            prev = line
            count = 1

    if prev is not None:
        emit(prev, count)

    return 0


@register(
    "cut",
    help_text="Remove sections from each line of files.",
    usage="cut -d delimiter -f field_list [file ...]",
    category="text",
)
def cmd_cut(ctx: CommandContext) -> int:
    delimiter = "\t"
    field_spec = ""
    files: list[str] = []

    i = 0
    while i < len(ctx.args):
        if ctx.args[i] == "-d" and i + 1 < len(ctx.args):
            delimiter = ctx.args[i + 1]
            i += 2
        elif ctx.args[i] == "-f" and i + 1 < len(ctx.args):
            field_spec = ctx.args[i + 1]
            i += 2
        elif not ctx.args[i].startswith("-"):
            files.append(ctx.args[i])
            i += 1
        else:
            i += 1

    if not field_spec:
        ctx.error("cut: you must specify a list of fields")
        return 1

    fields = _parse_field_spec(field_spec)

    if files:
        for f in files:
            path = ctx.resolve_path(f)
            try:
                content = ctx.fs.read_text(path)
                _cut_content(ctx, content, delimiter, fields)
            except Exception as e:
                ctx.error(f"cut: {e}")
                return 1
    else:
        content = ctx.read_stdin()
        _cut_content(ctx, content, delimiter, fields)

    return 0


@register(
    "sed",
    help_text="Stream editor for filtering and transforming text.",
    usage="sed 's/pattern/replacement/[g]' [file ...]",
    category="text",
)
def cmd_sed(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("sed: missing script")
        return 1

    script = ctx.args[0]
    files = ctx.args[1:]

    if not script.startswith("s") or len(script) < 2:
        ctx.error("sed: only s/pattern/replacement/ is supported")
        return 1

    delim = script[1]
    parts = script[2:].split(delim)
    if len(parts) < 2:
        ctx.error("sed: invalid substitution expression")
        return 1

    pattern = parts[0]
    replacement = parts[1]
    flags_str = parts[2] if len(parts) > 2 else ""
    global_flag = "g" in flags_str

    try:
        regex = re.compile(pattern)
    except re.error as e:
        ctx.error(f"sed: invalid pattern: {e}")
        return 1

    if files:
        for f in files:
            path = ctx.resolve_path(f)
            try:
                content = ctx.fs.read_text(path)
                result = _sed_process(content, regex, replacement, global_flag)
                ctx.write(result)
            except Exception as e:
                ctx.error(f"sed: {e}")
                return 1
    else:
        content = ctx.read_stdin()
        result = _sed_process(content, regex, replacement, global_flag)
        ctx.write(result)

    return 0


@register(
    "awk",
    help_text="Pattern scanning and processing language.",
    usage="awk '{print $N}' [file ...]",
    category="text",
)
def cmd_awk(ctx: CommandContext) -> int:
    if not ctx.args:
        ctx.error("awk: missing program")
        return 1

    program = ctx.args[0]
    files = ctx.args[1:]

    print_match = re.match(r"^\{?\s*print\s+(.*?)\s*\}?$", program)
    if not print_match:
        ctx.error("awk: only '{print $N}' syntax is supported")
        return 1

    field_refs = print_match.group(1)

    if files:
        for f in files:
            path = ctx.resolve_path(f)
            try:
                content = ctx.fs.read_text(path)
                _awk_process(ctx, content, field_refs)
            except Exception as e:
                ctx.error(f"awk: {e}")
                return 1
    else:
        content = ctx.read_stdin()
        _awk_process(ctx, content, field_refs)

    return 0


@register(
    "echo",
    help_text="Display a line of text.",
    usage="echo [-n] [-e] [string ...]",
    category="text",
)
def cmd_echo(ctx: CommandContext) -> int:
    no_newline = "-n" in ctx.args
    interpret_escapes = "-e" in ctx.args
    parts = [a for a in ctx.args if a not in ("-n", "-e")]

    text = " ".join(parts)

    if interpret_escapes:
        text = escape_string(text)

    ctx.write(text)
    if not no_newline:
        ctx.write("\n")
    return 0


@register(
    "tee",
    help_text="Read from standard input and write to standard output and files.",
    usage="tee [-a] [file ...]",
    category="text",
)
def cmd_tee(ctx: CommandContext) -> int:
    append = "-a" in ctx.args
    files = [a for a in ctx.args if not a.startswith("-")]

    content = ctx.read_stdin()
    ctx.write(content)

    for f in files:
        path = ctx.resolve_path(f)
        try:
            if append:
                ctx.fs.append_file(path, content)
            else:
                ctx.fs.write_file(path, content)
        except Exception as e:
            ctx.error(f"tee: {f}: {e}")
            return 1
    return 0


@register(
    "diff",
    help_text="Compare files line by line.",
    usage="diff file1 file2",
    category="text",
)
def cmd_diff(ctx: CommandContext) -> int:
    files = [a for a in ctx.args if not a.startswith("-")]
    if len(files) < 2:
        ctx.error("diff: missing operand")
        return 2

    try:
        content1 = ctx.fs.read_text(ctx.resolve_path(files[0]))
        content2 = ctx.fs.read_text(ctx.resolve_path(files[1]))
    except Exception as e:
        ctx.error(f"diff: {e}")
        return 2

    lines1 = content1.splitlines()
    lines2 = content2.splitlines()

    if lines1 == lines2:
        return 0

    max_lines = max(len(lines1), len(lines2))
    has_diff = False
    for i in range(max_lines):
        l1 = lines1[i] if i < len(lines1) else None
        l2 = lines2[i] if i < len(lines2) else None

        if l1 != l2:
            has_diff = True
            if l1 is not None and l2 is not None:
                ctx.writeln(f"{i + 1}c{i + 1}")
                ctx.writeln(f"< {l1}")
                ctx.writeln("---")
                ctx.writeln(f"> {l2}")
            elif l1 is None:
                ctx.writeln(f"{i + 1}a{i + 1}")
                ctx.writeln(f"> {l2}")
            else:
                ctx.writeln(f"{i + 1}d{i + 1}")
                ctx.writeln(f"< {l1}")

    return 1 if has_diff else 0


def _print_numbered(ctx: "CommandContext", content: str) -> None:
    for i, line in enumerate(content.splitlines(keepends=True), 1):
        ctx.write(f"{i:>6}\t{line}")


def _grep_file(
    ctx: "CommandContext",
    path: str,
    regex: re.Pattern,
    invert: bool,
    show_numbers: bool,
    count_only: bool,
    show_filename: bool,
) -> int:
    try:
        content = ctx.fs.read_text(path)
    except Exception:
        return 0

    match_count = 0
    for i, line in enumerate(content.splitlines(), 1):
        matched = bool(regex.search(line))
        if invert:
            matched = not matched
        if matched:
            match_count += 1
            if not count_only:
                prefix = f"{path}:" if show_filename else ""
                if show_numbers:
                    prefix += f"{i}:"
                ctx.writeln(f"{prefix}{line}")

    if count_only:
        prefix = f"{path}:" if show_filename else ""
        ctx.writeln(f"{prefix}{match_count}")

    return match_count


def _parse_field_spec(spec: str) -> list[int]:
    fields: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            start_end = part.split("-", 1)
            try:
                start = int(start_end[0]) if start_end[0] else 1
                end = int(start_end[1]) if start_end[1] else 100
                fields.extend(range(start, end + 1))
            except ValueError:
                pass
        else:
            try:
                fields.append(int(part))
            except ValueError:
                pass
    return fields


def _cut_content(ctx: "CommandContext", content: str, delimiter: str, fields: list[int]) -> None:
    for line in content.splitlines():
        parts = line.split(delimiter)
        selected = [parts[f - 1] for f in fields if 1 <= f <= len(parts)]
        ctx.writeln(delimiter.join(selected))


def _sed_process(content: str, regex: re.Pattern, replacement: str, global_flag: bool) -> str:
    result_lines = []
    for line in content.splitlines(keepends=True):
        count = 0 if global_flag else 1
        result_lines.append(regex.sub(replacement, line, count=count))
    return "".join(result_lines)


def _awk_process(ctx: "CommandContext", content: str, field_refs: str) -> None:
    refs = [r.strip().strip('"').strip("'") for r in field_refs.replace(",", " ").split()]

    for line in content.splitlines():
        fields = line.split()
        output_parts: list[str] = []

        for ref in refs:
            if ref.startswith("$"):
                field_id = ref[1:]
                if field_id == "0":
                    output_parts.append(line)
                elif field_id == "NF":
                    output_parts.append(fields[-1] if fields else "")
                else:
                    try:
                        idx = int(field_id) - 1
                        output_parts.append(fields[idx] if 0 <= idx < len(fields) else "")
                    except ValueError:
                        output_parts.append(ref)
            else:
                output_parts.append(ref)

        ctx.writeln(" ".join(output_parts))