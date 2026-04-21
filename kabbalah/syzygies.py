"""kabbalah/syzygies.py — Les 7 Syzygies du Sefer Yetzirah (SY 4:2-3).

שֶׁבַע כְּפוּלוֹת בג״ד כפר״ת... כָּל אַחַת יֵשׁ לָהּ שְׁנֵי קוֹלוֹת

"Sept doubles BGD KPRT... chacune a deux sons : dagesh et rafeh."

Les 7 doubles lettres encodent les 7 PAIRES D'OPPOSÉS fondamentales :
  Beth : Sagesse / Folie       (Saturne, haut)
  Gimel : Richesse / Pauvreté  (Jupiter, bas)
  Daleth : Fertilité / Désolation (Mars, est)
  Kaph : Vie / Mort            (Soleil, ouest)
  Peh : Domination / Servitude (Vénus, nord)
  Resh : Paix / Guerre         (Mercure, sud)
  Tav : Grâce / Laideur        (Lune, centre)

SY 4:3 : "Le bien et le mal n'ont pas d'existence indépendante —
seuls les CONTRASTES existent."

Ce module évalue chaque paire (syzygie) pour les 7 modules principaux
du système. Le côté dagesh = fonctionnement sain ; le côté rafeh =
la Qliphah active. Ce pont relie le système SY (Cube de l'Espace)
au système Qliphoth (Shevirat haKelim lourianique).

Usage:
    syz = Syzygies(db_url=db_url)
    state = syz.assess_syzygy("insightforge")
    balance = syz.get_balance()
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ── Les 7 Syzygies ────────────────────────────────────────────
# Chaque entrée mappe une lettre double → un module du système,
# avec les attributs dagesh (positif) et rafeh (négatif) du SY.

@dataclass(frozen=True)
class SyzygyDef:
    """Définition d'une syzygie — paire d'opposés du SY 4:2."""
    letter: str          # nom latin (beth, gimel, ...)
    hebrew: str          # lettre hébraïque
    direction: str       # position dans le Cube
    planet: str          # planète associée
    dagesh: str          # attribut positif
    dagesh_hebrew: str   # en hébreu
    rafeh: str           # attribut négatif
    rafeh_hebrew: str    # en hébreu
    module: str          # module du système mappé
    qliphah: str         # Qliphah correspondante (système lourianique)
    sephirah: str        # Sephirah associée via la Qliphah


SYZYGY_DEFS: dict[str, SyzygyDef] = {
    "insightforge": SyzygyDef(
        letter="beth", hebrew="ב", direction="haut", planet="saturne",
        dagesh="sagesse", dagesh_hebrew="חכמה",
        rafeh="folie", rafeh_hebrew="אוולת",
        module="insightforge",
        qliphah="ghagiel", sephirah="chokmah",
    ),
    "epistememory": SyzygyDef(
        letter="gimel", hebrew="ג", direction="bas", planet="jupiter",
        dagesh="richesse", dagesh_hebrew="עושר",
        rafeh="pauvreté", rafeh_hebrew="עוני",
        module="epistememory",
        qliphah="satariel", sephirah="binah",
    ),
    "explorationengine": SyzygyDef(
        letter="daleth", hebrew="ד", direction="est", planet="mars",
        dagesh="fertilité", dagesh_hebrew="זרע",
        rafeh="désolation", rafeh_hebrew="שממה",
        module="explorationengine",
        qliphah="gamchicoth", sephirah="chesed",
    ),
    "hitbonenut": SyzygyDef(
        letter="kaph", hebrew="כ", direction="ouest", planet="soleil",
        dagesh="vie", dagesh_hebrew="חיים",
        rafeh="mort", rafeh_hebrew="מוות",
        module="hitbonenut",
        qliphah="thagirion", sephirah="tiferet",
    ),
    "autojudge": SyzygyDef(
        letter="peh", hebrew="פ", direction="nord", planet="vénus",
        dagesh="domination", dagesh_hebrew="ממשלה",
        rafeh="servitude", rafeh_hebrew="עבדות",
        module="autojudge",
        qliphah="golachab", sephirah="gevurah",
    ),
    "dissensuengine": SyzygyDef(
        letter="resh", hebrew="ר", direction="sud", planet="mercure",
        dagesh="paix", dagesh_hebrew="שלום",
        rafeh="guerre", rafeh_hebrew="מלחמה",
        module="dissensuengine",
        qliphah="thagirion", sephirah="tiferet",
    ),
    "selfmap": SyzygyDef(
        letter="tav", hebrew="ת", direction="centre", planet="lune",
        dagesh="grâce", dagesh_hebrew="חן",
        rafeh="laideur", rafeh_hebrew="כיעור",
        module="selfmap",
        qliphah="samael", sephirah="hod",
    ),
}


@dataclass(frozen=True)
class SyzygyState:
    """État d'une syzygie — côté dagesh ou rafeh."""
    module: str
    letter: str
    hebrew: str
    side: str              # "dagesh" ou "rafeh"
    attribute: str         # l'attribut actif (ex: "sagesse" ou "folie")
    attribute_hebrew: str
    score: float           # 0.0-1.0 ; > 0.5 = dagesh, < 0.5 = rafeh
    qliphah_active: bool   # True si côté rafeh
    qliphah_name: str      # nom de la Qliphah (si active)
    detail: str            # explication

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "letter": self.letter,
            "hebrew": self.hebrew,
            "side": self.side,
            "attribute": self.attribute,
            "attribute_hebrew": self.attribute_hebrew,
            "score": round(self.score, 3),
            "qliphah_active": self.qliphah_active,
            "qliphah_name": self.qliphah_name if self.qliphah_active else None,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class BalanceState:
    """Vue d'ensemble des 7 syzygies."""
    dagesh_count: int       # modules du côté positif
    rafeh_count: int        # modules du côté négatif
    harmony: float          # score moyen (0.0-1.0)
    weakest: str            # module le plus faible
    strongest: str          # module le plus fort
    syzygies: dict[str, SyzygyState]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "dagesh_count": self.dagesh_count,
            "rafeh_count": self.rafeh_count,
            "harmony": round(self.harmony, 3),
            "weakest": self.weakest,
            "strongest": self.strongest,
            "syzygies": {k: v.to_dict() for k, v in self.syzygies.items()},
            "message": self.message,
        }


