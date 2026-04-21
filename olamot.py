"""Olamot — les 4 Mondes comme tiers de modèles LLM.

עוֹלָמוֹת — Chaque monde est un niveau de réalité,
chaque niveau de réalité est un modèle.

    Atziluth  → stratégie (Claude Opus / API / Claude Code CLI)
    Briah     → raisonnement profond (Claude Opus / Ollama thinking)
    Yetzirah  → tâches courantes (Claude Sonnet / Ollama)
    Assiah    → exécution rapide (Claude Haiku / Ollama)

Providers supportés :
    "ollama"      — Ollama local (qwen3.5:9b, etc.)
    "claude_code" — Claude Code CLI via subprocess (abonnement Max)
    "anthropic"   — API Anthropic directe (nécessite ANTHROPIC_API_KEY)

Le provider actif est déterminé par active_profile dans config.yaml.
Pour switcher : modifier active_profile ou utiliser etz_provider.py.

Usage:
    from olamot import config, get_model, ollama_generate

    # Obtenir le modèle pour un monde
    model = get_model("briah")          # dépend du profil actif

    # Obtenir le modèle pour une sephirah
    model = get_model_for("binah")      # → briah → modèle du profil

    # Appeler le LLM (dispatch automatique selon provider)
    response = ollama_generate("briah", "Explain causality",
        kavvanah={"intention": "...", "critere_succes": "...", "anti_pattern": "..."})
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

import yaml

from masakh import Masakh, write_reshimo
from masakh.context_assembler import ContextAssembler
from masakh.context_monitor import ContextMonitor

# ─── Circuit breaker Ollama ───────────────────────────────────
# Pattern copié de pool.py. Quand Ollama est down, chaque appel
# rejoue 3 retries (12s perdues). Le circuit breaker fast-fail
# après 5 échecs consécutifs, cooldown 30s avant re-test.

import threading as _ollama_threading

_OLLAMA_CB_THRESHOLD = 5       # Ouvrir après N échecs consécutifs
_OLLAMA_CB_COOLDOWN = 30.0     # Secondes avant re-test
_ollama_cb_failures = 0
_ollama_cb_open_until = 0.0
_ollama_cb_lock = _ollama_threading.Lock()


class OllamaCircuitOpenError(RuntimeError):
    """Circuit breaker Ollama ouvert — trop d'échecs consécutifs."""


def _ollama_cb_check() -> None:
    """Lever OllamaCircuitOpenError si le circuit est ouvert.

    Pattern half-open (cf. pool.py:_cb_is_open) : quand le cooldown
    expire, on reset le compteur à 0 pour que le premier échec
    post-cooldown ne re-ouvre pas le circuit immédiatement.
    """
    global _ollama_cb_failures, _ollama_cb_open_until
    with _ollama_cb_lock:
        if _ollama_cb_failures >= _OLLAMA_CB_THRESHOLD:
            if time.monotonic() < _ollama_cb_open_until:
                raise OllamaCircuitOpenError(
                    f"Ollama circuit open — {_ollama_cb_failures} failures, "
                    f"cooldown {_OLLAMA_CB_COOLDOWN}s"
                )
            # Cooldown expiré → half-open : reset pour une vraie fenêtre
            # de récupération (sinon le 1er échec post-cooldown ferait 6
            # et re-ouvrirait immédiatement).
            _ollama_cb_failures = 0
            _ollama_cb_open_until = 0.0
            log.info("Ollama circuit half-open — tentative de reconnexion")


def _ollama_cb_success() -> None:
    global _ollama_cb_failures, _ollama_cb_open_until
    with _ollama_cb_lock:
        _ollama_cb_failures = 0
        _ollama_cb_open_until = 0.0


def _ollama_cb_failure() -> None:
    global _ollama_cb_failures, _ollama_cb_open_until
    with _ollama_cb_lock:
        _ollama_cb_failures += 1
        if _ollama_cb_failures >= _OLLAMA_CB_THRESHOLD:
            _ollama_cb_open_until = time.monotonic() + _OLLAMA_CB_COOLDOWN
            log.warning(
                "Ollama circuit OPEN — %d consecutive failures, "
                "cooldown %.0fs",
                _ollama_cb_failures, _OLLAMA_CB_COOLDOWN,
            )


# ─── Fallback cache d'embeddings ──────────────────────────────
# Filet de sécurité quand Ollama est down : les requêtes répétées
# pendant une panne peuvent encore servir depuis le cache. Pas un
# remplacement d'Ollama — juste une protection contre les SPOF
# transitoires sur un pipeline critique (embedding = porte de Yesod).

import hashlib as _hashlib
from collections import OrderedDict as _OrderedDict

_EMBED_CACHE_MAX_SIZE = 512
_embed_cache: "_OrderedDict[tuple[str, str], list[float]]" = _OrderedDict()
_embed_cache_lock = _ollama_threading.Lock()


def _embed_cache_key(model: str, text: str) -> tuple[str, str]:
    digest = _hashlib.sha256(text.encode("utf-8")).hexdigest()
    return (model, digest)


def _embed_cache_get(model: str, text: str) -> list[float] | None:
    key = _embed_cache_key(model, text)
    with _embed_cache_lock:
        vec = _embed_cache.get(key)
        if vec is None:
            return None
        _embed_cache.move_to_end(key)
        return list(vec)


def _embed_cache_put(model: str, text: str, vec: list[float]) -> None:
    if not vec:
        return
    key = _embed_cache_key(model, text)
    with _embed_cache_lock:
        _embed_cache[key] = list(vec)
        _embed_cache.move_to_end(key)
        while len(_embed_cache) > _EMBED_CACHE_MAX_SIZE:
            _embed_cache.popitem(last=False)


