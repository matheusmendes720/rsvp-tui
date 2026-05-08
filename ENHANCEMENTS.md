# RSVP-TUI Enhancement Roadmap

Based on research into skimming, scanning, and RSVP techniques.

---

## The Three Reading Modes

### 1. SKIMMING Mode (New Feature)
**Purpose**: Get the gist/main ideas quickly

**Implementation**:
```
┌─────────────────────────────────────────────────────────────────┐
│  SKIMMING MODE                                                  │
├─────────────────────────────────────────────────────────────────┤
│  Showing: Chapter headings + first sentence of each paragraph   │
│                                                                  │
│  > Chapter 1: Understanding RSVP                                │
│    "Rapid Serial Visual Presentation (RSVP) is a method..."     │
│                                                                  │
│  > Chapter 2: The Science of Reading                            │
│    "Reading is a complex cognitive process..."                  │
│                                                                  │
│  [Space] Next  [Enter] Read Full Chapter  [q] Quit Skimming    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Extract headings and topic sentences
- Show only first sentence of each paragraph
- Jump to full reading at any point
- Auto-generated "summary" mode

---

### 2. SCANNING Mode (New Feature)
**Purpose**: Find specific information quickly

**Implementation**:
```
┌─────────────────────────────────────────────────────────────────┐
│  SCANNING MODE - Search: "cognitive"                            │
├─────────────────────────────────────────────────────────────────┤
│  Found 5 matches:                                               │
│                                                                  │
│  1. Word 45: "...complex [cognitive] process that involves..."  │
│  2. Word 128: "...[cognitive] psychology and has gained..."     │
│  3. Word 234: "...[cognitive] load during reading..."           │
│                                                                  │
│  [↑/↓] Select  [Enter] Jump to Word  [n] Add Note  [q] Quit    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Features**:
- Real-time search across entire book
- Show context around matches
- Jump to any match instantly
- Highlight all occurrences

---

### 3. RSVP Mode (Core - Already Implemented)
**Purpose**: High-speed reading with comprehension

**Current Features**:
- ✅ ORP highlighting
- ✅ Variable WPM (100-1000)
- ✅ Punctuation pauses
- ✅ Progress tracking

**Enhancements**:
- [ ] Dynamic speed adjustment based on word complexity
- [ ] Auto-pause on difficult words
- [ ] Comprehension quiz mode

---

## Feature Comparison with Competitors

### rsvp-term (Mootikins)
- **Pros**: Native Markdown, simple TUI, EPUB support
- **Cons**: No library management, no notes, no ORP
- **Our Advantage**: Rust backend performance, note-taking, library

### srit (yurug)
- **Pros**: Multiple formats (PDF, Word), CLI interface
- **Cons**: No TUI, no persistence, basic RSVP
- **Our Advantage**: Rich TUI, progress tracking, hybrid architecture

---

## Proposed New Features

### Phase 3: Skimming & Scanning

#### 3.1 Skimming Mode (`rsvp skim <book>`)
```python
class SkimmingMode:
    """Extract and display key sentences only."""
    
    def extract_key_sentences(text: str) -> List[str]:
        # Use NLP to find topic sentences
        # Show first sentence of each paragraph
        # Show sentences with keywords
        pass
    
    def display_chapter_outline(chapter: Chapter):
        # Show headings hierarchy
        # Show bullet points of key ideas
        pass
```

#### 3.2 Scanning Mode (`rsvp scan <book> --for "keyword"`)
```python
class ScanningMode:
    """Fast search and jump to specific content."""
    
    def search_book(book_id: str, query: str) -> List[SearchResult]:
        # Full-text index in SQLite
        # Fuzzy matching for typos
        # Context window display
        pass
```

#### 3.3 Hybrid Mode (Auto-switching)
```
Skim → Select interesting chapter → RSVP read → Scan for details → Take notes
```

---

## Technical Implementation

### Full-Text Search Index

Add to SQLite schema:
```sql
CREATE VIRTUAL TABLE book_fts USING fts5(
    word_index,
    content,
    content_row_id,
    content_table='words'
);

-- Index all words for fast scanning
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

### Skimming Algorithm

```rust
// In rsvp-core/src/text_engine.rs

