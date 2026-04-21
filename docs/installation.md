# Installation

Etz Chaim AI is installable as a Python package plus a thin CLI wrapper.
Three installation paths are supported :

| Path | When to use | Setup time |
|:---|:---|:---|
| **Wizard** | Fresh machine, accept the defaults | 5–10 min |
| **Docker Compose** | Self-hosted, managed infrastructure | 15 min |
| **Manual** | BYO Postgres / Ollama / enterprise LLM cloud | 30 min |

## Requirements

### Mandatory

- **Python 3.12+** (tested on 3.13)
- **PostgreSQL 16+** with the `pgvector` extension enabled
- **Docker** runtime, *if* you want the bundled compose stack
  ([OrbStack](https://orbstack.dev), Docker Desktop, or Colima)

### Recommended

- **TimescaleDB** extension on your Postgres. If present, heartbeats,
  routing logs, Beinoni interactions, and Malakh logs are stored as
  hypertables (compressed, auto-partitioned). Absent → the same tables
  fall back to plain Postgres tables, no functional loss.

  ```bash
  # macOS
  brew install timescaledb
  # or (Homebrew is already tapped) :
  brew install timescale/tap/timescaledb

  # Debian / Ubuntu
  apt install timescaledb-2-postgresql-16

  # enable in your database
  psql etz_chaim -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;'
  ```

### Optional — pick the LLM provider(s) you will use

| Provider | Env var(s) | Free tier | Best olam |
|:---|:---|:---:|:---|
| **Ollama** (local) | `OLLAMA_HOST` | ✓ | All (degraded quality) |
| **Anthropic** | `ANTHROPIC_API_KEY` | — | Atziluth, Briah |
| **OpenAI** | `OPENAI_API_KEY` | — | All tiers |
| **Google Gemini** | `GOOGLE_API_KEY` | ✓ (limits) | All tiers |
| **xAI** (Grok) | `XAI_API_KEY` | — | Yetzirah, Assiah |
| **Mistral** | `MISTRAL_API_KEY` | ✓ (limits) | Yetzirah, Assiah |
| **DeepSeek** | `DEEPSEEK_API_KEY` | — | Briah (reasoning) |
| **Cohere** | `COHERE_API_KEY` | ✓ (limits) | Yetzirah, embeddings |
| **OpenRouter** | `OPENROUTER_API_KEY` | — | All (any upstream model) |
| **Together AI** | `TOGETHER_API_KEY` | — | Yetzirah, Assiah |
| **Groq** | `GROQ_API_KEY` | ✓ (limits) | Assiah (latency-critical) |
| **Fireworks** | `FIREWORKS_API_KEY` | — | All tiers |
| **Perplexity** | `PERPLEXITY_API_KEY` | — | Tool-augmented Yetzirah |
| **AWS Bedrock** | `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` | — | Enterprise-compliant Claude |
| **Azure OpenAI** | `AZURE_API_KEY` + `AZURE_API_BASE` | — | Enterprise-compliant GPT |
| **HuggingFace** | `HUGGINGFACE_API_KEY` | ✓ (limits) | Open-weight models |
| **NVIDIA NIM** | `NVIDIA_NIM_API_KEY` | — | GPU-hosted frontier models |
| **Cloudflare AI** | `CLOUDFLARE_API_KEY` + `CLOUDFLARE_ACCOUNT_ID` | ✓ (limits) | Edge inference |
| **Replicate** | `REPLICATE_API_TOKEN` | — | Custom deployments |
| **Claude Code CLI** | `claude login` (OAuth) | — | Claude Max subscribers |

Embeddings-specific providers — one of these is required :

| Provider | Env var | Model example |
|:---|:---|:---|
| **Ollama** (default) | `OLLAMA_HOST` | `nomic-embed-text` (768 dim) |
| **OpenAI** | `OPENAI_API_KEY` | `text-embedding-3-small` (1536) |
| **Cohere** | `COHERE_API_KEY` | `embed-multilingual-v3.0` (1024) |
| **Voyage AI** | `VOYAGE_API_KEY` | `voyage-3` (1024) |
| **Jina AI** | `JINA_API_KEY` | `jina-embeddings-v3` (1024) |

### Ollama models to pull (for local_only / hybrid profiles)

If you use the Ollama-backed profiles, pull the models before running `etzchaim start` :

```bash
ollama pull nomic-embed-text    # embeddings — always required if EMBEDDING_PROVIDER=ollama
ollama pull qwen3.5:9b          # reasoning — used by local_only and hybrid profiles
```

Total disk footprint ≈ 6 GB. `etzchaim doctor` will report missing models.

## Path 1 — Wizard (recommended)

```bash
pip install etzchaim
etzchaim onboard
# → answer 8 prompts (system, DB, LLM providers, profile, web, observability)
# → http://localhost:8080
```

The wizard detects your environment and, for any missing local dependency,
asks **`[Y/n]`** before installing it automatically on macOS (Homebrew) or
Debian / Ubuntu (apt). You are never expected to run install commands
yourself unless you want to.

Auto-installed on demand :

| Dependency | macOS | Debian / Ubuntu |
|:---|:---|:---|
| Docker runtime | `brew install --cask orbstack` | Official `get.docker.com` script |
| PostgreSQL 16 | `brew install postgresql@16` | `apt install postgresql-16` |
| pgvector | `brew install pgvector` | `apt install postgresql-16-pgvector` |
| TimescaleDB | `brew install timescale/tap/timescaledb` | `apt install timescaledb-2-postgresql-16` |
| Ollama | `brew install ollama` | `curl -fsSL https://ollama.com/install.sh \| sh` |
| Ollama models | `ollama pull nomic-embed-text` + `ollama pull qwen3.5:9b` | same |

Flags :

```bash
etzchaim onboard --skip-start            # configure only, don't start services
etzchaim onboard --yes                   # auto-accept all install prompts
etzchaim onboard --skip-deps             # never offer to install dependencies
etzchaim onboard --no-browser            # don't auto-open the dashboard
etzchaim onboard --non-interactive --preset local-only   # scripted
etzchaim onboard --non-interactive --preset anthropic-full --yes
```

## Path 2 — Docker Compose (manual)

If you prefer to manage the compose file yourself :

```bash
git clone https://github.com/yohanpoul/etz-chaim-ai
cd etz-chaim-ai
cp .env.example .env
# edit .env : set at least ETZ_CHAIM_DB_URL, ANTHROPIC_API_KEY (or equivalent)
docker compose -f etzchaim/deploy/docker-compose.yml up -d
docker compose exec app etzchaim doctor
```

## Path 3 — Bring Your Own Infrastructure

You already run Postgres and / or Ollama ? Skip Docker entirely.

```bash
# 1. Prepare the database (pgvector is mandatory, timescaledb is optional).
createdb etz_chaim
psql etz_chaim -c 'CREATE EXTENSION IF NOT EXISTS vector;'
psql etz_chaim -c 'CREATE EXTENSION IF NOT EXISTS timescaledb;' || true  # optional
for f in etzchaim/deploy/init-db/*.sql; do psql etz_chaim -f "$f"; done

# 2. Install the package and create a config.
pip install etzchaim
cp $(python -c 'import etzchaim; print(etzchaim.__path__[0])')/../.env.example ~/.etzchaim/.env
# edit ~/.etzchaim/.env to point at your Postgres + pick LLM providers

# 3. Start the services manually.
etzchaim start --no-compose
```

## Verification

```bash
etzchaim doctor
# expected : 5/5 checks green — Postgres, pgvector, migrations, at least one
# LLM provider reachable, web bind free
```

Load the demo corpus to verify end-to-end :

```bash
etzchaim demo
# seeds 5 acts of doctrinal data, runs a walkthrough
```

## Upgrade

```bash
etzchaim update
# pip install --upgrade + compose pull + apply migrations + restart + doctor
```

## Uninstall

```bash
etzchaim stop
docker compose -f ~/.etzchaim/compose/docker-compose.yml down -v   # removes data
pip uninstall etzchaim
rm -rf ~/.etzchaim
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|:---|:---|:---|
| `etzchaim onboard` says `Docker runtime not found` | OrbStack / Docker Desktop not installed | Install one of the listed runtimes, or rerun with `--no-compose` |
| `etzchaim doctor` fails on `pgvector` | Extension not enabled | `psql <db> -c 'CREATE EXTENSION vector;'` |
| `etzchaim doctor` warns `TimescaleDB absent` | Optional extension missing | Safe to ignore (fallback to plain tables), or install per the [Recommended](#recommended) section |
| `etzchaim doctor` fails on `No LLM provider reachable` | All provider env vars empty or invalid | Check `.env`, try `etzchaim onboard` again |
| `etzchaim doctor` fails on `Ollama model not pulled` | `nomic-embed-text` or `qwen3.5:9b` missing | `ollama pull nomic-embed-text` (and `qwen3.5:9b` for local_only profile) |
| Dashboard loads but `/api/*` returns 503 | `ETZ_CHAIM_API_KEY` empty and `ETZ_CHAIM_ALLOW_ANON=0` | Either set the API key or flip `ALLOW_ANON=1` |
| Port 8080 collision | Another service on that port | Wizard auto-picks 8081-8099, or set `WEB_PORT` |
| Init SQL fails on `create_hypertable` | Pre-v0.2.1 install without TimescaleDB | Upgrade to v0.2.1+ — hypertable calls are now guarded |
