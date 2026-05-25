#!/usr/bin/env python3
"""Stop the storm — emergency hook cleanup for Claude Parachute.

If Parachute's window keeps popping open again and again, a hook in your Claude
settings is firing the app on every tool use. Normally you'd just turn it off in
the app, but an older build registered the hook under the packaged ".exe" name,
which the app's own uninstaller didn't recognise — so it couldn't remove it.

This little script fixes that directly. It:
  1. Finds your Claude settings (~/.claude/settings.json).
  2. Makes a timestamped backup right next to it (nothing is lost).
  3. Removes ONLY Parachute's snapshot hooks — any other hooks you have are
     left exactly as they were.
  4. Tells you what it did.

It is self-contained (no Parachute install needed) and safe to run twice.

How to run it:
  * Double-click "Stop the storm.bat" next to this file, OR
  * In a terminal:  python "stop-the-storm.py"

After the storm stops, grab the latest Parachute release so you're on the build
that fixes this for good, then re-arm it from inside the app if you want it back.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


def _say(msg: str) -> None:
    print("  " + msg)


def _settings_path() -> Path:
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    base = Path(override).expanduser() if override else (Path.home() / ".claude")
    return base / "settings.json"


def _looks_like_parachute(command: str) -> bool:
    """True for either hook form we've ever registered.

    Matches the python form ("... -m claude_parachute snapshot-hook") AND the
    packaged-exe form ('"...\\Claude Parachute.exe" snapshot-hook'). We require
    BOTH "parachute" and "snapshot-hook" (case-insensitive) so we never touch an
    unrelated hook that happens to mention one word.
    """
    c = command.lower()
    return "parachute" in c and "snapshot-hook" in c


def _clean_event(groups):
    """Return (new_groups, removed_count) with Parachute hooks stripped out."""
    if not isinstance(groups, list):
        return groups, 0
    removed = 0
    new_groups = []
    for group in groups:
        if not isinstance(group, dict):
            new_groups.append(group)
            continue
        inner = group.get("hooks", [])
        kept = []
        for h in inner:
            if isinstance(h, dict) and _looks_like_parachute(str(h.get("command", ""))):
                removed += 1
            else:
                kept.append(h)
        if kept:
            g = dict(group)
            g["hooks"] = kept
            new_groups.append(g)
        # a group whose hooks all got removed is dropped entirely
    return new_groups, removed


def main() -> int:
    print("")
    _say("Stopping the Parachute storm...")
    print("")

    path = _settings_path()
    if not path.exists():
        _say(f"No Claude settings found at {path}.")
        _say("Nothing to clean up — the storm isn't coming from a hook here. :)")
        return 0

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        _say(f"Couldn't read {path} ({exc}).")
        return 1

    if not text.strip():
        _say("Your settings file is empty — no hooks to remove.")
        return 0

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        _say(f"Your settings.json isn't valid JSON ({exc}).")
        _say("I didn't touch it. Fix the JSON, or remove the Parachute hook by hand.")
        return 1

    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        _say("No hooks section in your settings — nothing to remove.")
        return 0

    total_removed = 0
    for event in list(hooks.keys()):
        new_groups, removed = _clean_event(hooks[event])
        total_removed += removed
        if new_groups:
            hooks[event] = new_groups
        else:
            hooks.pop(event, None)
    if not hooks:
        data.pop("hooks", None)

    if total_removed == 0:
        _say("No Parachute hooks found — the storm isn't from a hook in this file.")
        _say("If a window is still open, just close it; the fixed build won't reopen it.")
        return 0

    # Back up before we write — belt and braces.
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"settings.json.parachute-backup-{stamp}")
    try:
        shutil.copy2(path, backup)
    except OSError as exc:
        _say(f"Couldn't make a backup ({exc}); stopping without changing anything.")
        return 1

    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    except OSError as exc:
        _say(f"Couldn't write the cleaned settings ({exc}).")
        _say(f"Your original is safe; a copy is at {backup}.")
        return 1

    _say(f"Done! Removed {total_removed} Parachute hook"
         f"{'s' if total_removed != 1 else ''}. The storm should stop now.")
    _say(f"A backup of the old settings is at: {backup}")
    print("")
    _say("If a Parachute window is still open, just close it — it won't reopen.")
    _say("To re-arm Parachute later, grab the latest release and turn it on in the app.")
    print("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
