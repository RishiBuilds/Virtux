"""Tests for the command executor."""

import io
import pytest
from virtux.executor import Executor
from virtux.parser import parse_command_line
from virtux.registry import CommandRegistry
from virtux.filesystem import VirtualFS
from virtux.environment import EnvManager
from virtux.users import UserManager
from virtux.commands import register_all_commands


@pytest.fixture
def shell_env():
    """Create a complete shell environment for testing."""
    users = UserManager(default_username="testuser")
    env = EnvManager(username="testuser", hostname="virtux")
    fs = VirtualFS(owner="testuser", group="testuser")
    fs.setup_user_home("testuser", "testuser")
    registry = CommandRegistry()
    register_all_commands(registry)
    executor = Executor(registry, fs, env, users)
    return executor, registry, fs, env, users


def _exec(shell_env, command: str) -> tuple[str, str, int]:
    """Execute a command and return (stdout, stderr, exit_code)."""
    executor, _, _, _, _ = shell_env
    stdout = io.StringIO()
    stderr = io.StringIO()
    cmd_list = parse_command_line(command)
    exit_code = executor.execute(cmd_list, io.StringIO(), stdout, stderr)
    return stdout.getvalue(), stderr.getvalue(), exit_code


class TestSingleCommands:
    def test_echo(self, shell_env):
        out, _, code = _exec(shell_env, "echo Hello World")
        assert code == 0
        assert "Hello World" in out

    def test_pwd(self, shell_env):
        out, _, code = _exec(shell_env, "pwd")
        assert code == 0
        assert "/home/testuser" in out

    def test_whoami(self, shell_env):
        out, _, code = _exec(shell_env, "whoami")
        assert code == 0
        assert "testuser" in out

    def test_command_not_found(self, shell_env):
        _, err, code = _exec(shell_env, "nonexistentcommand")
        assert code == 127
        assert "command not found" in err


class TestPipeline:
    def test_echo_pipe_grep(self, shell_env):
        executor, _, fs, _, _ = shell_env
        # Create a file with content to grep
        fs.write_file("/tmp/test.txt", "line1\nline2\nline3\n")
        out, _, code = _exec(shell_env, "cat /tmp/test.txt | grep line2")
        assert code == 0
        assert "line2" in out

    def test_echo_pipe_wc(self, shell_env):
        executor, _, fs, _, _ = shell_env
        fs.write_file("/tmp/count.txt", "one\ntwo\nthree\n")
        out, _, code = _exec(shell_env, "cat /tmp/count.txt | wc -l")
        assert code == 0
        assert "3" in out


class TestRedirection:
    def test_redirect_out(self, shell_env):
        _, _, fs, _, _ = shell_env
        _exec(shell_env, "echo Hello > /tmp/output.txt")
        assert fs.exists("/tmp/output.txt")
        content = fs.read_text("/tmp/output.txt")
        assert "Hello" in content

    def test_redirect_append(self, shell_env):
        _, _, fs, _, _ = shell_env
        _exec(shell_env, "echo line1 > /tmp/append.txt")
        _exec(shell_env, "echo line2 >> /tmp/append.txt")
        content = fs.read_text("/tmp/append.txt")
        assert "line1" in content
        assert "line2" in content

    def test_redirect_in(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/input.txt", "banana\napple\ncherry\n")
        out, _, code = _exec(shell_env, "sort < /tmp/input.txt")
        assert code == 0
        lines = out.strip().split("\n")
        assert lines[0] == "apple"


class TestLogicalOperators:
    def test_and_success(self, shell_env):
        out, _, _ = _exec(shell_env, "echo first && echo second")
        assert "first" in out
        assert "second" in out

    def test_and_failure(self, shell_env):
        out, _, _ = _exec(shell_env, "nonexistent && echo should_not_appear")
        assert "should_not_appear" not in out

    def test_or_success(self, shell_env):
        out, _, _ = _exec(shell_env, "echo success || echo fallback")
        assert "success" in out
        assert "fallback" not in out

    def test_or_failure(self, shell_env):
        out, _, _ = _exec(shell_env, "nonexistent || echo fallback")
        assert "fallback" in out

    def test_semicolon(self, shell_env):
        out, _, _ = _exec(shell_env, "echo first ; echo second")
        assert "first" in out
        assert "second" in out


class TestVariableExpansion:
    def test_home_var(self, shell_env):
        out, _, _ = _exec(shell_env, "echo $HOME")
        assert "/home/testuser" in out

    def test_user_var(self, shell_env):
        out, _, _ = _exec(shell_env, "echo $USER")
        assert "testuser" in out


class TestFileCommands:
    def test_mkdir_and_ls(self, shell_env):
        _exec(shell_env, "mkdir /tmp/testdir")
        out, _, code = _exec(shell_env, "ls /tmp")
        assert code == 0
        assert "testdir" in out

    def test_touch_and_rm(self, shell_env):
        _, _, fs, _, _ = shell_env
        _exec(shell_env, "touch /tmp/removeme.txt")
        assert fs.exists("/tmp/removeme.txt")
        _exec(shell_env, "rm /tmp/removeme.txt")
        assert not fs.exists("/tmp/removeme.txt")

    def test_cp(self, shell_env):
        _, _, fs, _, _ = shell_env
        _exec(shell_env, "echo content > /tmp/src.txt")
        _exec(shell_env, "cp /tmp/src.txt /tmp/dst.txt")
        assert fs.read_text("/tmp/dst.txt").strip() == "content"

    def test_mv(self, shell_env):
        _, _, fs, _, _ = shell_env
        _exec(shell_env, "echo data > /tmp/move_src.txt")
        _exec(shell_env, "mv /tmp/move_src.txt /tmp/move_dst.txt")
        assert not fs.exists("/tmp/move_src.txt")
        assert fs.exists("/tmp/move_dst.txt")
