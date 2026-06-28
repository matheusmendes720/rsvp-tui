"""Command-line interface for RSVP.

Designed with the same philosophy as ``uv`` / ``cargo``:
short aliases for common commands, a grouped ``--help`` that
surfaces workflow patterns at a glance, and dedicated helper
commands for app management (``where``, ``version``, ``info``).

Layout
------

* :class:`RsvpGroup` — custom ``click.Group`` that resolves
  aliases and renders a grouped help block.
* ``ALIASES`` — maps a short name (``r``, ``ls``, ``cfg``…) to
  its canonical command.
* ``COMMAND_GROUPS`` — controls the help layout and the order
  in which commands are listed.
* Subcommand implementations live below; the bulk of the file
  is straightforward Click boilerplate.
"""

from __future__ import annotations

import json
import os
import platform
import sys
from pathlib import Path

import click

from . import __version__
from .app import RSVPApp
from .managers.library_manager import LibraryManager
from .models import Config

# ---- Aliases + group registry ----------------------------------------------


# Short name -> canonical subcommand. Aliases are NOT registered
# as separate Click commands (that would require a stub command
# that re-dispatches); instead, ``RsvpGroup.get_command`` resolves
# them. This keeps the implementation list in one place.
ALIASES: dict[str, str] = {
    "r": "read",
    "open": "read",
    "i": "import",
    "add": "import",
    "ls": "library",
    "list": "library",
    "rm": "remove",
    "info": "stats",
    "cfg": "config",
    "diagnose": "doctor",
}

# Commands grouped by category, in the order they should appear
# in ``--help``. Each entry is ``(category, [commands...])``.
COMMAND_GROUPS: list[tuple[str, list[str]]] = [
    ("Reading", ["read"]),
    ("Library", ["import", "library", "remove", "stats"]),
    ("Configuration", ["config"]),
    ("Diagnostics", ["doctor", "themes"]),
    ("App", ["where", "version"]),
]


class RsvpGroup(click.Group):
    """Click group with aliases and a grouped ``--help`` layout."""

    def get_command(self, ctx: click.Context, name: str) -> click.Command | None:
        # Resolve an alias to its canonical name before lookup.
        canonical = ALIASES.get(name, name)
        return super().get_command(ctx, canonical)

    def list_commands(self, ctx: click.Context) -> list[str]:
        """Return subcommand names in grouped order, then any extras."""
        seen = set()
        ordered: list[str] = []
        for _, cmds in COMMAND_GROUPS:
            for c in cmds:
                if c not in seen and c in self.commands:
                    seen.add(c)
                    ordered.append(c)
        # Append anything registered but not in the group list
        # (keeps ``--help`` exhaustive if someone adds a command
        # without updating COMMAND_GROUPS).
        for c in sorted(self.commands):
            if c not in seen:
                seen.add(c)
                ordered.append(c)
        return ordered

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Render commands grouped by category, one section per group."""
        # Collect (category, name, help) rows.
        rows: list[tuple[str, str, str]] = []
        for category, cmds in COMMAND_GROUPS:
            for name in cmds:
                cmd = self.get_command(ctx, name)
                if cmd is None or getattr(cmd, "hidden", False):
                    continue
                rows.append(
                    (category, name, cmd.get_short_help_str(limit=60) or "")
                )
        if not rows:
            return
        # Group by category, print a section per category.
        last_cat = object()
        for cat, name, help_text in rows:
            if cat != last_cat:
                with formatter.section(f"{cat} Commands"):
                    pass
                last_cat = cat
            # Click renders a 24-char name column by default; we
            # want a bit more room for the longer command names.
            formatter.write_text(f"  {name:<14} {help_text}")

    def format_epilog(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Print a quickstart epilog and shell-completion hint."""
        # Click's ``write_text`` does not add newlines; the epilog
        # needs explicit ``\n`` separators or the lines run
        # together. We split on newlines and emit each as its own
        # paragraph so the formatter respects indentation.
        epilog = (
            "Quickstart:\n"
            "  rsvp book.epub    Read a book (alias: r)\n"
            "  rsvp i book.pdf   Import a book (alias: i)\n"
            "  rsvp ls           List your library (alias: ls)\n"
            "  rsvp where        Show data directory paths\n"
            "  rsvp doctor       Diagnose the install\n"
            "\n"
            "Shell completion:\n"
            "  eval \"$(_RSVP_COMPLETE=bash_source rsvp)\"   # bash\n"
            "  eval \"$(_RSVP_COMPLETE=zsh_source rsvp)\"    # zsh\n"
        )
        for block in epilog.split("\n\n"):
            formatter.write_paragraph()
            for line in block.split("\n"):
                formatter.write_text(line)


