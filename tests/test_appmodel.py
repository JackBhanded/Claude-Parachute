"""Tests for the Qt-free appmodel — the brains the window paints over.

Git-backed actions (arm/snapshot/restore) skip if git is absent; the read-side
snapshot and hook toggling don't need git.
"""

from __future__ import annotations

import pytest

from claude_parachute.appmodel import ParachuteModel
from claude_parachute.snapshots import git_available

needs_git = pytest.mark.skipif(not git_available(), reason="git not on PATH")


@pytest.fixture
def model(tmp_path, monkeypatch):
    proj = tmp_path / "project"
    proj.mkdir()
    ch = tmp_path / "dot-claude"
    ch.mkdir()
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(ch))
    return ParachuteModel(work_tree=proj, claude_home=ch)


def test_snapshot_view_unarmed(model):
    snap = model.build_snapshot()
    assert snap.armed is False
    assert snap.count == 0
    assert snap.rows == []
    assert snap.hooks_on is False
    # Headline is friendly, never blank.
    assert snap.headline


def test_hook_toggle_roundtrip(model):
    assert model.set_hooks(True) is True
    assert model.build_snapshot().hooks_on is True
    assert model.set_hooks(False) is True
    assert model.build_snapshot().hooks_on is False


@needs_git
def test_arm_and_snapshot(model):
    assert model.arm() is True
    (model.repo.work_tree / "a.txt").write_text("v1", encoding="utf-8")
    assert model.take_snapshot("first") is True
    snap = model.build_snapshot()
    assert snap.armed is True
    assert snap.count == 1
    assert snap.rows[0].index == 1
    assert snap.rows[0].label == "first"


@needs_git
def test_restore_by_index_is_undoable(model):
    model.arm()
    f = model.repo.work_tree / "a.txt"
    f.write_text("v1", encoding="utf-8"); model.take_snapshot("one")
    f.write_text("v2", encoding="utf-8"); model.take_snapshot("two")
    # Newest-first: index 2 == "one" (v1).
    assert model.restore("2") is True
    assert f.read_text(encoding="utf-8") == "v1"
    # A safety snapshot of v2 was taken, so undo gets us back.
    assert "undoable" in model.last_message.lower()


@needs_git
def test_undo_needs_two(model):
    model.arm()
    (model.repo.work_tree / "a.txt").write_text("v1", encoding="utf-8")
    model.take_snapshot("only")
    assert model.undo() is False
