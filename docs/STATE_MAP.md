# Etz Chaim AI — State Map (Phase 0 honest audit)

> Read-only audit, claim (docs/specs) vs implemented vs tested. Static analysis;
> the 4557-test suite was not executed. Legend: 🟢 real · 🟡 partial · 🔴 shell.
> Tally over 151 elements: 82 real · 37 partial · 32 shell.
>
> Method: 16 read-only sub-agents (one per zone), each labelling every element with
> `file:line` evidence. Full evidence (with internal module paths) lives in
> `docs/internal/STATE_MAP_DETAIL.md` (kept out of the public surface per the neutrality gate).
> The `verify-spec` completion gate could not be run because it does not exist (see §4); shell
> claims were re-verified by independent grep instead.

## 1. Cognitive faculties (10)

| # | Faculty (module) | Claim | Status | One-line reality |
|---|---|---|---|---|
| 1 | explorationengine | cross-domain exploration & surprise | 🟡 | sub-modules (cross_domain, analogy_engine, novelty_scorer, serendipity, db) real; **core misses the declared faculty interface** (inputs/outputs/metrics/spec_refs), no channel provenance, not wired into the nightly loop |
| 2 | autojudge | adversarial self-evaluation | 🟢 | full loop runner + multi-evaluator + domain judges + persistence, wired in; no E-label citations, optional bridge not circuit-broken |
| 3 | causalengine | Pearl: do-calculus/backdoor/frontdoor/IV | 🟡 | **Pearl criteria NOT implemented** — only a 3-level evidence hierarchy + confounder/DAG/scorer (those are real). No d-separation, no identifiability |
| 4 | dissensuengine | contradiction & divergence detection | 🟢 | 826-line core, divergence logic, scheduler, full persistence, 95+ tests, daemon-wired |
| 5 | insightforge | hypothesis generation & insight forging | 🟢 | real 7-phase orchestrator + validators + emergence/novelty, 248 tests; depends on pgvector being populated |
| 6 | selfmodel | predict own errors | 🟢 | state capture + bias + predictor + evolution + closed-loop verify, daemon-wired; **Guardian submodule 🔴 dead (never instantiated)**; verification heuristic not ground-truth |
| 7 | selfmap | competence landscape & routing | 🟢 | domain detect + eval + routing + calibration + DB; LLM-fallback detector is dead code; no drift rectifier |
| 8 | epistememory | persistent epistemic memory | 🟢 | deployed: pgvector, 11 methods, 44 tests, contradiction graph, GC; `recall_hybrid()` 🟡 beta (0 tests/calls) |
| 9 | failuretoinsight | learn from errors (loop input) | 🟡 | core classifier real, but **2 sub-modules 🔴 shell (NogahMiner, TmeotDetector: unused dead code)**; hypothesis guidance never fed back to the loop |
| 10 | intentkeeper | goal persistence across shifts | 🟢 | progress/abandon/strategy + planner + DB + daemon task; auto-seed & progress-recalc 🟡 fragile string-matching |

Faculties: **7 real · 3 partial · 0 fully shell.** The cognitive substrate is the strongest part.

## 2. Rectifiers (13)

| # | Rectifier (function) | Spec | Code | Test | Status |
|---|---|---|---|---|---|
| R01 | contradiction resolution | ✓ | ✓ | ✓ | 🟢 |
| R02 | memory bloat | ✓ | ✓ | ✓ | 🟢 |
| R03 | insight grounding | ✓ | ✓ | ✓ | 🟢 |
| R04 | goal drift | ✓ | ✓ | ✓ | 🟢 |
| R05 | tension freeze | ✓ | ✓ | ✓ | 🟢 |
| R06 | self-model overconfidence | ✓ | ✓ | ✓ | 🟢 |
| R07 | faculty starvation | ✓ | ✗ | ✗ | 🔴 unstarted |
| R08 | exploration starvation | ✓ | ✓* | partial | 🟢 *code in an internal rectification module, re-exported via `etzchaim/probes/` — not the declared `r08.py` path* |
| R09 | cross-coupling overload | ✓ | ✗ | ✗ | 🔴 unstarted |
| R10 | recursive analogy | ✓ | ✗ | ✗ | 🔴 unstarted |
| R11 | calibration drift | ✓ | ✗ | ✗ | 🔴 unstarted (7×7 matrix unbuilt) |
| R12 | probe noise | ✓ | ✗ | ✗ | 🔴 unstarted (meta-rectifier) |
| R13 | trace amnesia / stale causal claims | ✓ | ✓* | partial | 🟢 *same internal module as R08, path mismatch* |

Rectifiers: **8 real · 5 shell.** Specs exist for all 13; only 6 follow the declared module
structure; R08/R13 live elsewhere with `.implemented` markers but wrong paths; R07/R09-R12 are
specs with no code, no test, no marker.

