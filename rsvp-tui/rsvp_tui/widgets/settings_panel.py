"""Backward-compatible shim for the legacy SettingsPanel.

The new modal ``SettingsScreen`` (in
``rsvp_tui.screens.settings_screen``) replaces this widget. The
shim exists so the import path keeps working during the migration
and any test that imports ``SettingsPanel`` gets a clear
deprecation warning instead of a broken import.

If you're new to the codebase, prefer importing from
``rsvp_tui.screens.settings_screen`` directly.
"""

from __future__ import annotations

import warnings


def __getattr__(name: str):
    """Lazy-attribute shim: import the new screen on demand.

    Using ``__getattr__`` (PEP 562) lets us forward ``SettingsPanel``
    to the new ``SettingsScreen`` without importing textual at
    module load time. That keeps the legacy import path cheap and
    avoids pulling the whole screen machinery into apps that only
    need a config object.
    """
    if name == "SettingsPanel":
        warnings.warn(
            "rsvp_tui.widgets.SettingsPanel is deprecated; "
            "use rsvp_tui.screens.settings_screen.SettingsScreen instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        from ..screens.settings_screen import SettingsScreen

        return SettingsScreen
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["SettingsPanel"]
