"""etzchaim onboard — comprehensive install wizard (v0.2.1).

Eight steps :
    1. System detection (Docker, Postgres, Ollama on host)
    2. Database configuration (BYO Postgres OR docker-compose managed)
    3. LLM providers (multi-select from 20+ supported)
    4. Per-provider credentials (API keys)
    5. Profile composition (pick a ready-made profile OR auto-pick from keys)
    6. Web + auth (port, API key, anonymous access policy)
    7. Observability (log level, Sentry DSN, OTLP endpoint — optional)
    8. Review + confirm → write .env + config.yaml + extract compose + start

Uses questionary for checklists / single-select where available, falls back
to typer.prompt when stdin is not a TTY or questionary is absent.

Non-interactive mode : --non-interactive --preset <name>. Preset names :
    local-only          — Ollama only, no API key.
    anthropic-full      — Anthropic API for all olamot.
    openai-full         — OpenAI API for all olamot.
    gemini-full         — Google Gemini API for all olamot.
    bedrock-full        — AWS Bedrock for all olamot.
    hybrid              — Anthropic Opus for deep reasoning, Ollama for rest.
    claude-max          — Claude Code CLI (OAuth subscription).
"""
from __future__ import annotations

import os
import secrets as _secrets
import socket
from pathlib import Path

import typer

from etzchaim._paths import compose_dir, env_file, ensure_state_dir
from etzchaim.cli import compose, detect, installers
from etzchaim.cli.app import app

# ─── Providers catalog ────────────────────────────────────────────────
# Grouped by cost tier, each entry is (key_env_var, display_name, signup_url).
PROVIDERS = {
    "frontier": [
        ("ANTHROPIC_API_KEY", "Anthropic (Claude)",
         "https://console.anthropic.com/settings/keys"),
        ("OPENAI_API_KEY", "OpenAI (GPT-5 family)",
         "https://platform.openai.com/api-keys"),
        ("GOOGLE_API_KEY", "Google (Gemini 2.5)",
         "https://aistudio.google.com/app/apikey"),
        ("XAI_API_KEY", "xAI (Grok)",
         "https://console.x.ai"),
        ("MISTRAL_API_KEY", "Mistral",
         "https://console.mistral.ai/api-keys/"),
        ("COHERE_API_KEY", "Cohere",
         "https://dashboard.cohere.com/api-keys"),
        ("DEEPSEEK_API_KEY", "DeepSeek",
         "https://platform.deepseek.com/api_keys"),
    ],
    "aggregator": [
        ("OPENROUTER_API_KEY", "OpenRouter",
         "https://openrouter.ai/keys"),
        ("TOGETHER_API_KEY", "Together AI",
         "https://api.together.xyz/settings/api-keys"),
        ("GROQ_API_KEY", "Groq",
         "https://console.groq.com/keys"),
        ("FIREWORKS_API_KEY", "Fireworks",
         "https://fireworks.ai/api-keys"),
        ("PERPLEXITY_API_KEY", "Perplexity",
         "https://www.perplexity.ai/settings/api"),
    ],
    "enterprise": [
        ("AWS_ACCESS_KEY_ID", "AWS Bedrock (needs AWS_SECRET_ACCESS_KEY too)",
         "https://aws.amazon.com/bedrock/"),
        ("AZURE_API_KEY", "Azure OpenAI (needs AZURE_API_BASE)",
         "https://azure.microsoft.com/en-us/products/ai-services/openai-service"),
    ],
    "open_weight": [
        ("HUGGINGFACE_API_KEY", "HuggingFace",
         "https://huggingface.co/settings/tokens"),
        ("NVIDIA_NIM_API_KEY", "NVIDIA NIM",
         "https://build.nvidia.com"),
        ("CLOUDFLARE_API_KEY", "Cloudflare Workers AI",
         "https://dash.cloudflare.com/profile/api-tokens"),
        ("REPLICATE_API_TOKEN", "Replicate",
         "https://replicate.com/account/api-tokens"),
    ],
    "embeddings_specialized": [
        # Embedding-specific providers. Note : OpenAI / Cohere / HuggingFace
        # already cover embeddings — only pick these if you want specialized
        # embedding models (multi-lingual, long-context, domain-specific).
        ("VOYAGE_API_KEY", "Voyage AI (high-quality embeddings)",
         "https://dash.voyageai.com"),
        ("JINA_API_KEY", "Jina AI (multilingual embeddings)",
         "https://jina.ai/embeddings"),
    ],
    "local": [
        ("OLLAMA_HOST", "Ollama (local, free)",
         "https://ollama.com"),
        ("VLLM_HOST", "vLLM (self-hosted)",
         "https://docs.vllm.ai"),
        ("LMSTUDIO_HOST", "LM Studio",
         "https://lmstudio.ai"),
        ("LOCALAI_HOST", "LocalAI",
         "https://localai.io"),
    ],
    # CLI-based subscriptions (OAuth — no API key, but tied to a paid plan).
    # These do NOT work inside Docker (browser-based auth). Host-only.
    "cli_subscription": [
        ("USE_CLAUDE_CODE_CLI", "Claude Code CLI (Claude Max plan)",
         "https://www.anthropic.com/api"),
        ("USE_CODEX_CLI", "Codex CLI (ChatGPT Plus / Team / Enterprise)",
         "https://chat.openai.com"),
        ("USE_GEMINI_CLI", "Gemini CLI (Google account, free tier 1000/day)",
         "https://ai.google.dev/gemini-api"),
        ("USE_COPILOT_CLI", "GitHub Copilot CLI (Copilot subscription)",
         "https://github.com/features/copilot"),
    ],
}

