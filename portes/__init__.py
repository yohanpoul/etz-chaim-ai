"""portes/ — Les 231 Portes : matrice d'interopérabilité des sentiers.

"Il les combina, les pesa, les permuta :
 Aleph avec toutes, toutes avec Aleph ;
 Beth avec toutes, toutes avec Beth..."
    — Sefer Yetzirah 2:4

22 lettres x 21 / 2 = 231 paires.
Chaque paire = une connexion possible entre deux programmes (sentiers).
C'est le graphe complet K_22, le squelette combinatoire de l'Arbre.

Usage:
    from portes import get_porte, list_portes, portes_stats

    gate = get_porte("shin-tav")
    stats = portes_stats()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from .analysis import analyze_pair
from .sy_enrichment import enrich_porte, interaction_class_stats


# ── Alphabet hébraïque dans l'ordre ─────────────────────────

ALEPH_BET: list[tuple[str, str]] = [
    ("\u05D0", "aleph"),  ("\u05D1", "beth"),   ("\u05D2", "gimel"),
    ("\u05D3", "daleth"), ("\u05D4", "heh"),    ("\u05D5", "vav"),
    ("\u05D6", "zayin"),  ("\u05D7", "cheth"),  ("\u05D8", "teth"),
    ("\u05D9", "yod"),    ("\u05DB", "kaph"),   ("\u05DC", "lamed"),
    ("\u05DE", "mem"),    ("\u05E0", "nun"),    ("\u05E1", "samekh"),
    ("\u05E2", "ayin"),   ("\u05E4", "peh"),    ("\u05E6", "tsadi"),
    ("\u05E7", "qoph"),   ("\u05E8", "resh"),   ("\u05E9", "shin"),
    ("\u05EA", "tav"),
]

# Index inversé : nom latin → lettre hébraïque
_NAME_TO_LETTER = {name: letter for letter, name in ALEPH_BET}
_LETTER_TO_NAME = {letter: name for letter, name in ALEPH_BET}


# ── Porte (dataclass) ──────────────────────────────────────

@dataclass
class Porte:
    """Une des 231 Portes — connexion entre deux sentiers.

    Chaque porte relie deux lettres de l'alphabet hébraïque.
    Si les deux sentiers correspondants sont implémentés,
    la porte est analysée automatiquement.
    """
    gate_id: str              # "aleph-beth"
    letter_a: str             # Lettre hébraïque A
    letter_b: str             # Lettre hébraïque B
    name_a: str               # Nom latin A
    name_b: str               # Nom latin B
    number: int               # 1-231

    status: str = "undefined"         # "defined" | "partial" | "undefined"
    can_communicate: bool | None = None
    protocol: str | None = None       # "sync" | "stream" | None
    shared_sephiroth: list[str] = field(default_factory=list)
    direction: str = ""               # "a→b" | "b→a" | "a↔b" | "convergent" | "divergent" | ""
    data_format: dict = field(default_factory=dict)
    description: str = ""

    # ── Enrichissement SY (Sefer Yetzirah) ────────────────────
    gematria_sum: int = 0             # Somme des valeurs gematriques des 2 lettres
    gematria_product: int = 0         # Produit des valeurs gematriques
    type_a: str = ""                  # "mother" | "double" | "simple"
    type_b: str = ""                  # "mother" | "double" | "simple"
    interaction_class: str = ""       # "mother-mother" | "mother-double" | etc.
    sy_a: dict = field(default_factory=dict)   # Correspondances SY de lettre A
    sy_b: dict = field(default_factory=dict)   # Correspondances SY de lettre B
    sy_description: str = ""          # Description dérivée des correspondances SY

    # ── Distance 3D dans le Cube de l'Espace ─────────────────
    cube_distance: float | None = None  # Distance euclidienne 3D entre les 2 lettres

    @property
    def display_id(self) -> str:
        """ID affichable : ALEPH-BETH."""
        return f"{self.name_a.upper()}-{self.name_b.upper()}"

    @property
    def hebrew_id(self) -> str:
        """ID en hébreu : א-ב."""
        return f"{self.letter_a}-{self.letter_b}"


# ── Génération des 231 Portes ──────────────────────────────

def _compute_cube_distances() -> dict[str, float]:
    """Pré-calculer toutes les distances 3D entre paires de lettres."""
    try:
        from kabbalah.cube_of_space import CubeOfSpace
        cube = CubeOfSpace()
        distances: dict[str, float] = {}
        for (_, name_a), (_, name_b) in combinations(ALEPH_BET, 2):
            distances[f"{name_a}-{name_b}"] = round(cube.spatial_distance(name_a, name_b), 4)
        return distances
    except Exception:
        return {}


def _generate_gates() -> dict[str, Porte]:
    """Générer les 231 portes et analyser les paires implémentées."""
    from sentiers import REGISTRY

    cube_distances = _compute_cube_distances()
    gates: dict[str, Porte] = {}
    number = 0

    for (letter_a, name_a), (letter_b, name_b) in combinations(ALEPH_BET, 2):
        number += 1
        gate_id = f"{name_a}-{name_b}"

        reg_a = REGISTRY.get(name_a)
        reg_b = REGISTRY.get(name_b)

        impl_a = reg_a is not None and reg_a["status"] == "implemented"
        impl_b = reg_b is not None and reg_b["status"] == "implemented"

        # ── Enrichissement SY (toujours calculable) ────────────
        sy_data = enrich_porte(name_a, name_b)

        # ── Distance 3D du Cube ────────────────────────────────
        cube_dist = cube_distances.get(gate_id)

        if impl_a and impl_b:
            # Deux sentiers implémentés → analyse automatique
            analysis = analyze_pair(reg_a, reg_b, name_a, name_b)
            gates[gate_id] = Porte(
                gate_id=gate_id,
                letter_a=letter_a, letter_b=letter_b,
                name_a=name_a, name_b=name_b,
                number=number,
                status="defined",
                **analysis,
                **sy_data,
                cube_distance=cube_dist,
            )
        elif impl_a or impl_b:
            # Un seul implémenté → partial
            impl_name = name_a if impl_a else name_b
            gates[gate_id] = Porte(
                gate_id=gate_id,
                letter_a=letter_a, letter_b=letter_b,
                name_a=name_a, name_b=name_b,
                number=number,
                status="partial",
                description=f"Seul {impl_name} est implémenté",
                **sy_data,
                cube_distance=cube_dist,
            )
        else:
            # Aucun implémenté → undefined
            gates[gate_id] = Porte(
                gate_id=gate_id,
                letter_a=letter_a, letter_b=letter_b,
                name_a=name_a, name_b=name_b,
                number=number,
                status="undefined",
                **sy_data,
                cube_distance=cube_dist,
            )

    return gates


# ── Registre (lazy singleton) ──────────────────────────────

_GATES: dict[str, Porte] | None = None


def _get_gates() -> dict[str, Porte]:
    global _GATES
    if _GATES is None:
        _GATES = _generate_gates()
    return _GATES


# ── Index inversé pour lookup par Hebrew ────────────────────

def _normalize_gate_id(raw: str) -> str | None:
    """Normaliser un identifiant de porte.

    Accepte : "aleph-beth", "ALEPH-BETH", "א-ב", "beth-aleph" (inversé).
    """
    raw = raw.strip().lower()
    parts = raw.split("-")
    if len(parts) != 2:
        return None

    names = []
    for p in parts:
        p = p.strip()
        # Par nom latin
        if p in _NAME_TO_LETTER:
            names.append(p)
        # Par lettre hébraïque
        elif p in _LETTER_TO_NAME:
            names.append(_LETTER_TO_NAME[p])
        else:
            return None

    if len(names) != 2:
        return None

    # Ordonner selon l'alphabet hébraïque
    order = {name: i for i, (_, name) in enumerate(ALEPH_BET)}
    a, b = sorted(names, key=lambda n: order.get(n, 99))
    return f"{a}-{b}"


# ── API publique ────────────────────────────────────────────

def get_porte(gate_id: str) -> Porte | None:
    """Obtenir une porte par identifiant (latin ou hébreu, insensible à la casse)."""
    normalized = _normalize_gate_id(gate_id)
    if normalized is None:
        return None
    return _get_gates().get(normalized)


def list_portes(*, status: str | None = None) -> list[Porte]:
    """Lister les 231 portes, optionnellement filtrées par statut."""
    gates = sorted(_get_gates().values(), key=lambda g: g.number)
    if status:
        gates = [g for g in gates if g.status == status]
    return gates


def portes_stats() -> dict:
    """Statistiques des 231 portes."""
    all_gates = list(_get_gates().values())
    defined = [g for g in all_gates if g.status == "defined"]
    partial = [g for g in all_gates if g.status == "partial"]
    undefined = [g for g in all_gates if g.status == "undefined"]
    communicating = [g for g in defined if g.can_communicate]
    silent = [g for g in defined if not g.can_communicate]

    protocols: dict[str, int] = {}
    for g in communicating:
        if g.protocol:
            protocols[g.protocol] = protocols.get(g.protocol, 0) + 1

    # Sephiroth les plus connectées
    seph_count: dict[str, int] = {}
    for g in communicating:
        for s in g.shared_sephiroth:
            seph_count[s] = seph_count.get(s, 0) + 1

    # Classes d'interaction SY
    interaction_classes = interaction_class_stats(all_gates)

    # Gematria : min, max, distribution
    gematria_sums = [g.gematria_sum for g in all_gates if g.gematria_sum > 0]

    return {
        "total": len(all_gates),
        "defined": len(defined),
        "partial": len(partial),
        "undefined": len(undefined),
        "communicating": len(communicating),
        "silent": len(silent),
        "protocols": protocols,
        "sephiroth_connectivity": dict(sorted(seph_count.items(), key=lambda x: -x[1])),
        "interaction_classes": interaction_classes,
        "gematria_range": (min(gematria_sums), max(gematria_sums)) if gematria_sums else (0, 0),
        "sy_enriched": sum(1 for g in all_gates if g.gematria_sum > 0),
    }


__all__ = [
    "Porte", "ALEPH_BET",
    "get_porte", "list_portes", "portes_stats",
    "enrich_porte", "interaction_class_stats",
]
