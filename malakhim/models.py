"""Modèles de données — les structures du monde angélique."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable


class MalakhStage(str, Enum):
    """Stades IYM — calqués sur masakh/maturation.py."""
    IBUR = "ibur"
    YENIKAH = "yenikah"
    MOCHIN = "mochin"


class MalakhOrder(str, Enum):
    """Les 10 ordres angéliques (Maïmonide, Yesodei HaTorah 2:7).

    Du plus élevé au plus bas. Le terme malakhim (messagers)
    n'occupe que le 6ème rang — le mot générique pour « ange »
    ne désigne qu'une catégorie médiane.
    """
    CHAYYOT = "chayyot"        # 1. Vivants saints (Éz 1:5-14)
    OFANNIM = "ofannim"        # 2. Roues (Éz 1:15-21)
    ERELIM = "erelim"          # 3. Vaillants (Is 33:7 — quasi-hapax)
    CHASHMALIM = "chashmalim"  # 4. Silence-parole (Éz 1:4, Chagigah 13a)
    SERAFIM = "serafim"        # 5. Brûlants (Is 6:1-7)
    MALAKHIM = "malakhim"      # 6. Messagers
    ELOHIM = "elohim"          # 7. Puissances
    BNE_ELOHIM = "bne_elohim"  # 8. Fils des Puissances
    KERUVIM = "keruvim"        # 9. Chérubins (Gen 3:24, Ex 25:18-22)
    ISHIM = "ishim"            # 10. Êtres humanoïdes (Dan 10:5-6)


# ── Hiérarchies alternatives (§2.8 — la divergence EST un fait) ───────────────
# « La hiérarchisation est un ACTE THÉOLOGIQUE, pas une donnée révélée. »

HIERARCHY_RAMBAM: list[str] = [
    "chayyot", "ofannim", "erelim", "chashmalim", "serafim",
    "malakhim", "elohim", "bne_elohim", "keruvim", "ishim",
]
"""Maïmonide (Yesodei HaTorah 2:7) : intellection pure au sommet."""

HIERARCHY_ZOHAR: list[str] = [
    "malakhim", "erelim", "serafim", "chayyot", "ofannim",
    "chashmalim", "elohim", "bne_elohim", "keruvim", "ishim",
]
"""Zohar II:43a : la shelichut (mission/messagerie) au sommet.
Pour le Zohar, la FIDÉLITÉ DE TRANSMISSION est l'essence de
l'angélicité — pas la pureté d'intellection."""

HIERARCHY_RESHIT_CHOKHMAH: list[str] = [
    "chayyot", "ofannim", "serafim", "keruvim", "erelim",
    "chashmalim", "elohim", "malakhim", "bne_elohim", "ishim",
]
"""Reshit Chokhmah (Eliyahu de Vidas) : synthèse Cordovero."""


def rank_in_hierarchy(
    order: str,
    hierarchy: list[str] | None = None,
) -> int:
    """Rang d'un ordre dans une hiérarchie donnée (1 = plus haut).

    Par défaut : hiérarchie de Maïmonide (HIERARCHY_RAMBAM).
    Passer HIERARCHY_ZOHAR pour la priorité messagerie.

    La possibilité de CHOISIR la hiérarchie est le point :
    « Chaque auteur construit sa hiérarchie selon ses présupposés »
    (MALAKHIM.md §2.8).
    """
    hier = hierarchy or HIERARCHY_RAMBAM
    try:
        return hier.index(order) + 1
    except ValueError:
        return len(hier) + 1  # inconnu → rang le plus bas


@dataclass
class MalakhResult:
    """Résultat d'une exécution de Malakh."""
    response: str
    success: bool
    score: float = 0.0
    latency_ms: float = 0.0
    hitkalelut_warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    incomplete: bool = False
    """Tanya ch. 39 : une mitzvah sans kavvanah produit un ange de
    « matière » sans « forme » — un ange INCOMPLET. Ni succès ni
    échec : une entité difforme qui pollue le système.
    Un MalakhResult avec incomplete=True est techniquement fonctionnel
    mais creux, hors sujet, ou superficiel. Il accumule une dette
    ontologique distincte du Kategor (échec franc)."""


@dataclass
class FailurePattern:
    """Kategor — un accusateur persistant."""
    pattern_id: int
    agent_id: str | None
    domain: str
    error_type: str
    prompt_keywords: list[str]
    prompt_excerpt: str | None
    score: float | None
    active: bool = True
    occurrences: int = 1
    tikkun_description: str | None = None
    created_at: datetime | None = None
    last_seen: datetime | None = None
    resolved_at: datetime | None = None


@dataclass
class SuccessPattern:
    """Praklite — un défenseur réutilisable."""
    pattern_id: int
    agent_id: str | None
    domain: str
    strategy_used: str | None
    kavvanah: dict[str, Any] | None
    score: float
    reuse_count: int = 0
    created_at: datetime | None = None
    last_reused: datetime | None = None


@dataclass
class AgentProfile:
    """Profil Pekidah — compétences + stade IYM d'un agent."""
    agent_id: str
    domains: list[str]
    stage: MalakhStage
    total_tasks: int = 0
    scores: dict[str, float] = field(default_factory=dict)


# ── Nouveaux modèles — Refonte Kavvanah / Heikhalot ──────────────────────────


@dataclass
class KavvanahGrade:
    """Résultat de l'évaluation de la kavvanah (intention).

    Tanya ch. 39-40 : kavvanah pleine → Sephiroth directement (pas d'ange) ;
    kavvanah incomplète → crée des anges dans Yetzirah.
    """
    score: float          # 0.0–1.0
    tier: str             # "high" | "medium" | "low"
    missing: list[str] = field(default_factory=list)  # ce qui manque


@dataclass
class ValidationSpec:
    """Spécification de validation taillée pour une mission.

    Le Malakh EST sa mission — sa structure de validation est
    façonnée par ce qu'il doit accomplir, pas générique.
    """
    anti_patterns: list[str] = field(default_factory=list)
    required_structure: list[str] = field(default_factory=list)
    min_length: int = 0
    max_repetition_ratio: float = 0.5


@dataclass
class HeikhalotResult:
    """Résultat du pipeline ascendant des 7 Heikhalot.

    Chaque palais enrichit la requête. Le résultat contient
    la kavvanah enrichie, le system prompt généré, et la
    spécification de validation — tout ce qu'il faut pour
    engendrer un Malakh unique.
    """
    approved: bool
    enriched_kavvanah: dict[str, Any] = field(default_factory=dict)
    system_prompt: str = ""
    shem_index: int | None = None
    validation_spec: ValidationSpec | None = None
    warnings: list[str] = field(default_factory=list)
    stages_passed: list[str] = field(default_factory=list)
