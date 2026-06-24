"""Legacy compatibility wrapper for VirtualFileSystem."""

from __future__ import annotations

from virtux.core.filesystem import (
    FSNode as FSNode,
    VirtualFileSystem as VirtualFS,
    VirtualFSError as VirtualFSError,
    VirtualFileSystemError as VirtualFileSystemError,
    FileNotFoundError_ as FileNotFoundError_,
    FileExistsError_ as FileExistsError_,
    NotADirectoryError_ as NotADirectoryError_,
    IsADirectoryError_ as IsADirectoryError_,
    PermissionError_ as PermissionError_,
    DirectoryNotEmptyError_ as DirectoryNotEmptyError_,
)

__all__ = [
    "FSNode",
    "VirtualFS",
    "VirtualFSError",
    "VirtualFileSystemError",
    "FileNotFoundError_",
    "FileExistsError_",
    "NotADirectoryError_",
    "IsADirectoryError_",
    "PermissionError_",
    "DirectoryNotEmptyError_",
]
