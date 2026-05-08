# RSVP-TUI Project - AGENTS.md

This document provides essential information for AI coding agents working on the RSVP-TUI project.

---

## Project Overview

RSVP-TUI is a **Terminal User Interface (TUI) for RSVP (Rapid Serial Visual Presentation) speed reading**. It's built with a hybrid **Python + Rust** architecture where:

- **Rust Backend (`rsvp-core`)**: Handles performance-critical text processing (tokenization, ORP calculation, file parsing)
- **Python Frontend (`rsvp-tui`)**: Provides the interactive TUI using Textual framework

### Key Features
- Word-by-word RSVP display with ORP (Optimal Recognition Point) highlighting
- Library management with SQLite persistence
- Position-linked note-taking system
- Support for Markdown, TXT, and EPUB formats
- Configurable reading speeds (100-1000 WPM)
- Punctuation pause multipliers
- Focus mode for distraction-free reading

---

## Project Structure

```
rspv/
├── rsvp-core/                  # Rust backend (PyO3 bindings)
│   ├── Cargo.toml              # Rust package config
│   ├── src/
│   │   ├── lib.rs              # PyO3 module entry point
│   │   ├── text_engine.rs      # Text tokenization & normalization
│   │   ├── rsvp_core.rs        # ORP & timing calculations
│   │   ├── file_parser.rs      # PDF/EPUB/Markdown parsers
│   │   ├── word_stats.rs       # Word frequency analysis
│   │   └── errors.rs           # Error handling types
│   └── tests/                  # Rust unit tests
│       ├── test_text_engine.rs
│       └── test_rsvp_core.rs
│
├── rsvp-tui/                   # Python TUI frontend
│   ├── pyproject.toml          # Python package config
│   ├── rsvp_tui/
│   │   ├── __init__.py         # Rust detection & exports
│   │   ├── __main__.py         # Module entry point
│   │   ├── app.py              # Main Textual app (base)
│   │   ├── app_complete.py     # Full TUI implementation
│   │   ├── cli.py              # Click CLI commands
│   │   ├── models.py           # Data classes (Book, Note, Config)
│   │   ├── fallbacks.py        # Pure Python fallbacks
│   │   ├── managers/
│   │   │   ├── library_manager.py   # SQLite library ops
│   │   │   └── note_manager.py      # Note CRUD operations
│   │   └── widgets/
│   │       ├── reader_display.py    # RSVP display widget
│   │       ├── library_view.py      # Book browser table
│   │       ├── note_panel.py        # Note sidebar
│   │       ├── progress_bar.py      # Progress indicator
│   │       └── settings_panel.py    # Settings form
│   └── tests/                  # Python tests
│
├── rsvp-reader/                # Legacy Python RSVP (reference)
├── rsvp-reader-web/            # React-based web reader (reference)
├── rsvp-reading/               # Svelte-based web reader (reference)
├── Speed-up-your-Python-with-Rust/  # PyO3 learning materials
│
├── launch_rsvp.py              # Launcher script
├── demo_tui.py                 # Standalone TUI demo
├── test_demo.py                # Test suite demo
├── note_demo.py                # Note-taking demo
├── sample_book.md              # Test content (422 words)
│
└── Documentation/
    ├── PRD.md                  # Product Requirements Document
    ├── ARCHITECTURE_SUMMARY.md # Architecture overview
    ├── TUI_FEATURES.md         # Feature documentation
    ├── PROJECT_SUMMARY.md      # Implementation summary
    ├── QUICKSTART.md           # Quick start guide
    ├── WORKFLOW.md             # User workflow diagrams
    └── ENHANCEMENTS.md         # Future roadmap
```

---

## Technology Stack

### Rust Backend (`rsvp-core`)
| Category | Dependencies |
|----------|--------------|
| Python Bindings | `pyo3` (v0.20) |
| Text Processing | `regex`, `unicode-segmentation`, `once_cell` |
| File Parsing | `epub` (v2.1), `html2text`, `lopdf` (optional) |
| Markdown | `pulldown-cmark` (optional) |
| Serialization | `serde`, `serde_json` |
| Error Handling | `thiserror`, `anyhow` |
| Logging | `log`, `env_logger` |

