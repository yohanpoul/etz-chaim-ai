"""HitbonenutJudge — AutoJudge pour les réponses Hitbonenut.

Gevurah évalue les réponses de l'Arbre : 880 Q&A en DB,
175 à score < 0.5. Ce DomainJudge:
1. Tire un échantillon de réponses récentes
2. Évalue chaque réponse via métriques heuristiques
3. Identifie les domaines faibles
4. Propose des hypothèses d'amélioration

Loss function: qualité multi-axe (keywords, longueur, diversité,
pertinence, structure kabbalistique).
"""

from __future__ import annotations

import re
from collections import Counter

from autojudge.domains.base import DomainJudge
from autojudge.models import DomainScore


# Termes techniques kabbalistiques — présence = signe de profondeur
KABBALISTIC_TERMS = {
    "sefirot", "sephirot", "sefirah", "keter", "chokmah", "binah",
    "chesed", "gevurah", "tiferet", "netzach", "hod", "yesod", "malkuth",
    "tzimtzum", "shevirah", "tikkun", "partzuf", "partzufim",
    "ein sof", "reshimu", "kav", "kelim", "ohr", "nitzotzot",
    "zohar", "luria", "vital", "cordovero", "abulafia",
    "atik", "arikh", "abba", "imma", "zeir", "nukva",
    "zivug", "mochin", "gadlut", "katnut", "masakh",
    "atziluth", "briah", "yetzirah", "assiah",
    "gematria", "tzeruf", "notarikon", "temurah",
    "nefesh", "ruach", "neshamah", "chaya", "yechidah",
    "klipah", "klipot", "qliphah", "qliphoth", "sitra achra",
}

# Domaines et leurs keywords (repris de hitbonenut.py pour cohérence)
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "kabbale_lurianique": [
        "tzimtzum", "shevirah", "tikkun", "partzuf", "luria", "vital",
        "reshimu", "kav", "nitzotzot", "birur", "masakh", "kelim", "ohr",
    ],
    "sefer_yetzirah": [
        "231", "portes", "lettres mères", "aleph", "mem", "shin",
        "belimah", "sefirot", "teli", "galgal", "yetzirah",
    ],
    "gematria": [
        "mispar", "at-bash", "notarikon", "temurah", "gematria",
        "valeur", "tetragramme",
    ],
    "partzufim": [
        "atik", "arikh", "abba", "imma", "zeir", "nukva",
        "zivug", "mochin", "gadlut", "katnut",
    ],
    "olamot": [
        "atziluth", "briah", "yetzirah", "assiah",
        "émanation", "parsah", "hishtalshelut",
    ],
    "hishtalshelut": [
        "hishtalshelut", "chaîne", "émanation", "compression",
        "malkuth-keter", "parsah", "bottleneck",
    ],
    "tzimtzum": [
        "tzimtzum", "contraction", "halal", "reshimu", "kav",
        "tanya", "din", "limitation",
    ],
}


def _get_words(text: str) -> list[str]:
    return re.findall(r'\b[a-zA-ZÀ-ÿ]+\b', text.lower())


def _split_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


