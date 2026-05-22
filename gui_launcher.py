"""Entry point PyInstaller bundles into 'Claude Parachute.exe'. Launches the GUI.
Kept at the repo root (with ``--paths src`` at build time) so PyInstaller finds
the ``claude_parachute`` package."""

from claude_parachute.app import main

if __name__ == "__main__":
    raise SystemExit(main())
