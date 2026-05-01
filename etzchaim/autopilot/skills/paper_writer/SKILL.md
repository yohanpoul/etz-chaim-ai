---
name: paper-writer
description: Drafts one section of the arXiv paper per cycle. Reads section outline + recent benchmark results, produces a paper section in `paper/sections/`, opens a PR. Does not modify the theoretical contribution sections (those are operator-only).
version: 0.1.0
license: MIT
metadata:
  etzchaim:
    tags: [paper, drafting, arXiv]
    related_skills: [validate-edge]
---

# Paper Writer

## Overview

Drafts one paper section per autopilot cycle invocation. Eight target
sections plus appendices. Mechanical sections (related work, experiments,
implementation, datasets, hyperparameters) are autopilot-eligible. The
theoretical contribution section is operator-only.

## When to use

Invoked by `daemon_tasks/paper_draft.py` daily (default 24h interval).

## Sections eligible for autopilot

| # | Title | Source data |
|---|-------|-------------|
| 4 | Related work | ML/agent paper bibliography |
| 5 | Implementation | code structure + module list |
| 6 | Experiments | latest edge validation report |
| 7 | Results | latest edge metric values + plots |
| Appendix B | Datasets | suite dataset hashes |
| Appendix C | Hyperparameters | autopilot config snapshot |

## Sections NOT eligible (operator-only)

- 1. Introduction
- 2. Cognitive OS framework theory
- 3. Formal definitions
- 8. Discussion + Limitations
- Appendix A — Historical Note

## Steps

1. Read `paper/sections/_outline.md` to determine the next pending section.
2. If next section is operator-only, skip with status `operator-required`.
3. Otherwise gather inputs (bibliography, edge reports, code listings).
4. Draft the section in `paper/sections/<id>.md` ; respect the public
   surface neutrality (no Hebrew terms ; the appendix Historical Note is
   the only place such references are allowed and is operator-only).
5. Run `bash scripts/check_public_surface.sh` ; abort if it fails.
6. Branch + commit + push + PR titled `paper(section <id>): draft`.

## Guardrails

- Never modifies sections marked `operator-required`.
- Never touches `paper/sections/appendix_historical.md` (Hebrew refs
  permitted there, operator-controlled).
- Bibliography updates go in `paper/biblio.bib` (main, neutral).
- Hebrew bibliography entries (Vital, Scholem, Hellner-Eshed) live in
  `paper/biblio_appendix.bib`, not edited by autopilot.

## Verification checklist

- [ ] Section file written with non-empty content
- [ ] `check_public_surface.sh` exit 0
- [ ] PR title matches `paper(section <id>): draft`
- [ ] Bibliography updates land in `paper/biblio.bib` only
- [ ] Operator-only sections untouched
