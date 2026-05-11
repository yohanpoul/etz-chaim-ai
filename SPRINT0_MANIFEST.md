# Sprint 0 — Deliverables Manifest

> **Date**: 2026-05-11
> **Sprint focus**: Standards-first foundation + Claude for OSS Program funding
> **Status**: ✅ COMPLETE
>
> This manifest summarises every file produced in Sprint 0 of the Etz Chaim
> AI × Anthropic 2026 Stack integration. Use it as the index for what to
> commit and where each file goes in the repo.

## What Sprint 0 delivered

Sprint 0 lays the **architectural and documentation foundation** so every
subsequent sprint has a clean target. Specifically:

1. A **single source of truth** for agent instructions (`AGENTS.md`)
   that all coding agents (Claude Code, Codex CLI, Cursor, Windsurf,
   Gemini CLI, GitHub Copilot, Antigravity) read via symlinks
2. A **living anti-pattern catalog** (`memory/MISTAKES.md`) following
   Boris Cherny's "every mistake becomes a rule" pattern
3. A **decision record system** (`memory/DECISIONS.md`) with 6 starter
   ADRs documenting the standards-first choice and Boris-aligned
   patterns
4. An **architecture reference** (`memory/ARCHITECTURE.md`) capturing
   the 7 invariants, 10 faculties, 13 rectifiers, 11 malakhim, and
   Karpathy daemon design
5. A **portability guide** (`docs/PORTABILITY.md`) answering "can I
   switch to GPT-5.5?" with concrete scenarios
6. A **2026 feature map** (`docs/CODE_WITH_CLAUDE_2026.md`) showing
   exactly which Anthropic feature maps to which sprint and component
7. A **full reference index** (`docs/REFERENCES.md`) in 16 sections so
   any agent reading the repo can fetch primary sources
8. A **multi-tier README** with Bronze / Silver / Gold install paths
9. A **Claude for OSS application draft** (`scripts/apply-oss-program.md`)
   ready to submit before June 30, 2026
10. A **symlink setup script** (`scripts/setup-symlinks.sh`) that
    wires CLAUDE.md, .codex/AGENTS.md, .cursor/rules/etz-base.mdc,
    .windsurfrules, GEMINI.md, and .github/copilot-instructions.md all
    to the single AGENTS.md source

## File inventory

### Root-level files

| File | Purpose | Size | Repo location |
|---|---|---|---|
| `AGENTS.md` | **Source unique** — agent instructions, cross-tool | ~9.5KB | repo root |
| `CLAUDE.md` | Notice → will be symlinked to AGENTS.md | ~1KB | repo root |
| `README.md` | Multi-tier install, positioning, roadmap | ~12.5KB | repo root |
| `SPRINT0_MANIFEST.md` | This file | ~6KB | repo root |

### `/memory/` directory (agent memory / canonical references)

| File | Purpose | Size |
|---|---|---|
| `memory/ARCHITECTURE.md` | 7 invariants, 10 faculties, 13 rectifiers, daemon design | ~10KB |
| `memory/MISTAKES.md` | Living anti-pattern catalog (Boris pattern) | ~6.8KB |
| `memory/DECISIONS.md` | 6 starter ADRs + template | ~12KB |

### `/docs/` directory (human + agent documentation)

| File | Purpose | Size |
|---|---|---|
| `docs/PORTABILITY.md` | Cross-provider switching guide (the main strategic doc) | ~12.7KB |
| `docs/CODE_WITH_CLAUDE_2026.md` | Anthropic 2026 feature map by sprint | ~15KB |
| `docs/REFERENCES.md` | Full external reference index (16 sections) | ~14.2KB |

### `/scripts/` directory (operational scripts)

| File | Purpose | Size | Mode |
|---|---|---|---|
| `scripts/apply-oss-program.md` | Claude for OSS Program application draft | ~9.3KB | doc |
| `scripts/setup-symlinks.sh` | Post-clone agent-config wiring | ~6.7KB | executable |

**Total Sprint 0 output**: ~120KB across 11 files.

## Reference architecture embedded in these files

Every file includes inline links to the primary sources Etz Chaim builds
on, so any coding agent (Claude Code, Codex CLI, Cursor, etc.) reading
the repo can fetch them on demand:

