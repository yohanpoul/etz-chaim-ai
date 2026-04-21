"""shemot/sources.py — Skills 33-40 : gestion de sources.

Parsing de références, vérification de citations, bibliographie,
chaînes de transmission, fiabilité.
"""

from __future__ import annotations

import re

from .base import Shem, ShemResult


class ParseReference(Shem):
    """#33 YChV — Unité : parser une référence bibliographique."""
    name = "Parse Reference"
    skill_id = "parse_reference"
    trigram = "יחו"
    trigram_name = "YChV"
    number = 33
    category = "sources"
    quality = "Unité"
    description = "Parser une référence (Zohar III:123a, Quran 2:255, Talmud Shabbat 31a)"

    PATTERNS = [
        # Zohar : Zohar I:15a, Zohar II 176b
        (r"(?i)zohar\s+([IViv]+)\s*[:\s]?\s*(\d+[ab]?)", "zohar"),
        # Talmud : Shabbat 31a, Berakhot 6b
        (r"(?i)(berakhot|shabbat|eruvin|pesachim|yoma|sukkah|beitzah|rosh hashanah|taanit|megillah|moed katan|chagigah|yevamot|ketubot|nedarim|nazir|sotah|gittin|kiddushin|bava kamma|bava metzia|bava batra|sanhedrin|makkot|shevuot|avodah zarah|horayot|zevachim|menachot|chullin|bekhorot|arakhin|temurah|keritot|meilah|tamid|middot|kinnim|niddah)\s+(\d+[ab]?)", "talmud"),
        # Coran : 2:255, Quran 4:1
        (r"(?i)(?:quran|coran|qur'an|sourate?)\s*(\d+)\s*[:\s]\s*(\d+(?:-\d+)?)", "quran"),
        # Bible : Gen 1:1, Exode 14:19
        (r"(?i)(gen(?:esis|èse)?|exo(?:de|dus)?|lev(?:iticus|ítique)?|num(?:bers|éros)?|deut(?:eronomy|éronome)?|isa(?:iah|ïe)?|jer(?:emiah|émie)?|ezek(?:iel)?|psa(?:lms?|umes?)?|prov(?:erbs|erbes)?)\s*(\d+)\s*[:\s]\s*(\d+(?:-\d+)?)", "bible"),
        # Référence académique : (Scholem 1941, p.34)
        (r"\(([A-Z][a-zé]+(?:\s+(?:et al\.|&\s+[A-Z][a-zé]+))?)\s*[,]?\s*(\d{4})[,]?\s*(?:p\.?\s*(\d+(?:-\d+)?))?\)", "academic"),
        # Etz Chaim : Etz Chaim, Sha'ar 1, ch. 2
        (r"(?i)etz\s+cha[iy]m\s*[,:]?\s*(?:sha'ar|porte?)\s*(\d+)", "etz_chaim"),
    ]

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte contenant des références")
        refs = []
        for pattern, ref_type in self.PATTERNS:
            for match in re.finditer(pattern, text):
                refs.append({
                    "type": ref_type,
                    "raw": match.group(0),
                    "groups": match.groups(),
                    "position": match.start(),
                })
        return self._ok(
            {"references": refs, "count": len(refs)},
            f"{len(refs)} référence(s) parsée(s)",
        )


class VerifyCitation(Shem):
    """#34 LHCh — Vitalité : vérifier l'exactitude d'une citation."""
    name = "Verify Citation"
    skill_id = "verify_citation"
    trigram = "להח"
    trigram_name = "LHCh"
    number = 34
    category = "sources"
    quality = "Vitalité"
    description = "Comparer une citation avec le texte source (diff)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        source = kwargs.get("source", "")
        if not text or not source:
            return self._fail("Citation (text) et source requis")
        # Normaliser pour comparaison
        norm_cite = " ".join(text.lower().split())
        norm_source = " ".join(source.lower().split())
        # Vérifier inclusion exacte
        exact = norm_cite in norm_source
        # Similarité par mots communs
        cite_words = set(norm_cite.split())
        source_words = set(norm_source.split())
        overlap = cite_words & source_words
        similarity = len(overlap) / max(len(cite_words), 1)
        return self._ok(
            {"exact_match": exact, "word_similarity": round(similarity, 3),
             "common_words": len(overlap), "citation_words": len(cite_words)},
            f"{'Exacte' if exact else 'Approx'} — similarité: {similarity:.1%}",
        )


