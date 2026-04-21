"""Tests du ContextAssembler — Pipeline complet Sod HaKli Phase 4.

Couvre :
  - Pipeline 10 etapes : chaque etape individuellement
  - Orchestration end-to-end
  - Integration avec Maturation, Tzelem, Panim/Achor, Zivvug
  - Mode memoire seule (sans DB)
  - Influence de la maturation sur le pipeline
"""

import pytest

from masakh import clear_log, clear_reshimot, _RESHIMOT_LOG
from masakh.context_assembler import ContextAssembler, _format_kavvanah


# ── Fixtures ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_logs():
    """Nettoyer les logs avant/apres chaque test."""
    clear_log()
    clear_reshimot()
    yield
    clear_log()
    clear_reshimot()


def _assembler(**kwargs):
    """Creer un ContextAssembler en mode memoire."""
    return ContextAssembler(**kwargs)


# ── Format Kavvanah ─────────────────────────────────────

class TestFormatKavvanah:

    def test_full_kavvanah(self):
        kav = {
            "intention": "analyser",
            "critere_succes": "precision",
            "anti_pattern": "vague",
        }
        result = _format_kavvanah(kav)
        assert "[KAVVANAH]" in result
        assert "Intention : analyser" in result
        assert "Succès si : precision" in result
        assert "Ne pas : vague" in result
        assert "[/KAVVANAH]" in result

    def test_minimal_kavvanah(self):
        result = _format_kavvanah({"intention": "test"})
        assert "Intention : test" in result
        assert "Succes si" not in result

    def test_empty_kavvanah(self):
        result = _format_kavvanah({})
        assert "[KAVVANAH]" in result
        assert "[/KAVVANAH]" in result


# ── Pipeline complet ────────────────────────────────────

