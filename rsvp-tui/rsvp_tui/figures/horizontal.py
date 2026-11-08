"""HorizontalFigure — big-window peripheral-vision RSVP.

This is the production multi-word figure: every reading row is a
horizontal strip of words with the current word's ORP letter anchored
at the pivot column (fixed center). The focal row is surrounded by
4-6 context rows (configurable) showing the surrounding lines of the
current paragraph/section.

Layout at chunk_size=17, context_lines=5, pivot_col=43:

    ┌─── chapter · 53/67203 ────────────────────────────────┐
    │  line -4   line -3   line -2   line -1   ┃  line +1  ...  │
    │  word94 word95 word96 WOR|D word98 word99  ┃  line +1  ...  │
    │  ...                                      ┃  ...           │
    ├──── focal WOR|D centered at pivot=43  ━━━━━━━━━━━━━━━━━┤
    │  ...   line +1   line +2   line +3   ┃  line +4  ...  │
    └── ▶ 500 WPM · ░░░▓▓▓▓ ░ · ~134:18 · 0.1% ───────────┘

Key design decisions:

* **Pivot column**: every focal row's ORP lands at the same column,
  so the eye never has to re-acquire the highlight as words change.
* **Multi-word strip**: the focal row carries ``chunk_size``
  consecutive words — the focal word in the middle, the peripheral
  context on both sides. This is what makes the figure "multi-word":
  the words around the focal one are as important as the focal one.
* **Paragraph grouping**: the context rows are grouped by sentence
  boundary (`.!?`), not by a fixed character count. This makes the
  horizontal strip match natural reading flow.
* **Fade gradient**: words further from the focal position get
  progressively dimmer (``focus_dim``), creating a natural peripheral
  gradient without hard cut-offs.
* **Configurable density**: ``chunk_size`` (3-25) and
  ``context_lines`` (2-8) let the user dial in the density for
  their terminal width and reading speed.
* **Frame integration**: uses :class:`HorizontalFrame
  <rsvp_tui.figures.frame.HorizontalFrame>` for the chrome, so
  the frame is theme-coherent with every other figure.
"""
from __future__ import annotations

from typing import Any

from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from .. import calculate_orp_index, split_word_for_display
from ..themes import get_theme
from .base import Figure
from .frame import (
    DEFAULT_FRAME_WIDTH,
    FrameContext,
    FrameSpec,
    HorizontalFrame,
    ProgressInfo,
    resolve_frame_geometry,
)


