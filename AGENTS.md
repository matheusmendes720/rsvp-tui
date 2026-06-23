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
│   ├── pyproject.toml          # maturin build-system
│   └── src/
│       ├── lib.rs              # PyO3 module entry point (53 exports)
│       ├── text_engine.rs      # Text tokenization & normalization
│       ├── rsvp_engine.rs      # ORP & timing calculations
│       ├── file_parser.rs      # PDF/EPUB/Markdown parsers
│       ├── word_stats.rs       # Word frequency analysis
│       └── errors.rs           # Error handling types
│
├── rsvp-cli/                   # Native Rust CLI (NEW)
│   ├── Cargo.toml              # clap + ratatui + crossterm
│   └── src/
│       ├── main.rs             # clap subcommand parser + dispatch
│       ├── reader.rs           # Ratatui RSVP reader (--native)
│       ├── config.rs           # path discovery
│       ├── output.rs           # JSON / plain output helpers
│       └── commands/           # one module per subcommand
│           ├── mod.rs
│           ├── doctor.rs       # rsvp doctor
│           ├── help.rs         # rsvp help
│           ├── import.rs       # rsvp import
│           ├── library.rs      # rsvp library
│           ├── remove.rs       # rsvp remove
│           ├── stats.rs        # rsvp stats
│           ├── tasks.rs        # rsvp tasks
│           ├── themes.rs       # rsvp themes
│           ├── version.rs      # rsvp version
│           └── where_cmd.rs    # rsvp where
│
├── rsvp-tui/                   # Python TUI frontend
│   ├── pyproject.toml          # Python package config (setuptools-rust)
│   ├── rsvp_tui/
│   │   ├── __init__.py         # Rust detection & exports
│   │   ├── __main__.py         # Module entry point
│   │   ├── app.py              # Main Textual app (legacy + new-UI router)
│   │   ├── cli.py              # Click CLI commands
│   │   ├── keybindings.py      # Central action → key map
│   │   ├── models.py           # Data classes (Book, Note, Config v2)
│   │   ├── fallbacks.py        # Pure Python fallbacks
│   │   ├── themes.py           # 8 built-in colour themes
│   │   ├── util.py             # safe_callback, atomic_write_text
│   │   ├── py.typed            # PEP 561 marker for downstream typing
│   │   ├── managers/
│   │   │   ├── library_manager.py   # SQLite library ops
│   │   │   ├── note_manager.py      # Note CRUD operations
│   │   │   └── config_manager.py    # Config persistence + migration
│   │   ├── screens/                 # Phase 1 screens (RSVP_NEW_UI=1)
│   │   │   ├── base.py              #   ScreenBase + FigureState
│   │   │   ├── library_screen.py    #   Book list
│   │   │   ├── reader_screen.py     #   Reading surface
│   │   │   ├── settings_screen.py   #   Live settings modal
│   │   │   ├── figure_picker.py     #   Figure picker modal
│   │   │   ├── command_palette.py   #   Fuzzy command palette
│   │   │   └── messages.py          #   Cross-screen message types
│   │   ├── figures/                 # Word-display strategies
│   │   │   ├── base.py              #   Figure base class
│   │   │   ├── word.py              #   Classic ORP word
│   │   │   ├── spritz.py            #   Spritz-style single word
│   │   │   ├── bionic.py            #   Bionic Reading
│   │   │   ├── chunk.py             #   N-gram chunks
│   │   │   ├── line.py              #   Multi-word line
│   │   │   ├── minimap.py           #   Mini progress bar
│   │   │   ├── pacer.py             #   Pacing indicator
│   │   │   ├── stats.py             #   Stats overlay
│   │   │   └── registry.py          #   Figure registry singleton
│   │   └── widgets/                 # Legacy widgets (deprecated)
│   │       ├── reader_display.py    #   re-export of WordFigure
│   │       ├── library_view.py      #   Book browser table
│   │       ├── note_panel.py        #   Note sidebar
│   │       ├── progress_bar.py      #   Progress indicator
│   │       └── settings_panel.py    #   re-export of SettingsScreen
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

### Workspace task surface (the canonical entry points)

Every project task is exposed as a real console script in `.venv/Scripts/`
after `uv sync`. Run any of them directly or via `uv run`:

