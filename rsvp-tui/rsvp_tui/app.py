"""Main TUI Application for RSVP.

Two operating modes:

* **Legacy** (``RSVP_NEW_UI`` unset or ``"0"``): the original
  single-screen UI with CSS-class toggling. Unchanged from 0.2.x.
* **New** (``RSVP_NEW_UI=1``): a proper Screen-based UI with
  ``LibraryScreen`` and ``ReaderScreen``, modal picker/palette,
  and fluid figure switching. Implemented in
  :mod:`rsvp_tui.screens`.

The two paths share managers (``LibraryManager``, ``NoteManager``)
and the config layer (``Config`` / ``ConfigManager``); only the
presentational layer differs. To revert, set ``RSVP_NEW_UI=0`` (or
unset it) — no code changes needed.
"""

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label, Button
from textual.reactive import reactive
from textual.binding import Binding

from .managers.config_manager import ConfigManager
from .models import Book, Config
from .managers.library_manager import LibraryManager
from .managers.note_manager import NoteManager
from .screens import (
    BookOpened,
    ConfigChanged,
    FigureChanged,
    FigureCompleted,
    FigureStateAdvanced,
    LibraryScreen,
    ReaderScreen,
    new_ui_enabled,
)
# Legacy widgets. These are only imported (and therefore only
# emit the deprecation warning) when ``RSVP_NEW_UI`` is unset
# or "0" — the new screens-based app doesn't need them. See
# the ``new_ui_enabled`` check in the compose() / action
# handlers further down.
if not new_ui_enabled():
    from .widgets import (  # noqa: E402, F401 — conditional import
        LibraryView,
        NotePanel,
        ProgressBar,
        ReaderDisplay,  # deprecated
        SettingsPanel,  # deprecated
    )


