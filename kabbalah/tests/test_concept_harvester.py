"""kabbalah/tests/test_concept_harvester.py — Tests unitaires ConceptHarvester.

Yesod-Pipeline : harvest de concepts depuis 9 sources vivantes.

Tests Qliphoth (4 niveaux) :
  Niveau 1 — Gamchicoth (excès) : cap journalier respecté
  Niveau 2 — Gamaliel (corruption) : vecteurs NaN / norme-nulle rejetés
  Niveau 3 — Lilith (vide) : stop-words seuls rejetés
  Niveau 4 — Samael (dualité) : dédoublonnage sémantique correct
"""

from __future__ import annotations

import numpy as np
import pytest
from unittest.mock import MagicMock, patch


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _make_harvester() -> "ConceptHarvester":
    """Instancie un ConceptHarvester sans connexion DB (pour tests unitaires)."""
    from kabbalah.concept_harvester import ConceptHarvester
    ch = ConceptHarvester.__new__(ConceptHarvester)
    ch.db_url = "postgresql://localhost/etz_chaim"
    ch._conn = None
    ch._he = None
    ch.batch_size = 50
    ch.max_per_run = 200
    ch._harvested_keys = set()
    return ch


# ────────────────────────────────────────────────────────────────────
# Tests d'extraction (_extract_from_rows)
# ────────────────────────────────────────────────────────────────────

class TestExtractFromRows:
    """Extraction de concepts depuis les lignes de source."""

    def test_extracts_basic_concept(self):
        """Ligne simple → concept avec bonne authority_olam."""
        ch = _make_harvester()
        rows = [{"id": 1, "content": "La tsimtsum crée l'espace pour la créativité"}]
        concepts = ch._extract_from_rows(rows, text_field="content", source="tiferet", olam=0.75)

        assert len(concepts) == 1
        assert concepts[0]["authority_olam"] == 0.75
        assert concepts[0]["source_module"] == "tiferet"
        assert "tsimtsum" in concepts[0]["text"].lower()

    def test_extracts_multiple_rows(self):
        """Plusieurs lignes → autant de concepts."""
        ch = _make_harvester()
        rows = [
            {"id": 1, "assertion_text": "Le Keter est l'origine"},
            {"id": 2, "assertion_text": "Yesod est le canal"},
            {"id": 3, "assertion_text": "Malkuth est la manifestation"},
        ]
        concepts = ch._extract_from_rows(
            rows, text_field="assertion_text", source="sifrei_yesod", olam=1.0
        )
        assert len(concepts) == 3
        for c in concepts:
            assert c["authority_olam"] == 1.0
            assert c["source_module"] == "sifrei_yesod"

    def test_skips_empty_text_field(self):
        """Lignes avec text vide ou None → ignorées."""
        ch = _make_harvester()
        rows = [
            {"id": 1, "content": ""},
            {"id": 2, "content": None},
            {"id": 3, "content": "   "},
            {"id": 4, "content": "Concept valide ici"},
        ]
        concepts = ch._extract_from_rows(rows, text_field="content", source="tiferet", olam=0.75)
        assert len(concepts) == 1
        assert concepts[0]["text"] == "Concept valide ici"

    def test_causal_extracts_effect_when_present(self):
        """Source causal extrait aussi l'effet si la colonne existe."""
        ch = _make_harvester()
        rows = [{"id": 1, "cause": "stress chronique", "effect": "maladies cardiovasculaires"}]
        concepts = ch._extract_from_rows(
            rows, text_field="cause", source="causal", olam=0.25
        )
        texts = [c["text"] for c in concepts]
        assert "stress chronique" in texts
        assert "maladies cardiovasculaires" in texts

    def test_source_id_preserved(self):
        """source_id est préservé pour la traçabilité."""
        ch = _make_harvester()
        rows = [{"id": 42, "content": "Un concept avec ID"}]
        concepts = ch._extract_from_rows(rows, text_field="content", source="tiferet", olam=0.75)
        assert concepts[0]["source_id"] == "42"


