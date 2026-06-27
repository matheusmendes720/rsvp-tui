# SPEC — Data Architecture

> **Sources:** `PRD.md §4` (dataclasses), `PRD.md §7` (SQLite schema + on-disk
> layout), `TUI_FEATURES.md §Data Storage` (cache + notes layout).
>
> **Goal:** this spec is the single source of truth for *what data lives where
> and in what shape*. Where the PRD and TUI_FEATURES disagree (notably the
> notes table), the conflict is flagged inline.

---

## 1. Three-tier storage model

```
┌────────────────────────────────────────────────────────────────────┐
│  TIER 1 — STRUCTURED (SQLite)                                       │
│  books · chapters · notes · reading_sessions · book_fts · word_index│
│  Source of truth for: queries, joins, FTS, ordering                 │
├────────────────────────────────────────────────────────────────────┤
│  TIER 2 — CACHE (JSON files on disk)                                │
│  cache/books/<id>.json  (tokenized word list)                       │
│  cache/books/<id>.txt   (plain-text backup)                         │
│  cache/covers/<id>.jpg  (extracted cover image)                     │
│  Source of truth for: tokenization (avoids re-parse)                │
├────────────────────────────────────────────────────────────────────┤
│  TIER 3 — NOTES (per-book Markdown + index)                         │
│  notes/<book_id>/metadata.json   (note index)                       │
│  notes/<book_id>/<note_id>.md    (one file per note)                │
│  notes/exports/<book_id>_notes.md (combined export)                 │
│  Source of truth for: human-readable note history                   │
└────────────────────────────────────────────────────────────────────┘
```

Plus one top-level config file:

```
~/.rsvp/config.json    (Config dataclass, JSON-encoded)
```

---

## 2. Tier 1 — SQLite schema

### 2.1 `books` table (PRD §7.1 verbatim)

```sql
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
```

#### 2.1.1 Field-level requirements

| Field | Type | Constraints | Used by | Notes |
|-------|------|-------------|---------|-------|
| `id` | TEXT PK | unique, non-null | Library, Notes, Sessions | Likely a UUID or slug derived from title+hash |
| `title` | TEXT | non-null | Library display | Source: parser |
| `author` | TEXT | nullable | Library display | Source: parser (may be empty) |
| `file_path` | TEXT | nullable | Re-open original | Nullable if book came from cache only |
| `file_type` | TEXT | enum: `pdf`, `epub`, `md`, `txt`, `rst` | Parser dispatch | See `FMT-*` |
| `word_count` | INTEGER | non-null, ≥ 0 | Progress %, ETA | Cached count |
| `current_word_index` | INTEGER | 0 ≤ x ≤ word_count | Reader pointer | Updated every tick (debounced) |
| `current_chapter_index` | INTEGER | 0 ≤ x ≤ chapter_count-1 | Reader chapter label | Updated at chapter boundary |
| `added_date` | TIMESTAMP | non-null | Sort key | DEFAULT CURRENT_TIMESTAMP |
| `last_read_date` | TIMESTAMP | nullable | Library sort | Updated on each session |
| `total_reading_time_seconds` | INTEGER | ≥ 0 | Stats | Sum across sessions |
| `cache_file_path` | TEXT | non-null | Tokenizer bootstrap | Points at Tier-2 JSON |

> **Note (informational):** `PRD.md §4 Book` adds a `data JSON` field and a
> `completion_percentage` derived field. The §7.1 SQLite schema omits these.
> Spec retains the §7.1 schema as authoritative; derived percentage is computed
> at read time, not stored.

### 2.2 `chapters` table (PRD §7.1 verbatim)

```sql
CREATE TABLE chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_id TEXT,
    chapter_index INTEGER,
    title TEXT,
    start_word_index INTEGER,
    end_word_index INTEGER,
    FOREIGN KEY (book_id) REFERENCES books(id)
);
```

Field-level:

