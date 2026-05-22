"""Smoke test for app.py — it must import WITHOUT PySide6 (Qt is imported lazily
inside main()), and degrade gracefully when PySide6 is absent."""

from __future__ import annotations

import importlib.util


def test_app_imports_without_pyside():
    # Importing the module must not require PySide6.
    import claude_parachute.app as app
    assert callable(app.main)
    assert "PySide6" in app._missing_pyside_message()


def test_main_returns_1_without_pyside():
    # If PySide6 isn't installed, main() should explain, not crash.
    if importlib.util.find_spec("PySide6") is not None:
        import pytest
        pytest.skip("PySide6 is installed; the missing-deps path can't be exercised")
    import claude_parachute.app as app
    assert app.main() == 1
