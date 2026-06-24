"""Tests for the VirtuxShell class."""

import pytest
from virtux.shell import VirtuxShell


@pytest.fixture
def shell(tmp_path):
    """Create a non-persistent shell for testing."""
    return VirtuxShell(persist=False, data_dir=str(tmp_path / ".virtux"))


class TestShellExecute:
    def test_execute_echo(self, shell):
        output = shell.execute("echo Hello")
        assert "Hello" in output

    def test_execute_pwd(self, shell):
        output = shell.execute("pwd")
        assert "/home/" in output

    def test_execute_pipeline(self, shell):
        shell.execute("echo 'line1\nline2\nline3' > /tmp/pipe_test.txt")
        output = shell.execute("cat /tmp/pipe_test.txt | grep line2")
        assert "line2" in output

    def test_execute_cd_and_pwd(self, shell):
        shell.execute("mkdir -p /tmp/testcd")
        shell.execute("cd /tmp/testcd")
        output = shell.execute("pwd")
        assert "/tmp/testcd" in output

    def test_execute_multiple_commands(self, shell):
        shell.execute("mkdir -p /home/testproject")
        shell.execute("touch /home/testproject/file.txt")
        output = shell.execute("ls /home/testproject")
        assert "file.txt" in output

    def test_execute_redirect(self, shell):
        shell.execute("echo 'Hello World' > /tmp/redirect_test.txt")
        output = shell.execute("cat /tmp/redirect_test.txt")
        assert "Hello World" in output


class TestShellReset:
    def test_reset_clears_files(self, shell):
        shell.execute("touch /tmp/willbegone.txt")
        shell.reset()
        output = shell.execute("ls /tmp")
        assert "willbegone.txt" not in output


class TestShellPersistence:
    def test_persistence_saves_and_loads(self, tmp_path):
        data_dir = str(tmp_path / ".virtux")

        shell1 = VirtuxShell(persist=True, data_dir=data_dir)
        shell1.execute("echo persisted > /tmp/persistent.txt")
        shell1._save_state()

        shell2 = VirtuxShell(persist=True, data_dir=data_dir)
        output = shell2.execute("cat /tmp/persistent.txt")
        assert "persisted" in output

    def test_virtux_home_env_var(self, tmp_path, monkeypatch):
        virtux_home = str(tmp_path / "custom_home")
        monkeypatch.setenv("VIRTUX_HOME", virtux_home)

        shell = VirtuxShell(persist=True)
        assert shell._data_dir == virtux_home

    def test_run_command_returns_shell_result(self, shell):
        result = shell.run("ls /nonexistent")
        assert result is not None
        assert result.stdout == ""
        assert "No such file or directory" in result.stderr
        assert result.exit_code != 0

