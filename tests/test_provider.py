"""Tests pour le système de profils LLM multi-provider.

Vérifie :
- Chargement des profils depuis config.yaml
- Dispatch claude_code vs ollama dans ollama_generate()
- claude_code_generate() avec mock subprocess
- get_provider(), get_model(), get_active_profile()
- Basculement entre profils
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ─── Fixtures ────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_olamot_config():
    """Reset le cache config entre chaque test."""
    import olamot
    olamot._config = None
    yield
    olamot._config = None


# ─── Tests profil actif ─────────────────────────────────────

class TestActiveProfile:
    def test_get_active_profile_name(self):
        import olamot
        name = olamot.get_active_profile_name()
        # Profiles listed in config.yaml (v0.2.1 expanded set).
        assert name in (
            "local_only", "anthropic_full", "openai_full", "gemini_full",
            "bedrock_full", "hybrid", "claude_max",
            # Legacy names kept for back-compat reading of older config.yaml.
            "local_only",
        )

    def test_get_active_profile_returns_dict(self):
        import olamot
        profile = olamot.get_active_profile()
        assert isinstance(profile, dict)
        assert "olamot" in profile
        assert "embedding" in profile

    def test_get_active_profile_has_all_olamot(self):
        import olamot
        profile = olamot.get_active_profile()
        olamot_cfg = profile["olamot"]
        for olam in ["atziluth", "briah", "yetzirah", "assiah"]:
            assert olam in olamot_cfg, f"Olam {olam} manquant dans le profil"

    def test_unknown_profile_raises(self):
        import olamot
        import yaml
        cfg = olamot._load_config()
        orig = cfg.get("active_profile")
        try:
            cfg["active_profile"] = "nonexistent_profile"
            with pytest.raises(KeyError, match="Profil inconnu"):
                olamot.get_active_profile()
        finally:
            cfg["active_profile"] = orig


# ─── Tests get_provider / get_model ─────────────────────────

class TestProviderModel:
    def test_get_provider_returns_string(self):
        import olamot
        prov = olamot.get_provider("briah")
        assert prov in ("ollama", "claude_code", "anthropic")

    def test_get_model_returns_string(self):
        import olamot
        model = olamot.get_model("briah")
        assert isinstance(model, str)
        assert len(model) > 0

    def test_get_provider_unknown_olam_raises(self):
        import olamot
        with pytest.raises(KeyError):
            olamot.get_provider("sitra_achra")

    def test_get_model_unknown_olam_raises(self):
        import olamot
        with pytest.raises(KeyError):
            olamot.get_model("sitra_achra")

    def test_get_timeout(self):
        import olamot
        t = olamot.get_timeout("briah")
        assert isinstance(t, int)
        assert t > 0

    def test_get_think(self):
        import olamot
        # briah devrait avoir think dans la plupart des profils
        think = olamot.get_think("briah")
        assert isinstance(think, bool)

    def test_get_context_window(self):
        import olamot
        ctx = olamot.get_context_window("briah")
        assert isinstance(ctx, int)
        assert ctx > 0


# ─── Tests local_only profile ──────────────────────────────

class TestLocalOnlyProfile:
    """Vérifie que le profil local_only est 100% local (aucune clé API requise)."""

    def test_local_only_has_correct_providers(self):
        import olamot
        cfg = olamot._load_config()
        profile = cfg["profiles"]["local_only"]
        olamot_cfg = profile["olamot"]

        # local_only : all four olamot on Ollama, no cloud dependency.
        assert olamot_cfg["atziluth"]["provider"] == "ollama"
        assert olamot_cfg["briah"]["provider"] == "ollama"
        assert olamot_cfg["yetzirah"]["provider"] == "ollama"
        assert olamot_cfg["assiah"]["provider"] == "ollama"

    def test_local_only_has_qwen_models(self):
        import olamot
        cfg = olamot._load_config()
        profile = cfg["profiles"]["local_only"]
        olamot_cfg = profile["olamot"]

        assert olamot_cfg["briah"]["model"] == "qwen3.5:9b"
        assert olamot_cfg["yetzirah"]["model"] == "qwen3.5:9b"
        assert olamot_cfg["assiah"]["model"] == "qwen3.5:9b"

    def test_local_only_briah_has_think(self):
        import olamot
        cfg = olamot._load_config()
        profile = cfg["profiles"]["local_only"]
        assert profile["olamot"]["briah"]["think"] is True


# ─── Tests claude_max profile ────────────────────────────────

class TestClaudeMaxProfile:
    def test_claude_max_has_claude_code_providers(self):
        import olamot
        cfg = olamot._load_config()
        profile = cfg["profiles"]["claude_max"]
        olamot_cfg = profile["olamot"]

        for olam in ["atziluth", "briah", "yetzirah", "assiah"]:
            assert olamot_cfg[olam]["provider"] == "claude_code"

    def test_claude_max_models_are_correct(self):
        import olamot
        cfg = olamot._load_config()
        profile = cfg["profiles"]["claude_max"]
        olamot_cfg = profile["olamot"]

        assert olamot_cfg["atziluth"]["model"] == "opus"
        assert olamot_cfg["briah"]["model"] == "opus"
        assert olamot_cfg["yetzirah"]["model"] == "sonnet"
        assert olamot_cfg["assiah"]["model"] == "haiku"

    def test_claude_max_embedding_stays_ollama(self):
        import olamot
        cfg = olamot._load_config()
        profile = cfg["profiles"]["claude_max"]
        emb = profile["embedding"]
        assert emb["provider"] == "ollama"
        assert emb["model"] == "nomic-embed-text"


# ─── Tests claude_code_generate() ────────────────────────────

class TestClaudeCodeGenerate:
    @patch("olamot.get_model", return_value="sonnet")
    @patch("olamot.get_timeout", return_value=60)
    @patch("subprocess.run")
    def test_basic_call(self, mock_run, mock_timeout, mock_model):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Test response from Claude",
            stderr="",
        )
        import olamot
        response, latency = olamot.claude_code_generate("yetzirah", "Hello")

        assert response == "Test response from Claude"
        assert latency > 0
        mock_run.assert_called_once()

        # Vérifier les arguments de la commande
        call_args = mock_run.call_args
        cmd = call_args.args[0] if call_args.args else call_args.kwargs.get("args", [])
        assert any("claude" in str(c) for c in cmd)
        assert "-p" in cmd
        assert "--model" in cmd
        assert "sonnet" in cmd
        assert "--no-session-persistence" in cmd
        assert "--max-turns" in cmd

    @patch("olamot.get_model", return_value="sonnet")
    @patch("olamot.get_timeout", return_value=60)
    @patch("subprocess.run")
    @patch("time.sleep")  # Skip backoff delays dans les tests
    def test_error_returns_message(self, mock_sleep, mock_run, mock_timeout, mock_model):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Rate limit exceeded",
        )
        import olamot
        response, latency = olamot.claude_code_generate("yetzirah", "Hello")

        # Rate limit détecté → retry exhausted → message d'erreur rate limit
        assert "rate limit" in response.lower() or "[Erreur" in response
        assert latency > 0

    @patch("olamot.get_model", return_value="sonnet")
    @patch("olamot.get_timeout", return_value=1)
    @patch("subprocess.run", side_effect=FileNotFoundError("claude not found"))
    def test_missing_cli(self, mock_run, mock_timeout, mock_model):
        import olamot
        response, latency = olamot.claude_code_generate("yetzirah", "Hello")

        assert "[Erreur: claude CLI non installee]" in response

    @patch("olamot.get_model", return_value="sonnet")
    @patch("olamot.get_timeout", return_value=1)
    @patch("subprocess.run", side_effect=__import__("subprocess").TimeoutExpired(cmd=["claude"], timeout=1))
    def test_timeout(self, mock_run, mock_timeout, mock_model):
        import olamot
        response, latency = olamot.claude_code_generate("yetzirah", "Hello", timeout=1)

        assert "[Erreur: timeout" in response


# ─── Tests dispatch dans ollama_generate() ───────────────────

class TestDispatch:
    @patch("olamot.get_provider", return_value="claude_code")
    @patch("olamot.claude_code_generate", return_value=("Claude response", 100.0))
    @patch("olamot._persist_post_response")
    @patch("olamot.ContextAssembler")
    def test_dispatch_to_claude_code(self, mock_asm, mock_persist, mock_cc_gen, mock_prov):
        """Quand provider=claude_code, ollama_generate dispatch vers claude_code_generate."""
        mock_asm_instance = MagicMock()
        mock_asm_instance.assemble.return_value = {
            "prompt_final": "assembled prompt",
            "masakh_level": "shoresh",
            "dimensions_score": 0.5,
            "excluded": {"tokens_rejected": 0},
            "monitor_state": None,
        }
        mock_asm.return_value = mock_asm_instance

        import olamot
        response, latency = olamot.ollama_generate(
            "yetzirah", "test prompt",
            kavvanah={"intention": "test"},
        )

        assert response == "Claude response"
        assert latency == 100.0
        mock_cc_gen.assert_called_once()
        mock_persist.assert_called_once()

    @patch("olamot.get_provider", return_value="ollama")
    @patch("olamot.get_model", return_value="qwen3.5:9b")
    @patch("olamot.get_options", return_value={"temperature": 0.7})
    @patch("olamot.get_ollama_host", return_value="http://localhost:11434")
    @patch("olamot.get_think", return_value=False)
    @patch("olamot.get_context_window", return_value=8192)
    @patch("olamot.ContextAssembler")
    @patch("urllib.request.urlopen")
    @patch("olamot._persist_post_response")
    def test_dispatch_to_ollama(self, mock_persist, mock_urlopen, mock_asm,
                                 mock_ctx, mock_think, mock_host, mock_opts,
                                 mock_model, mock_prov):
        """Quand provider=ollama, ollama_generate utilise le code Ollama existant."""
        mock_asm_instance = MagicMock()
        mock_asm_instance.assemble.return_value = {
            "prompt_final": "assembled",
            "masakh_level": "shoresh",
            "dimensions_score": 0.5,
            "excluded": {"tokens_rejected": 0},
            "monitor_state": None,
        }
        mock_asm.return_value = mock_asm_instance

        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps({
            "response": "Ollama response",
        }).encode()
        mock_urlopen.return_value = mock_resp

        import olamot
        response, latency = olamot.ollama_generate(
            "yetzirah", "test prompt",
            kavvanah={"intention": "test"},
        )

        assert response == "Ollama response"
        # Ollama path should NOT call claude_code_generate
        mock_persist.assert_called_once()


# ─── Tests sephirot mapping ─────────────────────────────────

class TestSephirotMapping:
    def test_get_model_for_binah(self):
        import olamot
        model = olamot.get_model_for("binah")
        assert isinstance(model, str)
        assert len(model) > 0

    def test_get_judge_model_for_hod(self):
        import olamot
        model = olamot.get_judge_model_for("hod")
        assert isinstance(model, str)

    def test_unknown_sephirah_raises(self):
        import olamot
        with pytest.raises(KeyError, match="Sephirah inconnue"):
            olamot.get_model_for("sitra_achra")

    def test_get_embedding_model(self):
        import olamot
        model = olamot.get_embedding_model()
        assert model == "nomic-embed-text"


# ─── Tests etz_provider.py ───────────────────────────────────

class TestEtzProvider:
    def test_import(self):
        import etz_provider
        assert hasattr(etz_provider, "cmd_status")
        assert hasattr(etz_provider, "cmd_profiles")
        assert hasattr(etz_provider, "cmd_switch")
        assert hasattr(etz_provider, "cmd_test")
