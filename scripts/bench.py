"""``uv run bench`` — cargo benchmark suite."""
from __future__ import annotations

import sys
from typing import Optional, Sequence

from ._lib import RSVP_CORE, ensure, run


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure("cargo")
    return run(["cargo", "bench", *args], cwd=RSVP_CORE)


if __name__ == "__main__":
    raise SystemExit(main())
