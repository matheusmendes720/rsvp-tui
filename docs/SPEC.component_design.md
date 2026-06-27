# SPEC — Component Design

> **Sources:** `PRD.md §3, §5` (module specs + CLI), `TUI_FEATURES.md §2–5`
> (per-screen widget breakdowns), `ARCHITECTURE_SUMMARY.md §Key Components`.
>
> **Convention:** every component name below is tagged with the layer it
> belongs to (`[CLI]`, `[TUI]`, `[BUSINESS]`, `[BRIDGE]`, `[CORE]`, `[DATA]`)
> so the layering can be checked at a glance.

---

## 1. Layering (the canonical stack)

```
┌─────────────────────────────────────────────────────────────────────┐
│  L1 — CLI SURFACE          [CLI]      rsvp <subcommand> [args]     │
│            │   click-based group of subcommands                     │
├─────────────────────────────────────────────────────────────────────┤
│  L2 — TUI SURFACE          [TUI]      Textual App + Screens        │
│            │   composable screens + modal widgets                  │
├─────────────────────────────────────────────────────────────────────┤
│  L3 — BUSINESS LOGIC       [BUSINESS] LibraryMgr / NoteMgr / Config│
│            │   orchestrators, persistence policy                   │
├─────────────────────────────────────────────────────────────────────┤
│  L4 — PYTHON <-> RUST      [BRIDGE]   rsvp_core (PyO3 module)     │
│            │   thin facade; falls back to pure-Python if missing   │
├─────────────────────────────────────────────────────────────────────┤
│  L5 — RUST CORE            [CORE]     text_engine / file_parser /  │
│            │                rsvp_core / word_stats                 │
├─────────────────────────────────────────────────────────────────────┤
│  L6 — PERSISTENCE          [DATA]     SQLite + cache/ + notes/     │
└─────────────────────────────────────────────────────────────────────┘
```

Source: `PRD.md §2` (architecture diagram) + `ARCHITECTURE_SUMMARY.md §Architecture Layers`.

### 1.1 Layer rules (NF-COMP-*)

| ID | Rule | Source |
|----|------|--------|
| NF-COMP-01 | L1 (CLI) **must not** import L2 (TUI) — only the reverse (`click` group can call into the Python entry point, but TUI is its own entry) | derived from PRD §5.1 |
| NF-COMP-02 | L3 (business) is the only layer allowed to write to L6 (persistence) | derived from PRD §2 |
| NF-COMP-03 | L4 (bridge) **must** expose `RUST_AVAILABLE: bool` so callers can pick the fallback path | PRD §9.3 |
| NF-COMP-04 | L5 (Rust core) is the only layer that performs ORP / tokenization / file parsing | PRD §9 |
| NF-COMP-05 | All public L3 methods must be safe to call from both sync CLI and async TUI event loops | derived from NF-COMP-01 |

---

## 2. Component inventory (per layer)

Each row gives the **canonical name**, the **source doc paragraph** that
introduces it, and the **role in one sentence**.

### 2.1 L1 — CLI surface (`[CLI]`)

| Component | Source | Role |
|-----------|--------|------|
| `cli` (Click group) | PRD §5.1 | Root `rsvp` command group; dispatches to subcommands |
| `cli.read` | PRD §5.1 | `rsvp read <book_id>` — start reading a book (TUI launch with pre-loaded book) |
| `cli.import` | PRD §5.1 | `rsvp import <file>` — import + persist a book |
| `cli.library` | PRD §5.1 | `rsvp library [--list]` — list library (CLI / TUI bridge) |
| `cli.notes` | PRD §5.1 | `rsvp notes` — open notes manager |
| `cli.stats` | PRD §5.1 | `rsvp stats <book_id>` — show reading statistics |
| `cli.config` | PRD §5.1 | `rsvp config` — open settings UI |
| `cli.serve` | PRD §5.1 | `rsvp serve <book_id>` — start server mode (placeholder; Phase 4) |

