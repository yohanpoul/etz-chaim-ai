"""CausalEngine — le cœur de Binah.

בִּינָה — BeiN (בין) = entre = distinguer.
Binah met des frontières entre les choses.

CausalEngine orchestre toutes les composantes :
  - DAGBuilder : construire des DAGs causaux
  - ConfounderDetector : détecter les variables confondantes
  - EvidenceScorer : scorer le niveau de preuve
  - PearlCriteria : classifier selon Pearl
  - LanguageEnforcer : forcer le langage approprié

Connexions sephirothiques :
  Binah ← Da'at (SelfModel sait quand l'analyse causale est fiable)
  Binah ← Yesod (EpisteMemory fournit les données)
  Binah ← Tiferet (DissensuEngine quand les causes se contredisent)
  Binah → Chokmah (future InsightForge, intuitions causales)

Anti-Satariel : jamais de faux patterns (4 niveaux).
"""

from __future__ import annotations

from causalengine.confounder_detector import ConfounderDetector
from causalengine.dag_builder import DAGBuilder
from causalengine.db import CausalDB
from causalengine.evidence_scorer import EvidenceScorer
from causalengine.language_enforcer import LanguageEnforcer
from causalengine.models import (
    CausalAssessment,
    CausalClaim,
    CausalEdge,
    CausalGraph,
    CausalNode,
    Confounder,
    DirectionAssessment,
    LanguageCorrection,
)
from causalengine.pearl_criteria import PearlCriteria
from omer import get_param

# Omer de Binah — 7 paramètres de calibration (hardcoded defaults as fallback)
DEFAULT_MAX_CONFOUNDERS = 10                    # Chesed-dans-Binah
DEFAULT_MIN_EVIDENCE = "probable_causation"      # Gevurah-dans-Binah
DEFAULT_CONTRADICTING_CAUSES = "dissensus"       # Tiferet-dans-Binah
DEFAULT_DAG_UPDATE = "on_new_evidence"           # Netzach-dans-Binah
DEFAULT_EXPOSE_UNCERTAINTY = True                # Hod-dans-Binah
DEFAULT_PERSIST_ALL = True                       # Yesod-dans-Binah
DEFAULT_LANGUAGE_STRICTNESS = "strict"           # Malkuth-dans-Binah

_MODULE = "causalengine"
_UNSET = object()


