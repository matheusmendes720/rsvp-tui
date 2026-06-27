# SPEC — Three Reading Modes (Skim / Scan / RSVP)

> **Sources:** `WORKFLOW.md`, `ENHANCEMENTS.md` (entire file), `TUI_FEATURES.md`
> (per-screen sections).
> **Spec only.** This doc derives from the four planning artifacts and adds no
> new requirements — it consolidates them into one journey-focused view.

---

## 1. The mode triangle

The app is defined by **three modes** that the user moves between inside a single
reading session. They share the same library, the same notes, and the same
position pointer (`Book.current_word_index`) but differ in what they display and
which engine drives the loop.

```
                    ┌──────────────┐
                    │   LIBRARY    │  ← entry point (TUI-FEATURES §1)
                    └──────┬───────┘
                           │ open book
                           ▼
              ┌────────────────────────┐
              │      SKIMMING          │   UX-S01
              │  chapter outline +     │
              │  topic sentences       │
              └─────┬───────────┬──────┘
                    │           │
       (Enter Ch.)  │           │  (/ search)
                    ▼           ▼
              ┌──────────┐  ┌──────────┐
              │   RSVP   │←→│ SCANNING │   UX-S02 / UX-S03
              │  word    │  │  FTS     │
              │  loop    │  │  results │
              └──────────┘  └──────────┘
                    │
                    │ (book end)
                    ▼
              ┌──────────────┐
              │   COMPLETE   │   UX-S04
              │  statistics  │
              └──────────────┘
```

The three engines are deliberately **disjoint at render time** but **unified at
state time** — every mode reads and writes the same `Book.current_word_index`,
so jumping from a Scan hit into RSVP is just `reader.seek(hit.word_index)`.

---

## 2. Mode 1 — Skimming (UX-S01)

### 2.1 Purpose (per `ENHANCEMENTS.md §1`)

> *"Get the gist / main ideas quickly. Show chapter headings + first sentence of
> each paragraph."*

### 2.2 Surface

