"""Data models for RSVP TUI."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# v3 schema marker. Kept as a module constant so tests and the
# ConfigManager can import it without a circular dependency on
# managers.config_manager.
CURRENT_SCHEMA_VERSION = 3


class FileType(str, Enum):
    """Supported file types."""

    PDF = "pdf"
    EPUB = "epub"
    MARKDOWN = "md"
    TEXT = "txt"


@dataclass
class Chapter:
    """Represents a chapter or section of a book."""

    title: str
    start_word_index: int
    end_word_index: int
    word_count: int = 0

    def __post_init__(self) -> None:
        if self.word_count == 0:
            self.word_count = self.end_word_index - self.start_word_index

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "start_word_index": self.start_word_index,
            "end_word_index": self.end_word_index,
            "word_count": self.word_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Chapter":
        return cls(**data)


@dataclass
class Book:
    """Represents a book or document."""

    id: str
    title: str
    author: str = "Unknown"
    file_path: Path | None = None
    file_type: str = "txt"

    # Content info
    word_count: int = 0
    chapters: list[Chapter] = field(default_factory=list)

    # Reading state
    current_word_index: int = 0
    current_chapter_index: int = 0

    # Metadata
    added_date: datetime = field(default_factory=datetime.now)
    last_read_date: datetime | None = None
    total_reading_time_seconds: int = 0

    # Cache
    cache_file_path: Path | None = None

    @property
    def completion_percentage(self) -> float:
        """Calculate reading completion percentage."""
        if self.word_count == 0:
            return 0.0
        return (self.current_word_index / self.word_count) * 100

    @property
    def current_chapter(self) -> Chapter | None:
        """Get current chapter."""
        if not self.chapters:
            return None
        idx = min(self.current_chapter_index, len(self.chapters) - 1)
        return self.chapters[idx]

    def get_chapter_for_word(self, word_index: int) -> Chapter | None:
        """Find chapter containing given word index."""
        for chapter in self.chapters:
            if chapter.start_word_index <= word_index <= chapter.end_word_index:
                return chapter
        return None

    def update_progress(self, word_index: int) -> None:
        """Update reading progress."""
        self.current_word_index = min(word_index, self.word_count)
        self.last_read_date = datetime.now()

        # Update chapter index
        for i, chapter in enumerate(self.chapters):
            if chapter.start_word_index <= self.current_word_index <= chapter.end_word_index:
                self.current_chapter_index = i
                break

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "file_path": str(self.file_path) if self.file_path else None,
            "file_type": self.file_type,
            "word_count": self.word_count,
            "chapters": [c.to_dict() for c in self.chapters],
            "current_word_index": self.current_word_index,
            "current_chapter_index": self.current_chapter_index,
            "added_date": self.added_date.isoformat(),
            "last_read_date": self.last_read_date.isoformat() if self.last_read_date else None,
            "total_reading_time_seconds": self.total_reading_time_seconds,
            "cache_file_path": str(self.cache_file_path) if self.cache_file_path else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Book":
        """Create Book from dictionary."""
        chapters = [Chapter.from_dict(c) for c in data.get("chapters", [])]

        return cls(
            id=data["id"],
            title=data["title"],
            author=data.get("author", "Unknown"),
            file_path=Path(data["file_path"]) if data.get("file_path") else None,
            file_type=data.get("file_type", "txt"),
            word_count=data.get("word_count", 0),
            chapters=chapters,
            current_word_index=data.get("current_word_index", 0),
            current_chapter_index=data.get("current_chapter_index", 0),
            added_date=(
                datetime.fromisoformat(data["added_date"])
                if data.get("added_date")
                else datetime.now()
            ),
            last_read_date=(
                datetime.fromisoformat(data["last_read_date"])
                if data.get("last_read_date")
                else None
            ),
            total_reading_time_seconds=data.get("total_reading_time_seconds", 0),
            cache_file_path=Path(data["cache_file_path"]) if data.get("cache_file_path") else None,
        )


@dataclass
class Note:
    """Represents a note linked to a reading position."""

    id: str
    book_id: str
    word_index: int
    chapter_index: int
    content: str
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    word_context: str = ""

    def to_markdown(self) -> str:
        """Convert note to markdown format."""
        tags_str = ", ".join(self.tags) if self.tags else "none"
        return f"""## Note at word {self.word_index}

**Context:** {self.word_context}
**Chapter:** {self.chapter_index}
**Tags:** {tags_str}
**Created:** {self.created_at.strftime("%Y-%m-%d %H:%M")}

{self.content}

