# Roadmap

## Shipped in v0.1.0

- Sprint 9 — Probe orchestrator pilot (2 active probes, 12 TDD tests)
- Sprint 10 Phase α Batch 1 — 3 rectifiers (HIGH confidence)
- Sprint 10 Phase B — generalized specification bridge (1696 items)
- Sprint 10 Phase C — probe orchestrator 3-mode rectification (observe / suggest / act)
- Sprint 10 Phase D — persistent trace coefficient (`faculty_reshimot`)
- Sprint 10 Phase E — coupling refactor (canonical schema + unified factory)
- Sprint 10 Phase G — Publication polish

## Shipped in v0.2.x

- Container-first install (Docker Compose)
- Multi-LLM provider support (LiteLLM)
- Specification corpus shipped via package
- Daemon idempotence audit + trajectory tooling
- Benchmark v2 with bilingual judges, 1200 invocations

## Sprint 11 — Probe orchestrator extension Batch 2

- Transpose 7 additional rectifiers (MEDIUM confidence) from primary sources.
- Extend probe orchestrator to cover the 7 new rectifiers.
- Scope : approximately 49 new specification items.

## Sprint 11+ — Batch 3 LOW

- 3 remaining rectifiers. Some require philological work on alternate editions of primary sources.

## Sprint 12 — Source extension

- Transpose additional source sections.
- Integrate with existing corpus via `see_also` links.

## Sprint 13 — Pre-extension foundational corpus

- Important for structural context.

## Sprint 14 — Cross-source coherence

- Tests for convergences and divergences across primary sources.

## Adversarial counterpart (deferred)

The design review for an adversarial counterpart to the probe orchestrator found no direct attestation in the primary sources. Possible alternative scopes to be decided :

- Channel failure detector (4 modes : closed / misoriented / insufficient receiver / exposed back) — derivation from authoritative reading.
- Integration with existing adversarial tests (`malakhim/adversarial/`) without a new engine.
- Skip entirely ; the existing qualification testing framework already covers adversarial validation.

## Longer term

- Complete implementation of all 10 cognitive faculty modules with 4-level qualification tests.
- Synthesis bridge (cross-faculty insight ↔ causal reasoning).
- Full daemon integration for all hourly and daily rectification cycles.
- Academic paper describing the probe orchestrator auto-rectification mechanism.

## v1.0 milestones

- arXiv paper "A Cognitive Operating System for Structurally-Evolving LLM Agents"
- Cognitive OS Evaluation Suite (8 metrics) outperforms baselines (LLM seul, LangChain, AutoGen) on 6/8 with p<0.05, reproducible across 4 LLMs
- Repo public stable, pip + docker
- Discord 100+ members, 3 external contributors, 1 third-party reproduction of the benchmark

## Sprint cadence

Sprints are not time-boxed. Each Sprint ends when its DoD (Definition of Done) is met and all non-regression tests are green. Historical cadence has been one Sprint per 1-2 weeks of active work.
