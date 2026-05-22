"""Enable ``python -m claude_parachute ...``. The Claude Code hooks invoke the
package this way (with the absolute Python that installed it) so it works even
when the ``parachute`` launcher isn't on PATH."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
