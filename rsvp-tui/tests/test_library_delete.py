"""Regression test for the library delete target (critical defect B1).

The library used to delete the WRONG book: ``selected_book_id`` was
only updated by ``RowSelected`` (i.e. by pressing Enter), so moving
the cursor with the arrow keys left the selection pointing at the book
that was last *opened*. Pressing Delete (or Backspace) then dropped
that book — one the user was no longer looking at — with no
confirmation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.app import App
from textual.widgets import DataTable

from rsvp_tui.managers.library_manager import LibraryManager
from rsvp_tui.models import Config
from rsvp_tui.screens.library_screen import LibraryScreen
from rsvp_tui.screens.settings_screen import _ConfirmModal


def _import_book(manager: LibraryManager, tmp_path: Path, title: str) -> str:
    """Create a tiny text book and import it into the library."""
    source = tmp_path / f"{title.replace(' ', '_')}.txt"
    source.write_text(f"{title} " + " ".join(f"word{i}" for i in range(20)), encoding="utf-8")
    book = manager.import_book(source)
    return book.id


def _make_app(manager: LibraryManager) -> App:
    class LibraryApp(App):
        def __init__(self) -> None:
            super().__init__()
            self.library_manager = manager

    return LibraryApp()


@pytest.mark.asyncio
async def test_delete_removes_the_book_under_the_cursor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Delete must target the row under the cursor — the row the user sees.

    Reproduction of the original defect: focus the table, press Enter
    on the FIRST book (which pins the selection to it), move the cursor
    down to the SECOND book, then press Delete. The old code deleted
    the FIRST book — the one no longer under the cursor.
    """
    monkeypatch.setenv("RSVP_HOME", str(tmp_path))
    manager = LibraryManager(db_path=tmp_path / "library.db")
    first_id = _import_book(manager, tmp_path, "Book First")
    second_id = _import_book(manager, tmp_path, "Book Second")
    assert first_id != second_id

    app = _make_app(manager)
    async with app.run_test() as pilot:
        # The real app pushes the library screen (app.py::_push_library);
        # a screen that is merely composed is not the active screen and
        # its bindings never fire.
        await app.push_screen(LibraryScreen(config=Config()))
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, LibraryScreen)
        view = screen._library_view
        assert view is not None
        table = view.query_one(DataTable)
        await pilot.pause()

        # The row order is the library's, not the import order.
        row_ids = [str(key.value) for key in table.rows]
        assert len(row_ids) == 2
        first_row_id, second_row_id = row_ids
        assert {first_row_id, second_row_id} == {first_id, second_id}

        # Enter on the first row pins the selection to that book.
        table.focus()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert view.selected_book_id == first_row_id

        # Move the cursor down: the selection must follow it.
        await pilot.press("down")
        await pilot.pause()
        assert table.cursor_row == 1
        assert view.selected_book_id == second_row_id

        # Delete: a confirmation must show up before anything is dropped.
        await pilot.press("delete")
        await pilot.pause()
        assert isinstance(app.screen, _ConfirmModal), (
            "deleting a book must ask for confirmation first"
        )

        # Confirm.
        app.screen.query_one("#yes-btn").press()
        await pilot.pause()

        assert manager.get_book(second_row_id) is None, "the book under the cursor was not deleted"
        assert manager.get_book(first_row_id) is not None, "the WRONG book was deleted"


@pytest.mark.asyncio
async def test_delete_can_be_cancelled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cancelling the confirmation must leave the book alone."""
    monkeypatch.setenv("RSVP_HOME", str(tmp_path))
    manager = LibraryManager(db_path=tmp_path / "library.db")
    book_id = _import_book(manager, tmp_path, "Book Only")

    app = _make_app(manager)
    async with app.run_test() as pilot:
        await app.push_screen(LibraryScreen(config=Config()))
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, LibraryScreen)
        view = screen._library_view
        assert view is not None
        view.query_one(DataTable).focus()
        await pilot.pause()

        await pilot.press("delete")
        await pilot.pause()
        assert isinstance(app.screen, _ConfirmModal)

        app.screen.query_one("#no-btn").press()
        await pilot.pause()

        assert manager.get_book(book_id) is not None
