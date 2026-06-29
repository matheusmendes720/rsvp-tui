"""Shared utilities for the helper scripts.

Centralises path discovery, coloured logging, and subprocess
invocation so each helper stays small and readable.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

# The workspace root is the parent of the ``scripts/`` package.
ROOT: Path = Path(__file__).resolve().parent.parent
PYPROJECT: Path = ROOT / "pyproject.toml"
RSVP_TUI: Path = ROOT / "rsvp-tui"
RSVP_CORE: Path = ROOT / "rsvp-core"
SCRIPTS: Path = ROOT / "scripts"
MAN_DIR: Path = ROOT / "man"
DOCS_DIR: Path = ROOT / "docs"
DATA_DIR: Path = Path(os.environ.get("RSVP_HOME", Path.home() / ".rsvp"))


# ---- terminal output ------------------------------------------------------

_IS_TTY = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _IS_TTY else text


def info(msg: str) -> None:
    print(_c("36", f"  · {msg}"))


def step(msg: str) -> None:
    print(_c("1;34", f"==> {msg}"))


def ok(msg: str) -> None:
    print(_c("32", f"  ✓ {msg}"))


def warn(msg: str) -> None:
    print(_c("33", f"  ! {msg}"), file=sys.stderr)


def err(msg: str) -> None:
    print(_c("31;1", f"  ✗ {msg}"), file=sys.stderr)


def header(title: str) -> None:
    bar = "─" * max(0, 60 - len(title) - 2)
    print(_c("1;30", f"\n── {title} {bar}"))


# ---- subprocess -----------------------------------------------------------


def run(
    cmd: Sequence[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
    env: dict[str, str] | None = None,
    stream: bool = True,
) -> int:
    """Run ``cmd``; print a friendly header; return exit code.

    ``stream=True`` forwards stdout/stderr live (used for build/test
    output where the user wants to see the progress). ``stream=False``
    captures output (used when we'll do our own summary).
    """
    pretty = " ".join(cmd)
    info(f"$ {pretty}" + (f"   (cwd={cwd})" if cwd else ""))
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd) if cwd else None,
        env={**os.environ, **(env or {})},
        check=False,
    )
    if check and proc.returncode != 0:
        err(f"command failed (exit {proc.returncode}): {pretty}")
    return proc.returncode


def have(cmd: str) -> bool:
    """Return True if ``cmd`` is on PATH."""
    return shutil.which(cmd) is not None


def ensure(*tools: str) -> list[str]:
    """Warn about any missing tools. Returns the list of missing names."""
    missing = [t for t in tools if not have(t)]
    if missing:
        warn(f"missing tools: {', '.join(missing)} (some tasks will be skipped)")
    return missing


__all__ = [
    "ROOT",
    "PYPROJECT",
    "RSVP_TUI",
    "RSVP_CORE",
    "SCRIPTS",
    "MAN_DIR",
    "DOCS_DIR",
    "DATA_DIR",
    "info",
    "step",
    "ok",
    "warn",
    "err",
    "header",
    "run",
    "have",
    "ensure",
]
