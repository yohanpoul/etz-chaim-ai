---
public_name: CognitiveOSEvaluationSuite
module_path: etzchaim/eval/cognitive_os_suite.py
spec_id: SPEC-EVAL-001
version: 0.1.0
status: draft
validated_by: []
---

# Cognitive OS Evaluation Suite

## Purpose

8 metrics measuring whether plugging a frontier LLM into Etz Chaim AI yields
a structurally distinct agent vs. the baseline LLM alone or other agent
frameworks (LangChain, AutoGen, generic self-improving loops).

Hypothesis : LLM + Etz Chaim AI outperforms the four named baselines on
**6/8 metrics with p<0.05**, with the same delta structure reproducible
across **4 LLMs** (Claude Opus 4.7, GPT-5.5, Llama 3.5, Gemini 3).

## Public API

```python
class CognitiveOSEvaluationSuite:
    def __init__(self, agent: AgentUnderTest, dataset_root: Path) -> None: ...

    def run(self, runs: int = 3) -> EvaluationReport:
        """Run all 8 metrics with `runs` independent passes. Returns
        statistical summary and per-metric breakdown."""
```

## The 8 metrics

| # | Metric | Test | Dataset |
|---|--------|------|---------|
| 1 | `self_model_coherence` | 100 self-knowledge questions; score consistency between consecutive sessions | `datasets/self_knowledge_100.jsonl` |
| 2 | `causal_depth` | 50 causal-reasoning problems (cause-effect, confounder, counterfactual); score depth | `datasets/causal_50.jsonl` |
| 3 | `memory_consistency` | 10 sessions × 20 facts each; score recall after 1, 7, 30-day decay | `datasets/memory_sessions.jsonl` |
| 4 | `contradiction_detection_rate` | 200 statement pairs (some contradictory, some compatible); precision + recall | `datasets/contradiction_200.jsonl` |
| 5 | `failure_insight_conversion_rate` | 50 failure scenarios; rate of policy adjustment turn N+1 | `datasets/failures_50.jsonl` |
| 6 | `self_rectification_rate` | 13 synthetic failure patterns injected; rate of auto-correction | runtime injection |
| 7 | `sequential_consolidation_integrity` | static check; faculty `n` never advances before `n-1` consolidated | runtime invariant |
| 8 | `persistent_trace_coefficient` | 100 cycles; verify plateau ≈ 0.3 and decay ≈ 5%/cycle | runtime measurement |

## Baselines

- LLM alone (no framework)
- LLM + LangChain (`langchain.agents.AgentExecutor`)
- LLM + AutoGen (`autogen.AssistantAgent` + `UserProxyAgent`)
- LLM + Hermes self-evolution loop (`gepa-ai/gepa` standalone)

## Type signatures

```python
@dataclass
class MetricResult:
    name: str
    value: float
    n_runs: int
    std: float
    baselines: dict[str, float]  # baseline_name -> value
    p_value: float

@dataclass
class EvaluationReport:
    agent_id: str
    runs: int
    metrics: list[MetricResult]
    overall_significant: bool  # 6/8 with p<0.05
    timestamp: str
```

## Reproducibility

- Datasets versioned in `datasets/` with content hash.
- `EvaluationReport` includes Python version, model versions, dataset hashes,
  random seeds.
- Re-running the suite with the same inputs must produce statistically
  equivalent reports (same significance verdict).

## Tests

`tests/test_cognitive_os_suite.py` must cover :

- Each metric runs in isolation with a stub agent and produces a `MetricResult`.
- `EvaluationReport.overall_significant` returns True iff ≥ 6/8 metrics
  have p < 0.05.
- Reproducibility : two runs with same seed produce identical reports.
- Multi-LLM extension : the suite accepts any `AgentUnderTest` implementing
  the minimal interface.

## Non-goals

- This module does not train models.
- It does not implement the faculties or configurations under test; it
  measures their behavior end-to-end.
- It does not run continuously in the daemon; it is invoked by
  `daemon_tasks/edge_validation.py` weekly or on demand.
