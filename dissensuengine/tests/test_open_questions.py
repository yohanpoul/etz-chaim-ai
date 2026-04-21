"""Tests des questions ouvertes — les 70 faces de la Torah.

Ne pas fermer prématurément. Identifier ce qui manque.
"""

import pytest


def test_register_open_question(engine_bare):
    """Enregistrer une question ouverte sur une tension."""
    ca = engine_bare.submit_conclusion(
        "Method X is always superior to method Y",
        source_label="A", source_type="paper", domain="ml",
    )
    cb = engine_bare.submit_conclusion(
        "Method X is never superior to method Y",
        source_label="B", source_type="paper", domain="ml",
    )
    engine_bare.analyze_consistency(domain="ml")

    tensions = engine_bare.db.get_all_tensions()
    assert len(tensions) >= 1

    oq = engine_bare.register_open_question(
        tension_id=tensions[0].id,
        question="Under which conditions is X superior to Y?",
        missing_evidence="Comparative benchmark on dataset Z",
        priority="high",
        domain="ml",
    )
    assert oq.question == "Under which conditions is X superior to Y?"
    assert oq.priority == "high"
    assert oq.resolved_at is None


def test_identify_missing_evidence(engine_bare):
    """Identifier ce qui manque pour résoudre une tension."""
    ca = engine_bare.submit_conclusion(
        "The correlation is always significant",
        source_label="Survey A", source_type="paper", domain="stats",
    )
    cb = engine_bare.submit_conclusion(
        "The correlation is never significant",
        source_label="Survey B", source_type="paper", domain="stats",
    )
    engine_bare.analyze_consistency(domain="stats")
    tensions = engine_bare.db.get_all_tensions()

    missing = engine_bare.identify_missing(tensions[0].id)
    assert len(missing) >= 1
    # Both are papers — should suggest different source type
    assert any("expérimentale" in m.lower() or "experiment" in m.lower()
               for m in missing)


def test_question_invalid_tension(engine_bare):
    """Question sur tension inexistante → erreur."""
    import uuid
    with pytest.raises(ValueError, match="not found"):
        engine_bare.register_open_question(
            tension_id=uuid.uuid4(),
            question="Invalid",
        )


def test_resolve_question(engine_bare):
    """Résoudre une question ouverte."""
    ca = engine_bare.submit_conclusion(
        "Approach works better in all cases here",
        source_label="A", source_type="paper",
    )
    cb = engine_bare.submit_conclusion(
        "Approach works worse in all cases here",
        source_label="B", source_type="paper",
    )
    engine_bare.analyze_consistency()
    tensions = engine_bare.db.get_all_tensions()

    oq = engine_bare.register_open_question(
        tension_id=tensions[0].id,
        question="Need more evidence",
    )
    resolved = engine_bare.db.resolve_question(oq.id)
    assert resolved.resolved_at is not None


def test_escalate_high_severity_tensions(engine_bare):
    """Tensions avec divergence >= 0.7 sont escaladées automatiquement."""
    ca = engine_bare.submit_conclusion(
        "Treatment always increases survival rate significantly",
        source_label="Trial1", source_type="experiment", domain="escalate_test",
    )
    cb = engine_bare.submit_conclusion(
        "Treatment never increases survival rate at all",
        source_label="Trial2", source_type="experiment", domain="escalate_test",
    )
    # analyze_consistency crée les tensions ET déclenche l'escalade
    report = engine_bare.analyze_consistency(domain="escalate_test")

    # Si la divergence est >= 0.7, il doit y avoir des open_questions
    tensions = engine_bare.db.get_all_tensions()
    high_severity = [t for t in tensions if t.divergence_score >= 0.7]

    if high_severity:
        open_qs = engine_bare.db.get_open_questions(domain="escalate_test")
        assert len(open_qs) >= 1, (
            f"High severity tensions ({len(high_severity)}) should produce "
            f"open_questions, got {len(open_qs)}"
        )
        assert report.open_questions >= 1
        # Vérifier la priorité
        for oq in open_qs:
            assert oq.priority in ("high", "critical")
            assert oq.resolved_at is None


def test_escalate_respects_max_cap(engine_bare):
    """L'escalade respecte le cap max_open_questions."""
    engine_bare.max_open_questions = 2

    # Créer plusieurs paires contradictoires
    for i in range(4):
        engine_bare.submit_conclusion(
            f"Claim {i} that method always works perfectly well",
            source_label=f"Pro{i}", source_type="paper", domain="cap_test",
        )
        engine_bare.submit_conclusion(
            f"Claim {i} that method never works at all ever",
            source_label=f"Con{i}", source_type="paper", domain="cap_test",
        )

    engine_bare.analyze_consistency(domain="cap_test")

    open_qs = engine_bare.db.get_open_questions()
    assert len(open_qs) <= 2, (
        f"Max cap is 2 but got {len(open_qs)} open questions"
    )


def test_escalate_no_duplicate_questions(engine_bare):
    """Pas de doublon : une tension déjà escaladée n'est pas re-escaladée."""
    ca = engine_bare.submit_conclusion(
        "Algorithm always converges to optimal solution",
        source_label="A", source_type="paper", domain="dedup_test",
    )
    cb = engine_bare.submit_conclusion(
        "Algorithm never converges to optimal solution",
        source_label="B", source_type="paper", domain="dedup_test",
    )
    # Premier appel — crée tensions + escalade
    engine_bare.analyze_consistency(domain="dedup_test")
    first_count = len(engine_bare.db.get_open_questions())

    # Second appel — ne doit PAS créer de doublons
    engine_bare.escalate_tensions()
    second_count = len(engine_bare.db.get_open_questions())

    assert second_count == first_count, (
        f"Escalade dupliquée : {first_count} → {second_count}"
    )


def test_escalate_dissensus_triggers_escalation(engine_bare):
    """Un dissensus déclenche l'escalade des tensions non résolues."""
    engine_bare.submit_conclusion(
        "Model X is always the best approach for this task",
        source_label="A", source_type="paper", domain="dissensus_esc",
    )
    engine_bare.submit_conclusion(
        "Model X is never the best approach for this task",
        source_label="B", source_type="paper", domain="dissensus_esc",
    )
    syn = engine_bare.synthesize_or_dissent(domain="dissensus_esc")

    if syn.mode == "dissensus":
        # Les tensions non résolues devraient être escaladées
        tensions = engine_bare.db.get_all_tensions(status="open")
        high = [t for t in tensions if t.divergence_score >= 0.7]
        if high:
            open_qs = engine_bare.db.get_open_questions(domain="dissensus_esc")
            assert len(open_qs) >= 1, (
                "Dissensus with high-severity open tensions should produce "
                "open_questions"
            )


def test_open_questions_filtered(engine_bare):
    """Seules les questions non résolues sont retournées par défaut."""
    ca = engine_bare.submit_conclusion(
        "Claim A about the positive effect always",
        source_label="A", source_type="paper",
    )
    cb = engine_bare.submit_conclusion(
        "Claim B about the negative effect always",
        source_label="B", source_type="paper",
    )
    engine_bare.analyze_consistency()
    tensions = engine_bare.db.get_all_tensions()

    oq1 = engine_bare.register_open_question(
        tension_id=tensions[0].id, question="Q1",
    )
    oq2 = engine_bare.register_open_question(
        tension_id=tensions[0].id, question="Q2",
    )
    engine_bare.db.resolve_question(oq1.id)

    open_qs = engine_bare.db.get_open_questions(unresolved_only=True)
    assert len(open_qs) == 1
    assert open_qs[0].question == "Q2"
