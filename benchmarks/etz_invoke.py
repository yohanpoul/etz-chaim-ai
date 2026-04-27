"""Etz Chaim invoke wrapper — subprocess + stdout parsing.

Le pipeline complet d'Etz Chaim (descente Yosher + remontée Or Chozer)
imprime sa réponse finale entre des marqueurs très lisibles dans stdout :

    ┌─── מַלְכוּת (réponse) ──────────────────────────────────┐
    │ <ligne de réponse>
    │ <ligne de réponse>
    └──────────────────────────────────────────────────────────┘

Plutôt que de modifier main.py (1734 LOC, surface d'attaque), on capture
le subprocess stdout et on parse les marqueurs.

Avantages :
    - Aucune modification de main.py (zéro régression)
    - Isolation naturelle entre prompts (fresh process = états globaux
      `_HISHTALSHELUT_STATE`, `_NITZOTZOT_STATE`, `_IGULIM_STATE` reset
      automatiquement)
    - Composable avec le profil benchmark_opus via env / config

Inconvénients (acceptés) :
    - ~2-3s overhead par subprocess (35min cumulé sur 950 prompts)
    - DB writes vers la DB principale (à mitiger pour bench production en
      pointant vers DB séparée via --db flag)
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Marqueurs Unicode dans la sortie main.py:_cmd_ask_yosher
_RESPONSE_START = "┌─── מַלְכוּת"
_RESPONSE_END = "└──"
_RESPONSE_PREFIX = "│ "

# Patterns extraction métriques
_PATTERN_CONFIDENCE = re.compile(r"Confiance réponse\s*:\s*([\d.]+)")
_PATTERN_TOTAL_TIME = re.compile(r"Temps total\s*:\s*([\d.]+)s")
_PATTERN_MALKUTH_TIME = re.compile(r"Temps Malkuth\s*:\s*([\d.]+)s")
_PATTERN_GENERATION_OLAM = re.compile(r"Génération\s*:\s*[\d.]+s\s+\(([a-z]+)\)")
_PATTERN_HISHTALSHELUT = re.compile(r"סֵדֶר הִשְׁתַּלְשְׁלוּת\s*:\s*([a-z\s→]+)")
_PATTERN_QUALITY = re.compile(r"Qualité\s*:\s*([\w_]+)")
_PATTERN_ACTIVE_MODULES = re.compile(r"Modules actifs\s*:\s*(\d+)/10")


@dataclass
class EtzInvocationResult:
    """Résultat d'une invocation Etz Chaim parsée depuis subprocess stdout."""

    response: str = ""
    confidence: float = 0.0
    total_latency_s: float = 0.0
    malkuth_latency_s: float = 0.0
    generation_olam: str = ""
    world_path: list[str] = field(default_factory=list)
    quality_verdict: str = ""
    active_modules: int = 0
    success: bool = False
    error: str | None = None
    raw_stdout: str = ""
    raw_stderr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _extract_response(stdout: str) -> str:
    """Extraire la réponse entre les marqueurs ┌─── מַלְכוּת ... └──.

    Returns:
        Réponse multi-line si trouvée, "" sinon.
    """
    lines = stdout.splitlines()
    in_response = False
    response_lines: list[str] = []

    for line in lines:
        if not in_response:
            if _RESPONSE_START in line:
                in_response = True
            continue
        # in_response == True
        if line.startswith(_RESPONSE_END):
            break
        if line.startswith(_RESPONSE_PREFIX):
            response_lines.append(line[len(_RESPONSE_PREFIX):])
        elif line.startswith("│"):
            # Variante : juste │ sans espace
            response_lines.append(line[1:].lstrip())

    return "\n".join(response_lines).strip()


def _extract_metric(pattern: re.Pattern, stdout: str, default: Any = None) -> Any:
    """Extract metric via regex, return default si absent."""
    match = pattern.search(stdout)
    if match:
        return match.group(1).strip()
    return default


def _parse_world_path(stdout: str) -> list[str]:
    """Extraire le chemin Hishtalshelut (worlds traversés)."""
    raw = _extract_metric(_PATTERN_HISHTALSHELUT, stdout, "")
    if not raw:
        # Pas de Hishtalshelut → un seul olam (chercher generation olam)
        olam = _extract_metric(_PATTERN_GENERATION_OLAM, stdout, "")
        return [olam] if olam else []
    parts = [p.strip().lower() for p in raw.split("→")]
    return [p for p in parts if p]


