"""Regression test — igulim.py final report must not crash on NameError.

Sprint imports-scan Finding I1: igulim.py:516 referenced ``t_gen`` (bare) while
the variable was defined as ``t_gen_ms`` on line 460. This crashed the final
report formatting of ``_cmd_ask_igulim`` every time Igulim mode was invoked
(forced by CLI or auto-triggered when confidence < 0.2).

The bug was latent because it fired after the LLM response was already
printed, so partial output masked the traceback as a post-print glitch.
"""
from __future__ import annotations

import ast
from pathlib import Path


IGULIM_PATH = Path(__file__).resolve().parent.parent / "igulim.py"


def _get_function(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in igulim.py")


def _referenced_names(fn: ast.FunctionDef) -> set[str]:
    """All bare Name loads inside fn (best-effort, ignores comprehensions)."""
    names: set[str] = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
    return names


def test_cmd_ask_igulim_does_not_reference_bare_t_gen():
    """Explicit regression guard: ``t_gen`` must not be used bare in the
    Igulim final report. Use ``t_gen_ms/1000`` or a properly-bound local."""
    source = IGULIM_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    fn = _get_function(tree, "_cmd_ask_igulim")

    used = _referenced_names(fn)
    assert "t_gen" not in used, (
        "_cmd_ask_igulim should no longer reference bare `t_gen` — the "
        "variable is defined as `t_gen_ms` on line ~460. Use t_gen_ms/1000 "
        "or rename t_gen_ms → t_gen consistently."
    )


def test_t_gen_ms_is_used_in_generation_line():
    """The 'Génération' line in the final report must format t_gen_ms/1000."""
    source = IGULIM_PATH.read_text(encoding="utf-8")
    # Be tolerant of whitespace variants around /
    normalised = "".join(source.split())
    assert "t_gen_ms/1000" in normalised, (
        "expected t_gen_ms/1000 formatting somewhere in igulim.py — check "
        "the Igulim final report block"
    )
