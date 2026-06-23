"""``uv run lint`` — ruff + black --check.

Two tools, one command:

* ``ruff check rsvp-tui/ scripts/`` — fast static analysis.
* ``black --check rsvp-tui/ scripts/`` — formatting drift detector.

Exits non-zero if either tool reports a problem. Pass ``--fix`` to
upgrade ``lint`` into ``format`` for the ruff side; for black you
still need ``uv run format``.
"""
from __future__ import annotations

import sys
from typing import Optional, Sequence

from ._lib import ROOT, ensure, err, header, ok, run


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    fix = "--fix" in args
    args = [a for a in args if a != "--fix"]

    ensure("ruff", "black")
    header("ruff check")
    ruff_args = ["check"]
    if fix:
        ruff_args.append("--fix")
    ruff_args += ["rsvp-tui", "scripts"]
    rc = run([sys.executable, "-m", "ruff", *ruff_args], cwd=ROOT)
    if rc != 0:
        return rc
    ok("ruff: clean")

    if fix:
        # ``format`` is the bigger hammer; defer to the format helper.
        from .format import main as fmt_main
        return fmt_main([])

    header("black --check")
    return run(
        [sys.executable, "-m", "black", "--check", "rsvp-tui", "scripts"],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
