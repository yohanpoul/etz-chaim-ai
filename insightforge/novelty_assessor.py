"""NoveltyAssessor — évaluer si un insight est genuinement nouveau.

Anti-Ghagiel Nogah : trop d'insights "nouveaux" = inflation.
Anti-Ghagiel Ruach : les mêmes insights qui reviennent = boucle.

Un insight est genuinement NOUVEAU si :
  1. Pas déjà dans EpisteMemory
  2. Pas une reformulation d'un fait connu
  3. Pas une conclusion triviale des données
  4. Connecte des concepts de domaines différents de manière non évidente
  5. Résiste à la vérification causale (Binah)
"""

from __future__ import annotations

import re

from insightforge.models import CandidateInsight, NoveltyAssessment

# Regex d'extraction des "content words" : alphabétique (accent FR-aware),
# 3+ char, insensible à la casse via .lower() upstream. Remplace la
# naïve `.split()` qui gardait la ponctuation attachée ("structures."
# ≠ "structures" → stop words inopérants). Cf Sprint megaclean T4 / Dette 9.
_WORD_RE = re.compile(r"\b[a-zA-ZÀ-ÿ]{3,}\b")


# Seuils
DEFAULT_MIN_NOVELTY = 0.45          # Score minimum pour "genuinely new" (abaissé de 0.7 — Tikkun Ghagiel)
DEFAULT_SIMILARITY_THRESHOLD = 0.82 # Seuil Jaccard (relevé de 0.65 — anti-faux positifs kabbalistiques)
DEFAULT_TRIVIAL_THRESHOLD = 0.3     # En-dessous = trivial

# Stop words pour le Jaccard — boilerplate qui pollue la similarité
_STOP_WORDS = frozenset({
    # Préfixes de source
    "hitbonenut", "insight", "insight:", "fti", "cross-domain",
    "opportunity", "pattern", "warning", "opportunity:",
    "pattern:", "warning:", "cross-domain:",
    # Mots grammaticaux FR
    "le", "la", "les", "un", "une", "des", "de", "du", "d'",
    "et", "ou", "en", "est", "sont", "a", "à", "au", "aux",
    "ce", "cette", "ces", "que", "qui", "quoi", "dans", "par",
    "pour", "sur", "avec", "sans", "entre", "plus", "moins",
    "pas", "ne", "se", "il", "elle", "on", "nous", "vous",
    "leur", "son", "sa", "ses", "mon", "ma", "mes", "ton",
    "ta", "tes", "être", "avoir", "faire", "dit", "fait",
    # Mots grammaticaux EN
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall",
    "of", "in", "to", "for", "with", "on", "at", "from", "by",
    "about", "as", "into", "through", "during", "before", "after",
    "above", "below", "between", "out", "off", "over", "under",
    "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "each", "every", "both", "few",
    "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "just",
    "because", "but", "and", "or", "if", "while", "that", "this",
    "these", "those", "it", "its", "my", "your", "his", "her",
    "their", "our", "what", "which", "who", "whom",
    # Boilerplate domaine
    "quelle", "quelles", "quel", "quels", "comment", "pourquoi",
    "relation", "différence", "—",
    # Boilerplate kabbalistique (cause faux positifs Jaccard)
    "sephirah", "sephiroth", "kabbale", "kabbalistique", "connexion",
    "domaine", "analyse", "structure", "concept", "processus",
    "systeme", "module", "niveau", "principe",
})


