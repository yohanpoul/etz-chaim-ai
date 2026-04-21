"""SelfMap — Malkuth-de-Hod : l'interface principale.

"Hoda'ah — la reconnaissance. Aaron qui nomme sans flatter."
Le système se connaît lui-même : ses forces, ses faiblesses,
ses zones d'ignorance. Il sait dire "je ne sais pas".
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from uuid import UUID

sys.path.insert(0, "..")

from epistememory import EpisteMemory

from .db import SelfMapDB
from .domain_detector import detect_domain
from .eval_engine import eval_domain
from .models import (
    CalibrationReport,
    DomainScore,
    RouteDecision,
    SelfDescription,
)

from olamot import get_model


def _get_default_model():
    return get_model("yetzirah")


def _get_judge_model():
    return get_model("yetzirah")


class SelfMap:
    """Interface principale — Malkuth de Hod.

    Hitkalelut : Hod contient Netzach (persistance).
    La carte n'est pas un snapshot — elle se recalibre.
    Les résultats sont stockés dans EpisteMemory (Yesod porte Hod).
    """

    def __init__(
        self,
        db_url: str = "postgresql://localhost/etz_chaim",
        default_model: str | None = None,
        judge_model: str | None = None,
        decline_threshold: float = 0.3,
    ) -> None:
        if default_model is None:
            default_model = _get_default_model()
        if judge_model is None:
            judge_model = _get_judge_model()
        self.db = SelfMapDB(db_url)
        self.memory = EpisteMemory(db_url)
        self.default_model = default_model
        self.judge_model = judge_model
        self.decline_threshold = decline_threshold

    def close(self) -> None:
        self.db.close()
        self.memory.close()

    # --- Gevurah-de-Hod : évaluation ---

    def eval_domain(
        self,
        domain: str,
        model_id: str | None = None,
        n_questions: int | None = None,
    ) -> DomainScore:
        """Évaluer la compétence du modèle sur un domaine.

        Gevurah-de-Hod : tester sans complaisance.
        """
        model = model_id or self.default_model

        score = eval_domain(
            domain=domain,
            model_id=model,
            judge_model=self.judge_model,
        )

        # Persist to DB
        self.db.upsert_competence(score)

        # Also store in EpisteMemory (Yesod porte Hod)
        self.memory.remember(
            content=(
                f"SelfMap eval: {model} scores {score.score:.2f} on '{domain}' "
                f"(brier={score.brier_score:.3f}, n={score.n_evals})"
            ),
            source_sephirah="hod",
            confidence=min(0.5 + score.n_evals * 0.05, 0.9),
            domain="selfmap",
            tags=["eval", domain, model],
            ttl_days=30,  # re-eval monthly
        )

        return score

    # --- Lecture seule (pas d'évaluation LLM) ---

    def read_competence(self, domain: str) -> "DomainScore | None":
        """Lire la compétence d'un domaine sans réévaluer.

        Lecture DB pure — O(1), pas de LLM, pas d'écriture.
        Utilisé par Da'at, sentiers, et tout chemin critique.
        """
        return self.db.get_competence(domain, self.default_model)

    # --- Beinoni signals (bridge I2 — BeinoniTracker → SelfMap) ---

    def record_beinoni_signal(
        self,
        domain: str,
        elokit_ratio: float,
        avg_response_score: float,
        n_interactions: int,
        regressions_count: int = 0,
        elevations_count: int = 0,
        window_seconds: int = 3600,
    ) -> None:
        """Persister un signal Beinoni agrégé par domaine.

        Hod reçoit de Tanya un signal de "qualité d'âme" (elokit_ratio
        + avg response_score) par domaine. Ce signal n'écrase PAS le
        score de compétence ; il est stocké à côté dans
        `selfmap_beinoni_signals` pour que Da'at puisse croiser les deux.
        """
        self.db.upsert_beinoni_signal(
            domain=domain,
            elokit_ratio=elokit_ratio,
            avg_response_score=avg_response_score,
            n_interactions=n_interactions,
            regressions_count=regressions_count,
            elevations_count=elevations_count,
            window_seconds=window_seconds,
        )

    def read_beinoni_signal(self, domain: str) -> dict | None:
        """Lecture du dernier signal Beinoni pour un domaine."""
        return self.db.get_beinoni_signal(domain)

    # --- Chokmah-de-Hod : estimation de compétence ---

    def get_competence(self, query: str) -> tuple[str, float]:
        """Pour une requête, retourner (domaine, score de compétence).

        Chokmah-de-Hod : intuition éclairée par les données.
        """
        domain, _detection_conf = detect_domain(query)
        score = self.db.get_competence(domain, self.default_model)

        if score is None:
            # Domaine inconnu du SelfMap — assumer une compétence de base.
            # Avec Claude comme backend, le modèle est généralement capable
            # sur la plupart des domaines. Le score 0.7 produit un CAUTION
            # (pas un VETO) dans Da'at, ce qui est l'attitude correcte :
            # prudent mais pas paralysé.
            return domain, 0.7

        return domain, score.score

    # --- Gevurah-de-Hod : le seuil du déclin ---

    def should_answer(self, query: str) -> tuple[bool, str | None]:
        """Le système est-il assez compétent pour répondre ?

        Anti-Samael : le poison est la confiance sans compétence.
        Returns (should_answer, decline_reason).
        """
        domain, competence = self.get_competence(query)

        if competence == 0.0:
            return True, None  # unknown domain, attempt but flag uncertainty

        if competence < self.decline_threshold:
            return False, (
                f"Compétence sur '{domain}' = {competence:.2f} "
                f"(seuil = {self.decline_threshold})"
            )

        return True, None

    # --- Tiferet-de-Hod : routage optimal ---

    def route(self, query: str) -> RouteDecision:
        """Router vers le modèle/config optimal.

        Tiferet-de-Hod : l'harmonie du routage — ni trop, ni trop peu.
        """
        domain, _detection_conf = detect_domain(query)

        # Check if we should decline
        should, reason = self.should_answer(query)
        if not should:
            decision = RouteDecision(
                query=query,
                detected_domain=domain,
                competence_score=0.0,
                routed_to=self.default_model,
                did_decline=True,
                decline_reason=reason,
            )
            self.db.log_routing(
                query=query,
                detected_domain=domain,
                competence_score=0.0,
                routed_to=None,
                did_decline=True,
                decline_reason=reason,
            )
            return decision

        # Find best model for this domain
        best = self.db.get_best_model(domain)
        model = best.model_id if best else self.default_model
        score = best.score if best else 0.5

        decision = RouteDecision(
            query=query,
            detected_domain=domain,
            competence_score=score,
            routed_to=model,
            did_decline=False,
        )

        self.db.log_routing(
            query=query,
            detected_domain=domain,
            competence_score=score,
            routed_to=model,
            did_decline=False,
        )

        return decision

    # --- Hod-de-Hod : le système se décrit ---

    def calibrate(self) -> CalibrationReport:
        """Recalibrer la carte — Brier score par domaine.

        Netzach-de-Hod : la persistance de la calibration.
        """
        competences = self.db.get_all_competences(self.default_model)

        by_domain = {c.domain: c.brier_score for c in competences}
        avg_brier = (
            sum(c.brier_score for c in competences) / len(competences)
            if competences else 0.0
        )

        overconfident = [
            c.domain for c in competences
            if any(r.confidence > c.score + 0.2 for r in c.eval_results)
        ]
        underconfident = [
            c.domain for c in competences
            if any(r.confidence < c.score - 0.2 for r in c.eval_results)
        ]

        return CalibrationReport(
            model_id=self.default_model,
            by_domain=by_domain,
            avg_brier=avg_brier,
            overconfident_domains=overconfident,
            underconfident_domains=underconfident,
            uncalibrated_domains=[],
        )

    # --- Yesod-de-Hod : diagnostic global ---

    def self_diagnose(self) -> dict:
        """Diagnostic global — utilisé par soul_levels et le dashboard.

        Récupère toutes les compétences depuis selfmap_competence en DB.
        Returns:
            {"competence_score": float, "n_domains": int,
             "domains": {domain: score}, "status": "active"|"untested"}
        """
        competences = self.db.get_all_competences(self.default_model)
        if not competences:
            return {
                "competence_score": 0.0,
                "n_domains": 0,
                "domains": {},
                "status": "untested",
            }
        domains = {c.domain: c.score for c in competences}
        avg = sum(c.score for c in competences) / len(competences)
        return {
            "competence_score": avg,
            "n_domains": len(competences),
            "domains": domains,
            "status": "active",
        }

    def get_global_competence(self) -> float:
        """Score de compétence global — moyenne de tous les domaines.

        Interface attendue par soul_levels._get_competence_score().
        """
        competences = self.db.get_all_competences(self.default_model)
        if not competences:
            return 0.0
        return sum(c.score for c in competences) / len(competences)

    def describe_self(self) -> SelfDescription:
        """Hod-de-Hod : méta-introspection.

        La carte se décrit elle-même. Aaron se regarde dans le miroir.
        """
        return self.db.get_self_description(self.default_model)