### Boris Cherny (creator of Claude Code) — workflow patterns
- [Pinned thread on his workflow (Jan 2, 2026)](https://www.threads.com/@boris_cherny/post/DTBVlMIkpcm)
- [Worktree announcement (Feb 20, 2026)](https://www.threads.com/@boris_cherny/post/DVAAnexgRUj)
- [`/batch` announcement (Feb 27, 2026)](https://github.com/NousResearch/hermes-agent/issues/380)
- [VentureBeat manifesto](https://venturebeat.com/technology/the-creator-of-claude-code-just-revealed-his-workflow-and-developers-are)
- [Tips compendium](https://howborisusesclaudecode.com/)

### Anthropic engineering — foundational papers
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Writing tools for agents (Ken Aizawa)](https://www.anthropic.com/engineering/writing-tools-for-agents)
- [Equipping agents with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [Claude Code Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode)

### Barry Zhang & Mahesh Murag — Anthropic agents thesis
- [Don't Build Agents, Build Skills Instead — YouTube](https://www.youtube.com/watch?v=CEvIs9y1uog)

### Standards
- [Agent Skills (agentskills.io)](https://agentskills.io)
- [AGENTS.md (Linux Foundation AAIF)](https://agents.md)
- [Model Context Protocol](https://modelcontextprotocol.io)
- [Claude Code documentation](https://code.claude.com/docs/)

### Code with Claude SF 2026 — May 6, 2026
- [Recap (Blake Crosley)](https://blakecrosley.com/blog/code-with-claude-sf-2026-recap)
- [Notes (Chris Ebert)](https://chrisebert.net/notes-from-code-with-claude-2026/)

## How to deploy Sprint 0 to your repo

```bash
# 1. Clone your repo locally if not already
gh repo clone yohanpoul/etz-chaim-ai
cd etz-chaim-ai

# 2. Copy the Sprint 0 files into place
#    (download from this conversation's outputs first)
cp /path/to/downloads/AGENTS.md .
cp /path/to/downloads/CLAUDE.md .
cp /path/to/downloads/README.md .
cp /path/to/downloads/SPRINT0_MANIFEST.md .
mkdir -p memory docs scripts
cp /path/to/downloads/memory/*.md memory/
cp /path/to/downloads/docs/*.md docs/
cp /path/to/downloads/scripts/* scripts/
chmod +x scripts/setup-symlinks.sh

# 3. Wire the symlinks
./scripts/setup-symlinks.sh

# 4. Commit
git add AGENTS.md CLAUDE.md README.md SPRINT0_MANIFEST.md
git add memory/ docs/ scripts/
git add .codex .cursor .windsurfrules GEMINI.md .github/copilot-instructions.md
git commit -m "Sprint 0: standards-first foundation

- AGENTS.md as source unique config
- CLAUDE.md / .codex / .cursor / etc. symlink to AGENTS.md
- /memory/ directory: ARCHITECTURE, MISTAKES (Boris pattern), DECISIONS (6 ADRs)
- /docs/ directory: PORTABILITY, CODE_WITH_CLAUDE_2026, REFERENCES
- README with Bronze/Silver/Gold install tiers
- Claude for OSS Program application draft (deadline 2026-06-30)
- scripts/setup-symlinks.sh for cross-tool agent config wiring

See SPRINT0_MANIFEST.md for the full inventory.
"
git push
```

## What's next — Sprint 1 (Quick wins)

Sprint 1 focuses on **zero-architecture wins** — features you turn on
without restructuring code:

| Item | Effort | Impact |
|---|---|---|
| Prompt caching on the 1696-spec corpus | 2h | ~90% cost reduction on improve-loop |
| Upgrade deep facultés to Opus 4.7 (Apr 16, 2026) | 1h | ~13% quality lift |
| Adaptive thinking instead of manual `budget_tokens` | 2h | Quality + cost balance |
| Batch API for the nightly daemon | 4h | Additional 50% cost reduction |
| Citations API native mapping for E1–E6 | 6h | Cleaner audit trail |
| Sandbox + Auto Mode activation (if on Max+) | 1h | Remove `--dangerously-skip-permissions` |
| Submit Claude for OSS application | 30min | Up to 6 months Max free |

**Recommended order**: Submit OSS application first (deadline pressure),
then prompt caching (immediate cost win), then Opus 4.7 (quality), then
the rest.

## Sprint 0 commitments delivered ✅

From the agreed-upon Sprint 0 plan:

- [x] Apply Claude for OSS Program — draft ready, see `scripts/apply-oss-program.md`
- [x] Mettre en place AGENTS.md + CLAUDE.md symlink — done, see `scripts/setup-symlinks.sh`
- [x] Restructurer `memory/` avec MISTAKES.md, DECISIONS.md, ARCHITECTURE.md — done
- [x] README mis à jour avec 3 niveaux d'install (Bronze/Silver/Gold) — done
- [x] Article positionnement — embedded in README

## Acknowledgments

This Sprint 0 output stands on the shoulders of:

- **Boris Cherny** (creator of Claude Code) — the workflow patterns
  encoded throughout
- **Barry Zhang & Mahesh Murag** (Anthropic) — the Skills-first thesis
  we apply
- **Erik Schluntz** (Anthropic) — the Building Effective Agents foundations
- **The Anthropic engineering team** — for shipping a stack worth
  building on
- **The Linux Foundation AAIF + agentskills.io community** — for
  stewarding the standards that make Etz Chaim portable

Full reference index in [`docs/REFERENCES.md`](docs/REFERENCES.md).

---

**Ready to commit.** When you're ready, run `./scripts/setup-symlinks.sh`
after copying these files into the repo, then `git add && git commit`.

Then we move on to Sprint 1.
