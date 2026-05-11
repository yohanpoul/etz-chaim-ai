# Etz Chaim AI — Cognitive OS for LLM agents

> Apache 2.0 · Multi-provider · Anthropic-optimized, OpenAI/Google/local supported
> Maintainer: [@yohanpoul](https://github.com/yohanpoul) ·
> Build: standards-first ([agentskills.io](https://agentskills.io), [MCP](https://modelcontextprotocol.io), [AGENTS.md](https://agents.md))

This file is the **single source of truth** for agent instructions across all tools.
- `CLAUDE.md` (Anthropic Claude Code) → symlinks to this file
- `.codex/AGENTS.md` (OpenAI Codex CLI) → symlinks to this file
- `.cursor/rules/etz-base.mdc` → references this file

Run `scripts/setup-symlinks.sh` after cloning to wire these up.

## Layered project rules — Claude Code auto-loads these

In addition to this file, Claude Code automatically loads **engineering discipline
rules** from `.claude/rules/`. These are **orthogonal** to AGENTS.md and apply
across every session in this repo:

| File | Lines | Purpose |
|---|---|---|
| [`.claude/rules/session-discipline.md`](.claude/rules/session-discipline.md) | 24 | depth > breadth, E1–E6, isomorphism gate, plan order |
| [`.claude/rules/python-dev.md`](.claude/rules/python-dev.md) | 20 | Py 3.12+, type hints, device-agnostic torch, ruff, **never hardcode model names** |
| [`.claude/rules/public-surface-neutrality.md`](.claude/rules/public-surface-neutrality.md) | 176 | CI-gated no-Hebrew rule, rename map, scan script |
| [`.claude/rules/kabbalistic-rigor.md`](.claude/rules/kabbalistic-rigor.md) | 33 | rigor for internal doctrinal work |
| [`.claude/rules/hitlabshut.md`](.claude/rules/hitlabshut.md) | 115 | layered composition discipline |
| [`.claude/rules/reshimu_persistence.md`](.claude/rules/reshimu_persistence.md) | 107 | persistent trace coefficient discipline |

When AGENTS.md and `.claude/rules/` overlap, both apply jointly. When they
conflict, file an issue — that's a contract bug we must resolve in writing.

## Critical Invariants — never violate

These 8 invariants distinguish Etz Chaim AI from a generic RAG or prompt-chain
system. Violating any of them silently breaks the self-improvement loop.

1. **Channel-only writes to aggregate scores** — use named channels (causalengine,
   explorationengine, etc.). No direct mutation of `*.aggregate_score`.
2. **Circuit breaker on all external LLM calls** — 5 failures / 30s cooldown,
   exponential backoff up to 5 minutes.
3. **Plan mode + verify-spec for spec mutations** — every spec corpus change
   goes through Plan mode (Shift+Tab×2 in Claude Code) and the `verify-spec`
   subagent before PR approval.
4. **Citations E1–E6** on every new spec assertion (E1=verbatim primary source,
   E6=speculative). Enforced by `make verify-bidirectional`.
5. **Test budget <3 seconds** for the 1388-test fast suite. Slow tests go in
   `tests/slow/` and run nightly.
6. **One-shot installable** — `pipx install etzchaim` or devcontainer "reopen
   in container" must take <5 minutes from clone to operational.
7. **Provider-agnostic core** — every LLM call goes through `config.yaml`
   profile resolution. No hardcoded model strings in business logic.
8. **Public-surface neutrality** — zero Hebrew doctrinal terms in public
   paths (`README`, `docs/`, `web/`, CLI surfaces, spec filenames, paper body).
   Internal aliases only. CI gate: [`scripts/check_public_surface.sh`](scripts/check_public_surface.sh).
   Full rule: [`.claude/rules/public-surface-neutrality.md`](.claude/rules/public-surface-neutrality.md).

## Architecture in one paragraph

Etz Chaim AI is a cognitive operating system for LLM agents in the lineage of
SOAR / ACT-R / CLARION / LIDA. **10 cognitive faculties** (exploration, judgment,
causal, dissensus, insight, selfmodel, selfmap, epistememory, failuretoinsight,
intentkeeper) compose into **6 mature configurations**, route through
**22 typed paths (sentiers)**, and are policed by **13 rectifiers**. The corpus
holds **1696 primary-source specs** with E1–E6 confidence labels. A nightly
**auto-improve daemon** (`daemon.py`, ~2554 lines) implements the Karpathy
AutoResearch pattern. See [`memory/ARCHITECTURE.md`](memory/ARCHITECTURE.md) for
the full system contract.

## Provider stack — the real configuration

LLM dispatch is **profile-keyed**, not single-model. Configuration lives in:

| File | Role |
|---|---|
| [`config.yaml`](config.yaml) | **Source unique** — 6 profiles, full slugs, env-driven |
| [`etzchaim/deploy/config.yaml`](etzchaim/deploy/config.yaml) | Autopilot loop config (`loop.py:150`) |
| [`etzchaim/providers/registry.py`](etzchaim/providers/registry.py) | `select_claude_backend()` — picks `anthropic_sdk` if `ANTHROPIC_API_KEY` set, else `claude_cli` subprocess |
| [`etzchaim/providers/anthropic_sdk.py`](etzchaim/providers/anthropic_sdk.py) | Direct SDK path (`client.messages.create`) |
| [`etzchaim/providers/litellm_provider.py`](etzchaim/providers/litellm_provider.py) | LiteLLM path (`self._litellm.completion`) — used for non-Anthropic providers |

### The 6 profiles in `config.yaml`

| Profile | Use case |
|---|---|
| `claude_max` | Anthropic Pro/Max plan via Claude Code CLI (no API key needed) |
| `sefira_full` | Full Anthropic API via key (Opus + Sonnet + Haiku 4.x) |
| `gpt5_full` | OpenAI GPT-5.x family via API |
| `gemini_full` | Google Gemini 3 family via API |
| `bedrock` | Anthropic models via AWS Bedrock |
| `benchmark_opus` | Fixed Opus build for benchmark reproducibility |

To switch provider: edit `config.yaml`'s active profile. See [`docs/PORTABILITY.md`](docs/PORTABILITY.md)
for the full guide. **Switching to GPT-5.5 or Gemini 3 Pro is a profile swap.**

### Model registry — single source of truth (Sprint 1)

To eliminate model-string drift (currently 2 leak sites: `claude_skill.py:29`
default + `anthropic_sdk.py::MODEL_SLUGS` table), Sprint 1 introduces
[`etzchaim/llm/model_registry.py`](etzchaim/llm/model_registry.py) as the single
source for all model aliases. After Sprint 1, no module hardcodes a model slug.

## Available Tools

### Skills (`/skills/`, auto-synced to `.claude/skills/`, `.codex/skills/`, `.cursor/skills/`)

| Skill | Purpose |
|---|---|
| `etz-faculty-exploration` | Cross-domain exploration & cognitive surprise |
| `etz-faculty-judgment` | Autojudge & adversarial evaluation |
| `etz-faculty-causal-pearl` | Pearl criteria (do-calculus, backdoor, frontdoor, IV) |
| `etz-faculty-dissensus` | Contradiction & belief-divergence detection |
| `etz-faculty-insight` | Hypothesis generation & insight forging |
| `etz-faculty-selfmodel` | Predict own errors before they occur |
| `etz-faculty-selfmap` | Track competence landscape |
| `etz-faculty-epistememory` | Persistent epistemic memory |
| `etz-faculty-failuretoinsight` | Learn from past errors |
| `etz-faculty-intentkeeper` | Goal persistence across context shifts |
| `etz-spec-lookup` | Query the 1696 spec corpus (manual only) |
| `etz-rectifier-diagnose` | Invoke the 13 rectifiers |
| `etz-gematria-equivalence` | 13 equivalence mappings (internal aliases) |

### MCP server — `etzchaim-mcp` (Sprint 5)
- **15 tools**: 5 diagnostic + 7 cognitive + 3 spec
- Consumed by Claude Code, Codex CLI, Cursor, Windsurf, ChatGPT Developer Mode

### Subagents (`/agents/`, Sprint 3)
- `triage` — initial dispatch to the right faculty
- `verify-spec` — Boris pattern: refuse "done" without proof
- `improve-loop` — nightly Karpathy auto-research worker
- `spec-auditor` — bidirectional spec↔code audit
- `doctor` — 20 health checks

### Slash commands (`/commands/`, Sprint 3)
- `/diagnose-faculty <name>`
- `/spec <EC-XX-NNN>`
- `/mutate-spec` — Plan mode + verify gate
- `/verify-bidirectional`
- `/batch-migration` — parallel worktree workers
- `/adversarial-probe` — 11 malakhim parallel
- `/mistake-to-rule` — append to `memory/MISTAKES.md`
- `/insights-weekly` — flywheel from past 7 days

## Standard Commands

```bash
make test                      # 1388-test fast suite, ~3 seconds (HARD GATE)
make doctor                    # 20 health checks
make verify-bidirectional      # spec↔code audit
make check-public-surface      # Hebrew-term leakage scan (CI-gated)
etzchaim improve               # trigger nightly improve loop manually
etzchaim probes --adversarial  # run the 11 malakhim
pipx install etzchaim          # canonical install
```

## Behavior Rules (Boris-aligned)

1. **Plan Mode** (Shift+Tab×2 in Claude Code) for any spec mutation.
   _Boris: "Most sessions start in Plan mode. Then auto-accept can one-shot it."_
   — [thread](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)

2. **Use the `verify-spec` subagent** before marking ANY task complete.
   _Boris: "Give Claude a way to verify its work. 2-3× the quality of the final result."_
   — [VentureBeat manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)

3. **Every mistake → `memory/MISTAKES.md`** rule (via `/mistake-to-rule`).
   _Boris: "Every time we see Claude do something incorrectly, we add it to CLAUDE.md."_

4. **For batch / migration work, use `/batch-migration`** — spawns N worktree workers
   in parallel. _Boris's [`/batch` announcement (Feb 27, 2026)](https://github.com/NousResearch/hermes-agent/issues/380)._

5. **For adversarial validation, use `/adversarial-probe`** — 11 malakhim run in
   parallel worktrees. _Pattern: [worktree subagents](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj) (Feb 20, 2026)._

6. **Never `--dangerously-skip-permissions` outside a sandbox.**
   _Prefer [Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode)
   (Max/Team/Enterprise) — Sonnet 4.6 classifier + prompt-injection probe._

7. **Verify externally:** for UI-touching changes, exercise the Flask+SSE
   dashboard at `/health` and `/grafana` before marking done.

8. **Public-surface scan** — before any PR that touches `README`, `docs/`,
   `web/`, CLI surfaces, or spec filenames, run `make check-public-surface`
   locally. CI will block PRs with Hebrew doctrinal terms in public paths.

## Provider Compatibility

This project is **standards-first, Anthropic-optimized.**

| Layer | Standard | Portable? |
|---|---|---|
| Cognitive engine | Python + LiteLLM (100+ providers) + provider registry | ✓ 100% |
| Skills | [agentskills.io](https://agentskills.io) (35+ tools) | ✓ 100% |
| MCP | [AAIF / Linux Foundation](https://github.com/modelcontextprotocol) | ✓ 100% |
| Agent config | [AGENTS.md (AAIF)](https://agents.md) | ✓ 100% |
| Bonus features | Auto Mode, Routines, Channels, Managed Agents, Dreaming, Outcomes | ⚠ Anthropic-only |

**Switching providers**: edit the active profile in `config.yaml`. Full guide:
[`docs/PORTABILITY.md`](docs/PORTABILITY.md).

## Reference Documents (in-repo)

- [`memory/ARCHITECTURE.md`](memory/ARCHITECTURE.md) — system invariants & faculty contracts
- [`memory/MISTAKES.md`](memory/MISTAKES.md) — anti-patterns we've encountered (**LIVING DOCUMENT**)
- [`memory/DECISIONS.md`](memory/DECISIONS.md) — Architecture Decision Records
- [`docs/PORTABILITY.md`](docs/PORTABILITY.md) — cross-provider switching guide
- [`docs/CODE_WITH_CLAUDE_2026.md`](docs/CODE_WITH_CLAUDE_2026.md) — Anthropic 2026 features map
- [`docs/REFERENCES.md`](docs/REFERENCES.md) — full external reference index
- [`config.yaml`](config.yaml) — **the real provider configuration**

## Key external references (curated)

### Boris Cherny — creator of Claude Code
- [Pinned workflow thread (Jan 2, 2026)](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)
- [Tips compendium](https://howborisusesclaudecode.com/)
- [Worktree announcement (Feb 20, 2026)](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj)
- [VentureBeat manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)

### Anthropic engineering — foundational papers
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Writing tools for agents (Ken Aizawa)](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Code Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode)

### Standards
- [Agent Skills](https://agentskills.io)
- [AGENTS.md (Linux Foundation AAIF)](https://agents.md)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Claude Code documentation](https://code.claude.com/docs/)

For the complete reference index see [`docs/REFERENCES.md`](docs/REFERENCES.md).
