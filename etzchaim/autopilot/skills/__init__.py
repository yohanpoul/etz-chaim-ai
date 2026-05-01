"""Autopilot skills — markdown definitions invoked by the worker.

Each skill is a directory containing `SKILL.md` with YAML frontmatter and
markdown body. The validator enforces a small schema:

```yaml
---
name: <kebab-case-name>          # required
description: <one-liner>         # required, <=512 chars
version: <semver>                # required
license: <SPDX>                  # default MIT
metadata:
  etzchaim:                      # our namespace, not 'hermes:'
    tags: [list]
    related_skills: [list]
---
```

Skills are not the same as Claude Code's built-in skills; they are
autopilot-specific procedural prompts.
"""

from __future__ import annotations

from etzchaim.autopilot.skills._validator import (
    FrontmatterError,
    SkillFrontmatter,
    parse_skill_file,
    validate_frontmatter,
)

__all__ = [
    "FrontmatterError",
    "SkillFrontmatter",
    "parse_skill_file",
    "validate_frontmatter",
]