# ---- Root group -------------------------------------------------------------


@click.group(cls=RsvpGroup, invoke_without_command=True)
@click.version_option(version=__version__, prog_name="rsvp")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """RSVP Speed Reader — read books at 300-1000 WPM in your terminal."""
    if ctx.invoked_subcommand is None:
        # No subcommand: launch the TUI.
        app = RSVPApp()
        app.run()


# ---- Reading ----------------------------------------------------------------


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--wpm", "-w", type=int, default=None, help="Override reading speed in WPM"
)
@click.option(
    "--word", "-p", type=int, default=0, help="Start at word position"
)
@click.option("--focus", "-f", is_flag=True, help="Start in focus mode")
def read(
    file_path: Path,
    wpm: int | None,
    word: int,
    focus: bool,
) -> None:
    """Read a book by file path (imports if not in library)."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    try:
        book = library.import_book(file_path)
        click.echo(f"Imported: {book.title} by {book.author}")
        # The ``word`` option is the start position; only honor it
        # if the caller actually passed a non-default value. The
        # old code gated this on ``if wpm`` which was a copy-paste
        # bug.
        if word:
            book.current_word_index = word
        app = RSVPApp()
        app.current_book = book
        app.config = config
        if wpm:
            app.config.default_wpm = wpm
        if focus:
            app.focus_mode = True
        app.run()
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.read", exc)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


# ---- Library ---------------------------------------------------------------


@cli.command(name="import")
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def import_(file_path: Path) -> None:
    """Import a book into the library."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    try:
        book = library.import_book(file_path)
        click.echo(f"✓ Imported: {book.title} by {book.author}")
        click.echo(f"  ID:        {book.id}")
        click.echo(f"  Words:     {book.word_count:,}")
        click.echo(f"  Chapters:  {len(book.chapters)}")
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.import_", exc)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--list", "-l", "list_books", is_flag=True, help="List all books")
@click.option("--search", "-s", help="Search books by title/author")
def library(list_books: bool, search: str | None) -> None:
    """Manage book library (or launch the TUI at the library view)."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    if list_books or search:
        try:
            books = library.list_books(search=search)
        except Exception as exc:
            from .logging_ import telemetry_error
            telemetry_error("cli.library.list_books", exc)
            click.echo(f"Error listing books: {exc}", err=True)
            sys.exit(1)
        if not books:
            click.echo("No books in library.")
            return
        click.echo(f"{'ID':<20} {'Title':<30} {'Author':<20} {'Progress':<10}")
        click.echo("-" * 80)
        for book in books:
            progress = f"{book.completion_percentage:.0f}%"
            title = book.title[:28] + ".." if len(book.title) > 30 else book.title
            author = book.author[:18] + ".." if len(book.author) > 20 else book.author
            click.echo(f"{book.id:<20} {title:<30} {author:<20} {progress:<10}")
        return
    # No flags: launch the TUI at the library view.
    try:
        app = RSVPApp()
        app.run()
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.library.app_run", exc)
        raise


@cli.command()
@click.argument("book_id")
def remove(book_id: str) -> None:
    """Remove a book from the library."""
    try:
        config = Config.load()
        library = LibraryManager(config.library_db_path)
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.remove.config", exc)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    try:
        book = library.get_book(book_id)
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.remove.get_book", exc)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    if not book:
        click.echo(f"Book not found: {book_id}", err=True)
        sys.exit(1)
    try:
        if click.confirm(f"Delete '{book.title}' by {book.author}?"):
            library.delete_book(book_id)
            click.echo("Book deleted.")
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.remove.delete", exc)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("book_id")
def stats(book_id: str) -> None:
    """Show reading statistics for a book (verbose)."""
    try:
        config = Config.load()
        library = LibraryManager(config.library_db_path)
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.stats.config", exc)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    try:
        book = library.get_book(book_id)
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.stats.get_book", exc)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    if not book:
        click.echo(f"Book not found: {book_id}", err=True)
        sys.exit(1)
    click.echo(f"\nStatistics: {book.title}\n")
    click.echo(f"  Author:           {book.author}")
    click.echo(f"  File type:        {book.file_type}")
    click.echo(f"  Total words:      {book.word_count:,}")
    click.echo(f"  Chapters:         {len(book.chapters)}")
    click.echo("\nReading progress:")
    click.echo(f"  Current word:     {book.current_word_index:,}")
    click.echo(f"  Completion:       {book.completion_percentage:.1f}%")
    if book.last_read_date:
        click.echo(f"  Last read:        {book.last_read_date.strftime('%Y-%m-%d %H:%M')}")


# ---- Configuration ---------------------------------------------------------


@cli.command()
def config() -> None:
    """Open the settings UI (live preview, debounced auto-save)."""
    try:
        app = RSVPApp()
        # Force the new-UI path so the modal SettingsScreen is used.
        from .screens.settings_screen import SettingsScreen

        original_on_mount = app.on_mount

        def _on_mount() -> None:
            original_on_mount()
            app.push_screen(SettingsScreen(app.config))

        app.on_mount = _on_mount  # type: ignore[method-assign]
        app.run()
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.config.app_run", exc)
        raise


# ---- Diagnostics ------------------------------------------------------------


@cli.command()
def doctor() -> None:
    """Diagnose the local RSVP install: paths, schema, library.

    Prints a JSON report. Exit code 0 on a healthy install,
    1 if anything is wrong (e.g. config or library missing).
    """
    cfg = Config.load()
    report: dict = {
        "version": __version__,
        "config_path": str(cfg.config_path),
        "config_exists": cfg.config_path.exists(),
        "schema_version": cfg.schema_version,
        "library_db": str(cfg.library_db_path),
        "library_exists": cfg.library_db_path.exists(),
        "notes_dir": str(cfg.notes_dir),
        "notes_exists": cfg.notes_dir.exists(),
        "theme": cfg.theme,
        "figure_id": cfg.figure_id,
        "new_ui_env": os.environ.get("RSVP_NEW_UI", "<unset>"),
    }
    try:
        library = LibraryManager(cfg.library_db_path)
        report["book_count"] = len(library.list_books())
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.doctor", exc)
        report["book_count_error"] = str(exc)
    click.echo(json.dumps(report, indent=2))
    healthy = (
        report["config_exists"]
        and report["library_exists"]
        and "book_count_error" not in report
    )
    sys.exit(0 if healthy else 1)


@cli.command()
def themes() -> None:
    """List the available themes."""
    try:
        from .themes import all_themes, default_theme

        current_id = getattr(default_theme(), "id", "dark")
        click.echo(f"Current: {current_id}\n")
        click.echo(f"{'ID':<12} {'Name':<20}")
        click.echo("-" * 32)
        for t in all_themes():
            marker = " *" if t.id == current_id else "  "
            click.echo(f"{marker} {t.id:<10} {t.name}")
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.themes", exc)
        raise


# ---- App management --------------------------------------------------------


@cli.command()
def where() -> None:
    """Show the data directory paths used by RSVP."""
    try:
        cfg = Config.load()
        click.echo("RSVP data locations:\n")
        rows = [
            ("Config file", cfg.config_path),
            ("Library DB", cfg.library_db_path),
            ("Notes dir", cfg.notes_dir),
            ("Cache dir", getattr(cfg, "cache_dir", None)),
        ]
        for label, path in rows:
            if path is None:
                click.echo(f"  {label:<14} <not configured>")
                continue
            p = Path(path)
            marker = "✓" if p.exists() else "·"
            click.echo(f"  {marker} {label:<14} {p}")
        click.echo(
            "\nTo override, set RSVP_HOME to a directory of your choice."
        )
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.where", exc)
        raise


@cli.command()
def version() -> None:
    """Show version, Python, and platform info (more than --version)."""
    try:
        cfg = Config.load()
        info = {
            "rsvp": __version__,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "config_schema": cfg.schema_version,
            "rust_core": _safe_check_rust(),
        }
        for k, v in info.items():
            click.echo(f"  {k:<14} {v}")
        click.echo(f"  {'config_path':<14} {cfg.config_path}")
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.version", exc)
        raise


def _safe_check_rust() -> str:
    """Best-effort check for the optional Rust core extension."""
    try:
        from . import RUST_AVAILABLE

        return "available" if RUST_AVAILABLE else "not built"
    except Exception:
        return "unknown"


# ---- Entry point ------------------------------------------------------------


def main() -> None:
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
        sys.exit(130)
    except Exception as exc:
        from .logging_ import telemetry_error
        telemetry_error("cli.main", exc)
        click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
