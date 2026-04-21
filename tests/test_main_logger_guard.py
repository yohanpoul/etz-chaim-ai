"""Regression test — main.py must not reference a bare ``logger`` symbol.

Sprint imports-scan followup (Findings U2/U3/U4): three except-blocks in
``main.py`` referenced ``logger.debug(...)`` while the module defines the
logger as ``log = logging.getLogger("etz-malkuth")`` at line 31. The bug
was latent — ``logger`` would only be evaluated when the surrounding
``try`` raised, and the resulting ``NameError`` masked the original error.

Branches that were exposed:
  * line 678 — Masakh pressure regulation skipped
  * line 941 — Auto-hizdakchut skipped
  * line 979 — Partzuf transition check

This test scans ``main.py`` as AST and asserts no ``Name`` load targets
``logger``. It also confirms ``log`` is the canonical module logger.
"""
from __future__ import annotations

import ast
from pathlib import Path


MAIN_PATH = Path(__file__).resolve().parent.parent / "main.py"


def _loaded_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
    return names


def _assigned_top_level(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    names.add(tgt.id)
    return names


def test_main_does_not_reference_bare_logger():
    """No bare ``logger`` should be loaded anywhere in main.py — the
    module uses ``log`` (see line ~31: ``log = logging.getLogger(...)``)."""
    source = MAIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    used = _loaded_names(tree)
    assert "logger" not in used, (
        "main.py should not reference bare `logger` — the module logger "
        "is `log` (defined as logging.getLogger(\"etz-malkuth\")). Replace "
        "`logger.debug(...)` with `log.debug(...)` in any except-block."
    )


def test_main_defines_log_as_module_logger():
    """Positive assertion: ``log`` must be bound at module scope."""
    source = MAIN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assigned = _assigned_top_level(tree)
    assert "log" in assigned, (
        "main.py must bind `log` at module top-level — if renamed, update "
        "this test and every downstream `log.debug/info/warning/error`."
    )
