"""Tests Sprint 5.2 — Synthesis extraction pour Binah (It'aruta Diltata).

Doctrine : la contemplation hitbonenut produit des descriptions au format
``"Hitbonenut insight: <question> — <synthèse>"``. Avant Sprint 5.2, toute
description en forme de question était rejetée sur ``question_deferred``,
même lorsque la synthèse substantielle après em-dash contenait un claim
causal évaluable. Sprint 5.2 extrait la synthèse et la route vers Binah,
tout en préservant ``question_deferred`` pour les questions pures.

Invariants doctrinaux préservés :
- ``DEFAULT_MIN_CONFIDENCE = 0.5`` (insight_validator)
- Seuil ``correlation_only`` < 0.6 (ligne 192) — garde Ghagiel
- ``ZivvugEngine.MIN_ACTIVE_SCORE = 0.5`` (Sprint 5.1 invariant)
"""

from __future__ import annotations

from insightforge.models import CandidateInsight
from insightforge.insight_validator import (
    DEFAULT_MIN_CONFIDENCE,
    InsightValidator,
    _extract_synthesis,
    _is_question,
)

from .conftest import StubCausal


class _ProbeCausal(StubCausal):
    """Stub Binah qui enregistre le claim texte reçu par check_claim."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.called = False
        self.last_cause = None

    def check_claim(self, cause, effect, domain=""):
        self.called = True
        self.last_cause = cause
        return super().check_claim(cause=cause, effect=effect, domain=domain)


# --- _extract_synthesis : unit tests ---


def test_extract_synthesis_no_em_dash():
    """Pas d'em-dash → pas de synthèse extractible."""
    assert _extract_synthesis("Hitbonenut insight: Comment X ?") is None


def test_extract_synthesis_empty_description():
    """Description vide ou None → None."""
    assert _extract_synthesis("") is None
    assert _extract_synthesis("   ") is None


def test_extract_synthesis_empty_after_dash():
    """Em-dash suivi de rien → None (pas de synthèse substantielle)."""
    assert _extract_synthesis("Comment X ? — ") is None


def test_extract_synthesis_too_short():
    """Synthèse <30 chars → None (probable titre court, pas un claim)."""
    assert _extract_synthesis("Comment X ? — # Court") is None


def test_extract_synthesis_substantial_claim():
    """Synthèse ≥30 chars non-question → extraite."""
    desc = (
        "Hitbonenut insight: Comment X fonctionne ? — Le mécanisme Y "
        "relie cause A et effet B via feedback loop structural"
    )
    result = _extract_synthesis(desc)
    assert result is not None
    assert result.startswith("Le mécanisme Y")
    assert "feedback loop" in result


def test_extract_synthesis_refuses_question_as_synthesis():
    """Synthèse qui est elle-même une question → None (préserve deferred)."""
    # La synthèse commence par "Pourquoi" → détectée comme question.
    desc = "Comment X ? — Pourquoi Y cause-t-il cela alors qu'on attendait Z ?"
    assert _extract_synthesis(desc) is None


def test_extract_synthesis_multiple_em_dashes():
    """Plusieurs em-dashes → split sur le premier, synthèse = reste."""
    desc = (
        "Hitbonenut insight: Comment X ? — # Synthèse — Trois principes "
        "fondateurs du mécanisme Y"
    )
    result = _extract_synthesis(desc)
    assert result is not None
    assert result.startswith("# Synthèse")
    # Le second em-dash reste dans la synthèse extraite.
    assert "—" in result


# --- Sprint 5.3 extension : format Q/A (hitbonenut.py direct path) ---


def test_extract_synthesis_qa_substantial():
    """Sprint 5.3 : format ``Q:/A:`` avec synthèse substantielle → extraite.

    hitbonenut.py:_submit_insight_candidate crée des candidates au format
    ``"Q: <question>\\nA: <response>"``. L'em-dash interne à la synthèse
    (ex. ``# Synthèse — Architecture``) n'est PAS un séparateur structurel
    — c'est du contenu. Cette extension route la synthèse complète après
    ``\\nA:`` vers Binah.
    """
    desc = (
        "Q: Quel monde correspond à l'action concrète ?\n"
        "A: # Synthèse — Le monde de Assiah correspond à l'action concrète "
        "via le mécanisme de descente des étincelles vers Malkuth"
    )
    result = _extract_synthesis(desc)
    assert result is not None
    assert result.startswith("# Synthèse")
    assert "Assiah" in result
    assert "action concrète" in result
    # La question d'origine doit être EXCLUE de la synthèse.
    assert "Quel monde correspond" not in result


def test_extract_synthesis_qa_preserves_em_dash_inside():
    """Sprint 5.3 : em-dash INTERNE à la synthèse Q/A n'est pas un séparateur.

    Doctrine de la dette n°2 (audit 18 avril) : le split sur em-dash ne
    doit PAS s'appliquer au format Q/A où l'em-dash est un caractère de
    contenu (titres markdown, listes, emphases).
    """
    desc = (
        "Q: Comment X fonctionne ?\n"
        "A: Le mécanisme Y — une structure causale complète — relie "
        "cause A et effet B via un feedback structural ouvert"
    )
    result = _extract_synthesis(desc)
    assert result is not None
    # La synthèse complète est préservée, em-dashes inclus.
    assert result.startswith("Le mécanisme Y")
    assert result.count("—") == 2
    assert "cause A et effet B" in result


