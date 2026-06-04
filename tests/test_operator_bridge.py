from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path


def _sample_loop_payload() -> dict:
    return {
        "status": "written",
        "dry_run": False,
        "generated_at": "2026-06-04T21:00:00Z",
        "cycle_id": "loop-20260604T210000Z",
        "heartbeat": {
            "timestamp": "2026-06-04T21:00:00Z",
            "cycle_id": "loop-20260604T210000Z",
            "status": "written",
            "top_issue_id": "pytest-corpus-gate-missing-tikkunim-non-bidir-links",
            "action_count": 1,
            "guardian_verdict": "caution",
            "applies_patch": False,
        },
        "improve": {
            "top_issue": {
                "id": "pytest-corpus-gate-missing-tikkunim-non-bidir-links",
                "source": "pytest",
                "severity": "error",
                "priority": 95,
                "title": "Corpus gate pytest failed: missing tikkunim and non-bidirectional links",
                "description": "The bounded pytest subset reached a source-backed corpus gate.",
                "verification_command": ".venv/bin/python -m pytest sifrei_yesod/tests/test_idra_corpus_fidelity.py -q",
                "verified": False,
                "evidence": ["diagnostic_category=corpus-gate"],
            },
            "proposed_actions": [
                {
                    "id": "test-pytest-corpus-gate-missing-tikkunim-non-bidir-links",
                    "type": "test",
                    "title": "Triage corpus-gate pytest failure",
                    "description": "Plan source-backed missing tikkunim work; do not repair the corpus automatically.",
                    "event_ids": ["pytest-corpus-gate-missing-tikkunim-non-bidir-links"],
                    "verification_command": ".venv/bin/python -m pytest sifrei_yesod/tests/test_idra_corpus_fidelity.py -q",
                    "applies_patch": False,
                }
            ],
            "faculty_evaluation": {
                "guardian": {
                    "verdict": "caution",
                    "confidence": 0.72,
                    "reason": "Requires human-supervised corpus work.",
                    "active_biases": ["automation-bias"],
                }
            },
        },
    }


def test_build_pulse_payload_routes_to_codex_cli_without_api(tmp_path):
    from etzchaim.operator_bridge import build_pulse_payload

    config = tmp_path / "config.yaml"
    config.write_text(
        """
active_profile: codex_cli
profiles:
  codex_cli:
    olamot:
      atziluth:
        provider: cli
        cli: codex
        model: gpt-5
        args: ["exec", "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only", "--ephemeral", "--model", "{model}", "-"]
      briah:
        provider: cli
        cli: codex
        model: gpt-5
        args: ["exec", "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only", "--ephemeral", "--model", "{model}", "-"]
      yetzirah:
        provider: cli
        cli: codex
        model: gpt-5-mini
        args: ["exec", "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only", "--ephemeral", "--model", "{model}", "-"]
      assiah:
        provider: cli
        cli: codex
        model: gpt-5-nano
        args: ["exec", "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only", "--ephemeral", "--model", "{model}", "-"]
""".strip(),
        encoding="utf-8",
    )

    payload = build_pulse_payload(
        repo_root=tmp_path,
        config_path=config,
        vault_dir=tmp_path / "vault" / "00-system" / "operator-kernel",
        loop_payload=_sample_loop_payload(),
        codex_status={
            "status": "ok",
            "cli": "codex",
            "path": str(tmp_path / "bin" / "codex"),
            "version": "codex-cli 0.128.0",
            "smoke": None,
        },
        now=datetime(2026, 6, 4, 21, 5, tzinfo=UTC),
    )

    assert payload["status"] == "ready"
    assert payload["provider"]["active_profile"] == "codex_cli"
    assert payload["provider"]["uses_api_key"] is False
    assert payload["provider"]["codex_cli_configured"] is True
    assert payload["codex"]["status"] == "ok"
    assert payload["work_packet"]["target_agent"] == "codex_cli"
    assert payload["work_packet"]["requires_human_go"] is True
    assert payload["work_packet"]["applies_patch"] is False
    assert "Ne modifie pas le corpus automatiquement" in payload["work_packet"]["prompt"]
    assert payload["vault"]["dir"].endswith("00-system/operator-kernel")
    assert not (tmp_path / "vault").exists()


