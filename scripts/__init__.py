"""Cross-platform helpers for the RSVP workspace.

Every helper in this package is a real entry point exposed via
``[tool.uv.scripts]`` in the root ``pyproject.toml``. Run them with:

    uv run <task> [args...]

Each module exposes a ``main(argv=None) -> int`` that returns a
process exit code. ``sys.exit(0)`` on success, ``>=1`` on failure.
The helpers are deliberately thin: they call ``subprocess.run`` on
the underlying tools (``pytest``, ``ruff``, ``maturin``,
``cargo``) so the same code works on Windows-bash, MSYS, Linux,
and macOS.
"""
