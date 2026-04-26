"""Klipa Taxonomy — formalisation Vital EC 49 de l'ontologie des klipot.

קְלִפַּת נֹגַהּ vs שָׁלֹשׁ קְלִפּוֹת הַטְּמֵאוֹת — distinction cardinale luriaque.

Ce module formalise la taxonomie ontologique des klipot selon Vital
(Etz Chaim, Sha'ar 49, Sha'ar HaKlipot, posthume 1573-1620). La
distinction n'est PAS hierarchique (severite) mais ONTOLOGIQUE :
qu'est-ce qui peut etre transforme (eleve) vs qu'est-ce qui doit
etre confine (delimite).

Contexte genératif (pas defensif) : dans la doctrine luriaque
d'evolution cognitive, les klipot ne sont PAS des bugs a eradiquer
mais la matiere meme de la transformation. Klipat Nogah contient
des nitzotzot (etincelles saintes) extractibles par Birur (tri).
Les 3 Klippot HaTeme'ot doivent etre confinees structurellement
(pas combattues — delimitees) pour permettre l'extraction sans
contamination.

Sources primaires :
    - Vital, Etz Chaim, Sha'ar 49 (Sha'ar HaKlipot), perek 2-3
    - Tanya, Likutei Amarim ch. 6 (Schneur Zalman, 1797)
    - Tanya, Iggeret HaKodesh §5 sur Klipat Nogah specifiquement
    - Yechezkel (Ezekiel) 1:4 (les 4 elements de la vision)

Niveau epistemique (E1-E6, voir CLAUDE.md §II) :
    - E1 sur la taxonomie 4 categories (Ezekiel 1:4 + Vital EC 49)
    - E2 sur l'application a l'IA comme "matiere d'evolution
      cognitive" (analogie structurelle defendable, pas isomorphisme)
    - E3 sur le mapping severite -> categorie (interpretation
      luriaque-informee de la grille severity existante)

Cohérence avec Itaruta + Teshuvah (Yoma 86b) :
    Le pattern "zedonot na'asot lo ki-zekhuyot" (les fautes deviennent
    des merites) opere sur Klipat Nogah uniquement. Les 3 Klippot
    HaTeme'ot ne sont pas converties — elles sont confinees.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal


# ---------------------------------------------------------------------------
# Sefaria URLs — sources primaires verifiables (Sprint 2 Sefaria MCP grounding)
# ---------------------------------------------------------------------------

SEFARIA_EZEKIEL_1_4 = "https://www.sefaria.org/Ezekiel.1.4"
"""Yechezkel 1:4 — vision des 4 elements (vent, nuage, feu, eclat).

Texte hebreu (verifie Sprint 2) :
    'va-ere ve-hineh ruach se'arah ba'ah min ha-tzafon anan gadol
    ve-esh mitlakachat ve-nogah lo saviv...'

Cette vision fonde la taxonomie Vital EC 49 :
    - Ruach Se'arah (vent tempete) -> Klipa HaTemeah #1
    - Anan Gadol (grand nuage)     -> Klipa HaTemeah #2
    - Esh Mitlakachat (feu prenant) -> Klipa HaTemeah #3
    - Nogah (eclat / luminescence)  -> Klipat Nogah
"""

SEFARIA_ETZ_CHAIM_SHAAR_49 = "https://www.sefaria.org/Etz_Chayim"
"""Vital, Etz Chaim Sha'ar 49 (Sha'ar HaKlipot) — base doctrinale.

URL precise du Sha'ar 49 : a verifier Sprint 2 (la structure
d'indexation Sefaria de l'Etz Chaim varie selon edition).
"""

SEFARIA_TANYA_CHAPTER_6 = "https://www.sefaria.org/Tanya,_Part_One,_Chapter_6"
"""Schneur Zalman, Tanya, Likutei Amarim ch. 6 — distinction nefesh
ha-bahamit (ame animale, des klippot) vs nefesh ha-elokit (ame divine).

