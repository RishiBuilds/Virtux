"""Regression tests from the Virtux repository audit checklist."""

from __future__ import annotations

import io
import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from virtux.core.environment import Environment
from virtux.core.executor import Executor
from virtux.core.filesystem import (
    DirectoryNotEmptyError_,
    SymlinkLoopError_,
    VirtualFileSystem,
    PermissionError_,
)
from virtux.core.parser import _tokenize
from virtux.core.registry import get_command
from virtux.core.shell import Shell
from virtux.users import UserManager


@pytest.fixture
def live_env():
    """Executor using the live run_line() parser+registry path."""
    users = UserManager(default_username="testuser")
    env = Environment(user="testuser", hostname="virtux")
    fs = VirtualFileSystem(owner="testuser", group="testuser")
    fs.setup_user_home("testuser", "testuser")
    executor = Executor(fs, env, users=users)
    return executor, fs, env


def _run(executor: Executor, command: str) -> tuple[str, str, int]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with patch.object(sys, "stdin", io.StringIO()), patch.object(
        sys, "stdout", stdout
    ), patch.object(sys, "stderr", stderr):
        code = executor.run_line(command)
    return stdout.getvalue(), stderr.getvalue(), code


class TestLiveLogicalOperators:
    def test_false_and_blocks(self, live_env):
        executor, _, _ = live_env
        out, _, code = _run(executor, "false && echo should-not-print")
        assert "should-not-print" not in out
        assert code != 0

    def test_true_or_blocks(self, live_env):
        executor, _, _ = live_env
        out, _, code = _run(executor, "true || echo should-not-print")
        assert "should-not-print" not in out
        assert code == 0


class TestRedirectsAndBackground:
    def test_err_append_redirect(self, live_env):
        executor, fs, _ = live_env
        _run(executor, "ls /definitely-missing-1 2>/tmp/err.log")
        _run(executor, "ls /definitely-missing-2 2>>/tmp/err.log")
        content = fs.read_text("/tmp/err.log")
        assert "definitely-missing-1" in content
        assert "definitely-missing-2" in content

    def test_ampersand_redirect(self, live_env):
        executor, fs, _ = live_env
        _run(executor, "echo both 1>&2 2>&1 &> /tmp/combined.log")
        content = fs.read_text("/tmp/combined.log")
        assert "both" in content

    def test_background_does_not_drop_following_command(self, live_env):
        executor, _, _ = live_env
        out, _, _ = _run(executor, "echo bg & echo fg")
        assert "bg" in out
        assert "fg" in out

    def test_tokenizer_recognizes_err_append(self):
        tokens = _tokenize("cmd 2>> /tmp/log")
        assert "2>>" in tokens


class TestAliasExpansion:
    def test_alias_in_semicolon_chain(self, live_env):
        executor, _, env = live_env
        env.aliases["ll"] = "echo alias-ran"
        out, _, _ = _run(executor, "true; ll")
        assert "alias-ran" in out

    def test_alias_in_and_chain(self, live_env):
        executor, _, env = live_env
        env.aliases["ll"] = "echo alias-ran"
        out, _, _ = _run(executor, "true && ll")
        assert "alias-ran" in out


