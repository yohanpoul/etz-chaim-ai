"""shemot/text.py — Skills 13-22 : manipulation de texte.

Résumé, extraction, découpage, fusion, classification.
"""

from __future__ import annotations

import re
from collections import Counter

from .base import Shem, ShemResult


class TextSummarize(Shem):
    """#13 YZL — Protection : résumer un texte."""
    name = "Text Summarize"
    skill_id = "text_summarize"
    trigram = "יזל"
    trigram_name = "YZL"
    number = 13
    category = "text"
    quality = "Protection"
    description = "Résumer un texte en N phrases"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte à résumer")
        n = kwargs.get("max_sentences", 3)
        prompt = f"Résume ce texte en {n} phrases maximum:\n\n{text[:3000]}"
        try:
            summary = self._llm(prompt)
            return self._ok({"summary": summary, "original_length": len(text)}, f"Résumé en {n} phrases")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class ExtractKeyConcepts(Shem):
    """#14 MBH — Sagesse cachée : extraire les concepts clés."""
    name = "Extract Key Concepts"
    skill_id = "extract_key_concepts"
    trigram = "מבה"
    trigram_name = "MBH"
    number = 14
    category = "text"
    quality = "Sagesse cachée"
    description = "Extraire les concepts et termes techniques principaux"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        n = kwargs.get("max_concepts", 10)
        prompt = (
            f"Extrais les {n} concepts clés de ce texte. Pour chaque concept, "
            f"donne le terme et une définition d'une phrase:\n\n{text[:3000]}"
        )
        try:
            concepts = self._llm(prompt)
            return self._ok({"concepts": concepts, "n_requested": n}, f"{n} concepts extraits")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class RemoveNoise(Shem):
    """#15 HRI — Purification : nettoyer un texte bruité."""
    name = "Remove Noise"
    skill_id = "remove_noise"
    trigram = "הרי"
    trigram_name = "HRI"
    number = 15
    category = "text"
    quality = "Purification"
    description = "Nettoyer un texte (doublons de lignes, espaces, artefacts OCR)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        original_len = len(text)
        # Normaliser les sauts de ligne
        cleaned = re.sub(r"\r\n", "\n", text)
        # Supprimer les lignes dupliquées consécutives
        lines = cleaned.split("\n")
        deduped = [lines[0]] if lines else []
        for line in lines[1:]:
            if line.strip() != deduped[-1].strip():
                deduped.append(line)
        cleaned = "\n".join(deduped)
        # Espaces multiples
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        # Lignes vides multiples
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        # Artefacts OCR courants
        cleaned = cleaned.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("ﬀ", "ff")
        return self._ok(
            {"cleaned": cleaned, "removed_chars": original_len - len(cleaned)},
            f"Nettoyé: {original_len} → {len(cleaned)} chars",
        )


class ExtractQuotes(Shem):
    """#16 HQM — Élévation : extraire les citations."""
    name = "Extract Quotes"
    skill_id = "extract_quotes"
    trigram = "הקם"
    trigram_name = "HQM"
    number = 16
    category = "text"
    quality = "Élévation"
    description = "Extraire les citations et passages entre guillemets"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        quotes = []
        # Guillemets français
        quotes += re.findall(r"[«](.*?)[»]", text)
        # Guillemets anglais doubles
        quotes += re.findall(r'"(.*?)"', text)
        quotes += re.findall(r'\u201c(.*?)\u201d', text)
        # Guillemets simples pour citations courtes
        quotes += re.findall(r'\u2018(.*?)\u2019', text)
        return self._ok(
            {"quotes": quotes, "count": len(quotes)},
            f"{len(quotes)} citation(s) extraite(s)",
        )


