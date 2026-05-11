# Claude for Open Source Program — Application Draft for Etz Chaim AI

> **Deadline: June 30, 2026.** Apply at https://claude.com/contact-sales/claude-for-oss
>
> Approved maintainers receive **6 months of Claude Max free**. Etz Chaim
> AI qualifies on every public criterion (active OSS project, Apache 2.0,
> single primary maintainer, technical-infrastructure focus).
>
> Use this draft as a starting point. Fill in personal details and
> submit.

## Application content

### Project name
**Etz Chaim AI**

### GitHub URL
https://github.com/yohanpoul/etz-chaim-ai

### License
Apache 2.0 (OSI-approved, permissive)

### Maintainer
Yohan Poul ([@yohanpoul](https://github.com/yohanpoul))

### One-line description
A cognitive operating system for LLM agents in the SOAR / ACT-R / CLARION
/ LIDA lineage — 10 faculties, 13 rectifiers, 11 adversarial probes,
1696 primary-source specs, nightly auto-improve daemon. Built standards-
first on agentskills.io + MCP + AGENTS.md.

### What does the project do?

Etz Chaim AI gives LLM agents the cognitive primitives they don't have
out of the box: a typed model of their own competence (selfmap), a way
to predict their own errors before they occur (selfmodel), persistent
epistemic memory across sessions (epistememory), causal reasoning under
Pearl's criteria (causalengine), contradiction detection (dissensuengine),
and a nightly auto-improve daemon that mutates the system's own
specification based on observed failure traces (the Karpathy
AutoResearch pattern).

The project sits architecturally in the lineage of classical cognitive
architectures (SOAR, ACT-R, CLARION, LIDA) but is implemented as a set
of composable primitives that plug into modern coding agents (Claude
Code, Codex CLI, Cursor, Windsurf, OpenCode, Antigravity) via the open
**Agent Skills** and **Model Context Protocol** standards.

### Why is this an active OSS project?

- **107k+ lines of Python**, 1388 tests passing in <3s
- **1696 primary-source spec assertions** with E1–E6 confidence labels
- **22 typed routing paths**, 13 rectifiers, 11 adversarial probes
- Apache 2.0 from day one
- Single primary maintainer (Yohan Poul) with public contribution log
- Distributed via `pipx install etzchaim` (PyPI)
- Roadmap to v1.0 publicly tracked; clear sprint structure
- Targeting LangChain / DSPy adapters by Sprint 9

### Why specifically Claude?

Etz Chaim AI is structurally aligned with Anthropic's 2026 stack:

1. **The Karpathy auto-improve daemon** maps directly onto Anthropic's
   [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
   pattern (initializer agent + coding agent + persistent artifacts).
2. **The 10 faculties** are designed for delivery as Anthropic
   [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
   — Etz Chaim is one of the first non-trivial implementations of
   [Barry Zhang & Mahesh Murag's "build skills, not agents"](https://www.youtube.com/watch?v=CEvIs9y1uog)
   thesis at scale.
3. **The 13 rectifiers and 11 malakhim adversaries** map naturally onto
   the [Multiagent Orchestration](https://www.anthropic.com/news/) public
   beta announced at Code with Claude SF (May 6, 2026).
4. **The persistent epistememory faculty** maps onto Anthropic's
   [Memory tool](https://docs.anthropic.com/en/docs/build-with-claude/memory)
   and the new [Dreaming](https://releasebot.io/updates/anthropic)
   research preview — Etz Chaim is publishing patterns for using Dreaming
   in cognitive-architecture work.
5. **The auto-improve loop's quality gate** implements
   [Boris Cherny's "verify-app" pattern](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
   (the 2-3× quality multiplier), specialized as our `verify-spec`
   subagent.
6. **Spec mutation outputs** will be graded by Anthropic
   [Outcomes (public beta)](https://www.anthropic.com/news/) rubrics —
   one rubric per faculty.

In short: Etz Chaim is **the open-source reference implementation** of
how to wire a non-trivial cognitive architecture onto the Anthropic 2026
stack. Its mere existence demonstrates the stack at full depth.

### What would 6 months of Claude Max enable?

Specifically:

1. **Auto Mode** — turn on classifier-gated approvals across the nightly
   auto-improve daemon, removing the operational risk of running on a
   host machine.
2. **Claude Code Routines** (Pro 5/day, Max 15/day) — migrate the nightly
   Karpathy improve-loop from the local Python daemon to a cloud-hosted
   Routine. The maintainer's laptop doesn't need to be on overnight, and
   the 5h rate-limit doubling announced May 6, 2026 makes deep nightly
   reasoning practical.
3. **Channels** (research preview) — Telegram alerts for drift events
   detected by the 13 rectifiers, so the maintainer can intervene on
   spec mutations from anywhere.
4. **Managed Agents + Memory + Dreaming + Outcomes + Multiagent** — the
   full long-running agent infrastructure for migrating from a local
   daemon to a properly persistent, dreamable, rubric-graded, multi-agent
   cognitive OS.
5. **Cowork Dispatch** — assign Etz Chaim work from a phone, work
   finishes on the desktop; particularly useful for the nightly review
   cycle.
6. **Prompt caching** at full Max throughput on the 36 086-line spec
   corpus → ~90% cost reduction on every faculty call.

### Community evidence

- Issues + discussions on GitHub
- Roadmap publicly tracked through Sprint 9 to v1.0
- Plan to submit talks for Code with Claude **London (May 19)** and
  **Tokyo (June 10)** 2026
- Targeting an arXiv paper on the architecture by Q3 2026
- Public commitment to multi-provider portability (see
  [docs/PORTABILITY.md](../docs/PORTABILITY.md)) — Etz Chaim works
  beyond Anthropic, which means broader adoption surface

### What can Anthropic expect in return?

- **A reference implementation** of the 2026 stack at non-trivial depth
  (cognitive architecture vs. a typical CRUD app), publicly documented
- **Pattern publication**: blog posts and (if accepted) Code with Claude
  talks describing how the Skills + MCP + Managed Agents + Dreaming +
  Outcomes + Multiagent layers compose in practice
- **A second-order ecosystem contribution**: the `etzchaim-mcp` server,
  published on mcp.so / Glama / Smithery, becomes one of the more
  thoughtfully-designed MCP servers in the registry; its tool
  descriptions follow Ken Aizawa's
  [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents)
  pattern faithfully
- **Cross-tool standards advocacy**: Etz Chaim's CLAUDE.md → AGENTS.md
  symlink pattern is documented and replicable; we'll promote it
- **Feedback loop**: as we wire each Anthropic feature, we'll send back
  field reports on what works and what's rough, particularly on the
  newer research-preview features (Dreaming, Channels)

### Maintainer commitment

- I commit to releasing v1.0 by Q3 2026
- I commit to submitting a Code with Claude talk (London or Tokyo) on
  the cognitive-architecture-on-Anthropic-stack pattern
- I commit to producing at least 4 public posts during the 6-month
  period documenting how each Anthropic feature plays with Etz Chaim
- I commit to maintaining the project beyond the 6-month window
  regardless of the Claude Max outcome — this is multi-year work for me

### Contact

- GitHub: [@yohanpoul](https://github.com/yohanpoul)
- Email: [fill in personal email]
- Twitter / X: [fill in if applicable]
- LinkedIn: [fill in if applicable]

---

## Tactical notes (not part of the application)

### When to submit

ASAP. The deadline is **June 30, 2026** but approvals are rolling. The
earlier the application lands, the more runway you get from the 6 months.

### What to attach

1. This README link (it now positions the project clearly)
2. The AGENTS.md (shows the architecture is real and standards-first)
3. The roadmap (the 9-sprint plan in `memory/DECISIONS.md` + this README)
4. A short demo video (record a Claude Code session running
   `etzchaim doctor` + a single faculty call + a verify-bidirectional
   audit — 2 minutes max)

### Tone

Boris Cherny's published workflow is well-known inside Anthropic. The
application should signal that you've read it, internalized it, and are
applying it (which this draft does). Don't fawn — just demonstrate
technical depth.

### After submission

- Watch for the rolling review (typically 1-3 weeks)
- If approved, the bonus Anthropic features in
  [`docs/CODE_WITH_CLAUDE_2026.md`](../docs/CODE_WITH_CLAUDE_2026.md)
  Sprints 7-8 become accessible
- If not approved, no impact — Layers 1 and 2 of Etz Chaim work fine
  without Claude Max. See [`docs/PORTABILITY.md`](../docs/PORTABILITY.md).

### References

- [Claude for Open Source Program landing](https://claude.com/contact-sales/claude-for-oss)
- [Code with Claude SF 2026 recap (Crosley)](https://blakecrosley.com/blog/code-with-claude-sf-2026-recap)
- [Code with Claude attendee notes (Ebert)](https://chrisebert.net/notes-from-code-with-claude-2026/)
- [Boris Cherny's verification-loop principle](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)
