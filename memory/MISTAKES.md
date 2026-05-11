# MISTAKES.md — Anti-patterns we've encountered

> **LIVING DOCUMENT.** Every time we see Claude (or Codex, Cursor, Gemini, etc.)
> do something incorrectly on Etz Chaim AI, we add it here so future sessions
> avoid the same mistake.
>
> This is the Boris Cherny pattern from his
> [Jan 2 2026 thread](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm):
> _"Every time we see Claude do something incorrectly we add it to the
> CLAUDE.md, so Claude knows not to do it next time."_
>
> Update workflow: when you spot a mistake in a PR or session, run
> `/mistake-to-rule "the mistake"` to append a structured entry. Or edit
> this file directly and commit.

## How to add an entry

Each entry follows this template:

```markdown
### [YYYY-MM-DD] Short title of the mistake

**What happened**: One sentence describing what the agent did wrong.

**Why it's wrong**: The invariant or principle violated.

**The rule**: A clear, imperative instruction agents should follow.

**Detection**: How we noticed (test failure / PR review / production issue).

**Spec refs (optional)**: EC-XX-NNN if it relates to a specific spec.
```

---

## Anti-patterns (chronological)

### [2026-05-11] Direct write to aggregate score

**What happened**: An agent wrote `causalengine.aggregate_score = 0.85`
directly, bypassing channel infrastructure.

**Why it's wrong**: Invariant 1 — aggregate scores must carry provenance
(spec_ref, e_label, reason). Direct writes lose the audit trail and break
the bidirectional spec↔code audit.

**The rule**: Never assign to `*.aggregate_score` directly. Always use
`<faculty>.channel("<channel_name>").write(...)`. The
`PreToolUse-aggregate-write.sh` hook will refuse these writes.

**Detection**: `make check-aggregates` static check fails.

---

### [2026-05-11] Citing a spec without E-label

**What happened**: An agent added `spec_ref="EC-K7-042"` to a function
comment but did not include `e_label="E3"` or a justification.

**Why it's wrong**: Invariant 4 — every assertion carries an E-label
that signals epistemic confidence. Without it, the spec corpus drifts
toward false-confidence.

**The rule**: When citing a spec_ref, ALWAYS include `e_label` (E1–E6)
and a one-line justification. Format:
```python
# spec_ref: EC-K7-042 (E3 — derivation from Pearl §3.3.2 backdoor criterion)
```

**Detection**: `make verify-bidirectional` warns on missing E-labels.

---

### [2026-05-11] Marking a task "done" without running verify-spec

**What happened**: An agent declared a spec mutation complete after
running only `make test`, without invoking the `verify-spec` subagent.

**Why it's wrong**: Boris pattern. `make test` alone misses:
- Bidirectional spec↔code drift
- E-label decay
- Adversarial-probe regressions
- Rubric / outcome evaluation

**The rule**: For spec mutations, "done" requires `verify-spec` subagent
returning APPROVED. No exceptions. See `agents/verify-spec.md`.

**Detection**: The `Stop-verify-app.sh` hook blocks task completion.

---

### [2026-05-11] Loading the full spec corpus into context

**What happened**: An agent ran `cat etzchaim/specs/*.md` to "understand
all 1696 specs."