def test_extract_synthesis_qa_too_short():
    """Sprint 5.3 régression : synthèse Q/A <30 chars → None."""
    desc = "Q: Comment X fonctionne ?\nA: # Court"
    assert _extract_synthesis(desc) is None


def test_extract_synthesis_qa_synthesis_is_question():
    """Sprint 5.3 régression : synthèse Q/A qui est elle-même une question → None."""
    desc = (
        "Q: Pourquoi X ?\n"
        "A: Pourquoi Y se produit-il différemment que Z dans ce domaine ?"
    )
    assert _extract_synthesis(desc) is None


def test_extract_synthesis_qa_malformed_no_answer_marker():
    """Sprint 5.3 régression : 'Q:' sans '\\nA:' — retombe sur comportement em-dash si applicable."""
    # Sans em-dash NI \nA: → None
    assert _extract_synthesis("Q: Comment X fonctionne ?") is None
    # Avec em-dash mais sans \nA: → format em-dash classique appliqué
    desc_em = "Q: Comment X ? — Le mécanisme Y cause Z via feedback structural B"
    result = _extract_synthesis(desc_em)
    assert result is not None
    assert result.startswith("Le mécanisme Y")


def test_extract_synthesis_qa_precedence_over_em_dash():
    """Sprint 5.3 : format Q/A a précédence sur em-dash quand les deux présents.

    hitbonenut.py produit Q/A avec em-dash INTERNE. Si on applique l'em-dash
    split en premier, on tronque la synthèse au milieu d'un mot. Le Q/A split
    doit gagner pour préserver l'intégrité du contenu.
    """
    desc = (
        "Q: Comment X ?\n"
        "A: # Synthèse — Trois Principes Structuraux — Architecture complète "
        "du système avec ses sous-modules et leurs interactions"
    )
    result = _extract_synthesis(desc)
    assert result is not None
    assert result.startswith("# Synthèse")
    # La synthèse doit contenir le troisième morceau après le 2e em-dash.
    assert "Architecture complète" in result


# --- _check_binah integration : Sprint 5.2 behavior ---


def test_question_with_substantial_synthesis_calls_binah_on_synthesis():
    """Sprint 5.2 : question + synthèse substantielle → Binah évalue la synthèse."""
    probe = _ProbeCausal()
    v = InsightValidator(binah=probe)
    candidate = CandidateInsight(
        description=(
            "Hitbonenut insight: Comment X fonctionne ? — Le mécanisme Y "
            "cause Z via feedback structural B et module W"
        ),
        confidence=0.7,
        connects_domains=["kabbalah", "ml"],
    )
    v.validate(candidate)
    assert probe.called is True
    assert probe.last_cause is not None
    # Binah doit voir la synthèse, pas la question entière.
    assert "mécanisme Y" in probe.last_cause
    assert "Comment X fonctionne" not in probe.last_cause


def test_question_without_synthesis_still_deferred():
    """Régression Sprint 5.2 : question pure sans synthèse → toujours deferred."""
    probe = _ProbeCausal()
    v = InsightValidator(binah=probe)
    candidate = CandidateInsight(
        description="Quelle est la relation entre Hishtalshelut et Information Bottleneck ?",
        confidence=0.7,
        connects_domains=["kabbalah", "ml"],
    )
    result = v.validate(candidate)
    assert not result.binah_ok
    assert "question_deferred" in result.binah_detail
    assert probe.called is False


def test_question_with_short_synthesis_still_deferred():
    """Régression Sprint 5.2 : question + synthèse trop courte → deferred.

    Le format réel hitbonenut est ``"Hitbonenut insight: Comment X ? — ..."``.
    Le préfixe ``:`` déclenche la détection question via `_is_question`,
    puis la synthèse courte (<30 chars) retourne None via `_extract_synthesis`.
    """
    probe = _ProbeCausal()
    v = InsightValidator(binah=probe)
    candidate = CandidateInsight(
        description="Hitbonenut insight: Comment X fonctionne ? — # Titre",
        confidence=0.7,
        connects_domains=["a", "b"],
    )
    result = v.validate(candidate)
    assert not result.binah_ok
    assert "question_deferred" in result.binah_detail
    assert probe.called is False


def test_claim_description_still_calls_binah_on_full_description():
    """Régression Sprint 5.2 : claim direct (pas question) → Binah sur description complète."""
    probe = _ProbeCausal()
    v = InsightValidator(binah=probe)
    candidate = CandidateInsight(
        description="Le mécanisme X cause Y via feedback structural Z dans le domaine D",
        confidence=0.7,
        connects_domains=["a", "b"],
    )
    v.validate(candidate)
    assert probe.called is True
    assert probe.last_cause == "Le mécanisme X cause Y via feedback structural Z dans le domaine D"


# --- Invariants doctrinaux préservés ---


def test_default_min_confidence_unchanged():
    """Invariant Sprint 5.2 : DEFAULT_MIN_CONFIDENCE reste 0.5."""
    assert DEFAULT_MIN_CONFIDENCE == 0.5


def test_zivvug_min_active_score_unchanged():
    """Invariant Sprint 5.2 : MIN_ACTIVE_SCORE Zivvug (0.5) non touché.

    Ce sprint travaille en amont (Binah) selon It'aruta Diltata. L'invariant
    doctrinal Zivvug figé en Sprint 5.1 reste absolument inchangé.
    """
    from partzufim.zivvug import ZivvugEngine

    assert ZivvugEngine.MIN_ACTIVE_SCORE == 0.5
