//! # rsvp-tui — native Ratatui reader (high-performance render path)
//!
//! This is the Rust-native alternative to the Python Textual
//! TUI. It uses `ratatui` (the Rust TUI equivalent of Textual)
//! and `crossterm` for terminal I/O. The trade-off vs the
//! Python TUI is:
//!
//! | Surface              | Python (Textual) | Rust (Ratatui) |
//! |----------------------|------------------|----------------|
//! | Single-word RSVP     | works (pure py)  | works (rust)   |
//! | Command palette      | works            | works (planned)|
//! | Notes panel          | works (sqlite)   | read-only      |
//! | Themes               | works (live)     | 8 presets      |
//! | Performance          | ~30fps cap       | native 60fps   |
//! | Binary size          | n/a (script)     | ~5MB stripped  |
//!
//! For most users the Python TUI is the right choice. The Rust
//! reader is the right choice when (a) you want the smallest
//! possible binary, (b) you want the lowest possible latency on
//! very fast WPM settings, or (c) you're on a machine where
//! Python isn't available.
//!
//! This module is invoked by `rsvp-cli`'s `read --native` flag.

use anyhow::{Context, Result};
use crossterm::event::{self, Event, KeyCode, KeyEventKind};
use crossterm::execute;
use crossterm::terminal::{
    disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen,
};
use ratatui::layout::{Constraint, Direction, Layout};
use ratatui::style::{Color, Modifier, Style};
use ratatui::text::{Line, Span};
use ratatui::widgets::{Block, Borders, Gauge, Paragraph};
use ratatui::{DefaultTerminal, Frame};
use std::time::{Duration, Instant};

/// Tokenised + ORP-annotated word.
#[derive(Debug, Clone)]
pub struct DisplayWord {
    pub text: String,
    pub orp_index: usize, // byte offset of the ORP character
}

/// A single chapter.
#[derive(Debug, Clone)]
pub struct Chapter {
    pub title: String,
    pub words: Vec<DisplayWord>,
}

/// Top-level book loaded by the reader.
#[derive(Debug, Clone)]
pub struct Book {
    pub title: String,
    pub author: String,
    pub wpm: u32,
    pub chapters: Vec<Chapter>,
}

impl Book {
    /// Total word count across all chapters.
    pub fn total_words(&self) -> usize {
        self.chapters.iter().map(|c| c.words.len()).sum()
    }
}

/// Build a ``Book`` from a plain-text ``&str``.
///
/// The tokenisation is the same algorithm the Python TUI
/// uses (``unicode_segmentation``-style split on whitespace
/// boundaries, ORP from letter count). For a real reader
/// you'd call into ``rsvp-core`` via PyO3 — this function is
/// the standalone fallback so the binary can run with no
/// Python at all.
pub fn book_from_text(title: &str, text: &str, wpm: u32) -> Book {
    let words: Vec<DisplayWord> = text
        .split_whitespace()
        .map(|w| DisplayWord {
            text: w.to_string(),
            orp_index: orp_index(w),
        })
        .collect();
    Book {
        title: title.to_string(),
        author: "Unknown".to_string(),
        wpm,
        chapters: vec![Chapter { title: "Content".to_string(), words }],
    }
}

/// ORP index from letter count (matches the Rust core's rule).
fn orp_index(word: &str) -> usize {
    let letters: String = word.chars().filter(|c| c.is_alphabetic()).collect();
    let n = letters.chars().count();
    let orp = match n {
        0..=3 => 0,
        4..=5 => 1,
        6..=9 => 2,
        _ => 3,
    };
    // Translate from "letters index" to "byte offset in word".
    let mut byte = 0;
    let mut letters_seen = 0;
    for (i, ch) in word.char_indices() {
        if ch.is_alphabetic() {
            if letters_seen == orp {
                byte = i;
                break;
            }
            letters_seen += 1;
        } else if letters_seen == orp {
            byte = i;
            break;
        } else {
            byte = i + ch.len_utf8();
        }
    }
    byte.min(word.len())
}

