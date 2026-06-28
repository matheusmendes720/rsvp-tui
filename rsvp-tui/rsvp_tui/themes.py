"""Color theme definitions for the RSVP TUI.

Themes are a small set of named color tokens consumed by figures, the
SettingsScreen, and the ReaderScreen. They are deliberately tiny — we
keep the palette surface narrow so adding a theme is a one-dataclass
exercise.

Why: prior versions of the app had no theme support at all; users got
one hard-coded blue/red palette. The Phase 0 plan introduces themes as
a first-class concept so per-figure rendering can be themed, the
SettingsScreen can offer a theme picker, and live theme switching is
possible without restart.

Usage:
    from rsvp_tui.themes import THEMES, default_theme, get_theme

    theme = get_theme("dark")
    panel_border = theme.border_active
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """A named palette of color tokens used by figures and chrome.

    Tokens are intentionally simple Rich color strings ("red", "bold
    cyan", "#aabbcc"). Rich handles parsing; we don't need to.
    """

    id: str
    name: str
    primary: str
    accent: str
    orp: str  # the ORP character's color
    orp_anchor: str  # color of the letter anchored at the ORP position
    focus_dim: str  # color for dimmed context words
    muted: str  # color for helper / hint text
    error: str  # error / danger color
    success: str  # success / save color
    border_active: str  # border when widget is active / playing
    border_idle: str  # border when widget is idle
    background: str = "default"
    foreground: str = "default"

    def token(self, name: str) -> str:
        """Return a token by name, falling back to ``muted`` if missing."""
        return getattr(self, name, self.muted)


# --- Concrete themes ---------------------------------------------------------


@dataclass(frozen=True)
class DarkTheme(Theme):
    """The default theme — high contrast on dark terminals."""


@dataclass(frozen=True)
class LightTheme(Theme):
    """A theme tuned for light terminals (solar-ish)."""


@dataclass(frozen=True)
class SolarizedTheme(Theme):
    """Solarized Dark — easy on the eyes for long reading sessions."""


# Theme table — add new themes here. ``id`` is the value stored in
# ``Config.theme``; ``name`` is the human-readable label shown in the
# SettingsScreen theme picker.
THEMES: dict[str, Theme] = {
    "dark": DarkTheme(
        id="dark",
        name="Dark (default)",
        primary="cyan",
        accent="magenta",
        orp="bold red",
        orp_anchor="white",
        focus_dim="dim white",
        muted="grey50",
        error="bold red",
        success="bold green",
        border_active="red",
        border_idle="blue",
    ),
    "light": LightTheme(
        id="light",
        name="Light",
        primary="blue",
        accent="purple",
        orp="bold red",
        orp_anchor="black",
        focus_dim="dim black",
        muted="grey50",
        error="bold red",
        success="bold green",
        border_active="red",
        border_idle="blue",
    ),
    "solarized": SolarizedTheme(
        id="solarized",
        name="Solarized Dark",
        primary="#268bd2",  # blue
        accent="#d33682",  # magenta
        orp="bold #dc322f",  # red
        orp_anchor="#fdf6e3",  # base3
        focus_dim="#586e75",  # base01
        muted="#93a1a1",  # base1
        error="bold #dc322f",
        success="bold #859900",
        border_active="#b58900",
        border_idle="#586e75",
        background="default",
        foreground="#fdf6e3",
    ),
}


def get_theme(theme_id: str) -> Theme:
    """Look up a theme by id, falling back to the default theme.

    Why a helper: settings migrations or a stale Config may carry an
    unknown id. We never want a missing theme to crash startup; we
    fall back to "dark" and continue.
    """
    return THEMES.get(theme_id, THEMES["dark"])


def default_theme() -> Theme:
    """Return the default theme (always the "dark" entry)."""
    return THEMES["dark"]


def all_themes() -> list[Theme]:
    """Return all themes in registration order."""
    return list(THEMES.values())


def cycle_theme(current_id: str) -> Theme:
    """Return the next theme in registration order, wrapping around.

    Useful for the "cycle theme" command in the command palette.
    """
    ids_list = list(THEMES.keys())
    if current_id not in ids_list:
        return default_theme()
    idx = ids_list.index(current_id)
    next_id = ids_list[(idx + 1) % len(ids_list)]
    return THEMES[next_id]


__all__ = [
    "Theme",
    "DarkTheme",
    "LightTheme",
    "SolarizedTheme",
    "THEMES",
    "get_theme",
    "default_theme",
    "all_themes",
    "cycle_theme",
]
