"""LineFigure — show the full sentence/line with the current word highlighted.

Where ``WordFigure`` and ``ChunkFigure`` reduce the visual to a small
window, ``LineFigure`` keeps the whole sentence on screen and just
highlights (in red) the word that matches the current index. The
``context_words`` param controls how many words on each side of the
current are shown.

This figure is useful for users who rely on sentence structure to
parse meaning — e.g. people learning a new language, or readers of
dense academic prose.
"""

from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from ..themes import get_theme
from .base import Figure


class LineFigure(Figure):
    """Full-line display with the current word highlighted."""

    id = "line"
    name = "Full Line"
    description = "Render a sentence slice; current word highlighted."
    default_keybinding = "3"
    default_params: dict[str, Any] = {
        "wrap": True,
        "context_words": 5,
    }

    DEFAULT_CSS = """
    LineFigure {
        content-align: center middle;
        text-align: center;
    }
    """

    def _on_init(self) -> None:
        self._theme = get_theme("dark")

    def render(self) -> object:  # type: ignore[override]
        if not self._words:
            return Panel(
                Align.center(Text("Ready", style="dim")),
                border_style=self._theme.border_idle,
            )

        window = max(1, int(self.get_param("context_words", 5)))
        start = max(0, self.word_index - window)
        end = min(len(self._words), self.word_index + window + 1)

        # Walk back to the previous sentence terminator.
        scan = self.word_index - 1
        while scan > start and self._words[scan][-1:] not in ".!?":
            scan -= 1
        if scan > start and self._words[scan][-1:] in ".!?":
            start = scan + 1

        # Walk forward to the next sentence terminator.
        scan = self.word_index + 1
        while scan < end and self._words[scan - 1][-1:] not in ".!?":
            scan += 1
        if scan < end and self._words[scan - 1][-1:] in ".!?":
            end = scan

        line_words = self._words[start:end]
        text = Text()
        for i, word in enumerate(line_words):
            actual_index = start + i
            if i > 0:
                text.append(" ")
            if actual_index == self.word_index:
                text.append(word, style=self._theme.orp)
            else:
                text.append(word, style=self._theme.orp_anchor)

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
