# RSVP TUI

A high-performance Terminal User Interface (TUI) for RSVP (Rapid Serial Visual Presentation) speed reading.

## Features

- **Hybrid Architecture**: Rust backend for speed, Python (Textual) for TUI
- **Multiple Formats**: PDF, EPUB, Markdown, Plain Text
- **Optimal Recognition Point (ORP)**: Highlighted focal point for faster reading
- **Smart Timing**: Punctuation pauses, word-length adjustments
- **Note Taking**: Link notes to specific reading positions
- **Library Management**: SQLite-based book library with progress tracking
- **Focus Mode**: Minimal distraction reading interface

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/rsvp-tui.git
cd rsvp-tui

# Install with Rust backend (recommended)
pip install -e "./rsvp-core"
pip install -e "./rsvp-tui"

# Or install Python only (slower, fallback implementations)
pip install -e "./rsvp-tui"
```

### Requirements

- Python 3.10+
- Rust 1.70+ (for building native extensions)

## Usage

### Launch TUI

```bash
rsvp
```

### Import a Book

```bash
rsvp import ./my-book.epub
rsvp import ./article.md
```

### Read a Book

```bash
# Read by file
rsvp read ./my-book.epub

# Read with options
rsvp read ./book.pdf --wpm 400 --focus
```

### Library Commands

```bash
# List books
rsvp library --list

# Search books
rsvp library --search "python"

# View statistics
rsvp stats-all
```

### Keyboard Shortcuts

#### Reading Mode

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `←` / `→` | Previous/Next word |
| `↑` / `↓` | Increase/Decrease speed |
| `Home` | Jump to start |
| `End` | Jump to end |
| `f` | Toggle focus mode |
| `n` | Add note |
| `l` | Library view |
| `s` | Settings |
| `q` | Quit |

## Architecture

```
┌─────────────────────────────────────┐
│        Python TUI (Textual)          │
│  ┌──────────┐  ┌──────────┐        │
│  │  Reader  │  │  Library │        │
│  │  Display │  │   View   │        │
│  └────┬─────┘  └────┬─────┘        │
└───────┼─────────────┼───────────────┘
        │             │
        ▼             ▼
┌─────────────────────────────────────┐
│    PyO3 Bridge (Rust Bindings)       │
│  ┌──────────┐  ┌──────────┐        │
│  │  Text    │  │  RSVP    │        │
│  │  Engine  │  │  Core    │        │
│  └──────────┘  └──────────┘        │
└─────────────────────────────────────┘
```

## Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install in development mode
pip install -e "./rsvp-core"
pip install -e "./rsvp-tui[dev]"
```

### Running Tests

```bash
# Rust tests
cd rsvp-core
cargo test

# Python tests
cd rsvp-tui
pytest
```

### Project Structure

```
rspv/
├── PRD.md                  # Product Requirements Document
├── rsvp-core/              # Rust backend
│   ├── src/
│   │   ├── lib.rs          # PyO3 module
│   │   ├── text_engine.rs  # Text processing
│   │   ├── rsvp_core.rs    # RSVP timing
│   │   ├── file_parser.rs  # File parsing
│   │   └── word_stats.rs   # Statistics
│   └── Cargo.toml
└── rsvp-tui/               # Python TUI
    ├── rsvp_tui/
    │   ├── app.py          # Main app
    │   ├── cli.py          # CLI commands
    │   ├── models.py       # Data models
    │   ├── managers/       # Business logic
    │   └── widgets/        # TUI widgets
    └── pyproject.toml
```

## License

MIT License - see LICENSE file for details.
