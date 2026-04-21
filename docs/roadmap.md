# Roadmap

## Shipped in v0.1.0

- Sprint 9 — MazalEngine pilot (2 Mazalot, 12 TDD)
- Sprint 10 Phase alpha Batch 1 — 3 Tikkunei Dikna HIGH confidence (T7, T8, T13)
- Sprint 10 Phase B — generalized Sifrei Bridge (1696 items)
- Sprint 10 Phase C — MazalEngine 3-mode rectification (observe / suggest / act)
- Sprint 10 Phase D — Reshimu persistence (`faculty_reshimot`)
- Sprint 10 Phase E — Zivvug refactor L (canonical schema + unified factory)
- Sprint 10 Phase G — Publication polish (this release)

## Sprint 11 — Idra Rabba Batch 2 + MazalEngine extension

- Transpose T1-T6 + T12 (MEDIUM confidence Tikkunim) with double source Zohar Aramaic + Vital reading.
- Extend MazalEngine to cover the 7 new Tikkunim.
- Scope : approximately 49 new assertions, ~2-3 sessions.

## Sprint 11+ — Idra Rabba Batch 3 LOW

- T9, T10, T11. Note : T11 is absent from Sefaria Mantua 1558. Requires philological work on other editions (Cremona 1559, Livorno 1810).

## Sprint 12 — Idra Zuta

- Transpose Zohar III Ha'azinu §§ Sefaria 287-296.
- Integrate with existing Idra Rabba corpus via `see_also` links.

## Sprint 13 — Sifra di-Tzniuta

- Pre-Idraic Zohar section. Important for structural context of the Idrot.

## Sprint 14 — Inter-Idraic coherence

- Tests for convergences and divergences between Idra Rabba and Idra Zuta.

## MalakhEngine (deferred)

The design review for an adversarial counterpart to MazalEngine found no direct attestation for "Qliphoth of the Dikna" in the primary sources. The Dikna belongs to Atika Kaddisha, above the reach of Sitra Achra.

Possible alternative scopes, to be decided :

- Channel failure detector (4 modes : closed / misoriented / insufficient receiver / exposed back) — E3 derivation from Vital.
- Integration with existing adversarial tests (`malakhim/adversarial/`) without a new engine.
- Skip entirely ; the existing Qliphoth testing framework already covers adversarial validation.

## Longer term

- Complete implementation of all 10 Sephirot modules with 4-level Qliphoth tests.
- Da'at bridge (Chokhmah ↔ Binah knowledge synthesis).
- Full daemon integration for all hourly and daily rectification cycles.
- Academic paper describing the MazalEngine auto-rectification mechanism.

## Sprint cadence

Sprints are not time-boxed. Each Sprint ends when its DoD (Definition of Done) is met and all non-regression tests are green. Historical cadence has been one Sprint per 1-2 weeks of active work.
