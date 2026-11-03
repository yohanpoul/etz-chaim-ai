"""Offline mechanism proof for the deprecated-API prior-trap task — NO live model.

Proves, deterministically and cheaply, BEFORE paying for a Haiku probe:
  - the AST classifier flags the removed API (DataFrame.append / np.float) while NEVER
    flagging the legitimate ``list.append`` or ``np.float64``;
  - the behavioural oracle FAILS a deprecated-API candidate (and flags hit_trap on the
    AttributeError) and PASSES a current-API one, through the sandboxed guarded importer;
  - code-first key inference works with no APPROACH line;
  - ORACLE_CASES are internally consistent and at least one case is discriminating.

Classifier tests are pure ``ast`` and run unconditionally (no pandas/numpy needed). Oracle
tests are guarded by capability flags: when a library is absent or too old to raise the
AttributeError, the signal is invalid and the test ``pytest.skip``s cleanly — which is the
live state for pandas until it is installed for the probe.
"""

from __future__ import annotations

import sys

import pytest

from benchmarks.gating_harness.task import deprecated_api_trap as task

pandasmark = pytest.mark.skipif(not task.PANDAS_OK, reason="pandas absent / < 2.0")
numpymark = pytest.mark.skipif(not task.NUMPY_OK, reason="numpy absent / < 1.24")


# --------------------------------------------------------------------------- #
# AST classifier — numpy (pure ast, unconditional)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "code,expected",
    [
        ("import numpy as np\ndef to_amounts(v):\n    return np.array(v, dtype=np.float)\n",
         task.DEADEND_APPROACH),
        ("import numpy\ndef to_amounts(v):\n    return numpy.array(v, dtype=numpy.float)\n",
         task.DEADEND_APPROACH),
        ("import numpy as np\ndef to_amounts(v):\n    return np.array(v, dtype=np.int)\n",
         task.DEADEND_APPROACH),
        ("from numpy import float as npf\ndef to_amounts(v):\n    return [npf(x) for x in v]\n",
         task.DEADEND_APPROACH),
        ("import numpy as np\ndef to_amounts(v):\n    return np.array(v, dtype=float)\n",
         task.CORRECT_APPROACH),
        ("import numpy as np\ndef to_amounts(v):\n    return np.asarray(v, dtype='float64')\n",
         task.CORRECT_APPROACH),
        ("import numpy as np\ndef to_amounts(v):\n    return np.array(v, dtype=np.float64)\n",
         task.CORRECT_APPROACH),
        ("import numpy as np\ndef to_amounts(v):\n    return np.array([float(x) for x in v])\n",
         task.CORRECT_APPROACH),
        ("import numpy as np\ndef to_amounts(v):\n    return np.array(v).astype(float)\n",
         task.CORRECT_APPROACH),
    ],
)
def test_classify_numpy(code, expected):
    assert task.classify_from_code_numpy(code) == expected


def test_classify_numpy_bool_not_flagged():
    # np.bool is STILL valid in numpy 2.x -> must NOT be flagged deprecated (no oracle confirm).
    code = "import numpy as np\ndef to_amounts(v):\n    x = np.bool\n    return np.array(v)\n"
    assert task.classify_from_code_numpy(code) is None


def test_classify_numpy_bypass_is_none():
    code = "def to_amounts(v):\n    return [x for x in v]\n"
    assert task.classify_from_code_numpy(code) is None


