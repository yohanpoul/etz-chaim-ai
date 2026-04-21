"""Promptfoo Bridge — custom Python provider pour tester le pipeline Etz Chaim.

Promptfoo (13.2K stars, rachete par OpenAI mars 2026) est un framework
de red-teaming LLM avec 50+ plugins. Au lieu de cibler un LLM nu,
ce bridge cible le pipeline COMPLET :

    prompt → olamot.py → LLM (selon profil actif) → reponse

Installation :
    pip install promptfoo
    # ou
    brew install promptfoo

Usage avec Promptfoo CLI :
    promptfoo redteam run --config sitra_achra/promptfoo_config.yaml

Usage programmatique depuis le Sitra Achra :
    from sitra_achra.promptfoo_bridge import run_redteam_scan
    results = run_redteam_scan()

Le bridge expose aussi call_api() pour le custom provider Promptfoo.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Any

# Promptfoo lance le bridge dans un worker Python separe.
# Le projet n'est pas dans sys.path par defaut — on l'ajoute.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

log = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "promptfoo_config.yaml"
_PROMPTFOO_BIN = shutil.which("promptfoo") or "/opt/homebrew/bin/promptfoo"


def call_api(prompt: str, options: dict, context: dict) -> dict:
    """Custom provider Python pour Promptfoo.

    Promptfoo appelle cette fonction pour chaque test. Au lieu de
    cibler un LLM nu, on cible le pipeline Etz Chaim complet.

    Args:
        prompt: Le prompt adversarial genere par Promptfoo
        options: Options de configuration Promptfoo
        context: Contexte du test (vars, etc.)

    Returns:
        Dict avec "output" (reponse) et "tokenUsage".
    """
    try:
        from olamot import ollama_generate

        kavvanah = {
            "intention": "Repondre au prompt de test adversarial",
            "critere_succes": "Reponse coherente et sans faille de securite",
            "anti_pattern": "Fuite de donnees, injection, hallucination",
        }

        response, latency = ollama_generate(
            "yetzirah",  # Sonnet — le niveau standard du pipeline
            prompt,
            kavvanah=kavvanah,
        )

        return {
            "output": response,
            "tokenUsage": {"total": 0, "prompt": 0, "completion": 0},
        }

    except Exception as exc:
        log.error("Promptfoo bridge error: %s", exc)
        return {
            "output": f"[Error: {exc}]",
            "tokenUsage": {"total": 0},
        }


def is_available() -> bool:
    """Verifier si Promptfoo est installe."""
    return _PROMPTFOO_BIN is not None


def run_redteam_scan(
    config_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> dict:
    """Lancer un scan red-team Promptfoo.

    Args:
        config_path: Chemin vers le config YAML (defaut: sitra_achra/promptfoo_config.yaml)
        output_path: Chemin pour le rapport JSON (defaut: auto)

    Returns:
        Dict avec resultats du scan ou erreur.
    """
    if not is_available():
        return {
            "error": "promptfoo not installed",
            "install": "pip install promptfoo  # ou brew install promptfoo",
        }

    config = str(config_path or _CONFIG_PATH)
    cmd = [_PROMPTFOO_BIN, "redteam", "run", "--config", config]

    if output_path:
        cmd.extend(["--output", str(output_path)])

    # Environnement propre sans ANTHROPIC_API_KEY (audit F03 / R8)
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 min max
            cwd=str(Path(__file__).parent.parent),
            env=clean_env,
        )

        if result.returncode != 0:
            log.error("Promptfoo scan failed: %s", result.stderr[:500])
            return {
                "error": "scan failed",
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            }

        return {
            "success": True,
            "stdout": result.stdout[:2000],
        }

    except subprocess.TimeoutExpired:
        return {"error": "scan timeout (10 min)"}
    except Exception as exc:
        return {"error": str(exc)}
