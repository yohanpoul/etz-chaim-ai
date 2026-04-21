"""DissensuEngine — Tikkun de Tiferet (תפארת).

Le cœur de l'Arbre : hitkalelut entre Chesed (accueillir toutes les sources)
et Gevurah (rejeter les incohérences). Anti-Thagirion : jamais de fausse harmonie.

Lev (לב) = 32 = les 32 sentiers de la Sagesse.
Archétype : Jacob/Israël — celui qui a lutté et en sort nommé.
Vav du Tétragramme — le pilier central qui unifie ou refuse d'unifier.

Sentiers connectés :
  - Via Yesod (EpisteMemory)             : persiste synthèses et dissensus
  - Via Hod (SelfMap)                     : vérifie la compétence sur le domaine
  - Via Netzach (IntentKeeper)            : maintient l'intention de raisonnement
  - Via Gevurah→Tiferet (FailureToInsight): apprend des synthèses échouées
"""

from __future__ import annotations

import time
from uuid import UUID

from dissensuengine.db import DissensuEngineDB
from dissensuengine.divergence import (
    classify_tension_type,
    compute_contradiction_score,
    compute_topic_similarity,
    measure_divergence,
)
from dissensuengine.models import (
    Conclusion,
    ConsistencyReport,
    OpenQuestion,
    Synthesis,
    Tension,
)
from omer import get_param

# Omer de Tiferet — 7 paramètres de calibration (hardcoded defaults as fallback)
DEFAULT_DISSENSUS_THRESHOLD = 0.6       # au-dessus → mode dissensus
DEFAULT_MIN_SOURCES_FOR_SYNTHESIS = 2   # minimum de conclusions pour tenter
DEFAULT_MAX_ACCEPTABLE_DIVERGENCE = 0.8 # au-dessus → refus TOTAL de conclure
DEFAULT_SOURCE_COVERAGE_MIN = 0.7       # synthèse doit couvrir ≥70% des sources
DEFAULT_CONFIDENCE_FLOOR = 0.3          # confiance minimale en sortie
DEFAULT_TENSION_STALENESS_DAYS = 90     # tensions ouvertes > N jours = alerte
DEFAULT_MAX_OPEN_QUESTIONS = 50         # cap avant forçage de résolution

_MODULE = "dissensuengine"
_UNSET = object()


