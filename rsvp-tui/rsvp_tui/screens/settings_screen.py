"""SettingsScreen — modal screen with live preview.

Replaces the legacy ``SettingsPanel`` widget. Differences from the
old design:

* It's a real ``ModalScreen`` — pushes on top of the current
  screen, dims the rest of the app, and dismisses on Escape.
* Every change is **debounced and live**: as you type, the value
  flows through to ``Config`` and into the active figure
  immediately. No "Save" button to forget; no `except ValueError:
  pass` swallowing invalid input.
* Validation is built in: ``textual.validation.Number`` rejects
  out-of-range values and we surface the error in a small red
  label beneath the input.
* Per-figure params (Tab 5) are exposed as a ``Select`` + dynamic
  form so adding a new figure with new params requires no settings
  code change — we just introspect ``default_params()``.

Returns ``None`` on dismiss (Esc); the screen is auto-saving so
there's no separate save return value.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.timer import Timer
from textual.validation import Number
from textual.widgets import (
    Button,
    Checkbox,
    Input,
    Label,
    Select,
    Static,
    TabbedContent,
    TabPane,
)

from ..figures import default_registry
from ..managers.config_manager import ConfigManager
from ..models import Config
from ..themes import all_themes
from .messages import ConfigChanged


# ---- Field helpers ---------------------------------------------------------


def _int_field(attr: str, label: str, lo: int, hi: int) -> Dict[str, Any]:
    return {"attr": attr, "label": label, "type": "int", "lo": lo, "hi": hi}


def _float_field(attr: str, label: str, lo: float, hi: float) -> Dict[str, Any]:
    return {"attr": attr, "label": label, "type": "float", "lo": lo, "hi": hi}


def _bool_field(attr: str, label: str) -> Dict[str, Any]:
    return {"attr": attr, "label": label, "type": "bool"}


def _choice_field(
    attr: str, label: str, choices: List[Tuple[str, str]]
) -> Dict[str, Any]:
    """``choices`` is a list of ``(value, label)`` tuples."""
    return {"attr": attr, "label": label, "type": "choice", "choices": choices}


# Tab 1 — Reading.
READING_FIELDS: List[Dict[str, Any]] = [
    _int_field("default_wpm", "Default WPM", 100, 1000),
    _int_field("min_wpm", "Min WPM", 50, 1000),
    _int_field("max_wpm", "Max WPM", 100, 1500),
    _int_field("wpm_step", "WPM Step", 5, 100),
]

# Tab 2 — Display & Theme.
DISPLAY_FIELDS: List[Dict[str, Any]] = [
    _bool_field("enable_orp", "Enable ORP Highlighting"),
    _bool_field("focus_mode", "Start in Focus Mode"),
    _bool_field("show_progress_bar", "Show Progress Bar"),
    _bool_field("show_context_words", "Show Context Words"),
    _choice_field(
        "theme", "Theme", [(t, t) for t in all_themes()]
    ),
    _choice_field(
        "figure_id",
        "Default Figure",
        [(f.id, f.name) for f in default_registry().all()],
    ),
]

# Tab 3 — Timing.
TIMING_FIELDS: List[Dict[str, Any]] = [
    _float_field("punctuation_multiplier", "Punctuation Multiplier", 1.0, 5.0),
    _bool_field("pause_on_punctuation", "Pause on Punctuation"),
    _float_field("comma_pause_multiplier", "Comma Multiplier", 1.0, 3.0),
]


# ---- Confirm modal --------------------------------------------------------


class _ConfirmModal(ModalScreen[bool]):
    """A small yes/no modal for the reset action."""

    DEFAULT_CSS = """
    _ConfirmModal {
        align: center middle;
    }
    _ConfirmModal > Vertical {
        width: 50;
        height: auto;
        border: solid $warning;
        background: $surface;
        padding: 1 2;
    }
    _ConfirmModal Horizontal {
        height: auto;
        margin-top: 1;
    }
    _ConfirmModal Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_no", "Cancel"),
    ]

    def __init__(self, prompt: str = "Are you sure?") -> None:
        super().__init__()
        self._prompt = prompt

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._prompt, id="confirm-prompt")
            with Horizontal():
                yield Button("Yes", id="yes-btn", variant="warning")
                yield Button("No", id="no-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "yes-btn":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_dismiss_no(self) -> None:
        self.dismiss(False)


# ---- Main settings screen -------------------------------------------------


class SettingsScreen(ModalScreen[None]):
    """Live-preview settings modal.

    The screen auto-saves every change to ``Config`` (and to disk
    via ``ConfigManager.update``) with a 200ms debounce. There is
    no separate "Save" button. Escape dismisses; the screen
    returns ``None`` and emits a final ``ConfigChanged`` so any
    active figure picks up the latest params.
    """

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }
    SettingsScreen > Vertical {
        width: 90%;
        height: 90%;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    SettingsScreen Label.field-label {
        margin-top: 1;
    }
    SettingsScreen Input {
        width: 100%;
    }
    SettingsScreen .field-row {
        height: auto;
    }
    SettingsScreen .field-error {
        color: $error;
        height: 1;
    }
    SettingsScreen #status-line {
        dock: bottom;
        height: 1;
        padding: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "dismiss_settings", "Close"),
        Binding("ctrl+r", "reset_defaults", "Reset"),
    ]

    DEBOUNCE_MS = 200

    def __init__(self, config: Optional[Config] = None) -> None:
        super().__init__()
        self._config = config or Config.load()
        self._manager = ConfigManager()
        self._debounce_timer: Optional[Timer] = None
        # Track which fields are currently invalid so we don't
        # apply them. Maps attr -> error message.
        self._errors: Dict[str, str] = {}
        # Snapshot for the per-figure params tab.
        self._figure_params: Dict[str, Dict[str, Any]] = dict(
            self._config.figure_params or {}
        )

    # ---- Compose --------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Settings", id="settings-title")
            with TabbedContent(initial="tab-reading"):
                with TabPane("Reading", id="tab-reading"):
                    yield VerticalScroll(
                        *self._build_fields(READING_FIELDS)
                    )
                with TabPane("Display & Theme", id="tab-display"):
                    yield VerticalScroll(
                        *self._build_fields(DISPLAY_FIELDS)
                    )
                with TabPane("Timing", id="tab-timing"):
                    yield VerticalScroll(
                        *self._build_fields(TIMING_FIELDS)
                    )
                with TabPane("Input", id="tab-input"):
                    yield Static(
                        "Key remapping is not yet exposed in the UI.\n"
                        "Edit ~/.rsvp/config.json directly or use\n"
                        "the command palette (Ctrl+P) for common actions.",
                        id="input-help",
                    )
                with TabPane("Advanced", id="tab-advanced"):
                    yield self._build_figure_params_tab()
            yield Static("", id="status-line")

    def _build_fields(self, fields: List[Dict[str, Any]]) -> List[Any]:
        """Build a list of widgets for a flat field list.

        Yields ``(Label, Input/Checkbox/Select, Static(error))``
        rows for each field. The ``Static(error)`` is empty by
        default; it appears when the user enters an invalid value.
        """
        widgets: List[Any] = []
        for f in fields:
            attr = f["attr"]
            label = f["label"]
            current = getattr(self._config, attr)
            widgets.append(Label(label, classes="field-label"))
            if f["type"] == "bool":
                widgets.append(
                    Checkbox(label, value=bool(current), id=f"fld-{attr}")
                )
            elif f["type"] == "choice":
                widgets.append(
                    Select(
                        options=f["choices"],
                        value=current,
                        id=f"fld-{attr}",
                        allow_blank=False,
                    )
                )
            else:
                lo, hi = f["lo"], f["hi"]
                placeholder = str(current)
                validator = Number(minimum=lo, maximum=hi)
                widgets.append(
                    Input(
                        value=placeholder,
                        id=f"fld-{attr}",
                        validators=[validator],
                        type="integer" if f["type"] == "int" else "number",
                    )
                )
                widgets.append(Static("", id=f"err-{attr}", classes="field-error"))
        return widgets

    def _build_figure_params_tab(self) -> ComposeResult:
        """Build the per-figure params tab (Advanced)."""
        with VerticalScroll():
            yield Label(
                "Per-figure parameters are stored under\n"
                "config.figure_params[figure_id]. Changes here apply\n"
                "the next time the figure is mounted.",
                id="advanced-help",
            )
            yield Label("Figure:", classes="field-label")
            yield Select(
                options=[(f.id, f.name) for f in default_registry().all()],
                value=default_registry().all()[0].id,
                id="adv-figure",
                allow_blank=False,
            )
            yield Vertical(id="adv-params")
            yield Static(
                "Tip: use Ctrl+R in this screen to reset all settings to defaults.",
                id="advanced-tip",
            )

    # ---- Lifecycle ------------------------------------------------------

    def on_mount(self) -> None:
        """Render the initial params form for the first figure."""
        self._refresh_figure_params_form()
        self._set_status("Edit a value to see live preview.")

    # ---- Debounced apply ------------------------------------------------

    def _schedule_apply(self) -> None:
        """Debounce: re-apply 200ms after the last edit.

        Why debounce: every keystroke would otherwise rewrite
        ``config.json``. 200ms is the budget in the plan — fast
        enough to feel live, slow enough to batch rapid typing.
        """
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        self._debounce_timer = self.set_timer(
            self.DEBOUNCE_MS / 1000.0, self._apply_now
        )

    def _apply_now(self) -> None:
        """Flush all current form values to ``Config`` and emit."""
        self._debounce_timer = None
        patch: Dict[str, Any] = {}

        # Read all simple fields.
        for fld_list in (READING_FIELDS, DISPLAY_FIELDS, TIMING_FIELDS):
            for f in fld_list:
                attr = f["attr"]
                wid = f"fld-{attr}"
                if attr in self._errors:
                    # Don't apply fields with active errors.
                    continue
                try:
                    widget = self.query_one(f"#{wid}")
                except Exception:
                    continue
                if f["type"] == "bool":
                    patch[attr] = bool(widget.value)
                elif f["type"] == "choice":
                    val = widget.value
                    if val is not None and val != Select.BLANK:
                        patch[attr] = val
                elif f["type"] == "int":
                    try:
                        patch[attr] = int(widget.value)
                    except (TypeError, ValueError):
                        continue
                else:
                    try:
                        patch[attr] = float(widget.value)
                    except (TypeError, ValueError):
                        continue

        # Persist + update in-memory config.
        if patch:
            try:
                self._manager.update(**patch)
            except Exception as exc:
                self._set_status(f"Save failed: {exc}", error=True)
                return
            for k, v in patch.items():
                setattr(self._config, k, v)

        # Figure params tab.
        self._config.figure_params = dict(self._figure_params)
        try:
            self._manager.update(figure_params=self._config.figure_params)
        except Exception as exc:
            self._set_status(f"Save failed: {exc}", error=True)
            return

        # Tell the rest of the app.
        self.post_message(ConfigChanged(keys=tuple(patch.keys())))
        self._set_status("Saved")

    # ---- Input handlers -------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        """Validate on every keystroke; debounce apply."""
        wid = event.input.id or ""
        if wid.startswith("fld-"):
            attr = wid[len("fld-"):]
            result = event.input.validation_result
            if result is not None and not result.is_valid:
                errors = result.failure_descriptions
                msg = "; ".join(errors) if errors else "Invalid"
                self._set_field_error(attr, msg)
            else:
                self._clear_field_error(attr)
            self._schedule_apply()
            return
        if wid.startswith("advp-"):
            self._handle_advp_input(event)
            return

    def _handle_advp_input(self, event: Input.Changed) -> None:
        """Capture edits to the figure-params form.

        Uses ``event.input.fig_id`` and ``event.input.param_key``
        (set by :meth:`_make_param_widget`) so hyphenated keys
        parse correctly. The widget id is only used for the
        ``advp-`` namespace prefix check.
        """
        fig_id = getattr(event.input, "fig_id", None)
        key = getattr(event.input, "param_key", None)
        if not fig_id or not key:
            return
        try:
            self._figure_params.setdefault(fig_id, {})[key] = int(
                event.input.value
            )
        except ValueError:
            try:
                self._figure_params.setdefault(fig_id, {})[key] = float(
                    event.input.value
                )
            except ValueError:
                self._figure_params.setdefault(fig_id, {})[key] = event.input.value
        self._schedule_apply()

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Apply on checkbox change."""
        wid = event.checkbox.id or ""
        if wid.startswith("fld-"):
            attr = wid[len("fld-"):]
            self._clear_field_error(attr)
            self._schedule_apply()
            return
        if wid.startswith("advp-"):
            fig_id = getattr(event.checkbox, "fig_id", None)
            key = getattr(event.checkbox, "param_key", None)
            if not fig_id or not key:
                return
            self._figure_params.setdefault(fig_id, {})[key] = bool(
                event.checkbox.value
            )
            self._schedule_apply()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Apply on choice change; switch figure on the advanced tab."""
        wid = event.select.id or ""
        if wid.startswith("fld-"):
            attr = wid[len("fld-"):]
            self._clear_field_error(attr)
            self._schedule_apply()
        elif wid == "adv-figure":
            self._refresh_figure_params_form()

    # ---- Field error rendering -----------------------------------------

    def _set_field_error(self, attr: str, msg: str) -> None:
        self._errors[attr] = msg
        try:
            err = self.query_one(f"#err-{attr}")
            err.update(msg)
        except Exception:
            pass

    def _clear_field_error(self, attr: str) -> None:
        self._errors.pop(attr, None)
        try:
            err = self.query_one(f"#err-{attr}")
            err.update("")
        except Exception:
            pass

    def _set_status(self, msg: str, error: bool = False) -> None:
        try:
            status = self.query_one("#status-line", Static)
        except Exception:
            return
        if error:
            status.update(f"[red]{msg}[/red]")
        else:
            status.update(f"[dim]{msg}[/dim]")

    # ---- Per-figure params tab -----------------------------------------

    def _refresh_figure_params_form(self) -> None:
        """Render the per-figure params form for the selected figure.

        We read ``self._figure_params[fig_id]`` (or the figure's
        ``default_params``) and compose a dynamic form of Input /
        Checkbox widgets. Each edit schedules a debounced apply
        that writes back into ``self._figure_params[fig_id]``.
        """
        try:
            sel = self.query_one("#adv-figure", Select)
            fig_id = sel.value
        except Exception:
            return
        if fig_id is None or fig_id == Select.BLANK:
            return
        registry = default_registry()
        fig = registry.get(fig_id)
        if fig is None:
            return

        container = self.query_one("#adv-params", Vertical)
        container.remove_children()

        current = dict(fig.default_params)
        current.update(self._figure_params.get(fig_id, {}))

        if not current:
            container.mount(
                Static(f"Figure '{fig.name}' has no tunable parameters.")
            )
            return

        container.mount(Label(f"Parameters for {fig.name}:"))

        for key, default_val in current.items():
            label = Label(key, classes="field-label")
            container.mount(label)
            widget = self._make_param_widget(fig_id, key, default_val)
            container.mount(widget)

    def _make_param_widget(self, fig_id: str, key: str, current: Any) -> Any:
        """Build the right input widget for a param's runtime type.

        Stamps ``fig_id`` and ``param_key`` onto the widget as
        attributes so the change handlers can look them up
        directly. This avoids parsing the widget id (which would
        break for keys that contain ``-``).
        """
        wid = f"advp-{fig_id}-{key}"
        if isinstance(current, bool):
            widget = Checkbox(key, value=current, id=wid)
        elif isinstance(current, int):
            widget = Input(value=str(current), id=wid, type="integer")
        elif isinstance(current, float):
            widget = Input(value=str(current), id=wid, type="number")
        else:
            widget = Input(value=str(current), id=wid)
        # Side-channel attrs so handlers can look up (fig_id, key)
        # without parsing the id.
        widget.fig_id = fig_id
        widget.param_key = key
        return widget

    # ---- Actions --------------------------------------------------------

    def action_dismiss_settings(self) -> None:
        """Escape: flush pending changes, then dismiss."""
        if self._debounce_timer is not None:
            self._debounce_timer.stop()
        self._apply_now()
        self.dismiss(None)

    def action_reset_defaults(self) -> None:
        """Ctrl+R: confirm then reset to defaults."""
        self.app.push_screen(
            _ConfirmModal("Reset all settings to defaults?"),
            self._on_reset_confirmed,
        )

    def _on_reset_confirmed(self, confirmed: bool) -> None:
        """Apply the reset if the user confirmed."""
        if not confirmed:
            return
        self._manager.reset()
        self._config = Config.load()
        self._figure_params = dict(self._config.figure_params or {})
        self._rebuild_form()
        self.post_message(ConfigChanged(keys=("reset",)))
        self._set_status("Reset to defaults")

    def _rebuild_form(self) -> None:
        """Re-populate every field with the latest config values."""
        for fld_list in (READING_FIELDS, DISPLAY_FIELDS, TIMING_FIELDS):
            for f in fld_list:
                attr = f["attr"]
                wid = f"fld-{attr}"
                try:
                    widget = self.query_one(f"#{wid}")
                except Exception:
                    continue
                current = getattr(self._config, attr)
                if f["type"] == "bool":
                    widget.value = bool(current)
                elif f["type"] == "choice":
                    if current is not None:
                        widget.value = current
                else:
                    widget.value = str(current)
        self._refresh_figure_params_form()


__all__ = ["SettingsScreen", "_ConfirmModal"]
