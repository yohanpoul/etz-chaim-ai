"""Deprecated-API prior-trap task: two REAL obsolete-API footguns (pandas / numpy), oracle-checked.

TEMPS 2e. Mirror of ``datalib_prior_trap.py``, but the dead-end is a REAL removed API
rather than an invented sibling function. The two prior NO-GOs failed for structural
reasons: ``balanced_brackets`` let the frontier *author* the right algorithm, and
``datalib_prior_trap`` let it *read* a short inlined library and pick the documented-correct
function (an invented library carries NO obsolete-API training prior to exploit). A REAL
deprecated API, by contrast, carries a massive pre-removal prior in the weights — the only
honest way to elicit a single-shot dead-end *without* burying the modern solution.

Two subtasks live in one module behind a registry:

    P (pandas)  build_ledger(records)  — DEAD-END: DataFrame.append (removed pandas 2.0,
        Jan 2023 -> AttributeError). The streaming "one record at a time" framing is the
        natural place a model trained on pre-2.0 pandas reaches for ``df = df.append(row)``.
        CORRECT: accumulate in a list then ``pd.DataFrame(rows)``, or ``pd.concat``.
    N (numpy)   to_amounts(values)     — DEAD-END: np.float / np.int (removed numpy 1.24,
        Dec 2022 -> AttributeError). The old reflex is ``np.array(values, dtype=np.float)``.
        CORRECT: ``dtype=float`` / ``np.float64`` / ``[float(v) for v in values]``.

"Dead-end" is an OBJECTIVE, AST-derived label (the code uses the removed API), cross-checked
behaviourally by the oracle (the removed API *raises* at run time, exactly as a wrong
``settle`` did — no plausible-but-wrong number, a hard AttributeError). Buckets, mirroring
datalib's {total, settle, bypass, unknown}: ``deprecated`` / ``correct`` / ``bypass`` /
``unknown``.

HONEST CALIBRATION (founder constraint, 2026-06-14): the prompt states the GOAL only. It
NEVER names the deprecated method (append / np.float) nor the modern fix (concat / dtype=
float / float64). The streaming / "floating-point" framing is the realistic footgun, not a
gotcha tuned to deceive. If Haiku does not fall in naturally, that is a finding to report
(a clean 3rd NO-GO closes the cheap single-shot path), NOT a cue to bias the prompt.

Capability-guarded: the module imports cleanly even when pandas is absent or a library is
too old to raise the AttributeError (``PANDAS_OK`` / ``NUMPY_OK`` computed once at import).
A subtask whose library cannot produce the signal self-skips (``OracleResult.skipped``) so
the offline tests ``pytest.skip`` cleanly and the probe skips that subtask rather than
mis-reporting an invalid signal.
"""

from __future__ import annotations

import ast
import signal
import sys
import threading
from dataclasses import dataclass, field
from typing import Callable

TASK_ID = "deprecated_api_trap"

# The objective dead-end (a REMOVED API) and the correct approach (a current one). Shared
# across both subtasks so the probe reads them once, exactly like datalib.
DEADEND_APPROACH = "deprecated"
CORRECT_APPROACH = "correct"


# --------------------------------------------------------------------------- #
# Capability flags — computed once at import, NEVER raise.
# A library < the removal version means the removed API still works -> the AttributeError
# signal is invalid -> the subtask must self-skip rather than mis-report.
# --------------------------------------------------------------------------- #


def _ver_tuple(v: str) -> tuple[int, ...]:
    """(major, minor) as ints, crash-proof on dev/rc tags ('2.0.0rc1' -> (2, 0))."""
    out: list[int] = []
    for part in v.split(".")[:2]:
        digits = "".join(ch for ch in part if ch.isdigit())
        out.append(int(digits) if digits else 0)
    return tuple(out)


PANDAS_OK = False
PANDAS_VERSION: str | None = None
try:
    import pandas as _pd  # noqa: F401

    PANDAS_VERSION = _pd.__version__
    PANDAS_OK = _ver_tuple(PANDAS_VERSION) >= (2, 0)  # 2.0 removed DataFrame.append
except Exception:  # noqa: BLE001 — ImportError or any import-time failure
    _pd = None  # type: ignore[assignment]