CLI surface flags (PRD §5.1):

| Flag | Long form | Applies to | Default |
|------|-----------|------------|---------|
| `--wpm`, `-w` | int | read | 300 |
| `--chapter`, `-c` | int | read | 0 |
| `--word`, `-p` | int | read | 0 |
| `--focus-mode`, `-f` | bool | read | False |
| `--no-orp` | bool | read | False |
| `--export-notes` | str (`md`\|`json`) | read | None |

### 2.2 L2 — TUI surface (`[TUI]`)

| Component | Source | Role |
|-----------|--------|------|
| `RSVPApp` | PRD §3.2 app.py | Top-level Textual `App`; routes key events to active screen |
| `ReaderDisplay` | PRD §3.2 widgets/reader_display.py | One-word RSVP display with ORP highlight |
| `LibraryView` | PRD §3.2 widgets/library_view.py | Book browser DataTable |
| `NotePanel` | PRD §3.2 widgets/note_panel.py | Position-aware notes sidebar |
| `SettingsPanel` | TUI §5 | Settings form (WPM, ORP, pauses, paths) |
| `ImportModal` | TUI §4 | File-path input + format auto-detect |
| `AddNoteModal` | TUI §3 | Tag + content form bound to current position |
| `ProgressBar` | ARCH §Widgets | Thin progress indicator widget |
| `CommandPalette` | derived (see §3.4) | Fuzzy command launcher (`Ctrl+P` — **key conflict to resolve**) |

#### 2.2.1 TUI binding declarations

`RSVPApp.BINDINGS` (PRD §3.2 — copy verbatim, expand):

```python
BINDINGS = [
    ("q",       "quit",         "Quit"),
    ("l",       "show_library", "Library"),
    ("s",       "show_settings","Settings"),
    ("space",   "toggle_play",  "Play/Pause"),
    ("left",    "prev_word",    "Previous"),
    ("right",   "next_word",    "Next"),
    ("up",      "increase_speed","Faster"),
    ("down",    "decrease_speed","Slower"),
    ("n",       "add_note",     "Add Note"),
]
```

Additional bindings the spec **adds** to satisfy PRD §8.2 + TUI §2:

| Action | Key | Source |
|--------|-----|--------|
| `restart` | `r` | PRD §8.2 + TUI §2 |
| `toggle_focus` | `f` and `Tab` | PRD §8.2 (uses both) + TUI §2 |
| `toggle_orp` | `m` (PRD) / `o` (TUI) — conflict | PRD §8.2 vs TUI §2 |
| `jump_start` | `Home` | PRD §8.2 |
| `jump_end` | `End` | PRD §8.2 |
| `jump_position` | `j` | PRD §8.2 |
| `jump_back_10` | `b` | PRD §8.2 |
| `export_notes` | `e` | PRD §8.2 |
| `chapter_list` | `c` | PRD §8.2 |
| `enter_scan` | `/` | WORKFLOW §RSVP Mode |
| `enter_skim` | `m` (after first press) | WORKFLOW §RSVP Mode ("m Switch mode") |
| `palette` | `Ctrl+P` | derived from TUI §Keyboard Reference ("?" shows help — palette inferred as natural extension) |

### 2.3 L3 — Business logic (`[BUSINESS]`)

| Component | Source | Role |
|-----------|--------|------|
| `LibraryManager(db_path)` | PRD §3.2 managers/library_manager.py | CRUD over books, progress, chapters |
| `NoteManager(notes_dir)` | PRD §3.2 managers/note_manager.py | Position-linked note CRUD + Markdown export |
| `Config` (dataclass) | PRD §3.2 config.py | Application config + persistence |

#### 2.3.1 `LibraryManager` API surface (from PRD §3.2 verbatim)

