# Sprint 0.5 — AGENTS.md correctness hotfix

> **Date**: 2026-05-11
> **Sprint focus**: Fix the inaccuracies Claude Code's audit surfaced after PR #12 merged.
> **Status**: ✅ READY TO APPLY
>
> Sprint 0.5 is a **chirurgical hotfix**, not a feature sprint. It exists
> because Claude Code's first session after Sprint 0 merge audited the
> codebase and discovered AGENTS.md contained 3 architectural inaccuracies
> that would propagate confusion to every future agent session if left
> uncorrected. Boris pattern: **fix the source unique before building on it**.

## What this sprint corrects

### Drift #1 — `litellm.config.yaml` referenced as the provider config

**Reality**: The file does not exist. The real provider config is
**`config.yaml`** at the repo root (24KB) with **6 profiles** (`sefira_full`,
`gpt5_full`, `gemini_full`, `bedrock`, `claude_max`, `benchmark_opus`).

**Files touched**: `AGENTS.md`, `docs/PORTABILITY.md`, `memory/MISTAKES.md`.

### Drift #2 — `.claude/rules/` not indexed by AGENTS.md

**Reality**: 6 files / 475 lines of project-scoped rules exist
(`session-discipline.md`, `python-dev.md`, `public-surface-neutrality.md`,
`kabbalistic-rigor.md`, `hitlabshut.md`, `reshimu_persistence.md`) but
AGENTS.md never mentions them. Claude Code auto-loads them anyway — but
new agents and contributors have no way to know they exist via AGENTS.md.

**Files touched**: `AGENTS.md` (new "Layered project rules" section),
`memory/MISTAKES.md`.

### Drift #3 — Missing 8th invariant: public-surface neutrality

**Reality**: `scripts/check_public_surface.sh` is **gated in CI** and
enforces zero Hebrew doctrinal terms in public paths. AGENTS.md listed
7 invariants and omitted this one entirely.

