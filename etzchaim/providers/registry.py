"""Provider registry — selects best backend for a given provider family.

For the Claude family (opus/sonnet/haiku), prefers anthropic SDK when
ANTHROPIC_API_KEY is set (Docker-compatible, no interactive auth required).
Falls back to the legacy `claude` CLI subprocess on hosts with the CLI authed.

v0.3.0 Phase FULL will extend to OpenAI, Google, xAI, DeepSeek, etc. via LiteLLM.
"""
from __future__ import annotations

import os
import shutil


def select_claude_backend() -> str:
    """Return 'anthropic_sdk' or 'claude_cli' based on availability.

    Priority :
    1. ANTHROPIC_API_KEY set → use anthropic SDK (container-safe, preferred)
    2. `claude` binary on PATH → use CLI subprocess (legacy v0.1, native hosts)
    3. Raise RuntimeError with 3 remediation paths

    Raises:
        RuntimeError: neither backend available.
    """
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic_sdk"
    if shutil.which("claude"):
        return "claude_cli"
    raise RuntimeError(
        "Aucun backend Claude disponible. Solutions :\n"
        "  1. export ANTHROPIC_API_KEY=sk-ant-... (recommandé, Docker-compatible)\n"
        "  2. Installer Claude Code CLI : npm install -g @anthropic-ai/claude-code\n"
        "  3. Basculer au profil ollama_local (pas de clé requise) :\n"
        "     etzchaim config set olamot.atziluth.provider ollama"
    )
