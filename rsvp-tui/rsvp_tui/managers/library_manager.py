"""Library management for books."""

import json
import logging
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from .. import parse_epub_path, parse_markdown, parse_pdf_path, parse_plain_text, tokenize_text
from ..logging_ import telemetry
from ..models import Book, Chapter, FileType

log = logging.getLogger(__name__)


class LibraryManager:
    """Manages book library with SQLite backend."""

    def __init__(self, db_path: Path | None = None):
        from ..models import Config
        if db_path is None:
            config = Config.load()
            db_path = config.library_db_path

        self.db_path = db_path
        self.cache_dir = db_path.parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self._init_db()
        log.info(
            "LibraryManager init: db=%s cache=%s",
            self.db_path,
            self.cache_dir,
        )

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT,
                    file_path TEXT,
                    file_type TEXT,
                    word_count INTEGER DEFAULT 0,
                    current_word_index INTEGER DEFAULT 0,
                    current_chapter_index INTEGER DEFAULT 0,
                    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_read_date TIMESTAMP,
                    total_reading_time_seconds INTEGER DEFAULT 0,
                    cache_file_path TEXT,
                    data JSON
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS chapters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id TEXT,
                    chapter_index INTEGER,
                    title TEXT,
                    start_word_index INTEGER,
                    end_word_index INTEGER,
                    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
                )
            """)

            conn.commit()

    def import_book(self, file_path: Path) -> Book:
        """Import a book from file."""
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Detect file type
        suffix = file_path.suffix.lower()
        file_type_map = {
            ".md": FileType.MARKDOWN,
            ".markdown": FileType.MARKDOWN,
            ".txt": FileType.TEXT,
            ".epub": FileType.EPUB,
            ".pdf": FileType.PDF,
        }

        file_type = file_type_map.get(suffix)
        if file_type is None:
            raise ValueError(f"Unsupported file type: {suffix}")

        # Parse file
        content = file_path.read_bytes()

        if file_type == FileType.MARKDOWN:
            text = content.decode("utf-8", errors="replace")
            result = parse_markdown(text)
        elif file_type == FileType.TEXT:
            text = content.decode("utf-8", errors="replace")
            result = parse_plain_text(text)
        elif file_type == FileType.EPUB:
            # For EPUB, use path directly for better performance
            result = parse_epub_path(file_path)
        elif file_type == FileType.PDF:
            # For PDF, use path directly for faster parsing
            result = parse_pdf_path(file_path)

        # Generate unique ID
        book_id = f"book_{uuid.uuid4().hex[:16]}"

        # Create book object
        chapters = [
            Chapter(
                title=ch.title,
                start_word_index=ch.start_word_index,
                end_word_index=ch.end_word_index,
            )
            for ch in result.chapters
        ]

        book = Book(
            id=book_id,
            title=result.title or file_path.stem,
            author=result.author or "Unknown",
            file_path=file_path,
            file_type=file_type.value,
            word_count=result.word_count,
            chapters=chapters,
            added_date=datetime.now(),
        )

        # Cache tokenized words
        words = tokenize_text(result.plain_text)
        cache_path = self.cache_dir / f"{book_id}.json"
        with open(cache_path, "w") as f:
            json.dump(words, f)
        book.cache_file_path = cache_path

        # Save to database
        self._save_book_to_db(book)

        log.info(
            "book.import: id=%s title=%r file_type=%s word_count=%d",
            book_id,
            book.title,
            file_type.value,
            len(words),
        )
        telemetry.book_import(
            book_id=book_id,
            title=book.title,
            file_type=file_type.value,
            word_count=len(words),
        )

        return book

    def _save_book_to_db(self, book: Book):
        """Save book to database."""
        with sqlite3.connect(self.db_path) as conn:
            # Save book
            conn.execute("""
                INSERT INTO books (
                    id, title, author, file_path, file_type, word_count,
                    current_word_index, current_chapter_index, added_date,
                    last_read_date, total_reading_time_seconds, cache_file_path, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                book.id,
                book.title,
                book.author,
                str(book.file_path) if book.file_path else None,
                book.file_type,
                book.word_count,
                book.current_word_index,
                book.current_chapter_index,
                book.added_date.isoformat(),
                book.last_read_date.isoformat() if book.last_read_date else None,
                book.total_reading_time_seconds,
                str(book.cache_file_path) if book.cache_file_path else None,
                json.dumps(book.to_dict()),
            ))

            # Save chapters
            for i, chapter in enumerate(book.chapters):
                conn.execute("""
                    INSERT INTO chapters (
                        book_id, chapter_index, title, start_word_index, end_word_index
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    book.id,
                    i,
                    chapter.title,
                    chapter.start_word_index,
                    chapter.end_word_index,
                ))

            conn.commit()

    def list_books(self, search: str | None = None) -> list[Book]:
        """List all books in library."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if search:
                cursor = conn.execute(
                    """SELECT data FROM books 
                       WHERE title LIKE ? OR author LIKE ?
                       ORDER BY last_read_date DESC NULLS LAST, added_date DESC""",
                    (f"%{search}%", f"%{search}%")
                )
            else:
                cursor = conn.execute(
                    """SELECT data FROM books 
                       ORDER BY last_read_date DESC NULLS LAST, added_date DESC"""
                )

            books = []
            for row in cursor:
                data = json.loads(row["data"])
                books.append(Book.from_dict(data))

            return books

    def get_book(self, book_id: str) -> Book | None:
        """Get book by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            row = conn.execute(
                "SELECT data FROM books WHERE id = ?",
                (book_id,)
            ).fetchone()

            if row:
                data = json.loads(row["data"])
                return Book.from_dict(data)

            return None

    def update_progress(self, book_id: str, word_index: int):
        """Update reading progress."""
        with sqlite3.connect(self.db_path) as conn:
            book = self.get_book(book_id)
            if book:
                book.update_progress(word_index)

                conn.execute(
                    """UPDATE books
                       SET current_word_index = ?,
                           current_chapter_index = ?,
                           last_read_date = ?,
                           data = ?
                       WHERE id = ?""",
                    (
                        book.current_word_index,
                        book.current_chapter_index,
                        book.last_read_date.isoformat() if book.last_read_date else None,
                        json.dumps(book.to_dict()),
                        book_id,
                    )
                )
                conn.commit()
                log.debug(
                    "progress.update: book_id=%s word_index=%d/%d",
                    book_id,
                    word_index,
                    book.word_count,
                )

    def delete_book(self, book_id: str):
        """Remove book from library."""
        with sqlite3.connect(self.db_path) as conn:
            # Get cache file path before deletion
            row = conn.execute(
                "SELECT cache_file_path FROM books WHERE id = ?",
                (book_id,)
            ).fetchone()

            # Delete from database
            conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
            conn.commit()

            # Delete cache file
            if row and row[0]:
                cache_path = Path(row[0])
                if cache_path.exists():
                    cache_path.unlink()

        log.info("book.delete: book_id=%s", book_id)

    def load_words(self, book_id: str) -> list[str]:
        """Load cached words for a book."""
        book = self.get_book(book_id)
        if not book or not book.cache_file_path:
            log.warning("load_words: cache miss for book_id=%s", book_id)
            return []

        try:
            with open(book.cache_file_path) as f:
                words = json.load(f)
            log.debug("load_words: book_id=%s count=%d", book_id, len(words))
            return words
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            log.error(
                "load_words: failed for book_id=%s: %s",
                book_id,
                exc,
                exc_info=True,
            )
            return []

    def get_statistics(self) -> dict[str, Any]:
        """Get library statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total_books = conn.execute("SELECT COUNT(*) FROM books").fetchone()[0]
            total_words = conn.execute("SELECT SUM(word_count) FROM books").fetchone()[0] or 0

            recently_read = conn.execute(
                """SELECT title, current_word_index, word_count 
                   FROM books 
                   WHERE last_read_date IS NOT NULL
                   ORDER BY last_read_date DESC LIMIT 5"""
            ).fetchall()

            return {
                "total_books": total_books,
                "total_words": total_words,
                "recently_read": [
                    {
                        "title": r[0],
                        "progress": (r[1] / r[2] * 100) if r[2] > 0 else 0,
                    }
                    for r in recently_read
                ],
            }