```
┌─────────────────────────────────────────────────────────────────┐
│  📖 <book title>                              [Skim][Scan][RSVP]│
├─────────────────────────────────────────────────────────────────┤
│  CHAPTER OUTLINE                                                │
│  ════════════════════════════════════════════════════════════  │
│  ▶ Chapter 1: Understanding RSVP (120 words)                    │
│    • RSVP displays text one word at a time                      │
│    • Eliminates eye movements (saccades)                        │
│    [Read Chapter] [Add Note]                                    │
│  ▶ Chapter 2: The Science of Reading (150 words)                │
│    …                                                            │
│  KEY CONCEPTS:  • Saccadic eye movement • ORP                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Functional requirements

| ID | Requirement | Source |
|----|-------------|--------|
| UX-S01-01 | Show chapter headings and the first sentence of each paragraph | ENH §1 + §3.1 |
| UX-S01-02 | Display chapter word count + estimated read time | WORKFLOW §1 |
| UX-S01-03 | "Read Chapter" jump from any chapter outline entry into RSVP at that chapter's `start_word_index` | ENH §3.1 + WORKFLOW §2 |
| UX-S01-04 | "Add Note" attaches a note to chapter start position | ENH §3.1 |
| UX-S01-05 | Mode switch bar (`[Skim][Scan][RSVP]`) is always visible | ENH §3.3, UI mockup |

### 2.4 Keyboard bindings (skimming)

| Key | Action | Source |
|-----|--------|--------|
| `s` | Start RSVP from current selection | WORKFLOW §Skimming Mode |
| `/` | Enter scan mode | WORKFLOW §Skimming Mode |
| `o` | View outline (this view) | WORKFLOW §Skimming Mode |
| `↓` / `↑` | Next / previous chapter | WORKFLOW §Skimming Mode |
| `Enter` | Read selected chapter in RSVP mode | WORKFLOW §Skimming Mode |
| `q` | Quit skimming | TUI §Skim UI |

---

## 3. Mode 2 — RSVP (UX-S02)

### 3.1 Purpose (per `TUI_FEATURES.md §2`)

Word-by-word display with ORP highlighting at a configurable WPM (100–1000),
with optional punctuation pauses, focus mode, and a notes sidebar.

### 3.2 Surface

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

### 3.3 Functional requirements (RSVP core)

| ID | Requirement | Source |
|----|-------------|--------|
| UX-S02-01 | Display exactly one word at a time, centered, with ORP highlight (red letter) | TUI §2, PRD §3.1 |
| UX-S02-02 | Show progress: `Word N/Total (P%)`, current chapter, WPM, ETA | TUI §2 mockup |
| UX-S02-03 | Play/pause toggle without losing position | TUI §2, PRD §8.2 |
| UX-S02-04 | Step ±1 word with `←` / `→` | TUI §2 |
| UX-S02-05 | Speed ±25 WPM with `↑` / `↓` | TUI §2 + PRD §8.2 |
| UX-S02-06 | Jump to start (`Home`) and end (`End`) | PRD §8.2 |
| UX-S02-07 | Skip back 10 words (`b`) | PRD §8.2 |
| UX-S02-08 | Add note at current word (`n`) | TUI §2 |
| UX-S02-09 | Toggle ORP highlighting (`m`) | PRD §8.2 (also `o` in TUI) |
| UX-S02-10 | Toggle focus mode (`f` or `Tab`) | PRD §8.2 / TUI §2 |
| UX-S02-11 | Restart from word 0 (`r`) | PRD §8.2 / TUI §2 |
| UX-S02-12 | Export notes (`e`) | PRD §8.2 |
| UX-S02-13 | Show notes within ±10-word window in sidebar | TUI §2 mockup "NOTES (2 nearby)" |
| UX-S02-14 | Persist position on quit + auto-resume | PRD §2 (Library) |

### 3.4 Keyboard bindings (RSVP, complete)

Global: `q` quit, `l` library, `s` settings, `?`/`h` help — `PRD §8.1`.
RSVP-specific per `PRD §8.2` + `TUI §2`:

| Key | Action | PRD ref | TUI ref |
|-----|--------|---------|---------|
| `Space` | Play/Pause | — | §2 |
| `Tab` | Toggle focus | §8.2 | §2 |
| `←` / `→` | Prev / Next word | §8.2 | §2 |
| `↑` / `↓` | Increase / Decrease WPM | §8.2 | §2 |
| `Home` | Jump to start | §8.2 | — |
| `End` | Jump to end | §8.2 | — |
| `j` | Jump to position (modal) | §8.2 | — |
| `c` | Open chapter list | §8.2 | — |
| `n` | Add note | §8.2 | §2 |
| `m` | Toggle ORP highlight | §8.2 | — |
| `f` | Toggle focus mode | §8.2 | §2 |
| `r` | Reset to beginning | §8.2 | §2 |
| `b` | Jump back 10 words | §8.2 | — |
| `e` | Export notes | §8.2 | — |

**Conflict noted (informational):** the TUI-FEATURES doc uses `o` to toggle ORP
while the PRD uses `m`. Spec leaves both as candidates; resolves to whichever
the keybinding map (`keybindings.py`) authoritatively declares. See
`SPEC.component_design.md` §3.4 for the current canonical map.

---

## 4. Mode 3 — Scanning (UX-S03)

### 4.1 Purpose (per `ENHANCEMENTS.md §2`)

> *"Find specific information quickly. Real-time search across entire book.
> Show context around matches. Jump to any match instantly."*

### 4.2 Surface

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 Search: [cognitive                    ]  [Search] [Clear]   │
├─────────────────────────────────────────────────────────────────┤
│  Found 12 matches in 0.003s                                     │
│  ╔═══════════════════════════════════════════════════════════╗  │
│  ║ 1. Ch1, Word 45                                            ║  │
│  ║    "…complex [cognitive] process that involves…"           ║  │
│  ║    [Jump] [Add Note] [Copy]                                ║  │
│  ╠═══════════════════════════════════════════════════════════╣  │
│  ║ 2. Ch1, Word 128                                           ║  │
│  …                                                            ║  │
│  ╚═══════════════════════════════════════════════════════════╝  │
│  [←/→] Page  [↑/↓] Select  [Enter] Jump  [Esc] Close           │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Functional requirements

| ID | Requirement | Source |
|----|-------------|--------|
| UX-S03-01 | Full-text search over the entire book (FTS5) | ENH §2 + §Technical |
| UX-S03-02 | Show match count + search time (ms) | ENH §UI mockup "Found 12 matches in 0.003s" |
| UX-S03-03 | Each result shows chapter + word_index + context window (configurable size) | ENH §UI mockup |
| UX-S03-04 | Mark the result closest to current reading position with "▶" or "Currently reading here" | WORKFLOW §3 mockup |
| UX-S03-05 | Jump to selected result (`Enter`) — sets `Book.current_word_index = hit.word_index` and returns to RSVP mode | WORKFLOW §3 + §4 |
| UX-S03-06 | Add note at result position (`n`) | WORKFLOW §Scanning Mode |
| UX-S03-07 | Fuzzy matching for typos | ENH §3.2 docstring |
| UX-S03-08 | Cross-book search (`rsvp find "query" --all-books`) | ENH §Command Extensions |
| UX-S03-09 | Regex search (`rsvp grep`) | ENH §Command Extensions |

### 4.4 Keyboard bindings (scanning)

| Key | Action | Source |
|-----|--------|--------|
| `Enter` | Jump to selected result (→ RSVP) | WORKFLOW §Scanning Mode |
| `↓` / `↑` | Next / previous result | WORKFLOW §Scanning Mode |
| `n` | Add note at selection | WORKFLOW §Scanning Mode |
| `Esc` | Return to RSVP at last position | WORKFLOW §Scanning Mode |
| `←/→` | Page results | ENH §UI mockup |

---

## 5. Mode 4 — Completion (UX-S04)

### 5.1 Purpose (per `WORKFLOW.md §Reading Complete`)

End-of-book summary screen with statistics + export options.

### 5.2 Surface

```
┌─────────────────────────────────────────────────────────────────┐
│  ✅ "<book title>" — COMPLETED                                  │
│                                                                 │
│  Statistics:                                                    │
│  • Reading time: 12 minutes                                     │
│  • Average WPM: 285                                             │
│  • Notes created: 4                                             │
│  • Chapters read: 4/4                                           │
│                                                                 │
│  Export Options:                                                │
│  [1] Export notes to Markdown  [2] Generate summary             │
│  [3] Review notes               [q] Return to Library           │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Functional requirements

