"""Prior-trap task: pick the right `datalib` function for `order_cost`, oracle-checked.

TEMPS 2d. Replaces ``balanced_brackets`` (too easy: Haiku wrote the correct algorithm
10/10). That task asked the model to *author* an algorithm — a frontier model authors
the correct one. This task *inverts* that: it hands the model a small library and makes
it *choose* between two sibling functions.

    THE DEAD-END ("total") — the obvious, verb-matching function. ``datalib.total``
    sums ``qty * unit_cents`` and is correct for one- or two-line orders, so it looks
    right. It silently OMITS the store handling fee, so it is SUBTLY WRONG on orders of
    three or more line-items (off by exactly the fee — no exception, a plausible number).
    "Dead-end" is therefore an OBJECTIVE, AST-derived label (the code CALLS
    ``datalib.total``), cross-checked behaviourally by the oracle (DIRECTION §7).

    THE CORRECT APPROACH ("settle") — ``datalib.settle`` adds the flat handling fee for
    orders of three or more line-items. The fee is an ARBITRARY magic constant
    (``HANDLING_FEE_CENTS``) documented ONLY in the inlined source: it cannot be guessed
    from priors or re-derived from the two trivial examples shown in the prompt, which
    FORCES use of the library (a model that bypasses-and-reimplements gets the fee wrong
    and fails the oracle — it cannot masquerade as "correct").

HONEST CALIBRATION (founder constraint, 2026-06-14): this is a *natural* obsolete-API
trap — the obvious name (``total``) is the wrong one because the business rule moved on.
``settle``'s source and docstring are fully inlined, so the fix is honestly discoverable;
a model that READS the library picks ``settle``. The task is NOT tuned to deceive Haiku
into the trap; if Haiku does not fall in naturally, that is a finding to report, not a
cue to bury ``settle`` deeper.

``classify_from_code`` maps the model's code to {total, settle, None} by AST. STIPULATED
PERFECT for the kill-test (A): perfect identification is the gate's UPPER BOUND. A fourth
observable state — calling NEITHER function (a bypass) — is keyed ``unknown`` by
``infer_approach_key`` and reported separately by the probe (it must not be read as the
trap firing or as a correct solution).
"""

from __future__ import annotations

import ast
import signal
import sys
import threading
import types
from dataclasses import dataclass, field

TASK_ID = "datalib_prior_trap"

# The objective dead-end (calling datalib.total) and the correct approach (datalib.settle).
DEADEND_APPROACH = "total"
CORRECT_APPROACH = "settle"

# The clean discriminating case: three identical lines -> total omits the fee.
TRAP_CASE = [(1, 100), (1, 100), (1, 100)]

# --------------------------------------------------------------------------- #
# datalib — SINGLE SOURCE OF TRUTH.
# Inlined verbatim into PROMPT *and* exec'd at oracle time, so the prompt the model
# reads and the module the oracle runs can never drift.
# --------------------------------------------------------------------------- #
DATALIB_SOURCE = '''\
"""datalib — tiny order-pricing helper.

A *ledger* is a list of (qty, unit_cents) tuples; all amounts are integer cents.
"""

HANDLING_FEE_CENTS = 13  # store handling fee — see settle()


def total(lines):
    """Total an order: the sum of qty * unit_cents over the ledger."""
    return sum(qty * unit_cents for qty, unit_cents in lines)


def settle(lines):
    """Settled order amount, in cents.

    The line sum plus the store handling fee: an order of three or more distinct
    line-items carries a flat HANDLING_FEE_CENTS surcharge, added once; orders of
    one or two line-items carry no surcharge.
    """
    base = sum(qty * unit_cents for qty, unit_cents in lines)
    fee = HANDLING_FEE_CENTS if len(lines) >= 3 else 0
    return base + fee
'''

# (lines, expected_cents) — the reference oracle. expected == datalib.settle(lines).
# Four trivial cases (<= 2 lines, total == settle) + three discriminating cases
# (>= 3 lines, total != settle, off by HANDLING_FEE_CENTS). The internal-consistency
# test locks these values to DATALIB_SOURCE.
ORACLE_CASES: list[tuple[list[tuple[int, int]], int]] = [
    ([], 0),                                            # trivial
    ([(1, 500)], 500),                                  # trivial
    ([(3, 120)], 360),                                  # trivial
    ([(2, 999), (1, 1)], 1999),                         # trivial (2 lines, no fee)
    (TRAP_CASE, 313),                                   # discriminating (300 + 13)
    ([(2, 50), (3, 40), (1, 10), (4, 25)], 343),        # discriminating (330 + 13)
    ([(1, 1), (1, 1), (1, 1), (1, 1), (1, 1)], 18),     # discriminating (5 + 13)
]

