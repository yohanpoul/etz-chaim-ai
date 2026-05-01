# Etz Chaim AI

*Ten cognitive faculties. Ten distinct failure signals. One probe orchestrator that can fix them.*

## Why this exists

When a standard AI system fails, you get one error : *the model hallucinated / was biased / repeated itself*. You cannot tell which cognitive faculty actually broke, and fixing it usually means re-prompting and hoping.

Etz Chaim AI splits cognition into 10 explicit faculties — each with its own tests, tunable parameters, and persistent state. A built-in probe orchestrator monitors these faculties and can detect drift, name it, and apply corrections.

## What is in v0.1.0

| Component | Role | Tests |
|:----------|:-----|:-----:|
| `bridge/` | loads the 1696-item specification corpus into code | 16 |
| `probes/` | probe orchestrator + rectifier (observe / suggest / act) | 25 |
| `configurations/` | 6 composition layers + persistent learning trace | 150+ |
| internal corpus | primary-source specification (YAML) | 10+ |

## Start here

- [Getting started](getting_started.md) — install and run your first self-rectification cycle.
- [Architecture](architecture.md) — how the pieces fit together.
- [Advanced](advanced.md) — opt-in : the structural framework that inspired the architecture.

## Project scope

This project **is** :

- An AI architecture with capability-level failure diagnostics.
- A set of small autonomous Python modules (~500 LoC each), each adding one cognitive capability.
- A specification corpus transposed with rigorous care and epistemic labeling (E1–E6).

This project **is not** :

- A generic framework for orchestrating arbitrary LLM agents.
- A trained model (we call Claude / Ollama / OpenAI under the hood).
- A general-purpose reference for any specific intellectual tradition.