# ────────────────────────────────────────────────────────────────────
# Tests Masakh (_masakh_filter) — Qliphah Niveau 3 : Lilith
# ────────────────────────────────────────────────────────────────────

class TestMasakhFilter:
    """Filtre Masakh — rejeter les fragments sans substance."""

    def test_rejects_short_text(self):
        """Texte < 4 caractères → rejeté."""
        ch = _make_harvester()
        raw = [
            {"text": "ab", "source_module": "test", "authority_olam": 0.5},
            {"text": "abc", "source_module": "test", "authority_olam": 0.5},
        ]
        assert ch._masakh_filter(raw) == []

    def test_rejects_empty_text(self):
        """Texte vide → rejeté."""
        ch = _make_harvester()
        raw = [{"text": "", "source_module": "test", "authority_olam": 0.5}]
        assert ch._masakh_filter(raw) == []

    def test_rejects_stopwords_only(self):
        """Texte composé uniquement de stop-words → rejeté."""
        ch = _make_harvester()
        raw = [
            {"text": "le la les", "source_module": "test", "authority_olam": 0.5},
            {"text": "the and or", "source_module": "test", "authority_olam": 0.5},
            {"text": "et ou en", "source_module": "test", "authority_olam": 0.5},
        ]
        assert ch._masakh_filter(raw) == []

    def test_keeps_meaningful_concept(self):
        """Texte avec au moins un mot substantiel → conservé."""
        ch = _make_harvester()
        raw = [
            {"text": "La tsimtsum", "source_module": "test", "authority_olam": 0.5},
        ]
        filtered = ch._masakh_filter(raw)
        assert len(filtered) == 1
        assert filtered[0]["text"] == "La tsimtsum"

    def test_mixed_keeps_only_valid(self):
        """Mélange valide/invalide → seuls les valides passent."""
        ch = _make_harvester()
        raw = [
            {"text": "La tsimtsum crée l'espace", "source_module": "test", "authority_olam": 0.5},
            {"text": "ab", "source_module": "test", "authority_olam": 0.5},
            {"text": "le la les du", "source_module": "test", "authority_olam": 0.5},
            {"text": "Yesod canal transmission", "source_module": "test", "authority_olam": 0.5},
        ]
        filtered = ch._masakh_filter(raw)
        assert len(filtered) == 2
        texts = [c["text"] for c in filtered]
        assert "La tsimtsum crée l'espace" in texts
        assert "Yesod canal transmission" in texts

    def test_exact_4_chars_passes(self):
        """Texte de exactement 4 caractères (non stop-word) → conservé."""
        ch = _make_harvester()
        raw = [{"text": "keter", "source_module": "test", "authority_olam": 0.5}]
        filtered = ch._masakh_filter(raw)
        assert len(filtered) == 1


# ────────────────────────────────────────────────────────────────────
# Tests cap journalier (_apply_daily_cap) — Qliphah Niveau 1 : Gamchicoth
# ────────────────────────────────────────────────────────────────────

class TestApplyDailyCap:
    """Anti-Gamchicoth : limiter le nombre de concepts par run."""

    def test_max_200_concepts(self):
        """300 concepts → max 200 retournés."""
        ch = _make_harvester()
        ch.max_per_run = 200
        concepts = [{"text": f"concept_{i}"} for i in range(300)]
        capped = ch._apply_daily_cap(concepts)
        assert len(capped) == 200

    def test_less_than_cap_unchanged(self):
        """50 concepts avec cap à 200 → les 50 sont retournés."""
        ch = _make_harvester()
        ch.max_per_run = 200
        concepts = [{"text": f"concept_{i}"} for i in range(50)]
        capped = ch._apply_daily_cap(concepts)
        assert len(capped) == 50

    def test_respects_custom_cap(self):
        """Cap personnalisé respecté."""
        ch = _make_harvester()
        ch.max_per_run = 10
        concepts = [{"text": f"concept_{i}"} for i in range(50)]
        capped = ch._apply_daily_cap(concepts)
        assert len(capped) == 10

    def test_order_preserved(self):
        """L'ordre des concepts est préservé (priorité Olam)."""
        ch = _make_harvester()
        ch.max_per_run = 3
        concepts = [{"text": f"c{i}", "authority_olam": 1.0 - i * 0.1} for i in range(5)]
        capped = ch._apply_daily_cap(concepts)
        assert capped[0]["text"] == "c0"
        assert capped[1]["text"] == "c1"
        assert capped[2]["text"] == "c2"


