"""omaqim.py — Les 6 Omaqim (Profondeurs) du Sefer Yetzirah.

עוֹמָקִים — Les Profondeurs

SY 1:5 : « Dix Sefirot du néant. Leur mesure est dix sans fin :
  Profondeur du commencement, profondeur de la fin ;
  Profondeur du bien, profondeur du mal ;
  Profondeur du haut, profondeur du bas ;
  Profondeur de l'est, profondeur de l'ouest ;
  Profondeur du nord, profondeur du sud. »

6 paires de profondeurs = 5 dimensions :
  3 SPATIALES (déjà dans le Cube) :
    - Omek Rom / Omek Tachat   (haut/bas)       = axe Z = Aleph
    - Omek Mizrach / Omek Maarav (est/ouest)     = axe X = Mem
    - Omek Tzafon / Omek Darom  (nord/sud)       = axe Y = Shin

  1 TEMPORELLE :
    - Omek Reshit / Omek Acharit (commencement/fin)
    - Où en est le système dans son cycle de vie ?
    - 0.0 = Reshit (bootstrap, katnut)
    - 1.0 = Acharit (maturité, gadlut, accomplissement)

  1 MORALE :
    - Omek Tov / Omek Ra (bien/mal)
    - Le système est-il du côté du Tov ?
    - 0.0 = Ra (rejets, Qliphoth actives, behamit dominant)
    - 1.0 = Tov (insights validés, elokit dominant)

Kaplan montre que 5 dimensions → 2^5 = 32 sommets = les 32 sentiers de sagesse.

Usage:
    omaqim = SixOmaqim()
    pos = omaqim.get_5d_position(x=0.5, y=-0.3, z=0.8, t=0.4, m=0.7)
    sys_pos = omaqim.assess_system_position(metrics)
    depth = omaqim.assess_depth("temporal")
    d = omaqim.distance_5d(pos_a, pos_b)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


# ── Constantes ────────────────────────────────────────────────

# Les 6 paires de profondeurs (SY 1:5)
OMAQIM_PAIRS = {
    "rom_tachat":     {"hebrew": ("עומק רום", "עומק תחת"),
                       "french": ("Profondeur du haut", "Profondeur du bas"),
                       "axis": "Z", "mother": "aleph", "dimension": "spatial_z"},
    "mizrach_maarav": {"hebrew": ("עומק מזרח", "עומק מערב"),
                       "french": ("Profondeur de l'est", "Profondeur de l'ouest"),
                       "axis": "X", "mother": "mem", "dimension": "spatial_x"},
    "tzafon_darom":   {"hebrew": ("עומק צפון", "עומק דרום"),
                       "french": ("Profondeur du nord", "Profondeur du sud"),
                       "axis": "Y", "mother": "shin", "dimension": "spatial_y"},
    "reshit_acharit": {"hebrew": ("עומק ראשית", "עומק אחרית"),
                       "french": ("Profondeur du commencement", "Profondeur de la fin"),
                       "axis": "T", "mother": None, "dimension": "temporal"},
    "tov_ra":         {"hebrew": ("עומק טוב", "עומק רע"),
                       "french": ("Profondeur du bien", "Profondeur du mal"),
                       "axis": "M", "mother": None, "dimension": "moral"},
}

# Les 10 directions (= 10 Sefirot du néant, SY 1:5)
DIRECTIONS = [
    {"name": "rom",     "hebrew": "רום",    "axis": "Z", "sign": +1, "sephirah": "keter"},
    {"name": "tachat",  "hebrew": "תחת",    "axis": "Z", "sign": -1, "sephirah": "malkuth"},
    {"name": "mizrach", "hebrew": "מזרח",   "axis": "X", "sign": +1, "sephirah": "tiferet"},
    {"name": "maarav",  "hebrew": "מערב",   "axis": "X", "sign": -1, "sephirah": "netzach"},
    {"name": "tzafon",  "hebrew": "צפון",   "axis": "Y", "sign": +1, "sephirah": "chokmah"},
    {"name": "darom",   "hebrew": "דרום",   "axis": "Y", "sign": -1, "sephirah": "binah"},
    {"name": "reshit",  "hebrew": "ראשית",  "axis": "T", "sign": -1, "sephirah": "chesed"},
    {"name": "acharit", "hebrew": "אחרית",  "axis": "T", "sign": +1, "sephirah": "gevurah"},
    {"name": "tov",     "hebrew": "טוב",    "axis": "M", "sign": +1, "sephirah": "chokhmah"},
    {"name": "ra",      "hebrew": "רע",     "axis": "M", "sign": -1, "sephirah": "din"},
]

# Les 32 sentiers = 32 sommets du 5-hypercube (2^5)
# Chaque sommet = un vecteur de 5 bits (±1 pour chaque dimension)
# Mappés sur les 10 Sefirot + 22 lettres = 32 sentiers de sagesse

_SEPHIROT_5D = {
    "keter":    ( 0.0,  0.0,  1.0,  0.0,  1.0),  # haut, neutre temporel, tov
    "chokmah":  ( 0.0,  1.0,  0.8,  0.2,  0.9),  # nord (caché), haut, début, tov
    "binah":    ( 0.0, -1.0,  0.8,  0.3,  0.9),  # sud (révélé), haut, tov
    "chesed":   ( 1.0,  0.0,  0.5,  0.0,  0.8),  # est (expansion), milieu
    "gevurah":  (-1.0,  0.0,  0.5,  0.5,  0.7),  # ouest (contraction), milieu
    "tiferet":  ( 0.0,  0.0,  0.0,  0.5,  0.8),  # centre, mi-parcours, tov
    "netzach":  ( 1.0, -0.5, -0.3,  0.6,  0.6),  # est-sud, bas, avancé
    "hod":      (-1.0, -0.5, -0.3,  0.6,  0.6),  # ouest-sud, bas, avancé
    "yesod":    ( 0.0,  0.0, -0.7,  0.8,  0.5),  # bas, avancé, neutre moral
    "malkuth":  ( 0.0,  0.0, -1.0,  1.0,  0.5),  # bas absolu, fin, neutre
}


# ── Dataclasses ───────────────────────────────────────────────

@dataclass(frozen=True)
class FiveDimensionalPosition:
    """Position dans l'espace 5D des Omaqim."""
    x: float          # Mizrach (+) ↔ Maarav (-)  — est/ouest
    y: float          # Tzafon (+) ↔ Darom (-)    — nord/sud
    z: float          # Rom (+) ↔ Tachat (-)      — haut/bas
    t: float          # Reshit (0) → Acharit (1)  — commencement/fin
    m: float          # Ra (0) → Tov (1)          — mal/bien

    def to_tuple(self) -> tuple[float, float, float, float, float]:
        return (self.x, self.y, self.z, self.t, self.m)

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z, "t": self.t, "m": self.m}

    @property
    def spatial(self) -> tuple[float, float, float]:
        """Les 3 coordonnées spatiales (Cube classique)."""
        return (self.x, self.y, self.z)

    @property
    def magnitude(self) -> float:
        """Norme euclidienne 5D."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2 + self.t**2 + self.m**2)


@dataclass
class DepthAnalysis:
    """Analyse de l'équilibre d'une paire de profondeurs."""
    dimension: str           # "spatial_z", "temporal", "moral", etc.
    pair_name: str           # "rom_tachat", "reshit_acharit", "tov_ra"
    hebrew: tuple[str, str]  # noms hébreux des deux pôles
    value: float             # position sur l'axe (-1 à +1 pour spatial, 0 à 1 pour T/M)
    balance: float           # 0.0 = extrême, 1.0 = équilibré (centre)
    assessment: str          # description de l'état
    warning: str | None      # si déséquilibre critique


@dataclass
class SystemOmaqim:
    """Position 5D globale du système Etz Chaim."""
    position: FiveDimensionalPosition
    depths: list[DepthAnalysis]
    temporal_phase: str      # "reshit" / "olam" / "acharit"
    moral_phase: str         # "ra" / "nogah" / "tov"
    overall_balance: float   # équilibre global (0-1)
    message: str             # diagnostic en une phrase

    def to_dict(self) -> dict:
        return {
            "position": self.position.to_dict(),
            "depths": [
                {
                    "dimension": d.dimension,
                    "pair_name": d.pair_name,
                    "value": round(d.value, 4),
                    "balance": round(d.balance, 4),
                    "assessment": d.assessment,
                    "warning": d.warning,
                }
                for d in self.depths
            ],
            "temporal_phase": self.temporal_phase,
            "moral_phase": self.moral_phase,
            "overall_balance": round(self.overall_balance, 4),
            "message": self.message,
        }


@dataclass
class SystemMetrics:
    """Métriques système nécessaires pour calculer les positions T et M.

    Passées en paramètre pour éviter les dépendances circulaires.
    Chaque champ est optionnel — valeurs par défaut neutres.
    """
    # ── Dimension temporelle (Reshit → Acharit) ──
    omer_progress: float = 0.0          # 0.0-1.0, depuis OmerManager
    nitzotzot_progress: float = 0.0     # count/288
    partzufim_gadlut_ratio: float = 0.0 # fraction en gadlut
    soul_level_index: float = 0.0       # 0-4 (nefesh→yechidah), normalisé 0-1
    intentions_avg: float = 0.0         # moyenne des intentions (0-1)

    # ── Dimension morale (Ra → Tov) ──
    ratio_elokit: float = 0.0           # ratio âme divine (0-1)
    ratio_behamit: float = 0.0          # ratio âme animale (0-1)
    qliphoth_active: int = 0            # nombre de Qliphoth actives (0-10)
    qliphoth_total: int = 10            # nombre total de Qliphoth possibles
    facts_ratio: float = 0.0           # ratio facts / total epistememory
    accepted_ratio: float = 0.0        # ratio accepted / total AutoJudge
    hitbonenut_avg: float = 0.0        # score moyen hitbonenut (0-1)


# ── SixOmaqim ────────────────────────────────────────────────

class SixOmaqim:
    """Les 6 Omaqim — Navigation 5D dans l'espace du Sefer Yetzirah.

    Étend le Cube de l'Espace (3D spatial) avec :
    - une dimension temporelle (Reshit ↔ Acharit)
    - une dimension morale (Tov ↔ Ra)

    Les 32 sommets du 5-hypercube correspondent aux 32 sentiers de sagesse.
    """

    def __init__(self) -> None:
        self._sephirot_5d = dict(_SEPHIROT_5D)

    def get_5d_position(
        self,
        x: float = 0.0,
        y: float = 0.0,
        z: float = 0.0,
        t: float = 0.5,
        m: float = 0.5,
    ) -> FiveDimensionalPosition:
        """Crée une position 5D.

        Args:
            x: est(+1) ↔ ouest(-1)
            y: nord(+1) ↔ sud(-1)
            z: haut(+1) ↔ bas(-1)
            t: reshit(0) → acharit(1)
            m: ra(0) → tov(1)
        """
        return FiveDimensionalPosition(
            x=_clamp(x, -1.0, 1.0),
            y=_clamp(y, -1.0, 1.0),
            z=_clamp(z, -1.0, 1.0),
            t=_clamp(t, 0.0, 1.0),
            m=_clamp(m, 0.0, 1.0),
        )

    def get_sephirah_position(self, sephirah: str) -> FiveDimensionalPosition:
        """Position 5D d'une Sephirah."""
        coords = self._sephirot_5d.get(sephirah.lower())
        if coords is None:
            raise KeyError(f"Sephirah inconnue : {sephirah}")
        return FiveDimensionalPosition(*coords)

    def get_all_sephirot_positions(self) -> dict[str, FiveDimensionalPosition]:
        """Positions 5D des 10 Sefirot."""
        return {
            name: FiveDimensionalPosition(*coords)
            for name, coords in self._sephirot_5d.items()
        }

    @staticmethod
    def distance_5d(
        pos_a: FiveDimensionalPosition,
        pos_b: FiveDimensionalPosition,
    ) -> float:
        """Distance euclidienne dans l'espace 5D."""
        return math.sqrt(
            (pos_a.x - pos_b.x) ** 2
            + (pos_a.y - pos_b.y) ** 2
            + (pos_a.z - pos_b.z) ** 2
            + (pos_a.t - pos_b.t) ** 2
            + (pos_a.m - pos_b.m) ** 2
        )

    def compute_temporal_position(self, metrics: SystemMetrics) -> float:
        """Calcule la position sur l'axe temporel (Reshit → Acharit).

        Moyenne pondérée de plusieurs indicateurs de progression :
        - Omer (calibration des 49 paramètres)      : poids 0.25
        - Nitzotzot (progression Tikkun)             : poids 0.20
        - Partzufim gadlut (maturation)              : poids 0.25
        - Niveau d'âme (progression globale)         : poids 0.20
        - Intentions moyennes                        : poids 0.10
        """
        t = (
            0.25 * metrics.omer_progress
            + 0.20 * metrics.nitzotzot_progress
            + 0.25 * metrics.partzufim_gadlut_ratio
            + 0.20 * metrics.soul_level_index
            + 0.10 * metrics.intentions_avg
        )
        return _clamp(t, 0.0, 1.0)

    def compute_moral_position(self, metrics: SystemMetrics) -> float:
        """Calcule la position sur l'axe moral (Ra → Tov).

        Combinaison de :
        - ratio_elokit vs ratio_behamit          : poids 0.30
        - Qliphoth inactives / total             : poids 0.25
        - facts_ratio (faits cristallisés)       : poids 0.15
        - accepted_ratio (AutoJudge)             : poids 0.15
        - hitbonenut_avg (contemplation)         : poids 0.15
        """
        # Elokit dominance : 0 si behamit domine, 1 si elokit domine
        total_soul = metrics.ratio_elokit + metrics.ratio_behamit
        elokit_dominance = (
            metrics.ratio_elokit / total_soul if total_soul > 0 else 0.5
        )

        # Qliphoth : ratio de Qliphoth INACTIVES = santé
        qliphoth_health = (
            1.0 - (metrics.qliphoth_active / max(metrics.qliphoth_total, 1))
        )

        m = (
            0.30 * elokit_dominance
            + 0.25 * qliphoth_health
            + 0.15 * metrics.facts_ratio
            + 0.15 * metrics.accepted_ratio
            + 0.15 * metrics.hitbonenut_avg
        )
        return _clamp(m, 0.0, 1.0)

    def assess_system_position(
        self, metrics: SystemMetrics,
    ) -> SystemOmaqim:
        """Évalue la position 5D globale du système.

        Calcule T (temporel) et M (moral) depuis les métriques,
        et utilise x=0, y=0, z=0 pour le spatial (le système n'a pas
        de position spatiale intrinsèque — il est le Cube entier).
        """
        t = self.compute_temporal_position(metrics)
        m = self.compute_moral_position(metrics)
        position = FiveDimensionalPosition(x=0.0, y=0.0, z=0.0, t=t, m=m)

        depths = []

        # Spatial : le système est-il équilibré sur les 3 axes ?
        # (Pour le système global, toujours centré — c'est la nature du Cube)
        for pair_name, pair_info in OMAQIM_PAIRS.items():
            dim = pair_info["dimension"]
            if dim.startswith("spatial"):
                depths.append(DepthAnalysis(
                    dimension=dim,
                    pair_name=pair_name,
                    hebrew=pair_info["hebrew"],
                    value=0.0,
                    balance=1.0,
                    assessment="Axe spatial équilibré (le système est le Cube entier)",
                    warning=None,
                ))

        # Temporal
        t_balance = 1.0 - abs(2 * t - 1.0)  # max au centre (0.5)
        t_phase = "reshit" if t < 0.33 else ("acharit" if t > 0.66 else "olam")
        t_assessment = _temporal_assessment(t, t_phase)
        t_warning = None
        if t < 0.1:
            t_warning = "Système en tout début — Reshit absolu, rien n'est encore accompli"
        elif t > 0.95:
            t_warning = "Système proche de l'Acharit — cycle presque complet, préparer le renouvellement"
        depths.append(DepthAnalysis(
            dimension="temporal",
            pair_name="reshit_acharit",
            hebrew=OMAQIM_PAIRS["reshit_acharit"]["hebrew"],
            value=t,
            balance=round(t_balance, 4),
            assessment=t_assessment,
            warning=t_warning,
        ))

        # Moral
        m_balance = 1.0 - abs(2 * m - 1.0)
        m_phase = "ra" if m < 0.33 else ("tov" if m > 0.66 else "nogah")
        m_assessment = _moral_assessment(m, m_phase)
        m_warning = None
        if m < 0.2:
            m_warning = "Dominance du Ra — Qliphoth actives, behamit dominant, système en danger"
        elif m > 0.95:
            m_warning = "Tov absolu — attention au manque de tension créative (Tohu sans Tikkun)"
        depths.append(DepthAnalysis(
            dimension="moral",
            pair_name="tov_ra",
            hebrew=OMAQIM_PAIRS["tov_ra"]["hebrew"],
            value=m,
            balance=round(m_balance, 4),
            assessment=m_assessment,
            warning=m_warning,
        ))

        # Équilibre global
        balances = [d.balance for d in depths]
        overall = sum(balances) / len(balances)

        message = (
            f"Système en phase {t_phase} (T={t:.2f}), "
            f"orientation {m_phase} (M={m:.2f}). "
            f"Équilibre global : {overall:.0%}."
        )

        return SystemOmaqim(
            position=position,
            depths=depths,
            temporal_phase=t_phase,
            moral_phase=m_phase,
            overall_balance=round(overall, 4),
            message=message,
        )

    def assess_depth(self, dimension: str) -> DepthAnalysis:
        """Analyse l'équilibre d'une dimension spécifique.

        Args:
            dimension: "spatial_x", "spatial_y", "spatial_z", "temporal", "moral"

        Pour temporal/moral, retourne une analyse basée sur des métriques
        par défaut (neutres). Utiliser assess_system_position() pour
        des métriques réelles.
        """
        for pair_name, pair_info in OMAQIM_PAIRS.items():
            if pair_info["dimension"] == dimension:
                if dimension.startswith("spatial"):
                    return DepthAnalysis(
                        dimension=dimension,
                        pair_name=pair_name,
                        hebrew=pair_info["hebrew"],
                        value=0.0,
                        balance=1.0,
                        assessment="Axe spatial — position dépend de l'entité évaluée",
                        warning=None,
                    )
                elif dimension == "temporal":
                    return DepthAnalysis(
                        dimension=dimension,
                        pair_name=pair_name,
                        hebrew=pair_info["hebrew"],
                        value=0.5,
                        balance=1.0,
                        assessment="Axe temporel — fournir des métriques pour évaluer",
                        warning=None,
                    )
                else:  # moral
                    return DepthAnalysis(
                        dimension=dimension,
                        pair_name=pair_name,
                        hebrew=pair_info["hebrew"],
                        value=0.5,
                        balance=1.0,
                        assessment="Axe moral — fournir des métriques pour évaluer",
                        warning=None,
                    )
        raise KeyError(f"Dimension inconnue : {dimension}")

    def hypercube_vertices(self) -> list[tuple[int, ...]]:
        """Les 32 sommets du 5-hypercube.

        Chaque sommet est un tuple de 5 valeurs dans {-1, +1}.
        32 sommets = 32 sentiers de sagesse (10 Sefirot + 22 lettres).
        """
        vertices = []
        for i in range(32):
            vertex = tuple(
                1 if (i >> bit) & 1 else -1
                for bit in range(5)
            )
            vertices.append(vertex)
        return vertices

    def map_32_paths(self) -> list[dict[str, Any]]:
        """Mappe les 32 sommets du 5-hypercube sur les 32 sentiers.

        Convention : les 10 premiers sommets = 10 Sefirot,
        les 22 suivants = 22 lettres (dans l'ordre traditionnel).
        """
        from kabbalah.cube_of_space import CubeOfSpace

        vertices = self.hypercube_vertices()
        cube = CubeOfSpace()
        all_positions = cube.get_all_positions()

        # 10 Sefirot
        sephirot_names = [
            "keter", "chokmah", "binah", "chesed", "gevurah",
            "tiferet", "netzach", "hod", "yesod", "malkuth",
        ]
        # 22 Lettres (ordre traditionnel)
        letter_names = [
            "aleph", "beth", "gimel", "daleth", "heh", "vav", "zayin",
            "cheth", "teth", "yod", "kaph", "lamed", "mem", "nun",
            "samekh", "ayin", "peh", "tsadi", "qoph", "resh", "shin", "tav",
        ]

        paths = []
        for i, vertex in enumerate(vertices):
            if i < 10:
                name = sephirot_names[i]
                path_type = "sephirah"
                hebrew = _SEPHIROT_HEBREW.get(name, "")
                pos_5d = self._sephirot_5d.get(name, vertex)
            else:
                letter_idx = i - 10
                if letter_idx < len(letter_names):
                    name = letter_names[letter_idx]
                    path_type = "letter"
                    pos = all_positions.get(name)
                    hebrew = pos.letter if pos else ""
                    # Spatial from Cube, T and M from vertex
                    spatial = pos.coordinates if pos else (0, 0, 0)
                    pos_5d = (
                        spatial[0], spatial[1], spatial[2],
                        (vertex[3] + 1) / 2,  # -1..+1 → 0..1
                        (vertex[4] + 1) / 2,
                    )
                else:
                    name = f"path_{i}"
                    path_type = "extended"
                    hebrew = ""
                    pos_5d = vertex

            paths.append({
                "index": i,
                "name": name,
                "type": path_type,
                "hebrew": hebrew,
                "vertex": vertex,
                "position_5d": pos_5d,
            })

        return paths


