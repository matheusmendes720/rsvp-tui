"""Tests for the SettingsScreen (Phase 3).

The screen is a ``ModalScreen``; we don't need a full Textual app
to test its contracts. We focus on:

* Field-list declarations are non-empty and well-formed.
* Default values come from the current ``Config``.
* The shim ``rsvp_tui.widgets.settings_panel.SettingsPanel``
  resolves to the new class.
* ``ConfigChanged`` is the message the screen emits on flush.
* The legacy ``widgets.settings_panel`` import still works
  (deprecation warning is expected).
"""

from __future__ import annotations

import warnings

from rsvp_tui.models import Config
from rsvp_tui.screens import SettingsScreen
from rsvp_tui.screens.messages import ConfigChanged
from rsvp_tui.screens.settings_screen import (
    DISPLAY_FIELDS,
    READING_FIELDS,
    TIMING_FIELDS,
    _ConfirmModal,
)

# ---- Field-list shape ----------------------------------------------------


def test_reading_fields_nonempty():
    """The Reading tab has at least the WPM controls."""
    assert len(READING_FIELDS) >= 1
    attrs = {f["attr"] for f in READING_FIELDS}
    assert "default_wpm" in attrs


def test_display_fields_have_theme_and_figure():
    """The Display tab exposes theme + figure choice."""
    attrs = {f["attr"] for f in DISPLAY_FIELDS}
    assert "theme" in attrs
    assert "figure_id" in attrs


def test_timing_fields_have_punctuation_multiplier():
    """The Timing tab exposes the punctuation multiplier."""
    attrs = {f["attr"] for f in TIMING_FIELDS}
    assert "punctuation_multiplier" in attrs


def test_all_field_attrs_are_real_config_attrs():
    """Every field references a real ``Config`` attribute.

    Catches typos like ``punctutation_multiplier`` (a real bug
    that's easy to miss without a test).
    """
    cfg = Config()
    for fld_list in (READING_FIELDS, DISPLAY_FIELDS, TIMING_FIELDS):
        for f in fld_list:
            assert hasattr(cfg, f["attr"]), f"unknown Config attr: {f['attr']!r}"


def test_all_field_labels_nonempty():
    """Every field has a non-empty label."""
    for fld_list in (READING_FIELDS, DISPLAY_FIELDS, TIMING_FIELDS):
        for f in fld_list:
            assert f["label"].strip(), f"empty label for {f['attr']}"


def test_int_fields_have_bounds():
    """Integer/float fields have a ``lo`` <= ``hi`` range."""
    for fld_list in (READING_FIELDS, DISPLAY_FIELDS, TIMING_FIELDS):
        for f in fld_list:
            if f["type"] in ("int", "float"):
                assert f["lo"] <= f["hi"], f"bad bounds on {f['attr']}: {f['lo']} > {f['hi']}"


def test_choice_fields_have_choices():
    """Choice fields have at least one option."""
    for fld_list in (READING_FIELDS, DISPLAY_FIELDS, TIMING_FIELDS):
        for f in fld_list:
            if f["type"] == "choice":
                assert len(f["choices"]) >= 1, f"empty choices for {f['attr']}"
                for value, label in f["choices"]:
                    assert value and label


def test_figure_id_choice_matches_registry():
    """The default-figure choice is in sync with the registry."""
    choice = next(f for f in DISPLAY_FIELDS if f["attr"] == "figure_id")
    from rsvp_tui.figures import default_registry

    registry_ids = {f.id for f in default_registry().all()}
    choice_ids = {v for v, _ in choice["choices"]}
    assert registry_ids == choice_ids


def test_theme_choice_matches_themes():
    """The theme choice is in sync with the themes module."""
    choice = next(f for f in DISPLAY_FIELDS if f["attr"] == "theme")
    from rsvp_tui.themes import all_themes

    theme_ids = set(all_themes())
    choice_ids = {v for v, _ in choice["choices"]}
    assert theme_ids == choice_ids


# ---- SettingsScreen direct construction ----------------------------------


def test_settings_screen_default_config_loads():
    """Constructing without an explicit config loads defaults."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        screen = SettingsScreen()
    assert screen._config is not None
    assert screen._config.default_wpm >= screen._config.min_wpm


def test_settings_screen_accepts_explicit_config():
    """An explicit config is honored (not overwritten)."""
    cfg = Config()
    cfg.default_wpm = 425
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        screen = SettingsScreen(config=cfg)
    assert screen._config.default_wpm == 425


def test_settings_screen_starts_with_no_errors():
    """No fields are in error on a fresh screen."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        screen = SettingsScreen()
    assert screen._errors == {}


def test_settings_screen_debounce_timer_initially_none():
    """The debounce timer hasn't fired yet at construction."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        screen = SettingsScreen()
    assert screen._debounce_timer is None


def test_settings_screen_figure_params_default_to_config():
    """The figure-params snapshot is built from the config."""
    cfg = Config()
    cfg.figure_params = {"word": {"orp_enabled": False}}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        screen = SettingsScreen(config=cfg)
    assert screen._figure_params == {"word": {"orp_enabled": False}}


# ---- Confirm modal -------------------------------------------------------


def test_confirm_modal_default_prompt():
    """The confirm modal has a default prompt."""
    m = _ConfirmModal()
    assert m._prompt


def test_confirm_modal_custom_prompt():
    """A custom prompt is honored."""
    m = _ConfirmModal("Really delete?")
    assert m._prompt == "Really delete?"


# ---- Legacy shim ---------------------------------------------------------


def test_legacy_settings_panel_shim_warns():
    """Importing the legacy path emits a DeprecationWarning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        from rsvp_tui.widgets import settings_panel  # noqa: F401

        # We imported the module; now access the symbol to fire
        # the PEP 562 shim.
        _ = settings_panel.SettingsPanel
    assert any(
        issubclass(w.category, DeprecationWarning) for w in caught
    ), "expected a DeprecationWarning when accessing SettingsPanel"


def test_legacy_settings_panel_resolves_to_new_class():
    """The shim returns the new SettingsScreen."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from rsvp_tui.widgets.settings_panel import SettingsPanel

    assert SettingsPanel is SettingsScreen


# ---- ConfigChanged message shape -----------------------------------------


def test_config_changed_message_default_empty_keys():
    """Default keys is an empty tuple (no edits)."""
    m = ConfigChanged()
    assert m.keys == ()


def test_config_changed_message_carries_keys():
    """``keys`` is the names of the changed config attrs."""
    m = ConfigChanged(keys=("default_wpm", "theme"))
    assert m.keys == ("default_wpm", "theme")
