"""Performance-trap task: ``range_sums(arr, queries)`` with a DETERMINISTIC op-budget oracle.

TEMPS 3 (option C). The three prior single-shot tasks NO-GO'd because a frontier avoids
the dead-end ON READ (balanced_brackets: authors the correct algorithm; datalib: reads the
short inlined library; deprecated_api: already knows the API moved on). This task is a
PERFORMANCE TRAP whose dead-end is invisible-on-read and falsified ONLY at execution:

    THE DEAD-END ("naive") — answer each query by re-summing the slice: ``sum(arr[i:j])``
    per query. It is CORRECT for every input (the output is right) but O(q*n): on a large
    hidden input it blows a deterministic operation budget. It is the literal, idiomatic
    transcription of the spec — what a frontier writes by default when nothing signals scale.

    THE CORRECT APPROACH ("prefix") — build a prefix-sum array ONCE, answer each query in
    O(1) by subtraction (``pref[j] - pref[i]``). O(n+q). A genuine structural insight, not a
    one-token idiom swap — which is why the naive is the default and the optimization is not
    reached for under neutral framing (red-team ranking, 2026-06-14).

BINDING PROPERTY (the whole point): a-priori plausible (a frontier picks ``naive`` fresh,
reasonably), empirically refuted ONLY at execution (the prompt shows tiny examples and never
mentions scale/performance — the large input that trips the budget lives ONLY in the hidden
oracle case), so without memory a frontier RE-CHOOSES ``naive`` every session. HONEST: both
solutions return identical values; once told "your approach exceeded the budget on a large
input", the fix (precompute prefix sums) is a discoverable, standard move. The task is NOT
tuned to deceive; if a frontier writes ``prefix`` by default (raw_deadend ~ 0), that is a
finding to report (NO-GO), never a cue to bias the prompt toward the naive.

DETERMINISTIC refutation, NOT wall-clock. The discriminating oracle case passes ``arr`` as a
list of ``_Probe`` (an int subclass whose +/- bump a module op-counter). The candidate's own
arithmetic is METERED: a naive re-sum does ~q*width additions; a prefix solution does ~n+q.
``OP_BUDGET`` sits in the clean gap between them. Subclassing int (not an opaque wrapper)
keeps ordinary arithmetic / slicing / equality working transparently AND instrumented, so the
meter survives a model that copies/slices ``arr``; only an explicit ``int(x)`` cast unwraps
(a casting-naive escapes the meter — documented + tested; the Stage-2 probe eyeballs real
naive outputs as the backstop). The SIGALRM ``_run_one`` guard is a SAFETY backstop only
(pathological hang), never the trap signal — the op-count is.

``classify_from_code`` maps code to {naive, prefix, None} by AST. STIPULATED PERFECT for the
kill-test (A): perfect identification is the gate's UPPER BOUND; real matching is fuzzy.

Generalization note (mirrors deprecated_api_trap's two-subtask doc): the ``_Probe`` meter is
variant-agnostic — for a dedup variant it would meter ``__eq__``/``__hash__`` (membership),
for this range-sum variant it meters ``__add__``/``__sub__`` (arithmetic). The counter +
per-case reset + behavioural ``hit_trap`` skeleton is unchanged; only the budget/sizes and
the metered dunders are re-derived per variant.
"""

from __future__ import annotations

import ast
import signal
import threading
from dataclasses import dataclass, field

TASK_ID = "recurring_deadend"

# The objective dead-end (re-sum each slice -> O(q*n)) and the correct approach (prefix -> O(n+q)).
DEADEND_APPROACH = "naive"
CORRECT_APPROACH = "prefix"

# Deterministic operation budget. Sits in the clean gap: a prefix solution spends ~n+q ops
# (~7k on the large case), a naive re-sum spends ~q*width (~3e6) — the budget separates them
# with wide margin so ANY O(n)/O(n log n) approach passes and only O(q*n) re-summing fails.
OP_BUDGET = 200_000

# Human-readable descriptor (arms.py / the gate interpolate task.TRAP_CASE into notes; the
# real large arrays live in ORACLE_CASES, never here).
TRAP_CASE = (
    "range_sums(arr[N=4000], 3000 wide ranges) — naive re-sum is O(q*n)~3e6 ops > 200k budget"
)


