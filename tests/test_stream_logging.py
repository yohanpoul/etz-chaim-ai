"""Tests F7 — ollama_generate_stream() persiste masakh_log et context_monitor_log.

Vérifie la parité de logging entre ollama_generate() et ollama_generate_stream().
Mocke le réseau (pas d'Ollama requis) et la DB (pas de PostgreSQL requis).
"""

import io
import json
from unittest.mock import MagicMock, patch, call

import pytest


# ── Helpers ──────────────────────────────────────────────

def _fake_assembly(**overrides):
    """Assembly dict minimal simulant la sortie du ContextAssembler."""
    base = {
        "prompt_final": "prompt test",
        "masakh_level": "shoresh",
        "dimensions_score": 0.5,
        "excluded": {
            "tokens_before": 100,
            "tokens_after": 80,
            "tokens_rejected": 20,
            "rejection_reason": "budget_masakh",
        },
        "pipeline_steps": ["kavvanah", "masakh"],
        "monitor_state": {
            "olam": "yetzirah",
            "score_global": 0.75,
            "dimensions": {},
        },
        "reshimo_pre": {
            "reshimo_hitlabshut": {
                "pipeline_steps": ["kavvanah", "masakh"],
                "maturation_stage": None,
            },
            "reshimo_aviut": {
                "masakh_level": "shoresh",
                "was_filtered": True,
                "kavvanah": None,
                "score": 0.5,
            },
        },
        "kashiut": 0.3,
        "aviut_mode": "head_tail",
    }
    base.update(overrides)
    return base


def _fake_stream_response(tokens: list[str]) -> io.BytesIO:
    """Simule la réponse HTTP streaming d'Ollama (une ligne JSON par chunk)."""
    lines = []
    for t in tokens:
        lines.append(json.dumps({"response": t, "done": False}).encode() + b"\n")
    lines.append(json.dumps({"response": "", "done": True}).encode() + b"\n")
    return io.BytesIO(b"".join(lines))


def _fake_thinking_stream(thinking_tokens: list[str]) -> io.BytesIO:
    """Simule un stream Qwen3.5 thinking mode (response vide, thinking rempli)."""
    lines = []
    for t in thinking_tokens:
        lines.append(json.dumps({"response": "", "thinking": t, "done": False}).encode() + b"\n")
    lines.append(json.dumps({"response": "", "done": True}).encode() + b"\n")
    return io.BytesIO(b"".join(lines))


# ── Tests ────────────────────────────────────────────────

