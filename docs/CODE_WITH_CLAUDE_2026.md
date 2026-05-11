# Code with Claude 2026 — feature mapping for Etz Chaim AI

> This document maps every Anthropic 2026 feature announced at or before
> [Code with Claude SF (May 6, 2026)](https://blakecrosley.com/blog/code-with-claude-sf-2026-recap)
> to its role in Etz Chaim AI. Use this as the reference when deciding
> whether to wire a new Anthropic feature in.
>
> Last sync: May 11, 2026 (3 days after Code with Claude SF keynote)

## The Code with Claude SF 2026 announcements

Held at SVN West, San Francisco, May 6, 2026. Three thousand-ish
attendees in person. Tracks: **Research · Claude Platform · Claude Code**.

### Headline announcements (with Etz Chaim mapping)

| Announcement | Etz Chaim impact | Sprint |
|---|---|---|
| Claude Code 5h rate limits **doubled** for Pro/Max/Team/Enterprise | Maintainer can run longer improve-loops | 1 |
| Peak-hours throttling **removed** for Pro/Max | Nightly daemon runs reliably | 1 |
| Opus API rate limits **considerably raised** | Adversarial probes can run in parallel | 1 |
| 300+ MW SpaceX/Colossus 1 partnership · 220 000+ GPUs | Backend capacity for Routines | (infra) |
| **Dreaming** → research preview | Memory curation for `epistememory` faculty | 8 |
| **Outcomes** → public beta | Rubric grader per faculty | 8 |
| **Multiagent orchestration** → public beta | 11 malakhim as parallel sub-agents | 8 |
| **Webhooks** for Managed Agents | Drift alerts → Telegram | 7 |
| Harvey case study: **6× task completion** with Dreaming | Validation of our memory direction | (proof point) |
| Wisedocs: **−50% review time** with Outcomes | Validation of rubric direction | (proof point) |
| Netflix: hundreds of parallel builds via Multiagent | Pattern for our 11 adversaries | 8 |
| Q1 2026: **80×** annualized revenue growth | Strategic context (don't bet against the stack) | — |
| API volume: **+70×** YoY | Same | — |
| Avg dev uses Claude Code **20 h/week** | Validates the workflow we're standardizing on | — |
| **4% of public GitHub commits** are Claude Code authored | Distribution surface for OSS visibility | — |

## Anthropic feature catalog → Etz Chaim mapping

Updated table, sorted by sprint priority.

### Sprint 1 — Zero-architecture wins

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **Prompt caching** (explicit breakpoints) | Cache the 36 086-line spec corpus → ~90% cost reduction on improve-loop | [docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) |
| **Claude Opus 4.7** (released Apr 16, 2026) | Upgrade from 4.6 on deep facultés (causal, dissensus, insight) | [release notes](https://www.anthropic.com/news/claude-opus-4-7) |
| **Adaptive thinking** | Replace manual `budget_tokens` on facultés | [docs](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting) |
| **Batch API** | Nightly daemon runs as batch (-50% cost on top of caching) | [docs](https://docs.anthropic.com/en/docs/build-with-claude/batch-processing) |
| **Citations API** | Native E1–E6 label mapping | [docs](https://docs.anthropic.com/en/docs/build-with-claude/citations) |
| **Advisor tool** (beta `advisor-tool-2026-03-01`) | Sonnet executor + Opus advisor for the dispatcher in `triage` subagent | [Anthropic news](https://www.anthropic.com/news/) |

### Sprint 2 — Skills (the Barry Zhang / Mahesh Murag thesis)

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **Skills standard (agentskills.io)** | 13 SKILL.md files for 10 facultés + 3 utility | [agentskills.io](https://agentskills.io) |
| **Progressive disclosure** | Metadata up-front, full content on demand (Anthropic's stated pattern) | [Barry Zhang talk](https://www.youtube.com/watch?v=CEvIs9y1uog) |
| **`disable-model-invocation: true`** frontmatter | Use on `etz-spec-lookup` (manual-only skill) | [Skills docs](https://code.claude.com/docs/en/skills) |
| **Skills marketplaces** | Publish to skills.sh, skillsmp.com, agensi.io, buildwithclaude.com, awesome-agent-skills | [skills.sh](https://skills.sh) |
| **Cross-tool skills** | Same skills work on Codex CLI, Cursor, Antigravity (35+ platforms) | [Agent Skills explainer](https://www.agensi.io/learn/agent-skills-open-standard) |

### Sprint 3 — Subagents (Boris pattern)

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **Subagents** (`/agents/*.md`) | 5 subagents: triage, verify-spec, improve-loop, spec-auditor, doctor | [Claude Code docs](https://code.claude.com/docs/en/subagents) |
| **`isolation: worktree`** frontmatter | On `improve-loop` and `verify-spec` (Boris pattern) | [Boris's worktree thread](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj) |
| **`/batch` slash command** | Adapt as `/batch-migration` for spec migrations | [Boris's `/batch` announcement](https://github.com/NousResearch/hermes-agent/issues/380) |
| **`/simplify` slash command** | Adapt for post-mutation cleanup | (built-in Claude Code) |
| **Plan Mode** (Shift+Tab×2) | Mandatory for all spec mutations | [Boris thread](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm) |
| **Verification loop** (verify-spec) | The 2-3× quality boost insight | [VentureBeat manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are) |

### Sprint 4 — Hooks, Sandbox, Auto Mode, DevContainer

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **Hooks (26 lifecycle events in v2.1.116)** | 8 hooks: PreToolUse aggregate-write guard, PostToolUse format, Stop verify-app | [Hooks docs](https://code.claude.com/docs/en/hooks) |
| **Sandbox** (Seatbelt/Landlock) | OS-level isolation for the daemon | [Sandbox docs](https://code.claude.com/docs/en/sandbox) |
| **Auto Mode** (Sonnet 4.6 classifier) | Replace `--dangerously-skip-permissions` for the daemon | [Auto Mode blog](https://www.anthropic.com/engineering/claude-code-auto-mode) |
| **Prompt-injection probe** | Screen Sefaria-sourced content | (part of Auto Mode) |
| **DevContainer** | One-line install via VS Code / Codespaces | [DevContainer docs](https://code.claude.com/docs/en/devcontainer) |
| **Trail of Bits hardened devcontainer** | Reference firewall pattern | [GitHub](https://github.com/trailofbits/claude-code-devcontainer) |
| **`/loop`** & **`/schedule`** | Boris's autonomous workflows | [Boris's tips](https://howborisusesclaudecode.com/) |
| **`--worktree`** flag | Each adversary in its own worktree | [Worktree announcement](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj) |
| **statusline custom** | Show context %, model, branch, cost, active rectifiers | [statusline docs](https://code.claude.com/docs/en/statusline) |
| **`/insights` + `cleanupPeriodDays: 365`** | Longitudinal flywheel | (Shrivu Shankar pattern) |

### Sprint 5 — MCP server (`etzchaim-mcp`)

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **MCP standard** (AAIF) | Build `etzchaim-mcp` (15 tools) | [MCP spec](https://modelcontextprotocol.io) |
| **Tool Search** (auto-defer, 95% context reduction) | All `etzchaim-mcp` tools default-deferred | [Tool Search docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-search) |
| **`alwaysLoad: true`** annotation | On `diagnose_faculty` (critical, no defer) | [docs](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview) |
| **`anthropic/maxResultSizeChars`** annotation | Cap result size to 50 000 chars | (MCP server best practice) |
| **Tool description optimization** | Use the [tool-testing agent pattern](https://www.anthropic.com/engineering/multi-agent-research-system) (40% latency reduction) | [Anthropic eng](https://www.anthropic.com/engineering/writing-tools-for-agents) |
| **Parameter naming** (Ken Aizawa rule) | `spec_id` not `id`, `faculty_name` not `name` | [Writing tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents) |

### Sprint 6 — Plugin distribution

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **Claude Code Plugins** (`.claude-plugin/plugin.json`) | Bundle skills + agents + commands + hooks + MCP config | [Plugins docs](https://code.claude.com/docs/en/plugins) |
| **buildwithclaude.com** marketplace | Primary distribution channel | [buildwithclaude](https://buildwithclaude.com) |
| **skills.sh** (Vercel) | Cross-tool skills installation: `npx skills add yohanpoul/etz-chaim-ai` | [skills.sh](https://skills.sh) |
| **mcp.so** | MCP server registry | [mcp.so](https://mcp.so) |
| **Glama** | MCP server discovery | [Glama](https://glama.ai/mcp) |
| **agensi.io** | Security-scanned skills | [agensi.io](https://agensi.io) |
| **awesome-agent-skills** | Community list | [GitHub](https://github.com/heilcheng/awesome-agent-skills) |

### Sprint 7 — Cloud asynchrone (Routines + Channels + Webhooks)

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **Claude Code Routines** | REPLACES local daemon for nightly improve-loop | [TheNewStack launch](https://thenewstack.io/claude-code-can-now-do-your-job-overnight/) |
| **Channels** (research preview) | Telegram alerts for drift / mutation approval | [Channels docs](https://code.claude.com/docs/en/channels) |
| **`--channels permission relay`** | Approve tool calls from phone | (Claude Code v2.1.x) |
| **Webhooks** for Managed Agents (whsec_) | At-least-once dedup via Hookdeck | [Hookdeck guide](https://hookdeck.com/blog/anthropic-managed-agent-webhooks) |
| **Claude Code Action** GHA | PR-from-anywhere via `@claude` mention | [claude-code-action](https://github.com/anthropics/claude-code-action) |
| **OpenTelemetry expansion in Cowork** | Trace nightly routines into Grafana | (Code with Claude 2026 announcement) |

### Sprint 8 — Managed Agents (the long bet)

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **Managed Agents** (`anthropic.beta.agents.create`) | Persistent agent for Etz Chaim | [Managed Agents docs](https://docs.anthropic.com/en/docs/build-with-claude/managed-agents) |
| **Memory tool** + **stores** | Replace local `epistememory` storage | [Memory docs](https://docs.anthropic.com/en/docs/build-with-claude/memory) |
| **Dreaming** (research preview) | Nightly memory curation, review-human-required | [Dreaming announcement](https://releasebot.io/updates/anthropic) |
| **Outcomes** (public beta) | Rubric grader per faculty in separate context | [Outcomes blog](https://www.anthropic.com/news/) |
| **Multiagent orchestration** (public beta, `managed-agents-2026-04-01`) | The 11 malakhim as parallel specialist sub-agents | [Multiagent docs](https://docs.anthropic.com/en/docs/build-with-claude/multiagent) |
| **Persistent events** | Trace every step in Claude Console | (Managed Agents feature) |
| **Vault credentials background refresh** | mcp_oauth secret rotation | (May 2026 release notes) |

### Sprint 9 — Evangelism & v1.0

| Feature | Etz Chaim use | Reference |
|---|---|---|
| **Claude Certified Architect** | Certification track | [Claude Certified](https://claude.com/certified) |
| **Code with Claude London** (May 19) / **Tokyo** (June 10) | Talk submissions | [Code with Claude](https://claude.com/code-with-claude) |
| **Claude for Open Source Program** | 6 months Max free for OSS maintainers (deadline June 30, 2026) | [Apply](https://claude.com/contact-sales/claude-for-oss) |

## Features we explicitly DON'T use (and why)

| Feature | Why we skip |
|---|---|
| **Cowork plugins** | Cowork is for knowledge workers, not OSS infrastructure |
| **Claude in Excel/PowerPoint/Word/Outlook** | Not relevant to Etz Chaim's core use case |
| **Finance agent templates** | Domain-specific to financial services |
| **Computer Use (full)** | Overkill for our needs; the Chrome extension on the Flask dashboard is sufficient |
| **Claude Security** | We'll use Semgrep + dependency scanning on `etzchaim-mcp`, but not the full Claude Security product |

## Reference index

### Boris Cherny (creator of Claude Code) — workflow
- [Pinned thread on his daily workflow](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)
- [Tips compendium (curated)](https://howborisusesclaudecode.com/)
- [VentureBeat manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
- [Product with Attitude breakdown](https://karozieminski.substack.com/p/boris-cherny-claude-code-workflow)
- [Mindwiredai 7 secrets](https://mindwiredai.com/2026/04/14/claude-code-creator-workflow-boris-cherny/)
- [Worktree announcement (Feb 20, 2026)](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj)
- [`/batch` announcement (Feb 27, 2026)](https://github.com/NousResearch/hermes-agent/issues/380)

### Anthropic engineering — foundational papers
- [Effective context engineering for AI agents (Sep 2025)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Writing tools for agents (Ken Aizawa)](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Code Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode)
- [Building Effective Agents (Erik Schluntz)](https://resources.anthropic.com/building-effective-ai-agents)

### Anthropic thesis — Barry Zhang & Mahesh Murag
- [Don't Build Agents, Build Skills Instead — YouTube](https://www.youtube.com/watch?v=CEvIs9y1uog)
- [Talk summary (Class Central)](https://www.classcentral.com/course/youtube-don-t-build-agents-build-skills-instead-barry-zhang-mahesh-murag-anthropic-510545)
- [Fresh HQ analysis](https://www.brgr.one/blog/stop-building-agents-build-skills)
- [Barry Zhang bio](https://thefocus.ai/reports/aiecode-2025-11/speakers/barry-zhang/bio/)

### Code with Claude SF 2026
- [Official event page](https://claude.com/code-with-claude/san-francisco)
- [Crosley recap](https://blakecrosley.com/blog/code-with-claude-sf-2026-recap)
- [Ebert notes](https://chrisebert.net/notes-from-code-with-claude-2026/)
- [Context Studios field guide](https://www.contextstudios.ai/blog/code-with-claude-the-may-6-readiness-field-guide)
- [Pasquale Pillitteri preview](https://pasqualepillitteri.it/en/news/1727/code-with-claude-2026-anthropic-developer-conference)
- [GadgetBond preview](https://gadgetbond.com/code-with-claude-2026-anthropic-developer-conference/)

### Standards
- [Agent Skills (agentskills.io)](https://agentskills.io)
- [AGENTS.md (Linux Foundation AAIF)](https://agents.md)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Dev Containers spec](https://containers.dev/)
- [Claude Code docs](https://code.claude.com/docs/)
- [Anthropic API docs](https://docs.anthropic.com/)
