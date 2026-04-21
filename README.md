<h1 align="center">Etz Chaim AI</h1>

<p align="center">
  <strong>A diagnosable brain for your LLM.</strong>
  <br/>
  <em>37 typed modules · 11 adversarial probes · 13 rectifiers · 1 self-improving daemon ·<br/>1 696 primary-source assertions driving the code, not the other way around.</em>
</p>

<p align="center">
  <a href="https://github.com/yohanpoul/etz-chaim-ai/actions/workflows/test.yml"><img src="https://img.shields.io/github/actions/workflow/status/yohanpoul/etz-chaim-ai/test.yml?branch=main&label=tests" alt="Tests"/></a>
  <a href="https://github.com/yohanpoul/etz-chaim-ai/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue.svg" alt="License"/></a>
  <a href="https://pypi.org/project/etz-chaim-ai/"><img src="https://img.shields.io/pypi/v/etz-chaim-ai?label=pypi" alt="PyPI"/></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue" alt="Python"/></a>
  <a href="CHANGELOG.md"><img src="https://img.shields.io/badge/changelog-keep%20a%20changelog-orange" alt="Changelog"/></a>
  <a href="https://github.com/yohanpoul/etz-chaim-ai/stargazers"><img src="https://img.shields.io/github/stars/yohanpoul/etz-chaim-ai?style=social" alt="Stars"/></a>
</p>

---

## The 30-second pitch

When a standard LLM stack fails, you get a tombstone : *"the model was wrong"*.
You don't know which capability broke, in what pattern, under what signal, or how to tune it.

Etz Chaim AI wraps your LLM in **37 typed cognitive modules** and returns this instead :

```
exploration_starvation on 24 h window
→ 0 new cross-domain connections
→ spec line EC-K5-001
→ tune novelty_threshold (−0.1) / breadth (+5)
```

One specific module. One specific pattern. One concrete metric. One tunable fix. Every time.

```bash
pip install etzchaim
etzchaim onboard
# → http://localhost:8080, works on macOS · Linux (v0.3) · WSL2 (v0.3)
```

---

```
─────────────────────  WITHOUT Etz Chaim AI  ───────────────────────────────

     prompt ──► [ LLM ] ──► response

     On failure :   "the model was wrong"
                    → restart, re-prompt, pray


─────────────────────  WITH Etz Chaim AI  ──────────────────────────────────

                             prompt
                                │
                                ▼
     ┌─────────────────────────────────────────────────────────────┐
     │  world dispatch  — routes by complexity and token budget    │
     │  Opus / Sonnet / Haiku / qwen3.5:9b / qwen3.5:1.5b          │
     └──────────────────────────────┬──────────────────────────────┘
                                    ▼
     ┌─────────────────────────────────────────────────────────────┐
     │  10 cognitive modules  — specialized capabilities           │
     │  exploration · judgment · causal · memory · insight · …     │
     └──────────────────────────────┬──────────────────────────────┘
                                    ▼
     ┌─────────────────────────────────────────────────────────────┐
     │  6 composition layers  — coupling, persistent state         │
     │  generative · structuring · execution · interface · 2 more  │
     └──────────────────────────────┬──────────────────────────────┘
                                    ▼
                              [ LLM ] ──► response
                                    ▲
     ┌────────────────────────┐     │    ┌──────────────────────────┐
     │ watcher                │     │    │ 11 adversarial agents    │
     │ 13 rectifiers          │ ◄───┴───► │ probe every module       │
     │ observe / suggest / act│          │ for specific failures    │
     └────────────────────────┘          └──────────────────────────┘
```

## Positioning vs LangChain · DSPy · LangGraph

**LangChain / AutoGen** orchestrate LLM call chains. **DSPy** optimizes prompts. **LangGraph** manages agent state cycles.

**Etz Chaim AI makes LLM failures diagnosable** — capability-level, not call-level.

