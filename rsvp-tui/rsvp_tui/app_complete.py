#!/usr/bin/env python3
"""
RSVP-TUI: Complete Interactive Speed Reading Application

A fully-featured terminal UI for RSVP speed reading with:
- Rust backend for performance (with Python fallbacks)
- Library management with SQLite
- Note-taking at reading positions
- Multiple reading modes
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path
from typing import Any

from rich.align import Align
from rich.console import RenderableType

# Rich imports
from rich.panel import Panel
from rich.text import Text

# Textual imports
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.timer import Timer
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
    TextArea,
)

# Local imports
try:
    from . import (
        calculate_orp_index,
        calculate_word_delay,
        parse_epub_bytes,
        parse_markdown,
        parse_plain_text,
        split_word_for_display,
        tokenize_text,
    )
    from .logging_ import telemetry_error
    from .managers.library_manager import LibraryManager
    from .managers.note_manager import NoteManager
    from .models import Book, Config

    IMPORT_OK = True
except ImportError as _exc:
    # Fallback imports for direct script execution
    import traceback as _tb

    sys.stderr.write(f"[app_complete] import error: {_exc}\n{_tb.format_exc()}\n")
    # Re-raise so the failure is visible rather than silent
    raise


# =============================================================================
# RSVP DISPLAY WIDGET
# =============================================================================


class RSVPWordDisplay(Static):
    """Widget that displays RSVP words with ORP highlighting."""

    DEFAULT_CSS = """
    RSVPWordDisplay {
        content-align: center middle;
        text-align: center;
        height: 100%;
    }
    """

    current_word: reactive[str] = reactive("")
    word_index: reactive[int] = reactive(0)
    total_words: reactive[int] = reactive(0)
    wpm: reactive[int] = reactive(300)
    is_playing: reactive[bool] = reactive(False)
    enable_orp: reactive[bool] = reactive(True)

    def __init__(self, words: list[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.words = words
        self.total_words = len(words)
        self._timer: Timer | None = None
        self.punctuation_multiplier = 2.0
        self.pause_chars = [".", "!", "?", ";", ":"]
        self.on_word_change = None
        self.on_complete = None

    def render(self) -> RenderableType:
        """Render the RSVP word display."""
        if not self.words or self.word_index >= len(self.words):
            return Panel(
                Align.center(Text("Reading Complete! Press 'r' to restart.", style="dim green")),
                border_style="green",
            )

        self.current_word = self.words[self.word_index]

        # Build display based on ORP settings
        if self.enable_orp:
            orp_idx = calculate_orp_index(self.current_word)
            parts = split_word_for_display(self.current_word, orp_idx)
            word_text = self._format_orp(parts)
        else:
            word_text = Text(self.current_word, style="bold white", justify="center")

        # Progress bar
        progress = (self.word_index / self.total_words) * 100 if self.total_words > 0 else 0

        # Status info
        status = Text()
        status.append(f"Word {self.word_index + 1}/{self.total_words} ", style="dim")
        status.append(f"({progress:.0f}%) ", style="cyan")
        status.append(f"• {self.wpm} WPM", style="yellow")

        # Combine
        content = Text.assemble(
            Text("\n"),
            Align.center(word_text),  # type: ignore[arg-type]
            Text("\n"),
            Align.center(status),  # type: ignore[arg-type]
        )

        border = "red" if self.is_playing else "blue"
        return Panel(content, border_style=border)

    def _format_orp(self, parts: Any) -> Text:
        """Format word with ORP character highlighted."""
        result = Text()
        if parts.before_orp:
            result.append(parts.before_orp, style="white")
        result.append(parts.orp_char, style="bold red")
        if parts.after_orp:
            result.append(parts.after_orp, style="white")
        return result

    def watch_word_index(self, index: int) -> None:
        """React to word index changes."""
        if self.on_word_change:
            self.on_word_change(index)
        if index >= self.total_words and self.on_complete:
            self.on_complete()

    def toggle_play(self) -> None:
        """Toggle play/pause state."""
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        """Start reading."""
        if not self.is_playing and self.word_index < self.total_words:
            self.is_playing = True
            self._schedule_next()

    def pause(self) -> None:
        """Pause reading."""
        self.is_playing = False
        if self._timer:
            self._timer.stop()
            self._timer = None

    def _schedule_next(self) -> None:
        """Schedule the next word."""
        if not self.is_playing or self.word_index >= self.total_words:
            return

        delay = calculate_word_delay(
            self.current_word, self.wpm, self.punctuation_multiplier, self.pause_chars
        )

        self._timer = self.set_timer(delay / 1000, self._advance)

    def _advance(self) -> None:
        """Advance to next word."""
        if self.is_playing:
            self.word_index += 1
            if self.word_index < self.total_words:
                self._schedule_next()
            else:
                self.is_playing = False

    def next_word(self) -> None:
        """Manual next word."""
        if self.word_index < self.total_words - 1:
            self.word_index += 1

    def prev_word(self) -> None:
        """Manual previous word."""
        if self.word_index > 0:
            self.word_index -= 1

    def jump_to(self, index: int) -> None:
        """Jump to specific word."""
        self.word_index = max(0, min(index, self.total_words - 1))

    def jump_to_percentage(self, percentage: float) -> None:
        """Jump to percentage position."""
        index = int((percentage / 100) * self.total_words)
        self.jump_to(index)

    def restart(self) -> None:
        """Restart from beginning."""
        self.pause()
        self.word_index = 0

    def change_speed(self, delta: int) -> None:
        """Change reading speed."""
        self.wpm = max(100, min(1000, self.wpm + delta))


# =============================================================================
# LIBRARY SCREEN
# =============================================================================


class LibraryScreen(Screen[Any]):
    """Screen for browsing and managing the book library."""

    BINDINGS = [
        Binding("r", "read_book", "Read Book"),
        Binding("d", "delete_book", "Delete"),
        Binding("i", "import_book", "Import"),
        Binding("q", "app.quit", "Quit"),
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, library: LibraryManager, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.library = library
        self.selected_book_id: str | None = None

    def compose(self) -> ComposeResult:
        """Compose the library screen."""
        yield Header()

        with Vertical():
            yield Label("📚 Library", id="library-title")
            yield Input(placeholder="Search books...", id="search")

            table: DataTable[Any] = DataTable(id="books-table")
            table.add_columns("Title", "Author", "Progress", "Last Read", "Words", "Type")
            table.cursor_type = "row"
            yield table

            with Horizontal(id="library-buttons"):
                yield Button("📖 Read [r]", id="btn-read", variant="primary")
                yield Button("➕ Import [i]", id="btn-import")
                yield Button("🗑️ Delete [d]", id="btn-delete", variant="error")

        yield Footer()

    def on_mount(self) -> None:
        """Load books on mount."""
        try:
            self._load_books()
        except Exception as exc:
            telemetry_error("app_complete.LibraryScreen.on_mount", exc)
            raise

    def _load_books(self, search: str = "") -> None:
        """Load books into the table."""
        try:
            table = self.query_one("#books-table", DataTable)
            table.clear()

            books = self.library.list_books(search=search if search else None)

            for book in books:
                progress = f"{book.completion_percentage:.0f}%"
                last_read = (
                    book.last_read_date.strftime("%Y-%m-%d") if book.last_read_date else "Never"
                )

                table.add_row(
                    book.title[:40],
                    book.author[:20],
                    progress,
                    last_read,
                    f"{book.word_count:,}",
                    book.file_type.upper(),
                    key=book.id,
                )
        except Exception as exc:
            telemetry_error("app_complete.LibraryScreen._load_books", exc)
            self.notify(f"Error loading library: {exc}", severity="error")

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input."""
        if event.input.id == "search":
            self._load_books(search=event.value)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle book selection."""
        self.selected_book_id = str(event.row_key)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        btn_id = event.button.id
        if btn_id == "btn-read":
            self.action_read_book()
        elif btn_id == "btn-import":
            self.action_import_book()
        elif btn_id == "btn-delete":
            self.action_delete_book()

    def action_read_book(self) -> None:
        """Read the selected book."""
        if self.selected_book_id:
            book = self.library.get_book(self.selected_book_id)
            if book:
                self.app.push_screen(ReaderScreen(book, self.library, self.app.note_manager))  # type: ignore[attr-defined]

    def action_import_book(self) -> None:
        """Show import dialog."""
        self.app.push_screen(ImportScreen(self.library))

    def action_delete_book(self) -> None:
        """Delete the selected book."""
        if self.selected_book_id:
            book = self.library.get_book(self.selected_book_id)
            if book:
                self.app.push_screen(ConfirmDeleteScreen(book, self.library, self))


# =============================================================================
# READER SCREEN
# =============================================================================


class ReaderScreen(Screen[Any]):
    """Screen for RSVP reading."""

    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("left", "prev_word", "Previous"),
        Binding("right", "next_word", "Next"),
        Binding("up", "speed_up", "Faster"),
        Binding("down", "speed_down", "Slower"),
        Binding("home", "jump_start", "Start"),
        Binding("end", "jump_end", "End"),
        Binding("n", "add_note", "Add Note"),
        Binding("o", "toggle_orp", "Toggle ORP"),
        Binding("f", "focus_mode", "Focus"),
        Binding("r", "restart", "Restart"),
        Binding("escape", "go_back", "Back"),
    ]

    def __init__(self, book: Book, library: LibraryManager, note_manager: NoteManager, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.book = book
        self.library = library
        self.note_manager = note_manager
        self.words: list[str] = []
        self.rsvp_display: RSVPWordDisplay | None = None
        self.focus_mode = False
        self.show_notes = True

    def compose(self) -> ComposeResult:
        """Compose the reader screen."""
        yield Header()

        with Horizontal():
            # Main reading area
            with Vertical(id="reader-main"):
                yield Label(f"📖 {self.book.title}", id="book-title")
                yield RSVPWordDisplay([], id="rsvp-display")

                with Horizontal(id="reader-controls"):
                    yield Button("▶ Play [Space]", id="btn-play", variant="primary")
                    yield Button("← Back", id="btn-prev")
                    yield Button("Next →", id="btn-next")
                    yield Button("⏮ Restart [r]", id="btn-restart")
                    yield Button("📝 Note [n]", id="btn-note")
                    yield Button("👁 ORP [o]", id="btn-orp")

            # Notes sidebar
            with Vertical(id="notes-panel"):
                yield Label("📝 Notes", id="notes-title")
                yield Static("No notes yet. Press 'n' to add one.", id="notes-list")
                yield Button("Hide [tab]", id="btn-toggle-notes")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize reader on mount."""
        try:
            self.words = self.library.load_words(self.book.id)

            if not self.words and self.book.file_path and Path(self.book.file_path).exists():
                self._parse_file(Path(self.book.file_path))

            if self.words:
                display = self.query_one("#rsvp-display", RSVPWordDisplay)
                display.words = self.words
                display.word_index = self.book.current_word_index
                display.on_word_change = self._on_word_change  # type: ignore[assignment]
                display.on_complete = self._on_complete  # type: ignore[assignment]
                display.enable_orp = self.app.config.enable_orp  # type: ignore[attr-defined]
                self.rsvp_display = display

                self._update_notes_display()
            else:
                self.notify("Error loading book content", severity="error")
        except Exception as exc:
            telemetry_error("app_complete.ReaderScreen.on_mount", exc)
            raise

    def _parse_file(self, path: Path) -> None:
        """Parse file to extract words."""
        try:
            suffix = path.suffix.lower()
            if suffix == ".md":
                result = parse_markdown(path.read_text(encoding="utf-8"))
            elif suffix == ".txt":
                result = parse_plain_text(path.read_text(encoding="utf-8"))
            elif suffix == ".epub":
                result = parse_epub_bytes(path.read_bytes())
            else:
                return

            self.words = tokenize_text(result.plain_text)

            # Cache words
            if self.book.cache_file_path:
                import json

                self.book.cache_file_path.write_text(json.dumps(self.words))

        except Exception as e:
            telemetry_error("app_complete.ReaderScreen._parse_file", e)
            self.notify(f"Error parsing file: {e}", severity="error")

    def _on_word_change(self, index: int) -> None:
        """Handle word change."""
        self.book.current_word_index = index

        # Save progress every 50 words
        if index % 50 == 0:
            self.library.update_progress(self.book.id, index)

        # Update notes display
        self._update_notes_display()

    def _on_complete(self) -> None:
        """Handle reading complete."""
        self.library.update_progress(self.book.id, self.book.word_count)
        self.notify("🎉 Reading complete!", severity="success")  # type: ignore[arg-type]

    def _update_notes_display(self) -> None:
        """Update notes sidebar."""
        if not self.rsvp_display:
            return

        notes = self.note_manager.get_notes_for_position(
            self.book.id, self.rsvp_display.word_index, context_window=50
        )

        notes_widget = self.query_one("#notes-list", Static)

        if not notes:
            notes_widget.update("No notes nearby.")
        else:
            lines = []
            for note in notes:
                offset = note.word_index - self.rsvp_display.word_index
                if offset == 0:
                    pos = "HERE"
                elif offset > 0:
                    pos = f"+{offset}"
                else:
                    pos = f"{offset}"

                content = note.content[:30] + "..." if len(note.content) > 30 else note.content
                lines.append(f"[{pos}] {content}")

            notes_widget.update("\n".join(lines))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        btn_id = event.button.id

        if btn_id == "btn-play":
            self.action_toggle_play()
        elif btn_id == "btn-prev":
            self.action_prev_word()
        elif btn_id == "btn-next":
            self.action_next_word()
        elif btn_id == "btn-restart":
            self.action_restart()
        elif btn_id == "btn-note":
            self.action_add_note()
        elif btn_id == "btn-orp":
            self.action_toggle_orp()
        elif btn_id == "btn-toggle-notes":
            self._toggle_notes()

    def action_toggle_play(self) -> None:
        """Toggle play/pause."""
        if self.rsvp_display:
            self.rsvp_display.toggle_play()
            btn = self.query_one("#btn-play", Button)
            btn.label = "❚❚ Pause" if self.rsvp_display.is_playing else "▶ Play"

    def action_prev_word(self) -> None:
        """Previous word."""
        if self.rsvp_display:
            self.rsvp_display.prev_word()

    def action_next_word(self) -> None:
        """Next word."""
        if self.rsvp_display:
            self.rsvp_display.next_word()

    def action_speed_up(self) -> None:
        """Increase speed."""
        if self.rsvp_display:
            self.rsvp_display.change_speed(25)
            self.notify(f"Speed: {self.rsvp_display.wpm} WPM")

    def action_speed_down(self) -> None:
        """Decrease speed."""
        if self.rsvp_display:
            self.rsvp_display.change_speed(-25)
            self.notify(f"Speed: {self.rsvp_display.wpm} WPM")

    def action_jump_start(self) -> None:
        """Jump to start."""
        if self.rsvp_display:
            self.rsvp_display.jump_to(0)

    def action_jump_end(self) -> None:
        """Jump to end."""
        if self.rsvp_display:
            self.rsvp_display.jump_to(self.rsvp_display.total_words - 1)

    def action_toggle_orp(self) -> None:
        """Toggle ORP highlighting."""
        if self.rsvp_display:
            self.rsvp_display.enable_orp = not self.rsvp_display.enable_orp
            status = "ON" if self.rsvp_display.enable_orp else "OFF"
            self.notify(f"ORP highlighting: {status}")

    def action_restart(self) -> None:
        """Restart reading."""
        if self.rsvp_display:
            self.rsvp_display.restart()

    def action_add_note(self) -> None:
        """Open add note dialog."""
        if self.rsvp_display:
            try:
                self.app.push_screen(
                    AddNoteScreen(
                        self.book.id,
                        self.rsvp_display.word_index,
                        (
                            self.words[self.rsvp_display.word_index]
                            if self.rsvp_display.word_index < len(self.words)
                            else ""
                        ),
                        self.note_manager,
                        self,
                    )
                )
            except Exception as exc:
                telemetry_error("app_complete.ReaderScreen.action_add_note", exc)
                self.notify(f"Error adding note: {exc}", severity="error")

    def action_go_back(self) -> None:
        """Go back to library."""
        if self.rsvp_display:
            self.rsvp_display.pause()
            self.library.update_progress(self.book.id, self.rsvp_display.word_index)
        self.app.pop_screen()

    def _toggle_notes(self) -> None:
        """Toggle notes panel."""
        notes_panel = self.query_one("#notes-panel")
        if self.show_notes:
            notes_panel.add_class("hidden")
            self.show_notes = False
        else:
            notes_panel.remove_class("hidden")
            self.show_notes = True

    def action_focus_mode(self) -> None:
        """Toggle focus mode."""
        self.focus_mode = not self.focus_mode
        if self.focus_mode:
            self.add_class("focus-mode")
            self.notify("Focus mode ON")
        else:
            self.remove_class("focus-mode")
            self.notify("Focus mode OFF")


