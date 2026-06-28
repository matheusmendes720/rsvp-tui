"""NavigationPanel — chapter/page navigation widget for the reader.

Shows the chapter list, current position (chapter X of Y | page Z of W),
and provides navigation controls. Emits NavigationJump messages when
the user selects a chapter or jumps to a specific position.
"""

from __future__ import annotations

from dataclasses import dataclass

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Static

from ..models import Book, Chapter


@dataclass
class NavigationState:
    """Current navigation state for the widget."""

    current_chapter_index: int
    total_chapters: int
    current_page: int
    total_pages: int
    page_size: int


class NavigationPanel(Static):
    """Chapter and page navigation panel.

    Displays:
    - Current position: "Chapter 3 of 12 | Page 15 of 40"
    - Chapter list (scrollable)
    - Prev/Next chapter buttons
    - Jump to page input

    Emits NavigationJump when the user selects a target.
    """

    DEFAULT_CSS = """
    NavigationPanel {
        width: 30;
        height: 100%;
        background: $surface;
        border-left: solid $primary;
        padding: 1 0;
    }
    NavigationPanel .nav-header {
        text-align: center;
        color: $text;
        text-style: bold;
        margin-bottom: 1;
    }
    NavigationPanel .nav-position {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }
    NavigationPanel .nav-chapters {
        height: 1fr;
        border: solid $border;
        margin: 1 0;
    }
    NavigationPanel .nav-buttons {
        height: auto;
        layout: horizontal;
        align: center middle;
    }
    NavigationPanel Button {
        margin: 0 1;
    }
    """

    # Book and chapters data
    _book: Book | None = None
    _chapters: list[Chapter] = []
    _page_size: int = 500
    _word_count: int = 0

    # Current state
    current_chapter_index: reactive[int] = reactive(0)
    current_word_index: reactive[int] = reactive(0)

    def __init__(
        self,
        book: Book | None = None,
        page_size: int = 500,
        **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self._book = book
        self._chapters = book.chapters if book else []
        self._page_size = page_size
        self._word_count = book.word_count if book else 0
        # Calculate initial chapter
        if book and book.current_word_index > 0:
            self._update_chapter_from_word(book.current_word_index)

    def _update_chapter_from_word(self, word_index: int) -> None:
        """Update current chapter based on word index."""
        for i, ch in enumerate(self._chapters):
            if ch.start_word_index <= word_index <= ch.end_word_index:
                self.current_chapter_index = i
                return
        self.current_chapter_index = 0

    def _get_current_page(self) -> int:
        """Calculate current page number (1-indexed)."""
        if self._word_count == 0 or self._page_size == 0:
            return 1
        return (self.current_word_index // self._page_size) + 1

    def _get_total_pages(self) -> int:
        """Calculate total pages."""
        if self._word_count == 0 or self._page_size == 0:
            return 1
        return (self._word_count + self._page_size - 1) // self._page_size

    def _get_nav_state(self) -> NavigationState:
        """Get current navigation state."""
        return NavigationState(
            current_chapter_index=self.current_chapter_index,
            total_chapters=len(self._chapters),
            current_page=self._get_current_page(),
            total_pages=self._get_total_pages(),
            page_size=self._page_size,
        )

    def compose(self) -> ComposeResult:
        """Compose the navigation panel."""
        state = self._get_nav_state()

        # Header
        yield Static("Navigation", classes="nav-header")

        # Position display
        position_text = self._format_position(state)
        yield Static(position_text, classes="nav-position")

        # Chapter list
        chapter_list = self._format_chapter_list()
        yield Static(chapter_list, classes="nav-chapters")

        # Navigation buttons
        with Vertical(classes="nav-buttons"):
            yield Button("Prev", variant="default", id="btn-prev-chapter")
            yield Button("Next", variant="default", id="btn-next-chapter")

    def _format_position(self, state: NavigationState) -> str:
        """Format the position display text."""
        if state.total_chapters > 0:
            chapter_part = f"Chapter {state.current_chapter_index + 1} of {state.total_chapters}"
        else:
            chapter_part = "No chapters"
        page_part = f"Page {state.current_page} of {state.total_pages}"
        return f"{chapter_part}\n{page_part}"

    def _format_chapter_list(self) -> str:
        """Format the chapter list for display."""
        if not self._chapters:
            return "No chapters"

        lines = []
        for i, ch in enumerate(self._chapters):
            prefix = ">" if i == self.current_chapter_index else " "
            # Truncate long titles
            title = ch.title[:25] + "..." if len(ch.title) > 25 else ch.title
            lines.append(f"{prefix} {i + 1}. {title}")
        return "\n".join(lines)

    def update_position(self, word_index: int) -> None:
        """Update the current position from the reader."""
        self.current_word_index = word_index
        self._update_chapter_from_word(word_index)
        self.refresh()

    def set_book(self, book: Book, page_size: int = 500) -> None:
        """Set the book and recalculate navigation state."""
        self._book = book
        self._chapters = book.chapters
        self._page_size = page_size
        self._word_count = book.word_count
        self.current_word_index = book.current_word_index
        self._update_chapter_from_word(book.current_word_index)
        self.refresh()

    def watch_current_chapter_index(self) -> None:
        """Refresh display when chapter changes."""
        self.refresh()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-prev-chapter":
            self._prev_chapter()
        elif button_id == "btn-next-chapter":
            self._next_chapter()

    def _prev_chapter(self) -> None:
        """Navigate to the previous chapter."""
        if self.current_chapter_index > 0:
            new_index = self.current_chapter_index - 1
            target_word = self._chapters[new_index].start_word_index
            self.post_message(NavigationJump(target_word, new_index))

    def _next_chapter(self) -> None:
        """Navigate to the next chapter."""
        if self.current_chapter_index < len(self._chapters) - 1:
            new_index = self.current_chapter_index + 1
            target_word = self._chapters[new_index].start_word_index
            self.post_message(NavigationJump(target_word, new_index))

    def jump_to_chapter(self, chapter_index: int) -> None:
        """Jump to a specific chapter by index."""
        if 0 <= chapter_index < len(self._chapters):
            target_word = self._chapters[chapter_index].start_word_index
            self.post_message(NavigationJump(target_word, chapter_index))

    def jump_to_page(self, page: int) -> None:
        """Jump to a specific page (1-indexed)."""
        if page < 1:
            page = 1
        if self._page_size > 0:
            word_index = (page - 1) * self._page_size
            # Clamp to word count
            if word_index >= self._word_count:
                word_index = max(0, self._word_count - 1)
            self.post_message(NavigationJump(word_index, self.current_chapter_index))


class NavigationJump(Message):
    """Message emitted when user triggers a navigation jump."""

    def __init__(self, word_index: int, chapter_index: int = 0) -> None:
        super().__init__()
        self.word_index = word_index
        self.chapter_index = chapter_index


__all__ = ["NavigationPanel", "NavigationJump"]
