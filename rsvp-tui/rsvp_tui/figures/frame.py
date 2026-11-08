"""HorizontalFrame — the production reading-window frame for RSVP figures.

WHY THIS EXISTS
---------------
A speed-reading TUI needs a *frame*, not a loose dim Panel. The frame
is what makes "this is a reading surface" obvious at a glance:

    ┌── chapter · p.42 ──────────── 53/67,203 ─ 03:21 left ──────┐
    │   context -3  context -2  context -1  ┃ context +1  ...     │
    │                              Recarg│arregar                 │
    │   context -3  context -2  context -1  ┃ context +1  ...     │
    ├──────────────────────────────────────────────────────────────┤
    │   ▶ 500 WPM  · ░░░░▓▓▓▓▓▓▓▓▓▓▓▓  · 0.1%  ·  ⏱ 03:21 left    │
    └──────────────────────────────────────────────────────────────┘

The vertical bar `│` between ``context -1`` and ``Recarg|arregar`` is
the **PIVOT COLUMN**. Every focal word is anchored so its ORP
character lands at exactly this column. As the reader progresses,
the word slides horizontally but the eye never moves. That is the
entire trick of Spritz-style reading made production-grade.

DESIGN PILLARS
--------------
1. **Bigger window, more peripheral content.** ``context_lines``
   controls how many rows above + below the focal line appear. The
   frame stretches to the terminal width (clamped between
   ``min_width`` and ``max_width``) so a 160-col terminal gets a
   160-col reading area, not a 60-col pill in the middle of the
   screen.
2. **Same highlight, fixed center.** ORP highlighting is unchanged
   (see ``WordFigure._format_with_orp``); only the *position* of
   the highlighted letter is now fixed at the pivot column.
3. **Theme tokens, not strings.** ``frame_rule``, ``frame_pivot``,
   ``frame_corner``, ``frame_focus``, ``frame_rule_heavy`` are
   first-class theme tokens. Switching the palette in
   ``themes.THEMES`` re-paints the frame with no code change.
4. **Four box-drawing styles.** ``heavy`` (━ ┃ ┏ ┓), ``double``
   (═ ║ ╔ ╗), ``light`` (─ │ ┌ ┐), ``ascii`` (- | +). The frame
   auto-picks the closest available style based on
   ``os.environ.get('TERM')`` and explicit override, so terminals
   without Unicode still render correctly.
5. **Pure-Renderable.** ``HorizontalFrame`` builds standard
   ``rich.text.Text`` / ``rich.console.Group`` objects. No
   terminal escape sequences, no Textual-specific calls — easy
   to unit-test, easy to reuse as the body of any figure's
   ``render()``.

API
---
>>> spec = FrameSpec(width=120, context_lines=4, border="heavy")
>>> ctx = FrameContext(
...     theme=get_theme("dark"),
...     spec=spec,
...     focal_word="Recarregar",
...     focal_parts=split_word_for_display("Recarregar", 3),
...     context_above=("alpha", "beta", "gamma"),
...     context_below=("delta", "epsilon"),
...     progress=ProgressInfo(word_index=53, total=67203, wpm=500,
...                          time_remaining="134:18"),
...     show_pivot=True,
...     playing=True,
... )
>>> renderable = HorizontalFrame().build(ctx)
>>> # renderable is a rich.console.Group; pass it to Panel or Static.
"""
from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from rich.cells import get_character_cell_size
from rich.console import ConsoleRenderable, Group
from rich.text import Text

from ..themes import Theme

# --------------------------------------------------------------------------- #
# Box-drawing character sets
# --------------------------------------------------------------------------- #


class BorderStyle(str, Enum):
    """Box-drawing character family for the frame.

    The string values are stored in ``FrameSpec.border`` so the JSON
    config can carry them verbatim — keep them stable.
    """

    HEAVY = "heavy"     # ━ ┃ ┏ ┓ ┗ ┛ ┳ ┫
    DOUBLE = "double"   # ═ ║ ╔ ╗ ╚ ╝ ╤ ╡
    LIGHT = "light"     # ─ │ ┌ ┐ └ ┘ ┬ ┤
    ASCII = "ascii"     # - | + (no cross, no L-segments)


