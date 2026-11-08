"""Tests for the HorizontalFrame system (figures/frame.py)."""

from __future__ import annotations

import pytest

from rsvp_tui.figures.frame import (
    FrameContext,
    FrameSpec,
    HorizontalFrame,
    ProgressInfo,
    _cell_width,
    _normalise_focal_parts,
    _pad_to_width,
    _truncate_to_cells,
    build_horizontal_frame,
)
from rsvp_tui.themes import get_theme

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _make_ctx(
    width: int = 80,
    context_lines: int = 2,
    header_meta: str = "",
    footer_meta: str = "",
    show_frame: bool = True,
    show_pivot: bool = True,
    context_above: list[str] | None = None,
    context_below: list[str] | None = None,
) -> FrameContext:
    """Build a minimal FrameContext for testing."""
    spec = FrameSpec(
        width=width,
        context_lines=context_lines,
        border="heavy",
        show_frame=show_frame,
        show_pivot=show_pivot,
    )
    return FrameContext(
        theme=get_theme("dark"),
        spec=spec,
        focal_word="testing",
        focal_parts=(None, None, None),   # ORP disabled
        context_above=context_above if context_above is not None else ["alpha", "beta"],
        context_below=context_below if context_below is not None else ["gamma", "delta"],
        progress=ProgressInfo(
            word_index=10,
            total=100,
            wpm=300,
            time_remaining="1:30",
            percentage=10.0,
        ),
        playing=True,
        header_meta=header_meta,
        footer_meta=footer_meta,
    )


# --------------------------------------------------------------------------- #
# Geometry helpers
# --------------------------------------------------------------------------- #


class TestCellWidth:
    def test_plain_ascii(self) -> None:
        assert _cell_width("abc") == 3

    def test_mixed(self) -> None:
        assert _cell_width("hello world") == 11

    def test_empty(self) -> None:
        assert _cell_width("") == 0

    def test_leading_trailing_spaces(self) -> None:
        # 2 leading + 2 letters + 2 trailing = 6 cells
        assert _cell_width("  hi  ") == 6


class TestTruncate:
    def test_under_budget(self) -> None:
        assert _truncate_to_cells("hi", 5) == "hi"

    def test_exact_fit(self) -> None:
        assert _truncate_to_cells("hello", 5) == "hello"

    def test_truncates_with_ellipsis(self) -> None:
        result = _truncate_to_cells("hello", 3)
        assert result.endswith("…")
        assert _cell_width(result) <= 3


class TestPadToWidth:
    def test_left_pad(self) -> None:
        assert _pad_to_width("hi", 5, align="left") == "hi   "

    def test_right_pad(self) -> None:
        assert _pad_to_width("hi", 5, align="right") == "   hi"

    def test_center_pad(self) -> None:
        assert _pad_to_width("hi", 5, align="center") == " hi  "

    def test_truncate_if_too_wide(self) -> None:
        result = _pad_to_width("hello", 3, align="center")
        assert result.endswith("…")
        assert _cell_width(result) <= 3


class TestNormaliseFocalParts:
    def test_none(self) -> None:
        assert _normalise_focal_parts(None) == ("", "", "")

    def test_tuple(self) -> None:
        assert _normalise_focal_parts(("bef", "X", "aft")) == ("bef", "X", "aft")

    def test_short_tuple(self) -> None:
        assert _normalise_focal_parts(("a",)) == ("", "", "")

    def test_object(self) -> None:
        class Obj:
            before_orp = "be"
            orp_char = "f"
            after_orp = "ter"

        assert _normalise_focal_parts(Obj()) == ("be", "f", "ter")


# --------------------------------------------------------------------------- #
# FrameSpec
# --------------------------------------------------------------------------- #


class TestFrameSpec:
    def test_clamped_width_default(self) -> None:
        spec = FrameSpec(width=100)
        assert spec.clamped_width() == 100

    def test_clamped_width_respects_min(self) -> None:
        spec = FrameSpec(width=30, min_width=60)
        assert spec.clamped_width() == 60

    def test_clamped_width_respects_max(self) -> None:
        spec = FrameSpec(width=200, max_width=120)
        assert spec.clamped_width() == 120

    def test_clamped_width_respects_terminal(self) -> None:
        spec = FrameSpec(width=100)
        assert spec.clamped_width(terminal_cols=70) == 70

    def test_clamped_width_terminal_too_small(self) -> None:
        spec = FrameSpec(width=100, min_width=60)
        assert spec.clamped_width(terminal_cols=50) == 60

    def test_box_chars_heavy(self) -> None:
        spec = FrameSpec(border="heavy")
        box = spec.box_chars()
        assert box.horizontal == "━"
        assert box.vertical == "┃"
        assert box.top_left == "┏"

    def test_box_chars_ascii(self) -> None:
        spec = FrameSpec(border="ascii")
        box = spec.box_chars()
        assert box.horizontal == "-"
        assert box.vertical == "|"


