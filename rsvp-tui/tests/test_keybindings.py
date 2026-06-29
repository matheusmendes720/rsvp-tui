"""Tests for the centralized keybindings module."""

from rsvp_tui.keybindings import (
    BINDING_DESCRIPTIONS,
    DEFAULT_BINDINGS,
    merged_bindings,
    resolve,
)


def test_defaults_match_legacy_bindings() -> None:
    """The default bindings keep the legacy 0.1.x muscle memory."""
    assert DEFAULT_BINDINGS["toggle_play"] == "space"
    assert DEFAULT_BINDINGS["next_figure"] == "n"
    assert DEFAULT_BINDINGS["prev_figure"] == "shift+n"
    assert DEFAULT_BINDINGS["show_library"] == "l"
    assert DEFAULT_BINDINGS["show_settings"] == "s"
    assert DEFAULT_BINDINGS["quit"] == "q"


def test_resolve_returns_default() -> None:
    assert resolve("toggle_play") == "space"


def test_resolve_honors_user_override() -> None:
    overrides = {"toggle_play": "p"}
    assert resolve("toggle_play", overrides) == "p"
    # Non-overridden action still returns default
    assert resolve("quit", overrides) == "q"


def test_resolve_unknown_action_returns_empty_string() -> None:
    assert resolve("does_not_exist") == ""


def test_merged_bindings_overrides_apply() -> None:
    overrides = {"toggle_play": "p", "next_figure": "."}
    merged = merged_bindings(overrides)
    assert merged["toggle_play"] == "p"
    assert merged["next_figure"] == "."
    # Other actions unchanged
    assert merged["quit"] == "q"


def test_descriptions_cover_defaults() -> None:
    """Every default action has a human-readable description."""
    for action in DEFAULT_BINDINGS:
        assert action in BINDING_DESCRIPTIONS, f"missing description for {action}"
        assert BINDING_DESCRIPTIONS[action], f"empty description for {action}"
