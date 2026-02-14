from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def atomic_replace(src_tmp: Path, dst: Path) -> None:
    # os.replace is atomic on POSIX when src and dst are on same filesystem.
    os.replace(src_tmp, dst)


def copy_bytes(src: Path, dst: Path) -> None:
    ensure_parent_dir(dst)
    shutil.copyfile(src, dst)


def preserve_stat(src: Path, dst: Path, *, preserve_times: bool, preserve_perms: bool) -> None:
    st = src.stat()
    if preserve_perms:
        os.chmod(dst, st.st_mode)
    if preserve_times:
        os.utime(dst, (st.st_atime, st.st_mtime))


def strip_xattrs(path: Path) -> tuple[str, ...]:
    # Works on macOS/Linux. On Windows, these functions may not exist.
    listxattr = getattr(os, "listxattr", None)
    removexattr = getattr(os, "removexattr", None)
    if listxattr is None or removexattr is None:
        return ()

    removed: list[str] = []
    try:
        names = listxattr(path, follow_symlinks=False)
    except OSError:
        return ()

    for name in names:
        try:
            removexattr(path, name, follow_symlinks=False)
            removed.append(name)
        except OSError:
            # Best-effort; leave what we can't remove.
            pass

    return tuple(removed)


class TempPath:
    """Context manager for a temp file path.

    Creates a temp file in the same directory as the intended destination to keep
    atomic replace possible.
    """

    def __init__(self, dst: Path):
        self._dst = dst
        self.path: Path | None = None

    def __enter__(self) -> Path:
        ensure_parent_dir(self._dst)
        fd, p = tempfile.mkstemp(prefix=f".{self._dst.name}.", suffix=".tmp", dir=str(self._dst.parent))
        os.close(fd)
        self.path = Path(p)
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.path is None:
            return
        try:
            if self.path.exists():
                self.path.unlink()
        except OSError:
            pass
