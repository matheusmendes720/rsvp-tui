import json
from pathlib import Path

import pytest

from rsvp_tui.managers.config_manager import ConfigManager
from rsvp_tui.models import CURRENT_SCHEMA_VERSION, Book, Chapter, Config, Note


def test_book_serialization(sample_book):
    data = sample_book.to_dict()
    assert data["id"] == sample_book.id
    assert data["title"] == sample_book.title
    assert len(data["chapters"]) == 2

    restored = Book.from_dict(data)
    assert restored.id == sample_book.id
    assert restored.title == sample_book.title
    assert len(restored.chapters) == 2


def test_book_progress(sample_book):
    # 0/25 = 0%
    assert sample_book.completion_percentage == 0.0

    # 12/25 = 48%
    sample_book.current_word_index = 12
    assert sample_book.completion_percentage == 48.0

    # 25/25 = 100%
    sample_book.current_word_index = 25
    assert sample_book.completion_percentage == 100.0


def test_note_to_markdown():
    note = Note(
        id="note_1",
        book_id="book_1",
        word_index=10,
        chapter_index=0,
        content="Interesting fact.",
        tags=["fact"],
        word_context="science",
    )
    md = note.to_markdown()
    assert "## Note at word 10" in md
    assert "Context:** science" in md
    assert "Interesting fact." in md


def test_config_save_load(mock_config, tmp_path):
    mock_config.default_wpm = 450
    # Saving via the shim must write to mock_config.config_path,
    # which the conftest fixture already points at tmp_path.
    mock_config.config_path = tmp_path / "config.json"
    mock_config.save()
    assert mock_config.config_path.exists()


# ---- Phase 0 verification tests --------------------------------------------


def test_config_v1_migrates_to_v2(tmp_path):
    """A v1-shaped JSON file loads with all v2 fields populated."""
    v1_payload = {
        # no schema_version, no v2 fields
        "default_wpm": 425,
        "min_wpm": 100,
        "max_wpm": 900,
        "wpm_step": 25,
        "punctuation_multiplier": 2.0,
        "pause_on_punctuation": True,
        "pause_chars": [".", "!", "?"],
        "comma_pause_multiplier": 1.5,
        "enable_orp": True,
        "focus_mode": False,
        "show_progress_bar": True,
        "show_context_words": False,
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(v1_payload), encoding="utf-8")

    manager = ConfigManager(config_path)
    cfg = manager.load()

    # v1 fields preserved
    assert cfg.default_wpm == 425
    assert cfg.pause_chars == [".", "!", "?"]
    # v2 fields populated with defaults
    assert cfg.schema_version == CURRENT_SCHEMA_VERSION == 2
    assert cfg.theme == "dark"
    assert cfg.figure_id == "word"
    assert cfg.figure_params == {}
    assert cfg.keybindings == {}


def test_config_atomic_write_no_partial_file(tmp_path, monkeypatch):
    """If os.replace fails, the real config file is not corrupted."""
    config_path = tmp_path / "config.json"
    config_path.write_text("ORIGINAL", encoding="utf-8")

    manager = ConfigManager(config_path)

    # Force os.replace to fail mid-save
    def boom(src, dst):
        raise OSError("simulated crash")

    monkeypatch.setattr("os.replace", boom)

    with pytest.raises(OSError):
        manager.update(Config(), default_wpm=550)

    # Original file is untouched
    assert config_path.read_text(encoding="utf-8") == "ORIGINAL"
    # No stray .tmp file left behind
    tmp = config_path.with_suffix(config_path.suffix + ".tmp")
    assert not tmp.exists()


def test_config_invalid_wpm_clamped():
    """default_wpm is clamped to [min_wpm, max_wpm] in __post_init__."""
    # Too low
    cfg = Config(default_wpm=10, min_wpm=100, max_wpm=1000)
    assert cfg.default_wpm == 100

    # Too high
    cfg = Config(default_wpm=9999, min_wpm=100, max_wpm=1000)
    assert cfg.default_wpm == 1000

    # In range
    cfg = Config(default_wpm=500, min_wpm=100, max_wpm=1000)
    assert cfg.default_wpm == 500


def test_config_save_round_trip(tmp_path):
    """save() -> load() round-trips all v2 fields."""
    config_path = tmp_path / "config.json"
    manager = ConfigManager(config_path)
    cfg = manager.load()
    cfg.theme = "solarized"
    cfg.figure_id = "bionic"
    cfg.figure_params = {"bionic": {"bold_ratio": 0.4}}
    cfg.keybindings = {"toggle_play": "space"}
    manager.save(cfg)

    loaded = ConfigManager(config_path).load()
    assert loaded.theme == "solarized"
    assert loaded.figure_id == "bionic"
    assert loaded.figure_params == {"bionic": {"bold_ratio": 0.4}}
    assert loaded.keybindings == {"toggle_play": "space"}


def test_config_corrupt_json_falls_back_to_defaults(tmp_path):
    """A corrupted config returns defaults rather than crashing."""
    config_path = tmp_path / "config.json"
    config_path.write_text("NOT JSON{", encoding="utf-8")
    cfg = ConfigManager(config_path).load()
    # Sanity: defaults are applied
    assert cfg.default_wpm == 300
    assert cfg.theme == "dark"
