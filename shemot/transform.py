"""shemot/transform.py — Skills 59-66 : transformations de données.

Unicode, unités, formats, diff, déduplication.
"""

from __future__ import annotations

import re
import unicodedata

from .base import Shem, ShemResult


class NormalizeUnicode(Shem):
    """#59 HRCh — Chemin : normaliser l'unicode."""
    name = "Normalize Unicode"
    skill_id = "normalize_unicode"
    trigram = "הרח"
    trigram_name = "HRCh"
    number = 59
    category = "transform"
    quality = "Chemin"
    description = "Normaliser l'unicode (NFC/NFD, voyelles hébraïques, diacritiques)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        form = kwargs.get("form", "NFC")
        strip_vowels = kwargs.get("strip_vowels", False)

        result = unicodedata.normalize(form, text)
        n_changed = sum(1 for a, b in zip(text, result) if a != b) if len(text) == len(result) else abs(len(text) - len(result))

        if strip_vowels:
            # Supprimer les nikudot hébreux (U+05B0-U+05BD, U+05BF, U+05C1-U+05C2, U+05C4-U+05C5, U+05C7)
            result = re.sub(r"[\u05B0-\u05BD\u05BF\u05C1\u05C2\u05C4\u05C5\u05C7]", "", result)
            # Supprimer les diacritiques arabes (tashkil)
            result = re.sub(r"[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E4\u06E7-\u06E8\u06EA-\u06ED]", "", result)

        return self._ok(
            {"normalized": result, "form": form, "strip_vowels": strip_vowels,
             "original_length": len(text), "result_length": len(result)},
            f"Normalisé ({form}): {len(text)} → {len(result)} chars",
        )


class ConvertUnits(Shem):
    """#60 MTzR — Détresse : convertir des unités anciennes."""
    name = "Convert Units"
    skill_id = "convert_units"
    trigram = "מצר"
    trigram_name = "MTzR"
    number = 60
    category = "transform"
    quality = "Détresse"
    description = "Convertir des unités anciennes vers le métrique"

    UNITS = {
        # Longueur
        "coudée": ("m", 0.4445), "amah": ("m", 0.4445),
        "palme": ("cm", 7.4), "tefach": ("cm", 7.4),
        "doigt": ("cm", 1.85), "etzba": ("cm", 1.85),
        "parasange": ("km", 5.94), "farsakh": ("km", 5.94),
        "mil": ("km", 0.96), "ris": ("m", 128.0),
        "stade": ("m", 185.0),
        # Volume
        "log": ("ml", 345.0), "hin": ("l", 6.07),
        "bath": ("l", 36.44), "ephah": ("l", 36.44),
        "homer": ("l", 364.4), "kor": ("l", 364.4),
        "seah": ("l", 12.15),
        # Poids
        "shekel": ("g", 11.4), "mina": ("g", 570.0),
        "talent": ("kg", 34.2), "kikar": ("kg", 34.2),
        "gerah": ("g", 0.57),
    }

    def run(self, text: str = "", **kwargs) -> ShemResult:
        unit = kwargs.get("unit", "").lower()
        value = kwargs.get("value", 1.0)
        if not unit and text:
            # Essayer de parser "5 coudées"
            match = re.match(r"([\d.]+)\s+(\w+)", text)
            if match:
                value = float(match.group(1))
                unit = match.group(2).lower()
        if unit not in self.UNITS:
            return self._ok(
                {"available_units": list(self.UNITS.keys())},
                f"Unité '{unit}' inconnue — voir available_units",
            )
        target_unit, factor = self.UNITS[unit]
        result = value * factor
        return self._ok(
            {"input": value, "input_unit": unit, "result": round(result, 4),
             "result_unit": target_unit, "factor": factor},
            f"{value} {unit} = {result:.4f} {target_unit}",
        )


