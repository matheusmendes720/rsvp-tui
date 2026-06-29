"""PacerFigure — word + pacer dots representing position in the book.

The pacer dots form a single horizontal row of N cells; each cell
fills in (or brightens) as the reader advances. The number of dots
is set by ``dot_count`` (default 20). This is a "where am I in the
book at a glance" view — useful for long sessions where the reader
loses track of overall progress.
"""

from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from ..themes import get_theme
from .base import Figure


class PacerFigure(Figure):
    """Word display with a pacer-dot progress row beneath."""

    id = "pacer"
    name = "Pacer"
    description = "Word + horizontal pacer dots showing progress."
    default_keybinding = "6"
    default_params: dict[str, Any] = {
        "dot_count": 20,
        "fill_char": "●",
        "empty_char": "○",
    }

    DEFAULT_CSS = """
    PacerFigure {
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

        word_text = Text(
            current or "(end)",
            style=self._theme.orp_anchor if current else self._theme.muted,
        )

        dot_count = max(1, int(self.get_param("dot_count", 20)))
        fill_char = str(self.get_param("fill_char", "●"))
        empty_char = str(self.get_param("empty_char", "○"))
        ratio = 0.0
        if self._words:
            ratio = self.word_index / max(1, len(self._words) - 1)
        filled = int(round(ratio * (dot_count - 1)))
        dots: list[Text] = []
        for i in range(dot_count):
            char = fill_char if i <= filled else empty_char
            style = self._theme.orp if i <= filled else self._theme.muted
            dots.append(Text(char + " ", style=style))
        row = Text()
        for d in dots:
            row.append_text(d)

        display = Group(Align.center(word_text), Text(""), Align.center(row))
        return Panel(
            display,
            border_style=self._theme.border_active if self.is_playing else self._theme.border_idle,
            title=self._progress_title(),
        )

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%)"
