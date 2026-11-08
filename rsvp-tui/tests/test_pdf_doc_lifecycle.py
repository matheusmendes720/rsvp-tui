"""Regression tests for PDF/EPUB document lifecycle.

The fallback PDF/EPUB openers pass an opened ``doc`` / ``book`` to a
private parser helper. If the helper raises before reaching the
``close()`` call inside it, the underlying file handle is leaked.
These tests pin the fix: doc.close() must always run, even when the
parser raises.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from rsvp_tui import fallbacks


class _RecordingDoc:
    """Stand-in for a fitz document. Tracks ``close()`` calls."""

    def __init__(self) -> None:
        self.closed = False
        # Surface the attributes the parser pokes at.
        self.metadata: dict[str, str] = {"title": "T", "author": "A"}

    def close(self) -> None:
        self.closed = True


def _install_fake_fitz(monkeypatch: pytest.MonkeyPatch) -> _RecordingDoc:
    """Install a fake ``fitz`` so we don't require pymupdf installed.

    Returns the sentinel doc so the test can assert on ``close()``.
    """
    fake = types.ModuleType("fitz")
    sentinel = _RecordingDoc()

    def fake_open(*_args, **_kwargs):
        return sentinel

    fake.open = fake_open  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "fitz", fake)
    return sentinel


def test_parse_pdf_bytes_closes_doc_even_when_parser_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If ``_parse_pdf_doc`` raises, ``parse_pdf_bytes`` must still close
    the underlying fitz document. Otherwise the document stays open
    for the lifetime of the process (file descriptor / memory leak)."""
    sentinel = _install_fake_fitz(monkeypatch)

    def boom(_doc):
        raise RuntimeError("simulated parser crash")

    monkeypatch.setattr(fallbacks, "_parse_pdf_doc", boom)

    with pytest.raises(RuntimeError, match="simulated parser crash"):
        fallbacks.parse_pdf_bytes(b"%PDF-1.4 fake")

    assert sentinel.closed, (
        "parse_pdf_bytes leaked the fitz document: close() was not "
        "called when _parse_pdf_doc raised."
    )


def test_parse_pdf_path_closes_doc_even_when_parser_raises(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same as the bytes variant, but for the on-disk entry point.

    The path is never read because the fake fitz short-circuits
    ``open`` — that's fine, we only care that the doc lifetime is
    scoped to the ``with`` block.
    """
    sentinel = _install_fake_fitz(monkeypatch)

    def boom(_doc):
        raise RuntimeError("simulated parser crash")

    monkeypatch.setattr(fallbacks, "_parse_pdf_doc", boom)

    fake_pdf = tmp_path / "fake.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")

    with pytest.raises(RuntimeError, match="simulated parser crash"):
        fallbacks.parse_pdf_path(fake_pdf)

    assert sentinel.closed, (
        "parse_pdf_path leaked the fitz document: close() was not "
        "called when _parse_pdf_doc raised."
    )


def test_parse_pdf_bytes_closes_doc_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sanity check: even on the happy path the doc must be closed
    once the parser returns. (Already true before the fix — guards
    against a regression that re-introduces the leak.)"""
    sentinel = _install_fake_fitz(monkeypatch)
    monkeypatch.setattr(
        fallbacks,
        "_parse_pdf_doc",
        lambda _doc: fallbacks.ParseResult(
            title="T", author="A", plain_text="", chapters=[], word_count=0
        ),
    )

    result = fallbacks.parse_pdf_bytes(b"%PDF-1.4 fake")
    assert result.title == "T"
    assert sentinel.closed, (
        "parse_pdf_bytes did not close the fitz document on the "
        "success path."
    )