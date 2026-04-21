"""Tests de l'API de requête Sifrei Yesod."""

from unittest.mock import patch

import pytest


def test_get_assertion_existing(query, seeded_db):
    """Récupérer une assertion existante par ID."""
    result = query.get_assertion("EC-K99-001")
    assert result is not None
    assert result["assertion_id"] == "EC-K99-001"
    assert result["assertion_type"] == "axiome_explicite"
    assert "test" in result["assertion"].lower()


def test_get_assertion_nonexistent(query, seeded_db):
    """Récupérer une assertion inexistante retourne None."""
    result = query.get_assertion("NOPE-999")
    assert result is None


def test_get_concept_with_relations(query, seeded_db):
    """Récupérer un concept retourne ses assertions et relations."""
    result = query.get_concept("test_concept_a")
    assert result is not None
    assert result["concept_id"] == "test_concept_a"
    assert len(result["assertions"]) >= 1
    assert len(result["relations"]) >= 1


def test_get_concept_nonexistent(query, seeded_db):
    """Un concept inexistant retourne None."""
    result = query.get_concept("concept_fantome")
    assert result is None


def test_get_relations_for_concept(query, seeded_db):
    """Les relations d'un concept sont retrouvées."""
    rels = query.get_relations_for_concept("test_concept_a")
    assert len(rels) >= 1
    assert any(r["relation_type"] == "causal" for r in rels)


def test_traverse_relations(query, seeded_db):
    """La traversée de graphe retourne des noeuds et arêtes."""
    result = query.traverse_relations("test_concept_a", depth=2)
    assert result["root"] == "test_concept_a"
    assert "test_concept_a" in result["nodes"]
    assert len(result["edges"]) >= 1


def test_get_perek_complet(query, seeded_db):
    """Récupérer un perek complet avec les 3 couches."""
    result = query.get_perek_complet("etz_chaim", 1, 99)
    assert result is not None
    assert len(result["assertions"]) == 2
    assert len(result["relations"]) == 1
    assert len(result["principes"]) == 1


def test_get_perek_nonexistent(query, seeded_db):
    """Un perek inexistant retourne None."""
    result = query.get_perek_complet("etz_chaim", 99, 99)
    assert result is None


def test_stats(query, seeded_db):
    """Les statistiques globales sont cohérentes."""
    result = query.stats()
    assert result["global"]["sefarim"] >= 1
    assert result["global"]["assertions"] >= 2
    assert result["global"]["relations"] >= 1
    assert result["global"]["principes"] >= 1
    assert result["global"]["concepts"] >= 2


def test_get_principe(query, seeded_db):
    """Récupérer un principe par ID."""
    result = query.get_principe("PG-K99-001")
    assert result is not None
    assert result["nom"] == "Principe de test"


def test_consult_for_hitbonenut(query, seeded_db):
    """consult_for_hitbonenut retourne une structure valide."""
    mock_vec = [0.0] * 768
    with patch("epistememory.embedding.embed", return_value=mock_vec):
        result = query.consult_for_hitbonenut("Qu'est-ce que le Tzimtzum?")
    assert "principes" in result
    assert "assertions" in result
    assert "concepts_lies" in result
    assert isinstance(result["principes"], list)
    assert isinstance(result["assertions"], list)
    assert isinstance(result["concepts_lies"], list)
