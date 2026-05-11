# Portability — Cross-provider switching for Etz Chaim AI

> _"If I switch to GPT-5.5 / Gemini 3 / Ollama, does Etz Chaim still work?"_
>
> **TL;DR — Yes.** Etz Chaim is built standards-first. The cognitive engine
> routes through a profile-keyed `config.yaml` with 6 pre-baked profiles.
> Switching providers is a profile swap, not a refactor.

## The three-layer architecture

Etz Chaim AI is split into three layers with very different portability
guarantees.

```
┌───────────────────────────────────────────────────────────────────┐
│  LAYER 3 — Anthropic-specific bonuses (NOT portable)              │
│  Auto Mode · Channels · Routines · Managed Agents · Dreaming      │
│  Outcomes · Multiagent orchestration · Cowork Dispatch            │
└───────────────────────────────────────────────────────────────────┘
                                ▲
                                │ optional, feature-flagged
                                │
┌───────────────────────────────────────────────────────────────────┐
│  LAYER 2 — Open standards (PORTABLE 95-100%)                      │
│  Skills (agentskills.io · 35+ tools) · MCP (AAIF/Linux Foundation │
│  · 6000+ servers) · AGENTS.md (AAIF) · Dev Containers spec        │
│  · OpenTelemetry · JSON Schema                                    │
└───────────────────────────────────────────────────────────────────┘
                                ▲
                                │
┌───────────────────────────────────────────────────────────────────┐
│  LAYER 1 — Cognitive engine (PORTABLE 100%)                       │
│  10 facultés · 13 rectifieurs · 11 adversaires · 22 sentiers      │
│  1696 specs · daemon.py · config.yaml + provider registry         │
└───────────────────────────────────────────────────────────────────┘
```

## What's PORTABLE (works on any provider)

### Layer 1 — Cognitive engine via profile-keyed `config.yaml`

The cognitive engine is **provider-agnostic by design**. Every LLM call
goes through `etzchaim/providers/registry.py::select_claude_backend()`
which dispatches to the active profile in `config.yaml`.

`config.yaml` contains **6 pre-baked profiles** at the repo root:

| Profile | Stack | When to use |
|---|---|---|
| `claude_max` | Anthropic CLI subprocess | You have Claude Pro/Max (no API key in env) |
| `anthropic_full` | Anthropic API direct (Opus + Sonnet + Haiku 4.x) | Full Anthropic, programmatic |
| `gpt5_full` | OpenAI GPT-5.x family | Full OpenAI stack |
| `gemini_full` | Google Gemini 3 family | Full Google stack |
| `bedrock` | Anthropic via AWS Bedrock | Enterprise / AWS-aligned |
| `benchmark_opus` | Fixed Opus build | Benchmark reproducibility (anti-drift) |

To switch provider: change the **active profile** in `config.yaml`. The
cognitive engine adapts automatically.

```yaml
# config.yaml (excerpt — real structure)
active_profile: anthropic_full  # ← change this line to switch
profiles:
  anthropic_full:
    primary: anthropic/claude-opus-4-7
    fast: anthropic/claude-haiku-4-5
    # ...
  gpt5_full:
    primary: openai/gpt-5.5
    fast: openai/gpt-5.2-mini
    # ...
```

### Layer 2 — Open standards