class JsonToMarkdown(Shem):
    """#61 VMB — Puissance : convertir JSON en markdown."""
    name = "JSON to Markdown"
    skill_id = "json_to_markdown"
    trigram = "ומב"
    trigram_name = "VMB"
    number = 61
    category = "transform"
    quality = "Puissance"
    description = "Convertir un JSON structuré en markdown lisible"

    def _to_md(self, obj, level=0) -> str:
        indent = "  " * level
        lines = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    lines.append(f"{indent}- **{k}**:")
                    lines.append(self._to_md(v, level + 1))
                else:
                    lines.append(f"{indent}- **{k}**: {v}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    lines.append(f"{indent}{i+1}.")
                    lines.append(self._to_md(item, level + 1))
                else:
                    lines.append(f"{indent}{i+1}. {item}")
        else:
            lines.append(f"{indent}{obj}")
        return "\n".join(lines)

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de JSON")
        import json as json_mod
        try:
            data = json_mod.loads(text)
        except json_mod.JSONDecodeError as e:
            return self._fail(f"JSON invalide: {e}")
        md = self._to_md(data)
        return self._ok({"markdown": md}, f"Converti en markdown ({len(md)} chars)")


class MarkdownToStructured(Shem):
    """#62 YHH — Connaissance : parser du markdown en structure."""
    name = "Markdown to Structured"
    skill_id = "markdown_to_structured"
    trigram = "יהה"
    trigram_name = "YHH"
    number = 62
    category = "transform"
    quality = "Connaissance"
    description = "Parser du markdown en structure JSON (headings, listes, tables)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de markdown")
        sections = []
        current = {"heading": "", "level": 0, "content": []}
        for line in text.split("\n"):
            heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
            if heading_match:
                if current["content"] or current["heading"]:
                    sections.append(current)
                current = {
                    "heading": heading_match.group(2),
                    "level": len(heading_match.group(1)),
                    "content": [],
                }
            elif line.strip():
                current["content"].append(line.strip())
        if current["content"] or current["heading"]:
            sections.append(current)
        return self._ok(
            {"sections": sections, "n_sections": len(sections)},
            f"{len(sections)} section(s) parsée(s)",
        )


class DiffTexts(Shem):
    """#63 ONV — Affliction : calculer le diff entre deux textes."""
    name = "Diff Texts"
    skill_id = "diff_texts"
    trigram = "ענו"
    trigram_name = "ONV"
    number = 63
    category = "transform"
    quality = "Affliction"
    description = "Calculer le diff entre deux versions d'un texte"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        text_b = kwargs.get("text_b", "")
        if not text or not text_b:
            return self._fail("Deux textes requis (text + text_b)")
        import difflib
        lines_a = text.splitlines(keepends=True)
        lines_b = text_b.splitlines(keepends=True)
        diff = list(difflib.unified_diff(lines_a, lines_b, fromfile="a", tofile="b", lineterm=""))
        added = sum(1 for d in diff if d.startswith("+") and not d.startswith("+++"))
        removed = sum(1 for d in diff if d.startswith("-") and not d.startswith("---"))
        return self._ok(
            {"diff": "\n".join(diff[:100]), "added": added, "removed": removed,
             "total_changes": added + removed},
            f"+{added} -{removed} lignes modifiées",
        )


class SemanticDedup(Shem):
    """#64 MChY — Vivification : déduplication sémantique."""
    name = "Semantic Dedup"
    skill_id = "semantic_dedup"
    trigram = "מחי"
    trigram_name = "MChY"
    number = 64
    category = "transform"
    quality = "Vivification"
    description = "Déduplication sémantique (pas juste exacte)"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        items = kwargs.get("items", [])
        if not items and text:
            items = [l.strip() for l in text.split("\n") if l.strip()]
        if len(items) < 2:
            return self._fail("Au moins 2 items requis")
        # Dédup exacte d'abord
        seen_exact = set()
        unique = []
        for item in items:
            normalized = " ".join(item.lower().split())
            if normalized not in seen_exact:
                seen_exact.add(normalized)
                unique.append(item)
        exact_removed = len(items) - len(unique)
        # Si reste trop d'items, utiliser LLM pour dédup sémantique
        if len(unique) > 5:
            combined = "\n".join(f"{i+1}. {u}" for i, u in enumerate(unique[:30]))
            prompt = (
                f"Ces items contiennent des doublons sémantiques (même sens, mots différents). "
                f"Liste les numéros des items qui sont des doublons sémantiques:\n\n{combined}"
            )
            try:
                analysis = self._llm(prompt)
                return self._ok(
                    {"unique": unique, "exact_removed": exact_removed, "semantic_analysis": analysis},
                    f"{exact_removed} doublons exacts supprimés, analyse sémantique faite",
                )
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        return self._ok(
            {"unique": unique, "exact_removed": exact_removed},
            f"{exact_removed} doublons exacts supprimés, {len(unique)} items uniques",
        )