def _embed_cache_clear() -> None:
    """Vider le cache (utile pour les tests)."""
    with _embed_cache_lock:
        _embed_cache.clear()


# Résoudre le chemin complet de la CLI Claude une seule fois.
# Nécessaire car le serveur web (Flask) peut être lancé avec un PATH
# qui ne contient pas ~/.local/bin.
import shutil as _shutil
_CLAUDE_BIN = (
    _shutil.which("claude")
    or os.path.expanduser("~/.local/bin/claude")
)


def _get_db_conn():
    """Obtenir une connexion DB pour persister les Reshimot.

    Retourne None si le pool n'est pas disponible — dégradation gracieuse.
    """
    try:
        from pool import get_conn
        return get_conn()
    except Exception:
        return None


# ─── Chargement du config ────────────────────────────────────

_CONFIG_PATH = Path(__file__).parent / "config.yaml"
_config: dict | None = None


def _load_config() -> dict:
    global _config
    if _config is None:
        with open(_CONFIG_PATH) as f:
            _config = yaml.safe_load(f)
    return _config


def reload_config() -> dict:
    """Forcer le rechargement (après édition du config.yaml)."""
    global _config
    _config = None
    return _load_config()


@property
def config() -> dict:
    return _load_config()


# ─── Profils & accès aux modèles ────────────────────────────

def get_active_profile_name() -> str:
    """Nom du profil LLM actif."""
    cfg = _load_config()
    return cfg.get("active_profile", "ollama_local")


def get_active_profile() -> dict:
    """Retourne la config du profil LLM actif.

    Structure: {"olamot": {olam: {...}}, "embedding": {...}, "description": "..."}
    """
    cfg = _load_config()
    profile_name = cfg.get("active_profile", "ollama_local")
    profiles = cfg.get("profiles", {})
    profile = profiles.get(profile_name)
    if not profile:
        raise KeyError(f"Profil inconnu: {profile_name}. Disponibles: {list(profiles.keys())}")
    return profile


def _get_olam_config(olam: str) -> dict:
    """Config complète d'un olam depuis le profil actif."""
    profile = get_active_profile()
    olamot = profile.get("olamot", {})
    olam_cfg = olamot.get(olam)
    if not olam_cfg:
        raise KeyError(f"Olam inconnu dans le profil: {olam}")
    return olam_cfg


def get_model(olam: str) -> str:
    """Obtenir le nom du modèle pour un monde.

    Args:
        olam: "atziluth", "briah", "yetzirah", ou "assiah"
    """
    return _get_olam_config(olam)["model"]


def get_provider(olam: str) -> str:
    """Obtenir le provider pour un monde ("ollama", "claude_code", ou "anthropic")."""
    return _get_olam_config(olam).get("provider", "ollama")


def get_options(olam: str) -> dict:
    """Obtenir les options Ollama pour un monde."""
    return _get_olam_config(olam).get("options", {})


# ─── Avertissement température non supportée (audit cycle 4, I5) ─
# La CLI `claude` n'expose AUCUN flag de sampling : ni --temperature,
# ni --top-p, ni seed. Les valeurs sous `options.temperature` du profil
# claude_max sont donc IGNORÉES par claude_code_generate. Ne pas faire
# semblant de les passer — émettre un warning une fois par olam pour
# que l'utilisateur sache que la "reproductibilité par température" est
# une propriété du provider ollama, pas de claude_code.
_TEMP_WARNING_EMITTED: set[str] = set()


def _warn_temperature_unsupported_for_claude_code(olam: str) -> None:
    """Avertir une seule fois par olam si température configurée mais ignorée."""
    if olam in _TEMP_WARNING_EMITTED:
        return
    try:
        cfg = _get_olam_config(olam)
    except KeyError:
        return
    if cfg.get("provider") != "claude_code":
        return
    temp = cfg.get("options", {}).get("temperature")
    if temp is None:
        return
    _TEMP_WARNING_EMITTED.add(olam)
    log.warning(
        "Profil claude_code (olam=%s) configure temperature=%s mais la CLI "
        "`claude` n'expose pas de flag --temperature. Valeur IGNORÉE — "
        "reproductibilité par température impossible avec ce provider.",
        olam, temp,
    )


def get_think(olam: str) -> bool:
    """Obtenir le mode thinking pour un monde (défaut: False)."""
    return _get_olam_config(olam).get("think", False)


def get_timeout(olam: str) -> int:
    """Obtenir le timeout en secondes pour un monde."""
    return _get_olam_config(olam).get("timeout", 120)


def get_model_for(sephirah: str) -> str:
    """Obtenir le modèle pour une sephirah (via son olam assigné).

    Args:
        sephirah: "yesod", "hod", "binah", etc.
    """
    cfg = _load_config()
    seph = cfg["sephirot"].get(sephirah)
    if not seph:
        raise KeyError(f"Sephirah inconnue: {sephirah}")
    return get_model(seph["olam"])


def get_judge_model_for(sephirah: str) -> str:
    """Obtenir le modèle juge pour une sephirah (si défini).

    Hod (SelfMap) a un judge_olam séparé — le juge doit être
    plus fort que le jugé.
    """
    cfg = _load_config()
    seph = cfg["sephirot"].get(sephirah)
    if not seph:
        raise KeyError(f"Sephirah inconnue: {sephirah}")
    judge_olam = seph.get("judge_olam", seph["olam"])
    return get_model(judge_olam)


def get_embedding_model() -> str:
    """Obtenir le modèle d'embedding depuis le profil actif."""
    profile = get_active_profile()
    emb = profile.get("embedding", {})
    return emb.get("model", "nomic-embed-text")


