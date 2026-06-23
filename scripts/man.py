"""``uv run man`` — render the man page and optionally install it.

Generates ``man/rsvp.1`` from a Python-side template (so the page
stays in sync with the click help) and offers an install target
that copies it to the user's ``~/.local/share/man/man1/`` for
``man rsvp`` to work.

Subcommands:

    uv run man              # render rsvp.1
    uv run man --view       # render and pipe through `man -l -`
    uv run man --install    # render and copy to $MANPATH/man1/
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Sequence

from ._lib import MAN_DIR, ROOT, err, header, info, ok, warn

# The actual page is hand-written in scripts/_man_template.py so we
# get Python f-strings, conditionals, and triple-quoted sections
# without any extra build step. Keeping the man source in Python
# also means the project banner, version, and key lists are pulled
# from a single source of truth.
from . import _man_template as tpl


def _render() -> Path:
    MAN_DIR.mkdir(exist_ok=True)
    out = MAN_DIR / "rsvp.1"
    out.write_text(tpl.render(), encoding="utf-8")
    return out


def _view(page: Path) -> int:
    if shutil.which("man") is None:
        warn("`man` not found on PATH; printing raw page to stdout instead")
        sys.stdout.write(page.read_text(encoding="utf-8"))
        return 0
    proc = __import__("subprocess").run(
        ["man", "-l", "-", page],
        input=page.read_bytes(),
        check=False,
    )
    return proc.returncode


def _install(page: Path) -> int:
    # Honour $MANPATH; fall back to ~/.local/share/man.
    base = os.environ.get("MANPATH", "").split(os.pathsep)
    targets = [Path(p) / "man1" for p in base if p]
    targets.append(Path.home() / ".local" / "share" / "man" / "man1")
    for dest in targets:
        try:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(page, dest / "rsvp.1")
            ok(f"installed to {dest / 'rsvp.1'}")
            return 0
        except OSError as e:
            warn(f"could not install to {dest}: {e}")
    err("no writable MANPATH location found")
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="uv run man")
    p.add_argument("--view", action="store_true",
                   help="Render and pipe through `man -l -`.")
    p.add_argument("--install", action="store_true",
                   help="Render and copy to $MANPATH/man1/.")
    args = p.parse_args(list(argv or ()))

    header("man · render")
    page = _render()
    info(f"wrote {page.relative_to(ROOT)}")
    ok("man page rendered")

    if args.view:
        return _view(page)
    if args.install:
        return _install(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
