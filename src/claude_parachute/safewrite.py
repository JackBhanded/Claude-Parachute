"""safewrite.py — the one safe-file primitive Parachute needs.

Parachute's heavy lifting is the shadow-git engine; the only *user* file it edits
is ``~/.claude/settings.json`` (to install hooks). That edit must never leave a
half-written or lost settings file, so we use the same crash-safe atomic-write
discipline as the rest of the fleet: write to a temp file, fsync, atomically
``os.replace`` it into place, fsync the directory, and (optionally) keep a
timestamped backup first. Stdlib only.
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

__all__ = ["write_text_atomic"]


def _resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError:
        return path


def _fsync_dir(directory: Path) -> None:
    if os.name != "posix":
        return
    try:
        fd = os.open(str(directory), os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError:
        pass


def _atomic_write(path: Path, text: str) -> None:
    directory = path.parent
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".parachute.tmp", dir=str(directory))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
        _fsync_dir(directory)
    except BaseException:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise


def _make_backup(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.parent / f"{path.name}.{stamp}.bak"
    backup.write_bytes(path.read_bytes())
    return backup


def write_text_atomic(path, text: str, *, backup: bool = False) -> Optional[Path]:
    """Crash-safely write ``text`` to ``path`` (UTF-8, no BOM). Returns the
    timestamped backup path if ``backup=True`` and the file already existed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bak = _make_backup(path) if backup else None
    _atomic_write(_resolve(path), text)
    return bak