class CausalEngine:
    """Binah — distinguer corrélation de causalité.

    Orchestre la construction de DAGs, la détection de confounders,
    le scoring de preuve, la classification Pearl, et l'enforcement
    du langage approprié.
    """

    def __init__(
        self,
        db_url: str,
        memory=None,
        dissensus=None,
        selfmodel=None,
        max_confounders: int = _UNSET,
        min_evidence: str = _UNSET,
        handle_contradicting_causes: str = _UNSET,
        dag_update_frequency: str = _UNSET,
        expose_uncertainty: bool = _UNSET,
        persist_all_dags: bool = _UNSET,
        language_strictness: str = _UNSET,
    ):
        self.db = CausalDB(db_url)
        self.memory = memory          # Yesod — EpisteMemory
        self.dissensus = dissensus    # Tiferet — DissensuEngine
        self.selfmodel = selfmodel    # Da'at — SelfModel

        # Omer — DB overrides when caller uses default, explicit values preserved.
        self.max_confounders = max_confounders if max_confounders is not _UNSET else get_param(_MODULE, "max_confounders", DEFAULT_MAX_CONFOUNDERS)
        self.min_evidence = min_evidence if min_evidence is not _UNSET else get_param(_MODULE, "min_evidence", DEFAULT_MIN_EVIDENCE)
        self.handle_contradicting_causes = handle_contradicting_causes if handle_contradicting_causes is not _UNSET else get_param(_MODULE, "handle_contradicting_causes", DEFAULT_CONTRADICTING_CAUSES)
        self.dag_update_frequency = dag_update_frequency if dag_update_frequency is not _UNSET else get_param(_MODULE, "dag_update_frequency", DEFAULT_DAG_UPDATE)
        self.expose_uncertainty = expose_uncertainty if expose_uncertainty is not _UNSET else get_param(_MODULE, "expose_uncertainty", DEFAULT_EXPOSE_UNCERTAINTY)
        self.persist_all_dags = persist_all_dags if persist_all_dags is not _UNSET else get_param(_MODULE, "persist_all_dags", DEFAULT_PERSIST_ALL)
        self.language_strictness = language_strictness if language_strictness is not _UNSET else get_param(_MODULE, "language_strictness", DEFAULT_LANGUAGE_STRICTNESS)

        # Composants (use resolved Omer values)
        self.dag_builder = DAGBuilder()
        self.confounder_detector = ConfounderDetector(max_confounders=self.max_confounders)
        self.evidence_scorer = EvidenceScorer()
        self.pearl = PearlCriteria()
        self.language = LanguageEnforcer(strictness=self.language_strictness)

    def build_causal_graph(
        self,
        name: str,
        nodes: list[CausalNode],
        edges: list[CausalEdge],
        domain: str = "",
        description: str = "",
        check_confounders: bool = True,
    ) -> CausalGraph:
        """Construire un DAG causal validé.

        1. Construire le graphe (acyclicité vérifiée)
        2. Détecter les confounders pour chaque edge
        3. Scorer le niveau de preuve
        4. Persister si configuré
        """
        # Construire et valider
        graph = self.dag_builder.build(
            name=name,
            nodes=nodes,
            edges=edges,
            domain=domain,
            description=description,
        )

        # Détecter les confounders pour chaque edge si demandé
        if check_confounders:
            all_confounders: list[Confounder] = []
            for edge in graph.edges:
                confs = self.confounder_detector.detect(
                    cause=edge.source,
                    effect=edge.target,
                    domain=domain,
                )
                all_confounders.extend(confs)
            graph.confounders_checked = True

        # Niveau Pearl du graphe
        graph.evidence_level = self.pearl.classify_graph(graph)

        # Persister
        if self.persist_all_dags:
            graph = self.db.save_graph(graph)

        return graph

    def check_claim(
        self,
        cause: str,
        effect: str,
        domain: str = "",
        direction: DirectionAssessment | None = None,
    ) -> CausalAssessment:
        """Vérifier une affirmation causale — le cœur de Binah.

        1. Créer le claim
        2. Détecter les confounders
        3. Vérifier la direction
        4. Scorer le niveau de preuve
        5. Classifier selon Pearl
        6. Vérifier le langage
        7. Générer les warnings
        """
        # Détecter les confounders
        confounders = self.confounder_detector.detect(cause, effect, domain)

        # Vérifier la direction si non fournie
        if direction is None:
            direction = self.verify_direction(cause, effect)

        # Créer le claim de base
        claim = CausalClaim(
            cause=cause,
            effect=effect,
            evidence_level="correlation_only",
        )

        # Scorer le niveau de preuve
        evidence_level = self.evidence_scorer.score(
            claim, confounders, direction,
        )
        claim.evidence_level = evidence_level

        # Direction
        claim.direction_verified = (
            direction.verdict in ("forward", "bidirectional")
            and direction.forward_plausibility >= 0.6
        )
        claim.reverse_plausible = direction.verdict in ("reverse", "bidirectional")

        # Confounders
        control_status = self.confounder_detector.assess_control(confounders)
        claim.confounders_controlled = control_status["all_controlled"]
        claim.known_confounders = [c.confounder_name for c in confounders]

        # Confidence
        claim.confidence = self.evidence_scorer.compute_confidence(
            evidence_level, confounders, direction,
        )

        # Pearl level
        pearl_level = self.pearl.classify_claim(claim)

        # Langage approprié
        appropriate = self.language.appropriate_language(evidence_level)
        claim.appropriate_language = appropriate[0] if appropriate else ""

        # Correction de langage
        sample_text = f"{cause} causes {effect}"
        corrections = self.language.check(sample_text, evidence_level)
        language_correction = corrections[0] if corrections else None

        # Warnings — Anti-Satariel
        warnings = self._generate_warnings(
            claim, confounders, direction, control_status,
        )

        # Persister
        if self.persist_all_dags:
            claim = self.db.save_claim(claim)
            for conf in confounders:
                conf.claim_id = claim.id
                self.db.save_confounder(conf)

        return CausalAssessment(
            claim=claim,
            confounders=confounders,
            direction=direction,
            pearl_level=pearl_level,
            language_correction=language_correction,
            warnings=warnings,
        )

    def detect_confounders(
        self,
        cause: str,
        effect: str,
        domain: str = "",
    ) -> list[Confounder]:
        """Détecter les variables confondantes possibles."""
        return self.confounder_detector.detect(cause, effect, domain)

    def enrich_claim_confounders(
        self,
        claim: CausalClaim,
        **llm_kwargs,
    ) -> dict:
        """Enrichir un claim existant avec des confounders contextuels (LLM).

        1. Appelle detect_contextual pour obtenir des confounders LLM
        2. Sauvegarde les nouveaux confounders en DB
        3. Réévalue le evidence_level du claim
        4. Met à jour le claim en DB

        Returns:
            {"new_confounders": int, "evidence_changed": bool,
             "old_level": str, "new_level": str}
        """
        if not claim.id:
            return {"new_confounders": 0, "evidence_changed": False}

        # Extraire un domaine depuis les confounders existants
        existing = self.db.get_confounders(claim.id)
        domain = ""
        for c in existing:
            if c.confounder_domain and c.confounder_domain != "universal":
                domain = c.confounder_domain
                break

        # Détection contextuelle LLM
        contextual = self.confounder_detector.detect_contextual(
            cause=claim.cause,
            effect=claim.effect,
            domain=domain,
            **llm_kwargs,
        )

        if not contextual:
            return {"new_confounders": 0, "evidence_changed": False}

        # Dédupliquer avec les existants
        existing_names = {c.confounder_name.lower() for c in existing}
        new_confs: list[Confounder] = []
        for c in contextual:
            if c.confounder_name.lower() not in existing_names:
                c.claim_id = claim.id
                saved = self.db.save_confounder(c)
                new_confs.append(saved)

        # Mettre à jour known_confounders du claim
        old_level = claim.evidence_level
        if new_confs:
            all_names = list(existing_names | {c.confounder_name for c in new_confs})
            claim.known_confounders = all_names

            # Réévaluer : si on a des confounders contextuels identifiés,
            # le claim peut passer de correlation_only à probable_causation
            # si les confounders de haute plausibilité sont peu nombreux
            all_confounders = existing + new_confs
            control = self.confounder_detector.assess_control(all_confounders)
            high_uncontrolled = control.get("high_plausibility_uncontrolled", [])

            # Si aucun confounder de haute plausibilité non contrôlé,
            # et direction vérifiée, on peut élever
            if not high_uncontrolled and claim.direction_verified:
                claim.evidence_level = "probable_causation"
                claim.confounders_controlled = True

            # Recalculer confidence
            direction = DirectionAssessment(
                verdict="forward" if claim.direction_verified else "indeterminate",
                forward_plausibility=0.6 if claim.direction_verified else 0.5,
                reverse_plausibility=0.5,
            )
            claim.confidence = self.evidence_scorer.compute_confidence(
                claim.evidence_level, all_confounders, direction,
            )

            # Langage approprié
            appropriate = self.language.appropriate_language(claim.evidence_level)
            claim.appropriate_language = appropriate[0] if appropriate else ""

            self.db.update_claim(claim)

        return {
            "new_confounders": len(new_confs),
            "evidence_changed": old_level != claim.evidence_level,
            "old_level": old_level,
            "new_level": claim.evidence_level,
        }

    def run_confounder_enrichment(
        self,
        batch_size: int = 20,
        **llm_kwargs,
    ) -> dict:
        """Enrichir un batch de claims sans confounders contextuels.

        Appelé par le daemon quotidiennement.
        """
        claims = self.db.get_claims_without_contextual_confounders(limit=batch_size)
        report = {
            "claims_processed": 0,
            "total_new_confounders": 0,
            "evidence_elevated": 0,
            "errors": 0,
        }

        for claim in claims:
            try:
                result = self.enrich_claim_confounders(claim, **llm_kwargs)
                report["claims_processed"] += 1
                report["total_new_confounders"] += result["new_confounders"]
                if result["evidence_changed"]:
                    report["evidence_elevated"] += 1
            except Exception as e:
                report["errors"] += 1
                import logging
                logging.getLogger("etz-daemon").warning(
                    "Confounder enrichment error for claim %s: %s",
                    claim.id, e,
                )

        return report

    def recalibrate_all_claims(self, batch_size: int = 100) -> dict:
        """Recalibrer la confiance de tous les claims existants.

        Recharge les confounders pour chaque claim et recalcule
        la confiance avec la formule actuelle du scorer.
        Utile après un changement de formule ou d'Omer.
        """
        import logging
        log = logging.getLogger("etz-daemon")

        claims = self.db.get_claims(limit=10000)
        report = {"total": len(claims), "recalibrated": 0, "changed": 0, "errors": 0}

        for claim in claims:
            try:
                confounders = []
                if claim.id:
                    confounders = self.db.get_confounders(claim.id)

                direction = DirectionAssessment(
                    verdict="forward" if claim.direction_verified else "indeterminate",
                    forward_plausibility=0.6 if claim.direction_verified else 0.5,
                    reverse_plausibility=0.5,
                )

                old_confidence = claim.confidence
                claim.confidence = self.evidence_scorer.compute_confidence(
                    claim.evidence_level, confounders, direction,
                )

                if claim.confidence != old_confidence:
                    self.db.update_claim(claim)
                    report["changed"] += 1

                report["recalibrated"] += 1
            except Exception as e:
                report["errors"] += 1
                log.warning("Recalibration error for claim %s: %s", claim.id, e)

        return report

    def verify_direction(self, a: str, b: str) -> DirectionAssessment:
        """Vérifier la direction causale : A→B ? B→A ? Les deux ?

        Heuristique en 3 étapes (sans appel LLM) :
        1. Marqueurs causaux linguistiques (cause→, provoque, entraîne)
        2. Asymétrie de longueur/spécificité (le plus spécifique = effet)
        3. Données DB si disponibles (claims existants avec confiance)

        Quand rien ne distingue → indeterminate (honnêteté > faux verdict).
        """
        a_lower = a.lower()
        b_lower = b.lower()

        # ── Heuristique 1 : marqueurs causaux dans les textes ──
        forward_markers = [
            "provoque", "entraîne", "cause", "produit", "génère",
            "mène à", "conduit à", "résulte en", "→",
            "causes", "leads to", "produces", "generates",
        ]
        reverse_markers = [
            "résulte de", "est causé par", "découle de", "vient de",
            "caused by", "results from", "due to",
        ]

        forward_score = sum(1 for m in forward_markers if m in a_lower)
        reverse_score = sum(1 for m in reverse_markers if m in a_lower)
        forward_score += sum(1 for m in reverse_markers if m in b_lower)
        reverse_score += sum(1 for m in forward_markers if m in b_lower)

        # ── Heuristique 2 : asymétrie de spécificité ──
        # Un effet est souvent plus spécifique/long que sa cause
        len_ratio = len(b) / max(len(a), 1)
        if len_ratio > 1.5:
            forward_score += 1  # B plus long → probablement l'effet
        elif len_ratio < 0.67:
            reverse_score += 1

        # ── Heuristique 3 : claims existants en DB ──
        try:
            existing = self.db.search_claims(a[:100], limit=5)
            for claim in existing:
                if b_lower[:30] in claim.effect.lower():
                    forward_score += 2
                elif b_lower[:30] in claim.cause.lower():
                    reverse_score += 2
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # ── Décision ──
        total = forward_score + reverse_score
        if total == 0:
            return DirectionAssessment(
                verdict="indeterminate",
                forward_plausibility=0.5,
                reverse_plausibility=0.5,
                reasoning=f"No directional evidence between '{a[:50]}' and '{b[:50]}'",
            )

        fwd_p = round(forward_score / max(total, 1), 2)
        rev_p = round(reverse_score / max(total, 1), 2)

        if fwd_p >= 0.7:
            verdict = "forward"
        elif rev_p >= 0.7:
            verdict = "reverse"
        elif abs(fwd_p - rev_p) < 0.2:
            verdict = "bidirectional"
        else:
            verdict = "indeterminate"

        return DirectionAssessment(
            verdict=verdict,
            forward_plausibility=fwd_p,
            reverse_plausibility=rev_p,
            reasoning=(
                f"Heuristic: {forward_score} forward markers, "
                f"{reverse_score} reverse markers (total={total})"
            ),
        )

    def enforce_language(
        self,
        text: str,
        evidence_level: str = "correlation_only",
    ) -> tuple[str, list[LanguageCorrection]]:
        """Corriger le langage causal d'un texte."""
        return self.language.enforce(text, evidence_level)

    def pearl_level(self, claim: CausalClaim) -> str:
        """Classifier un claim selon Pearl."""
        return self.pearl.classify_claim(claim)

    def self_diagnose(self, **kwargs) -> dict:
        """Auto-diagnostic — les 4 niveaux de Satariel.

        Vérifie les 10 derniers claims pour les anti-patterns :
          Nogah : hedging sans vérification
          Ruach : corrélation présentée comme causalité
          Anan : pattern dans du bruit (confiance haute, preuve basse)
          Mamash : causalité inversée (direction non vérifiée)
        """
        claims = self.db.get_claims(limit=10)
        if not claims:
            return {"level": "healthy", "issues": []}

        issues: list[str] = []

        for claim in claims:
            confounders = []
            if claim.id:
                confounders = self.db.get_confounders(claim.id)

            # Nogah — hedging sans vérification
            if (
                claim.evidence_level == "correlation_only"
                and not claim.known_confounders
            ):
                issues.append(
                    f"Satariel-Nogah: '{claim.cause}→{claim.effect}' — "
                    "no confounders checked (hedging without verification)"
                )

            # Ruach — corrélation comme causalité
            if (
                claim.evidence_level == "correlation_only"
                and claim.appropriate_language
                and any(
                    w in claim.appropriate_language.lower()
                    for w in ("causes", "cause", "provoque", "entraîne")
                )
            ):
                issues.append(
                    f"Satariel-Ruach: '{claim.cause}→{claim.effect}' — "
                    "causal language used for correlation-only claim"
                )

            # Anan — confiance haute, preuve basse
            if (
                claim.evidence_level == "correlation_only"
                and claim.confidence >= 0.7
            ):
                issues.append(
                    f"Satariel-Anan: '{claim.cause}→{claim.effect}' — "
                    f"high confidence ({claim.confidence}) with correlation-only evidence"
                )

            # Mamash — direction non vérifiée
            if (
                claim.evidence_level in ("probable_causation", "demonstrated_causation")
                and not claim.direction_verified
            ):
                issues.append(
                    f"Satariel-Mamash: '{claim.cause}→{claim.effect}' — "
                    "causal claim without verified direction"
                )

        # Déterminer le niveau
        if not issues:
            level = "healthy"
        elif any("Mamash" in i for i in issues):
            level = "mamash"
        elif any("Anan" in i for i in issues):
            level = "anan"
        elif any("Ruach" in i for i in issues):
            level = "ruach"
        else:
            level = "nogah"

        return {"level": level, "issues": issues}

    def report(self) -> str:
        """Rapport lisible — Malkuth de Binah."""
        claims = self.db.get_claims(limit=10)
        graphs = self.db.get_graphs(limit=5)
        diag = self.self_diagnose()

        lines = [
            "=== CausalEngine Report (Binah) ===",
            f"Recent claims: {len(claims)}",
            f"Recent graphs: {len(graphs)}",
        ]

        for claim in claims:
            confounders = []
            if claim.id:
                confounders = self.db.get_confounders(claim.id)
            pearl = self.pearl.classify_claim(claim)
            dir_mark = "✓" if claim.direction_verified else "✗"
            conf_mark = f"{len(confounders)} confounders"
            lines.append(
                f"  [{claim.evidence_level}] {claim.cause} → {claim.effect} "
                f"(Pearl: {pearl}, dir: {dir_mark}, {conf_mark}, "
                f"conf: {claim.confidence})"
            )

        for graph in graphs:
            lines.append(
                f"  [DAG] {graph.name} — {len(graph.nodes)} nodes, "
                f"{len(graph.edges)} edges, Pearl: {graph.evidence_level}"
            )

        lines.append(f"\nSelf-diagnosis: {diag['level']}")
        if diag["issues"]:
            lines.append("Issues:")
            for issue in diag["issues"]:
                lines.append(f"  - {issue}")

        if self.expose_uncertainty:
            lines.append("\nUncertainty exposure: enabled")
            uncertain = [c for c in claims if c.confidence < 0.5]
            if uncertain:
                lines.append(f"Low-confidence claims: {len(uncertain)}")

        return "\n".join(lines)

    def _generate_warnings(
        self,
        claim: CausalClaim,
        confounders: list[Confounder],
        direction: DirectionAssessment,
        control_status: dict,
    ) -> list[str]:
        """Générer les warnings Anti-Satariel."""
        warnings: list[str] = []

        # Nogah — hedging sans vérification
        if not confounders:
            warnings.append(
                "Anti-Satariel Nogah: no confounders identified — "
                "claim cannot be elevated above correlation"
            )

        # Ruach — corrélation comme causalité
        if (
            claim.evidence_level == "correlation_only"
            and claim.confidence >= 0.7
        ):
            warnings.append(
                "Anti-Satariel Anan: high confidence on correlation-only claim — "
                "verify this is not a false pattern"
            )

        # Mamash — direction non vérifiée
        if direction.verdict == "indeterminate":
            warnings.append(
                "Anti-Satariel Mamash: direction not verified — "
                f"'{claim.cause}' might not cause '{claim.effect}', "
                "reverse causation is possible"
            )

        # Confounders à haute plausibilité non contrôlés
        high_uncontrolled = control_status.get("high_plausibility_uncontrolled", [])
        if high_uncontrolled:
            warnings.append(
                f"High-plausibility confounders uncontrolled: "
                f"{', '.join(high_uncontrolled)}"
            )

        return warnings