class TestStreamLogging:
    """F7: ollama_generate_stream() doit persister reshimo, masakh_log, context_monitor_log."""

    @patch("olamot.urllib.request.urlopen")
    @patch("olamot._get_db_conn")
    @patch("olamot.write_reshimo")
    @patch("olamot.ContextAssembler")
    @patch("olamot.get_context_window", return_value=4096)
    @patch("olamot.get_think", return_value=False)
    @patch("olamot.get_ollama_host", return_value="http://localhost:11434")
    @patch("olamot.get_options", return_value={})
    @patch("olamot.get_model", return_value="qwen3.5:9b")
    @patch("olamot.get_provider", return_value="ollama")
    def test_stream_calls_write_reshimo(
        self,
        _m_prov, _m_model, _m_opts, _m_host, _m_think, _m_ctx_win,
        mock_assembler_cls, mock_reshimo, mock_db, mock_urlopen,
    ):
        """write_reshimo est appelé après consommation complète du stream."""
        mock_assembler_cls.return_value.assemble.return_value = _fake_assembly()
        mock_db.return_value = None  # pas de DB
        mock_urlopen.return_value = _fake_stream_response(["Sha", "lom"])

        from olamot import ollama_generate_stream

        chunks = list(ollama_generate_stream("yetzirah", "test prompt"))

        assert len(chunks) == 3  # 2 tokens + 1 done
        mock_reshimo.assert_called_once()
        kw = mock_reshimo.call_args
        assert kw.kwargs["hitlabshut"]["stream"] is True
        assert kw.kwargs["hitlabshut"]["response_length"] == len("Shalom")
        assert kw.kwargs["hitlabshut"]["response_preview"] == "Shalom"
        assert kw.kwargs["aviut"]["masakh_level"] == "shoresh"

    @patch("olamot.urllib.request.urlopen")
    @patch("olamot._get_db_conn")
    @patch("olamot.write_reshimo")
    @patch("olamot.ContextAssembler")
    @patch("olamot.get_context_window", return_value=4096)
    @patch("olamot.get_think", return_value=False)
    @patch("olamot.get_ollama_host", return_value="http://localhost:11434")
    @patch("olamot.get_options", return_value={})
    @patch("olamot.get_model", return_value="qwen3.5:9b")
    @patch("olamot.get_provider", return_value="ollama")
    def test_stream_persists_masakh_log(
        self,
        _m_prov, _m_model, _m_opts, _m_host, _m_think, _m_ctx_win,
        mock_assembler_cls, mock_reshimo, mock_db, mock_urlopen,
    ):
        """masakh_log INSERT est exécuté quand une connexion DB est disponible."""
        mock_assembler_cls.return_value.assemble.return_value = _fake_assembly()

        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_db.return_value = mock_ctx

        mock_urlopen.return_value = _fake_stream_response(["Hello"])

        from olamot import ollama_generate_stream

        list(ollama_generate_stream("yetzirah", "test"))

        # Vérifier qu'un des appels execute() est un INSERT INTO masakh_log
        assert mock_cursor.execute.called
        masakh_calls = [
            c for c in mock_cursor.execute.call_args_list
            if "masakh_log" in c[0][0]
        ]
        assert len(masakh_calls) == 1, f"Expected 1 masakh_log INSERT, got {len(masakh_calls)}"
        sql = masakh_calls[0][0][0]
        assert "INSERT" in sql.upper()

        params = masakh_calls[0][0][1]
        assert params[0] == "yetzirah"  # olam
        mock_conn.commit.assert_called()

    @patch("olamot.urllib.request.urlopen")
    @patch("olamot._get_db_conn")
    @patch("olamot.write_reshimo")
    @patch("olamot.ContextAssembler")
    @patch("olamot.get_context_window", return_value=4096)
    @patch("olamot.get_think", return_value=False)
    @patch("olamot.get_ollama_host", return_value="http://localhost:11434")
    @patch("olamot.get_options", return_value={})
    @patch("olamot.get_model", return_value="qwen3.5:9b")
    @patch("olamot.get_provider", return_value="ollama")
    def test_stream_persists_context_monitor_log(
        self,
        _m_prov, _m_model, _m_opts, _m_host, _m_think, _m_ctx_win,
        mock_assembler_cls, mock_reshimo, mock_db, mock_urlopen,
    ):
        """context_monitor_log est persisté via log_to_db quand monitor_state existe."""
        assembly = _fake_assembly()
        mock_assembler_cls.return_value.assemble.return_value = assembly

        mock_conn = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_conn)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_db.return_value = mock_ctx

        mock_urlopen.return_value = _fake_stream_response(["ok"])

        from olamot import ollama_generate_stream

        with patch("olamot.ContextMonitor") as mock_cm_cls:
            mock_cm_cls.return_value.update_post_response.return_value = {}
            with patch(
                "masakh.context_monitor.log_to_db"
            ) as mock_monitor_log:
                list(ollama_generate_stream("yetzirah", "test"))
                mock_monitor_log.assert_called_once_with(
                    mock_conn, assembly["monitor_state"]
                )

    @patch("olamot.urllib.request.urlopen")
    @patch("olamot._get_db_conn")
    @patch("olamot.write_reshimo")
    @patch("olamot.ContextAssembler")
    @patch("olamot.get_context_window", return_value=4096)
    @patch("olamot.get_think", return_value=False)
    @patch("olamot.get_ollama_host", return_value="http://localhost:11434")
    @patch("olamot.get_options", return_value={})
    @patch("olamot.get_model", return_value="qwen3.5:9b")
    @patch("olamot.get_provider", return_value="ollama")
    def test_stream_logging_on_early_break(
        self,
        _m_prov, _m_model, _m_opts, _m_host, _m_think, _m_ctx_win,
        mock_assembler_cls, mock_reshimo, mock_db, mock_urlopen,
    ):
        """Le logging s'exécute même si le consumer break avant la fin du stream."""
        mock_assembler_cls.return_value.assemble.return_value = _fake_assembly()
        mock_db.return_value = None
        mock_urlopen.return_value = _fake_stream_response(["A", "B", "C"])

        from olamot import ollama_generate_stream

        gen = ollama_generate_stream("yetzirah", "test")
        next(gen)  # consomme 1 chunk
        gen.close()  # consumer abandonne

        # write_reshimo doit quand même être appelé (finally block)
        mock_reshimo.assert_called_once()
        # Seul le premier token "A" a été consommé avant close()
        kw = mock_reshimo.call_args
        assert kw.kwargs["hitlabshut"]["response_length"] <= len("A")

    @patch("olamot.urllib.request.urlopen")
    @patch("olamot._get_db_conn")
    @patch("olamot.write_reshimo")
    @patch("olamot.ContextAssembler")
    @patch("olamot.get_context_window", return_value=4096)
    @patch("olamot.get_think", return_value=False)
    @patch("olamot.get_ollama_host", return_value="http://localhost:11434")
    @patch("olamot.get_options", return_value={})
    @patch("olamot.get_model", return_value="qwen3.5:9b")
    @patch("olamot.get_provider", return_value="ollama")
    def test_stream_no_monitor_state(
        self,
        _m_prov, _m_model, _m_opts, _m_host, _m_think, _m_ctx_win,
        mock_assembler_cls, mock_reshimo, mock_db, mock_urlopen,
    ):
        """Pas de crash si monitor_state est None."""
        mock_assembler_cls.return_value.assemble.return_value = _fake_assembly(
            monitor_state=None
        )
        mock_db.return_value = None
        mock_urlopen.return_value = _fake_stream_response(["ok"])

        from olamot import ollama_generate_stream

        chunks = list(ollama_generate_stream("yetzirah", "test"))
        assert len(chunks) == 2
        mock_reshimo.assert_called_once()

    @patch("olamot.urllib.request.urlopen")
    @patch("olamot._get_db_conn")
    @patch("olamot.write_reshimo")
    @patch("olamot.ContextAssembler")
    @patch("olamot.get_context_window", return_value=4096)
    @patch("olamot.get_think", return_value=True)
    @patch("olamot.get_ollama_host", return_value="http://localhost:11434")
    @patch("olamot.get_options", return_value={})
    @patch("olamot.get_model", return_value="qwen3.5:9b")
    @patch("olamot.get_provider", return_value="ollama")
    def test_stream_thinking_mode_fallback(
        self,
        _m_prov, _m_model, _m_opts, _m_host, _m_think, _m_ctx_win,
        mock_assembler_cls, mock_reshimo, mock_db, mock_urlopen,
    ):
        """Briah thinking mode: réponse vide → fallback sur thinking tokens."""
        mock_assembler_cls.return_value.assemble.return_value = _fake_assembly()
        mock_db.return_value = None
        mock_urlopen.return_value = _fake_thinking_stream(["Let me ", "think..."])

        from olamot import ollama_generate_stream

        chunks = list(ollama_generate_stream("briah", "complex question"))
        assert len(chunks) == 3  # 2 thinking + 1 done
        mock_reshimo.assert_called_once()
        kw = mock_reshimo.call_args
        assert kw.kwargs["hitlabshut"]["response_length"] == len("Let me think...")
        assert kw.kwargs["hitlabshut"]["response_preview"] == "Let me think..."
