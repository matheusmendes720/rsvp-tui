#!/usr/bin/env python3
"""
Demonstration of the note-taking system with sample book.
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "rsvp-tui"))

from rsvp_tui.models import Book, Chapter, Note, Config
from rsvp_tui import tokenize_text, parse_markdown
from rsvp_tui.managers.note_manager import NoteManager


def main():
    print("=" * 70)
    print("RSVP NOTE-TAKING SYSTEM DEMO")
    print("=" * 70)
    
    # Load sample book
    sample_md = Path(__file__).parent / "sample_book.md"
    content = sample_md.read_text(encoding="utf-8")
    result = parse_markdown(content)
    words = tokenize_text(result.plain_text)
    
    print(f"\nLoaded: '{result.title}'")
    print(f"Total words: {len(words):,}")
    print(f"Words 100-110: {' '.join(words[100:110])}")
    
    # Create a book
    book = Book(
        id="demo_book_001",
        title=result.title,
        author="Demo Author",
        file_type="md",
        word_count=len(words),
        chapters=[
            Chapter(
                title="Chapter 1",
                start_word_index=0,
                end_word_index=150,
            ),
            Chapter(
                title="Chapter 2", 
                start_word_index=150,
                end_word_index=len(words),
            ),
        ],
    )
    
    # Setup note manager
    config = Config.load()
    note_mgr = NoteManager(config.notes_dir)
    
    print("\n" + "-" * 70)
    print("SIMULATING READING SESSION WITH NOTES")
    print("-" * 70)
    
    # Simulate reading and adding notes at specific positions
    reading_positions = [45, 120, 280, 350]
    
    for pos in reading_positions:
        context_words = words[pos:pos+3]
        context = ' '.join(context_words)
        
        print(f"\n[Reading... Word {pos}]")
        print(f"  Context: '...{context}...'")
        
        # Create note
        note = note_mgr.create_note(
            book_id=book.id,
            word_index=pos,
            chapter_index=0 if pos < 150 else 1,
            content=get_sample_note_content(pos),
            tags=get_sample_tags(pos),
            word_context=words[pos] if pos < len(words) else "",
        )
        print(f"  [NOTE ADDED] ID: {note.id}")
        print(f"  Tags: {note.tags}")
    
    # Show all notes
    print("\n" + "=" * 70)
    print("ALL NOTES FOR THIS BOOK")
    print("=" * 70)
    
    all_notes = note_mgr.get_notes_for_book(book.id)
    for i, note in enumerate(all_notes, 1):
        print(f"\n{i}. Note at word {note.word_index} (Chapter {note.chapter_index + 1})")
        print(f"   Context word: '{note.word_context}'")
        print(f"   Content: {note.content[:60]}...")
        print(f"   Tags: {', '.join(note.tags)}")
    
    # Demonstrate context-aware note retrieval
    print("\n" + "=" * 70)
    print("CONTEXT-AWARE NOTE RETRIEVAL")
    print("=" * 70)
    print("(Notes within 50 words of current reading position)\n")
    
    current_positions = [40, 130, 300]
    for curr_pos in current_positions:
        nearby = note_mgr.get_notes_for_position(book.id, curr_pos, context_window=50)
        print(f"At word {curr_pos}: {len(nearby)} note(s) nearby")
        for note in nearby:
            distance = note.word_index - curr_pos
            direction = "ahead" if distance > 0 else "behind" if distance < 0 else "here"
            print(f"  - '{note.content[:40]}...' ({abs(distance)} words {direction})")
    
    # Export notes
    print("\n" + "=" * 70)
    print("EXPORTING NOTES TO MARKDOWN")
    print("=" * 70)
    
    export_path = note_mgr.export_notes_to_markdown(book.id, book.title)
    print(f"\nExported to: {export_path}")
    
    # Show exported content
    exported = export_path.read_text(encoding="utf-8")
    print("\n--- EXPORTED CONTENT ---")
    print(exported)
    
    # Cleanup
    print("\n" + "=" * 70)
    print("CLEANUP")
    print("=" * 70)
    
    for note in all_notes:
        note_mgr.delete_note(book.id, note.id)
    print(f"\nDeleted {len(all_notes)} notes")
    
    # Remove export file
    export_path.unlink()
    print(f"Removed export file")
    
    print("\n" + "=" * 70)
    print("DEMO COMPLETE!")
    print("=" * 70)


def get_sample_note_content(position: int) -> str:
    """Get sample note content based on position."""
    notes = {
        45: "RSVP eliminates saccadic eye movements - this is the key insight!",
        120: "Average reading speed is 200-250 WPM. I should benchmark myself.",
        280: "ORP positioning depends on word length. Need to memorize the rules.",
        350: "Don't sacrifice comprehension for speed. Quality over quantity.",
    }
    return notes.get(position, "Interesting point to remember.")


def get_sample_tags(position: int) -> list:
    """Get sample tags based on position."""
    tags_map = {
        45: ["key-concept", "rsvp"],
        120: ["statistics", "benchmark"],
        280: ["orp", "technique"],
        350: ["advice", "comprehension"],
    }
    return tags_map.get(position, ["general"])


if __name__ == "__main__":
    main()
