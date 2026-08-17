"""Behavior and performance tests for NotePanel."""

from __future__ import annotations

from pathlib import Path

import pytest
from textual.app import App

from rsvp_tui.managers.note_manager import NoteManager
from rsvp_tui.widgets.note_panel import NotePanel


@pytest.mark.asyncio
async def test_note_panel_does_not_re_read_notes_per_word(tmp_path: Path) -> None:
    """``watch_current_word_index`` must NOT re-read ``notes.json`` from
    disk on every reactive change.

    Regression: at 300+ WPM, ``_load_notes()`` ran 5+ Hz — disk read +
    JSON parse + ``Note.from_dict()`` reconstruction per word during
    RSVP reading. The fix caches parsed notes by ``book_id`` so per-word
    updates only filter the in-memory list.
    """
    notes_dir = tmp_path / "notes"
    mgr = NoteManager(notes_dir)
    book_id = "perf_book"
    for i in range(5):
        mgr.create_note(book_id, i * 100, 0, f"note {i}", [], "ctx")

    class PanelApp(App):
        def compose(self):
            yield NotePanel(mgr, id="panel")

    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(NotePanel)
        panel.current_book_id = book_id
        panel.current_word_index = 0
        await pilot.pause()

        # Spy on the disk-read method. After the first book load (or
        # never, if pre-cached), no further reads should happen.
        call_count = 0
        original = mgr._load_notes_for_book

        def spy(book_id_arg: str):
            nonlocal call_count
            call_count += 1
            return original(book_id_arg)

        mgr._load_notes_for_book = spy  # type: ignore[method-assign]

        # Simulate RSVP reading: 100 word-index updates.
        for w in range(1, 101):
            panel.current_word_index = w
        await pilot.pause()

        assert call_count <= 1, (
            f"notes.json was read {call_count} times during 100 position "
            f"changes; expected <= 1 (cache-by-book-id)."
        )


@pytest.mark.asyncio
async def test_note_panel_refresh_notes_re_reads_after_save(
    tmp_path: Path,
) -> None:
    """After a new note is saved externally, ``refresh_notes()`` must
    reload from disk so the panel sees it.

    This guards the cache invalidation hook — if we cache forever, edits
    from elsewhere never appear.
    """
    notes_dir = tmp_path / "notes"
    mgr = NoteManager(notes_dir)
    book_id = "refresh_book"
    # Place "first" and "second" within ±50 of the panel's current
    # word_index (100) so both should appear in the rendered output
    # after refresh_notes() reloads them from disk.
    mgr.create_note(book_id, 100, 0, "first", [], "ctx")

    class PanelApp(App):
        def compose(self):
            yield NotePanel(mgr, id="panel")

    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(NotePanel)
        panel.current_book_id = book_id
        panel.current_word_index = 100
        await pilot.pause()

        # Save a note externally AFTER the panel mounted (so the
        # in-memory cache still holds only "first"), then refresh.
        mgr.create_note(book_id, 125, 0, "second", [], "ctx")
        panel.refresh_notes()
        await pilot.pause()

        # The cached display should now include the new note's content.
        from textual.widgets import Static

        notes_list = panel.query_one("#notes-list", Static)
        rendered = notes_list.renderable if hasattr(notes_list, "renderable") else str(notes_list.render())
        assert "second" in str(rendered), (
            f"refresh_notes() did not pick up newly-saved note; "
            f"rendered: {rendered!r}"
        )


@pytest.mark.asyncio
async def test_note_panel_switching_books_reloads(tmp_path: Path) -> None:
    """When ``current_book_id`` changes, the cache must reload from
    disk for the new book (notes from book A must not leak into book B).
    """
    notes_dir = tmp_path / "notes"
    mgr = NoteManager(notes_dir)
    mgr.create_note("book_a", 100, 0, "alpha", [], "ctx")
    mgr.create_note("book_b", 100, 0, "beta", [], "ctx")

    class PanelApp(App):
        def compose(self):
            yield NotePanel(mgr, id="panel")

    app = PanelApp()
    async with app.run_test() as pilot:
        panel = app.query_one(NotePanel)
        panel.current_book_id = "book_a"
        panel.current_word_index = 100
        await pilot.pause()

        from textual.widgets import Static

        notes_list = panel.query_one("#notes-list", Static)

        def rendered_text() -> str:
            r = notes_list.renderable if hasattr(notes_list, "renderable") else str(notes_list.render())
            return str(r)

        assert "alpha" in rendered_text()
        assert "beta" not in rendered_text()

        # Switch books
        panel.current_book_id = "book_b"
        panel.current_word_index = 100
        await pilot.pause()

        assert "beta" in rendered_text()
        assert "alpha" not in rendered_text()