| Task | Purpose |
|---|---|
| `uv run rsvp-tui` | Launch the interactive TUI (default) |
| `uv run rsvp-read <file>` | Read a book (alias: `r`) |
| `uv run rsvp-import <file>` | Import a book (alias: `i`) |
| `uv run rsvp-library` | Manage the book library (alias: `ls`) |
| `uv run rsvp-config` | Open the live settings UI |
| `uv run rsvp-palette` | Open the in-TUI command palette |
| `uv run rsvp-demo` | Launch the dependency-free standalone demo |
| `uv run rsvp-build` | Build the Rust extension + install the Python package |
| `uv run rsvp-dev` | Editable install (maturin develop --release) |
| `uv run rsvp-sync` | uv sync (use `--rebuild` to rebuild the Rust ext) |
| `uv run rsvp-clean` | Remove build/, dist/, __pycache__, eggs, caches |
| `uv run rsvp-test` | Run the pytest suite (extras forwarded) |
| `uv run rsvp-lint` | ruff check + black --check |
| `uv run rsvp-format` | black + ruff --fix |
| `uv run rsvp-typecheck` | mypy --strict |
| `uv run rsvp-verify` | Full quality gate: lint + typecheck + test |
| `uv run rsvp-docs` | Build man page + snapshot CLI help |
| `uv run rsvp-man` | Render / view / install rsvp.1 |
| `uv run rsvp-bench` | Run cargo benchmarks (Rust micro-benchmarks) |
| `uv run rsvp-tasks` | Print the live task table (this list) |

A `Makefile` and `bin/rsvv-task[.bat]` wrappers provide the same
surface for users who don't have `uv` on PATH. The full workspace
task discovery lives in `scripts/tasks.py` and the man page in
`man/rsvp.1`.

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

### Phase 1 Architecture (NEW)

The TUI was refactored in v0.3.0 to a proper Screen-based
architecture with pluggable "figures" (word-display strategies).
The legacy single-screen UI is still available by setting
``RSVP_NEW_UI=0`` (the default); the new screens-based UI is
opt-in via ``RSVP_NEW_UI=1``.

```
┌─────────────────────────────────────────────────────────────┐
│ app.py — RSVPApp (Textual App)                              │
│   │                                                          │
│   ├── if RSVP_NEW_UI=1 (new):                                │
│   │     └── screens/LibraryScreen                            │
│   │           └── (push) → screens/ReaderScreen              │
│   │                 ├── mounts active figure from registry   │
│   │                 ├── figure_picker modal                  │
│   │                 └── command_palette modal                │
│   │                                                          │
│   └── if RSVP_NEW_UI=0 (legacy):                             │
│         └── widgets/ReaderDisplay + LibraryView + ...        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
   ┌──────────────────── shared ──────────────────────┐
   │  managers/LibraryManager (SQLite)                 │
   │  managers/NoteManager                             │
   │  managers/ConfigManager (Config v2 schema)        │
   │  themes.get_theme(id)        — 8 built-in themes  │
   │  keybindings.Action          — action → key map   │
   └───────────────────────────────────────────────────┘
```

**Screens** (``rsvp_tui/screens/``):

* ``base.py`` — ``ScreenBase`` (shared boilerplate) +
  ``FigureState`` (singleton-ish state shared across screens).
* ``library_screen.py`` — book list; selecting one pushes
  ``ReaderScreen``.
* ``reader_screen.py`` — the reading surface. Mounts the
  active figure from the registry; exposes figure cycling,
  picker, palette; emits messages back to the app for
  cross-cutting concerns (config persistence, library sync).
* ``settings_screen.py`` — live settings modal; the
  replacement for the legacy ``widgets.SettingsPanel``.
* ``figure_picker.py`` — modal figure picker.
* ``command_palette.py`` — fuzzy command palette (18
  commands, ranked by ``SequenceMatcher`` similarity).
* ``messages.py`` — cross-screen message types
  (``BookOpened``, ``ConfigChanged``, ``FigureChanged``,
  ``FigureCompleted``, ``FigureStateAdvanced``).

**Figures** (``rsvp_tui/figures/``):

A figure is a single word-display strategy. The
``FigureRegistry`` singleton tracks the registered set and
the user's currently selected one (``config.figure_id``).

| Figure    | id         | Default keybinding |
|-----------|------------|--------------------|
| Word      | ``word``   | 1                  |
| Spritz    | ``spritz`` | 2                  |
| Bionic    | ``bionic`` | 3                  |
| Chunk     | ``chunk``  | 4                  |
| Line      | ``line``   | 5                  |
| Minimap   | ``minimap``| 6                  |
| Pacer     | ``pacer``  | 7                  |
| Stats     | ``stats``  | 8                  |

To add a new figure:

