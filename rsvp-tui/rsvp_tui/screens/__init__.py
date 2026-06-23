"""Screen classes for the new RSVP TUI.

When ``RSVP_NEW_UI=1`` is set, the app routes to the screens in this
package instead of the legacy single-screen-with-CSS-class-toggling
behavior. The screens here all share the same ``FigureState`` model
and the same ``FigureRegistry`` singleton, so they stay in sync.

Public API:

* :class:`LibraryScreen` — list of imported books; selecting one
  pushes :class:`ReaderScreen`.
* :class:`ReaderScreen` — the reading surface. Mounts the active
  figure from the registry into a host container, exposes figure
  cycling and picker/palette actions, and emits messages back to the
  app for cross-cutting concerns (config persistence, library
  progress updates, toasts).
* :class:`FigurePickerScreen` — ``ModalScreen[str]`` that returns the
  selected figure id.
* :class:`CommandPaletteScreen` — ``ModalScreen[None]`` for fuzzy
  command dispatch.
* :class:`Messages` — Textual message types shared by the screens.
"""

from .messages import (
    FigureChanged,
    FigureStateAdvanced,
    FigureCompleted,
    ConfigChanged,
    BookOpened,
)
from .base import RSVPBaseScreen, new_ui_enabled
from .library_screen import LibraryScreen
from .reader_screen import ReaderScreen
from .figure_picker import FigurePickerScreen
from .command_palette import CommandPaletteScreen
from .settings_screen import SettingsScreen

__all__ = [
    "FigureChanged",
    "FigureStateAdvanced",
    "FigureCompleted",
    "ConfigChanged",
    "BookOpened",
    "RSVPBaseScreen",
    "new_ui_enabled",
    "LibraryScreen",
    "ReaderScreen",
    "FigurePickerScreen",
    "CommandPaletteScreen",
    "SettingsScreen",
]