def invoke_etz(
    query: str,
    *,
    profile: str = "benchmark_opus",
    mode: str = "yosher",
    world: str | None = None,
    timeout: int = 300,
    db_url: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> EtzInvocationResult:
    """Invoke Etz Chaim pipeline pour un prompt et parser la réponse.

    Args:
        query: Le prompt utilisateur.
        profile: Profil config.yaml (défaut benchmark_opus).
        mode: yosher|igulim.
        world: monde forcé optionnel (assiah|yetzirah|briah|atziluth).
        timeout: timeout subprocess seconds.
        db_url: URL PostgreSQL custom (par défaut config.yaml).
        extra_env: env vars additionnels.

    Returns:
        EtzInvocationResult avec response, confidence, world_path, etc.
    """
    import os

    cmd = [sys.executable, "main.py", "ask", query, "--mode", mode]
    if world:
        cmd += ["--world", world]
    if db_url:
        cmd += ["--db", db_url]

    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    # Force le profile via env var (à interpréter par olamot.py si supporté,
    # sinon il faut éditer config.yaml :: active_profile au préalable)
    env["ETZCHAIM_PROFILE"] = profile

    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        return EtzInvocationResult(
            success=False,
            error=f"Timeout after {timeout}s",
            raw_stdout=(e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")),
            raw_stderr=(e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")),
            total_latency_s=time.time() - t0,
        )
    except Exception as e:
        return EtzInvocationResult(
            success=False,
            error=f"Subprocess error: {type(e).__name__}: {e}",
            total_latency_s=time.time() - t0,
        )

    elapsed = time.time() - t0

    if proc.returncode != 0:
        return EtzInvocationResult(
            success=False,
            error=f"main.py exit {proc.returncode}",
            raw_stdout=proc.stdout,
            raw_stderr=proc.stderr,
            total_latency_s=elapsed,
        )

    response = _extract_response(proc.stdout)

    confidence = float(_extract_metric(_PATTERN_CONFIDENCE, proc.stdout, "0.0"))
    total_time = float(_extract_metric(_PATTERN_TOTAL_TIME, proc.stdout, "0.0"))
    malkuth_time = float(_extract_metric(_PATTERN_MALKUTH_TIME, proc.stdout, "0.0"))
    generation_olam = _extract_metric(_PATTERN_GENERATION_OLAM, proc.stdout, "")
    quality_verdict = _extract_metric(_PATTERN_QUALITY, proc.stdout, "")
    active_modules = int(_extract_metric(_PATTERN_ACTIVE_MODULES, proc.stdout, "0"))
    world_path = _parse_world_path(proc.stdout)

    return EtzInvocationResult(
        response=response,
        confidence=confidence,
        total_latency_s=total_time or elapsed,
        malkuth_latency_s=malkuth_time,
        generation_olam=generation_olam,
        world_path=world_path,
        quality_verdict=quality_verdict,
        active_modules=active_modules,
        success=bool(response),  # success si on a extrait au moins une réponse
        raw_stdout=proc.stdout,
        raw_stderr=proc.stderr,
    )


# ---------------------------------------------------------------------------
# Offline tests (no API call)
# ---------------------------------------------------------------------------

_FIXTURE_STDOUT = """
═══════════════════════════════════════════════════════════
  Etz Chaim — Ask Mode — יוֹשֶׁר YOSHER (Double Flux)
  Question : Test prompt
═══════════════════════════════════════════════════════════
  ⟐ Keter (intention) — classification...
  ⟐ ⑪ Malkuth — génération de la réponse...
    סֵדֶר הִשְׁתַּלְשְׁלוּת : assiah → yetzirah → briah
    Monde final : BRIAH (conf=0.85)
    Temps Malkuth : 12.3s

┌─── מַלְכוּת (réponse) ──────────────────────────────────┐
│ This is the test response.
│ Multi-line content preserved.
└──────────────────────────────────────────────────────────┘

── Méta ──
  Niveau Âme         : ר RUACH (domaine=test)
  Modules actifs     : 8/10
  Temps total        : 14.5s
  Génération         : 12.3s (briah)
  Confiance réponse  : 0.85
  Qualité            : excellent
"""


def _self_test_parser() -> bool:
    """Test offline du parser sur fixture statique."""
    response = _extract_response(_FIXTURE_STDOUT)
    expected_response = "This is the test response.\nMulti-line content preserved."
    if response != expected_response:
        print(f"FAIL response: got {response!r}, expected {expected_response!r}",
              file=sys.stderr)
        return False

    confidence = float(_extract_metric(_PATTERN_CONFIDENCE, _FIXTURE_STDOUT, "0"))
    if confidence != 0.85:
        print(f"FAIL confidence: got {confidence}", file=sys.stderr)
        return False

    total = float(_extract_metric(_PATTERN_TOTAL_TIME, _FIXTURE_STDOUT, "0"))
    if total != 14.5:
        print(f"FAIL total_time: got {total}", file=sys.stderr)
        return False

    olam = _extract_metric(_PATTERN_GENERATION_OLAM, _FIXTURE_STDOUT, "")
    if olam != "briah":
        print(f"FAIL olam: got {olam!r}", file=sys.stderr)
        return False

    world_path = _parse_world_path(_FIXTURE_STDOUT)
    if world_path != ["assiah", "yetzirah", "briah"]:
        print(f"FAIL world_path: got {world_path}", file=sys.stderr)
        return False

    quality = _extract_metric(_PATTERN_QUALITY, _FIXTURE_STDOUT, "")
    if quality != "excellent":
        print(f"FAIL quality: got {quality!r}", file=sys.stderr)
        return False

    active = int(_extract_metric(_PATTERN_ACTIVE_MODULES, _FIXTURE_STDOUT, "0"))
    if active != 8:
        print(f"FAIL active_modules: got {active}", file=sys.stderr)
        return False

    print("PASS — parser correctly extracts all metrics from fixture stdout",
          file=sys.stderr)
    return True


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        ok = _self_test_parser()
        sys.exit(0 if ok else 1)

    if len(sys.argv) < 2:
        print(
            "Usage: python -m benchmarks.etz_invoke '<query>' [--world WORLD]\n"
            "       python -m benchmarks.etz_invoke --self-test",
            file=sys.stderr,
        )
        sys.exit(1)

    query = sys.argv[1]
    world = None
    if "--world" in sys.argv:
        idx = sys.argv.index("--world")
        if idx + 1 < len(sys.argv):
            world = sys.argv[idx + 1]

    result = invoke_etz(query, world=world)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
