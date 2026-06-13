# Etz Chaim AI — Direction (Phase 1)

> Where does wrapping an LLM in EtzChaim augment it *measurably*, and via which real faculties?
> Grounded on the Phase-0 audit (docs/STATE_MAP.md) — built on what exists, not what docs promise.
> Status: PROPOSED (ADR-0009). The project currently sits on a pivot-trigger edge; this direction is
> the escape route, conditional on the Phase-2 test below.

## 1. Answer in one line
Yes — but only for **long-horizon, multi-session, context-wiped agentic work**, where the edge is
**persistent, contradiction-aware self-state that actively gates the loop** (continue / stop /
reject-re-attempt). NOT for single-shot factual or safety tasks, where the layer can only add noise.

## 2. Why the current benchmark degrades the host
The v2 benchmark is single-shot factual + safety (near model ceiling). It has no state and no "self"
for the faculties to act on, so the layer adds latency, tokens, format mismatch (MMLU −79pp = essays
without a letter, not a reasoning deficit), and — honestly — speculation: the hypothesis-generating
faculties manufacture novel content where the task rewards terse recall. The −35pp on factual QA is
an upper bound (judge artifact, per the report's own caveat) but the sign is structurally expected.
Degradation is **task-class specific**, not universal.

## 3. The bar to beat (native Claude, 2026)
Scheduling/looping (`/goal`, `/loop`, `/schedule`), verify-against-oracle, parallelism (worktrees,
`/batch`), and unstructured cross-session memory (a `CHANGELOG.md` with "failed approaches and why")
are **native**. So "memory" and "keep working toward a goal" are not differentiators. The only
defensible space is **structured metacognition** the native tools do not provide.

## 4. Candidate directions and why three were set aside
| Dir | Idea | Why not (collapses to) |
|---|---|---|
| D1 | calibrated abstention across sessions | conformal prediction / Brier scaling; self-verification is circular; no risk-coverage measured |
| D3 | learning verify-loop | native `/goal` + rubric; the learning hook (failure-mining) is unbuilt |
| D4 | drift monitor for long runs | Stop-hook threshold poll; integrator absent; goal-tracking faculty only partial |
| **D2** | **contradiction-aware belief lifecycle, multi-session** | **chosen — see §5** |

All four, as the code stands today, reduce to a generic primitive — because the faculties are real
but **not wired to gate the live loop**. That missing wire is the work. (An independent adversarial
collapse-test returned COLLAPSES on all four *as built*, for this same shared reason.)

## 5. Chosen direction
**Persistent contradiction-aware self-state that actively gates a long-horizon multi-session loop.**
- Real faculties that deliver it: **epistememory** (`contradict`/`deprecate`/`verify`/`mature` — a
  belief lifecycle, not similarity retrieval), **dissensuengine** (`measure_divergence`/
  `synthesize_or_dissent`), with **intentkeeper** as the goal carrier and **selfmap.calibrate** as
  the measurement instrument.
- What still has to exist to test it: the **synthesis/gating layer** — query the contradiction graph
  at `set_intention` and `submit_conclusion`, and reject/flag re-entry of refuted approaches across
  context wipes. (Today these entry points treat each session as epistemically fresh.)
- The one sentence that must hold (else pivot): RAG retrieves and appends; **the edge is active
  gating — the agent is blocked from re-committing a belief it already refuted.**

## 6. Minimal falsifiable test (Phase 2 seed)
Domain (decided, §8): **code/debug against a reference oracle.** A multi-session, **context-wiped**
implementation/debugging task with a reference implementation as the ground-truth oracle and
identifiable dead-ends (approaches the oracle proves wrong). Arms:
- **A0** bare Claude, fresh context each session (no external memory).
- **A1** bare Claude + `CHANGELOG.md` (the native pattern) — **the baseline to beat**.
- **A2** Claude + EtzChaim gating: at `set_intention`/`submit_conclusion`, query
  `epistememory`+`dissensuengine`; auto-reject re-attempts of deprecated/refuted approaches;
  flag contradictions.

Metrics per task across N sessions: (1) **dead-end re-attempt rate**, (2) **self-contradiction rate**,
(3) iterations/tokens to oracle pass, (4) final correctness.
- **Proof:** A2 significantly < A1 on (1)+(2) at equal/better (3)+(4), and an **ablation** (disable
  the `contradict`/`deprecate` gating) erases the gain → the gating wire is the cause.
- **Refutation (null → PIVOT):** A2 ≈ A1 → the lifecycle adds nothing beyond a markdown log.

Adversary's precise null-probe: Session A creates + deprecates "approach X fails" as a committed
fact; Session B `set_intention("try X again")` must auto-reject or warn with the prior fact — if it
returns nothing, it is raw retrieval, not gating.

## 7. Risk #1
**The native CHANGELOG baseline (A1) is already good enough.** A frontier model + a good markdown
"failed approaches" log may capture most of the value at ~0 cost, and capable models need less
scaffolding over time. If A2 cannot significantly beat **A1, not just A0**, the edge does not exist.
(Secondary risk: defining "dead-end"/"contradiction" objectively enough to count without the judge
bias that already burned the v2 benchmark — the reference-oracle domain is chosen partly to make
these labels objective.)

## 8. Harness domain — decided
- **(a) Code/debug against a reference oracle — CHOSEN.** Cleanest ground truth, objective dead-end
  and contradiction labels (the oracle decides), matches the long-running-agent pattern. Accepted
  trade-off: it temporarily frames EtzChaim as a "coding-memory layer" — acceptable for a mechanism
  proof.
- **(b) Open-ended research/analysis across sessions — DEFERRED, conditional.** Pursued **only if
  (a) first validates the gating mechanism.** This is where the broader identity lives, but its
  dead-end/contradiction labels are subjective, so it must not be the mechanism's first test.
- **(c) Synthetic task with injected known dead-ends — optional sanity sub-check** alongside (a) to
  isolate the gating logic from domain noise.
```
