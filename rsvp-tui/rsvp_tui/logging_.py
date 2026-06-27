"""Centralised logging + structured telemetry for the RSVP TUI.

Call :func:`init_logging` once at application startup (pass the
already-parsed ``Config`` object so we can honour
``config.log_level``).  After that every module that does::

    import logging
    log = logging.getLogger(__name__)

gets a well-behaved logger with timestamps, level, module, and
message.

Telemetry events
----------------
For first-pass TDD observability the module emits structured dict
events on the ``rsvp.telemetry`` logger — a *child* of the root
``rsvp`` logger so it can be routed separately (e.g. to a file or
external collector).  Event names are the ``event`` key:

    event=app.startup
    event=app.shutdown
    event=screen.push       {screen, from_screen}
    event=screen.pop        {screen}
    event=book.open         {book_id, title, word_count}
    event=book.close        {book_id, final_index, total_words}
    event=book.import       {book_id, title, file_type, word_count}
    event=figure.mount      {figure_id, reason}   # reason: initial|swap|restore
    event=figure.swap       {from_id, to_id}
    event=figure.complete   {book_id, figure_id}
    event=transport.play
    event=transport.pause
    event=transport.seek    {word_index, reason}
    event=wpm.change        {from_wpm, to_wpm}
    event=note.create       {book_id, note_id, word_index}
    event=note.delete       {book_id, note_id}
    event=config.load       {schema_version, path}
    event=config.save       {schema_version}
    event=config.reset
    event=chapter.nav       {book_id, from_chapter, to_chapter}
    event=error             {module, exc_type, exc_value, tb}

Usage::

    from .logging_ import init_logging, telemetry
    log = logging.getLogger(__name__)

    # In your startup:
    init_logging(config)       # reads config.log_level / config.log_file

    # TDD telemetry (noop if telemetry logger has no handlers):
    telemetry.info(event="book.open", book_id=book.id, title=book.title)
"""

from __future__ import annotations

import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Optional

# The rsvp hierarchy — every rsvp_tui module should get a logger child of this.
_RSVP_ROOT = "rsvp"

# Our dedicated telemetry child logger.
_telemetry_logger: Optional[logging.Logger] = None


# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------

def init_logging(
    config: Optional[object] = None,
    *,
    level: Optional[str] = None,
    log_file: Optional[Path] = None,
) -> None:
    """Configure the ``rsvp`` logger tree.

    Safe to call multiple times; subsequent calls are no-ops.

    Parameters
    ----------
    config:
        The ``Config`` object. When supplied we read ``log_level`` and
        ``log_file`` from it (if those attributes exist). Explicit
        ``level`` / ``log_file`` kwargs always override config values.
    level:
        Override log level (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
    log_file:
        Optional path to append a rotating file handler to.
    """
    global _telemetry_logger

    # Resolve effective level
    effective_level = _resolve_level(level, config)

    # Resolve effective file path
    effective_file = _resolve_file(log_file, config)

    # Configure root rsvp logger
    rsvp_root = logging.getLogger(_RSVP_ROOT)
    rsvp_root.setLevel(getattr(logging, effective_level, logging.INFO))

    # Remove any existing handlers (safe on re-init)
    for h in list(rsvp_root.handlers):
        rsvp_root.removeHandler(h)

    _install_handlers(rsvp_root, effective_file, effective_level)

    # Set up telemetry logger
    _telemetry_logger = logging.getLogger(f"{_RSVP_ROOT}.telemetry")
    _telemetry_logger.setLevel(logging.DEBUG)  # Always capture; filter at handler

    # Propagate to root so messages also appear on the console handler.
    rsvp_root.propagate = True

    # Log startup marker
    startup_log = logging.getLogger(f"{_RSVP_ROOT}.startup")
    startup_log.info(
        "rsvp logging initialised level=%s log_file=%s",
        effective_level,
        effective_file,
    )


