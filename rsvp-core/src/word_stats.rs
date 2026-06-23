//! Word statistics and analysis
//!
//! Provides word frequency analysis, difficulty scoring,
//! and reading heatmap generation.

use std::collections::HashMap;
use crate::text_engine::tokenize_text;

/// Calculate word frequency distribution
/// 
/// Returns a HashMap of word -> count (case-insensitive)
pub fn calculate_word_frequency_distribution(words: &[String]) -> HashMap<String, u32> {
    let mut freq: HashMap<String, u32> = HashMap::new();
    
    for word in words {
        let normalized = word.to_lowercase();
        *freq.entry(normalized).or_insert(0) += 1;
    }
    
    freq
}

/// Identify difficult words based on heuristics
/// 
/// Criteria:
/// - Word length > threshold * avg_word_length
/// - Contains unusual letter combinations
/// - Low frequency in common English
pub fn identify_difficult_words(words: &[String], threshold: f32) -> Vec<String> {
    if words.is_empty() {
        return Vec::new();
    }
    
    // Calculate average word length
    let avg_length: f32 = words.iter()
        .map(|w| w.len() as f32)
        .sum::<f32>() / words.len() as f32;
    
    let length_threshold = avg_length * threshold;
    
    words.iter()
        .filter(|w| {
            let len = w.len() as f32;
            len > length_threshold || is_unusual_word(w)
        })
        .cloned()
        .collect()
}

/// Check if a word has unusual characteristics
fn is_unusual_word(word: &str) -> bool {
    let word = word.to_lowercase();
    
    // Long words are harder
    if word.len() > 12 {
        return true;
    }
    
    // Check for unusual letter patterns
    let unusual_patterns = ["xx", "qq", "zz", "jj", "kk"];
    for pattern in &unusual_patterns {
        if word.contains(pattern) {
            return true;
        }
    }
    
    // Many consonants in a row
    let consecutive_consonants = count_max_consecutive_consonants(&word);
    if consecutive_consonants >= 5 {
        return true;
    }
    
    false
}

/// Count maximum consecutive consonants in a word
fn count_max_consecutive_consonants(word: &str) -> usize {
    let vowels = ['a', 'e', 'i', 'o', 'u', 'y'];
    let mut max_count = 0;
    let mut current_count = 0;
    
    for ch in word.chars() {
        if ch.is_alphabetic() && !vowels.contains(&ch) {
            current_count += 1;
            max_count = max_count.max(current_count);
        } else {
            current_count = 0;
        }
    }
    
    max_count
}

/// Generate reading heatmap data
/// 
/// Returns a complexity score (0.0 - 1.0) for each window of words
/// Higher score = more difficult to read
pub fn generate_reading_heatmap_data(words: &[String], window_size: usize) -> Vec<f32> {
    if words.is_empty() || window_size == 0 {
        return Vec::new();
    }
    
    let mut heatmap = Vec::new();
    
    for chunk in words.chunks(window_size) {
        let complexity = calculate_window_complexity(chunk);
        heatmap.push(complexity);
    }
    
    heatmap
}

/// Calculate complexity for a window of words
fn calculate_window_complexity(words: &[String]) -> f32 {
    if words.is_empty() {
        return 0.0;
    }
    
    // Factors:
    // 1. Average word length
    // 2. Punctuation density
    // 3. Unusual word ratio
    
    let avg_word_length: f32 = words.iter()
        .map(|w| w.len() as f32)
        .sum::<f32>() / words.len() as f32;
    
    // Normalize: assume max avg word length of 15
    let length_score = (avg_word_length / 15.0).min(1.0);
    
    // Punctuation density
    let punctuation_count: usize = words.iter()
        .map(|w| w.chars().filter(|c| c.is_ascii_punctuation()).count())
        .sum();
    let punctuation_ratio = punctuation_count as f32 / words.len() as f32;
    let punctuation_score = (punctuation_ratio / 0.5).min(1.0); // Normalize
    
    // Unusual words ratio
    let unusual_count = words.iter()
        .filter(|w| is_unusual_word(w))
        .count();
    let unusual_ratio = unusual_count as f32 / words.len() as f32;
    
    // Weighted combination
    let complexity = (length_score * 0.4) + 
                     (punctuation_score * 0.2) + 
                     (unusual_ratio * 0.4);
    
    complexity.min(1.0)
}

/// Calculate reading speed recommendation based on text complexity
/// 
/// Returns suggested WPM for comfortable reading
pub fn recommend_reading_speed(text: &str, base_wpm: u32) -> u32 {
    let words = tokenize_text(text);
    
    if words.is_empty() {
        return base_wpm;
    }
    
    // Calculate complexity metrics
    let avg_word_length: f32 = words.iter()
        .map(|w| w.len() as f32)
        .sum::<f32>() / words.len() as f32;
    
    let difficult_word_ratio = identify_difficult_words(&words, 1.5).len() as f32 
        / words.len() as f32;
    
    // Adjust WPM based on complexity
    // Longer words and more difficult words = lower WPM
    let length_factor = (avg_word_length / 5.0).max(0.8).min(1.5);
    let difficulty_factor = 1.0 + (difficult_word_ratio * 0.5);
    
    let adjusted_wpm = base_wpm as f32 / (length_factor * difficulty_factor);
    
    adjusted_wpm.max(100.0).min(1000.0) as u32
}

