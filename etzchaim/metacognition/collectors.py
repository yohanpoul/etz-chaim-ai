"""Safe local collectors for the Phase 1A improve command."""

from __future__ import annotations

import json
import re
import shutil
from collections.abc import Callable, Iterable
from pathlib import Path

from etzchaim.cli import compose, detect
from etzchaim.cli.doctor.checks import (
    check_compose_services_up,
    check_docker_running,
    check_postgres_healthy,
)
from etzchaim.metacognition.events import MetacognitionEvent
from etzchaim.metacognition.verify import run_verification

DOCTOR_CHECKS: list[tuple[str, Callable[[], tuple[bool, str]]]] = [
    ("docker_running", check_docker_running),
    ("compose_services_up", check_compose_services_up),
    ("postgres_healthy", check_postgres_healthy),
]

DEFAULT_PYTEST_PATHS: tuple[str, ...] = (
    "tests/test_install/test_psql_helper.py",
    "sifrei_yesod/tests/test_folio_map.py",
    "sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s1_each_tikkun_has_zohar_and_vital",
    "sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s3_see_also_bidirectional",
)
KNOWN_P0_PSQL_COMMAND: tuple[str, ...] = (
    ".venv/bin/python",
    "-m",
    "pytest",
    "tests/test_install/test_psql_helper.py",
    "sifrei_yesod/tests/test_folio_map.py",
    "-q",
)


def _slug(value: str) -> str:
    return value.replace("_", "-").lower()


def collect_doctor_events() -> list[MetacognitionEvent]:
    events: list[MetacognitionEvent] = []
    for name, check in DOCTOR_CHECKS:
        try:
            ok, message = check()
        except Exception as exc:
            ok = False
            message = f"doctor check raised {type(exc).__name__}: {exc}"
        if ok:
            continue
        slug = _slug(name)
        priority = 85 if "postgres" in name else 75 if "docker" in name else 60
        severity = "error" if "postgres" in name else "warning"
        events.append(
            MetacognitionEvent(
                id=f"doctor-{slug}",
                source="doctor",
                severity=severity,
                title=f"Doctor check failed: {slug}",
                description=message,
                evidence=[message],
                priority=priority,
                verification_command=".venv/bin/etzchaim doctor --json",
            )
        )
    return events


def _parse_compose_ps(raw: str) -> list[dict]:
    raw = raw.strip()
    if not raw:
        return []
    if raw.startswith("["):
        return json.loads(raw)
    return [json.loads(line) for line in raw.splitlines() if line.strip()]


def collect_status_events() -> list[MetacognitionEvent]:
    profile = detect.detect_compose_profile()
    services: list[dict] = []
    evidence: list[str] = [f"profile={profile}"]
    if compose.compose_dir().exists():
        try:
            raw = compose.compose_ps(profile=profile)
            services = _parse_compose_ps(raw)
            evidence.append(f"services={len(services)}")
        except Exception as exc:
            evidence.append(f"compose ps raised {type(exc).__name__}: {exc}")
    else:
        evidence.append("compose directory is absent")

    if services:
        return []
    return [
        MetacognitionEvent(
            id="status-no-services-running",
            source="status",
            severity="warning",
            title="No Etz Chaim services are running",
            description=(
                "The status surface reports no running services; Phase 1A treats this "
                "as an observation, not a reason to start Docker/PostgreSQL."
            ),
            evidence=evidence,
            priority=45,
            verification_command=".venv/bin/etzchaim status --json",
        )
    ]


def collect_python_events() -> list[MetacognitionEvent]:
    if shutil.which("python") is not None:
        return []
    return [
        MetacognitionEvent(
            id="python-command-missing",
            source="python",
            severity="warning",
            title="python command is not available",
            description=(
                "The shell cannot resolve `python`; use `.venv/bin/python` or "
                "`python3` until packaging/setup is reconciled."
            ),
            evidence=["python was not found on PATH"],
            priority=30,
            verification_command="python --version",
        )
    ]


def collect_known_p0_events(
    repo_root: Path | str,
    runner: Callable[[list[str], Path, int], dict] = run_verification,
) -> list[MetacognitionEvent]:
    root = Path(repo_root)
    report_path = (
        root
        / "strategy"
        / "codex-prompt"
        / "codex-plan"
        / "etzchaim-p0-preflight.md"
    )
    if not report_path.exists():
        return []
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError:
        return []
    if "/my/psql" not in text:
        return []

    command = list(KNOWN_P0_PSQL_COMMAND)
    result = runner(command, root, 30)
    output = "\n".join(
        part for part in (result.get("stdout", ""), result.get("stderr", "")) if part
    )
    if result.get("passed") is True or "/my/psql" not in output:
        return []

    return [
        MetacognitionEvent(
            id="known-p0-psql-helper-pollution",
            source="p0-preflight",
            severity="error",
            title="Known /my/psql test helper pollution",
            description=(
                "P0 reproduced an inter-test pollution where the psql helper kept "
                "`/my/psql` after a helper test; the current reproduction still fails."
            ),
            evidence=[
                f"{report_path}: contains /my/psql reproduction notes",
                *_summarize_pytest_output(result),
            ],
            priority=100,
            verification_command=str(result.get("command") or " ".join(command)),
            verified=False,
            verification_result=result,
        )
    ]