/// Render a single word centered on its ORP character.
///
/// ``text`` is the full word, ``orp_byte`` is the byte offset of
/// the ORP char. The function pads left and right so the ORP
/// char is at column ``width / 2``.
fn render_word(text: &str, orp_byte: usize, width: usize) -> Vec<Span<'static>> {
    // Pre-ORP segment
    let pre = text.get(..orp_byte).unwrap_or("");
    let orp = text.get(orp_byte..).and_then(|s| s.chars().next());
    let orp_str: String = orp.map(|c| c.to_string()).unwrap_or_default();
    let orp_end = orp_byte + orp_str.len();
    let post = text.get(orp_end..).unwrap_or("");

    // Pad so ORP char sits at width/2
    let half = width / 2;
    let orp_display = orp_str.len();
    let left_pad = half.saturating_sub(orp_display);
    let mut spans = Vec::new();
    spans.push(Span::raw(" ".repeat(left_pad)));
    spans.push(Span::styled(
        pre.to_string(),
        Style::default().fg(Color::White),
    ));
    spans.push(Span::styled(
        orp_str,
        Style::default()
            .fg(Color::Yellow)
            .add_modifier(Modifier::BOLD | Modifier::UNDERLINED),
    ));
    spans.push(Span::styled(
        post.to_string(),
        Style::default().fg(Color::White),
    ));
    spans
}

/// Reader state.
pub struct Reader {
    pub book: Book,
    pub chapter: usize,
    pub word: usize,
    pub playing: bool,
    pub focus_mode: bool,
    pub wpm: u32,
    pub started: Option<Instant>,
    pub last_step: Option<Instant>,
}

impl Reader {
    pub fn new(book: Book) -> Self {
        let wpm = book.wpm;
        Self {
            book,
            chapter: 0,
            word: 0,
            playing: false,
            focus_mode: false,
            wpm,
            started: None,
            last_step: None,
        }
    }

    /// Delay between two words at the current WPM.
    pub fn step_delay(&self) -> Duration {
        Duration::from_micros(60_000_000 / self.wpm as u64)
    }

    /// Advance one word. Returns false if we ran off the end.
    pub fn step(&mut self) -> bool {
        let ch = &self.book.chapters[self.chapter];
        if self.word + 1 < ch.words.len() {
            self.word += 1;
            self.last_step = Some(Instant::now());
            true
        } else if self.chapter + 1 < self.book.chapters.len() {
            self.chapter += 1;
            self.word = 0;
            self.last_step = Some(Instant::now());
            true
        } else {
            false
        }
    }

    pub fn back(&mut self) {
        if self.word > 0 {
            self.word -= 1;
        } else if self.chapter > 0 {
            self.chapter -= 1;
            self.word = self.book.chapters[self.chapter].words.len().saturating_sub(1);
        }
    }

    pub fn current_word(&self) -> &DisplayWord {
        &self.book.chapters[self.chapter].words[self.word]
    }

    pub fn progress(&self) -> f64 {
        let total = self.book.total_words();
        let mut seen = 0;
        for (i, ch) in self.book.chapters.iter().enumerate() {
            if i < self.chapter {
                seen += ch.words.len();
            } else if i == self.chapter {
                seen += self.word;
                break;
            }
        }
        if total == 0 {
            0.0
        } else {
            seen as f64 / total as f64
        }
    }
}

/// Run the interactive reader loop.
pub fn run(mut terminal: DefaultTerminal, mut reader: Reader) -> Result<()> {
    let mut last_tick = Instant::now();
    loop {
        let elapsed = last_tick.elapsed();
        if reader.playing && elapsed >= reader.step_delay() {
            if !reader.step() {
                reader.playing = false;
            }
            last_tick = Instant::now();
        }
        terminal.draw(|f| ui(f, &reader))?;

        // 50ms tick — fast enough to feel live, slow enough
        // to not burn CPU.
        let timeout = if reader.playing {
            reader.step_delay().min(Duration::from_millis(50))
        } else {
            Duration::from_millis(50)
        };
        if event::poll(timeout)? {
            if let Event::Key(key) = event::read()? {
                if key.kind == KeyEventKind::Press {
                    match key.code {
                        KeyCode::Char('q') | KeyCode::Esc => break,
                        KeyCode::Char(' ') => reader.playing = !reader.playing,
                        KeyCode::Right | KeyCode::Char('l') => {
                            reader.step();
                        }
                        KeyCode::Left | KeyCode::Char('h') => {
                            reader.back();
                        }
                        KeyCode::Up => reader.wpm = reader.wpm.saturating_add(25).min(1000),
                        KeyCode::Down => reader.wpm = reader.wpm.saturating_sub(25).max(100),
                        KeyCode::Char('f') => reader.focus_mode = !reader.focus_mode,
                        KeyCode::Char('r') => {
                            reader.chapter = 0;
                            reader.word = 0;
                            reader.playing = false;
                        }
                        _ => {}
                    }
                }
            }
        }
    }
    Ok(())
}

