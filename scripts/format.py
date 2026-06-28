"""``uv run format`` — black + ruff --fix."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from ._lib import ROOT, ensure, ok, run


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure("black", "ruff")

    rc = run(
        [sys.executable, "-m", "black", "rsvp-tui", "scripts", *args],
        cwd=ROOT,
    )
    if rc != 0:
        return rc
    ok("black: reformatted")

    rc = run(
        [sys.executable, "-m", "ruff", "check", "--fix", "rsvp-tui", "scripts", *args],
        cwd=ROOT,
    )
    if rc != 0:
        return rc
    ok("ruff: auto-fixed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