def get_ollama_host() -> str:
    """Obtenir l'URL d'Ollama."""
    cfg = _load_config()
    return cfg["ollama"]["host"]


def get_context_window(olam: str) -> int:
    """Obtenir la taille du context window pour un monde (en tokens)."""
    olam_cfg = _get_olam_config(olam)
    # Ollama : num_ctx dans options
    ctx = olam_cfg.get("options", {}).get("num_ctx")
    if ctx:
        return ctx
    # Claude Code / Anthropic : pas de num_ctx, grande fenêtre par défaut
    return 200_000


# ─── Claude Code CLI ─────────────────────────────────────────

def claude_code_generate(
    olam: str,
    prompt: str,
    timeout: int | None = None,
    model: str | None = None,
    **kwargs,
) -> tuple[str, float]:
    """Appeler Claude Code CLI (abonnement Max) pour la génération.

    כְּלִי חָדָשׁ — Un nouveau Kli (réceptacle) pour la Lumière.
    Claude Code CLI comme canal : le prompt descend, la réponse remonte.

    Inclut retry avec backoff exponentiel sur rate limit/overloaded.

    Args:
        olam: Le monde ("atziluth", "briah", "yetzirah", "assiah")
        prompt: Le prompt à envoyer
        timeout: Timeout en secondes (None = lire depuis config.yaml)
        model: Override le modèle du profil

    Returns:
        (response_text, latency_ms)

    Note:
        La CLI `claude` ne supporte pas --temperature ni autre flag de
        sampling — les valeurs `options.temperature` du profil claude_max
        sont IGNORÉES (audit cycle 4, I5). Un warning est émis une fois
        par olam au premier appel pour signaler ce gap.
    """
    model = model or get_model(olam)
    timeout = timeout or get_timeout(olam)

    # Opus tente des tool_use même avec --tools "". En mode text, seul le
    # texte avant la première tentative est capturé. En mode JSON, le champ
    # "result" contient la réponse finale complète après les cycles d'échec.
    _CLI_SYSTEM_PROMPT = (
        "IMPORTANT: Tu es en mode texte pur. Tu ne peux PAS lire de fichiers, "
        "PAS utiliser d'outils, PAS executer de commandes. Reponds UNIQUEMENT "
        "avec tes connaissances. Si on te demande d'analyser du code, donne "
        "une analyse theorique basee sur l'architecture decrite."
    )

    # ── v0.2 : Dispatch to anthropic SDK when ANTHROPIC_API_KEY is set ──
    # Container-safe path (no interactive auth). Falls back to CLI subprocess
    # below if only the legacy CLI is available.
    try:
        from etzchaim.providers.registry import select_claude_backend
        backend = select_claude_backend()
    except RuntimeError:
        backend = "claude_cli"  # let the CLI path emit its own error if binary missing
    if backend == "anthropic_sdk":
        from etzchaim.providers.anthropic_sdk import AnthropicSDKProvider
        options = get_options(olam) or {}
        temperature = float(options.get("temperature", 0.7))
        max_tokens = int(options.get("num_predict", 4096))
        thinking_mode = bool(get_think(olam))
        provider = AnthropicSDKProvider()
        text, latency_ms = provider.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system_prompt=_CLI_SYSTEM_PROMPT,
            thinking=thinking_mode,
        )
        return text, float(latency_ms)

    # ── Legacy CLI subprocess path (pre-v0.2, native hosts with authed claude) ──
    _warn_temperature_unsupported_for_claude_code(olam)

    cmd = [
        _CLAUDE_BIN, "-p",
        "--output-format", "json",
        "--model", model,
        "--no-session-persistence",
        "--max-turns", "10",
        "--system-prompt", _CLI_SYSTEM_PROMPT,
        "--tools", "",
        "--disable-slash-commands",
        "--strict-mcp-config",
    ]

    # Environnement propre sans ANTHROPIC_API_KEY pour forcer l'auth Max
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    # ── Retry avec backoff sur rate limit / overloaded ──
    MAX_RETRIES = 3
    BACKOFF_BASE = 5  # 5s, 10s, 20s

    for attempt in range(MAX_RETRIES):
        t0 = time.monotonic()
        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=clean_env,
            )
            latency = (time.monotonic() - t0) * 1000

            # ── Détecter le rate limit AVANT de parser le JSON ──
            stderr_lower = (result.stderr or "").lower()
            if result.returncode != 0 and (
                "rate limit" in stderr_lower
                or "overloaded" in stderr_lower
                or "429" in stderr_lower
                or "too many requests" in stderr_lower
            ):
                backoff = BACKOFF_BASE * (2 ** attempt)
                log.warning(
                    "Rate limit détecté (olam=%s, tentative %d/%d) — "
                    "backoff %ds",
                    olam, attempt + 1, MAX_RETRIES, backoff,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)
                    continue
                return f"[Erreur: rate limit après {MAX_RETRIES} tentatives]", latency

            # Parse JSON — extraire "result" qui contient la réponse finale
            try:
                data = json.loads(result.stdout)
                response_text = data.get("result", "").strip()
                if not response_text and result.returncode != 0:
                    err = data.get("subtype", "unknown_error")
                    # Vérifier rate limit dans la réponse JSON aussi
                    if "rate" in str(err).lower() or "overloaded" in str(err).lower():
                        backoff = BACKOFF_BASE * (2 ** attempt)
                        log.warning("Rate limit (JSON) olam=%s — backoff %ds", olam, backoff)
                        if attempt < MAX_RETRIES - 1:
                            time.sleep(backoff)
                            continue
                    log.error("Claude Code error (olam=%s, model=%s): %s", olam, model, err)
                    return f"[Erreur Claude Code: {err}]", latency
                return response_text, latency
            except json.JSONDecodeError:
                # Fallback : stdout brut si pas JSON
                if result.returncode != 0:
                    err = result.stderr[:500].strip() or result.stdout[:500].strip()
                    log.error("Claude Code error (olam=%s, model=%s): %s", olam, model, err)
                    return f"[Erreur Claude Code: {err[:200]}]", latency
                return result.stdout.strip(), latency

        except subprocess.TimeoutExpired:
            latency = (time.monotonic() - t0) * 1000
            log.error("Claude Code timeout (%ss) pour olam=%s", timeout, olam)
            return f"[Erreur: timeout {timeout}s depasse]", latency
        except FileNotFoundError:
            latency = (time.monotonic() - t0) * 1000
            log.error("CLI 'claude' non trouvee. Installer: npm install -g @anthropic-ai/claude-code")
            return "[Erreur: claude CLI non installee]", latency
        except Exception as e:
            latency = (time.monotonic() - t0) * 1000
            log.error("Claude Code exception: %s", e)
            return f"[Erreur Claude Code: {str(e)[:200]}]", latency

    # Ne devrait jamais arriver, mais safety
    return "[Erreur: retry exhausted]", 0.0