| Standard | Used by | Etz Chaim component |
|---|---|---|
| [Agent Skills](https://agentskills.io) | Claude Code, Codex CLI, Cursor, Gemini CLI, GitHub Copilot, Antigravity, Cline, Windsurf, OpenCode, goose, Letta, Amp, Devin (35+ platforms) | 13 SKILL.md files |
| [MCP](https://modelcontextprotocol.io) | Claude Code, Codex CLI, Cursor, Windsurf, VS Code Copilot, ChatGPT Developer Mode | `etzchaim-mcp` server |
| [AGENTS.md](https://agents.md) | Codex CLI, Cursor, Windsurf, Amp, Devin, Jules, Factory, GitHub Copilot | source-unique config |
| [Dev Containers](https://containers.dev/) | VS Code, GitHub Codespaces, JetBrains, Cursor | one-line install |
| [OpenTelemetry](https://opentelemetry.io/) | Grafana, Datadog, Honeycomb, Sentry | observability |
| [JSON Schema](https://json-schema.org/) | All providers | tool definitions |

## What's ANTHROPIC-ONLY (Layer 3 bonuses)

| Feature | What it does | Etz Chaim equivalent without it |
|---|---|---|
| [Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode) | Sonnet 4.6 classifier gates risky actions | Manual permission prompts or sandbox |
| [Channels](https://code.claude.com/docs/en/channels) | Push events into session | Hookdeck CLI + custom script |
| [Routines](https://thenewstack.io/claude-code-can-now-do-your-job-overnight/) | Cloud-hosted scheduled prompts | GitHub Actions on schedule |
| [Managed Agents](https://docs.anthropic.com/en/docs/build-with-claude/managed-agents) | Persistent agent + memory + dreaming | Local Python daemon + Pydantic AI |
| Dreaming | Memory curation | Custom Python: compaction + summarization |
| Outcomes | Rubric grader in separate context | Custom Pydantic eval + LLM-as-judge |
| Multiagent orchestration | Lead agent + parallel sub-agents | Worktrees + tmux via `/adversarial-probe` |
| Extended/Adaptive thinking | Model decides thinking budget | Manual reasoning_effort on OpenAI |
| Prompt caching (breakpoints) | ~90% cost reduction | OpenAI prompt caching (different format) |
| Citations native API | First-class citation tokens | Post-processing E-label extraction |

## Concrete switching scenarios

### Scenario A — Switch from Claude Opus 4.7 to GPT-5.5

**Steps**:
1. Edit `config.yaml`, set `active_profile: gpt5_full`
2. Set `OPENAI_API_KEY` env var
3. Disable Anthropic-only bonus features in `.claude/settings.json`
4. Run `make test` (1388 tests should pass — they're provider-agnostic)
5. Run `python scripts/multi-provider-test.py --profile gpt5_full`
   (Sprint 1 deliverable) to validate cognitive faculties end-to-end

**Time**: ~30 minutes.

**Caveats**:
- Lose Auto Mode safety net → use Codex Cloud sandboxing or manual reviews
- Lose Channels Telegram alerts → use webhook → Telegram bot manually
- Lose Routines → use `.github/workflows/nightly-improve.yml`
- Lose Dreaming → memory curation runs as nightly Python job

### Scenario B — Run fully local (Ollama on a workstation)

**Steps**:
1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull a capable local model: `ollama pull qwen3:72b`
3. Add a `local_ollama` profile to `config.yaml`:
   ```yaml
   profiles:
     local_ollama:
       primary: ollama/qwen3:72b
       api_base: http://localhost:11434
   active_profile: local_ollama
   ```
4. Disable all Anthropic-bonus features
5. Use [OpenCode](https://opencode.ai) as the coding agent

**Time**: ~1 hour (Ollama pull is the slow step).

### Scenario C — Hybrid: Anthropic for primary, OpenAI for fallback

In `config.yaml`, define a profile with fallback chain:

```yaml
profiles:
  hybrid:
    primary: anthropic/claude-opus-4-7
    primary_api_key_env: ANTHROPIC_API_KEY
    fallback: openai/gpt-5.5
    fallback_api_key_env: OPENAI_API_KEY
active_profile: hybrid
```

The provider registry handles failover on rate limit / 5xx.

### Scenario D — Pydantic AI route (typed cross-provider)

For modules where type safety matters, use [Pydantic AI](https://ai.pydantic.dev/):

```python
from pydantic_ai import Agent
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel

primary = AnthropicModel('claude-opus-4-7')
fallback = OpenAIChatModel('gpt-5.5')

agent = Agent(
    FallbackModel(primary, fallback),
    output_type=SpecMutation,
)
```

## Validation — does the switch work?

After Sprint 1 lands the multi-provider test harness, run:
```bash
python scripts/multi-provider-test.py
```

Expected: ≥90% parity between Anthropic, OpenAI, Google. <80% indicates
a regression that should be filed as an issue.

## The Provider Compatibility Matrix

| Component | Anthropic | OpenAI | Google | Local (Ollama) |
|---|---|---|---|---|
| 10 facultés | ✓ | ✓ | ✓ | ✓ |
| 13 rectifieurs | ✓ | ✓ | ✓ | ✓ |
| 11 adversaires | ✓ | ✓ | ✓ | ✓ |
| 1696 specs | ✓ | ✓ | ✓ | ✓ |
| `daemon.py` (Karpathy loop) | ✓ | ✓ | ✓ | ✓ |
| Skills (`/skills/`) | ✓ Claude Code | ✓ Codex CLI | ✓ Gemini CLI | ✓ goose / OpenCode |
| MCP server (`etzchaim-mcp`) | ✓ | ✓ | ✓ | ✓ |
| AGENTS.md | ✓ Claude Code | ✓ Codex CLI | ⚠ Gemini reads GEMINI.md | ✓ OpenCode |
| Hooks | ✓ (26 events) | ✓ (codex_hooks) | ⚠ Limited | ⚠ OpenCode partial |
| Auto Mode | ✓ Max+/Team/Ent | — | — | — |
| Channels | ✓ research preview | — | — | — |
| Routines | ✓ Pro+ | ⚠ Codex Cloud | — | — |
| Managed Agents + Dreaming | ✓ | — | — | — |
| Multiagent orchestration | ✓ public beta | ⚠ Codex v2 | ⚠ Antigravity | ⚠ Workspaces |
| Prompt caching | ✓ explicit breakpoints | ✓ auto | ✓ implicit | — |
| Extended thinking | ✓ adaptive | ✓ reasoning_effort | ✓ thinking | — |

## The bottom line

If you stick to **Layer 1 + Layer 2**, Etz Chaim is fully portable.
Switching providers is a profile edit in `config.yaml`. The cognitive
engine keeps working, the rectifiers keep policing, the 1696 specs keep
their audit trail, the Karpathy daemon keeps improving — on whatever
provider you choose.

**Layer 3 is the icing.** When you have an Anthropic Max plan (or qualify
for the [Claude for Open Source Program](https://claude.com/contact-sales/claude-for-oss)),
turn it on for the extra polish. Otherwise, the system works.

## References

- [LiteLLM 100+ providers](https://docs.litellm.ai/docs/providers)
- [Pydantic AI multi-model](https://ai.pydantic.dev/)
- [OpenCode 75+ providers (Models.dev)](https://opencode.ai/)
- [Bifrost / Kong / Cloudflare AI Gateway comparison](https://www.getmaxim.ai/articles/top-5-enterprise-llm-gateways-in-2026/)
- [Agent Skills cross-tool standard](https://www.agensi.io/learn/agent-skills-open-standard)
- [AGENTS.md cross-tool guide](https://vibecoding.app/blog/agents-md-guide)
- [Anthropic OpenAI SDK compatibility caveats](https://docs.anthropic.com/en/api/openai-sdk)
- The real configuration: see `config.yaml` (in repo root) in repo root
