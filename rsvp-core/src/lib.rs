//! RSVP Core - High-performance text processing for speed reading
//!
//! This crate provides Rust implementations for:
//! - Text tokenization and normalization
//! - File parsing (PDF, EPUB, Markdown, TXT)
//! - RSVP timing calculations and ORP (Optimal Recognition Point) detection
//! - Word statistics and complexity analysis

use pyo3::prelude::*;

pub mod text_engine;
pub mod file_parser;
pub mod rsvp_engine;
pub mod word_stats;
pub mod errors;

// Re-export commonly used items
pub use text_engine::{
    tokenize_text,
    split_into_sentences,
    normalize_whitespace,
    extract_words_with_positions,
    calculate_reading_complexity,
};

pub use file_parser::{
    parse_pdf_bytes,
    parse_epub_bytes,
    parse_markdown,
    parse_plain_text,
    ParseResult,
    Chapter,
    DocumentMetadata,
};

pub use rsvp_engine::{
    calculate_orp_index,
    calculate_word_delay,
    split_word_for_display,
    estimate_reading_time,
    should_pause_at_punctuation,
    WordParts,
};

pub use word_stats::{
    calculate_word_frequency_distribution,
    identify_difficult_words,
    generate_reading_heatmap_data,
};

pub use errors::{RsvpError, RsvpResult};

/// Python module initialization
///
/// The function is named ``rsvp_core`` so pyo3 generates the
/// ``PyInit_rsvp_core`` symbol that the Python extension loader
/// expects. To avoid a name collision with the
/// ``rsvp_engine`` submodule, the inner crate was renamed
/// Python module initialization
///
/// The function is named ``rsvp_core`` so pyo3 generates the
/// ``PyInit_rsvp_core`` symbol that the Python extension loader
/// expects. The inner crate was renamed from ``rsvp_core`` to
/// ``rsvp_engine`` to avoid a name collision.
#[pymodule]
fn rsvp_core(_py: Python, m: &PyModule) -> PyResult<()> {
    // Text engine functions
    m.add_wrapped(wrap_pyfunction!(py_tokenize_text))?;
    m.add_wrapped(wrap_pyfunction!(py_split_into_sentences))?;
    m.add_wrapped(wrap_pyfunction!(py_normalize_whitespace))?;
    m.add_wrapped(wrap_pyfunction!(py_extract_words_with_positions))?;
    m.add_wrapped(wrap_pyfunction!(py_calculate_reading_complexity))?;
    
    // File parser functions
    m.add_wrapped(wrap_pyfunction!(py_parse_pdf_bytes))?;
    m.add_wrapped(wrap_pyfunction!(py_parse_epub_bytes))?;
    m.add_wrapped(wrap_pyfunction!(py_parse_markdown))?;
    m.add_wrapped(wrap_pyfunction!(py_parse_plain_text))?;
    m.add_class::<ParseResult>()?;
    m.add_class::<Chapter>()?;
    m.add_class::<DocumentMetadata>()?;
    
    // RSVP core functions
    m.add_wrapped(wrap_pyfunction!(py_calculate_orp_index))?;
    m.add_wrapped(wrap_pyfunction!(py_calculate_word_delay))?;
    m.add_wrapped(wrap_pyfunction!(py_split_word_for_display))?;
    m.add_wrapped(wrap_pyfunction!(py_estimate_reading_time))?;
    m.add_wrapped(wrap_pyfunction!(py_should_pause_at_punctuation))?;
    m.add_class::<WordParts>()?;
    
    // Word stats functions
    m.add_wrapped(wrap_pyfunction!(py_calculate_word_frequency_distribution))?;
    m.add_wrapped(wrap_pyfunction!(py_identify_difficult_words))?;
    m.add_wrapped(wrap_pyfunction!(py_generate_reading_heatmap_data))?;
    
    Ok(())
}

// Python wrapper functions
use pyo3::types::PyDict;

#[pyfunction(name = "tokenize_text")]
fn py_tokenize_text(text: &str) -> Vec<String> {
    text_engine::tokenize_text(text)
}

#[pyfunction(name = "split_into_sentences")]
fn py_split_into_sentences(text: &str) -> Vec<String> {
    text_engine::split_into_sentences(text)
}

#[pyfunction(name = "normalize_whitespace")]
fn py_normalize_whitespace(text: &str) -> String {
    text_engine::normalize_whitespace(text)
}

#[pyfunction(name = "extract_words_with_positions")]
fn py_extract_words_with_positions(text: &str) -> Vec<(String, usize, usize)> {
    text_engine::extract_words_with_positions(text)
}

#[pyfunction(name = "calculate_reading_complexity")]
fn py_calculate_reading_complexity(text: &str) -> f64 {
    text_engine::calculate_reading_complexity(text)
}

#[pyfunction(name = "parse_pdf_bytes")]
fn py_parse_pdf_bytes(data: &[u8]) -> PyResult<ParseResult> {
    file_parser::parse_pdf_bytes(data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

#[pyfunction(name = "parse_epub_bytes")]
fn py_parse_epub_bytes(data: &[u8]) -> PyResult<ParseResult> {
    file_parser::parse_epub_bytes(data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

#[pyfunction(name = "parse_markdown")]
fn py_parse_markdown(text: &str) -> PyResult<ParseResult> {
    file_parser::parse_markdown(text)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

#[pyfunction(name = "parse_plain_text")]
fn py_parse_plain_text(text: &str) -> ParseResult {
    file_parser::parse_plain_text(text)
}

#[pyfunction(name = "calculate_orp_index")]
fn py_calculate_orp_index(word: &str) -> usize {
    rsvp_engine::calculate_orp_index(word)
}

#[pyfunction(name = "calculate_word_delay")]
fn py_calculate_word_delay(
    word: &str,
    wpm: u32,
    punctuation_multiplier: f32,
    pause_chars: Vec<char>,
) -> u64 {
    rsvp_engine::calculate_word_delay(word, wpm, punctuation_multiplier, &pause_chars)
}

#[pyfunction(name = "split_word_for_display")]
fn py_split_word_for_display(word: &str, orp_index: usize) -> WordParts {
    rsvp_engine::split_word_for_display(word, orp_index)
}

#[pyfunction(name = "estimate_reading_time")]
fn py_estimate_reading_time(word_count: usize, wpm: u32) -> (u32, u32) {
    rsvp_engine::estimate_reading_time(word_count, wpm)
}

#[pyfunction(name = "should_pause_at_punctuation")]
fn py_should_pause_at_punctuation(word: &str, pause_chars: Vec<char>) -> bool {
    rsvp_engine::should_pause_at_punctuation(word, &pause_chars)
}

#[pyfunction(name = "calculate_word_frequency_distribution")]
fn py_calculate_word_frequency_distribution(words: Vec<String>) -> Py<PyDict> {
    Python::with_gil(|py| {
        let dist = word_stats::calculate_word_frequency_distribution(&words);
        let dict = PyDict::new(py);
        for (word, count) in dist {
            dict.set_item(word, count).unwrap();
        }
        dict.into()
    })
}

#[pyfunction(name = "identify_difficult_words")]
fn py_identify_difficult_words(words: Vec<String>, threshold: f32) -> Vec<String> {
    word_stats::identify_difficult_words(&words, threshold)
}

#[pyfunction(name = "generate_reading_heatmap_data")]
fn py_generate_reading_heatmap_data(words: Vec<String>, window_size: usize) -> Vec<f32> {
    word_stats::generate_reading_heatmap_data(&words, window_size)
}
