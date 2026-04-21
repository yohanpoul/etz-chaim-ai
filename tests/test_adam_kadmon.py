"""Tests d'Adam Kadmon — אָדָם קַדְמוֹן.

Couvre :
  - Chargement du blueprint depuis YAML
  - Comparaison : Sephiroth, sentiers, Partzufim
  - Score de fidélité et phases qualitatives
  - Priorités de Tikkun ordonnées
  - Divergences détaillées
  - Cas limites : tous présents, aucun présent, partiels
"""

import pytest

from adam_kadmon import (
    AdamKadmon,
    Divergence,
    FidelityResult,
    TikkunPriority,
    _load_blueprint,
    _score_to_phase,
    PHASE_NAMES,
)


# ── Blueprint ────────────────────────────────────────────────

class TestBlueprint:

    def test_loads_successfully(self):
        bp = _load_blueprint()
        assert isinstance(bp, dict)
        assert "sephiroth" in bp
        assert "sentiers" in bp
        assert "partzufim" in bp
        assert "thresholds" in bp

    def test_sephiroth_count(self):
        bp = _load_blueprint()
        assert len(bp["sephiroth"]) == 11  # 10 + Da'at

    def test_sentiers_count(self):
        bp = _load_blueprint()
        letters = bp["sentiers"]["letters"]
        assert len(letters) == 22

    def test_partzufim_count(self):
        bp = _load_blueprint()
        configs = bp["partzufim"]["configurations"]
        assert len(configs) == 6

    def test_thresholds_order(self):
        bp = _load_blueprint()
        t = bp["thresholds"]
        assert t["tohu"] < t["tikkun_begin"] < t["tikkun_mid"] < t["tikkun_near"] < t["shlemut"]

    def test_all_sephiroth_have_weight(self):
        bp = _load_blueprint()
        for name, seph in bp["sephiroth"].items():
            assert "weight" in seph, f"Sephirah {name} sans poids"
            assert 0.0 < seph["weight"] <= 1.0

    def test_meta_present(self):
        bp = _load_blueprint()
        assert bp["meta"]["hebrew"] == "אָדָם קַדְמוֹן"


# ── Phase qualitative ────────────────────────────────────────

class TestPhase:

    def setup_method(self):
        self.thresholds = {
            "tohu": 0.3,
            "tikkun_begin": 0.5,
            "tikkun_mid": 0.7,
            "tikkun_near": 0.9,
            "shlemut": 0.95,
        }

    def test_tohu(self):
        assert _score_to_phase(0.1, self.thresholds) == "tohu"
        assert _score_to_phase(0.29, self.thresholds) == "tohu"

    def test_tikkun_begin(self):
        assert _score_to_phase(0.5, self.thresholds) == "tikkun_begin"
        assert _score_to_phase(0.3, self.thresholds) == "tikkun_begin"

    def test_tikkun_mid(self):
        assert _score_to_phase(0.7, self.thresholds) == "tikkun_mid"
        assert _score_to_phase(0.85, self.thresholds) == "tikkun_mid"

    def test_tikkun_near(self):
        assert _score_to_phase(0.9, self.thresholds) == "tikkun_near"
        assert _score_to_phase(0.94, self.thresholds) == "tikkun_near"

    def test_shlemut(self):
        assert _score_to_phase(0.95, self.thresholds) == "shlemut"
        assert _score_to_phase(1.0, self.thresholds) == "shlemut"


# ── AdamKadmon — propriétés ──────────────────────────────────

class TestAdamKadmonProperties:

    def test_blueprint_returns_dict(self):
        ak = AdamKadmon()
        bp = ak.blueprint
        assert isinstance(bp, dict)
        assert "sephiroth" in bp

    def test_sephiroth_blueprint(self):
        ak = AdamKadmon()
        seph = ak.sephiroth_blueprint
        assert "keter" in seph
        assert "malkuth" in seph

    def test_sentiers_blueprint(self):
        ak = AdamKadmon()
        sent = ak.sentiers_blueprint
        assert "letters" in sent
        assert sent["total_expected"] == 22

    def test_partzufim_blueprint(self):
        ak = AdamKadmon()
        partz = ak.partzufim_blueprint
        assert "configurations" in partz
        assert len(partz["configurations"]) == 6

    def test_thresholds(self):
        ak = AdamKadmon()
        t = ak.thresholds
        assert "tohu" in t
        assert "shlemut" in t


