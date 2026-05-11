# Etz Chaim AI — Cognitive OS for LLM agents

> Apache 2.0 · Multi-provider · Anthropic-optimized, OpenAI/Google/local supported
> Maintainer: [@yohanpoul](https://github.com/yohanpoul) ·
> Build: standards-first ([agentskills.io](https://agentskills.io), [MCP](https://modelcontextprotocol.io), [AGENTS.md](https://agents.md))

This file is the **single source of truth** for agent instructions across all tools.
- `CLAUDE.md` (Anthropic Claude Code) → symlinks to this file
- `.codex/AGENTS.md` (OpenAI Codex CLI) → symlinks to this file
- `.cursor/rules/etz-base.mdc` → references this file

Run `scripts/setup-symlinks.sh` after cloning to wire these up.

---

## Critical Invariants — never violate

- **0 direct writes to aggregate scores** — use named channels only (causalengine, explorationengine, etc.)
- **Every external LLM call wraps in circuit breaker** (5 failures / 30s cooldown)
- **Spec mutations REQUIRE Plan mode + `verify-spec` subagent + PR approval**
- **Citations E1–E6 required** on any new spec assertion (E1=verbatim source, E6=speculative)
- **All 1388 tests must pass in <3s** before any merge to `main`

## Architecture in one paragraph

Etz Chaim AI is a cognitive operating system for LLM agents in the lineage of
SOAR / ACT-R / CLARION / LIDA. **10 cognitive faculties** (exploration, judgment,
causal, dissensus, insight, selfmodel, selfmap, epistememory, failuretoinsight,
intentkeeper) compose into **6 mature configurations**, route through
**22 typed paths (sentiers)**, and are policed by **13 rectifiers**. The corpus
holds **1696 primary-source specs** with E1–E6 confidence labels. A nightly
**auto-improve daemon** implements the Karpathy AutoResearch pattern: read past
failure traces, propose spec mutations, verify, gate, merge. See
[`memory/ARCHITECTURE.md`](memory/ARCHITECTURE.md) for the full system contract.

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
| `etz-gematria-equivalence` | 13 numerologies and equivalence mappings |

### MCP server — `etzchaim-mcp`
- **15 tools**: 5 diagnostic + 7 cognitive + 3 spec
- Consumed by Claude Code, Codex CLI, Cursor, Windsurf, ChatGPT Developer Mode
- See [`docs/MCP_SERVER.md`](docs/MCP_SERVER.md) (Sprint 5)

### Subagents (`/agents/`)
- `triage` — initial dispatch to the right faculty
- `verify-spec` — Boris pattern: refuse "done" without proof
- `improve-loop` — nightly Karpathy auto-research worker
- `spec-auditor` — bidirectional spec↔code audit
- `doctor` — 20 health checks

### Slash commands (`/commands/`)
- `/diagnose-faculty <name>`
- `/spec <EC-XX-NNN>` — lookup a spec assertion
- `/mutate-spec` — Plan mode + verify gate
- `/verify-bidirectional` — full spec↔code audit
- `/batch-migration` — parallel worktree workers (adapted from Boris's `/batch`)
- `/adversarial-probe` — 11 malakhim in parallel worktrees + tmux
- `/mistake-to-rule` — Boris pattern (append to `memory/MISTAKES.md`)
- `/insights-weekly` — flywheel summary from past 7 days

## Standard Commands

```bash
make test                # 1388 tests, ~3 seconds (HARD GATE)
make doctor              # 20 health checks
make verify-bidirectional   # spec↔code audit
etzchaim improve         # trigger nightly loop manually
etzchaim probes --adversarial   # run the 11 malakhim
pipx install etzchaim    # canonical install
```

## Behavior Rules (Boris-aligned)

1. **Always start in Plan Mode** (Shift+Tab twice in Claude Code) for any spec mutation.
   _Boris: "Most sessions start in Plan mode. Then auto-accept can one-shot it. A good plan is really important."_ — [thread](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)

2. **Use the `verify-spec` subagent** before marking ANY task complete.
   _Boris: "Give Claude a way to verify its work. 2-3× the quality of the final result."_ — [VentureBeat manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)

3. **Every mistake → `memory/MISTAKES.md`** rule (via `/mistake-to-rule`).
   _Boris: "Every time we see Claude do something incorrectly, we add it to CLAUDE.md."_

4. **For batch / migration work, use `/batch-migration`** — spawns N worktree workers in parallel.
   _Boris's [`/batch` announcement Feb 27, 2026](https://github.com/NousResearch/hermes-agent/issues/380)._

5. **For adversarial validation, use `/adversarial-probe`** — 11 malakhim run in parallel worktrees.
   _Pattern: [worktree subagents](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj) (Feb 20, 2026)._

6. **Never `--dangerously-skip-permissions` outside a sandbox.**
   _Prefer [Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode) (Max/Team/Enterprise) — Sonnet 4.6 classifier + prompt-injection probe._

7. **Verify externally:** the [Chrome extension test pattern](https://www.builder.io/blog/codex-vs-claude-code) for UI-touching changes (the Flask+SSE dashboard at `/health` and `/grafana`).

## Provider Compatibility

This project is **standards-first, Anthropic-optimized.**

| Layer | Standard | Portable? |
|---|---|---|
| Cognitive engine | Python + [LiteLLM](https://github.com/BerriAI/litellm) (100+ providers) | ✓ 100% |
| Skills | [agentskills.io](https://agentskills.io) (35+ tools) | ✓ 100% |
| MCP | [AAIF / Linux Foundation](https://github.com/modelcontextprotocol) | ✓ 100% |
| Agent config | [AGENTS.md (AAIF)](https://agents.md) | ✓ 100% |
| Bonus features | Auto Mode, Routines, Channels, Managed Agents, Dreaming, Outcomes | ⚠ Anthropic-only |

**Switching to GPT-5.5 / Gemini 3 / Ollama**: edit `litellm.config.yaml`, one line.
Full guide in [`docs/PORTABILITY.md`](docs/PORTABILITY.md).

## Reference Documents (in-repo)

- [`memory/ARCHITECTURE.md`](memory/ARCHITECTURE.md) — system invariants & faculty contracts
- [`memory/MISTAKES.md`](memory/MISTAKES.md) — anti-patterns we've encountered (**LIVING DOCUMENT**)
- [`memory/DECISIONS.md`](memory/DECISIONS.md) — Architecture Decision Records
- [`docs/PORTABILITY.md`](docs/PORTABILITY.md) — cross-provider switching guide
- [`docs/CODE_WITH_CLAUDE_2026.md`](docs/CODE_WITH_CLAUDE_2026.md) — Anthropic 2026 features map
- [`docs/REFERENCES.md`](docs/REFERENCES.md) — full external reference index

## Key external references (curated — fetch when relevant)

### Boris Cherny — creator of Claude Code, workflow principles
- [Boris's pinned workflow thread](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm) (Jan 2, 2026 — 8M views, "watershed moment")
- [Tips compendium (curated)](https://howborisusesclaudecode.com/)
- [Worktree announcement](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj) (Feb 20, 2026)
- [VentureBeat manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)

### Anthropic engineering — foundational papers
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Code Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode)
- [Building Effective Agents (Erik Schluntz et al.)](https://resources.anthropic.com/building-effective-ai-agents)

### Anthropic thesis on agents — Barry Zhang & Mahesh Murag
- [Don't Build Agents, Build Skills Instead — talk](https://www.youtube.com/watch?v=CEvIs9y1uog)
- [Barry Zhang bio + key ideas](https://thefocus.ai/reports/aiecode-2025-11/speakers/barry-zhang/bio/)

### Code with Claude SF — May 6, 2026
- [Code with Claude SF 2026 recap (Blake Crosley)](https://blakecrosley.com/blog/code-with-claude-sf-2026-recap)
- [Notes from the conference (Chris Ebert)](https://chrisebert.net/notes-from-code-with-claude-2026/)

### Standards bodies
- [Agent Skills standard](https://agentskills.io)
- [AGENTS.md (Linux Foundation AAIF)](https://agents.md)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Claude Code documentation](https://code.claude.com/docs/)

For the complete reference index see [`docs/REFERENCES.md`](docs/REFERENCES.md).
