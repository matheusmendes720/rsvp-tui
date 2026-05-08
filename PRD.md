# RSVP Speed Reader - Product Requirements Document
## Python + Rust TUI Implementation

**Version:** 1.0  
**Date:** 2026-04-10  
**Status:** Draft

---

## 1. Executive Summary

A high-performance Terminal User Interface (TUI) RSVP (Rapid Serial Visual Presentation) speed reader built with Python for the interface layer and Rust for performance-critical text processing. Supports multiple document formats (.md, .pdf, .epub, .txt) with persistent library management, note-taking, and reading progress tracking.

### Key Differentiators
- **Hybrid Architecture:** Rust backend for speed, Python for TUX
- **Universal Format Support:** PDF, EPUB, Markdown, TXT
- **Integrated Note System:** Link notes to specific words/positions
- **Smart Timing:** ORP highlighting, punctuation pauses, word-length adjustments
- **Offline First:** Local library with SQLite/JSON storage

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           PYTHON TUI LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Main App    │  │  Reader View │  │  Library UI  │  │  Settings UI │  │
│  │  (Textual)   │  │  (RSVP Disp) │  │  (Table)     │  │  (Forms)     │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │                 │          │
│  ┌──────┴─────────────────┴─────────────────┴─────────────────┴──────┐   │
│  │                      Python Orchestration                          │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│  │  │ BookMgr  │  │ NoteMgr  │  │ Config   │  │ Storage  │          │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │   │
│  └───────┼─────────────┼─────────────┼─────────────┼────────────────┘   │
│          │             │             │             │                     │
└──────────┼─────────────┼─────────────┼─────────────┼─────────────────────┘
           │             │             │             │
           ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PYO3 BRIDGE (Rust)                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  TextEngine  │  │  FileParser  │  │  RSVP Core   │  │  WordStats   │  │
│  │  (tokenizer) │  │  (pdf/epub)  │  │  (timing)    │  │  (analyze)   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
           │             │             │             │
           ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA LAYER                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  SQLite DB   │  │  File Cache  │  │  Config JSON │  │  Note Store  │  │
│  │  (metadata)  │  │  (extracted) │  │  (settings)  │  │  (markdown)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Module Specifications

### 3.1 Rust Backend (`rsvp_core`)

#### Module: `text_engine`
**Purpose:** High-performance text processing and tokenization

```rust
// Functions exposed to Python via PyO3
#[pyfunction]
pub fn tokenize_text(text: &str) -> Vec<String>

#[pyfunction]
pub fn split_into_sentences(text: &str) -> Vec<String>

#[pyfunction]
pub fn normalize_whitespace(text: &str) -> String

#[pyfunction]
pub fn extract_words_with_positions(text: &str) -> Vec<(String, usize, usize)>
// Returns: (word, start_pos, end_pos)

#[pyfunction]
pub fn calculate_reading_complexity(text: &str) -> f64
// Returns: Flesch-Kincaid or similar score
```

#### Module: `file_parser`
**Purpose:** Extract text from various document formats

```rust
#[pyfunction]
pub fn parse_pdf_bytes(data: &[u8]) -> ParseResult

#[pyfunction]
pub fn parse_epub_bytes(data: &[u8]) -> ParseResult

#[pyfunction]
pub fn parse_markdown(text: &str) -> ParseResult

#[pyclass]
pub struct ParseResult {
    #[pyo3(get)]
    pub title: String,
    #[pyo3(get)]
    pub author: String,
    #[pyo3(get)]
    pub chapters: Vec<Chapter>,
    #[pyo3(get)]
    pub plain_text: String,
    #[pyo3(get)]
    pub word_count: usize,
}

#[pyclass]
pub struct Chapter {
    #[pyo3(get, set)]
    pub title: String,
    #[pyo3(get)]
    pub start_word_index: usize,
    #[pyo3(get)]
    pub end_word_index: usize,
    #[pyo3(get)]
    pub content: String,
}
```

