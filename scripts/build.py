"""``uv run rsvp-build`` / ``uv run rsvp-dev`` — build the Rust extension
and install the Python package.

* ``uv run rsvp-build``        — release build, non-editable install.
* ``uv run rsvp-dev``          — editable install (maturin develop --release).

Both also defensively re-install ``rsvp-tui`` and ``rsvp-core``
as editable packages, because uv 0.11 with ``package = true`` on
the workspace root skips the workspace members. Pass ``--no-rust``
to skip the Rust rebuild (e.g. when iterating on Python and the
binary is already importable).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from ._lib import ROOT, RSVP_CORE, ensure, err, header, info, ok, run


def _parse(argv: Optional[List[str]]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="uv run rsvp-build",
        description="Build the RSVP Rust extension and install the Python package.",
    )
    p.add_argument(
        "--editable", "-e", action="store_true",
        help="Editable install (maturin develop) — default for `uv run rsvp-dev`.",
    )
    p.add_argument(
        "--no-rust", action="store_true",
        help="Skip the Rust rebuild; assume the binary is already importable.",
    )
    p.add_argument(
        "--debug", action="store_true",
        help="Build with cargo profile=debug (faster, slower Python).",
    )
    return p.parse_args(list(argv or ()))


def _ensure_python_packages() -> None:
    """``uv sync`` only installs the workspace wheel when
    ``package = true`` is set, which drops the workspace members
    (``rsvp-tui`` and ``rsvp-core``). Install them explicitly as
    editable installs so ``import rsvp_tui`` and ``import
    rsvp_core`` both work after ``uv sync``.

    We resolve ``uv`` to its absolute path so the subprocess
    works even when the venv's ``Scripts`` directory isn't on
    PATH (the helper is invoked from the venv where uv is the
    parent process, but the child may inherit a sanitised PATH
    on Windows).
    """
    import shutil

    uv = shutil.which("uv")
    if uv is None:
        err("`uv` not found on PATH; skipping member install")
        return
    for pkg in ("rsvp-tui", "rsvp-core"):
        info(f"ensuring {pkg} is installed editable")
        proc = subprocess.run(
            [uv, "pip", "install", "-e", str(ROOT / pkg)],
            cwd=ROOT,
            check=False,
        )
        if proc.returncode != 0:
            err(f"failed to install {pkg}; continuing anyway")


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse(argv)
    header("RSVP build")
    if args.editable:
        info("mode: editable (maturin develop)")
    else:
        info("mode: release wheel (pip install)")

    _ensure_python_packages()

    if not args.no_rust:
        ensure("cargo", "maturin")
        if not (RSVP_CORE / "Cargo.toml").exists():
            err(f"no Cargo.toml in {RSVP_CORE}")
            return 1
        # Invoke maturin as a Python module (``python -m maturin``)
        # because uv installs the package without putting ``maturin``
        # on PATH inside the venv. The ``--uv`` flag tells it to
        # forward the install step to ``uv pip`` so the binary
        # lands in the correct venv.
        cmd: List[str] = [sys.executable, "-m", "maturin", "develop", "--release", "--uv"]
        if args.editable:
            pass  # ``--uv`` is the editable-friendly form already
        if args.debug:
            # maturin's --profile flag replaces the leading flag
            cmd = [sys.executable, "-m", "maturin", "develop", "--profile=dev", "--uv"]
        if run(cmd, cwd=RSVP_CORE) != 0:
            return 1
        ok("Rust extension built and installed")
    else:
        info("--no-rust: assuming rsvp_core is already importable")

    ok("build complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