# --------------------------------------------------------------------------- #
# AST classifier — pandas (pure ast, unconditional). The cardinal case: list.append
# must NEVER be confused with the removed DataFrame.append.
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "code,expected",
    [
        # DataFrame.append (the removed API), various import forms -> deprecated
        ("import pandas as pd\ndef build_ledger(r):\n    df = pd.DataFrame()\n"
         "    for x in r:\n        df = df.append(x, ignore_index=True)\n    return df\n",
         task.DEADEND_APPROACH),
        ("from pandas import DataFrame\ndef build_ledger(r):\n    df = DataFrame()\n"
         "    for x in r:\n        df = df.append(x)\n    return df\n",
         task.DEADEND_APPROACH),
        ("from pandas import DataFrame as DF\ndef build_ledger(r):\n    df = DF()\n"
         "    for x in r:\n        df = df.append(x)\n    return df\n",
         task.DEADEND_APPROACH),
        ("import pandas as pd\ndef build_ledger(r):\n    return pd.DataFrame(r).append({})\n",
         task.DEADEND_APPROACH),  # chained pd.DataFrame(...).append(...)
        ("import pandas as pd\ndef build_ledger(r):\n    df = pd.read_csv('x')\n"
         "    return df.append({})\n",
         task.DEADEND_APPROACH),  # read_* marks df as DataFrame-typed
        # current-API constructions -> correct
        ("import pandas as pd\ndef build_ledger(r):\n    rows = []\n"
         "    for x in r:\n        rows.append(x)\n    return pd.DataFrame(rows)\n",
         task.CORRECT_APPROACH),  # CARDINAL: list.append NOT flagged
        ("import pandas as pd\ndef build_ledger(r):\n    acc = pd.DataFrame()\n"
         "    for x in r:\n        acc = pd.concat([acc, pd.DataFrame([x])])\n    return acc\n",
         task.CORRECT_APPROACH),
        ("import pandas as pd\ndef build_ledger(r):\n    return pd.DataFrame.from_records(r)\n",
         task.CORRECT_APPROACH),
    ],
)
def test_classify_pandas(code, expected):
    assert task.classify_from_code_pandas(code) == expected


def test_classify_pandas_list_append_only_is_none():
    # No DataFrame constructed at all + a list.append -> not the trap, not a df construction.
    code = "def build_ledger(r):\n    rows = []\n    for x in r:\n        rows.append(x)\n    return rows\n"
    assert task.classify_from_code_pandas(code) is None


def test_classify_pandas_local_def_append_not_flagged():
    code = (
        "def append(x):\n    return x\n"
        "def build_ledger(r):\n    return append(r)\n"
    )
    assert task.classify_from_code_pandas(code) is None


# --------------------------------------------------------------------------- #
# Oracle — numpy: trap raises (hit_trap), correct passes, sandbox closed
# --------------------------------------------------------------------------- #


@numpymark
def test_oracle_numpy_trap_raises_and_flags_hit_trap():
    res = task.run_oracle_numpy(
        "import numpy as np\ndef to_amounts(v):\n    return np.array(v, dtype=np.float)\n"
    )
    assert res.passed is False
    assert res.hit_trap is True
    assert res.skipped is False


@numpymark
def test_oracle_numpy_correct_passes():
    res = task.run_oracle_numpy(
        "import numpy as np\ndef to_amounts(v):\n    return np.array(v, dtype=float)\n"
    )
    assert res.passed is True
    assert res.hit_trap is False
    assert res.failed_cases == []


@numpymark
def test_oracle_numpy_from_import_resolves():
    res = task.run_oracle_numpy(
        "from numpy import array\ndef to_amounts(v):\n    return array(v, dtype=float)\n"
    )
    assert res.passed is True


@numpymark
def test_oracle_numpy_missing_func():
    res = task.run_oracle_numpy("import numpy as np\nx = 1\n")
    assert res.passed is False
    assert res.error == "to_amounts not defined"


@numpymark
def test_oracle_numpy_blocks_arbitrary_import():
    res = task.run_oracle_numpy(
        "import os\ndef to_amounts(v):\n    return os.getpid()\n"
    )
    assert res.passed is False
    assert res.error is not None and "error" in res.error.lower()


# --------------------------------------------------------------------------- #
# Oracle — pandas: trap raises (hit_trap), correct passes, sandbox closed
# --------------------------------------------------------------------------- #


@pandasmark
def test_oracle_pandas_trap_raises_and_flags_hit_trap():
    res = task.run_oracle_pandas(
        "import pandas as pd\ndef build_ledger(records):\n    df = pd.DataFrame()\n"
        "    for r in records:\n        df = df.append(r, ignore_index=True)\n    return df\n"
    )
    assert res.passed is False
    assert res.hit_trap is True
    assert res.skipped is False