#### Module: `rsvp_core`
**Purpose:** Core RSVP timing and display logic

```rust
#[pyfunction]
pub fn calculate_orp_index(word: &str) -> usize
// Optimal Recognition Point calculation

#[pyfunction]
pub fn calculate_word_delay(
    word: &str,
    wpm: u32,
    punctuation_multiplier: f32,
    pause_chars: Vec<char>
) -> u64
// Returns: delay in milliseconds

#[pyfunction]
pub fn split_word_for_display(word: &str, orp_index: usize) -> WordParts

#[pyclass]
pub struct WordParts {
    #[pyo3(get)]
    pub before_orp: String,
    #[pyo3(get)]
    pub orp_char: String,
    #[pyo3(get)]
    pub after_orp: String,
}

#[pyfunction]
pub fn estimate_reading_time(word_count: usize, wpm: u32) -> (u32, u32)
// Returns: (minutes, seconds)

#[pyfunction]
pub fn should_pause_at_punctuation(word: &str, pause_chars: Vec<char>) -> bool
```

#### Module: `word_stats`
**Purpose:** Word frequency and complexity analysis

```rust
#[pyfunction]
pub fn calculate_word_frequency_distribution(words: Vec<String>) -> HashMap<String, u32>

#[pyfunction]
pub fn identify_difficult_words(words: Vec<String>, threshold: f32) -> Vec<String>

#[pyfunction]
pub fn generate_reading_heatmap_data(
    words: Vec<String>,
    window_size: usize
) -> Vec<f32>
// Returns complexity score per window for heatmap visualization
```

### 3.2 Python Frontend (`rsvp_tui`)

#### Module: `app.py`
**Main Application Controller**

```python
class RSVPApp(App):
    """Main Textual application"""
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("l", "show_library", "Library"),
        ("s", "show_settings", "Settings"),
        ("space", "toggle_play", "Play/Pause"),
        ("left", "prev_word", "Previous"),
        ("right", "next_word", "Next"),
        ("up", "increase_speed", "Faster"),
        ("down", "decrease_speed", "Slower"),
        ("n", "add_note", "Add Note"),
    ]
    
    def __init__(self):
        self.library_manager: LibraryManager
        self.note_manager: NoteManager
        self.config: Config
        self.current_book: Optional[Book] = None
        self.current_session: Optional[ReadingSession] = None
```

#### Module: `widgets/reader_display.py`
**RSVP Display Widget**

```python
class ReaderDisplay(Static):
    """Displays words with ORP highlighting"""
    
    def __init__(self):
        self.current_word: str = ""
        self.word_index: int = 0
        self.total_words: int = 0
        self.wpm: int = 300
        self.is_playing: bool = False
        self._timer: Optional[Timer] = None
        
    def render(self) -> RenderableType:
        """Render current word with ORP highlight"""
        parts = rsvp_core.split_word_for_display(
            self.current_word,
            rsvp_core.calculate_orp_index(self.current_word)
        )
        return self._format_word_display(parts)
    
    def _format_word_display(self, parts: WordParts) -> Panel:
        """Create centered display with ORP highlighted"""
        ...
    
    def next_word(self) -> None:
        """Advance to next word with timing calculation"""
        delay = rsvp_core.calculate_word_delay(
            self.current_word,
            self.wpm,
            self.config.punctuation_multiplier,
            self.config.pause_chars
        )
        ...
```

#### Module: `widgets/library_view.py`
**Library Browser**

```python
class LibraryView(DataTable):
    """Table view of all books in library"""
    
    COLUMNS = ["Title", "Author", "Progress", "Last Read", "Words"]
    
    def on_mount(self):
        self.load_books()
    
    def load_books(self):
        books = self.app.library_manager.list_books()
        # Populate table
    
    def action_open_book(self, book_id: str):
        book = self.app.library_manager.get_book(book_id)
        self.app.open_book(book)
```

#### Module: `widgets/note_panel.py`
**Note-taking Interface**

