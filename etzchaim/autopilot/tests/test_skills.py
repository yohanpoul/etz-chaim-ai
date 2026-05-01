"""Tests for the skill validator."""

from __future__ import annotations

import pytest

from etzchaim.autopilot.skills import (
    FrontmatterError,
    parse_skill_file,
    validate_frontmatter,
)


def test_valid_frontmatter():
    fm = validate_frontmatter(
        {
            "name": "implement-spec",
            "description": "Implements a spec.",
            "version": "0.1.0",
            "metadata": {"etzchaim": {"tags": ["a", "b"]}},
        }
    )
    assert fm.name == "implement-spec"
    assert fm.tags == ["a", "b"]


def test_rejects_invalid_name():
    with pytest.raises(FrontmatterError):
        validate_frontmatter({"name": "BadName!", "description": "x"})


def test_rejects_missing_description():
    with pytest.raises(FrontmatterError):
        validate_frontmatter({"name": "ok-name", "description": ""})


def test_rejects_invalid_version():
    with pytest.raises(FrontmatterError):
        validate_frontmatter(
            {"name": "ok-name", "description": "x", "version": "not-semver"}
        )


def test_parse_real_skill_file(tmp_path):
    skill = tmp_path / "SKILL.md"
    skill.write_text(
        """---
name: example-skill
description: Example.
version: 0.1.0
---

# Body
"""
    )
    fm, body = parse_skill_file(skill)
    assert fm.name == "example-skill"
    assert "Body" in body
