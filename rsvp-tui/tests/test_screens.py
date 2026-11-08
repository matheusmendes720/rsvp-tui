"""Tests for the new screen system (Phase 2).

These tests focus on the *non-Textual* contracts of the screens:

* The picker/palette are pure data + small helpers, testable without
  spinning up a Textual ``App``.
* The base screen exposes config + registry lookup.
* The reader screen's figure-swap logic can be tested by mocking
  the figure out — we don't need to run Textual to verify it.

Full integration tests (``tests/e2e/``) cover the real app with
``App.run_test()``.
"""

from __future__ import annotations

import pytest

from rsvp_tui.figures import default_registry
from rsvp_tui.screens.base import new_ui_enabled
from rsvp_tui.screens.command_palette import (
    DEFAULT_COMMANDS,
    CommandPaletteScreen,
    PaletteCommand,
    _fuzzy_score,
)
from rsvp_tui.screens.messages import (
    BookOpened,
    ConfigChanged,
    FigureChanged,
    FigureCompleted,
    FigureStateAdvanced,
)

# ---- new_ui_enabled --------------------------------------------------------


def test_new_ui_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the env var, the gate is closed."""
    monkeypatch.delenv("RSVP_NEW_UI", raising=False)
    assert new_ui_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes", "on", " 1 "])
def test_new_ui_enabled_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """All these values enable the new UI."""
    monkeypatch.setenv("RSVP_NEW_UI", value)
    assert new_ui_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", ""])
def test_new_ui_disabled_values(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    """All these values keep the gate closed."""
    monkeypatch.setenv("RSVP_NEW_UI", value)
    assert new_ui_enabled() is False


# ---- Message dataclasses ---------------------------------------------------


def test_figure_changed_carries_ids() -> None:
    """FigureChanged holds prev/next ids."""
    m = FigureChanged(prev_id="word", next_id="chunk")
    assert m.prev_id == "word"
    assert m.next_id == "chunk"


def test_figure_state_advanced_default_book_id() -> None:
    """book_id is optional (None by default)."""
    m = FigureStateAdvanced(index=42)
    assert m.index == 42
    assert m.book_id is None


def test_figure_completed_default_book_id() -> None:
    m = FigureCompleted()
    assert m.book_id is None


def test_config_changed_default_keys_empty() -> None:
    m = ConfigChanged()
    assert m.keys == ()


def test_book_opened_default_id_empty() -> None:
    m = BookOpened()
    assert m.book_id == ""


# ---- Fuzzy scoring ---------------------------------------------------------


def test_fuzzy_score_empty_query_is_match() -> None:
    """Empty query matches everything with a low score."""
    assert _fuzzy_score("", "Next Figure") > 0


def test_fuzzy_score_exact_substring_high() -> None:
    """Consecutive matches score higher than scattered ones."""
    s_consecutive = _fuzzy_score("next", "Next Figure")
    s_scattered = _fuzzy_score("nx", "Next Figure")
    assert s_consecutive > s_scattered


def test_fuzzy_score_no_match_returns_zero() -> None:
    assert _fuzzy_score("xyzzy", "Next Figure") == 0


def test_fuzzy_score_case_insensitive() -> None:
    assert _fuzzy_score("NEXT", "next figure") > 0


# ---- Default command list -------------------------------------------------


def test_default_commands_have_unique_ids() -> None:
    """No two commands share an id (would break the palette callback)."""
    ids = [c.id for c in DEFAULT_COMMANDS]
    assert len(ids) == len(set(ids))


def test_default_commands_all_have_titles() -> None:
    """Every command has a non-empty title."""
    for c in DEFAULT_COMMANDS:
        assert c.title.strip()


def test_default_commands_contain_core_actions() -> None:
    """The core action set is always present."""
    ids = {c.id for c in DEFAULT_COMMANDS}
    for required in (
        "next_figure",
        "prev_figure",
        "toggle_play",
        "wpm_300",
        "theme_dark",
    ):
        assert required in ids


def test_palette_command_is_frozen() -> None:
    """PaletteCommand is a frozen dataclass — palette items don't mutate."""
    c = PaletteCommand(id="x", title="y")
    with pytest.raises(AttributeError):
        c.id = "z"  # type: ignore[misc]


# ---- CommandPaletteScreen direct construction ------------------------------


def test_palette_screen_accepts_custom_commands() -> None:
    """Custom command lists are honored."""
    custom = [PaletteCommand(id="hello", title="Say Hello")]
    screen = CommandPaletteScreen(commands=custom)
    assert screen._commands == custom


def test_palette_screen_defaults_to_default_commands() -> None:
    """When no commands are passed, the built-in list is used."""
    screen = CommandPaletteScreen()
    assert screen._commands is DEFAULT_COMMANDS


# ---- Default registry / figure metadata -----------------------------------


def test_default_registry_id_order_is_stable() -> None:
    """The registry order is documented; don't accidentally reorder."""
    expected = [
        "word",
        "chunk",
        "horizontal",
        "line",
        "bionic",
        "spritz",
        "pacer",
        "minimap",
        "stats",
    ]
    assert default_registry().ids() == expected


