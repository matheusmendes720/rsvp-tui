//! File parsing for various document formats
//!
//! Supports: PDF, EPUB, Markdown, Plain Text

use pyo3::prelude::*;
use crate::errors::{RsvpError, RsvpResult};
use crate::text_engine::{tokenize_text, normalize_whitespace};

/// Document metadata
#[pyclass]
#[derive(Debug, Clone)]
pub struct DocumentMetadata {
    #[pyo3(get, set)]
    pub title: String,
    #[pyo3(get, set)]
    pub author: String,
    #[pyo3(get, set)]
    pub language: String,
    #[pyo3(get, set)]
    pub description: String,
}

#[pymethods]
impl DocumentMetadata {
    #[new]
    pub fn new(title: String, author: String, language: String, description: String) -> Self {
        Self {
            title,
            author,
            language,
            description,
        }
    }
}

impl Default for DocumentMetadata {
    fn default() -> Self {
        Self {
            title: "Untitled".to_string(),
            author: "Unknown".to_string(),
            language: "en".to_string(),
            description: "".to_string(),
        }
    }
}

/// Chapter information
#[pyclass]
#[derive(Debug, Clone)]
pub struct Chapter {
    #[pyo3(get, set)]
    pub title: String,
    #[pyo3(get, set)]
    pub start_word_index: usize,
    #[pyo3(get, set)]
    pub end_word_index: usize,
    #[pyo3(get, set)]
    pub content: String,
}

#[pymethods]
impl Chapter {
    #[new]
    pub fn new(title: String, start_word_index: usize, end_word_index: usize) -> Self {
        Self {
            title,
            start_word_index,
            end_word_index,
            content: String::new(),
        }
    }
    
    pub fn word_count(&self) -> usize {
        self.end_word_index.saturating_sub(self.start_word_index)
    }
}

impl Chapter {
    pub fn to_dict(&self) -> std::collections::HashMap<String, String> {
        let mut map = std::collections::HashMap::new();
        map.insert("title".to_string(), self.title.clone());
        map.insert("start_word_index".to_string(), self.start_word_index.to_string());
        map.insert("end_word_index".to_string(), self.end_word_index.to_string());
        map
    }
}

/// Parse result containing extracted document information
#[pyclass]
#[derive(Debug, Clone)]
pub struct ParseResult {
    #[pyo3(get, set)]
    pub title: String,
    #[pyo3(get, set)]
    pub author: String,
    #[pyo3(get, set)]
    pub plain_text: String,
    #[pyo3(get, set)]
    pub word_count: usize,
    #[pyo3(get, set)]
    pub chapters: Vec<Chapter>,
    #[pyo3(get, set)]
    pub metadata: Option<Py<DocumentMetadata>>,
}

#[pymethods]
impl ParseResult {
    #[new]
    pub fn new(title: String, author: String, plain_text: String) -> Self {
        let word_count = tokenize_text(&plain_text).len();
        Self {
            title,
            author,
            plain_text,
            word_count,
            chapters: Vec::new(),
            metadata: None,
        }
    }
    
    pub fn get_chapter_for_word_index(&self, word_index: usize) -> Option<usize> {
        self.chapters.iter().position(|ch| {
            word_index >= ch.start_word_index && word_index <= ch.end_word_index
        })
    }
    
    pub fn get_words_in_range(&self, start: usize, end: usize) -> Vec<String> {
        let all_words = tokenize_text(&self.plain_text);
        all_words[start..all_words.len().min(end)].to_vec()
    }
}

/// Parse PDF from bytes
#[allow(dead_code)] // ``data`` is part of the public API contract.
pub fn parse_pdf_bytes(_data: &[u8]) -> RsvpResult<ParseResult> {
    // For now, return a placeholder error as PDF parsing requires external deps
    // In production, use lopdf or pdf-extract
    Err(RsvpError::pdf(
        "PDF parsing requires the 'pdf' feature to be enabled"
    ))
}

