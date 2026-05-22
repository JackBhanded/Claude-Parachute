"""cli.py — the friendly ``parachute`` command line.

    parachute init                 arm Parachute in THIS project (create the shadow repo)
    parachute snapshot [-m msg]    take a checkpoint right now
    parachute list                 show recent snapshots
    parachute restore <ref|n>      pull the cord — restore to a snapshot (undoable)
    parachute undo                 quick undo: restore to the snapshot before the last change
    parachute status               where things stand (snapshots, size, hooks)
    parachute dashboard            open a calm HTML status page in your browser
    parachute install-hooks        auto-snapshot after every tool + at session start
    parachute uninstall-hooks      remove the hooks
    parachute snapshot-hook        (internal) run by Claude Code's hooks
    parachute doctor               quick health check

Recovery-first, never destructive: every restore takes a safety snapshot first.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from . import __version__
from .hookconfig import (
    hook_command,
    hooks_installed,
    install_hooks,
    settings_path,
    uninstall_hooks,
)
from .snapshots import ParachuteError, ShadowRepo, git_available

CHUTE = "[^]"   # tiny ASCII parachute for headers


def _out(msg: str = "") -> None:
    print(msg)


def _repo() -> ShadowRepo:
    return ShadowRepo(Path.cwd())


def claude_code_home() -> Path:
    override = os.environ.get("CLAUDE_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".claude"


def _resolve_ref(repo: ShadowRepo, ref: str) -> str:
    """Allow a 1-based index from `list` (newest first) or a sha/ref."""
    if ref.isdigit():
        snaps = repo.list()
        i = int(ref)
        if 1 <= i <= len(snaps):
            return snaps[i - 1].sha
    return ref


# --------------------------------------------------------------------------- #
# commands
# --------------------------------------------------------------------------- #

def cmd_init(args) -> int:
    if not git_available():
        _out(f"{CHUTE} Parachute needs git installed and on PATH. Grab it from "
             "https://git-scm.com/download/win and try again.")
        return 1
    r = _repo()
    r.init()
    _out(f"{CHUTE} Parachute is armed in this project ({r.work_tree}).")
    _out("    Snapshots live in .parachute/ (separate from your real .git).")
    _out("    Turn on auto-snapshots with:  parachute install-hooks")
    return 0


def cmd_snapshot(args) -> int:
    try:
        sha = _repo().snapshot(args.message or "")
    except ParachuteError as exc:
        _out(f"{CHUTE} {exc}")
        return 1
    _out(f"{CHUTE} Checkpoint saved ({sha[:8]}).")
    return 0


def cmd_list(args) -> int:
    r = _repo()
    snaps = r.list(args.limit)
    if not snaps:
        _out(f"{CHUTE} No snapshots yet. Run  parachute snapshot  or  parachute "
             "install-hooks  to start the safety net.")
        return 0
    _out(f"{CHUTE} Recent snapshots (newest first):")
    _out("")
    for i, s in enumerate(snaps, 1):
        when = s.time.strftime("%a %d %b %I:%M %p").lstrip("0")
        _out(f"  [{i}] {s.short}  {when}   {s.label}")
    _out("")
    _out("    Restore one with:  parachute restore <number>")
    return 0


def cmd_restore(args) -> int:
    r = _repo()
    try:
        sha = _resolve_ref(r, args.ref)
        res = r.restore(sha)
    except ParachuteError as exc:
        _out(f"{CHUTE} {exc}")
        return 1
    _out(f"{CHUTE} Pulled the cord — restored to {res.restored[:8]}.")
    _out(f"    Your state just before this is safe in snapshot {res.safety[:8]}, "
         "so this is undoable.")
    return 0


def cmd_undo(args) -> int:
    r = _repo()
    if not r.exists() or r.resolve("HEAD~1") is None:
        _out(f"{CHUTE} Nothing to undo yet (need at least two snapshots).")
        return 1
    try:
        res = r.restore("HEAD~1")
    except ParachuteError as exc:
        _out(f"{CHUTE} {exc}")
        return 1
    _out(f"{CHUTE} Undone — restored to the snapshot before the last change "
         f"({res.restored[:8]}). Undoable via snapshot {res.safety[:8]}.")
    return 0


def _dir_size(path: Path) -> int:
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def cmd_status(args) -> int:
    r = _repo()
    _out(f"{CHUTE} Claude Parachute status")
    _out("")
    _out(f"  Project:    {r.work_tree}")
    if not r.exists():
        _out("  Armed:      no — run  parachute init")
    else:
        snaps = r.list(1000)
        size_mb = round(_dir_size(r.store_dir) / (1024 * 1024), 1)
        _out(f"  Armed:      yes ({len(snaps)} snapshot(s), {size_mb} MB)")
        if snaps:
            latest = snaps[0]
            _out(f"  Latest:     {latest.short}  {latest.label}")
    hooked = hooks_installed(claude_code_home())
    _out(f"  Auto-snap:  {'ON' if hooked else 'off'}"
         + ("" if hooked else "  (turn on: parachute install-hooks)"))
    return 0


def cmd_install_hooks(args) -> int:
    res = install_hooks(claude_code_home())
    _out(f"{CHUTE} {res.message}")
    if res.backup_path:
        _out(f"    (backup: {res.backup_path})")
    return 0 if res.ok else 1


def cmd_uninstall_hooks(args) -> int:
    res = uninstall_hooks(claude_code_home())
    _out(f"{CHUTE} {res.message}")
    return 0 if res.ok else 1


def cmd_snapshot_hook(args) -> int:
    """Run by Claude Code (PostToolUse / SessionStart). Snapshots the project
    cwd if anything changed. Must NEVER break the session: any error -> exit 0,
    no output."""
    cwd = os.getcwd()
    label = "auto checkpoint"
    try:
        if not sys.stdin.isatty():
            raw = sys.stdin.read()
            if raw and raw.strip():
                data = json.loads(raw)
                cwd = data.get("cwd") or cwd
                tn = data.get("tool_name") or data.get("hook_event_name") or ""
                if tn:
                    label = f"after {tn}"
    except Exception:
        pass
    try:
        ShadowRepo(cwd).snapshot_if_changed(label)
    except Exception:
        pass
    return 0


def cmd_dashboard(args) -> int:
    from .dashboard import write_dashboard
    r = _repo()
    if not r.exists():
        _out(f"{CHUTE} Parachute isn't armed here yet. Run  parachute init  first.")
        return 1
    out = write_dashboard(r)
    _out(f"{CHUTE} Dashboard ready: {out}")
    if not args.no_open:
        try:
            import webbrowser
            webbrowser.open(out.as_uri())
        except Exception:
            pass
    return 0


def cmd_doctor(args) -> int:
    r = _repo()
    _out(f"{CHUTE} Parachute check-up")
    _out("")
    _out(f"  Python:     {sys.version.split()[0]}")
    _out(f"  git:        {'found' if git_available() else 'NOT FOUND - please install git'}")
    _out(f"  Project:    {r.work_tree}")
    _out(f"  Armed:      {'yes' if r.exists() else 'no (run: parachute init)'}")
    _out(f"  Hooks:      {'on' if hooks_installed(claude_code_home()) else 'off'}")
    _out(f"  Hook cmd:   {hook_command()}")
    return 0


# --------------------------------------------------------------------------- #
# parser
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="parachute",
        description="A safety net for Claude Code — snapshots even the Bash "
                    "changes /rewind misses, with a one-pull restore.")
    p.add_argument("--version", action="version",
                   version=f"claude-parachute {__version__}")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("init", help="arm Parachute in this project").set_defaults(func=cmd_init)

    sn = sub.add_parser("snapshot", help="take a checkpoint now")
    sn.add_argument("-m", "--message", help="label for the snapshot")
    sn.set_defaults(func=cmd_snapshot)

    ls = sub.add_parser("list", help="show recent snapshots")
    ls.add_argument("--limit", type=int, default=30)
    ls.set_defaults(func=cmd_list)

    rs = sub.add_parser("restore", help="pull the cord: restore to a snapshot (undoable)")
    rs.add_argument("ref", help="a number from `list`, or a snapshot id")
    rs.set_defaults(func=cmd_restore)

    sub.add_parser("undo", help="restore to the snapshot before the last change").set_defaults(func=cmd_undo)
    sub.add_parser("status", help="where things stand").set_defaults(func=cmd_status)

    db = sub.add_parser("dashboard", help="open a calm HTML status page")
    db.add_argument("--no-open", action="store_true", help="write the file but don't open a browser")
    db.set_defaults(func=cmd_dashboard)

    sub.add_parser("install-hooks", help="auto-snapshot after every tool + at session start").set_defaults(func=cmd_install_hooks)
    sub.add_parser("uninstall-hooks", help="remove the hooks").set_defaults(func=cmd_uninstall_hooks)
    sub.add_parser("snapshot-hook", help=argparse.SUPPRESS).set_defaults(func=cmd_snapshot_hook)
    sub.add_parser("doctor", help="quick health check").set_defaults(func=cmd_doctor)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
