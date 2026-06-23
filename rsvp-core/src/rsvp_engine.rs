//! Core RSVP timing and display logic
//!
//! Implements Optimal Recognition Point (ORP) calculation
//! and word display timing algorithms.

use crate::text_engine::letter_count;
use pyo3::prelude::*;

/// Word parts for ORP display
#[pyclass]
#[derive(Debug, Clone)]
pub struct WordParts {
    #[pyo3(get)]
    pub before_orp: String,
    #[pyo3(get)]
    pub orp_char: String,
    #[pyo3(get)]
    pub after_orp: String,
}

impl WordParts {
    pub fn new(before: String, orp: String, after: String) -> Self {
        Self {
            before_orp: before,
            orp_char: orp,
            after_orp: after,
        }
    }
}

#[pymethods]
impl WordParts {
    fn __repr__(&self) -> String {
        format!(
            "WordParts(before_orp='{}', orp_char='{}', after_orp='{}')",
            self.before_orp, self.orp_char, self.after_orp
        )
    }
}

/// Calculate the Optimal Recognition Point (ORP) index for a word
///
/// The ORP is the character position where the eye naturally focuses.
/// Based on word letter count:
/// - 1 letter: position 0
/// - 2-3 letters: position 0
/// - 4-5 letters: position 1
/// - 6-9 letters: position 2
/// - 10-13 letters: position 3
/// - 14+ letters: log2-based calculation
pub fn calculate_orp_index(word: &str) -> usize {
    // Count only alphabetic characters for ORP calculation
    let letter_len = letter_count(word);
    
    match letter_len {
        0 | 1 | 2 | 3 => 0,
        4 | 5 => 1,
        6 | 7 | 8 | 9 => 2,
        10 | 11 | 12 | 13 => 3,
        _ => ((letter_len as f64).log2() + 0.5) as usize,
    }
}

/// Get the actual character index accounting for leading punctuation
///
/// Skips over non-alphabetic characters at the start of the word
pub fn get_actual_orp_index(word: &str, orp_index: usize) -> usize {
    let mut letter_count = 0;
    
    for (i, ch) in word.char_indices() {
        if ch.is_alphabetic() {
            if letter_count == orp_index {
                return i;
            }
            letter_count += 1;
        }
    }
    
    // Fallback: return minimum of orp_index and last char index
    word.char_indices().nth(orp_index)
        .map(|(i, _)| i)
        .unwrap_or_else(|| word.len().saturating_sub(1))
}

/// Split a word for ORP display
///
/// Returns the parts before ORP, the ORP character, and after ORP
pub fn split_word_for_display(word: &str, orp_index: usize) -> WordParts {
    let actual_idx = get_actual_orp_index(word, orp_index);
    
    // Get byte positions
    let before = &word[..actual_idx];
    
    // Get the ORP character (handle multi-byte UTF-8)
    let orp_char: String = word[actual_idx..]
        .chars()
        .next()
        .map(|c| c.to_string())
        .unwrap_or_default();
    
    let orp_char_len = orp_char.len();
    let after = &word[actual_idx + orp_char_len..];
    
    WordParts::new(before.to_string(), orp_char, after.to_string())
}

/// Calculate display delay for a word in milliseconds
///
/// Base delay: 60000 / WPM
/// Adjustments:
/// - Punctuation pause: multiply by punctuation_multiplier
/// - Long words (>12 chars): add word_length_factor per extra char
pub fn calculate_word_delay(
    word: &str,
    wpm: u32,
    punctuation_multiplier: f32,
    pause_chars: &[char],
) -> u64 {
    if wpm == 0 {
        return 200; // Default fallback
    }
    
    let base_delay_ms = 60000.0 / wpm as f64;
    
    // Check for punctuation at end
    let should_pause = should_pause_at_punctuation(word, pause_chars);
    
    let multiplier = if should_pause {
        punctuation_multiplier as f64
    } else {
        1.0
    };
    
    (base_delay_ms * multiplier) as u64
}

/// Check if a word ends with punctuation that should trigger a pause
pub fn should_pause_at_punctuation(word: &str, pause_chars: &[char]) -> bool {
    word.chars()
        .last()
        .map(|last_char| pause_chars.contains(&last_char))
        .unwrap_or(false)
}

/// Estimate reading time for a document
///
/// Returns (minutes, seconds)
pub fn estimate_reading_time(word_count: usize, wpm: u32) -> (u32, u32) {
    if wpm == 0 {
        return (0, 0);
    }
    
    let total_seconds = (word_count as f64 / wpm as f64 * 60.0) as u32;
    let minutes = total_seconds / 60;
    let seconds = total_seconds % 60;
    
    (minutes, seconds)
}