| Field | Type | Notes |
|-------|------|-------|
| `id` | INTEGER PK | surrogate |
| `book_id` | TEXT FK | on delete: CASCADE (derived NF) |
| `chapter_index` | INTEGER | 0-based |
| `title` | TEXT | may be empty for un-titled chapters |
| `start_word_index` | INTEGER | inclusive |
| `end_word_index` | INTEGER | exclusive (last word + 1) |

### 2.3 `notes` table (PRD §7.1 verbatim — see conflict note below)

```sql
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

#### 2.3.1 Conflict note — notes storage location

| Source | What it says |
|--------|-------------|
| PRD §7.1 | Notes live in a `notes` SQLite table |
| TUI_FEATURES §Data Storage | Notes live as JSON files in `~/.rsvp/notes/<book_id>/` |

**Spec resolution:** keep BOTH. Tier-1 (SQLite) for queryable joins; Tier-3
(per-book Markdown + index) for human-readable archive. The Python
`NoteManager` is responsible for writing to both in the same operation.
This dual-write is *not* in any source doc — flag it as a planning decision.

#### 2.3.2 Field-level (notes)

| Field | Type | Notes |
|-------|------|-------|
| `id` | TEXT PK | `note_001` per TUI_FEATURES example, but spec recommends UUID |
| `book_id` | TEXT FK | indexed (NF) |
| `word_index` | INTEGER | the canonical position pointer |
| `chapter_index` | INTEGER | denormalized for cheap sort |
| `content` | TEXT | Markdown body |
| `tags` | TEXT | JSON array, e.g. `["orp","technique"]` |
| `created_at` | TIMESTAMP | |
| `updated_at` | TIMESTAMP | updated on edit (no edit UI in current spec — see backlog) |
| `word_context` | TEXT | the actual word displayed when note was created |

### 2.4 `reading_sessions` table (PRD §7.1 verbatim)

```sql
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

Derived fields the app computes at session-end (PRD §4 ReadingSession/SessionStats):

| Computed | Source |
|----------|--------|
| `duration_seconds` = `end_time - start_time` | derived |
| `words_read` = `end_word_index - start_word_index` | derived |
| `average_wpm` = `words_read / (duration_seconds/60)` | derived + stored |
| `effective_wpm` = accounts for pause time | PRD §4 spec |
| `completion_percentage` = `end_word_index / books.word_count` | derived |
| `pauses_count` | tracked in-process, persisted on close |

### 2.5 Phase-3 tables (ENH §Technical — forward-looking)

```sql
CREATE VIRTUAL TABLE book_fts USING fts5(
    word_index,
    content,
    content_row_id,
    content_table='words'
);

CREATE TABLE word_index (
    book_id TEXT,
    word_index INTEGER,
    word TEXT,
    sentence_context TEXT,
    paragraph_index INTEGER,
    FOREIGN KEY (book_id) REFERENCES books(id)
);
CREATE INDEX idx_word ON word_index(word);
```

`book_fts` is the **full-text search index** that powers Scanning mode.
`word_index` is the per-word lookup that powers fuzzy search and topic
extraction (UX-S03-07).

---

## 3. Tier 2 — On-disk cache

Per `PRD §7.2`:

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

### 3.1 `<book_id>.json` token-cache shape (inferred from spec)

The PRD describes this as "tokenized words array" but does not specify JSON
shape. Spec recommends:

```json
{
  "book_id": "...",
  "version": 1,
  "tokens": [
    {"index": 0,    "text": "Hello,",      "start": 0,  "end": 6,  "sentence_idx": 0},
    {"index": 1,    "text": "world!",      "start": 7,  "end": 13, "sentence_idx": 0}
  ],
  "sentences": [
    {"index": 0, "start_word": 0, "end_word": 2, "text": "Hello, world!"}
  ],
  "paragraphs": [
    {"index": 0, "start_word": 0, "end_word": 50, "sentence_range": [0, 5]}
  ]
}
```

NF-CACHE-01: cache file is **valid iff** `len(tokens) == books.word_count`.
NF-CACHE-02: cache file MUST be atomically written (temp + rename).
NF-CACHE-03: on corruption, the app falls back to re-parse (no error to user).

### 3.2 `<book_id>.txt` plain-text backup