NUMPY_OK = False
NUMPY_VERSION: str | None = None
try:
    import numpy as _np  # noqa: F401

    NUMPY_VERSION = _np.__version__
    NUMPY_OK = _ver_tuple(NUMPY_VERSION) >= (1, 24)  # 1.24 removed np.float / np.int
except Exception:  # noqa: BLE001
    _np = None  # type: ignore[assignment]


# --------------------------------------------------------------------------- #
# Prompts — NEUTRAL. State the GOAL only; never name the deprecated method nor the fix.
# Same output contract as datalib (one 'APPROACH:' line, one fenced python block).
# --------------------------------------------------------------------------- #

_PROMPT_PANDAS = (
    "You are given `records`, a list of homogeneous dicts (every dict has the same keys), "
    "arriving as a STREAM: you receive them one at a time and do NOT have them all up "
    "front. Write a Python function `build_ledger(records) -> pandas.DataFrame` that, "
    "starting from an empty DataFrame, incorporates each incoming record one by one and "
    "returns a single pandas.DataFrame containing every row, in arrival order, with the "
    "dicts' keys as columns.\n\n"
    "Example: records = [{\"sku\": \"A\", \"qty\": 2}, {\"sku\": \"B\", \"qty\": 5}] -> a "
    "DataFrame with columns [\"sku\", \"qty\"] and two rows.\n\n"
    "Respond in exactly this format:\n"
    "APPROACH: <one short line naming your approach>\n"
    "```python\n<your implementation>\n```\n"
)

_PROMPT_NUMPY = (
    "You are given `values`, a list of numeric strings, e.g. ['12.50', '3.00', '0.99']. "
    "Write a Python function `to_amounts(values) -> numpy.ndarray` that returns a NumPy "
    "ndarray holding the corresponding floating-point numbers, in the same order.\n\n"
    "Example: ['12.50', '3.00'] -> array([12.5, 3.0])\n\n"
    "Respond in exactly this format:\n"
    "APPROACH: <one short line naming your approach>\n"
    "```python\n<your implementation>\n```\n"
)


# --------------------------------------------------------------------------- #
# Oracle cases — plain Python data (NO pandas/numpy at module level, so the module imports
# with the libraries absent). The oracle builds the reference values at call time.
# --------------------------------------------------------------------------- #

# pandas: each case is a list[dict] (a "stream" of records). Empty stream is non-
# discriminating (append never fires) but locks the shape contract; the four non-empty
# cases make the trap raise on the first append.
ORACLE_CASES_PANDAS: list[list[dict]] = [
    [],
    [{"sku": "A", "qty": 2}],
    [{"sku": "A", "qty": 2}, {"sku": "B", "qty": 5}],
    [{"sku": "A", "qty": 2}, {"sku": "B", "qty": 5}, {"sku": "C", "qty": 1}, {"sku": "D", "qty": 9}],
    [{"x": 1, "y": 10}, {"x": 2, "y": 20}, {"x": 3, "y": 30}],
]

# numpy: (values, expected_floats). The deprecated np.float lookup fails BEFORE any data is
# touched, so EVERY case (incl. empty) makes the trap raise -> all are discriminating.
ORACLE_CASES_NUMPY: list[tuple[list[str], list[float]]] = [
    ([], []),
    (["12.50", "3.00"], [12.5, 3.0]),
    (["0.99"], [0.99]),
    (["100", "0", "-4.5"], [100.0, 0.0, -4.5]),
    (["1e3", "2.5e-1"], [1000.0, 0.25]),
]


@dataclass
class OracleResult:
    """Outcome of running a candidate against the reference oracle."""

    passed: bool
    failed_cases: list[str] = field(default_factory=list)
    hit_trap: bool = False  # a case raised the removed-API AttributeError -> the dead-end
    error: str | None = None
    skipped: bool = False  # capability flag was False -> signal invalid, not a real result


# --------------------------------------------------------------------------- #
# Parsing the model output (shared, subtask-agnostic)
# --------------------------------------------------------------------------- #


def extract_declared_approach(text: str) -> str:
    """Pull the 'APPROACH: ...' line; empty string if absent. (Copy of the datalib helper —
    kept task-local to honour zero-edit-to-existing-modules.)"""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("APPROACH:"):
            return stripped.split(":", 1)[1].strip()
    return ""


