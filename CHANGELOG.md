# Changelog

All notable changes to Claude Parachute are noted here. This project follows
[semantic versioning](https://semver.org/).

## [0.1.0] — 2026-05-22

The first drop. A safety net for the changes `/rewind` can't see.

### Added

- **Shadow-git snapshot engine** (`snapshots.py`) — a private git repository at
  `.parachute/snapshots.git` whose work-tree is your project root, completely
  separate from your real `.git`. Snapshots the whole tree (Bash changes
  included), with undoable restore (safety snapshot taken first), `undo`, and a
  newest-first timeline.
- **Claude Code hooks** (`hookconfig.py`) — a PostToolUse hook (checkpoint after
  every tool) and a SessionStart baseline, installed into
  `~/.claude/settings.json` with crash-safe atomic writes that refuse to touch
  invalid JSON. The hook can never break your session (any error → clean exit).
- **CLI** (`parachute`) — `init`, `snapshot`, `list`, `restore`, `undo`,
  `status`, `dashboard`, `install-hooks`, `uninstall-hooks`, `doctor`.
- **Double-click app** — a calm light-Claude window with a snapshot timeline, a
  big **Pull the cord** restore button, an Auto-snapshot toggle, and a system
  tray companion. Built into a single `Claude Parachute.exe`.
- **HTML dashboard** — a self-contained, light/dark status page (snapshot count,
  disk used, hook state, timeline, and how to pull the cord).
- Tests for the engine, the hook installer, the CLI, the Qt-free app model, and
  the dashboard. Git-dependent tests skip cleanly when git isn't present.

### Safety promises

- Never touches your real `.git`.
- Restore is always undoable (safety snapshot first) and never deletes files you
  created since.
- Honours `.gitignore`; never snapshots `.git/` or `.parachute/`.

[0.1.0]: https://github.com/JackBhanded/claude-parachute/releases/tag/v0.1.0