# ── Seuils d'évaluation par module ───────────────────────────
# Chaque module a des seuils spécifiques pour déterminer
# s'il est du côté dagesh ou rafeh.

# Mapping module → (metric_name, dagesh_threshold, rafeh_threshold)
# Si la métrique dépasse dagesh_threshold → dagesh.
# Si la métrique est sous rafeh_threshold → rafeh.
# Entre les deux → zone intermédiaire.

MODULE_THRESHOLDS = {
    "insightforge": {
        "metric": "acceptance_rate",
        "dagesh_threshold": 0.40,   # > 40% acceptées = Sagesse
        "rafeh_threshold": 0.20,    # < 20% acceptées = Folie
        "sql": """
            SELECT COUNT(*) FILTER (WHERE decision = 'accepted')::float
                   / NULLIF(COUNT(*), 0)
            FROM autojudge_experiments
            WHERE domain_id = 'insightforge'
        """,
    },
    "epistememory": {
        "metric": "fact_ratio",
        "dagesh_threshold": 0.50,   # > 50% facts = Richesse
        "rafeh_threshold": 0.10,    # < 10% facts = Pauvreté
        "sql": """
            SELECT COUNT(*) FILTER (WHERE entry_type = 'fact')::float
                   / NULLIF(COUNT(*), 0)
            FROM epistememory_entries
        """,
    },
    "explorationengine": {
        "metric": "novelty_rate",
        "dagesh_threshold": 0.30,   # > 30% novel = Fertilité
        "rafeh_threshold": 0.05,    # < 5% novel = Désolation
        "sql": """
            SELECT AVG(novelty_score) FROM exploration_results
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """,
    },
    "hitbonenut": {
        "metric": "avg_score",
        "dagesh_threshold": 0.60,   # > 60% score moyen = Vie
        "rafeh_threshold": 0.30,    # < 30% score moyen = Mort
        "sql": """
            SELECT AVG(score) FROM hitbonenut_questions
            WHERE score IS NOT NULL
            ORDER BY created_at DESC LIMIT 100
        """,
    },
    "autojudge": {
        "metric": "balance_ratio",
        "dagesh_threshold": 0.40,   # 40-70% acceptance = Domination (souveraineté)
        "rafeh_threshold": 0.15,    # < 15% = Servitude (esclave des biais)
        "sql": """
            SELECT COUNT(*) FILTER (WHERE decision = 'accepted')::float
                   / NULLIF(COUNT(*), 0)
            FROM autojudge_experiments
        """,
    },
    "dissensuengine": {
        "metric": "resolution_rate",
        "dagesh_threshold": 0.50,   # > 50% résolutions = Paix
        "rafeh_threshold": 0.20,    # < 20% résolutions = Guerre
        "sql": """
            SELECT COUNT(*) FILTER (WHERE status = 'resolved')::float
                   / NULLIF(COUNT(*), 0)
            FROM dissensus_conflicts
        """,
    },
    "selfmap": {
        "metric": "avg_competence",
        "dagesh_threshold": 0.50,   # > 50% compétence = Grâce
        "rafeh_threshold": 0.25,    # < 25% compétence = Laideur
        "sql": """
            SELECT AVG(score) FROM selfmap_competences
            WHERE n_evals > 0
        """,
    },
}