def _t_emit(**kwargs: Any) -> None:
    """Emit a structured telemetry event on ``rsvp.telemetry``.

    If no handlers are configured for the telemetry logger this is a
    no-op, so it's safe to leave calls in production code.
    """
    if _telemetry_logger is None:
        return
    # The 'event' key is the primary discriminator.
    event_name = kwargs.pop("event", "unknown")
    # Pack remaining fields into a flat dict message.
    msg = "event=%s %s" % (
        event_name,
        " ".join(f"{k}={_fmt_value(v)!r}" for k, v in sorted(kwargs.items())),
    )
    _telemetry_logger.debug("%s", msg, extra={"_telemetry_event": event_name})


def telemetry_error(
    module: str,
    exc: BaseException,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    """Emit an error telemetry event with exception details."""
    _t_emit(
        event="error",
        module=module,
        exc_type=type(exc).__name__,
        exc_value=str(exc),
        tb=traceback.format_exc(),
        **(extra or {}),
    )


def shutdown_logging() -> None:
    """Flush and remove all handlers. Call at app shutdown."""
    rsvp_root = logging.getLogger(_RSVP_ROOT)
    for h in rsvp_root.handlers[:]:
        try:
            h.flush()
            h.close()
        except Exception:
            pass
        rsvp_root.removeHandler(h)
    global _telemetry_logger
    _telemetry_logger = None


# -------------------------------------------------------------------
# Internal helpers
# -------------------------------------------------------------------

def _resolve_level(level: Optional[str], config: Optional[object]) -> str:
    """Return the effective log level string."""
    if level:
        return level
    if config is not None:
        for attr in ("log_level", "LOG_LEVEL"):
            if hasattr(config, attr):
                val = getattr(config, attr)
                if val:
                    return str(val)
    return os.environ.get("RSVP_LOG_LEVEL", "INFO")


def _resolve_file(log_file: Optional[Path], config: Optional[object]) -> Optional[Path]:
    """Return the effective log file path."""
    if log_file is not None:
        return log_file
    if config is not None:
        for attr in ("log_file", "LOG_FILE"):
            if hasattr(config, attr):
                val = getattr(config, attr)
                if val:
                    return Path(val)
    env = os.environ.get("RSVP_LOG_FILE")
    if env:
        return Path(env)
    return None


def _install_handlers(
    rsvp_root: logging.Logger,
    log_file: Optional[Path],
    level: str,
) -> None:
    """Add console (+ optional file) handlers to the root logger."""
    fmt = "%(asctime)s %(levelname)-8s %(name)-30s %(message)s"
    datefmt = "%H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # Console handler
    console = logging.StreamHandler(sys.stderr)
    console.setLevel(getattr(logging, level, logging.INFO))
    console.setFormatter(formatter)
    rsvp_root.addHandler(console)

    # Optional file handler
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            log_file,
            mode="a",
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        # Verbose format for file — include thread/logger name.
        file_formatter = logging.Formatter(
            "%(asctime)s %(levelname)-8s %(threadName)-12s %(name)-30s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_formatter)
        rsvp_root.addHandler(file_handler)


def _fmt_value(v) -> str:
    """Coerce a value to a compact string for telemetry output."""
    if isinstance(v, Path):
        return str(v)
    if isinstance(v, (list, tuple)):
        return ",".join(str(x) for x in v)
    if isinstance(v, dict):
        return ",".join(f"{k}={_fmt_value(val)}" for k, val in v.items())
    return str(v)[:120]


# -------------------------------------------------------------------
# LoggingLogger wrapper (optional — use this in managers that need
# a logging.Logger with extra contextual fields injected).
# -------------------------------------------------------------------

class LoggingMixin:
    """Mix-in that adds a ``log`` attribute to any class.

    Subclasses must call ``self._init_logging(name)`` where ``name``
    is the ``__name__`` of the concrete class.

    Example::

        class MyService(LoggingMixin):
            def __init__(self):
                self._init_logging(__name__)
                self.log.info("service started")
    """

    log: logging.Logger

    def _init_logging(self, name: str, *, level: Optional[int] = None) -> None:
        self.log = logging.getLogger(name)
        if level is not None:
            self.log.setLevel(level)


# -------------------------------------------------------------------
# Telemetry events as a class with named methods (cleaner call sites)
# -------------------------------------------------------------------


class Telemetry:
    """Named telemetry events backed by the ``rsvp.telemetry`` logger.

    All methods are no-ops when no handlers are configured.
    """

    __slots__ = ()

    # ---- Book ------------------------------------------------------------

    def book_open(self, book_id: str, title: str, word_count: int) -> None:
        _t_emit(event="book.open", book_id=book_id, title=title, word_count=word_count)

    def book_close(self, book_id: str, final_index: int, total_words: int) -> None:
        _t_emit(
            event="book.close", book_id=book_id,
            final_index=final_index, total_words=total_words,
        )

    def book_import(self, book_id: str, title: str, file_type: str, word_count: int) -> None:
        _t_emit(
            event="book.import", book_id=book_id,
            title=title, file_type=file_type, word_count=word_count,
        )

    # ---- Figure ----------------------------------------------------------

    def figure_mount(self, figure_id: str, reason: str) -> None:
        _t_emit(event="figure.mount", figure_id=figure_id, reason=reason)

    def figure_swap(self, from_id: str, to_id: str) -> None:
        _t_emit(event="figure.swap", from_id=from_id, to_id=to_id)

    def reading_complete(self, figure_id: str, final_index: int, total_words: int) -> None:
        _t_emit(
            event="figure.complete",
            figure_id=figure_id,
            final_index=final_index,
            total_words=total_words,
        )

    # ---- Transport -------------------------------------------------------

    def transport_play(self, figure_id: str, wpm: int, word_index: int) -> None:
        _t_emit(event="transport.play", figure_id=figure_id, wpm=wpm, word_index=word_index)

    def transport_pause(self, figure_id: str, word_index: int) -> None:
        _t_emit(event="transport.pause", figure_id=figure_id, word_index=word_index)

    def transport_seek(self, figure_id: str, word_index: int, reason: str) -> None:
        _t_emit(event="transport.seek", figure_id=figure_id, word_index=word_index, reason=reason)

    # ---- Words / WPM -----------------------------------------------------

    def word_advance(self, figure_id: str, word: str, word_index: int, wpm: int) -> None:
        _t_emit(
            event="word.advance",
            figure_id=figure_id,
            word=word[:40],
            word_index=word_index,
            wpm=wpm,
        )

    def wpm_change(self, new_wpm: int, source: str) -> None:
        _t_emit(event="wpm.change", new_wpm=new_wpm, source=source)

    # ---- Notes -----------------------------------------------------------

    def note_created(self, book_id: str, note_id: str, word_index: int) -> None:
        _t_emit(event="note.create", book_id=book_id, note_id=note_id, word_index=word_index)

    def note_deleted(self, book_id: str, note_id: str) -> None:
        _t_emit(event="note.delete", book_id=book_id, note_id=note_id)

    # ---- Chapters --------------------------------------------------------

    def chapter_nav(
        self, book_id: str, from_chapter: int, to_chapter: int
    ) -> None:
        _t_emit(
            event="chapter.nav",
            book_id=book_id,
            from_chapter=from_chapter,
            to_chapter=to_chapter,
        )

    # ---- Config ---------------------------------------------------------

    def config_change(self, key: str, value: object) -> None:
        _t_emit(event="config.change", key=key, value=str(value)[:80])

    def config_load(self, schema_version: int, path: str) -> None:
        _t_emit(event="config.load", schema_version=schema_version, path=path)

    def config_save(self, schema_version: int) -> None:
        _t_emit(event="config.save", schema_version=schema_version)


# Singleton — must be named AFTER _t_emit is defined above
telemetry = Telemetry()


__all__ = [
    "init_logging",
    "shutdown_logging",
    "telemetry",
    "telemetry_error",
    "LoggingMixin",
]