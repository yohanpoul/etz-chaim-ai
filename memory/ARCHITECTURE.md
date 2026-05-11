# Etz Chaim AI — Architecture Reference

> Stable reference document. The source of truth for "how the system works."
> Read this before proposing any spec mutation or refactor.

## System invariants (NEVER violate)

These are the seven invariants that distinguish Etz Chaim AI from a generic
RAG or prompt-chain system. Violating any of them silently breaks the
self-improvement loop.

### Invariant 1 — Channel-only writes to aggregate scores

No code path may directly mutate aggregated scoring fields
(`causalengine.aggregate_score`, `explorationengine.aggregate_score`, etc.).
All writes go through named **channels** that record provenance:

```python
causal.channel("backdoor_validation").write(
    score=0.87,
    spec_ref="EC-K5-001",
    e_label="E2",
    reason="Backdoor criterion satisfied per Pearl §3.3.2",
)
```

This is enforced by the `PreToolUse-aggregate-write.sh` hook and the
`make check-aggregates` static check.

### Invariant 2 — Circuit-breaker on all external LLM calls

Every external call (LiteLLM, MCP server, web fetch, embedding API) wraps in
a circuit breaker with policy: **5 failures → 30s cooldown → exponential
backoff up to 5 minutes**. Failures during cooldown go to the fallback
provider or return a typed `CircuitOpenError`. No retry loops in user code.

### Invariant 3 — Plan-mode + verify-spec for spec mutations

Every change to a spec assertion (1696 specs, E1–E6 labeled) MUST:
1. Be proposed in **Plan mode** (Claude Code Shift+Tab twice, or
   `etzchaim mutate-spec --plan-only` in non-Claude tools)
2. Pass the `verify-spec` subagent (see `agents/verify-spec.md`)
3. Open a PR for human review

This is Boris Cherny's "give Claude a way to verify its work" pattern,
specialized for our spec corpus.

### Invariant 4 — Citations E1–E6

Every new spec assertion carries an E-label:
- **E1** — verbatim from primary source (with exact quote ≤ 15 words)
- **E2** — direct paraphrase of primary source
- **E3** — derivation from primary source(s) with explicit step
- **E4** — analogical extension from a known principle
- **E5** — hypothetical / proposed
- **E6** — speculative

The bidirectional audit (`make verify-bidirectional`) requires every spec
ID cited in code to exist in the corpus, and every corpus spec referenced
in code to have valid citations.

### Invariant 5 — Test budget

The 1388 tests run in <3 seconds. Adding tests that push this over 5
seconds requires an ADR (see `memory/DECISIONS.md`). Slow tests go in
`tests/slow/` and run nightly, not on every commit.

### Invariant 6 — One-shot installable

A new contributor runs `pipx install etzchaim` (or opens the devcontainer)
and is operational in <5 minutes. No system-specific tweaks, no manual env
variables beyond `ANTHROPIC_API_KEY` or equivalent. If you change
something that breaks this, document it in the devcontainer's `init.sh`.

### Invariant 7 — Provider-agnostic core

The cognitive engine MUST work on any LiteLLM-supported provider. Anthropic
features (Auto Mode, Channels, Routines, Managed Agents, Dreaming, Outcomes)
are wired in OPTIONALLY behind feature flags; absence of an Anthropic key
must not break the core nightly loop or any of the 13 rectifiers.

## The 10 cognitive faculties — contracts

Each faculty is a Python module under `etzchaim/faculties/<name>/`. Contract:

| Field | Type | Purpose |
|---|---|---|
| `name` | `str` | Unique identifier |
| `inputs` | `Pydantic BaseModel` | Typed input schema |
| `outputs` | `Pydantic BaseModel` | Typed output schema |
| `metrics` | `dict[str, Histogram]` | Prometheus-compatible observability |
| `rectifiers` | `list[Rectifier]` | Which rectifiers apply |
| `spec_refs` | `list[str]` | EC-XX-NNN backing references |

### The faculties

1. **explorationengine** — cross-domain exploration & cognitive surprise
2. **autojudge** — adversarial evaluation of own outputs
3. **causalengine** — Pearl criteria (do-calculus, backdoor, frontdoor, IV)
4. **dissensuengine** — contradiction & belief-divergence detection
5. **insightforge** — hypothesis generation
6. **selfmodel** — predict own errors before they occur
7. **selfmap** — track competence landscape
8. **epistememory** — persistent epistemic memory
9. **failuretoinsight** — learn from past errors (the Karpathy loop input)
10. **intentkeeper** — goal persistence across context shifts

Each is independently testable, observable, and replaceable. The system
is composable, not monolithic.

## The 13 rectifiers

Background daemons that police invariants and report drift. Each has:
- A trigger condition (Prometheus query or Python predicate)
- A diagnosis function (returns structured report)
- A proposed rectification (spec mutation candidate)
- Visibility in Grafana dashboard at `/grafana/d/rectifiers`

