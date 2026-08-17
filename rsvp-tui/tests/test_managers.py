from pathlib import Path

import pytest

from rsvp_tui.managers.library_manager import LibraryManager
from rsvp_tui.managers.note_manager import NoteManager


def test_note_manager_lifecycle(tmp_path: Path) -> None:
    notes_dir = tmp_path / "notes"
    mgr = NoteManager(notes_dir)
    book_id = "test_book"

    # Create
    note = mgr.create_note(
        book_id=book_id,
        word_index=100,
        chapter_index=0,
        content="Testing notes",
        tags=["test"],
        word_context="sample",
    )
    assert note.content == "Testing notes"
    assert mgr.get_note_count(book_id) == 1

    # Retrieve
    notes = mgr.get_notes_for_book(book_id)
    assert len(notes) == 1
    assert notes[0].id == note.id

    # Search
    results = mgr.search_notes(book_id, "Testing")
    assert len(results) == 1

    # Delete
    mgr.delete_note(book_id, note.id)
    assert mgr.get_note_count(book_id) == 0


def test_library_manager_db_init(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    LibraryManager(db_path)
    assert db_path.exists()

    # Check if tables exist
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "books" in tables
        assert "chapters" in tables


def test_library_manager_import_markdown(tmp_path: Path) -> None:
    db_path = tmp_path / "library.db"
    mgr = LibraryManager(db_path)

    # Create a dummy markdown file
    md_file = tmp_path / "test.md"
    md_file.write_text("# Chapter 1\n\nWord1 Word2 Word3.")

    book = mgr.import_book(md_file)
    assert book.title == "Chapter 1"
    assert book.word_count > 0
    assert len(book.chapters) == 1

    # Check if it was saved
    saved_book = mgr.get_book(book.id)
    assert saved_book is not None
    assert saved_book.title == "Chapter 1"

    # Check cache
    words = mgr.load_words(book.id)
    assert len(words) > 0
    assert words[0] == "Word1"


def test_library_manager_cache_round_trip_is_reader_tolerant(tmp_path: Path) -> None:
    """The cache written by import_book must round-trip via the same loader
    the ReaderScreen uses (it does `words_data.get("words", [])`).
    """
    import json

    from rsvp_tui.models import Config

    db_path = tmp_path / "library.db"
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()

    # Patch Config defaults so cache_dir is writable
    Config.cache_dir = cache_dir  # type: ignore[misc]

    mgr = LibraryManager(db_path)
    md_file = tmp_path / "t.md"
    md_file.write_text("# A\n\nalpha beta gamma.")
    book = mgr.import_book(md_file)

    # 1. load_words returns the words (the canonical loader)
    words = mgr.load_words(book.id)
    assert words == ["alpha", "beta", "gamma."]

    # 2. The on-disk JSON MUST be a dict envelope so reader_screen.py's
    #    `words_data.get("words", [])` loader works. A bare-list shape
    #    crashes with AttributeError ("list has no .get") in _on_file_selected.
    cache_path = cache_dir / f"{book.id}.json"
    raw = json.loads(cache_path.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), (
        f"cache file must be dict-shaped envelope, got {type(raw).__name__}"
    )
    assert raw["words"] == ["alpha", "beta", "gamma."]


def test_note_manager_handles_unicode(tmp_path: Path) -> None:
    """Notes with non-ASCII content must survive a save/load round-trip on
    Windows cp1252 default. (Regression: open() without encoding='utf-8'
    would raise UnicodeDecodeError on read.)
    """
    notes_dir = tmp_path / "notes"
    mgr = NoteManager(notes_dir)
    book_id = "unicode_book"

    mgr.create_note(
        book_id=book_id,
        word_index=1,
        chapter_index=0,
        content="Café — naïve résumé. 漢字テスト.",
        tags=["unicode"],
        word_context="café",
    )

    notes = mgr.get_notes_for_book(book_id)
    assert len(notes) == 1
    assert notes[0].content == "Café — naïve résumé. 漢字テスト."


def test_note_manager_logs_warning_on_corrupt_notes_json(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Corrupt notes.json must not silently look like 'no notes' — the user
    loses data without ever knowing. The manager should log a warning so
    the issue is visible in the log file / telemetry.
    """
    import logging

    notes_dir = tmp_path / "notes"
    book_id = "corrupt_book"
    book_dir = notes_dir / book_id
    book_dir.mkdir(parents=True)
    notes_file = book_dir / "notes.json"
    # Truncated JSON — will raise JSONDecodeError on load.
    notes_file.write_text('[{"id": "note_x", "conte', encoding="utf-8")

    mgr = NoteManager(notes_dir)

    with caplog.at_level(logging.WARNING, logger="rsvp_tui.managers.note_manager"):
        notes = mgr.get_notes_for_book(book_id)

    # Don't lose the user's data — return an empty list but TELL someone.
    assert notes == []
    assert any(
        "corrupt" in rec.message.lower() or "json" in rec.message.lower()
        for rec in caplog.records
    ), f"expected a warning log, got: {[r.message for r in caplog.records]}"


def test_note_manager_atomic_save_no_partial_file(
    tmp_path: Path, monkeypatch
) -> None:
    """If os.replace fails mid-save, the existing notes file is untouched."""
    notes_dir = tmp_path / "notes"
    mgr = NoteManager(notes_dir)
    book_id = "atomic_book"

    mgr.create_note(book_id, 1, 0, "original note", [], "ctx")
    notes_file = notes_dir / book_id / "notes.json"
    assert notes_file.exists()
    original_bytes = notes_file.read_bytes()

    # Force os.replace to fail mid-save
    def boom(src: str, dst: str) -> None:
        raise OSError("simulated crash")

    monkeypatch.setattr("os.replace", boom)

    with pytest.raises(OSError):
        mgr.create_note(book_id, 2, 0, "second note", [], "ctx")

    # Original file untouched
    assert notes_file.read_bytes() == original_bytes
    # No stray .tmp file left behind
    tmp = notes_file.with_suffix(notes_file.suffix + ".tmp")
    assert not tmp.exists()
