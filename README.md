<div align="center">

<img src="https://raw.githubusercontent.com/JackBhanded/claude-parachute/main/docs/logo.svg" width="72" alt="Claude Parachute" />

# Claude Parachute

**An undo button for the things Claude Code can't undo.**

[![Build Windows app](https://github.com/JackBhanded/claude-parachute/actions/workflows/build.yml/badge.svg)](https://github.com/JackBhanded/claude-parachute/actions/workflows/build.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

</div>

---

## The problem, in one breath

Claude Code can edit your files for you. It also runs **commands** for you — and
some of those commands delete things, overwrite things, or reset your project.

Claude Code's built-in undo (`/rewind`) only remembers the file edits. It does
**not** remember the commands. So when a command wipes something out, `/rewind`
can't bring it back. It's just gone.

**Claude Parachute** is the missing safety net. It quietly saves a copy of your
whole project every time Claude does anything — including those commands — so you
can always go back. One click and you're rescued.

> Think of it like autosave in a video game. Parachute keeps dropping checkpoints
> as you go, so a bad move is never the end of the world — you just reload the
> last good one.

## What you can do with it

- **Go back in time.** Restore your project to any earlier checkpoint with one
  click. We call it *pulling the cord*.
- **Never lose work by accident.** Every checkpoint is saved automatically in the
  background while you and Claude work.
- **Undo the undo.** Even *restoring* is reversible — Parachute saves where you
  were first, so you can't make things worse by pressing the button.
- **Stay calm.** A tidy timeline shows every checkpoint, so you always know you
  have a way back.

It can't lose your work, and it can't make a mess of your project — by design
(more on that [below](#is-it-safe)).

## Get started in 2 minutes

**The easy way — no typing.** Download **`Claude Parachute.exe`** from the
[latest release](https://github.com/JackBhanded/claude-parachute/releases) and
double-click it. You'll get a simple window with your list of checkpoints and a
big **Pull the cord** button. It tucks into your system tray and looks after you
from there.

> The first time you open it, Windows may show a blue "Windows protected your PC"
> box. That's normal for small free apps like this one — click **More info →
> Run anyway**.

That's it. Open your project, click **Snapshot now** once to switch it on, and
Parachute takes it from there.

## The one button that matters: Pull the cord

When something goes wrong, you don't need to understand anything technical. You
just:

1. Open Claude Parachute.
2. Click the checkpoint you want to go back to.
3. Press **Pull the cord**.

Your project snaps back to exactly how it was at that moment. And because
Parachute saves your current state *first*, you can always change your mind and
come back. There's no way to make it worse — that's the whole promise.

## Prefer typing? There's a command for everything

If you live in a terminal, install it once (no admin needed):

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Then, inside any project folder:

| Command | What it does |
| --- | --- |
| `parachute init` | Switch Parachute on for this project. |
| `parachute install-hooks` | Save a checkpoint automatically after everything Claude does. |
| `parachute snapshot -m "note"` | Save a checkpoint right now, with a note. |
| `parachute list` | Show your recent checkpoints (newest first). |
| `parachute restore 3` | **Pull the cord** — go back to checkpoint #3. |
| `parachute undo` | Quick one-step-back: go to the checkpoint before your last change. |
| `parachute status` | A quick "is everything switched on?" check. |
| `parachute dashboard` | Open a nice status page in your browser. |
| `parachute doctor` | Health check, if something feels off. |

To go back, you only ever need two: `parachute list` to see the numbers, then
`parachute restore <number>` to pull the cord. Both the restore and the quick
`undo` are always reversible.

<a name="is-it-safe"></a>
## Is it safe? Yes — that's the point

Parachute is built to be impossible to regret:

- **It can't lose your work.** Going back always saves where you are first, so
  you can undo the undo. And it only *brings old files back* — it never deletes
  the new ones you've made since.
- **It keeps to itself.** Parachute saves its checkpoints in their own private
  folder. It doesn't interfere with your project's own version history, and it
  skips anything your project already tells git to ignore.
- **It can't get in Claude's way.** If Parachute ever hiccups, it steps aside
  silently — it will never interrupt or break what Claude is doing.

## What you'll need

- **Windows 10 or 11** for the double-click app.
- **Git** installed on your computer — Parachute uses it under the hood to do the
  saving. If you don't have it, grab it (free) from
  [git-scm.com/download/win](https://git-scm.com/download/win) and install with
  all the default options.
- (For the typed commands only: **Python 3.9 or newer**.)

## Part of the fleet

A little set of friendly tools for people who build with Claude:

- [**Claude Meter**](https://github.com/JackBhanded/claude-meter) — see your Claude usage on your taskbar.
- [**Claude Lifeboat**](https://github.com/JackBhanded/claude-lifeboat) — back up and restore your Claude data.
- [**Claude Lifejacket**](https://github.com/JackBhanded/claude-lifejacket) — keep every chat aware of your projects.
- [**Claude Compass**](https://github.com/JackBhanded/claude-compass) — keep every chat tuned to how you like to work.
- **Claude Parachute** — you are here. The undo button for what Claude Code can't undo.

## About the author

Built by **Jack Bhanded** ([@JackBhanded](https://github.com/JackBhanded)) — part
of an open-source fleet of small, friendly tools that make building with Claude
calmer and safer.

## License

MIT — see [LICENSE](LICENSE). Free to use, share, and build on.
