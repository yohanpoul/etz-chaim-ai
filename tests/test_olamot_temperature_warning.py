"""Tests audit cycle 4, I5 — warning température ignorée sous claude_code.

La CLI `claude` n'expose pas --temperature : les valeurs configurées
sous provider=claude_code sont ignorées. On valide que :
  - Un warning est émis au premier appel par olam.
  - Le warning n'est PAS répété pour le même olam.
  - Aucun warning pour provider=ollama (où la température fonctionne).
  - Aucun warning si options.temperature absente.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def reset_warnings():
    """Vider le set de mémo des warnings avant chaque test."""
    import olamot
    olamot._TEMP_WARNING_EMITTED.clear()
    yield
    olamot._TEMP_WARNING_EMITTED.clear()


class TestTemperatureWarning:
    def test_warns_for_claude_code_with_temperature(self, reset_warnings, caplog):
        from olamot import _warn_temperature_unsupported_for_claude_code

        cfg = {"provider": "claude_code", "options": {"temperature": 0.7}}
        with patch("olamot._get_olam_config", return_value=cfg):
            with caplog.at_level("WARNING"):
                _warn_temperature_unsupported_for_claude_code("yetzirah")

        msgs = [r.message for r in caplog.records]
        assert any(
            "yetzirah" in m and "0.7" in m and "IGNORÉE" in m
            for m in msgs
        ), f"Pas de warning attendu dans: {msgs}"

    def test_does_not_warn_for_ollama_provider(self, reset_warnings, caplog):
        from olamot import _warn_temperature_unsupported_for_claude_code

        cfg = {"provider": "ollama", "options": {"temperature": 0.7}}
        with patch("olamot._get_olam_config", return_value=cfg):
            with caplog.at_level("WARNING"):
                _warn_temperature_unsupported_for_claude_code("briah")

        assert not any("temperature" in r.message.lower() for r in caplog.records)

    def test_does_not_warn_when_no_temperature_configured(
        self, reset_warnings, caplog,
    ):
        from olamot import _warn_temperature_unsupported_for_claude_code

        cfg = {"provider": "claude_code", "max_tokens": 8192}
        with patch("olamot._get_olam_config", return_value=cfg):
            with caplog.at_level("WARNING"):
                _warn_temperature_unsupported_for_claude_code("atziluth")

        assert not any("temperature" in r.message.lower() for r in caplog.records)

    def test_warns_only_once_per_olam(self, reset_warnings, caplog):
        from olamot import _warn_temperature_unsupported_for_claude_code

        cfg = {"provider": "claude_code", "options": {"temperature": 0.7}}
        with patch("olamot._get_olam_config", return_value=cfg):
            with caplog.at_level("WARNING"):
                _warn_temperature_unsupported_for_claude_code("yetzirah")
                _warn_temperature_unsupported_for_claude_code("yetzirah")
                _warn_temperature_unsupported_for_claude_code("yetzirah")

        warnings = [
            r for r in caplog.records
            if "yetzirah" in r.message and "IGNORÉE" in r.message
        ]
        assert len(warnings) == 1, f"Attendu 1 warning, vu {len(warnings)}"

    def test_warns_per_distinct_olam(self, reset_warnings, caplog):
        from olamot import _warn_temperature_unsupported_for_claude_code

        cfg = {"provider": "claude_code", "options": {"temperature": 0.5}}
        with patch("olamot._get_olam_config", return_value=cfg):
            with caplog.at_level("WARNING"):
                _warn_temperature_unsupported_for_claude_code("briah")
                _warn_temperature_unsupported_for_claude_code("yetzirah")
                _warn_temperature_unsupported_for_claude_code("assiah")

        warned_olamot = {
            o for o in ("briah", "yetzirah", "assiah")
            if any(o in r.message and "IGNORÉE" in r.message for r in caplog.records)
        }
        assert warned_olamot == {"briah", "yetzirah", "assiah"}

    def test_unknown_olam_does_not_raise(self, reset_warnings):
        from olamot import _warn_temperature_unsupported_for_claude_code

        # Si l'olam est inconnu (KeyError dans _get_olam_config), on ne lève pas.
        with patch("olamot._get_olam_config", side_effect=KeyError("nope")):
            _warn_temperature_unsupported_for_claude_code("unknown_olam")

    def test_real_config_briah_warns_under_claude_max(self, reset_warnings, caplog):
        """Vérifier sur la vraie config : briah/claude_max a temperature=0.3."""
        from olamot import (
            _warn_temperature_unsupported_for_claude_code,
            _get_olam_config,
        )

        cfg = _get_olam_config("briah")
        if cfg.get("provider") != "claude_code":
            pytest.skip("Profil actif n'est pas claude_max — test non pertinent.")

        with caplog.at_level("WARNING"):
            _warn_temperature_unsupported_for_claude_code("briah")

        assert any(
            "briah" in r.message and "IGNORÉE" in r.message
            for r in caplog.records
        )
