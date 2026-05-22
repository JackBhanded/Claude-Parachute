"""appmodel.py — the Qt-free brains behind the Parachute window.

All the logic the desktop app needs lives here, with no PySide6 import, so it
can be unit-tested without a display. ``app.py`` is a thin Qt shell over this:
it reads a :class:`Snapshot` (an immutable view of the safety net right now) and
calls the action methods (take a checkpoint, pull the cord, toggle auto-snap).

Everything routes through :class:`~claude_parachute.snapshots.ShadowRepo` and
``hookconfig`` so the app and the CLI can never drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .hookconfig import (
    claude_code_home,
    hooks_installed,
    install_hooks,
    uninstall_hooks,
)
from .snapshots import ParachuteError, ShadowRepo, Snapshot, git_available

__all__ = ["SnapRow", "AppSnapshot", "ParachuteModel"]


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


@dataclass(frozen=True)
class SnapRow:
    """One line in the timeline — display-ready, no git knowledge needed."""
    index: int          # 1-based, newest first (matches `parachute restore N`)
    sha: str
    short: str
    label: str
    when: str           # pre-formatted, friendly


@dataclass(frozen=True)
class AppSnapshot:
    """An immutable picture of the safety net, for the UI to render."""
    project: str
    git_ok: bool
    armed: bool
    hooks_on: bool
    count: int
    size_mb: float
    rows: List[SnapRow] = field(default_factory=list)
    taken_at: str = ""

    @property
    def latest(self) -> Optional[SnapRow]:
        return self.rows[0] if self.rows else None

    @property
    def headline(self) -> str:
        if not self.git_ok:
            return "git isn't installed — Parachute needs it"
        if not self.armed:
            return "Not armed yet — arm it to start the safety net"
        if self.hooks_on:
            return "Armed & auto-snapping — you're covered"
        return "Armed — turn on auto-snap for hands-free cover"


class ParachuteModel:
    """The app's controller. Wraps a ShadowRepo for one project."""

    def __init__(self, work_tree=None, claude_home: Optional[Path] = None):
        self.repo = ShadowRepo(work_tree or Path.cwd())
        self.claude_home = Path(claude_home) if claude_home else claude_code_home()
        self.last_message = ""

    # -- read --------------------------------------------------------------- #
    def build_snapshot(self, limit: int = 60) -> AppSnapshot:
        git_ok = git_available()
        armed = self.repo.exists()
        snaps: List[Snapshot] = self.repo.list(limit) if armed else []
        rows: List[SnapRow] = []
        for i, s in enumerate(snaps, 1):
            when = s.time.strftime("%a %d %b %I:%M %p").lstrip("0")
            rows.append(SnapRow(index=i, sha=s.sha, short=s.short,
                                label=s.label or "snapshot", when=when))
        size_mb = round(_dir_size(self.repo.store_dir) / (1024 * 1024), 1) if armed else 0.0
        return AppSnapshot(
            project=str(self.repo.work_tree),
            git_ok=git_ok,
            armed=armed,
            hooks_on=hooks_installed(self.claude_home),
            count=len(snaps),
            size_mb=size_mb,
            rows=rows,
            taken_at=datetime.now().strftime("%a %d %b %I:%M %p").lstrip("0"),
        )

    # -- actions ------------------------------------------------------------ #
    def arm(self) -> bool:
        """Create the shadow repo. Returns True on success."""
        if not git_available():
            self.last_message = ("Parachute needs git installed and on PATH. "
                                 "Grab it from git-scm.com/download/win.")
            return False
        try:
            self.repo.init()
        except ParachuteError as exc:
            self.last_message = str(exc)
            return False
        self.last_message = "Parachute is armed. Your work has a net now."
        return True

    def take_snapshot(self, label: str = "manual checkpoint") -> bool:
        try:
            sha = self.repo.snapshot(label)
        except ParachuteError as exc:
            self.last_message = str(exc)
            return False
        self.last_message = f"Checkpoint saved ({sha[:8]}). Breathe easy."
        return True

    def restore(self, ref: str) -> bool:
        """Pull the cord. ``ref`` is a 1-based index, sha, or HEAD~n."""
        try:
            sha = self._resolve_ref(ref)
            res = self.repo.restore(sha)
        except ParachuteError as exc:
            self.last_message = str(exc)
            return False
        self.last_message = (f"Pulled the cord — restored to {res.restored[:8]}. "
                            f"Your prior state is safe in {res.safety[:8]}, so this "
                            "is undoable.")
        return True

    def undo(self) -> bool:
        if not self.repo.exists() or self.repo.resolve("HEAD~1") is None:
            self.last_message = "Nothing to undo yet (need at least two snapshots)."
            return False
        try:
            res = self.repo.restore("HEAD~1")
        except ParachuteError as exc:
            self.last_message = str(exc)
            return False
        self.last_message = (f"Undone — back to the snapshot before the last change "
                            f"({res.restored[:8]}).")
        return True

    def set_hooks(self, on: bool) -> bool:
        res = install_hooks(self.claude_home) if on else uninstall_hooks(self.claude_home)
        self.last_message = res.message
        return res.ok

    def _resolve_ref(self, ref: str) -> str:
        ref = str(ref)
        if ref.isdigit():
            snaps = self.repo.list()
            i = int(ref)
            if 1 <= i <= len(snaps):
                return snaps[i - 1].sha
        return ref
