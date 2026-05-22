"""snapshots.py — the bedrock of Claude Parachute: a SHADOW git repo.

The whole safety promise rests here, so this is where we're careful. Parachute
keeps its own git repository at ``<project>/.parachute/snapshots.git`` whose
work-tree is the project root. It is completely separate from the user's real
``.git`` — different GIT_DIR — so we can snapshot and restore the working tree
without ever touching their index, branches, stashes, or history.

Why a shadow repo at all? Claude Code's native ``/rewind`` only tracks
Write/Edit edits; changes made through Bash (``rm``, ``sed -i``, ``>``,
``git reset --hard``, migrations) are invisible to it. Parachute commits the
*whole* tree after every tool, Bash included, so those are recoverable.

Safety guarantees:
  * We NEVER run git against the user's real repo — every command is pinned to
    our own GIT_DIR + GIT_WORK_TREE via environment, never inheriting theirs.
  * Restore takes a *safety snapshot first* (like Lifeboat), so recovery is
    undoable and we never lose the current state.
  * Restore only brings back the snapshot's files; it does NOT delete files you
    created since (those are preserved in the safety snapshot regardless). We
    never destroy user files.
  * We respect the project's ``.gitignore`` and additionally exclude ``.git/``
    and ``.parachute/`` so we never snapshot the real repo or our own store.
  * No console-window flash on Windows (CREATE_NO_WINDOW).

Pure stdlib + the ``git`` CLI. Keep it that way.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

__all__ = ["Snapshot", "ShadowRepo", "ParachuteError", "git_available"]

_CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0
_IDENTITY = ["-c", "user.email=parachute@local",
             "-c", "user.name=Claude Parachute",
             "-c", "commit.gpgsign=false"]


class ParachuteError(Exception):
    """Something went wrong we want to show the user kindly."""


@dataclass
class Snapshot:
    sha: str
    time: datetime
    label: str

    @property
    def short(self) -> str:
        return self.sha[:8]


def git_available() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True,
                       creationflags=_CREATE_NO_WINDOW)
        return True
    except (OSError, ValueError):
        return False


class ShadowRepo:
    """A git repo that shadows ``work_tree`` without touching its real ``.git``."""

    def __init__(self, work_tree, store_dir: Optional[Path] = None):
        self.work_tree = Path(work_tree).resolve()
        base = Path(store_dir) if store_dir is not None else self.work_tree / ".parachute"
        self.store_dir = base
        self.git_dir = base / "snapshots.git"

    # -- low-level ---------------------------------------------------------- #
    def _env(self) -> dict:
        env = dict(os.environ)
        # Pin git ENTIRELY to our shadow repo — never inherit the user's.
        env["GIT_DIR"] = str(self.git_dir)
        env["GIT_WORK_TREE"] = str(self.work_tree)
        env.pop("GIT_INDEX_FILE", None)
        return env

    def _git(self, *args, check: bool = True, identity: bool = False):
        cmd = ["git"] + (_IDENTITY if identity else []) + list(args)
        try:
            proc = subprocess.run(
                cmd, cwd=str(self.work_tree), env=self._env(),
                capture_output=True, text=True, creationflags=_CREATE_NO_WINDOW)
        except FileNotFoundError as exc:
            raise ParachuteError(
                "I couldn't find git. Parachute needs git installed and on PATH "
                "(grab it from https://git-scm.com/download/win)."
            ) from exc
        if check and proc.returncode != 0:
            raise ParachuteError(
                f"git {' '.join(args)} failed (exit {proc.returncode}): "
                f"{proc.stderr.strip() or proc.stdout.strip()}")
        return proc

    # -- lifecycle ---------------------------------------------------------- #
    def exists(self) -> bool:
        return self.git_dir.exists()

    def init(self) -> None:
        """Create the shadow repo if absent. Safe to call repeatedly."""
        if self.exists():
            return
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._git("init")
        # Never snapshot the real repo or our own store.
        info = self.git_dir / "info"
        info.mkdir(parents=True, exist_ok=True)
        (info / "exclude").write_text(".git/\n.parachute/\n", encoding="utf-8")

    # -- snapshots ---------------------------------------------------------- #
    def snapshot(self, label: str = "") -> str:
        """Stage the whole tree and commit it (allow-empty, so a checkpoint is
        recorded even when nothing changed). Returns the commit sha."""
        if not self.exists():
            self.init()
        label = (label or datetime.now().strftime("snapshot %Y-%m-%d %H:%M:%S")).replace("\n", " ")
        self._git("add", "-A")
        self._git("commit", "--allow-empty", "-m", label, identity=True)
        return self._git("rev-parse", "HEAD").stdout.strip()

    def has_changes(self) -> bool:
        """True if the work-tree differs from the latest snapshot (or there's no
        snapshot yet). Used so auto-snapshots only fire on real changes."""
        if not self.exists():
            return True
        self._git("add", "-A")
        proc = self._git("status", "--porcelain")
        return bool(proc.stdout.strip()) or self.current() is None

    def snapshot_if_changed(self, label: str = "") -> Optional[str]:
        """Snapshot only when something actually changed — the auto-snapshot
        path (keeps the shadow history from bloating with no-op commits)."""
        if not self.exists():
            self.init()
        if not self.has_changes():
            return None
        return self.snapshot(label)

    def current(self) -> Optional[str]:
        if not self.exists():
            return None
        proc = self._git("rev-parse", "HEAD", check=False)
        return proc.stdout.strip() if proc.returncode == 0 else None

    def list(self, limit: int = 50) -> List[Snapshot]:
        if not self.exists() or self.current() is None:
            return []
        out = self._git("log", f"-n{limit}",
                        "--pretty=format:%H%x1f%ct%x1f%s").stdout
        snaps: List[Snapshot] = []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts = line.split("\x1f")
            if len(parts) != 3:
                continue
            sha, ts, label = parts
            try:
                when = datetime.fromtimestamp(int(ts))
            except (ValueError, OSError):
                when = datetime.now()
            snaps.append(Snapshot(sha=sha, time=when, label=label))
        return snaps

    def resolve(self, ref: str) -> Optional[str]:
        """Turn a full/short sha (or HEAD~n) into a full sha, or None."""
        if not self.exists():
            return None
        proc = self._git("rev-parse", "--verify", f"{ref}^{{commit}}", check=False)
        return proc.stdout.strip() if proc.returncode == 0 else None

    # -- restore (the parachute cord) -------------------------------------- #
    def restore(self, ref: str) -> "RestoreResult":
        """Restore the working tree to a snapshot. Takes a SAFETY snapshot first
        (so this is undoable), then checks out the snapshot's files. Does NOT
        delete files created since — those live in the safety snapshot."""
        sha = self.resolve(ref)
        if not sha:
            raise ParachuteError(f"I couldn't find a snapshot matching '{ref}'.")
        safety = self.snapshot(f"safety: before restore to {sha[:8]}")
        # Restore tracked files from the snapshot into the work-tree.
        self._git("checkout", sha, "--", ".")
        return RestoreResult(restored=sha, safety=safety)


@dataclass
class RestoreResult:
    restored: str
    safety: str
