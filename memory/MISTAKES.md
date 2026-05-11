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

### [2026-05-11] Seed entries

#### Direct write to aggregate score

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

#### Citing a spec without E-label

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

#### Marking a task "done" without running verify-spec

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

#### Loading the full spec corpus into context

**What happened**: An agent ran `cat etzchaim/specs/*.md` to "understand
all 1696 specs."

**Why it's wrong**: 1696 specs ≈ 36,000 lines ≈ ~150k tokens. Burns
context budget, triggers compaction, degrades quality on the actual task.
This is the "context rot" Anthropic warns about in
[Effective context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).

**The rule**: Use the `etz-spec-lookup` skill or the `etzchaim-mcp`
`lookup_spec_item` tool to fetch ONLY the specs needed for the current
task. Just-in-time, not just-in-case. CLAUDE.md is the upfront context;
specs are JIT.

**Detection**: PR review or token usage spike in `/cost`.

---

#### Direct `--dangerously-skip-permissions` outside sandbox

**What happened**: A contributor ran `claude --dangerously-skip-permissions`
on a host machine to "speed up the nightly loop."

**Why it's wrong**: That flag disables all approval prompts on the host.
A model misstep (or prompt injection from external content) could `rm -rf`,
exfiltrate `.env`, or push to main. Anthropic's
[Claude Code Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode)
exists precisely to avoid this.

**The rule**: Use one of:
1. `Auto Mode` (Max/Team/Enterprise/API plan)
2. The devcontainer with firewall (`.devcontainer/`)
3. The Trail of Bits [sandboxed devcontainer](https://github.com/trailofbits/claude-code-devcontainer)

Never use the raw flag on a host with credentials present.

**Detection**: PR review, security scan.

---

#### Editing CLAUDE.md and AGENTS.md separately

**What happened**: An agent updated CLAUDE.md to add a rule but didn't
update AGENTS.md.

**Why it's wrong**: They should be the **same file via symlink**. Editing
them separately guarantees drift, defeats the standards-first design.

**The rule**: Edit `AGENTS.md` only. `CLAUDE.md`, `.codex/AGENTS.md`,
`.cursor/rules/etz-base.mdc` symlink or reference it.

If the symlinks were never set up, run `./scripts/setup-symlinks.sh`.

**Detection**: PR diff shows changes to both files independently.

---

#### Hardcoding a provider model string

**What happened**: A faculty module hardcoded
`anthropic.messages.create(model="claude-opus-4-7", ...)`.

**Why it's wrong**: Invariant 7 — provider-agnostic core. Hardcoding a
provider couples Etz Chaim to Anthropic. If we want to support GPT-5.5,
Gemini 3, Ollama, etc., we must route through LiteLLM.

**The rule**: All LLM calls go through `etzchaim.llm.completion(...)`
which dispatches via LiteLLM with the model identifier from
`litellm.config.yaml`. Provider-specific features (extended thinking,
prompt caching, citations) are wrapped in capability checks.

**Detection**: `grep -r "anthropic\." etzchaim/` finds direct SDK use.

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
