"""Textual message types used across the new screens.

Messages let screens communicate without holding direct references to
each other. The convention: the ``ReaderScreen`` *emits* these, the
``RSVPApp`` *handles* them. This keeps screens decoupled and makes
them easy to unit-test (just listen for the messages on a fake app).

Why a dedicated module: figure events are referenced from both
``reader_screen.py`` and tests, and Textual requires message types to
be importable. Putting them in their own module avoids the circular
imports that would happen if they lived inside the screens.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from textual.message import Message


@dataclass
class FigureChanged(Message):
    """A figure swap completed.

    Emitted by ``ReaderScreen`` after a successful figure swap. The
    app uses it to persist the new ``figure_id`` in config and show
    a toast.

    Attributes:
        prev_id: Figure id that was unmounted (``None`` for the
            initial mount).
        next_id: Figure id that is now active.
    """

    prev_id: Optional[str] = None
    next_id: str = ""


@dataclass
class FigureStateAdvanced(Message):
    """A figure advanced one word.

    Emitted by ``ReaderScreen`` (not the figure itself — the screen
    translates the figure's reactive ``word_index`` change into this
    message). The app uses it to update library progress and
    auto-save every N words.
    """

    index: int = 0
    book_id: Optional[str] = None


@dataclass
class FigureCompleted(Message):
    """The figure reached the last word of the active book.

    Emitted once per session when the index hits ``len(words) - 1``.
    The app marks the book as complete and shows a toast.
    """

    book_id: Optional[str] = None


@dataclass
class ConfigChanged(Message):
    """Any config field was updated.

    The app uses this to invalidate caches (e.g. theme cache) and to
    flush the in-memory config to disk via ``ConfigManager.update``.
    """

    keys: tuple = ()


@dataclass
class BookOpened(Message):
    """The user selected a book from the library.

    Carries the book id; the app loads words and pushes the
    ReaderScreen.
    """

    book_id: str = ""


__all__ = [
    "FigureChanged",
    "FigureStateAdvanced",
    "FigureCompleted",
    "ConfigChanged",
    "BookOpened",
]
