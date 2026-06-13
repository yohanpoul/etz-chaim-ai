"""Config-driven local model call with MEASURED tokens. Zero hardcoded slug.

The model identifier is resolved through ``etzchaim.llm.model_registry.resolve_model``
(the single source of truth, ADR-0007). The provider + host are read as config
scalars from ``config.yaml``. The token counts are read straight off the Ollama
response (``prompt_eval_count`` / ``eval_count``) — they are measured, never
fabricated or estimated. If the response omits them, we raise rather than invent a
number (an honest harness must fail loud here).

Smoke uses the ``local_only`` profile (all olamot -> Ollama qwen3.5:9b). The real run
must point ``profile`` at a frontier tier (Haiku minimum); the call path is identical.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from etzchaim.llm.model_registry import resolve_model

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

# alias -> olam slot, mirroring model_registry._ALIAS_TO_OLAM (kept local to avoid
# importing a private symbol; the resolution itself still goes through resolve_model).
_ALIAS_TO_OLAM = {"opus": "atziluth", "sonnet": "yetzirah", "haiku": "assiah"}

_ENV_DEFAULT_RE = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")


def _expand_env(value: str) -> str:
    """Expand ``${VAR}`` and ``${VAR:-default}`` shell-style references."""

    def repl(m: re.Match[str]) -> str:
        name, default = m.group(1), m.group(2)
        return os.environ.get(name, default if default is not None else "")

    return _ENV_DEFAULT_RE.sub(repl, value)


@dataclass
class ModelCall:
    """One model call with MEASURED token usage."""

    text: str
    prompt_tokens: int
    completion_tokens: int
    model: str
    provider: str
    done_reason: str | None = None
    latency_ms: int = 0
    cost_usd: float = 0.0  # measured from the provider when available (Ollama leaves 0)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class _Resolved:
    provider: str
    model: str
    host: str
    options: dict[str, Any]


def _load_config() -> dict[str, Any]:
    with CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh) or {}


def resolve_local(alias: str = "haiku", profile: str = "local_only") -> _Resolved:
    """Resolve (provider, model, host, options) for ``alias`` in ``profile``.

    The model slug comes from ``resolve_model`` (config single source). The provider
    and host come from the same ``config.yaml`` block. We assert the provider is
    ``ollama`` so the smoke cannot silently degrade into a fabricated-token path on an
    unconfigured backend.
    """
    cfg = _load_config()
    olam = _ALIAS_TO_OLAM.get(alias)
    if olam is None:
        raise ValueError(
            f"unknown alias {alias!r}; known: {sorted(_ALIAS_TO_OLAM)}"
        )
    slot = (
        cfg.get("profiles", {}).get(profile, {}).get("olamot", {}).get(olam, {})
    )
    provider = slot.get("provider")
    if provider != "ollama":
        raise RuntimeError(
            f"profile {profile!r} olam {olam!r} provider is {provider!r}, not "
            f"'ollama'. The smoke runs measured-token local calls only; point a "
            f"frontier run at the real provider explicitly."
        )
    model = resolve_model(alias, profile=profile)  # config-driven, zero hardcode
    host = _expand_env(str(cfg.get("ollama", {}).get("host", "http://localhost:11434")))
    options = dict(slot.get("options") or {})
    return _Resolved(provider=provider, model=model, host=host, options=options)


def chat(
    messages: list[dict[str, str]],
    *,
    alias: str = "haiku",
    profile: str = "local_only",
    seed: int = 7,
    num_predict: int = 768,
    timeout: int = 180,
) -> ModelCall:
    """Call Ollama /api/chat (stream off) and return text + MEASURED tokens.

    Determinism: temperature forced to 0 + a fixed seed, so identical prompts yield
    identical outputs (lets A0 re-attempt rate be interpretable across two sessions).
    """
    import time

    r = resolve_local(alias, profile)
    options = dict(r.options)
    options["temperature"] = 0
    options["seed"] = seed
    options["num_predict"] = num_predict

    payload = {
        "model": r.model,
        "messages": messages,
        "stream": False,
        "options": options,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{r.host}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:  # network / daemon down — fail loud, no fake
        raise RuntimeError(f"Ollama call failed ({r.host}): {e}") from e
    latency_ms = int((time.time() - t0) * 1000)

    # MEASURED tokens — read straight off the provider response. No fallback values:
    # a missing count is a hard error, never an invented number.
    if "prompt_eval_count" not in body or "eval_count" not in body:
        raise RuntimeError(
            "Ollama response missing token counts (prompt_eval_count/eval_count); "
            "refusing to fabricate. Keys present: " + ", ".join(sorted(body))
        )
    return ModelCall(
        text=body.get("message", {}).get("content", ""),
        prompt_tokens=int(body["prompt_eval_count"]),
        completion_tokens=int(body["eval_count"]),
        model=r.model,
        provider=r.provider,
        done_reason=body.get("done_reason"),
        latency_ms=latency_ms,
    )


def chat_claude_cli(
    messages: list[dict[str, str]],
    *,
    alias: str = "haiku",
    profile: str = "anthropic_full",
    max_turns: int = 1,
    timeout: int = 180,
) -> ModelCall:
    """Frontier (Haiku) call via the OAuth Max Claude CLI — MEASURED tokens + cost.

    Reuses ``benchmarks.claude_cli.ClaudeCLIInvoker`` (forces the OAuth path; reads
    ``usage.input_tokens``/``output_tokens`` and ``total_cost_usd`` straight off the CLI
    JSON — measured, never fabricated).

    The model slug is resolved through ``resolve_model`` (config single source) and
    guarded against a stale slug: only a current Haiku 4.5 slug is accepted, so the
    Phase-0 ``claude-*-20250514`` regression cannot slip through and the stale
    ``claude_cli.DEFAULT_MODEL`` is never used.
    """
    slug = resolve_model(alias, profile=profile)
    if "haiku-4-5" not in slug:
        raise RuntimeError(
            f"resolved model {slug!r} is not a current Haiku 4.5 slug — refusing "
            f"(stale-slug guard; cf the Phase-0 claude-*-20250514 bug)."
        )

    system = "\n\n".join(
        m["content"] for m in messages if m.get("role") == "system"
    )
    prompt = "\n\n".join(
        m["content"] for m in messages if m.get("role") == "user"
    )

    from benchmarks.claude_cli import ClaudeCLIInvoker

    invoker = ClaudeCLIInvoker()
    kwargs: dict = {"model": slug, "max_turns": max_turns, "timeout": timeout}
    if system:
        kwargs["system_prompt"] = system
    result = invoker.invoke(prompt, **kwargs)
    if not result.success:
        raise RuntimeError(
            f"claude CLI call failed (model={slug}): {result.error}"
        )
    return ModelCall(
        text=result.text,
        prompt_tokens=result.usage_input,       # MEASURED
        completion_tokens=result.usage_output,  # MEASURED
        model=slug,
        provider="anthropic_oauth_cli",
        done_reason=result.stop_reason,
        latency_ms=result.duration_ms,
        cost_usd=result.cost_usd,               # MEASURED (CLI total_cost_usd)
    )
