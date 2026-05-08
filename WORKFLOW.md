# RSVP-TUI Complete Workflow

## The Three-Mode Reading System

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER READING WORKFLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────┐
                              │   START     │
                              │  New Book   │
                              └──────┬──────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              1. SKIMMING MODE                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  📖 "The Art of Speed Reading" - SKIM VIEW                          │    │
│  │                                                                     │    │
│  │  Quick Stats: 422 words • 4 chapters • ~1.5 min read @ 300wpm      │    │
│  │                                                                     │    │
│  │  CHAPTER PREVIEW:                                                   │    │
│  │  ┌─────────────────────────────────────────────────────────────┐   │    │
│  │  │ Ch1: Understanding RSVP (120 words)                         │   │    │
│  │  │ • RSVP displays text one word at a time                    │   │    │
│  │  │ • Eliminates eye movements (saccades)                      │   │    │
│  │  │ [Read Chapter] [Add Note]                                   │   │    │
│  │  ├─────────────────────────────────────────────────────────────┤   │    │
│  │  │ Ch2: The Science of Reading (150 words)                     │   │    │
│  │  │ • Reading involves multiple brain regions                  │   │    │
│  │  │ • Average speed 200-250 WPM                                │   │    │
│  │  │ [Read Chapter] [Add Note]                                   │   │    │
│  │  └─────────────────────────────────────────────────────────────┘   │    │
│  │                                                                     │    │
│  │  [s] Start RSVP  [/] Search  [o] Outline  [q] Quit                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │ Read Ch1     │ │ Search Book  │ │ View Outline │
            │ (RSVP Mode)  │ │ (Scan Mode)  │ │ (Skim Mode)  │
            └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
                   │                │                │
                   ▼                ▼                │
