"""portes/sy_enrichment.py — Enrichissement des 231 Portes par le Sefer Yetzirah.

"Il les combina, les pesa, les permuta" (SY 2:4).
Chaque porte reçoit :
  - Valeur gematrique combinée (somme et produit)
  - Classification des lettres (mère / double / simple)
  - Classe d'interaction (mère×mère, mère×double, etc.)
  - Correspondances SY pour chaque lettre (élément, planète, zodiaque, sens, etc.)
  - Description SY dérivée automatiquement

Calcul pur — aucun LLM, aucune heuristique.
"""

from __future__ import annotations

import yaml
from pathlib import Path


# ── Chargement SY (lazy singleton) ────────────────────────────

_SY_DATA: dict | None = None
_SY_PATH = Path(__file__).resolve().parent.parent / "sentiers" / "sefer_yetzirah.yaml"


def _load_sy() -> dict:
    global _SY_DATA
    if _SY_DATA is None:
        with open(_SY_PATH) as f:
            _SY_DATA = yaml.safe_load(f)
    return _SY_DATA


# ── Index lettre → propriétés SY ──────────────────────────────

_LETTER_INDEX: dict[str, dict] | None = None


def _get_letter_index() -> dict[str, dict]:
    """Construit un index name → {category, gematria, ...} pour les 22 lettres."""
    global _LETTER_INDEX
    if _LETTER_INDEX is not None:
        return _LETTER_INDEX

    sy = _load_sy()
    index: dict[str, dict] = {}

    for name, data in sy.get("mothers", {}).items():
        index[name] = {
            "category": "mother",
            "letter": data["letter"],
            "gematria": data["gematria"],
            "element": data.get("element"),
            "body": data.get("body"),
            "season": data.get("season"),
            "quality": data.get("quality"),
            "archetype": data.get("archetype"),
        }

    for name, data in sy.get("doubles", {}).items():
        index[name] = {
            "category": "double",
            "letter": data["letter"],
            "gematria": data["gematria"],
            "planet": data.get("planet"),
            "day": data.get("day"),
            "gate": data.get("gate"),
            "direction": data.get("direction"),
            "archetype": data.get("archetype"),
        }

    for name, data in sy.get("simples", {}).items():
        index[name] = {
            "category": "simple",
            "letter": data["letter"],
            "gematria": data["gematria"],
            "sense": data.get("sense"),
            "zodiac": data.get("zodiac"),
            "month": data.get("month"),
            "direction": data.get("direction"),
            "organ": data.get("organ"),
            "archetype": data.get("archetype"),
        }

    _LETTER_INDEX = index
    return index


# ── Classes d'interaction ─────────────────────────────────────

# L'ordre reflète la hiérarchie SY : mères > doubles > simples
_CATEGORY_ORDER = {"mother": 0, "double": 1, "simple": 2}

# Description SY de chaque classe d'interaction
_INTERACTION_DESCRIPTIONS: dict[str, str] = {
    "mother-mother": "Interaction entre éléments primordiaux (feu/eau/air)",
    "mother-double": "Élément primordial × force planétaire",
    "mother-simple": "Élément primordial × sens/faculté",
    "double-double": "Interaction entre forces planétaires",
    "double-simple": "Force planétaire × sens/faculté",
    "simple-simple": "Interaction entre sens/facultés",
}


def _interaction_class(cat_a: str, cat_b: str) -> str:
    """Classe d'interaction canonique (toujours mère avant double avant simple)."""
    pair = sorted([cat_a, cat_b], key=lambda c: _CATEGORY_ORDER.get(c, 9))
    return f"{pair[0]}-{pair[1]}"


# ── Description SY d'une porte ────────────────────────────────

def _sy_description(name_a: str, name_b: str, info_a: dict, info_b: dict) -> str:
    """Génère une description basée sur les correspondances SY."""
    cat_a = info_a["category"]
    cat_b = info_b["category"]
    parts: list[str] = []

    # Éléments (mères)
    if cat_a == "mother" and cat_b == "mother":
        parts.append(f"{info_a['element']}×{info_b['element']}")
    elif cat_a == "mother":
        parts.append(f"élément {info_a['element']}")
    elif cat_b == "mother":
        parts.append(f"élément {info_b['element']}")

    # Planètes (doubles)
    planets = []
    if cat_a == "double" and info_a.get("planet"):
        planets.append(info_a["planet"])
    if cat_b == "double" and info_b.get("planet"):
        planets.append(info_b["planet"])
    if planets:
        parts.append("×".join(planets) if len(planets) == 2 else planets[0])

    # Sens (simples)
    senses = []
    if cat_a == "simple" and info_a.get("sense"):
        senses.append(info_a["sense"])
    if cat_b == "simple" and info_b.get("sense"):
        senses.append(info_b["sense"])
    if senses:
        parts.append("×".join(senses) if len(senses) == 2 else senses[0])

    # Zodiaques (simples)
    zodiacs = []
    if cat_a == "simple" and info_a.get("zodiac"):
        zodiacs.append(info_a["zodiac"])
    if cat_b == "simple" and info_b.get("zodiac"):
        zodiacs.append(info_b["zodiac"])
    if len(zodiacs) == 2:
        parts.append(f"{zodiacs[0]}–{zodiacs[1]}")

    return " | ".join(parts) if parts else ""


# ── API principale ────────────────────────────────────────────

def enrich_porte(name_a: str, name_b: str) -> dict:
    """Calcule l'enrichissement SY pour une paire de lettres.

    Retourne un dict prêt à être injecté dans les champs de Porte :
        gematria_sum, gematria_product,
        type_a, type_b, interaction_class,
        sy_a, sy_b, sy_description
    """
    index = _get_letter_index()
    info_a = index.get(name_a, {})
    info_b = index.get(name_b, {})

    gematria_a = info_a.get("gematria", 0)
    gematria_b = info_b.get("gematria", 0)
    cat_a = info_a.get("category", "unknown")
    cat_b = info_b.get("category", "unknown")

    return {
        "gematria_sum": gematria_a + gematria_b,
        "gematria_product": gematria_a * gematria_b,
        "type_a": cat_a,
        "type_b": cat_b,
        "interaction_class": _interaction_class(cat_a, cat_b),
        "sy_a": _compact_sy(info_a),
        "sy_b": _compact_sy(info_b),
        "sy_description": _sy_description(name_a, name_b, info_a, info_b),
    }


def _compact_sy(info: dict) -> dict:
    """Extrait les correspondances SY pertinentes (sans redondance)."""
    result: dict = {}
    for key in ("element", "planet", "sense", "zodiac", "month",
                "body", "season", "day", "gate", "direction", "organ",
                "quality", "archetype"):
        if key in info and info[key] is not None:
            result[key] = info[key]
    return result


def interaction_class_stats(portes: list) -> dict[str, int]:
    """Compte les portes par classe d'interaction."""
    counts: dict[str, int] = {}
    for p in portes:
        cls = getattr(p, "interaction_class", "unknown")
        counts[cls] = counts.get(cls, 0) + 1
    return dict(sorted(counts.items()))
