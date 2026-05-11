"""Single source of truth for model alias resolution.

`config.yaml` declares one or more provider profiles. Each profile maps four
reasoning tiers (atziluth/briah/yetzirah/assiah — internal names; see
`.claude/rules/public-surface-neutrality.md` for the public aliases) to a
model identifier such as ``anthropic/claude-opus-4-7``, ``openai/gpt-5``, or
the CLI alias ``opus``.

This module exposes :func:`resolve_model` and a handful of helpers that map
friendly aliases (``opus``/``primary``, ``sonnet``/``mid``, ``haiku``/``fast``,
``thinking``/``reasoning``) and substring matches (``gpt-5``, ``gemini-3-pro``)
to the bare slug declared in the active profile. The provider prefix (``anthropic/``,
``openai/``, ``bedrock/`` …) is stripped so callers passing the slug to the
Anthropic SDK or any other slug-only API keep working as before.

Implements ADR-0007 (`memory/DECISIONS.md`).
"""
from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class UnknownModelError(KeyError):
    """Raised when an alias cannot be resolved against the active profile."""

    def __init__(self, alias: str, available: list[str], profile: str) -> None:
        self.alias = alias
        self.available = sorted(available)
        self.profile = profile
        self.message = (
            f"Unknown model alias {alias!r} for profile {profile!r}. "
            f"Available aliases: {', '.join(self.available)}"
        )
        super().__init__(self.message)

    def __str__(self) -> str:
        return self.message


_ALIAS_TO_OLAM: dict[str, str] = {
    "opus": "atziluth",
    "primary": "atziluth",
    "sonnet": "yetzirah",
    "mid": "yetzirah",
    "haiku": "assiah",
    "fast": "assiah",
    "thinking": "briah",
    "reasoning": "briah",
}

# TODO Sprint 1.B: move this static map into a `tasks:` block in config.yaml so
# downstream task-keyed routing can be reconfigured without code changes.
_TASK_TO_ALIAS: dict[str, str] = {
    "deep-reasoning": "opus",
    "mid-tier": "sonnet",
    "fast-dispatch": "haiku",
    "thinking": "thinking",
}


def _discover_config_path() -> Path:
    """Locate ``config.yaml``.

    Resolution order:
      1. ``$ETZCHAIM_CONFIG`` (explicit override; used by tests).
      2. Repo-root ``config.yaml`` walking upward from this module — works for
         dev installs and editable installs.
      3. ``etzchaim/_paths.py::config_path()`` (user state dir, populated by
         ``etzchaim onboard``).

    Raises:
        FileNotFoundError: no candidate was found.
    """
    override = os.environ.get("ETZCHAIM_CONFIG")
    if override:
        p = Path(override)
        if p.is_file():
            return p

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "config.yaml"
        if candidate.is_file():
            return candidate

    from etzchaim._paths import config_path as _user_config_path

    user_path = _user_config_path()
    if user_path.is_file():
        return user_path

    raise FileNotFoundError(
        "Could not locate config.yaml. Set ETZCHAIM_CONFIG or run "
        "`etzchaim onboard` to install a user config."
    )


def _strip_provider_prefix(slug: str) -> str:
    """Strip a LiteLLM-style ``<provider>/`` prefix if present.

    ``anthropic/claude-opus-4-7`` → ``claude-opus-4-7``
    ``bedrock/anthropic.claude-opus-4-7-v1:0`` → ``anthropic.claude-opus-4-7-v1:0``
    ``opus`` → ``opus`` (unchanged; CLI aliases survive untouched).
    """
    head, sep, tail = slug.partition("/")
    return tail if sep and tail else slug