/// Parse EPUB from bytes
pub fn parse_epub_bytes(data: &[u8]) -> RsvpResult<ParseResult> {
    use std::io::Cursor;

    let cursor = Cursor::new(data);
    let mut doc = epub::doc::EpubDoc::from_reader(cursor)
        .map_err(|e| RsvpError::epub(format!("Failed to parse EPUB: {}", e)))?;

    // epub 2.1+ exposes metadata as a Vec<MetadataItem>, not a
    // HashMap. Each item has a ``property`` (e.g. "title",
    // "creator") and a ``value``. Pick the first matching one.
    let title = doc
        .metadata
        .iter()
        .find(|m| m.property == "title")
        .map(|m| m.value.clone())
        .unwrap_or_else(|| "Untitled".to_string());

    let author = doc
        .metadata
        .iter()
        .find(|m| m.property == "creator")
        .map(|m| m.value.clone())
        .unwrap_or_else(|| "Unknown".to_string());

    // Get spine (reading order). Each SpineItem carries an
    // ``idref`` string that is the lookup key for
    // ``EpubDoc::get_resource``.
    let spine = doc.spine.clone();

    let mut full_text = String::new();
    let mut chapters: Vec<Chapter> = Vec::new();
    let mut current_word_index: usize = 0;

    for (idx, item) in spine.iter().enumerate() {
        if let Some((content, _mime)) = doc.get_resource(&item.idref) {
            let content_str = String::from_utf8_lossy(&content);

            // Extract text from HTML
            let text = extract_text_from_html(&content_str);
            let normalized = normalize_whitespace(&text);

            if !normalized.is_empty() {
                let word_count = tokenize_text(&normalized).len();

                // Try to get chapter title
                let chapter_title = extract_chapter_title(&content_str)
                    .unwrap_or_else(|| format!("Chapter {}", idx + 1));

                let chapter = Chapter {
                    title: chapter_title,
                    start_word_index: current_word_index,
                    end_word_index: current_word_index + word_count,
                    content: normalized.clone(),
                };

                chapters.push(chapter);
                full_text.push_str(&normalized);
                full_text.push(' ');
                current_word_index += word_count;
            }
        }
    }

    Ok(ParseResult {
        title,
        author,
        plain_text: full_text.trim().to_string(),
        word_count: current_word_index,
        chapters,
        metadata: None,
    })
}

/// Parse Markdown text
pub fn parse_markdown(text: &str) -> RsvpResult<ParseResult> {
    // Simple markdown parsing - extract headers as chapters
    let mut chapters: Vec<Chapter> = Vec::new();
    let mut current_chapter_start: usize = 0;
    let mut current_chapter_title = "Chapter 1".to_string();
    let mut plain_text = String::new();
    
    for line in text.lines() {
        // Check for markdown headers
        if line.starts_with("# ") {
            // Save previous chapter if exists
            if !plain_text.is_empty() {
                let words = tokenize_text(&plain_text);
                let chapter = Chapter {
                    title: current_chapter_title.clone(),
                    start_word_index: current_chapter_start,
                    end_word_index: words.len(),
                    content: plain_text.clone(),
                };
                chapters.push(chapter);
            }

            current_chapter_title = line[2..].trim().to_string();
            current_chapter_start = tokenize_text(&plain_text).len();
            // Skip the header line — chapter titles are not part
            // of the word stream the reader sees. Including them
            // would make every chapter start with its own title
            // (``Chapter 1 Word1 Word2 …``).
            continue;
        } else if line.starts_with("## ") {
            // Level 2 header - could be sub-chapter
            let words = tokenize_text(&plain_text);
            if words.len() - current_chapter_start > 100 {
                // Only split if previous chapter has substantial content
                let chapter = Chapter {
                    title: current_chapter_title.clone(),
                    start_word_index: current_chapter_start,
                    end_word_index: words.len(),
                    content: plain_text[current_chapter_start..].to_string(),
                };
                chapters.push(chapter);

                current_chapter_title = line[3..].trim().to_string();
                current_chapter_start = words.len();
            }
            // Same rationale: skip the ``## Heading`` line so its
            // words don't pollute the next chapter.
            continue;
        }

        // Non-header line — remove markdown formatting and add
        // to plain text.
        let cleaned = clean_markdown_line(line);
        plain_text.push_str(&cleaned);
        plain_text.push(' ');
    }
    
    // Add final chapter
    if !plain_text.is_empty() {
        let words = tokenize_text(&plain_text);
        let chapter = Chapter {
            title: current_chapter_title,
            start_word_index: current_chapter_start,
            end_word_index: words.len(),
            content: plain_text.clone(),
        };
        chapters.push(chapter);
    }
    
    // Extract title from first h1 if available
    let title = text.lines()
        .find(|l| l.starts_with("# "))
        .map(|l| l[2..].trim().to_string())
        .unwrap_or_else(|| "Untitled".to_string());
    
    let word_count = tokenize_text(&plain_text).len();
    
    Ok(ParseResult {
        title,
        author: "Unknown".to_string(),
        plain_text: plain_text.trim().to_string(),
        word_count,
        chapters,
        metadata: None,
    })
}

/// Parse plain text (simplest case)
pub fn parse_plain_text(text: &str) -> ParseResult {
    let normalized = normalize_whitespace(text);
    let word_count = tokenize_text(&normalized).len();
    
    let chapter = Chapter {
        title: "Content".to_string(),
        start_word_index: 0,
        end_word_index: word_count,
        content: normalized.clone(),
    };
    
    ParseResult {
        title: "Untitled".to_string(),
        author: "Unknown".to_string(),
        plain_text: normalized,
        word_count,
        chapters: vec![chapter],
        metadata: None,
    }
}

