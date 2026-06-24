"""
Parser for Virtux shell input.
Handles: pipes (|), redirections (>, >>, <), semicolons (;),
         AND (&&), OR (||), background (&), quotes, env-var expansion,
         glob expansion, and alias substitution.
"""

import fnmatch
from dataclasses import dataclass, field
from typing import List


@dataclass
class Redirect:
    kind: str        # "out", "append", "in", "err", "err_append"
    target: str      # filename or "&1" / "&2"


@dataclass
class Command:
    """One simple command (possibly part of a pipeline)."""
    args: List[str] = field(default_factory=list)
    redirects: List[Redirect] = field(default_factory=list)
    background: bool = False

    @property
    def name(self) -> str:
        return self.args[0] if self.args else ""


@dataclass
class Pipeline:
    """A list of Commands joined by |."""
    commands: List[Command] = field(default_factory=list)
    operator: str = ";"   # ";", "&&", "||" - how the PREVIOUS pipeline's exit code gates this one
    background: bool = False


class ParseError(Exception):
    pass


_SPECIAL = set("|&;<>() \t\n")


def _tokenize(line: str) -> List[str]:
    """
    Split a shell line into raw tokens, respecting single/double quotes
    and backslash escapes.
    """
    tokens = []
    current = []
    i = 0
    length = len(line)

    while i < length:
        ch = line[i]

        if ch == "\\" and i + 1 < length:
            current.append(line[i + 1])
            i += 2
            continue

        if ch == "'":
            start = i
            i += 1
            while i < length and line[i] != "'":
                current.append(line[i])
                i += 1
            if i >= length:
                raise ParseError(f"Unterminated single quote starting at position {start}")
            i += 1
            continue

        if ch == '"':
            start = i
            i += 1
            while i < length and line[i] != '"':
                if line[i] == "\\" and i + 1 < length and line[i + 1] in ('"', '\\', '$'):
                    current.append(line[i + 1])
                    i += 2
                else:
                    current.append(line[i])
                    i += 1
            if i >= length:
                raise ParseError(f"Unterminated double quote starting at position {start}")
            i += 1
            continue

        if ch in (" ", "\t"):
            if current:
                tokens.append("".join(current))
                current = []
            i += 1
            continue

        if i + 2 < length and line[i:i+3] == "2>>":
            if current:
                tokens.append("".join(current))
                current = []
            tokens.append("2>>")
            i += 3
            continue

        if i + 1 < length:
            two = line[i:i+2]
            if two in (">>", "&&", "||", "2>", "&>"):
                if current:
                    tokens.append("".join(current))
                    current = []
                tokens.append(two)
                i += 2
                continue

        if ch in ("|", "&", ";", "<", ">", "(", ")"):
            if current:
                tokens.append("".join(current))
                current = []
            tokens.append(ch)
            i += 1
            continue

        current.append(ch)
        i += 1

    if current:
        tokens.append("".join(current))

    return tokens


