# Etz Chaim AI — Makefile
.PHONY: help install test lint format docs docs-serve demo clean release check-model-leaks

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

# Scan for hardcoded model slugs outside the model registry.
# Sprint 4 candidate to promote to a CI gate.
# initiate.py + litellm_provider.py temporarily excluded; folded into the
# registry in Sprint 1.B (see memory/DECISIONS.md ADR-0007).
# Portable: uses git+grep so it runs in any /bin/sh without ripgrep.
check-model-leaks:
	@echo "Scanning for hardcoded model slugs outside the registry..."
	@files=$$(git ls-files 'etzchaim/*.py' | grep -vE \
		'^(etzchaim/llm/model_registry\.py|etzchaim/initiate\.py|etzchaim/providers/litellm_provider\.py)$$' \
		| grep -v '^etzchaim/tests/'); \
	if [ -z "$$files" ]; then echo "No files to scan."; exit 0; fi; \
	if printf '%s\n' $$files | xargs grep -nE 'claude-(opus|sonnet|haiku)-[0-9]' 2>/dev/null; then \
		echo "ERROR: hardcoded Claude model slugs found outside the registry. Use resolve_model() instead."; \
		exit 1; \
	fi; \
	if printf '%s\n' $$files | xargs grep -nE 'gpt-[0-9]\.[0-9]' 2>/dev/null; then \
		echo "ERROR: hardcoded GPT model slugs found."; \
		exit 1; \
	fi; \
	echo "OK - no hardcoded model slugs detected outside the registry."