```python
class NotePanel(Static):
    """Side panel for viewing and adding notes"""
    
    def __init__(self):
        self.current_book_id: Optional[str] = None
        self.current_word_index: int = 0
        
    def render(self) -> RenderableType:
        notes = self.app.note_manager.get_notes_for_position(
            self.current_book_id,
            self.current_word_index
        )
        return self._format_notes(notes)
    
    def compose(self) -> ComposeResult:
        yield Button("Add Note", id="add-note")
        yield Static(id="notes-list")
```

#### Module: `managers/library_manager.py`
**Book Library Management**

```python
class LibraryManager:
    """Manages book library and metadata"""
    
    def __init__(self, db_path: Path):
        self.db = Database(db_path)
        self.cache_dir = Path.home() / ".rsvp" / "cache"
    
    def import_book(self, file_path: Path) -> Book:
        """Import a book from file"""
        # Detect file type
        # Parse with Rust backend
        # Store metadata in SQLite
        # Cache extracted text
        ...
    
    def list_books(self, filters: Optional[BookFilter] = None) -> List[Book]:
        """List all books with optional filtering"""
        ...
    
    def get_book(self, book_id: str) -> Optional[Book]:
        """Get book by ID"""
        ...
    
    def update_progress(self, book_id: str, word_index: int):
        """Update reading progress"""
        ...
    
    def delete_book(self, book_id: str):
        """Remove book from library"""
        ...
```

#### Module: `managers/note_manager.py`
**Note Management**

```python
class NoteManager:
    """Manages notes linked to reading positions"""
    
    def __init__(self, notes_dir: Path):
        self.notes_dir = notes_dir
        self.notes_dir.mkdir(parents=True, exist_ok=True)
    
    def create_note(
        self,
        book_id: str,
        word_index: int,
        content: str,
        tags: List[str] = None
    ) -> Note:
        """Create a new note at specific position"""
        ...
    
    def get_notes_for_book(self, book_id: str) -> List[Note]:
        """Get all notes for a book"""
        ...
    
    def get_notes_for_position(
        self,
        book_id: str,
        word_index: int,
        context_window: int = 10
    ) -> List[Note]:
        """Get notes near current position"""
        ...
    
    def export_notes_to_markdown(self, book_id: str) -> Path:
        """Export all notes as markdown file"""
        ...
```

#### Module: `config.py`
**Configuration Management**

```python
@dataclass
class Config:
    """Application configuration"""
    
    # Reading settings
    default_wpm: int = 300
    min_wpm: int = 100
    max_wpm: int = 1000
    wpm_step: int = 25
    
    # Timing settings
    punctuation_multiplier: float = 2.0
    pause_on_punctuation: bool = True
    pause_chars: List[str] = field(default_factory=lambda: ['.', '!', '?', ';', ':'])
    comma_pause_multiplier: float = 1.5
    
    # Display settings
    enable_orp: bool = True
    focus_mode: bool = False
    show_progress_bar: bool = True
    show_context_words: bool = False  # Show prev/next words
    
    # Storage paths
    library_db_path: Path = field(default_factory=lambda: Path.home() / ".rsvp" / "library.db")
    notes_dir: Path = field(default_factory=lambda: Path.home() / ".rsvp" / "notes")
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".rsvp" / "cache")
    
    def save(self):
        """Save config to JSON"""
        ...
    
    @classmethod
    def load(cls) -> "Config":
        """Load config from JSON or create default"""
        ...
```

---

## 4. Data Models

### 4.1 Core Data Classes

