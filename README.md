# Etz Chaim AI

> **A cognitive operating system for LLM agents.**
> Apache 2.0 · Multi-provider · Standards-first · Anthropic-optimized

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Provider-agnostic](https://img.shields.io/badge/provider-agnostic-green.svg)](docs/PORTABILITY.md)
[![Built on standards](https://img.shields.io/badge/standards-Skills_%2B_MCP_%2B_AGENTS.md-orange)](docs/PORTABILITY.md)

In the SOAR / ACT-R / CLARION / LIDA lineage, Etz Chaim AI gives LLM agents
**10 cognitive faculties**, **13 rectifiers**, **11 adversarial probes**,
**22 typed paths**, **1696 primary-source specs** with E1–E6 confidence
labels, and a **nightly auto-improve daemon** that mutates its own
specifications based on observed failures.

It works on Anthropic Claude, OpenAI GPT-5.5, Google Gemini 3, and local
models via Ollama — switch in <30 minutes. See [PORTABILITY.md](docs/PORTABILITY.md).

## Why Etz Chaim AI?

Today's coding agents are powerful but ahistorical. They forget. They
repeat the same mistakes. They have no model of what they don't know,
no way to detect when they're drifting from spec, no nightly housekeeping
that consolidates yesterday's failures into tomorrow's improvements.

Etz Chaim AI fills that gap with composable cognitive primitives that
plug into Claude Code, Codex CLI, Cursor, Windsurf, Antigravity,
OpenCode, or your own custom harness via the open Agent Skills + MCP
standards.

## Installation — choose your tier

We support three install tiers based on your budget and trust model.

### 🥉 Bronze — local & private ($0)

Fully local. No external API calls. Privacy-first.

```bash
# Prerequisites: Python 3.12+, Docker (for pgvector + TimescaleDB)
# Recommended local model: qwen3:72b or llama3.3:70b
ollama pull qwen3:72b

pipx install etzchaim
etzchaim init --provider ollama --model qwen3:72b
etzchaim doctor    # validates the install
```

Use cases: privacy-sensitive research, education, OSS contributors, air-gapped.
Trade-offs: slower inference; smaller context; some features (Auto Mode,
Channels, Routines, Managed Agents) unavailable.

### 🥈 Silver — pay-per-token API ($5–50/month typical)

API key from any provider. Most flexible.

```bash
pipx install etzchaim
export OPENAI_API_KEY=sk-...          # or ANTHROPIC_API_KEY or GEMINI_API_KEY
etzchaim init --provider openai --model gpt-5.5
etzchaim doctor
```

Supported providers (via [LiteLLM](https://github.com/BerriAI/litellm), 100+):
Anthropic, OpenAI, Google Vertex / Gemini, AWS Bedrock, Azure OpenAI,
xAI, Mistral, Cohere, DeepSeek, Groq, Together, Fireworks, OpenRouter,
Perplexity, NVIDIA NIM, Cloudflare AI, Replicate, vLLM, LM Studio.

Use cases: most contributors; teams evaluating Etz Chaim; multi-provider
experiments.

### 🥇 Gold — Anthropic Pro/Max + Managed Agents ($20–200/month)

Full Etz Chaim experience with the Anthropic-bonus layer wired in.

```bash
# Open in VS Code or GitHub Codespaces and "Reopen in Container"
gh repo clone yohanpoul/etz-chaim-ai
code etz-chaim-ai
# F1 → "Dev Containers: Reopen in Container"
# (or open in Codespaces — free 60h/month tier works)
```

Unlocks:
- **Auto Mode** (Max/Team/Enterprise) — Sonnet 4.6 classifier on every tool call
- **Channels** — Telegram / Discord / iMessage push alerts for drift events
- **Claude Code Routines** — nightly auto-improve loop runs on Anthropic
  infrastructure (your laptop doesn't need to be on)
- **Managed Agents + Dreaming + Outcomes + Multiagent orchestration** — the
  11 malakhim adversaries as parallel specialist sub-agents with persistent
  memory
- **Cowork Dispatch** — assign work to Etz Chaim from your phone, work
  finishes on your desktop

If you maintain an active OSS project, apply for the
**[Claude for Open Source Program](https://claude.com/contact-sales/claude-for-oss)**
— 6 months of Claude Max free for approved OSS maintainers. Deadline:
June 30, 2026. See [`scripts/apply-oss-program.md`](scripts/apply-oss-program.md)
for our application template.

## Quick start

After install, in your project directory:

```bash
# 1. Run the doctor
etzchaim doctor               # 20 health checks should pass

# 2. Try a faculty
etzchaim faculty causal-pearl \
  --query "Does drinking coffee cause better focus?"

# 3. Run the bidirectional spec↔code audit
etzchaim verify-bidirectional

# 4. (Optional) trigger the auto-improve loop manually
etzchaim improve --once

# 5. Connect a coding agent
# Claude Code: just run `claude` in this directory; .claude/ and skills/ are pre-wired
# Codex CLI:   run `codex` — reads AGENTS.md and .codex/skills/
# Cursor:      open the folder — .cursor/rules/etz-base.mdc references AGENTS.md
```

## The architecture in 30 seconds

```
┌──────────────────────────────────────────────────────────────────┐
│  10 facultés cognitives                                          │
│  exploration · judgment · causal · dissensus · insight           │
│  selfmodel · selfmap · epistememory · failuretoinsight · intent  │
└─────────────────────┬────────────────────────────────────────────┘
                      │ compose via 22 sentiers (typed paths)
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  6 mature configurations                                         │
│  diagnose · explore · judge · synthesize · audit · learn         │
└─────────────────────┬────────────────────────────────────────────┘
                      │ policed by
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  13 rectifiers + 11 malakhim adversaries                         │
│  Background daemons detecting drift, contradictions, decay       │
└─────────────────────┬────────────────────────────────────────────┘
                      │ feed into
                      ▼
┌──────────────────────────────────────────────────────────────────┐
│  Nightly auto-improve daemon (Karpathy pattern)                  │
│  Read failure traces → propose spec mutations → verify → PR      │
└──────────────────────────────────────────────────────────────────┘
```

The full architecture: [`memory/ARCHITECTURE.md`](memory/ARCHITECTURE.md).

## Why standards-first?

Etz Chaim is built on **open standards**, not vendor-specific APIs:

- **[Agent Skills](https://agentskills.io)** — 13 portable SKILL.md files,
  work in Claude Code, Codex CLI, Cursor, Gemini CLI, Antigravity, OpenCode,
  goose, Letta, Amp, Devin (35+ platforms)
- **[Model Context Protocol](https://modelcontextprotocol.io)** —
  `etzchaim-mcp` server consumable by any MCP client (Claude Code, Codex,
  Cursor, Windsurf, ChatGPT Dev Mode)
- **[AGENTS.md (Linux Foundation AAIF)](https://agents.md)** — single
  source of truth, symlinked to `CLAUDE.md` / `.codex/AGENTS.md`
- **[LiteLLM](https://github.com/BerriAI/litellm)** — 100+ LLM providers
  via OpenAI-compatible interface

Switching from Anthropic Claude to OpenAI GPT-5.5 is **one line** in
`litellm.config.yaml`. The cognitive engine, the rectifiers, the spec
corpus, the daemon — all keep working. See [PORTABILITY.md](docs/PORTABILITY.md).

## Contributing

Etz Chaim follows the
**[Boris Cherny workflow](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)**
adapted for cognitive-architecture work:

1. **Start in Plan mode** (Shift+Tab×2 in Claude Code) for any spec mutation
2. **Run the `verify-spec` subagent** before marking complete (the 2-3×
   quality boost insight)
3. **Every mistake → `memory/MISTAKES.md`** rule (`/mistake-to-rule`)
4. **For batch changes → `/batch-migration`** (parallel worktree workers)
5. **For adversarial validation → `/adversarial-probe`** (11 malakhim in
   parallel)
6. **CLAUDE.md is a symlink to AGENTS.md** — edit AGENTS.md only

Behavioral rules and Boris references in [`AGENTS.md`](AGENTS.md).
Full anti-pattern catalog in [`memory/MISTAKES.md`](memory/MISTAKES.md).

See [`memory/DECISIONS.md`](memory/DECISIONS.md) for our Architecture
Decision Records (ADRs) — particularly:
- **ADR-0001**: Standards-first architecture
- **ADR-0003**: Boris's verify-spec subagent pattern
- **ADR-0004**: Skills + 5 subagents (Barry Zhang's thesis applied)

## Documentation

- [`AGENTS.md`](AGENTS.md) — agent instructions (source unique)
- [`memory/ARCHITECTURE.md`](memory/ARCHITECTURE.md) — system invariants &
  faculty contracts
- [`memory/MISTAKES.md`](memory/MISTAKES.md) — anti-patterns (living doc)
- [`memory/DECISIONS.md`](memory/DECISIONS.md) — ADRs
- [`docs/PORTABILITY.md`](docs/PORTABILITY.md) — cross-provider switching
- [`docs/CODE_WITH_CLAUDE_2026.md`](docs/CODE_WITH_CLAUDE_2026.md) —
  Anthropic 2026 features map
- [`docs/REFERENCES.md`](docs/REFERENCES.md) — full external reference index

## Roadmap

| Sprint | Focus | Status |
|---|---|---|
| 0 | Standards-first foundation + Claude for OSS application | 🟢 Active (May 2026) |
| 1 | Prompt caching, Opus 4.7, Batch API, Citations API | 🔵 Next |
| 2 | 13 Skills (cross-tool, agentskills.io standard) | 🔵 Planned |
| 3 | 5 subagents (Boris pattern, isolation: worktree) | 🔵 Planned |
| 4 | Hooks + Sandbox + Auto Mode + DevContainer | 🔵 Planned |
| 5 | MCP server `etzchaim-mcp` (npm + PyPI) | 🔵 Planned |
| 6 | Plugin distribution (5 marketplaces) | 🔵 Planned |
| 7 | Cloud asynchrone (Routines + Channels + Webhooks) | 🟡 Anthropic-only |
| 8 | Managed Agents + Dreaming + Outcomes + Multiagent | 🟡 Anthropic-only |
| 9 | arXiv paper, Code with Claude talks, v1.0 | 🟢 Q3 2026 |

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Citation

If you use Etz Chaim AI in research, please cite:

```bibtex
@software{etz_chaim_ai_2026,
  author = {Yohan Poul},
  title = {Etz Chaim AI: A Cognitive Operating System for LLM Agents},
  year = {2026},
  url = {https://github.com/yohanpoul/etz-chaim-ai},
  license = {Apache-2.0}
}
```

## Acknowledgments

Etz Chaim AI builds directly on the work of:

- **Anthropic** for the Skills + MCP + Auto Mode foundations, and the
  engineering papers that shaped the architecture
- **Boris Cherny** (creator of Claude Code) whose workflow patterns are
  encoded throughout this project — [thread](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)
- **Barry Zhang & Mahesh Murag** for the
  ["Don't build agents, build skills"](https://www.youtube.com/watch?v=CEvIs9y1uog)
  thesis we apply
- **Erik Schluntz** for the
  [Building Effective Agents](https://resources.anthropic.com/building-effective-ai-agents)
  patterns
- **Andrej Karpathy** for the autonomous research loop concept that
  underlies our nightly daemon
- **Sun, Anderson, Newell, Franklin, Pearl** for the cognitive
  architecture lineage Etz Chaim sits in
- **The Linux Foundation AAIF** for stewarding the AGENTS.md and MCP
  standards
- **The agentskills.io community** for the cross-tool skills standard
- **The LiteLLM team** for making provider-agnostic LLM dispatch routine

Full reference index: [`docs/REFERENCES.md`](docs/REFERENCES.md).
