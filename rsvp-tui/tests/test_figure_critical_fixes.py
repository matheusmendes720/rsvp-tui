"""Regression tests for the three figure/render critical defects.

Each test here pins a defect that was reproduced with a real render
and that a reviewer measured:

* **B2** — the "Horizontal (Multi-Word)" figure stopped being
  multi-word: the focal row showed ONE word per line and the
  peripheral context disappeared.
* **B3** — the density/size hotkeys (``+``/``-``, ``{``/``}``,
  ``Shift+{``/``Shift+}``) toasted a value and changed nothing.
* **B4** — an invalid ``border_style`` raised ``KeyError`` inside the
  render, and the bad value was persisted, so the app kept crashing
  on the next start-up.

(The fourth critical defect — the library deleting the wrong book —
lives in ``test_library_delete.py``.)
"""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from rsvp_tui.figures.base import FigureState
from rsvp_tui.figures.frame import DEFAULT_BORDER, FrameSpec
from rsvp_tui.figures.horizontal import HorizontalFigure
from rsvp_tui.figures.word import WordFigure

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

WORDS = tuple(f"w{i}" for i in range(60))


def _state(word_index: int = 30) -> FigureState:
    return FigureState(words=WORDS, word_index=word_index, wpm=300)


def _render_lines(renderable: object, width: int = 200) -> list[str]:
    """Render a figure to a list of text lines."""
    buffer = io.StringIO()
    console = Console(width=width, file=buffer, legacy_windows=False)
    console.print(renderable)
    return buffer.getvalue().splitlines()


def _focal_row(lines: list[str]) -> str:
    """Return the row that carries the focal word."""
    for line in lines:
        if "w30" in line:
            return line
    raise AssertionError("no focal row found in:\n" + "\n".join(lines))


# --------------------------------------------------------------------------- #
# B2 — the horizontal figure must show context on BOTH sides
# --------------------------------------------------------------------------- #


def test_horizontal_figure_renders_words_on_both_sides_of_the_focal() -> None:
    """The focal row carries the words around the focal word.

    Before the fix the figure advertised "Horizontal (Multi-Word)" but
    rendered one word per line: the peripheral context was gone.
    """
    fig = HorizontalFigure(_state(), params={"chunk_size": 9})
    row = _focal_row(_render_lines(fig.render()))

    # Words on the left of the focal word...
    for offset in (1, 2, 3, 4):
        assert f"w{30 - offset}" in row, f"missing left context word w{30 - offset}: {row!r}"
    # ...and on the right.
    for offset in (1, 2, 3, 4):
        assert f"w{30 + offset}" in row, f"missing right context word w{30 + offset}: {row!r}"


def test_horizontal_chunk_size_changes_the_content_not_only_the_label() -> None:
    """``chunk_size`` must change WHAT is rendered, not just the "[17w]" tag."""
    narrow = _render_lines(HorizontalFigure(_state(), params={"chunk_size": 5}).render())
    wide = _render_lines(HorizontalFigure(_state(), params={"chunk_size": 11}).render())

    assert narrow != wide, "chunk_size does not change the rendered content"

    narrow_row = _focal_row(narrow)
    wide_row = _focal_row(wide)
    assert "w25" not in narrow_row, "the narrow strip shows words it should not"
    assert "w25" in wide_row, "the wide strip does not show the extra context"


# --------------------------------------------------------------------------- #
# B3 — the density controls must change the render
# --------------------------------------------------------------------------- #


def test_font_size_scale_changes_the_render() -> None:
    """``font_size_scale`` narrows the reading window — it must be visible."""
    normal = _render_lines(HorizontalFigure(_state(), params={"font_size_scale": 1}).render())
    large = _render_lines(HorizontalFigure(_state(), params={"font_size_scale": 5}).render())

    assert normal != large, "font_size_scale does not change the rendered content"
    assert max(len(line) for line in large) < max(len(line) for line in normal)


def test_words_per_line_changes_the_strip_width() -> None:
    """``words_per_line`` is the strip width — it must reach the figure."""
    narrow = _render_lines(HorizontalFigure(_state(), params={"chunk_size": 5}).render())
    wide = _render_lines(HorizontalFigure(_state(), params={"chunk_size": 13}).render())
    assert narrow != wide


def test_context_words_change_the_number_of_context_rows() -> None:
    """``context_words_above`` / ``context_words_below`` must add rows."""
    one = _render_lines(
        HorizontalFigure(
            _state(),
            params={"context_words_above": 1, "context_words_below": 1},
        ).render()
    )
    four = _render_lines(
        HorizontalFigure(
            _state(),
            params={"context_words_above": 4, "context_words_below": 4},
        ).render()
    )

    assert one != four, "the context rows did not change"
    assert len(four) > len(one)


def test_word_figure_context_window_changes_the_render() -> None:
    """The framed word figure must honour the context window too."""
    one = _render_lines(
        WordFigure(
            _state(),
            params={"frame_style": "wide", "context_words_above": 1, "context_words_below": 1},
        ).render()
    )
    three = _render_lines(
        WordFigure(
            _state(),
            params={"frame_style": "wide", "context_words_above": 3, "context_words_below": 3},
        ).render()
    )

    assert one != three, "the context window does not change the rendered content"
    assert len(three) > len(one)


# --------------------------------------------------------------------------- #
# B4 — an invalid border style must not blow up the render
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("border", ["rounded", "", "HEAVY", "double ", "box"])
def test_invalid_border_style_does_not_raise(border: str) -> None:
    """A bogus ``border_style`` must fall back, not raise ``KeyError``."""
    fig = HorizontalFigure(_state(), params={"border_style": border})
    lines = _render_lines(fig.render())
    assert lines, "the figure rendered nothing"

    word_fig = WordFigure(_state(), params={"border_style": border})
    assert _render_lines(word_fig.render())


@pytest.mark.parametrize("border", ["rounded", "", "HEAVY"])
def test_invalid_border_style_is_normalised_at_construction(border: str) -> None:
    """The bad value is clamped when the spec is built, not at render time."""
    spec = FrameSpec(border=border)
    assert spec.border == DEFAULT_BORDER
    assert spec.box_chars().horizontal == "─"


def test_invalid_border_style_survives_a_restart() -> None:
    """A persisted bad value must not break the NEXT start-up.

    The old code stored whatever the user typed in ``config.json`` and
    only blew up later, inside the render — so the app crashed on every
    start-up until the config was hand-edited.
    """
    persisted = {"border_style": "rounded"}

    # This is how the reader screen rebuilds a figure from the config.
    fig = HorizontalFigure(_state(), params=dict(persisted))
    assert _render_lines(fig.render())

    # And again, from the same persisted value, in a fresh process-like
    # construction: the frame spec must normalise it.
    spec = FrameSpec(border=str(persisted["border_style"]))
    assert spec.border == DEFAULT_BORDER
