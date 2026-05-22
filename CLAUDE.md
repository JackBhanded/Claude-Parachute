# CLAUDE.md — Claude Parachute

Context for any Claude (or human) picking up this repo. Keep it current.

## What this is

A safety net for Claude Code. `/rewind` only tracks Write/Edit changes; anything
done through the **Bash tool** (`rm`, `git reset --hard`, `sed -i`, `>`,
migrations) is invisible to it. Parachute keeps a private **shadow git repo** and
checkpoints the *whole* project after every tool — Bash included — so those
changes are recoverable with a one-pull, always-undoable restore. Python, stdlib
+ the `git` CLI, shipped as a single `.exe`.

## Architecture (`src/claude_parachute/`)

- `snapshots.py` — **the bedrock.** `ShadowRepo(work_tree)` keeps a git repo at
  `.parachute/snapshots.git` whose work-tree is the project root. Every git
  command is pinned to its own `GIT_DIR` + `GIT_WORK_TREE` via env, so the user's
  real `.git` is never touched. `snapshot`, `snapshot_if_changed`, `list`,
  `restore` (safety snapshot first → `git checkout <sha> -- .`), `undo`.
- `hookconfig.py` — installs two Claude Code hooks (PostToolUse + SessionStart),
  both running `parachute snapshot-hook`, into `~/.claude/settings.json` with
  never-corrupt care (refuses invalid JSON, atomic write, idempotent, removes
  only ours by tag).
- `safewrite.py` — LEAN vendored copy: just `write_text_atomic` (atomic
  temp→fsync→`os.replace`→fsync dir, optional timestamped backup). The only file
  outside `.parachute/` that Parachute edits is `settings.json`.
- `cli.py` / `__main__.py` — `init/snapshot/list/restore/undo/status/dashboard/
  install-hooks/uninstall-hooks/snapshot-hook/doctor`. `snapshot-hook` reads the
  hook's stdin JSON for `cwd`, calls `snapshot_if_changed`, and NEVER breaks the
  session (any error → exit 0, no output).
- `dashboard.py` — self-contained light-Claude HTML status page (light/dark
  toggle, stat chips, snapshot timeline, "pull the cord" note, real Claude logo).
- `appmodel.py` (Qt-free, tested) — `ParachuteModel` wraps a ShadowRepo;
  `build_snapshot()` → immutable `AppSnapshot` (rows, counts, hook state,
  headline); actions `arm/take_snapshot/restore/undo/set_hooks`.
- `app.py` — PySide6 window (lazy Qt import): snapshot timeline list, a big
  **Pull the cord** restore button (with an undoable-confirm dialog),
  Snapshot-now, Auto-snap checkbox, Open dashboard, system tray.

## Safety guarantees (the whole point)

- Never touches the real `.git` (pinned GIT_DIR/GIT_WORK_TREE).
- Restore takes a safety snapshot first → always undoable; never deletes files
  created since.
- Honours `.gitignore`; excludes `.git/` and `.parachute/`.
- Hooks can't break a session (errors swallowed, exit 0).
- `settings.json` edited with atomic writes; refuses invalid JSON.

## Testing

`pip install -e ".[dev]" && pytest` (or double-click `run-tests.bat`). Git-backed
tests skip cleanly when git isn't on PATH; the hook installer, CLI hook commands,
app-model read side, and dashboard empty-state run without git. The GUI logic
lives in the Qt-free `appmodel`, and `app.py` imports without PySide6 (Qt is lazy
inside `main()`), so both are tested without a display.

## Build & ship

`build-exe.ps1` (PyInstaller + PySide6, `--onefile --windowed --paths src
--collect-submodules claude_parachute gui_launcher.py`) → `dist/Claude
Parachute.exe`. GitHub Actions (`.github/workflows/build.yml`,
`permissions: contents: write`) builds + attaches the .exe on a `v*` tag.
`push-to-github.ps1` force-moves the tag so a re-push actually rebuilds the .exe.
SmartScreen warns on the unsigned exe (More info → Run anyway); documented in the
README.

## Roadmap

v0.2: **auto kill-switch** — a Stop-event watchdog that can halt a runaway session
(deferred from v0.1 as a footgun until the UX is right). Later: a prune/retention
policy for the snapshot store, and a diff view in the dashboard.

## Part of the fleet

- [Claude Meter](https://github.com/JackBhanded/claude-meter) — live usage on your taskbar.
- [Claude Lifeboat](https://github.com/JackBhanded/claude-lifeboat) — backup & restore for Claude data.
- [Claude Lifejacket](https://github.com/JackBhanded/claude-lifejacket) — keep every session aware of your projects.
- [Claude Compass](https://github.com/JackBhanded/claude-compass) — keep every session attuned to how you like to work.
- **Claude Parachute** — you are here. The net for when /rewind can't save you.

_Maintainer's working-style/personal context is kept in private notes, not in this public file._
