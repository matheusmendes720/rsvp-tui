from rsvp_tui.managers.library_manager import LibraryManager
from rsvp_tui.managers.note_manager import NoteManager


def test_note_manager_lifecycle(tmp_path):
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
        word_context="sample"
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

def test_library_manager_db_init(tmp_path):
    db_path = tmp_path / "library.db"
    mgr = LibraryManager(db_path)
    assert db_path.exists()

    # Check if tables exist
    import sqlite3
    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "books" in tables
        assert "chapters" in tables

def test_library_manager_import_markdown(tmp_path):
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
