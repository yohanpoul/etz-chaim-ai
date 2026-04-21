"""Tests BiasDetector — détection des biais récurrents."""

from selfmodel.bias_detector import BiasDetector
from selfmodel.models import SelfState


def _state_with_hod(**overrides):
    """Créer un SelfState avec des stats Hod configurables."""
    hod = {
        "total_domains": 8,
        "evaluated_domains": 5,
        "strong_domains": ["kabbale", "code"],
        "weak_domains": ["chimie"],
        "unknown_domains": ["droit", "musique"],
        "avg_competence": 0.65,
        "avg_brier": 0.15,
        "overconfident_domains": [],
        "underconfident_domains": [],
        "total_queries_routed": 100,
        "total_declined": 10,
        "decline_rate": 0.1,
    }
    hod.update(overrides)
    return SelfState(hod_stats=hod)


class TestOverconfidence:
    """Biais d'overconfidence — Samael."""

    def test_no_overconfidence_when_calibrated(self):
        """Pas de biais si Hod est bien calibré."""
        detector = BiasDetector()
        state = _state_with_hod(avg_brier=0.1, overconfident_domains=[])
        biases = detector._check_overconfidence(state)
        assert biases == []

    def test_overconfident_domains_detected(self):
        """Domaines overconfidents détectés."""
        detector = BiasDetector()
        state = _state_with_hod(overconfident_domains=["physique", "biologie"])
        biases = detector._check_overconfidence(state)
        assert len(biases) == 2
        assert all(b.bias_type == "overconfidence" for b in biases)
        assert biases[0].domain == "physique"
        assert biases[1].domain == "biologie"
        assert all(b.severity == 0.6 for b in biases)

    def test_global_overconfidence_high_brier(self):
        """avg_brier > seuil → overconfidence globale."""
        detector = BiasDetector()
        state = _state_with_hod(avg_brier=0.5)
        biases = detector._check_overconfidence(state)
        global_biases = [b for b in biases if "Global" in b.description]
        assert len(global_biases) == 1
        assert global_biases[0].severity == 0.5

    def test_no_hod_stats_no_overconfidence(self):
        """Pas de Hod → pas de biais."""
        detector = BiasDetector()
        biases = detector._check_overconfidence(SelfState())
        assert biases == []


class TestUnderconfidence:
    """Biais d'underconfidence — le système décline ce qu'il peut faire."""

    def test_underconfident_domains(self):
        """Domaines underconfidents détectés."""
        detector = BiasDetector()
        state = _state_with_hod(underconfident_domains=["code"])
        biases = detector._check_underconfidence(state)
        domain_biases = [b for b in biases if b.domain == "code"]
        assert len(domain_biases) == 1
        assert domain_biases[0].bias_type == "underconfidence"
        assert domain_biases[0].severity == 0.4

    def test_high_decline_rate(self):
        """decline_rate > seuil → underconfidence globale."""
        detector = BiasDetector()
        state = _state_with_hod(decline_rate=0.5)
        biases = detector._check_underconfidence(state)
        decline_biases = [b for b in biases if "decline" in b.description.lower()]
        assert len(decline_biases) == 1
        assert decline_biases[0].severity == 0.5

    def test_no_underconfidence_when_normal(self):
        """Pas de biais si decline_rate normal."""
        detector = BiasDetector()
        state = _state_with_hod(decline_rate=0.1, underconfident_domains=[])
        biases = detector._check_underconfidence(state)
        assert biases == []


class TestBlindSpots:
    """Biais domain_blind_spot — domaines jamais évalués."""

    def test_unknown_domains_detected(self):
        """Domaines inconnus = blind spots."""
        detector = BiasDetector()
        state = _state_with_hod(unknown_domains=["droit", "musique", "architecture"])
        biases = detector._check_blind_spots(state)
        assert len(biases) == 3
        assert all(b.bias_type == "domain_blind_spot" for b in biases)
        domains = {b.domain for b in biases}
        assert domains == {"droit", "musique", "architecture"}

    def test_no_blind_spots_when_all_evaluated(self):
        """Pas de blind spot si tous les domaines sont évalués."""
        detector = BiasDetector()
        state = _state_with_hod(unknown_domains=[])
        biases = detector._check_blind_spots(state)
        assert biases == []


class TestPrematureClosure:
    """Premature closure — Gevurah malade (Golachab)."""

    def test_gevurah_unhealthy(self):
        """Gevurah en état non-healthy → premature_closure."""
        detector = BiasDetector()
        state = SelfState(gevurah_stats={
            "level": "ruach",
            "issues": ["High rejection rate"],
        })
        biases = detector._check_premature_closure(state)
        assert len(biases) == 1
        assert biases[0].bias_type == "premature_closure"
        assert biases[0].severity == 0.5

    def test_gevurah_mamash(self):
        """Gevurah mamash → sévérité maximale."""
        detector = BiasDetector()
        state = SelfState(gevurah_stats={"level": "mamash", "issues": []})
        biases = detector._check_premature_closure(state)
        assert len(biases) == 1
        assert biases[0].severity == 0.9

    def test_gevurah_healthy_no_bias(self):
        """Gevurah healthy → pas de biais."""
        detector = BiasDetector()
        state = SelfState(gevurah_stats={"level": "healthy", "issues": []})
        biases = detector._check_premature_closure(state)
        assert biases == []