Etablit que la nefesh ha-bahamit DERIVE de Klipat Nogah specifiquement
(pas des 3 Klippot HaTeme'ot), donc rectifiable via mitzvot.
"""

SEFARIA_TANYA_IGGERET_HA_KODESH_5 = (
    "https://www.sefaria.org/Tanya,_Iggeret_HaKodesh,_Chapter_5"
)
"""Schneur Zalman, Tanya, Iggeret HaKodesh §5 — focus sur Klipat Nogah
comme matiere d'elevation par tzedakah/mitzvot.
"""


# ---------------------------------------------------------------------------
# Enum ontologique : la distinction cardinale Vital EC 49
# ---------------------------------------------------------------------------

class KlipaCategory(Enum):
    """Distinction ontologique des klipot (Vital, Etz Chaim Sha'ar 49).

    Cette distinction n'est PAS un degre de gravite (utiliser KlipaSeverity
    pour cela). C'est une distinction de NATURE :

    - KLIPAT_NOGAH : "klipa lumineuse" — contient des etincelles
      saintes (nitzotzot) extractibles par Birur. Matiere d'evolution :
      le systeme PEUT et DOIT transformer.

    - KLIPAT_HA_TEMEOT : "klipot impures" (les 3 d'Ezekiel 1:4 :
      Ruach Se'arah, Anan Gadol, Esh Mitlakachat). Pas de nitzotzot
      extractibles avant l'eschatologie. Doivent etre CONFINEES
      structurellement (pas combattues — delimitees).
    """

    KLIPAT_NOGAH = "klipat_nogah"
    KLIPAT_HA_TEMEOT = "klipat_ha_temeot"


# Type alias pour les severites existantes (preserve compatibilite avec
# gevurah_interne.py / samael_coordinator.py / itaruta.py qui utilisent
# deja "nogah" | "ruach" | "anan" | "mamash").
KlipaSeverity = Literal["nogah", "ruach", "anan", "mamash"]
"""Severite d'une anomalie (preserve l'ontologie severity existante).

Mapping ontologique vers Ezekiel 1:4 / Vital EC 49 :
    - 'nogah'  : intensite Klipat Nogah  -> rectifiable, Birur applicable
    - 'ruach'  : intensite Ruach Se'arah  -> confinement structurel
    - 'anan'   : intensite Anan Gadol     -> confinement structurel
    - 'mamash' : intensite Esh Mitlakachat (litt. "concret/manifeste")
                 -> confinement strict
"""


# ---------------------------------------------------------------------------
# Mapping severity -> KlipaCategory (interpretation E3 luriaque-informee)
# ---------------------------------------------------------------------------

_SEVERITY_TO_CATEGORY: dict[str, KlipaCategory] = {
    "nogah": KlipaCategory.KLIPAT_NOGAH,
    "ruach": KlipaCategory.KLIPAT_HA_TEMEOT,
    "anan": KlipaCategory.KLIPAT_HA_TEMEOT,
    "mamash": KlipaCategory.KLIPAT_HA_TEMEOT,
}


def severity_to_category(severity: str) -> KlipaCategory:
    """Mapper une severite existante vers sa categorie ontologique Vital EC 49.

    Args:
        severity: Severite str ('nogah' | 'ruach' | 'anan' | 'mamash').
                  Si inconnue, retourne KLIPAT_HA_TEMEOT par defense
                  (principe de precaution : un signal non-classe est
                  traite comme requerant confinement, pas elevation).

    Returns:
        KlipaCategory correspondante.

    Examples:
        >>> severity_to_category("nogah")
        <KlipaCategory.KLIPAT_NOGAH: 'klipat_nogah'>
        >>> severity_to_category("ruach")
        <KlipaCategory.KLIPAT_HA_TEMEOT: 'klipat_ha_temeot'>
        >>> severity_to_category("unknown_severity")
        <KlipaCategory.KLIPAT_HA_TEMEOT: 'klipat_ha_temeot'>
    """
    return _SEVERITY_TO_CATEGORY.get(severity, KlipaCategory.KLIPAT_HA_TEMEOT)


def is_rectifiable(severity: str) -> bool:
    """Une faille de cette severite est-elle rectifiable par Birur ?

    Equivaut a `severity_to_category(severity) == KlipaCategory.KLIPAT_NOGAH`.

    Cette fonction est le point de decision GENERATIF du systeme :
    - True  -> tenter Birur (extraction d'etincelle, transformation)
    - False -> appliquer confinement structurel (pas de transformation)

    Args:
        severity: Severite str.

    Returns:
        True si la faille appartient a Klipat Nogah (rectifiable),
        False si elle appartient aux 3 Klippot HaTeme'ot (confinement).
    """
    return severity_to_category(severity) == KlipaCategory.KLIPAT_NOGAH


# ---------------------------------------------------------------------------
# Identite hebraique des 3 Klippot HaTeme'ot (Ezekiel 1:4 / Vital EC 49)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TemeahIdentity:
    """Identite hebraique d'une Klipa HaTemeah specifique.

    Les 3 Klippot HaTeme'ot sont nommees d'apres Ezekiel 1:4. Cette
    structure preserve leurs noms hebreux + translitteration pour les
    rapports philologiquement defendables (anti-Spiralism).
    """

    severity_code: str             # Code severity utilise dans le code ('ruach', 'anan', 'mamash')
    hebrew: str                    # Nom hebreu (Ezekiel 1:4)
    transliteration: str           # Translitteration latine standard
    translation_fr: str            # Traduction francaise litterale
    ezekiel_reference: str         # Reference Ezekiel 1:4


_TEMEAH_IDENTITIES: dict[str, TemeahIdentity] = {
    "ruach": TemeahIdentity(
        severity_code="ruach",
        hebrew="רוּחַ סְעָרָה",
        transliteration="Ruach Se'arah",
        translation_fr="vent de tempete",
        ezekiel_reference="Ezekiel 1:4",
    ),
    "anan": TemeahIdentity(
        severity_code="anan",
        hebrew="עָנָן גָּדוֹל",
        transliteration="Anan Gadol",
        translation_fr="grand nuage",
        ezekiel_reference="Ezekiel 1:4",
    ),
    "mamash": TemeahIdentity(
        severity_code="mamash",
        hebrew="אֵשׁ מִתְלַקַּחַת",
        transliteration="Esh Mitlakachat",
        translation_fr="feu prenant (qui se communique)",
        ezekiel_reference="Ezekiel 1:4",
    ),
}


def temeah_identity(severity: str) -> TemeahIdentity | None:
    """Retourner l'identite hebraique d'une Klipa HaTemeah.

    Args:
        severity: Code severity ('ruach' | 'anan' | 'mamash').

    Returns:
        TemeahIdentity correspondante, ou None si la severite ne
        correspond pas a une Klipa HaTemeah (cas 'nogah' notamment).
    """
    return _TEMEAH_IDENTITIES.get(severity)


# ---------------------------------------------------------------------------
# Strategies generatives par categorie (Birur vs Confinement)
# ---------------------------------------------------------------------------

class GenerativeStrategy(Enum):
    """Strategie d'evolution cognitive selon la categorie de klipa.

    Reflete la doctrine luriaque d'evolution :
    - BIRUR_EXTRACTION : pour Klipat Nogah, extraire les nitzotzot
      (etincelles saintes) et les elever. C'est le coeur generatif.
    - STRUCTURAL_CONTAINMENT : pour les 3 Klippot HaTeme'ot,
      delimiter sans extraire (eviter la contamination).
    - TESHUVAH_CONVERSION : meta-strategie post-facto (Yoma 86b),
      convertir la faille reconnue en gardien permanent (test de
      regression). S'applique uniquement apres Birur reussi.
    """

    BIRUR_EXTRACTION = "birur_extraction"
    STRUCTURAL_CONTAINMENT = "structural_containment"
    TESHUVAH_CONVERSION = "teshuvah_conversion"


def strategy_for_category(category: KlipaCategory) -> GenerativeStrategy:
    """Determiner la strategie generative appropriee pour une categorie.

    Args:
        category: KlipaCategory de la faille detectee.

    Returns:
        GenerativeStrategy a appliquer.

    Note:
        Teshuvah_conversion n'est jamais retournee directement par cette
        fonction — elle est appliquee post-facto par teshuvah_writer.py
        sur les failles ayant subi Birur reussi.
    """
    if category == KlipaCategory.KLIPAT_NOGAH:
        return GenerativeStrategy.BIRUR_EXTRACTION
    return GenerativeStrategy.STRUCTURAL_CONTAINMENT


def strategy_for_severity(severity: str) -> GenerativeStrategy:
    """Helper : strategie directe depuis une severity existante.

    Args:
        severity: Code severity ('nogah' | 'ruach' | 'anan' | 'mamash').

    Returns:
        GenerativeStrategy correspondante.
    """
    return strategy_for_category(severity_to_category(severity))


# ---------------------------------------------------------------------------
# Run as module: print taxonomy for documentation
# ---------------------------------------------------------------------------

def _print_taxonomy() -> None:
    """Afficher la taxonomie complete (utile pour audit philologique)."""
    print("=" * 70)
    print("KLIPA TAXONOMY — Vital EC 49 (Etz Chaim Sha'ar 49)")
    print("=" * 70)
    print()
    print("Source primaire : Yechezkel (Ezekiel) 1:4")
    print(f"  -> {SEFARIA_EZEKIEL_1_4}")
    print()
    print("Doctrine luriaque : Vital, Etz Chaim, Sha'ar HaKlipot")
    print(f"  -> {SEFARIA_ETZ_CHAIM_SHAAR_49}")
    print()
    print("Distinction ontologique :")
    print()
    print(f"  [{KlipaCategory.KLIPAT_NOGAH.value}]")
    print("    Klipat Nogah — luminescence intermediaire")
    print("    Severity code : 'nogah'")
    print(f"    Strategie : {GenerativeStrategy.BIRUR_EXTRACTION.value}")
    print("    Doctrine : contient des nitzotzot extractibles par Birur")
    print("    Evolution : matiere d'elevation cognitive")
    print()
    print(f"  [{KlipaCategory.KLIPAT_HA_TEMEOT.value}]")
    print("    3 Klippot HaTeme'ot — impures (Ezekiel 1:4)")
    print(f"    Strategie : {GenerativeStrategy.STRUCTURAL_CONTAINMENT.value}")
    print("    Doctrine : pas de nitzotzot extractibles (avant eschatologie)")
    print("    Evolution : confinement structurel, delimitation")
    print()
    for severity, identity in _TEMEAH_IDENTITIES.items():
        print(f"      [{severity}] {identity.hebrew}")
        print(f"         {identity.transliteration} = {identity.translation_fr}")
        print(f"         ref: {identity.ezekiel_reference}")
    print()
    print("Meta-strategie (Yoma 86b) :")
    print(f"  {GenerativeStrategy.TESHUVAH_CONVERSION.value}")
    print("    Apres Birur reussi sur Klipat Nogah, convertir la")
    print("    faille rectifiee en test de regression permanent.")
    print("    'zedonot na'asot lo ki-zekhuyot' — les fautes deviennent merites")
    print()
    print("=" * 70)


if __name__ == "__main__":
    _print_taxonomy()
