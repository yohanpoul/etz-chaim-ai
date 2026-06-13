"""External code/debug task: ``is_balanced(s)`` for `()[]{}`, with a reference oracle.

This is NOT etz-chaim-ai development — it is a standalone textbook problem chosen
because its ground truth is a deterministic pytest-style oracle (no LLM judge) and it
has ONE clean, objective dead-end:

    THE DEAD-END ("count") — verify only that each bracket type has equal opens and
    closes, ignoring ordering/nesting. It passes trivial cases but FAILS the interleaved
    trap "([)]" (one of every pair, yet badly nested). "Dead-end" is therefore an
    OBJECTIVE, oracle-derived label (fails TRAP_CASE), not a judge opinion — which is
    exactly the property DIRECTION §7 (Risk #1 secondary) requires.

    THE CORRECT APPROACH ("stack") — push openers, pop+match on closers, reject if the
    stack is non-empty at the end.

``classify_approach`` maps a declared approach (or code) to one of {count, stack,
unknown}. For decision (A) this classifier is STIPULATED PERFECT — that perfect
identification is the gate's upper bound (see gating_harness/__init__.py).
"""

from __future__ import annotations

import signal
import threading
from dataclasses import dataclass, field

TASK_ID = "balanced_brackets"

# The objective dead-end the oracle proves wrong.
DEADEND_APPROACH = "count"
CORRECT_APPROACH = "stack"

# The single case that discriminates the dead-end from the correct approach:
# perfectly balanced *counts*, but illegally interleaved nesting.
TRAP_CASE = "([)]"

# (input, expected) — the reference oracle. Ground truth, no model in the loop.
ORACLE_CASES: list[tuple[str, bool]] = [
    ("", True),
    ("()", True),
    ("()[]{}", True),
    ("([{}])", True),
    ("{[()]}", True),
    ("(]", False),
    (TRAP_CASE, False),  # the trap: counts balanced, order wrong
    (")(", False),
    ("(((", False),
    ("([]", False),
]

PROMPT = (
    "Write a Python function `is_balanced(s: str) -> bool` that returns True iff every "
    "bracket in `s` is correctly matched AND correctly nested, for the three bracket "
    "types (), [], {}. Examples: '([{}])' -> True ; '([)]' -> False ; '(]' -> False.\n\n"
    "Respond in exactly this format:\n"
    "APPROACH: <one short line naming your approach>\n"
    "```python\n<your implementation>\n```\n"
)


@dataclass
class OracleResult:
    """Outcome of running a candidate against the reference oracle."""

    passed: bool
    failed_cases: list[str] = field(default_factory=list)
    hit_trap: bool = False  # failed TRAP_CASE specifically -> the dead-end signature
    error: str | None = None


# --------------------------------------------------------------------------- #
# Parsing the model output
# --------------------------------------------------------------------------- #


def extract_declared_approach(text: str) -> str:
    """Pull the 'APPROACH: ...' line; empty string if absent."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("APPROACH:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def extract_code(text: str) -> str | None:
    """Return the first fenced python block (or any fenced block) if present."""
    fences = text.split("```")
    if len(fences) < 3:
        return None
    block = fences[1]
    # drop a leading language tag like "python\n"
    if "\n" in block:
        first, rest = block.split("\n", 1)
        if first.strip().lower() in {"python", "py", ""}:
            return rest
    return block


def classify_approach(text: str) -> str:
    """Deterministically map declared-approach text (or code) to an approach key.

    STIPULATED PERFECT for decision (A): treat this as a ground-truth identifier of
    'same approach'. Real deployment needs fuzzy/semantic matching; that gap is exactly
    why a win here is an UPPER BOUND, not validation.
    """
    t = (text or "").lower()
    stack_signals = ("stack", "push", "pop", "append", "lifo", "last-in", "last in")
    count_signals = ("count", "tally", "number of", "equal number", "same number",
                     "occurrence", "frequency", "how many")
    if any(s in t for s in stack_signals):
        return CORRECT_APPROACH
    if any(s in t for s in count_signals):
        return DEADEND_APPROACH
    return "unknown"


# --------------------------------------------------------------------------- #
# Running the candidate against the oracle (sandboxed + time-bounded)
# --------------------------------------------------------------------------- #

_SAFE_BUILTINS = {
    "len": len, "range": range, "list": list, "dict": dict, "set": set,
    "str": str, "int": int, "bool": bool, "enumerate": enumerate, "zip": zip,
    "reversed": reversed, "sorted": sorted, "abs": abs, "min": min, "max": max,
    "all": all, "any": any, "map": map, "filter": filter, "tuple": tuple,
    "True": True, "False": False, "None": None,
}


class _Timeout(Exception):
    pass


def _run_one(fn, value: str, timeout_s: float = 2.0) -> bool:
    """Call fn(value) with a wall-clock timeout (SIGALRM on the main thread).

    A timeout (e.g. catastrophic backtracking) counts as a failed case. SIGALRM only
    works on the main thread; off-main we run without the alarm (the count/stack
    candidates do not hang, so this only loses the pathological-regex guard there).
    """
    use_alarm = threading.current_thread() is threading.main_thread()
    if use_alarm:
        def _handler(signum, frame):  # noqa: ARG001
            raise _Timeout()

        old = signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        return bool(fn(value))
    finally:
        if use_alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)


def run_oracle(code: str | None) -> OracleResult:
    """Compile + run a candidate ``is_balanced`` against ORACLE_CASES."""
    if not code or not code.strip():
        return OracleResult(passed=False, error="no code extracted")

    ns: dict = {"__builtins__": _SAFE_BUILTINS}
    try:
        # 're' is the one stdlib a regex-style solution might want; expose read-only.
        import re as _re

        ns["re"] = _re
        exec(code, ns)  # noqa: S102 — controlled local task, restricted builtins
    except Exception as e:  # noqa: BLE001
        return OracleResult(passed=False, error=f"compile/exec error: {e!r}")

    fn = ns.get("is_balanced")
    if not callable(fn):
        return OracleResult(passed=False, error="is_balanced not defined")

    failed: list[str] = []
    hit_trap = False
    for value, expected in ORACLE_CASES:
        try:
            got = _run_one(fn, value)
        except _Timeout:
            got = None  # timeout -> failed case
        except Exception:  # noqa: BLE001
            got = None
        if got != expected:
            failed.append(repr(value))
            if value == TRAP_CASE:
                hit_trap = True
    return OracleResult(passed=not failed, failed_cases=failed, hit_trap=hit_trap)
