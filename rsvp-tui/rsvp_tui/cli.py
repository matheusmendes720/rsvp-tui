"""Command-line interface for RSVP."""

import sys
import click
from pathlib import Path
from typing import Optional

from . import __version__
from .app import RSVPApp
from .managers.library_manager import LibraryManager
from .models import Config


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="rsvp")
@click.pass_context
def cli(ctx):
    """RSVP Speed Reader - Terminal User Interface for speed reading."""
    if ctx.invoked_subcommand is None:
        # Launch TUI app
        app = RSVPApp()
        app.run()


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--wpm", "-w", type=int, default=None, help="Reading speed in WPM")
@click.option("--chapter", "-c", type=int, default=0, help="Start at chapter")
@click.option("--word", "-p", type=int, default=0, help="Start at word position")
@click.option("--focus", "-f", is_flag=True, help="Start in focus mode")
def read(
    file_path: Path,
    wpm: Optional[int],
    chapter: int,
    word: int,
    focus: bool,
):
    """Read a book by file path or ID."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    
    # Try to import the file
    try:
        book = library.import_book(file_path)
        click.echo(f"Imported: {book.title} by {book.author}")
        
        # Apply options
        if wpm:
            book.current_word_index = word
        
        # Launch app with this book
        app = RSVPApp()
        app.current_book = book
        app.config = config
        if focus:
            app.focus_mode = True
        app.run()
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
def import_(file_path: Path):
    """Import a book into the library."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    
    try:
        book = library.import_book(file_path)
        click.echo(f"✓ Imported: {book.title} by {book.author}")
        click.echo(f"  ID: {book.id}")
        click.echo(f"  Words: {book.word_count:,}")
        click.echo(f"  Chapters: {len(book.chapters)}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command(name="library")
@click.option("--list", "-l", "list_books", is_flag=True, help="List all books")
@click.option("--search", "-s", help="Search books")
def library_cmd(list_books: bool, search: Optional[str]):
    """Manage book library."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    
    if list_books:
        books = library.list_books(search=search)
        
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
    else:
        # Launch TUI at library view
        app = RSVPApp()
        app.run()


@cli.command()
@click.argument("book_id")
def remove(book_id: str):
    """Remove a book from the library."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    
    book = library.get_book(book_id)
    if not book:
        click.echo(f"Book not found: {book_id}", err=True)
        sys.exit(1)
    
    if click.confirm(f"Delete '{book.title}' by {book.author}?"):
        library.delete_book(book_id)
        click.echo("Book deleted.")


@cli.command()
@click.argument("book_id")
def stats(book_id: str):
    """Show reading statistics for a book."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    
    book = library.get_book(book_id)
    if not book:
        click.echo(f"Book not found: {book_id}", err=True)
        sys.exit(1)
    
    click.echo(f"\n[b]Statistics: {book.title}[/b]\n")
    click.echo(f"Author: {book.author}")
    click.echo(f"File type: {book.file_type}")
    click.echo(f"Total words: {book.word_count:,}")
    click.echo(f"Chapters: {len(book.chapters)}")
    click.echo(f"\nReading Progress:")
    click.echo(f"  Current word: {book.current_word_index:,}")
    click.echo(f"  Completion: {book.completion_percentage:.1f}%")
    if book.last_read_date:
        click.echo(f"  Last read: {book.last_read_date.strftime('%Y-%m-%d %H:%M')}")


@cli.command()
def config():
    """Open settings configuration."""
    app = RSVPApp()
    # Start at settings view
    def start_at_settings():
        app._show_settings()
    
    app.on_mount = start_at_settings
    app.run()


@cli.command()
def stats_all():
    """Show overall library statistics."""
    config = Config.load()
    library = LibraryManager(config.library_db_path)
    
    stats = library.get_statistics()
    
    click.echo("\n[Library Statistics]\n")
    click.echo(f"Total books: {stats['total_books']}")
    click.echo(f"Total words: {stats['total_words']:,}")
    
    if stats['recently_read']:
        click.echo("\nRecently read:")
        for book in stats['recently_read']:
            click.echo(f"  • {book['title']} ({book['progress']:.0f}%)")


def main():
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\nInterrupted.")
        sys.exit(130)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
