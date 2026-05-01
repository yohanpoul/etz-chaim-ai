"""Pull request creation via `gh pr create`."""

from __future__ import annotations

from etzchaim.autopilot.git_integration.commit import assert_neutral
from etzchaim.autopilot.runners.local import LocalRunner

_runner = LocalRunner()


def open_pr(
    title: str,
    body: str,
    base: str = "main",
    cwd: str | None = None,
    push: bool = True,
) -> str:
    """Push the current branch (optional) and open a PR. Returns the URL."""
    assert_neutral(title, "PR title")
    assert_neutral(body, "PR body")

    if push:
        push_res = _runner.dispatch(
            ["git", "push", "-u", "origin", "HEAD"], cwd=cwd, timeout=120
        )
        if not push_res.success:
            raise RuntimeError(f"git push failed: {push_res.stderr}")

    res = _runner.dispatch(
        ["gh", "pr", "create", "--base", base, "--title", title, "--body", body],
        cwd=cwd,
        timeout=120,
    )
    if not res.success:
        raise RuntimeError(f"gh pr create failed: {res.stderr}")
    return res.stdout.strip().splitlines()[-1]