```python
@dataclass
class Book:
    """Represents a book/document"""
    id: str
    title: str
    author: str
    file_path: Optional[Path]
    file_type: str  # "pdf", "epub", "md", "txt"
    
    # Content
    word_count: int
    chapters: List[Chapter]
    
    # Reading state
    current_word_index: int = 0
    current_chapter_index: int = 0
    
    # Metadata
    added_date: datetime = field(default_factory=datetime.now)
    last_read_date: Optional[datetime] = None
    total_reading_time_seconds: int = 0
    
    # Statistics
    completion_percentage: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "file_path": str(self.file_path) if self.file_path else None,
            "file_type": self.file_type,
            "word_count": self.word_count,
            "chapters": [c.to_dict() for c in self.chapters],
            "current_word_index": self.current_word_index,
            "current_chapter_index": self.current_chapter_index,
            "added_date": self.added_date.isoformat(),
            "last_read_date": self.last_read_date.isoformat() if self.last_read_date else None,
            "total_reading_time_seconds": self.total_reading_time_seconds,
        }


@dataclass
class Chapter:
    """Represents a chapter/section"""
    title: str
    start_word_index: int
    end_word_index: int
    word_count: int
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "start_word_index": self.start_word_index,
            "end_word_index": self.end_word_index,
            "word_count": self.word_count,
        }


@dataclass
class Note:
    """Represents a note linked to reading position"""
    id: str
    book_id: str
    word_index: int
    chapter_index: int
    content: str
    tags: List[str]
    created_at: datetime
    updated_at: datetime
    word_context: str  # The actual word being read when note created
    
    def to_markdown(self) -> str:
        """Convert note to markdown format"""
        return f"""## Note at word {self.word_index}

**Context:** {self.word_context}
**Chapter:** {self.chapter_index}
**Tags:** {', '.join(self.tags)}
**Created:** {self.created_at}

{self.content}
---
"""


@dataclass
class ReadingSession:
    """Represents an active reading session"""
    book_id: str
    start_time: datetime
    current_word_index: int
    wpm: int
    is_playing: bool = False
    
    # Statistics
    words_read: int = 0
    pauses_count: int = 0
    total_pause_time: timedelta = field(default_factory=lambda: timedelta(0))
    
    def get_statistics(self) -> SessionStats:
        """Calculate session statistics"""
        ...


@dataclass
class SessionStats:
    """Statistics for a reading session"""
    duration_seconds: int
    words_read: int
    average_wpm: float
    effective_wpm: float  # Account for pauses
    completion_percentage: float
```

---

## 5. CLI Interface

### 5.1 Command Structure

```bash
# Main entry point
rsvp [COMMAND] [OPTIONS]

# Commands
rsvp read <book_id>              # Start reading a book
rsvp import <file>               # Import a new book
rsvp library                     # Open library browser
rsvp library list                # List all books (CLI output)
rsvp notes                       # Open notes manager
rsvp stats <book_id>             # Show reading statistics
rsvp config                      # Open settings UI
rsvp serve <book_id>             # Start server mode (optional web)

# Options
--wpm, -w <number>              # Set reading speed
--chapter, -c <number>          # Start at chapter
--word, -p <number>             # Start at word position
--focus-mode, -f                # Start in focus mode
--no-orp                        # Disable ORP highlighting
--export-notes <format>         # Export notes (md, json)
```

### 5.2 Interactive TUI Screens

