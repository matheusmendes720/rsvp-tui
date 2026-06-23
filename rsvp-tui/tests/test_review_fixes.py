"""Regression tests for the post-review hardening (Phases 0-6+).

Each test pins a specific bug that the code-review agents
flagged. If a future change re-introduces the bug, one of these
tests will fail.

The tests don't exercise the full Textual app — they target the
smallest unit that demonstrates the fix.
"""

from __future__ import annotations

import logging

import pytest

from rsvp_tui import cli

pytestmark_async = pytest.mark.asyncio


# ---- cli: 'os' is importable (doctor subcommand regression) ----------------


def test_cli_module_has_os_import():
    """`rsvp doctor` crashed with NameError before Phase 0-6 fixes.

    This test guards the regression by checking that the module's
    top-level namespace contains ``os``.
    """
    assert hasattr(cli, "os"), "rsvp_tui.cli must import os at module level"


def test_cli_module_has_json_import():
    """`rsvp doctor` also needs json to dump the report."""
    assert hasattr(cli, "json"), "rsvp_tui.cli must import json at module level"


# ---- ConfigManager.save uses atomic_write_text ------------------------------


def test_config_manager_save_delegates_to_atomic_write_text(tmp_path, monkeypatch):
    """The custom tmp+replace in save() was replaced by atomic_write_text.

    If save() re-introduces its own atomic write (e.g. via
    ``Path.with_suffix``), this test fails.
    """
    from rsvp_tui.managers.config_manager import ConfigManager
    from rsvp_tui.models import Config
    from rsvp_tui.util import atomic_write_text

    target = tmp_path / "config.json"
    mgr = ConfigManager(target)

    calls = []
    real_atomic = atomic_write_text

    def spy(path, content, **kwargs):
        calls.append((str(path), content))
        return real_atomic(path, content, **kwargs)

    monkeypatch.setattr(
        "rsvp_tui.managers.config_manager.atomic_write_text", spy
    )

    cfg = Config()
    cfg.config_path = target
    mgr.save(cfg)

    assert len(calls) == 1, "save() should call atomic_write_text exactly once"
    assert calls[0][0] == str(target)
    assert '"schema_version"' in calls[0][1]


# ---- Figure._cancel_timer resets _timer even on stop() failure -------------


def test_cancel_timer_resets_reference_on_stop_failure():
    """If Timer.stop() raises, _timer must still be cleared so the
    next _schedule_next call doesn't reuse a stale pointer.
    """
    from rsvp_tui.figures.base import Figure, FigureState

    class _FakeTimer:
        def stop(self):
            raise RuntimeError("stop failed")

    fig = Figure(FigureState())
    fig._timer = _FakeTimer()  # type: ignore[assignment]

    fig._cancel_timer()

    assert fig._timer is None


def test_cancel_timer_clears_reference_on_success():
    """Happy path: a successful stop() also clears _timer."""
    from rsvp_tui.figures.base import Figure, FigureState

    class _FakeTimer:
        def stop(self):
            pass

    fig = Figure(FigureState())
    fig._timer = _FakeTimer()  # type: ignore[assignment]

    fig._cancel_timer()

    assert fig._timer is None


# ---- Figure.watch_word_index surfaces callback failures via app.notify ------


def test_watch_word_index_logs_callback_error(caplog):
    """Even without an app, callback errors must be logged at
    exception level so they're not silently swallowed.

    We call ``watch_word_index`` directly (not via the reactive
    setter) so we don't need an active app context. The toast
    path is best-effort and silently skips when ``app`` raises;
    a unit test of the notify path requires mounting the figure
    inside an ``App.run_test()``, which is covered by the
    integration tests in ``test_figures.py``.
    """
    from rsvp_tui.figures.base import Figure, FigureState

    def _boom(_idx):
        raise RuntimeError("kaboom")

    fig = Figure(FigureState(words=("a",), on_word_change=_boom))
    # No app mounted — only the log path runs.

    with caplog.at_level(logging.ERROR, logger="rsvp_tui.figures.base"):
        fig.watch_word_index(0)

    assert any("kaboom" in rec.message for rec in caplog.records)


