"""LibraryScreen — top-level screen for browsing books.

Wraps the existing ``LibraryView`` widget so it can be pushed as a
Textual ``Screen`` under the new ``RSVP_NEW_UI=1`` flow. The
LibraryView's ``on_select`` callback emits a ``BookOpened`` message
that the app handles by pushing the ReaderScreen with the chosen
book id.

Why a screen wrapper instead of inlining the LibraryView: it gives
us a place to add screen-level concerns (header/footer, focused
keybindings, search) without re-implementing the table widget.
"""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from ..models import Book, Config
from ..widgets import LibraryView
from .base import RSVPBaseScreen
from .messages import BookOpened
from .settings_screen import SettingsScreen

log = logging.getLogger(__name__)


class LibraryScreen(RSVPBaseScreen):
    """Browse and select a book to read."""

    DEFAULT_CSS = """
    LibraryScreen {
        layout: vertical;
    }
    LibraryScreen #lib-status {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("ctrl+r", "app.refresh", "Refresh"),
        Binding("ctrl+s", "app.open_settings", "Settings"),
        Binding("ctrl+o", "app.open_file_explorer", "Open"),
    ]

    def __init__(self, config: Config | None = None) -> None:
        super().__init__(config=config)
        self._library_view: LibraryView | None = None

    def compose(self) -> ComposeResult:
        """Compose header, library view, status line, and footer."""
        yield Header(show_clock=True)
        self._library_view = LibraryView(
            library_manager=self.app.library_manager,  # type: ignore[attr-defined]
            on_select=self._on_book_selected,
            on_delete=self._on_book_deleted,
        )
        yield self._library_view
        yield Static("", id="lib-status")
        yield Footer()

    def on_mount(self) -> None:
        """Set the screen title and refresh the book list."""
        self.title = "RSVP Speed Reader"
        self.sub_title = "Library"

    def _on_book_selected(self, book: Book) -> None:
        """Forward book selection to the app via a message."""
        log.info("LibraryScreen: book selected id=%s title=%r", book.id, book.title)
        self.post_message(BookOpened(book_id=book.id))

    def _on_book_deleted(self, book_id: str) -> None:
        """Refresh after a delete so the row disappears."""
        if self._library_view is not None:
            self._library_view.load_books()
        self.app.notify("Book deleted")
        log.info("LibraryScreen: book deleted id=%s", book_id)

    # ---- Actions ---------------------------------------------------------

    def action_refresh(self) -> None:
        """Reload the book list (Ctrl+R)."""
        if self._library_view is not None:
            self._library_view.load_books()
            self.app.notify("Library refreshed")
            log.info("LibraryScreen: library refreshed")

    def action_open_settings(self) -> None:
        """Push the modal SettingsScreen (Ctrl+S)."""
        log.info("LibraryScreen: opening settings")
        self.app.push_screen(SettingsScreen(config=self.config))

    def action_open_file(self) -> None:
        """Open file explorer modal (Ctrl+O)."""
        from .file_explorer import FileExplorerScreen

        self.app.push_screen(
            FileExplorerScreen(),
            self._on_file_selected_path,
        )

    def _on_file_selected_path(self, path: str | None) -> None:
        """Handle file selection from the explorer."""
        if not path:
            return
        from pathlib import Path

        try:
            library_manager = self.app.library_manager  # type: ignore[attr-defined]
            book = library_manager.import_book(Path(path))
            if book:
                self.post_message(BookOpened(book_id=book.id))
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error")


__all__ = ["LibraryScreen"]
