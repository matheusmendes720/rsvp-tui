"""Tests for the figure system."""

import pytest

from rsvp_tui.figures.base import Figure, FigureState
from rsvp_tui.figures.registry import FigureRegistry, default_registry, reset_default_registry
from rsvp_tui.figures.word import WordFigure
from rsvp_tui.figures.chunk import ChunkFigure
from rsvp_tui.figures.line import LineFigure
from rsvp_tui.figures.bionic import BionicFigure
from rsvp_tui.figures.spritz import SpritzFigure
from rsvp_tui.figures.pacer import PacerFigure
from rsvp_tui.figures.minimap import MiniMapFigure
from rsvp_tui.figures.stats import StatsFigure


# A 50-word fixture for smoke tests. We build it programmatically so
# the test doesn't fail when someone edits the prose.
WORDS_50 = tuple(f"word{i}" for i in range(50))
assert len(WORDS_50) == 50


def make_state(**overrides):
    defaults = dict(
        words=tuple(WORDS_50),
        word_index=10,
        wpm=300,
        is_playing=False,
        punctuation_multiplier=2.0,
        pause_chars=(".", "!", "?", ";", ":"),
        comma_pause_multiplier=1.5,
    )
    defaults.update(overrides)
    return FigureState(**defaults)


# ---- Registry tests --------------------------------------------------------


def test_default_registry_has_eight_figures():
    reset_default_registry()
    reg = default_registry()
    assert len(reg) == 8
    ids = reg.ids()
    assert ids == ["word", "chunk", "line", "bionic", "spritz", "pacer", "minimap", "stats"]


def test_registry_next_wraps():
    reset_default_registry()
    reg = default_registry()
    assert reg.next("stats").id == "word"
    assert reg.next("word").id == "chunk"
    # Unknown id falls back to first
    assert reg.next("nonexistent").id == "word"


def test_registry_previous_wraps():
    reset_default_registry()
    reg = default_registry()
    assert reg.previous("word").id == "stats"
    assert reg.previous("chunk").id == "word"


def test_registry_by_index_modulo():
    reset_default_registry()
    reg = default_registry()
    assert reg.by_index(0).id == "word"
    assert reg.by_index(7).id == "stats"
    assert reg.by_index(8).id == "word"
    assert reg.by_index(16).id == "word"


def test_custom_registry_isolation():
    """Two separate registries don't see each other's figures."""
    reg_a = FigureRegistry()
    reg_b = FigureRegistry()
    reg_a.register(WordFigure())
    assert "word" in reg_a
    assert "word" not in reg_b


# ---- Smoke render tests for each figure ------------------------------------


ALL_FIGURE_CLASSES = [
    WordFigure,
    ChunkFigure,
    LineFigure,
    BionicFigure,
    SpritzFigure,
    PacerFigure,
    MiniMapFigure,
    StatsFigure,
]


@pytest.mark.parametrize("cls", ALL_FIGURE_CLASSES)
def test_each_figure_renders_smoke(cls):
    """Each figure constructs and renders without error."""
    fig = cls(make_state())
    result = fig.render()
    assert result is not None
    assert fig.word_index == 10


@pytest.mark.parametrize("cls", ALL_FIGURE_CLASSES)
def test_each_figure_pause_idempotent(cls):
    fig = cls(make_state(is_playing=False))
    fig.pause()
    fig.pause()
    assert fig.is_playing is False


@pytest.mark.parametrize("cls", ALL_FIGURE_CLASSES)
def test_each_figure_jump_to_bounds(cls):
    fig = cls(make_state())
    fig.jump_to(0)
    assert fig.word_index == 0
    fig.jump_to(999)
    assert fig.word_index == 49
    fig.jump_to(-5)
    assert fig.word_index == 0


# ---- apply_params tests ----------------------------------------------------


def test_apply_params_live_bionic():
    """Changing bionic.bold_ratio updates the figure."""
    fig = BionicFigure(make_state())
    fig.apply_params({"bold_ratio": 0.8})
    assert fig.get_param("bold_ratio") == 0.8


def test_apply_params_unknown_key_ignored():
    fig = WordFigure(make_state())
    fig.apply_params({"nonexistent_key": "ignored"})
    assert fig.get_param("nonexistent_key", "missing") == "missing"


# ---- FigureState update -----------------------------------------------------


def test_update_state_preserves_position():
    fig = WordFigure(make_state(word_index=10))
    new_state = make_state(word_index=25)
    fig.update_state(new_state)
    assert fig.word_index == 25


def test_update_state_preserves_wpm():
    fig = WordFigure(make_state(wpm=400))
    fig.update_state(make_state(wpm=600))
    assert fig.wpm == 600


# ---- Each figure has the right metadata ------------------------------------


def test_word_figure_metadata():
    fig = WordFigure()
    assert fig.id == "word"
    assert fig.name
    assert fig.description
    assert fig.default_keybinding == "1"
    assert "orp_enabled" in fig.default_params


def test_chunk_figure_metadata():
    fig = ChunkFigure()
    assert fig.id == "chunk"
    assert "chunk_size" in fig.default_params


def test_bionic_figure_metadata():
    fig = BionicFigure()
    assert fig.id == "bionic"
    assert "bold_ratio" in fig.default_params


def test_spritz_figure_metadata():
    fig = SpritzFigure()
    assert fig.id == "spritz"
    assert "padding" in fig.default_params


def test_pacer_figure_metadata():
    fig = PacerFigure()
    assert fig.id == "pacer"
    assert "dot_count" in fig.default_params


def test_minimap_figure_metadata():
    fig = MiniMapFigure()
    assert fig.id == "minimap"
    assert "bar_width" in fig.default_params


def test_stats_figure_metadata():
    fig = StatsFigure()
    assert fig.id == "stats"
    assert "history_size" in fig.default_params