def test_write_vault_pulse_creates_cockpit_pulse_and_work_packet(tmp_path):
    from etzchaim.operator_bridge import build_pulse_payload, write_vault_pulse

    payload = build_pulse_payload(
        repo_root=tmp_path,
        config_path=None,
        vault_dir=tmp_path / "vault" / "00-system" / "operator-kernel",
        loop_payload=_sample_loop_payload(),
        codex_status={"status": "ok", "cli": "codex", "path": "/bin/codex", "version": "codex-cli 0.128.0", "smoke": None},
        now=datetime(2026, 6, 4, 21, 5, tzinfo=UTC),
    )

    written = write_vault_pulse(payload)

    index = Path(written["index"])
    pulse = Path(written["pulse"])
    packet = Path(written["work_packet"])
    agents = Path(written["agents"])

    assert index.exists()
    assert pulse.exists()
    assert packet.exists()
    assert agents.exists()
    assert "type: cockpit" in index.read_text(encoding="utf-8")
    assert "# Operator Kernel" in index.read_text(encoding="utf-8")
    assert "Codex CLI" in index.read_text(encoding="utf-8")
    assert "# Pulse — loop-20260604T210000Z" in pulse.read_text(encoding="utf-8")
    assert "guardian_verdict" in pulse.read_text(encoding="utf-8")
    assert "# Work Packet — loop-20260604T210000Z" in packet.read_text(encoding="utf-8")
    assert "GO humain requis" in packet.read_text(encoding="utf-8")
    assert "Ne modifie pas le corpus automatiquement" in packet.read_text(encoding="utf-8")


def test_cli_generic_resolves_codex_from_user_npm_global_when_path_is_sparse(monkeypatch, tmp_path):
    from etzchaim.providers import cli_generic

    codex = tmp_path / ".npm-global" / "bin" / "codex"
    codex.parent.mkdir(parents=True)
    codex.write_text("#!/bin/sh\necho codex-cli 0.128.0\n", encoding="utf-8")
    codex.chmod(0o755)

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cli_generic.shutil, "which", lambda _name: None)

    assert cli_generic._resolve_binary("codex") == str(codex)


def test_build_pulse_payload_degrades_when_codex_safety_flags_are_missing(tmp_path):
    from etzchaim.operator_bridge import build_pulse_payload

    config = tmp_path / "config.yaml"
    config.write_text(
        """
active_profile: codex_cli
profiles:
  codex_cli:
    olamot:
      atziluth: {provider: cli, cli: codex, model: gpt-5.5, args: ["exec", "--model", "{model}", "-"]}
      briah: {provider: cli, cli: codex, model: gpt-5.5, args: ["exec", "--model", "{model}", "-"]}
      yetzirah: {provider: cli, cli: codex, model: gpt-5.5, args: ["exec", "--model", "{model}", "-"]}
      assiah: {provider: cli, cli: codex, model: gpt-5.5, args: ["exec", "--model", "{model}", "-"]}
""".strip(),
        encoding="utf-8",
    )

    payload = build_pulse_payload(
        repo_root=tmp_path,
        config_path=config,
        vault_dir=tmp_path / "vault",
        loop_payload=_sample_loop_payload(),
        codex_status={"status": "ok", "cli": "codex", "path": "/bin/codex", "version": "codex-cli", "smoke": None},
        now=datetime(2026, 6, 4, 21, 5, tzinfo=UTC),
    )

    assert payload["provider"]["codex_cli_configured"] is False
    assert payload["status"] == "degraded"