# ────────────────────────────────────────────────────────────────────
# Tests validation (_validate_embedding) — Qliphah Niveau 2 : Gamaliel
# ────────────────────────────────────────────────────────────────────

class TestValidateEmbedding:
    """Anti-Gamaliel : valider l'intégrité des vecteurs d'embedding."""

    def test_rejects_nan_embedding(self):
        """Vecteur avec NaN → rejeté."""
        ch = _make_harvester()
        bad = np.array([float("nan")] * 768, dtype=np.float32)
        assert not ch._validate_embedding(bad)

    def test_rejects_partial_nan(self):
        """Vecteur avec un seul NaN → rejeté."""
        ch = _make_harvester()
        bad = np.random.randn(768).astype(np.float32)
        bad[100] = float("nan")
        assert not ch._validate_embedding(bad)

    def test_rejects_zero_norm(self):
        """Vecteur de norme nulle → rejeté."""
        ch = _make_harvester()
        zero = np.zeros(768, dtype=np.float32)
        assert not ch._validate_embedding(zero)

    def test_rejects_near_zero_norm(self):
        """Vecteur de norme < 0.1 → rejeté."""
        ch = _make_harvester()
        tiny = np.full(768, 1e-10, dtype=np.float32)
        assert not ch._validate_embedding(tiny)

    def test_rejects_none(self):
        """None → rejeté."""
        ch = _make_harvester()
        assert not ch._validate_embedding(None)  # type: ignore[arg-type]

    def test_accepts_valid_embedding(self):
        """Vecteur normal (randn) → accepté."""
        ch = _make_harvester()
        good = np.random.randn(768).astype(np.float32)
        assert ch._validate_embedding(good)

    def test_accepts_unit_vector(self):
        """Vecteur unitaire → accepté."""
        ch = _make_harvester()
        v = np.zeros(768, dtype=np.float32)
        v[0] = 1.0
        assert ch._validate_embedding(v)


# ────────────────────────────────────────────────────────────────────
# Tests dédoublonnage sémantique (_semantic_dedup) — Qliphah Niveau 4 : Samael
# ────────────────────────────────────────────────────────────────────

class TestSemanticDedup:
    """Dédoublonnage sémantique par similarité cosinus."""

    def test_merges_near_identical_vectors(self):
        """Deux vecteurs quasi-identiques (cosine > 0.95) → un seul conservé."""
        ch = _make_harvester()
        np.random.seed(42)
        v1 = np.random.randn(768).astype(np.float32)
        v2 = v1 + np.random.randn(768).astype(np.float32) * 0.01  # très proche

        deduped = ch._semantic_dedup(
            [{"text": "a", "embedding": v1}, {"text": "b", "embedding": v2}],
            threshold=0.95,
        )
        assert len(deduped) == 1
        assert deduped[0]["text"] == "a"  # premier conservé

    def test_keeps_distinct_concepts(self):
        """Vecteurs orthogonaux → deux concepts conservés."""
        ch = _make_harvester()
        v1 = np.array([1.0] + [0.0] * 767, dtype=np.float32)
        v2 = np.array([0.0, 1.0] + [0.0] * 766, dtype=np.float32)

        deduped = ch._semantic_dedup(
            [{"text": "a", "embedding": v1}, {"text": "b", "embedding": v2}],
            threshold=0.95,
        )
        assert len(deduped) == 2

    def test_empty_list_unchanged(self):
        """Liste vide → liste vide."""
        ch = _make_harvester()
        assert ch._semantic_dedup([]) == []

    def test_single_element_unchanged(self):
        """Un seul élément → retourné tel quel."""
        ch = _make_harvester()
        v = np.random.randn(768).astype(np.float32)
        result = ch._semantic_dedup([{"text": "solo", "embedding": v}])
        assert len(result) == 1

    def test_no_embedding_key_not_deduped(self):
        """Concepts sans clé 'embedding' ne sont pas fusionnés entre eux."""
        ch = _make_harvester()
        concepts = [{"text": "a"}, {"text": "b"}, {"text": "c"}]
        result = ch._semantic_dedup(concepts, threshold=0.95)
        assert len(result) == 3


