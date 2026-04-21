"""cube_of_space.py — Le Cube de l'Espace du Sefer Yetzirah.

Système de navigation 3D basé sur SY 1:13, 3:2-5:4 (recension du Gra).
Les 22 lettres hébraïques sont mappées sur un cube :

  - 3 mères (אמ״ש) → 3 axes traversant le cube
  - 7 doubles (בגדכפר״ת) → 6 faces + 1 centre
  - 12 simples → 12 arêtes (gvulei alakhson)

Les 6 directions sont scellées par les 6 permutations de YHV (SY 1:13).
Chaque sceau définit un ORDRE DE PRIORITÉ cognitif pour le routing.

Chaque position encode un mode cognitif. La navigation entre
positions détermine le coût et le type de transition cognitive.

Usage:
    cube = CubeOfSpace()
    pos = cube.get_position("aleph")
    seal = cube.get_seal("haut")
    profile = cube.get_full_profile("beth")
    path = cube.navigate("beth", "resh")
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Chargement ──────────────────────────────────────────────

_YAML_PATH = Path(__file__).parent / "cube_of_space.yaml"
_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    with open(_YAML_PATH, encoding="utf-8") as f:
        _cache = yaml.safe_load(f) or {}
    return _cache


def _reload() -> dict:
    global _cache
    _cache = None
    return _load()


# ── Dataclasses ─────────────────────────────────────────────

@dataclass(frozen=True)
class CubePosition:
    """Position d'une lettre dans le Cube de l'Espace."""
    name: str               # nom latin (aleph, beth, ...)
    letter: str             # lettre hébraïque (א, ב, ...)
    gematria: int
    letter_type: str        # "mother", "double", "simple"
    cube_role: str          # "axis", "face", "center", "edge"
    direction: str          # "haut-bas", "nord", "nord-est", etc.
    coordinates: tuple[float, float, float]  # midpoint (rétrocompat)

    # Axes des mères (SY 3:2-4)
    from_coord: tuple[float, float, float] | None = None
    to_coord: tuple[float, float, float] | None = None

    # Mères
    element: str | None = None
    axis: str | None = None
    season: str | None = None
    body_part: str | None = None    # nefesh des mères (SY 3:4)

    # Doubles
    planet: str | None = None
    opposites: tuple[str, str] | None = None  # (dagesh, rafeh)
    day: str | None = None
    gate: str | None = None

    # Simples
    zodiac: str | None = None
    month: str | None = None
    sense: str | None = None
    tribe: str | None = None
    organ: str | None = None

    # Prononciation (SY 2:3)
    mouth_position: str | None = None   # gorge/palais/langue/dents/levres
    mouth_depth: int | None = None      # 5=gorge → 1=lèvres

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "name": self.name,
            "letter": self.letter,
            "gematria": self.gematria,
            "letter_type": self.letter_type,
            "cube_role": self.cube_role,
            "direction": self.direction,
            "coordinates": list(self.coordinates),
        }
        if self.from_coord is not None:
            d["from_coord"] = list(self.from_coord)
            d["to_coord"] = list(self.to_coord)
        if self.element is not None:
            d["element"] = self.element
            d["axis"] = self.axis
            d["season"] = self.season
            d["body_part"] = self.body_part
        if self.planet is not None:
            d["planet"] = self.planet
            d["opposites"] = list(self.opposites) if self.opposites else None
            d["day"] = self.day
            d["gate"] = self.gate
        if self.zodiac is not None:
            d["zodiac"] = self.zodiac
            d["month"] = self.month
            d["sense"] = self.sense
            d["tribe"] = self.tribe
            d["organ"] = self.organ
        if self.mouth_position is not None:
            d["mouth_position"] = self.mouth_position
            d["mouth_depth"] = self.mouth_depth
        return d


@dataclass(frozen=True)
class Seal:
    """Sceau directionnel — permutation de YHV (SY 1:13).

    Chaque sceau définit l'ordre de priorité cognitif :
      Y (Yod) = Chokmah = intuition/flash
      H (Hé)  = Binah   = analyse/compréhension
      V (Vav) = Tiferet = connexion/synthèse
    """
    direction: str            # "haut", "bas", "est", etc.
    permutation: str          # "YHV", "YVH", etc.
    hebrew: str               # "יהו", etc.
    letters: tuple[str, str, str]
    cognitive_order: tuple[str, str, str]
    sephirotic_order: tuple[str, str, str]
    description: str

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "permutation": self.permutation,
            "hebrew": self.hebrew,
            "letters": list(self.letters),
            "cognitive_order": list(self.cognitive_order),
            "sephirotic_order": list(self.sephirotic_order),
            "description": self.description,
        }


@dataclass(frozen=True)
class PronunciationPosition:
    """Position de prononciation d'une lettre dans la bouche (SY 2:3).

    Les 22 lettres sont placées en 5 endroits de la bouche,
    de l'intérieur (gorge) vers l'extérieur (lèvres).
    La profondeur encode le degré de « cachement » du son :
      gorge=5 (le plus profond) → lèvres=1 (le plus manifesté).
    """
    position: str          # "gorge", "palais", "langue", "dents", "levres"
    depth: int             # 5=gorge → 1=lèvres
    hebrew_name: str       # "גרון", "חיך", "לשון", "שיניים", "שפתיים"
    transliteration: str   # "garon", "chikk", "lashon", "shinayim", "sfatayim"
    quality: str           # description sonore


@dataclass(frozen=True)
class Triad:
    """Les 3 registres du Sefer Yetzirah (SY 3-5).

    Chaque lettre opère simultanément dans 3 plans :
      Olam  (עולם) = Espace — élément / planète / signe zodiacal
      Shanah (שנה) = Temps  — saison / jour / mois
      Nefesh (נפש) = Âme   — partie du corps
    """
    olam: str
    shanah: str
    nefesh: str

    def to_dict(self) -> dict:
        return {"olam": self.olam, "shanah": self.shanah, "nefesh": self.nefesh}


@dataclass(frozen=True)
class NavigationPath:
    """Chemin entre deux positions dans le cube."""
    origin: str
    destination: str
    distance: float
    axes_traversed: list[str]
    faces_traversed: list[str]
    cognitive_mode_from: str
    cognitive_mode_to: str

    def to_dict(self) -> dict:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "distance": round(self.distance, 4),
            "axes_traversed": self.axes_traversed,
            "faces_traversed": self.faces_traversed,
            "cognitive_mode_from": self.cognitive_mode_from,
            "cognitive_mode_to": self.cognitive_mode_to,
        }


# ── Constantes ──────────────────────────────────────────────

AXES = {
    "aleph": "z",   # haut-bas
    "mem": "x",     # est-ouest
    "shin": "y",    # nord-sud
}

FACE_DIRECTIONS = {
    "haut": (0, 0, 1),
    "bas": (0, 0, -1),
    "est": (1, 0, 0),
    "ouest": (-1, 0, 0),
    "nord": (0, 1, 0),
    "sud": (0, -1, 0),
}

_AXIS_NAMES = {0: "mem (est-ouest)", 1: "shin (nord-sud)", 2: "aleph (haut-bas)"}

# YHV → Sephirotic mapping
_YHV_SEPHIROT = {"Y": "chokmah", "H": "binah", "V": "tiferet"}
_YHV_COGNITIVE = {"Y": "intuition", "H": "analyse", "V": "synthèse"}


# ── CubeOfSpace ─────────────────────────────────────────────

class CubeOfSpace:
    """Le Cube de l'Espace — navigation cognitive 3D.

    Les 22 lettres du Sefer Yetzirah sont disposées sur un cube :
    mères = axes, doubles = faces + centre, simples = arêtes.
    Les 6 sceaux (permutations YHV) gouvernent l'ordre de routing.
    """

    def __init__(self) -> None:
        self._data = _load()
        self._positions: dict[str, CubePosition] = {}
        self._seals: dict[str, Seal] = {}

        # Lookups
        self._by_direction: dict[str, str] = {}
        self._by_element: dict[str, str] = {}
        self._by_planet: dict[str, str] = {}
        self._by_zodiac: dict[str, str] = {}
        self._by_sense: dict[str, str] = {}
        self._by_day: dict[str, str] = {}
        self._by_gate: dict[str, str] = {}
        self._by_tribe: dict[str, str] = {}
        self._by_month: dict[str, str] = {}
        self._by_organ: dict[str, str] = {}
        self._by_pronunciation: dict[str, list[str]] = {}  # position → [letter names]
        self._pronunciation_data: dict[str, PronunciationPosition] = {}  # position → PronunciationPosition

        self._build()

    def _build(self) -> None:
        self._build_pronunciation()
        self._build_seals()
        self._build_mothers()
        self._build_doubles()
        self._build_simples()

    def _build_pronunciation(self) -> None:
        for pos_name, info in self._data.get("pronunciation_positions", {}).items():
            self._pronunciation_data[pos_name] = PronunciationPosition(
                position=pos_name,
                depth=info["depth"],
                hebrew_name=info["hebrew"],
                transliteration=info["transliteration"],
                quality=info["quality"],
            )
            self._by_pronunciation[pos_name] = list(info["letters"])

    def _build_seals(self) -> None:
        for direction, info in self._data.get("seals", {}).items():
            self._seals[direction] = Seal(
                direction=direction,
                permutation=info["permutation"],
                hebrew=info["hebrew"],
                letters=tuple(info["letters"]),
                cognitive_order=tuple(info["cognitive_order"]),
                sephirotic_order=tuple(info["sephirotic_order"]),
                description=info.get("description", "").strip(),
            )

    def _build_mothers(self) -> None:
        for name, info in self._data.get("mothers", {}).items():
            coords_data = info["coordinates"]
            from_c = tuple(float(c) for c in coords_data["from"])
            to_c = tuple(float(c) for c in coords_data["to"])
            midpoint = tuple((f + t) / 2.0 for f, t in zip(from_c, to_c))
            pos = CubePosition(
                name=name,
                letter=info["letter"],
                gematria=info["gematria"],
                letter_type="mother",
                cube_role="axis",
                direction=info["axis"],
                coordinates=midpoint,
                from_coord=from_c,
                to_coord=to_c,
                element=info["element"],
                axis=info["axis"],
                season=info.get("season"),
                body_part=info.get("body_part"),
                mouth_position=info.get("mouth_position"),
                mouth_depth=info.get("mouth_depth"),
            )
            self._positions[name] = pos
            self._by_direction[info["axis"]] = name
            self._by_element[info["element"]] = name

    def _build_doubles(self) -> None:
        for name, info in self._data.get("doubles", {}).items():
            coords = tuple(float(c) for c in info["coordinates"])
            opps = info.get("opposites", {})
            pos = CubePosition(
                name=name,
                letter=info["letter"],
                gematria=info["gematria"],
                letter_type="double",
                cube_role=info["type"],
                direction=info["direction"],
                coordinates=coords,
                planet=info.get("planet"),
                opposites=(opps.get("dagesh", ""), opps.get("rafeh", "")),
                day=info.get("day"),
                gate=info.get("gate"),
                mouth_position=info.get("mouth_position"),
                mouth_depth=info.get("mouth_depth"),
            )
            self._positions[name] = pos
            self._by_direction[info["direction"]] = name
            if info.get("planet"):
                self._by_planet[info["planet"]] = name
            if info.get("day"):
                self._by_day[info["day"]] = name
            if info.get("gate"):
                self._by_gate[info["gate"]] = name

    def _build_simples(self) -> None:
        for name, info in self._data.get("simples", {}).items():
            coords = tuple(float(c) for c in info["coordinates"])
            pos = CubePosition(
                name=name,
                letter=info["letter"],
                gematria=info["gematria"],
                letter_type="simple",
                cube_role="edge",
                direction=info["direction"],
                coordinates=coords,
                zodiac=info.get("zodiac"),
                month=info.get("month"),
                sense=info.get("sense"),
                tribe=info.get("tribe"),
                organ=info.get("organ"),
                mouth_position=info.get("mouth_position"),
                mouth_depth=info.get("mouth_depth"),
            )
            self._positions[name] = pos
            self._by_direction[info["direction"]] = name
            if info.get("zodiac"):
                self._by_zodiac[info["zodiac"]] = name
            if info.get("sense"):
                self._by_sense[info["sense"]] = name
            if info.get("month"):
                self._by_month[info["month"]] = name
            if info.get("tribe"):
                self._by_tribe[info["tribe"]] = name
            if info.get("organ"):
                self._by_organ[info["organ"]] = name

    # ── Sceaux (SY 1:13) ───────────────────────────────────

    def get_seal(self, direction: str) -> Seal:
        """Le sceau (permutation YHV) d'une direction.

        Args:
            direction: "haut", "bas", "est", "ouest", "nord", "sud"

        Raises:
            KeyError: si la direction n'a pas de sceau.
        """
        if direction not in self._seals:
            raise KeyError(f"Pas de sceau pour: '{direction}'. Valides: {list(self._seals)}")
        return self._seals[direction]

    def get_all_seals(self) -> dict[str, Seal]:
        """Les 6 sceaux."""
        return dict(self._seals)

    def get_routing_priority(self, direction: str) -> list[str]:
        """Séquence sephirotique de routing pour une direction.

        Retourne l'ordre dans lequel consulter les modules
        Chokmah/Binah/Tiferet, selon le sceau de la direction.

        Ex: get_routing_priority("haut") → ["chokmah", "binah", "tiferet"]
        """
        seal = self.get_seal(direction)
        return list(seal.sephirotic_order)

    @staticmethod
    def seal_to_sephirotic_order(seal_str: str) -> list[str]:
        """Traduit une permutation YHV en ordre sephirotique.

        Args:
            seal_str: "YHV", "HVY", etc. (3 lettres Y/H/V)

        Returns:
            ["chokmah", "binah", "tiferet"] dans l'ordre du sceau.
        """
        if len(seal_str) != 3 or set(seal_str) != {"Y", "H", "V"}:
            raise ValueError(f"Permutation invalide: '{seal_str}'. Doit être une permutation de YHV.")
        return [_YHV_SEPHIROT[c] for c in seal_str]

    # ── Accès aux positions ─────────────────────────────────

    def get_position(self, letter_name: str) -> CubePosition:
        """Toutes les correspondances d'une lettre.

        Raises:
            KeyError: si la lettre n'existe pas dans le cube.
        """
        if letter_name not in self._positions:
            raise KeyError(f"Lettre inconnue: '{letter_name}'")
        return self._positions[letter_name]

    def get_letter_at(self, direction: str) -> str:
        """Lettre à une position donnée du cube.

        Raises:
            KeyError: si aucune lettre à cette position.
        """
        if direction not in self._by_direction:
            raise KeyError(f"Direction inconnue: '{direction}'")
        return self._by_direction[direction]

    def get_all_positions(self) -> dict[str, CubePosition]:
        """Toutes les 22 positions."""
        return dict(self._positions)

    def get_letters_by_class(self, letter_class: str) -> list[str]:
        """Toutes les lettres d'une classe.

        Args:
            letter_class: "mother", "double", "simple"
        """
        return [n for n, p in self._positions.items() if p.letter_type == letter_class]

    # ── Modes cognitifs ─────────────────────────────────────

    def get_cognitive_mode(self, letter_name: str) -> str:
        """Mode cognitif encodé par cette lettre.

        - Mère/axe : "axis:<element>"
        - Double/face : "face:<direction>:<opposites>"
        - Double/centre : "center:<opposites>"
        - Simple/arête : "edge:<sense>"
        """
        pos = self.get_position(letter_name)
        if pos.letter_type == "mother":
            return f"axis:{pos.element}"
        elif pos.cube_role == "center":
            return f"center:{pos.opposites[0]}/{pos.opposites[1]}"
        elif pos.letter_type == "double":
            return f"face:{pos.direction}:{pos.opposites[0]}/{pos.opposites[1]}"
        else:
            return f"edge:{pos.sense}"

    def get_opposites(self, letter_name: str) -> tuple[str, str] | None:
        """Paire d'opposés (dagesh/rafeh) pour les 7 doubles."""
        pos = self.get_position(letter_name)
        return pos.opposites

    # ── Profil complet ──────────────────────────────────────

    def get_full_profile(self, letter_name: str) -> dict:
        """Profil complet d'une lettre — toutes les correspondances.

        Inclut la position dans le cube, le mode cognitif,
        et le sceau de la direction si c'est une face.
        """
        pos = self.get_position(letter_name)
        profile = pos.to_dict()
        profile["cognitive_mode"] = self.get_cognitive_mode(letter_name)
        profile["triad"] = self.get_full_triad(letter_name).to_dict()

        # Si c'est une face avec un sceau
        if pos.cube_role == "face" and pos.direction in self._seals:
            seal = self._seals[pos.direction]
            profile["seal"] = seal.to_dict()

        # Arêtes adjacentes si c'est une face/centre
        if pos.cube_role in ("face", "center"):
            profile["adjacent_edges"] = self.get_adjacent_edges(letter_name)

        # Endpoints si c'est un axe
        if pos.cube_role == "axis":
            try:
                a, b = self.get_axis_endpoints(letter_name)
                profile["axis_endpoints"] = [a, b]
            except ValueError as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return profile

    # ── Registres Olam / Shanah / Nefesh (SY 3-5) ────────

    def get_olam(self, letter_name: str) -> str:
        """Ce que la lettre crée dans l'espace (עולם).

        Mères → élément (feu/eau/air), Doubles → planète, Simples → zodiaque.
        """
        pos = self.get_position(letter_name)
        if pos.letter_type == "mother":
            return pos.element
        elif pos.letter_type == "double":
            return pos.planet
        else:
            return pos.zodiac

    def get_shanah(self, letter_name: str) -> str:
        """Ce que la lettre gouverne dans le temps (שנה).

        Mères → saison, Doubles → jour de la semaine, Simples → mois.
        """
        pos = self.get_position(letter_name)
        if pos.letter_type == "mother":
            return pos.season
        elif pos.letter_type == "double":
            return pos.day
        else:
            return pos.month

    def get_nefesh(self, letter_name: str) -> str:
        """Ce que la lettre forme dans l'âme/corps (נפש).

        Mères → zone corporelle (tête/poitrine/ventre),
        Doubles → porte du visage, Simples → organe.
        """
        pos = self.get_position(letter_name)
        if pos.letter_type == "mother":
            return pos.body_part
        elif pos.letter_type == "double":
            return pos.gate
        else:
            return pos.organ

    def get_full_triad(self, letter_name: str) -> Triad:
        """Les 3 registres combinés d'une lettre."""
        return Triad(
            olam=self.get_olam(letter_name),
            shanah=self.get_shanah(letter_name),
            nefesh=self.get_nefesh(letter_name),
        )

    # ── Lookups par attribut ────────────────────────────────

    def get_by_element(self, element: str) -> str:
        """Lettre mère associée à un élément (feu/eau/air)."""
        if element not in self._by_element:
            raise KeyError(f"Élément inconnu: '{element}'. Valides: {list(self._by_element)}")
        return self._by_element[element]

    def get_by_planet(self, planet: str) -> str:
        """Lettre double associée à une planète."""
        if planet not in self._by_planet:
            raise KeyError(f"Planète inconnue: '{planet}'. Valides: {list(self._by_planet)}")
        return self._by_planet[planet]

    def get_by_zodiac(self, sign: str) -> str:
        """Lettre simple associée à un signe zodiacal."""
        if sign not in self._by_zodiac:
            raise KeyError(f"Signe inconnu: '{sign}'. Valides: {list(self._by_zodiac)}")
        return self._by_zodiac[sign]

    def get_by_sense(self, sense: str) -> str:
        """Lettre simple associée à un sens."""
        if sense not in self._by_sense:
            raise KeyError(f"Sens inconnu: '{sense}'. Valides: {list(self._by_sense)}")
        return self._by_sense[sense]

    def get_letter_by_day(self, day: str) -> str:
        """Lettre double associée à un jour de la semaine."""
        if day not in self._by_day:
            raise KeyError(f"Jour inconnu: '{day}'. Valides: {list(self._by_day)}")
        return self._by_day[day]

    def get_letter_by_gate(self, gate: str) -> str:
        """Lettre double associée à une porte de l'âme."""
        if gate not in self._by_gate:
            raise KeyError(f"Porte inconnue: '{gate}'. Valides: {list(self._by_gate)}")
        return self._by_gate[gate]

    def get_letter_by_month(self, month: str) -> str:
        """Lettre simple associée à un mois hébraïque."""
        if month not in self._by_month:
            raise KeyError(f"Mois inconnu: '{month}'. Valides: {list(self._by_month)}")
        return self._by_month[month]

    def get_letter_by_tribe(self, tribe: str) -> str:
        """Lettre simple associée à une tribu d'Israël."""
        if tribe not in self._by_tribe:
            raise KeyError(f"Tribu inconnue: '{tribe}'. Valides: {list(self._by_tribe)}")
        return self._by_tribe[tribe]

    def get_letter_by_organ(self, organ: str) -> str:
        """Lettre simple associée à un organe du corps."""
        if organ not in self._by_organ:
            raise KeyError(f"Organe inconnu: '{organ}'. Valides: {list(self._by_organ)}")
        return self._by_organ[organ]

    # ── Prononciation (SY 2:3) ─────────────────────────────

    def get_pronunciation(self, letter_name: str) -> PronunciationPosition:
        """Position de prononciation d'une lettre (SY 2:3).

        Retourne la position dans la bouche (gorge/palais/langue/dents/lèvres)
        avec la profondeur associée (5=gorge → 1=lèvres).

        Args:
            letter_name: nom latin (ex: "aleph", "beth")

        Raises:
            KeyError: si la lettre n'existe pas ou n'a pas de position.
        """
        pos = self.get_position(letter_name)
        if pos.mouth_position is None:
            raise KeyError(f"Pas de position de prononciation pour: '{letter_name}'")
        return self._pronunciation_data[pos.mouth_position]

    def get_letters_by_pronunciation(self, position: str) -> list[str]:
        """Lettres partageant une position de prononciation.

        Args:
            position: "gorge", "palais", "langue", "dents", "levres"

        Returns:
            Liste des noms de lettres dans cette famille sonore.

        Raises:
            KeyError: si la position n'existe pas.
        """
        if position not in self._by_pronunciation:
            raise KeyError(
                f"Position inconnue: '{position}'. "
                f"Valides: {list(self._by_pronunciation)}"
            )
        return list(self._by_pronunciation[position])

    def get_all_pronunciation_positions(self) -> dict[str, PronunciationPosition]:
        """Les 5 positions de prononciation."""
        return dict(self._pronunciation_data)

    # ── Navigation ──────────────────────────────────────────

    def get_axis(self, letter_name: str) -> tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ]:
        """Segment complet d'un axe mère : (from, to, direction).

        Les 3 mères sont des AXES qui traversent le cube,
        pas des points. Aleph relie Gimel(bas) à Beth(haut), etc.

        Raises:
            ValueError: si la lettre n'est pas une mère.
        """
        pos = self.get_position(letter_name)
        if pos.from_coord is None or pos.to_coord is None:
            raise ValueError(f"'{letter_name}' n'est pas un axe (mère)")
        direction = tuple(t - f for f, t in zip(pos.from_coord, pos.to_coord))
        return pos.from_coord, pos.to_coord, direction

    @staticmethod
    def _point_to_segment_dist(
        point: tuple[float, ...],
        seg_a: tuple[float, ...],
        seg_b: tuple[float, ...],
    ) -> float:
        """Distance d'un point au segment [seg_a, seg_b]."""
        seg_vec = tuple(b - a for a, b in zip(seg_a, seg_b))
        seg_len_sq = sum(v * v for v in seg_vec)
        if seg_len_sq == 0:
            return math.sqrt(sum((p - a) ** 2 for p, a in zip(point, seg_a)))
        t = sum((p - a) * v for p, a, v in zip(point, seg_a, seg_vec)) / seg_len_sq
        t = max(0.0, min(1.0, t))
        proj = tuple(a + t * v for a, v in zip(seg_a, seg_vec))
        return math.sqrt(sum((p - pr) ** 2 for p, pr in zip(point, proj)))

    @staticmethod
    def _segment_to_segment_dist(
        a1: tuple[float, ...], a2: tuple[float, ...],
        b1: tuple[float, ...], b2: tuple[float, ...],
    ) -> float:
        """Distance minimale entre deux segments [a1,a2] et [b1,b2]."""
        d = (a2[0] - a1[0], a2[1] - a1[1], a2[2] - a1[2])
        e = (b2[0] - b1[0], b2[1] - b1[1], b2[2] - b1[2])
        r = (a1[0] - b1[0], a1[1] - b1[1], a1[2] - b1[2])

        dd = sum(x * x for x in d)
        ee = sum(x * x for x in e)
        de = sum(x * y for x, y in zip(d, e))
        dr = sum(x * y for x, y in zip(d, r))
        er = sum(x * y for x, y in zip(e, r))

        denom = dd * ee - de * de
        if denom > 1e-12:
            s = (de * er - ee * dr) / denom
            t = (dd * er - de * dr) / denom
            s = max(0.0, min(1.0, s))
            t = max(0.0, min(1.0, t))
        else:
            s = 0.0
            t = er / ee if ee > 1e-12 else 0.0
            t = max(0.0, min(1.0, t))

        closest_a = tuple(a1[i] + s * d[i] for i in range(3))
        closest_b = tuple(b1[i] + t * e[i] for i in range(3))
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(closest_a, closest_b)))

    def spatial_distance(self, letter1: str, letter2: str) -> float:
        """Distance 3D entre deux lettres.

        Pour les mères (axes), utilise la distance point-à-segment
        ou segment-à-segment, pas la distance au midpoint.
        """
        p1 = self.get_position(letter1)
        p2 = self.get_position(letter2)
        is_axis1 = p1.from_coord is not None
        is_axis2 = p2.from_coord is not None

        if is_axis1 and is_axis2:
            return self._segment_to_segment_dist(
                p1.from_coord, p1.to_coord, p2.from_coord, p2.to_coord,
            )
        if is_axis1:
            return self._point_to_segment_dist(
                p2.coordinates, p1.from_coord, p1.to_coord,
            )
        if is_axis2:
            return self._point_to_segment_dist(
                p1.coordinates, p2.from_coord, p2.to_coord,
            )
        c1, c2 = p1.coordinates, p2.coordinates
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))

    def navigate(self, from_letter: str, to_letter: str) -> NavigationPath:
        """Chemin de navigation entre deux positions du cube.

        Pour les mères (axes), la distance est point-à-segment
        ou segment-à-segment.
        """
        p1 = self.get_position(from_letter)
        p2 = self.get_position(to_letter)

        dist = self.spatial_distance(from_letter, to_letter)

        # Effective coordinates for axis/face analysis
        c1 = p1.coordinates
        c2 = p2.coordinates

        axes = []
        for i, (a, b) in enumerate(zip(c1, c2)):
            if a != b:
                axes.append(_AXIS_NAMES[i])
        # If either letter IS an axis mother, note that axis is traversed
        _MOTHER_AXIS_IDX = {"aleph": 2, "mem": 0, "shin": 1}
        for name in (from_letter, to_letter):
            if name in _MOTHER_AXIS_IDX:
                axis_name = _AXIS_NAMES[_MOTHER_AXIS_IDX[name]]
                if axis_name not in axes:
                    axes.append(axis_name)

        faces = []
        for direction, face_coords in FACE_DIRECTIONS.items():
            for i, fc in enumerate(face_coords):
                if fc != 0:
                    if (c1[i] <= fc <= c2[i]) or (c2[i] <= fc <= c1[i]):
                        if c1[i] != c2[i]:
                            letter_at = self._by_direction.get(direction, "")
                            faces.append(f"{direction} ({letter_at})")
                    break

        return NavigationPath(
            origin=from_letter,
            destination=to_letter,
            distance=dist,
            axes_traversed=axes,
            faces_traversed=faces,
            cognitive_mode_from=self.get_cognitive_mode(from_letter),
            cognitive_mode_to=self.get_cognitive_mode(to_letter),
        )

    # ── Routing par le Cube ──────────────────────────────────

    # Mapping domaine → lettre(s) pour le routing
    _DOMAIN_LETTERS: dict[str, str] = {
        # Sens (12 simples)
        "vue": "heh", "ouïe": "vav", "odorat": "zayin",
        "parole": "cheth", "goût": "teth", "action": "yod",
        "mouvement": "lamed", "marche": "nun", "sommeil": "samekh",
        "colère": "ayin", "pensée": "tsadi", "méditation": "qoph",
        # Éléments (3 mères)
        "feu": "shin", "eau": "mem", "air": "aleph",
        # Planètes (7 doubles)
        "saturne": "beth", "jupiter": "gimel", "mars": "daleth",
        "soleil": "kaph", "vénus": "peh", "mercure": "resh", "lune": "tav",
        # Directions (faces)
        "haut": "beth", "bas": "gimel", "est": "daleth",
        "ouest": "kaph", "nord": "peh", "sud": "resh",
        # Opposés (dagesh des doubles)
        "sagesse": "beth", "richesse": "gimel", "fertilité": "daleth",
        "vie": "kaph", "domination": "peh", "paix": "resh", "grâce": "tav",
    }

    def route_by_cube(self, domain_or_letter: str) -> list[str]:
        """Séquence de routing sephirotique basée sur la position dans le Cube.

        Pour une lettre ou un domaine, détermine la face la plus proche
        dans le cube et retourne l'ordre de routing du sceau correspondant.

        Args:
            domain_or_letter: nom de lettre ("beth"), domaine ("vue"),
                              ou attribut ("saturne", "sagesse").

        Returns:
            Séquence ["chokmah", "binah", "tiferet"] dans l'ordre du sceau.
        """
        # Résoudre le nom en lettre
        letter = domain_or_letter.lower()
        if letter in self._DOMAIN_LETTERS:
            letter = self._DOMAIN_LETTERS[letter]
        if letter not in self._positions:
            raise KeyError(
                f"Domaine ou lettre inconnu: '{domain_or_letter}'. "
                f"Valides: lettres hébraïques ou {list(self._DOMAIN_LETTERS)}"
            )

        pos = self._positions[letter]

        # Si c'est une face avec un sceau direct, utiliser ce sceau
        if pos.cube_role == "face" and pos.direction in self._seals:
            return list(self._seals[pos.direction].sephirotic_order)

        # Sinon, trouver la face la plus proche (distance euclidienne)
        best_dir = None
        best_dist = float("inf")
        for direction, seal in self._seals.items():
            face_letter = self._by_direction.get(direction)
            if face_letter is None:
                continue
            face_pos = self._positions[face_letter]
            dist = math.sqrt(
                sum((a - b) ** 2 for a, b in zip(pos.coordinates, face_pos.coordinates))
            )
            if dist < best_dist:
                best_dist = dist
                best_dir = direction

        if best_dir is None:
            # Fallback : sceau du haut (YHV standard)
            return list(self._seals["haut"].sephirotic_order)

        return list(self._seals[best_dir].sephirotic_order)

    # ── Requêtes structurelles ──────────────────────────────

    def get_adjacent_edges(self, face_letter: str) -> list[str]:
        """Arêtes (simples) adjacentes à une face (double)."""
        pos = self.get_position(face_letter)
        if pos.cube_role not in ("face", "center"):
            raise ValueError(f"'{face_letter}' n'est pas une face/centre")

        if pos.cube_role == "center":
            return [n for n, p in self._positions.items() if p.cube_role == "edge"]

        adjacent = []
        fc = pos.coordinates
        for name, p in self._positions.items():
            if p.cube_role != "edge":
                continue
            for i in range(3):
                if fc[i] != 0 and p.coordinates[i] == fc[i]:
                    adjacent.append(name)
                    break
        return adjacent

    def get_axis_endpoints(self, mother_letter: str) -> tuple[str, str]:
        """Les deux faces aux extrémités de l'axe d'une lettre mère."""
        pos = self.get_position(mother_letter)
        if pos.letter_type != "mother":
            raise ValueError(f"'{mother_letter}' n'est pas une lettre mère")

        axis_dir = pos.axis
        parts = axis_dir.split("-")
        if len(parts) != 2:
            raise ValueError(f"Format d'axe inattendu: '{axis_dir}'")

        letter_a = self._by_direction.get(parts[0])
        letter_b = self._by_direction.get(parts[1])
        if letter_a is None or letter_b is None:
            raise ValueError(f"Faces introuvables pour l'axe '{axis_dir}'")
        return (letter_a, letter_b)

    # ── Format rapport ──────────────────────────────────────

    def format_report(self) -> list[str]:
        """Rapport formaté du Cube de l'Espace."""
        lines = [
            "══════════════════════════════════════════════════════════",
            "  קוּבִּיַּת הַמֶּרְחָב — Cube de l'Espace (SY, Gra)",
            "══════════════════════════════════════════════════════════",
            "",
            "  ── 6 Sceaux — Permutations YHV (SY 1:13) ──",
        ]
        for direction in ("haut", "bas", "est", "ouest", "nord", "sud"):
            seal = self._seals[direction]
            lines.append(
                f"    {seal.hebrew} {seal.permutation} → {direction:6s} │ "
                f"{' → '.join(seal.sephirotic_order)}"
            )

        lines.append("")
        lines.append("  ── 3 Mères — Axes ──")
        for name in ("aleph", "mem", "shin"):
            p = self._positions[name]
            lines.append(f"    {p.letter} {name:8s} │ {p.element:4s} │ {p.season:13s} │ axe {p.axis}")

        lines.append("")
        lines.append("  ── 7 Doubles — Faces + Centre ──")
        for name in ("beth", "gimel", "daleth", "kaph", "peh", "resh", "tav"):
            p = self._positions[name]
            opps = f"{p.opposites[0]}/{p.opposites[1]}" if p.opposites else ""
            lines.append(
                f"    {p.letter} {name:8s} │ {p.direction:7s} │ {p.planet:8s} │ "
                f"{p.day:9s} │ {p.gate:15s} │ {opps}"
            )

        lines.append("")
        lines.append("  ── 12 Simples — Arêtes ──")
        for name in ("heh", "vav", "zayin", "cheth", "teth", "yod",
                      "lamed", "nun", "samekh", "ayin", "tsadi", "qoph"):
            p = self._positions[name]
            lines.append(
                f"    {p.letter} {name:8s} │ {p.direction:12s} │ "
                f"{p.zodiac:12s} │ {p.month:10s} │ {p.sense:10s} │ "
                f"{p.tribe:10s} │ {p.organ}"
            )

        return lines
