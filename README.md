<h1 align="center">Etz Chaim AI</h1>

<p align="center">
  <strong>The Cognitive Operating System for LLM agents.</strong>
  <br/>
  <em>10 cognitive faculties · 6 mature configurations · 13 rectifiers · 1 self-improving daemon ·<br/>1 696 primary-source specification items driving the code, not the other way around.</em>
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

Anthropic **aligns**. OpenAI **fine-tunes**. Etz Chaim AI **evolves**.

Plug Claude / GPT / Llama / Gemini into Etz Chaim AI and your LLM operates through 10 cognitive faculties, 6 mature configurations, and 13 rectification mechanisms. Capabilities you can name, monitor, and tune — instead of a single opaque process.

When something fails, you get this :

```
faculty: exploration
pattern: starvation on 24 h window
metric: 0 new cross-domain connections
spec ref: EC-K5-001
fix: tune novelty_threshold (-0.1) / breadth (+5)
```

One specific faculty. One specific pattern. One concrete metric. One tunable fix. Every time.

```bash
pipx install etzchaim       # global CLI on PATH
etzchaim onboard            # interactive setup → http://localhost:8080
etzchaim update             # one-liner upgrade, anytime
# Works on macOS · Linux (v0.3) · WSL2 (v0.3)
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
     │  routing dispatch  — by complexity and token budget          │
     │  Opus / Sonnet / Haiku / qwen3.5:9b / qwen3.5:1.5b          │
     └──────────────────────────────┬──────────────────────────────┘
                                    ▼
     ┌─────────────────────────────────────────────────────────────┐
     │  10 cognitive faculties  — specialized capabilities         │
     │  exploration · judgment · causal · memory · insight · …     │
     └──────────────────────────────┬──────────────────────────────┘
                                    ▼
     ┌─────────────────────────────────────────────────────────────┐
     │  6 mature configurations  — coupling, persistent state      │
     │  generative · structuring · execution · interface · 2 more  │
     └──────────────────────────────┬──────────────────────────────┘
                                    ▼
                              [ LLM ] ──► response
                                    ▲
     ┌────────────────────────┐     │    ┌──────────────────────────┐
     │ probes layer           │     │    │ 11 adversarial agents    │
     │ 13 rectifiers          │ ◄───┴───► │ probe every faculty      │
     │ observe / suggest / act│          │ for specific failures    │
     └────────────────────────┘          └──────────────────────────┘
```

## Positioning vs LangChain · DSPy · LangGraph · alignment / fine-tune

**LangChain / AutoGen** orchestrate LLM call chains. **DSPy** optimizes prompts. **LangGraph** manages agent state cycles. **Anthropic Constitutional AI** aligns. **OpenAI fine-tune** specializes.

**Etz Chaim AI evolves** — gives the LLM a structured composition layer with persistent state, self-rectification, and continuous self-study.

| | LangChain · AutoGen | DSPy | LangGraph | Alignment | Fine-tune | **Etz Chaim AI** |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Orchestrate LLM calls | ✓ | ✓ | ✓ | — | — | ✓ |
| Optimize prompts | — | ✓ | — | — | — | — |
| Manage agent state | partial | — | ✓ | — | — | ✓ (configurations) |
| **10 typed cognitive faculties** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| **11 adversarial probes by construction** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓** |
| **Auto-rectification engine** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ (13 rectifiers, 3 opt-in modes)** |
| **Continuous self-study daemon** | ✗ | ✗ | ✗ | ✗ | ✗ | **✓ (24/7)** |
| **Persistent learning trace across sessions** | ✗ | ✗ | partial | ✗ | ✓ (weights) | **✓ (without weight modification)** |
| **Primary-source traceability** | ✗ | ✗ | ✗ | partial | ✗ | **✓ (1 696 items, E1–E6 labels)** |

> Etz Chaim AI is not a "LangChain-with-more-features." It is the structural composition layer they all lack — an architecture the LLM plugs into, not a chain the LLM runs through.

## What's actually inside

