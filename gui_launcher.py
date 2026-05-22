"""Entry point PyInstaller bundles into 'Claude Parachute.exe'.

Double-clicked with no arguments → opens the GUI window.

Invoked WITH arguments → runs the command-line interface instead and never opens
a window. This matters because the Claude Code hook is registered to run this
same executable (a PyInstaller build can't run ``python -m claude_parachute``).
Without this routing, every hook firing would pop open another app window — so
we dispatch any subcommand straight to the CLI here.

Kept at the repo root (with ``--paths src`` at build time) so PyInstaller finds
the ``claude_parachute`` package.
"""

import sys


def _run() -> int:
    argv = list(sys.argv[1:])

    # An older/frozen hook may pass the python-style "-m claude_parachute ..."
    # prefix as plain arguments to the exe. Strip it so we can dispatch cleanly.
    if argv and argv[0] == "-m":
        argv = argv[1:]
        if argv and argv[0] == "claude_parachute":
            argv = argv[1:]

    if argv:
        # A subcommand (e.g. the hook's "snapshot-hook") — run the CLI silently.
        from claude_parachute.cli import main as cli_main
        return cli_main(argv)

    # No arguments — open the window.
    from claude_parachute.app import main as app_main
    return app_main()


if __name__ == "__main__":
    raise SystemExit(_run())
