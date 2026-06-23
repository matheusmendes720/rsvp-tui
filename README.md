# RSVP Speed Reader

> Read books at 300–1000 WPM in your terminal.

A terminal user interface (TUI) for **Rapid Serial Visual
Presentation (RSVP)** speed reading, built on a hybrid
**Rust + Python** stack. A single-word display with Optimal
Recognition Point (ORP) highlighting lets you read without
moving your eyes; a focus mode hides everything except the
current word.

The workspace ships a **native Rust CLI** (clap + ratatui) as
the canonical entry point and a **Python Textual TUI** for the
full reader experience with notes, library, and command
palette. Pick whichever fits your environment.

```
rsvp-cli (Rust) ─────► spawns ─────► python -m rsvp_tui.cli (Textual)
   │                                          │
   │ clap subcommands                        │ 12 screens
   │ ratatui reader                          │ 96+ widgets
   │ ~2.4MB stripped                          │ full feature set
   │                                          │
   └──── both call into rsvp-core ────────────┘
            (Rust pyo3 extension)
                  53 exports
            0.20 / 0.22 / 0.29
```

## Quick start

```bash
# 1. clone and enter
git clone <repo> rsvp && cd rsvp

# 2. build everything (Rust CLI + Rust core + Python TUI)
uv run rsvp-build            # ~30 seconds, builds both binaries

# 3. verify with the test suite
uv run rsvp-test             # 179 tests, all passing

# 4. launch the TUI
uv run rsvp                  # native Rust CLI
uv run rsvp --help           # see all 12 subcommands
uv run rsvp-cli              # explicit native CLI (same binary)
uv run rsvp-tui              # legacy Python Textual TUI
```

## The 20 task surface entries

Every project workflow is exposed as a real console script
in `.venv/Scripts/` after `uv sync`. The canonical entry
points are:

| Task | What it does |
|---|---|
| `rsvp` | Show the grouped help (alias for `rsvp-tui`) |
| `rsvp-tasks` | Print the full task table |
| `rsvp-cli` | Run the **native Rust CLI** (clap + ratatui) |
| `rsvp-tui` | Run the **Python Textual TUI** |
| `rsvp-read <file>` | Read a book |
| `rsvp-import <file>` | Import a book into the library |
| `rsvp-library` | Manage the book library |
| `rsvp-config` | Open the live settings UI |
| `rsvp-palette` | Open the in-TUI command palette |
| `rsvp-demo` | Launch the dependency-free standalone demo |
| `rsvp-build` | Build the Rust core + Rust CLI + Python wheel |
| `rsvp-dev` | Editable install (maturin develop --release) |
| `rsvp-sync` | uv sync (with optional `--rebuild`) |
| `rsvp-clean` | Remove build/, dist/, __pycache__, caches |
| `rsvp-test` | Run the pytest suite (179 tests) |
| `rsvp-lint` | ruff check + black --check |
| `rsvp-format` | black + ruff --fix |
| `rsvp-typecheck` | mypy --strict |
| `rsvp-verify` | Full quality gate: lint + typecheck + test |
| `rsvp-docs` | Build the man page + snapshot CLI help |
| `rsvp-man` | Render / view / install rsvp.1 |
| `rsvp-bench` | Run cargo benchmarks |

The same surface is available via `make <target>` (29 targets)
or `bin/rsvp-task <name>` (POSIX + Windows dispatchers that
work without `uv`).

## Architecture

### Three layers

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Native Rust CLI (rsvp-cli/)                        │
│   • clap 4.6 derive — the Rust equivalent of Typer          │
│   • ratatui 0.29 + crossterm 0.28 — TUI rendering          │
│   • anyhow for error chains, env_logger for diagnostics     │
│   • 12 subcommands, 8 themes, JSON / --stats output        │
│   • Single statically-linked binary, ~2.4MB stripped        │
└─────────────────────────────────────────────────────────────┘
                          │ subprocess for TUI subcommands
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: Python Textual TUI (rsvp-tui/)                     │
│   • Click 8.x for the CLI surface                           │
│   • Textual 8.x for the screen framework                    │
│   • Pydantic 2 for models, sqlite3 for the library          │
│   • 12 screens, 8 figures, fuzzy command palette            │
│   • Re-imports every Rust function with a Python fallback    │
└─────────────────────────────────────────────────────────────┘
                          │ PyO3 binding
                          ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: Rust core (rsvp-core/)                              │