## 3. Adversaries (11 claimed) + orchestration

| Element | Claim | Status | Reality |
|---|---|---|---|
| 11 named failure-modes (false_authority, unbounded_exploration, concealed_failures, aesthetic_deception, overconfidence, premature_closure, spec_dilution, surface_mimicry, cognitive_overload, boundary_erosion, identity_drift) | named adversary set | 🔴 | **mapping does not exist** — code ships 10 internal-aliased adversary classes that are NOT reconciled to these 11 names |
| 10 adversary classes (`malakhim/adversarial/`) | generate attacks | 🟡 ×10 | `generate_attacks()` produce structured Attack objects, but **zero tests** and they are **not executed against live modules** (coordinator only classifies mock input) |
| `/adversarial-probe` CLI (11 parallel worktrees + tmux) | primary entrypoint | 🔴 | does not exist |
| `etzchaim probes --adversarial` | CLI | 🔴 | command not in CLI |
| nightly "run 11 probes" / end-to-end execution | wired into loop | 🔴 | no orchestrator; adversaries fire only reactively on anomaly detection |

Adversaries: substrate **partial**, every claimed *interface* (named set, CLI, orchestrator, tests) 🔴.

## 4. Auto-improve daemon — the flagship "Karpathy AutoResearch" loop

Central question: does it run end-to-end? **No.** Real entrypoint is `python daemon.py --task
auto-improve` → `daemon_tasks/exploration.py:207 task_auto_improve()`, which runs a **narrow inline
hypothesis loop** and stores accepted hypotheses in memory. The 7 claimed steps:

| Step | Claim | Status |
|---|---|---|
| 1 | read 24h failure traces (Sentry+logs) | 🔴 reads active goals from a DB, not failures |
| 2 | cluster by faculty/rectifier | 🔴 absent |
| 3 | generate ≤3 spec mutations via `improve-loop` subagent in Plan mode | 🔴 no subagent; generates domain hypotheses inline, not spec mutations |
| 4 | verify each via `verify-spec` subagent | 🔴 **subagent file does not exist**; accepted=True auto-stores, no gate |
| 5 | run 4557 tests + 11 probes | 🔴 no pytest call, no probe run |
| 6 | open PR tagged auto-improve | 🔴 zero git/gh calls; results are SSE events only |
| 7 | webhook → Telegram | 🔴 `_notify()` body is `pass` |
| — | entrypoint `etzchaim improve` | 🟡 no such CLI command; manual `python daemon.py` only |
| — | scheduler (nightly) | 🟡 launchd plist `PLIST_SRC` referenced but **file missing**; no GHA cron |
| — | `etzchaim_daemon/improve_loop.py ~630 lines` (per ARCHITECTURE) | 🔴 file does not exist (real code is the monolithic `daemon.py`, ~2.5k lines) |

Daemon: **a real cognitive loop, but the self-*improvement* contract (failure→mutate→verify→test→
ship) is shell.** It cannot currently improve+verify+ship anything autonomously.

## 5. Benchmark — does it measure "boosting the plugged-in AI"? No.

| Concern | MISSION claim | Reality | Status |
|---|---|---|---|
| Baselines | 4 (LLM, LangChain, AutoGen, Hermes) | 3 arms (raw, CoT, Etz); **no LangChain/AutoGen/Hermes** | 🔴 |
| Metrics | 8 cognitive-OS metrics (self_model_coherence, causal_depth, …) | measures 4 public NLP benches (TruthfulQA/HarmBench/XSTest/MMLU-Pro); **none of the 8 implemented** | 🔴 |
| Multi-LLM repro | 4 LLMs converge | single model hardcoded; no multi-provider harness | 🔴 |
| Etz cost/tokens | measured | **fabricated**: `est_cost=0.04×calls`, `350/400` tokens hardcoded | 🔴 |
| Stats machinery | — | Bonferroni paired-t + bootstrap CI + Cohen's d, 100 prompts/bench, sha256-cached | 🟢 |
| Judge | — | heuristic (needed 4 patch iterations to de-bias FR-markdown vs EN-short); external LLM-judge present but unrun | 🟡 |
| **Headline result** | "outperforms on 6/8, p<0.05" | own report: **"Etz beats raw Claude on no bench"** — reasoning −79pp, truthfulqa −35pp, harmbench −10pp, xstest ≈parity | 🔴 |

The benchmark is honest about its **negative result**, but it does not measure the mission's edge,
has no real baselines, fabricates Etz cost — and as run, it shows the wrapper *degrades* the host LLM.

## 6. Provider stack & model-string integrity (invariant #7)

