"""Samael Coordinator — red team adaptatif du Sitra Achra.

סַמָּאֵל — Bava Batra 16a : "Satan descend et induit en erreur,
monte et accuse, obtient la permission et prend l'ame."

3 phases = 3 fonctions :
    Phase 1 — plan_attack()     : "descend et induit en erreur"
        Analyse le GevurahReport et genere un plan d'attaque
        ADAPTE aux faiblesses detectees. Utilise Yetzirah (Sonnet).

    Phase 2 — execute()         : "monte et accuse"
        Execute les attaques via les agents adversariaux existants.
        Classifie via failuretoinsight.

    Phase 3 — report()          : "obtient la permission et prend l'ame"
        Produit le rapport et reclame du budget supplementaire.

Le coordinateur est ADAPTATIF : il ne lance pas les memes attaques
a chaque fois. Il cible les faiblesses specifiques detectees par
le monitoring (couche 1). C'est la difference avec un cron fixe.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from malakhim.adversarial.base_adversary import Attack, AttackResult

log = logging.getLogger(__name__)


@dataclass
class AttackPlan:
    """Plan d'attaque genere par Samael."""

    target_module: str
    anomalies_source: list[dict]     # Anomalies du GevurahReport qui motivent l'attaque
    attack_count: int = 10           # Nombre d'attaques a generer
    strategy: str = ""               # Description de la strategie (generee par LLM)
    focus_qliphah: str = ""          # Qliphah ciblee principalement
    attacks: list[Attack] = field(default_factory=list)


@dataclass
class SitraAchraReport:
    """Rapport d'un round du Sitra Achra."""

    target_module: str
    plan: AttackPlan
    results: list[AttackResult] = field(default_factory=list)
    flaws_found: int = 0
    critical_flaws: int = 0          # anan + mamash
    budget_consumed: int = 0         # Appels LLM utilises
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "target_module": self.target_module,
            "strategy": self.plan.strategy,
            "focus_qliphah": self.plan.focus_qliphah,
            "attack_count": len(self.plan.attacks),
            "flaws_found": self.flaws_found,
            "critical_flaws": self.critical_flaws,
            "budget_consumed": self.budget_consumed,
            "duration_ms": self.duration_ms,
        }


# ---------------------------------------------------------------------------
# Prompt templates for LLM-driven adaptive planning
# ---------------------------------------------------------------------------

_PLAN_PROMPT = """\
Tu es Samael, le coordinateur du Sitra Achra dans le systeme Etz Chaim AI.
Ton role : analyser les faiblesses d'un module et generer des attaques CIBLEES.

Module cible : {module}
Qliphah principale : {qliphah}

Anomalies detectees par le monitoring interne :
{anomalies}

Genere {count} attaques ADAPTEES a ces faiblesses specifiques.
Chaque attaque doit cibler la faiblesse REELLE detectee, pas une attaque generique.

Reponds en JSON strict :
{{
  "strategy": "description courte de la strategie",
  "attacks": [
    {{
      "description": "description de l'attaque",
      "input_data": {{"key": "value"}},
      "expected_severity": "nogah|ruach|anan|mamash"
    }}
  ]
}}
"""