@pandasmark
def test_oracle_pandas_correct_passes():
    res = task.run_oracle_pandas(
        "import pandas as pd\ndef build_ledger(records):\n    rows = []\n"
        "    for r in records:\n        rows.append(r)\n    return pd.DataFrame(rows)\n"
    )
    assert res.passed is True
    assert res.hit_trap is False
    assert res.failed_cases == []


@pandasmark
def test_oracle_pandas_from_import_resolves():
    res = task.run_oracle_pandas(
        "from pandas import DataFrame\ndef build_ledger(records):\n"
        "    return DataFrame(list(records))\n"
    )
    assert res.passed is True


@pandasmark
def test_oracle_pandas_missing_func():
    res = task.run_oracle_pandas("import pandas as pd\nx = 1\n")
    assert res.passed is False
    assert res.error == "build_ledger not defined"


@pandasmark
def test_oracle_pandas_blocks_arbitrary_import():
    res = task.run_oracle_pandas(
        "import os\ndef build_ledger(records):\n    return os.getpid()\n"
    )
    assert res.passed is False
    assert res.error is not None and "error" in res.error.lower()


# --------------------------------------------------------------------------- #
# Code-first key inference with no APPROACH line (qwen failure-mode parity)
# --------------------------------------------------------------------------- #


def test_infer_numpy_code_first_no_approach_line():
    fixture = (
        "```python\nimport numpy as np\n"
        "def to_amounts(v):\n    return np.array(v, dtype=np.float)\n```\n"
    )
    declared = task.extract_declared_approach(fixture)
    code = task.extract_code(fixture, task.NUMPY_SUBTASK.func_name)
    key = task.infer_approach_key(declared, code, task.NUMPY_SUBTASK)
    assert declared == ""
    assert key == task.DEADEND_APPROACH


def test_infer_pandas_code_first_no_approach_line():
    fixture = (
        "```python\nimport pandas as pd\n"
        "def build_ledger(records):\n    df = pd.DataFrame()\n"
        "    for r in records:\n        df = df.append(r)\n    return df\n```\n"
    )
    code = task.extract_code(fixture, task.PANDAS_SUBTASK.func_name)
    key = task.infer_approach_key(task.extract_declared_approach(fixture), code, task.PANDAS_SUBTASK)
    assert key == task.DEADEND_APPROACH


def test_infer_pandas_list_accumulate_is_correct_not_trap():
    # The most important false-positive guard end-to-end through infer_approach_key.
    fixture = (
        "```python\nimport pandas as pd\n"
        "def build_ledger(records):\n    rows = []\n"
        "    for r in records:\n        rows.append(r)\n    return pd.DataFrame(rows)\n```\n"
    )
    code = task.extract_code(fixture, task.PANDAS_SUBTASK.func_name)
    key = task.infer_approach_key("", code, task.PANDAS_SUBTASK)
    assert key == task.CORRECT_APPROACH


# --------------------------------------------------------------------------- #
# Internal consistency: ORACLE_CASES well-formed and discriminating
# --------------------------------------------------------------------------- #


@numpymark
def test_numpy_oracle_cases_consistent_and_discriminating():
    import numpy as np

    for values, expected in task.ORACLE_CASES_NUMPY:
        ref = np.asarray([float(v) for v in values], dtype=float)
        exp = np.asarray(expected, dtype=float)
        assert ref.shape == exp.shape and np.allclose(ref, exp), f"drift on {values!r}"
    # Every numpy case is discriminating: np.float lookup fails before any data is touched.
    assert len(task.ORACLE_CASES_NUMPY) >= 1


@pandasmark
def test_pandas_oracle_cases_have_discriminating_nonempty():
    nonempty = sum(1 for recs in task.ORACLE_CASES_PANDAS if recs)
    assert nonempty >= 1  # at least one case on which DataFrame.append would raise


def test_module_imports_without_libraries():
    # The module is already imported above; this asserts the capability contract holds:
    # numpy is present in this env, pandas may or may not be, and the module never raised.
    assert "benchmarks.gating_harness.task.deprecated_api_trap" in sys.modules
    assert isinstance(task.NUMPY_OK, bool) and isinstance(task.PANDAS_OK, bool)
