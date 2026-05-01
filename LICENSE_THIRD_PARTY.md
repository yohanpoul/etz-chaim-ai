# Third-Party Inspirations & Attributions

This project draws **architectural inspiration** from third-party open-source
projects. No code is copied verbatim — patterns are reimplemented from scratch
under our own naming and structure. We acknowledge inspirations as a courtesy.

## NousResearch / hermes-agent (MIT)

**Repository** : https://github.com/NousResearch/hermes-agent
**License** : MIT
**Copyright** : © 2025 Nous Research

The `etzchaim/autopilot/` module's high-level architecture takes inspiration
from `hermes-agent`'s approach to autonomous agent loops. We re-implemented
the patterns under our own naming conventions, file structure, and design
decisions. No verbatim code translation.

| Etz Chaim AI artifact | Hermes-agent pattern (inspiration only) |
|----------------------|------------------------------------------|
| `etzchaim/autopilot/skills/_validator.py` | YAML frontmatter validation for skill metadata |
| `etzchaim/autopilot/delegation/subagent.py` | ThreadPool-based isolated worker spawning with restricted tool surface |
| `etzchaim/autopilot/memory/snapshot.py` | Frozen-context-snapshot pattern preserving prompt-cache prefixes |
| `etzchaim/autopilot/memory/search.py` | SQLite FTS5 historical session retrieval with LLM-assisted summarization |
| `etzchaim/autopilot/memory/trajectory.py` | ShareGPT-style conversation logging for downstream training data |
| `etzchaim/autopilot/runners/local.py` | Subprocess execution abstraction with timeout + result capture |
| `etzchaim/autopilot/curator.py` | Idle-triggered automatic skill consolidation and age-based archival |

Our implementation diverges from Hermes-agent in :
- **Naming** : all classes, functions, variables, and files use Etz Chaim AI
  conventions, not Hermes-agent identifiers
- **Architecture** : tightly integrated with our existing daemon (`daemon.py`)
  rather than standalone agent runtime
- **Memory** : `~/.etz-chaim/autopilot/context.md` + `operator.md` (not Hermes'
  `MEMORY.md` / `USER.md`)
- **Skill format** : our SKILL.md frontmatter uses `etzchaim:` namespace, not
  `hermes:` — different schema fields, validation rules
- **License surface** : skills + tools are framework-agnostic, work standalone
  inside our daemon

### MIT License (preserved as courtesy)

```
MIT License

Copyright (c) 2025 Nous Research

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## NousResearch / hermes-agent-self-evolution (MIT)

**Repository** : https://github.com/NousResearch/hermes-agent-self-evolution
**License** : MIT

Architectural inspiration only for future evolution loop work (Phase 2+).
No code currently incorporated.

---

## Naming convention enforcement

To avoid confusion or implied endorsement :
- No file in `etzchaim/autopilot/` shares a filename with a Hermes-agent file
- No class name matches a Hermes-agent class name
- Public APIs and CLI commands use Etz Chaim AI naming throughout

---

## Other third-party dependencies

See `pyproject.toml` for the full list of Python dependencies and their
respective licenses (PyPI metadata).