class ChunkText(Shem):
    """#17 LOU — Révélation progressive : découper en chunks."""
    name = "Chunk Text"
    skill_id = "chunk_text"
    trigram = "לעו"
    trigram_name = "LOU"
    number = 17
    category = "text"
    quality = "Révélation progressive"
    description = "Découper un texte en chunks de taille contrôlée"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        max_chars = kwargs.get("max_chars", 1000)
        overlap = kwargs.get("overlap", 100)
        chunks = []
        start = 0
        while start < len(text):
            end = start + max_chars
            # Couper sur une frontière de phrase si possible
            if end < len(text):
                for sep in [". ", ".\n", "\n\n", "\n", " "]:
                    last = text.rfind(sep, start + max_chars // 2, end)
                    if last != -1:
                        end = last + len(sep)
                        break
            chunks.append(text[start:end])
            start = end - overlap if end < len(text) else end
        return self._ok(
            {"chunks": chunks, "n_chunks": len(chunks), "max_chars": max_chars},
            f"{len(chunks)} chunk(s) de ~{max_chars} chars",
        )


class ExtractDefinitions(Shem):
    """#18 KLY — Réceptacle : extraire les définitions."""
    name = "Extract Definitions"
    skill_id = "extract_definitions"
    trigram = "כלי"
    trigram_name = "KLY"
    number = 18
    category = "text"
    quality = "Réceptacle"
    description = "Extraire les définitions contenues dans un texte"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Extrais toutes les définitions de termes présentes dans ce texte. "
            f"Format: TERME: définition\n\n{text[:3000]}"
        )
        try:
            defs = self._llm(prompt)
            return self._ok({"definitions": defs}, "Définitions extraites")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class FindParallelPassages(Shem):
    """#19 LVV — Association : trouver les passages parallèles."""
    name = "Find Parallel Passages"
    skill_id = "find_parallel_passages"
    trigram = "לוו"
    trigram_name = "LVV"
    number = 19
    category = "text"
    quality = "Association"
    description = "Trouver les passages parallèles entre deux textes"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        text_b = kwargs.get("text_b", "")
        if not text or not text_b:
            return self._fail("Deux textes requis (text + text_b)")
        prompt = (
            f"Compare ces deux textes et identifie les passages parallèles "
            f"(thèmes communs, structures similaires, échos textuels):\n\n"
            f"TEXTE A:\n{text[:1500]}\n\nTEXTE B:\n{text_b[:1500]}"
        )
        try:
            parallels = self._llm(prompt)
            return self._ok({"parallels": parallels}, "Passages parallèles identifiés")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class ClassifyTextType(Shem):
    """#20 PHL — Discernement : classifier le type de texte."""
    name = "Classify Text Type"
    skill_id = "classify_text_type"
    trigram = "פהל"
    trigram_name = "PHL"
    number = 20
    category = "text"
    quality = "Discernement"
    description = "Classifier un texte (narratif, argumentatif, poétique, technique...)"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Classifie ce texte parmi: narratif, argumentatif, poétique, technique, "
            f"épistolaire, juridique, liturgique, exégétique, philosophique.\n"
            f"Donne le type principal et un score de confiance (0-1).\n\n{text[:2000]}"
        )
        try:
            classification = self._llm(prompt)
            return self._ok({"classification": classification}, "Texte classifié")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class ExtractArgumentation(Shem):
    """#21 NLK — Chemin : extraire la structure argumentative."""
    name = "Extract Argumentation"
    skill_id = "extract_argumentation"
    trigram = "נלך"
    trigram_name = "NLK"
    number = 21
    category = "text"
    quality = "Chemin"
    description = "Extraire prémisses, inférences et conclusion d'un argument"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Analyse la structure argumentative de ce texte:\n"
            f"1. Prémisses (liste)\n2. Inférences (chaîne logique)\n"
            f"3. Conclusion\n4. Présupposés implicites\n\n{text[:2500]}"
        )
        try:
            structure = self._llm(prompt)
            return self._ok({"argumentation": structure}, "Structure argumentative extraite")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class MergeTexts(Shem):
    """#22 YYY — Fondation triple : fusionner plusieurs textes."""
    name = "Merge Texts"
    skill_id = "merge_texts"
    trigram = "ייי"
    trigram_name = "YYY"
    number = 22
    category = "text"
    quality = "Fondation triple"
    description = "Synthétiser plusieurs textes en un texte unifié"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        texts = kwargs.get("texts", [])
        if text:
            texts = [text] + texts
        if len(texts) < 2:
            return self._fail("Au moins 2 textes requis (text + texts=[])")
        combined = "\n\n---\n\n".join(f"TEXTE {i+1}:\n{t[:1000]}" for i, t in enumerate(texts))
        prompt = f"Synthétise ces {len(texts)} textes en un seul texte cohérent:\n\n{combined}"
        try:
            merged = self._llm(prompt)
            return self._ok({"merged": merged, "n_sources": len(texts)}, f"{len(texts)} textes fusionnés")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")