@dataclass(frozen=True)
class _BoxChars:
    """The full set of box-drawing glyphs used by the frame."""

    horizontal: str          # rule char, e.g. "━"
    vertical: str            # pivot column char, e.g. "┃"
    top_left: str            # corner top-left
    top_right: str           # corner top-right
    bottom_left: str
    bottom_right: str
    tee_down: str            # ┳ / ╤ / ┬  (top rule joins pivot)
    tee_up: str              # ┻ / ╧ / ┴  (bottom rule joins pivot)
    tee_right: str           # ┣ / ╞ / ├  (left of pivot on inner rule)
    tee_left: str            # ┫ / ╡ / ┤  (right of pivot on inner rule)


# The border style used when the configured one is unknown. "light" is
# the most portable of the four (every terminal has ─ │ ┌ ┐).
DEFAULT_BORDER = BorderStyle.LIGHT.value

# Narrowest reading window we render. Below this the pivot column and
# the ORP highlight stop making sense.
MIN_FRAME_WIDTH = 20

# Width used when the terminal size can't be probed (figure rendered
# outside a running Textual app — e.g. in a unit test).
DEFAULT_FRAME_WIDTH = 100


_BOX_SETS: dict[str, _BoxChars] = {
    BorderStyle.HEAVY.value: _BoxChars(
        horizontal="━",
        vertical="┃",
        top_left="┏",
        top_right="┓",
        bottom_left="┗",
        bottom_right="┛",
        tee_down="┳",
        tee_up="┻",
        tee_right="┣",
        tee_left="┫",
    ),
    BorderStyle.DOUBLE.value: _BoxChars(
        horizontal="═",
        vertical="║",
        top_left="╔",
        top_right="╗",
        bottom_left="╚",
        bottom_right="╝",
        tee_down="╤",
        tee_up="╧",
        tee_right="╞",
        tee_left="╡",
    ),
    BorderStyle.LIGHT.value: _BoxChars(
        horizontal="─",
        vertical="│",
        top_left="┌",
        top_right="┐",
        bottom_left="└",
        bottom_right="┘",
        tee_down="┬",
        tee_up="┴",
        tee_right="├",
        tee_left="┤",
    ),
    BorderStyle.ASCII.value: _BoxChars(
        horizontal="-",
        vertical="|",
        top_left="+",
        top_right="+",
        bottom_left="+",
        bottom_right="+",
        # ascii has no T-segments; fall back to "+" which still parses
        # visually as a cross even though the rule itself is uniform
        # "-". Acceptable degradation; better than Unicode garbage on
        # a vt100.
        tee_down="+",
        tee_up="+",
        tee_right="+",
        tee_left="+",
    ),
}


def _detect_border_style() -> str:
    """Pick a sensible default box-drawing family for the current terminal.

    Order of preference: explicit env override > known good terminals >
    safe light > ASCII. Used only as the default for ``FrameSpec``;
    figures may override per-instance.

    The detection is heuristic — there are too many terminals and
    version skew to be exact. We always fall back to ASCII if a
    flag is set (``NO_UNICODE_BORDERS=1``).
    """
    if os.environ.get("RSVP_FRAME_ASCII") or os.environ.get("NO_UNICODE_BORDERS"):
        return BorderStyle.ASCII.value

    term = (os.environ.get("TERM") or "").lower()
    lang = (os.environ.get("LANG") or "").lower()

    # Windows native console without utf-8 — go ASCII.
    if os.name == "nt" and not lang.endswith(("utf-8", "utf8")):
        try:
            # If Python's stdout codec is mbcs/cp***, ASCII is safer.
            import sys

            encoding = (sys.stdout.encoding or "").lower()
            if encoding and "utf" not in encoding:
                return BorderStyle.ASCII.value
        except Exception:
            return BorderStyle.ASCII.value

    # xterm, alacritty, kitty, iterm, wezterm, gnome, konsole all
    # handle heavy box drawing. dumb/linux/screen are fuzzier.
    if any(t in term for t in ("xterm", "alacritty", "kitty", "iterm",
                               "wezterm", "gnome", "konsole", "vte",
                               "tmux-256color", "st-256color")):
        return BorderStyle.HEAVY.value
    if "256color" in term or "truecolor" in term:
        return BorderStyle.LIGHT.value
    return BorderStyle.LIGHT.value


