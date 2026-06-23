"""``uv run typecheck`` — mypy strict."""
from __future__ import annotations

import sys
from typing import Optional, Sequence

from ._lib import ROOT, ensure, run


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure("mypy")
    return run(
        [sys.executable, "-m", "mypy", "rsvp-tui", "scripts", *args],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
