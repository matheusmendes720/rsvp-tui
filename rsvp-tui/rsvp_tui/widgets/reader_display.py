"""Backward-compatible re-export of the new WordFigure.

The legacy ``ReaderDisplay`` widget has been refactored into
``figures.word.WordFigure`` as part of the Phase 1 figure system
work. This module preserves the old import path so callers
(``app.py:15``) keep working.

If you're new to the codebase, prefer importing from
``rsvp_tui.figures.word`` directly.

Lazy attribute access (PEP 562)
--------------------------------
We use ``__getattr__`` to defer the import of ``WordFigure`` and
the deprecation warning until the symbol is actually requested.
This means ``from rsvp_tui.widgets import reader_display`` (or
``from rsvp_tui.widgets import *``) does NOT emit a warning at
import time — only when someone explicitly accesses
``ReaderDisplay`` does the migration hint surface.

This keeps the warning honest (it fires when the deprecated
API is actually being used) instead of being a passive tax on
every test that touches the widgets package.
"""
from __future__ import annotations

import warnings


def __getattr__(name: str):
    """PEP 562 lazy attribute access for ``ReaderDisplay``.

    The first time a caller does
    ``from .reader_display import ReaderDisplay`` (or otherwise
    looks up that name on this module) we:

      1. Emit the deprecation warning.
      2. Forward to the new ``WordFigure`` class.
    """
    if name == "ReaderDisplay":
        warnings.warn(
            "rsvp_tui.widgets.ReaderDisplay is deprecated; "
            "use rsvp_tui.figures.word.WordFigure instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from ..figures.word import WordFigure

        # Cache the resolved symbol on the module so subsequent
        # attribute lookups don't re-warn.
        globals()["ReaderDisplay"] = WordFigure
        return WordFigure
    if name == "WordFigure":
        # Re-export the new symbol for the lazy-import path so
        # ``from .reader_display import WordFigure`` works
        # without touching the deprecation warning at all.
        from ..figures.word import WordFigure

        globals()["WordFigure"] = WordFigure
        return WordFigure
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ReaderDisplay", "WordFigure"]
