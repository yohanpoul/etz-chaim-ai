"""Tests du module Kategor — dette technique vivante."""

from malakhim.kategor.debt import DebtReport, get_debt_report, purge_resolved
from malakhim.pekidah.registry import PekidahRegistry


class TestDebtReport:
    def test_empty_report(self):
        reg = PekidahRegistry()
        report = get_debt_report(reg)
        assert report.total_active == 0
        assert report.oldest_unresolved is None

    def test_report_with_failures(self):
        reg = PekidahRegistry()
        reg.register("agent1", ["math"])
        reg.record_failure("agent1", "math", "timeout", "solve x", 0.1)
        reg.record_failure("agent1", "math", "hallucination", "prove theorem", 0.2)
        report = get_debt_report(reg)
        assert report.total_active == 2
        assert report.by_domain["math"] == 2
        assert "timeout" in report.by_error_type
        assert "hallucination" in report.by_error_type

    def test_resolved_not_counted(self):
        reg = PekidahRegistry()
        reg.register("agent1", ["math"])
        f = reg.record_failure("agent1", "math", "timeout", "solve x", 0.1)
        reg.resolve_failure(f.pattern_id, "fixed")
        report = get_debt_report(reg)
        assert report.total_active == 0

    def test_most_frequent(self):
        reg = PekidahRegistry()
        reg.register("agent1", ["math"])
        f1 = reg.record_failure("agent1", "math", "timeout", "solve x", 0.1)
        f2 = reg.record_failure("agent1", "math", "hallucination", "prove theorem", 0.2)
        # Simuler plus d'occurrences sur f2
        f2.occurrences = 5
        report = get_debt_report(reg)
        assert report.most_frequent is not None
        assert report.most_frequent.pattern_id == f2.pattern_id

    def test_dataclass_fields(self):
        reg = PekidahRegistry()
        report = get_debt_report(reg)
        assert isinstance(report, DebtReport)
        assert isinstance(report.by_domain, dict)
        assert isinstance(report.by_error_type, dict)


class TestPurgeResolved:
    def test_purge_removes_resolved(self):
        reg = PekidahRegistry()
        reg.register("agent1", ["math"])
        f = reg.record_failure("agent1", "math", "timeout", "solve x", 0.1)
        reg.resolve_failure(f.pattern_id, "fixed")
        purged = purge_resolved(reg)
        assert purged == 1

    def test_purge_keeps_active(self):
        reg = PekidahRegistry()
        reg.register("agent1", ["math"])
        reg.record_failure("agent1", "math", "timeout", "solve x", 0.1)
        purged = purge_resolved(reg)
        assert purged == 0

    def test_purge_mixed(self):
        reg = PekidahRegistry()
        reg.register("agent1", ["math"])
        f1 = reg.record_failure("agent1", "math", "timeout", "solve x", 0.1)
        reg.record_failure("agent1", "math", "hallucination", "prove theorem", 0.2)
        reg.resolve_failure(f1.pattern_id, "fixed")
        purged = purge_resolved(reg)
        assert purged == 1
        # Le pattern actif est toujours là
        report = get_debt_report(reg)
        assert report.total_active == 1
