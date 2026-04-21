"""EvidenceElevator — cristallisation des claims causaux.

בִּינָה ne se contente pas de distinguer — elle ÉLÈVE.
Le claim commence à correlation_only et monte quand les preuves
convergent depuis plusieurs modules du système :

  correlation_only → observed_association → probable_causation → demonstrated_causation

Chaque élévation est GAGNÉE par des critères croisés :
- Hitbonenut (questions explorées)
- InsightForge (insights candidats)
- CausalTreeBuilder (chaînes causales)
- DissensuEngine (conclusions consolidées)

Anti-Satariel : un claim ne monte JAMAIS par défaut.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict

from causalengine.db import CausalDB
from causalengine.evidence_scorer import EvidenceScorer
from causalengine.language_enforcer import LanguageEnforcer
from causalengine.models import (
    CausalClaim,
    DirectionAssessment,
    EVIDENCE_RANK,
)

log = logging.getLogger("etz-daemon")

# French + common stopwords to ignore in keyword extraction
_STOPWORDS = frozenset(
    "le la les un une des de du dans par pour en sur au aux "
    "est sont être avoir fait faire plus avec sans qui que quel quelle quels quelles "
    "comment quoi quand pourquoi entre cette cet ces son ses leur leurs "
    "peut être bien très tout tous toute toutes "
    "the a an and or is are was were to of in on at by for with".split()
)

# Domain-specific high-frequency words that match everything
_DOMAIN_STOPWORDS = frozenset(
    "hitbonenut insight kabbale connexions existent approche "
    "filtrage stricts critères trop envisager graduée "
    "structure elle connaissances base patterns information "
    "aussi existe questions question domain general".split()
)

# Minimum word length for keyword extraction
_MIN_WORD_LEN = 4


def _extract_keywords(text: str) -> set[str]:
    """Extraire les mots-clés significatifs d'un texte.

    Gère les apostrophes françaises : "l'arbre" → "arbre".
    """
    # Split on non-alpha, keeping accented chars
    raw = re.findall(r"[a-zA-ZÀ-ÿ]+", text.lower())
    # Also handle French contractions: l', d', s', n', qu'
    expanded = []
    for w in raw:
        if w in ("l", "d", "s", "n", "qu", "j", "c"):
            continue  # skip French article/preposition fragments
        expanded.append(w)

    return {
        w for w in expanded
        if len(w) >= _MIN_WORD_LEN
        and w not in _STOPWORDS
        and w not in _DOMAIN_STOPWORDS
    }


def _keyword_overlap(kw_a: set[str], kw_b: set[str]) -> float:
    """Jaccard similarity entre deux ensembles de mots-clés."""
    if not kw_a or not kw_b:
        return 0.0
    intersection = kw_a & kw_b
    union = kw_a | kw_b
    return len(intersection) / len(union)


class EvidenceElevator:
    """Élève les claims causaux au-dessus de correlation_only.

    Trois niveaux d'élévation, chacun avec des critères croisés :

    OBSERVED_ASSOCIATION :
      - Le claim apparaît dans 2+ contextes (cause/effect partagés)
      - OU ses termes apparaissent dans des questions Hitbonenut
      - ET confiance >= 0.3

    PROBABLE_CAUSATION :
      - Peu de confounders contextuels (< 3 par claim)
      - ET fait partie d'une chaîne causale (TreeBuilder)
      - ET confiance recalculée >= 0.5

    DEMONSTRATED_CAUSATION :
      - Termes testés par Hitbonenut avec score > 0.7
      - ET cohérent avec les synthèses DissensuEngine
      - ET confiance recalculée >= 0.7
    """

    def __init__(
        self,
        db: CausalDB,
        scorer: EvidenceScorer | None = None,
        language: LanguageEnforcer | None = None,
    ):
        self.db = db
        self.scorer = scorer or EvidenceScorer()
        self.language = language or LanguageEnforcer()

    def elevate_claims(self, batch_size: int = 50) -> dict:
        """Pipeline complet d'élévation — cascading.

        1. Charger les données de contexte (hitbonenut, insights, tree, dissensus)
        2. Élever correlation_only → observed_association
        3. Recalculer confidence
        4. Élever observed_association → probable_causation
        5. Recalculer confidence
        6. Élever probable_causation → demonstrated_causation
        7. Recalculer confidence
        8. Persister en batch

        Returns:
            Report with before/after counts.
        """
        report = {
            "total_claims": 0,
            "before": {},
            "after": {},
            "elevated_to_observed": 0,
            "elevated_to_probable": 0,
            "elevated_to_demonstrated": 0,
            "errors": 0,
        }

        # Load all claims
        claims = self.db.get_all_claims()
        report["total_claims"] = len(claims)
        if not claims:
            return report

        # Count before
        for c in claims:
            report["before"][c.evidence_level] = (
                report["before"].get(c.evidence_level, 0) + 1
            )

        # Load context data
        ctx = self._load_context()

        # Process in batches
        updates: list[tuple[str, float, str, str]] = []  # (level, conf, lang, id)
        processed = 0

        for claim in claims:
            if processed >= batch_size and batch_size > 0:
                break
            try:
                new_level, new_conf = self._evaluate_claim(claim, ctx)
                if new_level != claim.evidence_level or new_conf != claim.confidence:
                    appropriate = self.language.appropriate_language(new_level)
                    lang = appropriate[0] if appropriate else ""
                    updates.append((new_level, new_conf, lang, str(claim.id)))

                    if (
                        EVIDENCE_RANK.get(new_level, 0)
                        > EVIDENCE_RANK.get(claim.evidence_level, 0)
                    ):
                        if new_level == "observed_association":
                            report["elevated_to_observed"] += 1
                        elif new_level == "probable_causation":
                            report["elevated_to_probable"] += 1
                        elif new_level == "demonstrated_causation":
                            report["elevated_to_demonstrated"] += 1

                processed += 1
            except Exception as e:
                report["errors"] += 1
                log.warning("Elevator error for claim %s: %s", claim.id, e)

        # Persist
        if updates:
            self.db.bulk_update_evidence(updates)
            log.info(
                "EvidenceElevator: %d claims updated (%d→observed, %d→probable, %d→demonstrated)",
                len(updates),
                report["elevated_to_observed"],
                report["elevated_to_probable"],
                report["elevated_to_demonstrated"],
            )

        # Count after
        claims_after = self.db.get_all_claims()
        for c in claims_after:
            report["after"][c.evidence_level] = (
                report["after"].get(c.evidence_level, 0) + 1
            )

        return report

    def _load_context(self) -> dict:
        """Charger toutes les données de contexte pour l'élévation."""
        ctx: dict = {}

        # 1. Cause/effect frequencies (multi-context detection)
        ctx["cause_freq"] = self.db.get_cause_frequencies()
        ctx["effect_freq"] = self.db.get_effect_frequencies()

        # 2. Hitbonenut questions avec scores
        ctx["hitbonenut"] = self._load_hitbonenut()

        # 3. Candidate insights
        ctx["insights"] = self._load_insights()

        # 4. Causal chain nodes (from TreeBuilder graph)
        ctx["chain_nodes"] = self._load_chain_nodes()

        # 5. Dissensus conclusions
        ctx["dissensus"] = self._load_dissensus()

        log.info(
            "EvidenceElevator context: %d hitbonenut (score>0.7: %d), "
            "%d insights, %d chain_nodes, %d dissensus",
            len(ctx["hitbonenut"]["all"]),
            len(ctx["hitbonenut"]["high_score"]),
            len(ctx["insights"]),
            len(ctx["chain_nodes"]),
            len(ctx["dissensus"]),
        )

        return ctx

    def _load_hitbonenut(self) -> dict:
        """Charger les questions Hitbonenut avec mots-clés pré-calculés."""
        result: dict = {"all": [], "high_score": [], "keywords_all": set(), "keywords_high": set()}
        try:
            with self.db._cursor() as cur:
                cur.execute(
                    "SELECT question, score, domain FROM hitbonenut_questions"
                )
                for question, score, domain in cur.fetchall():
                    kw = _extract_keywords(question)
                    entry = {"question": question, "score": score, "domain": domain, "keywords": kw}
                    result["all"].append(entry)
                    result["keywords_all"].update(kw)
                    if score and score >= 0.7:
                        result["high_score"].append(entry)
                        result["keywords_high"].update(kw)
        except Exception as e:
            log.warning("EvidenceElevator: hitbonenut load error: %s", e)
        return result

    def _load_insights(self) -> list[dict]:
        """Charger les insights candidats avec mots-clés."""
        result: list[dict] = []
        try:
            with self.db._cursor() as cur:
                cur.execute(
                    "SELECT description, confidence, domain FROM candidate_insights "
                    "WHERE confidence >= 0.3"
                )
                for desc, conf, domain in cur.fetchall():
                    kw = _extract_keywords(desc)
                    result.append({"description": desc, "confidence": conf, "domain": domain, "keywords": kw})
        except Exception as e:
            log.warning("EvidenceElevator: insights load error: %s", e)
        return result

    def _load_chain_nodes(self) -> set[str]:
        """Nœuds qui apparaissent dans des chaînes causales (cause ET effect)."""
        try:
            with self.db._cursor() as cur:
                cur.execute(
                    """SELECT DISTINCT cause FROM causal_claims
                       INTERSECT
                       SELECT DISTINCT effect FROM causal_claims"""
                )
                return {row[0] for row in cur.fetchall()}
        except Exception as e:
            log.warning("EvidenceElevator: chain nodes load error: %s", e)
            return set()

    def _load_dissensus(self) -> list[dict]:
        """Charger les conclusions DissensuEngine avec mots-clés."""
        result: list[dict] = []
        try:
            with self.db._cursor() as cur:
                cur.execute(
                    "SELECT content, confidence, domain FROM dissensuengine_conclusions"
                )
                for content, conf, domain in cur.fetchall():
                    kw = _extract_keywords(content)
                    result.append({"content": content, "confidence": conf, "domain": domain, "keywords": kw})
        except Exception as e:
            log.warning("EvidenceElevator: dissensus load error: %s", e)
        return result

    def _evaluate_claim(self, claim: CausalClaim, ctx: dict) -> tuple[str, float]:
        """Évaluer un claim et déterminer son niveau maximal.

        Cascading : on vérifie d'abord observed, puis probable, puis demonstrated.
        À chaque palier, on recalcule la confidence AU NIVEAU CIBLE — le seuil
        de confiance s'applique à la confidence recalculée au nouveau niveau,
        pas à l'ancien. Sinon le cascading est impossible (la base de
        correlation_only = 0.35 ne peut jamais atteindre 0.5).
        """
        level = claim.evidence_level
        claim_kw = _extract_keywords(claim.cause + " " + claim.effect)

        # --- Observed Association ---
        if EVIDENCE_RANK.get(level, 0) < EVIDENCE_RANK["observed_association"]:
            if self._check_observed(claim, claim_kw, ctx):
                candidate_conf = self._recalculate_confidence(claim, "observed_association")
                if candidate_conf >= 0.3:
                    level = "observed_association"

        # --- Probable Causation ---
        if (
            EVIDENCE_RANK.get(level, 0) >= EVIDENCE_RANK["observed_association"]
            and EVIDENCE_RANK.get(level, 0) < EVIDENCE_RANK["probable_causation"]
        ):
            if self._check_probable(claim, claim_kw, ctx):
                candidate_conf = self._recalculate_confidence(claim, "probable_causation")
                if candidate_conf >= 0.5:
                    level = "probable_causation"

        # --- Demonstrated Causation ---
        if (
            EVIDENCE_RANK.get(level, 0) >= EVIDENCE_RANK["probable_causation"]
            and EVIDENCE_RANK.get(level, 0) < EVIDENCE_RANK["demonstrated_causation"]
        ):
            if self._check_demonstrated(claim, claim_kw, ctx):
                candidate_conf = self._recalculate_confidence(claim, "demonstrated_causation")
                if candidate_conf >= 0.7:
                    level = "demonstrated_causation"

        # Final confidence at the determined level
        conf = self._recalculate_confidence(claim, level)
        return level, conf

    def _check_observed(
        self, claim: CausalClaim, claim_kw: set[str], ctx: dict,
    ) -> bool:
        """Vérifier les critères d'OBSERVED_ASSOCIATION.

        1. Le claim apparaît dans 2+ contextes (cause partagée avec d'autres effects)
           OU ses mots-clés overlappent avec des questions Hitbonenut (Jaccard >= 0.10)
           OU ses mots-clés overlappent avec des insights (Jaccard >= 0.10)
        2. ET confiance actuelle >= 0.3
        """
        if claim.confidence < 0.3:
            return False

        if not claim_kw:
            return False

        # Multi-context : même cause apparaît dans 2+ claims (différents effects)
        cause_count = ctx["cause_freq"].get(claim.cause, 0)
        if cause_count >= 2:
            return True

        # Hitbonenut overlap — per-question Jaccard
        for hq in ctx["hitbonenut"]["all"]:
            if _keyword_overlap(claim_kw, hq["keywords"]) >= 0.10:
                return True

        # Insight overlap — per-insight Jaccard
        for insight in ctx["insights"]:
            if _keyword_overlap(claim_kw, insight["keywords"]) >= 0.10:
                return True

        return False

    def _check_probable(
        self, claim: CausalClaim, claim_kw: set[str], ctx: dict,
    ) -> bool:
        """Vérifier les critères de PROBABLE_CAUSATION.

        1. Peu de confounders contextuels (< 3)
        2. ET fait partie d'une chaîne causale
        """
        # Few contextual confounders
        if claim.id:
            ctx_conf_count = self.db.get_contextual_confounder_count(claim.id)
            if ctx_conf_count >= 3:
                return False

        # Part of a causal chain : cause or effect appears as both cause AND effect
        chain_nodes = ctx["chain_nodes"]
        in_chain = claim.cause in chain_nodes or claim.effect in chain_nodes

        if not in_chain:
            # Fuzzy check : keywords of cause/effect overlap with chain node keywords
            chain_kw = set()
            for node in chain_nodes:
                chain_kw.update(_extract_keywords(node))
            if len(claim_kw & chain_kw) >= 3:
                in_chain = True

        return in_chain

    def _check_demonstrated(
        self, claim: CausalClaim, claim_kw: set[str], ctx: dict,
    ) -> bool:
        """Vérifier les critères de DEMONSTRATED_CAUSATION.

        1. Termes testés par Hitbonenut avec score > 0.7 (Jaccard >= 0.15)
        2. ET cohérent avec les conclusions DissensuEngine (Jaccard >= 0.10)

        Seuils Jaccard stricts — le niveau le plus haut exige
        un overlap sémantique substantiel, pas juste du vocabulaire partagé.
        """
        if not claim_kw:
            return False

        # Hitbonenut high-score match — Jaccard >= 0.25
        hitbonenut_match = False
        for hq in ctx["hitbonenut"]["high_score"]:
            if _keyword_overlap(claim_kw, hq["keywords"]) >= 0.25:
                hitbonenut_match = True
                break

        if not hitbonenut_match:
            return False

        # Dissensus consistency — Jaccard >= 0.15
        for conclusion in ctx["dissensus"]:
            if _keyword_overlap(claim_kw, conclusion["keywords"]) >= 0.15:
                return True

        return False

    def _recalculate_confidence(self, claim: CausalClaim, level: str) -> float:
        """Recalculer la confiance avec le nouveau niveau d'évidence."""
        confounders = []
        if claim.id:
            confounders = self.db.get_confounders(claim.id)

        direction = DirectionAssessment(
            verdict="forward" if claim.direction_verified else "indeterminate",
            forward_plausibility=0.6 if claim.direction_verified else 0.5,
            reverse_plausibility=0.5,
        )

        return self.scorer.compute_confidence(level, confounders, direction)

    def dry_run(self) -> dict:
        """Simulation sans persistence — montre combien seraient élevés."""
        claims = self.db.get_all_claims()
        ctx = self._load_context()

        counts: dict[str, int] = defaultdict(int)
        examples: dict[str, list[str]] = defaultdict(list)

        for claim in claims:
            claim_kw = _extract_keywords(claim.cause + " " + claim.effect)
            new_level, new_conf = self._evaluate_claim(claim, ctx)

            if EVIDENCE_RANK.get(new_level, 0) > EVIDENCE_RANK.get(claim.evidence_level, 0):
                key = f"{claim.evidence_level}→{new_level}"
                counts[key] += 1
                if len(examples[key]) < 3:
                    examples[key].append(
                        f"{claim.cause[:50]}→{claim.effect[:50]} (conf: {claim.confidence}→{new_conf})"
                    )

        return {
            "total": len(claims),
            "would_elevate": dict(counts),
            "examples": dict(examples),
            "would_stay_correlation": len(claims) - sum(counts.values()),
        }
