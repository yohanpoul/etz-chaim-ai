"""Operator Bridge for Pulse-style cockpit summaries.

This module keeps the local metacognition loop mechanical and safe, then exposes
its state as an operator-facing pulse plus Codex CLI readiness metadata. It does
not mutate corpus sources and does not call Codex unless a caller explicitly asks
for a smoke probe.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from etzchaim._paths import state_dir
from etzchaim.metacognition import runtime_loop
from etzchaim.providers.cli_generic import _resolve_binary, strip_codex_banner

DEFAULT_VAULT_RELATIVE = Path("Documents") / "mon-cerveau" / "00-system" / "operator-kernel"


def utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _date(value: str) -> str:
    return value.split("T", 1)[0]


def default_vault_dir() -> Path:
    override = os.environ.get("ETZCHAIM_OPERATOR_VAULT_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / DEFAULT_VAULT_RELATIVE


def default_config_path(repo_root: Path | str | None = None) -> Path | None:
    override = os.environ.get("ETZCHAIM_CONFIG")
    if override:
        path = Path(override).expanduser()
        return path if path.exists() else None
    root = Path(repo_root or Path.cwd())
    candidate = root / "config.yaml"
    if candidate.exists():
        return candidate
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "config.yaml"
        if candidate.exists():
            return candidate
    return None


def _load_config(config_path: Path | str | None) -> dict[str, Any]:
    if config_path is None:
        return {}
    path = Path(config_path)
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _active_profile_block(config: dict[str, Any]) -> tuple[str | None, dict[str, Any]]:
    profile_name = config.get("active_profile")
    profiles = config.get("profiles") or {}
    if not isinstance(profile_name, str) or not isinstance(profiles, dict):
        return None, {}
    block = profiles.get(profile_name)
    return profile_name, block if isinstance(block, dict) else {}


def summarize_provider_config(config_path: Path | str | None) -> dict[str, Any]:
    config = _load_config(config_path)
    active_profile, block = _active_profile_block(config)
    olamot = block.get("olamot") or {}
    slots: dict[str, dict[str, Any]] = {}
    codex_slots = 0
    api_slots = 0
    for name, slot in olamot.items() if isinstance(olamot, dict) else []:
        if not isinstance(slot, dict):
            continue
        provider = slot.get("provider", "ollama")
        cli = slot.get("cli")
        model = slot.get("model")
        args = slot.get("args", [])
        slot_summary = {
            "provider": provider,
            "cli": cli,
            "model": model,
            "read_only_sandbox": "read-only" in args,
            "ephemeral": "--ephemeral" in args,
            "ignore_user_config": "--ignore-user-config" in args,
            "ignore_rules": "--ignore-rules" in args,
        }
        slots[str(name)] = slot_summary
        if provider == "cli" and cli == "codex":
            codex_slots += 1
        if provider in {"litellm", "anthropic", "openai"}:
            api_slots += 1

    expected_olamot = {"atziluth", "briah", "yetzirah", "assiah"}
    codex_cli_configured = (
        active_profile == "codex_cli"
        and expected_olamot.issubset(slots)
        and all(
            slots[name]["provider"] == "cli"
            and slots[name]["cli"] == "codex"
            and slots[name]["read_only_sandbox"] is True
            and slots[name]["ephemeral"] is True
            and slots[name]["ignore_user_config"] is True
            and slots[name]["ignore_rules"] is True
            for name in expected_olamot
        )
    )
    return {
        "config_path": str(config_path) if config_path else None,
        "active_profile": active_profile,
        "codex_cli_configured": codex_cli_configured,
        "uses_api_key": api_slots > 0 and not codex_cli_configured,
        "codex_slots": codex_slots,
        "olamot": slots,
    }


def codex_cli_status(
    *,
    cli: str = "codex",
    model: str = "gpt-5.5",
    smoke: bool = False,
    repo_root: Path | str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Return Codex CLI readiness without requiring API keys.

    The optional smoke probe calls the subscription-backed CLI once in read-only,
    ephemeral mode. It is off by default to avoid accidental subscription usage.
    """

    path = _resolve_binary(cli)
    if not path:
        return {
            "status": "missing",
            "cli": cli,
            "path": None,
            "version": None,
            "smoke": None,
            "message": "codex binary not found on PATH or known user install paths",
        }

    version = None
    try:
        result = subprocess.run(
            [path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        version = (result.stdout or result.stderr).strip()
    except Exception as exc:  # noqa: BLE001
        version = f"version probe failed: {type(exc).__name__}: {exc}"

    smoke_payload = None
    status = "ok"
    if smoke:
        command = [
            path,
            "exec",
            "--ignore-user-config",
            "--ignore-rules",
            "--sandbox",
            "read-only",
            "--ephemeral",
            "--model",
            model,
            "Réponds exactement CODEX_READY, sans autre texte.",
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(repo_root or Path.cwd()),
                check=False,
            )
            raw_output = (result.stdout or result.stderr or "").strip()
            parsed_output = strip_codex_banner(result.stdout or "").strip()
            smoke_payload = {
                "command": " ".join(command),
                "exit_code": result.returncode,
                "passed": result.returncode == 0 and parsed_output == "CODEX_READY",
                "output_excerpt": (parsed_output or raw_output)[-500:],
            }
            if not smoke_payload["passed"]:
                status = "degraded"
        except Exception as exc:  # noqa: BLE001
            status = "degraded"
            smoke_payload = {
                "command": " ".join(command),
                "exit_code": None,
                "passed": False,
                "output_excerpt": f"{type(exc).__name__}: {exc}",
            }

    return {
        "status": status,
        "cli": cli,
        "path": path,
        "version": version,
        "smoke": smoke_payload,
    }


def _read_last_loop_payload() -> dict[str, Any] | None:
    path = state_dir() / "state" / "last_loop_run.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _first_action(loop_payload: dict[str, Any]) -> dict[str, Any] | None:
    improve = loop_payload.get("improve") or {}
    top_issue = improve.get("top_issue") or {}
    actions = improve.get("proposed_actions") or []
    if not actions:
        return None
    top_issue_id = top_issue.get("id")
    for action in actions:
        if isinstance(action, dict) and top_issue_id in action.get("event_ids", []):
            return action
    first = actions[0]
    return first if isinstance(first, dict) else None


def _top_issue(loop_payload: dict[str, Any]) -> dict[str, Any] | None:
    improve = loop_payload.get("improve") or {}
    top_issue = improve.get("top_issue")
    return top_issue if isinstance(top_issue, dict) else None


def build_work_packet(loop_payload: dict[str, Any] | None, *, repo_root: Path | str) -> dict[str, Any]:
    if not loop_payload:
        return {
            "id": "work-packet-unavailable",
            "status": "unavailable",
            "target_agent": "codex_cli",
            "requires_human_go": True,
            "applies_patch": False,
            "title": "No loop payload available",
            "prompt": "Run `etzchaim pulse --run-loop --write-vault` first.",
        }
    cycle_id = str(loop_payload.get("cycle_id") or "loop-unknown")
    issue = _top_issue(loop_payload) or {}
    action = _first_action(loop_payload) or {}
    title = action.get("title") or issue.get("title") or "Review operator pulse"
    applies_patch = bool(action.get("applies_patch", False))
    verification = action.get("verification_command") or issue.get("verification_command") or ""
    prompt = f"""Tu es Codex CLI, lancé dans le repo local :
{Path(repo_root).resolve()}

Mission : transformer le pulse Operator Kernel `{cycle_id}` en plan de travail vérifiable.

Top issue : {issue.get('id') or 'none'}
Titre : {issue.get('title') or title}
Action proposée : {action.get('id') or 'none'} — {title}
Vérification : {verification or 'non fournie'}

Contraintes absolues :
- Ne modifie pas le corpus automatiquement.
- Ne supprime rien, ne lance pas `git clean`, ne fais pas de `git reset --hard`.
- Pas de git push.
- Pas de LaunchAgent, pas de cron, pas de service permanent.
- Si une mutation est nécessaire, écris d'abord un plan et attends un GO humain.
- Préserve le rôle du kernel : observer, prioriser, préparer ; pas auto-réparer.

Livrable attendu : un plan court sous `strategy/codex-prompt/codex-plan/` avec preuves, fichiers concernés, tests à lancer, risques, et prochaine décision humaine.
""".strip()
    return {
        "id": f"work-packet-{cycle_id}",
        "status": "needs-human-go",
        "target_agent": "codex_cli",
        "requires_human_go": True,
        "applies_patch": applies_patch,
        "title": str(title),
        "top_issue_id": issue.get("id"),
        "action_id": action.get("id"),
        "verification_command": verification,
        "prompt": prompt,
    }


def _safe_path_segment(value: str) -> str:
    """Return a conservative single path segment for generated vault files."""
    segment = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-")
    return segment or "pulse"


def _vault_paths(vault_dir: Path, cycle_id: str, generated_at: str) -> dict[str, str]:
    date_prefix = _date(generated_at)
    safe_cycle = _safe_path_segment(cycle_id)
    return {
        "dir": str(vault_dir),
        "index": str(vault_dir / "index.md"),
        "agents": str(vault_dir / "AGENTS.md"),
        "pulse": str(vault_dir / "pulses" / f"{date_prefix}-{safe_cycle}.md"),
        "work_packet": str(vault_dir / "work-packets" / f"{date_prefix}-{safe_cycle}.md"),
    }


def build_pulse_payload(
    *,
    repo_root: Path | str | None = None,
    config_path: Path | str | None = None,
    vault_dir: Path | str | None = None,
    loop_payload: dict[str, Any] | None = None,
    codex_status: dict[str, Any] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = now or utc_now()
    root = Path(repo_root or Path.cwd()).resolve()
    resolved_config = Path(config_path) if config_path else default_config_path(root)
    resolved_vault = Path(vault_dir).expanduser() if vault_dir else default_vault_dir()
    loop_payload = loop_payload if loop_payload is not None else _read_last_loop_payload()
    codex_status = codex_status if codex_status is not None else codex_cli_status(repo_root=root)
    generated_at = _iso(current)
    cycle_id = str((loop_payload or {}).get("cycle_id") or f"pulse-{current.strftime('%Y%m%dT%H%M%SZ')}")
    provider = summarize_provider_config(resolved_config)
    work_packet = build_work_packet(loop_payload, repo_root=root)
    status = "ready" if provider.get("codex_cli_configured") and codex_status.get("status") == "ok" else "degraded"
    return {
        "status": status,
        "generated_at": generated_at,
        "repo_root": str(root),
        "provider": provider,
        "codex": codex_status,
        "loop": loop_payload or {"status": "unavailable", "cycle_id": None},
        "work_packet": work_packet,
        "vault": _vault_paths(resolved_vault, cycle_id, generated_at),
    }


def render_index_markdown(payload: dict[str, Any]) -> str:
    vault = payload["vault"]
    provider = payload["provider"]
    codex = payload["codex"]
    loop = payload.get("loop") or {}
    generated_at = payload["generated_at"]
    pulse_name = Path(vault["pulse"]).stem
    packet_name = Path(vault["work_packet"]).stem
    return f"""---
type: cockpit
status: active
created: 2026-06-04
updated: {_date(generated_at)}
tags: [operator-kernel, etz-chaim, hermes, codex, pulse]
source: etzchaim-pulse
project: etz-chaim-ai
---

# Operator Kernel

Cockpit Obsidian pour le composant local de métacognition Etz Chaim extrait comme système nerveux opérateur.

## État courant

- Dernier pulse : [[pulses/{pulse_name}|{pulse_name}]]
- Dernier work packet : [[work-packets/{packet_name}|{packet_name}]]
- Statut : `{payload['status']}`
- Cycle : `{loop.get('cycle_id')}`
- Repo : `{payload['repo_root']}`

## IA branchée

- Fournisseur recommandé : Codex CLI
- Profil actif : `{provider.get('active_profile')}`
- Codex CLI configuré : `{provider.get('codex_cli_configured')}`
- Utilise une API key OpenAI : `{provider.get('uses_api_key')}`
- Codex CLI : `{codex.get('status')}` — `{codex.get('version')}`
- Binaire : `{codex.get('path')}`

## Rôle

- Hermès / Telegram : cockpit humain.
- Operator Kernel : observe, priorise, prépare.
- Codex CLI : cerveau IA subscription-backed quand un plan/travail est demandé.
- Obsidian : mémoire longue, rapports, décisions, work packets.

## Garde-fous

- Pas d'auto-réparation du corpus.
- Pas de suppression.
- Pas de push.
- Pas d'automatisation runtime cachée sans GO explicite.
"""


def render_pulse_markdown(payload: dict[str, Any]) -> str:
    loop = payload.get("loop") or {}
    heartbeat = loop.get("heartbeat") or {}
    improve = loop.get("improve") or {}
    issue = improve.get("top_issue") or {}
    provider = payload.get("provider") or {}
    codex = payload.get("codex") or {}
    return f"""---
type: report
status: active
created: {_date(payload['generated_at'])}
updated: {_date(payload['generated_at'])}
tags: [operator-kernel, pulse, etz-chaim, codex]
source: etzchaim-pulse
project: etz-chaim-ai
---

# Pulse — {loop.get('cycle_id')}

Generated at: `{payload['generated_at']}`

## Status

- payload_status: `{payload.get('status')}`
- loop_status: `{loop.get('status')}`
- guardian_verdict: `{heartbeat.get('guardian_verdict')}`
- applies_patch: `{heartbeat.get('applies_patch')}`
- action_count: `{heartbeat.get('action_count')}`

## Provider

- active_profile: `{provider.get('active_profile')}`
- codex_cli_configured: `{provider.get('codex_cli_configured')}`
- uses_api_key: `{provider.get('uses_api_key')}`
- codex_status: `{codex.get('status')}`
- codex_version: `{codex.get('version')}`

## Top issue

- id: `{issue.get('id')}`
- source: `{issue.get('source')}`
- severity: `{issue.get('severity')}`
- title: {issue.get('title')}
- verification: `{issue.get('verification_command')}`

## Work packet

[[work-packets/{Path(payload['vault']['work_packet']).stem}|Ouvrir le work packet Codex]]
"""


def render_work_packet_markdown(payload: dict[str, Any]) -> str:
    packet = payload["work_packet"]
    return f"""---
type: prompt
status: ready
created: {_date(payload['generated_at'])}
updated: {_date(payload['generated_at'])}
tags: [operator-kernel, codex, work-packet, etz-chaim]
source: etzchaim-pulse
project: etz-chaim-ai
---

# Work Packet — {(payload.get('loop') or {}).get('cycle_id')}

- Target agent: `{packet.get('target_agent')}`
- Status: `{packet.get('status')}`
- GO humain requis: `{packet.get('requires_human_go')}`
- Applies patch automatically: `{packet.get('applies_patch')}`
- Top issue: `{packet.get('top_issue_id')}`
- Action: `{packet.get('action_id')}`
- Verification: `{packet.get('verification_command')}`

## Prompt Codex copyable

```text
{packet.get('prompt')}
```
"""


def render_agents_markdown() -> str:
    return """---
type: rules
status: active
created: 2026-06-04
updated: 2026-06-04
tags: [operator-kernel, agents-md, etz-chaim]
---

# Operator Kernel — règles agents

Cette zone est un cockpit de contrôle, pas une zone d'exécution libre.

- Lire `index.md` puis le dernier fichier sous `pulses/`.
- Les fichiers `work-packets/` sont des prompts/briefs préparés pour Codex ou Hermès.
- Ne jamais modifier `sifrei_yesod` depuis cette zone.
- Ne jamais supprimer d'historique de pulses/work-packets.
- Ne pas activer cron, LaunchAgent ou service permanent sans GO explicite de Yohan.
- Toute mutation de code/corpus doit passer par un plan vérifiable puis validation humaine.
"""


def write_vault_pulse(payload: dict[str, Any]) -> dict[str, str]:
    vault = payload["vault"]
    paths = {key: Path(value) for key, value in vault.items() if key != "dir"}
    for path in paths.values():
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["index"].write_text(render_index_markdown(payload), encoding="utf-8")
    paths["pulse"].write_text(render_pulse_markdown(payload), encoding="utf-8")
    paths["work_packet"].write_text(render_work_packet_markdown(payload), encoding="utf-8")
    paths["agents"].write_text(render_agents_markdown(), encoding="utf-8")
    return {key: str(path) for key, path in paths.items()}


def run_loop_for_pulse(*, dry_run: bool, repo_root: Path | str | None = None) -> dict[str, Any]:
    return runtime_loop.run_loop_once(dry_run=dry_run, repo_root=repo_root or Path.cwd())