The 13:
1. **exploration-starvation** — too narrow exploration sampling
2. **judgment-bias** — autojudge favoring own outputs
3. **causal-spurious** — correlations slipping through as causes
4. **dissensus-suppression** — contradictions being hidden
5. **insight-stale** — no new hypotheses in N hours
6. **selfmodel-overconfidence** — predicted error rate diverges from actual
7. **selfmap-drift** — competence landscape becoming stale
8. **memory-rot** — epistememory accumulating contradictions
9. **failuretoinsight-blocked** — failures not being processed
10. **intent-drift** — current behavior diverging from declared intent
11. **aggregate-leak** — direct aggregate writes detected (invariant 1)
12. **circuit-storm** — circuit breaker opening too often (invariant 2)
13. **citation-decay** — E-label distribution shifting toward E5/E6

## The 11 malakhim adversaries

Adversarial probes that simulate failure modes. Run via
`/adversarial-probe` (spawns 11 parallel worktrees + tmux sessions) or via
Managed Agents multiagent orchestration:

1. **false_authority** — fake citation, plausible-looking but wrong
2. **unbounded_exploration** — explore until context overflow
3. **concealed_failures** — hide tool errors from the agent loop
4. **aesthetic_deception** — output is beautiful but wrong
5. **overconfidence** — claim certainty above empirical evidence
6. **premature_closure** — settle on first plausible answer
7. **spec_dilution** — mutate spec to lower E-label silently
8. **surface_mimicry** — copy form of correct answer, miss substance
9. **cognitive_overload** — flood context with relevant-looking noise
10. **boundary_erosion** — gradually violate invariants
11. **identity_drift** — claim to be a different agent than the one running

Each adversary has a corresponding rectifier and eval.

## The auto-improve daemon — Karpathy AutoResearch pattern

`etzchaim_daemon/improve_loop.py` (~630 lines). Nightly run (or via Claude
Code Routine, or via GHA workflow):

1. **Read failure traces** from the past 24h (Sentry + local logs)
2. **Cluster** by faculty / rectifier
3. **Generate spec mutation candidates** (≤3 per cluster) via the
   `improve-loop` subagent in Plan mode
4. **Verify each candidate** with `verify-spec` subagent
5. **Run 1388 tests** + the 11 adversarial probes
6. **Open PR** with passing mutations, tagged `auto-improve`
7. **Webhook → Telegram channel** for maintainer review

Pattern reference: Andrej Karpathy's AutoResearch tweets (2024) + the
Anthropic [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) doc (initializer + coding agent + persistent artifacts).

## Observability

- **Prometheus** scrapes `/metrics` (port 9090)
- **Grafana** dashboards at `/grafana` (port 3000)
- **TimescaleDB** stores time-series for rectifier triggers
- **OpenTelemetry** traces (compatible with Claude Code Cowork OTel
  expansion announced at Code with Claude 2026)
- **Sentry** for errors (with `etzchaim-mcp` integration)
- **`/insights`** in Claude Code with `cleanupPeriodDays: 365` for the
  longitudinal self-improvement flywheel (Shrivu Shankar pattern)

## Files & directories

```
etzchaim/                   # core Python package (existing)
├── faculties/              # 10 faculty modules
├── rectifiers/             # 13 rectifier modules
├── adversaries/            # 11 malakhim modules
├── sentiers/               # 22 typed routing paths
├── specs/                  # 1696 primary-source spec assertions
└── daemon/                 # Karpathy improve loop

etzchaim_mcp/               # MCP server (Sprint 5)
litellm.config.yaml         # provider config (one-line switching)

skills/                     # CANONICAL skill source (Sprint 2)
agents/                     # subagents (Sprint 3)
commands/                   # slash commands (Sprint 3)
hooks/                      # lifecycle hooks (Sprint 4)
.claude-plugin/             # plugin manifest (Sprint 6)
.mcp.json                   # MCP server registry (Sprint 5)
.devcontainer/              # one-line install (Sprint 4)

memory/                     # CANONICAL agent memory
docs/                       # human + agent documentation
scripts/                    # helper scripts (sync-skills, setup-symlinks)
evals/                      # eval suites per skill/rectifier/adversary
```

## External architectural references

- [Andrej Karpathy on autonomous research loops (2024)](https://x.com/karpathy)
- [Anthropic — Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Anthropic — Multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [SOAR cognitive architecture](https://soar.eecs.umich.edu/)
- [ACT-R cognitive architecture](http://act-r.psy.cmu.edu/)
- [CLARION cognitive architecture (Sun)](https://clarioncognitivearchitecture.com/)
- [LIDA framework (Franklin et al.)](https://ccrg.cs.memphis.edu/lida.html)
- [Pearl, J. — Causality (2009)](https://bayes.cs.ucla.edu/BOOK-2K/)
