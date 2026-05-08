#!/usr/bin/env python3
"""
Demo script to test the RSVP TUI implementation.
This simulates the core functionality without the full TUI.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the rsvp-tui to path
sys.path.insert(0, str(Path(__file__).parent / "rsvp-tui"))

try:
    from rsvp_tui.models import Book, Chapter, Note, Config
    from rsvp_tui import (
        tokenize_text,
        parse_markdown,
        calculate_orp_index,
        calculate_word_delay,
        split_word_for_display,
        estimate_reading_time,
    )
    RUST_AVAILABLE = True
    print("[OK] Rust backend available!")
except ImportError as e:
    print(f"[WARN] Rust backend not available: {e}")
    print("Using pure Python fallbacks...")
    from rsvp_tui.fallbacks import (
        tokenize_text,
        parse_markdown,
        calculate_orp_index,
        calculate_word_delay,
        split_word_for_display,
        estimate_reading_time,
        WordParts,
        ParseResult,
        Chapter,
    )
    RUST_AVAILABLE = False


def test_text_processing():
    """Test text processing functions."""
    print("\n" + "="*60)
    print("TESTING TEXT PROCESSING")
    print("="*60)
    
    sample_text = "Hello, world! This is a test of the RSVP system."
    
    # Test tokenization
    words = tokenize_text(sample_text)
    print(f"\nTokenized ({len(words)} words):")
    print(f"   {words}")
    
    # Test ORP calculation
    test_words = ["a", "the", "hello", "reading", "extraordinary", "international"]
    print("\nORP Indices:")
    for word in test_words:
        orp = calculate_orp_index(word)
        parts = split_word_for_display(word, orp)
        display = f"{parts.before_orp}[{parts.orp_char}]{parts.after_orp}"
        print(f"   '{word}' -> ORP@{orp}: {display}")
    
    # Test timing calculation
    print("\nWord Timing (at 300 WPM):")
    for word in ["word", "word.", "word!"]:
        delay = calculate_word_delay(word, 300, 2.0, ['.', '!', '?'])
        print(f"   '{word}' -> {delay}ms")


def test_markdown_parsing():
    """Test markdown parsing."""
    print("\n" + "="*60)
    print("TESTING MARKDOWN PARSING")
    print("="*60)
    
    sample_md = Path(__file__).parent / "sample_book.md"
    
    if not sample_md.exists():
        print(f"[ERROR] Sample file not found: {sample_md}")
        return
    
    content = sample_md.read_text(encoding="utf-8")
    
    try:
        result = parse_markdown(content)
        
        print(f"\nBook: {result.title}")
        print(f"   Author: {result.author}")
        print(f"   Total words: {result.word_count:,}")
        print(f"   Chapters: {len(result.chapters)}")
        
        print("\nChapter Breakdown:")
        for i, ch in enumerate(result.chapters, 1):
            ch_words = ch.end_word_index - ch.start_word_index
            print(f"   {i}. '{ch.title}' - {ch_words:,} words")
        
        # Estimate reading time
        mins, secs = estimate_reading_time(result.word_count, 300)
        print(f"\nEstimated reading time: {mins}:{secs:02d} at 300 WPM")
        
        mins_fast, secs_fast = estimate_reading_time(result.word_count, 500)
        print(f"   At 500 WPM: {mins_fast}:{secs_fast:02d}")
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Error parsing: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_book_model(result=None):
    """Test Book dataclass model."""
    print("\n" + "="*60)
    print("TESTING BOOK MODEL")
    print("="*60)
    
    if result is None:
        # Create a simple book
        chapters = [
            Chapter(
                title="Chapter 1",
                start_word_index=0,
                end_word_index=100,
            ),
            Chapter(
                title="Chapter 2",
                start_word_index=100,
                end_word_index=250,
            ),
        ]
        
        book = Book(
            id="test_book_001",
            title="Test Book",
            author="Test Author",
            file_type="md",
            word_count=250,
            chapters=chapters,
        )
    else:
        # Create from parse result
        chapters = [
            Chapter(
                title=ch.title,
                start_word_index=ch.start_word_index,
                end_word_index=ch.end_word_index,
            )
            for ch in result.chapters
        ]
        
        book = Book(
            id=f"book_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            title=result.title,
            author=result.author,
            file_type="md",
            word_count=result.word_count,
            chapters=chapters,
        )
    
    print(f"\nBook: {book.title}")
    print(f"   ID: {book.id}")
    print(f"   Author: {book.author}")
    print(f"   Type: {book.file_type}")
    print(f"   Words: {book.word_count:,}")
    print(f"   Chapters: {len(book.chapters)}")
    print(f"   Current position: {book.current_word_index}")
    print(f"   Completion: {book.completion_percentage:.1f}%")
    
    # Test serialization
    print("\n Serialization test:")
    data = book.to_dict()
    print(f"   Keys: {list(data.keys())[:5]}...")
    
    # Round-trip
    restored = Book.from_dict(data)
    print(f"   Round-trip OK: {restored.title == book.title}")
    
    return book


def test_note_model(book_id="test_book_001"):
    """Test Note dataclass model."""
    print("\n" + "="*60)
    print("TESTING NOTE MODEL")
    print("="*60)
    
    note = Note(
        id="note_001",
        book_id=book_id,
        word_index=150,
        chapter_index=1,
        content="This is a very important point about speed reading! I should remember this technique.",
        tags=["important", "technique"],
        word_context="speed",
    )
    
    print(f"\n Note: {note.id}")
    print(f"   Book: {note.book_id}")
    print(f"   Position: word {note.word_index}, chapter {note.chapter_index}")
    print(f"   Context: '{note.word_context}'")
    print(f"   Tags: {note.tags}")
    print(f"   Created: {note.created_at}")
    
    print("\nMarkdown export:")
    print(note.to_markdown())
    
    return note


def test_rsvp_simulation(words=None):
    """Simulate an RSVP reading session."""
    print("\n" + "="*60)
    print("RSVP SIMULATION (5 words)")
    print("="*60)
    
    if words is None:
        text = "The quick brown fox jumps over the lazy dog."
        words = tokenize_text(text)
    
    wpm = 300
    pause_chars = ['.', '!', '?']
    
    print(f"\nReading at {wpm} WPM:")
    print("-" * 40)
    
    total_delay = 0
    for i, word in enumerate(words[:10]):  # First 10 words
        orp_idx = calculate_orp_index(word)
        parts = split_word_for_display(word, orp_idx)
        delay = calculate_word_delay(word, wpm, 2.0, pause_chars)
        
        # Format display
        display = f"{parts.before_orp}[{parts.orp_char}]{parts.after_orp}"
        pause_marker = " [PAUSE]" if word[-1] in pause_chars else ""
        
        print(f"   Word {i+1}: '{display:20}' ({delay}ms){pause_marker}")
        total_delay += delay
    
    print("-" * 40)
    print(f"   Total time for 10 words: {total_delay}ms ({total_delay/1000:.2f}s)")
    print(f"   Effective WPM: {10 / (total_delay/60000):.0f}")


def test_config():
    """Test configuration."""
    print("\n" + "="*60)
    print("TESTING CONFIGURATION")
    print("="*60)
    
    config = Config()
    
    print(f"\nDefault Config:")
    print(f"   Default WPM: {config.default_wpm}")
    print(f"   WPM Range: {config.min_wpm}-{config.max_wpm}")
    print(f"   ORP Enabled: {config.enable_orp}")
    print(f"   Pause on punctuation: {config.pause_on_punctuation}")
    print(f"   Punctuation multiplier: {config.punctuation_multiplier}")
    print(f"   Library DB: {config.library_db_path}")
    print(f"   Notes dir: {config.notes_dir}")
    
    # Test save/load
    print("\nTesting save/load...")
    try:
        config.save()
        loaded = Config.load()
        print(f"   Save/Load OK: {loaded.default_wpm == config.default_wpm}")
    except Exception as e:
        print(f"   Save/Load failed: {e}")


def main():
    """Run all tests."""
    print("="*60)
    print("RSVP TUI - TEST SUITE")
    print("="*60)
    print(f"\nBackend: {'Rust' if RUST_AVAILABLE else 'Python Fallback'}")
    
    # Run tests
    test_text_processing()
    result = test_markdown_parsing()
    book = test_book_model(result)
    note = test_note_model(book.id if book else "test")
    test_rsvp_simulation(
        tokenize_text(result.plain_text) if result else None
    )
    test_config()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Build Rust backend: cd rsvp-core && cargo build --release")
    print("  2. Install Python TUI: cd rsvp-tui && pip install -e .")
    print("  3. Run TUI: rsvp")
    print("  4. Import book: rsvp import sample_book.md")


if __name__ == "__main__":
    main()