# =============================================================================
# ADD NOTE SCREEN
# =============================================================================


class AddNoteScreen(ModalScreen[Any]):
    """Modal screen for adding a note."""

    def __init__(
        self,
        book_id: str,
        word_index: int,
        word_context: str,
        note_manager: NoteManager,
        reader_screen: ReaderScreen,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.book_id = book_id
        self.word_index = word_index
        self.word_context = word_context
        self.note_manager = note_manager
        self.reader_screen = reader_screen

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        with Grid(id="note-dialog"):
            yield Label(f"📝 Add Note at Word {self.word_index}", id="note-title")
            yield Label(f"Context: '{self.word_context}'", id="note-context")
            yield Input(placeholder="Tags (comma-separated)", id="note-tags")
            yield TextArea(id="note-content", text="Enter your note here...")

            with Horizontal(id="note-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Save", id="btn-save", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-save":
            content = self.query_one("#note-content", TextArea).text
            tags_str = self.query_one("#note-tags", Input).value
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]

            if content.strip():
                self.note_manager.create_note(
                    book_id=self.book_id,
                    word_index=self.word_index,
                    chapter_index=0,
                    content=content,
                    tags=tags,
                    word_context=self.word_context,
                )
                self.reader_screen._update_notes_display()
                self.dismiss()
            else:
                self.notify("Please enter note content", severity="error")

        else:
            self.dismiss()


# =============================================================================
# IMPORT SCREEN
# =============================================================================


class ImportScreen(ModalScreen[Any]):
    """Modal screen for importing a book."""

    def __init__(self, library: LibraryManager, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.library = library

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        with Grid(id="import-dialog"):
            yield Label("➕ Import Book", id="import-title")
            yield Input(placeholder="Path to file (.md, .txt, .epub)", id="file-path")

            with Horizontal(id="import-buttons"):
                yield Button("Cancel", id="btn-cancel", variant="error")
                yield Button("Import", id="btn-import", variant="success")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-import":
            path_str = self.query_one("#file-path", Input).value
            path = Path(path_str)

            if path.exists():
                try:
                    book = self.library.import_book(path)
                    self.notify(f"✅ Imported: {book.title}")
                    self.dismiss()
                except Exception as e:
                    self.notify(f"❌ Error: {e}", severity="error")
            else:
                self.notify("File not found", severity="error")
        else:
            self.dismiss()


# =============================================================================
# CONFIRM DELETE SCREEN
# =============================================================================


class ConfirmDeleteScreen(ModalScreen[Any]):
    """Modal screen to confirm book deletion."""

    def __init__(
        self, book: Book, library: LibraryManager, library_screen: LibraryScreen, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.book = book
        self.library = library
        self.library_screen = library_screen

    def compose(self) -> ComposeResult:
        """Compose the modal."""
        with Grid(id="delete-dialog"):
            yield Label("🗑️ Confirm Delete", id="delete-title")
            yield Label(f"Are you sure you want to delete '{self.book.title}'?")
            yield Label("This cannot be undone.")

            with Horizontal(id="delete-buttons"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Delete", id="btn-delete", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-delete":
            self.library.delete_book(self.book.id)
            self.library_screen._load_books()
            self.notify("Book deleted")

        self.dismiss()


# =============================================================================
# MAIN APPLICATION
# =============================================================================


class RSVPTUI(App[Any]):
    """Main RSVP TUI Application."""

    CSS = """
    Screen { align: center middle; }

    /* Library Screen */
    #library-title { text-align: center; text-style: bold; padding: 1; }
    #search { margin: 1; }
    #books-table { height: 1fr; margin: 1; }
    #library-buttons { height: auto; align: center middle; padding: 1; }
    #library-buttons Button { margin: 0 1; }

    /* Reader Screen */
    #reader-main { width: 3fr; height: 100%; }
    #book-title { text-align: center; text-style: bold; padding: 1; }
    #rsvp-display { height: 2fr; }
    #reader-controls { height: auto; align: center middle; padding: 1; }
    #reader-controls Button { margin: 0 1; }

    #notes-panel { width: 1fr; height: 100%; border: solid blue; }
    #notes-title { text-align: center; text-style: bold; padding: 1; }
    #notes-list { padding: 1; }
    #btn-toggle-notes { width: 100%; }

    #notes-panel.hidden { display: none; }

    /* Focus Mode */
    .focus-mode Header { display: none; }
    .focus-mode Footer { display: none; }
    .focus-mode #reader-controls { display: none; }
    .focus-mode #notes-panel { display: none; }

    /* Modals */
    #note-dialog, #import-dialog, #delete-dialog {
        grid-size: 1;
        padding: 1;
        width: 60;
        height: auto;
        border: solid green;
        background: $surface;
    }

    #note-title, #import-title, #delete-title {
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    #note-context { text-style: italic; color: $text-muted; }

    #note-content { height: 10; }

    #note-buttons, #import-buttons, #delete-buttons {
        height: auto;
        align: center middle;
        padding: 1;
    }

    #note-buttons Button, #import-buttons Button, #delete-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("l", "show_library", "Library"),
        Binding("question", "show_help", "Help"),
    ]

    def __init__(self) -> None:
        try:
            super().__init__()
            self.config = Config.load()
            self.library = LibraryManager(self.config.library_db_path)
            self.note_manager = NoteManager(self.config.notes_dir)
        except Exception as exc:
            telemetry_error("app_complete.RSVPTUI.__init__", exc)
            raise

    def on_mount(self) -> None:
        """Start with library screen."""
        try:
            self.title = "RSVP Speed Reader"
            self.push_screen(LibraryScreen(self.library))
        except Exception as exc:
            telemetry_error("app_complete.RSVPTUI.on_mount", exc)
            raise

    def action_show_library(self) -> None:
        """Show library screen."""
        self.push_screen(LibraryScreen(self.library))

    def action_show_help(self) -> None:
        """Show help."""
        help_text = """
[b]Keyboard Shortcuts[/b]

[b]Library:[/b]
• ↑/↓ - Navigate books
• r - Read selected book
• i - Import book
• d - Delete book

[b]Reader:[/b]
• Space - Play/Pause
• ←/→ - Previous/Next word
• ↑/↓ - Speed up/down
• n - Add note
• o - Toggle ORP
• f - Focus mode
• r - Restart
• Escape - Back to library
        """
        self.notify(help_text, title="Help", timeout=10)


# =============================================================================
# ENTRY POINT
# =============================================================================


def main() -> None:
    """Run the application."""
    try:
        app = RSVPTUI()
        app.run()
    except Exception as exc:
        telemetry_error("app_complete.main", exc)
        sys.stderr.write(f"[app_complete] unhandled exception: {exc}\n")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
