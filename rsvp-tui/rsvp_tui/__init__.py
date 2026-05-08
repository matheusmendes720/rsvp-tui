"""
RSVP TUI - Terminal User Interface for Speed Reading

A high-performance TUI speed reader with Rust backend for text processing.
"""

__version__ = "0.1.0"
__author__ = "RSVP Team"

# Try to import Rust extensions
try:
    from rsvp_core import (
        tokenize_text,
        parse_pdf_bytes,
        parse_epub_bytes,
        parse_markdown,
        parse_plain_text,
        calculate_orp_index,
        calculate_word_delay,
        split_word_for_display,
        estimate_reading_time,
        should_pause_at_punctuation,
        calculate_word_frequency_distribution,
        identify_difficult_words,
        generate_reading_heatmap_data,
        ParseResult,
        Chapter,
        WordParts,
        DocumentMetadata,
    )
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Fall back to pure Python implementations
    from .fallbacks import (
        tokenize_text,
        parse_pdf_bytes,
        parse_epub_bytes,
        parse_markdown,
        parse_plain_text,
        calculate_orp_index,
        calculate_word_delay,
        split_word_for_display,
        estimate_reading_time,
        should_pause_at_punctuation,
        calculate_word_frequency_distribution,
        identify_difficult_words,
        generate_reading_heatmap_data,
    )
    # Create placeholder classes
    class ParseResult:
        def __init__(self, title, author, plain_text):
            self.title = title
            self.author = author
            self.plain_text = plain_text
            self.word_count = len(plain_text.split())
            self.chapters = []
            self.metadata = None

    class Chapter:
        def __init__(self, title, start_word_index, end_word_index):
            self.title = title
            self.start_word_index = start_word_index
            self.end_word_index = end_word_index
            self.content = ""
        
        def word_count(self):
            return self.end_word_index - self.start_word_index

    class WordParts:
        def __init__(self, before_orp, orp_char, after_orp):
            self.before_orp = before_orp
            self.orp_char = orp_char
            self.after_orp = after_orp

    class DocumentMetadata:
        def __init__(self, title="", author="", language="en", description=""):
            self.title = title
            self.author = author
            self.language = language
            self.description = description

__all__ = [
    "RUST_AVAILABLE",
    "tokenize_text",
    "parse_pdf_bytes",
    "parse_epub_bytes",
    "parse_markdown",
    "parse_plain_text",
    "calculate_orp_index",
    "calculate_word_delay",
    "split_word_for_display",
    "estimate_reading_time",
    "should_pause_at_punctuation",
    "calculate_word_frequency_distribution",
    "identify_difficult_words",
    "generate_reading_heatmap_data",
    "ParseResult",
    "Chapter",
    "WordParts",
    "DocumentMetadata",
]
