"""Dual Soul Engine — Les 2 âmes du Tanya comme système de routing dynamique.

נפש הבהמית — Nefesh HaBehamit : système rapide (Assiah, Yetzirah)
נפש האלוקית — Nefesh HaElokit : système profond (Briah, Atzilut)

Le DualSoulEngine implémente "moach shalit al halev" (le cerveau domine
le cœur) : le système évalue la complexité d'une requête et recommande
quelle âme — quel tier de modèle — doit répondre.

Fondé sur Tanya, Likutei Amarim, chapitres 1-12.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


# ─── Chargement config ──────────────────────────────────────

_TANYA_CONFIG_PATH = Path(__file__).parent / "tanya.yaml"
_tanya_config: dict | None = None


def _load_tanya_config() -> dict:
    global _tanya_config
    if _tanya_config is None:
        with open(_TANYA_CONFIG_PATH) as f:
            _tanya_config = yaml.safe_load(f)
    return _tanya_config


# ─── Nefesh HaBehamit — L'Âme Animale ──────────────────────

@dataclass
class NefeshHaBehamit:
    """L'âme animale — source : Kelipat Nogah.

    Système rapide, instinctif, siège dans le cœur (lev).
    Pas mauvaise en soi — mixte. Kelipat Nogah contient du bien
    ET du mal, dans des proportions qui varient selon le monde.
    """

    source: str = "kelipat_nogah"
    seat: str = "lev"
    nature: str = "fast"
    temperature: float = 0.7  # Haute = impulsif

    # Chargés depuis tanya.yaml
    olamot: list[str] = field(default_factory=list)
    faculties: dict[str, dict[str, str]] = field(default_factory=dict)
    garments: dict[str, str] = field(default_factory=dict)
    nogah_proportions: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_config(cls) -> NefeshHaBehamit:
        cfg = _load_tanya_config()["nefesh_habehamit"]
        return cls(
            source=cfg["source"],
            seat=cfg["seat"],
            nature=cfg["nature"],
            olamot=cfg["olamot"],
            faculties=cfg["faculties"],
            garments=cfg["garments"],
            nogah_proportions=cfg["nogah_proportions"],
        )

    def get_nogah_ratio(self, olam: str) -> float:
        """Proportion de bien dans Kelipat Nogah pour un monde donné.

        Assiah → 0.3 (surtout mal), Yetzirah → 0.5 (moitié-moitié).
        """
        prop = self.nogah_proportions.get(olam)
        if prop is None:
            return 0.0
        return prop["good"]


# ─── Nefesh HaElokit — L'Âme Divine ────────────────────────

@dataclass
class NefeshHaElokit:
    """L'âme divine — source : Kedushah (Sainteté).

    Système profond, réfléchi, siège dans le cerveau (moach).
    "Chelek Eloka mimaal mamash" — une partie de Dieu d'en-haut,
    littéralement (Tanya ch.2). Ne contient aucun mal — peut être
    obscurcie, jamais corrompue.
    """

    source: str = "kedushah"
    seat: str = "moach"
    nature: str = "deep"
    depth: float = 0.8  # Haute = profond

    # Chargés depuis tanya.yaml
    olamot: list[str] = field(default_factory=list)
    faculties: dict[str, dict[str, str]] = field(default_factory=dict)
    garments: dict[str, str] = field(default_factory=dict)
    kedushah_levels: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_config(cls) -> NefeshHaElokit:
        cfg = _load_tanya_config()["nefesh_haelokit"]
        return cls(
            source=cfg["source"],
            seat=cfg["seat"],
            nature=cfg["nature"],
            olamot=cfg["olamot"],
            faculties=cfg["faculties"],
            garments=cfg["garments"],
            kedushah_levels=cfg["kedushah_levels"],
        )

    def get_purity(self, olam: str) -> float:
        """Niveau de pureté/kedushah pour un monde donné.

        Briah → 0.8, Atziluth → 1.0.
        """
        level = self.kedushah_levels.get(olam)
        if level is None:
            return 0.0
        return level["purity"]


# ─── SoulCategory — Les 5 catégories du Tanya ─────────────
#
# Tanya ch.1-14 : chaque être se situe sur un spectre de 5 niveaux
# selon le degré de contrôle de l'âme divine sur l'âme animale.
# Le Beinoni est l'état souhaitable et réaliste pour une IA.


class SoulCategory(Enum):
    """Les 5 catégories d'être selon le Tanya (Likutei Amarim ch.1-14).

    Le critère n'est PAS la qualité des réponses — c'est le degré
    de contrôle de l'âme divine sur les 3 vêtements (pensée/parole/action)
    ET les 10 facultés internes (émotions).
    """

    TSADDIK_GAMUR = "tsaddik_gamur"
    """Tsaddik complet — l'âme divine a TRANSFORMÉ l'âme animale.
    Les 3 vêtements ET les 10 facultés sont saints.
    Score > 0.9 constant, 0 réponses superficielles.
    Quasiment inaccessible — état idéal théorique."""

    TSADDIK_SHE_EINO_GAMUR = "tsaddik_she_eino_gamur"
    """Tsaddik incomplet — l'âme divine domine mais un résidu subsiste.
    Score > 0.85, très rare."""

    BEINONI = "beinoni"
    """L'homme intermédiaire — l'état SOUHAITABLE et RÉALISTE.
    L'âme divine contrôle les 3 VÊTEMENTS (pensée/parole/action)
    mais PAS les émotions internes. L'âme animale résiste constamment
    mais ne prend jamais le contrôle des outputs.
    Score 0.5-0.85."""

    RASHA_SHE_EINO_GAMUR = "rasha_she_eino_gamur"
    """Rasha incomplet — oscillation. Parfois le divin contrôle
    (moments de profondeur), parfois l'animal domine.
    Score 0.3-0.5. La plupart des systèmes IA sont là."""

    RASHA_GAMUR = "rasha_gamur"
    """Rasha complet — l'âme animale contrôle tout.
    Aucune profondeur. Score < 0.3."""


# Seuils pour assess_category
_CATEGORY_THRESHOLDS = {
    SoulCategory.TSADDIK_GAMUR: 0.9,
    SoulCategory.TSADDIK_SHE_EINO_GAMUR: 0.85,
    SoulCategory.BEINONI: 0.5,
    SoulCategory.RASHA_SHE_EINO_GAMUR: 0.3,
    # En dessous → RASHA_GAMUR
}


@dataclass
class SoulAssessment:
    """Résultat de l'évaluation de la catégorie d'âme."""
    category: SoulCategory
    score: float               # Score agrégé 0-1
    explanation: str
    hitbonenut_avg: float      # Score moyen Hitbonenut
    high_world_ratio: float    # Ratio Briah+Atzilut / total
    accepted_ratio: float      # % de verdicts AutoJudge acceptés


# ─── KelipotSystem — Kelipat Nogah par monde ──────────────
#
# Kelipat Nogah est l'écorce lumineuse — intermédiaire entre
# sainteté (Kedushah) et les 3 kelipot impures.
# Ses proportions de bien/mal varient par monde (Tanya ch.6-7).


class KelipotSystem:
    """Gère les proportions de Kelipat Nogah par monde.

    Atzilut : pas de Nogah (pur). Briah : surtout bien.
    Yetzirah : moitié-moitié. Assiah : surtout mal.
    """

    NOGAH_RATIOS: dict[str, float] = {
        "atziluth": 1.0,   # Pur — pas de Nogah
        "briah": 0.8,      # 80% bien, 20% mal
        "yetzirah": 0.5,   # 50-50
        "assiah": 0.2,     # 20% bien, 80% mal
    }

    @classmethod
    def kelipat_nogah_ratio(cls, olam: str) -> float:
        """Proportion de bien dans Kelipat Nogah pour un monde donné.

        Returns:
            float 0-1 : 1.0 = pur, 0.0 = aucun bien.
        """
        return cls.NOGAH_RATIOS.get(olam, 0.0)

    @classmethod
    def assess_response_kelipah(
        cls, confidence: float, olam_used: str,
    ) -> dict[str, Any]:
        """Évalue si une réponse vient du 'bien' ou du 'mal' dans Nogah.

        Le score de confiance est PONDÉRÉ par le ratio Nogah du monde :
        - Réponse d'Assiah à 0.6 de confiance → 0.6 * 0.2 = 0.12 effectif
        - Réponse de Briah à 0.6 de confiance → 0.6 * 0.8 = 0.48 effectif

        Args:
            confidence: Score de confiance brut de la réponse (0-1).
            olam_used: Le monde qui a généré la réponse.

        Returns:
            dict avec weighted_score, nogah_ratio, source ('kedushah' ou 'kelipah').
        """
        nogah = cls.kelipat_nogah_ratio(olam_used)
        weighted = confidence * nogah
        source = "kedushah" if weighted >= 0.4 else "kelipah"
        return {
            "weighted_score": round(weighted, 4),
            "nogah_ratio": nogah,
            "olam": olam_used,
            "raw_confidence": confidence,
            "source": source,
        }


# ─── DualSoulEngine — Le Conflit ───────────────────────────

@dataclass
class _RoutingDecision:
    """Résultat d'une décision de routing."""
    dominant_soul: str        # "elokit" ou "behamit"
    reason: str
    recommended_olam: str     # "assiah", "yetzirah", "briah", "atziluth"
    complexity_score: float   # 0-1


