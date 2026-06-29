"""BionicFigure — bold the first ~40% of each word (Bionic Reading style).

Bionic Reading is a recognized reading-aid technique: by bolding the
beginning of each word, the eye can latch onto the word's shape
faster. The exact "split point" varies — we use ``bold_ratio``
(default 0.4) and round up so a 5-letter word bolds its first 2
letters.

This figure does not use ORP — bolding and ORP are visually similar
but emphasize different things (letter shape vs. recognition pivot).
We keep them separate so users can pick one or the other.
"""

from __future__ import annotations

import math
from typing import Any

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from ..themes import get_theme
from .base import Figure


class BionicFigure(Figure):
    """Bionic-style display: bold the leading portion of each word."""

    id = "bionic"
    name = "Bionic"
    description = "Bold the first portion of each word (Bionic style)."
    default_keybinding = "4"
    default_params: dict[str, Any] = {
        "bold_ratio": 0.4,
        "show_context": True,
        "context_window": 1,
    }

    DEFAULT_CSS = """
    BionicFigure {
        content-align: center middle;
        text-align: center;
    }
    """

    def _on_init(self) -> None:
        self._theme = get_theme("dark")

    def render(self) -> object:  # type: ignore[override]
        current = self._current_word()
        if not current:
            return Panel(
                Align.center(Text("Ready", style="dim")),
                border_style=self._theme.border_idle,
            )

        bold_word = self._bionicize(current, ratio=float(self.get_param("bold_ratio", 0.4)))

        if self.get_param("show_context", True) and len(self._words) > 1:
            window = max(0, int(self.get_param("context_window", 1)))
            lines = []
            for offset in range(window, 0, -1):
                idx = self.word_index - offset
                if 0 <= idx < len(self._words):
                    lines.append(
                        Align.center(
                            self._bionicize(
                                self._words[idx],
                                ratio=float(self.get_param("bold_ratio", 0.4)),
                                dim=True,
                            )
                        )
                    )
            lines.append(Align.center(bold_word))
            for offset in range(1, window + 1):
                idx = self.word_index + offset
                if 0 <= idx < len(self._words):
                    lines.append(
                        Align.center(
                            self._bionicize(
                                self._words[idx],
                                ratio=float(self.get_param("bold_ratio", 0.4)),
                                dim=True,
                            )
                        )
                    )
            display: Any = Group(*lines)
        else:
            display = Align.center(bold_word)

        return Panel(
            display,
            border_style=self._theme.border_active if self.is_playing else self._theme.border_idle,
            title=self._progress_title(),
        )

    def _bionicize(self, word: str, ratio: float, dim: bool = False) -> Text:
        """Bold the first ``math.ceil(len * ratio)`` characters of ``word``."""
        n = len(word)
        if n == 0:
            return Text(word, style=self._theme.orp_anchor)
        cut = max(1, math.ceil(n * ratio))
        text = Text()
        head_style = f"bold {self._theme.orp_anchor if not dim else self._theme.focus_dim}"
        text.append(word[:cut], style=head_style)
        if cut < n:
            tail_style = self._theme.focus_dim if dim else self._theme.orp_anchor
            text.append(word[cut:], style=tail_style)
        return text

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%)"
