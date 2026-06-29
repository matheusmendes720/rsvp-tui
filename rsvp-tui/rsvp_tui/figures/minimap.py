"""MiniMapFigure — vertical scrubber with the current word above.

A side-by-side layout: the current word (with ORP) on the top, a
vertical character-level scrubber below where each row is a
position in the book and a marker indicates the current index.
The ``bar_width`` param controls how many rows the scrubber uses.

This is mostly a "macro view" — useful for users reading long-form
text who want a sense of structure as they go.
"""

from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from .. import calculate_orp_index, split_word_for_display
from ..themes import get_theme
from .base import Figure


class MiniMapFigure(Figure):
    """Vertical scrubber + current word."""

    id = "minimap"
    name = "Mini-Map"
    description = "Vertical scrubber bar + current word."
    default_keybinding = "7"
    default_params: dict[str, Any] = {
        "bar_width": 10,
        "orp_enabled": True,
    }

    DEFAULT_CSS = """
    MiniMapFigure {
        content-align: center middle;
        text-align: center;
    }
    """

    def _on_init(self) -> None:
        self._theme = get_theme("dark")

    def render(self) -> object:  # type: ignore[override]
        current = self._current_word()
        if not self._words:
            return Panel(
                Align.center(Text("Ready", style="dim")),
                border_style=self._theme.border_idle,
            )

        if self.get_param("orp_enabled", True) and current:
            orp_idx = calculate_orp_index(current)
            parts = split_word_for_display(current, orp_idx)
            word_text = Text()
            if parts.before_orp:
                word_text.append(parts.before_orp, style=self._theme.orp_anchor)
            word_text.append(parts.orp_char, style=self._theme.orp)
            if parts.after_orp:
                word_text.append(parts.after_orp, style=self._theme.orp_anchor)
        else:
            word_text = Text(current or "(end)", style=self._theme.orp_anchor)

        bar_width = max(1, int(self.get_param("bar_width", 10)))
        n_words = len(self._words)
        rows: list[Text] = []
        for row in range(bar_width):
            idx = int((row / max(1, bar_width - 1)) * max(0, n_words - 1))
            if idx < 0:
                idx = 0
            if idx >= n_words:
                idx = n_words - 1
            if idx == self.word_index:
                bar = "█" * 6
                style = self._theme.orp
            elif idx < self.word_index:
                bar = "▓" * 6
                style = self._theme.focus_dim
            else:
                bar = "░" * 6
                style = self._theme.muted
            rows.append(Text(bar, style=style))

        body = Group(
            Align.center(word_text),
            Text(""),
            Align.center(Group(*rows)),
        )

        return Panel(
            body,
            border_style=self._theme.border_active if self.is_playing else self._theme.border_idle,
            title=self._progress_title(),
        )

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%)"