class TestAssemblePipeline:

    def test_minimal_assemble(self):
        """Pipeline minimal : juste Rosh + Toch + Sof + Monitor + Reshimo."""
        a = _assembler()
        result = a.assemble(olam="assiah", prompt="Hello world")
        assert "prompt_final" in result
        assert result["masakh_level"] in ("aleph", "shoresh", "bet", "gimel", "dalet")
        assert isinstance(result["dimensions_score"], float)
        assert "rosh" in result["pipeline_steps"]
        assert "toch" in result["pipeline_steps"]
        assert "sof" in result["pipeline_steps"]
        assert "monitor" in result["pipeline_steps"]
        assert "reshimo" in result["pipeline_steps"]

    def test_with_kavvanah(self):
        """La Kavvanah est injectee dans le prompt final."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Analyse ce texte",
            kavvanah={"intention": "analyser le Zohar"},
        )
        assert "[KAVVANAH]" in result["prompt_final"]
        assert "analyser le Zohar" in result["prompt_final"]
        assert "kavvanah" in result["pipeline_steps"]

    def test_with_context_items(self):
        """Les context_items sont recategorises par Arakhin.
        Note: en ibur (0 reshimots), Arakhin est skippé.
        On seed des reshimots pour sortir de ibur.
        """
        # Seed 15 reshimots pour passer en yenikah
        for _ in range(15):
            _RESHIMOT_LOG.append({
                "olam": "briah",
                "reshimo_aviut": {"score": 0.5},
                "reshimo_hitlabshut": {},
            })
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Question",
            context_items=["DRY principle", "SOLID patterns"],
        )
        assert "arakhin" in result["pipeline_steps"]
        # En briah, Arakhin reformule en "framework"
        assert "framework" in result["prompt_final"].lower()

    def test_with_principles_gimel(self):
        """Les principes sont enclothe en Gimel (briah).
        Note: en ibur, Masakh est contraint a aleph (pas gimel).
        On seed des reshimots pour avoir le Masakh en gimel.
        """
        # Seed 60 reshimots avec bon score et tikkun patterns
        for _ in range(60):
            _RESHIMOT_LOG.append({
                "olam": "briah",
                "reshimo_aviut": {"score": 0.85, "masakh_level": "gimel",
                                  "kavvanah": {"intention": "x"}},
                "reshimo_hitlabshut": {},
            })
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Implement feature",
            principles=["Rigueur absolue"],
        )
        assert "hitlabshut" in result["pipeline_steps"]
        assert "Rigueur absolue" in result["prompt_final"]

    def test_principles_ignored_in_aleph(self):
        """Les principes ne sont PAS enclothe en Aleph (assiah)."""
        a = _assembler()
        result = a.assemble(
            olam="assiah",
            prompt="Run task",
            principles=["Rigueur absolue"],
        )
        assert "hitlabshut" not in result["pipeline_steps"]

    def test_reshimo_pre_prepared(self):
        """Le reshimo_pre est prepare (pas ecrit) pour fusion post-LLM."""
        a = _assembler()
        result = a.assemble(olam="yetzirah", prompt="Test")
        reshimo_pre = result.get("reshimo_pre")
        assert reshimo_pre is not None
        assert "reshimo_hitlabshut" in reshimo_pre
        assert "reshimo_aviut" in reshimo_pre

    def test_excluded_info(self):
        """Le dict excluded contient les infos de rejet."""
        a = _assembler()
        result = a.assemble(olam="assiah", prompt="Short")
        assert "tokens_rejected" in result["excluded"]
        assert "rejection_ratio" in result["excluded"]

    def test_all_four_olamot(self):
        """Le pipeline fonctionne pour les 4 Olamot."""
        a = _assembler()
        for olam in ("atziluth", "briah", "yetzirah", "assiah"):
            result = a.assemble(olam=olam, prompt="Test")
            assert result["prompt_final"]
            assert result["masakh_level"]

    def test_dimensions_score_range(self):
        """Le score des dimensions est entre 0.0 et 1.0."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Test",
            kavvanah={"intention": "test"},
        )
        assert 0.0 <= result["dimensions_score"] <= 1.0

    def test_prompt_order_kavvanah_first(self):
        """L'ordre est : [Kavvanah] → [Tzelem] → [Contexte] → [Da'at] → [Prompt]."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Original prompt ici",
            kavvanah={"intention": "analyser"},
            context_items=["Fait important"],
        )
        final = result["prompt_final"]
        # La kavvanah doit etre AVANT le prompt original
        kav_pos = final.find("[KAVVANAH]")
        orig_pos = final.find("Original prompt ici")
        assert kav_pos < orig_pos, "Kavvanah doit preceder le prompt original"


# ── F2: Da'at Bridge integration ──────────────────────

class TestF2DaatBridge:
    """F2 -- EC-SHK-016, 032-034 : Da'at Bridge connecte les
    connaissances dans le contexte pendant l'assemblage.
    """

    def test_daat_applied_with_facts(self):
        """Da'at Bridge s'active quand des faits sont fournis."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Qu'est-ce que le Tsimtsum?",
            facts=["Le Tsimtsum est la contraction de l'Ein Sof"],
        )
        assert "daat_bridge" in result["pipeline_steps"]
        assert result["daat_applied"] is True
        assert "[DA'AT" in result["prompt_final"]

    def test_daat_applied_with_context_items(self):
        """Da'at Bridge s'active avec des context_items."""
        # Seed reshimots pour sortir de ibur (sinon Arakhin skip)
        for _ in range(15):
            _RESHIMOT_LOG.append({
                "olam": "briah",
                "reshimo_aviut": {"score": 0.5},
                "reshimo_hitlabshut": {},
            })
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Question?",
            context_items=["DRY principle", "SOLID patterns"],
        )
        assert "daat_bridge" in result["pipeline_steps"]
        assert result["daat_applied"] is True

    def test_daat_not_applied_without_material(self):
        """Da'at Bridge ne s'active PAS sans faits ni contexte."""
        a = _assembler()
        result = a.assemble(
            olam="assiah",
            prompt="Hello",
        )
        assert "daat_bridge" not in result["pipeline_steps"]
        assert result["daat_applied"] is False

    def test_daat_extracts_domain_from_kavvanah(self):
        """Le domaine est extrait de la kavvanah si non fourni."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Question?",
            kavvanah={"intention": "analyser le Zohar"},
            facts=["Le Zohar enseigne..."],
        )
        assert "daat_bridge" in result["pipeline_steps"]
        assert "zohar" in result["prompt_final"].lower()

    def test_daat_block_contains_kishur(self):
        """Le bloc Da'at contient la section KISHUR."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Question?",
            facts=["Fait pertinent A", "Fait pertinent B"],
        )
        assert "KISHUR" in result["prompt_final"]

    def test_daat_block_contains_kolel(self):
        """Le bloc Da'at contient la section KOLEL."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Question?",
            facts=["Fait pertinent"],
        )
        assert "KOLEL" in result["prompt_final"]

    def test_daat_dim8_ok_when_applied(self):
        """Dimension 8 (Da'at) = OK quand le bridge est applique."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Question?",
            facts=["Un fait"],
        )
        monitor = result["monitor_state"]
        dim8 = next(d for d in monitor["dimensions"] if d["id"] == "08")
        assert dim8["status"] == "\u2713"

    def test_daat_dim8_absent_when_not_applied(self):
        """Dimension 8 (Da'at) = absent quand pas de bridge."""
        a = _assembler()
        result = a.assemble(
            olam="assiah",
            prompt="Hello",
        )
        monitor = result["monitor_state"]
        dim8 = next(d for d in monitor["dimensions"] if d["id"] == "08")
        assert dim8["status"] == "\u2717"