def test_each_registry_figure_has_metadata() -> None:
    """Every figure has the metadata the reader screen consumes."""
    for fig in default_registry().all():
        assert fig.id
        assert fig.name
        assert fig.description
        assert fig.default_params


# ---- ReaderScreen / message dispatch (no Textual runtime) -----------------


def test_figure_changed_message_dispatch_contract() -> None:
    """The FigureChanged message shape is what on_figure_changed expects."""
    msg = FigureChanged(prev_id="word", next_id="chunk")
    assert msg.next_id == "chunk"
    assert msg.prev_id == "word"


def test_figure_state_advanced_message_dispatch_contract() -> None:
    """A FigureStateAdvanced with index=100 is a save candidate."""
    msg = FigureStateAdvanced(index=100, book_id="b1")
    assert msg.index == 100
    assert msg.book_id == "b1"


def test_figure_completed_message_dispatch_contract() -> None:
    """A FigureCompleted with no book_id is a no-op (defensive)."""
    msg = FigureCompleted(book_id=None)
    assert msg.book_id is None


# ---- Importability smoke ---------------------------------------------------


def test_all_screen_modules_importable() -> None:
    """All 4 screen modules are importable from the package."""
    from rsvp_tui.screens import (  # noqa: F401
        CommandPaletteScreen,
        FigurePickerScreen,
        LibraryScreen,
        ReaderScreen,
    )


def test_messages_module_importable() -> None:
    """All message types are importable from the package."""
    from rsvp_tui.screens import (  # noqa: F401
        BookOpened,
        ConfigChanged,
        FigureChanged,
        FigureCompleted,
        FigureStateAdvanced,
    )


# ---- NotePanel id forwarding (regression) -----------------------------------


def test_note_panel_accepts_id_kwarg() -> None:
    """NotePanel.__init__ forwards ``id`` to its parent so the screen
    can ``query_one('#note-panel', NotePanel)`` during ``on_mount``.

    Regression: this used to raise ``TypeError: unexpected keyword
    argument 'id'`` because ``NotePanel.__init__`` did not accept
    ``**kwargs``. As a knock-on, ``ReaderScreen.on_mount`` raised
    ``NoMatches`` because the widget never received the id.
    """
    from rsvp_tui.widgets.note_panel import NotePanel

    # A dummy NoteManager — __init__ does not call into it.
    panel = NotePanel(note_manager=None, id="note-panel")  # type: ignore[arg-type]
    assert panel.id == "note-panel"


def test_note_panel_accepts_classes_kwarg() -> None:
    """NotePanel.__init__ forwards arbitrary kwargs (not just ``id``).

    Catches regressions where ``**kwargs`` is removed from
    ``NotePanel.__init__`` — this would silently break every caller
    that supplies ``id=`` or ``classes=``.
    """
    from rsvp_tui.widgets.note_panel import NotePanel

    panel = NotePanel(
        note_manager=None,  # type: ignore[arg-type]
        id="note-panel",
        classes="hidden",
    )
    assert panel.id == "note-panel"
    assert "hidden" in panel.classes


def test_reader_screen_compose_passes_id_to_note_panel() -> None:
    """ReaderScreen.compose yields a NotePanel with id 'note-panel'.

    Regression: the panel used to mount without an id, so
    ``on_mount`` then tried to ``query_one('#note-panel', NotePanel)``
    and raised ``NoMatches``.

    This is a static check of the compose method's source — the full
    Textual app lifecycle is exercised by the e2e suite under
    ``tests/e2e/``.
    """
    import inspect
    import re

    from rsvp_tui.screens import reader_screen

    source = inspect.getsource(reader_screen.ReaderScreen.compose)
    match = re.search(r"yield NotePanel\((.*?)\)", source, re.DOTALL)
    assert match, "ReaderScreen.compose no longer yields a NotePanel"
    block = match.group(1)
    assert 'id="note-panel"' in block, (
        "ReaderScreen.compose yield NotePanel(...) block must include "
        f'id="note-panel" so on_mount can resolve it; got:\n{block}'
    )


def test_reader_screen_on_mount_queries_note_panel() -> None:
    """ReaderScreen.on_mount calls ``query_one('#note-panel', NotePanel)``.

    Regression: this used to raise ``NoMatches`` because the NotePanel
    in compose was missing ``id="note-panel"``. The two conditions
    (compose passes id AND on_mount queries by id) must both hold —
    this test pins the on_mount side.
    """
    import inspect

    from rsvp_tui.screens import reader_screen
    from rsvp_tui.widgets.note_panel import NotePanel

    source = inspect.getsource(reader_screen.ReaderScreen.on_mount)
    assert 'query_one("#note-panel"' in source, (
        "ReaderScreen.on_mount must call query_one(\"#note-panel\", NotePanel)"
    )
    assert NotePanel.__name__ in source, (
        "ReaderScreen.on_mount must specify NotePanel as the widget class"
    )