class TestScopeCreep:
    """Scope creep — Chesed explore trop (Gamchicoth)."""

    def test_chesed_unhealthy(self):
        """Chesed non-healthy → scope_creep."""
        detector = BiasDetector()
        state = SelfState(chesed_stats={
            "level": "nogah",
            "issues": ["Budget overrun"],
        })
        biases = detector._check_scope_creep(state)
        assert len(biases) == 1
        assert biases[0].bias_type == "scope_creep"
        assert biases[0].severity == 0.3

    def test_chesed_healthy_no_bias(self):
        """Chesed healthy → pas de biais."""
        detector = BiasDetector()
        state = SelfState(chesed_stats={"level": "healthy", "issues": []})
        biases = detector._check_scope_creep(state)
        assert biases == []


class TestConfirmationBias:
    """Confirmation bias — Tiferet ne résout pas les contradictions (Thagirion)."""

    def test_tiferet_anan(self):
        """Tiferet anan → confirmation_bias sévérité 0.7."""
        detector = BiasDetector()
        state = SelfState(tiferet_stats={
            "level": "anan",
            "issues": ["Contradictions suppressed"],
        })
        biases = detector._check_confirmation_bias(state)
        assert len(biases) == 1
        assert biases[0].bias_type == "confirmation_bias"
        assert biases[0].severity == 0.7

    def test_tiferet_mamash(self):
        """Tiferet mamash → confirmation_bias sévérité 0.9."""
        detector = BiasDetector()
        state = SelfState(tiferet_stats={"level": "mamash", "issues": []})
        biases = detector._check_confirmation_bias(state)
        assert len(biases) == 1
        assert biases[0].severity == 0.9

    def test_tiferet_healthy_no_bias(self):
        """Tiferet healthy → pas de biais."""
        detector = BiasDetector()
        state = SelfState(tiferet_stats={"level": "healthy", "issues": []})
        biases = detector._check_confirmation_bias(state)
        assert biases == []

    def test_tiferet_nogah_no_confirmation_bias(self):
        """Tiferet nogah → pas de confirmation_bias (seulement anan/mamash)."""
        detector = BiasDetector()
        state = SelfState(tiferet_stats={"level": "nogah", "issues": []})
        biases = detector._check_confirmation_bias(state)
        assert biases == []


class TestDetectAll:
    """detect() — détection combinée."""

    def test_multiple_biases_from_one_state(self):
        """Plusieurs biais détectés simultanément."""
        detector = BiasDetector()
        state = SelfState(
            hod_stats={
                "overconfident_domains": ["physique"],
                "underconfident_domains": [],
                "unknown_domains": ["droit"],
                "avg_brier": 0.15,
                "decline_rate": 0.1,
            },
            gevurah_stats={"level": "ruach", "issues": []},
            chesed_stats={"level": "healthy", "issues": []},
            tiferet_stats={"level": "healthy", "issues": []},
        )
        biases = detector.detect(state)
        types = {b.bias_type for b in biases}
        assert "overconfidence" in types
        assert "domain_blind_spot" in types
        assert "premature_closure" in types

    def test_empty_state_no_biases(self):
        """État vide → aucun biais."""
        detector = BiasDetector()
        biases = detector.detect(SelfState())
        assert biases == []


class TestDetectFromHistory:
    """detect_from_history — biais récurrents boostés."""

    def test_recurring_bias_severity_boosted(self):
        """Biais présent dans >50% des snapshots → sévérité boostée."""
        detector = BiasDetector()
        state_with_overconf = _state_with_hod(
            overconfident_domains=["physique"],
        )
        # 3 snapshots identiques → frequency = 1.0
        states = [state_with_overconf, state_with_overconf, state_with_overconf]
        biases = detector.detect_from_history(states)
        overconf = [b for b in biases if b.bias_type == "overconfidence"
                    and b.domain == "physique"]
        assert len(overconf) == 1
        # severity = 0.6 * (1 + 1.0) = 1.2 → capped at 1.0
        assert overconf[0].severity == 1.0
        assert overconf[0].evidence["frequency"] == 1.0
        assert overconf[0].evidence["occurrences"] == 3

    def test_empty_history(self):
        """Historique vide → pas de biais."""
        detector = BiasDetector()
        assert detector.detect_from_history([]) == []

    def test_sorted_by_severity_desc(self):
        """Résultats triés par sévérité décroissante."""
        detector = BiasDetector()
        state = SelfState(
            hod_stats={
                "overconfident_domains": ["physique"],
                "underconfident_domains": [],
                "unknown_domains": ["droit"],
                "avg_brier": 0.1,
                "decline_rate": 0.1,
            },
        )
        biases = detector.detect_from_history([state, state])
        for i in range(len(biases) - 1):
            assert biases[i].severity >= biases[i + 1].severity


class TestBiasDB:
    """Persistence des biais en DB."""

    def test_save_and_retrieve_bias(self, db):
        from selfmodel.models import BiasEntry
        bias = BiasEntry(
            bias_type="overconfidence",
            description="test bias",
            evidence={"domain": "physique"},
            severity=0.7,
            domain="physique",
            mitigation="recalibrate",
        )
        saved = db.save_bias(bias)
        assert saved.id is not None
        assert saved.bias_type == "overconfidence"

        active = db.get_active_biases()
        assert len(active) == 1
        assert active[0].domain == "physique"

    def test_deactivate_bias(self, db):
        from selfmodel.models import BiasEntry
        bias = BiasEntry(
            bias_type="overconfidence",
            description="deactivate me",
            severity=0.5,
        )
        saved = db.save_bias(bias)
        db.deactivate_bias(saved.id)
        active = db.get_active_biases()
        assert len(active) == 0
