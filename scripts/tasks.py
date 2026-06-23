"""``uv run tasks`` — print the workspace task table.

Introspects the same ``[tool.uv.scripts]`` table we wrote into
``pyproject.toml`` so the help text here can't drift from the
real surface.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path
from typing import Optional, Sequence

from ._lib import PYPROJECT, ok

_DESCRIPTIONS = {
    "tui":        "Launch the interactive TUI (default)",
    "read":       "Read a book by file path (alias: r)",
    "import":     "Import a book into the library (alias: i)",
    "library":    "Manage the book library (alias: ls)",
    "config":     "Open the live settings UI",
    "doctor":     "Diagnose the local install",
    "themes":     "List the available themes",
    "where":      "Show data directory paths",
    "version":    "Show version, Python, and platform info",
    "palette":    "Open the in-TUI command palette",
    "demo":       "Launch the dependency-free standalone demo",
    "build":      "Build the Rust extension + install the Python pkg",
    "dev":        "Editable install (maturin develop --release)",
    "sync":       "uv sync (optionally --rebuild the Rust ext)",
    "clean":      "Remove build/, dist/, __pycache__, eggs, caches",
    "test":       "Run the pytest suite (extras forwarded)",
    "lint":       "ruff check + black --check",
    "format":     "black + ruff --fix",
    "typecheck":  "mypy --strict",
    "verify":     "lint + typecheck + test (full quality gate)",
    "docs":       "Build man page + snapshot CLI help",
    "man":        "Render / view / install rsvp.1",
    "bench":      "Run cargo benchmarks (Rust micro-benchmarks)",
    "tasks":      "Print this task table",
}


def _load() -> dict:
    """Load the workspace ``pyproject.toml``.

    The task table is populated from two places:

    * ``[project.scripts]``   — the real console-script entry points
                                (what ``uv run rsvp-*`` actually invokes).
    * ``[tool.uv.scripts]``   — uv 0.12+ (forward-compat) for users on a
                                newer uv that supports it.

    We prefer the explicit ``[project.scripts]`` table because it is
    the one uv 0.11 actually honours.
    """
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts: dict = dict(data.get("project", {}).get("scripts", {}))
    scripts.update(data.get("tool", {}).get("uv", {}).get("scripts", {}))
    return scripts


def main(argv: Optional[Sequence[str]] = None) -> int:
    data = _load()
    scripts = dict(data)
    # Some workspaces declare scripts as ``rsvp-test`` while older
    # code expects ``test``; normalise the lookup so the table
    # renders for both layouts.
    def _lookup(name: str) -> str:
        for key in (name, name.removeprefix("rsvp-"), f"rsvp-{name}"):
            if key in _DESCRIPTIONS:
                return _DESCRIPTIONS[key]
        return "—"

    width = max((len(k) for k in scripts), default=8)
    print()
    print("  rsvp workspace — uv run task surface")
    print("  " + "─" * (width + 56))
    print(f"  {'task':<{width}}  {'runner':<32}  description")
    print("  " + "─" * (width + 56))
    for name, runner in scripts.items():
        print(f"  {name:<{width}}  {runner:<32}  {_lookup(name)}")
    print()
    print("  examples:")
    print("    uv run rsvp-tui              # launch the TUI")
    print("    uv run rsvp-read book.epub   # read a book")
    print("    uv run rsvp-test -k figure   # run figure tests")
    print("    uv run rsvp-lint --fix       # auto-fix lint issues")
    print("    uv run rsvp-clean --all      # full reset (incl. .venv)")
    print("    uv run rsvp-man --view       # render and view rsvp.1")
    print()
    ok(f"{len(scripts)} tasks available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
