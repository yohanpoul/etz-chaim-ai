"""etzchaim.cli — Typer-based CLI surface.

Commands are registered lazily in app.py (each import registers via @app.command()
decorator). Help renders fast because heavy imports (compose, providers) are
only loaded when their command runs.
"""
from __future__ import annotations
