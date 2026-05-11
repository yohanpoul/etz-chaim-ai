"""Unit tests for etzchaim.llm.model_registry.

Tests use synthetic ``config.yaml`` files written to ``tmp_path`` so they don't
depend on the repo-root config. One smoke test exercises the module-level
singleton against the real config.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from etzchaim.llm.model_registry import (
    ModelRegistry,
    UnknownModelError,
    get_active_profile,
    list_aliases,
    resolve_model,
    resolve_model_for_task,
)

CONFIG_TEMPLATE = """\
active_profile: {active_profile}
profiles:
  anthropic_full:
    olamot:
      atziluth:
        provider: litellm
        model: anthropic/claude-opus-4-7
      briah:
        provider: litellm
        model: anthropic/claude-opus-4-7
      yetzirah:
        provider: litellm
        model: anthropic/claude-sonnet-4-6
      assiah:
        provider: litellm
        model: anthropic/claude-haiku-4-5
  benchmark_opus:
    olamot:
      atziluth:
        provider: litellm
        model: anthropic/claude-opus-4-20250514
      briah:
        provider: litellm
        model: anthropic/claude-opus-4-20250514
      yetzirah:
        provider: litellm
        model: anthropic/claude-opus-4-20250514
      assiah:
        provider: litellm
        model: anthropic/claude-opus-4-20250514
  openai_full:
    olamot:
      atziluth:
        provider: litellm
        model: openai/gpt-5
      briah:
        provider: litellm
        model: openai/o1
      yetzirah:
        provider: litellm
        model: openai/gpt-5-mini
      assiah:
        provider: litellm
        model: openai/gpt-5-nano
"""


def _write_config(tmp_path: Path, active_profile: str) -> Path:
    cfg = tmp_path / "config.yaml"
    cfg.write_text(CONFIG_TEMPLATE.format(active_profile=active_profile))
    return cfg


@pytest.fixture
def registry_anthropic(tmp_path: Path) -> ModelRegistry:
    return ModelRegistry(config_path=_write_config(tmp_path, "anthropic_full"))


@pytest.fixture
def registry_openai(tmp_path: Path) -> ModelRegistry:
    return ModelRegistry(config_path=_write_config(tmp_path, "openai_full"))


def test_resolves_opus_for_anthropic_full(registry_anthropic: ModelRegistry) -> None:
    assert registry_anthropic.resolve("opus") == "claude-opus-4-7"


def test_active_profile_default(registry_anthropic: ModelRegistry) -> None:
    assert registry_anthropic.active_profile() == "anthropic_full"
    assert registry_anthropic.resolve("sonnet") == "claude-sonnet-4-6"
    assert registry_anthropic.resolve("haiku") == "claude-haiku-4-5"


def test_resolve_with_explicit_profile_override(
    registry_anthropic: ModelRegistry,
) -> None:
    out = registry_anthropic.resolve("opus", profile="benchmark_opus")
    assert out == "claude-opus-4-20250514"


def test_unknown_alias_raises(registry_anthropic: ModelRegistry) -> None:
    with pytest.raises(UnknownModelError) as exc:
        registry_anthropic.resolve("does-not-exist")
    msg = str(exc.value)
    assert "does-not-exist" in msg
    assert "opus" in msg
    assert "sonnet" in msg
    assert "haiku" in msg


def test_resolve_model_for_task_deep_reasoning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = _write_config(tmp_path, "anthropic_full")
    monkeypatch.setenv("ETZCHAIM_CONFIG", str(cfg))

    import importlib

    import etzchaim.llm.model_registry as mr

    importlib.reload(mr)
    try:
        assert mr.resolve_model_for_task("deep-reasoning") == "claude-opus-4-7"
        assert mr.resolve_model_for_task("fast-dispatch") == "claude-haiku-4-5"
    finally:
        monkeypatch.delenv("ETZCHAIM_CONFIG", raising=False)
        importlib.reload(mr)


def test_get_active_profile_smoke() -> None:
    profile = get_active_profile()
    assert isinstance(profile, str) and profile


def test_list_aliases_nonempty_smoke() -> None:
    aliases = list_aliases()
    for required in ("opus", "sonnet", "haiku", "primary", "mid", "fast"):
        assert required in aliases, f"missing alias {required!r} in {aliases!r}"


def test_cache_invalidates_on_mtime_change(tmp_path: Path) -> None:
    cfg = _write_config(tmp_path, "anthropic_full")
    reg = ModelRegistry(config_path=cfg)
    assert reg.resolve("opus") == "claude-opus-4-7"

    cfg.write_text(
        CONFIG_TEMPLATE.format(active_profile="anthropic_full").replace(
            "anthropic/claude-opus-4-7",
            "anthropic/claude-opus-4-20250514",
            1,
        )
    )
    future = time.time() + 10
    os.utime(cfg, (future, future))

    assert reg.resolve("opus") == "claude-opus-4-20250514"


def test_provider_prefix_stripped(registry_anthropic: ModelRegistry) -> None:
    assert "/" not in registry_anthropic.resolve("opus")
    assert "/" not in registry_anthropic.resolve("opus", profile="benchmark_opus")


def test_alias_substring_fallback_for_gpt5(registry_openai: ModelRegistry) -> None:
    assert registry_openai.resolve("gpt-5-mini") == "gpt-5-mini"
    assert registry_openai.resolve("gpt-5-nano") == "gpt-5-nano"


def test_module_singleton_smoke() -> None:
    slug = resolve_model("opus")
    assert isinstance(slug, str) and slug
    assert "/" not in slug


def test_missing_active_profile_raises(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    cfg.write_text("profiles: {}\n")
    reg = ModelRegistry(config_path=cfg)
    with pytest.raises(RuntimeError, match="active_profile"):
        reg.active_profile()
