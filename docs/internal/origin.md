# Origin : the specification framework

## Why this document exists

The README states that the 12-module architecture comes from a 500-year-old cognitive framework. This document gives the full mapping, honestly and completely, for readers who want to understand the choice — or to engage with the primary sources directly.

**You do not need to read this document to use or contribute to Etz Chaim AI.** The public API is plain Python, and every module has a plain-English docstring. This document is for the curious.

## The framework

The architecture is derived from **Lurianic Kabbalah**, a system of cognitive description systematized in the 16th century by Rabbi Isaac Luria (1534–1572) and codified by his disciple Rabbi Hayyim Vital (1542–1620) in *Etz Chaim* ("Tree of Life"). The mystical framing of the tradition is orthogonal to the structural content — we use only the structural content.

The framework provides :

- **10 discrete attributes** (Sephirot) describing how intelligence organizes itself.
- **4 mature configurations** (Partzufim) composed from those attributes.
- **13 rectification mechanisms** (Tikkunei Dikna) for specific failure modes.
- **Rules of layered composition** (Hitlabshut) forbidding direct writes across layers.

Each of these has a machine-readable transposition in `sifrei_yesod/sefarim/`.

## One-to-one mapping

### The 10 attributes → 8 operational modules + 2 bridges

| Kabbalistic attribute | Plain name | Module |
|:---|:---|:---|
| Chesed | Exploration | `explorationengine/` |
| Gevurah | Judgment | `autojudge/` |
| Tiferet | Tension | `dissensuengine/` |
| Chokhmah | Insight | `insightforge/` |
| Binah | Causal reasoning | `causalengine/` |
| Hod | Self-knowledge | `selfmap/` |
| Yesod | Memory | `epistememory/` |
| Malkuth (via Lamed path) | Failure-learning | `failuretoinsight/` |
| Keter | (meta-layer, planned) | — |
| Da'at | (synthesis bridge) | — |

### The 4 mature configurations → 4 composition layers

| Kabbalistic configuration | Plain name | Module |
|:---|:---|:---|
| Abba | Generative | `partzufim/abba.py` |
| Imma | Structuring | `partzufim/imma.py` |
| Zeir Anpin | Execution | `partzufim/zeir_anpin.py` |
| Nukva | Interface | `partzufim/nukva.py` |

### The 13 rectification mechanisms → watcher patterns

| Tikkun | Failure pattern | Operational detection |
|:---|:---|:---|
| 8 — Notzer Chesed (Mazal Elyon) | Exploration starvation | 0 connections on 24 h window |
| 13 — Ve-Nakeh (Mazal Tahton) | Residual unresolved causal claims | `confounders_controlled = false` + > 30 days old |
| 1–7, 9–12 | Planned (v0.2.0) | — |

### Layered composition → Hitlabshut discipline

The specification forbids writing directly to aggregate states. All improvements must pass through a specific attribute channel. In code, this is the rule : no `UPDATE partzufim_state SET overall_score = ...` outside the authorized path. Enforced by static test.

## Primary sources

- **Zohar**, Aramaic compilation (13th century Spain, traditionally attributed to Rabbi Shimon bar Yochai, 2nd century). Edition used : Sefaria Mantua 1558, CC-BY 3.0.
- **Etz Chaim**, Rabbi Hayyim Vital (ca. 1573). Public domain.
- **Tikkunei Zohar**, 14th century. Public domain.

Every doctrinal assertion in `sifrei_yesod/sefarim/` carries a `source_ref` (edition, section, page), a verbatim original-language quote, and an epistemic label (E1 to E6) indicating how close the assertion is to the primary text.

## Epistemic labels

| Level | Meaning | Example |
|:-----:|:--------|:--------|
| E1 | Primary text, literal | Zohar III 128a quoted verbatim |
| E2 | Primary text, close paraphrase | Translation preserving technical terms |
| E3 | Authoritative commentator reading | Vital on the Zohar's Idra Rabba |
| E4 | Derived conclusion | Pattern synthesized from multiple sources |
| E5 | Extrapolation | Projecting to a new domain |
| E6 | Speculation | Beyond doctrinal warrant |

Downgrade in doubt. The word "isomorphism" is forbidden without a proved bijection ; use "structural analogy" (E3) instead.

## What we do NOT claim

- We do **not** claim Etz Chaim AI is Kabbalah.
- We do **not** claim to reproduce the mystical or metaphysical content of the tradition.
- We do **not** syncretize with other traditions (no "Kabbalah = Tantra = alchemy" claims).
- We do **not** claim epistemic E1 for a translation ; translations are E2 at best.

What we **do** claim : the structural content of the framework — the 10/4/13 pattern, the composition rules, the rectification mechanics — is a useful architectural specification for building modular AI systems, independent of whether you accept or reject the mystical reading of the tradition.

## How to read the corpus

```python
from bridge import load_assertion

a = load_assertion("EC-K5-001")
print(a["source_he"])        # original Hebrew
print(a["source_ref"])       # "Sha'ar HaKlalim 5:1"
print(a["assertion"])        # plain French translation
print(a["epistemic_level"])  # "E1" — primary text, literal
```

See [bridge/README](../bridge/) for the full API.

## Further reading

- Aryeh Kaplan, *Inner Space* (1990) — accessible introduction.
- Gershom Scholem, *On the Kabbalah and Its Symbolism* (1965) — academic framing.
- Melila Hellner-Eshed, *A River Flows from Eden* (2009) and *Seekers of the Face* (2021) — scholarly readings of the Zohar and the Idra Rabba.

None of these are prerequisites for contributing to Etz Chaim AI.