┌────────────────────────────────────────────────────┼────────────────────────┐
│                   2. RSVP MODE                     │                        │
│  ┌─────────────────────────────────────────────────┴─────────────────────┐   │
│  │                                                                       │   │
│  │                           ext[r]aordinary                             │   │
│  │                             │                                         │   │
│  │                       [RED FOCUS LINE]                                │   │
│  │                                                                       │   │
│  │  ═════════════════════════════════════════════════════════════════   │   │
│  │  Word 280/422 (66%) • 300 WPM • 0:28 remaining • Ch2                 │   │
│  │                                                                       │   │
│  │  [Space] ▶/❚❚  [←/→] ±1  [↑/↓] WPM  [f] Focus  [n] Note             │   │
│  │                                                                       │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ (Press / to search)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    3. SCANNING MODE (Search Results)                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │ 🔍 Search: "cognitive                         [Search] [X]              │ │
│  │                                                                          │ │
│  │ Found 5 matches:                                                         │ │
│  │ ╔════════════════════════════════════════════════════════════════════╗  │ │
│  │ ║ ▶ 1. Word 45 - "...complex [cognitive] process..."                ║  │ │
│  │ ║   └─ Currently reading here                                         ║  │ │
│  │ ║ 2. Word 128 - "...[cognitive] psychology..."                      ║  │ │
│  │ ║ 3. Word 234 - "...[cognitive] load during..."                     ║  │ │
│  │ ║ 4. Word 301 - "...[cognitive] science research..."                ║  │ │
│  │ ║ 5. Word 356 - "...[cognitive] benefits of..."                     ║  │ │
│  │ ╚════════════════════════════════════════════════════════════════════╝  │ │
│  │                                                                          │ │
│  │ [←/→] Prev/Next  [Enter] Jump to Word  [n] Add Note  [Esc] Back        │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ (Select result #3, press Enter)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                    RETURN TO RSVP MODE (at Word 234)                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  [NOTIFICATION: Jumped to Word 234 - 1 note nearby]                    │ │
│  │                                                                          │ │
│  │                              cogni[t]ive                                │ │
│  │                                                                          │ │
│  │  ═══════════════════════════════════════════════════════════════════   │ │
│  │  Word 234/422 (55%) • 300 WPM • Ch2                                     │ │
│  │                                                                          │ │
│  │  💡 Note at Word 230 (20 words behind):                                │ │
│  │     "Remember to check cognitive load research"                         │ │
│  │                                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     │ (Continue reading...)
                                     ▼
                              ┌─────────────┐
                              │   FINISH    │
│                              │   BOOK      │
                              └──────┬──────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                            READING COMPLETE                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  ✅ "The Art of Speed Reading" - COMPLETED                             │ │
│  │                                                                          │ │
│  │  Statistics:                                                             │ │
│  │  • Reading time: 12 minutes                                              │ │
│  │  • Average WPM: 285                                                      │ │
│  │  • Notes created: 4                                                      │ │
│  │  • Chapters read: 4/4                                                    │ │
│  │                                                                          │ │
│  │  Export Options:                                                         │ │
│  │  [1] Export notes to Markdown  [2] Generate summary  [3] Review notes  │ │
│  │  [q] Return to Library                                                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Mode Comparison

| Aspect | SKIMMING | RSVP | SCANNING |
|--------|----------|------|----------|
| **Goal** | Get overview | Read comprehensively | Find specific info |
| **Speed** | Very fast (1000+ wpm) | Controlled (100-1000) | Instant jump |
| **Eye Movement** | Vertical scanning | Fixed focal point | Targeted jumps |
| **Content** | Headings + key sentences | Every word | Search results |
| **Use Case** | Preview, select chapters | Deep reading | Reference lookup |

---

## Keyboard Shortcuts by Mode

### Global (All Modes)
| Key | Action |
|-----|--------|
| `q` | Quit / Back |
| `?` | Help |
| `l` | Library view |

### Skimming Mode
| Key | Action |
|-----|--------|
| `s` | Start RSVP reading |
| `/` | Enter search/scan mode |
| `o` | View outline |
| `↓/↑` | Next/previous chapter |
| `Enter` | Read selected chapter |

### RSVP Mode
| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `←/→` | Previous/Next word |
| `↑/↓` | Speed up/down |
| `/` | Search (enters scan mode) |
| `n` | Add note |
| `f` | Toggle focus mode |
| `m` | Switch mode (skim/scan) |

### Scanning Mode
| Key | Action |
|-----|--------|
| `Enter` | Jump to selected result |
| `↓/↑` | Next/previous result |
| `n` | Add note at selection |
| `Esc` | Return to RSVP |

---

## Data Flow

```
User Input
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ Mode Router (determines which handler)                  │
│  • 's' or 'r' → RSVP Mode                               │
│  • '/' or '?' → Scanning Mode                           │
│  • 'k' or outline → Skimming Mode                       │
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ SKIMMING│    │  RSVP   │    │ SCANNING│
    │  Engine │    │  Engine │    │  Engine │
    │         │    │         │    │         │
    │- Topic  │    │- Word   │    │- Full   │
    │  extract│    │  timing │    │  text   │
    │- Outline│    │- ORP    │    │  index  │
    │  gen    │    │  display│    │- Fuzzy  │
    │         │    │         │    │  search │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
         └───────────────┴───────────────┘
                         │
                         ▼
              ┌───────────────────┐
              │  Shared Storage   │
              │  • SQLite DB      │
              │  • Notes          │
              │  • Progress       │
              │  • FTS Index      │
              └───────────────────┘
```

---

## Implementation Status

| Component | Status | Notes |
|-----------|--------|-------|
| RSVP Core | ✅ Done | Rust + Python, ORP, timing |
| Library Mgmt | ✅ Done | SQLite, import, progress |
| Note-taking | ✅ Done | Position-linked, markdown export |
| **Skimming** | 📝 Planned | Topic extraction, outline view |
| **Scanning** | 🔄 In Progress | FTS index, search UI |
| TUI Polish | 🔄 In Progress | Textual widgets, CSS |
| PDF Support | 📋 Planned | lopdf integration |

---

## Next Steps

1. **Immediate**: Finish RSVP TUI MVP (reading view, library, settings)
2. **Short-term**: Add full-text search for scanning mode
3. **Medium-term**: Implement skimming with NLP topic extraction
4. **Long-term**: PDF support, sync, advanced analytics

This three-mode system creates the most complete terminal-based reading experience available.
