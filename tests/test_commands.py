"""Tests for built-in commands."""

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
    executor, _, _, _, _ = shell_env
    stdout = io.StringIO()
    stderr = io.StringIO()
    cmd_list = parse_command_line(command)
    exit_code = executor.execute(cmd_list, io.StringIO(), stdout, stderr)
    return stdout.getvalue(), stderr.getvalue(), exit_code


class TestTextCommands:
    def test_cat(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/cat.txt", "Hello\nWorld\n")
        out, _, code = _exec(shell_env, "cat /tmp/cat.txt")
        assert code == 0
        assert "Hello" in out
        assert "World" in out

    def test_head(self, shell_env):
        _, _, fs, _, _ = shell_env
        lines = "\n".join(f"line{i}" for i in range(20))
        fs.write_file("/tmp/head.txt", lines)
        out, _, code = _exec(shell_env, "head -n 5 /tmp/head.txt")
        assert code == 0
        assert "line0" in out
        assert "line4" in out
        assert "line5" not in out

    def test_tail(self, shell_env):
        _, _, fs, _, _ = shell_env
        lines = "\n".join(f"line{i}" for i in range(20))
        fs.write_file("/tmp/tail.txt", lines)
        out, _, code = _exec(shell_env, "tail -n 3 /tmp/tail.txt")
        assert code == 0
        assert "line19" in out
        assert "line17" in out

    def test_grep(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/grep.txt", "apple\nbanana\ncherry\napricot\n")
        out, _, code = _exec(shell_env, "grep ap /tmp/grep.txt")
        assert code == 0
        assert "apple" in out
        assert "apricot" in out
        assert "banana" not in out

    def test_grep_case_insensitive(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/grep_i.txt", "Apple\nBANANA\ncherry\n")
        out, _, code = _exec(shell_env, "grep -i apple /tmp/grep_i.txt")
        assert code == 0
        assert "Apple" in out

    def test_grep_invert(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/grep_v.txt", "apple\nbanana\ncherry\n")
        out, _, code = _exec(shell_env, "grep -v apple /tmp/grep_v.txt")
        assert code == 0
        assert "banana" in out
        assert "cherry" in out
        assert "apple" not in out

    def test_wc(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/wc.txt", "one two\nthree four five\n")
        out, _, code = _exec(shell_env, "wc /tmp/wc.txt")
        assert code == 0

    def test_sort(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/sort.txt", "banana\napple\ncherry\n")
        out, _, code = _exec(shell_env, "sort /tmp/sort.txt")
        assert code == 0
        lines = out.strip().split("\n")
        assert lines == ["apple", "banana", "cherry"]

    def test_sort_reverse(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/sort_r.txt", "a\nb\nc\n")
        out, _, code = _exec(shell_env, "sort -r /tmp/sort_r.txt")
        assert code == 0
        lines = out.strip().split("\n")
        assert lines == ["c", "b", "a"]

    def test_echo_no_newline(self, shell_env):
        out, _, _ = _exec(shell_env, "echo -n hello")
        assert out == "hello"  

    def test_echo_escape(self, shell_env):
        out, _, _ = _exec(shell_env, r"echo -e hello\nworld")
        assert "hello" in out
        assert "world" in out

    def test_sed_substitution(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/sed.txt", "hello world\nhello there\n")
        out, _, code = _exec(shell_env, "sed s/hello/goodbye/ /tmp/sed.txt")
        assert code == 0
        assert "goodbye world" in out
        assert "goodbye there" in out


class TestSystemCommands:
    def test_uname(self, shell_env):
        out, _, code = _exec(shell_env, "uname")
        assert code == 0
        assert "Linux" in out

    def test_uname_all(self, shell_env):
        out, _, code = _exec(shell_env, "uname -a")
        assert code == 0
        assert "Linux" in out
        assert "virtux" in out

    def test_hostname(self, shell_env):
        out, _, code = _exec(shell_env, "hostname")
        assert code == 0
        assert "virtux" in out

    def test_date(self, shell_env):
        out, _, code = _exec(shell_env, "date")
        assert code == 0
        assert len(out.strip()) > 0

    def test_env(self, shell_env):
        out, _, code = _exec(shell_env, "env")
        assert code == 0
        assert "HOME=" in out
        assert "USER=" in out

    def test_export(self, shell_env):
        _, _, _, env, _ = shell_env
        _exec(shell_env, "export MY_VAR=hello")
        assert env.get("MY_VAR") == "hello"

    def test_unset(self, shell_env):
        _, _, _, env, _ = shell_env
        env.set("TEMP_VAR", "value")
        _exec(shell_env, "unset TEMP_VAR")
        assert env.get("TEMP_VAR") is None

    def test_which(self, shell_env):
        out, _, code = _exec(shell_env, "which ls")
        assert code == 0
        assert "/usr/bin/ls" in out

    def test_id(self, shell_env):
        out, _, code = _exec(shell_env, "id")
        assert code == 0
        assert "uid=" in out
        assert "testuser" in out

    def test_true_false(self, shell_env):
        _, _, code = _exec(shell_env, "true")
        assert code == 0
        _, _, code = _exec(shell_env, "false")
        assert code == 1


class TestPermissionCommands:
    def test_chmod(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/perm.txt", "data")
        _exec(shell_env, "chmod 755 /tmp/perm.txt")
        node = fs.get_node("/tmp/perm.txt")
        assert node.permissions == 0o755

    def test_chmod_symbolic(self, shell_env):
        _, _, fs, _, _ = shell_env
        fs.write_file("/tmp/sym.txt", "data")
        fs.chmod("/tmp/sym.txt", 0o644)
        _exec(shell_env, "chmod u+x /tmp/sym.txt")
        node = fs.get_node("/tmp/sym.txt")
        assert node.permissions & 0o100  


class TestNetworkCommands:
    def test_ping(self, shell_env):
        out, _, code = _exec(shell_env, "ping -c 2 localhost")
        assert code == 0
        assert "PING localhost" in out
        assert "icmp_seq=1" in out

    def test_ifconfig(self, shell_env):
        out, _, code = _exec(shell_env, "ifconfig")
        assert code == 0
        assert "eth0" in out

    def test_curl(self, shell_env):
        out, _, code = _exec(shell_env, "curl http://example.com")
        assert code == 0
        assert "Simulated" in out


class TestHelp:
    def test_help_command(self, shell_env):
        out, _, code = _exec(shell_env, "help")
        assert code == 0
        assert "File System" in out
        assert "ls" in out

    def test_man_command(self, shell_env):
        out, _, code = _exec(shell_env, "man ls")
        assert code == 0
        assert "LS" in out
        assert "SYNOPSIS" in out
