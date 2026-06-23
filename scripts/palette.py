"""``uv run palette`` — open the in-TUI command palette from outside.

Sometimes you want to jump straight to the palette (Ctrl+P inside the
TUI) without first navigating. This helper:

  1. Boots the TUI in library mode.
  2. Pushes the CommandPaletteScreen on top.
  3. Lets the user fuzzy-filter and pick a command.

The actual screen lives in ``rsvp_tui.screens.command_palette``;
we just import-and-push it so the wiring stays in one place.
"""
from __future__ import annotations

import sys
from typing import Optional, Sequence

from ._lib import RSVP_TUI, err, run

# We import the app and the palette lazily so this module stays
# cheap to load. The actual Textual run loop blocks until the user
# exits the TUI.


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    # The shortest path: launch the TUI via the CLI and bind Ctrl+P
    # to push the palette. The palette is already triggered by the
    # keybinding on the ReaderScreen, so opening the library first
    # is enough — pressing Ctrl+P (or running the `palette` command
    # once inside) brings it up. We don't push it programmatically
    # because that would couple this script to Textual internals.
    snippet = (
        "from rsvp_tui.app import RSVPApp\n"
        "from rsvp_tui.screens.command_palette import CommandPaletteScreen\n"
        "app = RSVPApp()\n"
        "def _push():\n"
        "    app.push_screen(CommandPaletteScreen())\n"
        "app.call_later(_push)\n"
        "app.run()\n"
    )
    return run([sys.executable, "-c", snippet, *args], cwd=RSVP_TUI)


if __name__ == "__main__":
    raise SystemExit(main())