```
┌─────────────────────────────────────────────────────────────────┐
│  LIBRARY VIEW                                                    │
├─────────────────────────────────────────────────────────────────┤
│  ╔═══════════════════════════════════════════════════════════╗  │
│  ║  Title                Author         Progress  Last Read  ║  │
│  ╠═══════════════════════════════════════════════════════════╣  │
│  ║> The Rust Book       Rust Team      45%       2026-04-09 ║  │
│  ║  Design Patterns      Gang of Four   12%       2026-04-08 ║  │
│  ║  Clean Code           Robert Martin  89%       2026-04-10 ║  │
│  ║  [+ Import New Book]                                      ║  │
│  ╚═══════════════════════════════════════════════════════════╝  │
│                                                                  │
│  [Enter] Open  [d] Delete  [s] Search  [i] Import  [q] Quit     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  READER VIEW (Focus Mode)                                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                                                                  │
│                                                                  │
│                     ┌────────────────────┐                      │
│                     │     [pre] v [suf]   │  ← ORP highlighted  │
│                     └────────────────────┘                      │
│                          │                                       │
│                          ▼                                       │
│                    [red focus line]                             │
│                                                                  │
│  ═══════════════════════════════════════════════════════════   │
│  The Rust Book - Chapter 3: Common Concepts                    │
│  Word 1,245 / 50,000 | 45% | ~8 min remaining | 300 WPM        │
│                                                                  │
│  [Space] Play/Pause  [←/→] Skip  [↑/↓] Speed  [n] Note  [q] Quit│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  READER VIEW (Normal Mode)                                       │
├─────────────────────────────────────────────────────────────────┤
│  [Library] [Settings] [Notes: 3]              [Save Progress]   │
│                                                                  │
│                                                                  │
│                     ┌────────────────────┐                      │
│                     │     reading        │                      │
│                     └────────────────────┘                      │
│                          │                                       │
│                    [red focus line]                             │
│                                                                  │
│  ═══════════════════════════════════════════════════════════   │
│  The Rust Book - Chapter 3: Common Concepts                    │
│  Word 1,245 / 50,000 | 45% | ~8 min remaining | 300 WPM        │
│                                                                  │
│  [Space] Play/Pause  [←/→] Skip  [↑/↓] Speed  [Tab] Focus Mode │
│  [n] Add Note  [c] Chapters  [j] Jump to  [s] Statistics       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. File Format Support

### 6.1 Supported Formats

| Format | Extension | Parser | Notes |
|--------|-----------|--------|-------|
| Markdown | .md, .markdown | Rust (pulldown-cmark) | Preserves structure |
| PDF | .pdf | Rust (pdf-extract or poppler) | May need external dep |
| EPUB | .epub | Rust (epub crate) | Full metadata support |
| Plain Text | .txt | Rust (native) | Auto-detect encoding |
| reStructuredText | .rst | Rust (optional) | Sphinx docs |

### 6.2 Import Pipeline

```
File Path
    │
    ▼
┌─────────────────┐
│ Detect Format   │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬──────────┐
    ▼         ▼          ▼          ▼
┌───────┐ ┌───────┐ ┌─────────┐ ┌───────┐
│  PDF  │ │ EPUB  │ │ Markdown│ │  TXT  │
└───┬───┘ └───┬───┘ └────┬────┘ └───┬───┘
    │         │          │          │
    └─────────┴──────────┴──────────┘
              │
              ▼
    ┌─────────────────────┐
    │ Rust Parse Function │
    │ - Extract text      │
    │ - Identify chapters │
    │ - Get metadata      │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ Tokenize & Index    │
    │ - Split words       │
    │ - Map positions     │
    │ - Build chapter idx │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │ Save to Library     │
    │ - SQLite metadata   │
    │ - Cache extracted   │
    │ - Create Book obj   │
    └─────────────────────┘
```

---

## 7. Storage Architecture

### 7.1 SQLite Schema

```sql
-- Books table
CREATE TABLE books (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    file_path TEXT,
    file_type TEXT,
    word_count INTEGER,
    current_word_index INTEGER DEFAULT 0,
    current_chapter_index INTEGER DEFAULT 0,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_read_date TIMESTAMP,
    total_reading_time_seconds INTEGER DEFAULT 0,
    cache_file_path TEXT
);

-- Chapters table
CREATE TABLE chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT,
    chapter_index INTEGER,
    title TEXT,
    start_word_index INTEGER,
    end_word_index INTEGER,
    FOREIGN KEY (book_id) REFERENCES books(id)
);

-- Notes table
CREATE TABLE notes (
    id TEXT PRIMARY KEY,
    book_id TEXT,
    word_index INTEGER,
    chapter_index INTEGER,
    content TEXT,
    tags TEXT,  -- JSON array
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    word_context TEXT,
    FOREIGN KEY (book_id) REFERENCES books(id)
);

