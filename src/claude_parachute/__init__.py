"""Claude Parachute — the safety net for when /rewind can't save you.

Claude Code's built-in checkpoints only track Write/Edit edits — changes made
through Bash (rm, sed -i, >, git reset --hard, migrations, build scripts) are NOT
captured. Parachute snapshots your WHOLE working tree after every tool (Bash
included) into a *separate* shadow git repo (`.parachute/snapshots.git`) that
never touches your real `.git`. When something goes sideways you "pull the cord"
and restore — and the restore is itself snapshotted first, so recovery is
undoable. Plus a kill switch for runaway agents.

Recovery-first, and never destructive itself.
"""

__version__ = "0.1.1"
__author__ = "Jack Bhanded"
__license__ = "MIT"
