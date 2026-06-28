"""``uv run rsvp-typecheck`` — mypy --strict."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from ._lib import ensure, run


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure("mypy")
    return run(
        [
            sys.executable,
            "-m",
            "mypy",
            "rsvp-tui",
            "scripts",
            "rsvp_workspace",
            *args,
        ],
        cwd=None,  # use the workspace root so mypy finds the
        # exclude list and resolves the path filters
    )


if __name__ == "__main__":
    raise SystemExit(main())