PRESETS = {
    "local-only":      ("local_only", {"OLLAMA_HOST"}),
    "anthropic-full":  ("anthropic_full", {"ANTHROPIC_API_KEY"}),
    "openai-full":     ("openai_full", {"OPENAI_API_KEY"}),
    "gemini-full":     ("gemini_full", {"GOOGLE_API_KEY"}),
    "bedrock-full":    ("bedrock_full", {"AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"}),
    "azure-full":      ("azure_full", {"AZURE_API_KEY", "AZURE_API_BASE"}),
    "xai-full":        ("xai_full", {"XAI_API_KEY"}),
    "mistral-full":    ("mistral_full", {"MISTRAL_API_KEY"}),
    "cohere-full":     ("cohere_full", {"COHERE_API_KEY"}),
    "deepseek-full":   ("deepseek_full", {"DEEPSEEK_API_KEY"}),
    "groq-full":       ("groq_full", {"GROQ_API_KEY"}),
    "openrouter-full": ("openrouter_full", {"OPENROUTER_API_KEY"}),
    "together-full":   ("together_full", {"TOGETHER_API_KEY"}),
    "fireworks-full":  ("fireworks_full", {"FIREWORKS_API_KEY"}),
    "perplexity-full": ("perplexity_full", {"PERPLEXITY_API_KEY"}),
    "hybrid":          ("hybrid", {"ANTHROPIC_API_KEY", "OLLAMA_HOST"}),
    # CLI-subscription presets (OAuth, no API key required).
    "claude-max":      ("claude_max", set()),
    "codex-cli":       ("codex_cli", set()),
    "gemini-cli":      ("gemini_cli", set()),
    "copilot-cli":     ("copilot_cli", set()),
}


