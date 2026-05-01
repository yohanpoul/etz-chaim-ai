"""Commit creation with neutral messages enforced."""

from __future__ import annotations

import re

from etzchaim.autopilot.runners.local import LocalRunner

_runner = LocalRunner()

# Reuse the public-surface forbidden term list (same pattern as the shell
# scanner). Hard-coded subset for fast in-process check; full check stays
# in scripts/check_public_surface.sh.
_FORBIDDEN_PATTERN = re.compile(
    r"\b(sephir|keter|chokmah|binah|chesed|gevurah|tiferet|netzach|hod|"
    r"yesod|malkuth|partzuf|abba|imma|nukva|tikkun|reshim|hitlabshut|"
    r"hitkalelut|zivvug|tzimtzum|sitra\s+achra|kabbal|lurianic|zohar|"
    r"vital|cordovero|luria|sifrei\s+yesod|mazal)\b",
    re.IGNORECASE,
)


def assert_neutral(text: str, what: str = "commit message") -> None:
    """Raise if the text contains forbidden terminology."""
    match = _FORBIDDEN_PATTERN.search(text)
    if match:
        raise ValueError(
            f"{what} contains forbidden term {match.group(0)!r}; "
            "neutralize before continuing"
        )


def commit_changes(
    title: str,
    body: str = "",
    paths: list[str] | None = None,
    cwd: str | None = None,
) -> str:
    """Stage paths and commit with a neutral message. Returns commit SHA."""
    assert_neutral(title, "commit title")
    if body:
        assert_neutral(body, "commit body")

    if paths:
        for p in paths:
            res = _runner.dispatch(["git", "add", "--", p], cwd=cwd, timeout=30)
            if not res.success:
                raise RuntimeError(f"git add {p} failed: {res.stderr}")
    else:
        res = _runner.dispatch(["git", "add", "-A"], cwd=cwd, timeout=60)
        if not res.success:
            raise RuntimeError(f"git add -A failed: {res.stderr}")

    full_message = title if not body else f"{title}\n\n{body}"
    res = _runner.dispatch(
        ["git", "commit", "-m", full_message], cwd=cwd, timeout=60
    )
    if not res.success:
        raise RuntimeError(f"git commit failed: {res.stderr}")

    sha_res = _runner.dispatch(["git", "rev-parse", "HEAD"], cwd=cwd, timeout=10)
    if not sha_res.success:
        raise RuntimeError(f"git rev-parse HEAD failed: {sha_res.stderr}")
    return sha_res.stdout.strip()
