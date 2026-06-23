"""FigurePicker — modal screen for choosing a figure.

Returns the selected figure id (str) via ``dismiss()``, or ``None``
if the user dismisses with escape.

Why a modal screen: it needs to take input focus away from the
ReaderScreen, present a focused list, and return a single result.
That's exactly what ``ModalScreen[ResultType]`` is for. Building it
as a separate widget that the ReaderScreen ``push_screen``-es means
the picker survives a figure swap (no parent state pollution).
"""

from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static

from ..figures import default_registry
from .base import RSVPBaseScreen


class FigurePickerScreen(ModalScreen[Optional[str]]):
    """Pick a figure from the registry.

    Use ``push_screen(FigurePickerScreen(), callback)``; the callback
    receives the figure id (str) or ``None`` if dismissed.
    """

    DEFAULT_CSS = """
    FigurePickerScreen {
        align: center middle;
    }
    FigurePickerScreen > Vertical {
        width: 60;
        height: auto;
        max-height: 80%;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    FigurePickerScreen Label#picker-title {
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    FigurePickerScreen ListView {
        height: auto;
        max-height: 20;
    }
    FigurePickerScreen ListItem {
        padding: 0 1;
    }
    FigurePickerScreen .picker-desc {
        color: $text-muted;
    }
    FigurePickerScreen .picker-key {
        color: $accent;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_picker", "Cancel"),
    ]

    def __init__(self, current_id: str = "") -> None:
        super().__init__()
        self._current_id = current_id

    def compose(self) -> ComposeResult:
        """Compose the picker UI.

        We render a ``ListView`` with one ``ListItem`` per figure. The
        first line of each item is the figure name (and keybinding),
        the second is its description. The currently-active figure
        is highlighted so the user has a sense of \"where I am\".
        """
        with Vertical():
            yield Label("Choose a Figure", id="picker-title")
            items: list[ListItem] = []
            for fig in default_registry().all():
                marker = "●" if fig.id == self._current_id else "○"
                label_text = f"{marker} [{fig.default_keybinding}] {fig.name}"
                item = ListItem(
                    Static(label_text),
                    Static(fig.description, classes="picker-desc"),
                    id=f"fig-{fig.id}",
                )
                items.append(item)
            yield ListView(*items, id="picker-list")

    def on_mount(self) -> None:
        """Focus the list and pre-select the current figure."""
        lv = self.query_one("#picker-list", ListView)
        if self._current_id:
            for idx, fig in enumerate(default_registry().all()):
                if fig.id == self._current_id:
                    lv.index = idx
                    break
        lv.focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Resolve the chosen list-item id to a figure id and dismiss."""
        item_id = event.item.id or ""
        if item_id.startswith("fig-"):
            self.dismiss(item_id[len("fig-"):])

    def action_dismiss_picker(self) -> None:
        """Escape: dismiss with no result."""
        self.dismiss(None)


__all__ = ["FigurePickerScreen"]