def extract_code(text: str, func_name: str) -> str | None:
    """Return the candidate code. Prefers a fenced block; salvages from the first
    ``def <func_name>`` otherwise. Mirror of datalib.extract_code, salvage anchor
    parameterised per subtask (kept local for the zero-edit discipline)."""
    fences = text.split("```")
    if len(fences) >= 3:
        block = fences[1]
        if "\n" in block:
            first, rest = block.split("\n", 1)
            if first.strip().lower() in {"python", "py", ""}:
                return rest
        return block
    idx = text.find(f"def {func_name}")
    if idx != -1:
        return text[idx:]
    return None


# Keyword fallback tables, per subtask. Deprecated-signals are checked first so a clear
# deprecation statement is not flipped by an incidental token.
_KW: dict[str, dict[str, tuple[str, ...]]] = {
    "pandas": {
        "deprecated": ("dataframe.append", ".append(", "append to the dataframe", "df.append"),
        "correct": ("concat", "pd.concat", "list", "accumulate", "pd.dataframe(",
                    "from_records", "from_dict"),
    },
    "numpy": {
        "deprecated": ("np.float", "np.int", "numpy.float", "numpy.int"),
        "correct": ("dtype=float", "float64", "np.float64", "astype", "dtype='float",
                    'dtype="float'),
    },
}


def classify_approach(text: str, key: str) -> str:
    """Keyword classifier on free text (declared approach OR raw code). Fallback layer only —
    the AST classifier (``classify_from_code_*``) is primary and resolves list-vs-DataFrame
    structurally."""
    t = (text or "").lower()
    tab = _KW[key]
    if any(s in t for s in tab["deprecated"]):
        return DEADEND_APPROACH
    if any(s in t for s in tab["correct"]):
        return CORRECT_APPROACH
    return "unknown"


# --------------------------------------------------------------------------- #
# AST classifiers (PRIMARY) — which API the code uses, structurally.
# --------------------------------------------------------------------------- #

# pandas module-attribute factories that return a DataFrame (read_* handled by prefix).
_PD_DF_FACTORIES = {"DataFrame", "concat", "merge"}
# DataFrame classmethod factories, accessed as ``pd.DataFrame.from_records`` / bare
# ``DataFrame.from_records`` — the receiver is the DataFrame CLASS, not the pandas module.
_PD_DF_CLASSMETHODS = {"from_records", "from_dict"}


def _resolves_to_df_class(node: ast.expr, pandas_names: set[str], df_ctor_names: set[str]) -> bool:
    """Is this expr the DataFrame class? ``pd.DataFrame`` (module attribute) or a bare
    ``DataFrame`` name (from-import)."""
    if isinstance(node, ast.Attribute) and node.attr == "DataFrame" \
            and isinstance(node.value, ast.Name) and node.value.id in pandas_names:
        return True
    return isinstance(node, ast.Name) and node.id in df_ctor_names


def _is_df_producing_call(node: ast.Call, pandas_names: set[str], df_ctor_names: set[str]) -> bool:
    """Does this Call return a DataFrame? ``pd.DataFrame(...)`` / ``pd.concat(...)`` /
    ``pd.read_*(...)`` (module-attribute factories), ``pd.DataFrame.from_records(...)`` (a
    classmethod on the DataFrame class), or a bare ``DataFrame(...)`` (from-import ctor)."""
    f = node.func
    if isinstance(f, ast.Attribute):
        if isinstance(f.value, ast.Name) and f.value.id in pandas_names \
                and (f.attr in _PD_DF_FACTORIES or f.attr.startswith("read_")):
            return True
        if f.attr in _PD_DF_CLASSMETHODS \
                and _resolves_to_df_class(f.value, pandas_names, df_ctor_names):
            return True
    if isinstance(f, ast.Name) and f.id in df_ctor_names:
        return True
    return False