class TestFilesystemSemantics:
    def test_umask_does_not_reset_tree(self):
        fs = VirtualFileSystem()
        fs.write_file("/tmp/keepme.txt", "data")
        fs.umask = 0o077
        assert fs.exists("/tmp/keepme.txt")

    def test_write_file_preserves_metadata_on_overwrite(self):
        fs = VirtualFileSystem(owner="alice", group="alice")
        fs.set_access_context("alice", ["alice"], enforce=False)
        fs.write_file("/tmp/meta.txt", "v1", owner="alice", permissions=0o600)
        created = fs.get_node("/tmp/meta.txt").created_at
        fs.set_access_context("alice", ["alice"], enforce=True)
        fs.write_file("/tmp/meta.txt", "v2")
        node = fs.get_node("/tmp/meta.txt")
        assert node.owner == "alice"
        assert node.permissions == 0o600
        assert node.created_at == created

    def test_rename_refuses_nonempty_destination_dir(self):
        fs = VirtualFileSystem()
        fs.set_access_context("root", ["root"], enforce=False)
        fs.makedirs("/tmp/parent")
        fs.makedirs("/tmp/parent/collision")
        fs.write_file("/tmp/parent/collision/f.txt", "x")
        fs.makedirs("/tmp/collision")
        fs.set_access_context("root", ["root"], enforce=True)
        with pytest.raises(DirectoryNotEmptyError_):
            fs.rename("/tmp/collision", "/tmp/parent")

    def test_symlink_loop_raises_clean_error(self):
        fs = VirtualFileSystem()
        fs.set_access_context("root", ["root"], enforce=False)
        fs.symlink("/tmp/a", "/tmp/a")
        fs.set_access_context("root", ["root"], enforce=True)
        with pytest.raises(SymlinkLoopError_):
            fs.read_file("/tmp/a")

    def test_path_traversal_stays_in_virtual_tree(self):
        fs = VirtualFileSystem()
        fs.set_access_context("root", ["root"], enforce=False)
        fs.write_file("/etc/secret", "top-secret", owner="root", permissions=0o600)
        fs.set_access_context("testuser", ["testuser"], enforce=True)
        escaped = fs.normalize("../../../etc/secret", "/home/testuser")
        assert escaped == "/etc/secret"
        assert fs.exists(escaped)
        with pytest.raises(PermissionError_):
            fs.read_file(escaped)


class TestRegistryHelpText:
    def test_cat_has_registered_description(self):
        cmd = get_command("cat")
        assert cmd is not None
        assert cmd.description != ""
        assert "Concatenate" in cmd.description


class TestNoPersist:
    def test_no_persist_skips_load_and_save(self, tmp_path, monkeypatch):
        persist_file = tmp_path / "virtux_state.json"
        persist_file.write_text('{"fs": {"name": "/", "is_dir": true, "children": {}}}', encoding="utf-8")
        monkeypatch.setenv("VIRTUX_HOME", str(tmp_path))

        shell = Shell(persist_path=None)
        assert shell._persist_enabled is False
        assert shell.persist_path is None
        assert shell.fs.exists("/etc/hostname")

        shell.fs.write_file("/tmp/ephemeral.txt", "gone")
        shell._save_state()
        assert not persist_file.exists() or "ephemeral" not in persist_file.read_text(encoding="utf-8")


class TestHistory:
    def test_repl_adds_history(self, live_env):
        executor, _, env = live_env
        _run(executor, "echo tracked")
        assert any("tracked" in line for line in env.history)


class TestUserSanitization:
    def test_reserved_username_is_sanitized(self, capsys):
        um = UserManager(default_username="root")
        assert um.current_user == "user"
        captured = capsys.readouterr()
        assert "reserved" in captured.err.lower()

    def test_windows_like_username_is_sanitized(self):
        um = UserManager(default_username="Rishi Build")
        assert um.current_user == "rishi_build"
        assert " " not in um.current_user


class TestPluginErrors:
    def test_plugin_import_failure_is_reported(self, capsys):
        from virtux.plugins import discover_plugins
        from virtux.registry import CommandRegistry

        registry = CommandRegistry()
        mock_ep = MagicMock()
        mock_ep.name = "broken"
        mock_ep.load.side_effect = ImportError("boom")

        with patch("importlib.metadata.entry_points", return_value=[mock_ep]):
            loaded = discover_plugins(registry)

        assert loaded == []
        assert "failed to import" in capsys.readouterr().err


class TestPersistenceSafety:
    def test_malformed_state_file_does_not_crash(self, tmp_path, monkeypatch, capsys):
        data_dir = tmp_path / "virtux"
        data_dir.mkdir()
        state = data_dir / "virtux_state.json"
        state.write_text("{not valid json", encoding="utf-8")
        monkeypatch.setenv("VIRTUX_HOME", str(data_dir))

        shell = Shell()
        assert shell.fs.exists("/etc/hostname")
        assert "could not load" in capsys.readouterr().err.lower()

    def test_state_uses_json_not_eval(self, tmp_path):
        fs = VirtualFileSystem()
        fs.set_access_context("root", ["root"], enforce=False)
        fs.write_file("/tmp/x", "y")
        path = tmp_path / "state.json"
        fs.save(str(path))
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
