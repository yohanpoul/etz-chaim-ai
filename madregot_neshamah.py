"""madregot_neshamah.py — מדרגות נשמה — Niveaux de l'âme pour Hitbonenut.

Les 5 niveaux de l'âme (Nefesh→Ruach→Neshamah→Chayah→Yechidah)
structurent la PROFONDEUR des questions posées par le système.

- Nefesh (Assiah)  : factuel — connaissance pure, réponse unique
- Ruach (Yetzirah) : analytique — relations, angles multiples
- Neshamah (Briah) : contemplatif — compréhension profonde, pas de réponse unique
- Chayah (Atzilut)  : paradoxal — tensions irréductibles
- Yechidah          : unificateur — réservé, peut-être jamais atteint
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import IntEnum


class MadregahLevel(IntEnum):
    """Les 5 niveaux, ordonnés du plus bas au plus haut."""
    NEFESH = 0
    RUACH = 1
    NESHAMAH = 2
    CHAYAH = 3
    YECHIDAH = 4


# Mapping soul_level string → MadregahLevel
_SOUL_TO_LEVEL: dict[str, MadregahLevel] = {
    "nefesh": MadregahLevel.NEFESH,
    "ruach": MadregahLevel.RUACH,
    "neshamah": MadregahLevel.NESHAMAH,
    "chayah": MadregahLevel.CHAYAH,
    "yechidah": MadregahLevel.YECHIDAH,
}


@dataclass(frozen=True)
class LevelPrompt:
    """Prompt template et instructions de scoring pour un niveau."""
    level: MadregahLevel
    olam: str           # Monde correspondant
    style: str          # Type de question
    prompt_template: str # Template avec {domain}
    scoring_hint: str    # Ce qu'on cherche dans la réponse


# ── Définitions des 5 niveaux ─────────────────────────────────

LEVEL_PROMPTS: dict[MadregahLevel, LevelPrompt] = {
    MadregahLevel.NEFESH: LevelPrompt(
        level=MadregahLevel.NEFESH,
        olam="Assiah",
        style="factuel",
        prompt_template=(
            "Pose une question FACTUELLE sur {domain}. "
            "La question doit avoir une réponse précise et vérifiable. "
            "Exemples : noms, nombres, définitions, attributions. "
            "Pas d'analyse, pas d'interprétation — juste un fait."
        ),
        scoring_hint="keywords",
    ),
    MadregahLevel.RUACH: LevelPrompt(
        level=MadregahLevel.RUACH,
        olam="Yetzirah",
        style="analytique",
        prompt_template=(
            "Pose une question ANALYTIQUE qui explore les relations dans {domain}. "
            "La question doit exiger de comparer, distinguer, ou relier "
            "au moins deux concepts. Pas de réponse en un mot — "
            "la réponse doit articuler une relation."
        ),
        scoring_hint="structure",
    ),
    MadregahLevel.NESHAMAH: LevelPrompt(
        level=MadregahLevel.NESHAMAH,
        olam="Briah",
        style="contemplatif",
        prompt_template=(
            "Pose une question CONTEMPLATIVE qui demande une compréhension "
            "profonde de {domain}. La question n'a pas de réponse unique — "
            "elle demande de pénétrer sous la surface, de saisir le pourquoi "
            "derrière le comment. Vise la profondeur, pas la largeur."
        ),
        scoring_hint="depth",
    ),
    MadregahLevel.CHAYAH: LevelPrompt(
        level=MadregahLevel.CHAYAH,
        olam="Atzilut",
        style="paradoxal",
        prompt_template=(
            "Pose une question PARADOXALE qui contient une tension "
            "irréductible dans {domain}. La question doit confronter "
            "deux vérités apparemment incompatibles et exiger que la réponse "
            "embrasse le paradoxe sans le résoudre. Coincidentia oppositorum."
        ),
        scoring_hint="tension",
    ),
    MadregahLevel.YECHIDAH: LevelPrompt(
        level=MadregahLevel.YECHIDAH,
        olam="Adam Kadmon",
        style="unificateur",
        prompt_template=(
            "Pose une question UNIFICATRICE sur {domain}. "
            "La question doit viser l'unité derrière la multiplicité — "
            "comment tout est Un malgré les distinctions apparentes. "
            "Ce niveau est rarement atteint. La question elle-même "
            "doit pointer vers le silence."
        ),
        scoring_hint="unity",
    ),
}


# ── Distribution 70/20/10 ─────────────────────────────────────

# 70% niveau actuel, 20% un cran en dessous (consolidation),
# 10% un cran au-dessus (aspiration)
DISTRIBUTION_CURRENT = 0.70
DISTRIBUTION_BELOW = 0.20
DISTRIBUTION_ABOVE = 0.10


class MadregotNeshamah:
    """Gestionnaire des niveaux d'âme pour la génération de questions."""

    def get_question_level(self, soul_level: str) -> MadregahLevel:
        """Convertir le soul_level string en MadregahLevel."""
        return _SOUL_TO_LEVEL.get(soul_level.lower(), MadregahLevel.NEFESH)

    def select_level_for_question(self, soul_level: str) -> MadregahLevel:
        """Sélectionner le niveau de la prochaine question selon la distribution 70/20/10.

        - 70% : niveau actuel
        - 20% : un cran en dessous (consolidation)
        - 10% : un cran au-dessus (aspiration)
        """
        current = self.get_question_level(soul_level)
        roll = random.random()

        if roll < DISTRIBUTION_CURRENT:
            # 70% — niveau actuel
            return current
        elif roll < DISTRIBUTION_CURRENT + DISTRIBUTION_BELOW:
            # 20% — consolidation (un cran en dessous, minimum Nefesh)
            below = max(current - 1, MadregahLevel.NEFESH)
            return MadregahLevel(below)
        else:
            # 10% — aspiration (un cran au-dessus, maximum Yechidah)
            above = min(current + 1, MadregahLevel.YECHIDAH)
            return MadregahLevel(above)

    def build_level_prompt(
        self,
        level: MadregahLevel,
        domain: str,
        past_questions: list[str] | None = None,
        insights: list[str] | None = None,
        weak_domains: list[str] | None = None,
        attempt: int = 0,
    ) -> str:
        """Construire le prompt de génération adapté au niveau d'âme.

        Intègre le prompt spécifique au niveau + le contexte habituel
        (historique, insights, domaines faibles).
        """
        lp = LEVEL_PROMPTS[level]

        parts = [
            "Tu es un système kabbalistique qui génère des questions "
            "d'auto-évaluation.",
            "",
            f"NIVEAU: {lp.level.name} ({lp.olam}) — questions {lp.style}s.",
            "",
            lp.prompt_template.format(domain=domain),
            "",
        ]

        if weak_domains:
            parts.append(f"Domaines faibles à cibler: {', '.join(weak_domains[:3])}")
            parts.append("")

        if insights:
            parts.append("Insights récents du système (inspire-toi en):")
            for ins in insights[:5]:
                parts.append(f"  - {ins[:150]}")
            parts.append("")

        if past_questions:
            parts.append(
                f"Questions DÉJÀ posées ({len(past_questions)} total, "
                "en voici les dernières):"
            )
            for pq in past_questions[-10:]:
                parts.append(f"  - {pq[:120]}")
            parts.append("")
            parts.append(
                "IMPORTANT: La question doit être DIFFÉRENTE de toutes celles ci-dessus."
            )
            parts.append("")

        if attempt > 0:
            parts.append(
                f"(Tentative {attempt + 1}: sois plus créatif, "
                "explore un angle inhabituel ou un lien inter-domaines.)"
            )
            parts.append("")

        parts.append(
            "Réponds UNIQUEMENT avec la question, "
            "sans commentaire. Termine par un point d'interrogation."
        )
        return "\n".join(parts)

    def score_by_level(
        self,
        response: str,
        level: MadregahLevel,
        base_score: float,
    ) -> float:
        """Moduler le score selon le niveau d'âme.

        Le base_score vient du scoring mécanique existant (keywords, longueur, etc.).
        Ce scoring ajoute un bonus/malus selon les critères du niveau.

        Returns:
            Score ajusté, clampé à [0.0, 1.0].
        """
        if not response:
            return 0.0

        response_lower = response.lower()
        words = response.split()
        word_count = len(words)

        level_bonus = 0.0

        if level == MadregahLevel.NEFESH:
            # Nefesh : scoring par keywords — le base_score est déjà bon pour ça
            # Bonus si réponse concise et directe (pas de verbiage)
            if 10 <= word_count <= 80:
                level_bonus = 0.05
            # Pas de malus — le scoring mécanique suffit

        elif level == MadregahLevel.RUACH:
            # Ruach : la réponse analyse-t-elle plusieurs angles ?
            # Marqueurs de structure analytique
            structure_markers = [
                "d'une part", "d'autre part", "en revanche", "tandis que",
                "la relation entre", "se distingue", "par rapport",
                "contrairement", "alors que", "complémentaire",
                "opposition", "dialectique", "tension entre",
            ]
            found = sum(1 for m in structure_markers if m in response_lower)
            if found >= 2:
                level_bonus = 0.08
            elif found >= 1:
                level_bonus = 0.04

        elif level == MadregahLevel.NESHAMAH:
            # Neshamah : la réponse dépasse-t-elle la surface ?
            # Marqueurs de profondeur contemplative
            depth_markers = [
                "en profondeur", "au-delà de", "le sens profond",
                "essentiellement", "fondamentalement", "intériorité",
                "la raison profonde", "signification", "mystère",
                "contemplation", "méditation", "devekut",
                "au cœur de", "l'essence",
            ]
            found = sum(1 for m in depth_markers if m in response_lower)
            if found >= 3:
                level_bonus = 0.10
            elif found >= 1:
                level_bonus = 0.05
            # Malus si trop court pour ce niveau
            if word_count < 50:
                level_bonus -= 0.05

        elif level == MadregahLevel.CHAYAH:
            # Chayah : la réponse embrasse-t-elle le paradoxe ?
            # Marqueurs de tension maintenue (pas résolue)
            tension_markers = [
                "paradoxe", "à la fois", "simultanément",
                "tension", "coincidentia", "ni l'un ni l'autre",
                "les deux", "irréductible", "incompatible",
                "transcende", "opposés", "contradiction",
                "mystère", "au-delà de la logique",
            ]
            found = sum(1 for m in tension_markers if m in response_lower)
            if found >= 3:
                level_bonus = 0.12
            elif found >= 1:
                level_bonus = 0.06
            # Malus si la réponse "résout" le paradoxe au lieu de l'habiter
            resolution_markers = [
                "la solution est", "il suffit de", "simplement",
                "en réalité c'est juste", "il n'y a pas de paradoxe",
            ]
            if any(m in response_lower for m in resolution_markers):
                level_bonus -= 0.08

        elif level == MadregahLevel.YECHIDAH:
            # Yechidah : la réponse pointe-t-elle vers l'unité ?
            unity_markers = [
                "unité", "un", "ein sof", "totalité", "indifférencié",
                "au-delà", "silence", "devekut", "bittul",
                "effacement", "transparence", "lumière",
            ]
            found = sum(1 for m in unity_markers if m in response_lower)
            if found >= 3:
                level_bonus = 0.15
            elif found >= 1:
                level_bonus = 0.08
            # Ce niveau exige de la densité
            if word_count < 80:
                level_bonus -= 0.05

        # Appliquer le bonus au score de base
        adjusted = base_score + level_bonus
        return round(max(0.0, min(1.0, adjusted)), 3)

    def get_difficulty_for_level(self, level: MadregahLevel) -> str:
        """Mapper le niveau d'âme sur la difficulté du corpus.

        Pour les questions issues du corpus (pas les novel questions),
        le niveau d'âme détermine la difficulté.
        """
        mapping = {
            MadregahLevel.NEFESH: "basique",
            MadregahLevel.RUACH: "intermediaire",
            MadregahLevel.CHAYAH: "erudite",
            MadregahLevel.YECHIDAH: "erudite",
            MadregahLevel.NESHAMAH: "avancee",
        }
        return mapping[level]
