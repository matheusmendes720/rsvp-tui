"""Note panel widget for viewing and adding notes."""

from collections.abc import Callable

from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

from ..managers.note_manager import NoteManager


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

    current_book_id = reactive(None)
    current_word_index = reactive(0)
    notes = reactive(list)

    def __init__(
        self,
        note_manager: NoteManager,
        on_note_added: Callable | None = None,
    ):
        super().__init__()
        self.note_manager = note_manager
        self.on_note_added = on_note_added

    def compose(self):
        """Compose the widget."""
        yield Label("Notes", id="notes-title")
        yield Button("Add Note", id="add-note-btn", variant="primary")
        yield Static(id="notes-list")

    def watch_current_word_index(self, index: int):
        """React to word index changes."""
        self._load_notes()

    def _load_notes(self):
        """Load notes for current position."""
        if not self.current_book_id:
            return

        self.notes = self.note_manager.get_notes_for_position(
            self.current_book_id,
            self.current_word_index,
            context_window=50,
        )
        self._update_display()

    def _update_display(self):
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

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "add-note-btn":
            self.action_add_note()

    def action_add_note(self):
        """Open add note dialog."""
        # This would open a modal dialog
        # For now, just a placeholder
        if self.on_note_added:
            self.on_note_added(self.current_word_index)

    def set_position(self, book_id: str, word_index: int):
        """Update the current reading position."""
        self.current_book_id = book_id
        self.current_word_index = word_index

    def refresh_notes(self):
        """Refresh the notes display."""
        self._load_notes()
