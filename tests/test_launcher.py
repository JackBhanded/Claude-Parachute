"""Regression tests for the bug where the Claude Code hook launched the GUI
window instead of taking a snapshot (a new window opened on every tool use).

The fix: gui_launcher routes ANY subcommand to the CLI (never the window), and
hook_command registers a bare subcommand when running as a frozen .exe.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_LAUNCHER = Path(__file__).resolve().parent.parent / "gui_launcher.py"


def _load_launcher():
    spec = importlib.util.spec_from_file_location("parachute_gui_launcher", _LAUNCHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_subcommand_routes_to_cli_not_gui(monkeypatch):
    launcher = _load_launcher()
    calls = {"cli": None, "app": 0}

    import claude_parachute.cli as cli
    import claude_parachute.app as app
    monkeypatch.setattr(cli, "main", lambda argv=None: calls.__setitem__("cli", list(argv or [])) or 0)
    monkeypatch.setattr(app, "main", lambda *a, **k: calls.__setitem__("app", calls["app"] + 1) or 0)

    monkeypatch.setattr(sys, "argv", ["Claude Parachute.exe", "snapshot-hook"])
    assert launcher._run() == 0
    assert calls["cli"] == ["snapshot-hook"]   # went to the CLI
    assert calls["app"] == 0                    # the window never opened


def test_old_python_m_prefix_is_stripped(monkeypatch):
    """An already-installed hook may pass '-m claude_parachute snapshot-hook'."""
    launcher = _load_launcher()
    seen = {}
    import claude_parachute.cli as cli
    import claude_parachute.app as app
    monkeypatch.setattr(cli, "main", lambda argv=None: seen.__setitem__("argv", list(argv or [])) or 0)
    monkeypatch.setattr(app, "main", lambda *a, **k: (_ for _ in ()).throw(AssertionError("GUI must not open")))

    monkeypatch.setattr(sys, "argv", ["x.exe", "-m", "claude_parachute", "snapshot-hook"])
    assert launcher._run() == 0
    assert seen["argv"] == ["snapshot-hook"]


def test_no_args_opens_the_window(monkeypatch):
    launcher = _load_launcher()
    opened = {"n": 0}
    import claude_parachute.app as app
    monkeypatch.setattr(app, "main", lambda *a, **k: opened.__setitem__("n", opened["n"] + 1) or 0)

    monkeypatch.setattr(sys, "argv", ["Claude Parachute.exe"])
    assert launcher._run() == 0
    assert opened["n"] == 1


def test_hook_command_uses_bare_subcommand_when_frozen(monkeypatch):
    from claude_parachute.hookconfig import hook_command
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Tools\Claude Parachute.exe", raising=False)
    cmd = hook_command()
    # Forward slashes, not backslashes: the hook often runs through Git Bash on
    # Windows, where backslashes get eaten. Path is normalised so it runs anywhere.
    assert cmd == '"C:/Tools/Claude Parachute.exe" snapshot-hook'
    assert "\\" not in cmd                     # bash-safe
    assert "-m claude_parachute" not in cmd    # the line that caused the window storm