/// Extract text from HTML
fn extract_text_from_html(html: &str) -> String {
    // Simple HTML tag removal - for production, use html2text
    let mut result = String::new();
    let mut in_tag = false;
    
    for ch in html.chars() {
        match ch {
            '<' => in_tag = true,
            '>' => {
                in_tag = false;
                result.push(' '); // Add space where tag was
            }
            _ if !in_tag => result.push(ch),
            _ => {}
        }
    }
    
    normalize_whitespace(&result)
}

/// Extract chapter title from HTML
fn extract_chapter_title(html: &str) -> Option<String> {
    // Look for h1, h2 tags
    for tag in ["h1", "h2", "h3"] {
        let start_tag = format!("<{}>", tag);
        let end_tag = format!("</{}>", tag);
        
        if let Some(start) = html.find(&start_tag) {
            if let Some(end) = html.find(&end_tag) {
                if end > start + start_tag.len() {
                    let title = &html[start + start_tag.len()..end];
                    let cleaned = extract_text_from_html(title);
                    if !cleaned.is_empty() {
                        return Some(cleaned);
                    }
                }
            }
        }
    }
    
    None
}

/// Clean a single markdown line to plain text.
///
/// Strips the things that show up in a reader's eye and would
/// otherwise pollute the RSVP word stream:
///
/// * ATX headers (``# …``, ``## …``, …)
/// * emphasis markers (``**``, ``*``, ``__``, ``_``, ``~~``, ````)
/// * inline code backticks
/// * Markdown link syntax — ``[text](url)`` becomes ``text``
///
/// Image syntax (``![alt](url)``) and reference-style links are
/// not handled here (out of scope for the v1 reader).
fn clean_markdown_line(line: &str) -> String {
    let mut result = line.to_string();

    // Strip ATX headers: ``# ``, ``## ``, … ``###### `` at the
    // very start of the line. We don't allow indented headers
    // here because the chapter splitter already broke the text
    // on bare ``#``/``##`` lines, so the ones we see here are
    // content paragraphs.
    let trimmed = result.trim_start();
    let header_count = trimmed.chars().take_while(|c| *c == '#').count();
    if header_count > 0 && header_count <= 6 {
        // Drop the leading ``#``s and any whitespace after them.
        let after = &trimmed[header_count..];
        let after = after.trim_start();
        // If the header is setext-style (``# Heading ===``)
        // also strip the trailing marker — but that's rare in
        // our usage; leave as plain text.
        if result.starts_with(|_: char| true) {
            // ``result`` may have leading whitespace; reconstruct
            // from ``trimmed[header_count..]`` and skip the rest.
            result = after.to_string();
        } else {
            // result didn't actually start with the marker (it was
            // already inside code). Keep as-is.
            result = line.to_string();
        }
    }

    // Remove emphasis markers (and stray backticks for inline code).
    for marker in ["**", "*", "__", "_", "~~", "`"] {
        result = result.replace(marker, "");
    }

    // Remove links but keep text [text](url) -> text
    while let Some(start) = result.find('[') {
        if let Some(end) = result[start..].find("](") {
            if let Some(close) = result[start + end..].find(')') {
                // Compute the replacement text first, drop the
                // borrow, then call ``replace_range``. Holding the
                // immutable borrow across the mutable call is a
                // classic borrow-checker error.
                let inner = result[start + 1..start + end].to_string();
                let end_total = end + close + 1;
                result.replace_range(start..start + end_total, &inner);
            } else {
                break;
            }
        } else {
            break;
        }
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_plain_text() {
        let text = "Hello world. This is a test.";
        let result = parse_plain_text(text);
        
        assert_eq!(result.word_count, 6);
        assert_eq!(result.chapters.len(), 1);
        assert_eq!(result.chapters[0].title, "Content");
    }

    #[test]
    fn test_parse_markdown() {
        let md = "# My Book\n\n## Chapter 1\n\nThis is the first chapter.\n\n## Chapter 2\n\nThis is the second chapter.";
        let result = parse_markdown(md).unwrap();
        
        assert_eq!(result.title, "My Book");
        assert!(result.chapters.len() >= 2);
    }

    #[test]
    fn test_extract_text_from_html() {
        let html = "<p>Hello <strong>world</strong>!</p>";
        let text = extract_text_from_html(html);
        assert_eq!(text, "Hello world !");
    }

    #[test]
    fn test_clean_markdown_line() {
        assert_eq!(clean_markdown_line("**bold**"), "bold");
        assert_eq!(clean_markdown_line("*italic*"), "italic");
        assert_eq!(clean_markdown_line("`code`"), "code");
    }

    #[test]
    fn test_chapter_word_count() {
        let chapter = Chapter {
            title: "Test".to_string(),
            start_word_index: 0,
            end_word_index: 100,
            content: String::new(),
        };
        assert_eq!(chapter.word_count(), 100);
    }
}