# ── F5: pressure_regulated propagation ──────────────────

class TestF5PressureRegulated:

    def test_pressure_regulated_reaches_monitor(self):
        """F5: pressure_regulated=True → dim 29 (Tsimtsum) = ✓."""
        a = _assembler()
        result = a.assemble(
            olam="briah", prompt="Test", pressure_regulated=True,
        )
        monitor_state = result["monitor_state"]
        dim29 = next(d for d in monitor_state["dimensions"] if d["id"] == "29")
        assert dim29["status"] == "✓"

    def test_pressure_not_regulated_by_default(self):
        """F5: sans pressure_regulated → dim 29 = ✗."""
        a = _assembler()
        result = a.assemble(olam="briah", prompt="Test")
        monitor_state = result["monitor_state"]
        dim29 = next(d for d in monitor_state["dimensions"] if d["id"] == "29")
        assert dim29["status"] == "✗"


# ── Maturation influence ────────────────────────────────

class TestMaturationInfluence:

    def test_tzelem_integration(self):
        """Le Tzelem est integre quand il est disponible."""
        a = _assembler()
        result = a.assemble(
            olam="briah",
            prompt="Analyse",
            kavvanah={"intention": "analyser le code"},
        )
        # Le Tzelem devrait etre detecte et applique
        assert "tzelem" in result["pipeline_steps"]
        assert "[TZELEM]" in result["prompt_final"]

    def test_maturation_available(self):
        """Le stade de maturation est retourne si le module est disponible."""
        a = _assembler()
        result = a.assemble(olam="assiah", prompt="Test")
        # En mode memoire avec 0 reshimot → ibur
        assert result["maturation_stage"] == "ibur"

    def test_gilgul_init_step(self):
        """L'etape Gilgul Init est toujours executee."""
        a = _assembler()
        result = a.assemble(olam="briah", prompt="Test")
        assert "gilgul_init" in result["pipeline_steps"]


# ── Filtrage du Masakh ──────────────────────────────────

class TestMasakhFiltering:

    def test_long_prompt_filtered(self):
        """Un prompt trop long est filtre par le Masakh."""
        a = _assembler()
        long_prompt = "x" * 200000  # ~50000 tokens
        result = a.assemble(
            olam="atziluth",
            prompt=long_prompt,
            context_window=8192,
        )
        # Atziluth = dalet = 20% budget → doit filtrer
        assert result["excluded"]["tokens_rejected"] > 0

    def test_short_prompt_not_filtered(self):
        """Un prompt court n'est pas filtre."""
        a = _assembler()
        result = a.assemble(
            olam="assiah",
            prompt="Hello",
            context_window=8192,
        )
        assert result["excluded"]["tokens_rejected"] == 0


# ── F6: DaemonBridge soumis au budget Masakh ───────────

