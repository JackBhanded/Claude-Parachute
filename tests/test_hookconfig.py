"""Tests for hookconfig.py — safely editing ~/.claude/settings.json (no git needed)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from claude_parachute.hookconfig import (
    HOOK_TAG,
    _command_is_ours,
    hook_command,
    hooks_installed,
    install_hooks,
    prune_stale_hooks,
    settings_path,
    uninstall_hooks,
)


def _gone_cmd():
    """A Parachute hook command whose exe is missing FOR THE CURRENT OS."""
    if os.name == "nt":
        return r'"C:\definitely\gone\Claude Parachute.exe" snapshot-hook'
    return '"/definitely/gone/parachute-bin" snapshot-hook'


def _other_os_cmd():
    """A Parachute hook command for the OTHER OS (must never be pruned here)."""
    if os.name == "nt":
        return '"/opt/parachute/parachute-bin" snapshot-hook'
    return r'"C:\Users\x\Claude Parachute.exe" snapshot-hook'

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
    # Point the hook at a real existing exe (as in real use), so the self-heal
    # keeps it and a second session-start install does NOT stack a duplicate.
    exe = tmp_path / "Claude Parachute.exe"
    exe.write_text("")
    cmd = f'"{exe}" snapshot-hook'
    install_hooks(tmp_path, command=cmd)
    assert install_hooks(tmp_path, command=cmd).status == "unchanged"


# --- self-heal: prune hooks whose exe has gone missing ------------------------

def test_hook_command_uses_forward_slashes():
    # Git Bash eats backslashes — the registered path must use forward slashes.
    cmd = hook_command(python=r"C:\Python311\python.exe")
    assert "\\" not in cmd and "snapshot-hook" in cmd and "C:/Python311/python.exe" in cmd


def test_prune_removes_missing_exe(tmp_path):
    sp = settings_path(tmp_path)
    sp.write_text(json.dumps({"hooks": {"PostToolUse": [{"hooks": [
        {"type": "command", "command": _gone_cmd()},
        {"type": "command", "command": "echo keep-me"},
    ]}]}}), encoding="utf-8")
    res = prune_stale_hooks(tmp_path)
    assert res.status == "healed"
    cmds = [h["command"] for g in read(sp)["hooks"].get("PostToolUse", []) for h in g["hooks"]]
    assert "echo keep-me" in cmds
    assert not any("snapshot-hook" in c for c in cmds)


def test_prune_keeps_other_os_hook(tmp_path):
    # A path valid for the OTHER OS must be left alone (Cowork+CLI share settings).
    sp = settings_path(tmp_path)
    sp.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [
        {"type": "command", "command": _other_os_cmd()},
    ]}]}}), encoding="utf-8")
    assert prune_stale_hooks(tmp_path).status == "clean"
    assert "snapshot-hook" in sp.read_text(encoding="utf-8")


def test_prune_keeps_python_form(tmp_path):
    # The "-m claude_parachute" form has no single bundled exe to miss → never pruned.
    sp = settings_path(tmp_path)
    sp.write_text(json.dumps({"hooks": {"PostToolUse": [{"hooks": [
        {"type": "command", "command": '"py" -m claude_parachute snapshot-hook'},
    ]}]}}), encoding="utf-8")
    assert prune_stale_hooks(tmp_path).status == "clean"


def test_install_self_heals_moved_exe(tmp_path):
    # Re-arming after the exe moved: the stale hook is pruned, the fresh one lands.
    sp = settings_path(tmp_path)
    sp.write_text(json.dumps({"hooks": {"PostToolUse": [{"hooks": [
        {"type": "command", "command": _gone_cmd()},
    ]}]}}), encoding="utf-8")
    install_hooks(tmp_path, command='"py" -m claude_parachute snapshot-hook')
    cmds = [h["command"] for g in read(sp)["hooks"]["PostToolUse"] for h in g["hooks"]]
    assert any("-m claude_parachute" in c for c in cmds)
    assert not any("gone" in c for c in cmds)
