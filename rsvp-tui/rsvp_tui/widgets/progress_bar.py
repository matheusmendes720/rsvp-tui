"""Progress bar widget for reading progress."""


from rich.panel import Panel
from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static


class ProgressBar(Static):
    """Display reading progress with visual bar."""

    DEFAULT_CSS = """
    ProgressBar {
        height: auto;
        content-align: center middle;
    }
    """

    current_word = reactive(0)
    total_words = reactive(0)
    wpm = reactive(300)
    time_remaining = reactive("")

    def __init__(
        self,
        current_word: int = 0,
        total_words: int = 0,
        wpm: int = 300,
        id: str | None = None,
    ):
        super().__init__(id=id)
        self.current_word = current_word
        self.total_words = total_words
        self.wpm = wpm

    def render(self) -> Panel:
        """Render progress bar."""
        if self.total_words == 0:
            return Panel("No content")

        percentage = (self.current_word / self.total_words) * 100

        # Create progress bar
        bar_width = 40
        filled = int((percentage / 100) * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)

        # Build info line
        info = f"Word {self.current_word:,}/{self.total_words:,} ({percentage:.1f}%) • {self.wpm} WPM"
        if self.time_remaining:
            info += f" • ~{self.time_remaining} remaining"

        content = Text.assemble(
            Text(bar, style="green"),
            "\n",
            Text(info, style="dim"),
        )

        return Panel(content, border_style="dim")

    def update_progress(self, current: int, total: int | None = None):
        """Update progress values."""
        self.current_word = current
        if total is not None:
            self.total_words = total
        self._update_time_remaining()

    def set_wpm(self, wpm: int):
        """Update WPM and recalculate time."""
        self.wpm = wpm
        self._update_time_remaining()

    def _update_time_remaining(self):
        """Calculate and update time remaining."""
        if self.wpm == 0:
            self.time_remaining = ""
            return

        remaining_words = self.total_words - self.current_word
        if remaining_words <= 0:
            self.time_remaining = "0:00"
            return

        minutes = remaining_words / self.wpm
        mins = int(minutes)
        secs = int((minutes - mins) * 60)
        self.time_remaining = f"{mins}:{secs:02d}"
