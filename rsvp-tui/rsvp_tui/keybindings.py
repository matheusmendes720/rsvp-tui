"""Centralized keybinding configuration for the RSVP TUI.

Keybindings are mapped from a stable *action name* (e.g. ``"toggle_play"``)
to a Textual key string (e.g. ``"space"``). Users can override individual
actions in their ``Config.keybindings`` map; the resolver merges overrides
over the defaults so the schema is forward-compatible — adding new actions
in code does not break old configs.

Why centralize: the legacy app scattered key strings across ``app.py``
and each widget. A single source of truth makes help text, command
palette population, and rebinding consistent.

Usage:
    from rsvp_tui.keybindings import resolve, BINDING_DESCRIPTIONS

    binding = resolve("toggle_play", user_overrides={...})
    # => "space"
"""

from __future__ import annotations

from collections.abc import Mapping

# Default action -> key string map. These match the existing UX of the
# legacy app (``space`` for play/pause, ``n`` for next figure, etc.) so
# users upgrading from 0.1.x keep their muscle memory.
DEFAULT_BINDINGS: dict[str, str] = {
    # Global
    "quit": "q",
    "show_library": "l",
    "show_settings": "s",
    "show_help": "question_mark",
    "command_palette": "ctrl+p",
    # Reading
    "toggle_play": "space",
    "prev_word": "left",
    "next_word": "right",
    "increase_speed": "up",
    "decrease_speed": "down",
    "jump_start": "home",
    "jump_end": "end",
    "toggle_focus": "f",
    "toggle_panel": "tab",
    # Figures
    "next_figure": "n",
    "prev_figure": "shift+n",
    "figure_picker": "ctrl+g",
    # Notes
    "add_note": "ctrl+n",
}


# Human-readable descriptions used in the help screen and command
# palette. Keep these in sync with ``DEFAULT_BINDINGS`` — when you add
# a new action, add a description here too.
BINDING_DESCRIPTIONS: dict[str, str] = {
    "quit": "Quit",
    "show_library": "Open library",
    "show_settings": "Open settings",
    "show_help": "Show help",
    "command_palette": "Command palette",
    "toggle_play": "Play / pause",
    "prev_word": "Previous word",
    "next_word": "Next word",
    "increase_speed": "Faster",
    "decrease_speed": "Slower",
    "jump_start": "Jump to start",
    "jump_end": "Jump to end",
    "toggle_focus": "Focus mode",
    "toggle_panel": "Toggle side panel",
    "next_figure": "Next figure",
    "prev_figure": "Previous figure",
    "figure_picker": "Figure picker",
    "add_note": "Add note at current position",
}


def resolve(action: str, overrides: Mapping[str, str] | None = None) -> str:
    """Return the key string for ``action``, honoring user overrides.

    Unknown actions fall back to a sensible empty string so callers can
    still build a Binding() — Textual will warn at startup if the key
    is invalid, which is the right place to surface the error.
    """
    if overrides and action in overrides:
        return overrides[action]
    return DEFAULT_BINDINGS.get(action, "")


def merged_bindings(overrides: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a complete action->key map with overrides applied."""
    merged = dict(DEFAULT_BINDINGS)
    if overrides:
        merged.update(overrides)
    return merged


__all__ = [
    "DEFAULT_BINDINGS",
    "BINDING_DESCRIPTIONS",
    "resolve",
    "merged_bindings",
]
