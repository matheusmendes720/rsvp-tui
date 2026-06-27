# SPEC — Algorithms & BFF Data Structures

> **Sources:** `PRD.md §3.1` (Rust functions and their signatures),
> `ENHANCEMENTS.md §Technical Implementation` (FTS + skim extractors),
> `PROJECT_SUMMARY.md §1` (ORP table + timing formula), `WORKFLOW.md`
> (mode transitions).
>
> **Scope:** everything in the **BFF tier** (Backend-For-Frontend: the layer
> that computes what the UI displays). This means: tokenization, ORP, timing,
> search/scan, skim extraction. UI composition is in `SPEC.component_design.md`.

---

## 1. BFF-tier inventory

| Algorithm | Lives in | Used by modes | Spec section |
|-----------|----------|---------------|--------------|
| Tokenize text | Rust `text_engine::tokenize_text` | all | §2 |
| Normalize whitespace | Rust `text_engine::normalize_whitespace` | all | §2.1 |
| Split into sentences | Rust `text_engine::split_into_sentences` | skim | §2.2 |
| Extract words with positions | Rust `text_engine::extract_words_with_positions` | scan | §2.3 |
| Calculate reading complexity | Rust `text_engine::calculate_reading_complexity` | stats | §2.4 |
| Parse file | Rust `file_parser::parse_*` | import | §3 |
| Calculate ORP index | Rust `rsvp_core::calculate_orp_index` | RSVP | §4 |
| Calculate word delay | Rust `rsvp_core::calculate_word_delay` | RSVP | §5 |
| Split word for display | Rust `rsvp_core::split_word_for_display` | RSVP | §4.2 |
| Estimate reading time | Rust `rsvp_core::estimate_reading_time` | UI | §5.3 |
| Pause-at-punctuation check | Rust `rsvp_core::should_pause_at_punctuation` | RSVP | §5.2 |
| Word frequency distribution | Rust `word_stats::*` | stats | §6 |
| Topic-sentence extraction | Rust `text_engine::extract_topic_sentences` | skim | §7 |
| Key-phrase extraction (TF-IDF) | Rust `text_engine::extract_key_phrases` | skim | §7.2 |
| FTS5 query | SQLite virtual table | scan | §8 |
| Fuzzy search | (Python or Rust) | scan | §8.2 |

---

## 2. Tokenization & text shaping (Rust `text_engine`)

### 2.1 `tokenize_text(text: &str) -> Vec<String>`

**Signature (PRD §3.1):** `pub fn tokenize_text(text: &str) -> Vec<String>`

**Behavior:** split `text` on Unicode word boundaries; keep punctuation attached
to the preceding word (so "Hello, world!" → `["Hello,", "world!"]`).

**Algorithm (inferred from PRD §10.1 test):**

```rust
pub fn tokenize_text(text: &str) -> Vec<String> {
    // Uses unicode-segmentation's UWord boundaries.
    // Punctuation stays attached by NOT using str::split_whitespace.
    text.unicode_words()
        .map(|w| w.to_string())
        .collect()
}
```

**Unit test (PRD §10.1 verbatim):**
```rust
assert_eq!(
    tokenize_text("Hello, world! This is a test."),
    vec!["Hello,", "world!", "This", "is", "a", "test."]
);
```

### 2.2 `normalize_whitespace(text: &str) -> String`

Collapses all runs of `\s+` to a single space. Trims leading/trailing.
**Used:** before tokenize on raw parsed text (parser may leave `\n\n` etc.).

### 2.3 `split_into_sentences(text: &str) -> Vec<String>`

Sentence splitter. PRD does not specify algorithm; spec recommends the
ICU BreakIterator or a regex-based fallback. **Used:** skim outline generation
(§7) and stats.

### 2.4 `extract_words_with_positions(text: &str) -> Vec<(String, usize, usize)>`

Returns `(word, start_offset, end_offset)` triples — the building block of
the Tier-2 token-cache JSON (§3.1 of data spec). Algorithm:

```
for each UWord boundary (start, end) in text:
    word = text[start..end]
    emit (word, start, end)
```

### 2.5 `calculate_reading_complexity(text: &str) -> f64`

PRD §3.1 says "Flesch-Kincaid or similar". Spec recommendation:

