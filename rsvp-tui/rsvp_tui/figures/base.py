"""Base class and state types for the RSVP figure system.

A *figure* is a Textual widget that visualizes the current word(s) of a
reading session in a specific way — single-word ORP, 3-word chunk,
full-line, bionic bolding, spritz pivot, pacer dots, mini-map, stats
overlay, etc. All figures share transport controls (play/pause/jump)
and reactive state (``word_index``, ``wpm``, ``is_playing``) so they
can be swapped at runtime without losing reading position.

Why a base class: prior to Phase 1, the app had a single widget
(``ReaderDisplay``) with two boolean flags to switch modes. A proper
class hierarchy lets us register, swap, and parameterize figures
uniformly. ``Figure`` extends ``textual.widgets.Static`` because every
figure is rendered as a Rich panel — no exceptions.

Design notes:

* ``FigureState`` is an immutable snapshot passed in at construction
  or via ``update_state``. This is what enables runtime swapping: the
  owning screen takes a snapshot, pauses the old figure, mounts a new
  one, and feeds it the same state.
* Each figure owns its own ``set_timer`` for word advancement (same
  pattern as the legacy ``ReaderDisplay``). Swapping always calls
  ``pause()`` first to cancel the timer, otherwise stale callbacks
  would advance the new figure's index.
* Subclasses override ``render()`` to produce the Rich renderable.
  Everything else (state, transport, navigation) is inherited.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from textual.reactive import reactive
from textual.widgets import Static

from .. import calculate_word_delay
from ..logging_ import telemetry

log = logging.getLogger(__name__)


def _notify_callback_error(figure: Figure, exc: BaseException, label: str) -> None:
    """Best-effort toast when a figure callback fails.

    Used by :meth:`Figure.watch_word_index` to surface a callback
    failure to the user instead of silently swallowing it. Skips
    gracefully if the figure is not yet mounted (the ``app``
    property raises ``NoActiveAppError`` outside of a running app,
    which we catch with a broad except).
    """
    try:
        app = figure.app
    except Exception:
        # NoActiveAppError or similar — not mounted yet.
        return
    if app is None:
        return
    notify = getattr(app, "notify", None)
    if notify is None:
        return
    try:
        notify(f"Figure {label} error: {exc}", severity="error")
    except Exception:
        # Never let a notification failure mask the original error.
        log.debug("notify() failed during figure callback error path", exc_info=True)


# ---- State ------------------------------------------------------------------


@dataclass(frozen=True)
class FigureState:
    """Immutable state passed into a figure to drive rendering.

    Frozen so the figure can rely on these values not mutating under
    its feet while a render is in flight. When the user changes a
    setting, the owning screen builds a new ``FigureState`` and calls
    ``update_state`` on the figure.
    """

    words: tuple[str, ...] = ()
    word_index: int = 0
    wpm: int = 300
    is_playing: bool = False
    punctuation_multiplier: float = 2.0
    pause_chars: tuple[str, ...] = (".", "!", "?", ";", ":")
    comma_pause_multiplier: float = 1.5
    on_word_change: Callable[[int], None] | None = None
    on_complete: Callable[[], None] | None = None


# ---- Base class -------------------------------------------------------------


class Figure(Static):
    """Base class for all RSVP figures.

    Subclasses must set the class attributes ``id``, ``name``,
    ``description``, ``default_keybinding``, ``default_params`` and
    override :meth:`render` to produce their unique visualization.

    Subclasses may also override :meth:`_on_init` for setup that
    needs the figure's reactive state to exist (e.g. creating child
    widgets).

    Note: we don't use ``abc.ABC`` because Textual's ``Static`` has
    its own metaclass and the two clash. Subclasses that forget to
    override :meth:`render` will get a clear ``NotImplementedError``
    at render time, which is the same contract ABC would have given.
    """

    # Subclass-overridable metadata
    id: str = ""
    name: str = ""
    description: str = ""
    default_keybinding: str = ""
    default_params: dict[str, Any] = {}

    # Reactive state — shared with the rest of the app via Textual
    # reactive semantics. ``word_index`` is the source of truth for
    # the current position; ``is_playing`` controls the timer.
    word_index: reactive[int] = reactive(0)
    is_playing: reactive[bool] = reactive(False)
    wpm: reactive[int] = reactive(300)

    def __init__(
        self,
        state: FigureState | None = None,
        params: dict[str, Any] | None = None,
        *,
        id: str | None = None,  # Textual widget id
    ) -> None:
        super().__init__(id=id)
        if state is None:
            state = FigureState()
        self._state = state
        self._words: tuple[str, ...] = state.words
        self._punctuation_multiplier: float = state.punctuation_multiplier
        self._pause_chars: tuple[str, ...] = state.pause_chars
        self._on_word_change: Callable[[int], None] | None = state.on_word_change
        self._on_complete: Callable[[], None] | None = state.on_complete

        # Merge defaults with caller-supplied params. Unknown keys
        # are silently dropped — keeps old configs from breaking new
        # figures.
        self._params: dict[str, Any] = dict(self.default_params)
        if params:
            for k, v in params.items():
                if k in self.default_params:
                    self._params[k] = v

        # Run subclass init BEFORE we set reactive attributes. Otherwise
        # the ``watch_word_index`` observer (e.g. StatsFigure's sparkline)
        # fires before ``_wpm_history`` exists.
        self._timer: Any = None
        self._on_init()

        self.wpm = state.wpm
        self.word_index = state.word_index
        self.is_playing = state.is_playing

    # ---- Subclass hooks ------------------------------------------------

    def _on_init(self) -> None:
        """Hook for subclasses to do extra setup (e.g. create children)."""
        pass

    def render(self):  # type: ignore[override]
        """Return a Rich renderable for the current state.

        Subclasses must implement. The base implementation raises
        ``NotImplementedError`` so a missing override fails loudly
        at render time rather than producing silent empty output.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must override render()"
        )

    # ---- Parameter & state updates -------------------------------------

    def apply_params(self, params: dict[str, Any]) -> None:
        """Update figure-specific parameters at runtime."""
        changed = False
        for k, v in params.items():
            if k in self.default_params and self._params.get(k) != v:
                self._params[k] = v
                changed = True
        if changed:
            self.refresh()

    def update_state(self, state: FigureState) -> None:
        """Replace the figure's state in-place.

        Used when swapping figures: the new figure is mounted with the
        same state the old one had, so position/speed/playback is
        preserved.
        """
        words_changed = state.words != self._words
        if words_changed and self.is_playing:
            self.pause()

        self._state = state
        self._words = state.words
        self._punctuation_multiplier = state.punctuation_multiplier
        self._pause_chars = state.pause_chars
        self._on_word_change = state.on_word_change
        self._on_complete = state.on_complete
        self.wpm = state.wpm
        self.word_index = state.word_index
        self.is_playing = state.is_playing
        self.refresh()

    # ---- Transport ------------------------------------------------------

    def start(self) -> None:
        if not self.is_playing and self._words:
            self.is_playing = True
            log.debug("Figure %s: started wpm=%d word_index=%d", self.id, self.wpm, self.word_index)
            self._schedule_next()

    def pause(self) -> None:
        self.is_playing = False
        log.debug("Figure %s: paused at word_index=%d", self.id, self.word_index)
        self._cancel_timer()

    def toggle(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.start()

    def stop(self) -> None:
        self.pause()
        log.info("Figure %s: stopped", self.id)
        self.word_index = 0

    # ---- Navigation -----------------------------------------------------

    def next_word(self) -> None:
        if self.word_index < len(self._words) - 1:
            prev = self.word_index
            self.word_index += 1
            telemetry.word_advance(figure_id=self.id, word=self._current_word(), word_index=self.word_index, wpm=self.wpm)
            log.debug("Figure %s: next_word %d -> %d", self.id, prev, self.word_index)

    def prev_word(self) -> None:
        if self.word_index > 0:
            prev = self.word_index
            self.word_index -= 1
            log.debug("Figure %s: prev_word %d -> %d", self.id, prev, self.word_index)

    def jump_to(self, index: int) -> None:
        if self._words:
            prev = self.word_index
            self.word_index = max(0, min(int(index), len(self._words) - 1))
            log.info("Figure %s: jump_to %d (was %d)", self.id, self.word_index, prev)

    def jump_to_percentage(self, percentage: float) -> None:
        if self._words:
            prev_pct = (self.word_index / len(self._words)) * 100
            index = int((percentage / 100.0) * len(self._words))
            self.jump_to(index)
            log.info("Figure %s: jump_to_percentage %.1f%% (was %.1f%%)", self.id, percentage, prev_pct)

    # ---- Speed ----------------------------------------------------------

    def set_wpm(self, wpm: int) -> None:
        # Clamp to a sane RSVP range. Zero or negative WPM would
        # produce an infinite delay in _schedule_next and freeze
        # the timer; the lower bound is 50 to leave room for
        # extremely slow reading practice.
        prev = self.wpm
        self.wpm = max(50, min(1500, int(wpm)))
        if prev != self.wpm:
            telemetry.wpm_change(new_wpm=self.wpm, source="figure")
            log.info("Figure %s: wpm changed %d -> %d", self.id, prev, self.wpm)

    def increase_speed(self, amount: int = 25) -> None:
        self.set_wpm(self.wpm + amount)

    def decrease_speed(self, amount: int = 25) -> None:
        self.set_wpm(self.wpm - amount)

    # ---- Reactive observers --------------------------------------------

    def watch_word_index(self, index: int) -> None:  # type: ignore[override]
        if self._on_word_change is not None:
            try:
                self._on_word_change(index)
            except Exception as exc:
                # Callback failures must not stop the figure from
                # advancing; log + toast via the screen's app.
                log.exception("Figure on_word_change failed: %s", exc)
                _notify_callback_error(self, exc, "on_word_change")
        if self._words and index >= len(self._words):
            self.is_playing = False
            log.info("Figure %s: reading complete at word_index=%d", self.id, index)
            telemetry.reading_complete(figure_id=self.id, final_index=index, total_words=len(self._words))
            if self._on_complete is not None:
                try:
                    self._on_complete()
                except Exception as exc:
                    log.exception("Figure on_complete failed: %s", exc)
                    _notify_callback_error(self, exc, "on_complete")

    # ---- Internal -------------------------------------------------------

    def _current_word(self) -> str:
        if 0 <= self.word_index < len(self._words):
            return self._words[self.word_index]
        return ""

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            try:
                self._timer.stop()
            except Exception:
                # Timer.stop() can raise if the timer was already
                # cancelled. The crucial invariant: we always clear
                # the reference so a later _schedule_next doesn't
                # see a stale pointer.
                log.debug("Figure timer stop() raised; ignoring", exc_info=True)
            finally:
                self._timer = None

    def _schedule_next(self) -> None:
        if not self.is_playing or not self._words:
            return
        current = self._current_word()
        if not current:
            return
        delay_ms = calculate_word_delay(
            current,
            self.wpm,
            self._punctuation_multiplier,
            list(self._pause_chars),
        )
        self._timer = self.set_timer(delay_ms / 1000, self._advance)

    def _advance(self) -> None:
        if not self.is_playing:
            return
        if self.word_index < len(self._words) - 1:
            self.word_index += 1
            self._schedule_next()
        else:
            self.is_playing = False

    # ---- Introspection --------------------------------------------------

    def get_param(self, key: str, default: Any = None) -> Any:
        return self._params.get(key, default)


__all__ = ["FigureState", "Figure"]
