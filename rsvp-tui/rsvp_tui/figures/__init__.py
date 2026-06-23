"""Figure package — all visualization modes for the RSVP TUI.

The figure package exposes the concrete figure classes and a default
registry. The eight figures are registered in this order so the
hotkeys 1-8 map consistently:

    1: Word  (single-word ORP, the classic)
    2: Chunk (3-word window with ORP on the first)
    3: Line  (full line, current word highlighted)
    4: Bionic (bionic-style bolding of word prefixes)
    5: Spritz (pivot-character highlight)
    6: Pacer (word + pacer dots showing progress)
    7: MiniMap (vertical scrubber + reading line)
    8: Stats (WPM sparkline + ETA overlay)

Adding a new figure: implement a subclass of ``Figure`` in its own
module, add a one-line import + registration in ``registry.py``.
"""

from .base import Figure, FigureState
from .registry import FigureRegistry, default_registry, reset_default_registry

__all__ = [
    "Figure",
    "FigureState",
    "FigureRegistry",
    "default_registry",
    "reset_default_registry",
]
