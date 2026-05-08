# RSVP-TUI: Complete Feature Documentation

## Overview

A fully interactive Terminal User Interface for RSVP speed reading with Python + Rust.

---

## Features

### 1. Library Management Screen

```
======================================================================
                            LIBRARY
======================================================================

Search: [                                     ]

 Title                    Author      Progress  Last Read   Words  
 ----------------------------------------------------------------
> The Art of Speed Re...  Demo Auth   45%       2026-04-10  422   
  Python Design Patte...  GoF         12%       2026-04-08  15K   
  Clean Code              Martin      89%       2026-04-10  35K   
 

 [Read]  [Import]  [Delete]

----------------------------------------------------------------------
[q] Quit  [?] Help
```

**Features:**
- Browse all books in SQLite library
- Search/filter by title/author
- Sort by last read date, progress, title
- Import new books (Markdown, TXT, EPUB)
- Delete books with confirmation
- Persistent reading progress

**Keyboard Shortcuts:**
| Key | Action |
|-----|--------|
| ↑/↓ | Navigate books |
| Enter | Select book |
| r | Read selected book |
| i | Import new book |
| d | Delete selected book |
| / | Search/filter |
| q | Quit |
| ? | Help |

---

### 2. RSVP Reader Screen

```
======================================================================
                    The Art of Speed Reading
======================================================================

                            ext[r]aordinary
                                  |
                           [FOCUS LINE]


Word 280/422 (66%) - 300 WPM - ~0:28 remaining

[Play] [Back] [Next] [Restart] [Note] [ORP]

----------------------------------------------------------------------
NOTES (2 nearby)
[HERE] ORP positioning depends on word...
[+50] Don't sacrifice comprehension...
----------------------------------------------------------------------
[Space] Play/Pause  [←/→] Skip  [↑/↓] Speed  [n] Note  [f] Focus  [q] Quit
```

**Features:**
- RSVP word-by-word display
- Optimal Recognition Point (ORP) highlighting
- Configurable WPM (100-1000)
- Punctuation pause multipliers
- Progress tracking
- Context-aware notes sidebar
- Focus mode (minimal UI)

**Keyboard Shortcuts:**
| Key | Action |
|-----|--------|
| Space | Play/Pause |
| ←/→ | Previous/Next word |
| ↑/↓ | Speed up/down (25 WPM steps) |
| Home | Jump to start |
| End | Jump to end |
| n | Add note at current position |
| o | Toggle ORP highlighting |
| f | Toggle focus mode |
| r | Restart reading |
| Tab | Toggle notes panel |
| Escape | Back to library |

---

### 3. Add Note Modal

```
======================================================================
                        ADD NOTE
======================================================================

Position: Word 280
Context: 'focal'

Tags: [orp, technique                    ]

Content:
+--------------------------------------------------+
| ORP positioning depends on word length. I need   |
| to remember this for longer words.               |
+--------------------------------------------------+

              [Cancel]    [Save]
```

**Features:**
- Auto-captures word context
- Tag support (comma-separated)
- Multi-line note content
- Links to exact reading position

---

### 4. Import Book Modal

```
======================================================================
                        IMPORT BOOK
======================================================================

File path: [/home/user/books/article.md    ]

Supported formats:
  - Markdown (.md)
  - Plain Text (.txt)
  - EPUB (.epub)
  - PDF (.pdf) [coming soon]

              [Cancel]    [Import]
```

**Features:**
- Auto-detect file type
- Extract metadata (title, author)
- Chapter detection (Markdown headers)
- Cache tokenized words
- Progress bar during import

---

### 5. Settings Screen

