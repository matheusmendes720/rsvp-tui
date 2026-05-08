# GEMINI.md

## Project Overview
**wirzard_point/rspv** is a high-performance RSVP (Rapid Serial Visual Presentation) speed reading system. It features a hybrid architecture with a performance-critical Rust core and a feature-rich Python TUI frontend.

### Key Components
- **rsvp-core**: Rust backend for text processing, ORP calculation, and document parsing (PyO3 bindings).
- **rsvp-tui**: Python frontend using the Textual framework for an interactive terminal experience.
- **rsvp-reader-web**: React-based web implementation.
- **rsvp-reading**: Svelte-based web implementation.

## Core Technologies
- **Rust**: pyo3, regex, unicode-segmentation, lopdf, pulldown-cmark.
- **Python**: textual, click, rich, pydantic, sqlite3.
- **Data Models**: Pydantic models for configuration and SQLite for library/note management.
- **Persistence**: SQLite for book metadata and reading progress; JSON/Markdown for notes and configuration.

## Building and Running

### Prerequisites
- Rust toolchain (cargo, rustc)
- Python 3.10+
- `uv` (optional, but recommended for Python dependency management)

### 1. Build Rust Backend (`rsvp-core`)
The Rust backend must be compiled and installed as a Python module.
```bash
cd rsvp-core
pip install maturin
maturin develop --release
```

### 2. Install Python TUI (`rsvp-tui`)
```bash
cd rsvp-tui
pip install -e "."
```

### 3. Run the Application
You can run the application using the installed CLI or the launcher script.
```bash
# Launch TUI
rsvp

# Or use launcher
python launch_rsvp.py
```

### Key CLI Commands
- `rsvp`: Launch the interactive TUI.
- `rsvp import <path>`: Import a book into the library.
- `rsvp library --list`: List all imported books.
- `rsvp read <id>`: Open a book for reading at a specific WPM.

## Development Conventions

### Hybrid Architecture & Fallbacks
- **Rust First**: Performance-critical logic (tokenization, ORP, parsing) belongs in `rsvp-core`.
- **Python Fallbacks**: Every Rust-backed function MUST have a pure Python implementation in `rsvp_tui/fallbacks.py` to ensure the app runs even if the Rust module is missing.

### Coding Standards
- **Rust**: Follow standard formatting (`cargo fmt`). Use `thiserror` for library errors.
- **Python**: Use `black` (line length: 100) and `ruff` for linting.
- **Types**: Strict type hinting is required for all Python code (`mypy`).

### Testing
- **Rust Tests**: `cd rsvp-core && cargo test`
- **Python Tests**: `cd rsvp-tui && pytest`
- **Manual Verification**: Use `launch_rsvp.py` or `demo_tui.py` for quick TUI verification.

## Directory Structure
- `/rsvp-core`: Rust performance core and document parsers.
- `/rsvp-tui`: Textual-based TUI application.
- `/data`: Sample documents and test data.
- `/rsvp-reader-web` & `/rsvp-reading`: Alternative web-based implementations.
- `AGENTS.md`: Detailed guidance for AI agents.
- `PRD.md`: Comprehensive product requirements.
