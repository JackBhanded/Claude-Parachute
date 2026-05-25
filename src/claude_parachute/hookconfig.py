"""hookconfig.py — install/remove Claude Code hooks for Parachute, safely.

Parachute installs two hooks, both running ``parachute snapshot-hook``:
  * **PostToolUse** — fires after *every* tool (Write/Edit AND Bash), so we
    checkpoint the changes ``/rewind`` can't see.
  * **SessionStart** — a baseline checkpoint when a session begins.

``~/.claude/settings.json`` is strict JSON the user may have customised, so we
treat it carefully: refuse to write if it won't parse, back it up first, write
atomically, detect our own hooks (by tag) so install is idempotent and uninstall
removes only ours. (Generic event editor vendored from Compass/Lifejacket.)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .safewrite import write_text_atomic

__all__ = [
    "HookResult", "hook_command", "settings_path", "claude_code_home",
    "install_hooks", "uninstall_hooks", "hooks_installed", "prune_stale_hooks",
    "HOOK_TAG", "HOOK_EVENTS",
]

HOOK_TAG = "claude_parachute"
HOOK_EVENTS = ("PostToolUse", "SessionStart")


def _command_is_ours(command: str) -> bool:
    """True if a hook command is one of ours, in EITHER form.

    We register two shapes depending on how Parachute runs:
      * from source : ``"<python>" -m claude_parachute snapshot-hook``
      * frozen .exe  : ``"...\\Claude Parachute.exe" snapshot-hook``

    The frozen form contains "Claude Parachute" (space + capitals), NOT the
    literal ``claude_parachute`` — so a bare ``HOOK_TAG in command`` test misses
    it, which once left the .exe's hook un-removable. We match case-insensitively
    on BOTH "parachute" and "snapshot-hook" so we recognise either form yet never
    grab an unrelated hook that merely mentions one of the words.
    """
    c = str(command).lower()
    return "parachute" in c and "snapshot-hook" in c


def claude_code_home() -> Path:
    import os
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude"


@dataclass
class HookResult:
    status: str          # installed | unchanged | removed | absent | refused | partial
    path: Path
    backup_path: Optional[Path] = None
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status != "refused"


def hook_command(python: Optional[str] = None) -> str:
    # When running as a PyInstaller .exe, sys.executable IS the bundled app — it
    # can't run "-m claude_parachute". Register the exe with a bare subcommand
    # instead; the launcher routes any subcommand to the CLI (never the window),
    # so the hook quietly snapshots rather than popping open the app.
    #
    # Forward slashes, not backslashes: Claude Code often runs hooks through Git
    # Bash on Windows, where "C:\Users\..." gets its backslashes eaten. Forward
    # slashes work in cmd, PowerShell AND bash, so the hook runs everywhere.
    if python is None and getattr(sys, "frozen", False):
        exe = sys.executable.replace("\\", "/")
        return f'"{exe}" snapshot-hook'
    py = (python or sys.executable).replace("\\", "/")
    return f'"{py}" -m claude_parachute snapshot-hook'


def _exe_path_from_command(command: str) -> Optional[str]:
    """Pull the executable/interpreter path out of a hook command, or None for
    the ``python -m`` form (there's no single bundled file that can go missing)."""
    c = str(command).strip()
    if " -m " in c:
        return None
    if c.startswith('"'):
        end = c.find('"', 1)
        if end > 1:
            return c[1:end]
    return c.split(" ")[0] if c else None


def _path_is_missing_on_this_os(p: str) -> bool:
    """True only if ``p`` looks like a path for the CURRENT OS and isn't there.

    Crucial for users who run both Cowork (Linux) and the CLI (Windows) off one
    shared settings.json: a Linux run must NOT prune a Windows-`.exe` hook just
    because that path is meaningless on Linux (it's valid for the Windows CLI),
    and vice-versa. So each OS only judges paths that look like its own.
    """
    import os
    looks_windows = (len(p) > 1 and p[1] == ":") or "\\" in p or p.lower().endswith(".exe")
    if os.name == "nt":
        return looks_windows and not os.path.exists(p)
    return (not looks_windows) and not os.path.exists(p)


def settings_path(claude_home: Path) -> Path:
    return Path(claude_home) / "settings.json"


def _load(path: Path):
    if not path.exists():
        return {}, None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"couldn't read {path} ({exc})"
    if not text.strip():
        return {}, None
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, (f"{path} isn't valid JSON ({exc}). I didn't touch it — fix "
                      "the JSON or add the hooks by hand, then re-run.")


def _dump(data) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _event_has_ours(arr) -> bool:
    return any(isinstance(h, dict) and _command_is_ours(h.get("command", ""))
               for g in arr if isinstance(g, dict) for h in g.get("hooks", []))


def prune_stale_hooks(claude_home: Path) -> HookResult:
    """Self-heal: drop any Parachute hook whose exe has gone missing.

    The classic nag: you ran the .exe from Downloads, it armed itself there, then
    the file moved/was cleaned up — leaving a hook Claude Code tries (and fails) to
    run after every tool. This removes only OUR hooks, only when their exe is
    genuinely missing *for the current OS*, and never touches anything else.
    """
    path = settings_path(claude_home)
    data, err = _load(path)
    if err:
        return HookResult(status="refused", path=path, message=err)
    if not data or not isinstance(data.get("hooks"), dict):
        return HookResult(status="clean", path=path, message="No hooks to check.")

    hooks = data["hooks"]
    removed = 0
    for event in list(hooks.keys()):
        arr = hooks.get(event)
        if not isinstance(arr, list):
            continue
        new_groups: List[dict] = []
        for group in arr:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            kept = []
            for h in group.get("hooks", []):
                cmd = h.get("command", "") if isinstance(h, dict) else ""
                if _command_is_ours(cmd):
                    exe = _exe_path_from_command(cmd)
                    if exe and _path_is_missing_on_this_os(exe):
                        removed += 1
                        continue
                kept.append(h)
            if kept:
                g = dict(group); g["hooks"] = kept; new_groups.append(g)
        if new_groups:
            hooks[event] = new_groups
        else:
            hooks.pop(event, None)
    if isinstance(hooks, dict) and not hooks:
        data.pop("hooks", None)

    if removed == 0:
        return HookResult(status="clean", path=path,
                          message="No stale Parachute hooks — all good.")
    word = "hook" if removed == 1 else "hooks"
    bak = write_text_atomic(path, _dump(data), backup=True)
    return HookResult(status="healed", path=path, backup_path=bak,
                      message=f"Cleaned up {removed} stale Parachute {word} pointing at a missing exe.")


def install_hooks(claude_home: Path, command: Optional[str] = None) -> HookResult:
    """Add our snapshot hook to every event in HOOK_EVENTS (idempotent)."""
    # Self-heal first: if a previous hook points at a now-missing exe (e.g. you
    # ran it from Downloads then moved it), drop it so re-arming repoints cleanly.
    prune_stale_hooks(claude_home)
    path = settings_path(claude_home)
    command = command or hook_command()
    data, err = _load(path)
    if err:
        return HookResult(status="refused", path=path, message=err)

    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        return HookResult(status="refused", path=path,
                          message="The 'hooks' section of your settings.json isn't "
                                  "an object, so I left it alone.")
    added = 0
    for event in HOOK_EVENTS:
        arr = hooks.setdefault(event, [])
        if not isinstance(arr, list):
            return HookResult(status="refused", path=path,
                              message=f"Your settings.json has a '{event}' that "
                                      "isn't a list, so I left it alone.")
        if not _event_has_ours(arr):
            arr.append({"hooks": [{"type": "command", "command": command}]})
            added += 1

    if added == 0:
        return HookResult(status="unchanged", path=path,
                          message="Parachute's hooks are already in place — you're "
                                  "covered.")
    bak = write_text_atomic(path, _dump(data), backup=path.exists())
    return HookResult(status="installed", path=path, backup_path=bak,
                      message="Parachute is armed — it'll snapshot after every tool "
                              "(Bash included) and at session start. ")


def uninstall_hooks(claude_home: Path) -> HookResult:
    path = settings_path(claude_home)
    data, err = _load(path)
    if err:
        return HookResult(status="refused", path=path, message=err)
    if not data or not isinstance(data.get("hooks"), dict):
        return HookResult(status="absent", path=path, message="No hooks to remove.")

    hooks = data["hooks"]
    removed = False
    for event in HOOK_EVENTS:
        arr = hooks.get(event)
        if not isinstance(arr, list):
            continue
        new_groups: List[dict] = []
        for group in arr:
            if not isinstance(group, dict):
                new_groups.append(group)
                continue
            kept = [h for h in group.get("hooks", [])
                    if not (isinstance(h, dict) and _command_is_ours(h.get("command", "")))]
            if len(kept) != len(group.get("hooks", [])):
                removed = True
            if kept:
                g = dict(group); g["hooks"] = kept; new_groups.append(g)
        if new_groups:
            hooks[event] = new_groups
        else:
            hooks.pop(event, None)
    if isinstance(hooks, dict) and not hooks:
        data.pop("hooks", None)

    if not removed:
        return HookResult(status="absent", path=path,
                          message="No Parachute hooks found — nothing to remove.")
    bak = write_text_atomic(path, _dump(data), backup=True)
    return HookResult(status="removed", path=path, backup_path=bak,
                      message="Removed Parachute's hooks. Your other settings are "
                              "untouched.")


def hooks_installed(claude_home: Path) -> bool:
    sp = settings_path(claude_home)
    if not sp.exists():
        return False
    data, err = _load(sp)
    if err or not isinstance(data, dict):
        return False
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return False
    return any(_event_has_ours(arr) for arr in hooks.values() if isinstance(arr, list))
