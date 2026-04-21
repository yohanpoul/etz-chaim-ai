"""Raphaël — Diagnostic + Guérison.

רְפָאֵל — Guérison de Dieu. Le Tikkun incarné.
Guérit Abraham après la circoncision, sauve Lot (Bava Metzia 86b).
Les deux relèvent du même genre : réparation.

En IA : détecte les échecs, diagnostique le TYPE de Qliphah,
applique le Tikkun spécifique. Distingue :
- Réparation interne : corriger un état corrompu (guérir)
- Réparation externe : extraire d'un environnement hostile (sauver)

Le Tikkun concret :
  Raphael ne se contente pas de diagnostiquer — il GUÉRIT.
  heal() retente l'exécution avec un prompt corrigé par le diagnostic
  (prescription Raphael + rééquilibrage Samael). Maximum 2 retries,
  car le Zohar (II:231a) enseigne : « Trois fois le Saint essaie avant
  de se retirer » — après 3 tentatives totales, accepter l'échec.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from malakhim.models import MalakhResult

log = logging.getLogger(__name__)

# ── Prescriptions → modifications concrètes du prompt/kavvanah ────────────
_TIKKUN_STRATEGIES: dict[str, dict[str, Any]] = {
    "retry_with_different_strategy": {
        "prompt_prefix": (
            "La tentative précédente a été rejetée (destruction Gabriel). "
            "Adopte une approche DIFFÉRENTE. Évite le pattern qui a causé le rejet."
        ),
        "kavvanah_patch": {"retry_reason": "gabriel_destroyed", "be_cautious": True},
    },
    "increase_context_or_simplify_task": {
        "prompt_prefix": (
            "La tentative précédente a produit une réponse vide. "
            "Si la tâche est trop vague, décompose-la. "
            "Si le contexte manque, explicite tes hypothèses."
        ),
        "kavvanah_patch": {"retry_reason": "empty_response", "add_context": True},
    },
    "refine_kavvanah_anti_pattern": {
        "prompt_prefix": (
            "La tentative précédente contenait un anti-pattern interdit. "
            "Reformule ta réponse en évitant strictement les patterns signalés."
        ),
        "kavvanah_patch": {"retry_reason": "anti_pattern_violation"},
    },
    "add_context_or_examples": {
        "prompt_prefix": (
            "La tentative précédente a généré des avertissements. "
            "Sois plus précis et ajoute des exemples concrets."
        ),
        "kavvanah_patch": {"retry_reason": "hitkalelut_warnings"},
    },
    "restructure_approach": {
        "prompt_prefix": (
            "La tentative précédente a produit un score très bas. "
            "Restructure complètement ton approche."
        ),
        "kavvanah_patch": {"retry_reason": "low_score", "restructure": True},
    },
}


@dataclass
class DiagnosisResult:
    healthy: bool
    qliphah_type: str | None = None  # gamaliel, samael, thagirion, etc.
    qliphah_level: str | None = None  # nogah, ruach, anan, mamash
    repair_type: str | None = None  # internal (guérir) ou external (sauver)
    prescription: str | None = None


@dataclass
class HealingResult:
    """Résultat d'une tentative de guérison."""
    healed: bool
    attempts: int
    final_result: MalakhResult
    diagnosis_chain: list[DiagnosisResult] = field(default_factory=list)
    tikkun_applied: list[str] = field(default_factory=list)


