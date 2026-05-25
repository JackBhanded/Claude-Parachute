"""Tests for hookconfig.py — safely editing ~/.claude/settings.json (no git needed)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from claude_parachute.hookconfig import (
    HOOK_TAG,
    _command_is_ours,
    hook_command,
    hooks_installed,
    install_hooks,
    settings_path,
    uninstall_hooks,
)

# The exact shape the packaged build registers (space + capitals, no underscore).
EXE_CMD = r'"C:\Users\Jack\AppData\Local\Programs\Claude Parachute\Claude Parachute.exe" snapshot-hook'


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_install_adds_both_events(tmp_path):
    res = install_hooks(tmp_path, command='"py" -m claude_parachute snapshot-hook')
    assert res.status == "installed"
    hooks = read(settings_path(tmp_path))["hooks"]
    for event in ("PostToolUse", "SessionStart"):
        assert event in hooks
        assert any(HOOK_TAG in h["command"] for g in hooks[event] for h in g["hooks"])


def test_install_idempotent(tmp_path):
    c = '"py" -m claude_parachute snapshot-hook'
    install_hooks(tmp_path, command=c)
    assert install_hooks(tmp_path, command=c).status == "unchanged"


def test_install_preserves_existing(tmp_path):
    sp = settings_path(tmp_path)
    sp.write_text(json.dumps({
        "model": "opus",
        "hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "echo hi"}]}]},
    }), encoding="utf-8")
    install_hooks(tmp_path, command='"py" -m claude_parachute snapshot-hook')
    data = read(sp)
    assert data["model"] == "opus"
    cmds = [h["command"] for g in data["hooks"]["PostToolUse"] for h in g["hooks"]]
    assert "echo hi" in cmds and any(HOOK_TAG in c for c in cmds)


def test_install_refuses_invalid_json(tmp_path):
    sp = settings_path(tmp_path)
    sp.write_text("{ not json", encoding="utf-8")
    res = install_hooks(tmp_path)
    assert res.status == "refused" and res.ok is False
    assert sp.read_text(encoding="utf-8") == "{ not json"


def test_uninstall_removes_only_ours(tmp_path):
    sp = settings_path(tmp_path)
    sp.write_text(json.dumps({
        "hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "echo hi"}]}]},
    }), encoding="utf-8")
    install_hooks(tmp_path, command='"py" -m claude_parachute snapshot-hook')
    assert uninstall_hooks(tmp_path).status == "removed"
    data = read(sp)
    cmds = [h["command"] for g in data["hooks"].get("PostToolUse", []) for h in g["hooks"]]
    assert "echo hi" in cmds and not any(HOOK_TAG in c for c in cmds)
    assert "SessionStart" not in data.get("hooks", {})   # ours fully cleaned up


def test_hooks_installed_flag(tmp_path):
    assert hooks_installed(tmp_path) is False
    install_hooks(tmp_path, command='"py" -m claude_parachute snapshot-hook')
    assert hooks_installed(tmp_path) is True


def test_hook_command_quotes_python():
    cmd = hook_command(python="/path with space/python")
    assert cmd.startswith('"/path with space/python"') and "snapshot-hook" in cmd


# --- regression: the "window storm" bug ---------------------------------------
# When Parachute ran as the packaged .exe, the hook was registered as
# '"...\Claude Parachute.exe" snapshot-hook' — which does NOT contain the literal
# "claude_parachute". The old matcher missed it, so uninstall couldn't remove it
# and install kept stacking duplicates → a window opened on every tool use.

def test_command_matcher_recognises_both_forms():
    assert _command_is_ours('"py" -m claude_parachute snapshot-hook') is True
    assert _command_is_ours(EXE_CMD) is True


def test_command_matcher_ignores_unrelated_hooks():
    assert _command_is_ours("echo hi") is False
    assert _command_is_ours('"py" -m claude_compass hook') is False
    # mentions parachute but isn't our snapshot hook → leave it alone
    assert _command_is_ours("parachute --help") is False


def test_uninstall_removes_frozen_exe_hook(tmp_path):
    # Simulate the packaged build having registered itself by the .exe name.
    install_hooks(tmp_path, command=EXE_CMD)
    assert hooks_installed(tmp_path) is True          # detected despite no underscore-tag
    assert uninstall_hooks(tmp_path).status == "removed"
    assert hooks_installed(tmp_path) is False
    # ...and the file no longer references our hook in any form.
    assert "snapshot-hook" not in settings_path(tmp_path).read_text(encoding="utf-8")


def test_install_idempotent_for_frozen_exe_hook(tmp_path):
    install_hooks(tmp_path, command=EXE_CMD)
    # A second session-start install must NOT stack a duplicate.
    assert install_hooks(tmp_path, command=EXE_CMD).status == "unchanged"
