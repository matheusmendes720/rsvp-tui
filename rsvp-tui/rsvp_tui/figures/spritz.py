"""SpritzFigure — pivot-character highlight with right-aligned padding.

The Spritz-style reader centers the *pivot character* (the ORP
letter) at a fixed column on screen. Surrounding letters are
right-padded with spaces so the pivot of every word lands at the
same horizontal position, reducing saccades. The result is a fixed
column for the eye, very fast for high-WPM reading.
"""

from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from .. import calculate_orp_index, split_word_for_display
from ..themes import get_theme
from .base import Figure


class SpritzFigure(Figure):
    """Spritz-style display: right-padded word with pivot character at fixed column."""

    id = "spritz"
    name = "Spritz"
    description = "Pivot letter at a fixed column; right-padded to align."
    default_keybinding = "5"
    default_params: dict[str, Any] = {
        "orp_enabled": True,
        "padding": 12,
    }

    DEFAULT_CSS = """
    SpritzFigure {
        content-align: center middle;
        text-align: center;
    }
    """

    def _on_init(self) -> None:
        self._theme = get_theme("dark")

    def render(self):  # type: ignore[override]
        current = self._current_word()
        if not current:
            return Panel(
                Align.center(Text("Ready", style="dim")),
                border_style=self._theme.border_idle,
            )

        padding = max(0, int(self.get_param("padding", 12)))

        if self.get_param("orp_enabled", True):
            orp_idx = calculate_orp_index(current)
            parts = split_word_for_display(current, orp_idx)
            text = Text()
            if parts.before_orp:
                text.append(parts.before_orp, style=self._theme.orp_anchor)
            text.append(parts.orp_char, style=self._theme.orp)
            if parts.after_orp:
                text.append(parts.after_orp, style=self._theme.orp_anchor)
            text.append(" " * padding, style="default")
        else:
            text = Text()
            text.append(current, style=self._theme.orp_anchor)
            text.append(" " * padding, style="default")

        return Panel(
            Align.center(text),
            border_style=self._theme.border_active if self.is_playing else self._theme.border_idle,
            title=self._progress_title(),
        )

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%)"
