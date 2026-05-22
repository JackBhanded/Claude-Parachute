"""Tests for the HTML dashboard. No git needed for the empty-state render; the
populated render skips if git is absent."""

from __future__ import annotations

import pytest

from claude_parachute.dashboard import render_dashboard_html, write_dashboard
from claude_parachute.snapshots import ShadowRepo, git_available

needs_git = pytest.mark.skipif(not git_available(), reason="git not on PATH")


def test_render_unarmed_is_valid_html(tmp_path):
    repo = ShadowRepo(tmp_path / "project")
    html = render_dashboard_html(repo)
    assert html.startswith("<!DOCTYPE html>")
    assert "Claude Parachute" in html
    assert "No snapshots yet" in html
    # The real Claude logo path must be present and intact (one long path).
    assert "M4.709 15.955" in html
    # Light/dark toggle wired up.
    assert "toggleTheme" in html


@needs_git
def test_write_dashboard_with_snapshots(tmp_path):
    proj = tmp_path / "project"
    proj.mkdir()
    repo = ShadowRepo(proj)
    repo.init()
    (proj / "a.txt").write_text("hi", encoding="utf-8")
    repo.snapshot("first checkpoint")
    out = write_dashboard(repo)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "first checkpoint" in text
    assert "Snapshot timeline" in text