def claude_code_generate_stream(
    olam: str,
    prompt: str,
    timeout: int = 300,
    model: str | None = None,
    **kwargs,
):
    """Streaming via Claude Code CLI.

    Yields des dicts compatibles avec le format ollama_generate_stream()
    pour que le web/app.py n'ait rien à changer.

    Args:
        olam: Le monde
        prompt: Le prompt
        timeout: Timeout en secondes
        model: Override le modèle

    Yields:
        dict avec "response" (token) et "done" (bool)

    Note: temperature ignorée (cf. claude_code_generate, audit I5).
    """
    _warn_temperature_unsupported_for_claude_code(olam)
    model = model or get_model(olam)
    timeout = timeout or get_timeout(olam)

    _CLI_SYSTEM_PROMPT = (
        "IMPORTANT: Tu es en mode texte pur. Tu ne peux PAS lire de fichiers, "
        "PAS utiliser d'outils, PAS executer de commandes. Reponds UNIQUEMENT "
        "avec tes connaissances. Si on te demande d'analyser du code, donne "
        "une analyse theorique basee sur l'architecture decrite."
    )

    cmd = [
        _CLAUDE_BIN, "-p",
        "--output-format", "json",
        "--model", model,
        "--no-session-persistence",
        "--max-turns", "10",
        "--system-prompt", _CLI_SYSTEM_PROMPT,
        "--tools", "",
        "--disable-slash-commands",
        "--strict-mcp-config",
    ]

    # Environnement propre sans ANTHROPIC_API_KEY pour forcer l'auth Max
    clean_env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}

    try:
        # Opus fait des cycles tool_use→échec internes (invisible sur stdout).
        # subprocess.run attend la fin, puis on parse le JSON "result" et
        # on émule le streaming en découpant la réponse en lignes SSE.
        result = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=clean_env,
        )

        # Parse JSON et extraire le result final
        response_text = ""
        try:
            data = json.loads(result.stdout)
            response_text = data.get("result", "").strip()
        except json.JSONDecodeError:
            response_text = result.stdout.strip()

        if not response_text:
            err = result.stderr[:200].strip() or "empty response"
            log.error("Claude Code stream error (olam=%s): %s", olam, err)
            yield {"response": f"[Erreur: {err}]", "done": True}
            return

        # Émuler le streaming : découper en lignes pour le SSE
        for line in response_text.split("\n"):
            yield {"response": line + "\n", "done": False}

        yield {"response": "", "done": True}

    except subprocess.TimeoutExpired:
        log.error("Claude Code stream timeout (%ss) pour olam=%s", timeout, olam)
        yield {"response": f"[Erreur: timeout {timeout}s]", "done": True}
    except Exception as e:
        log.error("Claude Code stream exception: %s", e)
        yield {"response": f"[Erreur streaming: {str(e)[:200]}]", "done": True}


# ─── Appel Ollama ─────────────────────────────────────────────