# --------------------------------------------------------------------------- #
# HorizontalFrame
# --------------------------------------------------------------------------- #


class TestHorizontalFrameRows:
    """Smoke tests: all rows in the renderable must be exactly `width` cells."""

    def test_all_rows_exactly_width_cells(self) -> None:
        ctx = _make_ctx(width=88)
        frame = HorizontalFrame()
        body = frame.build(ctx)
        from rich.console import Group

        assert isinstance(body, Group)
        for i, row in enumerate(body.renderables):
            if hasattr(row, "cell_len"):
                assert row.cell_len == 88, (
                    f"row {i} has cell_len={row.cell_len}, expected 88"
                )

    def test_row_count_with_frame(self) -> None:
        # _make_ctx provides 2 above + 2 below (context_above/below in the ctx call)
        ctx = _make_ctx(width=80, context_lines=3, show_frame=True)
        body = HorizontalFrame().build(ctx)
        from rich.console import Group

        assert isinstance(body, Group)
        rows = list(body.renderables)
        # frame=True: top + header + 2 above + focal + 2 below + footer + bottom
        expected = 1 + 1 + 2 + 1 + 2 + 1 + 1
        assert len(rows) == expected, f"expected {expected} rows, got {len(rows)}"

    def test_row_count_without_frame(self) -> None:
        ctx = _make_ctx(width=80, context_lines=2, show_frame=False)
        body = HorizontalFrame().build(ctx)
        from rich.console import Group

        assert isinstance(body, Group)
        rows = list(body.renderables)
        # frame=False: header + 2 above + focal + 2 below + footer
        expected = 1 + 2 + 1 + 2 + 1
        assert len(rows) == expected, f"expected {expected} rows, got {len(rows)}"

    def test_row_count_header_only(self) -> None:
        # Empty context lists: header + focal + footer only
        ctx = _make_ctx(width=80, context_lines=3, show_frame=False,
                        context_above=[], context_below=[])
        body = HorizontalFrame().build(ctx)
        from rich.console import Group

        assert isinstance(body, Group)
        rows = list(body.renderables)
        # header + focal + footer (no context rows since lists are empty)
        assert len(rows) == 3


class TestHorizontalFrameMetadata:
    def test_empty_header_is_flush_rule(self) -> None:
        ctx = _make_ctx(width=80, header_meta="")
        header_rule = HorizontalFrame._header_rule(ctx, 80, ctx.spec.box_chars(), "grey35", "grey35", "cyan")
        assert hasattr(header_rule, "cell_len")
        assert header_rule.cell_len == 80

    def test_header_centered_metadata(self) -> None:
        meta = " chapter · 50% "
        ctx = _make_ctx(width=80, header_meta=meta)
        header_rule = HorizontalFrame._header_rule(ctx, 80, ctx.spec.box_chars(), "grey35", "grey35", "cyan")
        assert header_rule.cell_len == 80

    def test_footer_centered_metadata(self) -> None:
        meta = " ▶ 300 WPM · 1:30 left "
        ctx = _make_ctx(width=80, footer_meta=meta)
        footer_rule = HorizontalFrame._footer_rule(ctx, 80, ctx.spec.box_chars(), "grey35", "grey35", "cyan")
        assert footer_rule.cell_len == 80


class TestBorderStyles:
    @pytest.mark.parametrize("style", ["heavy", "double", "light", "ascii"])
    def test_all_border_styles_produce_correct_width(self, style: str) -> None:
        spec = FrameSpec(width=80, border=style)
        ctx = FrameContext(
            theme=get_theme("dark"),
            spec=spec,
            focal_word="word",
            focal_parts=None,
            context_above=[],
            context_below=[],
            progress=ProgressInfo(),
            playing=False,
        )
        body = HorizontalFrame().build(ctx)
        from rich.console import Group

        assert isinstance(body, Group)
        for i, row in enumerate(body.renderables):
            if hasattr(row, "cell_len"):
                assert row.cell_len == 80, (
                    f"border={style} row {i} has cell_len={row.cell_len}, expected 80"
                )


# --------------------------------------------------------------------------- #
# build_horizontal_frame facade
# --------------------------------------------------------------------------- #


class TestFacade:
    def test_facade_returns_group(self) -> None:
        result = build_horizontal_frame(
            theme=get_theme("dark"),
            spec=FrameSpec(width=80),
            focal_word="test",
            focal_parts=None,
        )
        from rich.console import Group

        assert isinstance(result, Group)

    def test_facade_terminal_cols_overrides_width(self) -> None:
        result = build_horizontal_frame(
            theme=get_theme("dark"),
            spec=FrameSpec(width=200),
            focal_word="test",
            focal_parts=None,
            terminal_cols=60,
        )
        from rich.console import Group

        assert isinstance(result, Group)
        for row in result.renderables:
            if hasattr(row, "cell_len"):
                assert row.cell_len <= 60, (
                    f"facade with terminal_cols=60 produced rows wider than 60: {row.cell_len}"
                )