-- Reading sessions table
CREATE TABLE reading_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP,
    start_word_index INTEGER,
    end_word_index INTEGER,
    average_wpm INTEGER,
    FOREIGN KEY (book_id) REFERENCES books(id)
);
```

### 7.2 File Cache Structure

```
~/.rsvp/
├── config.json
├── library.db
├── cache/
│   ├── books/
│   │   ├── <book_id>.json      # Tokenized words array
│   │   └── <book_id>.txt       # Plain text backup
│   └── covers/
│       └── <book_id>.jpg       # Extracted cover image
└── notes/
    ├── <book_id>/
    │   ├── metadata.json       # Note index
    │   └── <note_id>.md        # Individual note files
    └── exports/
        └── <book_id>_notes.md  # Exported notes
```

---

## 8. Keyboard Shortcuts

### 8.1 Global Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit application |
| `l` | Open library |
| `s` | Open settings |
| `?` / `h` | Show help |

### 8.2 Reader Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `Tab` | Toggle focus mode |
| `←` / `→` | Previous/Next word |
| `↑` / `↓` | Increase/Decrease WPM |
| `Home` | Jump to start |
| `End` | Jump to end |
| `j` | Jump to position |
| `c` | Chapter list |
| `n` | Add note |
| `m` | Toggle ORP highlight |
| `f` | Toggle focus mode |
| `r` | Reset to beginning |
| `b` | Jump back 10 words |
| `e` | Export notes |

### 8.3 Library Shortcuts

| Key | Action |
|-----|--------|
| `Enter` | Open selected book |
| `i` | Import new book |
| `d` / `Delete` | Delete book |
| `/` | Search |
| `s` | Sort |

---

## 9. Rust + Python Integration Details

### 9.1 PyO3 Module Structure

```rust
// src/lib.rs
use pyo3::prelude::*;

mod text_engine;
mod file_parser;
mod rsvp_core;
mod word_stats;

use text_engine::__pyo3_get_function_tokenize_text;
use file_parser::__pyo3_get_function_parse_pdf_bytes;
use rsvp_core::__pyo3_get_function_calculate_orp_index;

#[pymodule]
fn rsvp_core(_py: Python, m: &PyModule) -> PyResult<()> {
    // Text engine
    m.add_wrapped(wrap_pyfunction!(tokenize_text))?;
    m.add_wrapped(wrap_pyfunction!(split_into_sentences))?;
    m.add_wrapped(wrap_pyfunction!(normalize_whitespace))?;
    
    // File parser
    m.add_wrapped(wrap_pyfunction!(parse_pdf_bytes))?;
    m.add_wrapped(wrap_pyfunction!(parse_epub_bytes))?;
    m.add_wrapped(wrap_pyfunction!(parse_markdown))?;
    m.add_class::<ParseResult>()?;
    m.add_class::<Chapter>()?;
    
    // RSVP core
    m.add_wrapped(wrap_pyfunction!(calculate_orp_index))?;
    m.add_wrapped(wrap_pyfunction!(calculate_word_delay))?;
    m.add_wrapped(wrap_pyfunction!(split_word_for_display))?;
    m.add_class::<WordParts>()?;
    
    // Word stats
    m.add_wrapped(wrap_pyfunction!(calculate_word_frequency_distribution))?;
    m.add_wrapped(wrap_pyfunction!(identify_difficult_words))?;
    
    Ok(())
}
```

### 9.2 Cargo.toml

```toml
[package]
name = "rsvp-core"
version = "0.1.0"
edition = "2021"

[lib]
name = "rsvp_core"
crate-type = ["cdylib", "rlib"]

[dependencies]
pyo3 = { version = "0.20", features = ["extension-module"] }

# Text processing
regex = "1.10"
unicode-segmentation = "1.11"

# File parsing
pdf-extract = "0.7"  # or alternative
epub = "2.1"
pulldown-cmark = "0.9"

# Serialization
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"