### Python Frontend (`rsvp-tui`)
| Category | Dependencies |
|----------|--------------|
| TUI Framework | `textual` (>=0.52.0) |
| CLI Framework | `click` (>=8.1.0) |
| Rich Text | `rich` (>=13.0.0) |
| Config/Paths | `platformdirs` (>=4.0.0) |
| Data Validation | `pydantic` (>=2.0.0) |
| TOML Config | `toml` (>=0.10.2) |

---

## Build and Development Commands

### Building the Rust Backend
```bash
cd rsvp-core

# Install maturin (if not already installed)
pip install maturin

# Build and install Rust extension for development
maturin develop --release

# Run Rust tests
cargo test

# Build release binary
cargo build --release
```

### Installing the Python Frontend
```bash
cd rsvp-tui

# Install in development mode
pip install -e "."

# Install with all optional dependencies
pip install -e ".[all]"

# Install with dev dependencies
pip install -e ".[dev]"
```

### Running the Application
```bash
# Method 1: Using installed CLI command
rsvp

# Method 2: Using launcher script
python launch_rsvp.py

# Method 3: Run as module
cd rsvp-tui && python -m rsvp_tui

# Method 4: Direct execution
python rsvp-tui/rsvp_tui/app_complete.py
```

### CLI Commands
```bash
# Launch TUI
rsvp

# Import a book
rsvp import ./my-book.md

# List all books
rsvp library --list

# Search books
rsvp library --search "python"

# Show book statistics
rsvp stats <book_id>

# Read specific file
rsvp read ./book.md --wpm 400 --focus
```

---

## Code Style Guidelines

### Rust Code Style
- Follow standard Rust formatting (`cargo fmt`)
- Use `snake_case` for functions and variables
- Use `PascalCase` for types and structs
- Error handling: Use `thiserror` for custom errors, `anyhow` for application errors
- Documentation: Use `///` for public items

### Python Code Style
- **Formatter**: Black (line length: 100)
- **Linter**: Ruff with the following rules:
  - E, F (pycodestyle, Pyflakes)
  - I (isort)
  - N (pep8-naming)
  - W (pycodestyle warnings)
  - UP (pyupgrade)
  - B (flake8-bugbear)
  - C4 (flake8-comprehensions)
  - SIM (flake8-simplify)
- **Type Checking**: mypy with strict mode
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Docstrings**: Google style or standard Sphinx

### Running Code Quality Tools
```bash
cd rsvp-tui

# Format code
black rsvp_tui/

# Lint code
ruff check rsvp_tui/

# Type check
mypy rsvp_tui/
```

---

## Testing Instructions

### Rust Tests
```bash
cd rsvp-core
cargo test

# Run benchmarks
cargo bench
```

### Python Tests
```bash
cd rsvp-tui
pytest

# Run with coverage
pytest --cov=rsvp_tui

# Run specific test file
pytest tests/test_specific.py
```

### Manual Testing
```bash
# Run the standalone demo (no dependencies required)
python demo_tui.py

# Run the note demo
python note_demo.py

# Run comprehensive tests
python test_demo.py
```

---

## Architecture Details

### Hybrid Rust/Python Design

```
┌─────────────────────────────────────────┐
│  Python TUI (Textual)                   │
│  - Screens, Widgets, Events            │
│  - Business logic                      │
└──────────────┬──────────────────────────┘
               │ PyO3 bindings
┌──────────────▼──────────────────────────┐
│  Rust Core (rsvp_core)                  │
│  - Text processing (10x faster)        │
│  - ORP calculation                     │
│  - File parsing                        │
└─────────────────────────────────────────┘
```

### Rust-Python Integration

Rust functions are exposed to Python via PyO3:

```rust
#[pyfunction]
pub fn calculate_orp_index(word: &str) -> usize

#[pyfunction]  
pub fn calculate_word_delay(word: &str, wpm: u32) -> u64

#[pyclass]
pub struct WordParts {
    #[pyo3(get)]
    pub before_orp: String,
    #[pyo3(get)]
    pub orp_char: String,
    #[pyo3(get)]
    pub after_orp: String,
}
```

### Graceful Degradation

The Python code gracefully handles missing Rust backend:

```python
# rsvp_tui/__init__.py
try:
    from rsvp_core import (
        tokenize_text,
        calculate_orp_index,
        # ... more functions
    )
    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    # Fall back to pure Python implementations
    from .fallbacks import (
        tokenize_text,
        calculate_orp_index,
        # ... more fallbacks
    )
```

