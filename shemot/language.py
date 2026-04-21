"""shemot/language.py — Skills 23-32 : analyse linguistique.

Détection de langue, translittération, gématria, notarikon, temura.
Le coeur kabbalistique du module.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from .base import Shem, ShemResult

# ── Tables de référence ──────────────────────────────────────

HEBREW_GEMATRIA = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
    "י": 10, "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80,
    "צ": 90, "ק": 100, "ר": 200, "ש": 300, "ת": 400,
    # Finales
    "ך": 500, "ם": 600, "ן": 700, "ף": 800, "ץ": 900,
}

HEBREW_ORDINAL = {c: i + 1 for i, c in enumerate("אבגדהוזחטיכלמנסעפצקרשת")}

HEBREW_LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"

ATBASH_MAP = {a: b for a, b in zip(HEBREW_LETTERS, reversed(HEBREW_LETTERS))}

HEBREW_TO_LATIN = {
    "א": "'", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "v", "ז": "z",
    "ח": "ch", "ט": "t", "י": "y", "כ": "k", "ך": "k", "ל": "l",
    "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s", "ע": "'",
    "פ": "p", "ף": "f", "צ": "tz", "ץ": "tz", "ק": "q", "ר": "r",
    "ש": "sh", "ת": "t",
}

ARABIC_TO_LATIN = {
    "ا": "a", "ب": "b", "ت": "t", "ث": "th", "ج": "j", "ح": "h", "خ": "kh",
    "د": "d", "ذ": "dh", "ر": "r", "ز": "z", "س": "s", "ش": "sh", "ص": "s",
    "ض": "d", "ط": "t", "ظ": "z", "ع": "'", "غ": "gh", "ف": "f", "ق": "q",
    "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "w", "ي": "y",
}

# Ranges Unicode pour la détection de script
SCRIPT_RANGES = [
    ("hebrew", 0x0590, 0x05FF),
    ("arabic", 0x0600, 0x06FF),
    ("greek", 0x0370, 0x03FF),
    ("devanagari", 0x0900, 0x097F),
    ("cyrillic", 0x0400, 0x04FF),
    ("cjk", 0x4E00, 0x9FFF),
    ("latin", 0x0041, 0x024F),
]


class DetectLanguage(Shem):
    """#23 MLH — Douceur : détecter la langue d'un texte."""
    name = "Detect Language"
    skill_id = "detect_language"
    trigram = "מלה"
    trigram_name = "MLH"
    number = 23
    category = "language"
    quality = "Douceur"
    description = "Détecter la langue d'un texte par heuristiques"

    MARKERS = {
        "fr": ["le", "la", "les", "de", "des", "du", "un", "une", "est", "et", "en", "que", "qui"],
        "en": ["the", "is", "of", "and", "to", "in", "that", "it", "for", "was", "with"],
        "de": ["der", "die", "das", "und", "ist", "ein", "eine", "von", "den", "auf"],
        "ar": ["في", "من", "على", "إلى", "هذا", "التي", "الذي", "كان", "عن"],
        "he": ["את", "של", "על", "הוא", "היה", "אל", "זה", "כי", "לא", "גם"],
    }

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        words = text.lower().split()
        scores = {}
        for lang, markers in self.MARKERS.items():
            scores[lang] = sum(1 for w in words if w in markers) / max(len(words), 1)
        best = max(scores, key=scores.get) if scores else "unknown"
        return self._ok(
            {"detected": best, "scores": scores, "sample_length": len(text)},
            f"Langue détectée: {best} ({scores.get(best, 0):.2%})",
        )


class TransliterateHebrew(Shem):
    """#24 ChHV — Lien : translittérer hébreu ↔ latin."""
    name = "Transliterate Hebrew"
    skill_id = "transliterate_hebrew"
    trigram = "חהו"
    trigram_name = "ChHV"
    number = 24
    category = "language"
    quality = "Lien"
    description = "Translittérer un texte hébreu en caractères latins"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        result = []
        for ch in text:
            if ch in HEBREW_TO_LATIN:
                result.append(HEBREW_TO_LATIN[ch])
            elif unicodedata.category(ch).startswith("M"):
                continue  # Ignorer les diacritiques/voyelles
            else:
                result.append(ch)
        transliterated = "".join(result)
        return self._ok(
            {"original": text, "transliterated": transliterated},
            f"Translittéré: {transliterated}",
        )