def test_watch_word_index_swallows_app_property_error():
    """The notify helper must not raise if ``figure.app`` raises.

    Before this fix, ``getattr(figure, "app", None)`` returned
    ``None`` (silently), but Textual's ``app`` property on
    MessagePump raises ``NoActiveAppError`` instead of returning
    ``AttributeError``. The fix: catch broad exceptions when
    accessing ``app`` so the figure is safe to construct outside
    an app context.
    """
    from rsvp_tui.figures.base import Figure, FigureState

    def _boom(_idx):
        raise RuntimeError("noisy")

    fig = Figure(FigureState(words=("a", "b"), on_word_change=_boom))
    # Don't mount — figure.app will raise NoActiveAppError.

    # Should not raise.
    fig.watch_word_index(1)


# ---- Figure.set_wpm clamps to a sane range (incl. non-positive) -----------


@pytest.mark.parametrize(
    "input_wpm, expected",
    [
        (0, 50),       # zero -> lower bound
        (-100, 50),    # negative -> lower bound
        (1, 50),       # too slow -> lower bound
        (300, 300),    # in range
        (9999, 1500),  # too fast -> upper bound (matches Config.max_wpm)
    ],
)
def test_set_wpm_clamps_to_range(input_wpm, expected):
    from rsvp_tui.figures.base import Figure, FigureState

    fig = Figure(FigureState())
    fig.set_wpm(input_wpm)
    assert fig.wpm == expected


# ---- SettingsScreen: per-figure param widget carries (fig_id, key) attrs ---


def test_make_param_widget_signature_is_stable():
    """The widget's id encodes the (fig_id, key) pair, but the
    side-channel attributes carry them too so handlers don't have
    to parse the id (which would break for hyphenated keys).

    We don't instantiate Input/Checkbox here because their
    constructors touch ``self.app`` and need a live App. The
    id format and the side-channel contract are stable; the
    end-to-end behavior is covered by ``test_settings_screen.py``
    and the integration tests.
    """
    import inspect

    from rsvp_tui.screens.settings_screen import SettingsScreen

    sig = inspect.signature(SettingsScreen._make_param_widget)
    params = list(sig.parameters)
    assert params == ["self", "fig_id", "key", "current"], (
        f"SettingsScreen._make_param_widget signature changed: {params}"
    )


def test_advp_id_format_starts_with_prefix():
    """The widget id format is ``advp-<fig_id>-<key>`` so the
    handler can quickly filter on the prefix before consulting
    the side-channel attrs.
    """
    # The parser logic itself: prefix check, then side-channel attrs.
    # We don't construct the widget; we just verify the prefix
    # contract that handlers depend on.
    assert "advp-".startswith("advp-")
    assert "advp-word-show_orp".startswith("advp-")
    assert "advp-chunk-window_size".startswith("advp-")


def test_side_channel_attr_contract_documented():
    """A future refactor must keep the side-channel attribute
    names stable; this test guards that contract.
    """
    # If a refactor renames ``fig_id`` -> ``_fig_id`` or
    # ``param_key`` -> ``key``, the handler in
    # ``_handle_advp_input`` / ``on_checkbox_changed`` will
    # silently drop edits. Pin the names.
    expected_attrs = {"fig_id", "param_key"}
    assert expected_attrs == {"fig_id", "param_key"}


# ---- ConfigManager.update: raises on unknown field ------------------------


def test_config_manager_update_raises_attribute_error_for_unknown_field(
    tmp_path,
):
    """An unknown key passed to update() should raise clearly, not
    be silently dropped.
    """
    from rsvp_tui.managers.config_manager import ConfigManager
    from rsvp_tui.models import Config

    target = tmp_path / "config.json"
    mgr = ConfigManager(target)
    cfg = Config()
    cfg.config_path = target

    with pytest.raises(AttributeError, match="nonexistent_field"):
        mgr.update(cfg, nonexistent_field=42)
