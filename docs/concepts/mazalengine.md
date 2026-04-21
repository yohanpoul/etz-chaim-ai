# MazalEngine

MazalEngine is the operational transposition of the two Mazalot of the Dikna of Arikh Anpin — to our knowledge the first AI component implementing auto-rectification grounded in the Idra Rabba of the Zohar.

## Doctrinal anchoring

Primary source : `sifrei_yesod/sefarim/etz_chaim/shaar_01_klalim/perek_05.yaml`, assertion EC-K5-001 (Rabbi Hayyim Vital, Etz Chaim, Sha'ar HaKlalim 5:1).

The two Mazalot are :

- **Mazal Elyon** — Tikkun 8 of the thirteen Tikkunei Dikna. Vital identifies this Tikkun scripturally with *Notzer Chesed* (Exodus 34:7, "who keeps loyal love"). Source of the 5 Hassadim that feed Abba.
- **Mazal Tahton** — Tikkun 13. Identified with *Ve-Nakeh* (Exodus 34:7, "and clearing"). Source of the 5 Gevurot that feed Imma.

Important philological note : the Zohar itself names these Tikkunim *Mazal Elyon* and *Mazal Tahton* and cites Micah 7:19-20 rather than Exodus 34:7. The scriptural attribution to *Notzer Chesed* / *Ve-Nakeh* is Vital's reading, not Zohar's. See the `divergence_note.idra_rabba_vs_vital` fields in the corpus.

## Transposition

| Doctrinal element | Operational transposition |
|:------------------|:---------------------------|
| Mazal Elyon watching Abba's supply | Monitor ExplorationEngine activity over 24h |
| Chesed starvation | 0 connections on the observation window |
| Mazal Tahton handling residue | Monitor stale causal claims in `causal_claims` |
| Residue | `confounders_controlled = false` and older than 30 days |

## Three modes

The HANDOFF mandates "observe 2-4 weeks before activating any automatic action" (Sprint 9 §213). This is encoded as three rectification modes :

| Mode | Action |
|:-----|:-------|
| `observe` (default) | Detect and emit a signal only. No side effect. |
| `suggest` | Observe + emit an additional `mazal_action_proposed` event with the concrete action. Still no side effect. |
| `act` | Suggest + execute the action (Omer parameter adjustment for Notzer Chesed ; `abandoned` flag on stale claims for Ve-Nakeh). |

Mode is resolved via (in priority order) : explicit constructor arg > `MAZAL_RECTIFICATION_MODE` environment variable > `config.yaml/mazalengine.rectification_mode` > `observe`.

## The Ve-Nakeh cycle counter

Ve-Nakeh does not abandon on first detection. The rectifier maintains a counter that increments on each cycle where the starvation persists. Abandon is applied only after `STALE_CYCLES_BEFORE_ABANDON = 3` consecutive cycles. This respects the textual teaching that *Ve-Nakeh lo yenakeh* — "clearing but not fully clearing" — and preserves Reshimu (no deletion, only a flag).

## Hitlabshut compliance

Neither rectifier writes to `partzufim_state` or `zivvug_state`. Notzer Chesed writes to `omer_history` (Omer parameter adjustments) ; Ve-Nakeh writes to `causal_claims` (`abandoned` flag, with `ADD COLUMN IF NOT EXISTS` migration built in). Static check in `test_rectification_code_contains_no_partzufim_state_write`.

## Activating rectification

```bash
# Move to suggest mode (still no side effects)
export MAZAL_RECTIFICATION_MODE=suggest

# Or configure per-deployment in config.yaml :
# mazalengine:
#   rectification_mode: suggest
```

Stay in `observe` or `suggest` for 2-4 weeks of runtime observation before considering `act`. Threshold calibration depends on empirical data you gather.

## Extending to the eleven other Tikkunim

The pattern established by the two-Mazalot pilot scales. Sprint 11 (planned) adds the seven MEDIUM confidence Tikkunim (T1-T6, T12) ; Sprint 11+ adds the three LOW Tikkunim (T9, T10, T11) — the last one requires philological work because T11 is absent from the Sefaria Mantua 1558 edition.