| Element | Status | Reality |
|---|---|---|
| `etzchaim/llm/model_registry.py` as single source | 🟡 | registry is real & tested, but Sprint 1.B incomplete: `etzchaim/initiate.py:73-83` still hardcodes a 9-model `_CANONICAL_LLMS` dict (TODO at :71) |
| config-driven resolution | 🟢 | profiles resolve via config + provider-prefix stripping works |
| profile count | 🟢 (doc mismatch) | config ships **21** profiles; docs say 6 |
| hardcoded slug leaks | 🔴 | `initiate.py:73-83`, `benchmarks/arms.py:31`, `benchmarks/claude_cli.py:30`, `benchmarks/cache.py`, `benchmarks/token_tracker.py`, `benchmarks/judge.py:27` |
| `make check-model-leaks` gate | 🟡 blind | scans only `etzchaim/*.py` and **exempts `initiate.py`**; never sees `benchmarks/` or top-level files → leaks slip through |
| no-Anthropic-key fallback | 🔴 | daemon would crash (`select_claude_backend` raises) if `claude_max` active without key — breaks invariant #7 |

## 7. Docs vs reality — the governing contract

| Claim (AGENTS.md / ARCHITECTURE.md) | Reality | Status |
|---|---|---|
| 1696 primary-source specs, E1-E6 | ~250 (31 spec files + 220 corpus files; 57 EC-* IDs cited) — off ~6.7× | 🔴 |
| 1388-test suite <3s | 4557 tests; no time gate in CI | 🟡 |
| 6 LLM profiles | 21 | 🟡 |
| `etzchaim/{faculties,rectifiers,adversaries,sentiers,specs,daemon}/` layout | none exist — real code is flat top-level modules | 🔴 |
| top-level `agents/ skills/ commands/ hooks/ evals/` | all missing | 🔴 |
| MCP server `etzchaim_mcp` (15 tools, Sprint 5) | zero implementation, no `.mcp.json` | 🔴 |
| 6 `.claude/rules/*.md` discipline files | none exist (`.claude/` = only `commands/handoff.md`) | 🔴 |
| 5 subagents (triage, verify-spec, improve-loop, spec-auditor, doctor) | only `doctor`/`loop` exist as Python, none as agent defs | 🔴 |
| 8 slash commands (`/diagnose-faculty` …) | 0 implemented | 🔴 |
| `make doctor` / `make verify-bidirectional` / `make check-public-surface` | not Makefile targets (doctor is a CLI subcmd; public-surface is a bare script) | 🟡 |

### The 8 invariants — enforcement reality
1. channel-only aggregate writes → 🔴 no hook, no `make check-aggregates`
2. circuit breaker on all external calls → 🟡 breaker exists, not on every path
3. plan-mode + verify-spec for spec mutations → 🔴 **verify-spec absent ⇒ unenforceable**
4. E1-E6 citations + `make verify-bidirectional` → 🟡 labels in specs, no audit target
5. test budget <3s for 1388 tests → 🟡 4557 tests, no time gate
6. one-shot installable → 🟢 pyproject + devcontainer present
7. provider-agnostic / no hardcoded models → 🟡 registry exists but leaks persist + blind gate
8. public-surface neutrality → 🟢 gate exists and currently **passes (EXIT 0)**

## 8. The 3 largest gaps (MISSION ambition vs code)

1. **The edge is unproven — and refuted by the repo's own benchmark.** North-star #2 (beat 4
   baselines on 6/8 metrics, p<0.05, across 4 LLMs) is unmet on every axis: 3 arms not 4 baselines,
   4 public NLP benches not the 8 cognitive-OS metrics, one hardcoded model not 4, fabricated Etz
   cost — and the existing run concludes the wrapper makes the host LLM *worse* (−79/−35/−10pp).
   "Boost the plugged-in AI" is currently contradicted by the only evidence in the repo.

2. **The self-improvement loop — the flagship — is not closed.** The nightly auto-improve daemon
   runs a narrow inline hypothesis loop; read-failures / cluster / spec-mutate / verify / test / PR
   / notify are shell. The verify-spec gate the loop (and the mission's own "verify before done"
   rule) depends on does not exist; there is no scheduler. The system cannot autonomously improve,
   verify, and ship — which is its definitional claim over "generic RAG/prompt-chain".

3. **The governing contract is substantially fictional.** AGENTS.md/ARCHITECTURE.md ("single source
   of truth") describe a neutral, layered, tool-rich system that largely isn't there: ~250 specs not
   1696, 4557 tests not 1388, flat modules not `etzchaim/faculties/…`, 0 of 8 slash commands, no
   MCP server, no `.claude/rules`, 5 documented subagents absent. Two critical invariants (1, 3) are
   unenforceable. Agents are steered by a map that doesn't match the territory.

> Caveat: 82/151 elements are genuinely real — the cognitive faculties are the solid core. The
> hollowness is concentrated in the *evaluation story*, the *autonomous loop*, and the *docs*.
