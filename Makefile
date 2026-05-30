PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: help venv install install-dev lint format format-check check clean

help:
	@echo "Targets:"
	@echo "  make venv         — create virtual environment (.venv)"
	@echo "  make install      — install runtime dependencies"
	@echo "  make install-dev  — install runtime + dev dependencies (ruff, typos)"
	@echo "  make lint         — run ruff linter + typos spell check"
	@echo "  make format       — auto-format code with ruff"
	@echo "  make format-check — check formatting without changes"
	@echo "  make check        — lint + format-check (CI-friendly)"
	@echo "  make clean        — remove venv and caches"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		$(PYTHON) -m venv "$(VENV)" 2>/dev/null \
		|| $(PYTHON) -m virtualenv "$(VENV)"; \
	fi

install: venv
	$(BIN)/pip install -U pip
	$(BIN)/pip install -r requirements.txt

install-dev: install
	$(BIN)/pip install -r requirements-dev.txt

lint:
	$(BIN)/ruff check .
	$(BIN)/typos

format:
	$(BIN)/ruff format .
	$(BIN)/ruff check --fix .

format-check:
	$(BIN)/ruff format --check .

check: lint format-check

clean:
	rm -rf $(VENV) .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
