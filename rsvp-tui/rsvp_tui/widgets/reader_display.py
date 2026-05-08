"""RSVP Reader Display Widget."""

from typing import Optional, Callable
from textual.widgets import Static
from textual.reactive import reactive
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich.style import Style

from .. import calculate_orp_index, split_word_for_display, calculate_word_delay


class ReaderDisplay(Static):
    """Widget for displaying RSVP words with ORP highlighting."""
    
    DEFAULT_CSS = """
    ReaderDisplay {
        content-align: center middle;
        text-align: center;
    }
    """
    
    # Reactive state
    current_word = reactive("")
    word_index = reactive(0)
    total_words = reactive(0)
    wpm = reactive(300)
    is_playing = reactive(False)
    
    def __init__(
        self,
        words: Optional[list] = None,
        start_index: int = 0,
        wpm: int = 300,
        enable_orp: bool = True,
        focus_mode: bool = False,
        punctuation_multiplier: float = 2.0,
        pause_chars: Optional[list] = None,
        on_word_change: Optional[Callable] = None,
        on_complete: Optional[Callable] = None,
    ):
        super().__init__()
        self.words = words or []
        self.word_index = start_index
        self.wpm = wpm
        self.enable_orp = enable_orp
        self.focus_mode = focus_mode
        self.punctuation_multiplier = punctuation_multiplier
        self.pause_chars = pause_chars or [".", "!", "?", ";", ":"]
        self.on_word_change = on_word_change
        self.on_complete = on_complete
        
        self._timer = None
        self._update_current_word()
    
    def _update_current_word(self):
        """Update the current word based on index."""
        if 0 <= self.word_index < len(self.words):
            self.current_word = self.words[self.word_index]
        else:
            self.current_word = ""
    
    def render(self) -> Panel:
        """Render the RSVP display."""
        if not self.current_word:
            return Panel(
                Align.center(Text("Ready", style="dim")),
                border_style="blue",
            )
        
        # Calculate ORP if enabled
        if self.enable_orp:
            orp_idx = calculate_orp_index(self.current_word)
            parts = split_word_for_display(self.current_word, orp_idx)
            word_display = self._format_with_orp(parts)
        else:
            word_display = Text(self.current_word, style="bold white")
        
        # Add context words if not in focus mode
        if not self.focus_mode and len(self.words) > 1:
            display = self._add_context_words(word_display)
        else:
            display = Align.center(word_display)
        
        return Panel(
            display,
            border_style="red" if self.is_playing else "blue",
            title=self._get_progress_title(),
        )
    
    def _format_with_orp(self, parts) -> Text:
        """Format word with ORP character highlighted."""
        result = Text()
        
        # Before ORP - right-aligned
        if parts.before_orp:
            result.append(parts.before_orp, style="white")
        
        # ORP character - highlighted in red
        result.append(parts.orp_char, style="bold red")
        
        # After ORP
        if parts.after_orp:
            result.append(parts.after_orp, style="white")
        
        return result
    
    def _add_context_words(self, current_display: Text) -> Align:
        """Add previous and next words for context."""
        lines = []
        
        # Previous word
        prev_word = ""
        if self.word_index > 0:
            prev_word = self.words[self.word_index - 1]
        prev_text = Text(prev_word, style="dim")
        
        # Next word
        next_word = ""
        if self.word_index < len(self.words) - 1:
            next_word = self.words[self.word_index + 1]
        next_text = Text(next_word, style="dim")
        
        # Layout
        lines.append(Align.center(prev_text))
        lines.append(Align.center(current_display))
        lines.append(Align.center(next_text))
        
        from rich.console import Group
        return Align.center(Group(*lines))
    
    def _get_progress_title(self) -> str:
        """Get progress indicator for panel title."""
        if not self.words:
            return ""
        pct = (self.word_index / len(self.words)) * 100
        return f"{self.word_index + 1}/{len(self.words)} ({pct:.1f}%)"
    
    def watch_word_index(self, index: int):
        """React to word index changes."""
        self._update_current_word()
        if self.on_word_change:
            self.on_word_change(index)
        if index >= len(self.words) and self.on_complete:
            self.on_complete()
    
    def start(self):
        """Start reading."""
        if not self.is_playing and self.words:
            self.is_playing = True
            self._schedule_next()
    
    def pause(self):
        """Pause reading."""
        self.is_playing = False
        if self._timer:
            self._timer.stop()
            self._timer = None
    
    def toggle(self):
        """Toggle play/pause."""
        if self.is_playing:
            self.pause()
        else:
            self.start()
    
    def stop(self):
        """Stop and reset."""
        self.pause()
        self.word_index = 0
    
    def _schedule_next(self):
        """Schedule the next word display."""
        if not self.is_playing or not self.current_word:
            return
        
        # Calculate delay
        delay_ms = calculate_word_delay(
            self.current_word,
            self.wpm,
            self.punctuation_multiplier,
            self.pause_chars,
        )
        
        from textual.timer import Timer
        self._timer = self.set_timer(delay_ms / 1000, self._advance)
    
    def _advance(self):
        """Advance to next word."""
        if self.is_playing:
            self.word_index += 1
            if self.word_index < len(self.words):
                self._schedule_next()
            else:
                self.is_playing = False
    
    def next_word(self):
        """Manually go to next word."""
        if self.word_index < len(self.words) - 1:
            self.word_index += 1
    
    def prev_word(self):
        """Manually go to previous word."""
        if self.word_index > 0:
            self.word_index -= 1
    
    def jump_to(self, index: int):
        """Jump to specific word index."""
        self.word_index = max(0, min(index, len(self.words) - 1))
    
    def jump_to_percentage(self, percentage: float):
        """Jump to percentage position."""
        if self.words:
            index = int((percentage / 100) * len(self.words))
            self.jump_to(index)
    
    def set_wpm(self, wpm: int):
        """Set reading speed."""
        self.wpm = max(100, min(1000, wpm))
    
    def increase_speed(self, amount: int = 25):
        """Increase reading speed."""
        self.set_wpm(self.wpm + amount)
    
    def decrease_speed(self, amount: int = 25):
        """Decrease reading speed."""
        self.set_wpm(self.wpm - amount)
