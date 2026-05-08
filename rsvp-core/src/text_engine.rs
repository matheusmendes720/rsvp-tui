//! Text processing engine for RSVP
//!
//! Provides high-performance text tokenization, normalization,
//! and reading complexity analysis.

use regex::Regex;
use once_cell::sync::Lazy;
use unicode_segmentation::UnicodeSegmentation;

// Pre-compiled regex patterns for performance
static WHITESPACE_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\s+").unwrap()
});

static SENTENCE_BOUNDARY_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"[.!?]+\s+").unwrap()
});

static WORD_REGEX: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\b[\w']+\b").unwrap()
});

/// Tokenize text into words
/// 
/// Preserves punctuation attached to words (e.g., "hello.")
/// Normalizes whitespace between words
pub fn tokenize_text(text: &str) -> Vec<String> {
    text.split_whitespace()
        .map(|word| word.to_string())
        .filter(|word| !word.is_empty())
        .collect()
}

/// Split text into sentences
/// 
/// Uses sentence boundary detection with punctuation
pub fn split_into_sentences(text: &str) -> Vec<String> {
    SENTENCE_BOUNDARY_REGEX
        .split(text)
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect()
}

/// Normalize whitespace in text
/// 
/// - Collapses multiple whitespace characters into single space
/// - Trims leading/trailing whitespace
pub fn normalize_whitespace(text: &str) -> String {
    WHITESPACE_REGEX
        .replace_all(text, " ")
        .trim()
        .to_string()
}

/// Extract words with their byte positions in original text
/// 
/// Returns: Vec<(word, start_pos, end_pos)>
pub fn extract_words_with_positions(text: &str) -> Vec<(String, usize, usize)> {
    WORD_REGEX
        .find_iter(text)
        .map(|m| {
            let word = m.as_str().to_string();
            let start = m.start();
            let end = m.end();
            (word, start, end)
        })
        .collect()
}

/// Calculate Flesch-Kincaid reading ease score
/// 
/// Returns score between 0-100 (higher = easier)
/// Formula: 206.835 - 1.015 * (total_words / total_sentences) - 84.6 * (total_syllables / total_words)
pub fn calculate_reading_complexity(text: &str) -> f64 {
    let words = tokenize_text(text);
    let sentences = split_into_sentences(text);
    
    if words.is_empty() || sentences.is_empty() {
        return 0.0;
    }
    
    let total_words = words.len() as f64;
    let total_sentences = sentences.len() as f64;
    let total_syllables: usize = words.iter()
        .map(|w| count_syllables(w))
        .sum();
    
    let avg_words_per_sentence = total_words / total_sentences;
    let avg_syllables_per_word = total_syllables as f64 / total_words;
    
    // Flesch Reading Ease
    206.835 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
}

/// Count syllables in a word using heuristic
fn count_syllables(word: &str) -> usize {
    let word = word.to_lowercase();
    let vowels = ['a', 'e', 'i', 'o', 'u', 'y'];
    
    let mut count = 0;
    let mut prev_was_vowel = false;
    
    for ch in word.chars() {
        let is_vowel = vowels.contains(&ch);
        if is_vowel && !prev_was_vowel {
            count += 1;
        }
        prev_was_vowel = is_vowel;
    }
    
    // Silent 'e' handling
    if word.ends_with('e') && count > 1 {
        count -= 1;
    }
    
    std::cmp::max(count, 1)
}

/// Check if a character is part of a word (alphanumeric or apostrophe)
pub fn is_word_char(ch: char) -> bool {
    ch.is_alphanumeric() || ch == '\''
}

/// Get character count excluding punctuation
pub fn letter_count(word: &str) -> usize {
    word.chars()
        .filter(|c| c.is_alphabetic())
        .count()
}

/// Get grapheme count (handles Unicode properly)
pub fn grapheme_count(word: &str) -> usize {
    word.graphemes(true).count()
}

/// Extract the leading punctuation from a word
pub fn leading_punctuation(word: &str) -> String {
    word.chars()
        .take_while(|c| !c.is_alphanumeric())
        .collect()
}

/// Extract the trailing punctuation from a word
pub fn trailing_punctuation(word: &str) -> String {
    word.chars()
        .rev()
        .take_while(|c| !c.is_alphanumeric())
        .collect::<String>()
        .chars()
        .rev()
        .collect()
}

/// Get the alphanumeric core of a word
pub fn word_core(word: &str) -> String {
    word.chars()
        .filter(|c| c.is_alphanumeric())
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tokenize_text() {
        let text = "Hello, world! This is a test.";
        let words = tokenize_text(text);
        assert_eq!(words, vec!["Hello,", "world!", "This", "is", "a", "test."]);
    }

    #[test]
    fn test_normalize_whitespace() {
        assert_eq!(
            normalize_whitespace("  Hello    world  "),
            "Hello world"
        );
        assert_eq!(
            normalize_whitespace("Hello\n\n\tworld"),
            "Hello world"
        );
    }

    #[test]
    fn test_split_into_sentences() {
        let text = "Hello world. This is a test! How are you?";
        let sentences = split_into_sentences(text);
        assert_eq!(sentences, vec!["Hello world", "This is a test", "How are you"]);
    }

    #[test]
    fn test_extract_words_with_positions() {
        let text = "Hello, world!";
        let words = extract_words_with_positions(text);
        assert_eq!(words, vec![
            ("Hello".to_string(), 0, 5),
            ("world".to_string(), 7, 12)
        ]);
    }

    #[test]
    fn test_count_syllables() {
        assert_eq!(count_syllables("hello"), 2);
        assert_eq!(count_syllables("world"), 1);
        assert_eq!(count_syllables("extraordinary"), 5);
        assert_eq!(count_syllables("the"), 1);
    }

    #[test]
    fn test_grapheme_count() {
        assert_eq!(grapheme_count("hello"), 5);
        assert_eq!(grapheme_count("👋🏽"), 1); // Emoji with skin tone
    }

    #[test]
    fn test_letter_count() {
        assert_eq!(letter_count("hello!"), 5);
        assert_eq!(letter_count("'quoted'"), 7);
    }
}
