"""``uv run doctor`` — diagnose the local install.

A friendly wrapper around ``rsvp doctor`` that adds workspace-level
info (git status, lockfile age, Rust toolchain) on top.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from ._lib import ROOT, RSVP_TUI, ensure, header, info, ok, run, warn


def _git(args: List[str]) -> Optional[str]:
    if shutil.which("git") is None:
        return None
    try:
        out = subprocess.check_output(
            ["git", *args], cwd=ROOT, stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except subprocess.CalledProcessError:
        return None


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure("git")

    header("workspace")
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "?"
    dirty = _git(["status", "--porcelain"]) or ""
    info(f"branch: {branch}")
    info(f"dirty:  {'yes' if dirty else 'no'}")
    if dirty:
        warn(f"{len(dirty.splitlines())} uncommitted change(s)")

    header("rsvp doctor")
    rc = run(
        [sys.executable, "-m", "rsvp_tui.cli", "doctor", *args],
        cwd=RSVP_TUI,
    )
    if rc != 0:
        warn("rsvp doctor reported issues (see above)")
        return rc
    ok("rsvp doctor: healthy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
