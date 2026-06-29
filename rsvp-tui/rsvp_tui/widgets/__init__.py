"""TUI widgets for RSVP.

PEP 562 lazy attributes
-----------------------
We use ``__getattr__`` to defer the import of every widget in
this package and to defer the deprecation warning that fires
when a legacy widget is actually requested.

Without this, simply importing ``rsvp_tui.widgets`` (or
referencing any of the names in ``__all__``) would trigger the
``ReaderDisplay`` and ``SettingsPanel`` deprecation warnings.
That made the warnings misleading — they fired during tests that
were never actually exercising the legacy widgets, just by
transitively importing the package.

With ``__getattr__`` in place, the deprecation warning fires
exactly once per process and only when the deprecated symbol
is actually used. The first access resolves and caches the
symbol on the module so subsequent uses are O(1).

Public API:

* ``ReaderDisplay`` — legacy alias for ``rsvp_tui.figures.word.WordFigure``.
* ``SettingsPanel`` — legacy alias for ``rsvp_tui.screens.settings_screen.SettingsScreen``.
* ``LibraryView``, ``NotePanel``, ``ProgressBar`` — current widgets,
  not deprecated.

New code should import directly from ``rsvp_tui.figures.*`` or
``rsvp_tui.widgets.*`` (only the non-deprecated names).
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - imported only by static checkers
    from .library_view import LibraryView
    from .navigation_panel import NavigationPanel
    from .note_panel import NotePanel
    from .progress_bar import ProgressBar

# Names that are NOT deprecated — always safe to import.
_NON_DEPRECATED = frozenset({"LibraryView", "NotePanel", "ProgressBar", "NavigationPanel"})

# Cache resolved attributes on the module to avoid re-resolving
# on every access (and re-warning on the deprecated ones).
_resolved: dict[str, object] = {}


def __getattr__(name: str) -> object:
    """PEP 562 lazy attribute access.

    * Non-deprecated widgets are imported normally on first
      access and cached.
    * Deprecated widgets (``ReaderDisplay``, ``SettingsPanel``)
      emit a one-shot warning per process and forward to the
      new home of the symbol.
    """
    # Fast path: already resolved.
    if name in _resolved:
        return _resolved[name]

    if name == "ReaderDisplay":
        warnings.warn(
            "rsvp_tui.widgets.ReaderDisplay is deprecated; "
            "use rsvp_tui.figures.word.WordFigure instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from ..figures.word import WordFigure

        _resolved[name] = WordFigure
        globals()[name] = WordFigure
        return WordFigure

    if name == "SettingsPanel":
        warnings.warn(
            "rsvp_tui.widgets.SettingsPanel is deprecated; "
            "use rsvp_tui.screens.settings_screen.SettingsScreen instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from ..screens.settings_screen import SettingsScreen

        _resolved[name] = SettingsScreen
        globals()[name] = SettingsScreen
        return SettingsScreen

    if name in _NON_DEPRECATED:
        # Import lazily so importing this package does NOT
        # pull textual widgets until the user actually asks
        # for one. Cheaper startup for any code that just
        # wants ``rsvp_tui.widgets`` to be importable.
        from . import library_view as _lv
        from . import navigation_panel as _navp
        from . import note_panel as _np
        from . import progress_bar as _pb

        mapping = {
            "LibraryView": _lv.LibraryView,
            "NotePanel": _np.NotePanel,
            "ProgressBar": _pb.ProgressBar,
            "NavigationPanel": _navp.NavigationPanel,
        }
        cls = mapping.get(name)
        if cls is None:
            raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
        _resolved[name] = cls
        globals()[name] = cls
        return cls

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(
        list(globals().keys()) + list(_NON_DEPRECATED) + ["ReaderDisplay", "SettingsPanel"]
    )


__all__ = [
    "ReaderDisplay",  # deprecated
    "LibraryView",
    "NotePanel",
    "ProgressBar",
    "NavigationPanel",
    "SettingsPanel",  # deprecated
]
