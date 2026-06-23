import pytest
from pathlib import Path
import tempfile
import shutil
from rsvp_tui.models import Config, Book, Chapter

@pytest.fixture
def mock_config(tmp_path):
    """Create a mock config with temp paths."""
    config = Config(
        library_db_path=tmp_path / "library.db",
        notes_dir=tmp_path / "notes",
        cache_dir=tmp_path / "cache",
    )
    config.notes_dir.mkdir(parents=True, exist_ok=True)
    config.cache_dir.mkdir(parents=True, exist_ok=True)
    return config

@pytest.fixture
def sample_book():
    """A sample Book object for testing."""
    chapters = [
        Chapter(title="Chapter 1", start_word_index=0, end_word_index=10, word_count=10),
        Chapter(title="Chapter 2", start_word_index=10, end_word_index=25, word_count=15),
    ]
    return Book(
        id="test_book_123",
        title="Test Book",
        author="Test Author",
        file_type="md",
        word_count=25,
        chapters=chapters,
    )