class TransliterateArabic(Shem):
    """#25 NThH — Extension : translittérer arabe ↔ latin."""
    name = "Transliterate Arabic"
    skill_id = "transliterate_arabic"
    trigram = "נתה"
    trigram_name = "NThH"
    number = 25
    category = "language"
    quality = "Extension"
    description = "Translittérer un texte arabe en caractères latins"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        result = []
        for ch in text:
            if ch in ARABIC_TO_LATIN:
                result.append(ARABIC_TO_LATIN[ch])
            elif unicodedata.category(ch).startswith("M"):
                continue
            else:
                result.append(ch)
        transliterated = "".join(result)
        return self._ok(
            {"original": text, "transliterated": transliterated},
            f"Translittéré: {transliterated}",
        )


class GematriaCalc(Shem):
    """#26 HAA — Fenêtre : calculer la gématria."""
    name = "Gematria Calculator"
    skill_id = "gematria_calc"
    trigram = "האא"
    trigram_name = "HAA"
    number = 26
    category = "language"
    quality = "Fenêtre"
    description = "Calculer la gématria (standard, ordinal, atbash, katan, kolel)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte hébreu")
        method = kwargs.get("method", "all")
        hebrew_chars = [ch for ch in text if ch in HEBREW_GEMATRIA or ch in HEBREW_ORDINAL]
        if not hebrew_chars:
            return self._fail("Aucun caractère hébreu trouvé")

        results = {}
        # Standard (Mispar Gadol)
        results["standard"] = sum(HEBREW_GEMATRIA.get(ch, 0) for ch in hebrew_chars)
        # Ordinal (Mispar Siduri)
        results["ordinal"] = sum(HEBREW_ORDINAL.get(ch, 0) for ch in hebrew_chars)
        # Katan (réduction : chaque lettre mod 9)
        results["katan"] = sum(HEBREW_GEMATRIA.get(ch, 0) % 10 or (10 if HEBREW_GEMATRIA.get(ch, 0) % 10 == 0 else 0) for ch in hebrew_chars)
        # Kolel (+1 pour le mot)
        results["kolel"] = results["standard"] + 1
        # Atbash
        atbash_text = "".join(ATBASH_MAP.get(ch, ch) for ch in hebrew_chars)
        results["atbash_text"] = atbash_text
        results["atbash_value"] = sum(HEBREW_GEMATRIA.get(ch, 0) for ch in atbash_text)

        if method != "all":
            val = results.get(method)
            if val is not None:
                results = {method: val}

        return self._ok(
            {"input": text, "hebrew_chars": "".join(hebrew_chars), **results},
            f"Gématria standard: {results.get('standard', '?')}",
        )


class Notarikon(Shem):
    """#27 YRTh — Héritage : appliquer le notarikon."""
    name = "Notarikon"
    skill_id = "notarikon"
    trigram = "ירת"
    trigram_name = "YRTh"
    number = 27
    category = "language"
    quality = "Héritage"
    description = "Extraire l'acronyme kabbalistique (premières ou dernières lettres)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        mode = kwargs.get("mode", "first")  # "first" ou "last"
        words = text.split()
        hebrew_words = []
        for w in words:
            chars = [ch for ch in w if ch in HEBREW_GEMATRIA or ch in HEBREW_ORDINAL]
            if chars:
                hebrew_words.append(chars)
        if not hebrew_words:
            return self._fail("Aucun mot hébreu trouvé")

        if mode == "first":
            acronym = "".join(w[0] for w in hebrew_words)
        else:
            acronym = "".join(w[-1] for w in hebrew_words)

        gematria_val = sum(HEBREW_GEMATRIA.get(ch, 0) for ch in acronym)
        return self._ok(
            {"input": text, "mode": mode, "acronym": acronym, "gematria": gematria_val},
            f"Notarikon ({mode}): {acronym} = {gematria_val}",
        )


