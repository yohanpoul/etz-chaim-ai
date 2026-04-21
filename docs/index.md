# Etz Chaim AI

*Twelve cognitive capabilities. Twelve distinct failure signals. One watcher that can fix them.*

## Why this exists

When a standard AI system fails, you get one error : *the model hallucinated / was biased / repeated itself*. You cannot tell which cognitive capability actually broke, and fixing it usually means re-prompting and hoping.

Etz Chaim AI splits cognition into 12 explicit modules — each with its own tests, tunable parameters, and persistent state. A built-in watcher monitors these modules and can detect drift, name it, and apply corrections.

## What is in v0.1.0

| Component | Role | Tests |
|:----------|:-----|:-----:|
| `bridge/` | loads the 1696-item specification corpus into code | 16 |
| `mazalengine/` | watcher + rectifier (observe / suggest / act) | 25 |
| `partzufim/` | 4 composition layers + persistent learning trace | 150+ |
| `sifrei_yesod/` | primary-source specification corpus (YAML) | 10+ |

## Start here

- [Getting started](getting_started.md) — install and run your first self-rectification cycle.
- [Architecture](architecture.md) — how the pieces fit together.
- [Origin](origin.md) — why these 12 modules and not another set.

## Project scope

This project **is** :

- An AI architecture with capability-level failure diagnostics.
- A set of small autonomous Python modules (~500 LoC each), each adding one cognitive capability.
- A corpus of primary sources transposed with philological care and epistemic labeling (E1–E6).

This project **is not** :

- A generic framework for orchestrating arbitrary LLM agents.
- A trained model (we call Claude / Ollama / OpenAI under the hood).
- A general-purpose reference for Kabbalistic studies.