Mirrors `ParseResult.plain_text` so a corrupted JSON cache can still feed the
Python tokenizer fallback.

### 3.3 `<book_id>.jpg` cover image

Optional (not every format yields one). Used by Library screen if implemented
in the future (not in current TUI_FEATURES mockup).

---

## 4. Tier 3 — Notes storage (per-book)

### 4.1 `notes/<book_id>/metadata.json` — note index

Shape (TUI_FEATURES §Data Storage — verbatim example):

```json
{
  "id": "note_001",
  "book_id": "book_123",
  "word_index": 280,
  "content": "Important point about ORP",
  "tags": ["orp", "technique"],
  "created_at": "2026-04-10T09:30:00"
}
```

NF-NOTE-01: this file is **only an index** — the canonical note body is in the
Markdown file. Reconstructing from a stale index is non-destructive.

### 4.2 `notes/<book_id>/<note_id>.md` — one Markdown file per note

Format (PRD §4 Note.to_markdown):

```markdown
## Note at word 280

**Context:** extraordinary
**Chapter:** 0
**Tags:** orp, technique
**Created:** 2026-04-10T09:30:00

ORP positioning depends on word length. I need to remember this for longer words.
```

NF-NOTE-02: Markdown is the human-readable archive. SQLite `notes.content`
is the queryable mirror. `metadata.json` is the lightweight index.

### 4.3 `notes/exports/<book_id>_notes.md` — combined export

`NoteManager.export_notes_to_markdown` writes one file per book containing all
notes concatenated. Format = concatenation of §4.2 files in `word_index` order.

---

## 5. Top-level config

`~/.rsvp/config.json` — JSON-serialized `Config` dataclass (PRD §3.2):

```json
{
  "default_wpm": 300,
  "min_wpm": 100,
  "max_wpm": 1000,
  "wpm_step": 25,
  "punctuation_multiplier": 2.0,
  "pause_on_punctuation": true,
  "pause_chars": [".", "!", "?", ";", ":"],
  "comma_pause_multiplier": 1.5,
  "enable_orp": true,
  "focus_mode": false,
  "show_progress_bar": true,
  "show_context_words": false,
  "library_db_path": "~/.rsvp/library.db",
  "notes_dir": "~/.rsvp/notes",
  "cache_dir": "~/.rsvp/cache"
}
```

NF-CFG-01: written atomically. NF-CFG-02: missing fields → default
(`Config.load` is tolerant).

---

## 6. Python dataclasses (mirror schema for in-memory use)

### 6.1 `Book` (PRD §4.1 — verbatim)

| Field | Type | Source |
|-------|------|--------|
| `id` | str | SQLite books.id |
| `title` | str | SQLite books.title |
| `author` | str | SQLite books.author |
| `file_path` | Optional[Path] | SQLite books.file_path |
| `file_type` | str | SQLite books.file_type (enum) |
| `word_count` | int | SQLite books.word_count |
| `chapters` | List[Chapter] | joined from chapters table |
| `current_word_index` | int | SQLite books.current_word_index |
| `current_chapter_index` | int | SQLite books.current_chapter_index |
| `added_date` | datetime | SQLite books.added_date |
| `last_read_date` | Optional[datetime] | SQLite books.last_read_date |
| `total_reading_time_seconds` | int | SQLite books.total_reading_time_seconds |
| `completion_percentage` | float | **derived** = current_word_index / word_count |

`Book.to_dict()` — PRD §4.1 — covers all of the above except chapters'
internal `word_count` field (sub-recursive `Chapter.to_dict`).

### 6.2 `Chapter` (PRD §4.1)

| Field | Type | Notes |
|-------|------|-------|
| `title` | str | |
| `start_word_index` | int | |
| `end_word_index` | int | |
| `word_count` | int | derived: `end - start` |

### 6.3 `Note` (PRD §4.1)

| Field | Type | Notes |
|-------|------|-------|
| `id` | str | UUID recommended |
| `book_id` | str | |
| `word_index` | int | |
| `chapter_index` | int | |
| `content` | str | |
| `tags` | List[str] | stored as JSON array in SQLite `tags` |
| `created_at` | datetime | |
| `updated_at` | datetime | |
| `word_context` | str | the word on screen at note creation |