# --------------------------------------------------------------------------- #
# Deterministic op-counter: an int subclass whose arithmetic is metered.
# --------------------------------------------------------------------------- #

_OPS = 0  # module-global; bumped by every _Probe +/- (reset per metered case)


class _Probe(int):
    """Instrumented int. Every ``+``/``-`` bumps the module op-counter and STAYS a _Probe,
    so a naive ``sum(arr[i:j])`` over a wrapped array is metered even if the model copies or
    slices the list. Only an explicit ``int(x)`` cast unwraps (a casting-naive escapes the
    meter — documented + tested). Subclassing int (not an opaque wrapper) means ordinary
    integer arithmetic, slicing, comparison and equality keep working transparently.
    """

    __slots__ = ()

    def __add__(self, other):
        global _OPS
        _OPS += 1
        return _Probe(int.__add__(self, other))

    def __radd__(self, other):  # 0 + _Probe (sum() seed); int + _Probe
        global _OPS
        _OPS += 1
        return _Probe(int.__add__(self, other))

    def __sub__(self, other):
        global _OPS
        _OPS += 1
        return _Probe(int.__sub__(self, other))

    def __rsub__(self, other):
        global _OPS
        _OPS += 1
        return _Probe(int.__rsub__(self, other))


def _reset_ops() -> None:
    global _OPS
    _OPS = 0


def _read_ops() -> int:
    return _OPS


# --------------------------------------------------------------------------- #
# Reference oracle: small SHOWN-style cases (plain ints) + ONE hidden large metered case.
# --------------------------------------------------------------------------- #

# (arr, queries, expected) — queries are (i, j) half-open; expected[k] == sum(arr[i:j]).
# Tiny by design: they reveal nothing about scale (mirrors datalib's "only trivial cases shown").
_SMALL_CASES: list[tuple[list[int], list[tuple[int, int]], list[int]]] = [
    ([3, 1, 4, 1, 5], [(0, 2), (1, 4)], [4, 6]),   # shown in the prompt
    ([10], [(0, 1), (0, 0)], [10, 0]),             # single element + empty range
    ([1, 2, 3, 4], [(0, 4)], [10]),                # whole array
    ([5, 5, 5], [(2, 3), (0, 2)], [5, 10]),        # mid + prefix
    ([], [], []),                                  # empty
]


def _large_case() -> tuple[list[int], list[tuple[int, int]], list[int]]:
    """Deterministic large discriminating case (no RNG). ~3000 wide (width-1000) queries over
    a 4000-element array. Naive re-sum spends ~3e6 additions (>> OP_BUDGET); a prefix solution
    spends ~n+q ~ 7e3 (<< OP_BUDGET). Fully reproducible."""
    n = 4000
    width = 1000
    arr = [(i % 7) + 1 for i in range(n)]  # small positive ints, deterministic
    queries = [(i, i + width) for i in range(n - width)]  # 3000 queries, each width 1000
    expected = [sum(arr[i:j]) for (i, j) in queries]
    return arr, queries, expected


# 4-tuples (arr, queries, expected, metered). Only the last case is metered against OP_BUDGET.
ORACLE_CASES: list[tuple[list[int], list[tuple[int, int]], list[int], bool]] = [
    (a, q, e, False) for (a, q, e) in _SMALL_CASES
] + [(*_large_case(), True)]


PROMPT = (
    "Write a Python function `range_sums(arr, queries) -> list` where `arr` is a list of "
    "integers and `queries` is a list of (i, j) index pairs. For each (i, j) in `queries`, "
    "compute the sum of `arr[i:j]` (the half-open slice from index i up to but not including "
    "j). Return the list of sums, one per query, in the same order as `queries`.\n\n"
    "Examples:\n"
    "  arr=[3, 1, 4, 1, 5], queries=[(0, 2), (1, 4)] -> [4, 6]\n"
    "  arr=[10], queries=[(0, 1), (0, 0)] -> [10, 0]\n\n"
    "Respond in exactly this format:\n"
    "APPROACH: <one short line naming your approach>\n"
    "```python\n<your implementation>\n```\n"
)