def _summarize_pytest_output(result: dict) -> list[str]:
    output = "\n".join(
        part for part in (result.get("stdout", ""), result.get("stderr", "")) if part
    )
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return ["pytest exited without captured output"]
    interesting = [
        line
        for line in lines
        if line.startswith("FAILED ")
        or " failed" in line
        or " error" in line
        or "AssertionError" in line
    ]
    return (interesting or lines)[:8]


MISSING_TIKKUNIM_RE = re.compile(
    r"Tikkunim missing \(other than expected T11\): (?P<missing>\[[^\]]+\])"
)
NON_BIDIRECTIONAL_RE = re.compile(
    r"Non-bidirectional: (?P<source>\S+)(?:→|->)(?P<target>\S+) "
    r"but not (?P=target)(?:→|->)(?P=source)"
)


def _diagnose_pytest_corpus_gate(result: dict) -> tuple[str, str, list[str]] | None:
    output = "\n".join(
        part for part in (result.get("stdout", ""), result.get("stderr", "")) if part
    )
    missing_match = MISSING_TIKKUNIM_RE.search(output)
    non_bidir_matches = list(NON_BIDIRECTIONAL_RE.finditer(output))
    non_bidir_match = next(
        (
            match
            for match in non_bidir_matches
            if "{" not in match.group("source")
            and "}" not in match.group("source")
            and "{" not in match.group("target")
            and "}" not in match.group("target")
        ),
        None,
    )
    if not missing_match and not non_bidir_match:
        return None

    evidence = ["diagnostic_category=corpus-gate"]
    suffix_parts: list[str] = []
    title_parts: list[str] = []
    if missing_match:
        evidence.append(
            f"missing_tikkunim_unexpected={missing_match.group('missing')}"
        )
        suffix_parts.append("missing-tikkunim")
        title_parts.append("missing tikkunim")
    if non_bidir_match:
        source = non_bidir_match.group("source")
        target = non_bidir_match.group("target")
        evidence.append(
            f"non_bidirectional_first={source}→{target} missing reciprocal"
        )
        suffix_parts.append("non-bidir-links")
        title_parts.append("non-bidirectional links")

    event_id = f"pytest-corpus-gate-{'-'.join(suffix_parts)}"
    title = f"Corpus gate pytest failed: {' and '.join(title_parts)}"
    return event_id, title, evidence


def collect_pytest_events(
    repo_root: Path | str,
    paths: Iterable[str] = DEFAULT_PYTEST_PATHS,
    runner: Callable[[list[str], Path, int], dict] = run_verification,
) -> list[MetacognitionEvent]:
    root = Path(repo_root)
    selected_paths = list(paths)
    command = [".venv/bin/python", "-m", "pytest", *selected_paths, "-q"]
    result = runner(command, root, 30)
    if result.get("passed") is True:
        return []
    diagnostic = _diagnose_pytest_corpus_gate(result)
    if diagnostic:
        event_id, title, diagnostic_evidence = diagnostic
        description = (
            "The bounded pytest subset reached a source-backed corpus gate: "
            "the Idra corpus is incomplete or has asymmetric `see_also` links. "
            "P2A observes this as a verification signal and does not repair "
            "corpus content automatically."
        )
        evidence = [*diagnostic_evidence, *_summarize_pytest_output(result)]
    else:
        event_id = "pytest-bounded-subset-failed"
        title = "Bounded pytest observer found failures"
        description = (
            "A bounded read-only pytest subset failed. P2A observes this as a "
            "verification signal and does not repair corpus or services."
        )
        evidence = _summarize_pytest_output(result)
    return [
        MetacognitionEvent(
            id=event_id,
            source="pytest",
            severity="error" if result.get("exit_code") not in (None, 0) else "warning",
            title=title,
            description=description,
            evidence=evidence,
            priority=95,
            verification_command=str(result.get("command") or " ".join(command)),
            verified=False,
            verification_result=result,
        )
    ]


def _collect_known_p0(repo_root: Path) -> list[MetacognitionEvent]:
    return collect_known_p0_events(repo_root)


def _collect_doctor(_repo_root: Path) -> list[MetacognitionEvent]:
    return collect_doctor_events()


def _collect_status(_repo_root: Path) -> list[MetacognitionEvent]:
    return collect_status_events()


def _collect_python(_repo_root: Path) -> list[MetacognitionEvent]:
    return collect_python_events()


def _collect_pytest(repo_root: Path) -> list[MetacognitionEvent]:
    return collect_pytest_events(repo_root)


COLLECTORS: list[Callable[[Path], Iterable[MetacognitionEvent]]] = [
    _collect_known_p0,
    _collect_doctor,
    _collect_status,
    _collect_python,
    _collect_pytest,
]


def collect_events(repo_root: Path | str | None = None) -> list[MetacognitionEvent]:
    root = Path(repo_root or Path.cwd())
    events: list[MetacognitionEvent] = []
    for collector in COLLECTORS:
        try:
            events.extend(list(collector(root)))
        except Exception as exc:
            events.append(
                MetacognitionEvent(
                    id=f"collector-{collector.__name__.strip('_').replace('_', '-')}-failed",
                    source="collector",
                    severity="warning",
                    title="Metacognition collector failed",
                    description=f"{collector.__name__} raised {type(exc).__name__}: {exc}",
                    evidence=[repr(exc)],
                    priority=10,
                    verification_command=".venv/bin/etzchaim improve --once --dry-run --json",
                )
            )
    by_id = {event.id: event for event in events}
    return sorted(by_id.values(), key=lambda event: (-event.priority, event.id))
