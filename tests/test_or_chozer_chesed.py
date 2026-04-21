"""Régression F-S1-002 — Or Chozer étape ↑⑥ Chesed : pistes d'exploration.

Bug : `ExplorationResult.novel_connections` est une @property int (pas une liste).
Le code traitait la valeur comme une liste (len(), for...in).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from explorationengine.models import Connection, ExplorationResult


def _make_explore_result(n_connections: int, novelty: float = 0.5) -> ExplorationResult:
    """Construit un ExplorationResult réaliste."""
    conns = [
        Connection(
            concept_a=f"claim A{i}",
            domain_a="ml",
            concept_b=f"claim B{i}",
            domain_b="kabbale",
            connection_type="analogy",
            description=f"Connexion {i}",
            novelty_score=novelty,
            relevance_score=0.7,
        )
        for i in range(n_connections)
    ]
    return ExplorationResult(
        connections=conns,
        status="completed",
        domains_explored=["ml", "kabbale"],
    )


def test_novel_connections_is_int_not_list():
    """novel_connections est un compteur (int), pas une liste."""
    result = _make_explore_result(3, novelty=0.5)
    assert isinstance(result.novel_connections, int)
    assert result.novel_connections == 3


def test_chesed_chozer_step_zero_novel_no_crash(monkeypatch, capsys):
    """F-S1-002: étape ↑⑥ Chesed ne doit pas crasher quand novel_connections est un int.

    Reproduction du contexte observé dans ohr_yashar.py: 0 novel_connection,
    domains_explored non vide. Avant fix: TypeError 'int' has no len().
    """
    import ohr_yashar

    # Mock le chesed module avec un explore() qui retourne 0 novel connections
    chesed = MagicMock()
    explore_result = _make_explore_result(0)
    chesed.explore.return_value = explore_result

    tree = {"chesed": chesed, "gematria": None}

    # Minimal ctx — route_decision qui expose detected_domain + did_decline=False
    route_decision = MagicMock()
    route_decision.detected_domain = "general"
    route_decision.did_decline = False

    ctx = {
        "route_decision": route_decision,
        "response_confidence": 0.5,
        "response": "",
        "intent": {"type": "factuel"},
        "_sentier_router": None,
    }

    chozer: list[str] = []

    # Appeler uniquement la partie Chesed (inline minimal reproduction)
    # — l'objectif est de vérifier qu'aucun len(int) ne se produit
    from ohr_yashar import _ascend_gadlut

    # On stubbe les autres étapes en court-circuitant _world_emit, le reste
    # étant protégé par try/except dans la fonction.
    monkeypatch.setattr(
        "ohr_yashar._sr", lambda *a, **k: None, raising=False,
    )

    _ascend_gadlut(tree, "question test", ctx, chozer)

    # L'important : aucune ligne "Erreur: object of type 'int' has no len()"
    chesed_errors = [line for line in chozer
                     if "Chesed" in line and "Erreur" in line and "len()" in line]
    assert not chesed_errors, f"Chesed a crashé avec len(int): {chesed_errors}"


def test_chesed_chozer_step_with_novel_no_crash():
    """Version avec plusieurs novel connections — doit produire le summary sans crash."""
    chesed = MagicMock()
    explore_result = _make_explore_result(3, novelty=0.6)
    chesed.explore.return_value = explore_result

    tree = {"chesed": chesed, "gematria": None}

    route_decision = MagicMock()
    route_decision.detected_domain = "general"
    route_decision.did_decline = False

    ctx = {
        "route_decision": route_decision,
        "response_confidence": 0.5,
        "response": "",
        "intent": {"type": "factuel"},
        "_sentier_router": None,
    }

    chozer: list[str] = []

    from ohr_yashar import _ascend_gadlut
    _ascend_gadlut(tree, "question test", ctx, chozer)

    chesed_errors = [line for line in chozer
                     if "Chesed" in line and "Erreur" in line]
    assert not chesed_errors, f"Chesed a crashé: {chesed_errors}"