class HitbonenutJudge(DomainJudge):
    """Évalue les réponses Hitbonenut — la loss de Gevurah appliquée à l'Arbre.

    Métriques:
    - kabbalistic_depth: densité de termes techniques kabbalistiques
    - domain_keywords: précision des keywords spécifiques au domaine
    - structure: organisation textuelle (paragraphes, connecteurs)
    - diversity: richesse lexicale (TTR)
    - relevance: pertinence par rapport à la question
    - length: longueur suffisante pour une réponse érudite
    """

    def __init__(self, domain: str | None = None):
        self.target_domain = domain
        self._current_question: str = ""
        self._current_domain: str = domain or "general"

    def set_context(self, question: str, domain: str):
        """Fixer la question et le domaine pour l'évaluation courante."""
        self._current_question = question
        self._current_domain = domain

    def compute_metrics(self, response: str) -> dict[str, float]:
        """Calculer toutes les métriques de qualité."""
        if not response or not response.strip() or "[erreur" in response:
            return {
                "kabbalistic_depth": 0.0, "domain_keywords": 0.0,
                "structure": 0.0, "diversity": 0.0,
                "relevance": 0.0, "length": 0.0,
            }

        words = _get_words(response)
        response_lower = response.lower()
        word_count = len(words)

        # 1. Profondeur kabbalistique (30%) — densité de termes techniques
        found_terms = sum(1 for t in KABBALISTIC_TERMS if t in response_lower)
        # 5 termes = bon, 10+ = excellent
        kab_depth = min(found_terms / 8.0, 1.0)

        # 2. Keywords domaine (25%) — termes spécifiques au domaine
        domain_kws = DOMAIN_KEYWORDS.get(self._current_domain, [])
        if domain_kws:
            found_kw = sum(1 for kw in domain_kws if kw.lower() in response_lower)
            kw_score = min(found_kw / max(len(domain_kws) * 0.4, 1), 1.0)
        else:
            kw_score = 0.5

        # 3. Structure (15%) — paragraphes, connecteurs, listes
        paragraphs = [p for p in response.split("\n\n") if p.strip()]
        has_headers = bool(re.search(r'\*\*[^*]+\*\*|\#{1,3}\s', response))
        has_lists = bool(re.search(r'^\s*[-*•]\s|^\s*\d+\.', response, re.MULTILINE))
        connectors = sum(
            1 for w in words
            if w in {"cependant", "donc", "néanmoins", "toutefois",
                      "notamment", "ainsi", "enfin", "premièrement",
                      "deuxièmement", "ensuite", "furthermore", "moreover"}
        )
        structure = min(
            (len(paragraphs) > 1) * 0.3
            + has_headers * 0.2
            + has_lists * 0.2
            + min(connectors / 3, 1.0) * 0.3,
            1.0,
        )

        # 4. Diversité lexicale (10%) — TTR
        if word_count > 10:
            unique = len(set(words))
            ttr = unique / word_count
            diversity = min(ttr / 0.45, 1.0)
        else:
            diversity = 0.0

        # 5. Pertinence (10%) — mots de la question dans la réponse
        q_words = set(
            w.lower() for w in self._current_question.split() if len(w) > 3
        )
        if q_words:
            q_found = sum(1 for w in q_words if w in response_lower)
            relevance = min(q_found / max(len(q_words) * 0.4, 1), 1.0)
        else:
            relevance = 0.5

        # 6. Longueur (10%) — paliers: 50=0.3, 100=0.6, 200+=1.0
        if word_count >= 200:
            length = 1.0
        elif word_count >= 50:
            length = 0.3 + 0.7 * (word_count - 50) / 150
        else:
            length = word_count / 170

        return {
            "kabbalistic_depth": round(max(0, min(kab_depth, 1)), 4),
            "domain_keywords": round(max(0, min(kw_score, 1)), 4),
            "structure": round(max(0, min(structure, 1)), 4),
            "diversity": round(max(0, min(diversity, 1)), 4),
            "relevance": round(max(0, min(relevance, 1)), 4),
            "length": round(max(0, min(length, 1)), 4),
        }

    def compute_quality(self, metrics: dict[str, float]) -> float:
        """Score global pondéré."""
        weights = {
            "kabbalistic_depth": 0.30,
            "domain_keywords": 0.25,
            "structure": 0.15,
            "diversity": 0.10,
            "relevance": 0.10,
            "length": 0.10,
        }
        return round(sum(metrics[k] * weights[k] for k in weights), 4)

    def generate_hypothesis(self, current_state: str) -> str:
        """Analyser la réponse et proposer une amélioration."""
        metrics = self.compute_metrics(current_state)
        weaknesses: list[tuple[float, str]] = []

        if metrics["kabbalistic_depth"] < 0.4:
            weaknesses.append((
                metrics["kabbalistic_depth"],
                "Enrichir avec des termes techniques kabbalistiques "
                "(Sefirot, Partzufim, Olamot, etc.)",
            ))
        if metrics["domain_keywords"] < 0.5:
            weaknesses.append((
                metrics["domain_keywords"],
                f"Ajouter les concepts clés du domaine '{self._current_domain}'",
            ))
        if metrics["structure"] < 0.4:
            weaknesses.append((
                metrics["structure"],
                "Structurer avec des paragraphes, titres, et connecteurs logiques",
            ))
        if metrics["diversity"] < 0.5:
            weaknesses.append((
                metrics["diversity"],
                "Diversifier le vocabulaire pour éviter les répétitions",
            ))
        if metrics["relevance"] < 0.5:
            weaknesses.append((
                metrics["relevance"],
                "Recentrer sur la question posée et y répondre directement",
            ))
        if metrics["length"] < 0.5:
            weaknesses.append((
                metrics["length"],
                "Développer la réponse avec plus de détails et d'exemples",
            ))

        if not weaknesses:
            return "Réponse de qualité suffisante — explorer un angle nouveau"

        weaknesses.sort(key=lambda x: x[0])
        return weaknesses[0][1]

    def apply_modification(self, content: str, hypothesis: str) -> str:
        """Annoter la réponse avec la suggestion d'amélioration."""
        return f"{content}\n\n[Gevurah suggère: {hypothesis}]"

    def evaluate(self, original: str, modified: str) -> DomainScore:
        """Évaluer la qualité absolue de la réponse (pas relative)."""
        metrics = self.compute_metrics(original)
        quality = self.compute_quality(metrics)

        explanation_parts = []
        for key, val in sorted(metrics.items(), key=lambda x: x[1]):
            if val < 0.5:
                explanation_parts.append(f"{key}={val:.2f}⚠")
            else:
                explanation_parts.append(f"{key}={val:.2f}✓")

        return DomainScore(
            quality=quality,
            metrics=metrics,
            explanation=", ".join(explanation_parts),
        )

    def get_loss_description(self) -> str:
        return (
            "Hitbonenut quality: kabbalistic_depth (0.30), domain_keywords (0.25), "
            "structure (0.15), diversity (0.10), relevance (0.10), length (0.10). "
            "Higher is better."
        )