# --------------------------------------------------------------------------- #
# Spec & context
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class FrameSpec:
    """Geometry + chrome parameters for one frame render.

    The spec is the static configuration; mutable per-render state
    (current word, progress, playing flag) lives on
    :class:`FrameContext`. This separation lets tests build a fixed
    spec and cycle contexts.
    """

    width: int = 100
    min_width: int = 60
    max_width: int = 160
    context_lines: int = 4       # rows ABOVE + BELOW the focal row
    border: str = field(default_factory=_detect_border_style)
    show_frame: bool = True      # outer ┏━┓ chrome; off == "minimal"
    show_header: bool = True
    show_footer: bool = True
    show_pivot: bool = True
    pivot_style: str = "fixed"   # "fixed" | "auto"
    title: str = ""
    subtitle: str = ""

    def __post_init__(self) -> None:
        """Reject an unknown border style instead of failing at render.

        ``border`` comes from user-editable config (Settings → Advanced
        → per-figure params), so any string can land here. An unknown
        value used to reach ``_BOX_SETS[self.border]`` and raise
        ``KeyError`` — in the middle of a render, on the next start-up,
        with the bad value still persisted in ``config.json``. We clamp
        it to the portable default at construction time so the bad
        value can never crash a frame.
        """
        if self.border not in _BOX_SETS:
            object.__setattr__(self, "border", DEFAULT_BORDER)

    def clamped_width(self, terminal_cols: int | None = None) -> int:
        """Pick a final width honoring min, max, AND terminal cols.

        Caps at terminal_cols so the frame doesn't overflow a narrow
        terminal. Note: the Panel wrapper (used by both WordFigure and
        HorizontalFigure) auto-sizes to the content width, so
        terminal_cols is a hard ceiling — the caller decides whether
        to pass it.
        """
        width = max(self.min_width, min(self.width, self.max_width))
        if terminal_cols is not None:
            width = min(width, max(self.min_width, terminal_cols))
        return width

    def box_chars(self) -> _BoxChars:
        """Return the box-drawing set for this spec's ``border``.

        ``__post_init__`` already normalised an unknown style; the
        ``.get`` fallback is belt-and-braces for specs rebuilt by
        ``dataclasses.replace`` or unpickled from an old config.
        """
        return _BOX_SETS.get(self.border, _BOX_SETS[DEFAULT_BORDER])