| Method | Returns | Behavior |
|--------|---------|----------|
| `import_book(file_path: Path) -> Book` | `Book` | Detect format → parse via Rust → cache → SQLite row |
| `list_books(filters: Optional[BookFilter] = None) -> List[Book]` | `List[Book]` | Optionally filtered list |
| `get_book(book_id: str) -> Optional[Book]` | `Book?` | Single book fetch |
| `update_progress(book_id: str, word_index: int)` | None | Persist position + bump `last_read_date` |
| `delete_book(book_id: str)` | None | Remove from library + cache |

#### 2.3.2 `NoteManager` API surface (from PRD §3.2 verbatim)

| Method | Returns | Behavior |
|--------|---------|----------|
| `create_note(book_id, word_index, content, tags=None) -> Note` | `Note` | Persist to JSON + Markdown sidecar |
| `get_notes_for_book(book_id) -> List[Note]` | `List[Note]` | All notes for a book |
| `get_notes_for_position(book_id, word_index, context_window=10) -> List[Note]` | `List[Note]` | Notes near position |
| `export_notes_to_markdown(book_id) -> Path` | `Path` | Write combined Markdown file |

#### 2.3.3 `Config` schema (from PRD §3.2 verbatim, fully expanded)

| Field | Type | Default | UI binding |
|-------|------|---------|------------|
| `default_wpm` | int | 300 | TUI Settings: "Default WPM" |
| `min_wpm` | int | 100 | TUI Settings: "Min WPM" |
| `max_wpm` | int | 1000 | TUI Settings: "Max WPM" |
| `wpm_step` | int | 25 | (not in TUI Settings UI) |
| `punctuation_multiplier` | float | 2.0 | TUI Settings: "Punctuation multiplier" |
| `pause_on_punctuation` | bool | True | TUI Settings: "Pause on punctuation" |
| `pause_chars` | List[str] | `['.', '!', '?', ';', ':']` | TUI Settings: "Pause characters" |
| `comma_pause_multiplier` | float | 1.5 | (not in TUI Settings UI) |
| `enable_orp` | bool | True | TUI Settings: "Enable ORP highlighting" |
| `focus_mode` | bool | False | TUI Settings: "Focus mode by default" |
| `show_progress_bar` | bool | True | TUI Settings: "Show progress bar" |
| `show_context_words` | bool | False | (not in TUI Settings UI) |
| `library_db_path` | Path | `~/.rsvp/library.db` | TUI Settings: read-only display |
| `notes_dir` | Path | `~/.rsvp/notes` | TUI Settings: read-only display |
| `cache_dir` | Path | `~/.rsvp/cache` | TUI Settings: read-only display |

Methods (PRD §3.2):

| Method | Purpose |
|--------|---------|
| `save()` | JSON-serialize to `~/.rsvp/config.json` |
| `Config.load() -> Config` | Load or default-construct |

### 2.4 L4 — Bridge (`[BRIDGE]`)

| Component | Source | Role |
|-----------|--------|------|
| `rsvp_core` PyO3 module | PRD §9.1 | Rust→Python exposure (53 named functions in actual code; spec covers the PRD-defined subset) |
| `__init__.py` (Python facade) | PRD §9.3 | `try import rsvp_core`; sets `RUST_AVAILABLE`; re-exports symbols; falls back to `fallbacks.py` |

### 2.5 L5 — Rust core (`[CORE]`)

| Module | Source | Public functions | Public types |
|--------|--------|-------------------|--------------|
| `text_engine` | PRD §3.1 | `tokenize_text`, `split_into_sentences`, `normalize_whitespace`, `extract_words_with_positions`, `calculate_reading_complexity` | — |
| `file_parser` | PRD §3.1 | `parse_pdf_bytes`, `parse_epub_bytes`, `parse_markdown` | `ParseResult`, `Chapter` |
| `rsvp_core` | PRD §3.1 | `calculate_orp_index`, `calculate_word_delay`, `split_word_for_display`, `estimate_reading_time`, `should_pause_at_punctuation` | `WordParts` |
| `word_stats` | PRD §3.1 | `calculate_word_frequency_distribution`, `identify_difficult_words`, `generate_reading_heatmap_data` | — |