pub fn extract_topic_sentences(text: &str) -> Vec<(String, usize)> {
    // 1. Split into paragraphs
    let paragraphs: Vec<_> = text.split("\n\n").collect();
    
    // 2. For each paragraph, extract first sentence
    paragraphs.iter()
        .map(|p| {
            let first_sentence = p.split('.').next().unwrap_or(p);
            first_sentence.to_string()
        })
        .filter(|s| !s.is_empty())
        .collect()
}

pub fn extract_key_phrases(text: &str, top_n: usize) -> Vec<String> {
    // TF-IDF algorithm to find important phrases
    // Return top N most significant phrases
}
```

---

## UI Mockups

### Skimming View
```
┌─────────────────────────────────────────────────────────────────┐
│  📖 The Art of Speed Reading          [Skim] [Scan] [RSVP]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  CHAPTER OUTLINE                                                 │
│  ═══════════════════════════════════════════════════════════   │
│                                                                  │
│  ▶ Chapter 1: Understanding RSVP                                 │
│    • RSVP displays text one word at a time                       │
│    • Eliminates eye movements (saccades)                         │
│    • Can increase reading speed significantly                    │
│    [Read Chapter] [25 words]                                     │
│                                                                  │
│  ▶ Chapter 2: The Science of Reading                             │
│    • Reading involves multiple brain regions                     │
│    • Average reading speed is 200-250 WPM                        │
│    [Read Chapter] [150 words]                                    │
│                                                                  │
│  KEY CONCEPTS                                                    │
│  • Saccadic eye movement • Optimal Recognition Point             │
│  • Comprehension vs Speed • Working memory                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Scanning View
```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 Search: [cognitive                    ]  [Search] [Clear]   │
├─────────────────────────────────────────────────────────────────┤
│  Found 12 matches in 0.003s                                      │
│                                                                  │
│  ╔═══════════════════════════════════════════════════════════╗  │
│  ║ 1. Ch1, Word 45                                            ║  │
│  ║    "...complex [cognitive] process that involves..."       ║  │
│  ║    [Jump] [Add Note] [Copy]                                ║  │
│  ╠═══════════════════════════════════════════════════════════╣  │
│  ║ 2. Ch1, Word 128                                           ║  │
│  ║    "...[cognitive] psychology and has gained..."           ║  │
│  ║    [Jump] [Add Note] [Copy]                                ║  │
│  ╠═══════════════════════════════════════════════════════════╣  │
│  ║ 3. Ch2, Word 234                                           ║  │
│  ║    "...[cognitive] load during reading..."                 ║  │
│  ║    [Jump] [Add Note] [Copy]                                ║  │
│  ╚═══════════════════════════════════════════════════════════╝  │
│                                                                  │
│  [←/→] Page  [↑/↓] Select  [Enter] Jump  [Esc] Close           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Command Extensions

```bash
# Skimming commands
rsvp skim <book_id>                    # Enter skimming mode
rsvp outline <book_id>                 # Print chapter outline
rsvp summary <book_id> --words 100     # Generate 100-word summary

# Scanning commands
rsvp search <book_id> "query"          # Search within book
rsvp grep <book_id> "pattern"          # Regex search
rsvp find "query" --all-books          # Search entire library

# Combined workflow
rsvp read <book_id> --mode=skim        # Start in skimming mode
rsvp read <book_id> --jump-to="topic"  # Start at search result
```

---

## Implementation Priority

### High Priority (Core Value)
1. ✅ RSVP reading with ORP
2. ✅ Library management
3. ✅ Note-taking
4. 🔄 Full-text search (Scanning)

### Medium Priority (Differentiation)
5. 📝 Skimming mode with topic extraction
6. 📝 Comprehension tracking
7. 📝 Reading statistics dashboard

### Low Priority (Nice to Have)
8. 📋 Auto-summarization
9. 📋 Flashcard generation from notes
10. 📋 Social/sharing features

---

## Summary

Our RSVP-TUI already exceeds competitors in:
- **Performance**: Rust backend
- **Features**: Notes + Library
- **Architecture**: Clean separation

Adding Skimming & Scanning modes would make it the **complete speed-reading toolkit** for the terminal.
