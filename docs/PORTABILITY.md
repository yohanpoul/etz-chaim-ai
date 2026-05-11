# Portability — Cross-provider switching for Etz Chaim AI

> _"If I switch to GPT-5.5 / Gemini 3 / Ollama, does Etz Chaim still work?"_
>
> **TL;DR — Yes.** Etz Chaim is built standards-first. Switch in <30 minutes
> if you follow this guide.

## The three-layer architecture

Etz Chaim AI is split into three layers with very different portability
guarantees. Understanding them is the key to knowing what's safe and what's
not when switching providers.

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
│  1696 specs · Karpathy daemon · Python + LiteLLM (100+ providers) │
└───────────────────────────────────────────────────────────────────┘
```

## What's PORTABLE (works on any provider)

### Layer 1 — Cognitive engine

The Python code that implements the 10 faculties, 13 rectifiers, 11
adversaries, 22 sentiers, and 1696 specs is **provider-agnostic**. Every
LLM call routes through [LiteLLM](https://github.com/BerriAI/litellm),
which supports 100+ providers.

```yaml
# litellm.config.yaml
model_list:
  - model_name: deep-reasoning
    litellm_params:
      model: anthropic/claude-opus-4-7   # ← swap this line
      api_key: ${ANTHROPIC_API_KEY}
  - model_name: fast-dispatch
    litellm_params:
      model: anthropic/claude-haiku-4-5
      api_key: ${ANTHROPIC_API_KEY}
```

To switch to GPT-5.5:
```yaml
  - model_name: deep-reasoning
    litellm_params:
      model: openai/gpt-5.5
      api_key: ${OPENAI_API_KEY}
```

To switch to Gemini 3 Pro:
```yaml
  - model_name: deep-reasoning
    litellm_params:
      model: gemini/gemini-3-pro
      api_key: ${GEMINI_API_KEY}
```

To run fully local on Ollama:
```yaml
  - model_name: deep-reasoning
    litellm_params:
      model: ollama/llama3.3:70b
      api_base: http://localhost:11434