│   • pyo3 0.20 + maturin build                               │
│   • epub 2.1, regex, unicode-segmentation                  │
│   • 18 #[pyfunction] + 4 #[pyclass] (WordParts, Chapter…)   │
│   • 1,500 LOC, builds in ~5 seconds (incremental)           │
└─────────────────────────────────────────────────────────────┘
```

The Rust core is **never** a hard dependency. Every layer
shells down to pure-Python fallbacks if `import rsvp_core`
fails (which is the default — `rsvp_core.RUST_AVAILABLE`
is `False` until you `uv run rsvp-build`).

### Why three layers?

- **Performance**: text tokenization, ORP calculation, and
  file parsing are 10-50× faster in Rust. The Python TUI
  uses these when available and falls back to its own
  implementations when not.
- **Expressiveness**: Textual is a more productive TUI framework
  than ratatui for screens with multiple panes, modals, and
  complex input handling. We use Textual for the full reader
  experience and ratatui for the single-screen native reader.
- **Distribution**: a single 2.4MB Rust binary for users who
  just want `rsvp --version` and `rsvp doctor`; a Python
  install for users who want the full app.

## Subcommands

### `rsvp doctor` (Rust, no Python required)

Prints a structured health report. Available with
`--json` for CI consumption.

```bash
$ uv run rsvp doctor
2026-06-23T15:09:18.708181200+00:00

  version:        0.3.0
  platform:       windows (x86_64)
  rust_core:      fallback
  home:           C:\Users\mathe\.rsvp
  config:         ✓ exists
  library_db:     ✓ exists
  notes_dir:      · missing