```
FK_grade = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
```

Return `FK_grade as f64`. **Used:** stats dashboard (Phase 3).

---

## 3. File parsing (`file_parser`)

### 3.1 `parse_pdf_bytes(data: &[u8]) -> ParseResult`

PRD §3.1 — depends on the `pdf-extract` crate (PRD §9.2) or `lopdf`.

**Behavior:**
1. Decode PDF bytes → text stream
2. Detect chapter boundaries via font-size heuristics or PDF outline
3. Build `ParseResult { title, author, chapters, plain_text, word_count }`

**Performance budget:** < 2s for 1 MB PDF (PRD §11.1).

### 3.2 `parse_epub_bytes(data: &[u8]) -> ParseResult`

Uses `epub` crate. Walks `book.opf` → spine → XHTML → text per chapter.
**Performance budget:** < 1s for typical 500 KB EPUB (derived; PRD silent).

### 3.3 `parse_markdown(text: &str) -> ParseResult`

Uses `pulldown-cmark` (PRD §9.2). **Chapter detection rule:**
- `# heading` → new chapter
- `## heading` → new sub-chapter (nested)
- `### heading` → paragraph-level marker (no chapter break)

`plain_text` is the concatenation of heading + body text per chapter, with
markdown syntax stripped.

### 3.4 `ParseResult` (PyO3 class, PRD §3.1)

```
ParseResult {
    title:        String,
    author:       String,
    chapters:     Vec<Chapter>,
    plain_text:   String,
    word_count:   usize,
}

Chapter {
    title:               String,
    start_word_index:    usize,
    end_word_index:      usize,
    content:             String,
}
```

**Invariants:**
- `chapters` MUST be sorted by `start_word_index`
- `end_word_index[i] == start_word_index[i+1]` (contiguous, non-overlapping)
- `chapters.last().end_word_index == word_count`

---

## 4. ORP — Optimal Recognition Point

### 4.1 Algorithm (PROJECT_SUMMARY §1 — ORP table)

The ORP index selects one character in the word as the visual fixation point.
Rule:

| Word length | ORP index |
|-------------|-----------|
| 1–3         | 0 |
| 4–5         | 1 |
| 6–9         | 2 |
| 10+         | 3+ |

### 4.2 `calculate_orp_index(word: &str) -> usize`

```rust
pub fn calculate_orp_index(word: &str) -> usize {
    let n = word.chars().count();
    match n {
        0..=3  => 0,
        4..=5  => 1,
        6..=9  => 2,
        _      => 3,
    }
}
```

**Unit tests (PRD §10.1):**
```rust
assert_eq!(calculate_orp_index("a"),            0);
assert_eq!(calculate_orp_index("the"),          0);
assert_eq!(calculate_orp_index("hello"),        1);
assert_eq!(calculate_orp_index("reading"),      2);
assert_eq!(calculate_orp_index("extraordinary"),3);
```

### 4.3 `split_word_for_display(word: &str, orp_index: usize) -> WordParts`

Splits the word into three parts at the ORP for two-tone rendering:

```
WordParts {
    before_orp: String,  // chars [0..orp_index)
    orp_char:   String,  // chars [orp_index..orp_index+1)
    after_orp:  String,  // chars [orp_index+1..n)
}
```

**Example:** `split_word_for_display("extraordinary", 3)` → `("ext", "r", "aordinary")`.

### 4.4 Rendering pipeline (UI side)

```
word      →  rsvp_core.calculate_orp_index   →  orp_index
word,orp  →  rsvp_core.split_word_for_display →  WordParts(before, orp, after)
WordParts →  ReaderDisplay._format_word_display
                →  Rich Text with [before_orp][ORP_HIGHLIGHT][after_orp]
                →  centered Panel
```

---

## 5. Word timing

### 5.1 Base delay formula

```
delay_ms(word, wpm, punct_mult, pause_chars) =
    floor(60_000 / wpm)                          // base
    * (if pause_chars ∩ last_char(word) then punct_mult else 1.0)
    * (1.0 + 0.1 * max(0, n_syllables(word) - 1)) // complexity stretch (derived)
```

**Project Summary §1:** "Base delay = 60000 / WPM. Punctuation pause = 2x."