class BuildBibliography(Shem):
    """#35 KVQ — Espoir : construire une bibliographie formatée."""
    name = "Build Bibliography"
    skill_id = "build_bibliography"
    trigram = "כוק"
    trigram_name = "KVQ"
    number = 35
    category = "sources"
    quality = "Espoir"
    description = "Construire une bibliographie à partir de métadonnées"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        entries = kwargs.get("entries", [])
        if not entries and text:
            # Essayer de parser un texte brut
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            entries = [{"raw": l} for l in lines]
        if not entries:
            return self._fail("Pas d'entrées bibliographiques")
        formatted = []
        for e in entries:
            if "raw" in e:
                formatted.append(e["raw"])
            else:
                author = e.get("author", "?")
                year = e.get("year", "s.d.")
                title = e.get("title", "Sans titre")
                publisher = e.get("publisher", "")
                pub_str = f". {publisher}" if publisher else ""
                formatted.append(f"{author} ({year}). *{title}*{pub_str}.")
        formatted.sort()
        return self._ok(
            {"bibliography": formatted, "count": len(formatted)},
            f"{len(formatted)} entrée(s) bibliographique(s)",
        )


class ExtractIsnad(Shem):
    """#36 MND — Serment : extraire une chaîne de transmission."""
    name = "Extract Isnad"
    skill_id = "extract_isnad"
    trigram = "מנד"
    trigram_name = "MND"
    number = 36
    category = "sources"
    quality = "Serment"
    description = "Extraire une chaîne de transmission (isnad, shalsheleth)"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Extrais la chaîne de transmission intellectuelle de ce texte "
            f"(maître → élève, isnad, ou généalogie d'idées). "
            f"Format: Personne1 → Personne2 → Personne3...\n\n{text[:2500]}"
        )
        try:
            chain = self._llm(prompt)
            return self._ok({"chain": chain}, "Chaîne de transmission extraite")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class ClassifySourceReliability(Shem):
    """#37 ANI — Réponse : évaluer la fiabilité d'une source."""
    name = "Classify Source Reliability"
    skill_id = "classify_source_reliability"
    trigram = "אני"
    trigram_name = "ANI"
    number = 37
    category = "sources"
    quality = "Réponse"
    description = "Évaluer la fiabilité d'une source (Tier 1-4)"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de description de source")
        prompt = (
            f"Évalue la fiabilité de cette source selon l'échelle :\n"
            f"Tier 1: paper peer-reviewed, édition critique, monographie universitaire\n"
            f"Tier 2: thèse, actes de congrès, preprint arXiv avec citations\n"
            f"Tier 3: Quanta Magazine, Stanford Encyclopedia, cours universitaire\n"
            f"Tier 4: blog, Medium, source non vérifiable\n\n"
            f"Source: {text[:2000]}\n\nRéponds: Tier [N] — [justification courte]"
        )
        try:
            assessment = self._llm(prompt)
            return self._ok({"assessment": assessment}, "Fiabilité évaluée")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class ExtractMetadata(Shem):
    """#38 ChOM — Chaleur : extraire les métadonnées d'un document."""
    name = "Extract Metadata"
    skill_id = "extract_metadata"
    trigram = "חעם"
    trigram_name = "ChOM"
    number = 38
    category = "sources"
    quality = "Chaleur"
    description = "Extraire auteur, date, éditeur, etc. d'un texte"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Extrais les métadonnées de ce document/extrait. Réponds en JSON:\n"
            f'{{"author": "...", "title": "...", "date": "...", "publisher": "...", '
            f'"language": "...", "type": "..."}}\n\n{text[:2000]}'
        )
        try:
            metadata = self._llm(prompt)
            return self._ok({"metadata": metadata}, "Métadonnées extraites")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class DetectInterpolation(Shem):
    """#39 RHO — Guérison : détecter les interpolations possibles."""
    name = "Detect Interpolation"
    skill_id = "detect_interpolation"
    trigram = "רהע"
    trigram_name = "RHO"
    number = 39
    category = "sources"
    quality = "Guérison"
    description = "Détecter les ajouts tardifs ou interpolations dans un texte"
    requires_llm = True
    olam = "briah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Analyse ce texte pour détecter d'éventuelles interpolations (ajouts tardifs). "
            f"Signes: ruptures de style, anachronismes, vocabulaire incohérent, "
            f"insertions qui brisent le flux narratif:\n\n{text[:3000]}"
        )
        try:
            analysis = self._llm(prompt)
            return self._ok({"analysis": analysis}, "Analyse d'interpolation")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class CrossReference(Shem):
    """#40 YYZ — Force : trouver les références croisées."""
    name = "Cross Reference"
    skill_id = "cross_reference"
    trigram = "ייז"
    trigram_name = "YYZ"
    number = 40
    category = "sources"
    quality = "Force"
    description = "Trouver les références croisées entre deux corpus"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        text_b = kwargs.get("text_b", "")
        if not text or not text_b:
            return self._fail("Deux textes requis (text + text_b)")
        prompt = (
            f"Identifie les références croisées entre ces deux textes "
            f"(allusions, citations, thèmes communs, termes techniques partagés):\n\n"
            f"CORPUS A:\n{text[:1500]}\n\nCORPUS B:\n{text_b[:1500]}"
        )
        try:
            refs = self._llm(prompt)
            return self._ok({"cross_references": refs}, "Références croisées trouvées")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")
