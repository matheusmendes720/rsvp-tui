#!/usr/bin/env python3
"""Launcher for the RSVP TUI.

Routes through :func:`rsvp_tui.cli.main` so this script and the
``rsvp`` / ``rsvp-tui`` console scripts and ``python -m rsvp_tui``
all land on the SAME entry point. Previously this file did its own
``sys.path.insert`` and imported ``rsvp_tui.app_complete.RSVPTUI`` —
that class lived only in the legacy monolithic runtime (now removed)
and the launcher would silently ImportError against the modular
``rsvp_tui.app.RSVPApp`` path that the package actually ships.
"""

import sys
from pathlib import Path

# Make the launcher work from a plain checkout (``python launch_rsvp.py``)
# where the package is not installed: put ``rsvp-tui/`` on the path.
sys.path.insert(0, str(Path(__file__).parent / "rsvp-tui"))

from rsvp_tui.cli import main  # noqa: E402 — needs the sys.path above

if __name__ == "__main__":
    main()