def classify_from_code_pandas(code: str | None) -> str | None:
    """Structural detection for the pandas subtask. Flags ``<name>.append(...)`` ONLY when
    ``<name>`` is DataFrame-typed (never ``list.append``), plus chained
    ``pd.DataFrame(...).append(...)``. Returns ``deprecated`` (tie-winner — the removed
    DataFrame.append is the discriminating dead-end signature), else ``correct`` if a
    DataFrame is constructed by a current path, else None (caller falls back to keywords).

    Flow-insensitive over-approximation (a name assigned a DataFrame anywhere is treated
    DataFrame-typed everywhere) — the same conservative stance datalib takes with shadows.
    """
    if not code or not code.strip():
        return None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    # Pass 1: import/alias tables and local-def shadows.
    pandas_names: set[str] = set()   # local names bound to the pandas module
    df_ctor_names: set[str] = set()  # local names meaning the DataFrame class
    shadowed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "pandas":
                    pandas_names.add(a.asname or a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "pandas":
                for a in node.names:
                    if a.name == "DataFrame":
                        df_ctor_names.add(a.asname or a.name)
        elif isinstance(node, ast.FunctionDef):
            shadowed.add(node.name)
    pandas_names -= shadowed
    df_ctor_names -= shadowed

    # Pass 2: collect DataFrame-typed variable names (assignments + annotations).
    df_vars: set[str] = set()

    def _is_df_annotation(ann: ast.expr) -> bool:
        if isinstance(ann, ast.Attribute) and ann.attr == "DataFrame" \
                and isinstance(ann.value, ast.Name) and ann.value.id in pandas_names:
            return True
        return isinstance(ann, ast.Name) and ann.id in df_ctor_names

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call) and _is_df_producing_call(
                node.value, pandas_names, df_ctor_names
            ):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        df_vars.add(tgt.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if _is_df_annotation(node.annotation):
                df_vars.add(node.target.id)
            elif isinstance(node.value, ast.Call) and _is_df_producing_call(
                node.value, pandas_names, df_ctor_names
            ):
                df_vars.add(node.target.id)

    # Pass 3: detect the deprecated append and any correct construction.
    deprecated_append = False
    correct_signal = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_df_producing_call(node, pandas_names, df_ctor_names):
            correct_signal = True
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr == "append":
            recv = f.value
            if isinstance(recv, ast.Name) and recv.id in df_vars:
                deprecated_append = True
            elif isinstance(recv, ast.Call) and _is_df_producing_call(
                recv, pandas_names, df_ctor_names
            ):
                deprecated_append = True  # chained pd.DataFrame(...).append(...)

    if deprecated_append:
        return DEADEND_APPROACH
    if correct_signal:
        return CORRECT_APPROACH
    return None


# numpy scalar aliases removed in 1.24. EXCLUDES bool/long (still valid in numpy 2.x —
# flagging them would be a false positive the oracle could never confirm).
_NP_REMOVED = {"float", "int", "object", "str", "complex"}
_NP_CORRECT_ATTRS = {"float64", "float32", "int64", "int32"}


def classify_from_code_numpy(code: str | None) -> str | None:
    """Structural detection for the numpy subtask. Flags ``np.float`` / ``np.int`` (a bare
    Attribute access on the numpy module — including ``dtype=np.float``, which is never a
    Call). Returns ``deprecated`` (tie-winner), else ``correct`` if a current float path is
    used (``dtype=float`` / ``np.float64`` / ``.astype`` / builtin ``float(...)``), else None.
    ``attr == 'float'`` is matched EXACTLY so ``np.float64`` stays correct.
    """
    if not code or not code.strip():
        return None
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None

    # Pass 1: numpy module aliases, direct-imported names, local-def shadows.
    numpy_names: set[str] = set()
    bad_direct: set[str] = set()   # `from numpy import float as f` -> f is deprecated
    shadowed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "numpy":
                    numpy_names.add(a.asname or a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module == "numpy":
                for a in node.names:
                    if a.name in _NP_REMOVED:
                        bad_direct.add(a.asname or a.name)
        elif isinstance(node, ast.FunctionDef):
            shadowed.add(node.name)
    numpy_names -= shadowed
    bad_direct -= shadowed

    # Pass 2: walk for deprecated / correct signals.
    deprecated = False
    correct = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id in numpy_names:
            if node.attr in _NP_REMOVED:
                deprecated = True
            elif node.attr in _NP_CORRECT_ATTRS or node.attr == "astype":
                correct = True
        elif isinstance(node, ast.Attribute) and node.attr == "astype":
            correct = True
        elif isinstance(node, ast.Name) and node.id in bad_direct:
            deprecated = True
        elif isinstance(node, ast.keyword) and node.arg == "dtype":
            v = node.value
            if isinstance(v, ast.Name) and v.id in {"float", "int"}:
                correct = True
            elif isinstance(v, ast.Constant) and isinstance(v.value, str) \
                    and v.value.lower().startswith(("float", "int")):
                correct = True
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in {"float", "int"}:
            correct = True

    if deprecated:
        return DEADEND_APPROACH
    if correct:
        return CORRECT_APPROACH
    return None


def infer_approach_key(declared: str, code: str | None, subtask: "Subtask") -> str:
    """Best available approach key: CODE-FIRST (structural AST), then keyword fallbacks.

      1. subtask.classify_from_code(code)       — structural AST, most reliable
      2. classify_approach(declared, key)       — keyword on the declared line
      3. classify_approach(code, key)            — keyword on raw code, NUMPY ONLY
                                                   (pandas 'append' is too ambiguous vs
                                                    list.append to run on raw code)
      4. 'unknown'                               — incl. a bypass that used neither API
    """
    if code:
        from_code = subtask.classify_from_code(code)
        if from_code is not None:
            return from_code
    if declared:
        k = classify_approach(declared, subtask.key)
        if k != "unknown":
            return k
    if code and subtask.key == "numpy":
        k = classify_approach(code, subtask.key)
        if k != "unknown":
            return k
    return "unknown"


# --------------------------------------------------------------------------- #
# Running the candidate against the oracle (sandboxed + time-bounded).
# REAL libraries (pandas/numpy already in sys.modules) — NOT an injected source module, so
# there is nothing to register or restore in sys.modules (cf datalib, which injected a fake).
# --------------------------------------------------------------------------- #

_ALLOWED_LIBS = {"pandas", "numpy"}


def _guarded_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
    """Restricted ``__import__`` for the model sandbox: resolves ONLY pandas/numpy (from the
    already-loaded sys.modules), blocks everything else. ``import os`` still raises. Lets both
    ``import pandas as pd`` and ``from pandas import DataFrame`` resolve."""
    if level == 0 and name in _ALLOWED_LIBS and name in sys.modules:
        return sys.modules[name]
    raise ImportError(f"import of {name!r} is not permitted in the sandbox")


# datalib's whitelist verbatim + the guarded importer. The candidate's function BODY runs
# under these (it is the model's code); pandas/numpy run via their OWN module globals (loaded
# at module import with full builtins), so the tight whitelist does not starve pd.DataFrame().
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
    candidate's value (a DataFrame / ndarray here — NOT coerced)."""
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


def _exec_candidate(code: str, func_name: str):
    """exec the candidate under the sandbox builtins; return (fn, error). fn is None on error."""
    ns: dict = {"__builtins__": _SAFE_BUILTINS}
    try:
        exec(code, ns)  # noqa: S102 — controlled local task, restricted builtins
    except Exception as e:  # noqa: BLE001
        return None, f"compile/exec error: {e!r}"
    fn = ns.get(func_name)
    if not callable(fn):
        return None, f"{func_name} not defined"
    return fn, None


def run_oracle_numpy(code: str | None) -> OracleResult:
    """Run a candidate ``to_amounts`` against ORACLE_CASES_NUMPY. ``hit_trap`` is BEHAVIOURAL:
    a case raising ``module 'numpy' has no attribute 'float'/'int'`` means the removed-alias
    dead-end fired — an oracle cross-check of the AST ``deprecated`` label."""
    if not NUMPY_OK:
        return OracleResult(passed=False, skipped=True, error=NUMPY_SUBTASK.skip_reason)
    if not code or not code.strip():
        return OracleResult(passed=False, error="no code extracted")
    fn, err = _exec_candidate(code, "to_amounts")
    if fn is None:
        return OracleResult(passed=False, error=err)

    failed: list[str] = []
    hit_trap = False
    for values, expected_list in ORACLE_CASES_NUMPY:
        try:
            got = _run_one(fn, values)
        except _Timeout:
            failed.append(repr(values))
            continue
        except AttributeError as e:
            if "has no attribute 'float'" in str(e) or "has no attribute 'int'" in str(e):
                hit_trap = True
            failed.append(repr(values))
            continue
        except Exception:  # noqa: BLE001
            failed.append(repr(values))
            continue
        expected = _np.asarray(expected_list, dtype=float)
        ok = isinstance(got, _np.ndarray) and got.shape == expected.shape \
            and _np.allclose(got, expected)
        if not ok:
            failed.append(repr(values))
    return OracleResult(passed=not failed, failed_cases=failed, hit_trap=hit_trap)


def _frames_equal(got, expected) -> bool:
    """Behaviourally-correct DataFrame comparison: same type, exact column order/names, equal
    rows. ``reset_index(drop=True)`` normalises a non-RangeIndex left by a per-row concat so an
    index artefact does not fail a correct solution. (Fallback if too strict on real output:
    compare ``got.to_dict("records") == expected.to_dict("records")``.)"""
    if not isinstance(got, _pd.DataFrame):
        return False
    g = got.reset_index(drop=True)
    e = expected.reset_index(drop=True)
    if list(g.columns) != list(e.columns):
        return False
    return bool(g.equals(e))


def run_oracle_pandas(code: str | None) -> OracleResult:
    """Run a candidate ``build_ledger`` against ORACLE_CASES_PANDAS. ``hit_trap`` is
    BEHAVIOURAL: a case raising ``'DataFrame' object has no attribute 'append'`` means the
    removed-API dead-end fired. The reference frame is ``pd.DataFrame(list(records))`` (the
    canonical modern construction, single source of truth)."""
    if not PANDAS_OK:
        return OracleResult(passed=False, skipped=True, error=PANDAS_SUBTASK.skip_reason)
    if not code or not code.strip():
        return OracleResult(passed=False, error="no code extracted")
    fn, err = _exec_candidate(code, "build_ledger")
    if fn is None:
        return OracleResult(passed=False, error=err)

    failed: list[str] = []
    hit_trap = False
    for records in ORACLE_CASES_PANDAS:
        expected = _pd.DataFrame(list(records))
        try:
            got = _run_one(fn, records)
        except _Timeout:
            failed.append(repr(records))
            continue
        except AttributeError as e:
            if "has no attribute 'append'" in str(e):
                hit_trap = True
            failed.append(repr(records))
            continue
        except Exception:  # noqa: BLE001
            failed.append(repr(records))
            continue
        if not _frames_equal(got, expected):
            failed.append(repr(records))
    return OracleResult(passed=not failed, failed_cases=failed, hit_trap=hit_trap)


# --------------------------------------------------------------------------- #
# Subtask registry — the probe iterates AVAILABLE_SUBTASKS.
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Subtask:
    key: str                       # "pandas" | "numpy"
    func_name: str                 # "build_ledger" | "to_amounts"
    lib_name: str                  # "pandas" | "numpy"
    available: bool
    version: str | None
    PROMPT: str
    ORACLE_CASES: list
    classify_from_code: Callable[[str | None], "str | None"]
    run_oracle: Callable[[str | None], OracleResult]
    skip_reason: str | None


PANDAS_SUBTASK = Subtask(
    key="pandas", func_name="build_ledger", lib_name="pandas",
    available=PANDAS_OK, version=PANDAS_VERSION,
    PROMPT=_PROMPT_PANDAS,
    ORACLE_CASES=ORACLE_CASES_PANDAS,
    classify_from_code=classify_from_code_pandas,
    run_oracle=run_oracle_pandas,
    skip_reason=None if PANDAS_OK else (
        f"pandas unavailable or < 2.0 (found {PANDAS_VERSION!r}); "
        "DataFrame.append cannot raise -> trap signal invalid"
    ),
)

NUMPY_SUBTASK = Subtask(
    key="numpy", func_name="to_amounts", lib_name="numpy",
    available=NUMPY_OK, version=NUMPY_VERSION,
    PROMPT=_PROMPT_NUMPY,
    ORACLE_CASES=ORACLE_CASES_NUMPY,
    classify_from_code=classify_from_code_numpy,
    run_oracle=run_oracle_numpy,
    skip_reason=None if NUMPY_OK else (
        f"numpy unavailable or < 1.24 (found {NUMPY_VERSION!r}); "
        "np.float/np.int cannot raise -> trap signal invalid"
    ),
)

SUBTASKS: dict[str, Subtask] = {"pandas": PANDAS_SUBTASK, "numpy": NUMPY_SUBTASK}
AVAILABLE_SUBTASKS: list[Subtask] = [s for s in SUBTASKS.values() if s.available]
