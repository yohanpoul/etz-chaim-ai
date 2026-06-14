"""The three arms — A0 bare / A1 bare+CHANGELOG / A2 bare+gate.

Isolation that makes the A1-vs-A2 contrast clean:
    A0  bare prompt, no memory channel at all.
    A1  bare prompt + a CHANGELOG of failed approaches injected INTO CONTEXT (advisory,
        the native pattern). No gate.
    A2  bare prompt (identical to A0) + an EXTERNAL gate on the persistent belief store.
        The gate is A2's ONLY memory channel — failures are NOT put back in the prompt.
        This isolates "enforced structured gate" from "advisory context memory".

Each session is a fresh model context (the wipe). For A1 the CHANGELOG persists across
the wipe; for A2 the Postgres belief store persists across the wipe. The store/changelog
surviving while the model context resets is the whole point of the test.

DECISION (A) kill-test framing: A2 keys on an EXACT TAG via a stipulated-perfect
classifier (task.classify_approach) — the UPPER BOUND of enforcement. See
gating_harness/__init__.py.
"""

from __future__ import annotations

import contextlib
import os

from gating.core import gate_intention

from . import provider
from .metrics import SessionRecord
from .task import balanced_brackets as _default_task

# Default task keeps the smoke byte-stable; the experiment passes task=... explicitly.
task = _default_task


@contextlib.contextmanager
def _gating(on: bool = True):
    """Set ETZ_GATING for the duration. on=True is the live gate; on=False is the
    ABLATION (gate_intention passes through) used by the experiment's A2-ablation arm."""
    prev = os.environ.get("ETZ_GATING")
    os.environ["ETZ_GATING"] = "on" if on else "off"
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("ETZ_GATING", None)
        else:
            os.environ["ETZ_GATING"] = prev


_SYSTEM = (
    "You are a careful Python engineer. Answer ONLY in the requested format: a single "
    "'APPROACH:' line, then one ```python code block. No prose outside that."
)


def _generate(
    extra_context: str | None = None, *, task=_default_task, gen=None
) -> provider.ModelCall:
    # gen is the model-call callable: default = local Ollama (smoke); experiment passes
    # provider.chat_claude_cli (Haiku). Both take messages and return a ModelCall.
    gen = gen or provider.chat
    user = task.PROMPT if not extra_context else f"{extra_context}\n\n{task.PROMPT}"
    return gen(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": user}]
    )


def _parse(call: provider.ModelCall, *, task=_default_task) -> tuple[str, str, str | None]:
    declared = task.extract_declared_approach(call.text)
    code = task.extract_code(call.text)
    # CODE-FIRST matching: robust even when the model omits the 'APPROACH:' line.
    approach_key = task.infer_approach_key(declared, code)
    return declared, approach_key, code


def _changelog_block(entries: list[str]) -> str | None:
    if not entries:
        return None
    body = "\n".join(f"- {e}" for e in entries)
    return (
        "## CHANGELOG — failed approaches (do NOT repeat these)\n"
        f"{body}\n"
        "Pick an approach that is not in the list above."
    )


# --------------------------------------------------------------------------- #
# A0 — bare, no memory
# --------------------------------------------------------------------------- #


def run_a0(sessions: int, *, task=_default_task, gen=None) -> list[SessionRecord]:
    records: list[SessionRecord] = []
    for i in range(sessions):
        call = _generate(task=task, gen=gen)
        declared, key, code = _parse(call, task=task)
        oracle = task.run_oracle(code)
        records.append(
            SessionRecord(
                arm="A0",
                session_idx=i,
                declared_approach=declared,
                approach_key=key,
                oracle_passed=oracle.passed,
                hit_trap=oracle.hit_trap,
                prompt_tokens=call.prompt_tokens,
                completion_tokens=call.completion_tokens,
                generations=1,
                memory_had_deadend=False,  # no memory channel
                committed_refuted=False,   # nothing to contradict
            )
        )
    return records


# --------------------------------------------------------------------------- #
# A1 — bare + CHANGELOG (advisory, in context)
# --------------------------------------------------------------------------- #