class Temura(Shem):
    """#28 ShAH — Retour : appliquer la temura (permutations)."""
    name = "Temura"
    skill_id = "temura"
    trigram = "שאה"
    trigram_name = "ShAH"
    number = 28
    category = "language"
    quality = "Retour"
    description = "Appliquer une permutation de lettres (Atbash, Albam, Avgad)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte hébreu")
        method = kwargs.get("method", "atbash")

        hebrew_chars = [ch for ch in text if ch in HEBREW_ORDINAL]
        if not hebrew_chars:
            return self._fail("Aucun caractère hébreu trouvé")

        from tzeruf.engine import apply_temura
        try:
            transformed = apply_temura(text, method)
        except ValueError as e:
            return self._fail(str(e))

        return self._ok(
            {"input": text, "method": method, "output": transformed,
             "gematria_input": sum(HEBREW_GEMATRIA.get(ch, 0) for ch in text),
             "gematria_output": sum(HEBREW_GEMATRIA.get(ch, 0) for ch in transformed)},
            f"Temura ({method}): {text} → {transformed}",
        )


class DetectScript(Shem):
    """#29 RYY — Berger : détecter le système d'écriture."""
    name = "Detect Script"
    skill_id = "detect_script"
    trigram = "ריי"
    trigram_name = "RYY"
    number = 29
    category = "language"
    quality = "Berger"
    description = "Détecter les systèmes d'écriture présents dans un texte"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        counts = {}
        for ch in text:
            cp = ord(ch)
            for script, lo, hi in SCRIPT_RANGES:
                if lo <= cp <= hi:
                    counts[script] = counts.get(script, 0) + 1
                    break
        total = sum(counts.values()) or 1
        scripts = {s: {"count": c, "ratio": round(c / total, 3)} for s, c in sorted(counts.items(), key=lambda x: -x[1])}
        primary = max(counts, key=counts.get) if counts else "unknown"
        return self._ok(
            {"scripts": scripts, "primary": primary},
            f"Script principal: {primary}",
        )


class WordFrequency(Shem):
    """#30 AVM — Patience : fréquence des mots."""
    name = "Word Frequency"
    skill_id = "word_frequency"
    trigram = "אום"
    trigram_name = "AVM"
    number = 30
    category = "language"
    quality = "Patience"
    description = "Calculer la fréquence des mots ou racines dans un texte"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        top_n = kwargs.get("top_n", 20)
        min_length = kwargs.get("min_length", 2)
        words = re.findall(r"\b\w+\b", text.lower())
        words = [w for w in words if len(w) >= min_length]
        freq = Counter(words).most_common(top_n)
        return self._ok(
            {"frequencies": freq, "total_words": len(words), "unique": len(set(words))},
            f"{len(set(words))} mots uniques sur {len(words)} total",
        )


class ExtractRoots(Shem):
    """#31 LKB — Cœur : extraire les racines trilitères."""
    name = "Extract Roots"
    skill_id = "extract_roots"
    trigram = "לכב"
    trigram_name = "LKB"
    number = 31
    category = "language"
    quality = "Cœur"
    description = "Extraire les racines trilitères hébraïques/arabes d'un texte"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        # Extraire les mots hébreux et identifier les consonnes
        words = text.split()
        roots = []
        for word in words:
            consonants = [ch for ch in word if ch in HEBREW_ORDINAL]
            if len(consonants) >= 3:
                # Heuristique simple : prendre les 3 premières consonnes
                root = "".join(consonants[:3])
                roots.append({"word": word, "root": root})
        root_counter = Counter(r["root"] for r in roots)
        return self._ok(
            {"roots": roots[:30], "unique_roots": dict(root_counter.most_common(20)),
             "n_words_analyzed": len(roots)},
            f"{len(root_counter)} racine(s) unique(s) trouvée(s)",
        )


class CompareTranslations(Shem):
    """#32 VShR — Rectitude : comparer des traductions."""
    name = "Compare Translations"
    skill_id = "compare_translations"
    trigram = "ושר"
    trigram_name = "VShR"
    number = 32
    category = "language"
    quality = "Rectitude"
    description = "Comparer plusieurs traductions d'un même passage"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        translations = kwargs.get("translations", [])
        if text:
            translations = [text] + translations
        if len(translations) < 2:
            return self._fail("Au moins 2 traductions requises")
        combined = "\n".join(f"TRADUCTION {i+1}: {t}" for i, t in enumerate(translations))
        prompt = (
            f"Compare ces {len(translations)} traductions du même passage. "
            f"Identifie les divergences significatives et ce qu'elles révèlent "
            f"sur les choix herméneutiques de chaque traducteur:\n\n{combined[:3000]}"
        )
        try:
            analysis = self._llm(prompt)
            return self._ok({"analysis": analysis, "n_translations": len(translations)}, "Traductions comparées")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")
