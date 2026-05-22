"""Tests for the shadow-git snapshot engine — Parachute's bedrock.

These need a real git on PATH (they shell out to it); they skip cleanly if git
isn't available. The point they prove: we can snapshot and restore a working
tree WITHOUT ever creating or touching a real `.git`, and restore is undoable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from claude_parachute.snapshots import (
    ParachuteError,
    ShadowRepo,
    git_available,
)

pytestmark = pytest.mark.skipif(not git_available(), reason="git not on PATH")


def _write(p: Path, text: str):
    p.write_text(text, encoding="utf-8")


def repo(tmp_path) -> ShadowRepo:
    wt = tmp_path / "project"
    wt.mkdir()
    r = ShadowRepo(wt)
    r.init()
    return r


# -- the core safety guarantee: separate from the real .git --------------- #

def test_init_creates_shadow_not_real_git(tmp_path):
    r = repo(tmp_path)
    assert r.exists()
    assert (r.work_tree / ".parachute" / "snapshots.git").exists()
    assert not (r.work_tree / ".git").exists()   # the real repo is never created


def test_excludes_self_and_real_git(tmp_path):
    r = repo(tmp_path)
    # a real git repo + the parachute store should never be snapshotted
    (r.work_tree / ".git").mkdir()
    _write(r.work_tree / ".git" / "config", "x")
    _write(r.work_tree / "keep.txt", "hi")
    r.snapshot("first")
    tracked = r._git("ls-files").stdout
    assert "keep.txt" in tracked
    assert ".git/" not in tracked and ".parachute" not in tracked


# -- snapshot + restore --------------------------------------------------- #

def test_snapshot_and_restore_reverts_content(tmp_path):
    r = repo(tmp_path)
    f = r.work_tree / "a.txt"
    _write(f, "v1")
    sha1 = r.snapshot("first")
    _write(f, "v2")
    sha2 = r.snapshot("second")
    assert sha1 != sha2
    assert f.read_text(encoding="utf-8") == "v2"
    r.restore(sha1)
    assert f.read_text(encoding="utf-8") == "v1"   # reverted


def test_restore_brings_back_a_deleted_file(tmp_path):
    r = repo(tmp_path)
    f = r.work_tree / "gone.txt"
    _write(f, "important")
    sha = r.snapshot("has the file")
    f.unlink()                      # simulate `rm` via Bash
    assert not f.exists()
    r.restore(sha)
    assert f.exists() and f.read_text(encoding="utf-8") == "important"


def test_restore_is_undoable_takes_safety_snapshot(tmp_path):
    r = repo(tmp_path)
    f = r.work_tree / "a.txt"
    _write(f, "v1"); sha1 = r.snapshot("first")
    _write(f, "v2"); r.snapshot("second")
    before = len(r.list())
    res = r.restore(sha1)
    assert res.safety and res.restored == sha1
    assert len(r.list()) == before + 1   # the safety snapshot was recorded


def test_restore_does_not_delete_new_files(tmp_path):
    r = repo(tmp_path)
    _write(r.work_tree / "a.txt", "v1")
    sha1 = r.snapshot("first")
    newf = r.work_tree / "created_later.txt"
    _write(newf, "new work")
    r.snapshot("second")
    r.restore(sha1)
    # we never destroy files you made since — it's still here
    assert newf.exists()


def test_respects_gitignore(tmp_path):
    r = repo(tmp_path)
    _write(r.work_tree / ".gitignore", "secret.env\n")
    _write(r.work_tree / "secret.env", "TOKEN=abc")
    _write(r.work_tree / "code.py", "print(1)")
    r.snapshot("first")
    tracked = r._git("ls-files").stdout
    assert "code.py" in tracked
    assert "secret.env" not in tracked   # ignored files aren't captured


# -- list / resolve / errors ---------------------------------------------- #

def test_list_returns_snapshots_newest_first(tmp_path):
    r = repo(tmp_path)
    _write(r.work_tree / "a.txt", "1"); r.snapshot("one")
    _write(r.work_tree / "a.txt", "2"); r.snapshot("two")
    snaps = r.list()
    assert len(snaps) == 2
    assert snaps[0].label == "two"      # newest first
    assert snaps[0].short and len(snaps[0].short) == 8


def test_restore_unknown_ref_raises(tmp_path):
    r = repo(tmp_path)
    _write(r.work_tree / "a.txt", "1"); r.snapshot("one")
    with pytest.raises(ParachuteError):
        r.restore("deadbeef")


def test_list_empty_before_any_snapshot(tmp_path):
    r = repo(tmp_path)
    assert r.list() == []
