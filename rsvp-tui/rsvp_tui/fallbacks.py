"""Pure Python fallback implementations when Rust is not available."""

import re
from typing import List, Tuple, Dict
from dataclasses import dataclass


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
    chapters: List[Chapter]


def tokenize_text(text: str) -> List[str]:
    """Tokenize text into words."""
    return text.split()


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    pattern = r'[.!?]+\s+'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace."""
    return re.sub(r'\s+', ' ', text).strip()


def extract_words_with_positions(text: str) -> List[Tuple[str, int, int]]:
    """Extract words with positions."""
    words = []
    for match in re.finditer(r'\b\w+\b', text):
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
    vowels = 'aeiouy'
    count = 0
    prev_vowel = False
    
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    
    if word.endswith('e') and count > 1:
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
    lines = text.split('\n')
    chapters = []
    current_content = []
    current_title = "Chapter 1"
    start_idx = 0
    all_words = []
    
    for line in lines:
        if line.startswith('# '):
            # Save previous chapter
            if current_content:
                content = ' '.join(current_content)
                words = tokenize_text(content)
                chapters.append(Chapter(
                    title=current_title,
                    start_word_index=start_idx,
                    end_word_index=start_idx + len(words),
                    content=content,
                ))
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
        content = ' '.join(current_content)
        words = tokenize_text(content)
        chapters.append(Chapter(
            title=current_title,
            start_word_index=start_idx,
            end_word_index=start_idx + len(words),
            content=content,
        ))
        all_words.extend(words)
    
    full_text = ' '.join(all_words)
    title = lines[0][2:].strip() if lines and lines[0].startswith('# ') else "Untitled"
    
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
    for marker in ['**', '*', '__', '_', '~~', '`']:
        line = line.replace(marker, '')
    
    # Simple link removal
    line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
    
    return line.strip()


def parse_epub_bytes(data: bytes) -> ParseResult:
    """Parse EPUB - requires external library."""
    raise NotImplementedError("EPUB parsing requires Rust backend or ebooklib")


def parse_pdf_bytes(data: bytes) -> ParseResult:
    """Parse PDF - requires external library."""
    raise NotImplementedError("PDF parsing requires Rust backend or pymupdf")


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
    after = word[actual_idx + 1:] if actual_idx < len(word) else ""
    
    return WordParts(before, orp_char, after)


def calculate_word_delay(
    word: str,
    wpm: int,
    punctuation_multiplier: float,
    pause_chars: List[str],
) -> int:
    """Calculate word display delay in milliseconds."""
    if wpm == 0:
        return 200
    
    base_delay = 60000 / wpm
    
    if word and word[-1] in pause_chars:
        return int(base_delay * punctuation_multiplier)
    
    return int(base_delay)


def estimate_reading_time(word_count: int, wpm: int) -> Tuple[int, int]:
    """Estimate reading time. Returns (minutes, seconds)."""
    if wpm == 0:
        return (0, 0)
    
    total_seconds = int((word_count / wpm) * 60)
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    
    return (minutes, seconds)


def should_pause_at_punctuation(word: str, pause_chars: List[str]) -> bool:
    """Check if word ends with pause punctuation."""
    return bool(word) and word[-1] in pause_chars


def calculate_word_frequency_distribution(words: List[str]) -> Dict[str, int]:
    """Calculate word frequency."""
    freq = {}
    for word in words:
        normalized = word.lower()
        freq[normalized] = freq.get(normalized, 0) + 1
    return freq


def identify_difficult_words(words: List[str], threshold: float) -> List[str]:
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
    
    unusual = ['xx', 'qq', 'zz', 'jj', 'kk']
    return any(p in word for p in unusual)


def generate_reading_heatmap_data(words: List[str], window_size: int) -> List[float]:
    """Generate reading complexity heatmap."""
    if not words or window_size == 0:
        return []
    
    heatmap = []
    for i in range(0, len(words), window_size):
        window = words[i:i + window_size]
        avg_len = sum(len(w) for w in window) / len(window)
        heatmap.append(min(avg_len / 10, 1.0))
    
    return heatmap