def resolve_frame_geometry(
    base_width: int, font_size_scale: int = 1
) -> tuple[int, int]:
    """Return ``(width, min_width)`` for the reading window.

    A terminal can't change the glyph size, so ``font_size_scale``
    narrows the reading window instead: every step up takes 10% of the
    width away, which makes the focal word take up a larger share of
    the window — the closest a TUI gets to "bigger font".

    ``min_width`` shrinks with the same ratio so a scaled window is
    never clamped back up to the unscaled minimum (which would make
    the scale a no-op on narrow terminals).
    """
    scale = max(1, min(5, int(font_size_scale)))
    base = max(MIN_FRAME_WIDTH, int(base_width))
    # scale 1 → 100% of the base width, scale 5 → 60%.
    percent = 11 - scale
    width = max(MIN_FRAME_WIDTH, base * percent // 10)
    min_width = max(MIN_FRAME_WIDTH, min(60, base) * percent // 10)
    return width, min_width


@dataclass(frozen=True)
class ProgressInfo:
    """Snapshot of reading progress for the footer rule."""

    word_index: int = 0
    total: int = 0
    wpm: int = 300
    time_remaining: str = ""     # "134:18"
    percentage: float = 0.0      # 0.0 .. 100.0


@dataclass(frozen=True)
class FrameContext:
    """All the per-render data the frame needs.

    Aggregating here means ``HorizontalFrame.build`` is pure (no
    implicit state lookup on the figure), making it trivial to test
    and to reuse from non-figure call sites (e.g. tests, or future
    "export-frame-as-SVG" tooling).
    """

    theme: Theme
    spec: FrameSpec
    focal_word: str = ""
    focal_parts: object | None = None  # WordParts (or any duck-typed obj with before_orp/orp_char/after_orp)
    context_above: Sequence[str] = ()
    context_below: Sequence[str] = ()
    progress: ProgressInfo = field(default_factory=ProgressInfo)
    playing: bool = False
    title: str = ""
    subtitle: str = ""
    header_meta: str = ""              # raw header metadata (chapter, %)
    footer_meta: str = ""              # raw footer metadata (controls, ETA)
    # ---- Horizontal strip (multi-word focal row) ---------------------- #
    # ``focal_strip`` holds the words shown around the focal word on the
    # focal row; ``focal_strip_index`` is the position of the focal word
    # inside it. Empty strip == single-word focal row (the classic RSVP
    # look, used by WordFigure).
    focal_strip: Sequence[str] = ()
    focal_strip_index: int = 0
    # Fade the peripheral words toward the edges of the strip.
    focal_strip_fade: bool = True
    # Bold the leading letter of every peripheral word (bionic-style).
    focal_strip_bold_hint: bool = False


# --------------------------------------------------------------------------- #
# Width & utility helpers
# --------------------------------------------------------------------------- #


def _cell_width(s: str) -> int:
    """Display cell width of a string, wcwidth-aware.

    Falls back to ``len(s)`` if ``get_character_cell_size`` returns
    ``None`` (control chars, malformed graphemes). We compute the
    SUM, not the max: a string of multiple chars is the sum of
    their cell widths.
    """
    total = 0
    for ch in s:
        cell = get_character_cell_size(ch)
        if cell is None:
            cell = 1
        elif cell < 0:
            cell = 0
        total += cell
    return total


def _truncate_to_cells(s: str, max_cells: int, ellipsis: str = "…") -> str:
    """Truncate ``s`` so its display width doesn't exceed ``max_cells``.

    Uses the same wcwidth-aware sum as :func:`_cell_width`. Returns
    ``s`` unchanged when it fits.
    """
    if _cell_width(s) <= max_cells:
        return s
    ell = _cell_width(ellipsis)
    budget = max(0, max_cells - ell)
    out: list[str] = []
    used = 0
    for ch in s:
        cw = get_character_cell_size(ch)
        if cw is None:
            cw = 1
        if used + cw > budget:
            break
        out.append(ch)
        used += cw
    return "".join(out) + ellipsis


def _pad_to_width(s: str, width: int, *, align: str = "left") -> str:
    """Pad ``s`` with spaces so its display width equals ``width``.

    Align: "left" / "center" / "right". Truncates with ellipsis if
    ``s`` is already wider than ``width`` (rare; reading window
    widths are big enough to swallow most context lines).
    """
    cells = _cell_width(s)
    if cells > width:
        return _truncate_to_cells(s, width)
    pad = width - cells
    if align == "left":
        return s + " " * pad
    if align == "right":
        return " " * pad + s
    # center
    left = pad // 2
    right = pad - left
    return " " * left + s + " " * right


def _normalise_focal_parts(parts: object) -> tuple[str, str, str]:
    """Return (before, char, after) regardless of which language the ORP came from.

    Pure-Python fallbacks return a 3-tuple; Rust returns a dataclass
    with ``before_orp``, ``orp_char``, ``after_orp``. We accept
    either. Defensive against None (e.g. ORP disabled).
    """
    if parts is None:
        return ("", "", "")
    if isinstance(parts, tuple):
        if len(parts) >= 3:
            return (parts[0] or "", parts[1] or "", parts[2] or "")
        return ("", "", "")
    # Duck-typed object: attribute lookup.
    before = getattr(parts, "before_orp", "") or ""
    char = getattr(parts, "orp_char", "") or ""
    after = getattr(parts, "after_orp", "") or ""
    return (before, char, after)


def _peripheral_style(theme: Theme, distance: int, fade: bool = True) -> str:
    """Style for a peripheral word: brighter close to the focal word.

    ``distance`` is 1 for the immediate neighbour and grows outwards.
    Without ``fade`` every peripheral word uses the plain anchor
    colour (the "flat dim" alternative the figure exposes).
    """
    anchor = theme.orp_anchor
    if not fade:
        return anchor
    focus_dim = getattr(theme, "focus_dim", "dim white")
    if distance <= 1:
        return anchor
    if distance == 2:
        return focus_dim
    # progressively dimmer via Rich's italic+dim combo
    return f"dim {focus_dim}" if "dim" not in focus_dim else focus_dim


def _append_peripheral(text: Text, word: str, style: str, bold_hint: bool) -> None:
    """Append a peripheral word, optionally bolding its first letter.

    ``bold_hint`` is the bionic-style hint: the leading letter is
    bolded so the eye can latch onto the word start without a full
    bionic rendering.
    """
    if not bold_hint or not word:
        text.append(word, style=style)
        return
    text.append(word[0], style=f"{style} bold")
    text.append(word[1:], style=style)


def _fit_strip(
    left_words: list[str],
    right_words: list[str],
    pivot_col: int,
    inner_width: int,
    before_cells: int,
    orp_cells: int,
    after_cells: int,
) -> tuple[list[str], list[str]]:
    """Drop the outermost words until the strip fits the window.

    Two constraints:
      * the words left of the focal word must fit before the pivot
        column, otherwise the ORP letter slides off the pivot;
      * the whole row must fit the inner width, otherwise the frame
        row overflows.

    Words are dropped from the outside in (the farthest word first),
    so the neighbours of the focal word always survive.
    """
    left_words = list(left_words)
    right_words = list(right_words)
    while True:
        left_cells = sum(_cell_width(w) for w in left_words) + len(left_words)
        right_cells = sum(_cell_width(w) for w in right_words) + len(right_words)

        if left_cells + before_cells > pivot_col and left_words:
            left_words = left_words[:-1]
            continue

        total = (
            left_cells + right_cells
            + before_cells + orp_cells + after_cells
        )
        if total > inner_width:
            if len(left_words) >= len(right_words) and left_words:
                left_words = left_words[:-1]
                continue
            if right_words:
                right_words = right_words[:-1]
                continue

        break
    return left_words, right_words


# --------------------------------------------------------------------------- #
# The frame renderer
# --------------------------------------------------------------------------- #


class HorizontalFrame:
    """Build a Rich renderable for one reading-window frame.

    Stateless after construction; thread-safe because the underlying
    Rich renderables are pure functions of the inputs.
    """

    def __init__(self) -> None:
        # Nothing to construct — kept as a class so future state
        # (cached glyph metrics, last terminal width) has somewhere
        # to live without a major refactor.
        pass

    # ---- Public builder --------------------------------------------------

    def build(self, ctx: FrameContext) -> ConsoleRenderable:
        """Render the frame described by ``ctx``.

        Returns a :class:`rich.console.Group` of :class:`rich.text.Text`
        rows: header, *reading rows, footer. Each row is a full-width
        Text whose display cells equal ``ctx.spec.clamped_width()``.

        The caller (figure render) typically wraps the Group in a
        :class:`rich.panel.Panel` if a border is desired; the frame
        itself is only the rule lines and reading content. This lets
        figure authors opt into "Panel with my frame inside" vs "just
        my frame, no extra chrome".
        """
        spec = ctx.spec
        width = spec.clamped_width()
        theme = ctx.theme
        box = spec.box_chars()
        rule_color = theme.frame_rule if hasattr(theme, "frame_rule") else theme.muted
        heavy_color = (
            theme.frame_rule_heavy if getattr(theme, "frame_rule_heavy", "")
            else rule_color
        )
        pivot_color = (
            theme.frame_pivot if getattr(theme, "frame_pivot", "")
            else theme.accent
        )
        corner_color = (
            theme.frame_corner if getattr(theme, "frame_corner", "")
            else heavy_color
        )

        rows: list[Text] = []

        # ---- Context rows ------------------------------------------------
        # ``spec.context_lines`` is the number of rows rendered on EACH
        # side of the focal row. Trimming here (instead of trusting the
        # caller) keeps the field live: the frame never draws more rows
        # than the spec allows.
        context_above = list(ctx.context_above)
        context_below = list(ctx.context_below)
        if spec.context_lines > 0:
            # ``above`` is ordered far→near, ``below`` near→far: keep the
            # rows closest to the focal word.
            context_above = context_above[-spec.context_lines:]
            context_below = context_below[:spec.context_lines]

        # ---- Header rule ----------------------------------------------
        if spec.show_header:
            rows.append(self._header_rule(ctx, width, box, rule_color, heavy_color, corner_color))

        # ---- Reading area ----------------------------------------------
        pivot_col = self._compute_pivot_column(width, ctx)
        # context_above is rendered TOP-TO-BOTTOM, top row first
        for i, word in enumerate(context_above):
            distance = len(context_above) - i   # 1 = nearest, N = farthest
            rows.append(
                self._context_line(
                    word, width, pivot_col=pivot_col,
                    distance=distance, side="above",
                    show_pivot=ctx.spec.show_pivot,
                    box=box, rule_color=rule_color, pivot_color=pivot_color,
                    theme=theme,
                )
            )
        rows.append(
            self._focal_row(
                ctx, width, pivot_col=pivot_col, box=box,
                rule_color=rule_color, pivot_color=pivot_color,
                heavy_color=heavy_color,
            )
        )
        for i, word in enumerate(context_below):
            distance = i + 1                         # 1 = nearest, N = farthest
            rows.append(
                self._context_line(
                    word, width, pivot_col=pivot_col,
                    distance=distance, side="below",
                    show_pivot=ctx.spec.show_pivot,
                    box=box, rule_color=rule_color, pivot_color=pivot_color,
                    theme=theme,
                )
            )

        # ---- Footer rule ----------------------------------------------
        if spec.show_footer:
            rows.append(self._footer_rule(ctx, width, box, rule_color, heavy_color, corner_color))

        # ---- Outer corners (only if show_frame) -----------------------
        if spec.show_frame:
            top = self._top_border(width, box, corner_color)
            bot = self._bottom_border(width, box, corner_color)
            return Group(top, *rows, bot)

        return Group(*rows)

    # ---- Internals -------------------------------------------------------

    @staticmethod
    def _compute_pivot_column(width: int, ctx: FrameContext) -> int:
        """Return the 0-based pivot column (inclusive) of the focal row.

        We default to horizontal-center for readability: the eye
        tracks the middle of the screen and the frame holds there.
        Future work: per-figure opt-in to ``pivot_style="orp"``
        which would put the pivot at the focal letter column.
        """
        if ctx.spec.pivot_style == "auto":
            return max(0, width // 2)
        # ``fixed`` (default) — column at the half-cell of the inner area.
        return max(1, (width - 2) // 2)

    @staticmethod
    def _top_border(width: int, box: _BoxChars, color: str) -> Text:
        return Text(
            box.top_left + box.horizontal * (width - 2) + box.top_right,
            style=color,
        )

    @staticmethod
    def _bottom_border(width: int, box: _BoxChars, color: str) -> Text:
        return Text(
            box.bottom_left + box.horizontal * (width - 2) + box.bottom_right,
            style=color,
        )

    @staticmethod
    def _header_rule(
        ctx: FrameContext,
        width: int,
        box: _BoxChars,
        rule_color: str,
        heavy_color: str,
        corner_color: str,
    ) -> Text:
        """Header rule spanning the full frame width, centered metadata.

        Visual:  ┅━━━━━ chapter · pct ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┅
        Uses ``┅`` (TRIPLE HORIZONTAL) as the leading glyph so the
        header visually anchors the frame without the pivot column.
        The row is always exactly ``width`` cells wide.
        """
        # U+2505 TRIPLE HORIZONTAL — heavier-than-━ visual anchor at
        # the start; falls back to box.horizontal on ASCII/non-supporting
        # terminals.
        _triple_h = "\u2505"
        if not ctx.header_meta:
            return Text(_triple_h + box.horizontal * (width - 1), style=heavy_color)
        # The metadata comes from the figure and can be longer than the
        # frame (a long book title on a narrow terminal). Truncate it so
        # the rule never overflows the row width.
        header_meta = _truncate_to_cells(ctx.header_meta, max(0, width - 2))
        meta_cells = _cell_width(header_meta)
        fill_total = max(0, width - meta_cells - 2)   # -2 for the triple-H chars
        left_fill = fill_total // 2
        right_fill = fill_total - left_fill
        text = Text()
        text.append(_triple_h, style=corner_color)
        text.append(
            " " * left_fill + header_meta + " " * right_fill,
            style=f"bold {heavy_color}",
        )
        text.append(_triple_h, style=corner_color)
        return text

    @staticmethod
    def _footer_rule(
        ctx: FrameContext,
        width: int,
        box: _BoxChars,
        rule_color: str,
        heavy_color: str,
        corner_color: str,
    ) -> Text:
        """Footer rule spanning the full frame width, centered metadata.

        Visual:  ┄━━━━  WPM · ░▓▓ · ETA ━━━━━━━━━━━━━━━━━━━━━━━━━━━┄
        Uses ``┄`` (TRIPLE HORIZONTAL — lighter variant) to mirror the
        header anchor. The row is always exactly ``width`` cells wide.
        """
        # U+2504 TRIPLE HORIZONTAL — mirror of the header anchor; always
        # 1 cell regardless of terminal (falls back to horizontal on
        # ASCII-only).
        _triple_l = "\u2504"
        if not ctx.footer_meta:
            return Text(_triple_l + box.horizontal * (width - 1), style=heavy_color)
        # Same overflow guard as the header rule.
        footer_meta = _truncate_to_cells(ctx.footer_meta, max(0, width - 2))
        meta_cells = _cell_width(footer_meta)
        fill_total = max(0, width - meta_cells - 2)
        left_fill = fill_total // 2
        right_fill = fill_total - left_fill
        text = Text()
        text.append(_triple_l, style=corner_color)
        text.append(
            " " * left_fill + footer_meta + " " * right_fill,
            style=heavy_color,
        )
        text.append(_triple_l, style=corner_color)
        return text

    @staticmethod
    def _focal_row(
        ctx: FrameContext,
        width: int,
        pivot_col: int,
        box: _BoxChars,
        rule_color: str,
        pivot_color: str,
        heavy_color: str,
    ) -> Text:
        """Render the focal word row, padded so ORP lands at ``pivot_col``.

        Strategy:
          1. Normalise the focal word into (before, orp_char, after).
          2. Pad BEFORE with right-aligned spaces so the orp column
             ends up at ``pivot_col``.
          3. Pad AFTER with left-aligned spaces so the row fills the
             width with a trailing pivot column vertex.

        When the context carries a horizontal strip (``focal_strip``),
        the row becomes a multi-word strip: the words on either side of
        the focal word are the peripheral context, and the ORP letter
        still lands on the pivot column.

        If ``show_pivot`` is False we skip the trailing tee so the
        row reads like a flat strip.
        """
        text = Text()
        before, orp_char, after = _normalise_focal_parts(ctx.focal_parts)
        pivot_width = 1 if ctx.spec.show_pivot else 0
        inner_width = width - pivot_width

        strip = list(ctx.focal_strip or ())
        if strip:
            focal_idx = max(0, min(ctx.focal_strip_index, len(strip) - 1))
            return HorizontalFrame._strip_row(
                ctx, strip, focal_idx, width, pivot_col, inner_width,
                before, orp_char, after, pivot_width, box, pivot_color,
            )

        if not orp_char:
            # ORP disabled: render the raw word centered in the inner area.
            raw = ctx.focal_word or ""
            text.append(
                _pad_to_width(raw, inner_width, align="center"),
                style=ctx.theme.orp_anchor,
            )
            if pivot_width:
                text.append(box.vertical, style=pivot_color)
            return text

        # ORP enabled: pad BEFORE so left_pad + width(before) = pivot_col.
        before_cells = _cell_width(before)
        orp_cells = _cell_width(orp_char)
        after_cells = _cell_width(after)
        left_pad = max(0, pivot_col - before_cells)
        right_pad = max(
            0,
            inner_width - left_pad - before_cells - orp_cells - after_cells,
        )

        text.append(" " * left_pad, style="default")
        text.append(before, style=ctx.theme.orp_anchor)
        text.append(orp_char, style=ctx.theme.orp)
        text.append(after, style=ctx.theme.orp_anchor)
        text.append(" " * right_pad, style="default")
        if pivot_width:
            text.append(box.vertical, style=pivot_color)
        return text

    @staticmethod
    def _strip_row(
        ctx: FrameContext,
        strip: list[str],
        focal_idx: int,
        width: int,
        pivot_col: int,
        inner_width: int,
        before: str,
        orp_char: str,
        after: str,
        pivot_width: int,
        box: _BoxChars,
        pivot_color: str,
    ) -> Text:
        """Render the focal row as a horizontal strip of words.

        The focal word keeps its ORP highlight and stays anchored at the
        pivot column; the words on either side are the peripheral
        context. Words that don't fit the window are dropped from the
        outside in, so the neighbours of the focal word always survive.
        """
        left_words = strip[:focal_idx]
        right_words = strip[focal_idx + 1:]

        before_cells = _cell_width(before)
        orp_cells = _cell_width(orp_char)
        after_cells = _cell_width(after)

        left_words, right_words = _fit_strip(
            left_words, right_words, pivot_col, inner_width,
            before_cells, orp_cells, after_cells,
        )

        left_cells = sum(_cell_width(w) for w in left_words) + len(left_words)
        right_cells = sum(_cell_width(w) for w in right_words) + len(right_words)

        left_pad = max(0, pivot_col - left_cells - before_cells)
        right_pad = max(
            0,
            inner_width - left_pad - left_cells - before_cells
            - orp_cells - after_cells - right_cells,
        )

        text = Text()
        text.append(" " * left_pad, style="default")

        for i, word in enumerate(left_words):
            if i:
                text.append(" ", style="default")
            # distance 1 == the word right before the focal one.
            distance = len(left_words) - i
            _append_peripheral(
                text, word,
                _peripheral_style(ctx.theme, distance, ctx.focal_strip_fade),
                ctx.focal_strip_bold_hint,
            )
        if left_words:
            text.append(" ", style="default")

        text.append(before, style=ctx.theme.orp_anchor)
        text.append(orp_char, style=ctx.theme.orp)
        text.append(after, style=ctx.theme.orp_anchor)

        for i, word in enumerate(right_words):
            text.append(" ", style="default")
            _append_peripheral(
                text, word,
                _peripheral_style(ctx.theme, i + 1, ctx.focal_strip_fade),
                ctx.focal_strip_bold_hint,
            )

        text.append(" " * right_pad, style="default")
        if pivot_width:
            text.append(box.vertical, style=pivot_color)
        return text

    @staticmethod
    def _context_line(
        word: str,
        width: int,
        pivot_col: int,
        distance: int,
        side: str,
        show_pivot: bool,
        box: _BoxChars,
        rule_color: str,
        pivot_color: str,
        theme: Theme,
    ) -> Text:
        """Render one context line, fading toward the edge.

        Fade model: every ``distance`` step adds one ``dim`` style
        layer. We cap the dimming at ``distance=4`` so very-far
        words are still readable (we want peripheral vision,
        not invisibility).
        """
        text = Text()
        word_cells = _cell_width(word)
        # Pad left so the word ends centered around (pivot_col - 2)
        center = max(0, pivot_col - 2)  # focal starts a few cells before pivot
        left_pad = max(0, center - word_cells // 2)
        right_pad = max(0, width - left_pad - word_cells - 1)
        # A context row can be longer than the frame (a whole sentence
        # on a narrow terminal). Truncate it so the row keeps its width.
        budget = max(0, width - left_pad - 1)
        word = _truncate_to_cells(word, budget) if budget else ""
        word_cells = _cell_width(word)
        right_pad = max(0, width - left_pad - word_cells - 1)
        # Trailing pivot column char (only if show_pivot)
        text.append(" " * left_pad, style="default")
        # Fade: closer to focal = brighter, farther = dimmer
        focus_dim = getattr(theme, "focus_dim", "dim white")
        focus_style = focus_dim
        if distance <= 1:
            focus_style = theme.orp_anchor  # immediate neighbours get anchor color
        elif distance == 2:
            focus_style = focus_dim
        else:
            # progressively dimmer via Rich's italic+dim combo
            focus_style = f"dim {focus_dim}" if "dim" not in focus_dim else focus_dim
        text.append(word, style=focus_style)
        text.append(" " * right_pad, style="default")
        if show_pivot:
            text.append(box.vertical, style=pivot_color)
        return text





# --------------------------------------------------------------------------- #
# Convenience facade
# --------------------------------------------------------------------------- #


def build_horizontal_frame(
    *,
    theme: Theme,
    spec: FrameSpec,
    focal_word: str,
    focal_parts: object | None = None,
    context_above: Sequence[str] = (),
    context_below: Sequence[str] = (),
    progress: ProgressInfo | None = None,
    playing: bool = False,
    title: str = "",
    subtitle: str = "",
    header_meta: str = "",
    footer_meta: str = "",
    terminal_cols: int | None = None,
) -> ConsoleRenderable:
    """One-shot builder.

    Figures with simple needs (e.g. ``WordFigure``) don't want to
    instantiate ``FrameContext`` themselves. This facade builds
    the context and renders in one call. Power users should use
    ``HorizontalFrame().build(ctx)`` directly so they can mutate
    the spec between renders.
    """
    if progress is None:
        progress = ProgressInfo()
    # If terminal_cols is constrained, clamp the spec's effective width
    # at build time via the FrameContext's spec — clamped_width() reads
    # spec.width but we can also override here.
    if terminal_cols is not None and terminal_cols < spec.width:
        spec = FrameSpec(
            width=terminal_cols,
            min_width=spec.min_width,
            max_width=spec.max_width,
            context_lines=spec.context_lines,
            border=spec.border,
            show_frame=spec.show_frame,
            show_header=spec.show_header,
            show_footer=spec.show_footer,
            show_pivot=spec.show_pivot,
            pivot_style=spec.pivot_style,
            title=spec.title,
            subtitle=spec.subtitle,
        )
    ctx = FrameContext(
        theme=theme,
        spec=spec,
        focal_word=focal_word,
        focal_parts=focal_parts,
        context_above=context_above,
        context_below=context_below,
        progress=progress,
        playing=playing,
        title=title,
        subtitle=subtitle,
        header_meta=header_meta,
        footer_meta=footer_meta,
    )
    return HorizontalFrame().build(ctx)


# --------------------------------------------------------------------------- #
# Exports
# --------------------------------------------------------------------------- #


__all__ = [
    "BorderStyle",
    "FrameSpec",
    "FrameContext",
    "ProgressInfo",
    "HorizontalFrame",
    "build_horizontal_frame",
]