class RSVPApp(App):
    """Main RSVP TUI Application."""
    
    CSS = """
    Screen {
        align: center middle;
    }
    
    #main-content {
        width: 100%;
        height: 100%;
    }
    
    #reader-container {
        width: 100%;
        height: 100%;
    }
    
    #reader-display {
        height: 3fr;
        content-align: center middle;
    }
    
    #progress-bar {
        height: auto;
        margin: 1;
    }
    
    #controls-bar {
        height: auto;
        content-align: center middle;
        margin: 1;
    }
    
    #library-view {
        width: 100%;
        height: 100%;
    }
    
    .hidden {
        display: none;
    }
    
    .focus-mode #header {
        display: none;
    }
    
    .focus-mode #footer {
        display: none;
    }
    
    .focus-mode #controls-bar {
        display: none;
    }
    
    .focus-mode #note-panel {
        display: none;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("l", "show_library", "Library"),
        Binding("s", "show_settings", "Settings"),
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("left", "prev_word", "Previous"),
        Binding("right", "next_word", "Next"),
        Binding("up", "increase_speed", "Faster"),
        Binding("down", "decrease_speed", "Slower"),
        Binding("home", "jump_start", "Start"),
        Binding("end", "jump_end", "End"),
        Binding("f", "toggle_focus", "Focus Mode"),
        Binding("n", "add_note", "Add Note"),
        Binding("tab", "toggle_panel", "Toggle Panel"),
        ("question", "show_help", "Help"),
    ]
    
    # Reactive state
    current_view = reactive("library")  # "library", "reader", "settings"
    focus_mode = reactive(False)
    
    def __init__(self):
        super().__init__()
        # Single source of truth for the in-memory config. The
        # legacy single-screen path uses self.config directly; the
        # new Screen path also uses it (passed at push time).
        self._config_manager = ConfigManager()
        self.config: Config = self._config_manager.load()
        self.library_manager = LibraryManager(self.config.library_db_path)
        self.note_manager = NoteManager(self.config.notes_dir)

        self.current_book: Optional[Book] = None
        self.words: list = []
        self.reader: Optional[ReaderDisplay] = None
        # When True, route to the Screen-based UI. Cached at
        # construction so behavior is consistent for the lifetime
        # of the process even if the env var is toggled.
        self._new_ui = new_ui_enabled()
    
    def compose(self) -> ComposeResult:
        """Compose the UI.

        In the new UI we don't compose widgets here — the screens
        own their own composition. We still yield a Header and
        Footer so the app-level chrome is consistent. In the
        legacy UI we keep the original layout.
        """
        if self._new_ui:
            # Header and Footer are yielded by the screens themselves.
            # We still need to push the initial screen from on_mount.
            return
        yield Header(show_clock=True)
        
        with Vertical(id="main-content"):
            # Library View
            with Vertical(id="library-view"):
                yield LibraryView(
                    self.library_manager,
                    on_select=self._on_book_selected,
                    on_delete=self._on_book_deleted,
                )
            
            # Reader View (initially hidden)
            with Horizontal(id="reader-container", classes="hidden"):
                with Vertical(id="reader-layout"):
                    yield Static(id="reader-display")
                    yield ProgressBar(id="progress-bar")
                    yield Static(
                        "[Space] Play/Pause  [←/→] Skip  [↑/↓] Speed  [f] Focus",
                        id="controls-bar",
                    )
                
                yield NotePanel(
                    self.note_manager,
                    on_note_added=self._on_note_added,
                )
            
            # Settings View (initially hidden)
            with Vertical(id="settings-view", classes="hidden"):
                yield SettingsPanel(
                    self.config,
                    on_save=self._on_settings_saved,
                )
        
        yield Footer()
    
    def on_mount(self):
        """Initialize on mount.

        New UI: push LibraryScreen. Legacy UI: existing single-screen
        behavior.
        """
        if self._new_ui:
            self.title = "RSVP Speed Reader"
            self._push_library()
            return
        self.title = "RSVP Speed Reader"
        self.sub_title = "Library"
        self._show_library()

    # ---- New-UI routing --------------------------------------------------

    def _push_library(self) -> None:
        """Push the LibraryScreen (new UI)."""
        # Pop everything; the library is the root.
        while len(self.screen_stack) > 1:
            self.pop_screen()
        if not isinstance(self.screen, LibraryScreen):
            self.push_screen(LibraryScreen(config=self.config))

    def _push_reader(self, book: Book) -> None:
        """Load words for ``book`` and push ReaderScreen (new UI)."""
        words = self.library_manager.load_words(book.id)
        if not words:
            self.notify("Error loading book content", severity="error")
            return
        self.current_book = book
        self.words = words
        self.push_screen(
            ReaderScreen(book=book, words=words, config=self.config)
        )

    # ---- Message handlers (new UI) --------------------------------------

    def on_book_opened(self, message: BookOpened) -> None:
        """A library row was selected; load the book and push reader."""
        if not self._new_ui:
            return
        book = self.library_manager.get_book(message.book_id)
        if book is None:
            self.notify("Book not found", severity="error")
            return
        self._push_reader(book)

    def on_figure_changed(self, message: FigureChanged) -> None:
        """Persist the new figure id and show a toast."""
        if not self._new_ui:
            return
        if message.next_id and message.next_id != self.config.figure_id:
            self._config_manager.update(figure_id=message.next_id)
            self.config.figure_id = message.next_id
            self.notify(f"Figure: {message.next_id}")

    def on_figure_state_advanced(self, message: FigureStateAdvanced) -> None:
        """Auto-save library progress every 100 words."""
        if not self._new_ui:
            return
        if not message.book_id:
            return
        if message.index > 0 and message.index % 100 == 0:
            self.library_manager.update_progress(message.book_id, message.index)
        # Always mirror onto the in-memory book object so the
        # library screen can show fresh progress on return.
        if self.current_book and self.current_book.id == message.book_id:
            self.current_book.current_word_index = message.index

    def on_figure_completed(self, message: FigureCompleted) -> None:
        """Mark the book as complete and toast."""
        if not self._new_ui:
            return
        if not message.book_id:
            return
        book = self.library_manager.get_book(message.book_id)
        if book is not None:
            self.library_manager.update_progress(
                message.book_id, book.word_count
            )
        self.notify("Reading complete!")

    def on_config_changed(self, message: ConfigChanged) -> None:
        """Settings screen flushed a change; reload our in-memory config.

        The settings screen writes through ``ConfigManager.update``
        which is atomic on disk; we just re-read to keep the
        app-level in-memory copy in sync.
        """
        if not self._new_ui:
            return
        self.config = self._config_manager.load()
    
    def _show_library(self):
        """Show library view."""
        self.current_view = "library"
        self.query_one("#library-view").remove_class("hidden")
        self.query_one("#reader-container").add_class("hidden")
        self.query_one("#settings-view").add_class("hidden")
        self.sub_title = "Library"
        
        # Refresh library
        library_view = self.query_one(LibraryView)
        library_view.load_books()
    
    def _show_reader(self):
        """Show reader view."""
        if not self.current_book:
            return
        
        self.current_view = "reader"
        self.query_one("#library-view").add_class("hidden")
        self.query_one("#reader-container").remove_class("hidden")
        self.query_one("#settings-view").add_class("hidden")
        self.sub_title = self.current_book.title
        
        # Initialize reader if needed
        if not self.reader:
            self._init_reader()
    
    def _show_settings(self):
        """Show settings view."""
        self.current_view = "settings"
        self.query_one("#library-view").add_class("hidden")
        self.query_one("#reader-container").add_class("hidden")
        self.query_one("#settings-view").remove_class("hidden")
        self.sub_title = "Settings"
    
    def _init_reader(self):
        """Initialize the reader display."""
        if not self.current_book:
            return
        
        # Load words from cache
        self.words = self.library_manager.load_words(self.current_book.id)
        
        if not self.words:
            self.notify("Error loading book content", severity="error")
            return
        
        # Create reader widget
        container = self.query_one("#reader-display")
        container.remove_children()
        
        self.reader = ReaderDisplay(
            words=self.words,
            start_index=self.current_book.current_word_index,
            wpm=self.config.default_wpm,
            enable_orp=self.config.enable_orp,
            focus_mode=self.focus_mode,
            punctuation_multiplier=self.config.punctuation_multiplier,
            pause_chars=self.config.pause_chars,
            on_word_change=self._on_word_changed,
            on_complete=self._on_reading_complete,
        )
        container.mount(self.reader)
        
        # Update progress bar
        progress = self.query_one(ProgressBar)
        progress.update_progress(
            self.current_book.current_word_index,
            len(self.words),
        )
        progress.set_wpm(self.config.default_wpm)
        
        # Update note panel
        note_panel = self.query_one(NotePanel)
        note_panel.set_position(self.current_book.id, self.current_book.current_word_index)
    
    def _on_book_selected(self, book: Book):
        """Handle book selection."""
        self.current_book = book
        if self._new_ui:
            self._push_reader(book)
            return
        self._show_reader()
    
    def _on_book_deleted(self, book_id: str):
        """Handle book deletion."""
        self.library_manager.delete_book(book_id)
        self.notify("Book deleted")
    
    def _on_word_changed(self, index: int):
        """Handle word change during reading."""
        if self.current_book:
            self.current_book.current_word_index = index
            
            # Update progress bar
            progress = self.query_one(ProgressBar)
            progress.update_progress(index)
            
            # Update note panel position
            note_panel = self.query_one(NotePanel)
            note_panel.set_position(self.current_book.id, index)
            
            # Auto-save progress every 100 words
            if index % 100 == 0:
                self.library_manager.update_progress(self.current_book.id, index)
    
    def _on_reading_complete(self):
        """Handle reading completion."""
        if self.current_book:
            self.library_manager.update_progress(
                self.current_book.id,
                self.current_book.word_count,
            )
            self.notify("Reading complete!")
    
    def _on_note_added(self, word_index: int):
        """Handle add note request."""
        # TODO: Open note dialog
        self.notify(f"Add note at word {word_index}")
    
    def _on_settings_saved(self, config: Optional[Config]):
        """Handle settings save."""
        if config:
            self.config = config
            self.notify("Settings saved")
        self._show_library()
    
    # Actions
    def action_show_library(self):
        """Show library view."""
        if self._new_ui:
            self._push_library()
            return
        self.reader.pause() if self.reader else None
        self._show_library()

    def action_show_settings(self):
        """Show settings view."""
        if self._new_ui:
            # Phase 3: push the live-preview SettingsScreen modal
            # over whatever screen is current.
            from .screens.settings_screen import SettingsScreen

            self.push_screen(SettingsScreen(self.config))
            return
        self.reader.pause() if self.reader else None
        self._show_settings()
    
    def action_toggle_play(self):
        """Toggle play/pause."""
        if self.current_view == "reader" and self.reader:
            self.reader.toggle()
    
    def action_prev_word(self):
        """Go to previous word."""
        if self.current_view == "reader" and self.reader:
            self.reader.prev_word()
    
    def action_next_word(self):
        """Go to next word."""
        if self.current_view == "reader" and self.reader:
            self.reader.next_word()
    
    def action_increase_speed(self):
        """Increase reading speed."""
        if self.reader:
            self.reader.increase_speed()
            progress = self.query_one(ProgressBar)
            progress.set_wpm(self.reader.wpm)
    
    def action_decrease_speed(self):
        """Decrease reading speed."""
        if self.reader:
            self.reader.decrease_speed()
            progress = self.query_one(ProgressBar)
            progress.set_wpm(self.reader.wpm)
    
    def action_jump_start(self):
        """Jump to start."""
        if self.reader:
            self.reader.jump_to(0)
    
    def action_jump_end(self):
        """Jump to end."""
        if self.reader:
            self.reader.jump_to(len(self.words) - 1)
    
    def action_toggle_focus(self):
        """Toggle focus mode."""
        self.focus_mode = not self.focus_mode
        if self.reader:
            self.reader.focus_mode = self.focus_mode
        
        if self.focus_mode:
            self.add_class("focus-mode")
        else:
            self.remove_class("focus-mode")
    
    def action_add_note(self):
        """Add note at current position."""
        if self.current_view == "reader" and self.reader and self.current_book:
            self._on_note_added(self.reader.word_index)
    
    def action_toggle_panel(self):
        """Toggle side panel."""
        note_panel = self.query_one(NotePanel)
        if note_panel.has_class("hidden"):
            note_panel.remove_class("hidden")
        else:
            note_panel.add_class("hidden")
    
    def action_show_help(self):
        """Show help dialog."""
        help_text = """
        [b]Keyboard Shortcuts[/b]
        
        [b]Navigation:[/b]
        • [b]Space[/b] - Play/Pause
        • [b]←/→[/b] - Previous/Next word
        • [b]↑/↓[/b] - Increase/Decrease speed
        • [b]Home[/b] - Jump to start
        • [b]End[/b] - Jump to end
        
        [b]Views:[/b]
        • [b]l[/b] - Library
        • [b]s[/b] - Settings
        • [b]f[/b] - Toggle focus mode
        • [b]Tab[/b] - Toggle side panel
        
        [b]Actions:[/b]
        • [b]n[/b] - Add note
        • [b]q[/b] - Quit
        • [b]?[/b] - This help
        """
        self.notify(help_text, title="Help", timeout=10)
    
    def on_unmount(self):
        """Cleanup on exit."""
        # Save final progress
        if self.current_book and self.reader:
            self.library_manager.update_progress(
                self.current_book.id,
                self.reader.word_index,
            )
