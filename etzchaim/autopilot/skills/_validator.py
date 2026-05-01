"""Frontmatter validator for autopilot skills.

Independently authored. Inspiration credit: NousResearch/hermes-agent (MIT) —
the idea of a strict frontmatter validator over markdown skill files. Our
namespace is `etzchaim:` (not `hermes:`), our schema fields differ, and our
parser is independent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Constraints
MAX_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 512
MAX_BODY_CHARS = 100_000
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")


class FrontmatterError(ValueError):
    """Raised when a skill file's frontmatter is invalid."""


@dataclass
class SkillFrontmatter:
    name: str
    description: str
    version: str = "0.1.0"
    license: str = "MIT"
    tags: list[str] = field(default_factory=list)
    related_skills: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Return (frontmatter_yaml, body) or raise."""
    if not text.startswith("---\n"):
        raise FrontmatterError("file must start with '---' frontmatter delimiter")
    rest = text[4:]
    end = rest.find("\n---\n")
    if end < 0:
        raise FrontmatterError("frontmatter has no closing '---'")
    return rest[:end], rest[end + 5 :]


def validate_frontmatter(doc: dict) -> SkillFrontmatter:
    """Validate a parsed frontmatter dict."""
    name = doc.get("name")
    if not isinstance(name, str) or not NAME_PATTERN.match(name):
        raise FrontmatterError(
            f"`name` must match {NAME_PATTERN.pattern}, got {name!r}"
        )

    description = doc.get("description")
    if not isinstance(description, str) or not description.strip():
        raise FrontmatterError("`description` is required and must be non-empty")
    if len(description) > MAX_DESCRIPTION_LEN:
        raise FrontmatterError(
            f"`description` is {len(description)} chars, max {MAX_DESCRIPTION_LEN}"
        )

    version = doc.get("version", "0.1.0")
    if not isinstance(version, str) or not SEMVER_PATTERN.match(version):
        raise FrontmatterError(f"`version` must be semver, got {version!r}")

    license_str = doc.get("license", "MIT")
    if not isinstance(license_str, str):
        raise FrontmatterError("`license` must be a string")

    metadata = doc.get("metadata") or {}
    etzchaim_meta = metadata.get("etzchaim") or {}
    tags = list(etzchaim_meta.get("tags") or [])
    related = list(etzchaim_meta.get("related_skills") or [])

    return SkillFrontmatter(
        name=name,
        description=description.strip(),
        version=version,
        license=license_str,
        tags=tags,
        related_skills=related,
        raw=doc,
    )


def parse_skill_file(path: str | Path) -> tuple[SkillFrontmatter, str]:
    """Parse a SKILL.md file and return (frontmatter, body).

    Raises FrontmatterError on validation issues.
    """
    p = Path(path)
    if not p.is_file():
        raise FrontmatterError(f"file not found: {p}")

    text = p.read_text(encoding="utf-8")
    if len(text) > MAX_BODY_CHARS:
        raise FrontmatterError(
            f"file is {len(text)} chars, max {MAX_BODY_CHARS}"
        )

    fm_yaml, body = _split_frontmatter(text)
    try:
        doc = yaml.safe_load(fm_yaml) or {}
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"invalid YAML in frontmatter: {exc}") from exc

    if not isinstance(doc, dict):
        raise FrontmatterError("frontmatter must be a mapping")

    return validate_frontmatter(doc), body