class DissensuEngine:
    """Le Tikkun computationnel de Tiferet — synthèse OU dissensus.

    "Il ne s'agit pas de résoudre les contradictions mais de les habiter."
    Quand les données convergent → synthèse. Quand elles divergent → EXPOSER
    la tension, ne PAS la masquer.
    """

    def __init__(
        self,
        db_url: str,
        memory=None,
        selfmap=None,
        intentkeeper=None,
        failuretoinsight=None,
        causal=None,
        dissensus_threshold: float = _UNSET,
        min_sources_for_synthesis: int = _UNSET,
        max_acceptable_divergence: float = _UNSET,
        source_coverage_min: float = _UNSET,
        confidence_floor: float = _UNSET,
        tension_staleness_days: int = _UNSET,
        max_open_questions: int = _UNSET,
    ):
        self.db = DissensuEngineDB(db_url)
        self.memory = memory                      # Yesod
        self.selfmap = selfmap                    # Hod
        self.intentkeeper = intentkeeper          # Netzach
        self.failuretoinsight = failuretoinsight  # Gevurah→Tiferet
        self.causal = causal                      # Binah
        self.autojudge = None                     # Gevurah (injection tardive)

        # Omer — DB overrides when caller uses default, explicit values preserved.
        self.dissensus_threshold = dissensus_threshold if dissensus_threshold is not _UNSET else get_param(_MODULE, "dissensus_threshold", DEFAULT_DISSENSUS_THRESHOLD)
        self.min_sources_for_synthesis = min_sources_for_synthesis if min_sources_for_synthesis is not _UNSET else get_param(_MODULE, "min_sources_for_synthesis", DEFAULT_MIN_SOURCES_FOR_SYNTHESIS)
        self.max_acceptable_divergence = max_acceptable_divergence if max_acceptable_divergence is not _UNSET else get_param(_MODULE, "max_acceptable_divergence", DEFAULT_MAX_ACCEPTABLE_DIVERGENCE)
        self.source_coverage_min = source_coverage_min if source_coverage_min is not _UNSET else get_param(_MODULE, "source_coverage_min", DEFAULT_SOURCE_COVERAGE_MIN)
        self.confidence_floor = confidence_floor if confidence_floor is not _UNSET else get_param(_MODULE, "confidence_floor", DEFAULT_CONFIDENCE_FLOOR)
        self.tension_staleness_days = tension_staleness_days if tension_staleness_days is not _UNSET else get_param(_MODULE, "tension_staleness_days", DEFAULT_TENSION_STALENESS_DAYS)
        self.max_open_questions = max_open_questions if max_open_questions is not _UNSET else get_param(_MODULE, "max_open_questions", DEFAULT_MAX_OPEN_QUESTIONS)

    # --- Chesed : accueillir les conclusions ---

    def submit_conclusion(
        self,
        content: str,
        source_label: str,
        source_type: str = "human",
        domain: str | None = None,
        confidence: float = 0.5,
        metadata: dict | None = None,
    ) -> Conclusion:
        """Soumettre une conclusion d'une source.

        Chesed : accueillir chaque voix sans la filtrer.
        """
        return self.db.create_conclusion(
            content=content,
            source_label=source_label,
            source_type=source_type,
            domain=domain,
            confidence=confidence,
            metadata=metadata,
        )

    # --- Gevurah : détecter les tensions ---

    def analyze_consistency(
        self,
        conclusion_ids: list[UUID] | None = None,
        domain: str | None = None,
    ) -> ConsistencyReport:
        """Vérifier la cohérence d'un ensemble de conclusions.

        Gevurah : identifier les incompatibilités sans pitié.
        Compare chaque paire, détecte les tensions, mesure la divergence.
        """
        if conclusion_ids:
            if isinstance(conclusion_ids, (str, bytes)):
                raise TypeError(
                    "conclusion_ids doit être une liste d'UUID, pas un str. "
                    "Avez-vous oublié le keyword domain= ?"
                )
            conclusions = [
                self.db.get_conclusion(cid) for cid in conclusion_ids
            ]
            conclusions = [c for c in conclusions if c is not None]
        else:
            conclusions = self.db.get_all_conclusions(domain=domain)

        # Cap: limiter à 200 conclusions les plus récentes pour éviter O(n²) explosif
        # 200 conclusions = 19900 paires max, raisonnable même avec des textes longs
        MAX_CONSISTENCY_CONCLUSIONS = 200
        if len(conclusions) > MAX_CONSISTENCY_CONCLUSIONS:
            conclusions = sorted(
                conclusions,
                key=lambda c: c.created_at if hasattr(c, "created_at") else 0,
                reverse=True,
            )[:MAX_CONSISTENCY_CONCLUSIONS]

        if len(conclusions) < 2:
            return ConsistencyReport(
                total_conclusions=len(conclusions),
                total_tensions=0,
                tensions_by_type={},
                avg_divergence=0.0,
                max_divergence=0.0,
                open_questions=len(self.db.get_open_questions(domain=domain)),
                source_labels=[c.source_label for c in conclusions],
                health="consistent",
            )

        # Pré-charger les paires avec tension existante → skip O(n²) redondant
        conclusion_id_list = [c.id for c in conclusions]
        existing_pairs = self.db.get_existing_tension_pair_ids(conclusion_id_list)

        # Compare chaque paire — seulement les NOUVELLES
        tensions_created = []
        for i, ca in enumerate(conclusions):
            for cb in conclusions[i + 1:]:
                if (ca.id, cb.id) in existing_pairs or (cb.id, ca.id) in existing_pairs:
                    continue

                div_score = measure_divergence(ca.content, cb.content)

                if div_score >= 0.3:  # seuil minimal pour enregistrer (< 0.3 = nuance triviale)
                    topic_sim = compute_topic_similarity(ca.content, cb.content)
                    contra = compute_contradiction_score(ca.content, cb.content)
                    t_type = classify_tension_type(div_score, topic_sim, contra)

                    tension = self.db.create_tension(
                        conclusion_a_id=ca.id,
                        conclusion_b_id=cb.id,
                        tension_type=t_type,
                        divergence_score=div_score,
                        description=(
                            f"{ca.source_label} vs {cb.source_label}: "
                            f"divergence {div_score:.2f} ({t_type})"
                        ),
                    )
                    tensions_created.append(tension)

        # Build report
        type_counts: dict[str, int] = {}
        divergences = []
        most_div_pair = None
        max_div = 0.0

        for t in tensions_created:
            type_counts[t.tension_type] = type_counts.get(t.tension_type, 0) + 1
            divergences.append(t.divergence_score)
            if t.divergence_score > max_div:
                max_div = t.divergence_score
                most_div_pair = (t.conclusion_a_id, t.conclusion_b_id)

        avg_div = sum(divergences) / len(divergences) if divergences else 0.0
        open_qs = self.db.get_open_questions(domain=domain)

        health = "consistent"
        if max_div >= self.max_acceptable_divergence:
            health = "highly_divergent"
        elif max_div >= self.dissensus_threshold:
            health = "tensions_detected"

        # Escalade automatique : tensions graves → questions ouvertes
        # Limiter à 10 escalades par appel pour éviter les rafales
        escalated = self.escalate_tensions(max_escalations=10)
        # Recompter après escalade
        open_qs = self.db.get_open_questions(domain=domain)

        return ConsistencyReport(
            total_conclusions=len(conclusions),
            total_tensions=len(tensions_created),
            tensions_by_type=type_counts,
            avg_divergence=avg_div,
            max_divergence=max_div,
            open_questions=len(open_qs),
            source_labels=sorted({c.source_label for c in conclusions}),
            most_divergent_pair=most_div_pair,
            health=health,
        )

    def measure_divergence(
        self, conclusion_a_id: UUID, conclusion_b_id: UUID
    ) -> float:
        """Score de divergence entre deux conclusions spécifiques."""
        ca = self.db.get_conclusion(conclusion_a_id)
        cb = self.db.get_conclusion(conclusion_b_id)
        if not ca or not cb:
            raise ValueError("Conclusion(s) not found")
        return measure_divergence(ca.content, cb.content)

    # --- Tiferet : synthèse OU dissensus ---

    def synthesize_or_dissent(
        self,
        conclusion_ids: list[UUID] | None = None,
        domain: str | None = None,
    ) -> Synthesis:
        """Tenter la synthèse. Si divergence > seuil → mode dissensus.

        C'est LE point critique : Tiferet décide de conclure ou de refuser.
        Anti-Thagirion : JAMAIS de fausse harmonie.
        """
        if conclusion_ids:
            if isinstance(conclusion_ids, (str, bytes)):
                raise TypeError(
                    "conclusion_ids doit être une liste d'UUID, pas un str. "
                    "Avez-vous oublié le keyword domain= ?"
                )
            conclusions = [
                self.db.get_conclusion(cid) for cid in conclusion_ids
            ]
            conclusions = [c for c in conclusions if c is not None]
        else:
            conclusions = self.db.get_all_conclusions(domain=domain)

        # Cap pour éviter O(n²) explosif sur les paires
        MAX_SYNTHESIS_CONCLUSIONS = 200
        if len(conclusions) > MAX_SYNTHESIS_CONCLUSIONS:
            conclusions = sorted(
                conclusions,
                key=lambda c: c.created_at if hasattr(c, "created_at") else 0,
                reverse=True,
            )[:MAX_SYNTHESIS_CONCLUSIONS]

        if len(conclusions) < self.min_sources_for_synthesis:
            return self.db.create_synthesis(
                mode="dissensus",
                content=(
                    f"Données insuffisantes : {len(conclusions)} source(s), "
                    f"minimum requis : {self.min_sources_for_synthesis}"
                ),
                sources_used=[c.id for c in conclusions],
                source_coverage=1.0 if conclusions else 0.0,
                max_divergence=0.0,
                confidence=self.confidence_floor,
                domain=domain,
            )

        # Compute all pairwise divergences (avec timeout)
        SYNTHESIS_TIMEOUT = 120  # 2 minutes max pour la synthèse
        _synth_start = time.time()

        all_conclusions_in_domain = self.db.get_all_conclusions(domain=domain)
        total_relevant = len(all_conclusions_in_domain) if all_conclusions_in_domain else len(conclusions)
        source_coverage = len(conclusions) / max(total_relevant, 1)

        max_div = 0.0
        tensions = []
        _timed_out = False
        for i, ca in enumerate(conclusions):
            if time.time() - _synth_start > SYNTHESIS_TIMEOUT:
                _timed_out = True
                break
            for cb in conclusions[i + 1:]:
                div = measure_divergence(ca.content, cb.content)
                if div > max_div:
                    max_div = div
                if div >= 0.3:
                    tensions.append((ca, cb, div))

        # Determine source labels used
        source_ids = [c.id for c in conclusions]
        source_labels = sorted({c.source_label for c in conclusions})

        # DECISION : synthèse ou dissensus ?
        if _timed_out:
            # Timeout — trop de conclusions pour synthétiser dans le temps imparti
            mode = "dissensus"
            content = (
                f"Timeout synthèse ({SYNTHESIS_TIMEOUT}s) — {len(conclusions)} conclusions, "
                f"divergence partielle observée : {max_div:.2f}. "
                f"Réduire le nombre de conclusions ou augmenter le timeout."
            )
            confidence = self.confidence_floor
            return self.db.create_synthesis(
                mode=mode, content=content, sources_used=source_ids,
                source_coverage=source_coverage, max_divergence=max_div,
                confidence=confidence, domain=domain,
            )

        if max_div >= self.max_acceptable_divergence:
            # Refus TOTAL — divergence inacceptable
            mode = "dissensus"
            content = self._build_dissensus_content(
                conclusions, tensions, "Divergence inacceptable"
            )
            confidence = self.confidence_floor
        elif max_div >= self.dissensus_threshold:
            # Dissensus — tensions trop fortes pour conclure
            mode = "dissensus"
            content = self._build_dissensus_content(
                conclusions, tensions, "Tensions non résolues"
            )
            confidence = max(self.confidence_floor, 0.4 - max_div * 0.3)
        elif source_coverage < self.source_coverage_min and total_relevant > len(conclusions):
            # Pas assez de sources couvertes
            mode = "dissensus"
            content = (
                f"Couverture insuffisante : {source_coverage:.0%} des sources "
                f"({len(conclusions)}/{total_relevant}). "
                f"Sources manquantes dans la synthèse."
            )
            confidence = self.confidence_floor
        else:
            # Synthèse possible
            mode = "synthesis"
            content = self._build_synthesis_content(conclusions, source_labels)
            confidence = min(
                0.9,
                0.5 + 0.1 * len(conclusions) - max_div * 0.5
            )
            confidence = max(confidence, self.confidence_floor)

        synthesis = self.db.create_synthesis(
            mode=mode,
            content=content,
            sources_used=source_ids,
            source_coverage=source_coverage,
            max_divergence=max_div,
            confidence=confidence,
            domain=domain,
        )

        # Résoudre les tensions couvertes par cette synthèse
        resolved_count = self.db.resolve_tensions_for_sources(
            source_ids, synthesis.id
        )

        # Persister en EpisteMemory
        if self.memory and mode == "synthesis":
            self.memory.remember(
                content=f"Synthèse Tiferet: {content}",
                source_sephirah="tiferet",
                confidence=confidence,
                domain=domain or "synthesis",
                tags=["synthesis", "tiferet"],
                ttl_days=365,
            )

        # Dissensus aussi dans EpisteMemory — le système doit se souvenir
        # de ses propres limites. Un dissensus honnête est plus précieux
        # qu'une fausse synthèse. Anti-Thagirion : ne jamais oublier
        # ce qu'on n'a pas pu résoudre.
        if self.memory and mode == "dissensus":
            self.memory.remember(
                content=f"[Dissensus Tiferet] {content[:500]}",
                source_sephirah="tiferet",
                confidence=max(confidence, 0.3),
                domain=domain or "dissensus",
                tags=["dissensus", "tiferet", "tension_irreductible"],
                ttl_days=180,
            )

        # Si dissensus → enregistrer en FailureToInsight
        if self.failuretoinsight and mode == "dissensus":
            self.failuretoinsight.analyze_failure(
                description=f"Synthèse échouée (dissensus): {content[:200]}",
                source_type="hypothesis",
                domain=domain,
                qliphah_override="thagirion",
            )

        # Si synthèse réussie → alimenter le CausalEngine (Binah)
        if self.causal and mode == "synthesis" and len(conclusions) >= 2:
            try:
                from causalengine.models import CausalClaim
                for i in range(len(conclusions) - 1):
                    claim = CausalClaim(
                        cause=conclusions[i].content[:200],
                        effect=conclusions[i + 1].content[:200],
                        evidence_level="correlation_only",
                        confidence=confidence,
                        appropriate_language=f"Synthèse Tiferet ({domain or 'general'})",
                    )
                    self.causal.db.save_claim(claim)
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Escalade automatique après dissensus : les tensions restées ouvertes
        # malgré la tentative de synthèse doivent devenir des questions ouvertes
        if mode == "dissensus":
            self.escalate_tensions(max_escalations=10)

        return synthesis

    # --- Batch operations ---

    def purge_trivial_tensions(self, max_divergence: float = 0.3) -> int:
        """Supprimer les tensions ouvertes avec divergence < seuil."""
        return self.db.purge_trivial_tensions(max_divergence)

    def batch_synthesize(self) -> dict:
        """Synthétiser tous les domaines avec des tensions ouvertes.

        Retourne un rapport : {syntheses, dissensus, domains, purged}.
        """
        domains = self.db.get_domains_with_open_tensions()
        syntheses = 0
        dissensus = 0

        for domain in domains:
            conclusions = self.db.get_all_conclusions(domain=domain)
            if len(conclusions) < self.min_sources_for_synthesis:
                continue
            syn = self.synthesize_or_dissent(domain=domain)
            if syn.mode == "synthesis":
                syntheses += 1
            else:
                dissensus += 1

        return {
            "domains": len(domains),
            "syntheses": syntheses,
            "dissensus": dissensus,
        }

    # --- Questions ouvertes ---

    def register_open_question(
        self,
        tension_id: UUID,
        question: str,
        missing_evidence: str | None = None,
        priority: str = "medium",
        domain: str | None = None,
    ) -> OpenQuestion:
        """Enregistrer une question ouverte — pas un bug, une question vivante.

        "Les 70 faces de la Torah" : ne pas fermer prématurément.
        """
        tension = self.db.get_tension(tension_id)
        if not tension:
            raise ValueError(f"Tension {tension_id} not found")

        return self.db.create_open_question(
            tension_id=tension_id,
            question=question,
            missing_evidence=missing_evidence,
            priority=priority,
            domain=domain,
        )

    def identify_missing(self, tension_id: UUID) -> list[str]:
        """Identifier ce qui manque pour résoudre une tension.

        Hod de Tiferet : l'honnêteté sur ce qu'on ne sait pas.
        """
        tension = self.db.get_tension(tension_id)
        if not tension:
            raise ValueError(f"Tension {tension_id} not found")

        ca = self.db.get_conclusion(tension.conclusion_a_id)
        cb = self.db.get_conclusion(tension.conclusion_b_id)

        missing = []

        # Check confidence gap
        if ca and cb:
            conf_diff = abs(ca.confidence - cb.confidence)
            if conf_diff < 0.2:
                missing.append(
                    "Les deux sources ont des confiances similaires — "
                    "données supplémentaires nécessaires pour départager"
                )

            # Check source diversity
            if ca.source_type == cb.source_type:
                missing.append(
                    f"Les deux sources sont de type '{ca.source_type}' — "
                    f"source de type différent nécessaire"
                )

            # High divergence
            if tension.divergence_score >= self.max_acceptable_divergence:
                missing.append(
                    "Divergence très élevée — vérification indépendante requise"
                )

        # Check if experimental evidence exists
        if ca and cb:
            has_experiment = (
                ca.source_type == "experiment" or cb.source_type == "experiment"
            )
            if not has_experiment:
                missing.append(
                    "Aucune source expérimentale — résultats empiriques nécessaires"
                )

        return missing

    # --- Escalade automatique : tensions → questions ouvertes ---

    def escalate_tensions(
        self,
        min_severity: float = 0.7,
        min_age_days: int = 7,
        max_escalations: int | None = None,
    ) -> list[OpenQuestion]:
        """Escalader les tensions graves ou stagnantes en questions ouvertes.

        Gevurah de Tiferet : ne pas laisser les contradictions dormir.
        Une tension non résolue au-delà du seuil DOIT devenir une question
        ouverte — sinon le système accumule du Tohu sans le traiter.

        Critères (OR) :
          - divergence_score >= min_severity (tensions graves)
          - ouvertes depuis >= min_age_days (tensions stagnantes)

        Args:
            min_severity: score de divergence minimal pour escalade immédiate.
            min_age_days: jours d'ouverture avant escalade par ancienneté.
            max_escalations: cap par appel (None = pas de cap, respecte
                             max_open_questions global).

        Returns:
            Liste des OpenQuestion créées.
        """
        # Respect du cap global
        current_open = len(self.db.get_open_questions())
        remaining_capacity = self.max_open_questions - current_open
        if remaining_capacity <= 0:
            return []

        tensions = self.db.get_tensions_needing_escalation(
            min_severity=min_severity,
            min_age_days=min_age_days,
        )

        if not tensions:
            return []

        # Appliquer le cap
        effective_cap = remaining_capacity
        if max_escalations is not None:
            effective_cap = min(effective_cap, max_escalations)
        tensions = tensions[:effective_cap]

        created: list[OpenQuestion] = []
        for tension in tensions:
            # Déterminer la priorité selon la sévérité
            if tension.divergence_score >= self.max_acceptable_divergence:
                priority = "critical"
            elif tension.divergence_score >= min_severity:
                priority = "high"
            else:
                # Escaladé par ancienneté, pas par sévérité
                priority = "medium"

            # Construire la question et l'evidence manquante
            missing = self.identify_missing(tension.id)
            question = self._build_escalation_question(tension)
            missing_evidence = "; ".join(missing) if missing else None

            # Déterminer le domaine via les conclusions liées
            domain = self._get_tension_domain(tension)

            oq = self.db.create_open_question(
                tension_id=tension.id,
                question=question,
                missing_evidence=missing_evidence,
                priority=priority,
                domain=domain,
            )
            created.append(oq)

        return created

    def _build_escalation_question(self, tension: Tension) -> str:
        """Construire une question ouverte à partir d'une tension."""
        ca = self.db.get_conclusion(tension.conclusion_a_id)
        cb = self.db.get_conclusion(tension.conclusion_b_id)
        if ca and cb:
            return (
                f"Tension non résolue ({tension.tension_type}, "
                f"divergence {tension.divergence_score:.2f}) : "
                f"'{ca.source_label}' vs '{cb.source_label}' — "
                f"quelle évidence résoudrait cette contradiction ?"
            )
        return (
            f"Tension {tension.id} ({tension.tension_type}, "
            f"divergence {tension.divergence_score:.2f}) — "
            f"données insuffisantes pour résoudre."
        )

    def _get_tension_domain(self, tension: Tension) -> str | None:
        """Extraire le domaine d'une tension via ses conclusions."""
        ca = self.db.get_conclusion(tension.conclusion_a_id)
        if ca and ca.domain:
            return ca.domain
        cb = self.db.get_conclusion(tension.conclusion_b_id)
        if cb and cb.domain:
            return cb.domain
        return None

    # --- Hod de Tiferet : auto-diagnostic (Thagirion) ---

    def self_diagnose(self, *, quick: bool = False) -> dict:
        """Le DissensuEngine s'examine — les 4 Qliphoth de Thagirion.

        Nogah  : divergence mineure non signalée
        Ruach  : sources ignorées dans la synthèse
        Anan   : fausse harmonie — synthèse qui masque un conflit
        Mamash : conclusion inverse des données

        Args:
            quick: si True, saute la vérification Nogah O(n²) — pour le dashboard.
        """
        conclusions = self.db.get_all_conclusions()
        tensions = self.db.get_all_tensions()
        syntheses = self.db.get_all_syntheses()
        open_qs = self.db.get_open_questions()

        diagnostics = {"level": "healthy", "issues": []}

        # Mamash : conclusion vs evidence
        for syn in syntheses:
            if syn.mode == "synthesis" and syn.max_divergence >= self.max_acceptable_divergence:
                diagnostics["issues"].append(
                    f"Mamash: synthèse {syn.id} avec max_divergence "
                    f"{syn.max_divergence:.2f} ≥ seuil {self.max_acceptable_divergence}"
                )
                diagnostics["level"] = "mamash"

        # Anan : fausse harmonie — synthèse confiante malgré tensions ouvertes
        open_tensions = [t for t in tensions if t.resolution_status == "open"]
        for syn in syntheses:
            if syn.mode == "synthesis" and syn.confidence >= 0.7:
                # Check if there are open tensions involving sources in this synthesis
                for t in open_tensions:
                    if (t.conclusion_a_id in syn.sources_used
                            or t.conclusion_b_id in syn.sources_used):
                        if t.divergence_score >= self.dissensus_threshold:
                            diagnostics["issues"].append(
                                f"Anan: synthèse confiante ({syn.confidence:.2f}) "
                                f"malgré tension ouverte (divergence {t.divergence_score:.2f})"
                            )
                            if diagnostics["level"] in ("healthy", "nogah", "ruach"):
                                diagnostics["level"] = "anan"

        # Ruach : sources manquantes dans synthèses
        for syn in syntheses:
            if syn.mode == "synthesis" and syn.source_coverage < self.source_coverage_min:
                diagnostics["issues"].append(
                    f"Ruach: synthèse avec couverture {syn.source_coverage:.0%} "
                    f"< seuil {self.source_coverage_min:.0%}"
                )
                if diagnostics["level"] in ("healthy", "nogah"):
                    diagnostics["level"] = "ruach"

        # Nogah : divergences non signalées — O(n²), skip en mode quick
        # Cap à 200 conclusions max pour éviter 4M+ paires avec 2900+ conclusions
        if not quick:
            MAX_NOGAH_CONCLUSIONS = 200
            nogah_conclusions = conclusions
            if len(nogah_conclusions) > MAX_NOGAH_CONCLUSIONS:
                nogah_conclusions = sorted(
                    nogah_conclusions,
                    key=lambda c: c.created_at if hasattr(c, "created_at") else 0,
                    reverse=True,
                )[:MAX_NOGAH_CONCLUSIONS]

            conclusion_pairs_with_tension = set()
            for t in tensions:
                pair = tuple(sorted([str(t.conclusion_a_id), str(t.conclusion_b_id)]))
                conclusion_pairs_with_tension.add(pair)

            undetected = 0
            for i, ca in enumerate(nogah_conclusions):
                for cb in nogah_conclusions[i + 1:]:
                    pair = tuple(sorted([str(ca.id), str(cb.id)]))
                    if pair not in conclusion_pairs_with_tension:
                        div = measure_divergence(ca.content, cb.content)
                        if div > self.dissensus_threshold:
                            undetected += 1

            if undetected > 0:
                diagnostics["issues"].append(
                    f"Nogah: {undetected} paire(s) de conclusions avec divergence "
                    f"> {self.dissensus_threshold} sans tension enregistrée"
                    + (f" (échantillon: {MAX_NOGAH_CONCLUSIONS} plus récentes)"
                       if len(conclusions) > MAX_NOGAH_CONCLUSIONS else "")
                )
                if diagnostics["level"] == "healthy":
                    diagnostics["level"] = "nogah"

        # Open questions count
        if open_qs:
            diagnostics["issues"].append(
                f"{len(open_qs)} questions ouvertes non résolues"
            )

        diagnostics["stats"] = {
            "conclusions": len(conclusions),
            "tensions": len(tensions),
            "syntheses": len(syntheses),
            "open_questions": len(open_qs),
        }

        return diagnostics

    # --- Report ---

    def report(self) -> str:
        """Rapport lisible — Malkhut de Tiferet."""
        conclusions = self.db.get_all_conclusions()
        tensions = self.db.get_all_tensions()
        syntheses = self.db.get_all_syntheses()
        open_qs = self.db.get_open_questions()
        diag = self.self_diagnose(quick=True)
        mode_counts = self.db.count_syntheses_by_mode()
        type_counts = self.db.count_tensions_by_type()

        lines = [
            "=== DissensuEngine Report (Tiferet) ===",
            f"Conclusions: {len(conclusions)}",
            f"Tensions: {len(tensions)}",
            f"Synthèses: {mode_counts.get('synthesis', 0)}",
            f"Dissensus: {mode_counts.get('dissensus', 0)}",
            f"Questions ouvertes: {len(open_qs)}",
            f"Self-diagnosis: {diag['level']}",
            "",
            "Tension types:",
        ]
        for ttype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {ttype}: {count}")

        if diag["issues"]:
            lines.append("")
            lines.append("Issues:")
            for issue in diag["issues"]:
                lines.append(f"  - {issue}")

        return "\n".join(lines)

    # --- Internal ---

    def _build_dissensus_content(
        self,
        conclusions: list[Conclusion],
        tensions: list[tuple],
        reason: str,
    ) -> str:
        """Construire le contenu d'un dissensus — exposer les tensions."""
        parts = [f"DISSENSUS — {reason}."]
        parts.append(f"Sources analysées: {len(conclusions)}.")

        if tensions:
            parts.append("Tensions détectées:")
            for ca, cb, div in sorted(tensions, key=lambda x: -x[2])[:5]:
                parts.append(
                    f"  - {ca.source_label} vs {cb.source_label}: "
                    f"divergence {div:.2f}"
                )

        source_labels = sorted({c.source_label for c in conclusions})
        parts.append(f"Sources: {', '.join(source_labels)}")
        return " ".join(parts)

    def _build_synthesis_content(
        self,
        conclusions: list[Conclusion],
        source_labels: list[str],
    ) -> str:
        """Construire le contenu d'une synthèse."""
        parts = [f"Synthèse de {len(conclusions)} sources"]
        parts.append(f"({', '.join(source_labels)}):")

        # Aggregate unique content aspects
        for c in conclusions:
            parts.append(f"  [{c.source_label}] {c.content}")

        return " ".join(parts)