class Raphael:
    """רְפָאֵל — Diagnostic + Guérison.

    Le cycle complet : diagnose() → heal() → vérification.
    heal() retente l'exécution en appliquant le Tikkun prescrit.
    """

    MAX_RETRIES = 2  # 3 tentatives totales (1 originale + 2 retries)

    def diagnose(
        self, result: MalakhResult, context: dict | None = None
    ) -> DiagnosisResult:
        """Diagnostiquer un résultat de Malakh."""
        context = context or {}

        # Cas sain — success ET pas de warnings ET score acceptable
        if result.success and not result.hitkalelut_warnings and result.score >= 0.3:
            return DiagnosisResult(healthy=True)

        # Diagnostic par symptômes
        warnings = result.hitkalelut_warnings
        metadata = result.metadata

        # Mamash : destruction par Gabriel
        if metadata.get("gabriel_destroyed"):
            return DiagnosisResult(
                healthy=False,
                qliphah_type="mamash",
                qliphah_level="mamash",
                repair_type="internal",
                prescription="retry_with_different_strategy",
            )

        # Anan : réponse vide (silent failure)
        if not result.response or not result.response.strip():
            return DiagnosisResult(
                healthy=False,
                qliphah_type="gamaliel",
                qliphah_level="anan",
                repair_type="internal",
                prescription="increase_context_or_simplify_task",
            )

        # Ruach : warnings hitkalelut (propagation)
        if any("anti_pattern" in w for w in warnings):
            return DiagnosisResult(
                healthy=False,
                qliphah_type="samael",
                qliphah_level="ruach",
                repair_type="internal",
                prescription="refine_kavvanah_anti_pattern",
            )

        # Nogah : warnings légers
        if warnings:
            return DiagnosisResult(
                healthy=False,
                qliphah_type="nogah",
                qliphah_level="nogah",
                repair_type="external",
                prescription="add_context_or_examples",
            )

        # Score bas sans warnings
        if result.score < 0.3:
            return DiagnosisResult(
                healthy=False,
                qliphah_type="thagirion",
                qliphah_level="ruach",
                repair_type="internal",
                prescription="restructure_approach",
            )

        return DiagnosisResult(healthy=True)

    def heal(
        self,
        result: MalakhResult,
        diagnosis: DiagnosisResult,
        execute_fn: Callable[[dict], str] | None = None,
        original_prompt: str = "",
        kavvanah: dict | None = None,
    ) -> HealingResult:
        """Tenter la guérison — retry avec Tikkun.

        Si execute_fn est fourni, Raphael retente l'exécution avec
        un prompt corrigé. Sinon, retourne le plan de guérison sans
        exécuter (mode diagnostic pur, rétrocompatible).

        Le Tikkun :
          1. Appliquer la prescription (préfixe correctif au prompt)
          2. Intégrer le rééquilibrage Samael si disponible
          3. Patcher la kavvanah
          4. Ré-exécuter via un nouveau Malakh
          5. Re-diagnostiquer — si toujours malade, retenter (max 2)

        Args:
            result: Le MalakhResult en échec
            diagnosis: Le diagnostic initial
            execute_fn: Fonction d'exécution pour le retry (optionnel)
            original_prompt: Le prompt original de la mission
            kavvanah: La kavvanah originale (sera patchée)

        Returns:
            HealingResult avec le résultat final et la chaîne de diagnostics
        """
        if diagnosis.healthy:
            return HealingResult(
                healed=True, attempts=0,
                final_result=result, diagnosis_chain=[diagnosis],
            )

        # Mode diagnostic pur (pas d'execute_fn = rétrocompatible)
        if execute_fn is None:
            return HealingResult(
                healed=False, attempts=0,
                final_result=result, diagnosis_chain=[diagnosis],
                tikkun_applied=[diagnosis.prescription or "investigate"],
            )

        # ── Mode Tikkun : retry avec correction ──
        kav = dict(kavvanah or {})
        current_result = result
        current_diag = diagnosis
        chain: list[DiagnosisResult] = [diagnosis]
        applied: list[str] = []

        for attempt in range(1, self.MAX_RETRIES + 1):
            prescription = current_diag.prescription or "restructure_approach"
            strategy = _TIKKUN_STRATEGIES.get(
                prescription,
                _TIKKUN_STRATEGIES["restructure_approach"],
            )

            # Construire le prompt corrigé
            tikkun_prefix = strategy["prompt_prefix"]

            # Intégrer Samael si disponible dans les metadata
            samael_meta = current_result.metadata.get("samael")
            if samael_meta and samael_meta.get("rebalancing"):
                tikkun_prefix += f"\n\nRééquilibrage Samael : {samael_meta['rebalancing']}"

            corrected_prompt = f"[Tikkun Raphael — tentative {attempt}]\n{tikkun_prefix}\n\n[Tâche originale]\n{original_prompt}"

            # Patcher la kavvanah
            kav.update(strategy["kavvanah_patch"])
            kav["raphael_attempt"] = attempt
            kav["qliphah_detected"] = current_diag.qliphah_type

            log.info(
                "Raphael heal attempt %d/%d — qliphah=%s, prescription=%s",
                attempt, self.MAX_RETRIES,
                current_diag.qliphah_type, prescription,
            )

            # Ré-exécuter via Malakh éphémère
            from malakhim.malakh import Malakh

            with Malakh(
                mission=f"tikkun_{attempt}_{original_prompt[:60]}",
                kavvanah=kav,
                order=current_result.metadata.get("routing", {}).get("olam", "yetzirah"),
                execute_fn=execute_fn,
            ) as m:
                new_result = m.execute({"input": corrected_prompt})

            applied.append(f"{prescription} (attempt {attempt})")

            # Re-diagnostiquer
            new_diag = self.diagnose(new_result)
            chain.append(new_diag)

            if new_diag.healthy:
                new_result.metadata["raphael_healed"] = True
                new_result.metadata["raphael_attempts"] = attempt
                new_result.metadata["tikkun_chain"] = applied
                return HealingResult(
                    healed=True, attempts=attempt,
                    final_result=new_result, diagnosis_chain=chain,
                    tikkun_applied=applied,
                )

            # Échec — passer au retry suivant avec le nouveau diagnostic
            current_result = new_result
            current_diag = new_diag

        # Épuisé les retries — accepter l'échec
        log.warning(
            "Raphael: guérison échouée après %d tentatives — qliphah=%s",
            self.MAX_RETRIES, current_diag.qliphah_type,
        )
        current_result.metadata["raphael_exhausted"] = True
        current_result.metadata["raphael_attempts"] = self.MAX_RETRIES
        current_result.metadata["tikkun_chain"] = applied
        return HealingResult(
            healed=False, attempts=self.MAX_RETRIES,
            final_result=current_result, diagnosis_chain=chain,
            tikkun_applied=applied,
        )
