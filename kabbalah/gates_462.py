"""gates_462.py — Les 462 Portes directionnelles du Sefer Yetzirah.

שַׁעֲרֵי כִּוּוּן — Portes de direction

SY 2:4-5 : "Il les plaça dans un cercle comme un mur avec 231 portes.
Le cercle oscille d'avant en arrière."
"Il les permuta : Aleph avec toutes et toutes avec Aleph,
Beth avec toutes et toutes avec Beth..."

Le SY dit explicitement AB ET BA — chaque porte a DEUX directions.
231 × 2 = 462 portes. AB ≠ BA : la porte Aleph→Beth (de l'air vers
la sagesse) n'est PAS la même que Beth→Aleph (de la sagesse vers l'air).

Le cercle "oscille" (מתגלגל) = les portes fonctionnent dans les deux sens.
L'oscillation est le Ratzo v'Shov à l'échelle du graphe complet K₂₂.

Usage:
    gates = Gates462()
    gate = gates.get_gate("aleph", "mem")       # A→M
    inv  = gates.oscillate(gate)                  # M→A
    pair = gates.get_gate_pair("aleph", "mem")   # (A→M, M→A)
    asc  = gates.get_ascending_gates()            # montantes
    route = gates.word_to_gates("אמת")            # séquence de portes
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import permutations as _perms
from typing import Iterator

from kabbalah.cube_of_space import CubeOfSpace, CubePosition


# ── Mapping hébreu → nom latin ─────────────────────────────────

_HEBREW_TO_NAME: dict[str, str] = {
    "א": "aleph", "ב": "beth", "ג": "gimel", "ד": "daleth",
    "ה": "heh", "ו": "vav", "ז": "zayin", "ח": "cheth",
    "ט": "teth", "י": "yod", "כ": "kaph", "ל": "lamed",
    "מ": "mem", "נ": "nun", "ס": "samekh", "ע": "ayin",
    "פ": "peh", "צ": "tsadi", "ק": "qoph", "ר": "resh",
    "ש": "shin", "ת": "tav",
}

# Noms ordonnés selon l'alphabet hébraïque
_ALEPH_BET_NAMES: list[str] = [
    "aleph", "beth", "gimel", "daleth", "heh", "vav",
    "zayin", "cheth", "teth", "yod", "kaph", "lamed",
    "mem", "nun", "samekh", "ayin", "peh", "tsadi",
    "qoph", "resh", "shin", "tav",
]


# ── DirectionalGate ───────────────────────────────────────────

@dataclass(frozen=True)
class DirectionalGate:
    """Une porte directionnelle — A→B dans le Cube de l'Espace.

    AB ≠ BA. La porte Aleph→Mem (descente de l'air vers l'eau)
    n'est pas la même que Mem→Aleph (montée de l'eau vers l'air).
    """
    # Identité
    letter_from: str          # nom latin de la lettre source
    letter_to: str            # nom latin de la lettre destination
    hebrew_from: str          # lettre hébraïque source
    hebrew_to: str            # lettre hébraïque destination
    gate_id: str              # "aleph→mem"

    # Géométrie 3D dans le Cube
    direction_vector: tuple[float, float, float]  # vecteur (dx, dy, dz)
    distance: float           # norme euclidienne du vecteur
    is_ascending: bool        # dz > 0 (montée dans le Cube)
    is_descending: bool       # dz < 0 (descente dans le Cube)
    is_horizontal: bool       # |dz| < seuil, mouvement latéral

    # Axes mères traversés
    axes_traversed: tuple[str, ...]   # ("aleph",) si traverse l'axe haut-bas, etc.
    primary_axis: str | None          # axe dominant du mouvement

    # Transitions dans les 3 registres (SY 3-5)
    olam_transition: tuple[str, str]     # (olam_from, olam_to) — espace
    shanah_transition: tuple[str, str]   # (shanah_from, shanah_to) — temps
    nefesh_transition: tuple[str, str]   # (nefesh_from, nefesh_to) — corps

    # Métadonnées des lettres
    type_from: str            # "mother" | "double" | "simple"
    type_to: str              # "mother" | "double" | "simple"
    interaction_class: str    # "mother→double", "simple→mother", etc.

    @property
    def display_id(self) -> str:
        return f"{self.letter_from.upper()}→{self.letter_to.upper()}"

    @property
    def hebrew_id(self) -> str:
        return f"{self.hebrew_from}→{self.hebrew_to}"

    @property
    def vertical_character(self) -> str:
        """Caractère vertical du mouvement."""
        if self.is_ascending:
            return "ascending"
        elif self.is_descending:
            return "descending"
        return "horizontal"

    def to_dict(self) -> dict:
        return {
            "gate_id": self.gate_id,
            "hebrew": self.hebrew_id,
            "from": self.letter_from,
            "to": self.letter_to,
            "direction_vector": list(self.direction_vector),
            "distance": round(self.distance, 4),
            "vertical": self.vertical_character,
            "axes_traversed": list(self.axes_traversed),
            "olam": list(self.olam_transition),
            "shanah": list(self.shanah_transition),
            "nefesh": list(self.nefesh_transition),
            "interaction_class": self.interaction_class,
        }


# ── Gates462 ──────────────────────────────────────────────────

# Seuil pour considérer un mouvement comme horizontal
_VERTICAL_THRESHOLD = 0.01

# Axes mères : index de coordonnée → nom de lettre mère
_AXIS_INDEX = {
    0: "mem",     # x = est-ouest
    1: "shin",    # y = nord-sud
    2: "aleph",   # z = haut-bas
}


class Gates462:
    """Les 462 Portes directionnelles — le graphe complet K₂₂ orienté.

    231 paires × 2 directions = 462 portes.
    Chaque porte encode un mouvement dans le Cube de l'Espace
    avec sa géométrie 3D et ses transitions dans les 3 registres.
    """

    def __init__(self, cube: CubeOfSpace | None = None) -> None:
        self.cube = cube or CubeOfSpace()
        self._gates: dict[str, DirectionalGate] = {}
        self._build_all_gates()

    def _effective_coords(
        self, pos: CubePosition, toward: CubePosition | None = None,
    ) -> tuple[float, float, float]:
        """Coordonnées effectives d'une lettre pour le calcul directionnel.

        Pour les mères (axes), quand toward est donné, utilise le point
        sur l'axe le PLUS PROCHE de la position de toward — pas le pôle
        positif ni le midpoint (0,0,0).

        Aleph→Beth : Beth EST à (0,0,1) = to_coord d'Aleph → distance 0.
        Aleph→Daleth : Daleth est à (1,0,0), point le plus proche sur
          l'axe z = (0,0,0) → vecteur (1,0,0).
        Shin→Resh : Resh est à (0,-1,0) = from_coord de Shin → distance 0.

        Ceci préserve l'antisymétrie : vec(A→B) = -vec(B→A).
        """
        if pos.from_coord is not None and pos.to_coord is not None:
            if toward is not None:
                # Référence = coordonnées de base de toward
                ref = toward.coordinates
                return self._closest_on_axis(pos.from_coord, pos.to_coord, ref)
            # Sans contexte toward : pôle positif (rétrocompat)
            return pos.to_coord
        return pos.coordinates

    @staticmethod
    def _closest_on_axis(
        seg_from: tuple[float, float, float],
        seg_to: tuple[float, float, float],
        point: tuple[float, float, float],
    ) -> tuple[float, float, float]:
        """Point le plus proche sur un segment [seg_from, seg_to] depuis point."""
        ax = (seg_to[0] - seg_from[0], seg_to[1] - seg_from[1], seg_to[2] - seg_from[2])
        ax_len_sq = ax[0] ** 2 + ax[1] ** 2 + ax[2] ** 2
        if ax_len_sq == 0:
            return seg_from
        diff = (point[0] - seg_from[0], point[1] - seg_from[1], point[2] - seg_from[2])
        t = (diff[0] * ax[0] + diff[1] * ax[1] + diff[2] * ax[2]) / ax_len_sq
        t = max(0.0, min(1.0, t))
        return (
            round(seg_from[0] + t * ax[0], 6),
            round(seg_from[1] + t * ax[1], 6),
            round(seg_from[2] + t * ax[2], 6),
        )

    def _direction_vector(
        self, from_pos: CubePosition, to_pos: CubePosition,
    ) -> tuple[float, float, float]:
        """Vecteur direction de from vers to.

        Quand une lettre est une mère (axe), utilise le point le plus
        proche sur l'axe vers l'autre lettre. Préserve l'antisymétrie.
        """
        c1 = self._effective_coords(from_pos, toward=to_pos)
        c2 = self._effective_coords(to_pos, toward=from_pos)
        return (
            round(c2[0] - c1[0], 6),
            round(c2[1] - c1[1], 6),
            round(c2[2] - c1[2], 6),
        )

    def _axes_traversed(
        self, vec: tuple[float, float, float],
    ) -> tuple[str, ...]:
        """Quels axes mères sont traversés par ce vecteur."""
        axes = []
        for i, component in enumerate(vec):
            if abs(component) > _VERTICAL_THRESHOLD:
                axes.append(_AXIS_INDEX[i])
        return tuple(axes)

    def _primary_axis(self, vec: tuple[float, float, float]) -> str | None:
        """Axe dominant du mouvement (composante la plus grande)."""
        abs_components = [abs(v) for v in vec]
        max_val = max(abs_components)
        if max_val < _VERTICAL_THRESHOLD:
            return None
        max_idx = abs_components.index(max_val)
        return _AXIS_INDEX[max_idx]

    def _build_gate(
        self, name_from: str, name_to: str,
    ) -> DirectionalGate:
        """Construit une porte directionnelle."""
        pos_from = self.cube.get_position(name_from)
        pos_to = self.cube.get_position(name_to)

        vec = self._direction_vector(pos_from, pos_to)
        dist = math.sqrt(sum(c * c for c in vec))
        dz = vec[2]

        return DirectionalGate(
            letter_from=name_from,
            letter_to=name_to,
            hebrew_from=pos_from.letter,
            hebrew_to=pos_to.letter,
            gate_id=f"{name_from}→{name_to}",
            direction_vector=vec,
            distance=round(dist, 6),
            is_ascending=dz > _VERTICAL_THRESHOLD,
            is_descending=dz < -_VERTICAL_THRESHOLD,
            is_horizontal=abs(dz) <= _VERTICAL_THRESHOLD,
            axes_traversed=self._axes_traversed(vec),
            primary_axis=self._primary_axis(vec),
            olam_transition=(
                self.cube.get_olam(name_from),
                self.cube.get_olam(name_to),
            ),
            shanah_transition=(
                self.cube.get_shanah(name_from),
                self.cube.get_shanah(name_to),
            ),
            nefesh_transition=(
                self.cube.get_nefesh(name_from),
                self.cube.get_nefesh(name_to),
            ),
            type_from=pos_from.letter_type,
            type_to=pos_to.letter_type,
            interaction_class=f"{pos_from.letter_type}→{pos_to.letter_type}",
        )

    def _build_all_gates(self) -> None:
        """Génère les 462 portes (231 paires × 2 directions)."""
        for i, name_a in enumerate(_ALEPH_BET_NAMES):
            for name_b in _ALEPH_BET_NAMES[i + 1:]:
                # Porte directe : A→B
                gate_ab = self._build_gate(name_a, name_b)
                self._gates[gate_ab.gate_id] = gate_ab
                # Porte inverse : B→A
                gate_ba = self._build_gate(name_b, name_a)
                self._gates[gate_ba.gate_id] = gate_ba

    # ── Accès ──────────────────────────────────────────────────

    def get_gate(self, from_letter: str, to_letter: str) -> DirectionalGate:
        """Obtenir une porte directionnelle.

        Args:
            from_letter: nom latin de la lettre source
            to_letter: nom latin de la lettre destination

        Raises:
            KeyError: si la paire n'existe pas.
        """
        gate_id = f"{from_letter}→{to_letter}"
        if gate_id not in self._gates:
            raise KeyError(
                f"Porte inconnue: '{gate_id}'. "
                f"Vérifier les noms : {from_letter}, {to_letter}"
            )
        return self._gates[gate_id]

    def get_gate_pair(
        self, letter_a: str, letter_b: str,
    ) -> tuple[DirectionalGate, DirectionalGate]:
        """La paire directe/inverse : (A→B, B→A).

        L'oscillation du cercle (SY 2:4).
        """
        return (
            self.get_gate(letter_a, letter_b),
            self.get_gate(letter_b, letter_a),
        )

    def oscillate(self, gate: DirectionalGate) -> DirectionalGate:
        """La porte inverse — le cercle qui oscille (מתגלגל).

        SY 2:4 : "Le cercle oscille d'avant en arrière."
        Si la porte va de A vers B, oscillate retourne B vers A.
        """
        return self.get_gate(gate.letter_to, gate.letter_from)

    # ── Filtres ────────────────────────────────────────────────

    def all_gates(self) -> list[DirectionalGate]:
        """Les 462 portes."""
        return list(self._gates.values())

    def get_ascending_gates(self) -> list[DirectionalGate]:
        """Portes qui montent dans le Cube (dz > 0).

        Montée = abstraction, spiritualisation (SY cosmologie).
        """
        return [g for g in self._gates.values() if g.is_ascending]

    def get_descending_gates(self) -> list[DirectionalGate]:
        """Portes qui descendent dans le Cube (dz < 0).

        Descente = concrétisation, matérialisation.
        """
        return [g for g in self._gates.values() if g.is_descending]

    def get_horizontal_gates(self) -> list[DirectionalGate]:
        """Portes de mouvement latéral (changement de perspective)."""
        return [g for g in self._gates.values() if g.is_horizontal]

    def get_gates_crossing_axis(self, axis: str) -> list[DirectionalGate]:
        """Portes qui traversent un axe mère.

        Args:
            axis: "aleph" (haut-bas), "mem" (est-ouest), "shin" (nord-sud)
        """
        return [g for g in self._gates.values() if axis in g.axes_traversed]

    def get_gates_from(self, letter: str) -> list[DirectionalGate]:
        """Les 21 portes partant d'une lettre donnée."""
        return [g for g in self._gates.values() if g.letter_from == letter]

    def get_gates_to(self, letter: str) -> list[DirectionalGate]:
        """Les 21 portes arrivant à une lettre donnée."""
        return [g for g in self._gates.values() if g.letter_to == letter]

    def get_gates_by_interaction(self, interaction: str) -> list[DirectionalGate]:
        """Portes filtrées par classe d'interaction.

        Args:
            interaction: "mother→double", "simple→simple", etc.
        """
        return [g for g in self._gates.values() if g.interaction_class == interaction]

    # ── Routes de mots ─────────────────────────────────────────

    def word_to_gates(self, word: str) -> list[DirectionalGate]:
        """Convertit un mot hébreu en séquence de portes directionnelles.

        Chaque transition lettre[i]→lettre[i+1] dans le mot
        est une porte traversée. Le mot אמת (Emet) = 2 portes :
          Aleph→Mem + Mem→Tav.

        Args:
            word: mot hébreu (ex: "אמת")

        Returns:
            Liste de DirectionalGate dans l'ordre du mot.
        """
        # Résoudre les lettres
        names = []
        for ch in word:
            name = _HEBREW_TO_NAME.get(ch)
            if name is not None:
                names.append(name)

        if len(names) < 2:
            return []

        gates = []
        for i in range(len(names) - 1):
            if names[i] != names[i + 1]:  # skip lettre identique
                gates.append(self.get_gate(names[i], names[i + 1]))

        return gates

    def word_gate_summary(self, word: str) -> dict:
        """Résumé des portes traversées par un mot.

        Donne le profil directionnel complet : combien de montées,
        descentes, quels axes traversés, distance totale.
        """
        gates = self.word_to_gates(word)
        if not gates:
            return {
                "word": word,
                "gates_count": 0,
                "gates": [],
                "total_distance": 0.0,
                "ascending_count": 0,
                "descending_count": 0,
                "horizontal_count": 0,
                "axes_traversed": [],
                "net_vertical": 0.0,
            }

        total_dist = sum(g.distance for g in gates)
        asc = sum(1 for g in gates if g.is_ascending)
        desc = sum(1 for g in gates if g.is_descending)
        horiz = sum(1 for g in gates if g.is_horizontal)

        all_axes: set[str] = set()
        for g in gates:
            all_axes.update(g.axes_traversed)

        net_vertical = sum(g.direction_vector[2] for g in gates)

        return {
            "word": word,
            "gates_count": len(gates),
            "gates": [g.gate_id for g in gates],
            "total_distance": round(total_dist, 4),
            "ascending_count": asc,
            "descending_count": desc,
            "horizontal_count": horiz,
            "axes_traversed": sorted(all_axes),
            "net_vertical": round(net_vertical, 4),
        }

    # ── Statistiques ───────────────────────────────────────────

    def stats(self) -> dict:
        """Statistiques des 462 portes."""
        all_g = self.all_gates()
        asc = [g for g in all_g if g.is_ascending]
        desc = [g for g in all_g if g.is_descending]
        horiz = [g for g in all_g if g.is_horizontal]

        # Classes d'interaction
        interaction_counts: dict[str, int] = {}
        for g in all_g:
            interaction_counts[g.interaction_class] = (
                interaction_counts.get(g.interaction_class, 0) + 1
            )

        # Axes traversés
        axis_counts: dict[str, int] = {}
        for g in all_g:
            for ax in g.axes_traversed:
                axis_counts[ax] = axis_counts.get(ax, 0) + 1

        return {
            "total": len(all_g),
            "ascending": len(asc),
            "descending": len(desc),
            "horizontal": len(horiz),
            "pairs": len(all_g) // 2,
            "interaction_classes": dict(sorted(
                interaction_counts.items(), key=lambda x: -x[1],
            )),
            "axis_crossing": dict(sorted(
                axis_counts.items(), key=lambda x: -x[1],
            )),
        }

    def __len__(self) -> int:
        return len(self._gates)

    def __iter__(self) -> Iterator[DirectionalGate]:
        return iter(self._gates.values())

    def __contains__(self, gate_id: str) -> bool:
        return gate_id in self._gates
