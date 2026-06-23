"""``uv run docs`` — generate man page + Markdown reference.

Right now this is a thin wrapper around the man-page helper. It also
dumps the in-TUI help text (``uv run tui --help``) into ``docs/``
for browsing without a TTY.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Sequence

from ._lib import DOCS_DIR, MAN_DIR, ROOT, RSVP_TUI, info, ok, run

from .man import main as man_main


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    DOCS_DIR.mkdir(exist_ok=True)
    MAN_DIR.mkdir(exist_ok=True)

    # 1. Build/install the man page.
    info("building man page")
    rc = man_main([])
    if rc != 0:
        return rc
    ok("man page ready")

    # 2. Snapshot the CLI help text.
    help_path = DOCS_DIR / "cli-help.txt"
    info(f"writing CLI help snapshot to {help_path.relative_to(ROOT)}")
    with help_path.open("w", encoding="utf-8") as fh:
        proc = subprocess_run = __import__("subprocess").run(
            [sys.executable, "-m", "rsvp_tui.cli", "--help"],
            cwd=RSVP_TUI, capture_output=True, text=True, check=False,
        )
        fh.write(proc.stdout)
        if proc.stderr:
            fh.write("\n--- stderr ---\n")
            fh.write(proc.stderr)
    ok("CLI help snapshot written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
