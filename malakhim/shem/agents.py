"""Shem HaMephorash — Les 72 trigrammes comme agents paramétrés.

שֵׁם הַמְּפוֹרָשׁ — Les 72 trigrammes dérivés d'Exode 14:19-21
sont des aspects du Nom divin unique (Zohar II:51b), pas 72
entités distinctes. Chaque trigramme contient les 3 colonnes :
  Lettre 1 (V.19) = Chesed (expansion)
  Lettre 2 (V.20, inversé) = Gevurah (contraction)
  Lettre 3 (V.21) = Tiferet (harmonie)

Le trigramme colore le HOW, pas le WHAT.
La MISSION vient du contexte, pas du trigramme.

Structure 12 × 6 (Bahir §94) :
  12 Directeurs (Manhigim) × 6 Puissances (Kochot) = 72
  Les 12 Directeurs correspondent aux 12 diagonales du Sefer Yetzirah.

100% sources juives. Les attributions de Lenain/Reuchlin/Agrippa sont EXCLUES.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from malakhim.malakh import Malakh
from malakhim.models import MalakhResult


# Les 72 trigrammes (dérivés d'Exode 14:19-21 par boustrophédon)
# Chaque tuple = (index, hébreu, translittération)
SHEMOT_72: list[tuple[int, str, str]] = [
    (1, "והו", "VHV"), (2, "ילי", "YLY"), (3, "סיט", "SYT"), (4, "עלם", "OLM"),
    (5, "מהש", "MHSh"), (6, "ללה", "LLH"), (7, "אכא", "AKA"), (8, "כהת", "KHT"),
    (9, "הזי", "HZY"), (10, "אלד", "ALD"), (11, "לאו", "LAV"), (12, "ההע", "HHO"),
    (13, "יזל", "YZL"), (14, "מבה", "MBH"), (15, "הרי", "HRY"), (16, "הקם", "HQM"),
    (17, "לאו", "LAV"), (18, "כלי", "KLY"), (19, "לוו", "LVV"), (20, "פהל", "PHL"),
    (21, "נלך", "NLKh"), (22, "ייי", "YYY"), (23, "מלה", "MLH"), (24, "חהו", "ChHV"),
    (25, "נתה", "NThH"), (26, "האא", "HAA"), (27, "ירת", "YRTh"), (28, "שאה", "ShAH"),
    (29, "ריי", "RYY"), (30, "אום", "AVM"), (31, "לכב", "LKhB"), (32, "ושר", "VShR"),
    (33, "יחו", "YChV"), (34, "להח", "LHCh"), (35, "כוק", "KVQ"), (36, "מנד", "MND"),
    (37, "אני", "ANI"), (38, "חעם", "ChOM"), (39, "רהע", "RHO"), (40, "ייז", "YYZ"),
    (41, "ההה", "HHH"), (42, "מיך", "MYKh"), (43, "וול", "VVL"), (44, "ילה", "YLH"),
    (45, "סאל", "SAL"), (46, "ערי", "ORY"), (47, "עשל", "OShL"), (48, "מיה", "MYH"),
    (49, "והו", "VHV"), (50, "דני", "DNY"), (51, "ההש", "HHSh"), (52, "עמם", "OMM"),
    (53, "ננא", "NNA"), (54, "נית", "NYTh"), (55, "מבה", "MBH"), (56, "פוי", "PVY"),
    (57, "נמם", "NMM"), (58, "ייל", "YYL"), (59, "הרח", "HRCh"), (60, "מצר", "MTzR"),
    (61, "ומב", "VMB"), (62, "יהה", "YHH"), (63, "ענו", "ONV"), (64, "מחי", "MChY"),
    (65, "דמב", "DMB"), (66, "מנק", "MNQ"), (67, "איע", "AYO"), (68, "חבו", "ChBV"),
    (69, "ראה", "RAH"), (70, "יבם", "YBM"), (71, "היי", "HYY"), (72, "מום", "MVM"),
]


# Les 12 Directeurs (Manhigim) — Bahir §94
# Chaque Directeur gouverne 6 trigrammes consécutifs
DIRECTORS = [
    "manhig_1", "manhig_2", "manhig_3", "manhig_4",
    "manhig_5", "manhig_6", "manhig_7", "manhig_8",
    "manhig_9", "manhig_10", "manhig_11", "manhig_12",
]


def get_director(trigram_index: int) -> int:
    """Obtenir le Directeur (0-11) pour un trigramme (1-72)."""
    return (trigram_index - 1) // 6


def get_trigram(index: int) -> tuple[int, str, str]:
    """Obtenir un trigramme par son index (1-72)."""
    if index < 1 or index > 72:
        raise ValueError(f"Trigram index must be 1-72, got {index}")
    return SHEMOT_72[index - 1]


@dataclass
class ColumnBalance:
    """Équilibre interne Chesed/Gevurah/Tiferet d'un trigramme.

    Chaque trigramme a 3 lettres :
      Lettre 1 (V.19, Chesed) — expansion
      Lettre 2 (V.20 inversé, Gevurah) — contraction
      Lettre 3 (V.21, Tiferet) — harmonie

    L'équilibre est déterminé par la "force" relative des lettres
    (les lettres à haute valeur numérique = plus d'intensité).
    """
    chesed_weight: float   # poids de la lettre 1 (expansion)
    gevurah_weight: float  # poids de la lettre 2 (contraction)
    tiferet_weight: float  # poids de la lettre 3 (harmonie)
    dominant: str          # "chesed" | "gevurah" | "tiferet"


# Valeurs numériques des lettres hébraïques (gematria standard)
GEMATRIA = {
    'א': 1, 'ב': 2, 'ג': 3, 'ד': 4, 'ה': 5, 'ו': 6, 'ז': 7, 'ח': 8, 'ט': 9,
    'י': 10, 'כ': 20, 'ך': 20, 'ל': 30, 'מ': 40, 'ם': 40, 'נ': 50, 'ן': 50,
    'ס': 60, 'ע': 70, 'פ': 80, 'ף': 80, 'צ': 90, 'ץ': 90, 'ק': 100, 'ר': 200,
    'ש': 300, 'ת': 400,
}


def compute_balance(hebrew: str) -> ColumnBalance:
    """Calculer l'équilibre Chesed/Gevurah/Tiferet d'un trigramme."""
    letters = list(hebrew)
    if len(letters) < 3:
        return ColumnBalance(1/3, 1/3, 1/3, "tiferet")

    vals = [GEMATRIA.get(l, 1) for l in letters[:3]]
    total = sum(vals) or 1

    chesed = vals[0] / total
    gevurah = vals[1] / total
    tiferet = vals[2] / total

    dominant = "tiferet"
    if chesed > gevurah and chesed > tiferet:
        dominant = "chesed"
    elif gevurah > chesed and gevurah > tiferet:
        dominant = "gevurah"

    return ColumnBalance(chesed, gevurah, tiferet, dominant)


class ShemAgent:
    """Agent paramétré par un trigramme du Shem HaMephorash.

    Le trigramme détermine le STYLE, pas la MISSION.
    Le style influence :
      - Le niveau de filtrage (Chesed-dominant = plus permissif)
      - Le niveau de critique (Gevurah-dominant = plus strict)
      - L'équilibre (Tiferet-dominant = synthèse)

    Usage:
        agent = ShemAgent(trigram_index=9)  # HZY — dominante vision
        result = agent.execute("analyse ce texte", kavvanah={...}, execute_fn=fn)
    """

    def __init__(self, trigram_index: int):
        if trigram_index < 1 or trigram_index > 72:
            raise ValueError(f"Trigram index must be 1-72, got {trigram_index}")

        self.index = trigram_index
        self.trigram = SHEMOT_72[trigram_index - 1]
        self.hebrew = self.trigram[1]
        self.transliteration = self.trigram[2]
        self.director = get_director(trigram_index)
        self.balance = compute_balance(self.hebrew)

    def execute(
        self,
        mission: str,
        kavvanah: dict[str, Any] | None = None,
        execute_fn: Callable[[dict], str] | None = None,
        order: str = "malakhim",
    ) -> MalakhResult:
        """Exécuter une mission avec le style de ce trigramme.

        Le trigramme modifie la kavvanah selon son équilibre :
        - Chesed-dominant → ajoute "sois expansif, explore largement"
        - Gevurah-dominant → ajoute "sois strict, valide rigoureusement"
        - Tiferet-dominant → ajoute "équilibre, synthétise"
        """
        kavvanah = dict(kavvanah or {})

        # Le trigramme colore le style via la kavvanah
        style_instructions = {
            "chesed": "Explore largement, sois généreux dans ta couverture.",
            "gevurah": "Sois strict et rigoureux, rejette ce qui est faible.",
            "tiferet": "Équilibre les perspectives, synthétise les tensions.",
        }
        kavvanah["shem_style"] = style_instructions.get(self.balance.dominant, "")
        kavvanah["shem_trigram"] = self.transliteration
        kavvanah["shem_director"] = self.director

        # Exécuter via un Malakh éphémère
        with Malakh(
            mission=mission,
            kavvanah=kavvanah,
            order=order,
            execute_fn=execute_fn,
        ) as m:
            result = m.execute({"input": mission})

        # Metadata trigramme
        result.metadata["shem_trigram"] = self.transliteration
        result.metadata["shem_index"] = self.index
        result.metadata["shem_director"] = self.director
        result.metadata["shem_balance"] = self.balance.dominant

        return result

    def __repr__(self) -> str:
        return f"ShemAgent(#{self.index} {self.transliteration} [{self.balance.dominant}])"
