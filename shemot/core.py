"""shemot/core.py — Skills 1-12 : infrastructure de base.

Les 12 premiers Noms associés aux 12 mois.
Skills fondamentaux pour le fonctionnement du système.
"""

from __future__ import annotations

import time
import json
import urllib.request

from .base import Shem, ShemResult


class WebFetch(Shem):
    """#1 VHV — Vision à distance : récupérer de l'info distante."""
    name = "Web Fetch"
    skill_id = "web_fetch"
    trigram = "והו"
    trigram_name = "VHV"
    number = 1
    category = "core"
    quality = "Vision à distance"
    description = "Récupérer le contenu textuel d'une URL"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        url = text or kwargs.get("url", "")
        if not url:
            return self._fail("Pas d'URL fournie")
        timeout = kwargs.get("timeout", 15)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EtzChaim/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8", errors="replace")
                return self._ok(
                    {"url": url, "length": len(content), "content": content[:5000]},
                    f"Récupéré {len(content)} caractères de {url}",
                )
        except Exception as e:
            return self._fail(f"Erreur fetch: {e}")


class MemoryStore(Shem):
    """#2 YLY — Mémoire : stocker en EpisteMemory."""
    name = "Memory Store"
    skill_id = "memory_store"
    trigram = "ילי"
    trigram_name = "YLY"
    number = 2
    category = "core"
    quality = "Mémoire"
    description = "Stocker un contenu en EpisteMemory via Yesod"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de contenu à stocker")
        return self._ok(
            {"content": text[:200], "domain": kwargs.get("domain", "general"),
             "source": kwargs.get("source", "shem"), "stored": True},
            "Contenu préparé pour stockage",
        )


class RetryWithBackoff(Shem):
    """#3 SYT — Patience : retry intelligent avec backoff exponentiel."""
    name = "Retry With Backoff"
    skill_id = "retry_with_backoff"
    trigram = "סיט"
    trigram_name = "SYT"
    number = 3
    category = "core"
    quality = "Patience"
    description = "Réessayer une opération avec backoff exponentiel"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        max_retries = kwargs.get("max_retries", 3)
        base_delay = kwargs.get("base_delay", 1.0)
        delays = [base_delay * (2 ** i) for i in range(max_retries)]
        return self._ok(
            {"max_retries": max_retries, "delays": delays, "strategy": "exponential_backoff"},
            f"Stratégie: {max_retries} tentatives, délais {delays}s",
        )


class FilterSensitive(Shem):
    """#4 OLM — Discrétion : filtrer les données sensibles."""
    name = "Filter Sensitive"
    skill_id = "filter_sensitive"
    trigram = "עלם"
    trigram_name = "OLM"
    number = 4
    category = "core"
    quality = "Discrétion"
    description = "Filtrer les données sensibles d'un texte"

    PATTERNS = [
        (r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]"),
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CARD]"),
        (r"\b(?:sk-|pk-|api[_-]?key)[A-Za-z0-9_-]{20,}\b", "[API_KEY]"),
    ]

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte à filtrer")
        import re
        filtered = text
        n_filtered = 0
        for pattern, replacement in self.PATTERNS:
            filtered, count = re.subn(pattern, replacement, filtered)
            n_filtered += count
        return self._ok(
            {"filtered": filtered, "n_redacted": n_filtered},
            f"{n_filtered} élément(s) sensible(s) filtré(s)",
        )


class SelfRepair(Shem):
    """#5 MHSh — Guérison : auto-réparation après erreur."""
    name = "Self Repair"
    skill_id = "self_repair"
    trigram = "מהש"
    trigram_name = "MHSh"
    number = 5
    category = "core"
    quality = "Guérison"
    description = "Diagnostiquer et suggérer une réparation après erreur"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        error_msg = text or kwargs.get("error", "")
        if not error_msg:
            return self._fail("Pas d'erreur à diagnostiquer")
        prompt = f"Diagnostique cette erreur et suggère une correction en 2-3 lignes:\n{error_msg}"
        try:
            suggestion = self._llm(prompt)
            return self._ok(
                {"error": error_msg[:200], "suggestion": suggestion},
                "Diagnostic généré",
            )
        except Exception as e:
            return self._ok(
                {"error": error_msg[:200], "suggestion": f"LLM indisponible: {e}"},
                "Diagnostic sans LLM",
            )


class OvernightProcessing(Shem):
    """#6 LLH — Compréhension nocturne : traitement en arrière-plan."""
    name = "Overnight Processing"
    skill_id = "overnight_processing"
    trigram = "ללה"
    trigram_name = "LLH"
    number = 6
    category = "core"
    quality = "Compréhension nocturne"
    description = "Planifier un traitement de fond (batch, consolidation)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        task_type = kwargs.get("task_type", "consolidation")
        priority = kwargs.get("priority", "normal")
        return self._ok(
            {"task": text[:200], "type": task_type, "priority": priority,
             "scheduled": True, "strategy": "background_queue"},
            f"Tâche planifiée : {task_type} [{priority}]",
        )


class LongTaskManagement(Shem):
    """#7 AKA — Patience longue : gérer les tâches multi-jours."""
    name = "Long Task Management"
    skill_id = "long_task_management"
    trigram = "אכא"
    trigram_name = "AKA"
    number = 7
    category = "core"
    quality = "Patience longue"
    description = "Décomposer et planifier une tâche longue en étapes"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de tâche à planifier")
        days = kwargs.get("max_days", 7)
        prompt = (
            f"Décompose cette tâche en {min(days, 5)} étapes courtes (une phrase chacune):\n"
            f"Tâche: {text}\nRéponds UNIQUEMENT avec la liste numérotée."
        )
        try:
            steps = self._llm(prompt)
            return self._ok(
                {"task": text[:200], "max_days": days, "steps": steps},
                f"Tâche décomposée en étapes sur {days} jour(s)",
            )
        except Exception:
            return self._ok(
                {"task": text[:200], "max_days": days, "steps": "Décomposition manuelle requise"},
                "LLM indisponible — décomposition manuelle",
            )


