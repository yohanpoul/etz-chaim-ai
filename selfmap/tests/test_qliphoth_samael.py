"""Tests Qliphoth Samael — les 4 niveaux de défaillance de Hod.

Samael = le Poison de Dieu = confiance sur des domaines d'incompétence.
"""

import pytest

from selfmap.models import DomainScore


def test_samael_nogah_hesitation(sm):
    """Nogah: le système répond sur un domaine faible mais ajoute un warning.

    Score entre decline_threshold et 0.5 → répond mais devrait signaler.
    """
    sm.db.upsert_competence(DomainScore(
        domain="history", model_id="test-model",
        score=0.35, brier_score=0.3, n_evals=10,
    ))

    # Should still answer (above decline threshold of 0.3)
    decision = sm.route("When did the Roman Empire fall?")
    assert not decision.did_decline
    # But the score is low enough to warrant caution
    assert decision.competence_score < 0.5


def test_samael_ruach_misrouting(sm):
    """Ruach: la requête est routée vers le mauvais modèle.

    Si un meilleur modèle existe pour le domaine, on doit le choisir.
    """
    sm.db.upsert_competence(DomainScore(
        domain="math", model_id="test-model",
        score=0.3, brier_score=0.3, n_evals=5,
    ))
    sm.db.upsert_competence(DomainScore(
        domain="math", model_id="math-specialist",
        score=0.95, brier_score=0.02, n_evals=20,
    ))

    decision = sm.route("Prove that sqrt(2) is irrational")
    # Must route to the specialist, not the weak default
    assert decision.routed_to == "math-specialist"


def test_samael_anan_overconfidence(sm):
    """Anan: haute confiance affichée sur domaine incompétent.

    Le système NE DOIT PAS répondre si la compétence est < seuil.
    """
    sm.db.upsert_competence(DomainScore(
        domain="medicine", model_id="test-model",
        score=0.1, brier_score=0.5, n_evals=20,
    ))

    decision = sm.route("Should I take aspirin for my chest pain?")
    assert decision.did_decline
    assert decision.decline_reason is not None


def test_samael_mamash_inverted_map(sm):
    """Mamash: la carte est entièrement fausse.

    Vérification d'intégrité : les scores doivent être cohérents.
    Un modèle ne peut pas avoir score=0.95 avec brier_score=0.8.
    """
    # A well-calibrated model has low brier when score is high
    sm.db.upsert_competence(DomainScore(
        domain="python", model_id="test-model",
        score=0.9, brier_score=0.05, n_evals=50,
    ))
    sm.db.upsert_competence(DomainScore(
        domain="medicine", model_id="test-model",
        score=0.2, brier_score=0.4, n_evals=50,
    ))

    desc = sm.describe_self()
    # SelfMap must distinguish strong from weak
    assert "python" in desc.strong_domains
    assert "medicine" in desc.weak_domains
    # And never confuse them
    assert "medicine" not in desc.strong_domains
    assert "python" not in desc.weak_domains


def test_samael_decline_below_threshold(sm):
    """Le refus se déclenche quand le domaine détecté est sous le seuil."""
    # route() détecte le domaine automatiquement — on met le domaine "general" bas
    sm.db.upsert_competence(DomainScore(
        domain="general", model_id="test-model",
        score=0.05, brier_score=0.6, n_evals=15,
    ))

    decision = sm.route("Tell me about quantum physics")
    # With general domain score at 0.05, below decline_threshold of 0.3
    assert decision.did_decline
    assert decision.decline_reason is not None


def test_samael_no_competence_data(sm):
    """Domaine inconnu : pas de données de compétence → score par défaut."""
    decision = sm.route("Question about obscure topic with no data")
    # Without any competence data, uses default score
    assert decision.competence_score is not None


def test_samael_high_brier_score_warning(sm):
    """Brier élevé : score haut mais mal calibré → le système route quand même."""
    sm.db.upsert_competence(DomainScore(
        domain="general", model_id="test-model",
        score=0.7, brier_score=0.45, n_evals=30,
    ))

    decision = sm.route("What will happen to oil prices?")
    assert decision.competence_score is not None
    assert not decision.did_decline  # Score above threshold


def test_samael_routing_with_domain_hint(sm):
    """Routage avec domaine explicite : le meilleur modèle gagne."""
    sm.db.upsert_competence(DomainScore(
        domain="math", model_id="test-model",
        score=0.4, brier_score=0.25, n_evals=10,
    ))
    sm.db.upsert_competence(DomainScore(
        domain="math", model_id="math-specialist",
        score=0.98, brier_score=0.01, n_evals=100,
    ))

    # Le test existant test_samael_ruach_misrouting vérifie déjà ce cas
    decision = sm.route("Prove that sqrt(2) is irrational")
    assert decision.routed_to == "math-specialist"


def test_samael_describe_empty(sm):
    """Carte vide : describe_self sans données ne crash pas."""
    desc = sm.describe_self()
    assert len(desc.strong_domains) == 0
    assert len(desc.weak_domains) == 0


def test_samael_score_update_reflected(sm):
    """Mise à jour de score : la compétence évolue après réévaluation."""
    sm.db.upsert_competence(DomainScore(
        domain="writing", model_id="test-model",
        score=0.3, brier_score=0.4, n_evals=5,
    ))

    # Initially weak
    desc1 = sm.describe_self()
    assert "writing" in desc1.weak_domains

    # Improve
    sm.db.upsert_competence(DomainScore(
        domain="writing", model_id="test-model",
        score=0.9, brier_score=0.05, n_evals=50,
    ))

    desc2 = sm.describe_self()
    assert "writing" in desc2.strong_domains
