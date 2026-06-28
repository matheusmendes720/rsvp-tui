"""``uv run tui | read | import | library | config | ...`` — thin pass-through.

Forwards straight to the canonical ``rsvp_tui.cli`` Click group
so the workspace surfaces (``uv run rsvp-read``, ``uv run
rsvp-import``) get exactly the same behaviour as the in-tree
``rsvp`` console script — same aliases, same grouped help, same
shell completion.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from ._lib import RSVP_TUI, run


def main(argv: Sequence[str] | None = None) -> int:
    # ``rsvp-read`` / ``rsvp-import`` are dispatched as
    # ``python -m scripts.run <name> [args]``. We want the CLI
    # to see exactly that: ``<name> [args]`` — so just forward
    # sys.argv verbatim. Click's group invocation reads from
    # ``sys.argv[1:]`` when no explicit args are given.
    return run(
        [sys.executable, "-m", "rsvp_tui.cli", *sys.argv[1:]],
        cwd=RSVP_TUI,
    )


if __name__ == "__main__":
    raise SystemExit(main())