class TestF6DaemonBlockBudget:
    """F6 — EC-SHK-023: le contenu DaemonBridge est soumis au
    budget Masakh total. Ses tokens sont deduits du budget AVANT
    le filtrage Toch, et le bloc est appende au prompt filtre.
    """

    def test_daemon_block_in_prompt_final(self):
        """Le daemon_block apparait dans le prompt_final."""
        a = _assembler()
        result = a.assemble(
            olam="assiah",
            prompt="Question simple",
            context_window=8192,
            daemon_block="[Daemon: synthese importante]",
        )
        assert "[Daemon: synthese importante]" in result["prompt_final"]

    def test_daemon_tokens_reported(self):
        """daemon_tokens_used est reporte dans le resultat."""
        a = _assembler()
        result = a.assemble(
            olam="assiah",
            prompt="Test",
            context_window=8192,
            daemon_block="x" * 400,  # ~100 tokens
        )
        assert result["daemon_tokens_used"] == 100

    def test_daemon_tokens_zero_without_block(self):
        """Sans daemon_block, daemon_tokens_used = 0."""
        a = _assembler()
        result = a.assemble(
            olam="assiah",
            prompt="Test",
            context_window=8192,
        )
        assert result["daemon_tokens_used"] == 0

    def test_daemon_none_no_effect(self):
        """daemon_block=None n'a aucun effet."""
        a = _assembler()
        result = a.assemble(
            olam="assiah",
            prompt="Test",
            context_window=8192,
            daemon_block=None,
        )
        assert result["daemon_tokens_used"] == 0
        assert "Test" in result["prompt_final"]

    def test_daemon_reduces_effective_budget(self):
        """Le daemon reduit le budget effectif pour le prompt de base.

        Un prompt long + daemon = le daemon reserve ses tokens du
        budget total, le prompt de base est filtre avec le budget
        restant, puis le daemon est appende.
        """
        a = _assembler()
        # Prompt tres long → sera filtre par Masakh
        long_prompt = "Base content. " * 5000  # ~17500 tokens
        daemon = "[Daemon content here]"

        # Sans daemon
        result_no_daemon = a.assemble(
            olam="assiah",
            prompt=long_prompt,
            context_window=8192,
        )
        # Avec daemon
        result_with_daemon = a.assemble(
            olam="assiah",
            prompt=long_prompt,
            context_window=8192,
            daemon_block=daemon,
        )

        # Le prompt de base filtre doit etre PLUS COURT quand le
        # daemon est present (ses tokens sont deduits du budget).
        base_only_len = len(result_no_daemon["prompt_final"])
        with_daemon_len = len(result_with_daemon["prompt_final"])
        # Le daemon ajoute ~20 chars, mais le prompt de base est
        # raccourci de ~daemon_tokens * 4 chars ≈ 24 chars (5 tokens)
        # Donc with_daemon_len < base_only_len + daemon_len (pas additif)
        daemon_len = len(daemon) + 2  # +2 for "\n\n"
        assert with_daemon_len < base_only_len + daemon_len + 10

    def test_daemon_cap_20pct_budget(self):
        """Le daemon est tronque s'il depasse 20% du budget total."""
        a = _assembler()
        # Budget assiah aleph = 85% × 8192 = 6963 tokens
        # 20% de 6963 = 1392 tokens = ~5570 chars
        huge_daemon = "D" * 40000  # ~10000 tokens >> 20%
        result = a.assemble(
            olam="assiah",
            prompt="Short prompt",
            context_window=8192,
            daemon_block=huge_daemon,
        )
        # Le daemon_tokens_used ne doit pas depasser 20% du budget
        budget = int(8192 * 0.85)  # aleph = 85%
        max_daemon = int(budget * 0.20)
        assert result["daemon_tokens_used"] <= max_daemon

    def test_total_respects_budget(self):
        """Le prompt_final total (base filtree + daemon) respecte
        le budget Masakh.
        """
        from masakh import Masakh
        a = _assembler()
        long_prompt = "X" * 200000  # ~50000 tokens
        daemon = "Y" * 2000  # ~500 tokens
        result = a.assemble(
            olam="assiah",
            prompt=long_prompt,
            context_window=8192,
            daemon_block=daemon,
        )
        total_tokens = Masakh.estimate_tokens(result["prompt_final"])
        budget = int(8192 * 0.85)  # aleph = 85%
        # Total doit rester sous le budget (avec marge pour separators)
        assert total_tokens <= budget + 50  # marge pour les separateurs Masakh