**Why it's wrong**: 1696 specs ≈ 36,000 lines ≈ ~150k tokens. Burns
context budget, triggers compaction, degrades quality on the actual task.
This is the "context rot" Anthropic warns about in
[Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

**The rule**: Use the `etz-spec-lookup` skill or the `etzchaim-mcp`
`lookup_spec_item` tool to fetch ONLY the specs needed for the current
task. Just-in-time, not just-in-case.

**Detection**: PR review or token usage spike in `/cost`.

---

### [2026-05-11] Direct `--dangerously-skip-permissions` outside sandbox

**What happened**: A contributor ran `claude --dangerously-skip-permissions`
on a host machine to "speed up the nightly loop."

**Why it's wrong**: That flag disables all approval prompts on the host.
A model misstep (or prompt injection from external content) could `rm -rf`,
exfiltrate `.env`, or push to main.

**The rule**: Use one of:
1. `Auto Mode` (Max/Team/Enterprise/API plan)
2. The devcontainer with firewall (`.devcontainer/`)
3. The Trail of Bits [sandboxed devcontainer](https://github.com/trailofbits/claude-code-devcontainer)

Never use the raw flag on a host with credentials present.

**Detection**: PR review, security scan.

---

### [2026-05-11] Editing CLAUDE.md and AGENTS.md separately

**What happened**: An agent updated CLAUDE.md to add a rule but didn't
update AGENTS.md.

**Why it's wrong**: They should be the **same file via symlink**. Editing
them separately guarantees drift, defeats the standards-first design.

**The rule**: Edit `AGENTS.md` only. `CLAUDE.md`, `.codex/AGENTS.md`,
`.cursor/rules/etz-base.mdc` symlink or reference it.

If the symlinks were never set up, run `./scripts/setup-symlinks.sh`.

**Detection**: PR diff shows changes to both files independently.

---

### [2026-05-11] Hardcoding a provider model string

**What happened**: A faculty module hardcoded
`anthropic.messages.create(model="claude-opus-4-7", ...)`.

**Why it's wrong**: Invariant 7 — provider-agnostic core. Hardcoding a
provider couples Etz Chaim to Anthropic. Also violates `.claude/rules/python-dev.md`
("never hardcode model names").

**The rule**: All LLM calls go through `etzchaim/providers/registry.py`
which dispatches via the active profile in `config.yaml`. After Sprint 1,
model aliases resolve through `etzchaim/llm/model_registry.py` — single
source of truth.

**Detection**: `rg "claude-opus|claude-sonnet|claude-haiku|gpt-5|gemini-" etzchaim/`
finds direct slug use.

---

### [2026-05-11] AGENTS.md mentioned `litellm.config.yaml` — wrong filename

**What happened**: The Sprint 0 AGENTS.md claimed *"edit `litellm.config.yaml`,
one line"* to switch providers. That file does not exist in the repo.
The actual provider config is `config.yaml` at the repo root, with 6 profile
blocks (`sefira_full`, `gpt5_full`, `gemini_full`, `bedrock`, `claude_max`,
`benchmark_opus`).

**Why it's wrong**: AGENTS.md is the single source of truth for agent
instructions. When it describes architecture that doesn't match the
codebase, every downstream agent (Claude Code, Codex CLI, Cursor) operates
on false context. Documentation drift in the source unique = cascading
errors.

**The rule**: AGENTS.md, `docs/PORTABILITY.md`, and any architectural doc
must reference **real filenames** verified against `ls` output. When
proposing structural changes, run the audit first (Claude Code: "without
changing anything, inspect and report"). Documentation lies more often than
code does.

**Detection**: Claude Code audit on PR #12 (Sprint 0) discovered the drift
between AGENTS.md claims and `find . -name "litellm*"` reality.

**Spec refs**: ADR-0008 (added in Sprint 0.5 fix).

---

### [2026-05-11] AGENTS.md silent on `.claude/rules/` — discoverability gap

**What happened**: The Sprint 0 AGENTS.md did not mention the
`.claude/rules/` directory (6 files, 475 lines of engineering discipline:
`session-discipline.md`, `python-dev.md`, `public-surface-neutrality.md`,
`kabbalistic-rigor.md`, `hitlabshut.md`, `reshimu_persistence.md`).

**Why it's wrong**: New contributors or agents arriving at the repo via
AGENTS.md never learn that these rules exist and auto-apply. Worst case:
agents violate `python-dev.md` ("never hardcode model names") because
nothing in AGENTS.md says they shouldn't.

**The rule**: AGENTS.md must index every project-scoped rule layer Claude
Code auto-loads. The "Layered project rules" section (added in Sprint 0.5)
makes `.claude/rules/` first-class in the AGENTS.md contract.

When adding a new rules file in `.claude/rules/`, also add a row to the
AGENTS.md "Layered project rules" table.

**Detection**: Claude Code audit on PR #12 surfaced two real violations
(`claude_skill.py:29` default + `anthropic_sdk.py::MODEL_SLUGS`) of
`python-dev.md` that AGENTS.md was silent on.

---

### [2026-05-11] Missing 8th invariant: public-surface neutrality

**What happened**: The Sprint 0 AGENTS.md listed 7 system invariants but
omitted **public-surface neutrality** — the rule that public paths
(`README`, `docs/`, `web/`, CLI surfaces, spec filenames, paper body)
contain zero Hebrew doctrinal terms. This rule is enforced by
`scripts/check_public_surface.sh` and gated in CI.

**Why it's wrong**: An invariant enforced by CI but absent from AGENTS.md
is invisible until it bites. An agent making changes to public docs would
have no way to know the rule exists until the CI build fails.

**The rule**: Invariant 8 ("Public-surface neutrality") is now first-class
in AGENTS.md. Before any PR touching public paths, run
`make check-public-surface` locally. See
`.claude/rules/public-surface-neutrality.md` for the full rename map.

**Detection**: Claude Code audit identified `scripts/check_public_surface.sh`
as a CI gate not referenced by AGENTS.md.

---

### [2026-05-11] Model-string leaks eliminated via model_registry.py

**What happened**: Sprint 0.5 documented (in ADR-0007) that 2 sites
hardcoded model strings: `claude_skill.py:29` default arg and
`anthropic_sdk.py::MODEL_SLUGS`. The MODEL_SLUGS `"opus"` entry pointed to
`claude-opus-4-20250514` (Opus 4, May 2025) while `config.yaml` used
`claude-opus-4-7` (Opus 4.7, April 2026) — a year of silent quality
regression risk for any path resolving "opus" via MODEL_SLUGS.

**Why it's wrong**: Violates `.claude/rules/python-dev.md` ("never hardcode
model names") and invariant #7 (provider-agnostic core). Multiple sources
of truth = drift.

**The rule**: All model alias resolution goes through
`etzchaim/llm/model_registry.py::resolve_model()`. The `MODEL_SLUGS` dict
is deleted. The `make check-model-leaks` target enforces this going
forward; Sprint 4 will promote it to a CI gate.

**Detection**: ADR-0007 spec + `make check-model-leaks` scan.

---

### [2026-05-11] Pre-existing test failures on main as of Sprint 1.A merge — documented for tracking, not fixed in this PR

**What happened**: When running the full suite (`pytest tests/`) on `main`
at commit `5253e23` (the Sprint 1.A merge base), three tests fail
deterministically:

1. `tests/test_olamot_temperature_warning.py::TestTemperatureWarning::test_real_config_briah_warns_under_claude_max`
   — fails both isolated and in full-suite mode; expects the briah olam
   to emit an `IGNORÉE` warning under the `claude_max` profile, but the
   warning never fires (signature drift between the test and the
   `_warn_temperature_unsupported_for_claude_code` helper, likely).
2. `tests/test_sprint8_d1_hitlabshut.py::test_delta_overall_matches_doctrinal_calibration`
   — passes in isolation, fails in full-suite mode. ΔOverall observed
   0.1691 vs expected 0.06 ± 0.015 → 3× the calibrated value. Test
   pollution from an earlier test mutating shared partzufim / boost state.
3. `tests/test_sprint8_d1_hitlabshut.py::test_multiple_mutual_reinforcements_accumulate_correctly`
   — same isolation-vs-full divergence, same likely cause.

**Why it's wrong**: An unstable suite hides regressions. Tests that
depend on import order or global state violate test-isolation discipline
(`tests/__init__.py` should fence cross-test mutation). The temperature
warning test is a flat assertion failure that suggests the helper
contract changed without the test being updated.

**The rule**: Sprint 1.A is a pure refactor with zero touchpoints on
`olamot.py`, partzufim state, or boost calibration. These failures are
**not** introduced by Sprint 1.A. Verified by running the full suite on
both `main` and `sprint-1.a/model-registry`: same 3 failures, same
assertion messages, identical numerics. Filing here so a future sprint
(Sprint 2 candidate) can pick them up.

**Detection**: Sprint 1.A verification step. Branch full-suite: 1305
passed / 3 failed. Main full-suite at `5253e23`: 1293 passed / 3 failed.
Delta = +12 new tests (`tests/test_llm/`), 0 new failures, same 3
pre-existing failures.

**Spec refs**: none yet — Sprint 2 follow-up will open issues per failure.

---

## How to use this file effectively

1. **At PR review time**, if you spot a category of mistake not yet in
   this list, add an entry rather than just commenting on the PR.
2. **At session start**, your Claude Code / Codex / Cursor agent reads
   this file as part of the AGENTS.md hierarchy. The more entries we
   accumulate, the smarter every future session becomes.
3. **Periodically prune**: entries that are now structurally impossible
   (because of a hook or static check) can be archived to
   `MISTAKES_ARCHIVED.md`.
4. **The `/mistake-to-rule` slash command** automates entry creation
   from a session transcript.

## References

- [Boris Cherny — "Every mistake becomes a rule"](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)
- [How Boris Uses Claude Code — tip compendium](https://howborisusesclaudecode.com/)
- [VentureBeat — Cherny's manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