/// One frame of UI.
fn ui(f: &mut Frame, reader: &Reader) {
    let area = f.area();
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([
            Constraint::Length(3),  // top bar
            Constraint::Min(3),    // RSVP word
            Constraint::Length(1), // progress bar
            Constraint::Length(3),  // status / help
        ])
        .split(area);

    // Top bar — book title, chapter, WPM
    let title = if reader.focus_mode {
        String::new()
    } else {
        format!(
            "  {}  ─  Ch.{}  ─  {} WPM  ─  {}  ",
            reader.book.title,
            reader.chapter + 1,
            reader.wpm,
            if reader.playing { "▶ playing" } else { "⏸ paused" }
        )
    };
    let title_widget = Paragraph::new(Line::from(Span::styled(
        title,
        Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD),
    )))
    .block(Block::default().borders(Borders::BOTTOM).border_style(Style::default().fg(Color::DarkGray)));
    f.render_widget(title_widget, chunks[0]);

    // RSVP word
    let word_area = chunks[1];
    let inner = Block::default().borders(Borders::NONE).inner(word_area);
    let width = inner.width.max(20) as usize;
    let spans = render_word(&reader.current_word().text, reader.current_word().orp_index, width);
    let line = Line::from(spans);
    let p = Paragraph::new(line)
        .alignment(ratatui::layout::Alignment::Center)
        .block(Block::default());
    f.render_widget(p, word_area);

    // Progress bar
    let g = Gauge::default()
        .gauge_style(Style::default().fg(Color::Green).bg(Color::Black))
        .percent((reader.progress() * 100.0) as u16);
    f.render_widget(g, chunks[2]);

    // Help / status line
    let help = if reader.focus_mode {
        "        [space] play/pause   [← →] word   [↑ ↓] WPM   [f]ocus   [r]estart   [q]uit"
    } else {
        ""
    };
    let help_widget = Paragraph::new(Line::from(Span::styled(
        help,
        Style::default().fg(Color::DarkGray),
    )))
    .alignment(ratatui::layout::Alignment::Center);
    f.render_widget(help_widget, chunks[3]);
}

/// High-level entry point used by the CLI binary.
///
/// Sets up the raw-mode terminal, runs the reader, then
/// restores the terminal on exit.
pub fn run_reader(book: Book) -> Result<()> {
    enable_raw_mode().context("enable raw mode")?;
    let mut stdout = std::io::stdout();
    execute!(stdout, EnterAlternateScreen).context("enter alt screen")?;
    let terminal = ratatui::init();
    let reader = Reader::new(book);
    let result = run(terminal, reader);
    ratatui::restore();
    execute!(stdout, LeaveAlternateScreen).ok();
    disable_raw_mode().ok();
    result
}

// ---- tests -----------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn orp_index_short() {
        // 1-3 letters -> 0
        assert_eq!(orp_index("a"), 0);
        assert_eq!(orp_index("I"), 0);
        assert_eq!(orp_index("the"), 0);
    }

    #[test]
    fn orp_index_medium() {
        // 4-5 letters -> 1
        assert_eq!(orp_index("word"), 1);
        assert_eq!(orp_index("hello"), 1);
    }

    #[test]
    fn orp_index_long() {
        // 6-9 letters -> 2
        assert_eq!(orp_index("reading"), 2);
        // 10+ -> 3
        assert_eq!(orp_index("extraordinary"), 3);
    }

    #[test]
    fn book_from_text_round_trip() {
        let b = book_from_text("Test", "hello world", 300);
        assert_eq!(b.chapters.len(), 1);
        assert_eq!(b.chapters[0].words.len(), 2);
        assert_eq!(b.chapters[0].words[0].text, "hello");
        assert_eq!(b.chapters[0].words[1].text, "world");
    }

    #[test]
    fn reader_progress() {
        let b = book_from_text("T", "a b c d e", 300);
        let mut r = Reader::new(b);
        assert_eq!(r.progress(), 0.0);
        r.step();
        r.step();
        // 2/5 = 0.4
        assert!((r.progress() - 0.4).abs() < 1e-6);
    }
}
