"""``uv run clean`` — remove build artefacts.

Removes (in this order, never anything outside the workspace):

  * ``rsvp-tui/build/``           — setuptools-rust output
  * ``rsvp-tui/dist/``            — wheel/sdist
  * ``rsvp-tui/rsvp_tui.egg-info``
  * ``rsvp-core/target/``         — cargo build output
  * All ``__pycache__/``          — Python bytecode
  * All ``*.pyc``                 — loose bytecode
  * Test caches: ``.pytest_cache``, ``.ruff_cache``, ``.mypy_cache``

Use ``--all`` to also remove ``.venv/`` and the lock file.
"""

from __future__ import annotations

import argparse
import shutil
from collections.abc import Sequence
from pathlib import Path

from ._lib import ROOT, info, ok, warn

TARGETS = [
    "rsvp-tui/build",
    "rsvp-tui/dist",
    "rsvp-tui/rsvp_tui.egg-info",
    "rsvp-core/target",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".coverage",
    "htmlcov",
]
NUCLEAR = [".venv", "uv.lock"]


def _rm(p: Path) -> None:
    if not p.exists():
        return
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    else:
        try:
            p.unlink()
        except OSError as e:
            warn(f"could not remove {p}: {e}")


def _walk_pycache(root: Path) -> list[Path]:
    return [p for p in root.rglob("__pycache__") if p.is_dir()]


def _walk_pyc(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.pyc") if p.is_file()]


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="uv run clean")
    p.add_argument(
        "--all", action="store_true", help="Also remove .venv/ and uv.lock (full reset)."
    )
    p.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Print what would be removed, but do not delete.",
    )
    args = p.parse_args(list(argv or ()))

    targets: list[Path] = [(ROOT / t) for t in TARGETS]
    targets += _walk_pycache(ROOT)
    targets += _walk_pyc(ROOT)
    if args.all:
        targets += [ROOT / t for t in NUCLEAR]

    seen: set = set()
    for t in targets:
        if t in seen:
            continue
        seen.add(t)
        rel = t.relative_to(ROOT) if t.is_absolute() else t
        if args.dry_run:
            info(f"would remove: {rel}")
            continue
        if t.exists():
            info(f"removing: {rel}")
            _rm(t)
    ok("clean complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
