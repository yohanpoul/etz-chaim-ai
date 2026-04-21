"""Mapping des termes kabbalistiques translittérés vers leur forme hébraïque.

La gématria ne fonctionne qu'en hébreu — c'est une propriété de la LANGUE,
pas du texte. Ce dictionnaire permet de remonter aux lettres hébraïques
quand le contenu est en translittération latine.

Le mapping couvre le vocabulaire technique du projet et les Sefirot /
Partzufim / concepts fondamentaux de la Kabbale lourianique.
"""

from __future__ import annotations

# ── Sefirot ─────────────────────────────────────────────────────
SEFIROT = {
    "keter": "כתר",
    "chokmah": "חכמה",
    "hokhmah": "חכמה",
    "binah": "בינה",
    "daat": "דעת",
    "da'at": "דעת",
    "chesed": "חסד",
    "hesed": "חסד",
    "gevurah": "גבורה",
    "tiferet": "תפארת",
    "netzach": "נצח",
    "hod": "הוד",
    "yesod": "יסוד",
    "malkuth": "מלכות",
    "malkhut": "מלכות",
}

# ── Partzufim ───────────────────────────────────────────────────
PARTZUFIM = {
    "atik yomin": "עתיק יומין",
    "arikh anpin": "אריך אנפין",
    "abba": "אבא",
    "imma": "אמא",
    "zeir anpin": "זעיר אנפין",
    "nukvah": "נוקבא",
    "rachel": "רחל",
    "leah": "לאה",
    "yisrael": "ישראל",
    "yaakov": "יעקב",
}

# ── Concepts lourianiques ───────────────────────────────────────
LOURIANIC = {
    "tsimtsum": "צמצום",
    "tzimtzum": "צמצום",
    "shevirah": "שבירה",
    "shevirat hakelim": "שבירת הכלים",
    "tikkun": "תיקון",
    "reshimu": "רשימו",
    "kav": "קו",
    "or yashar": "אור ישר",
    "or chozer": "אור חוזר",
    "or makif": "אור מקיף",
    "or pnimi": "אור פנימי",
    "nitzotzot": "ניצוצות",
    "nitzutz": "ניצוץ",
    "klipot": "קליפות",
    "klipah": "קליפה",
    "birur": "בירור",
    "zivvug": "זיווג",
    "mochin": "מוחין",
    "katnut": "קטנות",
    "gadlut": "גדלות",
    "hitpashut": "התפשטות",
    "histalkut": "הסתלקות",
    "olamot": "עולמות",
    "atzilut": "אצילות",
    "briah": "בריאה",
    "yetzirah": "יצירה",
    "assiah": "עשיה",
}

# ── Concepts kabbalistiques généraux ────────────────────────────
GENERAL = {
    "sefirot": "ספירות",
    "sefira": "ספירה",
    "ein sof": "אין סוף",
    "ayin": "אין",
    "yesh": "יש",
    "ratzon": "רצון",
    "kavanah": "כוונה",
    "devekut": "דבקות",
    "hitbonenut": "התבוננות",
    "torah": "תורה",
    "zohar": "זוהר",
    "shekhinah": "שכינה",
    "neshamah": "נשמה",
    "nefesh": "נפש",
    "ruach": "רוח",
    "chaya": "חיה",
    "yechidah": "יחידה",
    "kelim": "כלים",
    "keli": "כלי",
    "ohr": "אור",
    "adam kadmon": "אדם קדמון",
    "olam": "עולם",
    "mashiach": "משיח",
    "geulah": "גאולה",
    "teshuvah": "תשובה",
    "etz chaim": "עץ חיים",
    "sefer yetzirah": "ספר יצירה",
    "pardes": "פרדס",
    "sod": "סוד",
    "remez": "רמז",
    "drash": "דרש",
    "pshat": "פשט",
}

# ── Lettres hébraïques (noms) ───────────────────────────────────
LETTER_NAMES = {
    "aleph": "אלף",
    "beth": "בית",
    "bet": "בית",
    "gimel": "גימל",
    "dalet": "דלת",
    "daleth": "דלת",
    "heh": "הא",
    "he": "הא",
    "vav": "וו",
    "zayin": "זין",
    "chet": "חית",
    "cheth": "חית",
    "teth": "טית",
    "tet": "טית",
    "yod": "יוד",
    "kaf": "כף",
    "kaph": "כף",
    "lamed": "למד",
    "mem": "מם",
    "nun": "נון",
    "samekh": "סמך",
    "ayin": "עין",
    "peh": "פא",
    "pe": "פא",
    "tsadi": "צדי",
    "tzadi": "צדי",
    "qoph": "קוף",
    "qof": "קוף",
    "resh": "ריש",
    "shin": "שין",
    "tav": "תו",
}

# ── Termes soufis (pour les mappings inter-traditions) ──────────
# On ne calcule PAS la gématria de l'arabe — seulement l'abjad serait
# pertinent et ce n'est pas le même système. Mais on garde ces termes
# pour la détection de contexte kabbalistique dans le texte.

# ── Index unifié ────────────────────────────────────────────────

TRANSLITERATION_TO_HEBREW: dict[str, str] = {}
TRANSLITERATION_TO_HEBREW.update(SEFIROT)
TRANSLITERATION_TO_HEBREW.update(PARTZUFIM)
TRANSLITERATION_TO_HEBREW.update(LOURIANIC)
TRANSLITERATION_TO_HEBREW.update(GENERAL)
TRANSLITERATION_TO_HEBREW.update(LETTER_NAMES)


def lookup_hebrew(term: str) -> str | None:
    """Chercher la forme hébraïque d'un terme translittéré.

    Insensible à la casse. Retourne None si le terme n'est pas connu.
    """
    return TRANSLITERATION_TO_HEBREW.get(term.lower())