```
======================================================================
                        SETTINGS
======================================================================

Reading Settings:
  Default WPM:        [300        ]
  Min WPM:            [100        ]
  Max WPM:            [1000       ]

Timing Settings:
  [x] Pause on punctuation
  Punctuation multiplier: [2.0    ]
  Pause characters: [.,!?,;:      ]

Display Settings:
  [x] Enable ORP highlighting
  [ ] Focus mode by default
  [x] Show progress bar

Storage:
  Library: ~/.rsvp/library.db
  Notes: ~/.rsvp/notes/
  Cache: ~/.rsvp/cache/

              [Cancel]    [Save]
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Library    │  │    Reader    │  │   Settings   │              │
│  │   Screen     │  │    Screen    │  │    Screen    │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└────────────────────────────────────┬────────────────────────────────┘
                                     │
┌────────────────────────────────────▼────────────────────────────────┐
│                      PYTHON BUSINESS LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   Library    │  │     Note     │  │    Config    │              │
│  │   Manager    │  │   Manager    │  │   Manager    │              │
│  │  (SQLite)    │  │  (JSON/md)   │  │   (JSON)     │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└────────────────────────────────────┬────────────────────────────────┘
                                     │ PyO3 Bindings
┌────────────────────────────────────▼────────────────────────────────┐
│                        RUST CORE LAYER                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Text Engine │  │  RSVP Core   │  │ File Parser  │              │
│  │  - tokenize  │  │  - orp calc  │  │  - markdown  │              │
│  │  - normalize │  │  - timing    │  │  - epub      │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
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
    added_date TIMESTAMP,
    last_read_date TIMESTAMP,
    total_reading_time_seconds INTEGER DEFAULT 0,
    cache_file_path TEXT,
    data JSON
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

-- Notes (stored as JSON files in ~/.rsvp/notes/)
{
    "id": "note_001",
    "book_id": "book_123",
    "word_index": 280,
    "content": "Important point about ORP",
    "tags": ["orp", "technique"],
    "created_at": "2026-04-10T09:30:00"
}
```

---

## Performance

| Operation | Time (Rust) | Time (Python) |
|-----------|-------------|---------------|
| Tokenize 10K words | ~5ms | ~20ms |
| Calculate ORP | ~0.1ms | ~0.5ms |
| Parse Markdown | ~10ms | ~50ms |
| Import 100KB book | ~50ms | ~200ms |

---

## CLI Commands

```bash
# Launch TUI
rsvp

# Import book
rsvp import ./my-book.md

# Read specific book
rsvp read book_id

# List library
rsvp library --list
rsvp library --search "python"

# Show statistics
rsvp stats book_id

# Export notes
rsvp export-notes book_id --format markdown
```

---

## Configuration

Config file: `~/.rsvp/config.json`

```json
{
    "default_wpm": 300,
    "min_wpm": 100,
    "max_wpm": 1000,
    "enable_orp": true,
    "pause_on_punctuation": true,
    "punctuation_multiplier": 2.0,
    "pause_chars": [".", "!", "?", ";", ":"],
    "focus_mode": false
}
```

---

## Keyboard Reference Card

### Global
```
?   Show help
q   Quit
l   Library screen
```

### Library Screen
```
↑/↓ Navigate
r    Read selected
i    Import book
d    Delete book
/    Search
```

### Reader Screen
```
Space    Play/Pause
←/→      Skip word
↑/↓      Speed
Home/End Jump to start/end
n        Add note
o        Toggle ORP
f        Focus mode
r        Restart
Tab      Toggle notes
Esc      Back to library
```

---

## Future Enhancements

### Phase 3: Skimming & Scanning
- **Skimming Mode**: Auto-extract topic sentences
- **Scanning Mode**: Full-text search with context
- **Outline View**: Chapter overview

### Phase 4: Advanced Features
- PDF support
- Reading statistics dashboard
- Spaced repetition for notes
- Sync across devices

---

## Installation

```bash
# Build Rust backend
cd rsvp-core
cargo build --release
maturin develop

# Install Python TUI
cd ../rsvp-tui
pip install -e ".[dev]"

# Run
rsvp
```

---

## Credits

This implementation combines insights from:
- `ambevill/rsvp-reader` - Timing algorithms
- `yigit-cankurtaran/rsvp-reader-web` - EPUB parsing patterns
- `thomaskolmans/rsvp-reading` - ORP calculation
- `PacktPublishing/Speed-up-your-Python-with-Rust` - PyO3 integration