---

## Data Storage

### SQLite Schema

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
```

### File Locations

| Data | Location |
|------|----------|
| Config | `~/.rsvp/config.json` |
| Library DB | `~/.rsvp/library.db` |
| Notes | `~/.rsvp/notes/` |
| Cache | `~/.rsvp/cache/` |

---

## Keyboard Shortcuts

### Global
| Key | Action |
|-----|--------|
| `?` | Show help |
| `q` | Quit |
| `l` | Library screen |

### Library Screen
| Key | Action |
|-----|--------|
| `↑/↓` | Navigate books |
| `Enter` | Select book |
| `r` | Read selected |
| `i` | Import book |
| `d` | Delete book |
| `/` | Search/filter |

### Reader Screen
| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `←/→` | Previous/Next word |
| `↑/↓` | Speed up/down |
| `Home` | Jump to start |
| `End` | Jump to end |
| `n` | Add note |
| `o` | Toggle ORP highlighting |
| `f` | Toggle focus mode |
| `r` | Restart reading |
| `Tab` | Toggle notes panel |
| `Esc` | Back to library |

---

## Development Conventions

### Adding New Features

1. **Rust Core**: If the feature involves text processing, add it to `rsvp-core` first
   - Add the function in the appropriate module
   - Expose it via `lib.rs` with `#[pyfunction]`
   - Add corresponding fallback in `rsvp_tui/fallbacks.py`

2. **Python UI**: Add UI components in `rsvp_tui/widgets/`
   - Create new widget inheriting from Textual's widget classes
   - Add reactive properties for state that affects rendering
   - Use CSS for styling (Textual's CSS system)

3. **Managers**: For data operations, use or extend managers in `rsvp_tui/managers/`
   - `LibraryManager`: Book import, retrieval, progress updates
   - `NoteManager`: Note CRUD operations

### ORP Algorithm

Optimal Recognition Point calculation:
- 1-3 letters: position 0
- 4-5 letters: position 1
- 6-9 letters: position 2
- 10+ letters: position 3+

### Word Timing

- Base delay: `60000 / WPM` milliseconds
- Punctuation pause: multiply by `punctuation_multiplier` (default 2.0)
- Configurable pause characters: `['.', '!', '?', ';', ':']`

---

## Security Considerations

1. **File Paths**: Always validate and sanitize file paths when importing books
2. **SQL Injection**: Use parameterized queries in `LibraryManager` and `NoteManager`
3. **Unicode**: Handle Unicode text carefully; Rust backend uses `unicode-segmentation`
4. **PDF Parsing**: PDF parsing can be memory-intensive; consider size limits

---

## Troubleshooting

### Rust Import Error
```
ImportError: cannot import name 'rsvp_core'
```
**Fix:**
```bash
cd rsvp-core
maturin develop --release
```

### Textual Display Issues
```
Terminal doesn't support required features
```
**Fix:**
- Use a modern terminal (Windows Terminal, iTerm2, GNOME Terminal)
- Set `TERM=xterm-256color`

### Unicode Errors
```
UnicodeEncodeError: can't encode character
```
**Fix:**
```bash
export PYTHONIOENCODING=utf-8
# On Windows:
chcp 65001
```

---

## Performance Targets

| Operation | Target | Status |
|-----------|--------|--------|
| Import 100KB markdown | < 100ms | ✅ |
| Tokenize 10K words | < 50ms | ✅ |
| Word display latency | < 16ms | ✅ |
| Library list (100 books) | < 100ms | ✅ |

---

## References

- **PRD.md**: Complete product requirements (850+ lines)
- **ARCHITECTURE_SUMMARY.md**: Architecture overview
- **TUI_FEATURES.md**: Feature documentation
- **QUICKSTART.md**: Quick start guide
- **WORKFLOW.md**: User workflow diagrams
- **ENHANCEMENTS.md**: Future roadmap

### External References
The project integrates learnings from:
- `ambevill/rsvp-reader` - Timing algorithms
- `yigit-cankurtaran/rsvp-reader-web` - EPUB patterns
- `thomaskolmans/rsvp-reading` - ORP calculation
- `PacktPublishing/Speed-up-your-Python-with-Rust` - PyO3 integration

---

## Language

All documentation, comments, and user-facing text in this project is written in **English**.