---
"""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "book_id": self.book_id,
            "word_index": self.word_index,
            "chapter_index": self.chapter_index,
            "content": self.content,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "word_context": self.word_context,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Note":
        return cls(
            id=data["id"],
            book_id=data["book_id"],
            word_index=data["word_index"],
            chapter_index=data["chapter_index"],
            content=data["content"],
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            word_context=data.get("word_context", ""),
        )


@dataclass
class ReadingSession:
    """Represents an active reading session."""

    book_id: str
    start_time: datetime = field(default_factory=datetime.now)
    current_word_index: int = 0
    wpm: int = 300
    is_playing: bool = False

    # Statistics
    words_read: int = 0
    pauses_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "book_id": self.book_id,
            "start_time": self.start_time.isoformat(),
            "current_word_index": self.current_word_index,
            "wpm": self.wpm,
            "is_playing": self.is_playing,
            "words_read": self.words_read,
            "pauses_count": self.pauses_count,
        }


@dataclass
class SessionStats:
    """Statistics for a reading session."""

    duration_seconds: int
    words_read: int
    average_wpm: float
    effective_wpm: float
    completion_percentage: float


@dataclass
class Config:
    """Application configuration.

    Note: persistence is delegated to ``managers.config_manager.ConfigManager``.
    ``Config.save()`` and ``Config.load()`` remain as thin shims so existing
    callers (``LibraryManager``, ``NoteManager``, the CLI) keep working.
    """

    # --- v1 fields (preserved for backward compatibility) ---

    # Reading settings
    default_wpm: int = 300
    min_wpm: int = 100
    max_wpm: int = 1000
    wpm_step: int = 25

    # Timing settings
    punctuation_multiplier: float = 2.0
    pause_on_punctuation: bool = True
    pause_chars: list[str] = field(default_factory=lambda: [".", "!", "?", ";", ":"])
    comma_pause_multiplier: float = 1.5

    # Display settings
    enable_orp: bool = True
    focus_mode: bool = False
    show_progress_bar: bool = True
    show_context_words: bool = False

    # --- v2 fields (added by migration) ---

    schema_version: int = 2
    theme: str = "dark"
    figure_id: str = "word"
    figure_params: dict[str, dict[str, Any]] = field(default_factory=dict)
    keybindings: dict[str, str] = field(default_factory=dict)

    # --- v3 fields (added by migration) ---

    page_size: int = 500  # words per "page" for pagination
    show_navigation_panel: bool = True  # show chapter/page navigation in reader
    show_note_panel: bool = True  # show note panel in reader

    # --- v3.1 fields (horizontal reading) ---

    display_mode: str = "word"  # word, horizontal, line, chunk
    chunk_size: int = 7  # words per chunk (3, 5, 7, 9, 11, 15)
    text_alignment: str = "center"  # center, left, dynamic
    highlight_style: str = "focal"  # focal, bionic, central, full
    highlight_color: str = "red"  # red, cyan, green, yellow, magenta, white
    peripheral_opacity: int = 100  # 100, 75, 50, 25
    auto_advance: bool = True  # auto-advance to next word/chunk
    advance_trigger: str = "time"  # time, manual, hybrid

    # --- Storage paths ---

    library_db_path: Path = field(default_factory=lambda: Path.home() / ".rsvp" / "library.db")
    notes_dir: Path = field(default_factory=lambda: Path.home() / ".rsvp" / "notes")
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".rsvp" / "cache")
    config_path: Path = field(default_factory=lambda: Path.home() / ".rsvp" / "config.json")

    def __post_init__(self) -> None:
        """Clamp ``default_wpm`` to the configured range.

        Loading untrusted JSON from disk could otherwise leave us with
        a wpm value outside ``[min_wpm, max_wpm]``; we silently clamp
        here so the rest of the app can assume the invariant holds.
        """
        lo = min(self.min_wpm, self.max_wpm)
        hi = max(self.min_wpm, self.max_wpm)
        if self.default_wpm < lo:
            self.default_wpm = lo
        elif self.default_wpm > hi:
            self.default_wpm = hi

    # ---- Persistence (delegated to ConfigManager) ----

    def save(self) -> None:
        """Save configuration to JSON file (atomic)."""
        # Imported lazily to avoid a circular import at module load.
        from .managers.config_manager import ConfigManager

        manager = ConfigManager(self.config_path)
        manager.save(self)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from JSON file, migrating as needed.

        Returns a default ``Config`` (and writes it to disk) if the file
        does not exist or cannot be parsed.
        """
        from .managers.config_manager import ConfigManager

        manager = ConfigManager()
        return manager.load()
