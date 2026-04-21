"""Generic CLI-subscription provider.

Routes olamot.generate calls through third-party AI CLIs that authenticate
via OAuth (i.e. no API key, the user paid for a subscription). Supported
out-of-the-box :

    - Codex CLI        (OpenAI ChatGPT subscription)    → `codex`
    - Gemini CLI       (Google account, free tier + paid) → `gemini`
    - GitHub Copilot   (Copilot subscription)            → `gh copilot`

The mapping between an olam profile and a concrete CLI is declared in
config.yaml under `profiles.<name>.olamot.<olam>` :

    provider: cli
    cli: codex                   # binary name
    model: gpt-5
    args: ["--model", "{model}", "exec", "-"]   # '-' = read stdin
    timeout: 180

Placeholders in args : `{model}`, `{prompt}`. If `{prompt}` is absent the
prompt is piped via stdin. `response_parser` (optional) names a post-
processing function defined in this module, e.g. `strip_codex_banner`.

Design constraints :
    - The CLI must already be authenticated on the host (OAuth stored in
      ~/.config/<tool>/). No automation of the login flow here.
    - These CLIs generally do NOT work inside Docker (browser-based OAuth).
      Container deployments should keep `provider: litellm` profiles.
    - Rate-limit / transient-error retry with exponential backoff matches
      `claude_code_generate` (3 attempts, 5/10/20 s).
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from typing import Callable

log = logging.getLogger(__name__)

# ─── Response parsers ────────────────────────────────────────────────

def _identity(out: str) -> str:
    return out.strip()


def strip_codex_banner(out: str) -> str:
    """Drop the ASCII banner Codex CLI prints on non-TTY output."""
    lines = out.splitlines()
    # Banner lines start with '╭', '│', '╰' box-drawing characters.
    payload = [ln for ln in lines if not ln.lstrip().startswith(("╭", "│", "╰"))]
    return "\n".join(payload).strip()


def strip_gh_copilot_wrapper(out: str) -> str:
    """Extract the 'Suggestion:' block that `gh copilot suggest` prints."""
    marker = "Suggestion:"
    if marker in out:
        out = out.split(marker, 1)[1]
        # Drop the trailing prompt (Y/N/explain) that gh prints interactively.
        for sep in ("\n? ", "\nSelect", "\n[↑"):
            if sep in out:
                out = out.split(sep, 1)[0]
    return out.strip()


PARSERS: dict[str, Callable[[str], str]] = {
    "identity": _identity,
    "strip_codex_banner": strip_codex_banner,
    "strip_gh_copilot_wrapper": strip_gh_copilot_wrapper,
}


# ─── Binary resolution ───────────────────────────────────────────────

def _resolve_binary(cli_name: str) -> str | None:
    """Return the absolute path of the CLI binary, or None if missing.

    `gh copilot` is a special case : the binary is `gh` and the extension
    must be installed (`gh extension install github/gh-copilot`).
    """
    if cli_name == "gh copilot":
        return shutil.which("gh")
    return shutil.which(cli_name)


def check_cli_available(cli_name: str) -> tuple[bool, str]:
    """Return (ok, message) for a given CLI name. Used by doctor checks."""
    path = _resolve_binary(cli_name)
    if not path:
        return False, f"{cli_name} binary not on PATH"
    if cli_name == "gh copilot":
        # Verify the extension is installed.
        try:
            r = subprocess.run(
                ["gh", "extension", "list"],
                capture_output=True, text=True, timeout=5,
            )
            if "gh-copilot" not in (r.stdout or ""):
                return False, "gh is installed but gh-copilot extension is missing"
        except (FileNotFoundError, subprocess.TimeoutExpired) as e:
            return False, f"gh extension list failed : {e}"
    return True, f"{cli_name} found at {path}"


# ─── Main dispatcher ─────────────────────────────────────────────────

MAX_RETRIES = 3
BACKOFF_BASE = 5  # seconds


def cli_generate(
    *,
    cli: str,
    args: list[str],
    model: str,
    prompt: str,
    timeout: int = 180,
    response_parser: str = "identity",
    env_extra: dict[str, str] | None = None,
) -> tuple[str, float]:
    """Invoke a CLI subscription tool and return (text, latency_ms).

    Args:
        cli: binary name ('codex', 'gemini', 'gh copilot').
        args: argv template with optional {model} / {prompt} placeholders.
        model: model ID to substitute into args.
        prompt: user prompt (stdin if {prompt} absent from args).
        timeout: seconds before the subprocess is killed.
        response_parser: name of a parser function in this module.
        env_extra: extra env vars merged into the subprocess environment.

    Raises:
        FileNotFoundError: binary missing.
        RuntimeError: all retries exhausted.
    """
    binary = _resolve_binary(cli)
    if not binary:
        raise FileNotFoundError(
            f"CLI '{cli}' not found on PATH. Install it first "
            f"(see `etzchaim doctor` for guidance)."
        )

    # Substitute placeholders.
    stdin_prompt: str | None = None
    resolved: list[str] = []
    prompt_in_args = False
    for a in args:
        if "{prompt}" in a:
            prompt_in_args = True
            a = a.replace("{prompt}", prompt)
        a = a.replace("{model}", model)
        resolved.append(a)
    if not prompt_in_args:
        stdin_prompt = prompt

    # `gh copilot` requires splitting "gh copilot" into argv[0]="gh", then
    # prepending "copilot" + the verb to the rest.
    if cli == "gh copilot":
        argv = [binary, "copilot"] + resolved
    else:
        argv = [binary] + resolved

    parser = PARSERS.get(response_parser, _identity)

    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)

    last_err: str = ""
    for attempt in range(MAX_RETRIES):
        t0 = time.monotonic()
        try:
            result = subprocess.run(
                argv,
                input=stdin_prompt,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            latency_ms = (time.monotonic() - t0) * 1000.0

            stderr_lower = (result.stderr or "").lower()
            if result.returncode != 0 and any(
                k in stderr_lower
                for k in ("rate limit", "too many requests", "429",
                          "overloaded", "quota", "resource exhausted")
            ):
                backoff = BACKOFF_BASE * (2 ** attempt)
                log.warning(
                    "Rate limit from %s (attempt %d/%d), backoff %ds",
                    cli, attempt + 1, MAX_RETRIES, backoff,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(backoff)
                    continue
                last_err = f"Rate limited (final attempt): {result.stderr[:200]}"
                break

            if result.returncode != 0:
                last_err = (
                    f"{cli} exited {result.returncode} — "
                    f"stderr: {result.stderr[:500]}"
                )
                break

            text = parser(result.stdout or "")
            if not text:
                last_err = f"{cli} returned empty output"
                break
            return text, latency_ms

        except subprocess.TimeoutExpired:
            last_err = f"{cli} timed out after {timeout}s"
            break
        except Exception as e:  # noqa: BLE001
            last_err = f"{cli} invocation error: {e}"
            break

    raise RuntimeError(f"CLI provider '{cli}' failed: {last_err}")
