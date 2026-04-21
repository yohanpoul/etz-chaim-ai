# Guide : transpose a new Sefer

Adding a new primary source to `sifrei_yesod/sefarim/` extends the doctrinal base. This guide covers the full workflow.

## Prerequisites

- You have identified the source : author, work, edition, folio/section.
- The edition is either public domain or CC-BY compatible.
- You can access the original-language text (Hebrew, Aramaic) in machine-readable form (Sefaria, Otzar HaHochma, etc.).

## Step 1 — Directory and meta

Create a directory under `sifrei_yesod/sefarim/<corpus>/<work>/<section>/` and add a `meta.yaml` :

```yaml
meta:
  corpus: etz_chaim   # or zohar, lemegeton, ...
  work: etz_chaim
  section_path: ["heikhal_03_arikh_anpin", "shaar_02_dikna"]
  source_edition: "Jerusalem 1862 (public domain)"
  transposed_by: "Contributor name or pseudonym"
  version: 1
  strates: ["base"]
```

## Step 2 — File naming

Each perek (chapter) or logical unit gets its own YAML file. Naming convention :

- `perek_<n>.yaml` for ordinary chapters.
- `perek_<n>a.yaml`, `perek_<n>b.yaml` when a perek is split for readability.
- `tikkun_<n>_<slug>.yaml` for Tikkunim.

## Step 3 — Assertion template

```yaml
- id: "EC-<shaar>-<num>"              # canonical ID, must be unique corpus-wide
  source_aramaic: "..."                # or source_he for Hebrew works
  source_edition: "Sefaria Mantua 1558 (CC-BY 3.0)"
  source_ref: "Zohar III Naso, Idra Rabba, section 18"
  zohar_folio: "Zohar III Naso 133a"   # optional, Zohar-specific
  translation_fr: |
    French translation preserving technical terms.
  assertion: |
    Doctrinal content as it applies to the codebase.
  type: axiome_explicite
  epistemic_level: E1
  concepts:
    - {id: chut_had, role: fil_unique_topographique}
    - {id: mazal_elyon, role: canal_suspenseur_ontologique}
  mapping:
    modules: ["partzufim/arikh_anpin.py"]
    tables: ["partzufim_states"]
    partzufim: ["arikh_anpin"]
    relevance: "..."
  see_also:
    - {id: "EC-K5-001", role: "lecture_vital_meme_tikkun"}
  commentary:
    ashlag_hasulam_section_refs: ["Sulam_on_Zohar,_Idra_Rabba.18"]
  adversarial_notes:
    - "A5 (unity_constraint) : this Tikkun is ONE thread — image of the unity of the 13 modalities"
    - "P1 : the Aramaic Zohar says 'tiqquna teminah' (8th), does NOT name 'Notzer Chesed'"
  unity_constraint: |
    Note on how this assertion interacts with the rest of the corpus.
  philological_confidence:
    topography: high
    scriptural_attribution: low
  flux_direction: bidirectional
  divergence_note:
    idra_rabba_vs_vital: |
      Explain how the Zohar and Vital diverge on this point.
```

## Step 4 — Cross-references

Add `see_also` links from related assertions to the new ones. Example : when you add a Zohar transposition, update the Vital assertion on the same Tikkun to include a `see_also` entry pointing to the new Zohar IDs.

## Step 5 — Divergence notes

When the Zohar and Vital diverge, document both without synthesis :

```yaml
divergence_note:
  idra_rabba_vs_vital: |
    The Zohar Aramaic text says "one thread" (HAD HOTA) and names "Mazal",
    without "Notzer Chesed". Vital, Sha'ar HaKlalim 5:1 + Sha'ar Arikh Anpin
    perek 9-10, pairs T8 with "Notzer Chesed" (Exodus 34:7). This scriptural
    attribution is Lurianic, not Zohar.
```

## Step 6 — Tests

Add or extend `sifrei_yesod/tests/test_<work>_corpus_fidelity.py` to check the structural integrity of your new files. Minimal checks :

- Every assertion has the required fields.
- `source_ref` matches the edition in `meta.yaml`.
- `philological_confidence` is dissociated by axis when attribution and topography diverge.

## Step 7 — Alignment

```bash
python scripts/check_id_uniqueness.py sifrei_yesod/sefarim/ --strict
python scripts/check_doctrine_code_alignment.py
```

Both should pass. If `check_doctrine_code_alignment` reports missing modules, they should be tagged `[PLANNED]` until implemented.

## Step 8 — PR

Use the `[DOCTRINE]` issue template for any disagreement with prior transpositions ; use the standard PR template otherwise. Reviewers will check :

- Verbatim original-language preservation.
- Correct edition citation.
- Adequate epistemic labeling (downgrade in doubt).
- Cross-references added.
- No synthetic syncretism.

## Common mistakes

- **Over-translation** that loses technical terms. Keep the original-language word when translation is approximate.
- **Missing `divergence_note`** when sources disagree. Document the disagreement rather than picking a side silently.
- **E1 applied to translations**. Translations are E2 at best.
- **Skipping `see_also`**. Cross-references are part of the epistemic contract.