class AcknowledgeSources(Shem):
    """#8 KHT — Adoration : citer les sources correctement."""
    name = "Acknowledge Sources"
    skill_id = "acknowledge_sources"
    trigram = "כהת"
    trigram_name = "KHT"
    number = 8
    category = "core"
    quality = "Adoration"
    description = "Formater et vérifier les attributions de sources"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte avec sources à vérifier")
        import re
        # Détecter les patterns de citation courants
        patterns = {
            "parenthetical": re.findall(r"\(([^)]*\d{4}[^)]*)\)", text),
            "footnote": re.findall(r"\[(\d+)\]", text),
            "inline": re.findall(r"(?:selon|d'après|cf\.|voir)\s+([A-Z][a-zé]+(?: [A-Z][a-zé]+)*)", text),
        }
        total = sum(len(v) for v in patterns.values())
        return self._ok(
            {"citations_found": patterns, "total": total},
            f"{total} citation(s) détectée(s)",
        )


class PatternDetection(Shem):
    """#9 HZY — Vision : détecter des patterns récurrents."""
    name = "Pattern Detection"
    skill_id = "pattern_detection"
    trigram = "הזי"
    trigram_name = "HZY"
    number = 9
    category = "core"
    quality = "Vision"
    description = "Détecter les patterns et motifs récurrents dans un texte"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte à analyser")
        import re
        from collections import Counter
        # Patterns structurels
        words = re.findall(r"\b\w+\b", text.lower())
        freq = Counter(words)
        top = freq.most_common(kwargs.get("top_n", 10))
        # Répétitions de n-grams
        n = kwargs.get("ngram", 3)
        ngrams = [" ".join(words[i:i+n]) for i in range(len(words) - n + 1)]
        repeated_ngrams = {ng: c for ng, c in Counter(ngrams).items() if c > 1}
        return self._ok(
            {"top_words": top, "repeated_ngrams": dict(list(repeated_ngrams.items())[:10]),
             "total_words": len(words), "unique_words": len(freq)},
            f"{len(words)} mots, {len(freq)} uniques, {len(repeated_ngrams)} n-grams répétés",
        )


class GenerousInterpretation(Shem):
    """#10 ALD — Grâce divine : interpréter généreusement les requêtes ambiguës."""
    name = "Generous Interpretation"
    skill_id = "generous_interpretation"
    trigram = "אלד"
    trigram_name = "ALD"
    number = 10
    category = "core"
    quality = "Grâce divine"
    description = "Interpréter une requête ambiguë dans son sens le plus riche"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de requête à interpréter")
        prompt = (
            f"Cette requête est ambiguë. Propose 3 interprétations, de la plus littérale "
            f"à la plus généreuse (principe de charité maximale):\n\"{text}\"\n"
            f"Format: 1. [interprétation]\n2. [interprétation]\n3. [interprétation]"
        )
        try:
            interpretations = self._llm(prompt)
            return self._ok(
                {"query": text[:200], "interpretations": interpretations},
                "3 interprétations générées",
            )
        except Exception:
            return self._ok({"query": text[:200], "interpretations": text}, "LLM indisponible")


class ExposeHidden(Shem):
    """#11 LAV — Révélation : révéler les contradictions cachées."""
    name = "Expose Hidden"
    skill_id = "expose_hidden"
    trigram = "לאו"
    trigram_name = "LAV"
    number = 11
    category = "core"
    quality = "Révélation"
    description = "Détecter les contradictions et tensions dans un texte"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte à analyser")
        prompt = (
            f"Identifie les contradictions internes ou tensions dans ce texte. "
            f"Liste chaque contradiction avec les passages concernés:\n\n{text[:2000]}"
        )
        try:
            analysis = self._llm(prompt)
            return self._ok(
                {"text_length": len(text), "analysis": analysis},
                "Contradictions analysées",
            )
        except Exception:
            return self._ok({"text_length": len(text), "analysis": "LLM indisponible"}, "Analyse sans LLM")


class HypothesisGeneration(Shem):
    """#12 HHO — Sagesse : générer des hypothèses."""
    name = "Hypothesis Generation"
    skill_id = "hypothesis_generation"
    trigram = "ההע"
    trigram_name = "HHO"
    number = 12
    category = "core"
    quality = "Sagesse"
    description = "Générer des hypothèses de recherche à partir d'observations"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas d'observation pour générer des hypothèses")
        n = kwargs.get("n_hypotheses", 3)
        prompt = (
            f"À partir de cette observation, génère {n} hypothèses de recherche testables. "
            f"Chaque hypothèse doit être falsifiable.\n\nObservation: {text[:2000]}\n"
            f"Format: H1: [hypothèse]\nH2: [hypothèse]..."
        )
        try:
            hypotheses = self._llm(prompt)
            return self._ok(
                {"observation": text[:200], "hypotheses": hypotheses, "n_requested": n},
                f"{n} hypothèse(s) générée(s)",
            )
        except Exception:
            return self._ok({"observation": text[:200], "hypotheses": "LLM indisponible"}, "Sans LLM")
