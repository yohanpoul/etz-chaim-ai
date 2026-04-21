"""Tests — TikkunScheduler (synthèse proportionnelle aux tensions)."""

import pytest

from dissensuengine.tikkun_scheduler import (
    DomainTohuState,
    TikkunPriority,
    TikkunScheduler,
)


class TestAssessTohuState:
    """assess_tohu_state retourne les bons ratios et priorités."""

    def test_empty_state(self, db):
        scheduler = TikkunScheduler(db)
        state = scheduler.assess_tohu_state()
        assert state == {}

    def test_single_domain_with_tensions(self, engine_bare):
        # Créer des conclusions et une tension explicite dans un domaine
        c1 = engine_bare.submit_conclusion(
            "Position A on topic", "src_a", domain="cosmologie"
        )
        c2 = engine_bare.submit_conclusion(
            "Position B contradicts A completely", "src_b", domain="cosmologie"
        )
        # Créer la tension manuellement (les textes courts ne dépassent pas
        # toujours le seuil de divergence textuelle de 0.3)
        engine_bare.db.create_tension(
            conclusion_a_id=c1.id,
            conclusion_b_id=c2.id,
            tension_type="contradiction",
            divergence_score=0.7,
        )

        scheduler = TikkunScheduler(engine_bare.db)
        state = scheduler.assess_tohu_state()

        assert "cosmologie" in state
        s = state["cosmologie"]
        assert s.tensions_count == 1
        assert s.syntheses_count == 0
        assert isinstance(s.priority, TikkunPriority)

    def test_domain_with_syntheses_no_tensions(self, engine_bare):
        # Créer conclusions, synthétiser, vérifier ratio sain
        c1 = engine_bare.submit_conclusion(
            "Fact alpha about sefirot", "src_1", domain="sefirot"
        )
        c2 = engine_bare.submit_conclusion(
            "Fact alpha about sefirot from other source", "src_2", domain="sefirot"
        )
        engine_bare.synthesize_or_dissent(domain="sefirot")

        scheduler = TikkunScheduler(engine_bare.db)
        state = scheduler.assess_tohu_state()

        if "sefirot" in state:
            s = state["sefirot"]
            assert s.syntheses_count >= 1
            assert not s.needs_tikkun or s.tensions_count > 0

    def test_high_priority_when_ratio_above_10(self, db):
        # Simuler directement via DB : 12 tensions, 1 synthèse
        # Créer 12 conclusions
        conclusions = []
        for i in range(12):
            c = db.create_conclusion(
                content=f"Unique conclusion {i} on topic X with extra text to differentiate",
                source_label=f"src_{i}",
                source_type="human",
                domain="overflow",
                confidence=0.5,
            )
            conclusions.append(c)

        # Créer 11 tensions entre paires consécutives
        for i in range(11):
            db.create_tension(
                conclusion_a_id=conclusions[i].id,
                conclusion_b_id=conclusions[i + 1].id,
                tension_type="contradiction",
                divergence_score=0.7,
            )

        # Créer 1 synthèse
        db.create_synthesis(
            mode="synthesis",
            content="Synthesis attempt",
            sources_used=[conclusions[0].id],
            source_coverage=0.5,
            max_divergence=0.5,
            confidence=0.5,
            domain="overflow",
        )

        scheduler = TikkunScheduler(db)
        state = scheduler.assess_tohu_state()

        assert "overflow" in state
        s = state["overflow"]
        assert s.tensions_count == 11
        assert s.syntheses_count == 1
        assert s.ratio == 11.0
        assert s.priority == TikkunPriority.HIGH
        assert s.needs_tikkun is True