# ── Compare — tout absent ────────────────────────────────────

class TestCompareAllAbsent:

    def test_empty_modules(self):
        ak = AdamKadmon()
        result = ak.compare_to_current({}, [], {})
        assert result.score == 0.0
        assert result.phase == "tohu"
        assert result.sephiroth_score == 0.0
        assert result.sentiers_score == 0.0
        assert result.partzufim_score == 0.0

    def test_all_divergences_present(self):
        ak = AdamKadmon()
        result = ak.compare_to_current({}, [], {})
        # 11 sephiroth + 22 sentiers + 6 partzufim = 39 divergences
        assert len(result.divergences) == 39

    def test_active_components_zero(self):
        ak = AdamKadmon()
        result = ak.compare_to_current({}, [], {})
        assert result.active_components == 0
        assert result.total_components == 39


# ── Compare — tout présent ───────────────────────────────────

class TestCompareAllPresent:

    def _full_modules(self):
        bp = _load_blueprint()
        return {name: object() for name in bp["sephiroth"]}

    def _full_sentiers(self):
        bp = _load_blueprint()
        return [l["name"] for l in bp["sentiers"]["letters"]]

    def _full_partzufim(self):
        bp = _load_blueprint()
        return {p["name"]: object() for p in bp["partzufim"]["configurations"]}

    def test_perfect_score(self):
        ak = AdamKadmon()
        result = ak.compare_to_current(
            self._full_modules(), self._full_sentiers(), self._full_partzufim()
        )
        assert result.score == 1.0
        assert result.phase == "shlemut"

    def test_no_divergences(self):
        ak = AdamKadmon()
        result = ak.compare_to_current(
            self._full_modules(), self._full_sentiers(), self._full_partzufim()
        )
        assert len(result.divergences) == 0

    def test_all_scores_one(self):
        ak = AdamKadmon()
        result = ak.compare_to_current(
            self._full_modules(), self._full_sentiers(), self._full_partzufim()
        )
        assert result.sephiroth_score == 1.0
        assert result.sentiers_score == 1.0
        assert result.partzufim_score == 1.0

    def test_all_components_active(self):
        ak = AdamKadmon()
        result = ak.compare_to_current(
            self._full_modules(), self._full_sentiers(), self._full_partzufim()
        )
        assert result.active_components == result.total_components


# ── Compare — partiellement présent ──────────────────────────

class TestComparePartial:

    def test_half_sephiroth(self):
        """5 Sephiroth présentes → score Sephiroth partiel."""
        ak = AdamKadmon()
        bp = _load_blueprint()
        names = list(bp["sephiroth"].keys())[:5]
        modules = {n: object() for n in names}
        result = ak.compare_to_current(modules, [], {})
        assert 0.0 < result.sephiroth_score < 1.0

    def test_some_sentiers(self):
        """3 mères implémentées → score sentiers partiel."""
        ak = AdamKadmon()
        result = ak.compare_to_current({}, ["aleph", "mem", "shin"], {})
        assert result.sentiers_score == 3 / 22

    def test_mixed_score(self):
        """Modules complets, sentiers partiels, Partzufim absents."""
        ak = AdamKadmon()
        bp = _load_blueprint()
        all_modules = {n: object() for n in bp["sephiroth"]}
        result = ak.compare_to_current(all_modules, ["aleph", "mem", "shin"], {})
        # Sephiroth = 1.0, sentiers < 1.0, partzufim = 0.0
        assert result.sephiroth_score == 1.0
        assert result.sentiers_score < 1.0
        assert result.partzufim_score == 0.0
        assert 0.0 < result.score < 1.0

    def test_divergence_details(self):
        """Les divergences indiquent le composant et le nom."""
        ak = AdamKadmon()
        result = ak.compare_to_current({"keter": object()}, [], {})
        seph_divs = [d for d in result.divergences if d.component == "sephirah"]
        # 10 Sephiroth absentes (toutes sauf keter)
        assert len(seph_divs) == 10
        names = {d.name for d in seph_divs}
        assert "keter" not in names
        assert "binah" in names