class ExpandAbbreviation(Shem):
    """#65 DMB — Silence fécond : développer les abréviations."""
    name = "Expand Abbreviation"
    skill_id = "expand_abbreviation"
    trigram = "דמב"
    trigram_name = "DMB"
    number = 65
    category = "transform"
    quality = "Silence fécond"
    description = "Développer les abréviations courantes (religieuses, académiques)"

    ABBREVS = {
        # Hébraïque
        "ז\"ל": "זיכרונו לברכה (de mémoire bénie)",
        "ע\"ה": "עליו השלום (que la paix soit sur lui)",
        "ב\"ה": "ברוך ה' (béni soit Dieu)",
        "בס\"ד": "בסייעתא דשמיא (avec l'aide du Ciel)",
        "ר'": "רבי (Rabbi)",
        # Académique
        "cf.": "confer (comparer)",
        "ibid.": "ibidem (au même endroit)",
        "op. cit.": "opere citato (dans l'ouvrage cité)",
        "loc. cit.": "loco citato (à l'endroit cité)",
        "et al.": "et alii (et les autres)",
        "s.v.": "sub voce (sous le mot)",
        "viz.": "videlicet (c'est-à-dire)",
        "sc.": "scilicet (à savoir)",
        "fl.": "floruit (a vécu vers)",
        "ca.": "circa (environ)",
        "ed.": "editio/editor (édition/éditeur)",
        "trans.": "translator (traducteur)",
        "vol.": "volume",
        "p.": "page", "pp.": "pages",
        # Arabe
        "ṣ.": "ṣallā Allāhu ʿalayhi wa-sallam",
        "r.a.": "raḍiya Allāhu ʿanhu",
    }

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        expansions = []
        for abbr, full in self.ABBREVS.items():
            if abbr in text:
                expansions.append({"abbreviation": abbr, "expansion": full})
        return self._ok(
            {"expansions": expansions, "count": len(expansions)},
            f"{len(expansions)} abréviation(s) trouvée(s)",
        )


class FormatHebrewText(Shem):
    """#66 MNQ — Repos : formater un texte hébreu."""
    name = "Format Hebrew Text"
    skill_id = "format_hebrew_text"
    trigram = "מנק"
    trigram_name = "MNQ"
    number = 66
    category = "transform"
    quality = "Repos"
    description = "Formater un texte hébreu (direction RTL, espacement)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        # Ajouter les marques directionnelles RTL
        rtl_mark = "\u200F"  # RIGHT-TO-LEFT MARK
        lines = text.split("\n")
        formatted = []
        for line in lines:
            # Détecter si la ligne contient de l'hébreu
            has_hebrew = any("\u0590" <= ch <= "\u05FF" for ch in line)
            if has_hebrew:
                formatted.append(f"{rtl_mark}{line}")
            else:
                formatted.append(line)
        result = "\n".join(formatted)
        # Statistiques
        n_hebrew = sum(1 for ch in text if "\u0590" <= ch <= "\u05FF")
        n_vowels = sum(1 for ch in text if "\u05B0" <= ch <= "\u05BD")
        return self._ok(
            {"formatted": result, "hebrew_chars": n_hebrew, "vowel_marks": n_vowels,
             "has_nikud": n_vowels > 0},
            f"{n_hebrew} lettres hébraïques, {n_vowels} nikudot",
        )
