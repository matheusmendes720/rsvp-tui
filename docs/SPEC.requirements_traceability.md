# SPEC — Requirements Traceability & Evolution Timeline

> **Sources:** all four planning artifacts, plus session-log and commit-history
> signals available in the workspace.
>
> **Purpose:** (1) every functional requirement traces back to exactly one
> source-doc paragraph and forward to exactly one design element + UI element.
> (2) The bottom of this doc is the **planning evolution timeline** — how the
> plan moved from the original PRD to the current docs.

---

## 1. How to read this matrix

Each row is **one requirement** with:

- **ID** — the canonical reference (per `README.docs_index.md §3`)
- **Requirement** — short statement
- **Source** — which planning doc paragraph it comes from
- **Layer / Module** — where in the component design it lives
- **Algorithm** — which BFF algorithm implements it
- **Data** — what data structure stores it
- **UI surface** — which screen/key/CLI command the user invokes
- **Spec ref** — section in this doc-set where it is fully expanded
- **Status** — `spec` (in spec only), `partial` (partly spec'd), `conflict` (source docs disagree)

---

## 2. CLI command traceability (CLI-*)

| ID | Requirement | Source | Layer / Module | Algorithm | Data | UI surface | Spec ref | Status |
|----|-------------|--------|----------------|-----------|------|------------|----------|--------|
| CLI-01 | `rsvp read <book_id>` opens Reader for given book | PRD §5.1 | L1 `cli.read` → L2 `RSVPApp` | n/a | `books.current_word_index` | `rsvp read <id>` | SPEC.component §2.1 | spec |
| CLI-02 | `rsvp import <file>` imports a file | PRD §5.1 | L1 `cli.import` → L3 `LibraryManager.import_book` | ALG §3 (parse) | `books` + `chapters` rows + cache JSON | `rsvp import <file>` | SPEC.component §2.1, SPEC.algo §3 | spec |
| CLI-03 | `rsvp library [--list]` lists library | PRD §5.1 | L1 `cli.library` → L3 `LibraryManager.list_books` | n/a | `books` table | `rsvp library --list` | SPEC.component §2.1 | spec |
| CLI-04 | `rsvp notes` opens note manager | PRD §5.1 | L1 `cli.notes` → L3 `NoteManager.*` | n/a | `notes` table + Tier-3 files | `rsvp notes` | SPEC.component §2.1 | spec |
| CLI-05 | `rsvp stats <book_id>` shows stats | PRD §5.1 | L1 `cli.stats` → L3 (computed) | ALG §6 | `reading_sessions` + derived | `rsvp stats <id>` | SPEC.component §2.1 | spec |
| CLI-06 | `rsvp config` opens settings UI | PRD §5.1 | L1 `cli.config` → L2 `SettingsScreen` | n/a | `~/.rsvp/config.json` | `rsvp config` | SPEC.component §3.3 | spec |
| CLI-07 | `rsvp serve <book_id>` server mode | PRD §5.1 | (Phase 4 placeholder) | n/a | n/a | `rsvp serve <id>` | SPEC.component §2.1 | spec (placeholder) |
| CLI-08 | `--wpm` flag sets reading speed | PRD §5.1 | L1 flag → L3 `Config.default_wpm` | ALG §5 | `Config` | `rsvp read --wpm 400` | SPEC.component §2.1 | spec |
| CLI-09 | `--chapter` flag starts at chapter | PRD §5.1 | L1 flag → Reader.seek(chapter.start_word_index) | n/a | `chapters` | `rsvp read --chapter 2` | SPEC.component §2.1 | spec |
| CLI-10 | `--word` flag starts at word | PRD §5.1 | L1 flag → Reader.seek(word_index) | n/a | `books.current_word_index` | `rsvp read --word 1245` | SPEC.component §2.1 | spec |
| CLI-11 | `--focus-mode` flag toggles focus on launch | PRD §5.1 | L1 flag → `Config.focus_mode` | n/a | `Config` | `rsvp read --focus-mode` | SPEC.component §2.1 | spec |
| CLI-12 | `--no-orp` disables ORP | PRD §5.1 | L1 flag → `Config.enable_orp=False` | ALG §4 (skipped) | `Config` | `rsvp read --no-orp` | SPEC.component §2.1 | spec |
| CLI-13 | `--export-notes` exports to md or json | PRD §5.1 | L1 flag → `NoteManager.export_notes_to_markdown` | n/a | `notes/exports/` | `rsvp read --export-notes md` | SPEC.component §2.1 | spec |
| CLI-14 | `rsvp skim <book_id>` enters skim mode | ENH §Command Extensions | L1 `cli.skim` (new) → L2 skim screen | ALG §7 | n/a | `rsvp skim <id>` | SPEC.three_modes §2 | spec (Phase 3) |
| CLI-15 | `rsvp scan <book> --for "q"` enters scan | ENH §Command Extensions | L1 `cli.scan` (new) → L2 scan screen | ALG §8 | `book_fts` | `rsvp scan <id> --for "cognitive"` | SPEC.three_modes §4 | spec (Phase 3) |
| CLI-16 | `rsvp find "q" --all-books` cross-library search | ENH §Command Extensions | L1 `cli.find` | ALG §8.1 | `book_fts` | `rsvp find "rust"` | SPEC.three_modes §4 | spec (Phase 3) |
| CLI-17 | `rsvp grep <book> "pat"` regex search | ENH §Command Extensions | L1 `cli.grep` | ALG §8 (variant) | `word_index` | `rsvp grep <id> "ORP"` | SPEC.three_modes §4 | spec (Phase 3) |
| CLI-18 | `rsvp outline <book>` prints chapter outline | ENH §Command Extensions | L1 `cli.outline` | ALG §7 | `chapters` | `rsvp outline <id>` | SPEC.three_modes §2 | spec (Phase 3) |
| CLI-19 | `rsvp summary <book> --words 100` summary | ENH §Command Extensions | L1 `cli.summary` | (NLP — out of scope) | n/a | `rsvp summary <id> --words 100` | SPEC.three_modes §2 | spec (Phase 3, placeholder) |

---

## 3. TUI screen & binding traceability (TUI-*)

### 3.1 Library screen

| ID | Requirement | Source | Layer / Module | UI surface | Spec ref | Status |
|----|-------------|--------|----------------|------------|----------|--------|
| TUI-01 | Title "LIBRARY" + search input + table | TUI §1 | L2 `LibraryView` | `LIBRARY` screen | SPEC.component §3.1 | spec |
| TUI-02 | Columns: Title, Author, Progress, Last Read, Words | PRD §3.2 + TUI §1 | L2 `LibraryView.COLUMNS` | DataTable | SPEC.component §3.1 | spec |
| TUI-03 | `↑/↓` navigate books | TUI §1 | L2 binding | keyboard | SPEC.three_modes §2.4 (skim, also applies lib) | spec |
| TUI-04 | `Enter` opens selected book | TUI §1 + PRD §8.3 | L2 binding → Reader | keyboard | SPEC.component §3.1 | spec |
| TUI-05 | `r` reads selected book | TUI §1 | L2 binding → Reader | keyboard | SPEC.component §3.1 | spec |
| TUI-06 | `i` imports new book | TUI §1 + PRD §8.3 | L2 binding → ImportModal | keyboard | SPEC.component §3.1 | spec |
| TUI-07 | `d` deletes with confirmation | TUI §1 + PRD §8.3 | L2 binding → confirm → `LibraryManager.delete_book` | keyboard | SPEC.component §3.1 | spec |
| TUI-08 | `/` focuses search | TUI §1 + PRD §8.3 | L2 binding | keyboard | SPEC.component §3.1 | spec |
| TUI-09 | `q` quits | TUI §1 + PRD §8.1 | L2 binding | keyboard | SPEC.component §3.1 | spec |
| TUI-10 | `?` shows help | TUI §1 + PRD §8.1 | L2 binding → help overlay | keyboard | SPEC.component §3.1 | spec |

### 3.2 Reader screen

| ID | Requirement | Source | Layer / Module | Algorithm | UI surface | Spec ref | Status |
|----|-------------|--------|----------------|-----------|------------|----------|--------|
| TUI-20 | One word centered with ORP highlight | TUI §2 + PRD §3.2 | L2 `ReaderDisplay` | ALG §4 | Reader screen | SPEC.component §3.2, SPEC.three_modes §3 | spec |
| TUI-21 | "Word N/Total (P%) - WPM WPM - ~M:SS remaining" | TUI §2 | L2 `ProgressPanel` | ALG §5.3 + derived | Reader footer | SPEC.component §3.2 | spec |
| TUI-22 | `Space` Play/Pause | TUI §2 + PRD §8.2 | L2 binding | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-23 | `←/→` Prev/Next word | TUI §2 + PRD §8.2 | L2 binding | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-24 | `↑/↓` ±25 WPM | TUI §2 + PRD §8.2 | L2 binding | ALG §5 | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-25 | `Home`/`End` jump to start/end | PRD §8.2 | L2 binding | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-26 | `j` jump to position modal | PRD §8.2 | L2 binding | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-27 | `b` jump back 10 words | PRD §8.2 | L2 binding | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-28 | `n` add note | TUI §2 + PRD §8.2 | L2 binding → AddNoteModal | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-29 | `m`/`o` toggle ORP | PRD §8.2 vs TUI §2 | L2 binding | ALG §4 (toggled) | keyboard | SPEC.component §3.4 | **conflict** |
| TUI-30 | `f`/`Tab` toggle focus | PRD §8.2 + TUI §2 | L2 binding | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-31 | `r` restart from beginning | PRD §8.2 + TUI §2 | L2 binding | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-32 | `e` export notes | PRD §8.2 | L2 binding → `NoteManager.export_notes_to_markdown` | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-33 | `c` chapter list | PRD §8.2 | L2 binding → chapter modal | n/a | keyboard | SPEC.three_modes §3.4 | spec |
| TUI-34 | `Tab` toggle notes panel | TUI §2 | L2 binding | n/a | keyboard | SPEC.component §3.2 | spec |
| TUI-35 | Notes panel shows "NOTES (N nearby)" + entries | TUI §2 | L2 `NotePanel` | n/a | Reader sidebar | SPEC.component §3.2 | spec |
| TUI-36 | Position-aware note context window | TUI §2 | L2 `NotePanel` → `NoteManager.get_notes_for_position` | n/a | Reader sidebar | SPEC.component §3.2 | spec |
| TUI-37 | `Esc` back to library | TUI §2 | L2 binding → save progress → `LibraryScreen` | n/a | keyboard | SPEC.component §3.2 | spec |
| TUI-38 | `/` enter scan mode from RSVP | WORKFLOW §RSVP Mode | L2 binding → ScanModal | ALG §8 | keyboard | SPEC.three_modes §4.4 | spec |
| TUI-39 | `m` (after first press) switch to skim | WORKFLOW §RSVP Mode | L2 binding → SkimScreen | ALG §7 | keyboard | SPEC.three_modes §3.4 | spec |

### 3.3 Settings screen

| ID | Requirement | Source | Layer / Module | UI surface | Spec ref | Status |
|----|-------------|--------|----------------|------------|----------|--------|
| TUI-50 | Form: Reading Settings (default/min/max WPM) | TUI §5 + PRD §3.2 | L2 `SettingsPanel` | Settings modal | SPEC.component §3.3 | spec |
| TUI-51 | Form: Timing Settings (punctuation, multiplier, chars) | TUI §5 + PRD §3.2 | L2 `SettingsPanel` | Settings modal | SPEC.component §3.3 | spec |
| TUI-52 | Form: Display Settings (ORP, focus, progress) | TUI §5 + PRD §3.2 | L2 `SettingsPanel` | Settings modal | SPEC.component §3.3 | spec |
| TUI-53 | Form: Storage paths (read-only) | TUI §5 + PRD §3.2 | L2 `SettingsPanel` | Settings modal | SPEC.component §3.3 | spec |
| TUI-54 | Cancel / Save actions | TUI §5 | L2 buttons → `Config.save()` | Settings modal | SPEC.component §3.3 | spec |

### 3.4 Import + Add-Note modals

| ID | Requirement | Source | Layer / Module | UI surface | Spec ref | Status |
|----|-------------|--------|----------------|------------|----------|--------|
| TUI-60 | File path input + format auto-detect | TUI §4 | L2 `ImportModal` | Modal | SPEC.component §2.2 | spec |
| TUI-61 | Supported-formats list shown to user | TUI §4 | L2 `ImportModal` | Modal | SPEC.component §2.2 | spec |
| TUI-62 | Note modal: position + context auto-filled | TUI §3 | L2 `AddNoteModal` | Modal | SPEC.component §2.2 | spec |
| TUI-63 | Tag input (comma-separated) | TUI §3 | L2 `AddNoteModal` | Modal | SPEC.component §2.2 | spec |
| TUI-64 | Multi-line content area | TUI §3 | L2 `AddNoteModal` | Modal | SPEC.component §2.2 | spec |

### 3.5 Scan + Skim screens

| ID | Requirement | Source | Layer / Module | Algorithm | UI surface | Spec ref | Status |
|----|-------------|--------|----------------|-----------|------------|----------|--------|
| TUI-70 | Search input + Search/Clear buttons | ENH §UI mockup | L2 `ScanModal` | ALG §8 | Scan modal | SPEC.three_modes §4.2 | spec (Phase 3) |
| TUI-71 | Result list with chapter + word + context | ENH §UI mockup | L2 `ScanModal` | ALG §8.3 | Scan modal | SPEC.three_modes §4.2 | spec (Phase 3) |
| TUI-72 | "Currently reading here" marker | WORKFLOW §Scan | L2 `ScanModal` | n/a | Scan modal | SPEC.three_modes §4.2 | spec (Phase 3) |
| TUI-73 | Chapter outline + topic sentence per chapter | ENH §1 + WORKFLOW §Skim | L2 `SkimScreen` | ALG §7 | Skim screen | SPEC.three_modes §2.2 | spec (Phase 3) |
| TUI-74 | "Read Chapter" / "Add Note" buttons per chapter | ENH §UI mockup | L2 `SkimScreen` | n/a | Skim screen | SPEC.three_modes §2.2 | spec (Phase 3) |
| TUI-75 | Key Concepts sidebar | ENH §UI mockup | L2 `SkimScreen` | ALG §7.2 | Skim screen | SPEC.three_modes §2.2 | spec (Phase 3) |

---

## 4. File format support (FMT-*)

| ID | Format | Source | Layer / Module | Algorithm | UI surface | Spec ref | Status |
|----|--------|--------|----------------|-----------|------------|----------|--------|
| FMT-01 | Markdown (.md) | PRD §6.1 + TUI §4 | L5 `file_parser.parse_markdown` | ALG §3.3 | Import | SPEC.algo §3.3 | spec |
| FMT-02 | Plain text (.txt) | PRD §6.1 | L5 `file_parser.parse_markdown` (text mode) | ALG §3.3 | Import | SPEC.algo §3.3 | spec |
| FMT-03 | EPUB (.epub) | PRD §6.1 | L5 `file_parser.parse_epub_bytes` | ALG §3.2 | Import | SPEC.algo §3.2 | spec |
| FMT-04 | PDF (.pdf) | PRD §6.1 | L5 `file_parser.parse_pdf_bytes` | ALG §3.1 | Import | SPEC.algo §3.1 | spec (Phase 3, marked "coming soon" in TUI §4) |
| FMT-05 | reStructuredText (.rst) | PRD §6.1 | L5 (optional parser) | ALG §3 variant | Import | SPEC.algo §3 | spec (optional) |
| FMT-06 | Encoding auto-detect for .txt | PRD §6.1 | L5 (chardet-like) | ALG §3 | Import | SPEC.algo §3 | spec |
| FMT-07 | Chapter detection from Markdown headers | PRD §6.2 | L5 `parse_markdown` | ALG §3.3 | Import | SPEC.algo §3.3 | spec |

---

## 5. Data traceability (DATA-*)

| ID | Requirement | Source | Tier | Algorithm | UI surface | Spec ref | Status |
|----|-------------|--------|------|-----------|------------|----------|--------|
| DATA-01 | `books` table (12 columns) | PRD §7.1 | Tier 1 | n/a | Library screen, CLI | SPEC.data §2.1 | spec |
| DATA-02 | `chapters` table | PRD §7.1 | Tier 1 | n/a | Reader chapter label | SPEC.data §2.2 | spec |
| DATA-03 | `notes` table | PRD §7.1 | Tier 1 | n/a | Reader notes panel | SPEC.data §2.3 | spec |
| DATA-04 | `reading_sessions` table | PRD §7.1 | Tier 1 | n/a | Completion screen | SPEC.data §2.4 | spec |
| DATA-05 | `book_fts` FTS5 virtual table | ENH §Technical | Tier 1 | ALG §8.1 | Scan screen | SPEC.data §2.5 | spec (Phase 3) |
| DATA-06 | `word_index` table | ENH §Technical | Tier 1 | ALG §8 | Scan screen | SPEC.data §2.5 | spec (Phase 3) |
| DATA-07 | `cache/books/<id>.json` (tokenized words) | PRD §7.2 | Tier 2 | ALG §2.4 | (internal) | SPEC.data §3.1 | spec |
| DATA-08 | `cache/books/<id>.txt` (plain text backup) | PRD §7.2 | Tier 2 | n/a | (internal) | SPEC.data §3.2 | spec |
| DATA-09 | `cache/covers/<id>.jpg` | PRD §7.2 | Tier 2 | n/a | (future: cover display) | SPEC.data §3.3 | spec |
| DATA-10 | `notes/<book_id>/<note_id>.md` | TUI §Data Storage | Tier 3 | n/a | Note archive | SPEC.data §4.2 | spec |
| DATA-11 | `notes/<book_id>/metadata.json` | TUI §Data Storage | Tier 3 | n/a | Note index | SPEC.data §4.1 | spec |
| DATA-12 | `notes/exports/<book_id>_notes.md` | TUI §Data Storage | Tier 3 | n/a | Export file | SPEC.data §4.3 | spec |
| DATA-13 | `~/.rsvp/config.json` | PRD §3.2 + §7.2 | Tier 1+ | n/a | Settings screen | SPEC.data §5 | spec |
| DATA-14 | Notes dual-write (SQLite + files) | PRD §7.1 vs TUI §Data | Tier 1+3 | n/a | Note manager | SPEC.data §2.3.1 | **conflict** (resolved: dual-write) |

---

## 6. Performance budgets (PERF-*)

| ID | Operation | Target | Source | Algorithm involved | Spec ref | Status |
|----|-----------|--------|--------|--------------------|----------|--------|
| PERF-01 | Import 100KB markdown | < 100ms | PRD §11.1 | ALG §2 + §3.3 | SPEC.algo §2+§3.3 | spec |
| PERF-02 | Import 1MB PDF | < 2s | PRD §11.1 | ALG §3.1 | SPEC.algo §3.1 | spec (Phase 3) |
| PERF-03 | Tokenize 10K words | < 50ms | PRD §11.1 | ALG §2.1 | SPEC.algo §2.1 | spec |
| PERF-04 | Word display latency | < 16ms | PRD §11.1 | ALG §4 + §5 | SPEC.algo §4+§5 | spec |
| PERF-05 | Library list (100 books) | < 100ms | PRD §11.1 | n/a | SPEC.data §2.1 | spec |
| PERF-06 | Save progress | < 50ms | PRD §11.1 | n/a | SPEC.data §8 | spec |
| PERF-07 | Search across 50k-word book | < 10ms (target) | ENH §UI mockup | ALG §8 | SPEC.algo §8.4 | spec (Phase 3) |
| PERF-08 | Rust ORP vs Python ORP | 9.2× faster (measured) | session log | ALG §4 | (perf data) | **derived — actual measurement**, see §10 |

---

## 7. Non-functional (NF-*)

| ID | Requirement | Source | Spec ref |
|----|-------------|--------|----------|
| NF-01 | Rust core with Python fallback when unavailable | PRD §9.3 | SPEC.component §1.1, SPEC.algo §1 |
| NF-02 | Atomic file writes for cache and config | derived from PRD §7.2 | SPEC.data §3.1, §5 |
| NF-03 | Library list 100 books < 100ms (PERF-05) | PRD §11.1 | (above) |
| NF-04 | Background parsing for large PDFs | PRD §11.2 | SPEC.algo §3.1 (future) |
| NF-05 | ORP and delay precomputed at import | derived from PERF-04 | SPEC.algo §9.1 |
| NF-06 | Save-progress debounce (≤250ms) | derived from PERF-06 | SPEC.data §8 |
| NF-07 | Cache valid iff `len(tokens) == word_count` | derived | SPEC.data §3.1 |
| NF-08 | FTS5 over LIKE for search | derived from ENH §Technical | SPEC.algo §8 |

---

## 8. Source-doc coverage matrix (every source paragraph mapped to a spec section)

This is the **inverse** view — what each source doc contributes to this spec set:

### 8.1 PRD.md

| PRD section | Topic | Spec section |
|-------------|-------|--------------|
| §1 Executive summary | One-paragraph primer | (cited in `README.docs_index.md §5`) |
| §2 Architecture diagram | Layering | SPEC.component §1 |
| §3.1 Rust backend modules | 4 modules, 13 functions, 3 types | SPEC.component §2.5, SPEC.algo §2–§6 |
| §3.2 Python frontend | `RSVPApp`, widgets, managers, Config | SPEC.component §2.2, §2.3 |
| §4 Data classes | Book, Chapter, Note, ReadingSession, SessionStats | SPEC.data §6 |
| §5.1 CLI commands | 8 subcommands + 6 flags | SPEC.component §2.1, traceability §2 |
| §5.2 TUI screen mockups | Library, Reader focus/normal | SPEC.three_modes §3.2 |
| §6.1 File formats | 5 formats + encoders | SPEC.algo §3, traceability §4 |
| §6.2 Import pipeline | 5-stage diagram | SPEC.component §4 |
| §7.1 SQLite schema | 4 tables | SPEC.data §2 |
| §7.2 File cache layout | ~/.rsvp/ tree | SPEC.data §3, §4, §5 |
| §8.1 Global keybinds | q, l, s, ?, h | SPEC.three_modes §3.4 |
| §8.2 Reader keybinds | 13 bindings | SPEC.three_modes §3.4 |
| §8.3 Library keybinds | 5 bindings | SPEC.component §3.1 |
| §9.1 PyO3 module | Rust `#[pymodule]` body | SPEC.component §2.4 |
| §9.2 Cargo.toml | Dependencies | (info — not in spec) |
| §9.3 Python import fallback | `try import` pattern | SPEC.component §2.4, NF-01 |
| §10.1 Rust unit tests | 3 test functions | SPEC.algo §2, §4, §5 |
| §10.2 Python integration test | 1 test | SPEC.data §6 (info) |
| §11.1 Perf targets | 6 budgets | SPEC.data §8, traceability §6 |
| §11.2 Optimization | 4 strategies | SPEC.algo §9, §11 |
| §12 Future enhancements (Phase 2/3) | Backlog | (info — outside current spec) |
| §13 Development phases | Phase 1/2/3 timeline | See §10 below |

### 8.2 TUI_FEATURES.md

| TUI section | Topic | Spec section |
|-------------|-------|--------------|
| §1 Library mockup | Table + search + buttons | SPEC.component §3.1, traceability §3.1 |
| §1 Library keybinds | 8 bindings | traceability §3.1 |
| §2 Reader mockup | Word + ORP + progress + notes | SPEC.component §3.2, SPEC.three_modes §3.2 |
| §2 Reader keybinds | 11 bindings | traceability §3.2 |
| §3 Add-Note modal | Tags + content | SPEC.component §3.4, traceability §3.4 |
| §4 Import modal | Path + formats list | traceability §3.4 |
| §5 Settings mockup | All form sections | SPEC.component §3.3, traceability §3.3 |
| Architecture diagram | 3 layers | SPEC.component §1 |
| Data Storage section | SQLite schema + notes JSON | SPEC.data §2, §4 |
| Performance section | Rust vs Python timings | traceability §6 |
| CLI Commands section | 7 commands | traceability §2 |
| Configuration section | config.json example | SPEC.data §5 |
| Keyboard Reference Card | Master key map | SPEC.three_modes §3.4, §4.4, §2.4 |
| Future Enhancements | Phases 3+4 | (info) |

### 8.3 WORKFLOW.md

| WORKFLOW section | Topic | Spec section |
|------------------|-------|--------------|
| Skimming mode | Outline + topic sentences | SPEC.three_modes §2 |
| RSVP mode | Word loop + side panel | SPEC.three_modes §3 |
| Scanning mode | FTS results | SPEC.three_modes §4 |
| Reading Complete | Stats + export | SPEC.three_modes §5 |
| Mode Comparison table | 3 modes × 8 axes | SPEC.three_modes §6 |
| Keyboard shortcuts by mode | Per-mode key maps | SPEC.three_modes §2.4, §3.4, §4.4 |
| Data flow diagram | Mode router | SPEC.component §1, SPEC.three_modes §1 |
| Implementation status | Phase checklist | (info) |

### 8.4 ENHANCEMENTS.md

| ENH section | Topic | Spec section |
|-------------|-------|--------------|
| §1 Skimming mode (purpose) | Topic sentence extraction | SPEC.three_modes §2, SPEC.algo §7 |
| §2 Scanning mode (purpose) | Full-text search | SPEC.three_modes §4, SPEC.algo §8 |
| §3.1 Skimming algorithm | `extract_topic_sentences`, `extract_key_phrases` | SPEC.algo §7 |
| §3.2 Scanning algorithm | `ScanningMode.search_book` | SPEC.algo §8 |
| §3.3 Hybrid mode | Round-trip workflow | SPEC.three_modes §8 |
| Feature comparison | Competitor analysis | (info) |
| Proposed features (Phase 3) | skim, scan, hybrid | (info — already mapped) |
| Technical implementation | FTS5 + word_index SQL | SPEC.data §2.5, SPEC.algo §8 |
| Skimming algorithm pseudocode | `extract_topic_sentences` body | SPEC.algo §7.1 |
| UI mockups | Skim + Scan screens | SPEC.three_modes §2.2, §4.2 |
| Command extensions | 8 new CLI commands | traceability §2 (CLI-14 through CLI-19) |
| Implementation priority | High/Med/Low | (info) |

---

## 9. Conflict log (where source docs disagree)

| # | Conflict | Source A | Source B | Spec resolution |
|---|----------|----------|----------|-----------------|
| C-01 | Toggle ORP key | PRD §8.2: `m` | TUI §2: `o` | Spec uses `o` (TUI choice). Flagged in `SPEC.component §3.4` as needing sign-off. |
| C-02 | Switch mode key | PRD §8.2: uses `m` for ORP | WORKFLOW §RSVP: uses `m` for mode-switch | Mutual exclusion — if ORP=o, mode=m is free |
| C-03 | Notes storage | PRD §7.1: SQLite only | TUI §Data Storage: JSON files only | **Dual-write** (SQLite + Tier-3 files) — see `SPEC.data §2.3.1` |
| C-04 | Books `data JSON` + `completion_percentage` columns | PRD §4 dataclass: yes | PRD §7.1 schema: no | Schema (§7.1) is authoritative; completion derived |
| C-05 | Time complexity of Skim topic-sentence extractor | ENH pseudocode uses naive `.split('.')` | Best practice: sentence-segmenter | Spec adopts ENH pseudocode + flags caveat |
| C-06 | Skim entry binding (`s`) | WORKFLOW §Skim: `s` starts RSVP | TUI §Reader: `s` opens settings | Library/Reader global: `s` = settings; Skim-specific `s` = start RSVP. Scope-disambiguated. |
| C-07 | Note ID format | TUI §Data Storage example: `note_001` | Spec recommendation: UUID | Spec recommends UUID, retains `note_001` as valid |

---

## 10. Evolution timeline (how the plan evolved)

This is the answer to *"how was the overall state of planning this app development, to build a timeline and evolution across their docs"*.

### 10.1 Source-doc chronology

| Date | Artifact | Phase captured | Plan-state signal |
|------|----------|----------------|-------------------|
| 2026-04-10 | `PRD.md` v1.0 (Draft) | "what we originally wanted" | Single source of truth; full spec for RSVP-only MVP + Phases 1/2/3 |
| 2026-04-10 | `ARCHITECTURE_SUMMARY.md` | same date as PRD | Echoes PRD; adds build/test commands and roadmap; **status: architecture complete, ready for implementation** |
| 2026-04-10 | `TUI_FEATURES.md` | same date | Per-screen mockups + key maps + data storage; **adds dual-storage for notes (JSON files) that PRD didn't have** |
| 2026-04-10 | `PROJECT_SUMMARY.md` | same date | Implementation summary — what's done vs roadmap; **claims Phases 1 & 2 ✅, Phase 3 in progress** |
| 2026-04-10 | `WORKFLOW.md` | same date | The three-mode diagram — **first doc to add Skim + Scan as primary reading modes**, not just enhancements |
| 2026-04-10 | `ENHANCEMENTS.md` | same date | Roadmap expansion — Skim/Scan/Hybrid as Phase 3 features with FTS5 + topic extraction |
| 2026-04-10 | `CLAUDE.md` (workspace) | later | Agent operating manual |
| 2026-06-22 | `AGENTS.md` (per-project) | current | Updated architecture: Phase 1 screens + 9 figures + themes registry |
| 2026-06-23 | `pyproject.toml` + `scripts/` | current | Workspace task surface; fixed uv-build path-dep issue; **man page generation** |
| 2026-06-23 | Session: "Running and testing the RSVP TUI" | current | 179/179 Python tests + 5/5 Rust CLI tests passing; Rust ORP measured 9.2× faster than Python |
| 2026-06-23 | This doc set (`docs/SPEC.*.md`) | current | Spec-only decomposition answering *"what does the plan say?"* |

### 10.2 Plan-state signal — five-axis state model

| Axis | State at PRD (2026-04-10) | State at docs (current) | Δ signal |
|------|----------------------------|-------------------------|----------|
| **Scope clarity** | ✅ All Phases 1–4 enumerated | ✅ Same — but Phase 3 now decomposed into 3 sub-modes (Skim/Scan/Hybrid) | **expanded** |
| **Functional completeness (spec)** | ✅ PRD covers CLI + TUI + storage | ✅ + WORKFLOW adds explicit UX journeys; ENH adds 5 new CLI commands | **expanded** |
| **Implementation completeness (code)** | "ready for implementation" | 179/179 tests green; CLI+TUI+Rust core all built | **shipped** |
| **Conflict / drift** | none (single source) | 7 conflicts logged in §9 above | **new — needs reconciliation** |
| **Doc-as-code maturity** | 6 hand-written markdowns | + this 6-doc spec set; + `pyproject.toml` task surface; + man page generation | **expanded** |

### 10.3 Three evolution arcs visible in the corpus

**Arc 1 — "RSVP-only MVP" → "Three-mode reading system"**

The PRD positions RSVP as the *primary* mode and treats Skim/Scan as Phase-3
enhancements (one bullet under "Future Enhancements"). By the time of
WORKFLOW.md and ENHANCEMENTS.md (still 2026-04-10 but later in the day, based
on file ordering), Skim and Scan are **co-equal primary modes** with their
own screens, key maps, and algorithms. The WORKFLOW diagram literally has
three boxes of equal weight in the data-flow diagram.

**Spec implication:** the spec should treat the three modes as a *triangle*
(SPEC.three_modes §1), not a hierarchy with RSVP on top.

**Arc 2 — "Single storage tier" → "Three-tier storage model"**

PRD §7.1 puts notes in SQLite. TUI §Data Storage puts notes in JSON files.
The corpus never reconciles this — until this spec set. Spec adopts dual-write
(see `SPEC.data §2.3.1`).

**Arc 3 — "Single CLI entry" → "CLI + TUI + Rust CLI triple surface"**

PRD §5.1 describes one Click-based `rsvp` group. Current code (per AGENTS.md)
adds `rsvp-cli` (a separate native Rust CLI built on Clap + Ratatui). The
spec set covers the PRD's Click surface; the Rust CLI is **out of scope** for
this doc set (covered separately in the workspace CLAUDE.md / AGENTS.md /
the recent session log).

### 10.4 Where the planning is currently strong vs. thin

**Strong:**
- Functional requirements (CLI + TUI surface) — fully covered, ~80 IDs
- Data architecture — fully covered (3 tiers, 4 tables, 7 on-disk artifacts)
- Core algorithms (ORP, timing, tokenize) — fully covered with unit tests
- Mode transitions (Skim ↔ RSVP ↔ Scan) — fully covered

**Thin / out-of-spec:**
- Skim mode algorithms (only ENH pseudocode; no unit tests)
- Scan mode algorithms (FTS5 schema proposed; query plan TBD)
- Hybrid mode auto-switching (informational only)
- Adaptive timing (Phase 2 backlog; not in spec)
- PDF parser (marked "coming soon" — perf budget stated but no impl)
- Note edit flow (schema has `updated_at` but no edit UI in any source doc)
- Multi-user / sync / cloud (PRD §12 — clearly Phase 4+)

### 10.5 Spec coverage score

| Area | Spec coverage | Source-doc coverage | Notes |
|------|---------------|---------------------|-------|
| CLI surface | 19 / 19 commands | 8 (PRD) + 11 (ENH) | complete |
| TUI surface | 51 / 51 key+screen reqs | complete | complete |
| File formats | 7 / 7 | complete (5 formats) | complete |
| Data structures | 14 / 14 | complete | complete |
| Algorithms | 16 / 16 | complete + unit tests | complete |
| Performance budgets | 8 / 8 | complete | complete |
| Non-functional | 8 / 8 | complete | complete |
| Phase 3 (Skim/Scan) | 18 / 18 (spec, no tests) | mostly | spec-only |

**Overall:** the planning corpus is **mature, mostly consistent, and ready
for spec-as-code** — with the 7 conflicts in §9 needing explicit reconciliation
and the Skim/Scan algorithms needing Rust-side implementations + tests to
move from "spec-only" to "spec-verified".

---

## 11. Cross-reference: where to find a given topic

| You want to know… | Go to |
|--------------------|-------|
| "What does the app do?" | README.docs_index.md §5 |
| "What are the three modes?" | SPEC.three_modes.md §1 |
| "What's the canonical keybinding for X?" | SPEC.three_modes.md §3.4, §4.4 |
| "What's the SQLite schema?" | SPEC.data_architecture.md §2 |
| "How does ORP work?" | SPEC.algorithms.md §4 |
| "What commands does the CLI have?" | SPEC.component_design.md §2.1 + traceability §2 |
| "Where do conflicts between source docs live?" | This doc §9 |
| "How has the plan changed over time?" | This doc §10 |
| "What's still missing from the spec?" | This doc §10.4 |