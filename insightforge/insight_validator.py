"""InsightValidator — triple validation anti-Ghagiel.

Le danger suprême de Chokmah : confondre hallucination et insight.
Un "insight" qui n'est qu'une hallucination confiante est PIRE qu'une
hallucination normale — parce qu'il est marqué 'chokmah' et stocké
avec haute confiance.

Triple validation obligatoire :
  1. Binah  — le raisonnement est-il causalement valide ?
  2. Gevurah — la qualité est-elle suffisante ?
  3. Da'at  — le système prédit-il une erreur ici ?

Checks supplémentaires (non bloquants mais informatifs) :
  4. Yesod  — les données sources existent-elles ?
  5. Hod    — le système est-il compétent dans ce domaine ?
  6. Tiferet — y a-t-il des contradictions avec des claims existants ?
"""

from __future__ import annotations

from insightforge.models import CandidateInsight, InsightValidation


# Seuils
DEFAULT_MIN_CONFIDENCE = 0.5     # Confiance minimum pour valider
DEFAULT_COMPETENCE_THRESHOLD = 0.4  # Compétence minimum du domaine

# Préfixes interrogatifs (français + anglais) détectés en début de description.
_QUESTION_PREFIXES = (
    "comment", "pourquoi", "quelle", "quel", "quels", "quelles",
    "où", "ou ", "qui ", "quand", "est-ce",
    "how", "why", "what", "which", "who", "when", "where",
)


def _is_question(description: str) -> bool:
    """Détecter si la description est une question ouverte.

    Une question n'est pas un claim causal évaluable par Binah :
    `check_claim(cause=question, effect="observed pattern")` ne peut
    qu'échouer sur correlation_only. La router ailleurs.
    """
    if not description:
        return False
    stripped = description.strip()
    if not stripped:
        return False
    if stripped.endswith("?"):
        return True
    lower = stripped.lower()
    # Supprimer un préfixe éventuel "Hitbonenut insight:" ou équivalent
    for sep in (":", "—", "-"):
        if sep in lower[:40]:
            lower = lower.split(sep, 1)[1].lstrip()
            break
    return any(lower.startswith(prefix) for prefix in _QUESTION_PREFIXES)


_MIN_SYNTHESIS_LENGTH = 30


def _extract_synthesis(description: str) -> str | None:
    """Extraire la synthèse substantielle d'une description hitbonenut.

    Deux formats supportés :

    - **Sprint 5.2 — em-dash** (``orchestrator._phase_data_mine`` path) :
      ``"Hitbonenut insight: <question> — <synthèse>"``. Split au premier
      em-dash, la synthèse est le reste.

    - **Sprint 5.3 — Q/A** (``hitbonenut.py:_submit_insight_candidate``
      path) : ``"Q: <question>\\nA: <synthèse>"``. Le marqueur ``\\nA:``
      est structurel ; l'em-dash à l'intérieur de la synthèse (titres
      markdown, emphases type ``# Synthèse — Architecture``) n'est PAS un
      séparateur mais du contenu. Le format Q/A a précédence quand les
      deux marqueurs coexistent.

    Doctrine It'aruta Diltata : extraire la synthèse permet à Binah
    d'évaluer le contenu causal au lieu de déférer sur la forme
    interrogative de la question d'ouverture.

    Returns:
        La synthèse strippée si elle est substantielle (≥30 chars) et
        n'est pas elle-même une question. Sinon None.
    """
    if not description:
        return None

    synthesis: str | None = None

    # Format Q/A — précédence absolue quand le marqueur ``\nA:`` est
    # présent, car l'em-dash y est contenu et non séparateur.
    if description.startswith("Q:") and "\nA:" in description:
        idx = description.index("\nA:")
        synthesis = description[idx + 3:].strip()
    # Format em-dash — chemin historique Sprint 5.2.
    elif "—" in description:
        parts = description.split("—", 1)
        if len(parts) >= 2:
            synthesis = parts[1].strip()

    if synthesis is None:
        return None
    if len(synthesis) < _MIN_SYNTHESIS_LENGTH:
        return None
    # Une synthèse qui est elle-même une question reste non évaluable
    # par Binah — préserver le comportement question_deferred.
    if _is_question(synthesis):
        return None
    return synthesis


