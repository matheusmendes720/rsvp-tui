"""StatsFigure — word + WPM sparkline + ETA overlay.

Adds a 60-sample WPM history sparkline above the current word, and
shows ETA and words-remaining below. The WPM is sampled whenever
the figure advances a word. This makes the figure useful both for
real-time feedback ("am I reading consistently?") and as a
diagnostic while tuning the per-figure params.
"""

from __future__ import annotations

from collections import deque
from typing import Any

from rich.align import Align
from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from ..themes import get_theme
from .base import Figure


class StatsFigure(Figure):
    """Word + WPM history sparkline + ETA / words-remaining stats."""

    id = "stats"
    name = "Stats Overlay"
    description = "Word + WPM sparkline + ETA and words-remaining."
    default_keybinding = "8"
    default_params: dict[str, Any] = {
        "history_size": 60,
        "show_eta": True,
    }

    BARS = " ▁▂▃▄▅▆▇█"

    DEFAULT_CSS = """
    StatsFigure {
        content-align: center middle;
        text-align: center;
    }
    """

    def _on_init(self) -> None:
        self._theme = get_theme("dark")
        self._wpm_history: deque[int] = deque(maxlen=int(self.get_param("history_size", 60)))

    def render(self):  # type: ignore[override]
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

        spark = self._build_sparkline()
        eta = self._build_eta()

        body = Group(
            Align.center(spark),
            Text(""),
            Align.center(word_text),
            Text(""),
            Align.center(eta),
        )
        return Panel(
            body,
            border_style=self._theme.border_active if self.is_playing else self._theme.border_idle,
            title=self._progress_title(),
        )

    def watch_word_index(self, index: int) -> None:  # type: ignore[override]
        # Sample WPM on each advance. The base class's observer will
        # also fire (via super().watch_word_index) and emit
        # on_word_change / on_complete — that's intentional.
        if self.wpm > 0:
            self._wpm_history.append(int(self.wpm))
        super().watch_word_index(index)

    def _build_sparkline(self) -> Text:
        if not self._wpm_history:
            return Text(" " * 20, style=self._theme.muted)
        max_w = max(self._wpm_history)
        min_w = min(self._wpm_history)
        rng = max(1, max_w - min_w)
        text = Text()
        for w in self._wpm_history:
            level = int(((w - min_w) / rng) * (len(self.BARS) - 1))
            text.append(self.BARS[level], style=self._theme.primary)
        return text

    def _build_eta(self) -> Text:
        remaining = max(0, len(self._words) - self.word_index)
        eta_minutes = 0.0 if self.wpm <= 0 else remaining / max(1, self.wpm)
        eta_text = Text()
        eta_text.append(f"ETA: {eta_minutes:0.1f} min  ", style=self._theme.muted)
        eta_text.append(f"Remaining: {remaining} words  ", style=self._theme.muted)
        eta_text.append(f"WPM: {self.wpm}", style=self._theme.orp)
        return eta_text

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%)"
