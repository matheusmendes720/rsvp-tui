"""Library view widget for browsing books."""

from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.containers import Vertical
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

    def action_delete_selected(self) -> None:
        """Delete the selected book."""
        if self.selected_book_id and self.on_delete_callback:
            self.on_delete_callback(self.selected_book_id)
            self.load_books()

    def action_refresh(self) -> None:
        """Refresh the book list."""
        self.load_books()

    def get_selected_book(self) -> Book | None:
        """Get the currently selected book."""
        if self.selected_book_id:
            return self.library_manager.get_book(self.selected_book_id)
        return None
