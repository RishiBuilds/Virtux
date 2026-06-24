"""Tests for the VirtualFS filesystem."""

import pytest
from virtux.filesystem import (
    VirtualFS,
    FileNotFoundError_,
    FileExistsError_,
    IsADirectoryError_,
    DirectoryNotEmptyError_,
)


@pytest.fixture
def fs():
    """Create a fresh VirtualFS instance."""
    vfs = VirtualFS(owner="testuser", group="testuser")
    vfs.setup_user_home("testuser", "testuser")
    return vfs


class TestBasicOperations:
    def test_root_exists(self, fs):
        assert fs.exists("/")
        assert fs.is_dir("/")

    def test_standard_dirs_exist(self, fs):
        for d in ["/bin", "/etc", "/home", "/tmp", "/usr", "/var"]:
            assert fs.exists(d), f"{d} should exist"
            assert fs.is_dir(d), f"{d} should be a directory"

    def test_home_setup(self, fs):
        assert fs.exists("/home/testuser")
        assert fs.exists("/home/testuser/.bashrc")
        assert fs.is_file("/home/testuser/.bashrc")

    def test_etc_files(self, fs):
        assert fs.is_file("/etc/hostname")
        content = fs.read_text("/etc/hostname")
        assert "virtux" in content


class TestFileOperations:
    def test_write_and_read(self, fs):
        fs.write_file("/tmp/test.txt", "Hello, World!")
        assert fs.exists("/tmp/test.txt")
        assert fs.read_text("/tmp/test.txt") == "Hello, World!"

    def test_write_bytes(self, fs):
        fs.write_file("/tmp/binary.bin", b"\x00\x01\x02")
        assert fs.read_file("/tmp/binary.bin") == b"\x00\x01\x02"

    def test_overwrite_file(self, fs):
        fs.write_file("/tmp/test.txt", "first")
        fs.write_file("/tmp/test.txt", "second")
        assert fs.read_text("/tmp/test.txt") == "second"

    def test_append_file(self, fs):
        fs.write_file("/tmp/test.txt", "line1\n")
        fs.append_file("/tmp/test.txt", "line2\n")
        assert fs.read_text("/tmp/test.txt") == "line1\nline2\n"

    def test_touch_creates_file(self, fs):
        fs.touch("/tmp/new.txt")
        assert fs.exists("/tmp/new.txt")
        assert fs.read_text("/tmp/new.txt") == ""

    def test_touch_updates_timestamp(self, fs):
        import time
        fs.write_file("/tmp/test.txt", "data")
        old_time = fs.get_node("/tmp/test.txt").modified_at
        time.sleep(0.01)
        fs.touch("/tmp/test.txt")
        new_time = fs.get_node("/tmp/test.txt").modified_at
        assert new_time >= old_time

    def test_read_nonexistent(self, fs):
        with pytest.raises(FileNotFoundError_):
            fs.read_file("/tmp/nonexistent.txt")


class TestDirectoryOperations:
    def test_mkdir(self, fs):
        fs.mkdir("/tmp/mydir", owner="testuser", group="testuser")
        assert fs.is_dir("/tmp/mydir")

    def test_mkdir_parents(self, fs):
        fs.mkdir("/tmp/a/b/c", parents=True, owner="testuser", group="testuser")
        assert fs.is_dir("/tmp/a")
        assert fs.is_dir("/tmp/a/b")
        assert fs.is_dir("/tmp/a/b/c")

    def test_mkdir_exists_error(self, fs):
        fs.mkdir("/tmp/mydir", owner="testuser", group="testuser")
        with pytest.raises(FileExistsError_):
            fs.mkdir("/tmp/mydir", owner="testuser", group="testuser")

    def test_rmdir_empty(self, fs):
        fs.mkdir("/tmp/empty", owner="testuser", group="testuser")
        fs.rmdir("/tmp/empty")
        assert not fs.exists("/tmp/empty")

    def test_rmdir_not_empty(self, fs):
        fs.mkdir("/tmp/notempty", owner="testuser", group="testuser")
        fs.write_file("/tmp/notempty/file.txt", "data")
        with pytest.raises(DirectoryNotEmptyError_):
            fs.rmdir("/tmp/notempty")

    def test_listdir(self, fs):
        fs.mkdir("/tmp/listtest", owner="testuser", group="testuser")
        fs.write_file("/tmp/listtest/a.txt", "a")
        fs.write_file("/tmp/listtest/b.txt", "b")
        entries = fs.listdir("/tmp/listtest")
        assert "a.txt" in entries
        assert "b.txt" in entries


