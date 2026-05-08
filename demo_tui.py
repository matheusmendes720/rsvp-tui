#!/usr/bin/env python3
"""
Demo TUI for RSVP - Standalone version without full package install.
This demonstrates all features in a working (though simplified) TUI.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent / "rsvp-tui"))

# Try to import from package, fall back to fallbacks
try:
    from rsvp_tui.fallbacks import (
        tokenize_text, parse_markdown, parse_plain_text,
        calculate_orp_index, calculate_word_delay, split_word_for_display,
        estimate_reading_time, WordParts, ParseResult
    )
except ImportError:
    # Inline fallbacks for true standalone
    def tokenize_text(text: str) -> list:
        return text.split()
    
    def parse_plain_text(text: str):
        words = text.split()
        return type('obj', (object,), {
            'title': 'Untitled',
            'author': 'Unknown',
            'plain_text': text,
            'word_count': len(words),
            'chapters': [type('ch', (object,), {
                'title': 'Content',
                'start_word_index': 0,
                'end_word_index': len(words)
            })()]
        })()
    
    def parse_markdown(text: str):
        lines = text.split('\n')
        title = 'Untitled'
        for line in lines:
            if line.startswith('# '):
                title = line[2:].strip()
                break
        words = text.split()
        return type('obj', (object,), {
            'title': title,
            'author': 'Unknown',
            'plain_text': text,
            'word_count': len(words),
            'chapters': []
        })()
    
    def calculate_orp_index(word: str) -> int:
        letters = sum(1 for c in word if c.isalpha())
        if letters <= 3: return 0
        if letters <= 5: return 1
        if letters <= 9: return 2
        return 3
    
    def split_word_for_display(word: str, orp_idx: int):
        actual_idx = min(orp_idx, len(word) - 1) if word else 0
        before = word[:actual_idx]
        orp_char = word[actual_idx] if actual_idx < len(word) else ""
        after = word[actual_idx + 1:] if actual_idx < len(word) else ""
        return type('parts', (object,), {
            'before_orp': before,
            'orp_char': orp_char,
            'after_orp': after
        })()
    
    def calculate_word_delay(word: str, wpm: int, mult: float, chars: list) -> int:
        base = 60000 // wpm if wpm > 0 else 200
        if word and word[-1] in chars:
            return int(base * mult)
        return base
    
    def estimate_reading_time(words: int, wpm: int):
        secs = (words * 60) // wpm if wpm > 0 else 0
        return (secs // 60, secs % 60)


class SimpleRSVPDemo:
    """Simple text-based RSVP demo."""
    
    def __init__(self):
        self.words = []
        self.index = 0
        self.wpm = 300
        self.is_playing = False
        self.enable_orp = True
        self.punctuation_multiplier = 2.0
        self.pause_chars = ['.', '!', '?', ';', ':']
        self.book_title = "Demo"
    
    def clear_screen(self):
        """Clear terminal."""
        print("\033[2J\033[H", end="")
    
    def display_word(self):
        """Display current word with ORP."""
        if not self.words or self.index >= len(self.words):
            print("\n[Reading Complete!]")
            return False
        
        word = self.words[self.index]
        
        # Build display
        if self.enable_orp:
            orp_idx = calculate_orp_index(word)
            parts = split_word_for_display(word, orp_idx)
            display = f"{parts.before_orp}[{parts.orp_char}]{parts.after_orp}"
        else:
            display = word
        
        # Progress
        progress = (self.index / len(self.words)) * 100
        
        # Display
        self.clear_screen()
        print("=" * 70)
        print(f" {self.book_title}")
        print("=" * 70)
        print()
        print(f"          {display:^50}")
        print()
        print(f"Word {self.index + 1}/{len(self.words)} ({progress:.1f}%)  {self.wpm} WPM")
        print()
        print("[Space] Play/Pause  [/] Skip  [/] Speed  [o] ORP  [q] Quit")
        print()
        
        return True
    
    def read_interactive(self):
        """Interactive reading mode."""
        import tty
        import termios
        import select
        
        # Save terminal settings
        old_settings = termios.tcgetattr(sys.stdin)
        
        try:
            # Set terminal to raw mode
            tty.setcbreak(sys.stdin.fileno())
            
            self.display_word()
            
            while True:
                # Check for input
                if select.select([sys.stdin], [], [], 0.1)[0]:
                    char = sys.stdin.read(1)
                    
                    if char == ' ':  # Space - toggle play
                        self.is_playing = not self.is_playing
                        if self.is_playing:
                            self._play_loop()
                    
                    elif char == '\x1b':  # Escape sequence
                        next_char = sys.stdin.read(1)
                        if next_char == '[':
                            arrow = sys.stdin.read(1)
                            if arrow == 'D':  # Left
                                self.prev_word()
                            elif arrow == 'C':  # Right
                                self.next_word()
                            elif arrow == 'A':  # Up
                                self.wpm = min(1000, self.wpm + 25)
                            elif arrow == 'B':  # Down
                                self.wpm = max(100, self.wpm - 25)
                            self.display_word()
                    
                    elif char == 'o':  # Toggle ORP
                        self.enable_orp = not self.enable_orp
                        self.display_word()
                    
                    elif char == 'r':  # Restart
                        self.index = 0
                        self.is_playing = False
                        self.display_word()
                    
                    elif char == 'q':  # Quit
                        break
                
                # Auto-advance if playing
                if self.is_playing:
                    delay = calculate_word_delay(
                        self.words[self.index],
                        self.wpm,
                        self.punctuation_multiplier,
                        self.pause_chars
                    )
                    import time
                    time.sleep(delay / 1000)
                    
                    self.index += 1
                    if self.index >= len(self.words):
                        self.is_playing = False
                        print("\n Reading complete!")
                        input("Press Enter to continue...")
                        break
                    
                    self.display_word()
        
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    
    def _play_loop(self):
        """Play mode - words advance automatically."""
        pass  # Handled in main loop
    
    def next_word(self):
        """Go to next word."""
        if self.index < len(self.words) - 1:
            self.index += 1
    
    def prev_word(self):
        """Go to previous word."""
        if self.index > 0:
            self.index -= 1
    
    def load_file(self, path: Path):
        """Load a file."""
        text = path.read_text(encoding='utf-8')
        
        if path.suffix == '.md':
            result = parse_markdown(text)
        else:
            result = parse_plain_text(text)
        
        self.words = tokenize_text(result.plain_text)
        self.book_title = result.title
        self.index = 0
    
    def run(self):
        """Run the demo."""
        # Load sample book
        sample = Path(__file__).parent / "sample_book.md"
        if sample.exists():
            self.load_file(sample)
        else:
            # Default sample text
            text = """Speed reading is a set of techniques used to improve reading speed while maintaining comprehension. 
            RSVP is one such technique where words are displayed one at a time.
            This demo shows how RSVP works in a terminal interface.
            You can control the reading speed and navigate through words."""
            self.words = text.split()
            self.book_title = "Demo Text"
        
        print("\n" + "=" * 70)
        print(" RSVP Speed Reader - Demo Mode")
        print("=" * 70)
        print()
        print(f"Book: {self.book_title}")
        print(f"Words: {len(self.words)}")
        mins, secs = estimate_reading_time(len(self.words), self.wpm)
        print(f"Est. time @ {self.wpm} WPM: {mins}:{secs:02d}")
        print()
        print("Controls:")
        print("  Space = Play/Pause")
        print("  / = Previous/Next word")
        print("  / = Increase/Decrease speed")
        print("  o = Toggle ORP highlighting")
        print("  r = Restart")
        print("  q = Quit")
        print()
        input("Press Enter to start...")
        
        self.read_interactive()
        
        print("\n Thanks for trying RSVP!")


def main():
    """Main entry point."""
    try:
        demo = SimpleRSVPDemo()
        demo.run()
    except KeyboardInterrupt:
        print("\n\n Goodbye!")
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
