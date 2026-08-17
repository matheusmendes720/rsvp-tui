"""WordFigure — the classic single-word RSVP display with ORP.

This is the canonical "1 word at a time, Optimal Recognition Point
highlighted" view. It is the refactor of the legacy ``ReaderDisplay``
into the new ``Figure`` hierarchy — the old widget's boolean flags
(``enable_orp``, ``focus_mode``) are now per-figure parameters
(``orp_enabled``, ``show_context``) that live on the figure and can
be edited at runtime via the SettingsScreen.

Optionally wraps the display in a :class:`HorizontalFrame
<rsvp_tui.figures.frame.HorizontalFrame>` when ``frame_style`` is
set to ``wide`` or ``expanded``. The default ``minimal`` preserves
the original single-panel aesthetic for users who prefer it.
"""
from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.console import ConsoleRenderable, Group
from rich.panel import Panel
from rich.text import Text

from .. import calculate_orp_index, split_word_for_display
from ..themes import get_theme
from .base import Figure
from .frame import (
    FrameContext,
    FrameSpec,
    HorizontalFrame,
    ProgressInfo,
)


class WordFigure(Figure):
    """Single-word RSVP display with ORP highlighting.

    Supports three frame styles via the ``frame_style`` parameter:

    * ``"minimal"`` — the original single-Panel aesthetic (default,
      backward-compatible).
    * ``"wide"`` — wraps the word in a HorizontalFrame with 1 row of
      context above and below the focal word. Good for users who want
      the frame chrome without a full multi-word strip.
    * ``"expanded"`` — HorizontalFrame with 3 rows of context on each
      side, matching the peripheral-vision density of HorizontalFigure.
      The focal word stays centered with the same ORP highlight.
    """

    id = "word"
    name = "Single Word (ORP)"
    description = "One word at a time, ORP letter highlighted."
    default_keybinding = "1"
    default_params: dict[str, Any] = {
        "orp_enabled": True,
        "show_context": True,
        "context_window": 3,
        # Frame style: "minimal" | "wide" | "expanded"
        # Default to "wide" so newcomers immediately see 1 context row
        # above + below the focal word without having to enable the
        # frame in settings.
        "frame_style": "wide",
        "frame_width": 0,        # 0 = auto (terminal width)
        "border_style": "heavy",
    }

    DEFAULT_CSS = """
    WordFigure {
        content-align: center middle;
        text-align: center;
    }
    """

    def _on_init(self) -> None:
        self._theme = get_theme("dark")

    # ------------------------------------------------------------------ #
    # Focus-mode property (backward-compatible API)
    # ------------------------------------------------------------------ #

    @property
    def focus_mode(self) -> bool:
        """Return current focus mode state (show context words)."""
        return bool(self._params.get("show_context", True))

    @focus_mode.setter
    def focus_mode(self, value: bool) -> None:
        """Set focus mode (controls show_context parameter)."""
        self._params["show_context"] = bool(value)
        self.refresh()

    def toggle_focus(self) -> None:
        """Toggle focus mode (hide/show context words)."""
        self._params["show_context"] = not self._params.get("show_context", True)
        self.refresh()

    # ------------------------------------------------------------------ #
    # Render
    # ------------------------------------------------------------------ #

    def render(self) -> object:   # type: ignore[override]
        current = self._current_word()
        if not current:
            return Panel(
                Align.center(Text("Ready", style="dim")),
                border_style=self._theme.border_idle,
            )

        frame_style = self._params.get("frame_style", "minimal")
        if frame_style != "minimal":
            return self._render_framed(current, frame_style)

        # ---- Minimal (original single-Panel path) -----------------------
        if self.get_param("orp_enabled", True):
            orp_idx = calculate_orp_index(current)
            parts = split_word_for_display(current, orp_idx)
            word_display = self._format_with_orp(parts)
        else:
            word_display = Text(current, style=f"bold {self._theme.orp_anchor}")

        display: ConsoleRenderable
        if self.get_param("show_context", True) and len(self._words) > 1:
            display = self._add_context_words(word_display)
        else:
            display = Align.center(word_display)

        return Panel(
            display,
            border_style=(
                self._theme.border_active if self.is_playing
                else self._theme.border_idle
            ),
            title=self._progress_title(),
        )

    # ------------------------------------------------------------------ #
    # Framed rendering (wide / expanded)
    # ------------------------------------------------------------------ #

    def _render_framed(self, current: str, frame_style: str) -> object:
        """Render with a HorizontalFrame around the focal word."""
        orp_idx = calculate_orp_index(current)
        parts = split_word_for_display(current, orp_idx)

        context_lines = 1 if frame_style == "wide" else 3
        frame_width = int(self._params.get("frame_width", 0)) or 100

        spec = FrameSpec(
            width=frame_width,
            min_width=60,
            max_width=160,
            context_lines=context_lines,
            border=str(self._params.get("border_style", "heavy")),
            # show_frame=False: the outer Panel below is the single frame.
            show_frame=False,
            show_header=True,
            show_footer=True,
            show_pivot=True,
        )

        # Context: surrounding words (1 row above + 1 below in "wide" mode)
        context_above, context_below = self._get_context_words(
            window=1 if frame_style == "wide" else 2
        )

        total = len(self._words)
        remaining = total - self.word_index
        eta_mins = int(remaining / max(1, self.wpm))
        eta_secs = int((remaining / max(1, self.wpm) - eta_mins) * 60)
        pct = (self.word_index / total) * 100 if total else 0.0
        progress = ProgressInfo(
            word_index=self.word_index,
            total=total,
            wpm=self.wpm,
            time_remaining=f"{eta_mins}:{eta_secs:02d}",
            percentage=pct,
        )

        header_meta = f" {self.word_index + 1}/{total} ({pct:.1f}%) "
        footer_meta = f" ▶ {self.wpm} WPM · ~{eta_mins}:{eta_secs:02d}"

        ctx = FrameContext(
            theme=self._theme,
            spec=spec,
            focal_word=current,
            focal_parts=parts,
            context_above=context_above,
            context_below=context_below,
            progress=progress,
            playing=self.is_playing,
            header_meta=header_meta,
            footer_meta=footer_meta,
        )

        frame_body = HorizontalFrame().build(ctx)

        return Panel(
            frame_body,
            border_style=(
                self._theme.border_active if self.is_playing
                else self._theme.border_idle
            ),
            title=self._progress_title(),
            expand=False,
        )

    def _get_context_words(
        self, window: int = 1
    ) -> tuple[list[str], list[str]]:
        """Return up to ``window`` words before and after the focal word."""
        above: list[str] = []
        below: list[str] = []
        for offset in range(1, window + 1):
            idx_before = self.word_index - offset
            if 0 <= idx_before < len(self._words):
                above.insert(0, self._words[idx_before])
            else:
                above.insert(0, "")
            idx_after = self.word_index + offset
            if 0 <= idx_after < len(self._words):
                below.append(self._words[idx_after])
            else:
                below.append("")
        return above, below

    # ------------------------------------------------------------------ #
    # ORP formatting
    # ------------------------------------------------------------------ #

    def _format_with_orp(self, parts: Any) -> Text:
        result = Text()
        if parts.before_orp:
            result.append(parts.before_orp, style=self._theme.orp_anchor)
        result.append(parts.orp_char, style=self._theme.orp)
        if parts.after_orp:
            result.append(parts.after_orp, style=self._theme.orp_anchor)
        return result

    def _add_context_words(self, current_display: Text) -> ConsoleRenderable:
        window = max(0, int(self.get_param("context_window", 1)))
        lines = []
        for offset in range(window, 0, -1):
            idx = self.word_index - offset
            if 0 <= idx < len(self._words):
                lines.append(
                    Align.center(Text(self._words[idx], style=self._theme.focus_dim))
                )
        lines.append(Align.center(current_display))
        for offset in range(1, window + 1):
            idx = self.word_index + offset
            if 0 <= idx < len(self._words):
                lines.append(
                    Align.center(Text(self._words[idx], style=self._theme.focus_dim))
                )
        return Group(*lines)

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        return f"{self.word_index + 1}/{len(self._words)} ({pct:.1f}%)"