`Note.to_markdown()` — PRD §4.1 (see §4.2 above for rendered shape).

### 6.4 `ReadingSession` + `SessionStats` (PRD §4.1)

`ReadingSession`:

| Field | Type | Default |
|-------|------|---------|
| `book_id` | str | — |
| `start_time` | datetime | — |
| `current_word_index` | int | — |
| `wpm` | int | — |
| `is_playing` | bool | False |
| `words_read` | int | 0 |
| `pauses_count` | int | 0 |
| `total_pause_time` | timedelta | 0 |

`SessionStats`:

| Field | Type |
|-------|------|
| `duration_seconds` | int |
| `words_read` | int |
| `average_wpm` | float |
| `effective_wpm` | float |
| `completion_percentage` | float |

---

## 7. Data-flow diagrams

### 7.1 Import flow (Tier 0 → Tier 1 → Tier 2)

```
File on disk
    │ (path)
    ▼
LibraryManager.import_book(path)
    │
    ├── file_parser.parse_* → ParseResult
    ├── text_engine.tokenize_text → List[str]
    ├── build tokens with positions
    ├── write cache/books/<id>.json (Tier 2)
    ├── write cache/books/<id>.txt  (Tier 2)
    ├── insert books row        (Tier 1)
    └── insert chapters rows    (Tier 1)
```

### 7.2 Reading flow (Tier 1 → Tier 2 → Reader)

```
User presses Space
    │
    ▼
ReaderDisplay.next_word()
    │
    ├── read current_word_index from books row
    ├── read tokens[word_index] from Tier 2 cache (hot)
    ├── call rsvp_core.calculate_word_delay(word, wpm, …)
    ├── schedule Textual Timer(delay_ms)
    └── on tick: advance word_index, update books row
```

### 7.3 Note flow (User → Tier 1 + Tier 3)

```
User presses 'n' at word 280
    │
    ▼
AddNoteModal opens
    │ (user fills content + tags)
    ▼
NoteManager.create_note(book_id, 280, content, tags)
    │
    ├── insert notes row (Tier 1)
    ├── write notes/<book_id>/<note_id>.md (Tier 3)
    └── update notes/<book_id>/metadata.json (Tier 3)
```

### 7.4 Search flow (UX-S03 → Tier 1)

```
User presses '/' in RSVP
    │
    ▼
ScanModal opens
    │ (user types query)
    ▼
Search engine (ENH §3.2 ScanningMode.search_book)
    │
    ├── query book_fts (FTS5 virtual table)
    ├── fall back to LIKE on word_index if FTS5 not built
    └── return List[SearchResult(book_id, chapter_index, word_index, context)]
```

---

## 8. Performance considerations (data layer)

| ID | Constraint | Source |
|----|------------|--------|
| PERF-DATA-01 | Library list (100 books) < 100ms | PRD §11.1 |
| PERF-DATA-02 | Save progress < 50ms | PRD §11.1 |
| PERF-DATA-03 | Tokenize 10K words < 50ms | PRD §11.1 |

NF-DATA-PERF-01: hot-path data structures (current word, current tokens)
must live entirely in memory; SQLite is only touched on save events.
NF-DATA-PERF-02: `current_word_index` writes should be **debounced**
(e.g. once per 250ms while playing, immediately on pause/quit).

---

## 9. Spec-coverage check

| Section | Source | Coverage |
|---------|--------|----------|
| §1 Tiering | PRD §7.2 | complete |
| §2 SQLite | PRD §7.1 | complete (4 tables) + Phase 3 schema |
| §3 Cache | PRD §7.2 | complete |
| §4 Notes | TUI §Data Storage + PRD §4 | complete + conflict flagged |
| §5 Config | PRD §3.2 Config | complete (15 fields) |
| §6 Dataclasses | PRD §4.1 | complete |
| §7 Data-flow | synthesized | complete (4 flows) |
| §8 Perf | PRD §11.1 | complete |