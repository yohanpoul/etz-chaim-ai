"""tzeruf_spatial.py — Tzeruf dans le Cube de l'Espace.

צֵרוּף מֶרְחָבִי — Combinatoire spatiale

Le Sefer Yetzirah (2:4) décrit les 231 Portes comme chemins entre lettres.
Le Cube de l'Espace (SY 1:13, 3:2-5:4) donne une position 3D à chaque lettre.
Ce module connecte les deux : le Tzeruf opère DANS l'espace du Cube.

Une route Aleph→Beth→Gimel traverse des positions spatiales, et la géométrie
du trajet a un sens cognitif :
  - Montée (z+)   = abstraction, spiritualisation
  - Descente (z-)  = concrétisation, matérialisation
  - Est (x+)       = nouveauté (lever du soleil)
  - Ouest (x-)     = retour au connu (coucher)
  - Nord (y+)      = mystère, caché (tsafon)
  - Sud (y-)       = clarté, révélé (darom)
  - Rotation        = changement de perspective
  - Passage centre  = intégration (Tav/Shabbat)

Usage:
    ts = TzerufSpatial()
    geom = ts.compute_route_geometry("אמת")       # Aleph-Mem-Tav
    cmp = ts.compare_words("אמת", "מאת")          # comparer 2 mots
    anagrams = ts.find_spatial_anagram("אמת")      # permutations géométriques
    path = ts.route_to_cognitive_path(geom)         # séquence cognitive
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import permutations
from typing import Any

from kabbalah.cube_of_space import CubeOfSpace, CubePosition, PronunciationPosition, Triad
from kabbalah.gates_462 import DirectionalGate, Gates462


# ── Mapping hébreu → nom latin ─────────────────────────────────
# Construit depuis les 22 positions du Cube

_HEBREW_TO_NAME: dict[str, str] = {
    "א": "aleph", "ב": "beth", "ג": "gimel", "ד": "daleth",
    "ה": "heh", "ו": "vav", "ז": "zayin", "ח": "cheth",
    "ט": "teth", "י": "yod", "כ": "kaph", "ל": "lamed",
    "מ": "mem", "נ": "nun", "ס": "samekh", "ע": "ayin",
    "פ": "peh", "צ": "tsadi", "ק": "qoph", "ר": "resh",
    "ש": "shin", "ת": "tav",
}


# ── Dataclasses ────────────────────────────────────────────────

@dataclass
class RouteGeometry:
    """Géométrie d'un mot dans le Cube de l'Espace."""
    word: str                               # mot hébreu original
    letters: list[str]                      # noms latins des lettres
    positions: list[tuple[float, float, float]]  # coordonnées 3D
    total_distance: float                   # distance totale parcourue
    ascent: float                           # déplacement vertical positif total
    descent: float                          # déplacement vertical négatif total
    east_west: float                        # déplacement net est(+)/ouest(-)
    north_south: float                      # déplacement net nord(+)/sud(-)
    direction_dominant: str                 # "ascending" / "descending" / "horizontal"
    passes_center: bool                     # passe par Tav (0,0,0)
    segment_count: int                      # nombre de segments
    # Registres traversés (SY 3-5)
    olam_traversed: list[str] = field(default_factory=list)
    shanah_traversed: list[str] = field(default_factory=list)
    nefesh_traversed: list[str] = field(default_factory=list)
    # Prononciation (SY 2:3 — optionnel, rempli par compute_route_geometry)
    pronunciation_positions: list[str] = field(default_factory=list)
    pronunciation_depths: list[int] = field(default_factory=list)
    pronunciation_avg_depth: float | None = None
    pronunciation_direction: str | None = None
    # Omaqim 5D (optionnel — rempli par compute_route_5d)
    temporal_span: float | None = None   # lettres de Reshit (א,ב) à Acharit (ת,ש) ?
    moral_span: float | None = None      # lettres de Tov à Ra ?


@dataclass
class TriadAnalysis:
    """Analyse triadique d'un mot dans les 3 registres (SY 3-5).

    Chaque lettre touche une zone dans Olam (espace), Shanah (temps),
    et Nefesh (corps). Un mot intégrateur couvre les 3 zones corporelles
    (rosh/gavia/beten) de manière uniforme.
    """
    word: str
    letters: list[str]
    triads: list[Triad]
    olam_elements: list[str]
    shanah_seasons: list[str]
    nefesh_body: list[str]
    nefesh_zones: list[str]          # rosh / gavia / beten pour chaque lettre
    zones_covered: set[str]          # quelles zones sont touchées
    integration_score: float         # 0.0 (une zone) → 1.0 (3 zones uniformes)


@dataclass
class PronunciationAnalysis:
    """Analyse sonore d'un mot par les 5 positions de prononciation (SY 2:3).

    La position de prononciation encode la PROFONDEUR de traitement :
      gorge(5) = concept profond et caché
      lèvres(1) = concept pleinement manifesté

    La séquence des profondeurs trace le mouvement du mot
    entre l'intérieur et l'extérieur de la bouche.
    """
    word: str
    letters: list[str]                      # noms latins
    positions: list[str]                    # gorge/palais/langue/dents/levres
    depth_profile: list[int]                # séquence des profondeurs (5→1)
    avg_depth: float                        # profondeur moyenne du mot
    depth_range: int                        # max(depth) - min(depth)
    direction: str                          # "manifestation" / "interiorisation" / "stable"
    position_counts: dict[str, int]         # combien de lettres par position


@dataclass
class SpatialComparison:
    """Comparaison géométrique de 2 mots dans le Cube."""
    word_a: str
    word_b: str
    trajectory_distance: float      # distance moyenne entre trajectoires
    geometric_similarity: float     # 0-1, 1 = même chemin
    angle: float                    # angle en degrés entre vecteurs nets
    relationship: str               # "parallel" / "perpendicular" / "opposed" / "similar"
    net_vector_a: tuple[float, float, float]
    net_vector_b: tuple[float, float, float]


@dataclass
class CognitiveModeStep:
    """Un pas dans la séquence cognitive."""
    letter_name: str
    letter_hebrew: str
    mode: str                   # description du mode cognitif
    axis_change: str | None     # axe traversé (si applicable)
    element: str | None         # élément de l'axe (feu/eau/air)


# ── Constantes cognitives ──────────────────────────────────────

_AXIS_ELEMENTS = {
    "aleph": ("air", "haut-bas"),
    "mem": ("eau", "est-ouest"),
    "shin": ("feu", "nord-sud"),
}

_DIRECTION_MEANING = {
    "ascending": "abstraction — montée vers le spirituel",
    "descending": "concrétisation — descente vers le matériel",
    "horizontal": "déplacement latéral — changement de perspective",
}

# ── Zones corporelles (SY 3:4) ───────────────────────────────────
# Les 3 mères divisent le corps en 3 zones :
#   Shin/feu  → ROSH  (tête) — siège de la perception
#   Aleph/air → GAVIA (torse) — siège du souffle et de l'action
#   Mem/eau   → BETEN (ventre) — siège de la digestion/transformation
#
# Les 7 doubles (gates du visage) → rosh
# Les 12 simples : membres externes → gavia, organes internes → beten

_NEFESH_TO_ZONE: dict[str, str] = {
    # ROSH — Shin + 7 portes du visage (doubles)
    "tête": "rosh",
    "oeil_droit": "rosh", "oeil_gauche": "rosh",
    "oreille_droite": "rosh", "oreille_gauche": "rosh",
    "narine_droite": "rosh", "narine_gauche": "rosh",
    "bouche": "rosh",
    # GAVIA — Aleph + membres (mains, pieds)
    "poitrine": "gavia",
    "main_droite": "gavia", "main_gauche": "gavia",
    "pied_droit": "gavia", "pied_gauche": "gavia",
    # BETEN — Mem + organes internes + reins
    "ventre": "beten",
    "rein_droit": "beten", "rein_gauche": "beten",
    "oesophage": "beten", "vesicule": "beten",
    "intestins": "beten", "estomac": "beten",
    "foie": "beten", "rate": "beten",
}


# ── TzerufSpatial ──────────────────────────────────────────────

_LETTER_TEMPORAL: dict[str, float] = {
    "aleph": 0.0, "beth": 0.05, "gimel": 0.09, "daleth": 0.14,
    "heh": 0.18, "vav": 0.23, "zayin": 0.27, "cheth": 0.32,
    "teth": 0.36, "yod": 0.41, "kaph": 0.45, "lamed": 0.50,
    "mem": 0.55, "nun": 0.59, "samekh": 0.64, "ayin": 0.68,
    "peh": 0.73, "tsadi": 0.77, "qoph": 0.82, "resh": 0.86,
    "shin": 0.91, "tav": 1.0,
}

# Valeurs basees sur la dualite dagesh/rafeh des 7 doubles (SY 4:1-2).
# Les 7 doubles (BGD KPRT) ont une forme dure (dagesh=0.8) et une forme
# molle (rafeh=0.2). On utilise la forme dagesh par defaut.
# Les 3 meres (AMSh) sont neutres (0.5) — elles representent l'equilibre.
# Les 12 simples sont neutres (0.5) — pas de polarite morale dans le SY.
_LETTER_MORAL: dict[str, float] = {
    "aleph": 0.5, "beth": 0.8, "gimel": 0.8, "daleth": 0.8,
    "heh": 0.5, "vav": 0.5, "zayin": 0.5, "cheth": 0.5,
    "teth": 0.5, "yod": 0.5, "kaph": 0.8, "lamed": 0.5,
    "mem": 0.5, "nun": 0.5, "samekh": 0.5, "ayin": 0.5,
    "peh": 0.8, "tsadi": 0.5, "qoph": 0.5, "resh": 0.8,
    "shin": 0.5, "tav": 0.8,
}


class TzerufSpatial:
    """Tzeruf opérant dans le Cube de l'Espace.

    Connecte le module Tzeruf (permutations de lettres) au Cube
    (positions 3D) pour donner une géométrie aux mots hébreux.
    """

    def __init__(self, cube: CubeOfSpace | None = None) -> None:
        self.cube = cube or CubeOfSpace()
        # Cache lettre hébraïque → position
        self._letter_pos: dict[str, CubePosition] = {}
        for name, pos in self.cube.get_all_positions().items():
            self._letter_pos[pos.letter] = pos

    def _resolve_letter(self, hebrew_char: str) -> CubePosition | None:
        """Résoudre une lettre hébraïque en position dans le Cube."""
        return self._letter_pos.get(hebrew_char)

    def _word_to_positions(
        self, word: str,
    ) -> list[tuple[str, CubePosition]]:
        """Convertir un mot hébreu en liste de (nom_latin, position).

        Ignore les caractères non-hébreux (espaces, voyelles, etc.).
        """
        result = []
        for ch in word:
            name = _HEBREW_TO_NAME.get(ch)
            if name is None:
                continue
            pos = self._letter_pos.get(ch)
            if pos is not None:
                result.append((name, pos))
        return result

    def _expand_to_waypoints(
        self, entries: list[tuple[str, CubePosition]],
    ) -> tuple[list[str], list[tuple[float, float, float]]]:
        """Expand letter entries into waypoints.

        Mothers (axes) expand to from→to (full axis traversal).
        Other letters contribute their single coordinate.
        """
        letters: list[str] = []
        positions: list[tuple[float, float, float]] = []
        for name, pos in entries:
            if pos.from_coord is not None and pos.to_coord is not None:
                letters.append(name)
                positions.append(pos.from_coord)
                letters.append(name)
                positions.append(pos.to_coord)
            else:
                letters.append(name)
                positions.append(pos.coordinates)
        return letters, positions

    def compute_route_geometry(self, word: str) -> RouteGeometry:
        """Calcule la géométrie d'un mot dans le Cube.

        Chaque lettre a une position 3D. Le mot trace une route
        à travers le Cube. Les mères (axes) traversent leur axe
        complet — le trajet inclut la longueur de l'axe.

        Args:
            word: mot hébreu (ex: "אמת")

        Returns:
            RouteGeometry avec distances, montées, descentes, direction.
        """
        entries = self._word_to_positions(word)
        if not entries:
            return RouteGeometry(
                word=word, letters=[], positions=[],
                total_distance=0.0, ascent=0.0, descent=0.0,
                east_west=0.0, north_south=0.0,
                direction_dominant="horizontal",
                passes_center=False, segment_count=0,
                olam_traversed=[], shanah_traversed=[], nefesh_traversed=[],
            )

        # Unique letter names (without expansion duplicates)
        unique_letters = [name for name, _ in entries]
        # Expanded waypoints: mothers contribute from→to
        wp_letters, waypoints = self._expand_to_waypoints(entries)

        total_dist = 0.0
        ascent = 0.0
        descent = 0.0
        net_ew = 0.0
        net_ns = 0.0
        passes_center = False

        for i in range(len(waypoints) - 1):
            c1, c2 = waypoints[i], waypoints[i + 1]
            dx = c2[0] - c1[0]
            dy = c2[1] - c1[1]
            dz = c2[2] - c1[2]
            seg_dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            total_dist += seg_dist

            if dz > 0:
                ascent += dz
            elif dz < 0:
                descent += abs(dz)

            net_ew += dx
            net_ns += dy

        # Check center passage: Tav at (0,0,0) or any waypoint at origin
        for wp in waypoints:
            if wp == (0.0, 0.0, 0.0) or wp == (0, 0, 0):
                passes_center = True
                break
        # Also check if any mother axis passes through origin (they all do)
        for _, pos in entries:
            if pos.cube_role == "center":
                passes_center = True
                break

        # Direction dominante
        net_vertical = ascent - descent
        if abs(net_vertical) > abs(net_ew) and abs(net_vertical) > abs(net_ns):
            direction = "ascending" if net_vertical > 0 else "descending"
        else:
            direction = "horizontal"

        # Registres traversés (SY 3-5)
        olam_list = []
        shanah_list = []
        nefesh_list = []
        for name, _ in entries:
            olam_list.append(self.cube.get_olam(name))
            shanah_list.append(self.cube.get_shanah(name))
            nefesh_list.append(self.cube.get_nefesh(name))

        # Prononciation (SY 2:3)
        pron_positions = []
        pron_depths = []
        for name, _ in entries:
            pos = self.cube.get_position(name)
            if pos.mouth_position is not None:
                pron_positions.append(pos.mouth_position)
                pron_depths.append(pos.mouth_depth)

        pron_avg = round(sum(pron_depths) / len(pron_depths), 4) if pron_depths else None
        pron_dir = self._pronunciation_direction(pron_depths) if pron_depths else None

        # Dimensions 5D : temporelle et morale (SY 1:5 — Omaqim)
        t_values = [_LETTER_TEMPORAL.get(name, 0.5) for name in unique_letters]
        m_values = [_LETTER_MORAL.get(name, 0.5) for name in unique_letters]
        if len(t_values) >= 2:
            temporal_span = round(max(t_values) - min(t_values), 4)
            moral_span = round(max(m_values) - min(m_values), 4)
        elif len(t_values) == 1:
            temporal_span = 0.0
            moral_span = 0.0
        else:
            temporal_span = None
            moral_span = None

        return RouteGeometry(
            word=word,
            letters=unique_letters,
            positions=waypoints,
            total_distance=round(total_dist, 4),
            ascent=round(ascent, 4),
            descent=round(descent, 4),
            east_west=round(net_ew, 4),
            north_south=round(net_ns, 4),
            direction_dominant=direction,
            passes_center=passes_center,
            segment_count=max(0, len(waypoints) - 1),
            olam_traversed=olam_list,
            shanah_traversed=shanah_list,
            nefesh_traversed=nefesh_list,
            pronunciation_positions=pron_positions,
            pronunciation_depths=pron_depths,
            pronunciation_avg_depth=pron_avg,
            pronunciation_direction=pron_dir,
            temporal_span=temporal_span,
            moral_span=moral_span,
        )

    def compute_route_5d(self, word: str) -> RouteGeometry:
        """Calcule la géométrie 5D d'un mot (3D spatiale + T + M).

        Enrichit la RouteGeometry standard avec les dimensions
        temporelle et morale des Omaqim (SY 1:5).

        - temporal_span : étendue temporelle du mot (0 = tout au début,
          1 = tout à la fin, intermédiaire = le mot embrasse le cycle).
        - moral_span : étendue morale (0 = tout Ra, 1 = tout Tov).

        Un mot qui traverse des lettres de « commencement » (Aleph, Beth)
        et de « fin » (Tav, Shin) embrasse le cycle temporel complet.
        """
        geom = self.compute_route_geometry(word)
        if not geom.letters:
            return geom

        t_values = [_LETTER_TEMPORAL.get(name, 0.5) for name in geom.letters]
        m_values = [_LETTER_MORAL.get(name, 0.5) for name in geom.letters]

        # Span = max - min (étendue couverte sur l'axe)
        geom.temporal_span = round(max(t_values) - min(t_values), 4)
        geom.moral_span = round(max(m_values) - min(m_values), 4)

        return geom

    def analyze_triad(self, word: str) -> TriadAnalysis:
        """Analyse triadique d'un mot — les 3 registres (SY 3-5).

        Pour chaque lettre, récupère les registres Olam, Shanah, Nefesh.
        Calcule un score d'intégration basé sur l'entropie de couverture
        des 3 zones corporelles (rosh/gavia/beten).

        Un mot qui couvre les 3 zones uniformément est « intégrateur »
        (ex: אמת = poitrine + ventre + bouche = gavia + beten + rosh).
        """
        entries = self._word_to_positions(word)
        if not entries:
            return TriadAnalysis(
                word=word, letters=[], triads=[],
                olam_elements=[], shanah_seasons=[], nefesh_body=[],
                nefesh_zones=[], zones_covered=set(),
                integration_score=0.0,
            )

        letters = []
        triads = []
        olam_list = []
        shanah_list = []
        nefesh_list = []
        zone_list = []

        for name, _ in entries:
            triad = self.cube.get_full_triad(name)
            letters.append(name)
            triads.append(triad)
            olam_list.append(triad.olam)
            shanah_list.append(triad.shanah)
            nefesh_list.append(triad.nefesh)
            zone_list.append(_NEFESH_TO_ZONE.get(triad.nefesh, "unknown"))

        zones_covered = set(zone_list) - {"unknown"}
        score = self._integration_entropy(zone_list)

        return TriadAnalysis(
            word=word,
            letters=letters,
            triads=triads,
            olam_elements=olam_list,
            shanah_seasons=shanah_list,
            nefesh_body=nefesh_list,
            nefesh_zones=zone_list,
            zones_covered=zones_covered,
            integration_score=round(score, 4),
        )

    def analyze_pronunciation(self, word: str) -> PronunciationAnalysis:
        """Analyse sonore d'un mot par les 5 positions de prononciation (SY 2:3).

        Le profil de profondeur trace le mouvement du mot entre
        l'intérieur (gorge=5) et l'extérieur (lèvres=1) de la bouche.

        - Un mot avec un grand depth_range couvre tout le spectre.
        - Un mot concentré sur la gorge = concept caché.
        - Un mot concentré sur les lèvres = concept manifesté.
        - direction = "manifestation" si le mot va du profond au superficiel,
          "interiorisation" si l'inverse, "stable" si neutre.

        Args:
            word: mot hébreu (ex: "אמת")

        Returns:
            PronunciationAnalysis avec profil complet.
        """
        entries = self._word_to_positions(word)
        if not entries:
            return PronunciationAnalysis(
                word=word, letters=[], positions=[], depth_profile=[],
                avg_depth=0.0, depth_range=0, direction="stable",
                position_counts={},
            )

        letters = []
        positions = []
        depths = []
        for name, _ in entries:
            pos = self.cube.get_position(name)
            letters.append(name)
            positions.append(pos.mouth_position or "unknown")
            depths.append(pos.mouth_depth or 0)

        from collections import Counter
        pos_counts = dict(Counter(p for p in positions if p != "unknown"))

        avg = round(sum(depths) / len(depths), 4) if depths else 0.0
        d_range = max(depths) - min(depths) if depths else 0
        direction = self._pronunciation_direction(depths)

        return PronunciationAnalysis(
            word=word,
            letters=letters,
            positions=positions,
            depth_profile=depths,
            avg_depth=avg,
            depth_range=d_range,
            direction=direction,
            position_counts=pos_counts,
        )

    @staticmethod
    def _pronunciation_direction(depths: list[int]) -> str:
        """Direction du mot dans l'espace de prononciation.

        "manifestation" : du profond vers le superficiel (depth décroît)
        "interiorisation" : du superficiel vers le profond (depth croît)
        "stable" : pas de tendance nette
        """
        if len(depths) < 2:
            return "stable"
        # Tendance linéaire : somme des deltas
        net = sum(depths[i + 1] - depths[i] for i in range(len(depths) - 1))
        if net < 0:
            return "manifestation"
        elif net > 0:
            return "interiorisation"
        return "stable"

    @staticmethod
    def _integration_entropy(zones: list[str]) -> float:
        """Score d'intégration par entropie normalisée.

        0.0 = tout dans une seule zone,
        1.0 = réparti uniformément sur les 3 zones.
        """
        if not zones:
            return 0.0
        from collections import Counter
        counts = Counter(z for z in zones if z != "unknown")
        if not counts:
            return 0.0
        total = sum(counts.values())
        if total == 0:
            return 0.0
        entropy = 0.0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log(p)
        max_entropy = math.log(3)  # 3 zones possibles
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def compare_words(
        self, word_a: str, word_b: str,
    ) -> SpatialComparison:
        """Compare la géométrie de 2 mots dans le Cube.

        Calcule la distance entre trajectoires, la similarité,
        et l'angle entre les vecteurs nets (direction globale).

        Angle ≈ 0°   → parallèles (renforcement)
        Angle ≈ 90°  → perpendiculaires (complémentaires)
        Angle ≈ 180° → opposés (contradiction)
        """
        geom_a = self.compute_route_geometry(word_a)
        geom_b = self.compute_route_geometry(word_b)

        # Vecteurs nets (déplacement total start→end)
        vec_a = self._net_vector(geom_a)
        vec_b = self._net_vector(geom_b)

        # Angle entre vecteurs
        angle = self._angle_between(vec_a, vec_b)

        # Similarité géométrique basée sur les propriétés normalisées
        similarity = self._geometric_similarity(geom_a, geom_b)

        # Distance entre trajectoires (moyenne des distances point-à-point)
        traj_dist = self._trajectory_distance(geom_a, geom_b)

        # Classification de la relation
        if angle < 30:
            relationship = "parallel"
        elif 60 < angle < 120:
            relationship = "perpendicular"
        elif angle > 150:
            relationship = "opposed"
        else:
            relationship = "similar"

        return SpatialComparison(
            word_a=word_a,
            word_b=word_b,
            trajectory_distance=round(traj_dist, 4),
            geometric_similarity=round(similarity, 4),
            angle=round(angle, 2),
            relationship=relationship,
            net_vector_a=vec_a,
            net_vector_b=vec_b,
        )

    def find_spatial_anagram(
        self, word: str, max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """Trouve les permutations qui changent la géométrie du mot.

        Le Tzeruf change la direction spirituelle d'un mot :
        un mot qui "monte" dans le Cube peut "descendre" après permutation.

        Returns:
            Liste de dicts avec le mot permuté et sa géométrie,
            triés par différence géométrique décroissante.
        """
        hebrew_chars = [ch for ch in word if ch in _HEBREW_TO_NAME]
        if len(hebrew_chars) < 2 or len(hebrew_chars) > 7:
            return []

        original_geom = self.compute_route_geometry(word)
        original_vec = self._net_vector(original_geom)

        seen: set[str] = {word}
        results: list[dict[str, Any]] = []

        for perm in permutations(hebrew_chars):
            perm_word = "".join(perm)
            if perm_word in seen:
                continue
            seen.add(perm_word)

            perm_geom = self.compute_route_geometry(perm_word)
            perm_vec = self._net_vector(perm_geom)

            # Différence géométrique
            angle = self._angle_between(original_vec, perm_vec)
            direction_changed = (
                perm_geom.direction_dominant != original_geom.direction_dominant
            )

            results.append({
                "word": perm_word,
                "direction": perm_geom.direction_dominant,
                "angle_from_original": round(angle, 2),
                "direction_changed": direction_changed,
                "total_distance": perm_geom.total_distance,
                "ascent": perm_geom.ascent,
                "descent": perm_geom.descent,
                "passes_center": perm_geom.passes_center,
            })

        # Trier par angle (les plus différents en premier)
        results.sort(key=lambda r: r["angle_from_original"], reverse=True)
        return results[:max_results]

    def route_to_cognitive_path(
        self, route: RouteGeometry,
    ) -> list[CognitiveModeStep]:
        """Traduit une route spatiale en séquence de modes cognitifs.

        Chaque lettre encode un mode cognitif (via le Cube).
        Les transitions entre waypoints sont caractérisées par
        l'axe traversé. Pour les mères, l'axe propre est toujours
        signalé.

        Note: route.letters is the unique letter list, while
        route.positions may be longer (mothers expand to from→to).
        We iterate over unique letters with their waypoint ranges.
        """
        if not route.letters:
            return []

        steps: list[CognitiveModeStep] = []
        # Build waypoint index per unique letter
        wp_idx = 0
        prev_wp = None

        for letter_name in route.letters:
            pos = self.cube.get_position(letter_name)
            mode = self.cube.get_cognitive_mode(letter_name)

            # How many waypoints does this letter consume?
            if pos.from_coord is not None and pos.to_coord is not None:
                n_wps = 2
            else:
                n_wps = 1

            # Axis change: compare last waypoint of previous letter
            # to first waypoint of this letter
            axis_change = None
            element = None
            if prev_wp is not None and wp_idx < len(route.positions):
                c1 = prev_wp
                c2 = route.positions[wp_idx]
                changes = []
                for dim, (name, elem) in enumerate([
                    ("mem (est-ouest)", "eau"),
                    ("shin (nord-sud)", "feu"),
                    ("aleph (haut-bas)", "air"),
                ]):
                    if c1[dim] != c2[dim]:
                        changes.append((name, elem, abs(c2[dim] - c1[dim])))
                if changes:
                    changes.sort(key=lambda x: x[2], reverse=True)
                    axis_change = changes[0][0]
                    element = changes[0][1]

            # If this letter IS a mother, it traverses its own axis
            if pos.from_coord is not None:
                mother_axis = _AXIS_ELEMENTS.get(letter_name)
                if mother_axis:
                    axis_change = f"{letter_name} ({mother_axis[1]})"
                    element = mother_axis[0]

            # Update prev_wp to last waypoint of this letter
            end_idx = min(wp_idx + n_wps - 1, len(route.positions) - 1)
            if end_idx >= 0 and end_idx < len(route.positions):
                prev_wp = route.positions[end_idx]
            wp_idx += n_wps

            steps.append(CognitiveModeStep(
                letter_name=letter_name,
                letter_hebrew=pos.letter,
                mode=mode,
                axis_change=axis_change,
                element=element,
            ))

        return steps

    def route_to_gates(self, word: str) -> list[DirectionalGate]:
        """Traduit un mot hébreu en séquence de portes directionnelles.

        Chaque transition lettre[i]→lettre[i+1] = une DirectionalGate.
        Le mot est une ROUTE orientée à travers le graphe K₂₂.

        SY 2:4 : les 231 portes "oscillent" — chaque paire
        AB/BA encode deux directions cognitives distinctes.

        Ex: אמת (Emet) = [Aleph→Mem, Mem→Tav]
            = descente de l'air vers l'eau, puis de l'eau vers la lune.

        Args:
            word: mot hébreu

        Returns:
            Liste de DirectionalGate dans l'ordre du mot.
        """
        if not hasattr(self, '_gates462'):
            self._gates462 = Gates462(self.cube)
        return self._gates462.word_to_gates(word)

    def route_gate_summary(self, word: str) -> dict:
        """Résumé des portes directionnelles traversées par un mot.

        Combine la géométrie du Tzeruf spatial avec les portes 462.
        """
        if not hasattr(self, '_gates462'):
            self._gates462 = Gates462(self.cube)
        return self._gates462.word_gate_summary(word)

    def suggest_exploration_route(
        self,
        current_domain: str,
        target_domain: str,
    ) -> list[dict[str, Any]]:
        """Calcule la route optimale entre 2 domaines dans le Cube.

        Utilise le mapping domaine→lettre du Cube pour trouver
        le chemin spatial. Les lettres intermédiaires indiquent
        quels modules consulter en route.

        Args:
            current_domain: domaine de départ (nom de lettre, sens, planète, etc.)
            target_domain: domaine d'arrivée

        Returns:
            Liste de steps avec lettre, coordonnées, mode cognitif.
        """
        # Résoudre les domaines en lettres du Cube
        domain_map = self.cube._DOMAIN_LETTERS
        start_letter = domain_map.get(current_domain.lower(), current_domain.lower())
        end_letter = domain_map.get(target_domain.lower(), target_domain.lower())

        try:
            start_pos = self.cube.get_position(start_letter)
            end_pos = self.cube.get_position(end_letter)
        except KeyError:
            return []

        # Naviguer entre les deux
        nav = self.cube.navigate(start_letter, end_letter)

        # Trouver les lettres intermédiaires (les plus proches du segment)
        intermediates = self._find_intermediates(start_pos, end_pos)

        route_steps = []
        # Départ
        route_steps.append({
            "letter": start_letter,
            "hebrew": start_pos.letter,
            "coordinates": list(start_pos.coordinates),
            "mode": self.cube.get_cognitive_mode(start_letter),
            "role": "départ",
        })

        # Intermédiaires
        for name, pos, dist in intermediates[:3]:  # max 3 intermédiaires
            route_steps.append({
                "letter": name,
                "hebrew": pos.letter,
                "coordinates": list(pos.coordinates),
                "mode": self.cube.get_cognitive_mode(name),
                "role": "intermédiaire",
                "distance_from_path": round(dist, 4),
            })

        # Arrivée
        route_steps.append({
            "letter": end_letter,
            "hebrew": end_pos.letter,
            "coordinates": list(end_pos.coordinates),
            "mode": self.cube.get_cognitive_mode(end_letter),
            "role": "arrivée",
        })

        return route_steps

    # ── Méthodes internes ──────────────────────────────────────

    @staticmethod
    def _net_vector(geom: RouteGeometry) -> tuple[float, float, float]:
        """Vecteur net d'une route (premier point → dernier point)."""
        if len(geom.positions) < 2:
            return (0.0, 0.0, 0.0)
        first = geom.positions[0]
        last = geom.positions[-1]
        return (
            round(last[0] - first[0], 4),
            round(last[1] - first[1], 4),
            round(last[2] - first[2], 4),
        )

    @staticmethod
    def _angle_between(
        v1: tuple[float, float, float],
        v2: tuple[float, float, float],
    ) -> float:
        """Angle en degrés entre 2 vecteurs 3D."""
        mag1 = math.sqrt(sum(c * c for c in v1))
        mag2 = math.sqrt(sum(c * c for c in v2))
        if mag1 == 0 or mag2 == 0:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        cos_angle = max(-1.0, min(1.0, dot / (mag1 * mag2)))
        return round(math.degrees(math.acos(cos_angle)), 2)

    @staticmethod
    def _geometric_similarity(
        a: RouteGeometry, b: RouteGeometry,
    ) -> float:
        """Similarité géométrique entre 2 routes (0-1).

        Compare : direction dominante, ratio ascent/descent,
        distance totale, passage par le centre.
        """
        score = 0.0
        weights = 0.0

        # Direction dominante identique
        if a.direction_dominant == b.direction_dominant:
            score += 0.4
        weights += 0.4

        # Ratio ascent/descent similaire
        a_ratio = a.ascent / max(a.ascent + a.descent, 0.001)
        b_ratio = b.ascent / max(b.ascent + b.descent, 0.001)
        ratio_sim = 1.0 - abs(a_ratio - b_ratio)
        score += 0.3 * ratio_sim
        weights += 0.3

        # Distance totale similaire
        max_dist = max(a.total_distance, b.total_distance, 0.001)
        dist_sim = 1.0 - abs(a.total_distance - b.total_distance) / max_dist
        score += 0.2 * dist_sim
        weights += 0.2

        # Passage par le centre
        if a.passes_center == b.passes_center:
            score += 0.1
        weights += 0.1

        return score / weights if weights > 0 else 0.0

    @staticmethod
    def _trajectory_distance(
        a: RouteGeometry, b: RouteGeometry,
    ) -> float:
        """Distance moyenne entre les trajectoires de 2 routes.

        Pour chaque point de la route la plus courte,
        calcule la distance au point correspondant (par index normalisé)
        de la route la plus longue.
        """
        if not a.positions or not b.positions:
            return 0.0

        # Normaliser : interpoler les positions
        shorter = a.positions if len(a.positions) <= len(b.positions) else b.positions
        longer = b.positions if len(a.positions) <= len(b.positions) else a.positions

        if len(shorter) == 1 and len(longer) == 1:
            c1, c2 = shorter[0], longer[0]
            return math.sqrt(sum((x - y) ** 2 for x, y in zip(c1, c2)))

        total = 0.0
        for i, pos in enumerate(shorter):
            # Index normalisé dans la route plus longue
            j = int(i * (len(longer) - 1) / max(len(shorter) - 1, 1))
            other = longer[j]
            total += math.sqrt(sum((x - y) ** 2 for x, y in zip(pos, other)))

        return total / len(shorter)

    def _find_intermediates(
        self,
        start: CubePosition,
        end: CubePosition,
    ) -> list[tuple[str, CubePosition, float]]:
        """Trouve les lettres intermédiaires entre 2 positions.

        Retourne les lettres les plus proches du segment start→end,
        triées par distance au segment.
        """
        s = start.coordinates
        e = end.coordinates
        seg_vec = (e[0] - s[0], e[1] - s[1], e[2] - s[2])
        seg_len = math.sqrt(sum(c * c for c in seg_vec))

        candidates = []
        for name, pos in self.cube.get_all_positions().items():
            if name in (start.name, end.name):
                continue
            p = pos.coordinates
            # Distance du point au segment
            dist = self._point_to_segment_distance(p, s, e, seg_vec, seg_len)
            candidates.append((name, pos, dist))

        candidates.sort(key=lambda x: x[2])
        return candidates

    @staticmethod
    def _point_to_segment_distance(
        point: tuple, seg_start: tuple, seg_end: tuple,
        seg_vec: tuple, seg_len: float,
    ) -> float:
        """Distance d'un point au segment start→end."""
        if seg_len == 0:
            return math.sqrt(sum(
                (p - s) ** 2 for p, s in zip(point, seg_start)
            ))

        # Projection du point sur le segment
        t = sum(
            (p - s) * v for p, s, v in zip(point, seg_start, seg_vec)
        ) / (seg_len * seg_len)
        t = max(0.0, min(1.0, t))

        # Point projeté
        proj = tuple(s + t * v for s, v in zip(seg_start, seg_vec))
        return math.sqrt(sum((p - pr) ** 2 for p, pr in zip(point, proj)))