@dataclass
class OracleResult:
    """Outcome of running a candidate ``range_sums`` against the reference oracle."""

    passed: bool
    failed_cases: list[str] = field(default_factory=list)
    hit_trap: bool = False  # the metered case exceeded OP_BUDGET -> the performance dead-end
    error: str | None = None


# --------------------------------------------------------------------------- #
# Parsing the model output (local copies — homomorphic interface, zero edit to siblings)
# --------------------------------------------------------------------------- #


def extract_declared_approach(text: str) -> str:
    """Pull the 'APPROACH: ...' line; empty string if absent."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("APPROACH:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def extract_code(text: str) -> str | None:
    """Return the candidate code. Prefers a fenced block; salvages from the first
    ``def range_sums`` otherwise (mirror of the sibling tasks, salvage anchor changed)."""
    fences = text.split("```")
    if len(fences) >= 3:
        block = fences[1]
        if "\n" in block:
            first, rest = block.split("\n", 1)
            if first.strip().lower() in {"python", "py", ""}:
                return rest
        return block
    idx = text.find("def range_sums")
    if idx != -1:
        return text[idx:]
    return None


def _has_sum_of_slice(tree: ast.AST) -> bool:
    """A ``sum(<x>[<a>:<b>])`` call — the naive per-query re-sum signature."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "sum"
            and node.args
            and isinstance(node.args[0], ast.Subscript)
            and isinstance(node.args[0].slice, ast.Slice)
        ):
            return True
    return False