def _persist_post_response(
    olam: str,
    model: str,
    response_text: str,
    latency: float,
    assembly: dict,
    kavvanah: dict | None = None,
    stream: bool = False,
) -> None:
    """Persistance post-LLM commune à tous les providers.

    Reshimo, Masakh log, ContextMonitor — la traçabilité Sod HaKli
    est indépendante du provider qui produit la réponse.
    """
    # Post-response: évaluer Zivvug (dim 15) et Panim/Achor (dim 24)
    monitor_state = assembly.get("monitor_state")
    if monitor_state and response_text:
        try:
            _monitor = ContextMonitor()
            # F-006: passer le reshimo_pre pour que assess_zivvug score correctement
            reshimo_pre = assembly.get("reshimo_pre")
            _monitor.update_post_response(
                monitor_state,
                prompt_final=assembly["prompt_final"],
                response=response_text,
                kavvanah=kavvanah,
                reshimo=reshimo_pre,
            )
            assembly["dimensions_score"] = monitor_state["score_global"]
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # F-017: Reshimo unique — fusionner pré-LLM (CA étape 10) + post-LLM
    _conn_ctx = _get_db_conn()
    _conn = None
    try:
        if _conn_ctx is not None:
            _conn = _conn_ctx.__enter__()
    except Exception:
        _conn = None

    try:
        reshimo_pre = assembly.get("reshimo_pre") or {}
        pre_hitlabshut = reshimo_pre.get("reshimo_hitlabshut", {})
        pre_aviut = reshimo_pre.get("reshimo_aviut", {})

        # Fusionner: données pré-LLM + enrichissement post-LLM
        hitlabshut_data = {
            **pre_hitlabshut,
            "response_length": len(response_text),
            "response_preview": response_text[:200],
            "model": model,
            "latency_ms": latency,
        }
        if stream:
            hitlabshut_data["stream"] = True

        # Fix 7 : stocker zivvug_score et alignment_score dans le reshimo
        # pour que Gilgul puisse prioriser les patterns à haut Zivvug
        # (Or Chozer effectif — EC-SHK-073).
        aviut_data = {
            **pre_aviut,
            "dimensions_score": assembly["dimensions_score"],
            "zivvug_score": monitor_state.get("zivvug_score", 0.0)
            if monitor_state else 0.0,
            "alignment_score": monitor_state.get("alignment_score", 0.0)
            if monitor_state else 0.0,
        }

        write_reshimo(
            olam=olam,
            hitlabshut=hitlabshut_data,
            aviut=aviut_data,
            conn=_conn,
        )

        # Masakh log — persister l'activité de filtrage
        if _conn is not None:
            excluded = assembly.get("excluded", {})
            try:
                cur = _conn.cursor()
                cur.execute("""
                    INSERT INTO masakh_log (
                        olam, aviut_level, kashiut, aviut_mode,
                        tokens_before, tokens_after, tokens_rejected,
                        rejection_reason, kavvanah
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    olam,
                    assembly.get("masakh_level", "shoresh"),
                    assembly.get("kashiut", 0.0),
                    assembly.get("aviut_mode", "unknown"),
                    excluded.get("tokens_before", 0),
                    excluded.get("tokens_after", 0),
                    excluded.get("tokens_rejected", 0),
                    excluded.get("rejection_reason", "within budget"),
                    json.dumps(kavvanah) if kavvanah else None,
                ))
                _conn.commit()
                cur.close()
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # ContextMonitor — persister les 29 dimensions
        if _conn is not None and monitor_state is not None:
            try:
                from masakh.context_monitor import log_to_db as monitor_log_to_db
                monitor_log_to_db(_conn, monitor_state)
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
    finally:
        if _conn_ctx is not None:
            try:
                _conn_ctx.__exit__(None, None, None)
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)


def ollama_generate(
    olam: str,
    prompt: str,
    timeout: int = 60,
    model: str | None = None,
    kavvanah: dict | None = None,
    context_items: list[str] | None = None,
    principles: list[str] | None = None,
    domain: str | None = None,
    facts: list[str] | None = None,
    pressure_regulated: bool = False,
    daemon_block: str | None = None,
    tree_signals: dict | None = None,
    **override_options,
) -> tuple[str, float]:
    """Appeler le LLM via un monde — dispatch automatique selon provider.

    Le provider (ollama, claude_code, anthropic) est déterminé par
    le profil actif dans config.yaml. Les 18 call sites existants
    n'ont rien à changer.

    Args:
        olam: Le monde ("briah", "yetzirah", "assiah")
        prompt: Le prompt à envoyer
        timeout: Timeout en secondes
        model: Override le modèle de l'olam (pour eval, etc.)
        kavvanah: Intention dirigée — injectée en tête de prompt.
            Omission tolérée mais génère un avertissement (EC-SHK-038).
            Structure: {"intention": str, "critere_succes": str, "anti_pattern": str}
        context_items: Éléments de contexte à recatégoriser via Arakhin (optionnel).
        principles: Principes à enclothe via Hitlabshut (optionnel).
        domain: Domaine pour le pont Da'at (optionnel).
        facts: Faits pour le pont Da'at (optionnel).
        daemon_block: Contenu DaemonBridge pre-formate (optionnel).
            Soumis au budget Masakh total (F6 — EC-SHK-023).
        **override_options: Options à overrider

    Returns:
        (response_text, latency_ms)
    """
    # ─── Dispatch Claude Code CLI ────────────────────────────
    provider = get_provider(olam)
    if provider == "claude_code":
        # Kavvanah warning si absente (injection gérée par ContextAssembler étape 6)
        if kavvanah is None:
            import traceback
            caller = "".join(traceback.format_stack(limit=3)[:-1]).strip()
            log.warning(
                "ollama_generate() appelé SANS kavvanah (olam=%s, provider=claude_code). "
                "EC-SHK-038 : sans kavvanah, l'action ne peut pas monter.\n%s",
                olam, caller,
            )

        # ContextAssembler — même pipeline Sod HaKli pour Claude Code
        ctx_window = get_context_window(olam)
        assembler = ContextAssembler(db_pool_fn=_get_db_conn)
        assembly = assembler.assemble(
            olam=olam,
            prompt=prompt,
            context_window=ctx_window,
            kavvanah=kavvanah,
            context_items=context_items,
            principles=principles,
            domain=domain,
            facts=facts,
            pressure_regulated=pressure_regulated,
            daemon_block=daemon_block,
            tree_signals=tree_signals,
        )
        assembled_prompt = assembly["prompt_final"]

        # Claude Code CLI : Opus tente des tool_use sur les prompts
        # qui mentionnent du code/fichiers. Injecter une directive
        # directement dans le prompt pour forcer la réponse texte.
        assembled_prompt += (
            "\n\n[CONTRAINTE] Tu es en mode texte pur sans accès aux fichiers. "
            "Réponds directement avec tes connaissances. Ne tente PAS de lire "
            "des fichiers ou d'utiliser des outils."
        )

        response_text, latency = claude_code_generate(
            olam, assembled_prompt, timeout=timeout, model=model,
        )

        # Post-response : Reshimo + monitoring (même logique que Ollama)
        _persist_post_response(
            olam=olam, model=model or get_model(olam),
            response_text=response_text, latency=latency,
            assembly=assembly, kavvanah=kavvanah,
        )
        return response_text, latency

    # ─── Dispatch generic CLI subscription (Codex, Gemini, Copilot) ──
    if provider == "cli":
        if kavvanah is None:
            import traceback
            caller = "".join(traceback.format_stack(limit=3)[:-1]).strip()
            log.warning(
                "ollama_generate() appelé SANS kavvanah (olam=%s, provider=cli). "
                "EC-SHK-038 : sans kavvanah, l'action ne peut pas monter.\n%s",
                olam, caller,
            )

        ctx_window = get_context_window(olam)
        assembler = ContextAssembler(db_pool_fn=_get_db_conn)
        assembly = assembler.assemble(
            olam=olam, prompt=prompt, context_window=ctx_window,
            kavvanah=kavvanah, context_items=context_items,
            principles=principles, domain=domain, facts=facts,
            pressure_regulated=pressure_regulated, daemon_block=daemon_block,
            tree_signals=tree_signals,
        )
        assembled_prompt = assembly["prompt_final"]

        from etzchaim.providers.cli_generic import cli_generate
        cfg = _get_olam_config(olam)
        response_text, latency = cli_generate(
            cli=cfg["cli"],
            args=cfg.get("args", []),
            model=model or get_model(olam),
            prompt=assembled_prompt,
            timeout=timeout or get_timeout(olam),
            response_parser=cfg.get("response_parser", "identity"),
        )
        _persist_post_response(
            olam=olam, model=model or get_model(olam),
            response_text=response_text, latency=latency,
            assembly=assembly, kavvanah=kavvanah,
        )
        return response_text, latency

    # ─── Ollama (code existant) ──────────────────────────────
    # EC-SHK-038 : « Sans aucune Kavvanah, elles ne peuvent pas monter du tout. »
    # Chaque appel LLM DOIT porter une intention dirigée.
    if kavvanah is None:
        import traceback
        caller = "".join(traceback.format_stack(limit=3)[:-1]).strip()
        log.warning(
            "ollama_generate() appelé SANS kavvanah (olam=%s). "
            "EC-SHK-038 : sans kavvanah, l'action ne peut pas monter.\n%s",
            olam, caller,
        )

    model = model or get_model(olam)
    options = {**get_options(olam), **override_options}
    host = get_ollama_host()

    think = get_think(olam)

    # ContextAssembler — orchestre tout le pipeline Sod HaKli
    ctx_window = get_context_window(olam)
    assembler = ContextAssembler(db_pool_fn=_get_db_conn)
    assembly = assembler.assemble(
        olam=olam,
        prompt=prompt,
        context_window=ctx_window,
        kavvanah=kavvanah,
        context_items=context_items,
        principles=principles,
        domain=domain,
        facts=facts,
        pressure_regulated=pressure_regulated,
        daemon_block=daemon_block,
        tree_signals=tree_signals,
    )
    prompt = assembly["prompt_final"]

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": think,
        "options": options,
    }).encode()

    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    # ── Circuit breaker : fast-fail si Ollama est down ──
    try:
        _ollama_cb_check()
    except OllamaCircuitOpenError as e:
        return f"[Erreur: {e}]", 0.0

    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        _ollama_cb_success()
    except Exception as e:
        latency = (time.monotonic() - t0) * 1000
        _ollama_cb_failure()
        log.error("Ollama request failed (olam=%s): %s", olam, e)
        return f"[Erreur Ollama: {str(e)[:200]}]", latency
    latency = (time.monotonic() - t0) * 1000

    response_text = data.get("response", "").strip()
    # Qwen3.5 en thinking mode: le contenu utile peut être dans "thinking"
    # quand "response" est vide (tous les tokens consommés par le raisonnement)
    if not response_text and data.get("thinking"):
        response_text = data["thinking"].strip()

    _persist_post_response(
        olam=olam, model=model, response_text=response_text,
        latency=latency, assembly=assembly, kavvanah=kavvanah,
    )

    return response_text, latency


def ollama_embed(
    text: str,
    model: str | None = None,
    kavvanah: dict | None = None,
    domain: str | None = None,
) -> list[float]:
    """Obtenir un embedding via Ollama.

    Args:
        text: Texte à encoder
        model: Override le modèle d'embedding (sinon config)
        kavvanah: Intention dirigée pour le Reshimo (optionnel)
        domain: Domaine pour le Reshimo (optionnel)
    """
    model = model or get_embedding_model()
    host = get_ollama_host()

    payload = json.dumps({
        "model": model,
        "input": text,
    }).encode()

    req = urllib.request.Request(
        f"{host}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    # Fast-fail + fallback cache si circuit ouvert
    try:
        _ollama_cb_check()
    except OllamaCircuitOpenError:
        cached = _embed_cache_get(model, text)
        if cached is not None:
            log.warning(
                "Ollama circuit open — embedding servi depuis le cache "
                "(text_len=%d, model=%s)", len(text), model,
            )
            write_reshimo(
                olam="yesod",
                hitlabshut={
                    "type": "embedding_cache_hit",
                    "text_length": len(text),
                    "model": model,
                    "dimensions": len(cached),
                    "reason": "circuit_open",
                },
                aviut={
                    "masakh_level": "shoresh",
                    "kavvanah": kavvanah,
                    "domain": domain,
                    "was_filtered": False,
                },
            )
            return cached
        raise

    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        _ollama_cb_success()
    except Exception as e:
        _ollama_cb_failure()
        cached = _embed_cache_get(model, text)
        if cached is not None:
            log.warning(
                "Ollama embed failed (%s) — embedding servi depuis le cache",
                e,
            )
            write_reshimo(
                olam="yesod",
                hitlabshut={
                    "type": "embedding_cache_hit",
                    "text_length": len(text),
                    "model": model,
                    "dimensions": len(cached),
                    "reason": "embed_failure",
                },
                aviut={
                    "masakh_level": "shoresh",
                    "kavvanah": kavvanah,
                    "domain": domain,
                    "was_filtered": False,
                },
            )
            return cached
        raise RuntimeError(f"Ollama embed failed: {e}") from e
    latency = (time.monotonic() - t0) * 1000

    result = data["embeddings"][0]
    _embed_cache_put(model, text, result)

    # Reshimo post-embed — traçabilité Sod HaKli
    write_reshimo(
        olam="yesod",
        hitlabshut={
            "type": "embedding",
            "text_length": len(text),
            "model": model,
            "latency_ms": latency,
            "dimensions": len(result),
        },
        aviut={
            "masakh_level": "shoresh",
            "kavvanah": kavvanah,
            "domain": domain,
            "was_filtered": False,
        },
    )

    return result


def ollama_embed_batch(
    texts: list[str],
    model: str | None = None,
    kavvanah: dict | None = None,
    domain: str | None = None,
) -> list[list[float]]:
    """Obtenir des embeddings pour plusieurs textes en un appel.

    Args:
        texts: Liste de textes à encoder
        model: Override le modèle d'embedding (sinon config)
        kavvanah: Intention dirigée pour le Reshimo (optionnel)
        domain: Domaine pour le Reshimo (optionnel)
    """
    model = model or get_embedding_model()
    host = get_ollama_host()

    payload = json.dumps({
        "model": model,
        "input": texts,
    }).encode()

    req = urllib.request.Request(
        f"{host}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read())
    latency = (time.monotonic() - t0) * 1000

    result = data["embeddings"]

    # Reshimo post-embed-batch — traçabilité Sod HaKli
    write_reshimo(
        olam="yesod",
        hitlabshut={
            "type": "embedding_batch",
            "batch_size": len(texts),
            "model": model,
            "latency_ms": latency,
            "dimensions": len(result[0]) if result else 0,
        },
        aviut={
            "masakh_level": "shoresh",
            "kavvanah": kavvanah,
            "domain": domain,
            "was_filtered": False,
        },
    )

    return result


def ollama_generate_stream(
    olam: str,
    prompt: str,
    timeout: int = 300,
    model: str | None = None,
    kavvanah: dict | None = None,
    context_items: list[str] | None = None,
    principles: list[str] | None = None,
    domain: str | None = None,
    facts: list[str] | None = None,
    pressure_regulated: bool = False,
    daemon_block: str | None = None,
    tree_signals: dict | None = None,
    **override_options,
):
    """Appeler le LLM en streaming — dispatch automatique selon provider.

    Args:
        olam: Le monde ("briah", "yetzirah", "assiah")
        prompt: Le prompt à envoyer
        timeout: Timeout en secondes
        model: Override le modèle de l'olam
        kavvanah: Intention dirigée — omission tolérée mais génère
            un avertissement (EC-SHK-038).
        context_items: Éléments de contexte pour Arakhin (optionnel)
        principles: Principes pour Hitlabshut (optionnel)
        domain: Domaine pour Da'at Bridge (optionnel)
        facts: Faits pour Da'at Bridge (optionnel)
        daemon_block: Contenu DaemonBridge pre-formate (optionnel).
            Soumis au budget Masakh total (F6 — EC-SHK-023).
        **override_options: Options à overrider

    Yields:
        dict — chaque chunk (contient "response", "done", etc.)
    """
    # ─── Dispatch Claude Code CLI stream ─────────────────────
    provider = get_provider(olam)
    if provider == "claude_code":
        # Kavvanah warning si absente (injection gérée par ContextAssembler étape 6)
        if kavvanah is None:
            import traceback
            caller = "".join(traceback.format_stack(limit=3)[:-1]).strip()
            log.warning(
                "ollama_generate_stream() appelé SANS kavvanah (olam=%s, provider=claude_code).\n%s",
                olam, caller,
            )

        ctx_window = get_context_window(olam)
        assembler = ContextAssembler(db_pool_fn=_get_db_conn)
        assembly = assembler.assemble(
            olam=olam, prompt=prompt, context_window=ctx_window,
            kavvanah=kavvanah, context_items=context_items,
            principles=principles, domain=domain, facts=facts,
            pressure_regulated=pressure_regulated, daemon_block=daemon_block,
        )
        assembled_prompt = assembly["prompt_final"]

        # Directive anti-outil (même logique que le path non-stream)
        assembled_prompt += (
            "\n\n[CONTRAINTE] Tu es en mode texte pur sans accès aux fichiers. "
            "Réponds directement avec tes connaissances. Ne tente PAS de lire "
            "des fichiers ou d'utiliser des outils."
        )

        t0 = time.monotonic()
        full_response_parts: list[str] = []
        try:
            for chunk in claude_code_generate_stream(
                olam, assembled_prompt, timeout=timeout, model=model,
            ):
                token = chunk.get("response", "")
                if token:
                    full_response_parts.append(token)
                yield chunk
        finally:
            latency = (time.monotonic() - t0) * 1000
            response_text = "".join(full_response_parts).strip()
            _persist_post_response(
                olam=olam, model=model or get_model(olam),
                response_text=response_text, latency=latency,
                assembly=assembly, kavvanah=kavvanah, stream=True,
            )
        return

    # ─── Ollama stream (code existant) ───────────────────────
    # EC-SHK-038 : « Sans aucune Kavvanah, elles ne peuvent pas monter du tout. »
    if kavvanah is None:
        import traceback
        caller = "".join(traceback.format_stack(limit=3)[:-1]).strip()
        log.warning(
            "ollama_generate_stream() appelé SANS kavvanah (olam=%s). "
            "EC-SHK-038 : sans kavvanah, l'action ne peut pas monter.\n%s",
            olam, caller,
        )

    model = model or get_model(olam)
    options = {**get_options(olam), **override_options}
    host = get_ollama_host()
    think = get_think(olam)

    # ContextAssembler — orchestre tout le pipeline Sod HaKli
    ctx_window = get_context_window(olam)
    assembler = ContextAssembler(db_pool_fn=_get_db_conn)
    assembly = assembler.assemble(
        olam=olam,
        prompt=prompt,
        context_window=ctx_window,
        kavvanah=kavvanah,
        context_items=context_items,
        principles=principles,
        domain=domain,
        facts=facts,
        pressure_regulated=pressure_regulated,
        daemon_block=daemon_block,
        tree_signals=tree_signals,
    )
    prompt = assembly["prompt_final"]

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": True,
        "think": think,
        "options": options,
    }).encode()

    req = urllib.request.Request(
        f"{host}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    t0 = time.monotonic()
    full_response_parts: list[str] = []
    thinking_parts: list[str] = []
    resp = urllib.request.urlopen(req, timeout=timeout)
    try:
        for line in resp:
            if line:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    full_response_parts.append(token)
                thinking_token = chunk.get("thinking", "")
                if thinking_token:
                    thinking_parts.append(thinking_token)
                yield chunk
    finally:
        resp.close()
        # F7 fix — parité avec ollama_generate(): persister reshimo,
        # masakh_log et context_monitor_log après la fin du stream.
        latency = (time.monotonic() - t0) * 1000
        response_text = "".join(full_response_parts).strip()
        # Qwen3.5 thinking mode: fallback si tous les tokens sont en thinking
        if not response_text and thinking_parts:
            response_text = "".join(thinking_parts).strip()

        _persist_post_response(
            olam=olam, model=model, response_text=response_text,
            latency=latency, assembly=assembly, kavvanah=kavvanah,
            stream=True,
        )


# ─── Diagnostic ───────────────────────────────────────────────

def check_models() -> dict[str, bool]:
    """Vérifier la disponibilité des modèles pour le profil actif."""
    profile = get_active_profile()
    olamot = profile.get("olamot", {})
    host = get_ollama_host()
    results = {}

    # Récupérer la liste des modèles Ollama installés
    ollama_installed: set[str] = set()
    try:
        req = urllib.request.Request(f"{host}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        ollama_installed = {m["name"] for m in data.get("models", [])}
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    for olam_name, olam_cfg in olamot.items():
        prov = olam_cfg.get("provider", "ollama")
        if prov == "ollama":
            model = olam_cfg["model"]
            results[olam_name] = (
                model in ollama_installed
                or f"{model}:latest" in ollama_installed
                or any(m.startswith(model.split(":")[0]) for m in ollama_installed)
            )
        elif prov == "claude_code":
            # Vérifier que la CLI claude est disponible
            try:
                subprocess.run(["claude", "--version"], capture_output=True, timeout=5)
                results[olam_name] = True
            except Exception:
                results[olam_name] = False
        elif prov == "anthropic":
            results[olam_name] = bool(os.environ.get("ANTHROPIC_API_KEY"))

    # Embedding
    emb = profile.get("embedding", {})
    emb_model = emb.get("model", "nomic-embed-text")
    emb_prov = emb.get("provider", "ollama")
    if emb_prov == "ollama":
        results["embedding"] = (
            emb_model in ollama_installed
            or f"{emb_model}:latest" in ollama_installed
        )
    else:
        results["embedding"] = True

    return results


def report() -> str:
    """Rapport de configuration — état des 4 Mondes + profil actif."""
    cfg = _load_config()
    machine = cfg["machine"]
    profile_name = get_active_profile_name()
    profile = get_active_profile()
    olamot = profile.get("olamot", {})
    models_ok = check_models()

    lines = [
        f"=== Olamot Report — {machine['name']} ({machine['ram_gb']}Go) ===",
        f"  Profil actif: {profile_name} — {profile.get('description', '')}",
        "",
    ]

    for olam_name in ["atziluth", "briah", "yetzirah", "assiah"]:
        olam_cfg = olamot.get(olam_name, {})
        prov = olam_cfg.get("provider", "?")
        model = olam_cfg.get("model", "?")

        if prov == "claude_code":
            ok = models_ok.get(olam_name, False)
            status = "CLI OK" if ok else "CLI MISSING"
        elif prov == "anthropic":
            ok = models_ok.get(olam_name, False)
            status = "API key OK" if ok else "no API key"
        else:
            ok = models_ok.get(olam_name, False)
            status = "installed" if ok else "MISSING"

        lines.append(
            f"  {olam_name:<12} {prov:<12} {model:<24} [{status}]"
        )

    emb = profile.get("embedding", {})
    emb_ok = models_ok.get("embedding", False)
    lines.append(
        f"  {'embedding':<12} {emb.get('provider', 'ollama'):<12} "
        f"{emb.get('model', '?'):<24} [{'OK' if emb_ok else 'MISSING'}]"
    )

    lines.append("")
    lines.append("Sephirot mapping:")
    for seph, seph_cfg in cfg["sephirot"].items():
        model = get_model(seph_cfg["olam"])
        prov = get_provider(seph_cfg["olam"])
        extra = ""
        if seph_cfg.get("judge_olam"):
            extra = f" (judge: {get_model(seph_cfg['judge_olam'])})"
        if seph_cfg.get("embedding"):
            extra = f" (+ {emb.get('model', '?')})"
        lines.append(
            f"  {seph:<12} -> {seph_cfg['olam']:<12} = {prov}/{model}{extra}"
        )

    return "\n".join(lines)


if __name__ == "__main__":
    print(report())
