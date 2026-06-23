"""``uv run verify`` — full quality gate: lint + typecheck + test.

Use this in CI and before pushing. Returns the first non-zero exit
code so the failure is easy to spot.
"""
from __future__ import annotations

import sys
from typing import Optional, Sequence

from ._lib import err, header

from .lint import main as lint_main
from .test import main as test_main
from .typecheck import main as typecheck_main


_STAGES = [
    ("lint", lint_main),
    ("typecheck", typecheck_main),
    ("test", test_main),
]


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    for name, fn in _STAGES:
        header(f"verify · {name}")
        rc = fn(args)
        if rc != 0:
            err(f"{name} failed (exit {rc})")
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