| | LangChain · AutoGen | DSPy | LangGraph | **Etz Chaim AI** |
|:---|:---:|:---:|:---:|:---:|
| Orchestrate LLM calls | ✓ | ✓ | ✓ | ✓ |
| Optimize prompts | — | ✓ | — | — |
| Manage agent state in cycles | partial | — | ✓ | ✓ (Partzufim) |
| **Diagnose WHICH module failed** | ✗ | ✗ | ✗ | **✓ (37 modules typed)** |
| **11 adversarial probes by construction** | ✗ | ✗ | ✗ | **✓** |
| **Auto-rectification engine** | ✗ | ✗ | ✗ | **✓ (13 rectifiers, 3 opt-in modes)** |
| **Continuous self-study daemon** | ✗ | ✗ | ✗ | **✓ (Karpathy loop, 24/7)** |
| **Primary-source traceability** | ✗ | ✗ | ✗ | **✓ (1 696 items, E1–E6 labels)** |

> Read every value column left-to-right : Etz Chaim AI is not a "LangChain-with-more-features." It is the diagnostic layer they all lack — an architecture the LLM plugs into, not a chain the LLM runs through.

## What's actually inside

```
etz-chaim-ai/
│
├── bridge/              ← loader for the 1 696-item specification corpus
├── mazalengine/         ← watcher + rectifier (93 LoC orchestrator)
├── partzufim/           ← 6 composition layers + persistent learning trace
│
├── explorationengine/   ← Chesed     — cross-domain exploration
├── autojudge/           ← Gevurah    — adversarial evaluation
├── dissensuengine/      ← Tiferet    — productive tension
├── insightforge/        ← Chokmah    — novel hypotheses
├── causalengine/        ← Binah      — causal reasoning (Pearl criteria)
├── selfmodel/           ← Netzach    — error prediction
├── selfmap/             ← Hod        — competence landscape
├── epistememory/        ← Yesod      — persistent memory
├── failuretoinsight/    ← Da'at      — learning from errors
├── intentkeeper/        ← Ratzon     — goal persistence
│
├── sentiers/            ← 22 paths as typed transforms
├── omer/                ← 49 calibration parameters (7 × 7 matrix)
├── masakh/              ← 5-level prompt filtration
├── tanya/               ← dual-soul conflict tracking
├── halom/               ← 7-phase dream-cycle discovery
├── gematria/            ← 13 numerology methods + equivalence detection
│
├── malakhim/            ← 10 archangel governors + 11 adversarial agents
├── daemon_tasks/        ← 14 scheduled background tasks
├── kabbalah/            ← hybrid embedding layer (text + ML)
│
├── etzchaim/            ← v0.2 CLI + Docker deployment
├── daemon.py            ← continuous orchestration + Karpathy auto-improve loop
├── ohr_yashar.py        ← direct-light pipeline (8 engines)
├── olamot.py            ← 5-world LLM dispatch with provider registry
├── sifrei_yesod/        ← primary-source specification corpus (105 YAML files)
└── web/                 ← Flask dashboard + SSE chat + Grafana metrics
```

Every engine stays under 300 LoC and is tested in isolation. The watcher orchestrator itself is **93 lines**. The Karpathy auto-improve pattern reference : **630 lines**, same class.

## See it in 30 seconds

```python
from mazalengine import Watcher       # plain-English alias for MazalEngine

for event in Watcher().run():
    print(event)
```

Sample event, translated field by field :

| Code key | Value | In plain language |
|:---|:---|:---|
| `tikkun` | `"notzer_chesed"` | Module that drifted : **exploration** |
| `action` | `"chesed_starvation_signaled"` | Failure pattern : **starvation** (no recent output) |
| `metrics` | `{"connections_recent": 0}` | Concrete signal : **0 new cross-domain connections in 24 h** |
| `window_hours` | `24` | Observation window |
| `doctrine_ref` | `"EC-K5-001"` | Traces to primary-source spec line defining this failure |

