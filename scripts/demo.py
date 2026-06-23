"""``uv run demo`` — launch the dependency-free standalone demo."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

from ._lib import ROOT, err, run

# The repo ships a no-deps demo that exercises the core renderer.
# It's at the workspace root, not inside rsvp-tui/.
DEMO = ROOT / "demo_tui.py"


def main(argv: Optional[Sequence[str]] = None) -> int:
    if not DEMO.exists():
        err(f"demo not found at {DEMO}")
        return 1
    args = list(sys.argv[1:] if argv is None else argv)
    return run([sys.executable, str(DEMO), *args], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
