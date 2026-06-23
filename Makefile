# =====================================================================
#  RSVP workspace — task surface
# ---------------------------------------------------------------------
#  Run any target with:    make <target>
#  Or, equivalently:       uv run python -m scripts.<name>
#  Or, on Windows:         rspv.bat <target>
#
#  List every target:     make help
#  This is the canonical discovery surface; the Python ``tasks``
#  module and the man page both read this Makefile's help block.
# =====================================================================

# ---- User-facing knobs ----------------------------------------------------

PY      ?= python
RSVP    ?= $(PY) -m rsvp_tui.cli
PYTEST  ?= $(PY) -m pytest
RUFF    ?= $(PY) -m ruff
BLACK   ?= $(PY) -m black
MYPY    ?= $(PY) -m mypy
MATURIN ?= maturin

RSVP_TUI  := rsvp-tui
RSVP_CORE := rsvp-core
SCRIPTS   := scripts

# ---- Targets --------------------------------------------------------------

.PHONY: help
help: ## show this help (default)
	@$(PY) -m scripts.tasks

.PHONY: tui
tui: ## launch the interactive TUI
	$(RSVP)

.PHONY: read
read: ## rsvp read [file] — read a book
	$(RSVP) read

.PHONY: import
import: ## rsvp import <file> — import a book
	$(RSVP) import

.PHONY: library
library: ## rsvp library — open the library
	$(RSVP) library

.PHONY: config
config: ## rsvp config — open the settings UI
	$(RSVP) config

.PHONY: doctor
doctor: ## diagnose the local install
	$(PY) -m scripts.doctor

.PHONY: themes
themes: ## list themes
	$(RSVP) themes

.PHONY: where
where: ## show data directory paths
	$(RSVP) where

.PHONY: version
version: ## show version + platform info
	$(RSVP) version

.PHONY: palette
palette: ## open the in-TUI command palette
	$(PY) -m scripts.palette

.PHONY: demo
demo: ## launch the dependency-free demo
	$(PY) -m scripts.demo

# ---- build / install ------------------------------------------------------

.PHONY: build
build: ## build Rust ext + install Python package
	$(PY) -m scripts.build

.PHONY: dev
dev: ## editable install (maturin develop --release)
	$(PY) -m scripts.build --editable

.PHONY: sync
sync: ## uv sync
	uv sync

.PHONY: clean
clean: ## remove build artefacts (use clean-all for full reset)
	$(PY) -m scripts.clean

.PHONY: clean-all
clean-all: ## remove .venv and uv.lock too
	$(PY) -m scripts.clean --all

# ---- quality gates --------------------------------------------------------

.PHONY: test
test: ## run the pytest suite
	$(PY) -m scripts.test

.PHONY: lint
lint: ## ruff check + black --check
	$(PY) -m scripts.lint

.PHONY: lint-fix
lint-fix: ## ruff check --fix + black (reformat)
	$(PY) -m scripts.lint --fix

.PHONY: format
format: ## black + ruff --fix
	$(PY) -m scripts.format

.PHONY: typecheck
typecheck: ## mypy --strict
	$(PY) -m scripts.typecheck

.PHONY: verify
verify: ## lint + typecheck + test (full quality gate)
	$(PY) -m scripts.verify

# ---- docs -----------------------------------------------------------------

.PHONY: docs
docs: ## build man page + snapshot CLI help
	$(PY) -m scripts.docs

.PHONY: man
man: ## render rsvp.1
	$(PY) -m scripts.man

.PHONY: man-view
man-view: ## render and view rsvp.1
	$(PY) -m scripts.man --view

.PHONY: man-install
man-install: ## render and install rsvp.1 to $MANPATH/man1/
	$(PY) -m scripts.man --install

.PHONY: bench
bench: ## run cargo benchmarks
	$(PY) -m scripts.bench

# ---- meta ----------------------------------------------------------------

.PHONY: tasks
tasks: ## print the live task table
	$(PY) -m scripts.tasks