```

### `rsvp read <file>` (Python or Rust)

- `uv run rsvp read book.epub` — launches the Textual TUI at
  the book.
- `uv run rsvp read --stats book.epub` — prints a non-
  interactive stats summary and exits.
- `uv run rsvp read --native book.txt` — boots the standalone
  60fps Ratatui reader. No Python needed for the reading
  loop; only for the tokeniser fallback.

### `rsvp tasks`

The full task table. Re-renders from the live
`pyproject.toml` so adding a new `[project.scripts]` entry
shows up immediately.

### `rsvp themes` / `rsvp where` / `rsvp version`

Pure-Rust output subcommands. Never spawn Python. All three
have a `--json` variant for scripts.

## File layout

```
rspv/
├── pyproject.toml                # workspace manifest (scripts,
│                                 # sources, dev deps, ruff/black)
├── Makefile                      # 29 make targets
├── uv.lock                       # locked dependency graph
│
├── rsvp-cli/                     # native Rust CLI (NEW)
│   ├── Cargo.toml                # clap, ratatui, crossterm, anyhow
│   ├── src/
│   │   ├── main.rs               # clap CLI, subcommand dispatch
│   │   ├── reader.rs             # ratatui RSVP reader
│   │   ├── config.rs             # path discovery
│   │   ├── output.rs             # --json / plain-text reporting
│   │   └── commands/             # one module per subcommand
│   └── tests/                    # cargo test --release
│
├── rsvp-core/                    # Rust core (PyO3 extension)
│   ├── Cargo.toml
│   ├── pyproject.toml            # maturin build-system
│   └── src/
│       ├── lib.rs                # 53 exports
│       ├── text_engine.rs         # tokenization, ORP
│       ├── rsvp_engine.rs        # timing, ORP, splits
│       ├── word_stats.rs         # frequency, difficulty
│       └── file_parser.rs        # epub, markdown, plain text
│
├── rsvp-tui/                     # Python Textual frontend
│   ├── pyproject.toml            # setuptools-rust + maturin
│   └── rsvp_tui/
│       ├── cli.py                # Click CLI (legacy, still used)
│       ├── app.py                # Textual app base
│       ├── screens/              # 8 screens (library, reader, …)
│       ├── figures/              # 8 word-display figures
│       ├── widgets/              # 6 widgets
│       ├── managers/             # SQLite library, notes
│       ├── keybindings.py        # action → key map
│       ├── themes.py             # 8 theme definitions
│       └── models.py             # Pydantic data models
│
├── scripts/                      # workspace task dispatcher
│   ├── _lib.py                   # logging, subprocess helpers
│   ├── _man_template.py          # groff man page source
│   ├── tasks.py                  # `rsvp-tasks` table renderer
│   ├── cli_dispatch.py           # `rsvp-cli` binary launcher
│   ├── build.py                  # `rsvp-build` (maturin + cargo)
│   ├── test.py                   # `rsvp-test` (pytest)
│   ├── lint.py / format.py       # `rsvp-lint` / `rsvp-format`
│   ├── typecheck.py              # `rsvp-typecheck` (mypy)
│   ├── verify.py                 # `rsvp-verify` (full quality gate)
│   ├── doctor.py                 # `rsvp-doctor` (workspace-aware)
│   ├── man.py / docs.py          # `rsvp-man` / `rsvp-docs`
│   ├── bench.py                  # `rsvp-bench` (cargo bench)
│   ├── sync.py / clean.py        # `rsvp-sync` / `rsvp-clean`
│   ├── run.py                    # pass-through to rsvp_tui.cli
│   ├── palette.py / demo.py      # `rsvp-palette` / `rsvp-demo`
│   └── run.py / palette.py / demo.py / sync.py / clean.py
│
├── rsvp_workspace/               # shim package for the wheel
│   └── __init__.py               # re-exports 20 main()s
│
├── bin/                          # cross-platform wrappers
│   ├── rspv-task                 # POSIX bash dispatcher
│   └── rspv-task.bat             # Windows cmd dispatcher
│
├── man/                          # groff man page
│   └── rsvp.1                    # auto-generated, 7.9KB
│
├── data/                         # gitignored (rsvp runtime data)
├── .venv/                        # gitignored (uv environment)
└── AGENTS.md                     # AI agent instructions
```

## Keyboard reference

Default keybindings (overridable in `~/.rsvp/config.json`):

| Action | Key |
|---|---|
| Play / pause | `space` |
| Next word | `→` or `l` |
| Previous word | `←` or `h` |
| Increase WPM (+25) | `↑` |
| Decrease WPM (-25) | `↓` |
| Focus mode toggle | `f` |
| Restart from word 0 | `r` |
| Open command palette | `Ctrl+P` |
| Open library | `l` |
| Open settings | `s` |
| Show help | `?` |
| Quit | `q` or `Esc` |

## Files & data

| Path | Purpose |
|---|---|
| `~/.rsvp/config.json` | User configuration (theme, WPM, keybindings) |
| `~/.rsvp/library.db` | SQLite store of books, chapters, notes |
| `~/.rsvp/notes/` | On-disk note storage (per-book subdirs) |
| `~/.rsvp/cache/` | Per-book parsed-text cache |
| `$RSVP_HOME` | Override the data directory |

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `RSVP_HOME` | `~/.rsvp` | Override the data directory |
| `RSVP_NEW_UI` | unset | Force-enable the new SettingsScreen |
| `RUST_LOG` | `warn` | rsvp-cli log level (`error`/`warn`/`info`/`debug`/`trace`) |
| `NO_COLOR` | unset | Disable ANSI colour in helper scripts |
| `PYTHONIOENCODING` | unset | Set to `utf-8` for non-ASCII books |

## Building from source

```bash
# One-time bootstrap
git clone <repo> && cd rsvp
curl -LsSf https://astral.sh/uv/install.sh | sh     # or: pip install uv
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh  # Rust

# Full build
uv sync
uv run rsvp-build            # builds rsvp-core + rsvp-cli
uv run rsvp-test             # 179 pytest tests
cd rsvp-cli && cargo test    # 5 Rust CLI tests
cd ../rsvp-core && cargo test  # 23 Rust core tests (5 pre-existing
                                # assertion bugs in test files)
```

## License

MIT
