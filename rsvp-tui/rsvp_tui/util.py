"""Small utilities used across the package.

Right now this module is just one thing: ``safe_callback``, a
decorator that swallows exceptions in event handlers and routes
them to the app's ``notify`` instead of letting them crash the
TUI. A misbehaving ``on_input_changed`` shouldn't take the whole
app down; it should log, surface a toast, and let the user keep
going.

Why a decorator and not a context manager: Textual calls
``on_*`` methods by name, so we can't wrap them in ``with``. A
decorator that wraps the bound method is the only way to add
error handling without changing every call site.
"""

from __future__ import annotations

import contextlib
import functools
import logging
import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

log = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def safe_callback(default: Any = None, *, log_traceback: bool = True) -> Callable[[F], F]:
    """Decorator: run a callback, swallow exceptions, return ``default``.

    On exception we:

    1. Log the traceback (if ``log_traceback`` is True — the
       default).
    2. Try to surface a toast via ``self.app.notify(...)`` if
       the wrapped function's first positional arg is ``self``
       and that ``self`` has an ``app`` attribute.
    3. Return ``default`` so the caller can keep going.

    This is intentionally simple. The TUI is the kind of program
    where a stray ``KeyError`` in an event handler should not
    brick the whole app — the user just sees a toast and moves on.
    """

    def deco(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(self: object, *args: Any, **kwargs: Any) -> Any:
            try:
                return fn(self, *args, **kwargs)
            except Exception as exc:
                if log_traceback:
                    log.exception(
                        "safe_callback swallowed exception in %s: %s",
                        getattr(fn, "__qualname__", fn),
                        exc,
                    )
                else:
                    log.warning(
                        "safe_callback swallowed exception in %s: %s",
                        getattr(fn, "__qualname__", fn),
                        exc,
                    )
                # Best-effort toast; if the screen isn't mounted
                # yet (e.g. during compose), ``app`` may be None.
                app = getattr(self, "app", None)
                if app is not None and hasattr(app, "notify"):
                    with contextlib.suppress(Exception):
                        app.notify(
                            f"Something went wrong: {exc}",
                            severity="error",
                        )
                return default

        return wrapper  # type: ignore[return-value]

    return deco


def atomic_write_text(path: Path | str, content: str, *, encoding: str = "utf-8") -> None:
    """Write ``content`` to ``path`` atomically (tmp + replace).

    Centralized so every file write in the package uses the same
    pattern. ``ConfigManager.save`` was the first to use this
    pattern in Phase 0; this helper exists so other writers
    (``note_manager``, ``library_manager`` cache) can share it.

    Returns ``None`` on success. Raises on failure (the tmp file
    may be left behind, but the real file is never partial).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(content)
            f.flush()
            with contextlib.suppress(OSError):
                # Some filesystems (e.g. Windows network shares)
                # don't support fsync. The atomic replace still
                # gives us crash-safety; just lose the durability
                # guarantee on those filesystems.
                os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        # Clean up the tmp file on failure.
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


__all__ = ["safe_callback", "atomic_write_text"]
