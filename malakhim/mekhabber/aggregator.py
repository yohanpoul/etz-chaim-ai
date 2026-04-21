"""Mekhabber — Agrégateur synthétique (pattern Sandalphon).

מְחַבֵּר — Celui qui relie, qui compose. Sandalphon tresse des couronnes
à partir des prières d'Israël (Chagigah 13b). Le verbe est קושר (qosher).

Pas de concaténation. Pas de résumé. Du TRESSAGE :
chaque contribution conserve son identité tout en étant intégrée
dans une forme nouvelle — le Keter (couronne).

La base (Malkuth/Sandalphon) produit le sommet (Keter).
C'est le hitkalelut en acte.

3 modes :
  weighted     — synthèse pondérée par score de compétence
  dialectical  — thèse/antithèse/synthèse explicite
  hierarchical — les agents de rang supérieur priment
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Contribution:
    """Une contribution d'un Malakh à la synthèse."""
    agent_id: str
    response: str
    score: float = 0.5
    olam: str = "yetzirah"
    domain: str = "general"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SynthesisResult:
    """Résultat du tressage — le Keter produit par Sandalphon."""
    synthesis: str
    mode: str
    convergences: list[str] = field(default_factory=list)
    divergences: list[str] = field(default_factory=list)
    contributions_used: int = 0
    confidence: float = 0.0


OLAM_RANK = {"atziluth": 4, "briah": 3, "yetzirah": 2, "assiah": 1}


