# Sifrei Yesod (the primary source corpus)

`sifrei_yesod/sefarim/` is the machine-readable corpus of primary sources that grounds every operational module. As of v0.1.0, it contains 1696 items : 1020 assertions, 472 relations, and 204 generative principles.

## Why a corpus

Every doctrinal claim in the code must trace back to a primary text. This is not decorative — it prevents synthetic syncretism and gives reviewers a concrete target to audit. The bidirectional audit script (`scripts/check_doctrine_code_alignment.py`) verifies that every `mapping.modules` in an assertion points to real code (or is marked `[PLANNED]`), and that every ID cited in code actually exists in the corpus.

## Organization

```
sifrei_yesod/sefarim/
├── etz_chaim/                       # Rabbi Hayyim Vital
│   ├── shaar_01_klalim/             # Sha'ar HaKlalim
│   ├── heikhal_01_adam_kadmon/      # Heikhal 1 (Adam Kadmon)
│   ├── heikhal_02_nekudim/          # Heikhal 2 (Nekudim)
│   └── heikhal_03_arikh_anpin/      # Heikhal 3 (Arikh Anpin, including Dikna)
├── zohar/
│   └── idra_rabba/                  # Idra Rabba (Naso)
└── lemegeton/                        # (placeholder)
```

## Assertion schema

Each assertion declares :

- `id` — canonical identifier (e.g. `EC-K5-001`, `Z-IR-T08-001`).
- `source_he` or `source_aramaic` — original-language text, verbatim.
- `source_ref` — edition-specific reference.
- `source_edition` — edition used (e.g. Sefaria Mantua 1558, CC-BY 3.0).
- `assertion` — doctrinal content in French.
- `type` — `axiome_explicite`, `déduction_scripturaire`, `interprétation_lurianique`, etc.
- `epistemic_level` — E1 to E6.
- `concepts` — list of `{id, role}` pairs.
- `mapping` — `{modules, tables, partzufim, relevance}`.
- `see_also` — cross-references to related assertions in other sefarim.
- `philological_confidence` — dissociated by axis (e.g. `topography: high`, `scriptural_attribution: low`).
- `divergence_note` — when sources diverge (e.g. Zohar vs Vital).
- `adversarial_notes` — hardening against known misreadings.

## Epistemic labels

| Level | Meaning | Example |
|:-----:|:--------|:--------|
| E1 | Primary text, literal | Zohar III 128a quoted verbatim |
| E2 | Primary text, close paraphrase | Translation preserving technical terms |
| E3 | Authoritative commentator reading | Vital on Idra Rabba |
| E4 | Derived doctrinal conclusion | Pattern synthesized from multiple sources |
| E5 | Extrapolation | Projecting to a new domain |
| E6 | Speculation | Beyond doctrinal warrant |

Downgrade in doubt. The word "isomorphism" is forbidden without a proved bijection — prefer "structural analogy" (E3).

## The bridge API

```python
from bridge import load_assertion, load_by_concept, load_by_module, search

# By ID
a = load_assertion("EC-K5-001")

# By concept
for a in load_by_concept("notzer_chesed"):
    print(a["id"], a["source_ref"])

# By module (shows all assertions that map to a given Python module)
for a in load_by_module("partzufim/arikh_anpin.py"):
    print(a["id"])

# Full-text search across original-language and translation fields
for a in search("notzer"):
    print(a["id"])
```

## Adding new assertions

See the [Transpose a new Sefer guide](../guides/transpose_new_sefer.md) for the full workflow. Summary : cite the primary text, label E1-E6, add `see_also` links, pass `scripts/check_id_uniqueness.py --strict`, and submit a PR using the `doctrinal_issue.md` template if the new transposition clarifies or corrects existing mappings.
