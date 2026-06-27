# RSVP-TUI Documentation Index (Doc-as-Code Set)

> **Source of truth:** This index links every component, requirement, and decision
> to the planning artifacts that define them. Every doc in this set is
> **specification-only** — it describes what the app *should* be per the PRD,
> TUI_FEATURES, WORKFLOW, and ENHANCEMENTS docs as of 2026-04-10, plus the
> three-mode research arc. For what is *actually built today* see `AGENTS.md`
> and the workspace `CLAUDE.md`.

---

## 1. Doc set inventory

| # | File | Purpose | Primary source |
|---|------|---------|----------------|
| 1 | `README.docs_index.md` | This file — meta index + traceability | synthesized |
| 2 | `SPEC.three_modes.md` | Skim / Scan / RSVP roadmap & UX arcs | ENHANCEMENTS.md, WORKFLOW.md |
| 3 | `SPEC.component_design.md` | Per-component breakdown for CLI + TUI | PRD §3, TUI_FEATURES.md |
| 4 | `SPEC.data_architecture.md` | Dataclasses, SQLite schema, on-disk layout | PRD §4, §7, TUI_FEATURES.md §Data Storage |
| 5 | `SPEC.algorithms.md` | BFF algorithm + data structures (tokenize / ORP / timing / search / skim) | PRD §3.1 (Rust), ENHANCEMENTS.md §Technical Implementation |
| 6 | `SPEC.requirements_traceability.md` | Every functional req ↔ design element ↔ UI element + timeline | All four source docs |

---

## 2. Source-document provenance

Every requirement ID in this doc set cites the source document it came from.
When in conflict, this is the precedence (highest first):

1. **PRD.md** (2026-04-10, Draft v1.0) — the authoritative *what* (functional requirements, data model, perf budgets, dev phases)
2. **TUI_FEATURES.md** — the authoritative *UI surface* (screens, key bindings, mockups)
3. **WORKFLOW.md** — the authoritative *user journeys* (Skim → RSVP → Scan round-trip)
4. **ENHANCEMENTS.md** — the authoritative *forward roadmap* (Phases 3 & 4 — Skim, Scan, Hybrid, FTS, topic extraction)

When a requirement appears in only one of the four docs, it is tagged with the doc name and treated as informational, not normative.

---

## 3. Requirement-ID convention

Each spec uses IDs of the form **`{AREA}-{NNN}`** so they can be cross-referenced
and traced through the traceability matrix:

| Area prefix | Meaning |
|-------------|---------|
| `CLI-`      | Command-line surface, flags, exit codes |
| `TUI-`      | TUI screens, widgets, key bindings |
| `FMT-`      | File-format support / parsing pipeline |
| `DATA-`     | Persistent data structures (dataclasses, SQLite schema, on-disk layout) |
| `ALG-`      | Algorithm / data-structure (BFF-tier logic) |
| `UX-`       | User journey / mode transitions (Skim / Scan / RSVP) |
| `PERF-`     | Performance budget |
| `NF-`       | Non-functional (testability, fallback, portability) |

---

## 4. Navigation by user question

> *"What is the app, and what are the modes?"*
> → `SPEC.three_modes.md`

> *"What components exist and how do they talk?"*
> → `SPEC.component_design.md`

> *"What data lives where, and in what shape?"*
> → `SPEC.data_architecture.md`

> *"What algorithms compute ORP / timing / search / skim?"*
> → `SPEC.algorithms.md`

> *"Where does every requirement come from, and which UI covers it?"*
> → `SPEC.requirements_traceability.md`

> *"How has the plan evolved over time?"*
> → Timeline at the bottom of `SPEC.requirements_traceability.md`

---

## 5. Out-of-scope (explicitly)

These are **not** described here — they live in their own docs and are referenced
only when the spec cites them:

- Build / install commands → `rsvp-core/README.md`, `rsvp-tui/README.md`
- Test commands → `ARCHITECTURE_SUMMARY.md` §Testing
- Credit / source-repos → `PROJECT_SUMMARY.md` §Credits
- Man-page rendering → workspace `man/rsvp.1`

This doc set assumes the reader already knows the four-letter "what is RSVP" answer:
**R**apid **S**erial **V**isual **P**resentation. If they don't, `PRD.md §1` is the
one-paragraph primer.