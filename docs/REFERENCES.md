# References — full external index for Etz Chaim AI

> Every link Claude Code / Codex / Cursor / Gemini may need to fetch in
> order to operate effectively on this codebase. Organized by topic.
>
> **Tip for agents**: prefer fetching these references when you encounter
> a workflow / tool / pattern question. If the reference is fresh enough,
> follow it; if it's superseded, the most recent version usually links
> from the cited page.

## I. Boris Cherny — creator of Claude Code

### Primary sources

- [Boris's pinned thread (Jan 2, 2026)](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm) — the 8M-view "watershed moment" workflow disclosure
- [Worktree feature announcement (Feb 20, 2026)](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj) — `--worktree` flag, `isolation: worktree` subagents
- [`/batch` skill announcement (Feb 27, 2026)](https://github.com/NousResearch/hermes-agent/issues/380) — parallel migration orchestration

### Curation & analysis

- [howborisusesclaudecode.com](https://howborisusesclaudecode.com/) — full curated tip compendium
- [VentureBeat manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
- [Get Push To Prod breakdown](https://getpushtoprod.substack.com/p/how-the-creator-of-claude-code-actually)
- [Karo Zieminski substack breakdown](https://karozieminski.substack.com/p/boris-cherny-claude-code-workflow)
- [MindwiredAI 7 secrets](https://mindwiredai.com/2026/04/14/claude-code-creator-workflow-boris-cherny/)

### Key principles (from these sources)

1. ~100 lines / ~2500 tokens for CLAUDE.md
2. 150-200 instruction budget total
3. 5 parallel terminal Claudes + 5-10 browser Claudes
4. Plan Mode (Shift+Tab×2) before all PRs
5. Verification loop = 2-3× quality boost
6. Every mistake becomes a rule
7. Slash commands for every workflow you do >1×/day
8. Worktrees for parallel agents
9. PostToolUse formatting hook (the last 10%)
10. agent-stop hook for deterministic verification

## II. Anthropic engineering — foundational papers

### Architecture & context

- [Effective context engineering for AI agents (Sep 2025)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — attention budget, compaction, structured note-taking, multi-agent
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — initializer + coding agent + persistent artifacts (directly applicable to our daemon)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — multi-agent patterns, evaluator-optimizer
- [Building Effective Agents (Erik Schluntz)](https://resources.anthropic.com/building-effective-ai-agents)
- [Building Effective AI Agents (Brendan Falk's analysis)](https://www.anthropic.com/research/building-effective-agents) — sequential, parallel, evaluator-optimizer patterns

### Tools & evals

- [Writing tools for agents (Ken Aizawa)](https://www.anthropic.com/engineering/writing-tools-for-agents) — the gold standard for MCP tool descriptions
- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — 20-50 tasks to start, Swiss Cheese model
- [Anthropic Cookbook — building_evals.ipynb](https://github.com/anthropics/claude-cookbooks/blob/main/misc/building_evals.ipynb) — concrete eval recipes

### Skills

- [Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — the foundational essay
- [anthropics/skills GitHub](https://github.com/anthropics/skills) — official reference skills
- [Agent Skills standard (cross-tool)](https://agentskills.io)

### Auto Mode & sandboxing

- [Claude Code Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode) — Sonnet 4.6 classifier + prompt-injection probe
- [Beyond Permission Prompts: Making Claude Code More Secure](https://www.anthropic.com/news/beyond-permission-prompts) — sandbox-based security, 84% prompt reduction

## III. Anthropic thesis on agents — Barry Zhang & Mahesh Murag

The "Don't build agents, build skills instead" position.

- [Talk on YouTube (16 min)](https://www.youtube.com/watch?v=CEvIs9y1uog) — the canonical talk
- [Class Central summary](https://www.classcentral.com/course/youtube-don-t-build-agents-build-skills-instead-barry-zhang-mahesh-murag-anthropic-510545)
- [Fresh HQ analysis](https://www.brgr.one/blog/stop-building-agents-build-skills)
- [Bagrounds key takeaways](https://bagrounds.org/videos/dont-build-agents-build-skills-instead-barry-zhang-mahesh-murag-anthropic)
- [Lilys notes (detailed)](https://lilys.ai/en/notes/agent-skills-20251225/build-skills-not-agents)
- [Barry Zhang bio](https://thefocus.ai/reports/aiecode-2025-11/speakers/barry-zhang/bio/) — author of Skills system, key principles distilled
- [Mahesh Murag's Twitter](https://twitter.com/MaheshMurag) — for follow-ups

## IV. Erik Schluntz — head of programming agents

Author of *Building Effective Agents* (Anthropic 2024-2025).

- [Vibe Coding masterclass (36kr translation)](https://eu.36kr.com/en/p/3774648797659657)
- [DeepInsightAI summary](https://deepinsightai.io/how-to-properly-do-vibe-coding/)
- [Latent Space podcast — SWE-bench SOTA & Computer Use](https://www.latent.space/p/claude-sonnet)

### Key principles

- 15-20 min upfront with Claude exploring the codebase before writing any code
- Then one consolidated prompt
- Treat yourself as the PM of Claude
- 22 000-line PR merged in production RL codebase via this pattern
- Plan mode as the speccing tool

## V. Code with Claude SF — May 6, 2026

The Anthropic developer conference.

- [Official event page (SF)](https://claude.com/code-with-claude/san-francisco)
- [Conference index page](https://claude.com/code-with-claude) — also lists London May 19 and Tokyo June 10
- [Blake Crosley recap (deep dive)](https://blakecrosley.com/blog/code-with-claude-sf-2026-recap)
- [Chris Ebert notes (in-person attendee)](https://chrisebert.net/notes-from-code-with-claude-2026/)
- [Context Studios field guide](https://www.contextstudios.ai/blog/code-with-claude-the-may-6-readiness-field-guide)
- [Generation Digital preview](https://www.gend.co/blog/code-with-claude-live-demos-san-francisco-london-tokyo)
- [Pasquale Pillitteri preview](https://pasqualepillitteri.it/en/news/1727/code-with-claude-2026-anthropic-developer-conference)
- [GadgetBond preview](https://gadgetbond.com/code-with-claude-2026-anthropic-developer-conference/)
- [Releasebot updates — Anthropic May 2026](https://releasebot.io/updates/anthropic)

## VI. Claude Code documentation

- [Claude Code docs](https://code.claude.com/docs/) — root
- [Permissions](https://code.claude.com/docs/en/permissions)
- [Sandbox](https://code.claude.com/docs/en/sandbox)
- [Auto Mode](https://code.claude.com/docs/en/auto-mode)
- [Hooks](https://code.claude.com/docs/en/hooks)
- [Subagents](https://code.claude.com/docs/en/subagents)
- [Skills](https://code.claude.com/docs/en/skills)
- [Plugins](https://code.claude.com/docs/en/plugins)
- [MCP](https://code.claude.com/docs/en/mcp)
- [Channels](https://code.claude.com/docs/en/channels)
- [Routines](https://code.claude.com/docs/en/routines)
- [Devcontainer](https://code.claude.com/docs/en/devcontainer)
- [Statusline](https://code.claude.com/docs/en/statusline)
- [Output styles](https://code.claude.com/docs/en/output-styles)
- [GitHub Actions integration](https://code.claude.com/docs/en/github-actions)
- [Changelog](https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md)

## VII. Anthropic API documentation

- [Anthropic API docs](https://docs.anthropic.com/) — root
- [Prompt engineering guide](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
- [Tool use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use/overview)
- [Citations](https://docs.anthropic.com/en/docs/build-with-claude/citations)
- [Prompt caching](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
- [Batch processing](https://docs.anthropic.com/en/docs/build-with-claude/batch-processing)
- [Extended/Adaptive thinking](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting)
- [Models overview](https://docs.anthropic.com/en/docs/about-claude/models/overview)
- [Migration guide](https://docs.anthropic.com/en/docs/about-claude/models/migrating-to-claude-4)
- [Managed Agents (beta)](https://docs.anthropic.com/en/docs/build-with-claude/managed-agents)
- [Memory tool](https://docs.anthropic.com/en/docs/build-with-claude/memory)
- [Multiagent (beta)](https://docs.anthropic.com/en/docs/build-with-claude/multiagent)

## VIII. Standards & cross-tool

- [agentskills.io](https://agentskills.io) — Agent Skills standard
- [agents.md](https://agents.md) — AGENTS.md standard (Linux Foundation AAIF)
- [modelcontextprotocol.io](https://modelcontextprotocol.io) — MCP spec
- [Linux Foundation AAIF](https://www.linuxfoundation.org/projects/agentic-ai-foundation) — governance
- [containers.dev](https://containers.dev/) — Dev Containers spec
- [opentelemetry.io](https://opentelemetry.io/) — OpenTelemetry
- [json-schema.org](https://json-schema.org/) — JSON Schema

## IX. Distribution & marketplaces

- [skills.sh](https://skills.sh) — Vercel package manager for skills
- [skillsmp.com](https://skillsmp.com) — community skills marketplace
- [agensi.io](https://agensi.io) — security-scanned skills
- [mcp.so](https://mcp.so) — MCP server registry
- [Glama](https://glama.ai/mcp) — MCP discovery
- [Smithery](https://smithery.ai/) — MCP server marketplace
- [buildwithclaude.com](https://buildwithclaude.com) — Claude Code plugin marketplace
- [awesome-agent-skills](https://github.com/heilcheng/awesome-agent-skills) — community-curated list
- [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) — Claude Code ecosystem
- [awesome-codex-cli](https://github.com/RoggeOhta/awesome-codex-cli) — Codex CLI ecosystem

## X. Cross-provider tooling

- [LiteLLM (BerriAI)](https://github.com/BerriAI/litellm) — 100+ providers
- [LiteLLM docs](https://docs.litellm.ai/)
- [Pydantic AI](https://ai.pydantic.dev/) — typed multi-provider agent framework
- [Pydantic AI Gateway](https://ai.pydantic.dev/gateway/) — zero-translation routing
- [OpenCode](https://opencode.ai/) — 150K stars MIT, 75+ providers via Models.dev
- [Models.dev](https://models.dev/) — provider registry
- [Bifrost (Maxim AI)](https://github.com/maxim-ai/bifrost) — Go-based gateway, 11μs overhead

## XI. DevContainer references

- [Anthropic devcontainer feature](https://code.claude.com/docs/en/devcontainer)
- [Trail of Bits sandboxed devcontainer](https://github.com/trailofbits/claude-code-devcontainer)
- [StefanMaron multi-config](https://github.com/StefanMaron/claudeCodeAlDevContainer)
- [centminmod multi-CLI (Claude + Codex + Gemini)](https://github.com/centminmod/claude-code-devcontainers)
- [Morph Windows install guide](https://www.morphllm.com/claude-code-windows)

## XII. Comparative tooling analysis

For understanding the Claude Code vs Codex CLI vs Cursor vs OpenCode landscape:

- [Codex vs Claude Code (Blake Crosley)](https://blakecrosley.com/blog/codex-vs-claude-code-2026)
- [Codex vs Claude Code (Builder.io)](https://www.builder.io/blog/codex-vs-claude-code)
- [Codex vs Claude Code (Developers Digest)](https://www.developersdigest.tech/blog/codex-vs-claude-code-april-2026)
- [Codex vs Claude Code (Codersera)](https://codersera.com/blog/claude-code-vs-openai-codex-2026/)
- [Claude Code vs Codex CLI (NxCode)](https://www.nxcode.io/resources/news/claude-code-vs-codex-cli-terminal-coding-comparison-2026)
- [OpenCode vs Codex vs Claude (Nimbalyst)](https://nimbalyst.com/blog/claude-code-vs-codex-vs-opencode-definitive-comparison/)
- [MindStudio analysis](https://www.mindstudio.ai/blog/claude-code-vs-codex)
- [VILA-Lab — Dive into Claude Code (paper)](https://github.com/VILA-Lab/Dive-into-Claude-Code) — comprehensive academic analysis

## XIII. Patterns & community

- [Self-healing agent loops (MindStudio)](https://www.mindstudio.ai/blog/self-healing-agent-loops) — directly applicable to our Karpathy daemon
- [Adversarial PR review (MindStudio)](https://www.mindstudio.ai/blog/adversarial-pr-review-claude-codex) — Claude proposes, Codex reviews
- [Git worktrees for parallel AI (Botmonster)](https://botmonster.com/posts/parallel-ai-development-claude-code-sessions-git-worktrees/)
- [Mastering Git worktrees with Claude Code (Tuna)](https://medium.com/@dtunai/mastering-git-worktrees-with-claude-code-for-parallel-development-workflow-41dc91e645fe)
- [Parallel vibe coding (Dan Does Code)](https://www.dandoescode.com/blog/parallel-vibe-coding-with-git-worktrees)
- [Compound Engineering plugin](https://github.com/EveryInc/compound-engineering-plugin)
- [Ralph Wiggum loop pattern](https://github.com/vcz-Gray/loophaus)
- [BigBrain MCP (talk to Codex/Gemini from Claude)](https://github.com/Leonard013/BigBrain)

## XIV. Karpathy / autoresearch

- [Andrej Karpathy's Twitter](https://x.com/karpathy)
- [LLM Twitter — agent loops & autoresearch](https://x.com/karpathy/status/1759996651352035724)

## XV. Cognitive architecture (Etz Chaim lineage)

- [SOAR](https://soar.eecs.umich.edu/)
- [ACT-R](http://act-r.psy.cmu.edu/)
- [CLARION (Sun)](https://clarioncognitivearchitecture.com/)
- [LIDA (Franklin et al.)](https://ccrg.cs.memphis.edu/lida.html)
- [Pearl — Causality (2009)](https://bayes.cs.ucla.edu/BOOK-2K/)

## XVI. Etz Chaim AI itself

- [GitHub repo](https://github.com/yohanpoul/etz-chaim-ai)
- Installation: see [`README.md`](../README.md)
- Architecture: see [`memory/ARCHITECTURE.md`](../memory/ARCHITECTURE.md)
- Decisions: see [`memory/DECISIONS.md`](../memory/DECISIONS.md)
- Anti-patterns: see [`memory/MISTAKES.md`](../memory/MISTAKES.md)
- Portability: see [`docs/PORTABILITY.md`](PORTABILITY.md)
- 2026 features map: see [`docs/CODE_WITH_CLAUDE_2026.md`](CODE_WITH_CLAUDE_2026.md)
