"""WordFigure — the classic single-word RSVP display with ORP.

This is the canonical "1 word at a time, Optimal Recognition Point
highlighted" view. It is the refactor of the legacy ``ReaderDisplay``
into the new ``Figure`` hierarchy — the old widget's boolean flags
(``enable_orp``, ``focus_mode``) are now per-figure parameters
(``orp_enabled``, ``show_context``) that live on the figure and can
be edited at runtime via the SettingsScreen.

Why this is a refactor and not a copy: the original ``ReaderDisplay``
duplicated state, transport, and timer logic. By inheriting from
``Figure`` we get all of that for free, which leaves ``WordFigure``
with only the rendering concern — drawing a centered word with ORP
highlight plus dimmed context words.
"""

from __future__ import annotations

from typing import Any, Dict

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from .. import calculate_orp_index, split_word_for_display
from ..themes import get_theme
from .base import Figure, FigureState


class WordFigure(Figure):
    """Single-word RSVP display with ORP highlighting."""

    id = "word"
    name = "Single Word (ORP)"
    description = "One word at a time, ORP letter highlighted."
    default_keybinding = "1"
    default_params: Dict[str, Any] = {
        "orp_enabled": True,
        "show_context": True,
        "context_window": 1,
    }

    DEFAULT_CSS = """
    WordFigure {
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

        if self.get_param("orp_enabled", True):
            orp_idx = calculate_orp_index(current)
            parts = split_word_for_display(current, orp_idx)
            word_display = self._format_with_orp(parts)
        else:
            word_display = Text(current, style=f"bold {self._theme.orp_anchor}")

        if self.get_param("show_context", True) and len(self._words) > 1:
            display = self._add_context_words(word_display)
        else:
            display = Align.center(word_display)

        return Panel(
            display,
            border_style=self._theme.border_active if self.is_playing else self._theme.border_idle,
            title=self._progress_title(),
        )

    def _format_with_orp(self, parts: Any) -> Text:
        result = Text()
        if parts.before_orp:
            result.append(parts.before_orp, style=self._theme.orp_anchor)
        result.append(parts.orp_char, style=self._theme.orp)
        if parts.after_orp:
            result.append(parts.after_orp, style=self._theme.orp_anchor)
        return result

    def _add_context_words(self, current_display: Text) -> Group:
        window = max(0, int(self.get_param("context_window", 1)))
        lines = []
        for offset in range(window, 0, -1):
            idx = self.word_index - offset
            if 0 <= idx < len(self._words):
                lines.append(Align.center(Text(self._words[idx], style=self._theme.focus_dim)))
        lines.append(Align.center(current_display))
        for offset in range(1, window + 1):
            idx = self.word_index + offset
            if 0 <= idx < len(self._words):
                lines.append(Align.center(Text(self._words[idx], style=self._theme.focus_dim)))
        return Group(*lines)

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%)"