def parse(line: str, env=None, fs=None) -> List[Pipeline]:
    """
    Parse a shell line into a list of Pipelines (chained by ;, &&, ||).
    Performs alias substitution, variable expansion, and glob expansion
    when env and fs are provided.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return []

    if env:
        line = env.expand_vars(line)

    tokens = _tokenize(line)

    if env:
        tokens = _expand_aliases(tokens, env)

    return _parse_tokens(tokens, env=env, fs=fs)


def _expand_aliases(tokens: List[str], env, _seen=None) -> List[str]:
    """Expand aliases at the start of each command (after |, ;, &&, ||, &)."""
    if _seen is None:
        _seen = set()

    boundary = {"|", ";", "&&", "||", "&"}
    result: List[str] = []
    expect_command_start = True

    for tok in tokens:
        if expect_command_start and tok in env.aliases and tok not in _seen:
            replacement = env.aliases[tok]
            sub_tokens = _tokenize(replacement)
            sub_tokens = _expand_aliases(sub_tokens, env, _seen | {tok})
            result.extend(sub_tokens)
        else:
            result.append(tok)

        expect_command_start = tok in boundary

    return result


def _parse_tokens(tokens: List[str], env=None, fs=None) -> List[Pipeline]:
    pipelines: List[Pipeline] = []
    current_pipeline = Pipeline()
    current_cmd = Command()
    pending_operator = ";"
    i = 0

    def flush_cmd():
        nonlocal current_cmd
        if current_cmd.args or current_cmd.redirects:
            if fs and env:
                expanded = []
                for j, arg in enumerate(current_cmd.args):
                    if j == 0 or ("*" not in arg and "?" not in arg and "[" not in arg):
                        expanded.append(arg)
                    else:
                        matches = _glob_expand(arg, env.cwd, fs)
                        expanded.extend(matches if matches else [arg])
                current_cmd.args = expanded
            current_pipeline.commands.append(current_cmd)
        current_cmd = Command()

    def flush_pipeline(next_operator=";", background=False):
        nonlocal current_pipeline, pending_operator
        flush_cmd()
        if current_pipeline.commands:
            current_pipeline.operator = pending_operator
            current_pipeline.background = background
            pipelines.append(current_pipeline)
        pending_operator = next_operator
        current_pipeline = Pipeline()

    while i < len(tokens):
        tok = tokens[i]

        if tok == "|":
            flush_cmd()
            i += 1
        elif tok == ";":
            flush_pipeline(";")
            i += 1
        elif tok == "&&":
            flush_pipeline("&&")
            i += 1
        elif tok == "||":
            flush_pipeline("||")
            i += 1
        elif tok == "&":
            flush_pipeline(";", background=True)
            i += 1
        elif tok == ">":
            if i + 1 < len(tokens):
                current_cmd.redirects.append(Redirect("out", tokens[i + 1]))
                i += 2
            else:
                raise ParseError("Expected filename after >")
        elif tok == ">>":
            if i + 1 < len(tokens):
                current_cmd.redirects.append(Redirect("append", tokens[i + 1]))
                i += 2
            else:
                raise ParseError("Expected filename after >>")
        elif tok == "<":
            if i + 1 < len(tokens):
                current_cmd.redirects.append(Redirect("in", tokens[i + 1]))
                i += 2
            else:
                raise ParseError("Expected filename after <")
        elif tok == "2>":
            if i + 1 < len(tokens):
                current_cmd.redirects.append(Redirect("err", tokens[i + 1]))
                i += 2
            else:
                raise ParseError("Expected filename after 2>")
        elif tok == "2>>":
            if i + 1 < len(tokens):
                current_cmd.redirects.append(Redirect("err_append", tokens[i + 1]))
                i += 2
            else:
                raise ParseError("Expected filename after 2>>")
        elif tok == "&>":
            if i + 1 < len(tokens):
                current_cmd.redirects.append(Redirect("out", tokens[i + 1]))
                current_cmd.redirects.append(Redirect("err", tokens[i + 1]))
                i += 2
            else:
                raise ParseError("Expected filename after &>")
        else:
            current_cmd.args.append(tok)
            i += 1

    flush_pipeline(";")
    return pipelines


def _glob_expand(pattern: str, cwd: str, fs) -> List[str]:
    """Expand a glob pattern against the virtual filesystem."""
    if "/" in pattern:
        idx = pattern.rfind("/")
        base = fs.normalize(pattern[:idx] or "/", cwd)
        pat = pattern[idx + 1:]
    else:
        base = cwd
        pat = pattern

    if not fs.is_dir(base):
        return []

    names = fs.listdir(base)
    matches = [
        (base.rstrip("/") + "/" + n) if base != "/" else ("/" + n)
        for n in names
        if fnmatch.fnmatch(n, pat)
    ]
    return sorted(matches)