def test_codex_cli_status_smoke_requires_assistant_payload(monkeypatch, tmp_path):
    from etzchaim import operator_bridge

    class FakeResult:
        def __init__(self, stdout="", stderr="", returncode=0):
            self.stdout = stdout
            self.stderr = stderr
            self.returncode = returncode

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[1:] == ["--version"]:
            return FakeResult(stdout="codex-cli 0.128.0")
        return FakeResult(
            stdout="""OpenAI Codex v0.128.0
user
Réponds exactement CODEX_READY.

codex
NOT_READY

tokens used
42
CODEX_READY
"""
        )

    monkeypatch.setattr(operator_bridge, "_resolve_binary", lambda cli: "/bin/codex")
    monkeypatch.setattr(operator_bridge.subprocess, "run", fake_run)

    status = operator_bridge.codex_cli_status(smoke=True, repo_root=tmp_path)

    assert status["status"] == "degraded"
    assert status["smoke"]["passed"] is False
    assert status["smoke"]["output_excerpt"] == "NOT_READY"
    assert calls[1][1:4] == ["exec", "--ignore-user-config", "--ignore-rules"]


def test_vault_paths_sanitize_cycle_id(tmp_path):
    from etzchaim.operator_bridge import build_pulse_payload

    loop_payload = _sample_loop_payload()
    loop_payload["cycle_id"] = "../bad/cycle:1"
    payload = build_pulse_payload(
        repo_root=tmp_path,
        config_path=None,
        vault_dir=tmp_path / "vault",
        loop_payload=loop_payload,
        codex_status={"status": "missing", "cli": "codex", "path": None, "version": None, "smoke": None},
        now=datetime(2026, 6, 4, 21, 5, tzinfo=UTC),
    )

    assert ".." not in Path(payload["vault"]["pulse"]).name
    assert "/bad/" not in payload["vault"]["pulse"]
    assert Path(payload["vault"]["pulse"]).parent == tmp_path / "vault" / "pulses"


def test_ollama_generate_stream_cli_returns_single_pseudo_stream_chunk(monkeypatch):
    import olamot
    from etzchaim.providers import cli_generic

    class FakeAssembler:
        def assemble(self, **kwargs):
            return {"prompt_final": kwargs["prompt"]}

    persisted = {}

    def fake_cli_generate(**kwargs):
        assert kwargs["cli"] == "codex"
        assert "mode texte pur" in kwargs["prompt"]
        return "STREAM_OK", 12.0

    monkeypatch.setattr(olamot, "get_provider", lambda _olam: "cli")
    monkeypatch.setattr(olamot, "get_context_window", lambda _olam: 200_000)
    monkeypatch.setattr(olamot, "ContextAssembler", lambda db_pool_fn=None: FakeAssembler())
    monkeypatch.setattr(
        olamot,
        "_get_olam_config",
        lambda _olam: {"cli": "codex", "args": [], "response_parser": "identity"},
    )
    monkeypatch.setattr(olamot, "get_model", lambda _olam: "gpt-5.5")
    monkeypatch.setattr(cli_generic, "cli_generate", fake_cli_generate)
    monkeypatch.setattr(olamot, "_persist_post_response", lambda **kwargs: persisted.update(kwargs))

    chunks = list(
        olamot.ollama_generate_stream(
            "assiah",
            "ping",
            kavvanah={"intention": "test", "critere_succes": "chunk", "anti_pattern": "ollama"},
        )
    )

    assert chunks == [{"response": "STREAM_OK", "done": True}]
    assert persisted["response_text"] == "STREAM_OK"
    assert persisted["stream"] is True


def test_strip_codex_banner_extracts_current_cli_assistant_payload():
    from etzchaim.providers.cli_generic import strip_codex_banner

    raw = """OpenAI Codex v0.128.0 (research preview)
--------
workdir: /tmp/repo
model: gpt-5.5
--------
user
Réponds exactement OK.

codex
OK

tokens used
15 290
OK
"""

    assert strip_codex_banner(raw) == "OK"