def run_a1(
    sessions: int,
    *,
    task=_default_task,
    gen=None,
    changelog_noise: list[str] | None = None,
) -> list[SessionRecord]:
    records: list[SessionRecord] = []
    # changelog_noise = N unrelated prior failures seeding A1's log (discriminant regime,
    # Risk #1): stresses passive recall in a realistic noisy history. Default empty -> smoke
    # unchanged. Noise entries MUST NOT contain task.DEADEND_APPROACH (caller's contract).
    changelog: list[str] = list(changelog_noise or [])
    for i in range(sessions):
        knew = any(task.DEADEND_APPROACH in e for e in changelog)
        call = _generate(_changelog_block(changelog), task=task, gen=gen)
        declared, key, code = _parse(call, task=task)
        oracle = task.run_oracle(code)
        if oracle.hit_trap or not oracle.passed:
            changelog.append(
                f"approach '{key}' fails cases {oracle.failed_cases or ['(wrong)']}"
            )
        records.append(
            SessionRecord(
                arm="A1",
                session_idx=i,
                declared_approach=declared,
                approach_key=key,
                oracle_passed=oracle.passed,
                hit_trap=oracle.hit_trap,
                prompt_tokens=call.prompt_tokens,
                completion_tokens=call.completion_tokens,
                generations=1,
                memory_had_deadend=knew,
                committed_refuted=(knew and key == task.DEADEND_APPROACH),
            )
        )
    return records


# --------------------------------------------------------------------------- #
# A2 — bare + EtzChaim gate on the persistent store
# --------------------------------------------------------------------------- #


def _a2_store_knows_deadend(mem, *, task=_default_task, gating: bool = True) -> bool:
    """Does the persistent store already hold a FACT that refutes the dead-end?

    Uses the gate itself (the wire under test) as the probe: a rejection means a
    committed refutation is present and re-readable after the context wipe. Under the
    ablation (gating=False) the gate passes through, so this reports False.
    """
    with _gating(gating):
        probe = gate_intention(
            mem, goal="probe", approach_key=task.DEADEND_APPROACH, domain=task.TASK_ID
        )
    return probe.allowed is False


def run_a2(
    sessions: int, mem, *, task=_default_task, gen=None, gating: bool = True
) -> list[SessionRecord]:
    # gating=False is the ablation arm: the store still accumulates dead-ends, but the gate
    # is disabled (passthrough), so any re-attempt suppression must vanish -> proves the wire.
    records: list[SessionRecord] = []
    for i in range(sessions):
        knew = _a2_store_knows_deadend(mem, task=task, gating=gating)

        # Generate, then gate the DECLARED intention (set_intention point).
        call = _generate(task=task, gen=gen)
        declared, key, code = _parse(call, task=task)
        generations = 1
        gate_rejected = False

        with _gating(gating):
            decision = gate_intention(
                mem, goal=declared or task.PROMPT, approach_key=key, domain=task.TASK_ID
            )
        if not decision.allowed:
            # Gate caught a re-attempt of a refuted approach -> force a pivot.
            gate_rejected = True
            note = (
                f"REJECTED by memory gate: approach '{declared}' was previously proven "
                f"wrong on '{task.TRAP_CASE}'. Use a fundamentally different approach."
            )
            call2 = _generate(note, task=task, gen=gen)
            declared, key, code = _parse(call2, task=task)
            generations = 2
            call = provider.ModelCall(  # accumulate tokens across both generations
                text=call2.text,
                prompt_tokens=call.prompt_tokens + call2.prompt_tokens,
                completion_tokens=call.completion_tokens + call2.completion_tokens,
                model=call2.model,
                provider=call2.provider,
            )

        oracle = task.run_oracle(code)

        # Record the dead-end into the persistent store for the NEXT session.
        if oracle.hit_trap:
            mem.remember(
                content=(
                    f"approach {key} fails on {task.TASK_ID} — trap '{task.TRAP_CASE}'"
                ),
                source_sephirah="external",
                confidence=0.95,  # >= 0.9 -> EpistemicStatus.FACT
                domain=task.TASK_ID,
                tags=["deadend", f"approach:{key}"],
            )

        records.append(
            SessionRecord(
                arm="A2",
                session_idx=i,
                declared_approach=declared,
                approach_key=key,
                oracle_passed=oracle.passed,
                hit_trap=oracle.hit_trap,
                prompt_tokens=call.prompt_tokens,
                completion_tokens=call.completion_tokens,
                generations=generations,
                gate_rejected=gate_rejected,
                memory_had_deadend=knew,
                # A contradiction = committed the refuted approach despite the gate
                # knowing it was refuted (i.e. the gate failed to prevent re-commit).
                committed_refuted=(knew and key == task.DEADEND_APPROACH),
            )
        )
    return records