```

### Layer 2 — Open standards

| Standard | Used by | Etz Chaim component |
|---|---|---|
| [Agent Skills](https://agentskills.io) | Claude Code, Codex CLI, Cursor, Gemini CLI, GitHub Copilot, Antigravity, Cline, Windsurf, OpenCode, goose, Letta, Amp, Devin (35+ platforms) | 13 SKILL.md files |
| [MCP](https://modelcontextprotocol.io) | Claude Code, Codex CLI, Cursor, Windsurf, VS Code Copilot, ChatGPT Developer Mode, Bifrost, Kong AI Gateway | `etzchaim-mcp` server |
| [AGENTS.md](https://agents.md) | Codex CLI, Cursor, Windsurf, Amp, Devin, Jules, Factory, GitHub Copilot | source-unique config |
| [Dev Containers](https://containers.dev/) | VS Code, GitHub Codespaces, JetBrains, Cursor | one-line install |
| [OpenTelemetry](https://opentelemetry.io/) | Grafana, Datadog, Honeycomb, Sentry, Cowork OTel | observability layer |
| [JSON Schema](https://json-schema.org/) | All providers | tool definitions |

**These are not Anthropic-specific.** They work today on any conforming
agent.

## What's ANTHROPIC-ONLY (Layer 3 bonuses)

These features are wonderful but tie you to Anthropic. Etz Chaim wires
them in **optionally** behind feature flags:

| Feature | What it does | Etz Chaim equivalent without it |
|---|---|---|
| [Auto Mode](https://www.anthropic.com/engineering/claude-code-auto-mode) | Sonnet 4.6 classifier gates risky actions | Manual permission prompts or sandbox |
| [Channels](https://code.claude.com/docs/en/channels) | Push events into session (Telegram, Discord, iMessage, webhooks) | Hookdeck CLI + custom script |
| [Claude Code Routines](https://thenewstack.io/claude-code-can-now-do-your-job-overnight/) | Cloud-hosted scheduled prompts | GitHub Actions workflow on schedule |
| [Managed Agents](https://docs.anthropic.com/en/docs/build-with-claude/managed-agents) | Persistent agent + memory + dreaming | Local Python daemon + Pydantic AI |
| Dreaming | Scheduled memory curation | Custom Python: compaction + summarization |
| Outcomes | Rubric grader in separate context | Custom Pydantic eval + LLM-as-judge |
| Multiagent orchestration | Lead agent + parallel specialist sub-agents | Worktrees + tmux via `/adversarial-probe` |
| Cowork Dispatch | Mobile → desktop remote control | SSH + tmux |
| Extended/Adaptive thinking | Model decides thinking budget | Manual reasoning_effort on OpenAI, default on others |
| Prompt caching with breakpoints | ~90% cost reduction on repeated context | OpenAI prompt caching (different format) |
| Citations native API | First-class citation tokens | Post-processing E-label extraction |

## Concrete switching scenarios

### Scenario A — Switch from Claude Opus 4.7 to GPT-5.5

**Steps**:
1. Edit `litellm.config.yaml`, change `anthropic/claude-opus-4-7` to
   `openai/gpt-5.5`. (Approx 1 line.)
2. Set `OPENAI_API_KEY` env var.
3. Disable Anthropic-only bonus features:
   ```bash
   mv .claude/settings.json .claude/settings.json.anthropic-only
   gh workflow enable nightly-improve.yml   # use GHA fallback for daemon
   ```
4. Run `make test` (1388 tests should pass — they're provider-agnostic).
5. Run `python scripts/multi-provider-test.py --provider openai/gpt-5.5`
   to validate cognitive faculties end-to-end.

**Time**: ~30 minutes.

**Caveats**:
- Lose Auto Mode safety net → use [Codex Cloud sandboxing](https://www.developersdigest.tech/blog/codex-changelog-april-2026) or manual reviews
- Lose Channels Telegram alerts → use webhook → Telegram bot manually
- Lose Routines → use `.github/workflows/nightly-improve.yml`
- Lose Dreaming → memory curation runs as nightly Python job

### Scenario B — Run fully local (Ollama on a workstation)

**Steps**:
1. Install Ollama: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull a capable local model: `ollama pull qwen3:72b` or `llama3.3:70b`
3. Edit `litellm.config.yaml`:
   ```yaml
   - model_name: deep-reasoning
     litellm_params:
       model: ollama/qwen3:72b
       api_base: http://localhost:11434
   ```
4. Disable all Anthropic-bonus features (Layer 3).
5. Use [OpenCode](https://opencode.ai) as the coding agent (75+ providers,
   MIT, 150K stars).

**Time**: ~1 hour (Ollama pull is the slow step).

**Caveats**:
- Slower inference depending on hardware
- Smaller context window on most local models
- The 1696-spec corpus may need to use the `etz-spec-lookup` skill more
  aggressively (no prompt caching benefit on local)

### Scenario C — Hybrid: Anthropic for primary, OpenAI for fallback

**Steps**:
1. Configure LiteLLM fallback:
   ```yaml
   model_list:
     - model_name: deep-reasoning
       litellm_params:
         model: anthropic/claude-opus-4-7
         api_key: ${ANTHROPIC_API_KEY}
     - model_name: deep-reasoning   # same name → fallback
       litellm_params:
         model: openai/gpt-5.5
         api_key: ${OPENAI_API_KEY}
   router_settings:
     fallbacks: [{"deep-reasoning": ["deep-reasoning"]}]
   ```
2. LiteLLM automatically falls over on rate limit / 429.

**Time**: ~5 minutes.

**Caveats**: tool-use schemas differ between providers; LiteLLM normalizes
most but check `etzchaim/llm/normalize.py` for the specific tool you use.

### Scenario D — Pydantic AI route (typed cross-provider)

For modules where type safety matters more than raw speed, use
[Pydantic AI](https://ai.pydantic.dev/) which gives one-line provider
switching with full Pydantic schema enforcement:

```python
from pydantic_ai import Agent
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIChatModel

primary = AnthropicModel('claude-opus-4-7')
fallback = OpenAIChatModel('gpt-5.5')

agent = Agent(
    FallbackModel(primary, fallback),
    output_type=SpecMutation,   # typed!
)
result = agent.run_sync("Propose a mutation for spec EC-K7-042.")
mutation: SpecMutation = result.output   # full IDE autocomplete
```

## Validation — does the switch work?

Run the cross-provider test harness:
```bash
python scripts/multi-provider-test.py
```

This script:
1. Runs the 13 rectifiers against a fixed scenario
2. Validates the 11 adversarial probes
3. Compares outputs to golden references in `evals/benchmark/`
4. Reports the parity score across providers

Expected: ≥90% parity between Anthropic, OpenAI, Google. <80% indicates
a regression that should be filed as an issue.

## The Provider Compatibility Matrix

| Component | Anthropic | OpenAI | Google | Local (Ollama) |
|---|---|---|---|---|
| 10 facultés | ✓ | ✓ | ✓ | ✓ |
| 13 rectifieurs | ✓ | ✓ | ✓ | ✓ |
| 11 adversaires | ✓ | ✓ | ✓ | ✓ |
| 1696 specs | ✓ | ✓ | ✓ | ✓ |
| Karpathy daemon | ✓ | ✓ | ✓ | ✓ |
| Skills (`/skills/`) | ✓ Claude Code | ✓ Codex CLI | ✓ Gemini CLI | ✓ goose / OpenCode |
| MCP server (`etzchaim-mcp`) | ✓ | ✓ | ✓ | ✓ |
| AGENTS.md | ✓ Claude Code | ✓ Codex CLI | ⚠ Gemini reads GEMINI.md | ✓ OpenCode |
| Hooks | ✓ (26 events) | ✓ (codex_hooks) | ⚠ Limited | ⚠ OpenCode partial |
| Auto Mode | ✓ Max+/Team/Ent | — | — | — |
| Channels | ✓ research preview | — | — | — |
| Routines (cloud-hosted) | ✓ Pro+ | ⚠ Codex Cloud (different) | — | — |
| Managed Agents + Dreaming | ✓ | — | — | — |
| Multiagent orchestration | ✓ public beta | ⚠ Codex multi-agent v2 | ⚠ Antigravity | ⚠ Workspaces |
| Cowork Dispatch | ✓ | ⚠ ChatGPT mobile | — | — |
| Prompt caching | ✓ explicit breakpoints | ✓ auto | ✓ implicit | — |
| Extended thinking | ✓ adaptive | ✓ reasoning_effort | ✓ thinking | — |

## The bottom line

If you stick to **Layer 1 + Layer 2**, Etz Chaim is essentially fully
portable. Switching providers is a config file edit. The cognitive engine
keeps working, the rectifiers keep policing, the 1696 specs keep their
audit trail, the Karpathy daemon keeps improving — all on whatever
provider you choose.

**Layer 3 is the icing.** When you have an Anthropic Max plan (or qualify
for the [Claude for Open Source Program](https://claude.com/contact-sales/claude-for-oss)
— free Claude Max for 6 months for active OSS maintainers), turn it on
for the extra polish. Otherwise, the system works.

## References

- [LiteLLM 100+ providers](https://docs.litellm.ai/docs/providers)
- [Pydantic AI multi-model](https://ai.pydantic.dev/)
- [OpenCode 75+ providers (Models.dev)](https://opencode.ai/)
- [Bifrost / Kong / Cloudflare AI Gateway comparison](https://www.getmaxim.ai/articles/top-5-enterprise-llm-gateways-in-2026/)
- [Claude Code vs Codex CLI 2026](https://blakecrosley.com/blog/codex-vs-claude-code-2026)
- [Agent Skills cross-tool standard](https://www.agensi.io/learn/agent-skills-open-standard)
- [AGENTS.md cross-tool guide](https://vibecoding.app/blog/agents-md-guide)
- [Anthropic OpenAI SDK compatibility caveats](https://docs.anthropic.com/en/api/openai-sdk)
