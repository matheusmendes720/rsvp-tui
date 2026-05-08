"""Settings panel widget."""

from textual.widgets import Static, Input, Checkbox, Button, Label
from textual.containers import Vertical, Horizontal
from textual.reactive import reactive

from ..models import Config


class SettingsPanel(Vertical):
    """Settings configuration panel."""
    
    DEFAULT_CSS = """
    SettingsPanel {
        width: 60;
        height: auto;
        border: solid green;
        padding: 1;
    }
    SettingsPanel Input {
        width: 100%;
    }
    SettingsPanel Checkbox {
        margin: 1 0;
    }
    SettingsPanel Horizontal {
        height: auto;
        margin: 1 0;
    }
    """
    
    def __init__(self, config: Config, on_save: callable = None):
        super().__init__()
        self.config = config
        self.on_save = on_save
    
    def compose(self):
        """Compose the settings form."""
        yield Label("Reading Settings", variant="primary")
        
        yield Label("Default WPM:")
        yield Input(
            value=str(self.config.default_wpm),
            id="default-wpm",
            type="integer",
        )
        
        yield Label("Min/Max WPM:")
        with Horizontal():
            yield Input(
                value=str(self.config.min_wpm),
                id="min-wpm",
                type="integer",
            )
            yield Input(
                value=str(self.config.max_wpm),
                id="max-wpm",
                type="integer",
            )
        
        yield Checkbox(
            "Enable ORP Highlighting",
            value=self.config.enable_orp,
            id="enable-orp",
        )
        
        yield Checkbox(
            "Pause on Punctuation",
            value=self.config.pause_on_punctuation,
            id="pause-punctuation",
        )
        
        yield Label("Punctuation Multiplier:")
        yield Input(
            value=str(self.config.punctuation_multiplier),
            id="punctuation-multiplier",
            type="number",
        )
        
        with Horizontal():
            yield Button("Save", id="save-btn", variant="success")
            yield Button("Cancel", id="cancel-btn", variant="error")
    
    def on_button_pressed(self, event: Button.Pressed):
        """Handle button presses."""
        if event.button.id == "save-btn":
            self._save_settings()
        elif event.button.id == "cancel-btn":
            if self.on_save:
                self.on_save(None)
    
    def _save_settings(self):
        """Save settings from form."""
        try:
            self.config.default_wpm = int(self.query_one("#default-wpm", Input).value)
            self.config.min_wpm = int(self.query_one("#min-wpm", Input).value)
            self.config.max_wpm = int(self.query_one("#max-wpm", Input).value)
            self.config.enable_orp = self.query_one("#enable-orp", Checkbox).value
            self.config.pause_on_punctuation = self.query_one("#pause-punctuation", Checkbox).value
            self.config.punctuation_multiplier = float(
                self.query_one("#punctuation-multiplier", Input).value
            )
            
            self.config.save()
            
            if self.on_save:
                self.on_save(self.config)
        except ValueError as e:
            # Handle validation error
            pass
