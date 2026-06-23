"""Workspace entry-point shim package.

This package exists so the workspace ``pyproject.toml`` can ship
its console scripts (``rsvp-tasks``, ``rsvp-test``, etc.) as a
real, installable Python package. The actual implementations live
in the sibling ``scripts/`` package and the ``rsvp_tui`` workspace
member; this module is just a thin re-export layer.

Public surface (every name is also a console script in
``[project.scripts]``):

    rsvp_tasks        -> scripts.tasks:main
    rsvp_tui          -> rsvp_tui.cli:main
    rsvp_palette      -> scripts.palette:main
    rsvp_demo         -> scripts.demo:main
    rsvp_build        -> scripts.build:main
    rsvp_dev          -> scripts.build:main with --editable
    rsvp_sync         -> scripts.sync:main
    rsvp_clean        -> scripts.clean:main
    rsvp_test         -> scripts.test:main
    rsvp_lint         -> scripts.lint:main
    rsvp_format       -> scripts.format:main
    rsvp_typecheck    -> scripts.typecheck:main
    rsvp_verify       -> scripts.verify:main
    rsvp_docs         -> scripts.docs:main
    rsvp_man          -> scripts.man:main
    rsvp_bench        -> scripts.bench:main
    rsvp_read         -> scripts.run:main
    rsvp_import       -> scripts.run:main
    rsvp_library      -> scripts.run:main
    rsvp_config       -> scripts.run:main
"""
from __future__ import annotations

__version__ = "0.3.0"

# Re-export the entry points. ``main`` must be a callable taking
# ``argv`` and returning an int; the [project.scripts] table in
# the workspace pyproject.toml points each name at one of these.
from scripts.tasks import main as rsvp_tasks                        # noqa: F401
from scripts.palette import main as rsvp_palette                  # noqa: F401
from scripts.demo import main as rsvp_demo                        # noqa: F401
from scripts.build import main as rsvp_build                      # noqa: F401
from scripts.sync import main as rsvp_sync                        # noqa: F401
from scripts.clean import main as rsvp_clean                      # noqa: F401
from scripts.test import main as rsvp_test                        # noqa: F401
from scripts.lint import main as rsvp_lint                        # noqa: F401
from scripts.format import main as rsvp_format                    # noqa: F401
from scripts.typecheck import main as rsvp_typecheck              # noqa: F401
from scripts.verify import main as rsvp_verify                    # noqa: F401
from scripts.docs import main as rsvp_docs                        # noqa: F401
from scripts.man import main as rsvp_man                          # noqa: F401
from scripts.bench import main as rsvp_bench                      # noqa: F401
from scripts.run import main as _rsvp_run                         # noqa: F401
from scripts.cli_dispatch import main as rsvp_cli                  # noqa: F401

# All four pass-throughs (``read`` / ``import`` / ``library`` /
# ``config``) share the same implementation; the underlying CLI
# dispatches on argv[1]. We give each a distinct Python name so
# the [project.scripts] table reads cleanly.
rsvp_read = _rsvp_run       # type: ignore[assignment]
rsvp_import = _rsvp_run     # type: ignore[assignment]
rsvp_library = _rsvp_run    # type: ignore[assignment]
rsvp_config = _rsvp_run     # type: ignore[assignment]


def rsvp_dev() -> int:
    """``uv run rsvp-dev`` — alias for ``uv run rsvp-build --editable``."""
    import sys

    sys.argv = [sys.argv[0], "--editable"] + [a for a in sys.argv[1:] if a != "--editable"]
    return rsvp_build()
