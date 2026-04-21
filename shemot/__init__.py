"""shemot/ — Les 72 Noms (Shem HaMephorash) : micro-skills atomiques.

שֵׁם הַמְפֹרָשׁ — Le Nom Explicite.
72 trigrammes extraits d'Exode 14:19-21 (3 × 72 lettres).
Chaque Nom est un skill atomique, composable, réutilisable.

Usage:
    from shemot import get_shem, list_shemot, run_shem

    shem = get_shem("gematria_calc")
    result = shem.run("אלהים")

    for info in list_shemot():
        print(info["skill_id"], info["description"])
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from .base import Shem, ShemResult

# ── core (1-12) ─────────────────────────────────────────────
from .core import (
    WebFetch, MemoryStore, RetryWithBackoff, FilterSensitive,
    SelfRepair, OvernightProcessing, LongTaskManagement,
    AcknowledgeSources, PatternDetection, GenerousInterpretation,
    ExposeHidden, HypothesisGeneration,
)

# ── text (13-22) ────────────────────────────────────────────
from .text import (
    TextSummarize, ExtractKeyConcepts, RemoveNoise, ExtractQuotes,
    ChunkText, ExtractDefinitions, FindParallelPassages,
    ClassifyTextType, ExtractArgumentation, MergeTexts,
)

# ── language (23-32) ────────────────────────────────────────
from .language import (
    DetectLanguage, TransliterateHebrew, TransliterateArabic,
    GematriaCalc, Notarikon, Temura, DetectScript,
    WordFrequency, ExtractRoots, CompareTranslations,
)

# ── sources (33-40) ─────────────────────────────────────────
from .sources import (
    ParseReference, VerifyCitation, BuildBibliography, ExtractIsnad,
    ClassifySourceReliability, ExtractMetadata, DetectInterpolation,
    CrossReference,
)

# ── reasoning (41-50) ───────────────────────────────────────
from .reasoning import (
    DetectAnalogy, CheckSyllogism, GenerateCounterfactual,
    DetectFallacy, RateEvidenceLevel, FindDivergence,
    SteelmanArgument, DecomposeClaim, IdentifyAssumptions,
    MapStructure,
)

# ── temporal (51-58) ────────────────────────────────────────
from .temporal import (
    ParseDate, ConvertCalendar, BuildTimeline, DetectAnachronism,
    PeriodicityDetect, EpochContext, GenealogyParse,
    SynchronicityDetect,
)

# ── transform (59-66) ───────────────────────────────────────
from .transform import (
    NormalizeUnicode, ConvertUnits, JsonToMarkdown,
    MarkdownToStructured, DiffTexts, SemanticDedup,
    ExpandAbbreviation, FormatHebrewText,
)

# ── meta (67-72) ────────────────────────────────────────────
from .meta import (
    ComposeShemot, ShemDiagnostic, AuditResult, BatchRun,
    CacheResult, ShemToSentier,
)


# ── Registre ordonné des 72 Noms ───────────────────────────

_ALL_CLASSES: list[type[Shem]] = [
    # core 1-12
    WebFetch, MemoryStore, RetryWithBackoff, FilterSensitive,
    SelfRepair, OvernightProcessing, LongTaskManagement,
    AcknowledgeSources, PatternDetection, GenerousInterpretation,
    ExposeHidden, HypothesisGeneration,
    # text 13-22
    TextSummarize, ExtractKeyConcepts, RemoveNoise, ExtractQuotes,
    ChunkText, ExtractDefinitions, FindParallelPassages,
    ClassifyTextType, ExtractArgumentation, MergeTexts,
    # language 23-32
    DetectLanguage, TransliterateHebrew, TransliterateArabic,
    GematriaCalc, Notarikon, Temura, DetectScript,
    WordFrequency, ExtractRoots, CompareTranslations,
    # sources 33-40
    ParseReference, VerifyCitation, BuildBibliography, ExtractIsnad,
    ClassifySourceReliability, ExtractMetadata, DetectInterpolation,
    CrossReference,
    # reasoning 41-50
    DetectAnalogy, CheckSyllogism, GenerateCounterfactual,
    DetectFallacy, RateEvidenceLevel, FindDivergence,
    SteelmanArgument, DecomposeClaim, IdentifyAssumptions,
    MapStructure,
    # temporal 51-58
    ParseDate, ConvertCalendar, BuildTimeline, DetectAnachronism,
    PeriodicityDetect, EpochContext, GenealogyParse,
    SynchronicityDetect,
    # transform 59-66
    NormalizeUnicode, ConvertUnits, JsonToMarkdown,
    MarkdownToStructured, DiffTexts, SemanticDedup,
    ExpandAbbreviation, FormatHebrewText,
    # meta 67-72
    ComposeShemot, ShemDiagnostic, AuditResult, BatchRun,
    CacheResult, ShemToSentier,
]

# Index par skill_id → instance singleton
_REGISTRY: dict[str, Shem] = {}
for _cls in _ALL_CLASSES:
    _inst = _cls()
    _REGISTRY[_inst.skill_id] = _inst


# ── Chargement des attributs sacrés depuis shemot_72.yaml ──

_SACRED_YAML = Path(__file__).parent / "shemot_72.yaml"
_SACRED_ATTRS = (
    "suffix", "angel_name", "choir", "zodiac_sign",
    "zodiac_degrees", "element", "calendar_start", "calendar_end",
    "psalm_verse",
)

# Index par numéro → instance
_BY_NUMBER: dict[int, Shem] = {s.number: s for s in _REGISTRY.values()}


def _load_sacred_attributes() -> None:
    """Charger shemot_72.yaml et enrichir chaque Shem singleton."""
    if not _SACRED_YAML.exists():
        return
    with open(_SACRED_YAML, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not data or "shemot" not in data:
        return
    for entry in data["shemot"]:
        num = entry.get("number")
        shem = _BY_NUMBER.get(num)
        if shem is None:
            continue
        for attr in _SACRED_ATTRS:
            val = entry.get(attr)
            if val is not None:
                setattr(shem, attr, val)
        # sacred_sephirah from YAML "sephirah" (distinct from quality)
        seph = entry.get("sephirah")
        if seph is not None:
            shem.sacred_sephirah = seph


_load_sacred_attributes()


def get_shem(skill_id: str) -> Shem | None:
    """Obtenir un shem par son skill_id."""
    return _REGISTRY.get(skill_id)


def get_shem_by_number(number: int) -> Shem | None:
    """Obtenir un shem par son numéro (1-72)."""
    return _BY_NUMBER.get(number)


def list_shemot() -> list[dict]:
    """Lister les 72 shemot avec leurs métadonnées."""
    return [
        {
            "number": s.number,
            "trigram": s.trigram,
            "trigram_name": s.trigram_name,
            "skill_id": s.skill_id,
            "program": s.name,
            "category": s.category,
            "quality": s.quality,
            "description": s.description,
            "requires_llm": s.requires_llm,
            "olam": s.olam,
            # Attributs sacrés
            "suffix": s.suffix,
            "angel_name": s.angel_name,
            "choir": s.choir,
            "sacred_sephirah": s.sacred_sephirah,
            "zodiac_sign": s.zodiac_sign,
            "zodiac_degrees": s.zodiac_degrees,
            "element": s.element,
            "calendar_start": s.calendar_start,
            "calendar_end": s.calendar_end,
            "psalm_verse": s.psalm_verse,
        }
        for s in sorted(_REGISTRY.values(), key=lambda s: s.number)
    ]


def run_shem(skill_id: str, text: str = "", **kwargs) -> ShemResult:
    """Exécuter un shem par son skill_id."""
    shem = get_shem(skill_id)
    if shem is None:
        return ShemResult(
            shem=skill_id, trigram="???", number=0,
            success=False, message=f"Skill inconnu: {skill_id}",
            errors=[f"'{skill_id}' n'existe pas dans le registre"],
        )
    return shem.run(text, **kwargs)
