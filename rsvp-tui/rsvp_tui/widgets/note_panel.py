"""Note panel widget for viewing and adding notes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

from ..managers.note_manager import NoteManager
from ..models import Note


class NotePanel(Vertical):
    """Side panel for viewing and managing notes."""

    DEFAULT_CSS = """
    NotePanel {
        width: 35;
        height: 100%;
        border: solid blue;
        padding: 1;
    }
    NotePanel Button {
        width: 100%;
    }
    NotePanel TextArea {
        height: 5;
    }
    """

    current_book_id = reactive[str | None](None)
    current_word_index = reactive[int](0)
    notes: reactive[list[Note]] = reactive(list[Note]())

    def __init__(
        self,
        note_manager: NoteManager,
        on_note_added: Callable[[int], Any] | None = None,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.note_manager = note_manager
        self.on_note_added = on_note_added
        # Per-book cache of parsed notes so watch_current_word_index
        # (which fires ~5x/s at 300 WPM) does NOT hit disk + JSON parse
        # on every tick. The cache is populated lazily on a book-id
        # cache miss (book switch) and explicitly invalidated by
        # refresh_notes() after an external save.
        self._notes_cache: dict[str, list[Note]] = {}

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield Label("Notes", id="notes-title")
        yield Button("Add Note", id="add-note-btn", variant="primary")
        yield Static(id="notes-list")

    def _ensure_notes_loaded(self) -> list[Note]:
        """Return all notes for ``current_book_id``, loading on cache miss.

        ``get_notes_for_book`` performs the disk read + JSON parse +
        ``Note.from_dict()`` reconstruction; callers that just want
        "notes near position X" should use ``_filter_for_position``
        instead to avoid redundant disk I/O.
        """
        book_id = self.current_book_id
        if not book_id:
            return []
        cached = self._notes_cache.get(book_id)
        if cached is None:
            try:
                cached = self.note_manager.get_notes_for_book(book_id)
            except Exception:  # noqa: BLE001 — disk/JSON failure → empty list
                cached = []
            self._notes_cache[book_id] = cached
        return cached

    def _filter_for_position(self) -> list[Note]:
        """Return notes within ±50 words of current_word_index (no I/O)."""
        notes = self._ensure_notes_loaded()
        return [
            n for n in notes
            if abs(n.word_index - self.current_word_index) <= 50
        ]

    def watch_current_book_id(self, new_book_id: str | None) -> None:
        """React to book change: a new book_id is automatically a cache miss,
        so ``_ensure_notes_loaded`` reloads; we just re-render."""
        self.notes = self._filter_for_position()
        self._update_display()

    def watch_current_word_index(self, index: int) -> None:
        """React to word index changes.

        Per-tick (5+ Hz at 300 WPM): only refilter the already-cached
        notes for the current book. No disk read, no JSON parse.
        """
        self.notes = self._filter_for_position()
        self._update_display()

    def _load_notes(self) -> None:
        """Force a full reload from disk for the current book.

        Use when notes have been added/edited externally and the cache
        must reflect the new state. Public callers should prefer
        ``refresh_notes()``; this is a building block.
        """
        if not self.current_book_id:
            return
        # Drop the cached entry for this book so _ensure_notes_loaded
        # re-reads from disk on the next watcher tick.
        self._notes_cache.pop(self.current_book_id, None)
        self.notes = self._filter_for_position()
        self._update_display()

    def _update_display(self) -> None:
        """Update the notes display."""
        notes_list = self.query_one("#notes-list", Static)

        if not self.notes:
            notes_list.update("No notes near this position.")
            return

        lines = []
        for note in self.notes:
            offset = note.word_index - self.current_word_index
            if offset == 0:
                pos = "current"
            elif offset > 0:
                pos = f"+{offset} words"
            else:
                pos = f"{offset} words"

            content = note.content[:50] + "..." if len(note.content) > 50 else note.content
            lines.append(f"[dim]{pos}[/] {content}")

        notes_list.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "add-note-btn":
            self.action_add_note()

    def action_add_note(self) -> None:
        """Open add note dialog."""
        # This would open a modal dialog
        # For now, just a placeholder
        if self.on_note_added:
            self.on_note_added(self.current_word_index)

    def set_position(self, book_id: str, word_index: int) -> None:
        """Update the current reading position."""
        self.current_book_id = book_id
        self.current_word_index = word_index

    def refresh_notes(self) -> None:
        """Refresh the notes display."""
        self._load_notes()