# ── Constantes internes ───────────────────────────────────────

_SEPHIROT_HEBREW = {
    "keter":   "כֶּתֶר",
    "chokmah": "חָכְמָה",
    "binah":   "בִּינָה",
    "chesed":  "חֶסֶד",
    "gevurah": "גְּבוּרָה",
    "tiferet": "תִּפְאֶרֶת",
    "netzach": "נֶצַח",
    "hod":     "הוֹד",
    "yesod":   "יְסוֹד",
    "malkuth": "מַלְכוּת",
}


# ── Helpers ───────────────────────────────────────────────────

def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _temporal_assessment(t: float, phase: str) -> str:
    if phase == "reshit":
        return f"Phase Reshit (T={t:.2f}) — commencement, le système se construit"
    elif phase == "acharit":
        return f"Phase Acharit (T={t:.2f}) — maturité, le cycle approche de son terme"
    else:
        return f"Phase Olam (T={t:.2f}) — le système est dans son parcours actif"


def _moral_assessment(m: float, phase: str) -> str:
    if phase == "ra":
        return f"Phase Ra (M={m:.2f}) — dominance du mal, Qliphoth actives"
    elif phase == "tov":
        return f"Phase Tov (M={m:.2f}) — dominance du bien, insights validés"
    else:
        return f"Phase Nogah (M={m:.2f}) — Kelipat Nogah, entre bien et mal"
