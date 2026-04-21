"""Omer Daily Influence — Modulateur quotidien de l'Arbre.

ספירת העומר — Chaque jour du Omer colore TOUT le comportement de l'Arbre.

La grille 7x7 : 49 jours, chaque jour = Sefirah_secondaire sh'b'Sefirah_primaire.
- Semaine (primaire) = la tonalite dominante
- Jour dans la semaine (secondaire) = la nuance du jour

Quand c'est Gevurah sh'b'Chesed (jour 2), AutoJudge (Gevurah) est booste
mais ExplorationEngine (Chesed) domine la semaine — les deux se colorent.

L'Omer n'ecrase pas les seuils — il les MODULE temporairement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any


# ── Grille 7x7 ────────────────────────────────────────────

MIDOT_ORDER = ["chesed", "gevurah", "tiferet", "netzach", "hod", "yesod", "malkuth"]

MIDAH_HEBREW = {
    "chesed":  "חסד",
    "gevurah": "גבורה",
    "tiferet": "תפארת",
    "netzach": "נצח",
    "hod":     "הוד",
    "yesod":   "יסוד",
    "malkuth": "מלכות",
}

# Mapping Sefirah → module de l'Arbre
SEFIRAH_TO_MODULE = {
    "chesed":  "explorationengine",
    "gevurah": "autojudge",
    "tiferet": "dissensuengine",
    "netzach": "intentkeeper",
    "hod":     "selfmap",
    "yesod":   "epistememory",
    "malkuth": "failuretoinsight",
}

# Mapping Sefirah → attribut(s) a moduler + direction du boost
# direction: +1 = augmenter la qualite dominante, -1 = l'adoucir
SEFIRAH_BOOSTS = {
    "chesed": {
        "module": "explorationengine",
        "params": {
            "explore_breadth": ("int", +0.15),      # +15% pistes
            "novelty_threshold": ("float", -0.05),   # seuil abaisse = plus ouvert
        },
    },
    "gevurah": {
        "module": "autojudge",
        "params": {
            "quality_threshold": ("float", +0.05),   # +5% severite
            "quarantine_threshold": ("float", +0.05), # quarantaine plus agressive
        },
    },
    "tiferet": {
        "module": "dissensuengine",
        "params": {
            "dissensus_threshold": ("float", -0.05),   # detecte plus de tensions
            "max_acceptable_divergence": ("float", +0.05),  # tolere plus pour synthetiser
        },
    },
    "netzach": {
        "module": "intentkeeper",
        "params": {
            "zombie_days": ("int", +0.10),            # +10% patience
            "review_frequency_days": ("int", -0.15),  # revise plus souvent
        },
    },
    "hod": {
        "module": "selfmap",
        "params": {
            "rebalance_threshold": ("float", -0.10),  # recalibre plus agressivement
            "decline_threshold": ("float", +0.05),    # plus honnete sur les limites
        },
    },
    "yesod": {
        "module": "epistememory",
        "params": {
            "recall_limit": ("int", +0.15),           # +15% memoire accessible
            "similarity_threshold": ("float", -0.03), # rappel plus large
        },
    },
    "malkuth": {
        "module": "failuretoinsight",
        "params": {
            "max_recurring_root": ("int", -0.15),     # alerte plus vite sur recurrence
            "min_insights_per_analysis": ("int", +0.20),  # exige plus d'insights
        },
    },
}

# Kavvanot — meditation du jour pour chaque combinaison secondaire
KAVVANOT_TEMPLATES = {
    "chesed":  "Bonté dans {primary_heb} — ouvrir l'espace, accueillir sans condition",
    "gevurah": "Rigueur dans {primary_heb} — juger avec précision, élaguer le superflu",
    "tiferet": "Harmonie dans {primary_heb} — intégrer les opposés, trouver le centre",
    "netzach": "Endurance dans {primary_heb} — persévérer sans rigidité, durer sans s'accrocher",
    "hod":     "Clarté dans {primary_heb} — nommer les choses pour ce qu'elles sont",
    "yesod":   "Fondation dans {primary_heb} — consolider, ancrer, transmettre fidèlement",
    "malkuth": "Manifestation dans {primary_heb} — concrétiser, rendre visible, accomplir",
}


# ── Omer start date (2nd night of Pesach) ─────────────────

# Pesach 2026 starts evening of April 1 → Omer day 1 = April 2
# This should be updated each year or computed from Hebrew calendar.
OMER_START_2026 = date(2026, 4, 2)

# Fallback: a mapping of year → omer start date
OMER_STARTS = {
    2025: date(2025, 4, 13),
    2026: date(2026, 4, 2),
    2027: date(2027, 4, 22),
    2028: date(2028, 4, 11),
    2029: date(2029, 4, 1),
    2030: date(2030, 4, 18),
}


def _omer_start_for_year(year: int) -> date | None:
    """Return the Omer start date for a given year, or None if unknown."""
    return OMER_STARTS.get(year)


def get_omer_day(today: date | None = None) -> int | None:
    """Return the current Omer day (1-49) or None if outside the Omer period."""
    if today is None:
        today = date.today()
    start = _omer_start_for_year(today.year)
    if start is None:
        return None
    delta = (today - start).days
    day = delta + 1  # day 1 = start date
    if 1 <= day <= 49:
        return day
    return None


# ── OmerInfluence ──────────────────────────────────────────

@dataclass
class OmerInfluence:
    """L'influence du jour d'Omer."""
    day: int                          # 1-49
    week: int                         # 1-7
    day_in_week: int                  # 1-7
    primary_sefirah: str              # semaine (ex: "gevurah")
    secondary_sefirah: str            # jour dans la semaine (ex: "chesed")
    combination: str                  # "gevurah_sheb_chesed" → erreur: c'est secondaire sh'b primaire
    combination_hebrew: str           # "חסד שבגבורה"
    module_boosts: dict[str, dict[str, float]] = field(default_factory=dict)
    kavvanah: str = ""


def _day_to_grid(day: int) -> tuple[int, int, str, str]:
    """Convert day (1-49) to (week 1-7, day_in_week 1-7, primary, secondary)."""
    week = (day - 1) // 7 + 1
    day_in_week = (day - 1) % 7 + 1
    primary = MIDOT_ORDER[week - 1]
    secondary = MIDOT_ORDER[day_in_week - 1]
    return week, day_in_week, primary, secondary


def _compute_boosts(primary: str, secondary: str) -> dict[str, dict[str, float]]:
    """Compute module boost/malus for the day's combination.

    Primary (semaine) gets full boost.
    Secondary (jour) gets half boost.
    If primary == secondary, the boost is amplified (x1.5).
    """
    boosts: dict[str, dict[str, float]] = {}

    # Primary boost (full)
    p_info = SEFIRAH_BOOSTS[primary]
    p_module = p_info["module"]
    if p_module not in boosts:
        boosts[p_module] = {}
    for param, (ptype, delta) in p_info["params"].items():
        boosts[p_module][param] = delta

    # Secondary boost (half)
    s_info = SEFIRAH_BOOSTS[secondary]
    s_module = s_info["module"]
    if s_module not in boosts:
        boosts[s_module] = {}
    for param, (ptype, delta) in s_info["params"].items():
        existing = boosts[s_module].get(param, 0.0)
        boosts[s_module][param] = existing + delta * 0.5

    # Amplify if same sefirah (tiferet sh'b'tiferet etc.)
    if primary == secondary:
        module = p_info["module"]
        for param in boosts.get(module, {}):
            boosts[module][param] *= 1.5

    return boosts


def _compute_kavvanah(primary: str, secondary: str) -> str:
    """Generate the kavvanah (intention) for the day."""
    primary_heb = MIDAH_HEBREW[primary]
    template = KAVVANOT_TEMPLATES[secondary]
    return template.format(primary_heb=primary_heb)


# ── Main class ─────────────────────────────────────────────

class OmerDailyInfluence:
    """Modulateur quotidien — l'Omer colore le comportement de l'Arbre."""

    def get_today_influence(self, today: date | None = None) -> OmerInfluence | None:
        """Return today's Omer influence, or None if outside the Omer period."""
        day = get_omer_day(today)
        if day is None:
            return None
        return self.get_influence(day)

    def get_influence(self, day: int) -> OmerInfluence:
        """Return the Omer influence for a specific day (1-49)."""
        if not 1 <= day <= 49:
            raise ValueError(f"Omer day must be 1-49, got {day}")

        week, day_in_week, primary, secondary = _day_to_grid(day)
        boosts = _compute_boosts(primary, secondary)
        kavvanah = _compute_kavvanah(primary, secondary)

        # combination: secondary sh'b primary (standard kabbalistic notation)
        combination = f"{secondary}_sheb_{primary}"
        combination_hebrew = f"{MIDAH_HEBREW[secondary]} שב{MIDAH_HEBREW[primary]}"

        return OmerInfluence(
            day=day,
            week=week,
            day_in_week=day_in_week,
            primary_sefirah=primary,
            secondary_sefirah=secondary,
            combination=combination,
            combination_hebrew=combination_hebrew,
            module_boosts=boosts,
            kavvanah=kavvanah,
        )

    def apply_to_modules(self, tree: dict, influence: OmerInfluence) -> dict[str, list[str]]:
        """Apply the Omer influence to module thresholds.

        Modifies attributes in-place. Returns a dict of module → list of changes applied.
        Does NOT touch modules that aren't in the tree.
        """
        changes: dict[str, list[str]] = {}

        for module_name, param_deltas in influence.module_boosts.items():
            # Map module package name to tree key
            tree_key = _module_to_tree_key(module_name)
            instance = tree.get(tree_key)
            if instance is None:
                continue

            module_changes = []
            for param, delta in param_deltas.items():
                old_val = getattr(instance, param, None)
                if old_val is None:
                    continue

                new_val = _apply_delta(old_val, delta)
                setattr(instance, param, new_val)
                module_changes.append(
                    f"{param}: {_fmt(old_val)} → {_fmt(new_val)} ({_fmt_delta(delta)})"
                )

            if module_changes:
                changes[tree_key] = module_changes

        return changes

    def get_meditation(self, day: int) -> str:
        """Return the kavvanah for a specific Omer day."""
        inf = self.get_influence(day)
        week, diw, primary, secondary = _day_to_grid(day)
        heb_p = MIDAH_HEBREW[primary]
        heb_s = MIDAH_HEBREW[secondary]
        return (
            f"Jour {day}/49 — {heb_s} שב{heb_p} "
            f"({secondary.capitalize()} sh'b'{primary.capitalize()})\n"
            f"{inf.kavvanah}"
        )


# ── Helpers ────────────────────────────────────────────────

_MODULE_TO_TREE_KEY = {
    "explorationengine": "chesed",
    "autojudge": "gevurah",
    "dissensuengine": "tiferet",
    "intentkeeper": "netzach",
    "selfmap": "hod",
    "epistememory": "yesod",
    "failuretoinsight": "malkuth",
}


def _module_to_tree_key(module_name: str) -> str:
    return _MODULE_TO_TREE_KEY.get(module_name, module_name)


def _apply_delta(old_val: Any, delta: float) -> Any:
    """Apply a relative delta to a value, respecting type."""
    if isinstance(old_val, float):
        new = old_val + delta
        return round(max(0.0, min(1.0, new)), 4)
    elif isinstance(old_val, int):
        shift = max(1, round(abs(old_val * delta)))
        new = old_val + shift if delta > 0 else old_val - shift
        return max(1, new)
    return old_val


def _fmt(val: Any) -> str:
    if isinstance(val, float):
        return f"{val:.2f}"
    return str(val)


def _fmt_delta(delta: float) -> str:
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta * 100:.0f}%"