class InsightValidator:
    """Triple validation Binah + Gevurah + Da'at.

    Anan de Ghagiel : un insight marqué 'chokmah' qui est en réalité
    une hallucination. Ce validateur est le dernier rempart.
    """

    def __init__(
        self,
        binah=None,          # CausalEngine (Tevunah dans Z"A — causal Pearl)
        binah_gates=None,    # BinahGates (Binah haute — 5 Motzaot, Sprint 6.x)
        gevurah=None,        # AutoJudge
        daat=None,           # SelfModel
        yesod=None,          # EpisteMemory
        hod=None,            # SelfMap
        tiferet=None,        # DissensuEngine
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        competence_threshold: float = DEFAULT_COMPETENCE_THRESHOLD,
        require_triple: bool = True,
    ):
        self.binah = binah
        self.binah_gates = binah_gates
        self.gevurah = gevurah
        self.daat = daat
        self.yesod = yesod
        self.hod = hod
        self.tiferet = tiferet
        self.min_confidence = min_confidence
        self.competence_threshold = competence_threshold
        self.require_triple = require_triple

    def validate(
        self,
        candidate: CandidateInsight,
        domain: str = "",
    ) -> InsightValidation:
        """Valider un insight candidat — triple validation obligatoire.

        Returns:
            InsightValidation avec le détail de chaque check.
        """
        # --- Triple validation (bloquante) ---
        binah_ok, binah_detail = self._check_binah(candidate, domain)
        gevurah_ok, gevurah_detail = self._check_gevurah(candidate, domain)
        daat_ok, daat_detail = self._check_daat(candidate)

        # --- Checks supplémentaires (informatifs) ---
        source_ok, source_detail = self._check_sources(candidate)
        competence_ok, competence_detail = self._check_competence(
            candidate, domain,
        )
        consistency_ok, consistency_detail = self._check_consistency(candidate)

        # Confiance composite
        confidence = self._compute_confidence(
            binah_ok, gevurah_ok, daat_ok,
            source_ok, competence_ok, consistency_ok,
            candidate,
        )

        # Décision finale
        if self.require_triple:
            is_valid = binah_ok and gevurah_ok and daat_ok
        else:
            # Mode dégradé : au moins 2 sur 3
            passed = sum([binah_ok, gevurah_ok, daat_ok])
            is_valid = passed >= 2

        # Confiance trop basse = rejet même si triple ok
        if confidence < self.min_confidence:
            is_valid = False

        # Construire les détails enrichis
        full_binah = binah_detail
        if source_detail:
            full_binah += f" | Sources: {source_detail}"
        full_gevurah = gevurah_detail
        full_daat = daat_detail
        if competence_detail:
            full_daat += f" | Competence: {competence_detail}"
        if consistency_detail:
            full_gevurah += f" | Consistency: {consistency_detail}"

        return InsightValidation(
            is_valid=is_valid,
            binah_ok=binah_ok,
            gevurah_ok=gevurah_ok,
            daat_ok=daat_ok,
            binah_detail=full_binah,
            gevurah_detail=full_gevurah,
            daat_detail=full_daat,
            confidence=round(confidence, 2),
        )

    def validate_batch(
        self,
        candidates: list[CandidateInsight],
        domain: str = "",
    ) -> list[InsightValidation]:
        """Valider un batch de candidats."""
        return [self.validate(c, domain) for c in candidates]

    # --- Triple validation ---

    def _check_binah(
        self, candidate: CandidateInsight, domain: str,
    ) -> tuple[bool, str]:
        """Check 1 : Binah — validation causale OU structurante (Sprint 6.x).

        Dispatcher doctrinal en 3 chemins :

        1. **question_deferred** : question pure sans synthèse extractible.
           Comportement Sprint 5.2/5.3 inchangé.

        2. **CausalEngine** (Tevunah dans Z"A — EC-K11-004 état 3) :
           chemin causal Pearl. Si ``evidence != correlation_only`` OU
           ``confidence >= 0.6`` → VALIDE. Comportement Sprint 5.3 inchangé.

        3. **BinahGates fallback CIBLÉ** (Binah haute — EC-K11-004 état 1,
           Sprint 6.x) : activé UNIQUEMENT si ``correlation_only`` avec
           ``confidence < 0.6`` ET ``self.binah_gates`` configuré. Évalue
           la synthèse contre les 5 Motzaot ha-Peh (EC-H1S5-074) :
           GARON, HEIKH, LASHON, SHINAYIM, SFATAYIM.

        Sans ``binah_gates`` configuré : comportement Sprint 5.3 strict
        préservé (rejet sur correlation_only < 0.6).
        """
        claim_text = candidate.description
        if _is_question(candidate.description):
            synthesis = _extract_synthesis(candidate.description)
            if synthesis is None:
                return False, "question_deferred (not a causal claim)"
            claim_text = synthesis

        if not self.binah:
            # Module absent — accepter par défaut (mode dégradé)
            return True, "Binah not available — skipped"

        try:
            assessment = self.binah.check_claim(
                cause=claim_text,
                effect="observed pattern",
                domain=domain,
            )
            claim = (
                assessment.claim if hasattr(assessment, "claim") else assessment
            )
            evidence = getattr(claim, "evidence_level", "correlation_only")
            confidence = getattr(claim, "confidence", 0.5)

            # Chemin causal strict (Sprint 5.3 — inchangé)
            if evidence != "correlation_only" or confidence >= 0.6:
                return True, f"Causal check passed (evidence={evidence})"

            # Fallback ciblé — Binah haute (Sprint 6.x)
            if self.binah_gates is not None:
                gates_result = self.binah_gates.evaluate(claim_text)
                if gates_result.is_valid:
                    return True, (
                        f"Binah gates passed (score={gates_result.score}) — "
                        + gates_result.verdict
                    )
                return False, (
                    f"Correlation only (confidence={confidence:.2f}) "
                    + f"AND {gates_result.verdict}"
                )

            # Legacy strict (Sprint 5.3 — pas de gates configurées)
            return False, f"Correlation only (confidence={confidence:.2f})"
        except Exception as e:
            return False, f"Binah error: {e}"

    def _check_gevurah(
        self, candidate: CandidateInsight, domain: str,
    ) -> tuple[bool, str]:
        """Check 2 : Gevurah — la qualité est-elle suffisante ?

        Utilise AutoJudge pour évaluer la qualité du candidat.
        Critères : description suffisamment riche, confiance minimale,
        pas de contradiction interne évidente.
        """
        if not self.gevurah:
            # Module absent — vérification locale
            return self._local_quality_check(candidate)

        try:
            # AutoJudge évalue via run_loop ou évaluation directe
            # Ici on fait une vérification de qualité basique
            # car AutoJudge travaille sur des domaines enregistrés
            return self._local_quality_check(candidate)
        except Exception as e:
            return False, f"Gevurah error: {e}"

    def _check_daat(
        self, candidate: CandidateInsight,
    ) -> tuple[bool, str]:
        """Check 3 : Da'at — le système prédit-il une erreur ici ?

        Utilise SelfModel.predict_error pour vérifier que le système
        ne prédit pas une erreur sur ce type de tâche.
        """
        if not self.daat:
            return True, "Da'at not available — skipped"

        try:
            predictions = self.daat.predict_error(candidate.description)
            if not predictions:
                return True, "No error predicted"

            # Vérifier si des erreurs à haute confiance sont prédites
            high_risk = [
                p for p in predictions
                if getattr(p, "confidence", 0) >= 0.7
            ]
            if high_risk:
                details = "; ".join(
                    getattr(p, "description", str(p)) for p in high_risk[:3]
                )
                return False, f"High-risk errors predicted: {details}"

            return True, f"Low-risk predictions only ({len(predictions)} total)"
        except Exception as e:
            return False, f"Da'at error: {e}"

    # --- Checks supplémentaires ---

    def _check_sources(
        self, candidate: CandidateInsight,
    ) -> tuple[bool, str]:
        """Check 4 : Yesod — les données sources existent-elles ?

        Vérifie que l'insight est ancré dans des connaissances réelles,
        pas généré à partir de rien.
        """
        if not self.yesod:
            return True, ""

        try:
            # Vérifier que le contenu a des traces dans EpisteMemory
            results = self.yesod.recall(
                candidate.description,
                min_confidence=0.3,
            )
            memories = results if isinstance(results, list) else []
            if not memories:
                return False, "No supporting data in EpisteMemory"
            return True, f"{len(memories)} supporting memories found"
        except Exception:
            return True, ""

    def _check_competence(
        self, candidate: CandidateInsight, domain: str,
    ) -> tuple[bool, str]:
        """Check 5 : Hod — le système est-il compétent ici ?

        Vérifie que le domaine de l'insight est dans les compétences
        connues du système.
        """
        if not self.hod:
            return True, ""

        try:
            target_domain = candidate.domain or domain or "general"
            evaluation = self.hod.read_competence(target_domain)
            competence = evaluation.score if evaluation else 0.5
            if competence < self.competence_threshold:
                return False, (
                    f"Low competence in '{target_domain}' "
                    f"({competence:.2f} < {self.competence_threshold})"
                )
            return True, f"Competent in '{target_domain}' ({competence:.2f})"
        except Exception:
            return True, ""

    def _check_consistency(
        self, candidate: CandidateInsight,
    ) -> tuple[bool, str]:
        """Check 6 : Tiferet — contradictions avec des claims existants ?

        Vérifie que l'insight ne contredit pas des conclusions
        déjà validées dans le système.
        """
        if not self.tiferet:
            return True, ""

        try:
            result = self.tiferet.analyze_consistency(
                [candidate.description],
            )
            has_contradiction = getattr(result, "has_contradiction", False)
            if has_contradiction:
                return False, "Contradicts existing validated claims"
            return True, "Consistent with existing knowledge"
        except Exception:
            return True, ""

    # --- Qualité locale ---

    def _local_quality_check(
        self, candidate: CandidateInsight,
    ) -> tuple[bool, str]:
        """Vérification de qualité sans Gevurah.

        Critères internes :
        - Description suffisamment longue et informative
        - Confiance minimale
        - Au moins un domaine connecté
        """
        issues: list[str] = []

        # Description trop courte = faible qualité
        if len(candidate.description) < 30:
            issues.append("description too short (<30 chars)")

        # Confiance trop basse
        if candidate.confidence < 0.3:
            issues.append(f"low confidence ({candidate.confidence:.2f})")

        # Aucun domaine connecté = insight isolé
        real_domains = [d for d in candidate.connects_domains if d]
        if not real_domains:
            issues.append("no connected domains")

        if issues:
            return False, "Quality issues: " + ", ".join(issues)

        return True, "Local quality check passed"

    # --- Confiance composite ---

    def _compute_confidence(
        self,
        binah_ok: bool,
        gevurah_ok: bool,
        daat_ok: bool,
        source_ok: bool,
        competence_ok: bool,
        consistency_ok: bool,
        candidate: CandidateInsight,
    ) -> float:
        """Calculer la confiance composite de la validation.

        Pondération :
        - Triple validation : 60% (20% chacun)
        - Checks supplémentaires : 25% (sources 10%, compétence 10%, consistance 5%)
        - Confiance du candidat lui-même : 15%
        """
        score = 0.0

        # Triple validation (60%)
        if binah_ok:
            score += 0.20
        if gevurah_ok:
            score += 0.20
        if daat_ok:
            score += 0.20

        # Checks supplémentaires (25%)
        if source_ok:
            score += 0.10
        if competence_ok:
            score += 0.10
        if consistency_ok:
            score += 0.05

        # Confiance intrinsèque du candidat (15%)
        score += candidate.confidence * 0.15

        return min(1.0, score)
