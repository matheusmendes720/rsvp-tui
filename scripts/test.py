"""``uv run test`` — run the Python test suite.

Defaults to the workspace pytest config (see ``pyproject.toml`` →
``[tool.pytest.ini_options]``) which points at ``rsvp-tui/tests``.
Extra args are forwarded to pytest, so you can do:

    uv run test -k figure
    uv run test tests/test_models.py -x
    uv run test --cov=rsvp_tui
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from ._lib import ROOT, ensure, info, run


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure("pytest")
    info(f"pytest {ROOT / 'rsvp-tui' / 'tests'}")
    return run([sys.executable, "-m", "pytest", *args], cwd=ROOT)


if __name__ == "__main__":
    raise SystemExit(main())
