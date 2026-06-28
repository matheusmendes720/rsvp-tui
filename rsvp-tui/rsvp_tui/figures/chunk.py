"""ChunkFigure — show a small window of N consecutive words.

Where ``WordFigure`` shows a single word, ``ChunkFigure`` shows the
current word and the next 2 (by default) so the reader can use
context to disambiguate. The ORP is applied to the first word in the
chunk; the trailing words are dimmed. ``chunk_size`` is editable at
runtime via the per-figure params editor.
"""

from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from .. import calculate_orp_index, split_word_for_display
from ..themes import get_theme
from .base import Figure


class ChunkFigure(Figure):
    """Multi-word chunk display with ORP on the first word."""

    id = "chunk"
    name = "Word Chunk"
    description = "Show a window of N words, ORP on the first."
    default_keybinding = "2"
    default_params: dict[str, Any] = {
        "chunk_size": 3,
        "orp_enabled": True,
    }

    DEFAULT_CSS = """
    ChunkFigure {
        content-align: center middle;
        text-align: center;
    }
    """

    def _on_init(self) -> None:
        self._theme = get_theme("dark")

    def render(self):  # type: ignore[override]
        if not self._words:
            return Panel(
                Align.center(Text("Ready", style="dim")),
                border_style=self._theme.border_idle,
            )

        chunk_size = max(1, int(self.get_param("chunk_size", 3)))
        chunk = self._words[self.word_index : self.word_index + chunk_size]
        if not chunk:
            return Panel(
                Align.center(Text("(end)", style="dim")),
                border_style=self._theme.border_idle,
            )

        pieces: list[Text] = []
        for i, word in enumerate(chunk):
            text = Text()
            text.append(" " if i > 0 else "")
            if i == 0 and self.get_param("orp_enabled", True):
                orp_idx = calculate_orp_index(word)
                parts = split_word_for_display(word, orp_idx)
                if parts.before_orp:
                    text.append(parts.before_orp, style=self._theme.orp_anchor)
                text.append(parts.orp_char, style=self._theme.orp)
                if parts.after_orp:
                    text.append(parts.after_orp, style=self._theme.orp_anchor)
            else:
                text.append(word, style=self._theme.focus_dim)
            pieces.append(text)

        combined = Text()
        for p in pieces:
            combined.append_text(p)

        return Panel(
            Align.center(combined),
            border_style=self._theme.border_active if self.is_playing else self._theme.border_idle,
            title=self._progress_title(),
        )

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%)"