class TestScheduleTikkun:
    """schedule_tikkun trie par priorité."""

    def test_sorts_by_priority_then_ratio(self):
        states = {
            "low_domain": DomainTohuState(
                domain="low_domain", tensions_count=2,
                syntheses_count=1, ratio=2.0,
                needs_tikkun=False, priority=TikkunPriority.LOW,
            ),
            "high_domain": DomainTohuState(
                domain="high_domain", tensions_count=15,
                syntheses_count=1, ratio=15.0,
                needs_tikkun=True, priority=TikkunPriority.HIGH,
            ),
            "medium_domain": DomainTohuState(
                domain="medium_domain", tensions_count=8,
                syntheses_count=1, ratio=8.0,
                needs_tikkun=True, priority=TikkunPriority.MEDIUM,
            ),
        }

        from dissensuengine.db import DissensuEngineDB
        # Use a mock-like approach — TikkunScheduler only needs db for assess
        # but schedule_tikkun accepts pre-computed states
        scheduler = TikkunScheduler.__new__(TikkunScheduler)
        result = scheduler.schedule_tikkun(states)

        assert result == ["high_domain", "medium_domain", "low_domain"]

    def test_empty_returns_empty(self):
        scheduler = TikkunScheduler.__new__(TikkunScheduler)
        result = scheduler.schedule_tikkun({})
        assert result == []


class TestShouldSynthesizeNow:
    """should_synthesize_now déclenche au bon seuil."""

    def test_below_threshold_returns_false(self, db):
        scheduler = TikkunScheduler(db)
        assert scheduler.should_synthesize_now("empty_domain") is False

    def test_above_threshold_returns_true(self, db):
        # Créer 12 conclusions + 11 tensions dans un domaine
        conclusions = []
        for i in range(12):
            c = db.create_conclusion(
                content=f"Statement {i} about partzufim with detail {i*7}",
                source_label=f"s_{i}",
                source_type="human",
                domain="partzufim",
                confidence=0.5,
            )
            conclusions.append(c)

        for i in range(11):
            db.create_tension(
                conclusion_a_id=conclusions[i].id,
                conclusion_b_id=conclusions[i + 1].id,
                tension_type="nuance",
                divergence_score=0.5,
            )

        scheduler = TikkunScheduler(db)
        assert scheduler.should_synthesize_now("partzufim") is True

    def test_new_tension_count_adds_to_existing(self, db):
        # 4 tensions existantes + 0 = 4 < 10, ratio 4/0 = 4.0 < 5.0 → False
        # 4 tensions existantes + 7 nouvelles = 11 > seuil de 10 → True
        conclusions = []
        for i in range(5):
            c = db.create_conclusion(
                content=f"Claim {i} about olamot with specific detail {i}",
                source_label=f"cl_{i}",
                source_type="human",
                domain="olamot",
                confidence=0.5,
            )
            conclusions.append(c)

        for i in range(4):
            db.create_tension(
                conclusion_a_id=conclusions[i].id,
                conclusion_b_id=conclusions[i + 1].id,
                tension_type="framing_difference",
                divergence_score=0.4,
            )

        scheduler = TikkunScheduler(db)
        # 4 existing + 7 new = 11 > 10
        assert scheduler.should_synthesize_now("olamot", new_tension_count=7) is True
        # 4 existing + 0 new = 4 < 10, ratio 4.0 < 5.0
        assert scheduler.should_synthesize_now("olamot", new_tension_count=0) is False

    def test_ratio_trigger_without_reaching_count(self, db):
        # 4 tensions, 0 synthèses → ratio = 4.0 < 5.0 → False
        # But with ratio_max=3 → True
        conclusions = []
        for i in range(5):
            c = db.create_conclusion(
                content=f"View {i} about tzimtzum with elaboration {i}",
                source_label=f"v_{i}",
                source_type="model",
                domain="tzimtzum",
                confidence=0.6,
            )
            conclusions.append(c)

        for i in range(4):
            db.create_tension(
                conclusion_a_id=conclusions[i].id,
                conclusion_b_id=conclusions[i + 1].id,
                tension_type="scope_conflict",
                divergence_score=0.6,
            )

        scheduler = TikkunScheduler(db, ratio_max=3.0)
        assert scheduler.should_synthesize_now("tzimtzum") is True

        scheduler_lenient = TikkunScheduler(db, ratio_max=10.0)
        assert scheduler_lenient.should_synthesize_now("tzimtzum") is False