PyO3 module body (PRD §9.1):

```rust
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

### 2.6 L6 — Persistence (`[DATA]`)

See `SPEC.data_architecture.md` for the complete breakdown. Components listed
here for completeness:

| Component | Storage |
|-----------|---------|
| `books` (table) | SQLite |
| `chapters` (table) | SQLite |
| `notes` (table) | SQLite (per PRD §7.1) **and** JSON-on-disk per book_id (per TUI §Data Storage — see conflict note) |
| `reading_sessions` (table) | SQLite |
| `book_fts` (virtual FTS5 table) | SQLite (Phase 3) |
| `word_index` (table) | SQLite (Phase 3) |
| `cache/books/<book_id>.json` | disk (tokenized words) |
| `cache/books/<book_id>.txt` | disk (plain text backup) |
| `cache/covers/<book_id>.jpg` | disk (cover image) |
| `notes/<book_id>/metadata.json` | disk (note index) |
| `notes/<book_id>/<note_id>.md` | disk (one file per note) |
| `notes/exports/<book_id>_notes.md` | disk (combined export) |
| `config.json` | disk (single file at `~/.rsvp/config.json`) |

---

## 3. Per-screen component decomposition

### 3.1 Library screen

```
LibraryScreen
├── Header (Textual Header)
│   └── Title: "LIBRARY"
├── SearchBar (Input)
│   └── placeholder: "[                  ]"
├── BookTable (DataTable, columns from PRD §3.2)
│   └── COLUMNS = ["Title", "Author", "Progress", "Last Read", "Words"]
├── ActionBar (Horizontal with Buttons)
│   └── [Read]  [Import]  [Delete]
└── Footer (Textual Footer)
    └── "[q] Quit  [?] Help"
```

Bindings (TUI §1):

| Key | Action |
|-----|--------|
| `↑/↓` | Navigate |
| `Enter` | Select (opens Reader) |
| `r` | Read selected |
| `i` | Import |
| `d` | Delete (with confirmation) |
| `/` | Focus SearchBar |
| `q` | Quit |
| `?` | Help |

### 3.2 Reader screen

```
ReaderScreen
├── Header — book title + chapter
├── FocusLine (Vertical, conditional)
│   └── shows current chapter
├── WordDisplay (ReaderDisplay)
│   └── one word, ORP-highlighted, centered
├── ProgressPanel (Static)
│   └── "Word N/Total (P%) - WPM WPM - ~M:SS remaining"
├── ActionBar (Horizontal with Buttons)
│   └── [Play] [Back] [Next] [Restart] [Note] [ORP]
├── NotesPanel (NotePanel, toggle with Tab)
│   └── list of notes within context window
└── Footer
    └── "[Space] Play/Pause  [←/→] Skip  [↑/↓] Speed  [n] Note  [f] Focus  [q] Quit"
```

### 3.3 Settings screen

```
SettingsScreen (modal)
├── Form
│   ├── Section "Reading Settings"
│   │   ├── Input  default_wpm        (300)
│   │   ├── Input  min_wpm            (100)
│   │   └── Input  max_wpm            (1000)
│   ├── Section "Timing Settings"
│   │   ├── Checkbox pause_on_punctuation (True)
│   │   ├── Input  punctuation_multiplier  (2.0)
│   │   └── Input  pause_chars             ('.,!?,;:')
│   ├── Section "Display Settings"
│   │   ├── Checkbox enable_orp              (True)
│   │   ├── Checkbox focus_mode              (False)
│   │   └── Checkbox show_progress_bar       (True)
│   └── Section "Storage"
│       └── Static   "Library: ~/.rsvp/library.db"
│                   "Notes:   ~/.rsvp/notes/"
│                   "Cache:   ~/.rsvp/cache/"
└── ActionBar
    └── [Cancel] [Save]
