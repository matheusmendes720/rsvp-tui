"""Assert every BINDINGS entry points at a real handler.

Two failure modes this guards against:

1. **Orphan ``app.*`` bindings** — a screen declares
   ``Binding("space", "app.toggle_play", ...)`` but the App class
   never defines ``action_toggle_play``. Pressing the key does
   nothing. Silent no-op, terrible UX.
2. **Orphan screen-local bindings** — same shape, but the action
   targets the screen itself and the ``action_*`` method is missing.

Textual's action resolution rules:
  * ``"app.<name>"``   → dispatched to ``App.action_<name>``
  * ``"<name>"``        → dispatched to ``<self>.action_<name>``

For each binding we walk the MRO of the appropriate target class and
check the action method exists. We deliberately do not instantiate
the screens — many require config / DB / TUI runtime; we only need
the class objects.
"""

from __future__ import annotations

from typing import Iterable

import pytest

from rsvp_tui.app import RSVPApp
from rsvp_tui.screens.base import RSVPBaseScreen
from rsvp_tui.screens.command_palette import CommandPaletteScreen
from rsvp_tui.screens.figure_picker import FigurePickerScreen
from rsvp_tui.screens.file_explorer import FileExplorerScreen
from rsvp_tui.screens.library_screen import LibraryScreen
from rsvp_tui.screens.reader_screen import ReaderScreen
from rsvp_tui.screens.settings_screen import SettingsScreen


# Each entry: (class, expected-target-class for the binding lookup).
# Default target is the class itself (for screen-local actions).
# ``App`` is used for ``app.*`` actions; ``RSVPBaseScreen`` is included
# because the base declares its own BINDINGS.
SCREENS_WITH_APP_ACTIONS: list[tuple[type, type]] = [
    (RSVPApp, RSVPApp),
    (RSVPBaseScreen, RSVPApp),
    (ReaderScreen, RSVPApp),
    (LibraryScreen, RSVPApp),
    (SettingsScreen, RSVPApp),
    (FileExplorerScreen, RSVPApp),
    (CommandPaletteScreen, RSVPApp),
    (FigurePickerScreen, RSVPApp),
]


def _iter_bindings(bindings_obj: object) -> Iterable[tuple[str, str]]:
    """Yield (key, action) pairs from a BINDINGS list.

    Textual's ``Binding`` objects expose ``.key`` and ``.action``;
    older code uses plain tuples ``(key, action, description)``.
    """
    for entry in bindings_obj or []:
        if hasattr(entry, "key") and hasattr(entry, "action"):
            yield (entry.key, entry.action)
        elif isinstance(entry, (tuple, list)) and len(entry) >= 2:
            yield (str(entry[0]), str(entry[1]))


def _has_action(cls: type, action: str) -> bool:
    """Return True if ``cls`` (or any base) defines ``action_<action>``."""
    method_name = f"action_{action}"
    for klass in cls.__mro__:
        if method_name in klass.__dict__:
            return True
    return False


def _collect_mismatches(
    cls: type, target: type
) -> list[tuple[str, str, str]]:
    """Return [(key, action, reason), ...] for every orphan binding."""
    problems: list[tuple[str, str, str]] = []
    for key, action in _iter_bindings(getattr(cls, "BINDINGS", None)):
        if not action:
            problems.append((key, action, "empty action name"))
            continue
        if action.startswith("app."):
            sub = action[len("app."):]
            if not _has_action(target, sub):
                problems.append(
                    (key, action, f"{target.__name__}.action_{sub} not found")
                )
        else:
            if not _has_action(cls, action):
                problems.append(
                    (key, action, f"{cls.__name__}.action_{action} not found")
                )
    return problems


@pytest.mark.parametrize(
    "cls,target",
    SCREENS_WITH_APP_ACTIONS,
    ids=lambda c: c.__name__,
)
def test_all_bindings_resolve_to_real_handlers(
    cls: type, target: type
) -> None:
    """Every binding on every screen must point at a real action_*
    method on the appropriate target class (App for app.*, self for
    local)."""
    mismatches = _collect_mismatches(cls, target)
    assert not mismatches, (
        f"{cls.__name__} has orphan bindings — they would silently "
        f"no-op at runtime:\n"
        + "\n".join(
            f"  key={k!r} action={a!r}  →  {reason}"
            for k, a, reason in mismatches
        )
    )


def test_reader_screen_bindings_summary() -> None:
    """Sanity: ReaderScreen should expose the core playback hotkeys.

    If a future refactor accidentally drops one of these, this test
    flags it immediately.
    """
    actions = {
        a for _, a in _iter_bindings(getattr(ReaderScreen, "BINDINGS", None))
    }
    expected = {
        "app.toggle_play",
        "app.next_figure",
        "app.prev_figure",
        "app.open_picker",
        "app.open_palette",
        "app.open_file_explorer",
        "app.prev_word",
        "app.next_word",
        "app.increase_speed",
        "app.decrease_speed",
        "app.jump_start",
        "app.jump_end",
    }
    missing = expected - actions
    assert not missing, f"ReaderScreen is missing core bindings: {sorted(missing)}"