/// Calculate the effective WPM accounting for pauses
pub fn calculate_effective_wpm(
    words_read: usize,
    total_time_ms: u64,
    pause_time_ms: u64,
) -> f64 {
    let active_time_ms = total_time_ms.saturating_sub(pause_time_ms);
    if active_time_ms == 0 {
        return 0.0;
    }
    
    let active_time_minutes = active_time_ms as f64 / 60000.0;
    words_read as f64 / active_time_minutes
}

/// Calculate time remaining for current reading session
pub fn calculate_time_remaining(
    words_remaining: usize,
    wpm: u32,
    avg_pauses_per_100_words: f32,
    avg_pause_duration_ms: u64,
) -> u64 {
    let reading_time_ms = (words_remaining as f64 / wpm as f64 * 60000.0) as u64;
    let estimated_pauses =
        (words_remaining as f64 / 100.0 * avg_pauses_per_100_words as f64) as u64;
    let pause_time_ms = estimated_pauses * avg_pause_duration_ms;
    
    reading_time_ms + pause_time_ms
}

/// Get progress percentage
pub fn calculate_progress(current_word: usize, total_words: usize) -> f64 {
    if total_words == 0 {
        return 0.0;
    }
    (current_word as f64 / total_words as f64) * 100.0
}

/// Convert word index to percentage position
pub fn word_index_to_percentage(word_index: usize, total_words: usize) -> f64 {
    calculate_progress(word_index, total_words)
}

/// Convert percentage to word index
pub fn percentage_to_word_index(percentage: f64, total_words: usize) -> usize {
    ((percentage / 100.0) * total_words as f64) as usize
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_orp_index() {
        assert_eq!(calculate_orp_index("a"), 0);
        assert_eq!(calculate_orp_index("the"), 0);
        assert_eq!(calculate_orp_index("word"), 1);
        assert_eq!(calculate_orp_index("hello"), 1);
        assert_eq!(calculate_orp_index("reading"), 2);
        assert_eq!(calculate_orp_index("extraordinary"), 3);
        assert_eq!(calculate_orp_index("internationalization"), 4);
    }

    #[test]
    fn test_calculate_orp_index_with_punctuation() {
        assert_eq!(calculate_orp_index("hello!"), 1);  // 5 letters
        assert_eq!(calculate_orp_index("\"quoted\""), 2);  // 6 letters
    }

    #[test]
    fn test_split_word_for_display() {
        let parts = split_word_for_display("hello", 1);
        assert_eq!(parts.before_orp, "h");
        assert_eq!(parts.orp_char, "e");
        assert_eq!(parts.after_orp, "llo");
    }

    #[test]
    fn test_split_word_with_punctuation() {
        let parts = split_word_for_display("hello!", 1);
        assert_eq!(parts.before_orp, "h");
        assert_eq!(parts.orp_char, "e");
        assert_eq!(parts.after_orp, "llo!");
    }

    #[test]
    fn test_calculate_word_delay() {
        // At 300 WPM, base delay = 200ms
        let delay = calculate_word_delay("hello", 300, 2.0, &['.', '!', '?']);
        assert_eq!(delay, 200);
        
        // With punctuation, should be 400ms
        let delay = calculate_word_delay("hello!", 300, 2.0, &['.', '!', '?']);
        assert_eq!(delay, 400);
        
        // At 600 WPM, base delay = 100ms
        let delay = calculate_word_delay("test", 600, 2.0, &[]);
        assert_eq!(delay, 100);
    }

    #[test]
    fn test_should_pause_at_punctuation() {
        assert!(should_pause_at_punctuation("hello.", &['.', '!', '?']));
        assert!(should_pause_at_punctuation("what?!", &['.', '!', '?']));
        assert!(!should_pause_at_punctuation("hello", &['.', '!', '?']));
        assert!(!should_pause_at_punctuation("hello,", &['.', '!', '?']));
    }

    #[test]
    fn test_estimate_reading_time() {
        assert_eq!(estimate_reading_time(300, 300), (1, 0));  // 1 minute
        assert_eq!(estimate_reading_time(150, 300), (0, 30)); // 30 seconds
        assert_eq!(estimate_reading_time(600, 300), (2, 0));  // 2 minutes
    }

    #[test]
    fn test_calculate_progress() {
        assert_eq!(calculate_progress(50, 100), 50.0);
        assert_eq!(calculate_progress(0, 100), 0.0);
        assert_eq!(calculate_progress(100, 100), 100.0);
        assert_eq!(calculate_progress(25, 100), 25.0);
    }

    #[test]
    fn test_percentage_conversions() {
        assert_eq!(percentage_to_word_index(50.0, 100), 50);
        assert_eq!(percentage_to_word_index(25.0, 100), 25);
        assert_eq!(word_index_to_percentage(50, 100), 50.0);
    }
}
