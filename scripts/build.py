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

from ._lib import ROOT, RSVP_CORE, ensure, err, header, info, ok, run, warn


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="uv run rsvp-build",
        description="Build the RSVP Rust extension and install the Python package.",
    )
    p.add_argument(
        "--editable",
        "-e",
        action="store_true",
        help="Editable install (maturin develop) — default for `uv run rsvp-dev`.",
    )
    p.add_argument(
        "--no-rust",
        action="store_true",
        help="Skip the Rust rebuild; assume the binary is already importable.",
    )
    p.add_argument(
        "--debug",
        action="store_true",
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


def _build_rust_cli() -> None:
    """Build the rsvp-cli Rust binary (the native 2.4MB
    clap+ratatui CLI). The result lands at
    ``rsvp-cli/target/release/rsvp[.exe]``.

    We only build when the source actually changed or the
    binary is missing — ``cargo build --release`` is fast on
    an incremental build.
    """
    import platform
    import shutil

    rsvp_cli = ROOT / "rsvp-cli"
    if not (rsvp_cli / "Cargo.toml").exists():
        info("rsvp-cli/Cargo.toml missing; skipping Rust CLI build")
        return
    cargo = shutil.which("cargo")
    if cargo is None:
        warn("cargo not on PATH; skipping Rust CLI build")
        return
    binname = "rsvp.exe" if platform.system() == "Windows" else "rsvp"
    binpath = rsvp_cli / "target" / "release" / binname
    if binpath.exists():
        info("rsvp-cli binary already up to date; skipping cargo build")
        return
    info("$ cargo build --release   (cwd=rsvp-cli)")
    proc = subprocess.run(
        [cargo, "build", "--release"],
        cwd=rsvp_cli,
        check=False,
    )
    if proc.returncode != 0:
        warn("cargo build of rsvp-cli failed; the binary will be unavailable")


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    header("RSVP build")
    if args.editable:
        info("mode: editable (maturin develop)")
    else:
        info("mode: release wheel (pip install)")

    # Order matters here:
    #   1. Build the standalone Rust CLI binary first (no
    #      effect on site-packages).
    #   2. Build the rsvp-core pyo3 extension via maturin
    #      (this REPLACES the editable install of rsvp-tui
    #      because maturin's pip install is destructive).
    #   3. Re-install rsvp-tui and rsvp-core as editable
    #      packages afterwards so ``import rsvp_tui`` and
    #      ``import rsvp_core`` both work.
    _build_rust_cli()

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
        cmd: list[str] = [sys.executable, "-m", "maturin", "develop", "--release", "--uv"]
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

    # After maturin ran we defensively re-install both workspace
    # members so ``import rsvp_tui`` and ``import rsvp_core``
    # both work.
    _ensure_python_packages()

    ok("build complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
