"""Atomic, versioned, schema-migrating config loader for the RSVP TUI.

Why this exists: the legacy ``Config.save`` did a direct ``open(...).write``
which could leave a half-written file if the process died mid-write.
``Config.load`` also silently swallowed ``JSONDecodeError`` and returned a
default config — that meant a corrupted settings file wiped the user's
customizations without warning. The new flow is:

* ``load()`` reads the JSON, validates ``schema_version``, runs any
  necessary migrations, then returns a populated ``Config``.
* ``save()`` writes to ``config.json.tmp`` and atomically renames over
  the real file, so a crash never leaves a partial config on disk.
* ``update(**patch)`` mutates a single field and re-saves.
* ``reset()`` returns a fresh default and writes it.

Backward compatibility: ``Config.load()`` is preserved as a thin shim
that delegates here, so all existing callers (``LibraryManager``,
``NoteManager``) keep working unchanged.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..models import Config
from ..util import atomic_write_text

log = logging.getLogger(__name__)

# Bump CURRENT_SCHEMA when adding new fields. Add a migration entry in
# MIGRATIONS for every old version that should still be readable.
CURRENT_SCHEMA: int = 3


# ---- Migrations -------------------------------------------------------------


def _migrate_1_to_2(data: dict[str, Any]) -> dict[str, Any]:
    """v1 -> v2: add theme, figure_id, figure_params, keybindings.

    The v1 schema only had reading/timing/display fields. v2 adds a
    theme identifier, the active figure id, per-figure parameter
    overrides, and user keybinding overrides. We do *not* drop v1
    fields; we just add the new ones with sensible defaults and
    bump the schema marker.
    """
    data = dict(data)  # don't mutate the caller's dict
    data.setdefault("schema_version", 2)
    data.setdefault("theme", "dark")
    data.setdefault("figure_id", "word")
    data.setdefault("figure_params", {})
    data.setdefault("keybindings", {})
    return data


def _migrate_2_to_3(data: dict[str, Any]) -> dict[str, Any]:
    """v2 -> v3: add navigation panel settings.

    v3 adds page_size for pagination and visibility flags for
    the navigation panel and note panel.
    """
    data = dict(data)  # don't mutate the caller's dict
    data["schema_version"] = 3
    data.setdefault("page_size", 500)
    data.setdefault("show_navigation_panel", True)
    data.setdefault("show_note_panel", True)
    return data


# Map of old version -> migration function. Keys are the *old* version.
MIGRATIONS: dict[int, Any] = {
    1: _migrate_1_to_2,
    2: _migrate_2_to_3,
}


# ---- Manager ----------------------------------------------------------------


class ConfigManager:
    """Load, save, migrate, and mutate the user's config file.

    The manager is intentionally stateful: it owns the path and the
    in-memory copy. ``Config`` is treated as a value object the manager
    hands out and re-reads.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        if config_path is None:
            config_path = Path.home() / ".rsvp" / "config.json"
        self.path: Path = config_path

    # ---- Loading --------------------------------------------------------

    def load(self) -> Config:
        """Load and migrate the config, creating a default if none exists."""
        if not self.path.exists():
            cfg = Config()
            cfg.config_path = self.path
            self.save(cfg)
            return cfg

        try:
            raw = self.path.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("config unreadable (%s); falling back to defaults", exc)
            return self._default_with_path()

        data = self._migrate(data)
        return self._build_config(data)

    def _migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Run any necessary migrations so ``data`` matches CURRENT_SCHEMA."""
        version = int(data.get("schema_version", 1))
        while version < CURRENT_SCHEMA:
            migrator = MIGRATIONS.get(version)
            if migrator is None:
                log.warning(
                    "no migration from schema v%s to v%s; using defaults",
                    version,
                    CURRENT_SCHEMA,
                )
                return self._default_payload()
            data = migrator(data)
            version += 1  # Increment after each successful migration
        return data

    def _build_config(self, data: dict[str, Any]) -> Config:
        """Build a ``Config`` from a (now-migrated) dict."""
        # We only pass fields that exist in v2+; older fields default.
        try:
            cfg = Config(
                # v1 fields
                default_wpm=data.get("default_wpm", 300),
                min_wpm=data.get("min_wpm", 100),
                max_wpm=data.get("max_wpm", 1000),
                wpm_step=data.get("wpm_step", 25),
                punctuation_multiplier=data.get("punctuation_multiplier", 2.0),
                pause_on_punctuation=data.get("pause_on_punctuation", True),
                pause_chars=data.get("pause_chars", [".", "!", "?", ";", ":"]),
                comma_pause_multiplier=data.get("comma_pause_multiplier", 1.5),
                enable_orp=data.get("enable_orp", True),
                focus_mode=data.get("focus_mode", False),
                show_progress_bar=data.get("show_progress_bar", True),
                show_context_words=data.get("show_context_words", False),
                # v2 fields
                schema_version=int(data.get("schema_version", CURRENT_SCHEMA)),
                theme=data.get("theme", "dark"),
                figure_id=data.get("figure_id", "word"),
                figure_params=dict(data.get("figure_params", {})),
                keybindings=dict(data.get("keybindings", {})),
                config_path=self.path,
            )
        except (TypeError, ValueError) as exc:
            log.warning("config validation failed (%s); using defaults", exc)
            return self._default_with_path()
        return cfg

    # ---- Saving ---------------------------------------------------------

    def save(self, cfg: Config) -> None:
        """Atomically write ``cfg`` to disk.

        Delegates to :func:`rsvp_tui.util.atomic_write_text` so the
        whole package uses one atomic-write implementation. Raises
        on failure (the temp file is cleaned up; the real file is
        never partial).
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._serialize(cfg)
        atomic_write_text(
            self.path, json.dumps(payload, indent=2, ensure_ascii=False)
        )

    def update(self, cfg: Config, **patch: Any) -> Config:
        """Mutate fields on ``cfg`` and persist. Returns the same cfg."""
        for key, value in patch.items():
            if not hasattr(cfg, key):
                raise AttributeError(f"Config has no field {key!r}")
            setattr(cfg, key, value)
        self.save(cfg)
        return cfg

    def reset(self) -> Config:
        """Erase the on-disk config and return a fresh default."""
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError as exc:
                log.warning("could not remove old config: %s", exc)
        cfg = self._default_with_path()
        self.save(cfg)
        return cfg

    # ---- Helpers --------------------------------------------------------

    def _default_with_path(self) -> Config:
        cfg = Config()
        cfg.config_path = self.path
        return cfg

    def _default_payload(self) -> dict[str, Any]:
        cfg = self._default_with_path()
        return self._serialize(cfg)

    def _serialize(self, cfg: Config) -> dict[str, Any]:
        """Convert a ``Config`` to a JSON-safe dict.

        We hand-pick fields rather than using ``dataclasses.asdict`` so
        the on-disk schema stays stable even if we add internal-only
        fields later.
        """
        return {
            "schema_version": CURRENT_SCHEMA,
            # v1 fields
            "default_wpm": cfg.default_wpm,
            "min_wpm": cfg.min_wpm,
            "max_wpm": cfg.max_wpm,
            "wpm_step": cfg.wpm_step,
            "punctuation_multiplier": cfg.punctuation_multiplier,
            "pause_on_punctuation": cfg.pause_on_punctuation,
            "pause_chars": list(cfg.pause_chars),
            "comma_pause_multiplier": cfg.comma_pause_multiplier,
            "enable_orp": cfg.enable_orp,
            "focus_mode": cfg.focus_mode,
            "show_progress_bar": cfg.show_progress_bar,
            "show_context_words": cfg.show_context_words,
            # v2 fields
            "theme": cfg.theme,
            "figure_id": cfg.figure_id,
            "figure_params": dict(cfg.figure_params),
            "keybindings": dict(cfg.keybindings),
        }


__all__ = [
    "CURRENT_SCHEMA",
    "MIGRATIONS",
    "ConfigManager",
]
