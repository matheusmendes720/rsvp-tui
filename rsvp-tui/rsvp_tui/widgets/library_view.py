"""Library view widget for browsing books."""

from __future__ import annotations

import contextlib
from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.coordinate import Coordinate
from textual.reactive import reactive
from textual.widgets import DataTable, Input

from ..managers.library_manager import LibraryManager
from ..models import Book


class LibraryView(Vertical):
    """Widget for browsing and selecting books from library."""

    DEFAULT_CSS = """
    LibraryView {
        width: 100%;
        height: 100%;
    }
    LibraryView Input {
        dock: top;
        margin: 1;
    }
    LibraryView DataTable {
        width: 100%;
        height: 1fr;
        margin: 1;
    }
    """

    books: reactive[list[Book]] = reactive(list[Book]())
    selected_book_id: reactive[str | None] = reactive(None)

    def __init__(
        self,
        library_manager: LibraryManager,
        on_select: Callable[[Book], None] | None = None,
        on_delete: Callable[[str], None] | None = None,
    ):
        super().__init__()
        self.library_manager = library_manager
        self.on_select_callback = on_select
        self.on_delete_callback = on_delete
        self.search_query = ""

    def compose(self) -> ComposeResult:
        """Compose the widget."""
        yield Input(placeholder="Search books...", id="search-input")
        yield DataTable(id="books-table")

    def on_mount(self) -> None:
        """Initialize on mount."""
        table = self.query_one(DataTable)
        table.add_columns(
            "Title",
            "Author",
            "Progress",
            "Last Read",
            "Words",
        )
        table.cursor_type = "row"
        self.load_books()

    def load_books(self) -> None:
        """Load books from library."""
        self.books = self.library_manager.list_books(search=self.search_query or None)
        self._update_table()

    def _update_table(self) -> None:
        """Update the table with current books."""
        table = self.query_one(DataTable)
        table.clear()

        for book in self.books:
            progress = f"{book.completion_percentage:.0f}%"
            last_read = book.last_read_date.strftime("%Y-%m-%d") if book.last_read_date else "Never"

            table.add_row(
                book.title,
                book.author,
                progress,
                last_read,
                f"{book.word_count:,}",
                key=book.id,
            )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle search input changes."""
        if event.input.id == "search-input":
            self.search_query = event.value
            self.load_books()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle book selection."""
        book_id = event.row_key.value
        self.selected_book_id = book_id

        if self.on_select_callback and book_id is not None:
            book = self.library_manager.get_book(book_id)
            if book:
                self.on_select_callback(book)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """Keep the selection in sync with the table cursor.

        ``RowSelected`` only fires on Enter, so moving the cursor with
        the arrow keys used to leave ``selected_book_id`` pointing at
        the book that was last *opened*. Delete then removed that book
        — one the user was no longer looking at. The cursor is the
        truth about what is selected.
        """
        book_id = event.row_key.value
        if book_id is not None:
            self.selected_book_id = str(book_id)

    def get_book_under_cursor(self) -> Book | None:
        """Return the book the table cursor is on.

        This is the authoritative target for the destructive actions:
        it follows the cursor, not the last Enter.
        """
        try:
            table = self.query_one(DataTable)
        except Exception:
            return None
        if table.row_count == 0:
            return None
        row = min(max(0, table.cursor_row), table.row_count - 1)
        try:
            cell_key = table.coordinate_to_cell_key(Coordinate(row, 0))
        except Exception:
            return None
        book_id = cell_key.row_key.value
        if book_id is None:
            return None
        return self.library_manager.get_book(str(book_id))

    def action_delete_selected(self) -> None:
        """Delete the book under the cursor."""
        book = self.get_book_under_cursor()
        if book is None:
            return
        if self.on_delete_callback:
            self.on_delete_callback(book.id)
            self.load_books()

    def action_refresh(self) -> None:
        """Refresh the book list."""
        self.load_books()

    def get_selected_book(self) -> Book | None:
        """Get the selected book (the one under the cursor)."""
        book = self.get_book_under_cursor()
        if book is not None:
            return book
        if self.selected_book_id:
            return self.library_manager.get_book(self.selected_book_id)
        return None

    # ---- Live focus helpers (called by screen-level bindings) ----

    def focus_table(self) -> None:
        """Move focus to the DataTable so arrow keys navigate rows."""
        with contextlib.suppress(Exception):
            self.query_one(DataTable).focus()

    def move_cursor(self, delta: int) -> None:
        """Move the table cursor by ``delta`` rows (clamped)."""
        try:
            table = self.query_one(DataTable)
        except Exception:
            return
        if table.row_count == 0:
            return
        current = table.cursor_row
        new_row = max(0, min(table.row_count - 1, current + delta))
        table.move_cursor(row=new_row)
        # Mirror into our reactive so the screen-level action sees it.
        row_key = table.coordinate_to_cell_key(Coordinate(new_row, 0)).row_key
        if row_key is not None:
            self.selected_book_id = str(row_key.value)

    def focus_search(self) -> None:
        """Move focus to the search input."""
        with contextlib.suppress(Exception):
            self.query_one("#search-input", Input).focus()
