"""ReaderScreen — the reading surface in the new UI.

Hosts the active figure (one of the 8 in ``default_registry()``) in
a static container, owns the per-figure transport, and translates
the figure's reactive state into app-level messages. The
single-screen app used a single boolean to switch between
``enable_orp`` and ``focus_mode``; this screen can mount any of the
8 figures on the fly without losing position.

Why a separate screen: the figure may need the full viewport, and
the figure's own widgets (sparkline, pacer dots, etc.) need to
draw relative to its parent. The screen is the parent, and the
figure is mounted inside a ``Static(id="figure-host")`` container.
"""

from __future__ import annotations

import logging

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from ..figures import Figure, FigureState, default_registry
from ..logging_ import telemetry
from ..models import Book, Config
from ..widgets import NavigationPanel, NotePanel, ProgressBar
from .base import RSVPBaseScreen
from .command_palette import CommandPaletteScreen
from .figure_picker import FigurePickerScreen
from .file_explorer import FileExplorerScreen
from .messages import (
    ConfigChanged,
    FigureChanged,
    FigureCompleted,
    FigureStateAdvanced,
    NavigationJump,
)

log = logging.getLogger(__name__)


class ReaderScreen(RSVPBaseScreen):
    """The reading surface.

    Composes a ``#figure-host`` container, a progress bar, a note
    panel, and a footer. All transport is delegated to the mounted
    figure; this screen just orchestrates mounting and swap.
    """

    DEFAULT_CSS = """
    ReaderScreen {
        layout: vertical;
    }
    ReaderScreen #reader-row {
        height: 1fr;
    }
    ReaderScreen #figure-host {
        width: 1fr;
        height: 100%;
    }
    ReaderScreen #note-panel {
        width: 35;
        height: 100%;
    }
    ReaderScreen #nav-panel {
        width: 30;
        height: 100%;
    }
    ReaderScreen #progress-bar {
        height: 3;
    }
    ReaderScreen #status-bar {
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("space", "app.toggle_play", "Play/Pause"),
        Binding("n", "app.next_figure", "Next Fig"),
        Binding("shift+n", "app.prev_figure", "Prev Fig"),
        Binding("ctrl+g", "app.open_picker", "Picker"),
        Binding("ctrl+p", "app.open_palette", "Palette"),
        Binding("ctrl+o", "app.open_file_explorer", "Open"),
        Binding("left", "app.prev_word", "Prev"),
        Binding("right", "app.next_word", "Next"),
        Binding("up", "app.increase_speed", "Faster"),
        Binding("down", "app.decrease_speed", "Slower"),
        Binding("home", "app.jump_start", "Start"),
        Binding("end", "app.jump_end", "End"),
        Binding("f", "app.toggle_focus", "Focus"),
        Binding("1", "app.figure_1", "Word"),
        Binding("2", "app.figure_2", "Chunk"),
        Binding("3", "app.figure_3", "Line"),
        Binding("4", "app.figure_4", "Bionic"),
        Binding("5", "app.figure_5", "Spritz"),
        Binding("6", "app.figure_6", "Pacer"),
        Binding("7", "app.figure_7", "Mini"),
        Binding("8", "app.figure_8", "Stats"),
        # Navigation bindings
        Binding("[", "app.prev_chapter", "Prev Ch"),
        Binding("]", "app.next_chapter", "Next Ch"),
        Binding("ctrl+n", "app.toggle_navigation", "Nav"),
    ]

    focus_mode: reactive[bool] = reactive(False)
    current_figure_id: reactive[str] = reactive("")

    def __init__(
        self,
        book: Book,
        words: list[str],
        config: Config | None = None,
    ) -> None:
        super().__init__(config=config)
        self._book = book
        self._words: tuple[str, ...] = tuple(words)
        self._chapters = book.chapters
        self._figure: Figure | None = None
        self._progress: ProgressBar | None = None
        self._note_panel: NotePanel | None = None
        self._nav_panel: NavigationPanel | None = None
        # Where the user is. Updated by the figure's reactive
        # ``word_index`` observer; we mirror it for transport
        # actions (next/prev) that the figure also exposes.
        self._index: int = book.current_word_index

    # ---- Compose ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        """Compose header, reader row, progress, status, footer."""
        yield Header(show_clock=True)
        with Horizontal(id="reader-row"):
            with Vertical():
                yield Static(id="figure-host")
                yield ProgressBar(id="progress-bar")
            yield NotePanel(
                self.app.note_manager,  # type: ignore[attr-defined]
                on_note_added=self._on_note_added,
                id="note-panel",
            )
            # Navigation panel (shown based on config)
            if self.config.show_navigation_panel:
                yield NavigationPanel(
                    self._book,
                    page_size=self.config.page_size,
                    id="nav-panel",
                )
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Mount the initial figure and wire up progress/notes."""
        self.title = "RSVP Speed Reader"
        self.sub_title = self._book.title

        self._progress = self.query_one("#progress-bar", ProgressBar)
        self._progress.update_progress(self._book.current_word_index, len(self._words))
        self._progress.set_wpm(self.config.default_wpm)

        self._note_panel = self.query_one("#note-panel", NotePanel)
        self._note_panel.set_position(self._book.id, self._book.current_word_index)

        # Get navigation panel if it exists
        try:
            self._nav_panel = self.query_one("#nav-panel", NavigationPanel)
        except NoMatches:
            self._nav_panel = None

        # Mount the figure defined by the config. If the config
        # points at a figure that doesn't exist (e.g. user edited
        # the file), we fall back to "word" — never crash.
        target_id = self.config.figure_id or "word"
        registry = default_registry()
        if registry.get(target_id) is None:
            log.warning(
                "Config figure_id %r is not registered; falling back to 'word'",
                target_id,
            )
            target_id = "word"
        self.current_figure_id = target_id
        self._mount_figure(target_id, initial=True)

    # ---- Figure mounting -------------------------------------------------

    def _mount_figure(self, fig_id: str, *, initial: bool = False) -> None:
        """Mount ``fig_id`` into the figure-host.

        The old figure is unmounted and paused (mandatory; otherwise
        its timer would still tick and advance an index it no longer
        owns). The new figure receives a ``FigureState`` snapshot
        capturing the current word_index, wpm, playback, and the
        per-figure params from config.
        """
        registry = default_registry()
        new_fig = registry.get(fig_id)
        if new_fig is None:
            return

        # Pause the old figure FIRST. Cancels its timer.
        if self._figure is not None:
            try:
                self._figure.pause()
            except Exception as exc:
                # If pause fails, the old figure's timer might still
                # be ticking. We log and continue; the worst case is
                # one extra word advance before the figure is gone.
                log.warning("Figure pause() raised: %s", exc, exc_info=True)
            try:
                self._figure.remove()
            except NoMatches:
                # Already removed by something else — fine.
                pass
            except Exception as exc:
                # If remove() fails for any other reason, the old
                # figure may still be in the DOM. Log so this is
                # debuggable, but don't crash the swap.
                log.warning("Figure remove() raised: %s", exc, exc_info=True)

        host = self.query_one("#figure-host", Static)
        # Apply per-figure params from config (if any).
        params = self.config.figure_params.get(fig_id) or {}
        state = FigureState(
            words=self._words,
            word_index=self._index,
            wpm=self.config.default_wpm,
            is_playing=False,
            punctuation_multiplier=self.config.punctuation_multiplier,
            pause_chars=tuple(self.config.pause_chars),
            comma_pause_multiplier=self.config.comma_pause_multiplier,
            on_word_change=self._on_word_changed,
            on_complete=self._on_completed,
        )
        new_fig = type(new_fig)(state, params=params, id=f"figure-{fig_id}")
        host.mount(new_fig)
        self._figure = new_fig

        prev_id = None if initial else self.current_figure_id
        self.current_figure_id = fig_id
        self.post_message(FigureChanged(prev_id=prev_id, next_id=fig_id))

        # If the previous state was playing, resume.
        # (We don't auto-resume on initial mount — user presses space.)

    def _swap_figure(self, new_id: str) -> None:
        """Swap to ``new_id``, preserving position and playback."""
        if new_id == self.current_figure_id:
            return
        was_playing = bool(self._figure and self._figure.is_playing)
        prev_id = self.current_figure_id or None
        telemetry.figure_swap(from_id=prev_id, to_id=new_id)
        self._mount_figure(new_id)
        if was_playing and self._figure is not None:
            self._figure.start()

    # ---- Reactive observers ---------------------------------------------

    def _on_word_changed(self, index: int) -> None:
        """The figure's reactive ``word_index`` fired.

        We mirror it locally for transport actions, update the
        progress bar and note panel, and emit ``FigureStateAdvanced``
        so the app can persist library progress.
        """
        self._index = index
        if self._progress is not None:
            self._progress.update_progress(index, len(self._words))
        if self._note_panel is not None:
            self._note_panel.set_position(self._book.id, index)
        if self._nav_panel is not None:
            self._nav_panel.update_position(index)
        self.post_message(FigureStateAdvanced(index=index, book_id=self._book.id))

    def _on_completed(self) -> None:
        """Tell the app the user finished this book."""
        self.post_message(FigureCompleted(book_id=self._book.id))

    def on_config_changed(self, message: ConfigChanged) -> None:
        """React to live config changes (WPM, theme, etc.).

        The settings screen writes through ``ConfigManager.update``
        and posts a ``ConfigChanged`` message. The ReaderScreen
        picks it up and pushes the new values to the active figure
        without remounting it, so the user's position is preserved.
        """
        # Refresh our in-memory config from the manager (the
        # settings screen wrote through it).
        from ..managers.config_manager import ConfigManager

        manager = ConfigManager()
        fresh = manager.load()
        # Update the relevant fields on our cached config object.
        for field in (
            "default_wpm",
            "enable_orp",
            "focus_mode",
            "show_progress_bar",
            "show_context_words",
            "punctuation_multiplier",
            "pause_on_punctuation",
            "pause_chars",
            "comma_pause_multiplier",
            "theme",
            "figure_id",
            "figure_params",
        ):
            if hasattr(fresh, field):
                setattr(self.config, field, getattr(fresh, field))

        # Apply to active figure without remounting.
        if self._figure is not None and (
            "default_wpm" in message.keys or "wpm_step" in message.keys
        ):
            self._figure.set_wpm(self.config.default_wpm)
            if self._progress is not None:
                self._progress.set_wpm(self.config.default_wpm)

    # ---- Actions ---------------------------------------------------------

    def action_toggle_play(self) -> None:
        """Space: play / pause."""
        if self._figure is not None:
            self._figure.toggle()

    def action_next_word(self) -> None:
        """Right arrow: advance one word (no timer)."""
        if self._figure is not None:
            self._figure.next_word()

    def action_prev_word(self) -> None:
        """Left arrow: go back one word."""
        if self._figure is not None:
            self._figure.prev_word()

    def action_increase_speed(self) -> None:
        """Up arrow: +25 WPM."""
        if self._figure is not None:
            self._figure.increase_speed()
            if self._progress is not None:
                self._progress.set_wpm(self._figure.wpm)

    def action_decrease_speed(self) -> None:
        """Down arrow: -25 WPM."""
        if self._figure is not None:
            self._figure.decrease_speed()
            if self._progress is not None:
                self._progress.set_wpm(self._figure.wpm)

    def action_jump_start(self) -> None:
        """Home: jump to first word."""
        if self._figure is not None:
            self._figure.jump_to(0)

    def action_jump_end(self) -> None:
        """End: jump to last word."""
        if self._figure is not None and self._words:
            self._figure.jump_to(len(self._words) - 1)

    def action_toggle_focus(self) -> None:
        """F: hide header/footer/progress for distraction-free reading."""
        self.focus_mode = not self.focus_mode
        if self.focus_mode:
            self.add_class("focus-mode")
        else:
            self.remove_class("focus-mode")

    def action_prev_chapter(self) -> None:
        """[: navigate to the previous chapter."""
        self._navigate_chapter(-1)

    def action_next_chapter(self) -> None:
        """]: navigate to the next chapter."""
        self._navigate_chapter(1)

    def action_toggle_navigation(self) -> None:
        """Ctrl+N: toggle the navigation panel visibility."""
        if self._nav_panel is not None:
            if self._nav_panel.display:
                self._nav_panel.hide()
            else:
                self._nav_panel.show()

    def _navigate_chapter(self, delta: int) -> None:
        """Navigate by delta chapters (negative = prev, positive = next)."""
        if self._nav_panel is None or not self._chapters:
            return
        current = self._book.current_chapter_index
        new_index = current + delta
        if 0 <= new_index < len(self._chapters):
            telemetry.chapter_nav(
                book_id=self._book.id,
                from_chapter=current,
                to_chapter=new_index,
            )
            self._nav_panel.jump_to_chapter(new_index)

    def on_navigation_jump(self, message: NavigationJump) -> None:
        """Handle NavigationJump from the nav panel."""
        if self._figure is not None:
            self._figure.jump_to(message.word_index)
        # Update book chapter index
        if self._nav_panel is not None:
            prev = self._book.current_chapter_index
            next_ = message.chapter_index
            if prev != next_:
                telemetry.chapter_nav(
                    book_id=self._book.id,
                    from_chapter=prev,
                    to_chapter=next_,
                )
            self._book.current_chapter_index = message.chapter_index

    def action_next_figure(self) -> None:
        """N: cycle to the next figure in the registry."""
        registry = default_registry()
        new_fig = registry.next(self.current_figure_id)
        self._swap_figure(new_fig.id)

    def action_prev_figure(self) -> None:
        """Shift+N: cycle to the previous figure in the registry."""
        registry = default_registry()
        new_fig = registry.previous(self.current_figure_id)
        self._swap_figure(new_fig.id)

    def action_open_picker(self) -> None:
        """Ctrl+G: open the figure picker modal."""
        self.app.push_screen(
            FigurePickerScreen(current_id=self.current_figure_id),
            self._on_picker_dismissed,
        )

    def action_open_palette(self) -> None:
        """Ctrl+P: open the command palette modal."""
        self.app.push_screen(
            CommandPaletteScreen(),
            self._on_palette_dismissed,
        )

    def _open_file_explorer(self) -> None:
        """Ctrl+O: open the file explorer to select a file."""
        self.app.push_screen(
            FileExplorerScreen(),
            self._on_file_selected,
        )

    def _on_file_selected(self, path: str | None) -> None:
        """Handle file selection from the explorer."""
        if not path:
            return
        from pathlib import Path

        # Import and open the file via library manager
        try:
            library_manager = self.app.library_manager  # type: ignore[attr-defined]
            book = library_manager.import_book(Path(path))
            if book:
                # Get words and push reader
                from ..managers.config_manager import ConfigManager

                config = ConfigManager().load()
                cache_dir = config.cache_dir / f"{book.id}.json"
                if cache_dir.exists():
                    import json

                    words_data = json.loads(cache_dir.read_text(encoding="utf-8"))
                    words = words_data.get("words", [])
                else:
                    words = []
                # Pop current reader and push new one
                self.app.pop_screen()
                self.app.push_screen(
                    type(self)(book, words, config),
                )
        except Exception as e:
            self.app.notify(f"Error opening file: {e}", severity="error")

    def _on_picker_dismissed(self, fig_id: str | None) -> None:
        """Apply the picker choice, if any."""
        if fig_id:
            self._swap_figure(fig_id)

    def _on_palette_dismissed(self, command_id: str | None) -> None:
        """Dispatch a palette command."""
        if not command_id:
            return
        if command_id == "next_figure":
            self.action_next_figure()
        elif command_id == "prev_figure":
            self.action_prev_figure()
        elif command_id == "open_picker":
            self.action_open_picker()
        elif command_id == "toggle_play":
            self.action_toggle_play()
        elif command_id == "jump_start":
            self.action_jump_start()
        elif command_id == "jump_end":
            self.action_jump_end()
        elif command_id == "increase_speed":
            self.action_increase_speed()
        elif command_id == "decrease_speed":
            self.action_decrease_speed()
        elif command_id == "toggle_focus":
            self.action_toggle_focus()
        elif command_id == "open_file":
            self._open_file_explorer()
        elif command_id == "next_chapter":
            self.action_next_chapter()
        elif command_id == "prev_chapter":
            self.action_prev_chapter()
        elif command_id == "toggle_navigation":
            self.action_toggle_navigation()
        elif command_id == "go_to_chapter":
            # TODO: Show chapter picker overlay
            self.app.notify("Use [ and ] keys to navigate chapters")
        elif command_id == "go_to_page":
            # TODO: Show page input
            self.app.notify("Use page navigation in the panel")
        elif command_id.startswith("wpm_"):
            try:
                wpm = int(command_id.split("_", 1)[1])
            except ValueError:
                return
            self._set_wpm(wpm)
        elif command_id.startswith("theme_"):
            theme = command_id.split("_", 1)[1]
            self._set_theme(theme)

    def _on_note_added(self, word_index: int) -> None:
        """Forward note-add to the app for persistence (Phase 2 stub)."""
        self.app.notify(f"Add note at word {word_index}")

    # ---- Direct-jump keys 1-8 -------------------------------------------

    def _jump_to_index(self, idx: int) -> None:
        registry = default_registry()
        figs = registry.all()
        if 0 <= idx < len(figs):
            self._swap_figure(figs[idx].id)

    def action_figure_1(self) -> None:
        self._jump_to_index(0)

    def action_figure_2(self) -> None:
        self._jump_to_index(1)

    def action_figure_3(self) -> None:
        self._jump_to_index(2)

    def action_figure_4(self) -> None:
        self._jump_to_index(3)

    def action_figure_5(self) -> None:
        self._jump_to_index(4)

    def action_figure_6(self) -> None:
        self._jump_to_index(5)

    def action_figure_7(self) -> None:
        self._jump_to_index(6)

    def action_figure_8(self) -> None:
        self._jump_to_index(7)

    # ---- Config mutations (palette shortcuts) ---------------------------

    def _set_wpm(self, wpm: int) -> None:
        """Update default_wpm in config and reflect in the figure."""
        from ..managers.config_manager import ConfigManager

        manager = ConfigManager()
        manager.update(default_wpm=wpm)
        self.config.default_wpm = wpm
        if self._figure is not None:
            self._figure.set_wpm(wpm)
            if self._progress is not None:
                self._progress.set_wpm(wpm)
        self.app.notify(f"WPM set to {wpm}")

    def _set_theme(self, theme: str) -> None:
        """Update theme in config (refresh picks it up on next push)."""
        from ..managers.config_manager import ConfigManager

        manager = ConfigManager()
        manager.update(theme=theme)
        self.config.theme = theme
        self.app.notify(f"Theme: {theme}")


__all__ = ["ReaderScreen"]