class ModelRegistry:
    """Lazy, mtime-invalidated reader of ``config.yaml`` for model aliases.

    A single module-level instance (:data:`_REGISTRY`) is created at import
    time. Tests instantiate their own when they need to point at a synthetic
    config file via the ``config_path`` argument.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        self._config_path = config_path
        self._cache: dict[str, Any] | None = None
        self._cache_mtime: float | None = None
        self._lock = threading.Lock()

    @property
    def config_path(self) -> Path:
        if self._config_path is None:
            self._config_path = _discover_config_path()
        return self._config_path

    def _maybe_reload(self) -> dict[str, Any]:
        path = self.config_path
        mtime = path.stat().st_mtime
        with self._lock:
            if self._cache is None or mtime != self._cache_mtime:
                with path.open() as fh:
                    self._cache = yaml.safe_load(fh) or {}
                self._cache_mtime = mtime
                self._log_boot_snapshot()
            return self._cache

    def _log_boot_snapshot(self) -> None:
        if self._cache is None:
            return
        profile = self._cache.get("active_profile", "<unset>")
        olamot = (
            self._cache.get("profiles", {})
            .get(profile, {})
            .get("olamot", {})
        )
        mapping_parts: list[str] = []
        for alias, olam in (("opus", "atziluth"), ("sonnet", "yetzirah"), ("haiku", "assiah")):
            slot = olamot.get(olam, {})
            raw = slot.get("model")
            if raw:
                mapping_parts.append(f"{alias}->{_strip_provider_prefix(raw)}")
        logger.info(
            "[model_registry] profile=%s | %s",
            profile,
            " | ".join(mapping_parts) if mapping_parts else "<no aliases>",
        )

    def active_profile(self) -> str:
        cache = self._maybe_reload()
        profile = cache.get("active_profile")
        if not isinstance(profile, str) or not profile:
            raise RuntimeError(
                f"config.yaml at {self.config_path} has no string "
                "'active_profile' key."
            )
        return profile

    def _profile_block(self, profile: str) -> dict[str, Any]:
        cache = self._maybe_reload()
        profiles = cache.get("profiles") or {}
        block = profiles.get(profile)
        if not isinstance(block, dict):
            available = sorted(profiles.keys())
            raise UnknownModelError(
                alias=f"<profile:{profile}>",
                available=available,
                profile=profile,
            )
        return block

    def _profile_aliases(self, profile: str) -> dict[str, str]:
        """Return ``{alias: bare_slug}`` for every alias resolvable in ``profile``.

        Aliases come from two sources:
          * the structural :data:`_ALIAS_TO_OLAM` table (one per olam slot);
          * a substring match for free-form aliases (``gpt-5``, ``gemini-3-pro``).
        """
        block = self._profile_block(profile)
        olamot = block.get("olamot") or {}
        result: dict[str, str] = {}

        for alias, olam in _ALIAS_TO_OLAM.items():
            slot = olamot.get(olam)
            if not isinstance(slot, dict):
                continue
            raw = slot.get("model")
            if not raw:
                continue
            result[alias] = _strip_provider_prefix(str(raw))

        return result

    def list_aliases(self, profile: str | None = None) -> list[str]:
        profile = profile or self.active_profile()
        return sorted(self._profile_aliases(profile))

    def resolve(self, alias: str, profile: str | None = None) -> str:
        if not isinstance(alias, str) or not alias:
            raise UnknownModelError(alias=str(alias), available=[], profile=profile or "")
        profile = profile or self.active_profile()
        aliases = self._profile_aliases(profile)

        if alias in aliases:
            return aliases[alias]

        block = self._profile_block(profile)
        olamot = block.get("olamot") or {}
        substring_hits: list[str] = []
        for slot in olamot.values():
            if not isinstance(slot, dict):
                continue
            raw = slot.get("model")
            if not raw:
                continue
            bare = _strip_provider_prefix(str(raw))
            if alias.lower() in bare.lower():
                substring_hits.append(bare)
        deduped = sorted(set(substring_hits))
        if len(deduped) == 1:
            return deduped[0]

        raise UnknownModelError(
            alias=alias,
            available=list(aliases.keys()),
            profile=profile,
        )

    def resolve_for_task(self, task: str) -> str:
        alias = _TASK_TO_ALIAS.get(task)
        if alias is None:
            raise UnknownModelError(
                alias=f"<task:{task}>",
                available=list(_TASK_TO_ALIAS),
                profile=self.active_profile(),
            )
        return self.resolve(alias)


_REGISTRY = ModelRegistry()


def resolve_model(alias: str, profile: str | None = None) -> str:
    """Return the bare model slug for ``alias`` in ``profile`` (or active profile).

    Examples:
        >>> resolve_model("opus")                       # active profile lookup
        'claude-opus-4-7'
        >>> resolve_model("opus", profile="benchmark_opus")
        'claude-opus-4-20250514'

    Raises:
        UnknownModelError: alias not resolvable in the requested profile.
    """
    return _REGISTRY.resolve(alias, profile=profile)


def resolve_model_for_task(task: str) -> str:
    """Return the bare model slug for a task-keyed alias (``deep-reasoning`` …)."""
    return _REGISTRY.resolve_for_task(task)


def get_active_profile() -> str:
    """Return the ``active_profile`` declared in ``config.yaml``."""
    return _REGISTRY.active_profile()


def list_aliases(profile: str | None = None) -> list[str]:
    """Return aliases resolvable in ``profile`` (or the active profile)."""
    return _REGISTRY.list_aliases(profile=profile)


__all__ = [
    "ModelRegistry",
    "UnknownModelError",
    "get_active_profile",
    "list_aliases",
    "resolve_model",
    "resolve_model_for_task",
]
