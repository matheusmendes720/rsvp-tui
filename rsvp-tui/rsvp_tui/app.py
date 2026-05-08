"""Main TUI Application for RSVP."""

from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label, Button
from textual.reactive import reactive
from textual.binding import Binding

from .models import Book, Config
from .managers.library_manager import LibraryManager
from .managers.note_manager import NoteManager
from .widgets import ReaderDisplay, LibraryView, NotePanel, ProgressBar, SettingsPanel


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
        self.config = Config.load()
        self.library_manager = LibraryManager(self.config.library_db_path)
        self.note_manager = NoteManager(self.config.notes_dir)
        
        self.current_book: Optional[Book] = None
        self.words: list = []
        self.reader: Optional[ReaderDisplay] = None
    
    def compose(self) -> ComposeResult:
        """Compose the UI."""
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
        """Initialize on mount."""
        self.title = "RSVP Speed Reader"
        self.sub_title = "Library"
        self._show_library()
    
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
        self.reader.pause() if self.reader else None
        self._show_library()
    
    def action_show_settings(self):
        """Show settings view."""
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
