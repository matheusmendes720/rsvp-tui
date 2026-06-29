"""HorizontalFigure — multi-word horizontal speed reading with peripheral vision.

This figure displays a horizontal line of words with:
- Current word highlighted in the center (ORP)
- Peripheral words visible on left/right with fade effect
- WPM-controlled scrolling to next chunk
- Bionic-style optional highlighting on first letter of each word

This bridges the gap between RSVP (single-word flash) and natural reading,
giving users the benefits of context from multiple words while maintaining
the eye-anchoring highlight that makes speed reading effective.
"""

from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.console import ConsoleRenderable
from rich.panel import Panel
from rich.style import Style
from rich.text import Text

from .. import calculate_orp_index, split_word_for_display
from ..themes import get_theme
from .base import Figure


class HorizontalFigure(Figure):
    """Multi-word horizontal display with center highlight and peripheral fade."""

    id = "horizontal"
    name = "Horizontal (Multi-Word)"
    description = "Horizontal line with center highlight and peripheral vision."
    default_keybinding = "4"
    default_params: dict[str, Any] = {
        "chunk_size": 7,  # Words to show (odd number keeps center word centered)
        "orp_enabled": True,  # Use ORP highlighting
        "bionic_enabled": False,  # Bold first letters of all words
        "fade_peripheral": True,  # Fade peripheral words
        "center_anchor": True,  # Keep current word at center
    }

    DEFAULT_CSS = """
    HorizontalFigure {
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

        chunk_size = max(1, int(self.get_param("chunk_size", 7)))
        # Ensure odd number for centered display
        if chunk_size % 2 == 0:
            chunk_size += 1
        half = chunk_size // 2

        # Calculate the window range
        start = max(0, self.word_index - half)
        end = min(len(self._words), self.word_index + half + 1)

        # Adjust if we're at the edges
        if self.word_index - half < 0:
            end = min(len(self._words), chunk_size)
            start = 0
        elif self.word_index + half + 1 > len(self._words):
            start = max(0, len(self._words) - chunk_size)
            end = len(self._words)

        # Build the horizontal line
        text = Text()
        bionic = self.get_param("bionic_enabled", False)
        fade_peripheral = self.get_param("fade_peripheral", True)
        center_anchor = self.get_param("center_anchor", True)

        for idx in range(start, end):
            word = self._words[idx]
            is_current = idx == self.word_index
            is_peripheral = abs(idx - self.word_index) > 0

            if is_current:
                # Current word - apply ORP highlighting
                if self.get_param("orp_enabled", True):
                    orp_idx = calculate_orp_index(word)
                    parts = split_word_for_display(word, orp_idx)
                    if parts.before_orp:
                        text.append(parts.before_orp, style=self._theme.orp_anchor)
                    text.append(parts.orp_char, style=f"{self._theme.orp} bold")
                    if parts.after_orp:
                        text.append(parts.after_orp, style=self._theme.orp_anchor)
                else:
                    text.append(word, style=f"bold {self._theme.orp}")
            elif bionic:
                # Bionic style: bold first letter of each peripheral word
                if word:
                    text.append(word[0], style=f"bold {self._theme.orp_anchor}")
                    text.append(word[1:], style=self._theme.orp_anchor)
                else:
                    text.append(word, style=self._theme.orp_anchor)
            elif fade_peripheral and is_peripheral:
                # Peripheral with fade effect
                fade_style = self._get_fade_style(idx, self.word_index, start, end)
                text.append(word, style=fade_style)
            else:
                # Normal peripheral word
                text.append(word, style=self._theme.orp_anchor)

            # Add space between words
            if idx < end - 1:
                text.append(" ")

        # Wrap with peripheral fade effect on edges
        if fade_peripheral:
            display = self._wrap_with_fade(text, start, end)
        else:
            display = Align.center(text)

        return Panel(
            display,
            border_style=self._theme.border_active if self.is_playing else self._theme.border_idle,
            title=self._progress_title(),
        )

    def _get_fade_style(self, word_idx: int, center_idx: int, start: int, end: int) -> str:
        """Calculate fade intensity based on distance from center."""
        distance = abs(word_idx - center_idx)
        max_distance = max(1, (end - start) // 2)

        # Calculate opacity (1.0 = full, 0.3 = faded)
        opacity = 1.0 - (distance / max_distance) * 0.5
        opacity = max(0.3, min(1.0, opacity))

        # Return style with dim for faded words
        if opacity < 0.8:
            return f"dim {self._theme.orp_anchor}"
        return self._theme.orp_anchor

    def _wrap_with_fade(self, text: Text, start: int, end: int) -> ConsoleRenderable:
        """Add subtle visual fade effect to edges of the display."""
        # The fade is handled per-word in render(), so just center
        return Align.center(text)

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        chunk_size = self.get_param("chunk_size", 7)
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%) [{chunk_size}w]"