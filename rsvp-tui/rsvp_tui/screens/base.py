"""Base screen with shared CSS and keybinding helpers.

All new screens inherit from ``RSVPBaseScreen`` so they pick up the
same dark-theme look, the same header/footer handling, and the same
helper for looking up figure ids in the registry. Keeping the common
bits in one place stops each screen from re-declaring the same
bindings and CSS.
"""

from __future__ import annotations

import logging
import os

from textual.binding import Binding
from textual.screen import Screen

from ..figures import default_registry
from ..keybindings import resolve
from ..models import Config

log = logging.getLogger(__name__)


def new_ui_enabled() -> bool:
    """Whether the new Screen-based UI is active.

    Gated on the ``RSVP_NEW_UI`` environment variable. ``"1"`` and
    ``"true"`` (case-insensitive) enable; anything else falls back to
    the legacy single-screen behavior. Exposed as a function so tests
    can monkeypatch it.
    """
    val = os.environ.get("RSVP_NEW_UI", "").strip().lower()
    return val in {"1", "true", "yes", "on"}


class RSVPBaseScreen(Screen):
    """Common base for the new screens.

    Why a base class: every screen needs the same Header/Footer
    treatment, the same dark-theme default, and the same key for
    \"go back\" (``escape``). The base keeps that consistent.
    """

    DEFAULT_CSS = """
    RSVPBaseScreen {
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, config: Config | None = None) -> None:
        super().__init__()
        self._config = config
        log.debug("screen.init: %s", type(self).__name__)

    @property
    def config(self) -> Config:
        """Lazily-resolved config.

        Reading from disk is expensive enough that we don't want to
        do it on import; instead the screen picks it up on first
        access. The app sets ``self._config`` at push time when it
        already has a config in hand.
        """
        if self._config is None:
            self._config = Config.load()
        return self._config

    def resolve_key(self, action: str) -> str:
        """Resolve a key for ``action`` honoring the user's overrides."""
        return resolve(action, self.config.keybindings)

    def figure_registry(self):
        """The figure registry used by this screen."""
        return default_registry()


__all__ = ["RSVPBaseScreen", "new_ui_enabled"]