1. Subclass ``Figure`` in ``rsvp_tui/figures/your_figure.py``.
2. Implement ``render(self, state: FigureState) -> RenderableType``.
3. Register it in ``rsvp_tui/figures/registry.py``.
4. Add a test in ``rsvp-tui/tests/test_figures.py``.

The registry takes care of the rest — the picker modal
and the ``cycle_figure`` action both read from it.

**Config v2** (schema migration):

``Config.schema_version = 2`` introduces:
``theme``, ``figure_id``, ``figure_params`` (per-figure),
``keybindings`` (user-overridable action→key map).
``ConfigManager.load()`` migrates v1 configs on read.

### Adding New Features

1. **Rust Core**: If the feature involves text processing, add it to `rsvp-core` first
   - Add the function in the appropriate module
   - Expose it via `lib.rs` with `#[pyfunction]`
   - Add corresponding fallback in `rsvp_tui/fallbacks.py`

2. **Python UI (new screens path)**: If the feature is a new screen or modal,
   add it to `rsvp_tui/screens/`
   - Subclass `ScreenBase` (or `ModalScreen` for popups)
   - Emit cross-cutting changes as `messages.*` Message classes
   - Wire bindings via `BINDINGS = [...]` class attribute

3. **Python UI (figure)**: For a new word-display strategy, see
   "To add a new figure" above.

4. **Legacy Python UI**: If you must touch `widgets/`, prefer
   adding the new symbol under the new home and keeping a
   backward-compatible re-export at the legacy path. The
   `ReaderDisplay` and `SettingsPanel` re-exports use PEP 562
   lazy `__getattr__` so the deprecation warning fires only
   when the legacy symbol is actually used.

5. **Managers**: For data operations, use or extend managers in `rsvp_tui/managers/`
   - `LibraryManager`: Book import, retrieval, progress updates
   - `NoteManager`: Note CRUD operations
   - `ConfigManager`: Config load/save with v1→v2 migration

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

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **rspv** (1733 symbols, 3104 relationships, 131 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/rspv/context` | Codebase overview, check index freshness |
| `gitnexus://repo/rspv/clusters` | All functional areas |
| `gitnexus://repo/rspv/processes` | All execution flows |
| `gitnexus://repo/rspv/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |
| Work in the Rsvp_tui area (96 symbols) | `.claude/skills/generated/rsvp-tui/SKILL.md` |
| Work in the Components area (54 symbols) | `.claude/skills/generated/components/SKILL.md` |
| Work in the Widgets area (37 symbols) | `.claude/skills/generated/widgets/SKILL.md` |
| Work in the Rsvp-reader area (26 symbols) | `.claude/skills/generated/rsvp-reader/SKILL.md` |
| Work in the Managers area (20 symbols) | `.claude/skills/generated/managers/SKILL.md` |
| Work in the Cluster_4 area (7 symbols) | `.claude/skills/generated/cluster-4/SKILL.md` |
| Work in the Pages area (7 symbols) | `.claude/skills/generated/pages/SKILL.md` |
| Work in the Cluster_89 area (6 symbols) | `.claude/skills/generated/cluster-89/SKILL.md` |
| Work in the Cluster_6 area (5 symbols) | `.claude/skills/generated/cluster-6/SKILL.md` |
| Work in the Cluster_78 area (5 symbols) | `.claude/skills/generated/cluster-78/SKILL.md` |
| Work in the Cluster_87 area (5 symbols) | `.claude/skills/generated/cluster-87/SKILL.md` |
| Work in the Cluster_94 area (5 symbols) | `.claude/skills/generated/cluster-94/SKILL.md` |
| Work in the Cluster_5 area (4 symbols) | `.claude/skills/generated/cluster-5/SKILL.md` |
| Work in the Cluster_73 area (4 symbols) | `.claude/skills/generated/cluster-73/SKILL.md` |
| Work in the Cluster_85 area (4 symbols) | `.claude/skills/generated/cluster-85/SKILL.md` |
| Work in the Cluster_86 area (4 symbols) | `.claude/skills/generated/cluster-86/SKILL.md` |
| Work in the Misc area (3 symbols) | `.claude/skills/generated/misc/SKILL.md` |
| Work in the Cluster_61 area (3 symbols) | `.claude/skills/generated/cluster-61/SKILL.md` |
| Work in the Cluster_77 area (3 symbols) | `.claude/skills/generated/cluster-77/SKILL.md` |
| Work in the Cluster_91 area (3 symbols) | `.claude/skills/generated/cluster-91/SKILL.md` |

<!-- gitnexus:end -->