# Only trivial orders are SHOWN (they reveal nothing about the fee); the discriminating
# cases live unshown in the oracle, so the rule cannot be reverse-engineered from examples.
PROMPT = (
    "You are given a module `datalib` (full source below). Using `datalib`, write a "
    "Python function `order_cost(lines) -> int` that returns the integer-cents amount to "
    "charge the customer for an order, where `lines` is a list of (qty, unit_cents) "
    "tuples. Use the provided `datalib` — do not reimplement its pricing logic.\n\n"
    "Examples: [(1, 500)] -> 500 ; [(2, 999), (1, 1)] -> 1999\n\n"
    "```python\n# datalib (provided)\n" + DATALIB_SOURCE + "```\n\n"
    "Respond in exactly this format:\n"
    "APPROACH: <one short line naming your approach>\n"
    "```python\n<your implementation>\n```\n"
)


@dataclass
class OracleResult:
    """Outcome of running a candidate ``order_cost`` against the reference oracle."""

    passed: bool
    failed_cases: list[str] = field(default_factory=list)
    hit_trap: bool = False  # a failed case returned the naive total -> the dead-end
    error: str | None = None


# --------------------------------------------------------------------------- #
# Parsing the model output
# --------------------------------------------------------------------------- #


def extract_declared_approach(text: str) -> str:
    """Pull the 'APPROACH: ...' line; empty string if absent. (Copy of the
    balanced_brackets helper — kept task-local to honour zero-edit-to-existing-modules.)"""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("APPROACH:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def extract_code(text: str) -> str | None:
    """Return the candidate code. Prefers a fenced block; salvages from the first
    ``def order_cost`` otherwise. Mirror of balanced_brackets.extract_code with the
    salvage anchor changed (kept local for the zero-edit discipline)."""
    fences = text.split("```")
    if len(fences) >= 3:
        block = fences[1]
        if "\n" in block:
            first, rest = block.split("\n", 1)
            if first.strip().lower() in {"python", "py", ""}:
                return rest
        return block
    idx = text.find("def order_cost")
    if idx != -1:
        return text[idx:]
    return None


def classify_approach(text: str) -> str:
    """Keyword classifier on free text (declared approach OR raw code). Fallback layer.

    STIPULATED PERFECT for decision (A). Settle-signals are checked first so a line like
    'settle, includes the handling fee' wins over an incidental 'sum'/'total'.
    """
    t = (text or "").lower()
    settle_signals = ("settle", "handling fee", "handling_fee", "surcharge", "fee",
                      "reconcile", "correct amount")
    total_signals = ("total", "sum", "naive", "add up", "just add", "qty * ", "qty*")
    if any(s in t for s in settle_signals):
        return CORRECT_APPROACH
    if any(s in t for s in total_signals):
        return DEADEND_APPROACH
    return "unknown"


def classify_from_code(code: str | None) -> str | None:
    """Structural (AST) approach detection — which ``datalib`` function the code CALLS.

    Two passes, robust to every import form:
      pass 1 — build alias tables from Import / ImportFrom, minus local-def shadows;
      pass 2 — walk Call nodes, resolve each callee to a canonical datalib function.

    Resolves: ``datalib.total(...)``, ``import datalib as dl; dl.settle(...)``,
    ``from datalib import total, settle; total(...)``, ``from datalib import settle as s;
    s(...)``. Comments/strings are not Call nodes, so they never mis-trigger. A local
    ``def total``/``def settle`` shadow drops that name from the table (a bypasser who
    rolls their own ``total`` is NOT flagged as the datalib trap).

    Returns ``settle`` (tie-winner — a real settle call is the discriminating CORRECT
    signature), else ``total``, else None (caller falls back to the keyword classifier).
    """
    if not code or not code.strip():
        return None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    module_aliases: dict[str, str] = {}   # local name -> "datalib"
    func_aliases: dict[str, str] = {}     # local name -> "total" | "settle"
    shadowed: set[str] = set()            # names rebound by a local def
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "datalib":
                    module_aliases[a.asname or a.name] = "datalib"
        elif isinstance(node, ast.ImportFrom):
            if node.module == "datalib":
                for a in node.names:
                    if a.name in ("total", "settle"):
                        func_aliases[a.asname or a.name] = a.name
        elif isinstance(node, ast.FunctionDef):
            shadowed.add(node.name)
    for name in shadowed:
        func_aliases.pop(name, None)

    called: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name):
            if fn.value.id in module_aliases and fn.attr in ("total", "settle"):
                called.add(fn.attr)
        elif isinstance(fn, ast.Name) and fn.id in func_aliases:
            called.add(func_aliases[fn.id])

    if "settle" in called:
        return CORRECT_APPROACH
    if "total" in called:
        return DEADEND_APPROACH
    return None


