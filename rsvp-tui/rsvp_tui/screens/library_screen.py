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
import sqlite3

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
        # ---- Ctrl variants (always-on, no focus issues) ----
        # Action strings MUST be the bare method name (e.g. "refresh");
        # Textual auto-prefixes ``action_`` during dispatch. Using
        # ``"action_refresh"`` here would resolve to ``action_action_refresh``
        # and silently no-op. See tests/test_keybindings.py for the guard.
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("ctrl+s", "open_settings", "Settings"),
        Binding("ctrl+o", "open_file", "Open"),
        Binding("ctrl+q", "app.quit", "Quit"),
        # ---- Single-key variants (work when the table has focus) ----
        Binding("o", "open_file", "Open"),
        Binding("s", "open_settings", "Settings"),
        Binding("r", "refresh", "Refresh"),
        Binding("?", "show_help", "Help"),
        Binding("delete,backspace", "delete_selected", "Delete"),
        Binding("enter", "open_selected", "Read"),
        # ---- Arrow keys (DataTable handles these natively when focused,
        # but explicit bindings keep them working when the search input
        # has focus, via the Input's own handler). We re-bind so the
        # action shows in the footer. ----
        Binding("down", "focus_next_book", "Down"),
        Binding("up", "focus_prev_book", "Up"),
        Binding("j", "focus_next_book", "Next", show=False),
        Binding("k", "focus_prev_book", "Prev", show=False),
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
        except (OSError, ValueError) as e:
            # Narrow on purpose: import_book surfaces FileNotFoundError,
            # PermissionError, IsADirectoryError (all OSError subclasses)
            # and ValueError for unsupported file types. KeyboardInterrupt /
            # MemoryError / SystemExit must still propagate so the user
            # can Ctrl-C out and OOM crashes aren't masked.
            self.app.notify(f"Error: {e}", severity="error")
            log.warning(
                "LibraryScreen: import_book failed for path=%s: %s", path, e
            )

    def action_show_help(self) -> None:
        """Show a notification with the keybindings."""
        help_text = (
            "[b]Library Hotkeys[/b]\n"
            "  [b]o[/b] / [b]Ctrl+O[/b]  Import book\n"
            "  [b]s[/b] / [b]Ctrl+S[/b]  Settings\n"
            "  [b]r[/b] / [b]Ctrl+R[/b]  Refresh\n"
            "  [b]Enter[/b]        Open selected\n"
            "  [b]Delete[/b]       Delete selected\n"
            "  [b]j/k[/b] or [b]↑/↓[/b] Navigate\n"
            "  [b]Ctrl+Q[/b]       Quit"
        )
        self.app.notify(help_text, timeout=8)

    def action_open_selected(self) -> None:
        """Open the currently-selected book (Enter key)."""
        if self._library_view is None:
            return
        book = self._library_view.get_selected_book()
        if book is None:
            self.app.notify("No book selected")
            return
        self.post_message(BookOpened(book_id=book.id))

    def action_delete_selected(self) -> None:
        """Delete the currently-selected book."""
        if self._library_view is None:
            return
        book = self._library_view.get_selected_book()
        if book is None:
            self.app.notify("No book selected")
            return
        library_manager = self.app.library_manager  # type: ignore[attr-defined]
        try:
            library_manager.delete_book(book.id)
        except (OSError, ValueError, sqlite3.DatabaseError) as e:
            # Narrow on purpose: delete_book surfaces sqlite3.DatabaseError
            # (OperationalError / IntegrityError on a locked/corrupt DB),
            # OSError on cache_path.unlink() failures (PermissionError,
            # FileNotFoundError, disk errors), and ValueError for malformed
            # book ids. KeyboardInterrupt / MemoryError / SystemExit must
            # still propagate so the user can Ctrl-C out and OOM crashes
            # aren't masked. Programmer bugs (AttributeError, TypeError,
            # KeyError) also propagate — they should NOT be silently turned
            # into a toast that hides real defects. The same narrowing
            # philosophy as _on_file_selected_path, with sqlite3 added
            # because delete_book is DB-heavy.
            self.app.notify(f"Delete failed: {e}", severity="error")
            return
        self._library_view.load_books()
        self.app.notify(f"Deleted {book.title}")

    def action_focus_next_book(self) -> None:
        """Move DataTable selection down by one row."""
        if self._library_view is None:
            return
        self._library_view.move_cursor(+1)

    def action_focus_prev_book(self) -> None:
        """Move DataTable selection up by one row."""
        if self._library_view is None:
            return
        self._library_view.move_cursor(-1)


__all__ = ["LibraryScreen"]
