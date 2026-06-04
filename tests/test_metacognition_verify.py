from __future__ import annotations

import sys


def test_verify_records_pass_fail(tmp_path):
    from etzchaim.metacognition.verify import run_verification

    passed = run_verification(
        [sys.executable, "-c", "print('ok')"],
        cwd=tmp_path,
        timeout_seconds=5,
    )
    failed = run_verification(
        [sys.executable, "-c", "import sys; print('bad'); sys.exit(3)"],
        cwd=tmp_path,
        timeout_seconds=5,
    )

    assert passed["passed"] is True
    assert passed["exit_code"] == 0
    assert "ok" in passed["stdout"]
    assert failed["passed"] is False
    assert failed["exit_code"] == 3
    assert "bad" in failed["stdout"]
    assert passed["duration_seconds"] >= 0


def test_verify_forces_pytest_through_venv_python(monkeypatch, tmp_path):
    from etzchaim.metacognition import verify

    seen = {}

    class Completed:
        returncode = 0
        stdout = "pytest 9"
        stderr = ""

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    result = verify.run_verification(["pytest", "--version"], cwd=tmp_path)

    assert result["passed"] is True
    assert seen["command"][:3] == [".venv/bin/python", "-m", "pytest"]
    assert result["command"] == ".venv/bin/python -m pytest --version"


def test_verify_makes_pytest_environment_read_only(monkeypatch, tmp_path):
    from etzchaim.metacognition import verify

    seen = {}

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["env"] = kwargs["env"]
        return Completed()

    monkeypatch.setenv("PYTEST_ADDOPTS", "--strict-markers")
    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    result = verify.run_verification(["pytest", "tests/example.py", "-q"], cwd=tmp_path)

    assert result["passed"] is True
    assert seen["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert seen["env"]["PYTEST_ADDOPTS"] == "--strict-markers -p no:cacheprovider"


def test_verify_sets_psql_override_for_launchd_pytest(monkeypatch, tmp_path):
    from etzchaim.metacognition import verify

    seen = {}

    class Completed:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        seen["env"] = kwargs["env"]
        return Completed()

    def fake_which(command, path=None):
        if command == "psql" and path and "/opt/homebrew/bin" in path:
            return "/opt/homebrew/bin/psql"
        return None

    monkeypatch.delenv("ETZ_PSQL_BIN", raising=False)
    monkeypatch.setenv("PATH", "/bin:/usr/bin")
    monkeypatch.setattr(verify.shutil, "which", fake_which)
    monkeypatch.setattr(verify.subprocess, "run", fake_run)

    result = verify.run_verification(["pytest", "tests/example.py", "-q"], cwd=tmp_path)

    assert result["passed"] is True
    assert seen["env"]["ETZ_PSQL_BIN"] == "/opt/homebrew/bin/psql"
    assert "/opt/homebrew/bin" in seen["env"]["PATH"]
