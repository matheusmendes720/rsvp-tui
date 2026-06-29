"""Tests for the small util module (Phase 5)."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from rsvp_tui.util import atomic_write_text, safe_callback

# ---- safe_callback -------------------------------------------------------


def test_safe_callback_returns_normal_value() -> None:
    """When the wrapped function returns normally, we get that value."""

    class Holder:
        @safe_callback(default=None)
        def compute(self, x: int) -> int:
            return x * 2

    assert Holder().compute(21) == 42


def test_safe_callback_swallows_exception_returns_default() -> None:
    """An exception is swallowed and ``default`` is returned."""

    class Holder:
        @safe_callback(default="fallback")
        def boom(self) -> None:
            raise RuntimeError("kaboom")

    assert Holder().boom() == "fallback"


def test_safe_callback_surfaces_toast_when_possible() -> None:
    """If ``self.app.notify`` exists, we call it on exception."""

    captured: list[tuple[str, str | None]] = []

    class Holder:
        app = MagicMock()
        app.notify = lambda msg, severity=None: captured.append((msg, severity))

        @safe_callback(default=None)
        def boom(self) -> None:
            raise RuntimeError("nope")

    Holder().boom()
    assert len(captured) == 1
    assert "nope" in captured[0][0]
    assert captured[0][1] == "error"


def test_safe_callback_survives_when_notify_fails() -> None:
    """A failing notify doesn't mask the original error."""

    class Holder:
        app = MagicMock()
        app.notify = MagicMock(side_effect=RuntimeError("notify broken"))

        @safe_callback(default="ok")
        def boom(self) -> None:
            raise ValueError("real error")

    assert Holder().boom() == "ok"


def test_safe_callback_works_without_app_attr() -> None:
    """A holder with no ``app`` attribute doesn't crash the wrapper."""

    class Holder:
        @safe_callback(default=42)
        def boom(self) -> None:
            raise RuntimeError("oops")

    assert Holder().boom() == 42


def test_safe_callback_log_traceback_off(caplog: pytest.LogCaptureFixture) -> None:
    """``log_traceback=False`` logs a warning instead of full traceback."""

    class Holder:
        @safe_callback(default=None, log_traceback=False)
        def boom(self) -> None:
            raise RuntimeError("quiet")

    with caplog.at_level(logging.WARNING):
        Holder().boom()
    assert any("quiet" in rec.message for rec in caplog.records)


# ---- atomic_write_text ---------------------------------------------------


def test_atomic_write_text_creates_file(tmp_path: Path) -> None:
    """A simple write produces the file with the expected content."""
    target = tmp_path / "out.txt"
    atomic_write_text(target, "hello world")
    assert target.read_text(encoding="utf-8") == "hello world"


def test_atomic_write_text_overwrites_existing(tmp_path: Path) -> None:
    """An existing file is replaced (not appended)."""
    target = tmp_path / "out.txt"
    target.write_text("old", encoding="utf-8")
    atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"


def test_atomic_write_text_creates_parent_dirs(tmp_path: Path) -> None:
    """Missing parents are created."""
    target = tmp_path / "deep" / "nested" / "out.txt"
    atomic_write_text(target, "ok")
    assert target.read_text(encoding="utf-8") == "ok"


def test_atomic_write_text_cleans_up_tmp_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing write leaves no .tmp file behind."""
    target = tmp_path / "out.txt"
    real_replace = os.replace

    def broken_replace(src: str, dst: str) -> None:
        raise OSError("simulated crash")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError):
        atomic_write_text(target, "x")
    monkeypatch.setattr(os, "replace", real_replace)
    leftovers = list(tmp_path.glob("out.txt.*.tmp"))
    assert leftovers == []


def test_atomic_write_text_no_partial_file_on_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing write doesn't corrupt the existing file."""
    target = tmp_path / "out.txt"
    target.write_text("original", encoding="utf-8")

    def broken_replace(src: str, dst: str) -> None:
        raise OSError("simulated crash")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError):
        atomic_write_text(target, "NEW")
    assert target.read_text(encoding="utf-8") == "original"
