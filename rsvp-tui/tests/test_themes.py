"""Tests for the themes module."""

from rsvp_tui.themes import (
    THEMES,
    all_themes,
    cycle_theme,
    default_theme,
    get_theme,
)


def test_three_themes_defined():
    """We ship with at least 3 named themes (Phase 0 requirement)."""
    ids = set(THEMES.keys())
    assert {"dark", "light", "solarized"} <= ids


def test_default_theme_is_dark():
    assert default_theme().id == "dark"


def test_get_theme_falls_back_for_unknown():
    """An unknown theme id must not crash — fall back to dark."""
    theme = get_theme("nonexistent")
    assert theme.id == "dark"


def test_get_theme_known_returns_itself():
    theme = get_theme("solarized")
    assert theme.id == "solarized"
    assert theme.orp == "bold #dc322f"


def test_cycle_theme_wraps():
    """cycle_theme moves to the next theme in registration order."""
    ids = list(THEMES.keys())
    first = ids[0]
    second = cycle_theme(first)
    assert second.id == ids[1]
    # Wrap around
    last = ids[-1]
    wrapped = cycle_theme(last)
    assert wrapped.id == first


def test_all_themes_returns_list():
    themes = all_themes()
    assert isinstance(themes, list)
    assert len(themes) == len(THEMES)
