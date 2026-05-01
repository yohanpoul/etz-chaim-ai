# Advanced — Origin of the Structural Framework

This document is **opt-in informational**. You do not need to read it to use, contribute to, or evaluate Etz Chaim AI. The public API is plain Python with neutral naming throughout.

## Where the 10 / 6 / 13 numbers come from

Etz Chaim AI's architecture rests on three numerical commitments :
- **10 cognitive faculties**
- **6 mature configurations**
- **13 rectification mechanisms**

These numbers are not arbitrary. They derive from a 500-year-old cognitive description tradition known as **Lurianic Kabbalah**, systematized in the 16th century by R. Isaac Luria (1534–1572) and codified by his disciple R. Hayyim Vital (1542–1620) in the work *Etz Chaim* ("Tree of Life") — the project's namesake.

The framework specifies :
- **10 discrete attributes** through which intelligence organizes itself
- **6 mature configurations** built from those attributes
- **22 typed paths** connecting the configurations
- **13 rectification mechanisms** for specific failure modes
- **49 calibration cycles** — a 7×7 matrix of inner-within-outer tuning
- **Rules of layered composition** forbidding direct writes across layers

We translated this framework into 1696 machine-readable specification items with edition + section + page references. The code is built *against those specifications*, not the other way around.

## What we use

We use only the **structural content** :
- The 10/6/13 pattern
- The composition rules
- The rectification mechanics
- The calibration topology
- The persistent-trace dynamics

We do **not** :
- Claim Etz Chaim AI is Kabbalah
- Reproduce the mystical or metaphysical content of the tradition
- Syncretize with other traditions
- Claim epistemic E1 for translations (E2 at best)

## How we cite

Every doctrinal assertion in the internal corpus carries :
- a `source_ref` (edition, section, page)
- a verbatim original-language quote
- an epistemic label (E1 to E6) indicating proximity to the primary text

| Level | Meaning |
|:-----:|:--------|
| E1 | Primary text, literal |
| E2 | Primary text, close paraphrase |
| E3 | Authoritative commentator reading |
| E4 | Derived conclusion |
| E5 | Extrapolation |
| E6 | Speculation |

Downgrade in doubt. The word "isomorphism" is forbidden without a proved bijection ; use "structural analogy" (E3) instead.

## Primary sources

- **Zohar**, Aramaic compilation (13th century Spain). Edition used : Sefaria Mantua 1558 (CC-BY 3.0).
- **Etz Chaim**, R. Hayyim Vital (ca. 1573). Public domain.
- **Tikkunei Zohar**, 14th century. Public domain.
- **Pardes Rimonim**, R. Moshe Cordovero (1548). Public domain.

## Further reading

For readers wanting to engage with the source tradition academically :

- Aryeh Kaplan, *Inner Space* (1990) — accessible introduction.
- Gershom Scholem, *On the Kabbalah and Its Symbolism* (1965) — academic framing.
- Melila Hellner-Eshed, *A River Flows from Eden* (2009) and *Seekers of the Face* (2021) — scholarly readings.

None of these are prerequisites for using or contributing to Etz Chaim AI.

## CLI shortcut

```bash
etzchaim --explain-origin
```

Prints a brief version of this document.

## Why disclose the origin ?

Two reasons :
1. **Honesty.** The architecture's specificity (10/6/13, the path topology, the layered composition rule) cannot be invented from generic ML priors. Citing the source is the honest position.
2. **Reproducibility.** Researchers who want to reproduce the structural framework or extend it need to access the primary sources.

What we explicitly avoid is making the source tradition a *gating concept* for users. The default user-facing surface (CLI, docs, web UI, API) is 100% neutral. This document and the `--explain-origin` flag are opt-in.

## Internal documents

For project contributors who want the full mapping :
- `docs/internal/origin.md` — full mapping with epistemic labels
- `docs/internal/concepts/` — concept-by-concept transposition documents
- `docs/internal/guides/` — internal guides for adding new configurations or transposing new sources