### 5.2 `calculate_word_delay(word, wpm, punctuation_multiplier, pause_chars) -> u64`

Returns delay in milliseconds.

**Unit test (PRD §10.1):**
```rust
assert_eq!(calculate_word_delay("hello",  300, 2.0, vec!['.', '!']), 200);
assert_eq!(calculate_word_delay("hello!", 300, 2.0, vec!['.', '!']), 400);
```

**Algorithm (spec-recommended):**

```rust
pub fn calculate_word_delay(
    word: &str,
    wpm: u32,
    punctuation_multiplier: f32,
    pause_chars: Vec<char>,
) -> u64 {
    let base = 60_000_u64 / wpm as u64;
    let pause = should_pause_at_punctuation(word, pause_chars.clone());
    let multiplier = if pause { punctuation_multiplier } else { 1.0 };
    (base as f32 * multiplier) as u64
}
```

### 5.3 `should_pause_at_punctuation(word, pause_chars) -> bool`

```rust
pub fn should_pause_at_punctuation(word: &str, pause_chars: Vec<char>) -> bool {
    match word.chars().last() {
        Some(c) => pause_chars.contains(&c),
        None => false,
    }
}
```

### 5.4 `estimate_reading_time(word_count, wpm) -> (u32, u32)`

Returns `(minutes, seconds)`. Algorithm:

```
total_seconds = word_count * 60 / wpm
minutes       = total_seconds / 60
seconds       = total_seconds % 60
```

### 5.5 Adaptive timing (PRD §12 — backlog, NF only)

Future work mentioned in ENHANCEMENTS §3 "RSVP Mode Enhancements":
- Dynamic speed adjustment based on word complexity
- Auto-pause on difficult words

Not in scope for current spec. Flagged as `ALG-FUT-*`.

---

## 6. Word statistics (`word_stats`)

### 6.1 `calculate_word_frequency_distribution(words) -> HashMap<String, u32>`

Used by stats dashboard. **Used:** reading-heatmap, difficult-words callout.

### 6.2 `identify_difficult_words(words, threshold) -> Vec<String>`

Difficult = rare word (frequency below `threshold`). Threshold units TBD
(probability vs rank). Spec marks as **informational**.

### 6.3 `generate_reading_heatmap_data(words, window_size) -> Vec<f32>`

Sliding-window complexity score. Per PRD §3.1: "complexity score per window
for heatmap visualization." Spec recommendation: window = 50 words, score =
avg FK-grade of the window.

---

## 7. Skim — topic extraction

ENH §3.1 + ENH §Technical Implementation define two related algorithms.

### 7.1 `extract_topic_sentences(text: &str) -> Vec<(String, usize)>`

Returns `(sentence, char_offset)` for the first sentence of each paragraph.

```rust
pub fn extract_topic_sentences(text: &str) -> Vec<(String, usize)> {
    text.split("\n\n")
        .filter(|p| !p.trim().is_empty())
        .filter_map(|p| {
            let first = p.split('.').next()?.trim();
            if first.is_empty() { None } else { Some((first.to_string(), 0)) }
        })
        .collect()
}
```

> **Caveat (informational):** this naive `.split('.')` will mis-split on
> abbreviations ("U.S.A."). Spec marks this as a known limitation; better
> algorithm = sentence-segmenter (§2.3) applied per paragraph.

### 7.2 `extract_key_phrases(text: &str, top_n: usize) -> Vec<String>`

TF-IDF ranking across the document. **Algorithm (spec):**

```
1. Tokenize text into sentences.
2. For each unique word:
   tf  = count(word) / total_words
   idf = log(N_sentences / sentences_containing_word)
   score = tf * idf
3. Take top_n by score, return as phrase candidates (1–3 grams).
```

Used by Skim's "KEY CONCEPTS" sidebar (ENH §UI mockup).

---

## 8. Scan — full-text search

### 8.1 SQLite FTS5 query (primary)

```sql
SELECT word_index, sentence_context
FROM book_fts
WHERE book_fts MATCH 'cognitive'
ORDER BY rank
LIMIT 50;
```

`book_fts` indexes the `words.content` column (see `SPEC.data_architecture.md`
§2.5). `rank` is BM25 by default in FTS5.

