#!/usr/bin/env python3
"""Entry point for ``python -m rsvp_tui``.

Routes through :func:`rsvp_tui.cli.main` so ``python -m rsvp_tui`` and
the ``rsvp`` / ``rsvp-tui`` console scripts land on the SAME entry point
(the modular ``rsvp_tui.app.RSVPApp`` path that's actually tested and
audited).
"""

from .cli import main

if __name__ == "__main__":
    main()