class HorizontalFigure(Figure):
    """Big-window peripheral-vision reading.

    Renders N consecutive words in a horizontal strip, anchored at the
    pivot column, with M context rows above and below. The focal row
    uses ORP highlighting on the current word; peripheral words fade
    toward the edges.
    """

    id = "horizontal"
    name = "Horizontal (Multi-Word)"
    description = (
        "Wide multi-word strip, ORP fixed at pivot column, "
        "4-6 context lines, paragraph-grouped."
    )
    default_keybinding = "4"
    default_params: dict[str, Any] = {
        # Words per horizontal strip. Odd keeps the focal word
        # centered (chunk_size // 2 on each side). Seeded from the
        # global ``words_per_line`` preference when the figure is
        # mounted, unless the user customised it here.
        "chunk_size": 17,
        # Rows above + below the focal row. Each row is one
        # "logical line" (sentence or paragraph segment).
        "context_lines": 5,
        # Fade peripheral words toward the edges (vs flat dim).
        "fade_peripheral": True,
        # Bold the leading letter of every peripheral word
        # (bionic-style hint without full bionic rendering).
        "bold_hint": False,
        # ORP on the focal word.
        "orp_enabled": True,
        # Show the HorizontalFrame chrome (header/footer rules).
        "show_frame": True,
        # Width of the reading area in cells. 0 = auto (terminal width).
        "frame_width": 0,
        # Scale of the reading window (1 = full width, 5 = 60%).
        "font_size_scale": 1,
        # Context rows above/below (0 = follow ``context_lines``).
        "context_words_above": 0,
        "context_words_below": 0,
        # Box-drawing style: "heavy" | "double" | "light" | "ascii".
        "border_style": "heavy",
    }

    DEFAULT_CSS = """
    HorizontalFigure {
        content-align: center middle;
        text-align: center;
    }
    """

    def _on_init(self) -> None:
        self._theme = get_theme("dark")
        # Cache for the sentence grouping — see ``_group_into_lines``.
        self._lines_cache: tuple[tuple[str, ...], list[list[int]]] | None = None

    # ------------------------------------------------------------------ #
    # Public API (render & helpers)
    # ------------------------------------------------------------------ #

    def render(self) -> object:   # type: ignore[override]
        if not self._words:
            return Panel(
                Align.center(Text("Ready", style="dim")),
                border_style=self._theme.border_idle,
            )

        spec = self._build_spec()
        ctx = self._build_context(spec)
        frame_body = HorizontalFrame().build(ctx)

        # Panel expand=False: the frame body (FrameSpec.width wide) drives
        # the Panel width. Without this the Panel auto-expands to terminal
        # width, which would be wider than the frame body and look odd.
        return Panel(
            frame_body,
            border_style=(
                self._theme.border_active if self.is_playing
                else self._theme.border_idle
            ),
            title=self._progress_title(),
            expand=False,
        )

    # ------------------------------------------------------------------ #
    # Spec & context builders
    # ------------------------------------------------------------------ #

    def _build_spec(self) -> FrameSpec:
        """Derive the FrameSpec from figure params and terminal size."""
        p = self._params

        frame_width = int(p.get("frame_width", 0))
        if frame_width <= 0:
            # Probe the Textual app's screen width if available.
            frame_width = self._probe_terminal_width() or DEFAULT_FRAME_WIDTH

        # ``font_size_scale`` narrows the reading window (a terminal
        # can't change the glyph size) and ``min_width`` follows the
        # terminal so the frame never overflows a narrow one.
        width, min_width = resolve_frame_geometry(
            frame_width, int(p.get("font_size_scale", 1))
        )

        return FrameSpec(
            width=width,
            min_width=min_width,
            max_width=160,
            context_lines=self._context_rows(),
            border=str(p.get("border_style", "heavy")),
            # show_frame=False: the outer Panel below provides the single
            # box-drawing frame. This avoids nested double-borders.
            show_frame=False,
            show_header=True,
            show_footer=True,
            show_pivot=True,
        )

    def _context_rows(self) -> int:
        """Number of context rows rendered above/below the focal row.

        ``context_lines`` is the figure-local knob; the global
        ``context_words_above`` / ``context_words_below`` preferences
        override it when they are set (0 means "follow the figure").
        """
        rows = max(2, int(self._params.get("context_lines", 5)))
        for key in ("context_words_above", "context_words_below"):
            value = int(self._params.get(key, 0) or 0)
            if value > 0:
                rows = value
        return rows

    def effective_context_rows(self) -> tuple[int, int]:
        """(above, below) context rows currently rendered.

        The reader screen uses this to step the context window up and
        down from wherever it actually is.
        """
        rows = self._context_rows()
        return rows, rows

    def _strip_words(self) -> int:
        """Number of words in the horizontal strip.

        ``chunk_size`` is the figure-local knob (Settings → Advanced →
        figure params). It is seeded from the global ``words_per_line``
        preference when the reader mounts the figure, so both names
        describe the same thing: the width of the multi-word strip.
        """
        chunk = max(3, int(self._params.get("chunk_size", 17) or 17))
        # Odd keeps the focal word truly centred.
        if chunk % 2 == 0:
            chunk += 1
        return chunk

    def _build_context(self, spec: FrameSpec) -> FrameContext:
        """Build the FrameContext for the current word_index."""
        word_index = self.word_index

        # ---- Focal word components -----------------------------------
        focal_word = self._current_word()
        orp_idx = calculate_orp_index(focal_word)
        focal_parts = split_word_for_display(focal_word, orp_idx)

        # ---- The horizontal strip --------------------------------------
        # ``chunk_size`` consecutive words centred on the focal word:
        # the words on either side are the peripheral context.
        strip_words = self._strip_words()
        half = strip_words // 2
        start = max(0, word_index - half)
        end = min(len(self._words), word_index + half + 1)
        strip = list(self._words[start:end])
        focal_strip_index = word_index - start

        # ---- Paragraph-aware word grouping ----------------------------
        # Group all words into logical "lines" by sentence boundary.
        # Each line is a list of word indices.
        lines = self._group_into_lines()
        # Find which line the focal word belongs to.
        focal_line_idx = self._line_index_containing(word_index, lines)

        # ---- Build context rows ------------------------------------
        context_lines = self._context_rows()
        rows_above: list[str] = []
        rows_below: list[str] = []

        # Collect N lines above the focal line.
        for offset in range(1, context_lines + 1):
            line_idx = focal_line_idx - offset
            if 0 <= line_idx < len(lines):
                rows_above.insert(0, self._line_text(lines[line_idx]))

        # Collect N lines below the focal line.
        for offset in range(1, context_lines + 1):
            line_idx = focal_line_idx + offset
            if 0 <= line_idx < len(lines):
                rows_below.append(self._line_text(lines[line_idx]))

        # ---- Progress info -----------------------------------------
        total = len(self._words)
        pct = (word_index / total) * 100 if total else 0.0
        remaining_words = total - word_index
        eta_mins = int(remaining_words / max(1, self.wpm))
        eta_secs = int((remaining_words / max(1, self.wpm) - eta_mins) * 60)
        time_remaining = f"{eta_mins}:{eta_secs:02d}"

        progress = ProgressInfo(
            word_index=word_index,
            total=total,
            wpm=self.wpm,
            time_remaining=time_remaining,
            percentage=pct,
        )

        # ---- Header / footer metadata -------------------------------
        # The book title is optional — don't leave a dangling " · " when
        # the screen didn't pass one down.
        title = self._book_title()
        head = f"{title} · " if title else ""
        header_meta = f" {head}{word_index + 1}/{total} ({pct:.1f}%) "
        footer_meta = (
            f" ▶ {self.wpm} WPM · {time_remaining} left "
        )

        return FrameContext(
            theme=self._theme,
            spec=spec,
            focal_word=focal_word,
            focal_parts=focal_parts,
            context_above=rows_above,
            context_below=rows_below,
            progress=progress,
            playing=self.is_playing,
            header_meta=header_meta,
            footer_meta=footer_meta,
            focal_strip=strip,
            focal_strip_index=focal_strip_index,
            focal_strip_fade=bool(self._params.get("fade_peripheral", True)),
            focal_strip_bold_hint=bool(self._params.get("bold_hint", False)),
        )

    # ------------------------------------------------------------------ #
    # Line grouping helpers
    # ------------------------------------------------------------------ #

    def _group_into_lines(self) -> list[list[int]]:
        """Split the word list into logical lines by sentence boundary.

        A new line starts after any sentence terminator (.!?) or after
        ~12 words (whichever comes first). This gives natural line
        breaks for the horizontal context rows without requiring a
        fixed character-width pass.

        The grouping is O(len(words)) and used to run on EVERY render —
        at 500 WPM that is ~8 times per second over the whole book,
        growing linearly with the book size. We cache the result and
        recompute it only when the word list itself changes.
        """
        if not self._words:
            return []
        cached = self._lines_cache
        if cached is not None and cached[0] is self._words:
            return cached[1]
        lines = self._compute_lines()
        self._lines_cache = (self._words, lines)
        return lines

    def _compute_lines(self) -> list[list[int]]:
        """Do the actual sentence-boundary grouping (see ``_group_into_lines``)."""
        # max words per line before forcing a break (sentence boundary wins)
        _MAX_WORDS_PER_LINE = 12  # noqa: N806
        lines: list[list[int]] = []
        current: list[int] = []
        sentence_ends = {".", "!", "?"}

        for idx, word in enumerate(self._words):
            current.append(idx)
            ends_sentence = (
                word[-1:] in sentence_ends
                if word
                else False
            )
            if ends_sentence or len(current) >= _MAX_WORDS_PER_LINE:
                lines.append(current)
                current = []

        if current:
            lines.append(current)
        return lines

    def _line_text(self, line: list[int]) -> str:
        """Render one grouped line as the text of a context row."""
        return " ".join(self._words[i] for i in line)

    @staticmethod
    def _line_index_containing(word_index: int, lines: list[list[int]]) -> int:
        """Return the index into ``lines`` that contains ``word_index``."""
        for li, line in enumerate(lines):
            if word_index in line:
                return li
        # Fallback: put it at the nearest line.
        if not lines:
            return 0
        if word_index < lines[0][0]:
            return 0
        return len(lines) - 1

    # ------------------------------------------------------------------ #
    # Utilities
    # ------------------------------------------------------------------ #

    def _book_title(self) -> str:
        # The figure doesn't directly know the book title; expose
        # whatever the owning screen passes down via params.
        title = str(self._params.get("book_title", ""))
        if title:
            return title[:40]   # truncate long titles for the header
        return ""

    def _progress_title(self) -> str:
        if not self._words:
            return ""
        pct = (self.word_index / len(self._words)) * 100
        chunk_size = self._strip_words()
        return (
            f"{self.word_index + 1}/{len(self._words)} "
            f"({pct:.1f}%)  [{chunk_size}w]"
        )