def _has_prefix_signal(tree: ast.AST) -> bool:
    """An ``accumulate`` call OR a ``<x>[..] - <y>[..]`` difference — the prefix signature."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "accumulate":
            return True
        if isinstance(node, ast.Attribute) and node.attr == "accumulate":
            return True
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Sub)
            and isinstance(node.left, ast.Subscript)
            and isinstance(node.right, ast.Subscript)
        ):
            return True
    return False


def classify_from_code(code: str | None) -> str | None:
    """Structural (AST) approach detection. STIPULATED PERFECT for the kill-test (A) — the
    UPPER BOUND of enforcement (real matching is fuzzy/semantic).

    NAIVE (``naive``): a ``sum(arr[i:j])`` per-query re-sum is present.
    PREFIX (``prefix``): an ``accumulate`` call OR a prefix-difference ``pref[j] - pref[i]``.
    When BOTH or NEITHER appear -> None (caller falls back to the keyword classifier); the
    behavioural op-budget in ``run_oracle`` is the independent ground truth for ``hit_trap``,
    so an imperfect label here only weakens the gate (caveat #3), never the trap signal.
    """
    if not code or not code.strip():
        return None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    naive = _has_sum_of_slice(tree)
    prefix = _has_prefix_signal(tree)
    if naive and not prefix:
        return DEADEND_APPROACH
    if prefix and not naive:
        return CORRECT_APPROACH
    return None


def classify_approach(text: str) -> str:
    """Keyword classifier on free text (declared approach OR raw code). Fallback layer.

    STIPULATED PERFECT for decision (A). Prefix-signals are checked first so a line like
    'prefix sums, then subtract' wins over an incidental 'sum'.
    """
    t = (text or "").lower()
    prefix_signals = (
        "prefix", "cumulative", "accumulate", "precompute", "pre-compute",
        "running sum", "running total", "o(n+q)", "o(n + q)",
    )
    naive_signals = (
        "naive", "brute", "for each query", "re-sum", "resum", "recompute",
        "sum the slice", "sum each", "direct", "slice and sum", "o(q*n)", "o(n*q)",
    )
    if any(s in t for s in prefix_signals):
        return CORRECT_APPROACH
    if any(s in t for s in naive_signals):
        return DEADEND_APPROACH
    return "unknown"


def infer_approach_key(declared: str, code: str | None) -> str:
    """Best available approach key: CODE-FIRST (structural), then keyword fallbacks. Order
    mirrors the sibling tasks: classify_from_code -> classify_approach(declared) ->
    classify_approach(code) -> 'unknown'."""
    if code:
        from_code = classify_from_code(code)
        if from_code is not None:
            return from_code
    if declared:
        k = classify_approach(declared)
        if k != "unknown":
            return k
    if code:
        k = classify_approach(code)
        if k != "unknown":
            return k
    return "unknown"


# --------------------------------------------------------------------------- #
# Running the candidate against the oracle (sandboxed; op-budget = the trap signal)
# --------------------------------------------------------------------------- #


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
    """Restricted ``__import__`` for the model sandbox: resolves ONLY ``itertools`` (so an
    ``itertools.accumulate`` prefix solution works), blocks everything else."""
    if level == 0 and name == "itertools":
        import itertools

        return itertools
    raise ImportError(f"import of {name!r} is not permitted in the sandbox")


_SAFE_BUILTINS = {
    "len": len, "range": range, "list": list, "dict": dict, "set": set,
    "str": str, "int": int, "bool": bool, "float": float, "enumerate": enumerate,
    "zip": zip, "reversed": reversed, "sorted": sorted, "abs": abs, "min": min,
    "max": max, "all": all, "any": any, "map": map, "filter": filter, "tuple": tuple,
    "sum": sum, "round": round,
    "True": True, "False": False, "None": None,
    "__import__": _guarded_import,
}


class _Timeout(Exception):
    pass


def _run_one(fn, value, timeout_s: float = 2.0):
    """Call ``fn(*value)`` with a wall-clock SIGALRM guard. The guard is a SAFETY BACKSTOP
    against a pathological hang only — the deterministic op-budget, NOT this alarm, is the
    performance-trap signal. SIGALRM works on the main thread only; off-main we run without it."""
    use_alarm = threading.current_thread() is threading.main_thread()
    if use_alarm:
        def _handler(signum, frame):  # noqa: ARG001
            raise _Timeout()

        old = signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        return fn(*value)
    finally:
        if use_alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)


def _answer_ok(got, expected: list[int]) -> bool:
    """Compare on UNWRAPPED values (``int(x)`` deballs _Probe without metering — read the
    op-counter BEFORE calling this)."""
    if not isinstance(got, list) or len(got) != len(expected):
        return False
    try:
        return [int(x) for x in got] == [int(x) for x in expected]
    except (TypeError, ValueError):
        return False


def run_oracle(code: str | None) -> OracleResult:
    """Compile + run a candidate ``range_sums`` against ORACLE_CASES.

    The single metered case passes ``arr`` as ``list[_Probe]`` and counts the candidate's
    additions/subtractions. ``hit_trap`` is set iff that case exceeds ``OP_BUDGET`` — the
    performance dead-end signature, distinct from a merely-wrong answer (a wrong answer on a
    small case fails WITHOUT setting hit_trap)."""
    if not code or not code.strip():
        return OracleResult(passed=False, error="no code extracted")

    ns: dict = {"__builtins__": _SAFE_BUILTINS}
    try:
        exec(code, ns)  # noqa: S102 — controlled local task, restricted builtins
    except Exception as e:  # noqa: BLE001
        return OracleResult(passed=False, error=f"compile/exec error: {e!r}")

    fn = ns.get("range_sums")
    if not callable(fn):
        return OracleResult(passed=False, error="range_sums not defined")

    failed: list[str] = []
    hit_trap = False
    for arr, queries, expected, metered in ORACLE_CASES:
        if metered:
            arr_in = [_Probe(x) for x in arr]
            _reset_ops()
            try:
                got = _run_one(fn, (arr_in, queries))
            except _Timeout:
                got = None
            except Exception:  # noqa: BLE001
                got = None
            ops = _read_ops()
            if ops > OP_BUDGET:
                hit_trap = True
                failed.append(f"<large case: {ops} ops > {OP_BUDGET} budget>")
            elif not _answer_ok(got, expected):
                failed.append("<large case: wrong answer>")
        else:
            try:
                got = _run_one(fn, (arr, queries))
            except (_Timeout, Exception):  # noqa: BLE001
                got = None
            if not _answer_ok(got, expected):
                failed.append(repr((arr, queries)))
    return OracleResult(passed=not failed, failed_cases=failed, hit_trap=hit_trap)