# ────────────────────────────────────────────────────────────────────
# Tests cosine similarity (_cosine_sim)
# ────────────────────────────────────────────────────────────────────

class TestCosineSim:
    """Similarité cosinus — briques de base pour le dédup."""

    def test_identical_vectors_give_1(self):
        """Vecteur identique → cosine = 1.0."""
        ch = _make_harvester()
        v = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        assert abs(ch._cosine_sim(v, v) - 1.0) < 1e-5

    def test_orthogonal_vectors_give_0(self):
        """Vecteurs orthogonaux → cosine = 0.0."""
        ch = _make_harvester()
        a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        assert abs(ch._cosine_sim(a, b)) < 1e-5

    def test_opposite_vectors_give_minus_1(self):
        """Vecteurs opposés → cosine = -1.0."""
        ch = _make_harvester()
        v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert abs(ch._cosine_sim(v, -v) - (-1.0)) < 1e-5

    def test_zero_norm_gives_0(self):
        """Vecteur nul → retourne 0.0 sans division par zéro."""
        ch = _make_harvester()
        zero = np.zeros(3, dtype=np.float32)
        v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert ch._cosine_sim(zero, v) == 0.0
        assert ch._cosine_sim(v, zero) == 0.0


# ────────────────────────────────────────────────────────────────────
# Tests intégration légère (sans DB réelle)
# ────────────────────────────────────────────────────────────────────

class TestHarvestPipeline:
    """Tests du pipeline harvest avec DB mockée."""

    def test_harvest_returns_stats_dict(self):
        """harvest() retourne un dict avec les clés attendues."""
        from kabbalah.concept_harvester import ConceptHarvester
        ch = ConceptHarvester.__new__(ConceptHarvester)
        ch.db_url = "postgresql://localhost/etz_chaim"
        ch._conn = None
        ch._he = None
        ch.batch_size = 50
        ch.max_per_run = 200
        ch._harvested_keys = set()

        # Mocker toutes les méthodes qui touchent la DB
        ch._query_source = MagicMock(return_value=[])
        ch._prune_stale = MagicMock(return_value=0)

        from datetime import datetime, timezone
        stats = ch.harvest(last_harvest=datetime.now(timezone.utc))

        required_keys = {"harvested", "deduped", "rejected", "errors", "pruned", "sources"}
        assert required_keys.issubset(stats.keys())

    def test_harvest_handles_source_failure_gracefully(self):
        """Une source en erreur → erreur comptée, autres sources continuent."""
        from kabbalah.concept_harvester import ConceptHarvester
        ch = ConceptHarvester.__new__(ConceptHarvester)
        ch.db_url = "postgresql://localhost/etz_chaim"
        ch._conn = None
        ch._he = None
        ch.batch_size = 50
        ch.max_per_run = 200
        ch._harvested_keys = set()

        call_count = 0

        def failing_query_source(src, since):
            nonlocal call_count
            call_count += 1
            if src["name"] == "tiferet":
                raise RuntimeError("Connexion perdue")
            return []

        ch._query_source = failing_query_source
        ch._prune_stale = MagicMock(return_value=0)

        from datetime import datetime, timezone
        stats = ch.harvest(last_harvest=datetime.now(timezone.utc))

        assert stats["errors"] >= 1
        # Les autres sources ont quand même été interrogées
        assert call_count > 1