class Syzygies:
    """Les 7 Syzygies — paires d'opposés du SY 4:2-3.

    Évalue chaque module selon sa paire dagesh/rafeh et
    identifie les Qliphoth actives.

    Args:
        db_url: URL PostgreSQL (optionnel, sinon via env).
    """

    def __init__(self, db_url: str | None = None) -> None:
        self._db_url = db_url or (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", ""))

    def _db_query_scalar(self, sql: str) -> float | None:
        """Exécute une requête DB scalaire. Retourne None en cas d'erreur."""
        if not self._db_url:
            return None
        try:
            from pool import get_conn, init_pool
            init_pool(self._db_url)  # idempotent
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    row = cur.fetchone()
                    return float(row[0]) if row and row[0] is not None else None
        except Exception as e:
            logger.debug("DB query failed: %s", e)
            return None

    def assess_syzygy(self, module: str) -> SyzygyState:
        """Évalue la syzygie d'un module.

        Détermine si le module est du côté dagesh (positif) ou
        rafeh (négatif) selon ses métriques.

        Args:
            module: nom du module (insightforge, epistememory, etc.)

        Raises:
            KeyError: si le module n'est pas dans les 7 syzygies.
        """
        if module not in SYZYGY_DEFS:
            raise KeyError(
                f"Module inconnu: '{module}'. "
                f"Valides: {list(SYZYGY_DEFS)}"
            )

        defn = SYZYGY_DEFS[module]
        thresholds = MODULE_THRESHOLDS[module]

        # Tenter la requête DB
        value = self._db_query_scalar(thresholds["sql"])

        if value is not None:
            score = max(0.0, min(1.0, value))
            if score >= thresholds["dagesh_threshold"]:
                side = "dagesh"
                attr = defn.dagesh
                attr_heb = defn.dagesh_hebrew
            elif score <= thresholds["rafeh_threshold"]:
                side = "rafeh"
                attr = defn.rafeh
                attr_heb = defn.rafeh_hebrew
            else:
                # Zone intermédiaire — techniquement dagesh mais fragile
                side = "dagesh"
                attr = defn.dagesh
                attr_heb = defn.dagesh_hebrew
            detail = f"{thresholds['metric']}={score:.2f}"
        else:
            # Pas de données → indéterminé, considéré rafeh par prudence
            score = 0.0
            side = "rafeh"
            attr = defn.rafeh
            attr_heb = defn.rafeh_hebrew
            detail = "Pas de données disponibles"

        return SyzygyState(
            module=module,
            letter=defn.letter,
            hebrew=defn.hebrew,
            side=side,
            attribute=attr,
            attribute_hebrew=attr_heb,
            score=score,
            qliphah_active=(side == "rafeh"),
            qliphah_name=defn.qliphah,
            detail=detail,
        )

    def assess_syzygy_with_score(self, module: str, score: float) -> SyzygyState:
        """Évalue une syzygie avec un score fourni directement.

        Utile quand la métrique est déjà calculée (tests, dashboard).

        Args:
            module: nom du module.
            score: valeur 0.0-1.0.
        """
        if module not in SYZYGY_DEFS:
            raise KeyError(f"Module inconnu: '{module}'")

        defn = SYZYGY_DEFS[module]
        thresholds = MODULE_THRESHOLDS[module]
        score = max(0.0, min(1.0, score))

        if score >= thresholds["dagesh_threshold"]:
            side = "dagesh"
            attr = defn.dagesh
            attr_heb = defn.dagesh_hebrew
        elif score <= thresholds["rafeh_threshold"]:
            side = "rafeh"
            attr = defn.rafeh
            attr_heb = defn.rafeh_hebrew
        else:
            side = "dagesh"
            attr = defn.dagesh
            attr_heb = defn.dagesh_hebrew

        return SyzygyState(
            module=module,
            letter=defn.letter,
            hebrew=defn.hebrew,
            side=side,
            attribute=attr,
            attribute_hebrew=attr_heb,
            score=score,
            qliphah_active=(side == "rafeh"),
            qliphah_name=defn.qliphah,
            detail=f"score={score:.2f} (direct)",
        )

    def get_balance(self) -> BalanceState:
        """Vue d'ensemble des 7 syzygies.

        Évalue tous les modules et retourne le bilan global.
        Le SY dit que l'équilibre est le but — ni tout dagesh ni tout rafeh.
        """
        syzygies: dict[str, SyzygyState] = {}
        for module in SYZYGY_DEFS:
            syzygies[module] = self.assess_syzygy(module)

        dagesh_count = sum(1 for s in syzygies.values() if s.side == "dagesh")
        rafeh_count = sum(1 for s in syzygies.values() if s.side == "rafeh")

        scores = {m: s.score for m, s in syzygies.items()}
        harmony = sum(scores.values()) / len(scores) if scores else 0.0
        weakest = min(scores, key=scores.get) if scores else ""
        strongest = max(scores, key=scores.get) if scores else ""

        # Message contextuel
        if dagesh_count == 7:
            msg = (
                "Les 7 doubles sont toutes en dagesh — harmonie complète. "
                "Mais le SY prévient : les contrastes sont nécessaires."
            )
        elif rafeh_count == 7:
            msg = (
                "Les 7 doubles sont toutes en rafeh — "
                "toutes les Qliphoth sont actives. Tikkun urgent."
            )
        elif dagesh_count >= 5:
            msg = (
                f"{dagesh_count}/7 en dagesh. "
                f"Points faibles : {', '.join(m for m, s in syzygies.items() if s.side == 'rafeh')}."
            )
        else:
            msg = (
                f"Seulement {dagesh_count}/7 en dagesh. "
                f"Qliphoth actives : {', '.join(m for m, s in syzygies.items() if s.qliphah_active)}."
            )

        return BalanceState(
            dagesh_count=dagesh_count,
            rafeh_count=rafeh_count,
            harmony=harmony,
            weakest=weakest,
            strongest=strongest,
            syzygies=syzygies,
            message=msg,
        )

    def get_active_qliphoth(self) -> list[dict[str, str]]:
        """Retourne les Qliphoth actives (modules en rafeh).

        Pont entre le système SY et le système Qliphoth lourianique.
        Le côté rafeh d'une syzygie = la Qliphah correspondante.
        """
        result = []
        for module in SYZYGY_DEFS:
            state = self.assess_syzygy(module)
            if state.qliphah_active:
                defn = SYZYGY_DEFS[module]
                result.append({
                    "module": module,
                    "qliphah": defn.qliphah,
                    "sephirah": defn.sephirah,
                    "rafeh_attribute": defn.rafeh,
                    "score": round(state.score, 3),
                })
        return result

    @staticmethod
    def get_all_definitions() -> dict[str, dict[str, Any]]:
        """Toutes les définitions de syzygies (pour le dashboard)."""
        return {
            module: {
                "letter": d.letter,
                "hebrew": d.hebrew,
                "direction": d.direction,
                "planet": d.planet,
                "dagesh": d.dagesh,
                "dagesh_hebrew": d.dagesh_hebrew,
                "rafeh": d.rafeh,
                "rafeh_hebrew": d.rafeh_hebrew,
                "qliphah": d.qliphah,
                "sephirah": d.sephirah,
            }
            for module, d in SYZYGY_DEFS.items()
        }
