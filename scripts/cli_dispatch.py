"""``uv run rsvp-cli`` — launch the native Rust CLI binary.

This is a thin wrapper around ``rsvp-cli/target/release/rsvp.exe``
(the canonical 2.4MB statically-linked Rust binary built with
clap + ratatui). When the binary is missing, we attempt a
``cargo build --release`` first; if cargo isn't available, we
print a clear message and exit non-zero so the user knows what
to do.

Why a Python wrapper instead of a direct console script:
  * The Rust binary's path varies by platform and build
    configuration. A Python shim is the simplest way to
    *always* find the right one.
  * The Python side can re-export ``--help`` for ``rsvp-cli``
    even when the Rust binary hasn't been built yet (e.g. on a
    fresh ``uv sync``), so the help text is always accessible.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from ._lib import ROOT, err, info, run

# Conventional release-build path. The build helper in
# scripts/build.py puts the binary here.
_RSVP_CLI_RELEASE = (
    ROOT
    / "rsvp-cli"
    / "target"
    / "release"
    / ("rsvp.exe" if platform.system() == "Windows" else "rsvp")
)


def _find_binary() -> Path | None:
    """Locate the Rust CLI binary.

    Search order:
      1. ``rsvp-cli/target/release/rsvp[.exe]`` (the canonical path)
      2. Anywhere on ``PATH`` (in case the user moved it)
      3. ``CARGO_HOME`` workspace target (rare)
    """
    if _RSVP_CLI_RELEASE.exists():
        return _RSVP_CLI_RELEASE
    on_path = shutil.which("rsvp")
    if on_path:
        return Path(on_path)
    return None


def _build_binary() -> bool:
    """Run ``cargo build --release`` in the rsvp-cli directory.

    Returns True on success. We never fail loudly here — the
    caller will print a friendly message if the build is
    still missing.
    """
    info("rsvp-cli binary not found; building it now")
    cargo = shutil.which("cargo")
    if cargo is None:
        return False
    rsvp_cli = ROOT / "rsvp-cli"
    if not (rsvp_cli / "Cargo.toml").exists():
        return False
    info(f"$ cargo build --release   (cwd={rsvp_cli})")
    proc = subprocess.run(
        [cargo, "build", "--release"],
        cwd=rsvp_cli,
        check=False,
    )
    return proc.returncode == 0 and _RSVP_CLI_RELEASE.exists()


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    # ``--help`` / ``-h`` / no args: print help without needing
    # the binary to be present.
    if not args or "--help" in args or "-h" in args:
        info("rsvp-cli — native Rust CLI (clap + ratatui)")
        info("The rsvp-cli binary lives at:\n" f"  {_RSVP_CLI_RELEASE}\n")
        info("Build it with: uv run rsvp-build-rust  (or: cargo build --release -p rsvp-cli)")
        info("Then run:        uv run rsvp-cli --help")
        # Try the binary anyway so the user sees the canonical
        # help. If it's missing, fall back to a clear message.
        binpath = _find_binary()
        if binpath is not None:
            return run([str(binpath), *args])
        return 0

    binpath = _find_binary()
    if binpath is None:
        if not _build_binary():
            err("could not build the rsvp-cli binary")
            err("install Rust:  https://rustup.rs")
            err("then:           cargo build --release -p rsvp-cli")
            return 1
        binpath = _find_binary()
    if binpath is None:
        err("rsvp-cli binary still not found after build")
        return 1
    # Forward exit code from the binary.
    return run([str(binpath), *args])


if __name__ == "__main__":
    raise SystemExit(main())
