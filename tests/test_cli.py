"""Tests for the parachute CLI. Repo commands need git (skip if absent); the
hook-install commands don't."""

from __future__ import annotations

from pathlib import Path

import pytest

from claude_parachute.cli import main
from claude_parachute.snapshots import ShadowRepo, git_available

needs_git = pytest.mark.skipif(not git_available(), reason="git not on PATH")


@pytest.fixture
def env(tmp_path, monkeypatch):
    proj = tmp_path / "project"
    proj.mkdir()
    ch = tmp_path / "dot-claude"
    ch.mkdir()
    monkeypatch.chdir(proj)                       # cwd = the project (shadow lives here)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(ch))
    return {"proj": proj, "ch": ch}


# -- hooks (no git needed) ------------------------------------------------ #

def test_install_and_uninstall_hooks(env, capsys):
    assert main(["install-hooks"]) == 0
    sp = env["ch"] / "settings.json"
    assert "claude_parachute" in sp.read_text(encoding="utf-8")
    assert main(["uninstall-hooks"]) == 0
    assert "claude_parachute" not in sp.read_text(encoding="utf-8")


def test_status_runs(env, capsys):
    assert main(["status"]) == 0
    assert "status" in capsys.readouterr().out.lower()


# -- repo ops (need git) -------------------------------------------------- #

@needs_git
def test_init_creates_shadow(env, capsys):
    assert main(["init"]) == 0
    assert (env["proj"] / ".parachute" / "snapshots.git").exists()
    assert not (env["proj"] / ".git").exists()


@needs_git
def test_snapshot_list_restore_cycle(env, capsys):
    main(["init"])
    f = env["proj"] / "a.txt"
    f.write_text("v1", encoding="utf-8")
    main(["snapshot", "-m", "first"])
    f.write_text("v2", encoding="utf-8")
    main(["snapshot", "-m", "second"])
    capsys.readouterr()
    assert main(["list"]) == 0
    out = capsys.readouterr().out
    assert "first" in out and "second" in out
    # restore the older one (index 2 = "first", newest-first ordering)
    assert main(["restore", "2"]) == 0
    assert f.read_text(encoding="utf-8") == "v1"


@needs_git
def test_undo(env, capsys):
    main(["init"])
    f = env["proj"] / "a.txt"
    f.write_text("v1", encoding="utf-8"); main(["snapshot", "-m", "one"])
    f.write_text("v2", encoding="utf-8"); main(["snapshot", "-m", "two"])
    capsys.readouterr()
    assert main(["undo"]) == 0
    assert f.read_text(encoding="utf-8") == "v1"


@needs_git
def test_snapshot_hook_snapshots_cwd(env, capsys):
    main(["init"])
    (env["proj"] / "a.txt").write_text("hello", encoding="utf-8")
    assert main(["snapshot-hook"]) == 0     # no stdin -> uses cwd
    snaps = ShadowRepo(env["proj"]).list()
    assert len(snaps) >= 1


@needs_git
def test_undo_needs_two_snapshots(env, capsys):
    main(["init"])
    (env["proj"] / "a.txt").write_text("v1", encoding="utf-8")
    main(["snapshot", "-m", "only"])
    capsys.readouterr()
    assert main(["undo"]) == 1   # nothing before the first snapshot