def _port_busy(p: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", p))
            return False
        except OSError:
            return True


def _pick_free_port(start: int, end: int) -> int:
    for p in range(start, end + 1):
        if not _port_busy(p):
            return p
    raise RuntimeError(f"No free port in {start}-{end}")


def _write_env_file(vals: dict[str, str]) -> None:
    path = env_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for k, v in vals.items():
            f.write(f"{k}={v}\n")
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass  # Windows ACL differs, silent


def _questionary_available() -> bool:
    try:
        import questionary  # noqa: F401
        return True
    except ImportError:
        return False


def _multiselect_providers() -> list[tuple[str, str, str]]:
    """Return list of (env_var, name, url) the user selected.

    Uses questionary.checkbox when stdin is a TTY, falls back to plain
    typer.confirm per provider otherwise.
    """
    flat = [(k, name, url) for group in PROVIDERS.values() for (k, name, url) in group]

    if _questionary_available() and os.isatty(0):
        import questionary
        choices = [
            questionary.Choice(title=f"{name}", value=(k, name, url))
            for (k, name, url) in flat
        ]
        selected = questionary.checkbox(
            "  Select the LLM providers you want to use (space to toggle, enter to confirm)",
            choices=choices,
        ).ask() or []
        return selected

    # Fallback : explicit yes/no per provider.
    selected: list[tuple[str, str, str]] = []
    for k, name, url in flat:
        if typer.confirm(f"  Use {name} ?", default=False):
            selected.append((k, name, url))
    return selected


def _test_db_connection(url: str) -> tuple[bool, str]:
    """Return (ok, message). Checks connectivity + pgvector availability."""
    try:
        import psycopg2
    except ImportError:
        return True, "psycopg2 not installed yet — skipping connection test"
    try:
        conn = psycopg2.connect(url, connect_timeout=5)
        cur = conn.cursor()
        cur.execute("SELECT version()")
        ver = cur.fetchone()[0].split(",")[0]
        cur.execute(
            "SELECT count(*) FROM pg_available_extensions WHERE name = 'vector'"
        )
        has_pgvector = cur.fetchone()[0] > 0
        cur.close()
        conn.close()
        if not has_pgvector:
            return False, (
                f"Connected ({ver}) but pgvector extension NOT available. "
                "Install it first : brew install pgvector (macOS) OR "
                "apt install postgresql-16-pgvector (Debian)."
            )
        return True, f"Connected ({ver}) with pgvector available"
    except Exception as e:  # noqa: BLE001
        return False, f"Connection failed : {e}"


def _configure_database(non_interactive: bool, env_vals: dict[str, str],
                        *, skip_deps: bool = False, yes: bool = False) -> None:
    """Step 2 : populate DB_* or ETZ_CHAIM_DB_URL entries in env_vals."""
    typer.echo("[2/8] Database — PostgreSQL 16+ with pgvector")
    if non_interactive:
        env_vals["DB_HOST"] = "postgres"
        env_vals["DB_PORT"] = "5432"
        env_vals["DB_USER"] = "etz"
        env_vals["DB_PASSWORD"] = _secrets.token_urlsafe(24)
        env_vals["DB_NAME"] = "etz_chaim"
        env_vals["POSTGRES_PASSWORD"] = env_vals["DB_PASSWORD"]
        env_vals["POSTGRES_PORT"] = "5433"
        env_vals["ETZ_CHAIM_DB_URL"] = (
            f"postgresql://etz:{env_vals['DB_PASSWORD']}@localhost:5433/etz_chaim"
        )
        typer.echo("  ✓ Defaults set (docker-compose-managed)")
        return

    typer.echo("")
    typer.echo("  How do you want to run PostgreSQL ?")
    typer.echo("    1. Docker-managed   (recommended — a local container, zero setup)")
    typer.echo("    2. Your own Postgres (local or remote, you provide credentials)")
    choice = typer.prompt("  Choice", default="1").strip()

    if choice == "2":
        typer.echo("")
        if not skip_deps:
            typer.echo("  First, ensuring PostgreSQL + pgvector are installed ...")
            installers.install_postgres(non_interactive=non_interactive, yes=yes)
            installers.install_pgvector(non_interactive=non_interactive, yes=yes)
            want_ts = typer.confirm(
                "  Install TimescaleDB too (optional, hypertable compression) ?",
                default=False,
            ) if not non_interactive else False
            if want_ts:
                installers.install_timescaledb(non_interactive=non_interactive, yes=yes)
        typer.echo("")
        typer.echo("  Now create a role + database (one-time) :")
        typer.echo("")
        typer.echo("    createuser etz --pwprompt")
        typer.echo("    createdb etz_chaim --owner=etz")
        typer.echo("    psql etz_chaim -c 'CREATE EXTENSION IF NOT EXISTS vector;'")
        typer.echo("")
        typer.echo("  Then enter the credentials you used :")
        typer.echo("")
        host = typer.prompt("  DB_HOST", default="localhost")
        port = typer.prompt("  DB_PORT", default="5432")
        user = typer.prompt("  DB_USER", default="etz")
        password = typer.prompt("  DB_PASSWORD", hide_input=True, default="")
        name = typer.prompt("  DB_NAME", default="etz_chaim")
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
        env_vals.update({
            "DB_HOST": host,
            "DB_PORT": port,
            "DB_USER": user,
            "DB_PASSWORD": password,
            "DB_NAME": name,
            "ETZ_CHAIM_DB_URL": url,
        })
        typer.echo("")
        typer.echo("  Testing connection ...")
        ok, msg = _test_db_connection(url)
        mark = "✓" if ok else "✗"
        typer.echo(f"  {mark} {msg}")
        if not ok:
            if typer.confirm("  Continue anyway ?", default=False):
                typer.echo("  ⚠ Proceeding with unverified DB — fix before `etzchaim start`.")
            else:
                typer.echo("Aborted.")
                raise typer.Exit(1)
    else:
        pg_port = _pick_free_port(5433, 5450)
        pg_password = _secrets.token_urlsafe(24)
        env_vals.update({
            "DB_HOST": "postgres",
            "DB_PORT": "5432",
            "DB_USER": "etz",
            "DB_PASSWORD": pg_password,
            "DB_NAME": "etz_chaim",
            "POSTGRES_PASSWORD": pg_password,
            "POSTGRES_PORT": str(pg_port),
            "ETZ_CHAIM_DB_URL": (
                f"postgresql://etz:{pg_password}@localhost:{pg_port}/etz_chaim"
            ),
        })
        typer.echo(f"  ✓ Docker-managed Postgres on port {pg_port}")
    typer.echo("")


def _configure_providers(non_interactive: bool, preset: str | None,
                         env_vals: dict[str, str]) -> tuple[str, set[str]]:
    """Steps 3-5 : providers, credentials, profile. Returns (profile_name, picked_envs)."""
    typer.echo("[3/8] LLM providers")
    if non_interactive:
        if not preset or preset not in PRESETS:
            typer.echo(
                f"  ✗ --preset required (one of : {', '.join(PRESETS)})",
                err=True,
            )
            raise typer.Exit(2)
        profile_name, expected_envs = PRESETS[preset]
        picked: set[str] = set()
        for env_name in expected_envs:
            val = os.environ.get(env_name, "")
            if val:
                env_vals[env_name] = val
                picked.add(env_name)
        typer.echo(f"  ✓ Preset {preset} → profile {profile_name}")
        return profile_name, picked

    typer.echo("  Pick one or more providers. You will enter keys next.")
    typer.echo("")
    for tier_name, tier_list in PROVIDERS.items():
        typer.echo(f"  [{tier_name}]")
        for _, name, url in tier_list:
            typer.echo(f"    • {name}  →  {url}")
        typer.echo("")

    selected = _multiselect_providers()
    picked: set[str] = set()

    typer.echo("")
    typer.echo("[4/8] API keys")
    for env_name, display, url in selected:
        existing = os.environ.get(env_name, "")
        if existing:
            env_vals[env_name] = existing
            picked.add(env_name)
            typer.echo(f"  ✓ {display} — reading from environment")
            continue

        if env_name.startswith("USE_") and env_name.endswith("_CLI"):
            # CLI subscription toggle — no secret, just 1/0.
            typer.echo(f"  {display} — will install the binary + set {env_name}=1")
            env_vals[env_name] = "1"
            picked.add(env_name)
            continue

        if env_name in {"OLLAMA_HOST", "VLLM_HOST", "LMSTUDIO_HOST", "LOCALAI_HOST"}:
            default = "http://localhost:11434" if "OLLAMA" in env_name else ""
            value = typer.prompt(f"  {env_name}", default=default)
        elif env_name == "AWS_ACCESS_KEY_ID":
            value = typer.prompt(f"  {env_name}", default="")
            secret = typer.prompt("  AWS_SECRET_ACCESS_KEY", hide_input=True, default="")
            if secret:
                env_vals["AWS_SECRET_ACCESS_KEY"] = secret
                picked.add("AWS_SECRET_ACCESS_KEY")
            region = typer.prompt("  AWS_REGION_NAME", default="us-east-1")
            env_vals["AWS_REGION_NAME"] = region
            picked.add("AWS_REGION_NAME")
        elif env_name == "AZURE_API_KEY":
            value = typer.prompt(f"  {env_name}", hide_input=True, default="")
            base = typer.prompt("  AZURE_API_BASE (https://<resource>.openai.azure.com)", default="")
            if base:
                env_vals["AZURE_API_BASE"] = base
                picked.add("AZURE_API_BASE")
            env_vals["AZURE_API_VERSION"] = typer.prompt(
                "  AZURE_API_VERSION", default="2024-08-01-preview"
            )
            picked.add("AZURE_API_VERSION")
        elif env_name == "CLOUDFLARE_API_KEY":
            value = typer.prompt(f"  {env_name}", hide_input=True, default="")
            account = typer.prompt("  CLOUDFLARE_ACCOUNT_ID", default="")
            if account:
                env_vals["CLOUDFLARE_ACCOUNT_ID"] = account
                picked.add("CLOUDFLARE_ACCOUNT_ID")
        else:
            value = typer.prompt(f"  {env_name}", hide_input=True, default="")

        if value:
            env_vals[env_name] = value
            picked.add(env_name)

    # Step 5 : profile composition.
    typer.echo("")
    typer.echo("[5/8] Profile composition")
    profile_name = _auto_pick_profile(picked)
    typer.echo(f"  Auto-picked profile : {profile_name}")
    override = typer.prompt(
        "  Override ? Enter profile name or leave empty",
        default=profile_name,
    )
    return override or profile_name, picked


_PROFILE_TO_CLI_TOGGLE: dict[str, str] = {
    "claude_max":  "USE_CLAUDE_CODE_CLI",
    "codex_cli":   "USE_CODEX_CLI",
    "gemini_cli":  "USE_GEMINI_CLI",
    "copilot_cli": "USE_COPILOT_CLI",
}


def _profile_needs_cli(profile_name: str) -> str | None:
    """Return the env toggle for a CLI-subscription profile, else None."""
    return _PROFILE_TO_CLI_TOGGLE.get(profile_name)


def _auto_pick_profile(envs: set[str]) -> str:
    """Return the best-fit profile name from config.yaml given picked env vars.

    Priority order (most capable / most common first) :
        hybrid > frontier cloud > aggregator > enterprise cloud > local
    """
    if "ANTHROPIC_API_KEY" in envs and "OLLAMA_HOST" in envs:
        return "hybrid"
    if "ANTHROPIC_API_KEY" in envs:
        return "anthropic_full"
    if "OPENAI_API_KEY" in envs:
        return "openai_full"
    if "GOOGLE_API_KEY" in envs:
        return "gemini_full"
    if "XAI_API_KEY" in envs:
        return "xai_full"
    if "MISTRAL_API_KEY" in envs:
        return "mistral_full"
    if "COHERE_API_KEY" in envs:
        return "cohere_full"
    if "DEEPSEEK_API_KEY" in envs:
        return "deepseek_full"
    if "OPENROUTER_API_KEY" in envs:
        return "openrouter_full"
    if "GROQ_API_KEY" in envs:
        return "groq_full"
    if "TOGETHER_API_KEY" in envs:
        return "together_full"
    if "FIREWORKS_API_KEY" in envs:
        return "fireworks_full"
    if "PERPLEXITY_API_KEY" in envs:
        return "perplexity_full"
    if "AWS_ACCESS_KEY_ID" in envs:
        return "bedrock_full"
    if "AZURE_API_KEY" in envs:
        return "azure_full"
    # CLI-subscription toggles (OAuth, no API key).
    if "USE_CLAUDE_CODE_CLI" in envs:
        return "claude_max"
    if "USE_CODEX_CLI" in envs:
        return "codex_cli"
    if "USE_GEMINI_CLI" in envs:
        return "gemini_cli"
    if "USE_COPILOT_CLI" in envs:
        return "copilot_cli"
    if "OLLAMA_HOST" in envs:
        return "local_only"
    return "local_only"  # safe default


def _configure_web_auth(non_interactive: bool, env_vals: dict[str, str]) -> int:
    typer.echo("")
    typer.echo("[6/8] Web & auth")
    web_port = _pick_free_port(8080, 8099)
    api_key = _secrets.token_urlsafe(24)
    secret_key = _secrets.token_urlsafe(24)
    allow_anon = "0"
    if not non_interactive:
        web_port_in = typer.prompt("  WEB_PORT", default=str(web_port))
        try:
            web_port = int(web_port_in)
        except ValueError:
            pass
        allow_anon = "1" if typer.confirm(
            "  Allow anonymous dashboard access ? (not recommended in prod)",
            default=False,
        ) else "0"
    env_vals.update({
        "WEB_PORT": str(web_port),
        "ETZ_CHAIM_API_KEY": api_key,
        "ETZ_CHAIM_SECRET_KEY": secret_key,
        "ETZ_CHAIM_ALLOW_ANON": allow_anon,
    })
    typer.echo(f"  ✓ Web port {web_port} · allow_anon={allow_anon}")
    return web_port


def _configure_observability(non_interactive: bool, env_vals: dict[str, str]) -> None:
    typer.echo("")
    typer.echo("[7/8] Observability (optional — leave empty to skip)")
    env_vals["LOG_LEVEL"] = "INFO"
    if non_interactive:
        env_vals["SENTRY_DSN"] = ""
        env_vals["OTEL_EXPORTER_OTLP_ENDPOINT"] = ""
        env_vals["OTEL_SERVICE_NAME"] = "etz-chaim-ai"
        return
    typer.echo("  Error tracking  : https://sentry.io/signup/ (free tier, DSN under")
    typer.echo("                    Settings → Projects → your-project → Client Keys)")
    typer.echo("  Tracing         : any OpenTelemetry-compatible vendor — Honeycomb,")
    typer.echo("                    Grafana Cloud, Datadog, Jaeger (self-hosted), etc.")
    typer.echo("")
    env_vals["LOG_LEVEL"] = typer.prompt("  LOG_LEVEL", default="INFO")
    env_vals["SENTRY_DSN"] = typer.prompt("  SENTRY_DSN (optional)", default="")
    env_vals["OTEL_EXPORTER_OTLP_ENDPOINT"] = typer.prompt(
        "  OTEL_EXPORTER_OTLP_ENDPOINT (optional)", default="",
    )
    env_vals["OTEL_SERVICE_NAME"] = "etz-chaim-ai"


@app.command()
def onboard(
    non_interactive: bool = typer.Option(
        False, "--non-interactive", help="No prompts — requires --preset.",
    ),
    preset: str = typer.Option(
        None, "--preset",
        help=f"One of : {', '.join(PRESETS)}",
    ),
    skip_start: bool = typer.Option(
        False, "--skip-start", help="Configure only, don't run compose up.",
    ),
    skip_compose: bool = typer.Option(
        False, "--no-compose", help="Skip Docker Compose entirely (BYO infrastructure).",
    ),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Don't auto-open the dashboard in the default browser.",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Auto-accept all dependency install prompts (useful with --non-interactive).",
    ),
    skip_deps: bool = typer.Option(
        False, "--skip-deps",
        help="Don't offer to install missing local dependencies (Docker / Postgres / Ollama).",
    ),
    no_ceremony: bool = typer.Option(
        False, "--no-ceremony",
        help="Skip the birth ceremony (minimal banner only).",
    ),
) -> None:
    """Interactive 8-step install wizard.

    Walks through : system detection, database, LLM providers, API keys,
    profile composition, web + auth, observability, review + start.

    Use --non-interactive --preset <name> for CI / scripted setups.
    Use --no-compose to skip Docker entirely (requires BYO Postgres).
    """
    typer.echo("")
    typer.echo("═══════════════════════════════════════════════════════════")
    typer.echo("  Etz Chaim AI — onboard wizard (v0.2.1)")
    typer.echo("═══════════════════════════════════════════════════════════")
    typer.echo("")

    # ── Step 1 : detect ────────────────────────────────────────────
    typer.echo("[1/8] System detection")
    os_name = detect.detect_os()
    runtime = detect.detect_docker_runtime()
    compose_profile = detect.detect_compose_profile()
    typer.echo(f"  OS              : {os_name}")
    typer.echo(f"  Docker runtime  : {runtime or 'NOT FOUND'}")
    typer.echo(f"  Compose profile : {compose_profile}")

    if not skip_compose:
        if runtime is None:
            typer.echo("")
            if skip_deps:
                typer.echo("✗ Docker runtime not found and --skip-deps set. Install one of :")
                typer.echo("  - OrbStack (macOS, recommended, free)  https://orbstack.dev")
                typer.echo("  - Docker Desktop  https://docker.com")
                typer.echo("  - Colima  https://colima.dev")
                typer.echo("  - podman + podman-compose (Linux)")
                typer.echo("Or re-run with --no-compose to skip Docker entirely.")
                raise typer.Exit(1)
            ok = installers.install_docker(non_interactive=non_interactive, yes=yes)
            if not ok:
                typer.echo("")
                typer.echo("Docker still missing. Re-run `etzchaim onboard` once installed,")
                typer.echo("or pass --no-compose to skip Docker entirely.")
                raise typer.Exit(1)
            runtime = detect.detect_docker_runtime() or "installed"
        if not detect.docker_is_running():
            typer.echo("")
            typer.echo(f"⚠ {runtime} is installed but not running. Start it then retry.")
            raise typer.Exit(1)
    typer.echo("  ✓ System OK")
    typer.echo("")

    env_vals: dict[str, str] = {"TZ": os.environ.get("TZ", "UTC"), "ETZCHAIM_VERSION": "0.2.0"}

    # ── Steps 2-5 ──────────────────────────────────────────────────
    _configure_database(non_interactive, env_vals, skip_deps=skip_deps, yes=yes)
    profile_name, _picked = _configure_providers(non_interactive, preset, env_vals)

    # If Ollama ended up selected, offer to auto-install it + pull models.
    if not skip_deps and "OLLAMA_HOST" in env_vals and env_vals.get("OLLAMA_HOST"):
        typer.echo("")
        typer.echo("Ollama check ...")
        installers.install_ollama(non_interactive=non_interactive, yes=yes, pull_models=True)

    # CLI subscription tools : install the binary (npm / gh extension).
    if not skip_deps:
        cli_toggles = {
            "USE_CLAUDE_CODE_CLI": installers.install_claude_code_cli,
            "USE_CODEX_CLI":       installers.install_codex_cli,
            "USE_GEMINI_CLI":      installers.install_gemini_cli,
            "USE_COPILOT_CLI":     installers.install_copilot_cli,
        }
        for toggle, installer_fn in cli_toggles.items():
            if env_vals.get(toggle) == "1" or (
                profile_name in {"claude_max", "codex_cli", "gemini_cli", "copilot_cli"}
                and _profile_needs_cli(profile_name) == toggle
            ):
                typer.echo("")
                installer_fn(non_interactive=non_interactive, yes=yes)
                env_vals.setdefault(toggle, "1")
    env_vals["ETZ_CHAIM_ACTIVE_PROFILE"] = profile_name

    # ── Step 6 ─────────────────────────────────────────────────────
    web_port = _configure_web_auth(non_interactive, env_vals)

    # ── Step 7 ─────────────────────────────────────────────────────
    _configure_observability(non_interactive, env_vals)

    # Defaults
    env_vals.setdefault("OLLAMA_HOST", "http://localhost:11434")
    env_vals.setdefault("EMBEDDING_PROVIDER", "ollama")
    env_vals.setdefault("EMBEDDING_MODEL", "nomic-embed-text")
    env_vals.setdefault("EMBEDDING_DIMENSIONS", "768")
    env_vals.setdefault("MAZAL_RECTIFICATION_MODE", "observe")
    env_vals.setdefault("DAEMON_AUTO_IMPROVE_HOUR", "21")

    # ── Step 8 : review + write + start ────────────────────────────
    typer.echo("")
    typer.echo("[8/8] Review")
    typer.echo(f"  Profile   : {profile_name}")
    typer.echo(f"  DB        : {env_vals.get('ETZ_CHAIM_DB_URL', '—')}")
    typer.echo(f"  Web port  : {web_port}")
    non_empty_keys = [
        k for k in env_vals
        if k.endswith(("_API_KEY", "_API_TOKEN", "_ACCESS_KEY_ID", "_HOST"))
        and env_vals[k] and env_vals[k] != "http://localhost:11434"
    ]
    typer.echo(f"  Providers : {', '.join(non_empty_keys) or '—'}")

    if not non_interactive:
        if not typer.confirm("  Confirm ?", default=True):
            typer.echo("Aborted.")
            raise typer.Exit(1)

    ensure_state_dir()
    compose.extract_compose_files()
    typer.echo(f"  Compose extracted : {compose_dir()}")

    _write_env_file(env_vals)
    typer.echo(f"  .env written : {env_file()} (chmod 600 on Unix)")

    if skip_start or skip_compose:
        typer.echo("")
        typer.echo("✓ Configuration complete.")
        if skip_compose:
            typer.echo("  You chose --no-compose : provision Postgres yourself, then run :")
            typer.echo("    etzchaim start --no-compose")
        else:
            typer.echo("  Start services when ready : etzchaim start")
        return

    typer.echo("")
    typer.echo("Starting services (docker compose up -d) ...")
    rc = compose.compose_up(profile=compose_profile)
    if rc != 0:
        typer.echo("✗ compose up failed. Check `etzchaim logs`.", err=True)
        raise typer.Exit(rc)

    dashboard_url = f"http://localhost:{web_port}"
    api_key = env_vals["ETZ_CHAIM_API_KEY"]

    from etzchaim.cli import ceremony as _cer
    from etzchaim.cli.ceremony._terminal import should_play_ceremony, terminal_size

    cols, _ = terminal_size()
    if should_play_ceremony(non_interactive=non_interactive, no_ceremony=no_ceremony):
        try:
            result = _cer.play_ceremony(width=cols)
        except KeyboardInterrupt:
            typer.echo("\nCeremony aborted. Use `etzchaim ceremony --preview` to retry.", err=True)
            raise typer.Exit(130)
    else:
        result = _cer.play_compact()

    env_vals["ETZCHAIM_SHEM"] = result.shem
    env_vals["ETZCHAIM_BIRTHTIME"] = result.birthtime.isoformat()
    _write_env_file(env_vals)

    typer.echo("")
    born_local = result.birthtime.strftime("%Y-%m-%d %H:%M:%S")
    tz_name = result.birthtime.tzname() or result.birthtime.strftime("%z")
    typer.echo(f"  ◉ {result.shem}   ·   born {born_local} · {tz_name}")
    typer.echo(f"              ·   listening at {dashboard_url}")
    typer.echo("")
    typer.echo(f"  API key: {api_key}")
    typer.echo(f"  .env:    {env_file()}")
    typer.echo("")

    if not no_browser:
        try:
            import webbrowser
            webbrowser.open(dashboard_url)
        except Exception:
            pass
