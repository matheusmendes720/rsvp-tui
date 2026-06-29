"""
RSVP TUI - Terminal User Interface for Speed Reading

A high-performance TUI speed reader with Rust backend for text processing.
"""

__version__ = "0.3.0"
__author__ = "RSVP Team"

# Try to import Rust extensions
try:
    from rsvp_core import (
        Chapter,
        DocumentMetadata,
        ParseResult,
        WordParts,
        calculate_orp_index,
        calculate_word_delay,
        calculate_word_frequency_distribution,
        estimate_reading_time,
        generate_reading_heatmap_data,
        identify_difficult_words,
        parse_epub_bytes,
        parse_markdown,
        parse_pdf_bytes,
        parse_plain_text,
        should_pause_at_punctuation,
        split_word_for_display,
        tokenize_text,
    )

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Fall back to pure Python implementations
    from .fallbacks import (
        Chapter,
        DocumentMetadata,
        ParseResult,
        WordParts,
        calculate_orp_index,
        calculate_word_delay,
        calculate_word_frequency_distribution,
        estimate_reading_time,
        generate_reading_heatmap_data,
        identify_difficult_words,
        parse_epub_bytes,
        parse_epub_path,
        parse_markdown,
        parse_pdf_bytes,
        parse_pdf_path,
        parse_plain_text,
        should_pause_at_punctuation,
        split_word_for_display,
        tokenize_text,
    )

# Aliases for path-based parsing (not in rsvp_core, always available from fallbacks)
from .fallbacks import parse_epub_path, parse_pdf_path  # noqa: E402

__all__ = [
    "RUST_AVAILABLE",
    "tokenize_text",
    "parse_pdf_bytes",
    "parse_pdf_path",
    "parse_epub_bytes",
    "parse_epub_path",
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
