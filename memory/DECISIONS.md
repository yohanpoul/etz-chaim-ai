# DECISIONS.md — Architecture Decision Records (ADRs)

> Lightweight ADRs for Etz Chaim AI. Format inspired by
> [adr.github.io](https://adr.github.io) but kept minimal.

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

### Decision

We choose **standards-first with Anthropic-bonus**:

- Cognitive engine routes through LiteLLM (100+ providers) and the
  in-repo `etzchaim/providers/` registry
- Skills follow the [agentskills.io](https://agentskills.io) standard
- Agent instructions live in [AGENTS.md](https://agents.md) (AAIF / Linux
  Foundation), with `CLAUDE.md` as a symlink
- MCP server uses the [open MCP standard](https://modelcontextprotocol.io)

Anthropic-only features (Auto Mode, Channels, Routines, Managed Agents,
Dreaming, Outcomes) are wired in optionally behind feature flags.

### Consequences

- ✓ Contributor on GPT-5.5 / Cursor / Codex / Ollama can use Etz Chaim
  without an Anthropic key
- ✓ Distribution surface expands (skills.sh, mcp.so, agensi.io, npm, PyPI,
  buildwithclaude — five marketplaces)
- ✓ Provider switching is a profile swap in `config.yaml`
- ⚠ Maintaining feature parity between providers requires capability
  checks throughout
- ⚠ The Anthropic-bonus layer must be carefully isolated

### References

- [LiteLLM 100+ providers list](https://docs.litellm.ai/docs/providers)
- [Pydantic AI one-line provider switching](https://ai.pydantic.dev/)

---

## ADR-0002 — AGENTS.md as source unique, CLAUDE.md as symlink

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

In 2026 every coding agent reads a different config file by default:
Claude Code → `CLAUDE.md`, Codex CLI → `AGENTS.md`, Cursor → `.cursor/rules/`,
Windsurf → `.windsurfrules`, Gemini CLI → `GEMINI.md`, GitHub Copilot
→ `.github/copilot-instructions.md`. Maintaining six separate files with
the same content guarantees drift.

### Decision

`AGENTS.md` is the **source unique** for Etz Chaim AI. All other config
files are symlinks (where supported) or references (where not).
`scripts/setup-symlinks.sh` wires this up.

### Consequences

- ✓ Single edit point; zero drift between tools
- ⚠ Windows users may need WSL2 for symlinks
- ⚠ The convention is non-standard; documented explicitly in README

### References

- [AGENTS.md spec](https://agents.md)
- [Augment Code guide to AGENTS.md](https://www.augmentcode.com/guides/how-to-build-agents-md)

---

## ADR-0003 — Boris Cherny's verify-spec subagent pattern

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

Boris Cherny identifies the verification loop as the #1 driver of AI
coding quality. From his [Jan 2 2026 thread](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm):
_"Give Claude a way to verify its work. 2-3× the quality of the final
result."_

### Decision

Every spec mutation requires the `verify-spec` subagent (in
`agents/verify-spec.md`) to return APPROVED before merge. Enforced by:
- `Stop-verify-app.sh` hook in Claude Code
- Pre-commit hook for non-Claude tools
- `etzchaim mutate-spec` CLI refuses to commit without VERIFY OK

### Consequences

- ✓ Quality gate before merge
- ⚠ Adds ~15s to every mutation

---

## ADR-0004 — Skills + 5 subagents (not 13 subagents)

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

Initial plan envisioned 13 subagents (one per faculty). Re-reading
[Barry Zhang & Mahesh Murag's "Don't Build Agents, Build Skills Instead"](https://www.youtube.com/watch?v=CEvIs9y1uog)
clarified the Anthropic 2026 thesis: **one universal agent + library of
skills + the right MCP servers** beats multiple specialized agents.

### Decision

- **13 skills** in `/skills/` (10 facultés + 3 utility)
- **5 subagents** in `/agents/` — only where context isolation is essential:
  `triage`, `verify-spec`, `improve-loop`, `spec-auditor`, `doctor`
- **11 malakhim adversaries** — implemented as parallel `--worktree` + tmux
  sessions via `/adversarial-probe`

### Consequences

- ✓ Lighter session context
- ✓ Aligns with Anthropic's stated direction

---

## ADR-0005 — Claude Code Routines replace local daemon (when available)

**Date**: 2026-05-11
**Status**: ACCEPTED (conditional)

### Context

The Karpathy auto-improve loop currently runs as a local Python daemon
(`daemon.py`, ~2554 lines). Anthropic launched
[Claude Code Routines](https://thenewstack.io/claude-code-can-now-do-your-job-overnight/)
in March 2026: cloud-hosted scheduled prompts.

### Decision

Triple-stack strategy:
1. **Primary**: Claude Code Routine (cloud, no local machine needed) — when
   maintainer has Max+
2. **Fallback**: GitHub Actions workflow on schedule
3. **Local**: Python daemon for fully offline / non-Anthropic setups

### Consequences

- ✓ Maintainer's laptop doesn't need to be on overnight
- ⚠ Adds an Anthropic-only path (mitigated by GHA fallback)

---

## ADR-0006 — DevContainer for one-line install (Codespaces compatible)

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

For an open-source cognitive OS, install experience is distribution.

### Decision

`.devcontainer/` based on [Dev Containers spec](https://containers.dev/).
Works in VS Code, GitHub Codespaces (free 60h/month), JetBrains, Cursor.

### Consequences

- ✓ "Reopen in Container" → operational in <5 minutes
- ⚠ Docker Desktop licensing for corporate users (mitigated by Codespaces)

---

## ADR-0007 — Single `model_registry.py` to eliminate slug drift

**Date**: 2026-05-11
**Status**: ACCEPTED (Sprint 1.A)

### Context

Claude Code's audit of PR #12 (Sprint 0) surfaced **two leak sites**
of hardcoded model strings, violating `.claude/rules/python-dev.md`
("never hardcode model names"):

1. `etzchaim/autopilot/runners/claude_skill.py:29` →
   `model: str = "claude-opus-4-7"` as a default argument
2. `etzchaim/providers/anthropic_sdk.py:27-29` → `MODEL_SLUGS` alias
   table:
   ```python
   "opus":   "claude-opus-4-20250514"  # ← Opus 4 from May 2025
   "sonnet": "claude-sonnet-4-5-20250929"
   "haiku":  "claude-haiku-4-20250801"
   ```

Worse, `MODEL_SLUGS["opus"]` points at `claude-opus-4-20250514` (May 2025,
Opus 4) while `config.yaml` already uses `claude-opus-4-7` (April 2026,
Opus 4.7). **The alias table is a year behind reality** — silent
quality regression on any code path that resolves "opus" through
MODEL_SLUGS rather than config.yaml.

Two naming conventions cohabit in the codebase:
- Dated full slugs (`claude-opus-4-20250514`)
- Alias-style (`claude-opus-4-7`)

### Decision

In Sprint 1, introduce `etzchaim/llm/model_registry.py` as the **single
source of truth** for all model aliases. Every other module that needs
a model identifier imports from there:

```python
from etzchaim.llm.model_registry import resolve_model

# Returns the canonical slug for the active profile
model = resolve_model("opus")  # → "claude-opus-4-7" (from config.yaml)
```

The registry:
- Reads `config.yaml` for canonical slugs
- Maps friendly aliases (`opus`, `sonnet`, `haiku`, `gpt-5`, `gemini-3-pro`)
  to current canonical slugs
- Exposes a single function `resolve_model(alias: str) -> str`
- Raises typed `UnknownModelError` for unrecognized aliases
- Has its own test suite (`tests/test_llm/test_model_registry.py`)

After Sprint 1:
- `anthropic_sdk.py::MODEL_SLUGS` is **deleted**
- `claude_skill.py:29` default becomes `resolve_model("opus")`
- Linter check (Sprint 4) refuses PRs that import model slug strings
  outside `model_registry.py` or `config.yaml`

### Consequences

- ✓ Eliminates silent regression risk (Opus 4 vs Opus 4.7 drift)
- ✓ Aligns the codebase with `.claude/rules/python-dev.md`
- ✓ Single point to upgrade model versions
- ⚠ Migration touches `~8` files; needs careful PR review
- ⚠ Tests that mock specific slugs need re-wiring

### Alternatives considered

- **Status quo (live with drift)**: rejected — silent quality regression
  is a strict failure mode for a cognitive architecture project
- **Use LiteLLM aliases natively**: rejected — LiteLLM aliases require
  a running proxy server; we want library-only resolution too
- **Just rename `MODEL_SLUGS` entries**: rejected — doesn't fix the
  architectural problem, just patches symptoms

### References

- [`.claude/rules/python-dev.md`](.claude/rules/python-dev.md) — "never hardcode model names"
- [Anthropic model migration guide](https://docs.anthropic.com/en/docs/about-claude/models/migrating-to-claude-4)
- [Pydantic AI model overview](https://pydantic.dev/docs/ai/models/overview/)

### Implementation notes (Sprint 1.A)

Landed on branch `sprint-1.a/model-registry`. Module
`etzchaim/llm/model_registry.py` exposes `resolve_model`,
`resolve_model_for_task`, `get_active_profile`, `list_aliases`,
`UnknownModelError`, and the underlying `ModelRegistry` class (lazy
mtime-invalidated singleton). Provider prefix (``anthropic/``, ``openai/``,
``bedrock/`` …) is stripped before returning so SDK callsites keep getting
bare slugs.

Migrated leak sites:
- `etzchaim/providers/anthropic_sdk.py` — `MODEL_SLUGS` and `_resolve_model`
  deleted; SDK now calls `resolve_model()`.
- `etzchaim/providers/__init__.py` — dropped `MODEL_SLUGS` re-export.
- `etzchaim/autopilot/runners/claude_skill.py` — default model is now
  `resolve_model("opus")`.
- `tests/test_providers/test_anthropic_sdk.py` — rewrote
  `test_generate_resolves_short_alias_to_full_slug` to assert against
  `resolve_model("opus")`.

Out of scope for 1.A (deferred to 1.B with inline TODO):
- `etzchaim/initiate.py::_CANONICAL_LLMS` — user-facing identifier registry
  excluded from `make check-model-leaks` until the catalog migrates.
- `etzchaim/providers/litellm_provider.py` docstring examples — same
  treatment.

---

## ADR-0008 — AGENTS.md correctness audits (Boris pattern)

**Date**: 2026-05-11
**Status**: ACCEPTED

### Context

The Sprint 0 AGENTS.md contained at least 3 architectural inaccuracies
that survived multiple internal review passes:

1. Referenced `litellm.config.yaml` (file doesn't exist) — real config
   is `config.yaml` with 6 profiles
2. Did not mention `.claude/rules/` (475 lines of project-scoped rules)
3. Listed 7 invariants but omitted public-surface neutrality
   (CI-gated by `scripts/check_public_surface.sh`)

These were caught only when Claude Code's first audit of the merged PR
discovered them (the rapport included in commit history of Sprint 0.5).

### Decision

Adopt **AGENTS.md correctness audit** as a recurring discipline:

1. **Per-PR check**: any PR that modifies AGENTS.md must include a
   "Verification" section in the description listing the commands run
   to verify each claim against the actual codebase
2. **First-action audit on every fresh Claude Code / Codex CLI session**:
   the first instruction to the agent is to inspect the codebase
   read-only and report deltas vs AGENTS.md before any modification
3. **`/agents-md-audit` slash command** (Sprint 3): packages this
   pattern as a one-shot command — agent runs `rg` + `find` against
   AGENTS.md claims, reports drift, no changes made

### Consequences

- ✓ AGENTS.md drift is detected before propagating to downstream agents
- ✓ Documents the lesson: AGENTS.md is **especially** prone to drift
  because it's prose, not code
- ⚠ One extra step per AGENTS.md PR (acceptable — these PRs are rare)

### References

- The Sprint 0.5 audit rapport (this ADR's origin)
- `memory/MISTAKES.md` entries dated 2026-05-11 for the 3 specific drifts
- Boris Cherny: ["Every mistake becomes a rule"](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)

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