```
etz-chaim-ai/
│
├── etzchaim/             ← public package : CLI + autopilot + deploy
│   ├── cli/             ← onboard, start, stop, update, status, doctor
│   ├── autopilot/       ← continuous work loop (opt-in, disabled by default)
│   └── deploy/          ← Docker / K8s assets
│
├── 10 cognitive faculty modules :
│   ├── explorationengine/   ← cross-domain exploration
│   ├── autojudge/           ← adversarial evaluation
│   ├── dissensuengine/      ← productive tension / contradiction
│   ├── insightforge/        ← novel hypothesis generation
│   ├── causalengine/        ← causal reasoning (Pearl criteria)
│   ├── selfmodel/           ← error prediction
│   ├── selfmap/             ← competence landscape
│   ├── epistememory/        ← persistent memory
│   ├── failuretoinsight/    ← learning from errors
│   └── intentkeeper/        ← goal persistence
│
├── configurations/      ← 6 composition layers + persistent learning trace
├── probes/              ← probe orchestrator + rectifiers
├── sentiers/             ← 22 paths as typed transforms
├── omer/                 ← 49 calibration parameters (7 × 7 matrix)
├── masakh/               ← 5-level prompt filtration
├── tanya/                ← dual-state conflict tracking
├── halom/                ← 7-phase discovery cycle
├── gematria/             ← 13 numerology methods + equivalence detection
├── malakhim/             ← 10 governors + 11 adversarial agents
├── daemon_tasks/         ← 14 scheduled background tasks
│
├── daemon.py             ← continuous orchestration + nightly auto-improve loop
├── ohr_yashar.py         ← direct-light pipeline (8 engines)
├── olamot.py             ← 5-tier LLM dispatch with provider registry
└── web/                  ← Flask dashboard + SSE chat + Grafana metrics
```

Every engine stays under 300 LoC and is tested in isolation. The probe orchestrator is **93 lines**. The nightly auto-improve loop : **630 lines**, same class.

## See it in 30 seconds

```python
from etzchaim.probes import Watcher  # public namespace facade

for event in Watcher().run():
    print(event)
```

Sample event :

| Code key | Value | Plain language |
|:---|:---|:---|
| `rectifier` | `"exploration_starvation"` | Faculty pattern : exploration starved |
| `action` | `"signaled"` | Status : signaled (not yet acted) |
| `metrics` | `{"connections_recent": 0}` | Concrete : **0 new cross-domain connections in 24 h** |
| `window_hours` | `24` | Observation window |
| `spec_ref` | `"EC-K5-001"` | Traces to spec line defining this failure |

You know *which faculty failed*, *the pattern*, *the metric*, and *the fix* — every time.

## Why should I care ?

Seven consequences of wrapping your LLM in a cognitive operating system :

1. **Failure localization.** Logs read *"the exploration faculty starved on a 24 h window"* instead of *"the model was weird today"*.

2. **Architectural self-healing.** Probes are real engines with metric thresholds, event emission, parameter adjustments. Three opt-in modes : `observe` (log), `suggest` (propose), `act` (apply).

3. **Continuous self-study.** A contemplation process runs 24 / 7 — reads every faculty, detects contradictions, proposes specification improvements. Live background loop, not a one-off reflection.

