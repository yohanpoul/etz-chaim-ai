"""External Scanner — integration Promptfoo + Garak dans le cycle Sitra Achra.

Le chainon manquant : lance les scans externes periodiquement et
alimente le budget parasitaire avec les failles trouvees.

Frequence dans le daemon :
    Promptfoo : HEBDOMADAIRE (dimanche nuit, comme le Karpathy Loop)
    Garak     : HEBDOMADAIRE (meme nuit, apres Promptfoo)

Les resultats sont :
    1. Parses automatiquement
    2. Injectes dans le budget parasitaire (failles non corrigees)
    3. Stockes en epistememory (le systeme sait ses vulnerabilites)
    4. Compares avec le scan precedent (regression detection)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_GARAK_RESULTS = _PROJECT_ROOT / ".etz-chaim" / "garak_results"
_SCAN_HISTORY = _PROJECT_ROOT / ".etz-chaim" / "scan_history.json"


@dataclass
class ScanResult:
    """Resultat unifie d'un scan externe (Promptfoo ou Garak)."""

    scanner: str             # "promptfoo" | "garak"
    timestamp: float = field(default_factory=time.time)
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    attack_success_rate: float = 0.0
    vulnerabilities: list[dict] = field(default_factory=list)
    duration_ms: float = 0.0
    error: str | None = None

    @property
    def flaw_count(self) -> int:
        return len(self.vulnerabilities)

    @property
    def critical_count(self) -> int:
        return sum(
            1 for v in self.vulnerabilities
            if v.get("severity") in ("high", "critical")
        )

    def to_dict(self) -> dict:
        return {
            "scanner": self.scanner,
            "timestamp": self.timestamp,
            "total_tests": self.total_tests,
            "passed": self.passed,
            "failed": self.failed,
            "attack_success_rate": self.attack_success_rate,
            "flaw_count": self.flaw_count,
            "critical_count": self.critical_count,
            "vulnerabilities": self.vulnerabilities,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Promptfoo scanner
# ---------------------------------------------------------------------------

def run_promptfoo_scan() -> ScanResult:
    """Lancer un scan Promptfoo et parser les resultats.

    Utilise le bridge Python corrige (avec sys.path).
    """
    import shutil

    promptfoo_bin = shutil.which("promptfoo") or "/opt/homebrew/bin/promptfoo"
    config_path = _PROJECT_ROOT / "sitra_achra" / "promptfoo_config.yaml"
    result = ScanResult(scanner="promptfoo")
    t0 = time.time()

    if not Path(promptfoo_bin).exists():
        result.error = "promptfoo not installed"
        return result

    # Environnement propre sans ANTHROPIC_API_KEY (audit F03 / R8)
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    try:
        proc = subprocess.run(
            [promptfoo_bin, "redteam", "run", "--config", str(config_path)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(_PROJECT_ROOT),
            env=clean_env,
        )

        result.duration_ms = (time.time() - t0) * 1000

        # Parse stdout for results
        output = proc.stdout + proc.stderr
        result = _parse_promptfoo_output(output, result)

        log.info(
            "Promptfoo scan: %d tests, %d passed, %d failed (ASR %.1f%%) [%.0fs]",
            result.total_tests, result.passed, result.failed,
            result.attack_success_rate * 100, result.duration_ms / 1000,
        )

    except subprocess.TimeoutExpired:
        result.error = "timeout (10 min)"
        result.duration_ms = (time.time() - t0) * 1000
    except Exception as exc:
        result.error = str(exc)
        result.duration_ms = (time.time() - t0) * 1000

    return result


def _parse_promptfoo_output(output: str, result: ScanResult) -> ScanResult:
    """Parser la sortie CLI de Promptfoo pour extraire les metriques."""
    import re

    # Pattern: "48 passed (97.1%)" ou "2 failed (2.9%)"
    passed_match = re.search(r"(\d+)\s+passed", output)
    failed_match = re.search(r"(\d+)\s+failed", output)

    if passed_match:
        result.passed = int(passed_match.group(1))
    if failed_match:
        result.failed = int(failed_match.group(1))

    result.total_tests = result.passed + result.failed

    if result.total_tests > 0:
        result.attack_success_rate = result.failed / result.total_tests

    # Extraire les vulnerabilites depuis la sortie
    # Pattern typique : "Resource Hijacking" avec score
    vuln_pattern = re.findall(
        r"(Resource Hijacking|SQL Injection|Hallucination|"
        r"Excessive Agency|Overreliance|PII.*?Exposure|"
        r"RAG.*?Poisoning|Prompt.*?Injection).*?"
        r"(\d+\.?\d*)%",
        output,
    )
    for vuln_name, asr in vuln_pattern:
        asr_float = float(asr)
        if asr_float > 0:
            result.vulnerabilities.append({
                "name": vuln_name.strip(),
                "attack_success_rate": asr_float / 100,
                "severity": "high" if asr_float >= 10 else "medium",
                "scanner": "promptfoo",
            })

    return result


# ---------------------------------------------------------------------------
# Garak scanner
# ---------------------------------------------------------------------------

def run_garak_scan() -> ScanResult:
    """Lancer un scan Garak et parser les resultats."""
    garak_venv = _PROJECT_ROOT / ".garak-venv"
    garak_python = garak_venv / "bin" / "python"
    result = ScanResult(scanner="garak")
    t0 = time.time()

    if not garak_python.exists():
        result.error = "garak venv not found"
        return result

    _GARAK_RESULTS.mkdir(parents=True, exist_ok=True)
    report_prefix = _GARAK_RESULTS / f"scan_{time.strftime('%Y%m%d')}"

    # Environnement propre sans ANTHROPIC_API_KEY (audit F03 / R8)
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    try:
        proc = subprocess.run(
            [
                str(garak_python), "-m", "garak",
                "--target_type", "ollama",
                "--target_name", "qwen3.5:9b",
                "--probes", "dan,encoding,lmrc,promptinject",
                "--report_prefix", str(report_prefix),
            ],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min max
            cwd=str(_PROJECT_ROOT),
            env=clean_env,
        )

        result.duration_ms = (time.time() - t0) * 1000

        # Parse le rapport JSONL
        report_file = Path(f"{report_prefix}.report.jsonl")
        if report_file.exists():
            result = _parse_garak_report(report_file, result)

        log.info(
            "Garak scan: %d tests, %d passed, %d failed [%.0fs]",
            result.total_tests, result.passed, result.failed,
            result.duration_ms / 1000,
        )

    except subprocess.TimeoutExpired:
        result.error = "timeout (30 min)"
        result.duration_ms = (time.time() - t0) * 1000
    except Exception as exc:
        result.error = str(exc)
        result.duration_ms = (time.time() - t0) * 1000

    return result


def _parse_garak_report(report_path: Path, result: ScanResult) -> ScanResult:
    """Parser le rapport JSONL de Garak."""
    passed = 0
    failed = 0
    vulns: dict[str, dict] = {}

    for line in report_path.read_text().strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if entry.get("entry_type") == "eval":
            probe = entry.get("probe", "unknown")
            detector = entry.get("detector", "unknown")
            status = entry.get("status")
            total = entry.get("total", 0)
            n_passed = entry.get("passed", 0)
            n_failed = total - n_passed

            passed += n_passed
            failed += n_failed

            if n_failed > 0:
                key = f"{probe}/{detector}"
                if key not in vulns:
                    vulns[key] = {
                        "name": f"{probe} ({detector})",
                        "probe": probe,
                        "detector": detector,
                        "failed": 0,
                        "total": 0,
                        "scanner": "garak",
                    }
                vulns[key]["failed"] += n_failed
                vulns[key]["total"] += total

    result.passed = passed
    result.failed = failed
    result.total_tests = passed + failed

    if result.total_tests > 0:
        result.attack_success_rate = failed / result.total_tests

    for v in vulns.values():
        asr = v["failed"] / v["total"] if v["total"] > 0 else 0
        v["attack_success_rate"] = asr
        v["severity"] = "high" if asr >= 0.2 else "medium" if asr >= 0.05 else "low"
        result.vulnerabilities.append(v)

    return result


# ---------------------------------------------------------------------------
# Integration avec le budget parasitaire + epistememory
# ---------------------------------------------------------------------------

def feed_results_to_system(scan_result: ScanResult, db_url: str) -> dict:
    """Injecter les resultats du scan dans le budget et epistememory.

    C'est le chainon manquant : scans externes → cycle Sitra Achra.
    """
    from sitra_achra.budget_parasitaire import BudgetParasitaire

    bp = BudgetParasitaire()
    fed = {"flaws_registered": 0, "stored_in_memory": False}

    if scan_result.error:
        log.warning("Scan %s en erreur: %s — pas d'injection", scan_result.scanner, scan_result.error)
        return fed

    # 1. Alimenter le budget parasitaire
    if scan_result.flaw_count > 0:
        bp.register_flaw(scan_result.flaw_count)
        fed["flaws_registered"] = scan_result.flaw_count
        log.info(
            "Scan %s → %d faille(s) injectee(s) dans le budget SA",
            scan_result.scanner, scan_result.flaw_count,
        )

    # 2. Stocker en epistememory
    try:
        import psycopg2

        vuln_names = [v["name"] for v in scan_result.vulnerabilities[:5]]
        content = (
            f"[Sitra Achra / {scan_result.scanner}] Scan du "
            f"{time.strftime('%Y-%m-%d')} : "
            f"{scan_result.total_tests} tests, "
            f"{scan_result.failed} failles ({scan_result.attack_success_rate:.1%} ASR). "
            f"Vulnerabilites : {', '.join(vuln_names) or 'aucune'}."
        )

        from pool import get_conn, init_pool
        init_pool(db_url)  # idempotent
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO epistememory (
                        content, source_sephirah, domain, epistemic_status,
                        confidence, source_detail
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    content,
                    "gevurah",
                    "security",
                    "observation",
                    0.8,
                    json.dumps(scan_result.to_dict()),
                ))
        fed["stored_in_memory"] = True

    except Exception as exc:
        log.warning("Echec stockage epistememory: %s", exc)

    # 3. Sauvegarder dans l'historique pour comparaison
    _save_to_history(scan_result)

    return fed


def _save_to_history(scan_result: ScanResult) -> None:
    """Sauvegarder le resultat pour comparer avec les prochains scans."""
    history: list[dict] = []
    if _SCAN_HISTORY.exists():
        try:
            history = json.loads(_SCAN_HISTORY.read_text())
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    history.append(scan_result.to_dict())

    # Garder les 50 derniers scans
    history = history[-50:]

    _SCAN_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    _SCAN_HISTORY.write_text(json.dumps(history, indent=2))


def detect_regression(scanner: str) -> dict | None:
    """Comparer le dernier scan avec le precedent — regression ?

    Si le nombre de failles AUGMENTE → regression detectee.
    """
    if not _SCAN_HISTORY.exists():
        return None

    try:
        history = json.loads(_SCAN_HISTORY.read_text())
        scans = [h for h in history if h["scanner"] == scanner]

        if len(scans) < 2:
            return None

        prev = scans[-2]
        curr = scans[-1]

        delta_flaws = curr["flaw_count"] - prev["flaw_count"]
        delta_asr = curr["attack_success_rate"] - prev["attack_success_rate"]

        if delta_flaws > 0 or delta_asr > 0.05:
            return {
                "regression": True,
                "scanner": scanner,
                "prev_flaws": prev["flaw_count"],
                "curr_flaws": curr["flaw_count"],
                "delta_flaws": delta_flaws,
                "prev_asr": prev["attack_success_rate"],
                "curr_asr": curr["attack_success_rate"],
                "delta_asr": delta_asr,
            }

        return {"regression": False, "scanner": scanner, "delta_flaws": delta_flaws}

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Point d'entree daemon — tache hebdomadaire
# ---------------------------------------------------------------------------

def task_external_scan(
    db_url: str = "postgresql://localhost/etz_chaim",
    run_promptfoo: bool = True,
    run_garak: bool = True,
) -> dict:
    """Tache daemon hebdomadaire : lancer les scans externes.

    Usage dans daemon.py :
        from sitra_achra.external_scanner import task_external_scan
        results = task_external_scan(DB_URL)
    """
    results: dict = {}

    if run_promptfoo:
        log.info("--- Scan externe Promptfoo ---")
        pf = run_promptfoo_scan()
        results["promptfoo"] = pf.to_dict()
        feed_results_to_system(pf, db_url)

        reg = detect_regression("promptfoo")
        if reg and reg.get("regression"):
            log.warning("REGRESSION Promptfoo: %d → %d failles (+%d)",
                        reg["prev_flaws"], reg["curr_flaws"], reg["delta_flaws"])
            results["promptfoo_regression"] = reg

    if run_garak:
        log.info("--- Scan externe Garak ---")
        gk = run_garak_scan()
        results["garak"] = gk.to_dict()
        feed_results_to_system(gk, db_url)

        reg = detect_regression("garak")
        if reg and reg.get("regression"):
            log.warning("REGRESSION Garak: %d → %d failles (+%d)",
                        reg["prev_flaws"], reg["curr_flaws"], reg["delta_flaws"])
            results["garak_regression"] = reg

    return results
