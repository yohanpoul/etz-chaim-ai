# DECISIONS.md — Architecture Decision Records (ADRs)

> Lightweight ADRs for Etz Chaim AI. Format inspired by
> [adr.github.io](https://adr.github.io) but kept minimal.
>
> Each decision has: ID, date, status, context, decision, consequences,
> alternatives considered. Done in 100–200 lines max per ADR.

---

## ADR-0001 — Standards-first architecture (cross-provider portability)

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

Etz Chaim AI started as an Anthropic-flavored cognitive OS. With the
rapid release cadence of OpenAI (GPT-5.5 April 24, 2026), Google
(Gemini 3 Pro), and the maturity of open-source agents (OpenCode 150K
stars), maintainers and contributors increasingly ask: "What if I want
to use GPT-5.5 instead of Claude?" or "Can I run this fully locally on
Ollama?"

Two architectural paths:
1. **Anthropic-primary, hard-coded**: maximum feature richness today, but
   migration to another provider would require weeks of rework.
2. **Standards-first**: portable core, Anthropic features as bonuses.

### Decision

We choose **standards-first with Anthropic-bonus**:

- Cognitive engine routes through [LiteLLM](https://github.com/BerriAI/litellm)
  (100+ providers, one-line switching)
- Skills follow the [agentskills.io](https://agentskills.io) standard
  (35+ tools, cross-vendor)
- Agent instructions live in [AGENTS.md](https://agents.md) (AAIF / Linux
  Foundation), with `CLAUDE.md` as a symlink
- MCP server uses the [open MCP standard](https://modelcontextprotocol.io)
- DevContainer uses the open [Dev Containers spec](https://containers.dev/)
  (works in VS Code, Codespaces, JetBrains)

Anthropic-only features (Auto Mode, Channels, Routines, Managed Agents,
Dreaming, Outcomes) are wired in optionally behind feature flags. Their
presence improves the experience but is not required.

### Consequences

- ✓ A contributor on GPT-5.5 / Cursor / Codex / Ollama can use Etz Chaim
  without an Anthropic key
- ✓ Distribution surface expands (skills.sh, mcp.so, agensi.io, npm, PyPI,
  buildwithclaude — five marketplaces)
- ✓ Provider switching is one line in `litellm.config.yaml`
- ⚠ Maintaining feature parity between providers requires capability
  checks throughout (extended thinking, prompt caching, citations differ)
- ⚠ The Anthropic-bonus layer must be carefully isolated so its absence
  is graceful

### Alternatives considered

- **Anthropic-primary hard-coded**: rejected — too risky given Etz Chaim's
  positioning as open-source infrastructure
- **OpenAI-primary**: rejected — Anthropic's developer tooling (Skills,
  MCP, Auto Mode) is currently more mature
- **Custom abstraction layer (no LiteLLM)**: rejected — reinventing what
  LiteLLM already does well

### References

- [LiteLLM 100+ providers list](https://docs.litellm.ai/docs/providers)
- [Pydantic AI one-line provider switching](https://ai.pydantic.dev/)
- [OpenCode 75+ providers via Models.dev](https://opencode.ai/)

---

## ADR-0002 — AGENTS.md as source unique, CLAUDE.md as symlink

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

In 2026 every coding agent reads a different config file by default:
- Claude Code → `CLAUDE.md`
- Codex CLI → `AGENTS.md` (also `~/.codex/AGENTS.md` global)
- Cursor → `.cursor/rules/*.mdc` (also reads `AGENTS.md` and `CLAUDE.md`)
- Windsurf → `.windsurfrules` (also `AGENTS.md`)
- Gemini CLI → `GEMINI.md`
- GitHub Copilot → `.github/copilot-instructions.md`

Maintaining six separate files with the same content guarantees drift.

### Decision

`AGENTS.md` is the **source unique** for Etz Chaim AI. All other config
files are symlinks (where supported) or references (where not).

- `CLAUDE.md` → symlink to `AGENTS.md` (Claude Code reads symlinks)
- `.codex/AGENTS.md` → symlink to `../AGENTS.md`
- `.cursor/rules/etz-base.mdc` → frontmatter `references: AGENTS.md` + brief
  pointer

The `scripts/setup-symlinks.sh` post-clone script wires this up.

### Consequences

- ✓ Single edit point; zero drift between tools
- ✓ Boris Cherny's CLAUDE.md guidance (≤100 lines, ~2500 tokens) applies
  uniformly
- ⚠ Windows users may need WSL2 for symlinks (or git config
  `core.symlinks=true`)
- ⚠ The convention is non-standard (most repos still maintain separate
  files); we document it explicitly in the README

### References

- [AGENTS.md official spec](https://agents.md)
- [Cursor reads AGENTS.md and CLAUDE.md](https://benjamincrozat.com/agents-md)
- [Augment Code guide to AGENTS.md](https://www.augmentcode.com/guides/how-to-build-agents-md)

---

## ADR-0003 — Boris Cherny's verify-spec subagent pattern

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

Boris Cherny (creator of Claude Code) repeatedly identifies the
**verification loop** as the #1 driver of AI coding quality. From his
[Jan 2 2026 thread](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm):
_"Give Claude a way to verify its work. If Claude has that feedback loop,
it will 2-3x the quality of the final result."_

Etz Chaim's spec mutation workflow is exactly the kind of high-stakes
operation that needs this gate.

### Decision

We adopt the verify-spec subagent pattern. Every spec mutation requires
the `verify-spec` subagent (in `agents/verify-spec.md`) to return
APPROVED before the change can be marked complete. The subagent
deterministically checks:

1. Spec_ref exists in the corpus
2. E-label is valid and justified
3. Bidirectional spec↔code audit clean
4. 1388 / 1388 tests pass
5. 11 / 11 adversarial probes pass
6. No aggregate-write violations
7. Outcome rubric met (Sprint 8 when Outcomes is wired)

This is enforced by:
- `Stop-verify-app.sh` hook in Claude Code
- A pre-commit hook for non-Claude tools
- The `etzchaim mutate-spec` CLI which refuses to commit without VERIFY OK

### Consequences

- ✓ Quality gate before merge; reduces spec corpus drift
- ✓ Aligns with Boris's empirical 2-3x finding
- ⚠ Adds ~15s to every mutation (acceptable for our spec cadence)
- ⚠ The subagent itself must be tested; it can fail to fail

### References

- [Boris Cherny — verification loop = 2-3x quality](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
- [Boris on `verify-app` subagent (post 8 of his thread)](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)

---

## ADR-0004 — Skills + 5 subagents (not 13 subagents)

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

Initial plan envisioned 13 subagents (one per faculty) plus 13 skills.
Re-reading Barry Zhang & Mahesh Murag's
[Don't Build Agents, Build Skills Instead](https://www.youtube.com/watch?v=CEvIs9y1uog)
clarified the Anthropic 2026 thesis: **one universal agent + library of
skills + the right MCP servers** beats multiple specialized agents.

Subagents should only exist where context isolation is essential.

### Decision

- **13 skills** in `/skills/` (10 facultés + 3 utility) — auto-loaded by
  description match
- **5 subagents** in `/agents/` — only where context isolation is
  essential:
  - `triage` — initial dispatch (avoids polluting main session)
  - `verify-spec` — verification gate (must not see proposer's reasoning)
  - `improve-loop` — long-running nightly worker (isolated `worktree`)
  - `spec-auditor` — bidirectional audit (heavy file I/O, isolate)
  - `doctor` — 20 health checks (parallelizable, isolate)
- **11 malakhim adversaries** — implemented as either:
  - Parallel `--worktree` + tmux sessions via `/adversarial-probe`, OR
  - Multiagent orchestration sub-agents under Managed Agents (Sprint 8)

### Consequences

- ✓ Lighter session context (most facultés as skills, lazy-loaded)
- ✓ Aligns with Anthropic's stated direction
- ⚠ Less "neat" symmetry (10 skills + 5 subagents + 11 adversaries
  instead of 13×3)

### References

- [Barry Zhang & Mahesh Murag — Don't Build Agents, Build Skills Instead](https://www.youtube.com/watch?v=CEvIs9y1uog)
- [Anthropic — Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Barry Zhang bio + key principles](https://thefocus.ai/reports/aiecode-2025-11/speakers/barry-zhang/bio/)

---

## ADR-0005 — Claude Code Routines replace local daemon (when available)

**Date**: 2026-05-11
**Status**: ACCEPTED (conditional)

### Context

The Karpathy auto-improve loop currently runs as a local Python daemon
(`etzchaim/daemon/improve_loop.py`, 630 lines). This requires the
maintainer's machine to be on at the scheduled time.

Anthropic launched [Claude Code Routines](https://thenewstack.io/claude-code-can-now-do-your-job-overnight/)
in March 2026: cloud-hosted scheduled prompts on Anthropic
infrastructure, triggered by schedule / GitHub webhooks / API.

Pro: 5 routines/day, Max: 15, Team/Enterprise: 25.

### Decision

When the maintainer has a Max+ Anthropic plan (via the Claude for OSS
Program or paid), the nightly improve loop runs as a **Claude Code
Routine** in `.claude/routines/nightly-improve.yml`. The Python daemon
becomes the fallback for non-Anthropic users.

Triple-stack strategy:
1. **Primary**: Claude Code Routine (cloud, no local machine needed)
2. **Fallback**: GitHub Actions workflow on schedule
3. **Local**: Python daemon for fully offline / non-Anthropic setups

### Consequences

- ✓ Maintainer's laptop doesn't need to be on overnight
- ✓ Centralized observability via Anthropic Console + webhooks
- ⚠ Adds an Anthropic-only path (mitigated by GHA fallback)
- ⚠ Webhooks require Hookdeck / equivalent for at-least-once dedup

### References

- [Claude Code Routines launch — TheNewStack](https://thenewstack.io/claude-code-can-now-do-your-job-overnight/)
- [Anthropic Managed Agents webhooks](https://hookdeck.com/blog/anthropic-managed-agent-webhooks)

---

## ADR-0006 — DevContainer for one-line install (Codespaces compatible)

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

For an open-source cognitive OS, the install experience is the
distribution. If cloning + running takes >10 minutes, contribution
velocity drops.

### Decision

Etz Chaim ships with a `.devcontainer/` configuration based on the
official [Dev Containers spec](https://containers.dev/). Works in:
- VS Code with Dev Containers extension
- GitHub Codespaces (free tier 60h/month — perfect for evaluating)
- JetBrains IDEs (Toolbox + Dev Containers)
- Cursor (supports Dev Containers since v0.45)

The devcontainer:
- Installs Python 3.12, Node 22, Postgres+pgvector, Ollama, Claude Code
- Wires the firewall pattern from
  [Trail of Bits sandboxed devcontainer](https://github.com/trailofbits/claude-code-devcontainer)
- Runs `pipx install -e .` and `etzchaim doctor` on first start
- Provisions a TimescaleDB volume for the rectifier time series

### Consequences

- ✓ "Reopen in Container" → operational in <5 minutes
- ✓ Codespaces works zero-install (60h/month free)
- ⚠ Docker Desktop license consideration for corporate users (mitigated
  by Codespaces, Podman, OrbStack alternatives — documented)

### References

- [Anthropic Claude Code devcontainer docs](https://code.claude.com/docs/en/devcontainer)
- [Trail of Bits sandboxed devcontainer](https://github.com/trailofbits/claude-code-devcontainer)
- [centminmod multi-CLI devcontainer (Claude + Codex + Gemini)](https://github.com/centminmod/claude-code-devcontainers)

---

## ADR template (copy this for new decisions)

```markdown
## ADR-NNNN — Short title

**Date**: YYYY-MM-DD
**Status**: PROPOSED | ACCEPTED | DEPRECATED | SUPERSEDED-BY ADR-XXXX

### Context

What's the problem? Why are we deciding this now?

### Decision

The decision itself, in 1-3 sentences. Then the details.

### Consequences

- ✓ Positive consequences
- ⚠ Trade-offs
- ✗ Negative consequences

### Alternatives considered

What did we reject, and why?

### References

Links.
```