[dev-dependencies]
criterion = "0.5"
```

### 9.3 Python side import

```python
# rsvp_tui/__init__.py
try:
    from rsvp_core import (
        tokenize_text,
        parse_pdf_bytes,
        parse_epub_bytes,
        parse_markdown,
        calculate_orp_index,
        calculate_word_delay,
        split_word_for_display,
        ParseResult,
        Chapter,
        WordParts,
    )
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Fall back to pure Python implementations
    from .fallbacks import (
        tokenize_text,
        parse_pdf_bytes,
        # ... etc
    )
```

---

## 10. Testing Strategy

### 10.1 Rust Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_calculate_orp_index() {
        assert_eq!(calculate_orp_index("a"), 0);
        assert_eq!(calculate_orp_index("the"), 0);
        assert_eq!(calculate_orp_index("hello"), 1);
        assert_eq!(calculate_orp_index("reading"), 2);
        assert_eq!(calculate_orp_index("extraordinary"), 3);
    }

    #[test]
    fn test_tokenize_text() {
        let text = "Hello, world! This is a test.";
        let words = tokenize_text(text);
        assert_eq!(words, vec!["Hello,", "world!", "This", "is", "a", "test."]);
    }

    #[test]
    fn test_calculate_word_delay() {
        // At 300 WPM, base delay is 200ms
        let delay = calculate_word_delay("hello", 300, 2.0, vec!['.', '!']);
        assert_eq!(delay, 200);
        
        // With punctuation, should be 400ms (2x)
        let delay = calculate_word_delay("hello!", 300, 2.0, vec!['.', '!']);
        assert_eq!(delay, 400);
    }
}
```

### 10.2 Python Integration Tests

```python
import pytest
from rsvp_tui.managers.library_manager import LibraryManager

class TestLibraryManager:
    def test_import_markdown(self, tmp_path):
        manager = LibraryManager(tmp_path / "test.db")
        
        # Create test markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# Chapter 1\n\nThis is a test.")
        
        book = manager.import_book(md_file)
        
        assert book.title == "test"
        assert book.file_type == "md"
        assert book.word_count == 5
```

---

## 11. Performance Requirements

### 11.1 Target Metrics

| Operation | Target Time | Max Time |
|-----------|-------------|----------|
| Import 100KB markdown | < 100ms | < 500ms |
| Import 1MB PDF | < 2s | < 5s |
| Tokenize 10K words | < 50ms | < 200ms |
| Word display latency | < 16ms | < 50ms |
| Library list (100 books) | < 100ms | < 500ms |
| Save progress | < 50ms | < 200ms |

### 11.2 Optimization Strategies

1. **Lazy Loading:** Only load current chapter words into memory
2. **Caching:** Cache tokenized text to disk
3. **Background Parsing:** Parse large PDFs in background thread
4. **Word Pre-computation:** Pre-calculate ORP indices and delays

---

## 12. Future Enhancements (Backlog)

### Phase 2
- [ ] Web interface (share TUI backend)
- [ ] Sync across devices (cloud storage)
- [ ] Spaced repetition for notes
- [ ] Reading analytics dashboard
- [ ] Plugin system for custom parsers

### Phase 3
- [ ] OCR for scanned PDFs
- [ ] Text-to-speech integration
- [ ] Collaborative reading/annotations
- [ ] Mobile apps (use same Rust backend)

---

## 13. Development Phases

### Phase 1: MVP (Weeks 1-2)
- [ ] Rust text engine (tokenization, ORP)
- [ ] Basic Python TUI with Textual
- [ ] Markdown and TXT support
- [ ] Simple library management
- [ ] Reading with play/pause

### Phase 2: Core Features (Weeks 3-4)
- [ ] PDF and EPUB support (Rust)
- [ ] Note-taking system
- [ ] Progress tracking
- [ ] Settings/configuration
- [ ] Focus mode

### Phase 3: Polish (Weeks 5-6)
- [ ] Advanced timing options
- [ ] Statistics and analytics
- [ ] Import/export features
- [ ] Performance optimization
- [ ] Testing and documentation

---

**End of PRD**