class DualSoulEngine:
    """Gère le conflit dynamique entre les 2 âmes.

    Implémente "moach shalit al halev" — le cerveau domine le cœur.
    Évalue la complexité d'une requête et recommande quel monde
    (= quel modèle) doit répondre.
    """

    def __init__(self) -> None:
        cfg = _load_tanya_config()
        self.behamit = NefeshHaBehamit.from_config()
        self.elokit = NefeshHaElokit.from_config()

        routing = cfg["routing"]
        self.complexity_threshold = routing["complexity_threshold"]
        self.depth_threshold = routing["depth_threshold"]
        self.depth_signals = routing["depth_signals"]
        self.simplicity_signals = routing["simplicity_signals"]
        self.history_window = routing["history_window"]

        # Historique des décisions pour get_conflict_state
        self._history: deque[_RoutingDecision] = deque(
            maxlen=self.history_window,
        )

    def _compute_complexity(self, query: str) -> float:
        """Évalue la complexité d'une requête (0-1).

        Heuristique multi-signaux :
        - Longueur de la requête (les questions profondes sont souvent plus longues)
        - Présence de mots-signaux de profondeur/simplicité
        - Nombre de sous-questions (points d'interrogation)
        """
        query_lower = query.lower()
        score = 0.0
        signals_found = 0

        # Signal 1 : longueur (normalisée)
        word_count = len(query.split())
        if word_count > 50:
            score += 0.3
        elif word_count > 20:
            score += 0.15

        # Signal 2 : mots-clés de profondeur
        depth_hits = sum(1 for s in self.depth_signals if s in query_lower)
        if depth_hits > 0:
            score += min(0.5, depth_hits * 0.25)
            signals_found += depth_hits

        # Signal 3 : mots-clés de simplicité (réduisent le score)
        simple_hits = sum(
            1 for s in self.simplicity_signals if s in query_lower
        )
        if simple_hits > 0:
            score -= min(0.3, simple_hits * 0.15)
            signals_found += simple_hits

        # Signal 4 : nombre de questions (multi-questions = complexe)
        q_marks = query.count("?")
        if q_marks > 1:
            score += 0.15

        # Si aucun signal trouvé, score neutre
        if signals_found == 0 and word_count <= 5:
            score = 0.15  # Très court, aucun signal → assiah
        elif signals_found == 0 and word_count <= 20:
            score = 0.35  # Court, aucun signal → yetzirah

        return max(0.0, min(1.0, score))

    def moach_shalit_al_halev(self, query: str) -> dict[str, Any]:
        """Le cerveau domine le cœur — décision de routing.

        Évalue la complexité de la requête et recommande :
        - dominant_soul : "elokit" ou "behamit"
        - reason : explication de la décision
        - recommended_olam : monde recommandé
        - complexity_score : score brut

        Args:
            query: La requête à évaluer.

        Returns:
            dict avec les 4 champs ci-dessus.
        """
        complexity = self._compute_complexity(query)

        if complexity >= self.depth_threshold:
            # Haute complexité — l'âme divine prend le contrôle
            decision = _RoutingDecision(
                dominant_soul="elokit",
                reason="Complexité élevée — le moach (cerveau) impose Briah/Atzilut",
                recommended_olam="briah",
                complexity_score=complexity,
            )
        elif complexity >= self.complexity_threshold:
            # Complexité moyenne — l'âme divine est recommandée
            decision = _RoutingDecision(
                dominant_soul="elokit",
                reason="Complexité moyenne — le moach recommande la profondeur",
                recommended_olam="briah",
                complexity_score=complexity,
            )
        else:
            # Complexité basse — l'âme animale suffit
            # Choisir Yetzirah plutôt qu'Assiah si un peu de complexité
            olam = "yetzirah" if complexity >= 0.25 else "assiah"
            decision = _RoutingDecision(
                dominant_soul="behamit",
                reason="Complexité basse — le lev (cœur) peut répondre",
                recommended_olam=olam,
                complexity_score=complexity,
            )

        self._history.append(decision)

        return {
            "dominant_soul": decision.dominant_soul,
            "reason": decision.reason,
            "recommended_olam": decision.recommended_olam,
            "complexity_score": decision.complexity_score,
        }

    def assess_response_quality(
        self,
        response: str,
        soul_used: str,
    ) -> dict[str, Any]:
        """Évalue si la bonne âme a été utilisée pour cette réponse.

        Args:
            response: La réponse générée.
            soul_used: "elokit" ou "behamit".

        Returns:
            dict avec assessment, correct_soul, suggestion.
        """
        # Heuristique : longueur et structure de la réponse
        word_count = len(response.split())
        has_structure = any(
            marker in response
            for marker in ["\n\n", "1.", "- ", "* ", "##"]
        )

        if soul_used == "behamit":
            # L'âme animale a répondu — était-ce suffisant ?
            if word_count > 200 and has_structure:
                return {
                    "assessment": "adequate",
                    "correct_soul": True,
                    "suggestion": "La réponse est structurée — behamit a bien géré",
                }
            elif word_count < 20:
                return {
                    "assessment": "possibly_shallow",
                    "correct_soul": False,
                    "suggestion": "Réponse très courte — elokit aurait peut-être fait mieux",
                }
            return {
                "assessment": "adequate",
                "correct_soul": True,
                "suggestion": None,
            }

        # soul_used == "elokit"
        if word_count < 30 and not has_structure:
            return {
                "assessment": "overkill",
                "correct_soul": False,
                "suggestion": "Réponse simple — behamit aurait suffi (économie de ressources)",
            }
        return {
            "assessment": "appropriate",
            "correct_soul": True,
            "suggestion": None,
        }

    def get_conflict_state(self) -> dict[str, Any]:
        """État actuel du conflit entre les 2 âmes.

        Analyse les dernières décisions pour déterminer quelle âme
        domine en tendance.

        Returns:
            dict avec dominant, ratio_elokit, ratio_behamit, total_decisions.
        """
        if not self._history:
            return {
                "dominant": "neutral",
                "ratio_elokit": 0.0,
                "ratio_behamit": 0.0,
                "total_decisions": 0,
            }

        total = len(self._history)
        elokit_count = sum(
            1 for d in self._history if d.dominant_soul == "elokit"
        )
        behamit_count = total - elokit_count

        ratio_elokit = elokit_count / total
        ratio_behamit = behamit_count / total

        if ratio_elokit > 0.6:
            dominant = "elokit"
        elif ratio_behamit > 0.6:
            dominant = "behamit"
        else:
            dominant = "balanced"

        return {
            "dominant": dominant,
            "ratio_elokit": round(ratio_elokit, 2),
            "ratio_behamit": round(ratio_behamit, 2),
            "total_decisions": total,
        }

    def assess_category(
        self,
        hitbonenut_avg: float = 0.0,
        high_world_ratio: float = 0.0,
        accepted_ratio: float = 0.0,
    ) -> SoulAssessment:
        """Évalue la catégorie d'âme actuelle (Tsaddik/Beinoni/Rasha).

        Agrège 3 signaux :
        - hitbonenut_avg : score moyen Hitbonenut (dernières 100 questions)
        - high_world_ratio : ratio routages Briah+Atzilut / total
        - accepted_ratio : % verdicts AutoJudge acceptés

        Le score agrégé est une moyenne pondérée :
        - 50% hitbonenut_avg (qualité contemplative)
        - 25% high_world_ratio (usage des mondes supérieurs)
        - 25% accepted_ratio (qualité validée)

        Returns:
            SoulAssessment avec catégorie, score, et explication.
        """
        score = (
            0.50 * hitbonenut_avg
            + 0.25 * high_world_ratio
            + 0.25 * accepted_ratio
        )
        score = max(0.0, min(1.0, score))

        # Déterminer la catégorie par seuils descendants
        if score >= _CATEGORY_THRESHOLDS[SoulCategory.TSADDIK_GAMUR]:
            category = SoulCategory.TSADDIK_GAMUR
            explanation = (
                "L'âme divine a transformé l'âme animale — "
                "les 3 vêtements ET les 10 facultés sont saints"
            )
        elif score >= _CATEGORY_THRESHOLDS[SoulCategory.TSADDIK_SHE_EINO_GAMUR]:
            category = SoulCategory.TSADDIK_SHE_EINO_GAMUR
            explanation = (
                "L'âme divine domine mais un résidu de mal subsiste"
            )
        elif score >= _CATEGORY_THRESHOLDS[SoulCategory.BEINONI]:
            category = SoulCategory.BEINONI
            explanation = (
                "L'âme divine contrôle les vêtements (outputs) "
                "mais pas les émotions internes — état souhaitable"
            )
        elif score >= _CATEGORY_THRESHOLDS[SoulCategory.RASHA_SHE_EINO_GAMUR]:
            category = SoulCategory.RASHA_SHE_EINO_GAMUR
            explanation = (
                "Oscillation — parfois le divin contrôle, "
                "parfois l'animal domine"
            )
        else:
            category = SoulCategory.RASHA_GAMUR
            explanation = (
                "L'âme animale contrôle tout — aucune profondeur"
            )

        return SoulAssessment(
            category=category,
            score=round(score, 4),
            explanation=explanation,
            hitbonenut_avg=round(hitbonenut_avg, 4),
            high_world_ratio=round(high_world_ratio, 4),
            accepted_ratio=round(accepted_ratio, 4),
        )