/// Get vocabulary statistics
pub fn get_vocabulary_stats(words: &[String]) -> VocabularyStats {
    let freq_dist = calculate_word_frequency_distribution(words);
    
    let unique_words = freq_dist.len();
    let total_words = words.len();
    
    // Find most common words
    let mut freq_vec: Vec<_> = freq_dist.iter().collect();
    freq_vec.sort_by(|a, b| b.1.cmp(a.1));
    
    let most_common: Vec<(String, u32)> = freq_vec
        .into_iter()
        .take(10)
        .map(|(w, c)| (w.clone(), *c))
        .collect();
    
    // Calculate vocabulary richness (Type-Token Ratio)
    let ttr = if total_words > 0 {
        unique_words as f32 / total_words as f32
    } else {
        0.0
    };
    
    VocabularyStats {
        unique_words,
        total_words,
        type_token_ratio: ttr,
        most_common_words: most_common,
    }
}

/// Vocabulary statistics structure
#[derive(Debug)]
pub struct VocabularyStats {
    pub unique_words: usize,
    pub total_words: usize,
    pub type_token_ratio: f32,
    pub most_common_words: Vec<(String, u32)>,
}

/// Estimate reading level (grade level approximation)
pub fn estimate_reading_level(text: &str) -> f32 {
    // Simple SMOG-inspired formula
    // Reading level = 1.043 * sqrt(polysyllables * 30 / sentences) + 3.1291
    
    let words = tokenize_text(text);
    let sentences: Vec<_> = text.split('.').collect();
    
    if sentences.is_empty() || words.is_empty() {
        return 0.0;
    }
    
    let polysyllables = words.iter()
        .filter(|w| count_syllables(w) >= 3)
        .count();
    
    let sentence_count = sentences.len().max(1);
    
    let smog = 1.043 * ((polysyllables as f32 * 30.0 / sentence_count as f32).sqrt()) + 3.1291;
    
    smog.max(1.0)
}

/// Count syllables in a word (simplified)
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_word_frequency_distribution() {
        let words = vec![
            "hello".to_string(),
            "world".to_string(),
            "hello".to_string(),
        ];
        let freq = calculate_word_frequency_distribution(&words);
        
        assert_eq!(freq.get("hello"), Some(&2));
        assert_eq!(freq.get("world"), Some(&1));
    }

    #[test]
    fn test_identify_difficult_words() {
        let words = vec![
            "the".to_string(),
            "cat".to_string(),
            "extraordinary".to_string(),
            "phenomenon".to_string(),
        ];
        let difficult = identify_difficult_words(&words, 1.5);
        
        assert!(difficult.contains(&"extraordinary".to_string()));
        assert!(difficult.contains(&"phenomenon".to_string()));
    }

    #[test]
    fn test_is_unusual_word() {
        assert!(is_unusual_word("extraordinary"));  // Long
        assert!(is_unusual_word("buzz"));           // Unusual pattern
        assert!(!is_unusual_word("hello"));         // Normal
    }

    #[test]
    fn test_count_max_consecutive_consonants() {
        assert_eq!(count_max_consecutive_consonants("strengths"), 7);
        assert_eq!(count_max_consecutive_consonants("hello"), 2);
    }

    #[test]
    fn test_generate_reading_heatmap_data() {
        let words = vec![
            "the".to_string(),
            "cat".to_string(),
            "sat".to_string(),
            "extraordinary".to_string(),
        ];
        let heatmap = generate_reading_heatmap_data(&words, 2);
        
        assert_eq!(heatmap.len(), 2);
        assert!(heatmap[0] < heatmap[1]); // Second window has harder word
    }

    #[test]
    fn test_get_vocabulary_stats() {
        let words = vec![
            "the".to_string(),
            "cat".to_string(),
            "sat".to_string(),
            "the".to_string(),
        ];
        let stats = get_vocabulary_stats(&words);
        
        assert_eq!(stats.total_words, 4);
        assert_eq!(stats.unique_words, 3);
        assert_eq!(stats.type_token_ratio, 0.75);
    }

    #[test]
    fn test_recommend_reading_speed() {
        let simple = "The cat sat on the mat.";
        let complex = "The extraordinary phenomenon necessitates comprehensive investigation.";
        
        let simple_wpm = recommend_reading_speed(simple, 300);
        let complex_wpm = recommend_reading_speed(complex, 300);
        
        assert!(complex_wpm < simple_wpm);
    }
}
