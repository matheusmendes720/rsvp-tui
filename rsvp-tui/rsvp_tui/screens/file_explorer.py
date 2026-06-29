"""FileExplorerScreen — file path input for opening any supported file.

Simple modal that accepts a file path and validates it.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

log = logging.getLogger(__name__)


# Supported file extensions for RSVP
SUPPORTED_EXTENSIONS = (".md", ".markdown", ".txt", ".epub", ".pdf")


class FileExplorerScreen(ModalScreen[str | None]):
    """File path input modal.

    Dismisses with the selected file path (str) or None if cancelled.
    """

    DEFAULT_CSS = """
    FileExplorerScreen {
        align: center middle;
    }
    FileExplorerScreen #file-input-container {
        width: 80;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    FileExplorerScreen #file-input {
        margin-bottom: 1;
    }
    FileExplorerScreen #error-msg {
        color: $error;
        display: none;
    }
    FileExplorerScreen #error-msg.visible {
        display: block;
    }
    FileExplorerScreen .buttons {
        layout: horizontal;
        align: center middle;
        height: auto;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel"),
        Binding("enter", "submit", "Open"),
    ]

    def __init__(
        self,
        initial_path: Path | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._initial_path = initial_path or Path.cwd()

    def compose(self) -> ComposeResult:
        """Compose the file path input."""
        with Vertical(id="file-input-container"):
            yield Label("Open File", id="title")
            yield Label(
                "Enter path to supported file (.md, .txt, .epub, .pdf)",
                id="hint",
            )
            yield Input(
                str(self._initial_path),
                placeholder="C:/path/to/file.md",
                id="file-input",
            )
            yield Static("", id="error-msg")
            with Vertical(classes="buttons"):
                yield Button("Cancel", variant="default", id="btn-cancel")
                yield Button("Open", variant="primary", id="btn-open")

    def on_mount(self) -> None:
        """Focus the input on mount."""
        self.query_one("#file-input", Input).focus()

    def action_dismiss(self, result: str | None = None) -> None:  # type: ignore[override]
        """Cancel and dismiss."""
        log.debug("FileExplorer: dismissed (escape)")
        self.dismiss(None)

    def action_submit(self) -> None:
        """Validate and submit the path."""
        log.debug("FileExplorer: submit action triggered")
        self._validate_and_submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-cancel":
            log.debug("FileExplorer: cancelled via button")
            self.dismiss(None)
        elif event.button.id == "btn-open":
            log.debug("FileExplorer: open button pressed")
            self._validate_and_submit()

    def _validate_and_submit(self) -> None:
        """Validate the path and dismiss if valid."""
        input_widget = self.query_one("#file-input", Input)
        path_str = input_widget.value.strip()
        error_msg = self.query_one("#error-msg", Static)

        if not path_str:
            log.debug("FileExplorer: empty path submitted")
            error_msg.update("Please enter a file path")
            error_msg.add_class("visible")
            return

        path = Path(path_str)

        # Expand user home
        if path_str.startswith("~"):
            path = Path(path_str.replace("~", str(Path.home()), 1))

        if not path.exists():
            log.debug("FileExplorer: file not found path=%s", path)
            error_msg.update(f"File not found: {path}")
            error_msg.add_class("visible")
            return

        if not path.is_file():
            log.debug("FileExplorer: not a file path=%s", path)
            error_msg.update(f"Not a file: {path}")
            error_msg.add_class("visible")
            return

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            log.debug(
                "FileExplorer: unsupported extension path=%s ext=%s",
                path,
                path.suffix,
            )
            error_msg.update(f"Unsupported format. Use: {', '.join(SUPPORTED_EXTENSIONS)}")
            error_msg.add_class("visible")
            return

        # Valid file!
        log.info("FileExplorer: file accepted path=%s", path)
        self.dismiss(str(path.resolve()))


__all__ = ["FileExplorerScreen", "SUPPORTED_EXTENSIONS"]
