"""Tests Promptfoo Bridge — custom provider pour le pipeline."""

from unittest.mock import patch

from sitra_achra.promptfoo_bridge import call_api, is_available, run_redteam_scan


class TestCallApi:

    def test_returns_output_dict(self):
        """call_api retourne le format attendu par Promptfoo."""
        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.return_value = ("test response", 100.0)
            result = call_api("test prompt", {}, {})

        assert "output" in result
        assert result["output"] == "test response"
        assert "tokenUsage" in result

    def test_handles_llm_error(self):
        """Erreur LLM → reponse d'erreur propre."""
        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.side_effect = RuntimeError("LLM down")
            result = call_api("test", {}, {})

        assert "Error" in result["output"]

    def test_uses_yetzirah(self):
        """Le bridge utilise Yetzirah (Sonnet) comme olam."""
        with patch("olamot.ollama_generate") as mock_gen:
            mock_gen.return_value = ("ok", 50.0)
            call_api("test", {}, {})

        mock_gen.assert_called_once()
        assert mock_gen.call_args[0][0] == "yetzirah"


class TestRunRedteamScan:

    def test_returns_error_when_not_installed(self):
        """Si promptfoo pas installe → erreur claire."""
        with patch("sitra_achra.promptfoo_bridge._PROMPTFOO_BIN", None):
            result = run_redteam_scan()

        assert "error" in result
        assert "not installed" in result["error"]


class TestIsAvailable:

    def test_not_available_when_no_binary(self):
        with patch("sitra_achra.promptfoo_bridge._PROMPTFOO_BIN", None):
            assert not is_available()

    def test_available_when_binary_exists(self):
        with patch("sitra_achra.promptfoo_bridge._PROMPTFOO_BIN", "/usr/bin/promptfoo"):
            assert is_available()