class NoveltyAssessor:
    """Évalue si un insight candidat est genuinement nouveau.

    Le filtre de Chokmah : seul ce qui est VRAIMENT nouveau
    mérite le titre d'insight. Le reste est du recyclage.
    """

    def __init__(
        self,
        min_novelty: float = DEFAULT_MIN_NOVELTY,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        existing_knowledge: list[str] | None = None,
        past_insights: list[str] | None = None,
    ):
        self.min_novelty = min_novelty
        self.similarity_threshold = similarity_threshold
        self.existing_knowledge = existing_knowledge or []
        self.past_insights = past_insights or []

    def assess(self, candidate: CandidateInsight) -> NoveltyAssessment:
        """Évaluer la nouveauté d'un candidat.

        Returns:
            NoveltyAssessment avec le score et les raisons.
        """
        already_known = self._is_already_known(candidate)
        is_reformulation = self._is_reformulation(candidate)
        is_trivial = self._is_trivial(candidate)
        is_cross_domain = self._is_cross_domain(candidate)

        # Score de novelty
        score = self._compute_novelty_score(
            already_known, is_reformulation, is_trivial, is_cross_domain,
            candidate,
        )

        is_new = (
            not already_known
            and not is_reformulation
            and not is_trivial
            and score >= self.min_novelty
        )

        reasoning = self._build_reasoning(
            already_known, is_reformulation, is_trivial,
            is_cross_domain, score,
        )

        return NoveltyAssessment(
            is_genuinely_new=is_new,
            already_known=already_known,
            is_reformulation=is_reformulation,
            is_trivial=is_trivial,
            is_cross_domain=is_cross_domain,
            novelty_score=round(score, 2),
            reasoning=reasoning,
        )

    def assess_batch(
        self, candidates: list[CandidateInsight],
    ) -> list[NoveltyAssessment]:
        """Évaluer un batch de candidats — avec dédup inter-candidats."""
        assessments: list[NoveltyAssessment] = []
        seen_descriptions: list[str] = list(self.past_insights)

        for candidate in candidates:
            # Vérifier si ce candidat est un doublon d'un précédent dans le batch
            is_dup = self._matches_any(candidate.description, seen_descriptions)

            if is_dup:
                assessments.append(NoveltyAssessment(
                    is_genuinely_new=False,
                    is_reformulation=True,
                    novelty_score=0.0,
                    reasoning="Duplicate of earlier candidate in this batch",
                ))
            else:
                assessment = self.assess(candidate)
                assessments.append(assessment)

            seen_descriptions.append(candidate.description)

        return assessments

    def _is_already_known(self, candidate: CandidateInsight) -> bool:
        """L'insight est-il déjà dans la base de connaissances ?"""
        return self._matches_any(candidate.description, self.existing_knowledge)

    def _is_reformulation(self, candidate: CandidateInsight) -> bool:
        """L'insight est-il une reformulation d'un insight passé ?"""
        return self._matches_any(candidate.description, self.past_insights)

    def _is_trivial(self, candidate: CandidateInsight) -> bool:
        """L'insight est-il une conclusion triviale ?

        Critères de trivialité :
        - Description trop courte
        - Confidence trop basse
        - Ne connecte aucun domaine
        """
        if len(candidate.description) < 20:
            return True
        if candidate.confidence < DEFAULT_TRIVIAL_THRESHOLD:
            return True
        return False

    def _is_cross_domain(self, candidate: CandidateInsight) -> bool:
        """L'insight connecte-t-il des domaines différents ?"""
        domains = [d for d in candidate.connects_domains if d]
        unique_domains = set(domains)
        return len(unique_domains) >= 2

    def _compute_novelty_score(
        self,
        already_known: bool,
        is_reformulation: bool,
        is_trivial: bool,
        is_cross_domain: bool,
        candidate: CandidateInsight,
    ) -> float:
        """Calculer le score de novelty."""
        if already_known:
            return 0.0
        if is_reformulation:
            return 0.1
        if is_trivial:
            return 0.2

        score = 0.5  # Base

        # Bonus cross-domain
        if is_cross_domain:
            score += 0.2

        # Bonus confiance du candidat
        score += candidate.confidence * 0.15

        # Bonus description riche
        if len(candidate.description) > 100:
            score += 0.1

        # Bonus triple validation
        validated = sum([
            candidate.binah_validated,
            candidate.gevurah_validated,
            candidate.daat_validated,
        ])
        score += validated * 0.05

        return min(1.0, score)

    def _matches_any(self, text: str, corpus: list[str]) -> bool:
        """Vérifier si le texte matche un élément du corpus.

        Jaccard sur les mots significatifs (stop words filtrés)
        pour éviter les faux positifs sur le boilerplate partagé.

        Pré-Sprint T4 : `.split()` naïf attachait la ponctuation
        (ex: "structures." vs "structures") — les stop words
        devenaient inopérants sur les textes template générés par
        l'exploration (`"Both X and Y exhibit Z structures..."`),
        gonflant artificiellement la similarité Jaccard et flaggant
        81% des candidats comme `already_known` (novelty=0). Regex
        `\b[a-zA-ZÀ-ÿ]{3,}\b` extrait des content words propres.
        """
        if not corpus:
            return False

        text_words = set(_WORD_RE.findall(text.lower())) - _STOP_WORDS
        if not text_words:
            return False

        for existing in corpus:
            existing_words = set(_WORD_RE.findall(existing.lower())) - _STOP_WORDS
            if not existing_words:
                continue
            intersection = text_words & existing_words
            union = text_words | existing_words
            similarity = len(intersection) / len(union) if union else 0
            if similarity >= self.similarity_threshold:
                return True

        return False

    def _build_reasoning(
        self,
        already_known: bool,
        is_reformulation: bool,
        is_trivial: bool,
        is_cross_domain: bool,
        score: float,
    ) -> str:
        """Construire le raisonnement de l'évaluation."""
        parts: list[str] = []

        if already_known:
            parts.append("Already present in existing knowledge base")
        if is_reformulation:
            parts.append("Reformulation of a previously generated insight")
        if is_trivial:
            parts.append("Trivial — too short, low confidence, or single-domain")
        if is_cross_domain:
            parts.append("Cross-domain connection detected (positive signal)")

        parts.append(f"Novelty score: {score:.2f} (threshold: {self.min_novelty})")

        if score >= self.min_novelty and not already_known and not is_reformulation:
            parts.append("GENUINELY NEW — candidate passes novelty filter")
        else:
            parts.append("NOT NEW — candidate does not pass novelty filter")

        return "; ".join(parts)
