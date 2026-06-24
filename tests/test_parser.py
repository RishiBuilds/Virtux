"""Tests for the shell command parser."""

from virtux.parser import Tokenizer, TokenType, parse_command_line


class TestTokenizer:
    def test_simple_command(self):
        tokens = Tokenizer("ls -la").tokenize()
        words = [t for t in tokens if t.type == TokenType.WORD]
        assert len(words) == 2
        assert words[0].value == "ls"
        assert words[1].value == "-la"

    def test_pipe(self):
        tokens = Tokenizer("ls | grep test").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.PIPE in types

    def test_redirect_out(self):
        tokens = Tokenizer("echo hello > file.txt").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.REDIRECT_OUT in types

    def test_redirect_append(self):
        tokens = Tokenizer("echo hello >> file.txt").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.REDIRECT_APPEND in types

    def test_and_operator(self):
        tokens = Tokenizer("cmd1 && cmd2").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.AND in types

    def test_or_operator(self):
        tokens = Tokenizer("cmd1 || cmd2").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.OR in types

    def test_semicolon(self):
        tokens = Tokenizer("cmd1 ; cmd2").tokenize()
        types = [t.type for t in tokens if t.type != TokenType.EOF]
        assert TokenType.SEMICOLON in types

    def test_double_quotes(self):
        tokens = Tokenizer('echo "hello world"').tokenize()
        words = [t for t in tokens if t.type == TokenType.WORD]
        assert words[1].value == "hello world"

    def test_single_quotes(self):
        tokens = Tokenizer("echo 'hello world'").tokenize()
        words = [t for t in tokens if t.type == TokenType.WORD]
        assert words[1].value == "hello world"

    def test_escape(self):
        tokens = Tokenizer(r"echo hello\ world").tokenize()
        words = [t for t in tokens if t.type == TokenType.WORD]
        assert words[1].value == "hello world"

    def test_comment(self):
        tokens = Tokenizer("echo hello # this is a comment").tokenize()
        words = [t for t in tokens if t.type == TokenType.WORD]
        assert len(words) == 2
        assert words[0].value == "echo"
        assert words[1].value == "hello"

    def test_empty_input(self):
        tokens = Tokenizer("").tokenize()
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF


class TestParser:
    def test_simple_command(self):
        cmd_list = parse_command_line("ls -la /tmp")
        assert len(cmd_list.pipelines) == 1
        cmd = cmd_list.pipelines[0].commands[0]
        assert cmd.name == "ls"
        assert cmd.args == ["-la", "/tmp"]

    def test_pipeline(self):
        cmd_list = parse_command_line("ls | grep test | wc -l")
        assert len(cmd_list.pipelines) == 1
        pipeline = cmd_list.pipelines[0]
        assert len(pipeline.commands) == 3
        assert pipeline.commands[0].name == "ls"
        assert pipeline.commands[1].name == "grep"
        assert pipeline.commands[2].name == "wc"

    def test_redirect_out(self):
        cmd_list = parse_command_line("echo hello > output.txt")
        cmd = cmd_list.pipelines[0].commands[0]
        assert cmd.name == "echo"
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == "out"
        assert cmd.redirects[0].target == "output.txt"

    def test_redirect_in(self):
        cmd_list = parse_command_line("sort < input.txt")
        cmd = cmd_list.pipelines[0].commands[0]
        assert len(cmd.redirects) == 1
        assert cmd.redirects[0].type == "in"
        assert cmd.redirects[0].target == "input.txt"

    def test_and_operator(self):
        cmd_list = parse_command_line("cmd1 && cmd2")
        assert len(cmd_list.pipelines) == 2
        assert cmd_list.operators == ["&&"]

    def test_or_operator(self):
        cmd_list = parse_command_line("cmd1 || cmd2")
        assert len(cmd_list.pipelines) == 2
        assert cmd_list.operators == ["||"]

    def test_semicolon(self):
        cmd_list = parse_command_line("cmd1 ; cmd2 ; cmd3")
        assert len(cmd_list.pipelines) == 3
        assert cmd_list.operators == [";", ";"]

    def test_empty_input(self):
        cmd_list = parse_command_line("")
        assert len(cmd_list.pipelines) == 0

    def test_complex_command(self):
        cmd_list = parse_command_line("cat file.txt | grep error > errors.log && echo done")
        assert len(cmd_list.pipelines) == 2
        assert cmd_list.operators == ["&&"]
        # First pipeline 
        pipeline1 = cmd_list.pipelines[0]
        assert len(pipeline1.commands) == 2
        assert pipeline1.commands[0].name == "cat"
        assert pipeline1.commands[1].name == "grep"
        # Second pipeline
        assert cmd_list.pipelines[1].commands[0].name == "echo"
