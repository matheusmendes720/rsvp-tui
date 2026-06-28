"""CommandPalette — fuzzy-matched command dispatcher.

Returns ``None`` (dismissed) or the action name (str) the user
selected. The ReaderScreen maps action names to actual operations
(next figure, wpm 450, set theme light, etc.).

Why a custom palette instead of Textual's built-in
``CommandPalette``: we want commands that mutate ``Config`` (e.g.
``wpm 450``) in addition to actions like ``next_figure``. The
built-in palette only does action lookups. Building our own keeps
the contract simple — "you selected 'next_figure'" — and the
dispatcher on the caller side decides what to do.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListItem, ListView, Static

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaletteCommand:
    """A single command in the palette.

    Attributes:
        id: Machine-readable name. The caller maps this to a real
            operation (``"next_figure"`` → ``ReaderScreen._swap_figure``).
        title: Human-readable label shown in the list.
        hint: Optional short hint (e.g. \"wpm 450\"). Shown dimmed.
    """

    id: str
    title: str
    hint: str = ""


# Static command list. Adding a new command is a one-line change.
# Order is the display order when the palette opens.
DEFAULT_COMMANDS: list[PaletteCommand] = [
    PaletteCommand("next_figure", "Next Figure", "n"),
    PaletteCommand("prev_figure", "Previous Figure", "shift+n"),
    PaletteCommand("open_picker", "Open Figure Picker", "ctrl+g"),
    PaletteCommand("toggle_play", "Play / Pause", "space"),
    PaletteCommand("jump_start", "Jump to Start", "home"),
    PaletteCommand("jump_end", "Jump to End", "end"),
    PaletteCommand("increase_speed", "Increase WPM (+25)", "up"),
    PaletteCommand("decrease_speed", "Decrease WPM (-25)", "down"),
    PaletteCommand("wpm_300", "Set WPM = 300", ""),
    PaletteCommand("wpm_400", "Set WPM = 400", ""),
    PaletteCommand("wpm_500", "Set WPM = 500", ""),
    PaletteCommand("wpm_600", "Set WPM = 600", ""),
    PaletteCommand("theme_dark", "Theme: Dark", ""),
    PaletteCommand("theme_light", "Theme: Light", ""),
    PaletteCommand("theme_solarized", "Theme: Solarized", ""),
    PaletteCommand("toggle_focus", "Toggle Focus Mode", "f"),
    PaletteCommand("add_note", "Add Note at Position", "n"),
    PaletteCommand("show_help", "Show Help", "?"),
    # Navigation commands
    PaletteCommand("open_file", "Open File...", "ctrl+o"),
    PaletteCommand("next_chapter", "Next Chapter", "]"),
    PaletteCommand("prev_chapter", "Previous Chapter", "["),
    PaletteCommand("go_to_chapter", "Go to Chapter...", "g c"),
    PaletteCommand("go_to_page", "Go to Page...", "g p"),
    PaletteCommand("toggle_navigation", "Toggle Navigation Panel", "ctrl+n"),
    PaletteCommand("toggle_note_panel", "Toggle Note Panel", "ctrl+b"),
]


def _fuzzy_score(query: str, target: str) -> int:
    """Return a relevance score for ``query`` matching ``target``.

    Higher is better. ``0`` means no match. We do a simple subsequence
    match: each char of ``query`` must appear in ``target`` in order
    (case-insensitive), and the score rewards tight matches.

    Good enough for ~20 commands; if the list grows we can swap in
    a proper fuzzy library later.
    """
    if not query:
        return 1
    q = query.lower()
    t = target.lower()
    qi = 0
    score = 0
    last_pos = -1
    for i, ch in enumerate(t):
        if qi >= len(q):
            break
        if ch == q[qi]:
            # Reward consecutive matches and early matches.
            if last_pos == i - 1:
                score += 5
            else:
                score += 1
            if i < 3:
                score += 2
            last_pos = i
            qi += 1
    if qi < len(q):
        return 0
    # Shorter targets rank higher when the score is tied.
    return score * 100 - len(target)


class CommandPaletteScreen(ModalScreen[str | None]):
    """Fuzzy command palette.

    Dismisses with the command id (str) the user selected, or
    ``None`` if cancelled.
    """

    DEFAULT_CSS = """
    CommandPaletteScreen {
        align: center top;
    }
    CommandPaletteScreen > Vertical {
        width: 80;
        height: auto;
        max-height: 80%;
        margin-top: 1;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    CommandPaletteScreen Input {
        margin-bottom: 1;
    }
    CommandPaletteScreen ListView {
        height: auto;
        max-height: 18;
    }
    CommandPaletteScreen .cmd-hint {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_palette", "Cancel"),
    ]

    def __init__(self, commands: list[PaletteCommand] | None = None) -> None:
        super().__init__()
        self._commands = commands or DEFAULT_COMMANDS

    def compose(self) -> ComposeResult:
        """Compose the palette: title, input, list of commands."""
        with Vertical():
            yield Label("Command Palette", id="palette-title")
            yield Input(placeholder="Type to filter…", id="palette-input")
            yield ListView(id="palette-list")

    def on_mount(self) -> None:
        """Render initial command list and focus the input."""
        log.debug("CommandPalette: opened (on_mount)")
        self._refresh_list("")
        self.query_one("#palette-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Filter the list as the user types."""
        if event.input.id == "palette-input":
            log.debug("CommandPalette: input changed query=%r", event.value)
            self._refresh_list(event.value)

    def _refresh_list(self, query: str) -> None:
        """Re-render the list filtered by ``query``."""
        scored = []
        for cmd in self._commands:
            score = _fuzzy_score(query, cmd.title)
            if score > 0:
                scored.append((score, cmd))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        lv = self.query_one("#palette-list", ListView)
        lv.clear()
        for _, cmd in scored[:50]:
            label = cmd.title
            if cmd.hint:
                label = f"{label}  [dim]{cmd.hint}[/]"
            lv.append(ListItem(Static(label), id=f"cmd-{cmd.id}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Return the chosen command id."""
        item_id = event.item.id or ""
        if item_id.startswith("cmd-"):
            cmd_id = item_id[len("cmd-") :]
            log.info("CommandPalette: command selected id=%s", cmd_id)
            self.dismiss(cmd_id)
        else:
            log.debug("CommandPalette: no command matched item_id=%r", item_id)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Enter: pick the first remaining item (if any)."""
        lv = self.query_one("#palette-list", ListView)
        if lv.children:
            first = lv.children[0]
            item_id = first.id or ""
            if item_id.startswith("cmd-"):
                cmd_id = item_id[len("cmd-") :]
                log.info("CommandPalette: submitted first match id=%s", cmd_id)
                self.dismiss(cmd_id)
                return
        log.debug("CommandPalette: submitted with no matches")
        self.dismiss(None)

    def action_dismiss_palette(self) -> None:
        """Escape: dismiss without selecting."""
        log.debug("CommandPalette: dismissed (escape)")
        self.dismiss(None)


__all__ = [
    "PaletteCommand",
    "DEFAULT_COMMANDS",
    "CommandPaletteScreen",
]
