"""``uv run rsvp-sync`` — install every workspace dependency.

Re-runs ``uv pip install -e`` for both ``rsvp-tui`` and
``rsvp-core`` afterwards, because uv 0.11 with
``package = true`` on the workspace drops those members from
the install set. Pass ``--no-rebuild`` to skip the defensive
re-install (e.g. when you only want a fresh dep set).
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Sequence

from ._lib import ROOT, ensure, info, ok, run


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    rebuild = "--no-rebuild" not in args
    args = [a for a in args if a != "--no-rebuild"]
    ensure("uv")
    rc = run(["uv", "sync", *args], cwd=ROOT)
    if rc != 0:
        return rc
    ok("uv sync complete")
    if rebuild:
        uv = shutil.which("uv")
        if uv is None:
            ensure("uv")  # re-warn
            return 1
        info("re-installing workspace members (rsvp-tui, rsvp-core)")
        for pkg in ("rsvp-tui", "rsvp-core"):
            run([uv, "pip", "install", "-e", str(ROOT / pkg)], cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