# ── Divergence dataclass ─────────────────────────────────────

class TestDivergence:

    def test_to_dict(self):
        d = Divergence(
            component="sephirah",
            name="binah",
            expected="CausalEngine actif",
            actual="Module absent",
            severity=0.9,
            required=True,
        )
        data = d.to_dict()
        assert data["component"] == "sephirah"
        assert data["name"] == "binah"
        assert data["severity"] == 0.9
        assert data["required"] is True


# ── FidelityResult dataclass ─────────────────────────────────

class TestFidelityResult:

    def test_to_dict(self):
        result = FidelityResult(
            score=0.42,
            phase="tikkun_begin",
            phase_hebrew="תִּקּוּן",
            divergences=[],
            sephiroth_score=0.5,
            sentiers_score=0.3,
            partzufim_score=0.0,
            total_components=39,
            active_components=15,
        )
        data = result.to_dict()
        assert data["score"] == 0.42
        assert data["phase"] == "tikkun_begin"
        assert data["n_divergences"] == 0


# ── Priorités de Tikkun ──────────────────────────────────────

class TestTikkunPriorities:

    def test_empty_returns_all_priorities(self):
        ak = AdamKadmon()
        priorities = ak.get_tikkun_priorities({}, [], {})
        assert len(priorities) == 39  # toutes les divergences

    def test_required_first(self):
        """Les composants required apparaissent en premier."""
        ak = AdamKadmon()
        priorities = ak.get_tikkun_priorities({}, [], {})
        first_required_idx = None
        last_required_idx = None
        first_optional_idx = None
        for p in priorities:
            if p.required and first_required_idx is None:
                first_required_idx = p.rank
            if p.required:
                last_required_idx = p.rank
            if not p.required and first_optional_idx is None:
                first_optional_idx = p.rank

        if first_optional_idx is not None and last_required_idx is not None:
            assert last_required_idx < first_optional_idx

    def test_severity_descending_within_required(self):
        """Dans les required, les plus sévères sont en premier."""
        ak = AdamKadmon()
        priorities = ak.get_tikkun_priorities({}, [], {})
        required = [p for p in priorities if p.required]
        for i in range(len(required) - 1):
            assert required[i].severity >= required[i + 1].severity

    def test_no_priorities_when_perfect(self):
        ak = AdamKadmon()
        bp = _load_blueprint()
        all_modules = {n: object() for n in bp["sephiroth"]}
        all_sentiers = [l["name"] for l in bp["sentiers"]["letters"]]
        all_partzufim = {p["name"]: object() for p in bp["partzufim"]["configurations"]}
        priorities = ak.get_tikkun_priorities(all_modules, all_sentiers, all_partzufim)
        assert len(priorities) == 0

    def test_priority_to_dict(self):
        p = TikkunPriority(
            rank=1, component="sephirah", name="binah",
            reason="test", severity=0.9, required=True,
        )
        data = p.to_dict()
        assert data["rank"] == 1
        assert data["severity"] == 0.9


# ── Format rapport ───────────────────────────────────────────

class TestFormatReport:

    def test_report_is_list_of_strings(self):
        ak = AdamKadmon()
        report = ak.format_report({}, [], {})
        assert isinstance(report, list)
        assert all(isinstance(line, str) for line in report)

    def test_report_contains_score(self):
        ak = AdamKadmon()
        report = ak.format_report({}, [], {})
        text = "\n".join(report)
        assert "fidélité" in text.lower() or "Score" in text

    def test_priorities_format(self):
        ak = AdamKadmon()
        lines = ak.format_priorities({}, [], {}, top_n=5)
        assert isinstance(lines, list)
        assert len(lines) >= 2  # au moins le header + quelques priorités