**Files touched**: `AGENTS.md` (invariant #8 added), `memory/MISTAKES.md`.

### Drift #4 (related) — Model-string drift, 2 leak sites

**Not fixed in Sprint 0.5** (that's Sprint 1's job) but **documented**:

- `etzchaim/autopilot/runners/claude_skill.py:29` default arg
  `model: str = "claude-opus-4-7"`
- `etzchaim/providers/anthropic_sdk.py:27-29` `MODEL_SLUGS` table:
  - `"opus": "claude-opus-4-20250514"` ← **Opus 4 from May 2025**, not Opus 4.7

Both violate `.claude/rules/python-dev.md` ("never hardcode model names").
**Worse, MODEL_SLUGS is a year behind config.yaml's `claude-opus-4-7`.**
Silent quality regression for any code path that resolves "opus" through
MODEL_SLUGS rather than config.yaml.

**Files touched**: `memory/MISTAKES.md`, `memory/DECISIONS.md` (ADR-0007
proposes the fix in Sprint 1: `etzchaim/llm/model_registry.py` as single
source of truth).

## File inventory

### Modified files (4)

| File | What changed |
|---|---|
| `AGENTS.md` | Provider stack now references `config.yaml` + 6 profiles. New "Layered project rules" section indexes `.claude/rules/`. Invariant #8 (public-surface neutrality) added. Reference to `etzchaim/providers/registry.py` for the real backend selection logic. |
| `memory/MISTAKES.md` | 3 new entries (drifts #1, #2, #3) + 1 documenting the model-string leaks. The entries follow the Boris template. |
| `memory/DECISIONS.md` | ADR-0007 (model_registry, PROPOSED for Sprint 1) + ADR-0008 (AGENTS.md correctness audits as recurring discipline, ACCEPTED). |
| `docs/PORTABILITY.md` | Layer-1 section now describes the real `config.yaml` profile-keyed dispatch, not the fictional `litellm.config.yaml`. Scenarios A/B/C/D updated. |

### Unchanged from Sprint 0 (8 files — not in this hotfix)

`CLAUDE.md`, `README.md`, `SPRINT0_MANIFEST.md`, `memory/ARCHITECTURE.md`,
`docs/CODE_WITH_CLAUDE_2026.md`, `docs/REFERENCES.md`,
`scripts/apply-oss-program.md`, `scripts/setup-symlinks.sh`. They were
correct.

## How to deploy

```bash
cd /Users/fffff/Desktop/developper/claude/etz-chaim-ai
git checkout main
git pull origin main

# Create the hotfix branch
git checkout -b sprint-0.5/agents-md-correctness

# Copy the 4 corrected files from this deliverable into place
STAGING=/path/to/sprint-0.5-staging
cp "$STAGING"/AGENTS.md .
cp "$STAGING"/memory/MISTAKES.md memory/
cp "$STAGING"/memory/DECISIONS.md memory/
cp "$STAGING"/docs/PORTABILITY.md docs/

# Sanity check — these are the 4 expected diffs
git status

# Quick verification
grep -c "config.yaml" AGENTS.md      # should show multiple references
grep -c ".claude/rules/" AGENTS.md   # should show > 0
grep -c "Public-surface neutrality" AGENTS.md  # should show > 0 (the new invariant 8)

# Commit
git add AGENTS.md memory/ docs/PORTABILITY.md
git commit -m "Sprint 0.5: AGENTS.md correctness hotfix

Claude Code's first audit after Sprint 0 merge surfaced 3 architectural
inaccuracies in AGENTS.md. This hotfix corrects them before they propagate
to downstream agent sessions.

Drifts corrected:
- AGENTS.md referenced 'litellm.config.yaml' (file doesn't exist).
  Real provider config is 'config.yaml' at repo root with 6 profiles
  (sefira_full, gpt5_full, gemini_full, bedrock, claude_max, benchmark_opus).
- AGENTS.md was silent on .claude/rules/ (6 files, 475 lines of
  project-scoped engineering discipline rules). Now indexed in a new
  'Layered project rules' section.
- 8th invariant 'Public-surface neutrality' was missing (CI-gated by
  scripts/check_public_surface.sh). Now first-class.

Also documented (fix lands in Sprint 1):
- 2 model-string leak sites (claude_skill.py:29 default,
  anthropic_sdk.py::MODEL_SLUGS table). The MODEL_SLUGS entry for 'opus'
  points to claude-opus-4-20250514 (Opus 4 from May 2025) while
  config.yaml uses claude-opus-4-7 (Opus 4.7 from April 2026) — a year
  of silent regression risk.

Files:
- AGENTS.md: provider stack section rewritten, .claude/rules/ indexed,
  invariant #8 added
- memory/MISTAKES.md: 4 new entries (3 drifts + model leak)
- memory/DECISIONS.md: ADR-0007 (model_registry, PROPOSED) + ADR-0008
  (AGENTS.md correctness audits, ACCEPTED)
- docs/PORTABILITY.md: layer-1 section corrected, scenarios updated

References:
- The audit rapport from Claude Code (session of 2026-05-11 post-merge of PR #12)
- Boris Cherny: 'Every mistake becomes a rule' — https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm"

git push -u origin sprint-0.5/agents-md-correctness
```

Then open a PR for review. CI should pass (these are docs-only changes,
no Python touched).

## Verification checklist

Before merging Sprint 0.5:

- [ ] `grep -n "litellm.config.yaml" AGENTS.md` returns nothing (drift #1 cleared)
- [ ] `grep -c "config.yaml" AGENTS.md` ≥ 3 (real config is now properly referenced)
- [ ] `grep -c ".claude/rules/" AGENTS.md` ≥ 6 (one per rule file)
- [ ] `grep "Public-surface neutrality" AGENTS.md` returns a match (invariant 8)
- [ ] `grep "ADR-0007" memory/DECISIONS.md` returns a match
- [ ] `grep "ADR-0008" memory/DECISIONS.md` returns a match
- [ ] `make check-public-surface` passes (we didn't introduce any leaked terms)
- [ ] `mkdocs build --strict` passes (links resolve)

## What's next — Sprint 1 (now properly grounded)

Sprint 1 attacks the **real** wins now that AGENTS.md matches reality:

1. **`etzchaim/llm/model_registry.py`** — single source for model aliases
   (eliminates the 2 leak sites identified above)
2. **Prompt caching** wired into the provider registry (~90% cost
   reduction on the 1696-spec corpus)
3. **Opus 4.7 + Sonnet 4.6 + Haiku 4.5** migration across the 6 profiles
   in `config.yaml`
4. **Adaptive thinking** replacing manual `budget_tokens`
5. **Batch API** for `daemon.py`'s nightly improve loop (additional -50%)
6. **Citations API native** → E1–E6 mapping
7. **Auto Mode** wiring in `.claude/settings.json` (you have Claude Max)
8. Tests for everything above
9. Updated `memory/MISTAKES.md` if anything new gets surfaced
10. `SPRINT1_MANIFEST.md`

## References

- The audit rapport that triggered this hotfix
- Boris Cherny: "Every mistake becomes a rule" — https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm
- `.claude/rules/session-discipline.md` — "depth > breadth, one node 100% before next"
- `.claude/rules/python-dev.md` — "never hardcode model names" (the rule that found drift #4)
