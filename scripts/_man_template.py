"""Source of truth for ``man/rsvp.1``.

Why a Python template? The man page is a derivative of the click
help, the keybinding table, and the workspace task list. Keeping
it in Python means we can re-render on every ``uv run man`` and
the page can never drift from the code it documents.

Public surface:

    from scripts._man_template import render
    text = render()
    Path("man/rsvp.1").write_text(text)

The output is plain groff/troff (no preprocessing). It uses the
``-man`` macro package which ships with every Unix system and
renders fine in WSL, macOS, and most Linux distributions.
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path

# Re-use the same data the CLI and keybinding layer use, so the
# man page and the running app agree on what exists.
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _load_version() -> str:
    try:
        from rsvp_tui import __version__

        return __version__
    except Exception:
        return "0.3.0"


def _load_rust_cli_version() -> str:
    """Return the rsvp-cli (Rust) version, or "?" if the
    binary isn't built yet. The binary prints its version
    string on ``rsvp --version``; we read the same value from
    the Cargo.toml so the man page is consistent with the
    binary even before it's compiled.
    """
    import tomllib

    cargo = _REPO / "rsvp-cli" / "Cargo.toml"
    if not cargo.exists():
        return "?"
    try:
        data = tomllib.loads(cargo.read_text(encoding="utf-8"))
        return data.get("package", {}).get("version", "?")  # type: ignore[no-any-return]
    except Exception:
        return "?"


def _load_keybindings() -> list[tuple[str, str, str]]:
    """Return (action, key, description) triples."""
    try:
        from rsvp_tui.keybindings import (
            BINDING_DESCRIPTIONS,
            DEFAULT_BINDINGS,
        )
        default_bindings: dict[str, str] = DEFAULT_BINDINGS
        binding_descriptions: dict[str, str] = BINDING_DESCRIPTIONS
    except Exception:
        default_bindings = {}
        binding_descriptions = {}
    rows: list[tuple[str, str, str]] = []
    for action in default_bindings:
        rows.append(
            (
                action.replace("_", " "),
                default_bindings[action],
                binding_descriptions.get(action, ""),
            )
        )
    return rows


def _load_palette() -> list[tuple[str, str]]:
    """Return (command id, title) from the in-TUI command palette."""
    try:
        from rsvp_tui.screens.command_palette import DEFAULT_COMMANDS

        return [(c.id, c.title) for c in DEFAULT_COMMANDS]
    except Exception:
        return []


def _load_figures() -> list[tuple[str, str, str, str]]:
    """Return (id, name, description, default_key) for every
    registered figure.

    The registry is the same singleton the ``ReaderScreen``
    reads from at runtime, so adding a figure here updates
    the man page automatically on the next ``rsvp-man``.
    """
    try:
        from rsvp_tui.figures.registry import default_registry
    except Exception:
        return []
    try:
        registry = default_registry()
    except Exception:
        return []
    rows: list[tuple[str, str, str, str]] = []
    for cls in registry.all():
        try:
            rows.append(
                (
                    cls.id,
                    cls.name,
                    cls.description,
                    getattr(cls, "default_keybinding", "—"),
                )
            )
        except Exception:
            continue
    return rows


def _load_themes() -> list[tuple[str, str]]:
    """Return (id, name) pairs from the in-app theme registry.

    We import the theme registry the same way the Rust CLI
    does (a hard-coded catalog mirroring ``rsvp_tui.themes``)
    so the man page can be rendered even if the Python theme
    module can't be imported (e.g. before ``uv run rsvp-build``
    has installed ``rsvp_tui`` editable).
    """
    # First preference: the live Python registry.
    try:
        from rsvp_tui.themes import all_themes

        return [(t.id, t.name) for t in all_themes()]
    except Exception:
        pass
    # Fallback: hard-coded list (mirrors ``commands/themes.rs``).
    return [
        ("dark", "Dark (default)"),
        ("light", "Light"),
        ("solarized", "Solarized"),
        ("monokai", "Monokai"),
        ("solarized-dark", "Solarized Dark"),
        ("gruvbox", "Gruvbox"),
        ("nord", "Nord"),
        ("dracula", "Dracula"),
    ]


# --- groff helpers ----------------------------------------------------------


def _h(level: int, text: str) -> str:
    """Section header. level 1 = .SH, 2 = .SS."""
    macro = "SH" if level == 1 else "SS"
    return f".{macro} {text}\n"


def _p(text: str = "") -> str:
    """Paragraph. Empty text means a blank line."""
    return f"{text}\n" if text else "\n"


def _tag(label: str, body: str) -> str:
    """Indented tag/body pair, e.g. \fB--wpm\fR \\fIN\\fR."""
    return f".TP\n\\fB{label}\\fR\n{body}\n"


def _bullet(items: list[str]) -> str:
    return "".join(f"\\(bu {it}\n" for it in items) + "\n"


def _table(rows: list[tuple[str, str, str]], col_widths: tuple[int, int]) -> str:
    """3-column man-page table rendered as IP/PP pairs.

    groff -man has no real tables, so we use indented paragraphs.
    col_widths = (key_col, desc_col) measured in characters; the
    action column takes whatever's left.
    """
    out = []
    for action, key, desc in rows:
        out.append(
            f".TP\n"
            f"\\fB{action:<{col_widths[0]}}\\fR "
            f"\\fI{key:<{col_widths[1]}}\\fR\n"
            f"{desc}\n"
        )
    return "".join(out)


# --- the page --------------------------------------------------------------


def render() -> str:
    version = _load_version()
    rust_cli_version = _load_rust_cli_version()
    today = _dt.date.today().isoformat()
    keys = _load_keybindings()
    palette = _load_palette()
    figures = _load_figures()
    themes = _load_themes()

    parts: list[str] = []
    # ---- header -----------------------------------------------------------
    parts.append(
        f'.TH RSVP 1 "{today}" "rsvp {version} (rsvp-cli {rust_cli_version})" "User Commands"\n'
    )
    parts.append(_h(1, "NAME"))
    parts.append(
        _p(
            "rsvp \\(en terminal speed reader with Rapid Serial Visual "
            "Presentation (RSVP) and an in-TUI command palette."
        )
    )

    # ---- synopsis ---------------------------------------------------------
    parts.append(_h(1, "SYNOPSIS"))
    parts.append(_p("\\fBrsvp\\fR [\\fIOPTIONS\\fR] [\\fIcommand\\fR] [\\fIargs\\fR]"))
    parts.append(_p("Launches the TUI when no subcommand is given."))

    # ---- description ------------------------------------------------------
    parts.append(_h(1, "DESCRIPTION"))
    parts.append(
        _p(
            "RSVP is a terminal user interface (TUI) for reading text files at "
            "300\\-1000 words per minute using the RSVP method: a single word is "
            "shown at a time, centered on its Optimal Recognition Point (ORP). "
            "The Python frontend (Textual) is backed by a Rust core "
            "(\\fIrsvp\\-core\\fR) that handles tokenization, ORP calculation, "
            "and file parsing."
        )
    )
    parts.append(_p("Supported file types: Markdown, plain text, EPUB, and PDF."))
    parts.append(
        _p(
            "Project management is exposed as a set of \\fBuv run\\fR "
            "tasks; see the \\fBTASKS\\fR section below."
        )
    )

    # ---- commands ---------------------------------------------------------
    parts.append(_h(1, "COMMANDS"))
    # Native Rust CLI subcommands — handled by the rsvp.exe
    # binary directly. The Python side of the project exposes
    # the same surface through ``python -m rsvp_tui.cli`` and
    # through the ``uv run rsvp-cli`` shim.
    parts.append(_h(2, "Native Rust CLI (rsvp-cli)"))
    parts.append(
        _p(
            "The native binary at ``rsvp-cli/target/release/rsvp.exe`` "
            "is the canonical entry point. It is a single "
            "statically-linked executable (``~2.4MB`` stripped) that "
            "uses clap 4.6 derive macros (the Rust equivalent of "
            "Python's Typer) and ratatui 0.29 for the optional "
            "native reader."
        )
    )
    parts.append(_p("Subcommands exposed by ``rsvp.exe`` (via the ``rsvp-cli`` console script):"))
    rust_commands: list[tuple[str, str]] = [
        ("tui", "Launch the interactive Textual TUI (default)."),
        (
            "read <file>",
            "Read a book by file path. ``--stats`` prints a non-interactive "
            "summary; ``--native`` boots the standalone Ratatui reader.",
        ),
        ("import <file>", "Import a book into the library."),
        ("library", "Manage the library. ``--list`` / ``--search <text>`` print to stdout."),
        ("remove <book_id>", "Delete a book from the library (with ``--yes`` to skip the prompt)."),
        ("stats <book_id>", "Show verbose reading statistics for a book."),
        ("config", "Open the live settings UI (delegates to the Python Textual app)."),
        ("doctor", "Print a structured health report. ``--json`` for CI consumption."),
        ("themes", "List the available themes. ``--json`` for scripts."),
        ("where", "Show the data directory paths used by RSVP. ``--json`` for scripts."),
        ("version", "Show version, Python, platform, and rust_core status. ``--json`` available."),
        ("tasks", "Discover and print the workspace task table from pyproject.toml."),
        ("help [<subcommand>]", "Print top-level help (or per-subcommand help)."),
    ]
    for name, desc in rust_commands:
        parts.append(_tag(f"\\fBrsvp {name}\\fR", desc))

    parts.append(_h(2, "Python Textual CLI (rsvp_tui.cli)"))
    parts.append(
        _p(
            "The Python CLI at ``python -m rsvp_tui.cli`` exposes the "
            "same subcommand names with the same semantics. Use it "
            "directly when you want to avoid the Rust binary "
            "(e.g. on a machine without the Rust toolchain) or when "
            "you want the click-style grouped help output."
        )
    )
    commands: list[tuple[str, str]] = [
        (
            "read <file>",
            "Read a book by file path (imports on first run). "
            "Options: \\fB\\-\\-wpm\\fR N, \\fB\\-\\-word\\fR N, "
            "\\fB\\-\\-focus\\fR.",
        ),
        (
            "import <file>",
            "Import a book into the library. Prints ID, word " "count, and chapter count.",
        ),
        (
            "library",
            "Browse the library. With no flags, opens the library screen. "
            "\\fB\\-\\-list\\fR / \\fB\\-\\-search\\fR \\fItext\\fR print to stdout.",
        ),
        ("remove <book_id>", "Delete a book from the library (prompts to confirm)."),
        ("stats <book_id>", "Show verbose reading statistics for a book."),
        ("config", "Open the live settings UI with debounced auto\\-save."),
        ("doctor", "Print a JSON diagnostic report. Exit 0 if healthy."),
        ("themes", "List the available themes (current theme is starred)."),
        ("where", "Print the data directory paths (config, DB, notes)."),
        ("version", "Print version, Python, platform, schema, and rust core status."),
    ]
    for name, desc in commands:
        parts.append(_tag(name, desc))

    parts.append(_h(2, "Aliases"))
    parts.append(
        _p(
            "Short forms resolve to the canonical subcommand: "
            "\\fBr\\fR=\\fBread\\fR, \\fBopen\\fR=\\fBread\\fR, "
            "\\fBi\\fR/\\fBadd\\fR=\\fBimport\\fR, \\fBls\\fR/\\fBlist\\fR=\\fBlibrary\\fR, "
            "\\fBrm\\fR=\\fBremove\\fR, \\fBinfo\\fR=\\fBstats\\fR, "
            "\\fBcfg\\fR=\\fBconfig\\fR, \\fBdiagnose\\fR=\\fBdoctor\\fR."
        )
    )

    # ---- global options ---------------------------------------------------
    parts.append(_h(1, "OPTIONS"))
    parts.append(_tag("\\fB\\-\\-version\\fR", "Print the version of rsvp and exit."))
    parts.append(
        _tag(
            "\\fB\\-\\-help\\fR",
            "Print the grouped help (Reading, Library, Configuration, " "Diagnostics, App).",
        )
    )

    # ---- tasks ------------------------------------------------------------
    parts.append(_h(1, "TASKS"))
    parts.append(
        _p(
            "Project management lives in the workspace \\fBpyproject.toml\\fR and "
            "is run via \\fBuv run <task>\\fR. Each task is a real Python entry "
            "point in \\fIscripts/\\fR; run \\fBuv run tasks\\fR for the live table."
        )
    )
    tasks: list[tuple[str, str]] = [
        ("tui", "Launch the interactive TUI (default)."),
        ("read", "Forward to \\fBrsvp read\\fR."),
        ("import", "Forward to \\fBrsvp import\\fR."),
        ("library", "Forward to \\fBrsvp library\\fR."),
        ("config", "Forward to \\fBrsvp config\\fR."),
        ("doctor", "Forward to \\fBrsvp doctor\\fR with workspace extras."),
        ("themes", "Forward to \\fBrsvp themes\\fR."),
        ("where", "Forward to \\fBrsvp where\\fR."),
        ("version", "Forward to \\fBrsvp version\\fR."),
        ("palette", "Open the in\\-TUI command palette directly."),
        ("demo", "Run the dependency\\-free \\fIdemo_tui.py\\fR."),
        ("build", "Build the Rust extension and install the Python package."),
        ("dev", "Editable install (\\fBmaturin develop \\-\\-release\\fR)."),
        ("sync", "\\fBuv sync\\fR (use \\fB\\-\\-rebuild\\fR to rebuild Rust)."),
        (
            "clean",
            "Remove build/, dist/, eggs, bytecode, caches. "
            "\\fB\\-\\-all\\fR also wipes \\fI.venv/\\fR and \\fIuv.lock\\fR.",
        ),
        ("test", "Run the pytest suite (extras forwarded)."),
        ("lint", "\\fBruff check\\fR + \\fBblack \\-\\-check\\fR."),
        ("format", "\\fBblack\\fR + \\fBruff check \\-\\-fix\\fR."),
        ("typecheck", "\\fBmypy \\-\\-strict\\fR."),
        ("verify", "Full quality gate: \\fBlint\\fR + \\fBtypecheck\\fR + \\fBtest\\fR."),
        ("docs", "Build the man page and snapshot the CLI help."),
        ("man", "Render / view / install \\fIrsvp.1\\fR."),
        ("bench", "Run the \\fIcargo bench\\fR micro\\-benchmarks."),
        ("tasks", "Print the live task table (this section, refreshed)."),
    ]
    for name, desc in tasks:
        parts.append(_tag(f"\\fBuv run {name}\\fR", desc))

    # ---- in-tui command palette ------------------------------------------
    if palette:
        parts.append(_h(1, "IN\\-TUI COMMAND PALETTE"))
        parts.append(
            _p(
                "Press \\fBCtrl+P\\fR inside the TUI to open the fuzzy command "
                "palette. The current command set is:"
            )
        )
        for cid, title in palette:
            parts.append(f".TP\n\\fB{cid}\\fR\n{title}\n")
        parts.append(
            _p("Type to filter; \\fBEnter\\fR picks the top match; " "\\fBEsc\\fR dismisses.")
        )

    # ---- keybindings ------------------------------------------------------
    if keys:
        parts.append(_h(1, "KEYBINDINGS"))
        parts.append(_p("Defaults; override per\\-user via \\fBConfig.keybindings\\fR."))
        parts.append(_table(keys, (20, 14)))

    # ---- figures (Phase 1 architecture) ----------------------------------
    if figures:
        parts.append(_h(1, "FIGURES"))
        parts.append(
            _p(
                "A \\fIfigure\\fR is a word-display strategy. The Phase 1 architecture "
                "(\\`\\`RSVP_NEW_UI=1\\`\\`) ships the following figures, all read "
                "live from \\fIrsvp_tui.figures.registry\\fR. Override the active "
                "figure via \\fBConfig.figure_id\\fR; cycle at runtime with "
                "\\fBCtrl+T\\fR (or whatever key the user has bound to "
                "\\fBcycle_figure\\fR)."
            )
        )
        parts.append(".TS\n")
        parts.append("tab(|) lw(16) lw(28) lw(8) lw(40).\n")
        parts.append("_\n")
        parts.append("ID | Name | Key | Description\n")
        parts.append("_\n")
        for fid, name, desc, key in figures:
            # groff's T{} escapes stop the tabs from being
            # interpreted inside the description.
            safe_desc = desc.replace("|", "/")
            parts.append(f"{fid}|{name}|{key}|T{{}}\\fI{safe_desc}\\fRT{{}}\n")
        parts.append("_\n")
        parts.append(".TE\n")
        parts.append("\n")

    # ---- themes -----------------------------------------------------------
    if themes:
        parts.append(_h(1, "THEMES"))
        parts.append(
            _p(
                "Built-in colour themes. Override the active theme via "
                "\\fBConfig.theme\\fR; cycle at runtime with \\fBCtrl+Y\\fR "
                "(or whatever key the user has bound to \\fBcycle_theme\\fR)."
            )
        )
        for tid, tname in themes:
            parts.append(_tag(f"\\fB{tid}\\fR", tname))

    # ---- files ------------------------------------------------------------
    parts.append(_h(1, "FILES"))
    parts.append(_p("Default location is \\fI$RSVP_HOME\\fR or \\fI~/.rsvp/\\fR:"))
    parts.append(
        _bullet(
            [
                "\\fIconfig.json\\fR \\(en user configuration (theme, wpm, keybindings).",
                "\\fIlibrary.db\\fR \\(en SQLite store of books, chapters, and notes.",
                "\\fInotes/\\fR \\(en on\\-disk note storage.",
                "\\fIcache/\\fR \\(en per\\-book parsed\\-text cache.",
            ]
        )
    )

    # ---- environment ------------------------------------------------------
    parts.append(_h(1, "ENVIRONMENT"))
    parts.append(
        _tag("\\fBRSVP_HOME\\fR", "Override the data directory (default \\fI~/.rsvp\\fR).")
    )
    parts.append(
        _tag("\\fBRSVP_NEW_UI\\fR", "Force\\-enable the new SettingsScreen (set to \\fB1\\fR).")
    )
    parts.append(_tag("\\fBNO_COLOR\\fR", "Disable ANSI colour in the helper scripts."))
    parts.append(
        _tag("\\fBPYTHONIOENCODING\\fR", "Set to \\fButf\\-8\\fR when reading non\\-ASCII books.")
    )

    # ---- examples ---------------------------------------------------------
    parts.append(_h(1, "EXAMPLES"))
    parts.append(_p("Launch the TUI at the library view:"))
    parts.append(_p("    rsvp"))
    parts.append(_p("Read a book at 450 WPM in focus mode:"))
    parts.append(_p("    rsvp read ~/books/sapiens.epub \\-\\-wpm 450 \\-\\-focus"))
    parts.append(_p("Import a Markdown file and read it:"))
    parts.append(_p("    rsvp i ./essay.md && rsvp r ./essay.md"))
    parts.append(_p("Re\\-build the Rust extension in dev mode:"))
    parts.append(_p("    uv run dev"))
    parts.append(_p("Run the full quality gate:"))
    parts.append(_p("    uv run verify"))
    parts.append(_p("Render and install the man page:"))
    parts.append(_p("    uv run man \\-\\-install"))

    # ---- diagnostics ------------------------------------------------------
    parts.append(_h(1, "DIAGNOSTICS"))
    parts.append(
        _p(
            "If a book fails to import, the database is missing, or a keybinding "
            "fails to resolve, run \\fBuv run doctor\\fR \\(en the JSON report names "
            "the offending file. Exits 0 only on a healthy install."
        )
    )
    parts.append(
        _p(
            "Exit codes: \\fB0\\fR success, \\fB1\\fR generic error, "
            "\\fB130\\fR interrupted (Ctrl\\-C)."
        )
    )

    # ---- see also ---------------------------------------------------------
    parts.append(_h(1, "SEE ALSO"))
    parts.append(_p("\\fBproject.json\\fR (5), \\fBuv\\fR (1), \\fBman\\fR (1)."))
    parts.append(_p("Online docs: \\fIhttps://example.com/rsvp\\fR (placeholder)."))

    return "".join(parts)


__all__ = ["render"]


if __name__ == "__main__":
    sys.stdout.write(render())
