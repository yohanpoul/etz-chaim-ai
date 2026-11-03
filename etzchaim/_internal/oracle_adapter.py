"""oracle_adapter.py — real (model, code/debug oracle) adapter for SPEC-007.

ÉTAPE 2 of the PredictionGate experiment. This wires real callables into the
ÉTAPE-1 harness WITHOUT changing the analysis layer:

    real model attempt  ─┐
                          ├─►  prediction_gate.Task  ─►  run_arm / refutation_gate
    objective oracle    ─┘        (unchanged)

Design contract (so no token is spent before validation):

* The **model is an injected callable** (`ModelClient.complete`). The offline
  `MockModelClient` spends ZERO tokens; the `AnthropicModelClient` is **lazy** —
  it imports the SDK and authenticates only on the first real `.complete()`.
* The **oracle is objective**: a candidate fix is executed against a reference
  test in a sandboxed subprocess; the *test* decides pass/fail/error. No LLM,
  no self-judgment enters the outcome (SPEC-007 Invariant 3).
* A `pilot` reports only the decision-relevant numbers (see `run_pilot`):
  the real confident-but-wrong rate, A2 precision + false-escalation cost
  (not just recall), and A1-vs-A2 tokens with accuracy for the iso read.

Run offline (mock, no tokens):  python3 -m etzchaim._internal.oracle_adapter
Live run is gated behind ETZCHAIM_PILOT_LIVE=1 + a credential (see __main__).

⚠ Security: `run_oracle` executes candidate code in a subprocess (tmpdir,
timeout, minimal env). Only run against trusted suites / sandboxed hosts.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any

from etzchaim._internal.prediction_gate import ArmResult, Task, run_arm

# Outcomes are in the oracle's own vocabulary (gap() consumes these verbatim).
PASS = "will_pass"
FAIL = "will_fail"


# ─────────────────────────── data types ───────────────────────────
@dataclass(frozen=True)
class Bug:
    """A code/debug task with an objective, WITHHELD reference oracle.

    Shown to the model: `title`, `spec`, `buggy`, `visible`.
    Withheld (the ground truth it must predict against): `test_code`, `reference`.
    `plausible` is the tempting-but-wrong fix, used only to dry-prove the trap.
    """
    id: str
    title: str
    entry: str          # the function name the test imports from `cand`
    buggy: str          # the code the agent is asked to repair (shown)
    reference: str      # a known-good implementation (oracle ground truth — withheld)
    test_code: str      # the full hidden oracle — asserts that decide pass/fail (withheld)
    spec: str = ""      # natural-language contract (shown)
    visible: str = ""   # happy-path examples shown to the model (a subset of the oracle)
    plausible: str = "" # the obvious-but-wrong fix (withheld; dry trap validation only)


@dataclass(frozen=True)
class CallResult:
    text: str
    in_tokens: int
    out_tokens: int
    latency_ms: int = 0


@dataclass
class PilotReport:
    n: int
    model_alias: str
    conf_tau: float
    escalation_cost: float
    # (a) THE number — real confident-but-wrong rate of the agent
    confident_wrong_rate: float
    confident_wrong_count: int
    # (b) precision + the COST of false alarms, not just recall
    a2_precision: float
    a2_recall: float
    a2_false_positives: int
    a2_false_escalation_rate: float
    a2_false_escalation_cost: float
    a1_precision: float
    a1_recall: float
    # (c) tokens A1 vs A2 + accuracies for the iso-accuracy read
    a1_tokens: float
    a2_tokens: float
    accuracy_a1: float
    accuracy_a2: float
    base_tokens: float
    tasks: list[Task] = field(default_factory=list)


# ─────────────────────────── the oracle ───────────────────────────
_EXC_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*(?:Error|Exception|Warning))\b")


def _last_exception_type(stderr: str) -> str | None:
    for line in reversed([ln for ln in stderr.splitlines() if ln.strip()]):
        m = _EXC_RE.match(line.strip())
        if m:
            return m.group(1)
    return None


def run_oracle(candidate_code: str, test_code: str, *, timeout: int = 10) -> str:
    """Execute `candidate_code` as module `cand`, run `test_code` against it in a
    sandboxed subprocess, and return the objective outcome:

        "will_pass"            — the test exited 0
        "will_fail"            — an assertion failed
        "will_error:<Type>"    — an uncaught exception (or "Timeout")

    The oracle — not the model — decides. No self-judgment enters the result.
    """
    with tempfile.TemporaryDirectory() as d:
        dpath = pathlib.Path(d)
        (dpath / "cand.py").write_text(candidate_code)
        (dpath / "run_test.py").write_text(test_code)
        try:
            proc = subprocess.run(
                # -E -s: ignore env vars + user site, but (unlike -I/-P) keep the
                # script dir on sys.path so `import cand` resolves the candidate.
                [sys.executable, "-E", "-s", "run_test.py"],
                cwd=d,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": os.environ.get("PATH", "")},
            )
        except subprocess.TimeoutExpired:
            return "will_error:Timeout"
        if proc.returncode == 0:
            return PASS
        if "AssertionError" in proc.stderr:
            return FAIL
        etype = _last_exception_type(proc.stderr)
        return f"will_error:{etype}" if etype else FAIL


# ─────────────────────────── model clients ───────────────────────────
def _approx_tokens(s: str | None) -> int:
    return max(1, len(s) // 4) if s else 0


class MockModelClient:
    """Offline model — ZERO tokens, ZERO network. Deterministic.

    Resolution order per call:
      1. `forced_per_bug[bug_id]`  — exact payload for a given bug;
      2. `forced`                  — one payload for every call;
      3. seeded synthesis          — a deterministic realistic mix (needs `bugs`
         to emit runnable code; otherwise a trivial wrong fix).

    A payload is ``{"fix": <code>, "prediction": "will_pass"|"will_fail",
    "confidence": 0..1}``.
    """

    def __init__(
        self,
        *,
        forced: dict[str, Any] | None = None,
        forced_per_bug: dict[str, dict[str, Any]] | None = None,
        script: dict[str, Any] | None = None,
        bugs: dict[str, Bug] | None = None,
        seed: int = 0,
    ) -> None:
        self.forced = forced
        self.forced_per_bug = forced_per_bug or {}
        self.script = script or {}
        self.bugs = bugs or {}
        self.seed = seed

    def complete(self, prompt: str, *, system: str | None = None,
                 bug_id: str | None = None) -> CallResult:
        if bug_id is not None and bug_id in self.forced_per_bug:
            payload = self.forced_per_bug[bug_id]
        elif self.forced is not None:
            payload = self.forced
        else:
            payload = self._synth(prompt, bug_id)
        text = json.dumps(payload)
        return CallResult(
            text=text,
            in_tokens=_approx_tokens(prompt) + _approx_tokens(system),
            out_tokens=_approx_tokens(text),
        )

    def _synth(self, prompt: str, bug_id: str | None) -> dict[str, Any]:
        h = int(hashlib.sha256(f"{self.seed}|{bug_id}|{prompt}".encode()).hexdigest(), 16)
        fixes_correctly = (h % 100) < 60          # repairs the bug ~60% of the time
        confident = ((h >> 7) % 100) < 70         # is confident ~70% of the time
        believes_pass = ((h >> 13) % 100) < 80    # predicts its own success ~80%
        bug = self.bugs.get(bug_id) if bug_id else None
        if bug is not None:
            fix = bug.reference if fixes_correctly else bug.buggy
        else:
            fix = "def _missing():\n    return None\n"
        return {
            "fix": fix,
            "prediction": PASS if believes_pass else FAIL,
            "confidence": 0.9 if confident else 0.3,
        }


class AnthropicModelClient:
    """Live model via the project's Anthropic SDK provider — LAZY.

    Constructing this spends nothing: the SDK is imported and authenticated only
    on the first `.complete()` call. The model slug is resolved through the
    single source of truth (`model_registry`), so no model name is hardcoded.
    Token usage is read from `response.usage` (the provider's `generate()`
    discards it, so we call the SDK client directly here).
    """

    def __init__(self, model_alias: str = "haiku", *, profile: str | None = None,
                 client: Any = None, max_tokens: int = 2048,
                 temperature: float = 0.2) -> None:
        self.model_alias = model_alias
        self.profile = profile  # resolve the alias against this profile (None = active)
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._client = client  # None → built lazily on first call

    def _ensure_client(self) -> Any:
        if self._client is None:
            from anthropic import Anthropic  # imported only when truly needed
            self._client = Anthropic()
        return self._client

    def _resolve_slug(self) -> str:
        """Alias → bare API slug via the single source of truth. Falls back to
        the literal alias if the registry doesn't know it (lets a full dated
        slug pass through), mirroring `providers.anthropic_sdk._resolve_slug`."""
        from etzchaim.llm.model_registry import UnknownModelError, resolve_model
        try:
            return resolve_model(self.model_alias, profile=self.profile)
        except UnknownModelError:
            return self.model_alias

    def complete(self, prompt: str, *, system: str | None = None,
                 bug_id: str | None = None) -> CallResult:
        client = self._ensure_client()
        kwargs: dict[str, Any] = {
            "model": self._resolve_slug(),
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        text = "".join(
            b.text for b in resp.content if getattr(b, "type", "text") == "text"
        )
        usage = getattr(resp, "usage", None)
        return CallResult(
            text=text,
            in_tokens=getattr(usage, "input_tokens", 0) or 0,
            out_tokens=getattr(usage, "output_tokens", 0) or 0,
        )


# ─────────────────────────── attempt → Task ───────────────────────────
_SYSTEM = (
    "You repair a single Python function. Return ONLY a JSON object: "
    '{"fix": "<full corrected source of the module>", '
    '"prediction": "will_pass" or "will_fail", '
    '"confidence": <0..1 that your fix passes the hidden test>}. '
    "Commit the prediction before you could know the test result."
)


def _build_prompt(bug: Bug) -> str:
    """Prompt shown to the model. The reference oracle (`test_code`) is WITHHELD
    (SPEC-007 Invariant 1) — only the spec and happy-path examples are shown, so
    the committed prediction is a genuine bet against a result it cannot see."""
    parts = [f"# Task: {bug.title}", ""]
    if bug.spec:
        parts += ["## Specification", bug.spec, ""]
    parts += [
        f"## Current `cand.py` — repair `{bug.entry}`:",
        f"```python\n{bug.buggy}\n```",
        "",
    ]
    if bug.visible:
        parts += [
            f"## Examples you can see (`from cand import {bug.entry}`):",
            f"```python\n{bug.visible}\n```",
            "",
        ]
    parts += [
        "HIDDEN tests — including edge cases NOT shown above — will judge your fix.",
        "Return the JSON from the system prompt; commit your prediction before you "
        "could know the hidden result.",
    ]
    return "\n".join(parts)


def _norm_pred(pred: str) -> str:
    p = (pred or "").lower()
    if "fail" in p:
        return FAIL
    if "error" in p:
        return pred
    return PASS


def _clamp01(x: Any) -> float:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, v))


def _parse_attempt(text: str) -> tuple[str, str, float]:
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            return (
                str(obj.get("fix", "")),
                _norm_pred(str(obj.get("prediction", PASS))),
                _clamp01(obj.get("confidence", 0.5)),
            )
        except (json.JSONDecodeError, AttributeError):
            pass
    return text, PASS, 0.5  # fallback: treat the whole reply as the fix


def attempt_task(bug: Bug, client: Any, *, timeout: int = 10) -> Task:
    """One real attempt → one `Task` consumable by the ÉTAPE-1 harness."""
    r = client.complete(_build_prompt(bug), system=_SYSTEM, bug_id=bug.id)
    fix, pred, conf = _parse_attempt(r.text)
    actual = run_oracle(fix, bug.test_code, timeout=timeout)
    return Task(
        truth=actual,
        is_dead_end=(actual != PASS),
        model_pred=pred,
        model_conf=conf,
        tokens=r.in_tokens + r.out_tokens,
    )


# ─────────────────────────── the pilot ───────────────────────────
def run_pilot(bugs: list[Bug], client: Any, *, conf_tau: float = 0.6,
              model_alias: str = "mock", escalation_cost: float | None = None,
              timeout: int = 10) -> PilotReport:
    """Run every bug once with `client`, then read only the decision-relevant
    metrics. Reuses ÉTAPE 1's `run_arm` for the A1/A2 arithmetic.

    Escalation-cost model (stated, not hidden): an escalation buys one extra
    attempt, costed at `escalation_cost` tokens (default = mean attempt size).
    The accuracy fields come from `run_arm`'s "escalation lets you fix it"
    model — i.e. an UPPER bound on what catching a dead-end can recover; true
    final accuracy needs the re-attempts actually run (deferred to ÉTAPE 3).
    """
    tasks = [attempt_task(b, client, timeout=timeout) for b in bugs]
    n = len(tasks)

    a1: ArmResult = run_arm(tasks, "A1", conf_tau=conf_tau)
    a2: ArmResult = run_arm(tasks, "A2")

    # (a) real confident-but-wrong: the model was confident AND wrong about the outcome
    cw = [t for t in tasks if t.model_conf >= conf_tau and t.model_pred != t.truth]
    # (b) A2 false escalations: it escalated (gap>0) on a step that was NOT a dead-end
    a2_fp = sum(1 for t in tasks if t.model_pred != t.truth and not t.is_dead_end)

    base_tokens = sum(t.tokens for t in tasks)
    esc_cost = escalation_cost if escalation_cost is not None else (base_tokens / n if n else 0.0)
    a1_esc = sum(1 for t in tasks if t.model_conf < conf_tau)           # A1 escalates low conf
    a2_esc = sum(1 for t in tasks if t.model_pred != t.truth)           # A2 escalates on gap

    return PilotReport(
        n=n,
        model_alias=model_alias,
        conf_tau=conf_tau,
        escalation_cost=round(esc_cost, 1),
        confident_wrong_rate=round(len(cw) / n, 3) if n else 0.0,
        confident_wrong_count=len(cw),
        a2_precision=a2.escal_precision,
        a2_recall=a2.escal_recall,
        a2_false_positives=a2_fp,
        a2_false_escalation_rate=round(a2_fp / n, 3) if n else 0.0,
        a2_false_escalation_cost=round(a2_fp * esc_cost, 1),
        a1_precision=a1.escal_precision,
        a1_recall=a1.escal_recall,
        a1_tokens=round(base_tokens + a1_esc * esc_cost, 1),
        a2_tokens=round(base_tokens + a2_esc * esc_cost, 1),
        accuracy_a1=a1.accuracy,
        accuracy_a2=a2.accuracy,
        base_tokens=round(base_tokens, 1),
        tasks=tasks,
    )


# ─────────────────────────── the bug suites ───────────────────────────
def _code(s: str) -> str:
    return s.strip() + "\n" if s else s


def _bug(id: str, title: str, entry: str, buggy: str, reference: str, test_code: str,
         *, spec: str = "", visible: str = "", plausible: str = "") -> Bug:
    return Bug(id=id, title=title, entry=entry, buggy=_code(buggy), reference=_code(reference),
               test_code=_code(test_code), spec=spec.strip(), visible=_code(visible),
               plausible=_code(plausible))


BUG_SUITE: list[Bug] = [
    _bug(
        "off_by_one_sum", "Inclusive sum 1..n", "sum_to",
        "def sum_to(n):\n    return sum(range(1, n))",
        "def sum_to(n):\n    return sum(range(1, n + 1))",
        "from cand import sum_to\nassert sum_to(5) == 15\nassert sum_to(1) == 1",
    ),
    _bug(
        "max_of_list", "Maximum of a list", "max_of",
        "def max_of(xs):\n    return xs[0]",
        "def max_of(xs):\n    return max(xs)",
        "from cand import max_of\nassert max_of([3, 1, 4, 1, 5]) == 5\nassert max_of([-1, -2]) == -1",
    ),
    _bug(
        "is_even", "Even predicate", "is_even",
        "def is_even(n):\n    return n % 2 == 1",
        "def is_even(n):\n    return n % 2 == 0",
        "from cand import is_even\nassert is_even(4) is True\nassert is_even(3) is False",
    ),
    _bug(
        "reverse_string", "Reverse a string", "reverse",
        "def reverse(s):\n    return s",
        "def reverse(s):\n    return s[::-1]",
        "from cand import reverse\nassert reverse('abc') == 'cba'\nassert reverse('') == ''",
    ),
    _bug(
        "fib", "Fibonacci base case", "fib",
        "def fib(n):\n    if n < 2:\n        return 1\n    return fib(n - 1) + fib(n - 2)",
        "def fib(n):\n    if n == 0:\n        return 0\n    if n == 1:\n        return 1\n"
        "    return fib(n - 1) + fib(n - 2)",
        "from cand import fib\nassert fib(0) == 0\nassert fib(7) == 13",
    ),
    _bug(
        "count_vowels", "Count vowels", "count_vowels",
        "def count_vowels(s):\n    return sum(1 for c in s if c == 'a')",
        "def count_vowels(s):\n    return sum(1 for c in s if c in 'aeiou')",
        "from cand import count_vowels\nassert count_vowels('hello') == 2\nassert count_vowels('sky') == 0",
    ),
]


# Adversarial suite — engineered to ELICIT confident-but-wrong, i.e. a fix that
# satisfies the SHOWN examples yet violates the WITHHELD oracle's edge cases.
# Every trap is a real, well-known gotcha (banker's rounding, bool⊆int, falsey
# `or` default, str.strip≠removeprefix, list mutation, lexicographic vs numeric
# sort…). None is contrived to favour A2: the lever is withholding the oracle,
# not pathological inputs. `plausible` = the obvious fix a capable model writes.
ADVERSARIAL_SUITE: list[Bug] = [
    _bug(
        "median_even", "Median of a list", "median",
        "def median(xs):\n    s = sorted(xs)\n    return s[len(s) // 2]",
        "def median(xs):\n    s = sorted(xs)\n    n = len(s)\n    if n % 2:\n        return s[n // 2]\n"
        "    return (s[n // 2 - 1] + s[n // 2]) / 2",
        "from cand import median\nassert median([1, 2, 3, 4]) == 2.5\nassert median([1, 2]) == 1.5\n"
        "assert median([4, 1, 3, 2]) == 2.5\nassert median([1, 3, 2]) == 2",
        spec="median(xs): the median of a non-empty numeric list. For an EVEN count, "
             "return the average of the two middle values (a float).",
        visible="from cand import median\nassert median([1, 3, 2]) == 2\nassert median([5, 1, 3]) == 3",
        plausible="def median(xs):\n    s = sorted(xs)\n    n = len(s)\n    return s[n // 2]",
    ),
    _bug(
        "round_half_up", "Round half up", "round_half",
        "def round_half(x):\n    return round(x)",
        "import math\ndef round_half(x):\n    return math.floor(x + 0.5)",
        "from cand import round_half\nassert round_half(2.5) == 3\nassert round_half(0.5) == 1\n"
        "assert round_half(2.4) == 2\nassert round_half(2.6) == 3",
        spec="round_half(x): round x to the nearest integer, rounding halves UP "
             "(2.5 -> 3, 0.5 -> 1). Return an int.",
        visible="from cand import round_half\nassert round_half(2.4) == 2\nassert round_half(2.6) == 3",
        plausible="def round_half(x):\n    return int(round(x))",
    ),
    _bug(
        "dedupe_order", "Dedupe preserving order", "dedupe",
        "def dedupe(xs):\n    return list(set(xs))",
        "def dedupe(xs):\n    return list(dict.fromkeys(xs))",
        "from cand import dedupe\nassert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]\n"
        "assert dedupe([1, 2, 3]) == [1, 2, 3]",
        spec="dedupe(xs): remove duplicates while preserving first-occurrence order.",
        visible="from cand import dedupe\nassert dedupe([1, 2, 3]) == [1, 2, 3]\nassert dedupe([1, 1, 2]) == [1, 2]",
        plausible="def dedupe(xs):\n    return sorted(set(xs))",
    ),
    _bug(
        "chunk_remainder", "Chunk a list", "chunk",
        "def chunk(xs, k):\n    return [xs[i:i + k] for i in range(0, len(xs) - k + 1, k)]",
        "def chunk(xs, k):\n    return [xs[i:i + k] for i in range(0, len(xs), k)]",
        "from cand import chunk\nassert chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]\n"
        "assert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]",
        spec="chunk(xs, k): split xs into consecutive sublists of length k; the FINAL "
             "sublist may be shorter when k does not divide len(xs).",
        visible="from cand import chunk\nassert chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]\n"
                "assert chunk([1, 2], 2) == [[1, 2]]",
        plausible="def chunk(xs, k):\n    out = []\n    for i in range(0, len(xs) - k + 1, k):\n"
                  "        out.append(xs[i:i + k])\n    return out",
    ),
    _bug(
        "sum_ints_no_bool", "Sum ints, ignore bools", "sum_ints",
        "def sum_ints(xs):\n    return sum(x for x in xs if isinstance(x, int))",
        "def sum_ints(xs):\n    return sum(x for x in xs if type(x) is int)",
        "from cand import sum_ints\nassert sum_ints([1, 2, True, False]) == 3\n"
        "assert sum_ints([True, True]) == 0\nassert sum_ints([1, 'a', 2]) == 3",
        spec="sum_ints(xs): sum only genuine int values. Booleans are NOT integers "
             "here and must be ignored; non-numeric values are ignored too.",
        visible="from cand import sum_ints\nassert sum_ints([1, 2, 3]) == 6\nassert sum_ints([1, 'a', 2]) == 3",
        plausible="def sum_ints(xs):\n    total = 0\n    for x in xs:\n        if isinstance(x, int):\n"
                  "            total += x\n    return total",
    ),
    _bug(
        "getd_falsey", "Dict get with default", "getd",
        "def getd(d, k, default):\n    return d.get(k) or default",
        "def getd(d, k, default):\n    return d[k] if k in d else default",
        "from cand import getd\nassert getd({'a': 0}, 'a', 9) == 0\nassert getd({'a': ''}, 'a', 'x') == ''\n"
        "assert getd({}, 'a', 9) == 9\nassert getd({'a': 5}, 'a', 9) == 5",
        spec="getd(d, k, default): return d[k] when k is a key of d — EVEN if the value "
             "is falsey (0, '', False) — otherwise return default.",
        visible="from cand import getd\nassert getd({'a': 5}, 'a', 9) == 5\nassert getd({}, 'a', 9) == 9",
        plausible="def getd(d, k, default):\n    v = d.get(k)\n    return v if v else default",
    ),
    _bug(
        "remove_prefix", "Remove a leading prefix", "rmpre",
        "def rmpre(s, prefix):\n    return s.lstrip(prefix)",
        "def rmpre(s, prefix):\n    return s[len(prefix):] if s.startswith(prefix) else s",
        "from cand import rmpre\nassert rmpre('aabbaa_data', 'aab') == 'baa_data'\n"
        "assert rmpre('banana', 'ban') == 'ana'\nassert rmpre('aab_x', 'aab') == '_x'\n"
        "assert rmpre('hello', 'xyz') == 'hello'",
        spec="rmpre(s, prefix): if s starts with prefix, return s with that leading "
             "prefix removed ONCE; otherwise return s unchanged. Only a full leading "
             "match is removed — never arbitrary characters.",
        visible="from cand import rmpre\nassert rmpre('aab_x', 'aab') == '_x'\nassert rmpre('hello', 'xyz') == 'hello'",
        plausible="def rmpre(s, prefix):\n    return s.strip(prefix)",
    ),
    _bug(
        "add_immutable", "Append without mutating", "add",
        "def add(xs, x):\n    xs.append(x)\n    return xs",
        "def add(xs, x):\n    return xs + [x]",
        "from cand import add\norig = [1, 2]\nr = add(orig, 3)\nassert r == [1, 2, 3]\n"
        "assert orig == [1, 2]\ne = []\nadd(e, 9)\nassert e == []",
        spec="add(xs, x): return a NEW list equal to xs with x appended. Must NOT "
             "modify the caller's list.",
        visible="from cand import add\nassert add([1, 2], 3) == [1, 2, 3]\nassert add([], 1) == [1]",
        plausible="def add(xs, x):\n    xs.append(x)\n    return list(xs)",
    ),
    _bug(
        "avg_empty", "Average with empty guard", "avg",
        "def avg(xs):\n    return sum(xs) / len(xs)",
        "def avg(xs):\n    return sum(xs) / len(xs) if xs else 0.0",
        "from cand import avg\nassert avg([]) == 0.0\nassert avg([2, 4]) == 3.0\nassert avg([5]) == 5.0",
        spec="avg(xs): arithmetic mean of xs as a float. For an EMPTY list return 0.0 "
             "(must not raise).",
        visible="from cand import avg\nassert avg([2, 4]) == 3.0\nassert avg([5]) == 5.0",
        plausible="def avg(xs):\n    total = sum(xs)\n    return total / len(xs)",
    ),
    _bug(
        "numsort", "Numeric sort of numeric strings", "numsort",
        "def numsort(xs):\n    return sorted(xs)",
        "def numsort(xs):\n    return sorted(xs, key=int)",
        "from cand import numsort\nassert numsort(['10', '9', '2']) == ['2', '9', '10']\n"
        "assert numsort(['3', '1', '2']) == ['1', '2', '3']",
        spec="numsort(xs): given strings that each represent an integer, return them "
             "sorted in ascending NUMERIC order (not lexicographic).",
        visible="from cand import numsort\nassert numsort(['1', '2', '3']) == ['1', '2', '3']\n"
                "assert numsort(['3', '1', '2']) == ['1', '2', '3']",
        plausible="def numsort(xs):\n    return list(sorted(xs))",
    ),
]


_SUITES: dict[str, list[Bug]] = {"easy": BUG_SUITE, "adversarial": ADVERSARIAL_SUITE}


def _select_suite() -> tuple[str, list[Bug]]:
    name = os.environ.get("ETZCHAIM_PILOT_SUITE", "adversarial")
    return name, _SUITES.get(name, ADVERSARIAL_SUITE)


# ─────────────────────────── report printer / demo / live gate ───────────────────────────
def _print_report(rep: PilotReport, header: str) -> None:
    """Print ONLY the three decision groups. Never prints any credential."""
    print(header)
    print(f"  bugs n={rep.n}  model={rep.model_alias}  conf_tau={rep.conf_tau}  "
          f"esc_cost={rep.escalation_cost} tok")
    print(f"  (a) confident-but-wrong rate = {rep.confident_wrong_rate} "
          f"({rep.confident_wrong_count}/{rep.n})   ← THE number")
    print(f"  (b) A2 precision={rep.a2_precision}  recall={rep.a2_recall}  "
          f"false-escalations={rep.a2_false_positives} "
          f"(rate={rep.a2_false_escalation_rate}, cost={rep.a2_false_escalation_cost} tok)")
    print(f"      A1 precision={rep.a1_precision}  recall={rep.a1_recall}")
    print(f"  (c) tokens A1={rep.a1_tokens}  A2={rep.a2_tokens}  base={rep.base_tokens}  "
          f"| acc A1={rep.accuracy_a1}  A2={rep.accuracy_a2}")


def _demo() -> None:
    """Offline dry-run: mock model + real oracle. ZERO tokens. Shows the exact
    report shape the live pilot will emit (numbers here are synthetic)."""
    name, suite = _select_suite()
    client = MockModelClient(seed=0, bugs={b.id: b for b in suite})
    rep = run_pilot(suite, client, conf_tau=0.6, model_alias=f"mock/{name}")
    _print_report(rep, f"── PILOT (OFFLINE MOCK — suite={name}, synthetic, zero tokens) ──")
    print("  NOTE: mock numbers. Real numbers require a live GO (see header).")


def _live_pilot() -> PilotReport:
    """Live pilot — gated. Requires ETZCHAIM_PILOT_LIVE=1 and a non-empty key.

    The key guard fires BEFORE any client is built or any call is made, and
    never prints the key — only whether it is loaded and its length.
    """
    if os.environ.get("ETZCHAIM_PILOT_LIVE") != "1":
        raise SystemExit("Live pilot disabled. Set ETZCHAIM_PILOT_LIVE=1 to spend tokens.")
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key.strip():
        raise SystemExit(
            "ANTHROPIC_API_KEY is empty/unset — aborting BEFORE any API call.\n"
            "Create .env at the repo root with ANTHROPIC_API_KEY=... then run, "
            "from the repo root:\n"
            "  set -a; . ./.env; set +a\n"
            "  ETZCHAIM_PILOT_LIVE=1 .venv/bin/python -m etzchaim._internal.oracle_adapter"
        )
    print(f"✓ ANTHROPIC_API_KEY loaded (non-empty, {len(key.strip())} chars) — key never printed.")
    alias = os.environ.get("ETZCHAIM_PILOT_MODEL", "haiku")
    # anthropic_full maps haiku → anthropic/claude-haiku-4-5 (a real API slug);
    # the active profile (claude_max) only has CLI aliases the API rejects.
    profile = os.environ.get("ETZCHAIM_PILOT_PROFILE", "anthropic_full")
    name, suite = _select_suite()
    client = AnthropicModelClient(model_alias=alias, profile=profile)
    rep = run_pilot(suite, client, conf_tau=0.6, model_alias=f"{alias}@{profile}/{name}")
    _print_report(rep, f"── PILOT (LIVE — {alias}@{profile}, suite={name}, real tokens) ──")
    print("  NOTE: smallest model = CEILING, not the prod verdict. Edge NOT claimed; "
          "real verdict is ÉTAPE 3 on the prod model.")
    return rep


if __name__ == "__main__":
    if os.environ.get("ETZCHAIM_PILOT_LIVE") == "1":
        _live_pilot()
    else:
        _demo()
