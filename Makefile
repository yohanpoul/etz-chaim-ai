# Etz Chaim AI — Makefile
.PHONY: help install test lint format docs docs-serve demo clean release

PY ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PYBIN := $(VENV)/bin/python
PYTEST := $(VENV)/bin/pytest

help:
	@echo "Etz Chaim AI — available make targets"
	@echo ""
	@echo "  install        Create venv and install dependencies"
	@echo "  test           Run full test suite"
	@echo "  test-core      Run core modules only (bridge + mazalengine + partzufim)"
	@echo "  lint           Run ruff + mypy"
	@echo "  format         Apply ruff format"
	@echo "  docs           Build MkDocs site (requires 'docs' extras)"
	@echo "  docs-serve     Serve docs locally on :8000"
	@echo "  demo           Run MazalEngine runtime validation cycle"
	@echo "  clean          Remove build artifacts"
	@echo "  release        Verify release readiness (tests + lint + docs)"

install:
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev,docs]"
	$(VENV)/bin/pre-commit install || true
	@echo "✓ Install complete. Activate : source $(VENV)/bin/activate"

test:
	$(PYTEST) -v

test-core:
	$(PYTEST) bridge/tests mazalengine/tests partzufim/tests -v

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/mypy bridge mazalengine partzufim || true

format:
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check --fix .

docs:
	$(VENV)/bin/mkdocs build --strict

docs-serve:
	$(VENV)/bin/mkdocs serve

demo:
	$(PYBIN) scripts/sprint9_force_mazal_cycle.py

clean:
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf site htmlcov .coverage
	find . -type d -name __pycache__ -not -path "./.venv/*" -not -path "./.garak-venv/*" -exec rm -rf {} + 2>/dev/null || true

release: clean lint test docs
	@echo "✓ Release readiness verified"
	@echo "Next : git tag v0.1.0 && git push --tags"
