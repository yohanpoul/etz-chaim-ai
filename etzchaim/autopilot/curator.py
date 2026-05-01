"""SkillCurator — idle-tick skill consolidation.

Pattern inspiration : NousResearch/hermes-agent's idle curator (MIT). Our
implementation is much simpler : age-based stale flagging only, no PREFIX
clustering and no LLM consolidation pass. We re-promote stale skills back
to active when they are referenced again.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import time

SKILLS_DIR = Path(__file__).resolve().parent / "skills"
STALE_AFTER_DAYS = 90
ARCHIVE_AFTER_DAYS = 365


@dataclass
class SkillStatus:
    name: str
    age_days: float
    state: str  # active | stale | archived


def _age_days(path: Path) -> float:
    return max((time() - path.stat().st_mtime) / 86400.0, 0.0)


def consolidate_skills() -> list[SkillStatus]:
    """Walk the skills directory and classify by mtime."""
    if not SKILLS_DIR.exists():
        return []

    out: list[SkillStatus] = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name.startswith("_"):
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        age = _age_days(skill_md)
        state = "active"
        if age >= ARCHIVE_AFTER_DAYS:
            state = "archived"
        elif age >= STALE_AFTER_DAYS:
            state = "stale"
        out.append(SkillStatus(name=skill_dir.name, age_days=age, state=state))
    return out
