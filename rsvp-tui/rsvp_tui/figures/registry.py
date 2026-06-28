"""Registry of all available figures.

Figures register themselves with a singleton ``FigureRegistry`` at
import time. The ``ReaderScreen`` queries the registry to know what
to mount, and the ``FigurePicker`` uses the same registry to render
the picker list. This means adding a new figure is a two-line change
in the registry initializer.

Why a registry: prior to Phase 1 there was only one widget, so there
was nothing to register. With eight figures, the registry becomes the
single source of truth for "what figures exist, in what order, and
under what keybindings".

Why a singleton: the ``ReaderScreen`` and the figure picker need to
see the *same* registry, otherwise the picker would offer figures
the screen doesn't know how to mount. We use a module-level
``default_registry()`` function so tests can build their own isolated
registry via ``FigureRegistry()``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from .base import Figure

log = logging.getLogger(__name__)


class FigureRegistry:
    """Holds the available figures in a stable order.

    The registry is a thin wrapper around an ordered dict. Insertion
    order is the display order in the figure picker and the order in
    which ``next()`` / ``previous()`` cycle.
    """

    def __init__(self) -> None:
        self._figs: dict[str, Figure] = {}

    # ---- Registration ---------------------------------------------------

    def register(self, fig: Figure) -> None:
        if not fig.id:
            raise ValueError("figure must have a non-empty id")
        log.debug("FigureRegistry: registered figure id=%s name=%r", fig.id, fig.name)
        self._figs[fig.id] = fig

    def register_all(self, figs: Iterable[Figure]) -> None:
        for fig in figs:
            self.register(fig)

    # ---- Queries --------------------------------------------------------

    def all(self) -> list[Figure]:
        return list(self._figs.values())

    def ids(self) -> list[str]:
        return list(self._figs.keys())

    def get(self, fig_id: str) -> Figure | None:
        return self._figs.get(fig_id)

    def __contains__(self, fig_id: object) -> bool:
        return fig_id in self._figs

    def __len__(self) -> int:
        return len(self._figs)

    # ---- Navigation -----------------------------------------------------

    def by_index(self, index: int) -> Figure:
        if not self._figs:
            raise IndexError("registry is empty")
        ids = list(self._figs.keys())
        return self._figs[ids[index % len(ids)]]

    def index_of(self, fig_id: str) -> int:
        ids = list(self._figs.keys())
        if fig_id not in ids:
            raise KeyError(fig_id)
        return ids.index(fig_id)

    def next(self, current_id: str) -> Figure:
        ids = list(self._figs.keys())
        if not ids:
            raise IndexError("registry is empty")
        if current_id not in ids:
            return self._figs[ids[0]]
        idx = (ids.index(current_id) + 1) % len(ids)
        return self._figs[ids[idx]]

    def previous(self, current_id: str) -> Figure:
        ids = list(self._figs.keys())
        if not ids:
            raise IndexError("registry is empty")
        if current_id not in ids:
            return self._figs[ids[0]]
        idx = (ids.index(current_id) - 1) % len(ids)
        return self._figs[ids[idx]]


# ---- Module-level default registry ------------------------------------------


_default: FigureRegistry | None = None


def default_registry() -> FigureRegistry:
    """Return the process-wide default registry, building it on first call."""
    global _default
    if _default is None:
        _default = FigureRegistry()
        # Importing here avoids a circular import: figures import
        # Figure from .base, and the registry is the only thing
        # that wires them up.
        from . import bionic, chunk, line, minimap, pacer, spritz, stats, word

        _default.register_all(
            [
                word.WordFigure(),
                chunk.ChunkFigure(),
                line.LineFigure(),
                bionic.BionicFigure(),
                spritz.SpritzFigure(),
                pacer.PacerFigure(),
                minimap.MiniMapFigure(),
                stats.StatsFigure(),
            ]
        )
    return _default


def reset_default_registry() -> None:
    """Drop the cached default registry. Test helper."""
    global _default
    _default = None


__all__ = [
    "FigureRegistry",
    "default_registry",
    "reset_default_registry",
]