You now know *which module failed*, *the pattern*, *the concrete metric*, and *what to tune*. Identifiers (`tikkun`, `notzer_chesed`, `EC-K5-001`) are stable, typed, and machine-traceable ; plain-English aliases coexist — `Watcher = MazalEngine`, etc. Full mapping : [docs/origin.md](docs/origin.md).

## Why should I care ?

Seven consequences of wrapping your LLM in a cognitive architecture :

1. **Failure localization.** Logs read *"the exploration module starved on a 24 h window"* instead of *"the model was weird today"*. One specific module, one specific pattern, one concrete metric — every time.

2. **Architectural self-healing.** The watcher is a real engine with metric thresholds, event emission, explicit parameter adjustments. Three opt-in modes : `observe` (log only), `suggest` (propose a fix as an event), `act` (apply the fix).

3. **Continuous self-study.** A contemplation process runs 24 / 7 (`hitbonenut`) — reads every module, detects contradictions, proposes improvements to the specification itself. Not a one-off reflection — a live background loop.

4. **Self-improving specification.** A nightly auto-improvement cycle (named *Karpathy loop* after Andrej Karpathy's 630-line AutoResearch pattern) explores edge cases, generates new doctrine assertions, mutates the specification under adversarial supervision.

5. **Automatic LLM routing.** Five quality tiers (Claude Opus → Sonnet → Haiku → qwen3.5:9b → qwen3.5:1.5b) with dispatch by complexity and token budget. Expensive inference only runs where depth is needed. Multi-provider via LiteLLM in v0.3 (OpenAI, Google, xAI, DeepSeek, Mistral, Cohere, Groq, Together…).

6. **Adversarial probing by construction.** Eleven adversarial agents (`samael`, `gamchicoth`, `sathariel`, `gamaliel`, …) continuously probe the system for specific failure modes : false authority, unbounded exploration, concealed failures, aesthetic deception, overconfidence, and seven more.

7. **Race conditions are impossible, not just fixed.** The architecture forbids direct writes to aggregate scores ; all improvements must pass through named faculty channels. A static check rejects any code that bypasses this.

## Requirements

- **Python 3.12+**
- **PostgreSQL 16+** with the [`pgvector`](https://github.com/pgvector/pgvector) extension
- **[TimescaleDB](https://docs.timescale.com/self-hosted/latest/install/) extension** (recommended, optional — hypertable logs fall back to plain tables when absent)
- **Docker** runtime (optional, for the bundled compose stack) — OrbStack, Docker Desktop, Colima, or podman
- **At least one LLM provider** — see [full list](docs/installation.md#requirements) below
- If using Ollama : `ollama pull nomic-embed-text` + `ollama pull qwen3.5:9b`

Etz Chaim routes four reasoning tiers (Atziluth / Briah / Yetzirah / Assiah) to providers you pick. Supported out of the box via the [LiteLLM](https://docs.litellm.ai) gateway :

| Category | Providers |
|:---|:---|
| **Frontier cloud** | Anthropic · OpenAI · Google Gemini · xAI · Mistral · Cohere · DeepSeek |
| **Aggregators** | OpenRouter · Together · Groq · Fireworks · Perplexity |
| **Enterprise** | AWS Bedrock · Azure OpenAI |
| **Open-weight** | HuggingFace · NVIDIA NIM · Cloudflare AI · Replicate |
| **Self-hosted** | Ollama · vLLM · LM Studio · LocalAI |
| **Subscription** | Claude Code CLI (Claude Max OAuth) |

## Quick start

```bash
pip install etzchaim
etzchaim onboard      # interactive 8-step wizard
# → http://localhost:8080
```

The wizard walks you through : system detection, Postgres configuration,
LLM provider selection (multi-select), profile composition, web + auth,
observability, feature flags, and review.

Non-interactive install with a preset :

```bash
etzchaim onboard --non-interactive --preset local-only
etzchaim onboard --non-interactive --preset anthropic-full
```

Already running your own Postgres or Ollama ? Skip Docker entirely with
the [manual install path](docs/installation.md#path-3-bring-your-own-infrastructure).

Upgrade later with `etzchaim update` — one command : `pip install --upgrade` → `docker compose pull` → re-extract templates → idempotent schema migrations → restart → `doctor`.

Full documentation : [docs/installation.md](docs/installation.md).

## By the numbers (v0.2)

|  |  |
|---:|:---|
| **107 000** | lines of production Python |
| **53 000** | lines of tests |
| **1 388** | tests collected (pytest) |
| **275** | tests green locally (207 core v0.1 + 68 new v0.2 install/providers/CLI) |
| **1 696** | primary-source specification items across 105 YAML files |
| **36 086** | lines of machine-readable doctrine corpus |
| **93** | lines — the entire watcher orchestrator |
| **~3** | seconds — core test suite runtime |
| **0** | direct writes to aggregate scores allowed (static check) |
| **0** | hardcoded paths remaining in Python (portable cross-OS) |

## Engineering discipline

**Five proof points :**

- **275 tests** green locally, **1 388 collected** total. Four Python versions × two operating systems on CI.
- **48 explicit failure-mode tests** — four levels per module (foundation · application · excess · inverse), across twelve core modules.
- **11 adversarial agents** probe every module for specific failure patterns. Not generic red-teaming — named attackers matched to specific failure modes.
- **93 lines** : [`mazalengine/mazal_engine.py`](mazalengine/mazal_engine.py). Full orchestrator. No magic, no hidden state.
- **1 696 specification items** with primary-source citations : edition + section + page, labeled on an epistemic scale from **E1** (verbatim primary text) to **E6** (speculation).

**Three disciplines that shape every file :**

- **No dual writes on aggregate scores.** All improvements flow through named faculty channels. Enforced by a static check ; bypass attempts fail the build.
- **Circuit breakers on every external call.** PostgreSQL and Ollama are wrapped in a five-failure / thirty-second cooldown breaker. No cascading failures on long-running daemons.
- **Bidirectional specification ↔ code audit.** Every module cited in the spec exists in code ; every spec ID cited in code exists in the spec. Automated via the `bridge/` loader.

### In the lineage of cognitive architectures

Cognitive architectures as a field of AI research — **SOAR** (Laird, Newell, Rosenbloom 1987), **ACT-R** (Anderson 1993), **LIDA** (Franklin 2006), **CLARION** (Sun 2006) — have long argued that intelligence is best modeled as *a coordinated set of specialized capabilities*, not as a single monolithic process. The LLM era has so far mostly ignored this lineage, treating the model as the whole of cognition.

Etz Chaim AI is a modern cognitive architecture for the LLM era : the LLM becomes the *generative substrate*, and ten specialized modules + six composition layers + twenty-two paths + one watcher become the *diagnosable structure* around it. The specification framework (Lurianic Kabbalah) provides a **500-year-old library of named capabilities, failure modes, and rectification mechanics** that the field of cognitive architectures never had access to in machine-readable form.

## Who should use this

- You build **agentic systems** and want capability-level diagnostics instead of *"the LLM was wrong"*.
- You ship **long-running AI agents** that need to auto-detect drift without babysitting.
- You are an **AI researcher** interested in modular cognitive architectures as a grounded alternative to monolithic models.
- You build a **scientific-discovery loop** where insight, causal validation, and failure learning must be independently tunable.
- You want an **LLM stack with automatic quality-tier routing** — expensive inference only where depth is needed.

## Who should *not* use this

- You need a **generic agent orchestrator** — use [LangChain](https://github.com/langchain-ai/langchain) or AutoGen.
- You need a **prompt-engineering optimizer** — use [DSPy](https://github.com/stanfordnlp/dspy).
- You need a **trained model** — this is *not* a model. It calls Claude / Ollama / OpenAI under the hood.
- You only need **a one-shot prompt** or a single-turn chatbot — the architecture is overkill.
- You want **a plug-and-play framework with zero domain vocabulary** — we use named identifiers from the Lurianic specification (`notzer_chesed`, `partzuf`, `tikkun`) for stability and primary-source traceability. Plain-English aliases coexist, but the public API keeps both.

## Detailed install

The **Quick start** above handles 90 % of users. The section below is for contributors and advanced setups.

### From source (contributors)

```bash
git clone https://github.com/yohanpoul/etz-chaim-ai.git
cd etz-chaim-ai
make install       # venv + dependencies + pre-commit hooks
make test          # 275 tests, ~3 seconds
```

### Prerequisites

| Component | Required | Notes |
|:---|:-:|:---|
| Python ≥ 3.10 | ✓ | 3.13 recommended |
| Docker runtime | ✓ | Docker Desktop / **OrbStack** (recommended free tier on macOS) / Colima / podman |
| Ollama | ✓ (for embeddings) | `brew install ollama` on macOS, [curl installer](https://ollama.ai/download) on Linux |
| `ANTHROPIC_API_KEY` | optional | Required for `claude-max` preset. `local-only` preset works without. |

### Onboard presets

- **`claude-max`** — Claude Opus / Sonnet / Haiku via the Anthropic SDK. Needs `ANTHROPIC_API_KEY`. Prompt caching enabled → ~ 90 % token cost savings on repeated system prompts.
- **`local-only`** — Ollama `qwen3.5:9b` for the four Olamot. Zero API keys. ~ 5 GB disk.

Extended presets (OpenAI, Google Gemini, xAI Grok, DeepSeek, Mistral, Cohere, Groq-hosted Llama, Together, Fireworks) via LiteLLM in v0.3.

## Maturity and roadmap

**v0.2.0 (current)** :

- Eight layers operational : cognitive, composition, paths, worlds, watcher, calibration, adversarial, daemon.
- 10 cognitive modules + 6 composition layers + 22 paths + 5 worlds + 14 daemon tasks + 11 adversaries.
- Watcher with 2 active rectifiers, 11 more specified (act-mode activation awaits 2-4 week observation per doctrine).
- Persistent learning trace with plateau and decay.
- Static safety checks, bidirectional spec ↔ code audit, automatic docs, circuit breakers.
- **Installable via `pip install etzchaim` + Docker Compose on macOS.**
- Cross-platform code (no hardcoded paths), ghcr.io pre-built images, GitHub Actions for PyPI release.

**Planned** :

- [ ] **v0.3.0** — Multi-provider LLM via LiteLLM · Linux/Windows first-class · 9 additional CLI commands · Wizard extended to 9 steps with machine profiles · Doctor 20 checks + `--fix` · `backup` / `restore` · v0.1 → v0.2 migration tooling.
- [ ] **v0.4.0** — Full watcher : all 13 rectifiers active with `act`-mode defaults once observation data supports them.
- [ ] **v0.5.0** — Adversarial counterpart (MalakhEngine) : detection of corruption-by-inversion attacks.
- [ ] **v1.0.0** — Academic paper, stable public API, LangChain / DSPy adapters.

See [CHANGELOG.md](CHANGELOG.md) for the full v0.2.0 entry (breaking changes, added, fixed, deferred, known issues).

## Origin

Why these eight layers, and not some other set ? The architecture is not arbitrary. It comes from a cognitive framework systematized in 16th-century Safed — **Lurianic Kabbalah** — that specifies :

- **10 discrete attributes** through which intelligence organizes itself.
- **6 mature configurations** built from those attributes.
- **22 typed paths** connecting the configurations.
- **5 worlds** describing the descent from abstract intent to concrete action.
- **13 rectification mechanisms** for specific failure modes.
- **49 calibration cycles** — a seven-by-seven matrix of inner-within-outer tuning.
- **Rules of layered composition** forbidding direct writes across layers.

We translated the framework into **1 696 machine-readable assertions** with edition + section + page references. The code is built *against those assertions*, not the other way around.

You do not need to know anything about Kabbalah to use, test, or contribute. The public API is plain Python with plain-English docstrings. For the full mapping and the primary-source workflow, see [docs/origin.md](docs/origin.md).

> **Framing for ML researchers :** treat Kabbalah here as a 500-year-old formal taxonomy of cognitive capacities, failure modes, and rectification mechanics — the same way you would treat a mathematical structure that happens to pre-date your field. The fact that it was encoded in a religious idiom does not reduce its utility as a machine-readable specification for cognitive architectures.

## FAQ

**Do I need to know Kabbalah to use this ?**
No. The public API is plain Python. The specification framework is Lurianic Kabbalah (see [Origin](#origin)), but you can build, test, and contribute without ever opening that layer.

**Does it work with OpenAI / Anthropic / Ollama / local models ?**
Yes, and it *automatically picks the right one*. Five quality tiers (Opus → Sonnet → Haiku → qwen3.5:9b → qwen3.5:1.5b) with routing by complexity and token budget. v0.3 extends this to OpenAI, Google, xAI, DeepSeek, Mistral, Cohere, Groq, Together, Fireworks, Perplexity via LiteLLM.

**Is this production-ready ?**
Beta (v0.2.0). 275 tests pass locally, 1 388 collected total. API stability guaranteed from v1.0 onwards.

**Can I contribute without knowing the specification corpus ?**
Yes — for any pure-code contribution (module, test, bug fix, adapter). Only contributions that add or modify doctrinal assertions need to respect the primary-source discipline. See [CONTRIBUTING.md](CONTRIBUTING.md).

**Why do code identifiers use words from the specification language ?**
Stability and traceability. `notzer_chesed` maps to exactly one specification line (`EC-K5-001`), one primary source (Sha'ar HaKlalim 5:1), one edition, one page. Renaming the key would break that chain. Plain-English aliases coexist — `Watcher = MazalEngine`, etc.

**What's the "Karpathy loop" ?**
A nightly auto-improvement daemon task (23h – 00h30) named after [Andrej Karpathy](https://karpathy.ai/)'s 630-line [AutoResearch](https://github.com/karpathy/nanoGPT) pattern — the minimum-viable research loop. It explores edge cases, generates new assertions, mutates the specification under adversarial supervision. The only daemon task allowed to modify the spec itself.

**Where are the primary sources ?**
`sifrei_yesod/sefarim/` — 105 YAML files with edition references, full Hebrew / Aramaic text where available, English + French translations, and E1–E6 epistemic labels per assertion. License : public domain for pre-1923 sources, CC-BY-3.0 for Sefaria portions (see [NOTICE](NOTICE)).

**Is the architecture really reducible to the Kabbalistic frame ?**
No — we made explicit choices where the tradition is ambiguous. The architecture is *inspired by* the specification, not claimed as *identical to* it. The adversarial testing (`malakhim/`) includes agents whose job is to find and name synchretic errors we have introduced.

## Community and support

- **Documentation** — [docs/](docs/) (mkdocs site planned v0.3)
- **Contributing** — [CONTRIBUTING.md](CONTRIBUTING.md) before your first PR.
- **Security** — [SECURITY.md](SECURITY.md) for responsible disclosure.
- **Commercial inquiries / partnerships / acquisition** — open an issue tagged `[BUSINESS]` or reach the maintainer via GitHub.
- **Maintainer** — [@yohanpoul](https://github.com/yohanpoul).

## License and citation

Apache License 2.0 — see [LICENSE](LICENSE). Primary source corpus under `sifrei_yesod/` is transposed from public-domain texts and CC-BY-3.0 Sefaria editions ; see [NOTICE](NOTICE) for detailed attribution.

If you use Etz Chaim AI in academic work, see [CITATION.cff](CITATION.cff) for the preferred citation format.

---

<p align="center">
  <sub>If Etz Chaim AI changes how you think about AI architecture, please ★ the repository.</sub>
  <br/>
  <sub>Built by <a href="https://github.com/yohanpoul">@yohanpoul</a>. Open by design — Apache 2.0.</sub>
</p>