```

### 3.4 Keybinding source-of-truth (resolution policy)

The PRD and TUI_FEATURES disagree on:

| Conflict | PRD | TUI_FEATURES | Resolution |
|----------|-----|--------------|------------|
| Toggle ORP | `m` | `o` | Spec retains both; binding registry picks one. PRD is authoritative for §8.2 (explicit table) |
| Toggle focus | `f` and `Tab` | `f` | Both per PRD |
| Switch mode (skim↔RSVP) | — | `m` | Conflicts with PRD's `m` for ORP |

**Spec recommendation (to be ratified):** ORP toggle = `o` (TUI choice) and
mode switch = `m` (TUI choice), making PRD §8.2's `m` entry obsolete. This
is flagged as a **planning decision** still pending sign-off.

---

## 4. Import pipeline component decomposition

The import pipeline (PRD §6.2) decomposes into five stages, each implemented
by exactly one L5 module plus one L3 helper:

| Stage | L5 module | L3 helper | Input | Output |
|-------|-----------|-----------|-------|--------|
| 1. Detect format | n/a | `LibraryManager._detect_format(path)` | `Path` | `(format_str, parser_fn)` |
| 2. Parse | `file_parser` (`parse_*_bytes` / `parse_markdown`) | `LibraryManager.import_book` | bytes / str | `ParseResult` |
| 3. Tokenize + index | `text_engine` (`tokenize_text`, `extract_words_with_positions`) | `_build_word_index(parse_result)` | `ParseResult` | `List[Token]` |
| 4. Cache to disk | n/a | `_write_cache(book_id, tokens)` | `List[Token]` | `cache/books/<id>.json` |
| 5. Persist metadata | n/a | `_insert_book_row(...)` | `Book` | SQLite row |

NF-IMP-* (pipeline invariants):

| ID | Invariant |
|----|-----------|
| NF-IMP-01 | Stages 1→5 are sequential; failure of any stage aborts without partial side effects (use a `try/except` rollback at the orchestrator) |
| NF-IMP-02 | Cache files are written **before** SQLite row, so a crashed import can be recovered from cache |
| NF-IMP-03 | Token list length must equal `ParseResult.word_count` (assertion at stage 3→4) |

---

## 5. Cross-cutting components (referenced but not localized)

| Component | Source | Role | Where it lives |
|-----------|--------|------|----------------|
| `BookFilter` (dataclass) | PRD §3.2 managers/LibraryManager.list_books signature | Filter for `list_books` | `managers/library_manager.py` (inferred) |
| `WordParts` (PyO3 class) | PRD §3.1 + §9.1 | Rust-side split-word result | `rsvp_core/src/rsvp_core.rs` |
| `ParseResult`, `Chapter` | PRD §3.1 + §9.1 | File-parse outputs | `rsvp_core/src/file_parser.rs` |
| `FALLBACKS_AVAILABLE` flag | NF derived from PRD §9.3 | True if Rust not importable | `rsvp_tui/__init__.py` |

---

## 6. Spec-coverage check

| Section | Source | Coverage |
|---------|--------|----------|
| §1 Layering | PRD §2 + ARCH §Layers | complete |
| §2.1 CLI | PRD §5.1 | complete (8 subcommands + flags) |
| §2.2 TUI | PRD §3.2, TUI §2–5 | complete (8 widgets) |
| §2.3 Business | PRD §3.2 managers/config | complete (15 fields + 9 methods) |
| §2.4 Bridge | PRD §9.1, §9.3 | complete |
| §2.5 Rust core | PRD §3.1, §9.1 | complete (4 modules, 13 functions, 3 types) |
| §2.6 Persistence | PRD §7, TUI §Data | complete (4 tables + 7 on-disk artifacts) — note conflicts in §7 |
| §3 Per-screen | TUI §1–5 | complete |
| §4 Import pipeline | PRD §6.2 | complete (5 stages) |
| §5 Cross-cutting | synthesized | complete |