class TestRemoveAndCopy:
    def test_remove_file(self, fs):
        fs.write_file("/tmp/delete_me.txt", "bye")
        fs.remove("/tmp/delete_me.txt")
        assert not fs.exists("/tmp/delete_me.txt")

    def test_remove_dir_non_recursive(self, fs):
        fs.mkdir("/tmp/mydir", owner="testuser", group="testuser")
        with pytest.raises(IsADirectoryError_):
            fs.remove("/tmp/mydir")

    def test_remove_dir_recursive(self, fs):
        fs.mkdir("/tmp/mydir", owner="testuser", group="testuser")
        fs.write_file("/tmp/mydir/file.txt", "data")
        fs.remove("/tmp/mydir", recursive=True)
        assert not fs.exists("/tmp/mydir")

    def test_copy_file(self, fs):
        fs.write_file("/tmp/original.txt", "content")
        fs.copy("/tmp/original.txt", "/tmp/copy.txt")
        assert fs.read_text("/tmp/copy.txt") == "content"

    def test_copy_dir_recursive(self, fs):
        fs.mkdir("/tmp/srcdir", owner="testuser", group="testuser")
        fs.write_file("/tmp/srcdir/file.txt", "data")
        fs.copy("/tmp/srcdir", "/tmp/dstdir", recursive=True)
        assert fs.is_dir("/tmp/dstdir")
        assert fs.read_text("/tmp/dstdir/file.txt") == "data"

    def test_move_file(self, fs):
        fs.write_file("/tmp/moveme.txt", "moving")
        fs.move("/tmp/moveme.txt", "/tmp/moved.txt")
        assert not fs.exists("/tmp/moveme.txt")
        assert fs.read_text("/tmp/moved.txt") == "moving"


class TestSymlinks:
    def test_create_symlink(self, fs):
        fs.write_file("/tmp/target.txt", "real content")
        fs.symlink("/tmp/target.txt", "/tmp/link.txt")
        assert fs.is_symlink("/tmp/link.txt")
        assert fs.read_text("/tmp/link.txt") == "real content"

    def test_symlink_exists_error(self, fs):
        fs.write_file("/tmp/exists.txt", "data")
        with pytest.raises(FileExistsError_):
            fs.symlink("/tmp/target", "/tmp/exists.txt")


class TestFind:
    def test_find_by_name(self, fs):
        fs.write_file("/tmp/test.txt", "data")
        fs.write_file("/tmp/test.log", "data")
        results = fs.find("/tmp", name_pattern="*.txt")
        assert "/tmp/test.txt" in results
        assert "/tmp/test.log" not in results

    def test_find_by_type(self, fs):
        fs.mkdir("/tmp/finddir", owner="testuser", group="testuser")
        fs.write_file("/tmp/finddir/file.txt", "data")
        dirs = fs.find("/tmp/finddir", node_type="dir")
        files = fs.find("/tmp/finddir", node_type="file")
        assert "/tmp/finddir/file.txt" in files
        assert "/tmp/finddir/file.txt" not in dirs


class TestPersistence:
    def test_save_and_load(self, fs, tmp_path):
        fs.write_file("/tmp/persist.txt", "saved data")
        save_path = str(tmp_path / "fs.json")
        fs.save(save_path)

        fs2 = VirtualFS()
        fs2.load(save_path)
        assert fs2.read_text("/tmp/persist.txt") == "saved data"

    def test_reset(self, fs):
        fs.write_file("/tmp/willbegone.txt", "data")
        fs.reset()
        assert not fs.exists("/tmp/willbegone.txt")
        assert fs.exists("/etc/hostname")  