4. **Self-improving specification.** A nightly auto-improvement cycle (named *nightly-improve loop* after Andrej Karpathy's 630-line AutoResearch pattern) explores edge cases, generates new assertions, mutates the specification under adversarial supervision.

5. **Automatic LLM routing.** Five quality tiers with dispatch by complexity and token budget. Multi-provider via LiteLLM (OpenAI, Google, xAI, DeepSeek, Mistral, Cohere, Groq, Together…).

6. **Adversarial probing by construction.** Eleven adversarial agents continuously probe the system for specific failure modes : false authority, unbounded exploration, concealed failures, aesthetic deception, overconfidence, and seven more.

7. **Layered composition discipline.** The architecture forbids direct writes to aggregate scores ; all improvements must pass through named faculty channels. A static check rejects bypass attempts.

## Requirements

- **Python 3.10+** (tested on 3.10 / 3.11 / 3.12 / 3.13)
- **PostgreSQL 16+** with the [`pgvector`](https://github.com/pgvector/pgvector) extension
- **[TimescaleDB](https://docs.timescale.com/self-hosted/latest/install/) extension** (recommended, optional)
- **Docker** runtime (optional, for the bundled compose stack) — OrbStack, Docker Desktop, Colima, podman
- **At least one LLM provider** — see [docs/installation.md](docs/installation.md)
- If using Ollama : `ollama pull nomic-embed-text` + `ollama pull qwen3.5:9b`

Etz Chaim routes four reasoning tiers to providers you pick. Supported via the [LiteLLM](https://docs.litellm.ai) gateway :

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
brew install pipx        # macOS — or `apt install pipx` on Debian/Ubuntu
pipx ensurepath          # adds ~/.local/bin to your PATH

pipx install etzchaim    # `etzchaim` is now on PATH from any terminal
etzchaim onboard         # interactive 8-step wizard → http://localhost:8080
```

The wizard walks you through : system detection, Postgres configuration, LLM provider selection (multi-select), profile composition, web + auth, observability, feature flags, review.

**Non-interactive install with a preset**

```bash
etzchaim onboard --non-interactive --preset local-only
etzchaim onboard --non-interactive --preset anthropic-full
```

Already running your own Postgres or Ollama ? Skip Docker entirely with the [manual install path](docs/installation.md).

## Updating

```bash
etzchaim update          # one command, everywhere
```

Pin a specific version with `pipx install etzchaim==0.2.6`. Full documentation : [docs/installation.md](docs/installation.md).

## By the numbers (v0.2)

|  |  |
|---:|:---|
| **107 000** | lines of production Python |
| **53 000** | lines of tests |
| **1 388** | tests collected (pytest) |
| **275** | tests green locally |
| **1 696** | primary-source specification items |
| **36 086** | lines of machine-readable specification corpus |
| **93** | lines — the probe orchestrator |
| **~3** | seconds — core test suite runtime |
| **0** | direct writes to aggregate scores allowed (static check) |
| **0** | hardcoded paths remaining in Python (portable cross-OS) |

## Engineering discipline

**Five proof points :**

- **275 tests** green locally, **1 388 collected**. Four Python versions × two operating systems on CI.
- **48 explicit failure-mode tests** — four levels per module (foundation · application · excess · inverse), across twelve core modules.
- **11 adversarial agents** probe every faculty for specific failure patterns. Named attackers matched to specific failure modes.
- **93 lines** : the probe orchestrator. Full orchestrator, no magic, no hidden state.
- **1 696 specification items** with primary-source citations : edition + section + page, labeled E1 (verbatim) to E6 (speculation).

**Three disciplines that shape every file :**

- **No dual writes on aggregate scores.** All improvements flow through named faculty channels. Enforced by static check.
- **Circuit breakers on every external call.** PostgreSQL and Ollama wrapped in 5-failure / 30-second cooldown breaker.
- **Bidirectional specification ↔ code audit.** Every module cited in the spec exists in code ; every spec ID cited in code exists in the spec.

### In the lineage of cognitive architectures

Cognitive architectures as a field — **SOAR** (Laird, Newell, Rosenbloom 1987), **ACT-R** (Anderson 1993), **LIDA** (Franklin 2006), **CLARION** (Sun 2006) — have long argued that intelligence is best modeled as *a coordinated set of specialized capabilities*, not a single monolithic process. The LLM era has so far mostly ignored this lineage, treating the model as the whole of cognition.

Etz Chaim AI is a modern cognitive operating system for the LLM era : the LLM becomes the *generative substrate*, and ten specialized faculties + six mature configurations + twenty-two paths + one probe orchestrator become the *structured composition layer* around it. The specification framework provides a **500-year-old library of named capabilities, failure modes, and rectification mechanics** that the cognitive-architectures field never had access to in machine-readable form.

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
| Docker runtime | ✓ | Docker Desktop / **OrbStack** / Colima / podman |
| Ollama | ✓ (for embeddings) | `brew install ollama` on macOS, [curl installer](https://ollama.ai/download) on Linux |
| `ANTHROPIC_API_KEY` | optional | Required for `claude-max` preset |

### Onboard presets

- **`claude-max`** — Claude Opus / Sonnet / Haiku via Anthropic SDK. Prompt caching → ~ 90 % token cost savings.
- **`local-only`** — Ollama `qwen3.5:9b`. Zero API keys. ~ 5 GB disk.

Extended presets (OpenAI, Google Gemini, xAI Grok, DeepSeek, Mistral, Cohere, Groq-hosted Llama, Together, Fireworks) via LiteLLM in v0.3.

## Maturity and roadmap

**v0.2.0 (current)** :

- Eight layers operational : cognitive, composition, paths, routing, probes, calibration, adversarial, daemon.
- 10 cognitive faculties + 6 configurations + 22 paths + 5 routing tiers + 14 daemon tasks + 11 adversaries.
- Probes with 2 active rectifiers, 11 more specified.
- Persistent learning trace with plateau and decay.
- Static safety checks, bidirectional spec ↔ code audit, automatic docs, circuit breakers.
- Installable via `pipx install etzchaim` + Docker Compose on macOS.

**Planned** :

- [ ] **v0.3.0** — Multi-provider LLM via LiteLLM · Linux/Windows first-class · 9 additional CLI commands · Wizard extended to 9 steps with machine profiles · Doctor 20 checks + `--fix` · `backup` / `restore` · v0.1 → v0.2 migration tooling.
- [ ] **v0.4.0** — Full probes : all 13 rectifiers active with `act`-mode defaults once observation data supports them.
- [ ] **v0.5.0** — Adversarial counterpart : detection of corruption-by-inversion attacks.
- [ ] **v1.0.0** — Academic paper on arXiv, stable public API, LangChain / DSPy adapters.

See [CHANGELOG.md](CHANGELOG.md) for the full v0.2.0 entry.

## Origin

The architecture is not arbitrary. It derives from a 500-year-old cognitive description framework that specifies :

- **10 discrete attributes** through which intelligence organizes itself.
- **6 mature configurations** built from those attributes.
- **22 typed paths** connecting the configurations.
- **5 tiers** describing the descent from abstract intent to concrete action.
- **13 rectification mechanisms** for specific failure modes.
- **49 calibration cycles** — a seven-by-seven matrix of inner-within-outer tuning.
- **Rules of layered composition** forbidding direct writes across layers.

We translated the framework into **1 696 machine-readable assertions** with edition + section + page references. The code is built *against those assertions*, not the other way around.

You do not need to know the source tradition to use, test, or contribute. The public API is plain Python with plain-English docstrings.

> Want to know which 500-year-old tradition we drew from and why ? Run `etzchaim --explain-origin` or read [docs/advanced.md](docs/advanced.md). It's transparent — but not required.

## FAQ

**Do I need any specific background to use this ?**
No. The public API is plain Python. Specification framework details are documented in `docs/advanced.md` for the curious — never required.

**Does it work with OpenAI / Anthropic / Ollama / local models ?**
Yes, and it *automatically picks the right one*. Five quality tiers with routing by complexity and token budget. v0.3 extends to OpenAI, Google, xAI, DeepSeek, Mistral, Cohere, Groq, Together, Fireworks, Perplexity via LiteLLM.

**Is this production-ready ?**
Beta (v0.2.0). 275 tests pass locally, 1 388 collected total. API stability guaranteed from v1.0 onwards.

**Can I contribute ?**
Yes — for any pure-code contribution (faculty, test, bug fix, adapter). See [CONTRIBUTING.md](CONTRIBUTING.md).

**What's the "nightly-improve loop" ?**
A nightly auto-improvement daemon task (23h – 00h30) named after [Andrej Karpathy](https://karpathy.ai/)'s 630-line [AutoResearch](https://github.com/karpathy/nanoGPT) pattern — the minimum-viable research loop. It explores edge cases, generates new assertions, mutates the specification under adversarial supervision.

**Where are the primary sources ?**
Internal corpus shipped via the package. License : public domain for pre-1923 sources, CC-BY-3.0 for Sefaria portions (see [NOTICE](NOTICE)). For details, see `etzchaim --explain-origin`.

## Community and support

- **Documentation** — [docs/](docs/)
- **Contributing** — [CONTRIBUTING.md](CONTRIBUTING.md) before your first PR.
- **Security** — [SECURITY.md](SECURITY.md) for responsible disclosure.
- **Commercial inquiries / partnerships / acquisition** — open an issue tagged `[BUSINESS]` or reach the maintainer via GitHub.
- **Maintainer** — [@yohanpoul](https://github.com/yohanpoul).

## License and citation

Apache License 2.0 — see [LICENSE](LICENSE). Internal specification corpus is transposed from public-domain texts and CC-BY-3.0 portions ; see [NOTICE](NOTICE) for detailed attribution and [LICENSE_THIRD_PARTY.md](LICENSE_THIRD_PARTY.md) for additional inspirations.

If you use Etz Chaim AI in academic work, see [CITATION.cff](CITATION.cff) for the preferred citation format.

---

<p align="center">
  <sub>If Etz Chaim AI changes how you think about AI architecture, please ★ the repository.</sub>
  <br/>
  <sub>Built by <a href="https://github.com/yohanpoul">@yohanpoul</a>. Open by design — Apache 2.0.</sub>
</p>