def infer_approach_key(declared: str, code: str | None) -> str:
    """Best available approach key: CODE-FIRST (structural), then keyword fallbacks.

    Order mirrors balanced_brackets.infer_approach_key:
      1. classify_from_code(code)    — structural AST, most reliable
      2. classify_approach(declared) — keyword on the declared line
      3. classify_approach(code)     — keyword on raw code (rescues non-AST-parsable)
      4. 'unknown'                   — incl. a bypass that called neither datalib fn
    """
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
# Running the candidate against the oracle (sandboxed + time-bounded)
# --------------------------------------------------------------------------- #


def _build_datalib_module() -> types.ModuleType:
    """Build the live ``datalib`` module from DATALIB_SOURCE with FULL builtins.

    This is trusted task code (not the model's), so it runs with normal builtins —
    ``sum``/``len`` are available regardless of the model sandbox whitelist.
    """
    mod = types.ModuleType("datalib")
    exec(DATALIB_SOURCE, mod.__dict__)  # noqa: S102 — fixed, trusted task source
    return mod


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
    """Restricted ``__import__`` for the model sandbox: resolves ONLY ``datalib`` (from
    sys.modules), blocks everything else. Lets both ``import datalib`` and
    ``from datalib import settle`` resolve while keeping the sandbox closed."""
    if level == 0 and name == "datalib":
        return sys.modules["datalib"]
    raise ImportError(f"import of {name!r} is not permitted in the sandbox")


# balanced_brackets' whitelist + arithmetic helpers a reimplementation might use + the
# guarded importer. The model's code runs under these; the datalib logic already ran with
# full builtins inside _build_datalib_module.
_SAFE_BUILTINS = {
    "len": len, "range": range, "list": list, "dict": dict, "set": set,
    "str": str, "int": int, "bool": bool, "float": float, "enumerate": enumerate,
    "zip": zip, "reversed": reversed, "sorted": sorted, "abs": abs, "min": min,
    "max": max, "all": all, "any": any, "map": map, "filter": filter, "tuple": tuple,
    "sum": sum, "round": round, "divmod": divmod, "pow": pow,
    "True": True, "False": False, "None": None,
    "__import__": _guarded_import,
}


class _Timeout(Exception):
    pass


def _run_one(fn, value, timeout_s: float = 2.0):
    """Call fn(value) with a wall-clock timeout (SIGALRM on the main thread). Returns the
    candidate's value (an int here — NOT coerced to bool, unlike the bracket task)."""
    use_alarm = threading.current_thread() is threading.main_thread()
    if use_alarm:
        def _handler(signum, frame):  # noqa: ARG001
            raise _Timeout()

        old = signal.signal(signal.SIGALRM, _handler)
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
    try:
        return fn(value)
    finally:
        if use_alarm:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old)


def run_oracle(code: str | None) -> OracleResult:
    """Compile + run a candidate ``order_cost`` against ORACLE_CASES.

    Registers the live ``datalib`` in sys.modules around the exec (restored in finally)
    so the model's ``import datalib`` / ``from datalib import ...`` resolves through the
    guarded importer. ``hit_trap`` is BEHAVIOURAL: a failed case whose returned value
    equals ``datalib.total(lines)`` (while that differs from the expected settled amount)
    means the candidate took the naive-total dead-end — an oracle-derived cross-check of
    the AST label.
    """
    if not code or not code.strip():
        return OracleResult(passed=False, error="no code extracted")

    saved = sys.modules.get("datalib")
    datalib = _build_datalib_module()
    sys.modules["datalib"] = datalib
    try:
        ns: dict = {"__builtins__": _SAFE_BUILTINS}
        try:
            exec(code, ns)  # noqa: S102 — controlled local task, restricted builtins
        except Exception as e:  # noqa: BLE001
            return OracleResult(passed=False, error=f"compile/exec error: {e!r}")

        fn = ns.get("order_cost")
        if not callable(fn):
            return OracleResult(passed=False, error="order_cost not defined")

        naive = datalib.total
        failed: list[str] = []
        hit_trap = False
        for lines, expected in ORACLE_CASES:
            try:
                got = _run_one(fn, lines)
            except _Timeout:
                got = None
            except Exception:  # noqa: BLE001
                got = None
            if got != expected:
                failed.append(repr(lines))
                try:
                    naive_val = naive(lines)
                except Exception:  # noqa: BLE001
                    naive_val = None
                if got is not None and got == naive_val and naive_val != expected:
                    hit_trap = True
        return OracleResult(passed=not failed, failed_cases=failed, hit_trap=hit_trap)
    finally:
        if saved is None:
            sys.modules.pop("datalib", None)
        else:
            sys.modules["datalib"] = saved
