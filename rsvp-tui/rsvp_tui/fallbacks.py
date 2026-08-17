"""Pure Python fallback implementations when Rust is not available."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WordParts:
    """Word parts for display."""

    before_orp: str
    orp_char: str
    after_orp: str


@dataclass
class Chapter:
    """Chapter information."""

    title: str
    start_word_index: int
    end_word_index: int
    content: str = ""


@dataclass
class ParseResult:
    """Parse result."""

    title: str
    author: str
    plain_text: str
    word_count: int
    chapters: list[Chapter]


def tokenize_text(text: str) -> list[str]:
    """Tokenize text into words."""
    return text.split()


def split_into_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    pattern = r"[.!?]+\s+"
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def extract_words_with_positions(text: str) -> list[tuple[str, int, int]]:
    """Extract words with positions."""
    words = []
    for match in re.finditer(r"\b\w+\b", text):
        words.append((match.group(), match.start(), match.end()))
    return words


def calculate_reading_complexity(text: str) -> float:
    """Calculate Flesch Reading Ease score."""
    words = tokenize_text(text)
    sentences = split_into_sentences(text)

    if not words or not sentences:
        return 0.0

    total_words = len(words)
    total_sentences = len(sentences)

    # Count syllables (simplified)
    total_syllables = sum(count_syllables(w) for w in words)

    avg_words = total_words / total_sentences
    avg_syllables = total_syllables / total_words

    return 206.835 - (1.015 * avg_words) - (84.6 * avg_syllables)


def count_syllables(word: str) -> int:
    """Count syllables in a word."""
    word = word.lower()
    vowels = "aeiouy"
    count = 0
    prev_vowel = False

    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    if word.endswith("e") and count > 1:
        count -= 1

    return max(count, 1)


def parse_plain_text(text: str) -> ParseResult:
    """Parse plain text."""
    normalized = normalize_whitespace(text)
    words = tokenize_text(normalized)

    chapter = Chapter(
        title="Content",
        start_word_index=0,
        end_word_index=len(words),
        content=normalized,
    )

    return ParseResult(
        title="Untitled",
        author="Unknown",
        plain_text=normalized,
        word_count=len(words),
        chapters=[chapter],
    )


def parse_markdown(text: str) -> ParseResult:
    """Simple markdown parser."""
    lines = text.split("\n")
    chapters = []
    current_content: list[str] = []
    current_title = "Chapter 1"
    start_idx = 0
    all_words = []

    for line in lines:
        if line.startswith("# "):
            # Save previous chapter
            if current_content:
                content = " ".join(current_content)
                words = tokenize_text(content)
                chapters.append(
                    Chapter(
                        title=current_title,
                        start_word_index=start_idx,
                        end_word_index=start_idx + len(words),
                        content=content,
                    )
                )
                all_words.extend(words)
                start_idx += len(words)

            current_title = line[2:].strip()
            current_content = []
        else:
            # Clean markdown formatting
            cleaned = clean_markdown_line(line)
            if cleaned:
                current_content.append(cleaned)

    # Final chapter
    if current_content:
        content = " ".join(current_content)
        words = tokenize_text(content)
        chapters.append(
            Chapter(
                title=current_title,
                start_word_index=start_idx,
                end_word_index=start_idx + len(words),
                content=content,
            )
        )
        all_words.extend(words)

    full_text = " ".join(all_words)
    title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else "Untitled"

    return ParseResult(
        title=title,
        author="Unknown",
        plain_text=full_text,
        word_count=len(all_words),
        chapters=chapters,
    )


def clean_markdown_line(line: str) -> str:
    """Clean markdown formatting."""
    # Remove emphasis markers
    for marker in ["**", "*", "__", "_", "~~", "`"]:
        line = line.replace(marker, "")

    # Simple link removal
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)

    return line.strip()


def parse_epub_bytes(data: bytes) -> ParseResult:
    """Parse EPUB using ebooklib."""
    try:
        from ebooklib import epub
    except ImportError:
        raise NotImplementedError("EPUB parsing requires ebooklib: pip install ebooklib") from None

    from io import BytesIO

    try:
        book = epub.read_epub(BytesIO(data))
    except Exception:
        return ParseResult(title="EPUB Error", author="Unknown", plain_text="", chapters=[], word_count=0)

    # Scope the book reference so it's released (and any underlying
    # zip file handle freed) whether the parser succeeds or raises.
    # ebooklib's EpubBook has no explicit ``close()``; dropping the
    # reference is the best we can do.
    try:
        return _parse_epub_book(book)
    finally:
        book = None  # type: ignore[assignment]


def parse_epub_path(file_path: Path) -> ParseResult:
    """Parse EPUB from file path."""
    try:
        from ebooklib import epub
    except ImportError:
        raise NotImplementedError("EPUB parsing requires ebooklib: pip install ebooklib") from None

    try:
        book = epub.read_epub(str(file_path))
    except Exception:
        return ParseResult(title="EPUB Error", author="Unknown", plain_text="", chapters=[], word_count=0)

    try:
        return _parse_epub_book(book)
    finally:
        book = None  # type: ignore[assignment]


def _parse_epub_book(book: Any) -> ParseResult:
    """Internal EPUB parsing from open book."""
    # Extract metadata
    title = "Unknown"
    author = "Unknown"
    try:
        meta = book.get_metadata()
        if meta:
            title = meta[0][0].value if meta[0] else "Unknown"
        for item in book.get_metadata():
            if item[0] == "creator":
                author = item[1][0].value if item[1] else "Unknown"
    except Exception:
        pass

    # Extract text from all documents
    all_text = []
    for item in book.get_items():
        if item.get_type() == 9:  # DOCUMENT
            try:
                content = item.get_content()
                if content:
                    import re

                    text = re.sub(r"<[^>]+>", " ", str(content))
                    text = re.sub(r"\s+", " ", text).strip()
                    if text:
                        all_text.append(text)
            except Exception:
                pass

    full_text = " ".join(all_text)
    words = full_text.split()

    chapters = []
    if words:
        chapters.append(
            Chapter(
                title=title,
                start_word_index=0,
                end_word_index=len(words) - 1,
            )
        )

    return ParseResult(
        title=title,
        author=author,
        plain_text=" ".join(words),
        chapters=chapters,
        word_count=len(words),
    )


def parse_pdf_bytes(data: bytes) -> ParseResult:
    """Parse PDF using pymupdf (fitz) - direct file path."""
    try:
        import fitz
    except ImportError:
        raise NotImplementedError("PDF parsing requires pymupdf: pip install pymupdf") from None

    from io import BytesIO

    # Scope the fitz document lifetime so doc.close() always runs,
    # even when the parser raises — otherwise the underlying file
    # handle leaks for the life of the process.
    doc = fitz.open(stream=BytesIO(data), filetype="pdf")
    try:
        return _parse_pdf_doc(doc)
    finally:
        doc.close()


def parse_pdf_path(file_path: Path) -> ParseResult:
    """Parse PDF from file path - faster than bytes.

    Tries chapter-map-tui's 3-layer TOC cascade (PyMuPDF outline →
    regex TOC page → font-size heuristic) for real chapter boundaries.
    Falls back to simple single-chunk parsing if chapter-map-tui is not
    installed or extraction fails.
    """
    try:
        import fitz
    except ImportError:
        raise NotImplementedError("PDF parsing requires pymupdf: pip install pymupdf") from None

    try:
        doc = fitz.open(str(file_path))
    except Exception:
        return ParseResult(title="PDF Error", author="Unknown", plain_text="", chapters=[], word_count=0)

    try:
        return _parse_pdf_doc_with_chapters(doc, file_path)
    finally:
        doc.close()


def _parse_pdf_doc_with_chapters(doc: Any, file_path: Path) -> ParseResult:
    """Parse PDF with chapter detection via chapter-map-tui cascade."""
    # Extract metadata
    title = doc.metadata.get("title", "") or "Unknown"
    if not title or title == "Unknown":
        title = file_path.stem
    author = doc.metadata.get("author", "") or "Unknown"

    # --- Try chapter-map-tui cascade ---
    try:
        from chapter_map_tui.parsers.outline import parse_pymupdf_outline
        from chapter_map_tui.parsers.word_index import build_word_index
        from chapter_map_tui.parsers.font_size import parse_font_size_heuristic

        # Layer 1: PyMuPDF outline
        chapter_map = parse_pymupdf_outline(file_path)
        source = "outline"

        # Layer 2: regex TOC page (only if Layer 1 returned empty or too few chapters)
        if len(chapter_map.entries) < 2:
            try:
                from chapter_map_tui.parsers.regex_toc import parse_toc_page

                toc_chapters = parse_toc_page(file_path)
                if toc_chapters and len(toc_chapters.entries) >= len(chapter_map.entries):
                    chapter_map = toc_chapters
                    source = "toc_page"
            except Exception:  # noqa: BLE001
                pass

        # Layer 3: font-size heuristic (only if still sparse)
        if len(chapter_map.entries) < 2:
            font_chapters = parse_font_size_heuristic(file_path)
            if font_chapters and len(font_chapters.entries) >= len(chapter_map.entries):
                chapter_map = font_chapters
                source = "font_size"

        # Build word ranges so we know the word index boundaries
        indexed = build_word_index(file_path, chapter_map)

        # Build plain_text by iterating all pages in order
        all_text_parts: list[str] = []
        for page_num in range(doc.page_count):
            page = doc[page_num]
            text = page.get_text("text")
            if text:
                all_text_parts.append(text.strip())
            else:
                all_text_parts.append("")
        full_text = " ".join(all_text_parts)
        words = full_text.split()

        # Map chapter entries to Chapter objects using word ranges
        # Skip zero-width ranges — these come from PyMuPDF outline subsections that
        # start on the same page as their parent, giving them no distinct content.
        chapters: list[Chapter] = []
        for entry in chapter_map.entries:
            key = entry.raw_label if entry.raw_label else entry.title
            rng = indexed.ranges.get(key)
            if rng and rng.end_word_index > rng.start_word_index:
                chapters.append(
                    Chapter(
                        title=entry.title,
                        start_word_index=rng.start_word_index,
                        end_word_index=rng.end_word_index,
                    )
                )

        if chapters:
            return ParseResult(
                title=title,
                author=author,
                plain_text=" ".join(words),
                chapters=chapters,
                word_count=len(words),
            )

    except ImportError:
        # chapter-map-tui not installed — fall through to simple parser
        pass
    except Exception:  # noqa: BLE001
        # Any other error — fall through to simple parser
        pass

    # --- Fallback: simple single-chunk parsing ---
    return _parse_pdf_doc(doc)


def _parse_pdf_doc(doc: Any) -> ParseResult:
    """Internal PDF parsing from open document."""

    # Extract metadata
    title = doc.metadata.get("title", "") or "Unknown"
    if not title or title == "Unknown":
        title = "PDF Document"
    author = doc.metadata.get("author", "") or "Unknown"

    # Extract text from all pages - limit for speed
    all_text = []
    max_pages = min(len(doc), 500)  # Limit pages for performance
    for page_num in range(max_pages):
        page = doc[page_num]
        text = page.get_text("text")
        if text:
            all_text.append(text.strip())

    doc.close()

    full_text = " ".join(all_text)
    words = full_text.split()

    chapters = []
    if words:
        chapters.append(
            Chapter(
                title=title,
                start_word_index=0,
                end_word_index=len(words) - 1,
            )
        )

    return ParseResult(
        title=title,
        author=author,
        plain_text=" ".join(words),
        chapters=chapters,
        word_count=len(words),
    )


def calculate_orp_index(word: str) -> int:
    """Calculate Optimal Recognition Point index."""
    letters = sum(1 for c in word if c.isalpha())

    if letters <= 3:
        return 0
    elif letters <= 5:
        return 1
    elif letters <= 9:
        return 2
    elif letters <= 13:
        return 3
    else:
        import math

        return int(math.log2(letters - 1)) + 1


def get_actual_orp_index(word: str, orp_index: int) -> int:
    """Get actual character index accounting for punctuation."""
    letter_count = 0
    for i, ch in enumerate(word):
        if ch.isalpha():
            if letter_count == orp_index:
                return i
            letter_count += 1
    return min(orp_index, len(word) - 1)


def split_word_for_display(word: str, orp_index: int) -> WordParts:
    """Split word for ORP display."""
    actual_idx = get_actual_orp_index(word, orp_index)

    before = word[:actual_idx]
    orp_char = word[actual_idx] if actual_idx < len(word) else ""
    after = word[actual_idx + 1 :] if actual_idx < len(word) else ""

    return WordParts(before, orp_char, after)


def calculate_word_delay(
    word: str,
    wpm: int,
    punctuation_multiplier: float,
    pause_chars: list[str],
) -> int:
    """Calculate word display delay in milliseconds."""
    if wpm == 0:
        return 200

    base_delay = 60000 / wpm

    if word and word[-1] in pause_chars:
        return int(base_delay * punctuation_multiplier)

    return int(base_delay)


def estimate_reading_time(word_count: int, wpm: int) -> tuple[int, int]:
    """Estimate reading time. Returns (minutes, seconds)."""
    if wpm == 0:
        return (0, 0)

    total_seconds = int((word_count / wpm) * 60)
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    return (minutes, seconds)


def should_pause_at_punctuation(word: str, pause_chars: list[str]) -> bool:
    """Check if word ends with pause punctuation."""
    return bool(word) and word[-1] in pause_chars


def calculate_word_frequency_distribution(words: list[str]) -> dict[str, int]:
    """Calculate word frequency."""
    freq: dict[str, int] = {}
    for word in words:
        normalized = word.lower()
        freq[normalized] = freq.get(normalized, 0) + 1
    return freq


def identify_difficult_words(words: list[str], threshold: float) -> list[str]:
    """Identify difficult words."""
    if not words:
        return []

    avg_len = sum(len(w) for w in words) / len(words)
    threshold_len = avg_len * threshold

    return [w for w in words if len(w) > threshold_len or is_unusual(w)]


def is_unusual(word: str) -> bool:
    """Check if word is unusual."""
    word = word.lower()
    if len(word) > 12:
        return True

    unusual = ["xx", "qq", "zz", "jj", "kk"]
    return any(p in word for p in unusual)


def generate_reading_heatmap_data(words: list[str], window_size: int) -> list[float]:
    """Generate reading complexity heatmap."""
    if not words or window_size == 0:
        return []

    heatmap = []
    for i in range(0, len(words), window_size):
        window = words[i : i + window_size]
        avg_len = sum(len(w) for w in window) / len(window)
        heatmap.append(min(avg_len / 10, 1.0))

    return heatmap


# Stub for when rsvp_core is not available (rsvp_core exports DocumentMetadata
# but it is not re-exported from fallbacks since it has no pure-Python equivalent)
@dataclass
class DocumentMetadata:
    """Stub document metadata when Rust backend is unavailable."""

    title: str = ""
    author: str = ""
    word_count: int = 0