| ID | Requirement | Source |
|----|-------------|--------|
| UX-S04-01 | Detect `current_word_index ≥ word_count` and route to completion screen | WORKFLOW §Reading Complete |
| UX-S04-02 | Compute session-level stats: time, avg WPM, notes, chapters | WORKFLOW mockup + PRD §4 (ReadingSession/SessionStats) |
| UX-S04-03 | Export notes to Markdown | WORKFLOW §Export Options |
| UX-S04-04 | Generate summary (placeholder — see Phase-3 §6) | WORKFLOW §Export Options |
| UX-S04-05 | Review notes in viewer (placeholder) | WORKFLOW §Export Options |
| UX-S04-06 | Return to Library (`q`) closes session and routes back | WORKFLOW §Export Options |

---

## 6. Mode-comparison matrix

The three reading modes differ along six orthogonal axes. This matrix is the
authoritative cross-reference for choosing which engine to invoke when.

| Aspect | Skimming | RSVP | Scanning | Source |
|--------|----------|------|----------|--------|
| **Goal** | Get overview | Read comprehensively | Find specific info | WORKFLOW §Mode Comparison |
| **Speed** | Very fast (1000+ wpm) | Controlled (100–1000) | Instant jump | WORKFLOW |
| **Eye movement** | Vertical scanning | Fixed focal point | Targeted jumps | WORKFLOW |
| **Content** | Headings + topic sentences | Every word | Search results | WORKFLOW |
| **Engine** | Topic extraction (Rust) | ORP + timing loop (Rust) | FTS5 index (SQLite) | ENH §Technical |
| **Driver loop** | User clicks `Enter` | Wall-clock timer (delay-based) | User-driven (Enter/Esc) | ENH + WORKFLOW |
| **State writes** | None on its own | `current_word_index` every tick | `current_word_index` on Jump | derived |
| **Notes writable?** | Yes (at chapter start) | Yes (at current word) | Yes (at hit position) | ENH §3.1/§3.2 + WORKFLOW |

---

## 7. Cross-mode transitions (the navigation graph)

| From → To | Trigger | State change | Source |
|-----------|---------|--------------|--------|
| Skim → RSVP | `Enter` on chapter | `current_word_index = chapter.start_word_index` | ENH §3.1 |
| Skim → Scan | `/` | none | WORKFLOW §Skimming Mode |
| Skim → Library | `q` | none | TUI §Skim |
| RSVP → Scan | `/` | none | WORKFLOW §RSVP Mode |
| RSVP → Skim | `m` then "skim" | none | ENH §3.3 Hybrid Mode |
| RSVP → Library | `Esc` | save progress to SQLite | TUI §2 |
| Scan → RSVP | `Enter` | `current_word_index = hit.word_index` | WORKFLOW §Scanning Mode |
| Scan → RSVP | `Esc` | none | WORKFLOW §Scanning Mode |
| RSVP → Complete | `current_word_index ≥ word_count` | mark book complete | WORKFLOW §Reading Complete |
| Complete → Library | `q` | persist session stats | WORKFLOW §Reading Complete |
| Any → Settings | `s` | none (modal) | PRD §8.1 |

---

## 8. Hybrid (auto-switching) workflow (UX-S05)

The forward-looking *Hybrid* mode (ENH §3.3) describes an idealized round trip:

> **Skim → Select interesting chapter → RSVP read → Scan for details → Take notes**

This is **informational only** (no concrete key binding specified) and is
tagged as Phase 3 in the roadmap. The above transition table is what the
app must minimally support to make this round-trip possible; the *auto* part
of "auto-switching" is not specified.

---

## 9. Spec → source-doc coverage check

| Section | Source doc(s) | Coverage |
|---------|---------------|----------|
| §2 Skimming | ENH §1, ENH §3.1, WORKFLOW §Skim Mode | complete |
| §3 RSVP | PRD §3.2, PRD §8.2, TUI §2 | complete + key conflict flagged |
| §4 Scanning | ENH §2, ENH §3.2, WORKFLOW §Scan Mode | complete |
| §5 Completion | WORKFLOW §Reading Complete | mostly complete (placeholders flagged) |
| §6 Mode matrix | WORKFLOW §Mode Comparison | complete |
| §7 Transitions | WORKFLOW + ENH (synthesized) | complete |
| §8 Hybrid | ENH §3.3 | informational only |