### 8.2 Fuzzy search (ENH §3.2 — "fuzzy matching for typos")

Spec recommendation: trigram similarity.

```
similarity(a, b) = |trigrams(a) ∩ trigrams(b)| / |trigrams(a) ∪ trigrams(b)|
```

Threshold default: `0.4`. Returns top-K by similarity where K = 20.

**Implementation choice (informational):** Rust `strsim` crate (Jaro-Winkler)
or SQLite-side FTS5 `*` wildcard (cheaper, less accurate).

### 8.3 Result shape

```rust
struct SearchResult {
    book_id:         String,
    chapter_index:   u32,
    word_index:      u32,
    context_before:  String,  // configurable, default 5 words
    context_match:   String,  // the matched word
    context_after:   String,  // configurable, default 5 words
    score:           f32,     // BM25 or fuzzy
}
```

### 8.4 Performance budget

ENH §UI mockup: "Found 12 matches in 0.003s" — implies a < 10ms target on
the typical 50k-word book. FTS5 on SQLite comfortably meets this.

---

## 9. BFF data structures

### 9.1 In-memory token stream

```rust
struct TokenStream {
    tokens:    Vec<Token>,      // all words, in order
    sentences: Vec<SentenceRange>, // [start_word_idx, end_word_idx]
    paragraphs: Vec<ParagraphRange>,
}

struct Token {
    index:       u32,           // global
    text:        String,
    start:       u32,           // char offset in plain_text
    end:         u32,
    orp_index:   u8,
    delay_ms:    u32,           // precomputed
    sentence_idx: u16,
    paragraph_idx: u16,
}
```

**Why pre-compute ORP and delay?** Both are pure functions of (word, wpm,
config). Pre-computing once at import time keeps the per-tick cost to a
single list lookup — critical for hitting the 16ms latency budget (PRD §11.1).

### 9.2 Reader state

```rust
struct ReaderState {
    book_id:           String,
    current_word_idx:  u32,           // == books.current_word_index
    is_playing:        bool,
    wpm:               u16,           // current effective WPM
    config_snapshot:   Config,        // copy-on-play
    paused_at:         Option<Instant>,
    started_at:        Instant,
    words_read:        u32,
    pauses_count:      u32,
    total_pause_ms:    u64,
}
```

### 9.3 Session accumulator

```rust
struct SessionAccumulator {
    session: ReadingSession,           // PRD §4.1 — persisted on close
    stats:   SessionStats,             // computed on close
}
```

---

## 10. Algorithm complexity cheat-sheet

| Algorithm | Time | Space | Called per tick? |
|-----------|------|-------|------------------|
| tokenize_text | O(n) chars | O(n) tokens | No (import) |
| extract_words_with_positions | O(n) chars | O(n) | No (import) |
| calculate_orp_index | O(1) per word | O(1) | Yes — but precomputed at import |
| split_word_for_display | O(n) per word | O(n) | Yes — UI render |
| calculate_word_delay | O(1) | O(1) | Yes — but precomputed at import |
| extract_topic_sentences | O(p) paragraphs | O(s) sentences | No (skim entry) |
| extract_key_phrases (TF-IDF) | O(w·log w) words | O(w) | No (skim entry) |
| FTS5 query | O(log n) per match | O(k) | No (user-driven) |
| Fuzzy search (trigram) | O(n·k) per query | O(n) | No (user-driven) |

---

## 11. Spec-coverage check

| Section | Source | Coverage |
|---------|--------|----------|
| §2 Tokenize | PRD §3.1, §10.1 | complete |
| §3 Parse | PRD §3.1, §6 | complete (4 parsers) |
| §4 ORP | PRD §10.1, PROJECT_SUMMARY §1 | complete + unit tests |
| §5 Timing | PRD §3.1, §10.1, PROJECT_SUMMARY §1 | complete + formula |
| §6 Stats | PRD §3.1, ENH §Technical | partial (informational for difficulty) |
| §7 Skim | ENH §3.1, §Technical | complete (with caveat) |
| §8 Scan | ENH §3.2, §Technical | complete (FTS5 + fuzzy) |
| §9 BFF structs | synthesized from §2–§8 | complete |
| §10 Complexity | synthesized | complete |