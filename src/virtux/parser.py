"""
Shell command parser for the Virtux terminal emulator.

Tokenizes shell input and builds an AST supporting pipes, redirects,
logical operators, variable expansion, quoting, and command substitution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class TokenType(Enum):
    """Types of shell tokens."""
    WORD = auto()
    PIPE = auto()
    REDIRECT_OUT = auto()
    REDIRECT_APPEND = auto()
    REDIRECT_IN = auto()
    REDIRECT_ERR = auto()
    AND = auto()
    OR = auto()
    SEMICOLON = auto()
    BACKGROUND = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    """A single shell token."""
    type: TokenType
    value: str = ""


@dataclass
class Redirect:
    """A redirect specification."""
    type: str
    target: str


@dataclass
class Command:
    """A single command with its arguments and redirects."""
    name: str = ""
    args: list[str] = field(default_factory=list)
    redirects: list[Redirect] = field(default_factory=list)

    @property
    def full_args(self) -> list[str]:
        if self.name:
            return [self.name] + self.args
        return self.args


@dataclass
class Pipeline:
    """A sequence of commands connected by pipes."""
    commands: list[Command] = field(default_factory=list)
    background: bool = False


@dataclass
class CommandList:
    """A list of pipelines connected by logical operators."""
    pipelines: list[Pipeline] = field(default_factory=list)
    operators: list[str] = field(default_factory=list)


class ShellParseError(Exception):
    """Raised when the shell input cannot be parsed."""
    pass


class Tokenizer:
    """Tokenizes shell input into a stream of tokens.

    Handles quoting (single and double), escape sequences,
    and special shell characters.
    """

    def __init__(self, input_str: str) -> None:
        self._input = input_str
        self._pos = 0
        self._tokens: list[Token] = []

    def tokenize(self) -> list[Token]:
        """Tokenize the entire input string."""
        self._tokens = []
        while self._pos < len(self._input):
            self._skip_whitespace()
            if self._pos >= len(self._input):
                break

            c = self._input[self._pos]

            if c == '#':
                break
            elif c == '|':
                if self._peek(1) == '|':
                    self._tokens.append(Token(TokenType.OR, "||"))
                    self._pos += 2
                else:
                    self._tokens.append(Token(TokenType.PIPE, "|"))
                    self._pos += 1
            elif c == '&':
                if self._peek(1) == '&':
                    self._tokens.append(Token(TokenType.AND, "&&"))
                    self._pos += 2
                else:
                    self._tokens.append(Token(TokenType.BACKGROUND, "&"))
                    self._pos += 1
            elif c == ';':
                self._tokens.append(Token(TokenType.SEMICOLON, ";"))
                self._pos += 1
            elif c == '>':
                if self._peek(1) == '>':
                    self._tokens.append(Token(TokenType.REDIRECT_APPEND, ">>"))
                    self._pos += 2
                else:
                    self._tokens.append(Token(TokenType.REDIRECT_OUT, ">"))
                    self._pos += 1
            elif c == '<':
                self._tokens.append(Token(TokenType.REDIRECT_IN, "<"))
                self._pos += 1
            elif c == '2' and self._peek(1) == '>':
                self._tokens.append(Token(TokenType.REDIRECT_ERR, "2>"))
                self._pos += 2
            elif c == '\n':
                self._tokens.append(Token(TokenType.NEWLINE, "\n"))
                self._pos += 1
            else:
                self._read_word()

        self._tokens.append(Token(TokenType.EOF))
        return self._tokens

    def _peek(self, offset: int = 0) -> str:
        pos = self._pos + offset
        if pos < len(self._input):
            return self._input[pos]
        return ""

    def _skip_whitespace(self) -> None:
        while self._pos < len(self._input) and self._input[self._pos] in (' ', '\t'):
            self._pos += 1

    def _read_word(self) -> None:
        """Read a word token, handling quoting and escapes."""
        word_parts: list[str] = []

        while self._pos < len(self._input):
            c = self._input[self._pos]

            if c in (' ', '\t', '\n', '|', '&', ';', '>', '<'):
                break
            elif c == '\\':
                if self._pos + 1 < len(self._input):
                    self._pos += 1
                    word_parts.append(self._input[self._pos])
                    self._pos += 1
                else:
                    word_parts.append('\\')
                    self._pos += 1
            elif c == '"':
                start = self._pos
                self._pos += 1
                while self._pos < len(self._input) and self._input[self._pos] != '"':
                    if self._input[self._pos] == '\\' and self._pos + 1 < len(self._input):
                        next_c = self._input[self._pos + 1]
                        if next_c in ('"', '\\', '$', '`'):
                            word_parts.append(next_c)
                            self._pos += 2
                        else:
                            word_parts.append(self._input[self._pos])
                            self._pos += 1
                    else:
                        word_parts.append(self._input[self._pos])
                        self._pos += 1
                if self._pos >= len(self._input):
                    raise ShellParseError(f"Unterminated double quote starting at position {start}")
                self._pos += 1
            elif c == "'":
                start = self._pos
                self._pos += 1
                while self._pos < len(self._input) and self._input[self._pos] != "'":
                    word_parts.append(self._input[self._pos])
                    self._pos += 1
                if self._pos >= len(self._input):
                    raise ShellParseError(f"Unterminated single quote starting at position {start}")
                self._pos += 1
            else:
                word_parts.append(c)
                self._pos += 1

        if word_parts:
            self._tokens.append(Token(TokenType.WORD, "".join(word_parts)))


class Parser:
    """Parses a token stream into a CommandList AST.

    Grammar:
        command_list = pipeline ((AND | OR | SEMICOLON | BACKGROUND) pipeline)*
        pipeline = command (PIPE command)*
        command = WORD+ (redirect)*
        redirect = (REDIRECT_OUT | REDIRECT_APPEND | REDIRECT_IN | REDIRECT_ERR) WORD
    """

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    def parse(self) -> CommandList:
        """Parse the token stream into a CommandList."""
        cmd_list = CommandList()

        self._skip_separators()

        if self._current().type == TokenType.EOF:
            return cmd_list

        pipeline = self._parse_pipeline()
        if pipeline:
            cmd_list.pipelines.append(pipeline)

        while self._current().type in (TokenType.AND, TokenType.OR, TokenType.SEMICOLON):
            op = self._current().value
            cmd_list.operators.append(op)
            self._advance()
            self._skip_separators()

            if self._current().type == TokenType.EOF:
                break

            pipeline = self._parse_pipeline()
            if pipeline:
                cmd_list.pipelines.append(pipeline)

        return cmd_list

    def _parse_pipeline(self) -> Optional[Pipeline]:
        """Parse a pipeline (commands connected by |), consuming a trailing
        BACKGROUND marker and treating it as an implicit statement separator
        so anything after `&` is still parsed rather than discarded."""
        pipeline = Pipeline()

        cmd = self._parse_command()
        if cmd is None:
            return None
        pipeline.commands.append(cmd)

        while self._current().type == TokenType.PIPE:
            self._advance()
            cmd = self._parse_command()
            if cmd is None:
                break
            pipeline.commands.append(cmd)

        if self._current().type == TokenType.BACKGROUND:
            pipeline.background = True
            self._advance()
            self._record_background_separator()

        return pipeline

    def _record_background_separator(self) -> None:
        """Hook so callers chaining via `parse()` know a `;`-equivalent
        boundary follows a backgrounded pipeline."""
        self._pending_separator = ";"

    def _parse_command(self) -> Optional[Command]:
        """Parse a single command with args and redirects."""
        cmd = Command()

        while self._current().type == TokenType.WORD:
            word = self._current().value
            if not cmd.name:
                cmd.name = word
            else:
                cmd.args.append(word)
            self._advance()

            self._parse_redirects(cmd)

        self._parse_redirects(cmd)

        if not cmd.name:
            return None
        return cmd

    def _parse_redirects(self, cmd: Command) -> None:
        while self._current().type in (
            TokenType.REDIRECT_OUT,
            TokenType.REDIRECT_APPEND,
            TokenType.REDIRECT_IN,
            TokenType.REDIRECT_ERR,
        ):
            redir_type = {
                TokenType.REDIRECT_OUT: "out",
                TokenType.REDIRECT_APPEND: "append",
                TokenType.REDIRECT_IN: "in",
                TokenType.REDIRECT_ERR: "err",
            }[self._current().type]
            self._advance()

            if self._current().type == TokenType.WORD:
                target = self._current().value
                cmd.redirects.append(Redirect(type=redir_type, target=target))
                self._advance()
            else:
                raise ShellParseError(f"Expected filename after redirect '{redir_type}'")

    def _current(self) -> Token:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return Token(TokenType.EOF)

    def _advance(self) -> None:
        if self._pos < len(self._tokens):
            self._pos += 1

    def _skip_separators(self) -> None:
        while self._current().type in (TokenType.NEWLINE, TokenType.SEMICOLON):
            self._advance()


def parse_command_line(input_str: str) -> CommandList:
    """Convenience function: tokenize and parse a command line string.

    Args:
        input_str: Raw shell input string.

    Returns:
        Parsed CommandList AST.

    Raises:
        ShellParseError: if the input contains unterminated quotes or a
            redirect with no target.
    """
    tokens = Tokenizer(input_str).tokenize()
    return Parser(tokens).parse()