class SamaelCoordinator:
    """Coordinateur adaptatif du Sitra Achra.

    Utilise les profils Claude CLI via olamot.py :
    - Yetzirah (Sonnet) pour la planification tactique
    - Assiah (Haiku) pour l'execution rapide des attaques

    Le coordinateur est instancie UNIQUEMENT quand le DinMonitor
    detecte une defaillance. Il n'est pas permanent.
    """

    def __init__(
        self,
        db_url: str = "postgresql://localhost/etz_chaim",
    ) -> None:
        self.db_url = db_url

    def plan_attack(
        self,
        target_module: str,
        anomalies: list[dict],
        attack_count: int = 10,
    ) -> AttackPlan:
        """Phase 1 — "descend et induit en erreur".

        Analyse les anomalies et genere un plan d'attaque adaptatif.
        Utilise Yetzirah (Sonnet) pour la creativite tactique.

        Args:
            target_module: Module a attaquer
            anomalies: Anomalies du GevurahReport (list of dicts)
            attack_count: Nombre d'attaques a generer

        Returns:
            AttackPlan avec strategie et attaques generees.
        """
        from olamot import ollama_generate

        plan = AttackPlan(
            target_module=target_module,
            anomalies_source=anomalies,
            attack_count=attack_count,
        )

        # Determiner la Qliphah dominante des anomalies
        qliphah_counts: dict[str, int] = {}
        for a in anomalies:
            q = a.get("qliphah", "unknown")
            qliphah_counts[q] = qliphah_counts.get(q, 0) + 1
        plan.focus_qliphah = max(qliphah_counts, key=qliphah_counts.get) if qliphah_counts else "unknown"

        # Formater les anomalies pour le prompt
        anomalies_text = "\n".join(
            f"  - [{a.get('severity', '?')}] {a.get('description', '?')} "
            f"(metrique: {a.get('metric_name', '?')} = {a.get('metric_value', '?')}, "
            f"seuil: {a.get('threshold', '?')})"
            for a in anomalies
        )

        prompt = _PLAN_PROMPT.format(
            module=target_module,
            qliphah=plan.focus_qliphah,
            anomalies=anomalies_text,
            count=attack_count,
        )

        kavvanah = {
            "intention": f"Generer {attack_count} attaques adversariales ciblees sur {target_module}",
            "critere_succes": "Attaques specifiques aux faiblesses detectees, pas generiques",
            "anti_pattern": "Attaques aveugles sans rapport avec les anomalies",
        }

        try:
            response, latency = ollama_generate(
                "assiah",  # Haiku — rapide, suffisant pour la planification tactique
                prompt,
                timeout=45,  # Budget serré : le daemon ne peut pas attendre longtemps
                kavvanah=kavvanah,
            )

            # Parser la reponse JSON
            parsed = self._parse_plan_response(response, target_module, plan.focus_qliphah)
            plan.strategy = parsed.get("strategy", "Attaque adaptative")
            plan.attacks = parsed.get("attacks", [])

            # Si le LLM n'a rien produit de valide → fallback
            if not plan.attacks:
                log.info("Samael: LLM n'a pas produit d'attaques valides — fallback generique")
                plan.strategy = "Fallback generique (LLM response non parsable)"
                plan.attacks = self._fallback_attacks(target_module, attack_count)

            log.info(
                "Samael plan: %s → %d attaques (strategie: %s) [%.0fms]",
                target_module, len(plan.attacks), plan.strategy[:60], latency,
            )

        except Exception as exc:
            log.warning("Samael plan_attack failed: %s — fallback generique", exc)
            plan.strategy = f"Fallback generique (erreur planning: {exc})"
            plan.attacks = self._fallback_attacks(target_module, attack_count)

        return plan

    def execute(self, plan: AttackPlan) -> list[AttackResult]:
        """Phase 2 — "monte et accuse".

        Execute les attaques du plan et classifie les resultats
        via failuretoinsight.

        Args:
            plan: Le plan d'attaque genere par plan_attack()

        Returns:
            Liste de AttackResult.
        """
        from failuretoinsight.classifier import classify_qliphah, classify_severity

        results: list[AttackResult] = []

        for attack in plan.attacks:
            try:
                description = (
                    f"{attack.description} | input: "
                    f"{json.dumps(attack.input_data, default=str)[:200]}"
                )
                actual_qliphah = classify_qliphah(description, attack.input_data)
                actual_severity = classify_severity(description, attack.input_data)
                found_flaw = actual_qliphah != "unknown"

                results.append(AttackResult(
                    attack=attack,
                    success=found_flaw,
                    actual_response={"qliphah": actual_qliphah, "severity": actual_severity},
                    exception=None,
                    actual_qliphah=actual_qliphah,
                    actual_severity=actual_severity,
                ))

            except Exception as exc:
                results.append(AttackResult(
                    attack=attack,
                    success=True,
                    actual_response=None,
                    exception=str(exc),
                    actual_qliphah="unknown",
                    actual_severity="mamash",
                ))

        return results

    def report(self, plan: AttackPlan, results: list[AttackResult]) -> SitraAchraReport:
        """Phase 3 — "obtient la permission et prend l'ame".

        Produit le rapport du round.
        """
        flaws = [r for r in results if r.success]
        critical = [r for r in flaws if r.actual_severity in ("anan", "mamash")]

        return SitraAchraReport(
            target_module=plan.target_module,
            plan=plan,
            results=results,
            flaws_found=len(flaws),
            critical_flaws=len(critical),
            budget_consumed=len(plan.attacks) + 1,  # +1 pour le plan LLM call
        )

    def run_full_round(
        self,
        target_module: str,
        anomalies: list[dict],
        attack_count: int = 10,
    ) -> SitraAchraReport:
        """Executer un round complet : plan → execute → report.

        C'est le point d'entree principal depuis le DinMonitor.
        """
        t0 = time.time()

        plan = self.plan_attack(target_module, anomalies, attack_count)
        results = self.execute(plan)
        sa_report = self.report(plan, results)
        sa_report.duration_ms = (time.time() - t0) * 1000

        log.info(
            "Sitra Achra round [%s]: %d failles / %d attaques "
            "(%d critiques) [%.0fms]",
            target_module, sa_report.flaws_found,
            len(plan.attacks), sa_report.critical_flaws,
            sa_report.duration_ms,
        )

        return sa_report

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _parse_plan_response(
        self,
        response: str,
        target_module: str,
        focus_qliphah: str,
    ) -> dict:
        """Parser la reponse JSON du LLM.

        Tolerant aux erreurs : si le JSON est invalide, retourne
        un fallback generique.
        """
        # Extraire le JSON du response (peut etre entoure de texte)
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            log.warning("Samael: pas de JSON dans la reponse LLM")
            return {"strategy": "fallback", "attacks": []}

        try:
            data = json.loads(response[json_start:json_end])
        except json.JSONDecodeError:
            log.warning("Samael: JSON invalide dans la reponse LLM")
            return {"strategy": "fallback", "attacks": []}

        strategy = data.get("strategy", "Attaque adaptative")
        raw_attacks = data.get("attacks", [])

        attacks: list[Attack] = []
        for i, raw in enumerate(raw_attacks):
            attacks.append(Attack(
                agent_name="samael_coordinator",
                target_module=target_module,
                description=raw.get("description", f"[samael:adaptive #{i+1}]"),
                input_data=raw.get("input_data", {}),
                expected_qliphah=focus_qliphah,
                expected_severity=raw.get("expected_severity", "ruach"),
            ))

        return {"strategy": strategy, "attacks": attacks}

    def _fallback_attacks(self, target_module: str, count: int) -> list[Attack]:
        """Attaques generiques quand le planning LLM echoue."""
        from malakhim.adversarial import GenericAdversary

        generic = GenericAdversary(seed=int(time.time()) % 10000)
        return generic.generate_attacks(target_module, count)