class Mekhabber:
    """מְחַבֵּר — Agrégateur synthétique.

    Tresse les contributions de multiples Malakhim en une synthèse
    qui préserve les tensions au lieu de les moyenner.
    """

    def __init__(self, generate_fn: Callable[[str], str] | None = None):
        """
        Args:
            generate_fn: fonction optionnelle pour la synthèse LLM (mode dialectical).
                         Signature: (prompt: str) -> str
                         Si None, le mode dialectical fait une synthèse structurée sans LLM.
        """
        self._generate = generate_fn

    def synthesize(
        self,
        query: str,
        contributions: list[Contribution],
        mode: str = "weighted",
    ) -> SynthesisResult:
        """Synthétiser les contributions de plusieurs Malakhim.

        Args:
            query: la question originale
            contributions: les réponses des Malakhim
            mode: "weighted" | "dialectical" | "hierarchical"
        """
        if not contributions:
            return SynthesisResult(
                synthesis="", mode=mode, contributions_used=0, confidence=0.0
            )

        divergences = self.detect_divergences(contributions)
        convergences = self.detect_convergences(contributions)

        if mode == "weighted":
            synthesis = self._weighted(contributions)
        elif mode == "dialectical":
            synthesis = self._dialectical(query, contributions, convergences, divergences)
        elif mode == "hierarchical":
            synthesis = self._hierarchical(contributions)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        # Confiance = moyenne pondérée des scores
        total_score = sum(c.score for c in contributions)
        confidence = total_score / len(contributions) if contributions else 0.0

        return SynthesisResult(
            synthesis=synthesis,
            mode=mode,
            convergences=convergences,
            divergences=divergences,
            contributions_used=len(contributions),
            confidence=confidence,
        )

    def detect_divergences(self, contributions: list[Contribution]) -> list[str]:
        """Détecter les divergences entre contributions.

        Heuristique simple : compare les mots-clés significatifs.
        Deux contributions divergent si elles ont peu de mots communs.
        """
        if len(contributions) < 2:
            return []

        divergences = []
        for i in range(len(contributions)):
            for j in range(i + 1, len(contributions)):
                a_words = set(contributions[i].response.lower().split())
                b_words = set(contributions[j].response.lower().split())
                # Filtrer les mots courts (< 4 chars)
                a_sig = {w for w in a_words if len(w) >= 4}
                b_sig = {w for w in b_words if len(w) >= 4}

                if not a_sig or not b_sig:
                    continue

                overlap = len(a_sig & b_sig)
                union = len(a_sig | b_sig)
                jaccard = overlap / union if union else 0

                if jaccard < 0.2:  # Moins de 20% de mots communs
                    divergences.append(
                        f"{contributions[i].agent_id} vs {contributions[j].agent_id}: "
                        f"low overlap ({jaccard:.1%})"
                    )

        return divergences

    def detect_convergences(self, contributions: list[Contribution]) -> list[str]:
        """Détecter les convergences entre contributions."""
        if len(contributions) < 2:
            return []

        convergences = []
        # Trouver les mots-clés présents dans TOUTES les contributions
        keyword_sets = []
        for c in contributions:
            words = {w.lower() for w in c.response.split() if len(w) >= 5}
            keyword_sets.append(words)

        if keyword_sets:
            common = keyword_sets[0]
            for ks in keyword_sets[1:]:
                common = common & ks

            if common:
                convergences.append(
                    f"all {len(contributions)} agents agree on: {', '.join(sorted(list(common)[:5]))}"
                )

        return convergences

    def _weighted(self, contributions: list[Contribution]) -> str:
        """Synthèse pondérée : contributions ordonnées par score.

        Le tressage préserve chaque voix avec son poids.
        """
        sorted_c = sorted(contributions, key=lambda c: c.score, reverse=True)
        parts = []
        for c in sorted_c:
            parts.append(f"[{c.agent_id} | score={c.score:.2f} | {c.olam}]\n{c.response}")
        return "\n\n---\n\n".join(parts)

    def _dialectical(
        self,
        query: str,
        contributions: list[Contribution],
        convergences: list[str],
        divergences: list[str],
    ) -> str:
        """Synthèse dialectique : thèse/antithèse/synthèse.

        Si generate_fn est disponible, utilise un LLM pour la synthèse.
        Sinon, produit une structure dialectique sans LLM.
        """
        if len(contributions) < 2:
            return contributions[0].response if contributions else ""

        # Sélectionner thèse (meilleur score) et antithèse (plus divergent)
        sorted_c = sorted(contributions, key=lambda c: c.score, reverse=True)
        thesis = sorted_c[0]
        antithesis = sorted_c[-1] if len(sorted_c) > 1 else sorted_c[0]

        if self._generate:
            prompt = (
                f"QUESTION: {query}\n\n"
                f"THÈSE ({thesis.agent_id}, score={thesis.score:.2f}):\n{thesis.response}\n\n"
                f"ANTITHÈSE ({antithesis.agent_id}, score={antithesis.score:.2f}):\n{antithesis.response}\n\n"
            )
            if convergences:
                prompt += f"CONVERGENCES: {'; '.join(convergences)}\n\n"
            if divergences:
                prompt += f"DIVERGENCES: {'; '.join(divergences)}\n\n"
            prompt += "SYNTHÈSE (préserve les tensions, ne moyennise pas) :"
            return self._generate(prompt)

        # Sans LLM : synthèse structurée
        parts = [
            f"## Thèse ({thesis.agent_id})\n{thesis.response}",
            f"## Antithèse ({antithesis.agent_id})\n{antithesis.response}",
        ]
        if convergences:
            parts.append(f"## Convergences\n" + "\n".join(f"- {c}" for c in convergences))
        if divergences:
            parts.append(f"## Divergences\n" + "\n".join(f"- {d}" for d in divergences))

        # Ajouter les contributions intermédiaires
        middle = sorted_c[1:-1] if len(sorted_c) > 2 else []
        if middle:
            parts.append(f"## Contributions additionnelles")
            for c in middle:
                parts.append(f"### {c.agent_id} (score={c.score:.2f})\n{c.response}")

        return "\n\n".join(parts)

    def _hierarchical(self, contributions: list[Contribution]) -> str:
        """Synthèse hiérarchique : les agents de rang supérieur priment.

        L'Olam détermine le rang. Atziluth > Briah > Yetzirah > Assiah.
        """
        sorted_c = sorted(
            contributions,
            key=lambda c: OLAM_RANK.get(c.olam, 0),
            reverse=True,
        )

        if not sorted_c:
            return ""

        # Le premier (rang le plus élevé) a le dernier mot
        primary = sorted_c[0]
        parts = [f"[Décision : {primary.agent_id} ({primary.olam})]\n{primary.response}"]

        if len(sorted_c) > 1:
            parts.append("\n[Contributions subordonnées]")
            for c in sorted_c[1:]:
                parts.append(f"- {c.agent_id} ({c.olam}): {c.response[:200]}...")

        return "\n".join(parts)
