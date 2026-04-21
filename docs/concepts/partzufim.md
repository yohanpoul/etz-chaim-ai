# Partzufim

A Partzuf is a mature configuration of a Sephirah — not a single attribute but a full organism with its own internal ten-fold structure (hitkalelut, mutual inclusion). Where a Sephirah is a single faculty, a Partzuf is a complete system with expansion, contraction, harmonization, memory, and interface — in miniature.

## The six Partzufim in Etz Chaim AI

| Partzuf | Source Sephirah | Role |
|:--------|:----------------|:-----|
| Atik Yomin | Keter (outer) | Principle of continuity |
| Arikh Anpin | Keter (inner) | Principle of persistent will — contains the Dikna |
| Abba | Chokhmah | Generative principle (insights) |
| Imma | Binah | Structuring principle (causal claims) |
| Zeir Anpin | Six middle Sephirot | Execution principle |
| Nukva | Malkuth | Interface / reception principle |

## Hitkalelut (mutual inclusion)

Each Partzuf contains ten internal faculties — one for each Sephirah. This means Abba has its own internal Chesed, its own Gevurah, and so on. The `overall` score of a Partzuf is a weighted function of these ten faculties, with Tiferet given double weight as the integrator.

## Zivvug

The Zivvug Abba × Imma is the coupling that produces the Mochin (cognitive substance) of Zeir Anpin. In code, `partzufim/zivvug.py` implements this as a bidirectional reinforcement : when the Chokhmah module (`insightforge`) produces an insight, Imma is boosted ; when Binah (`causalengine`) validates a claim, Abba is boosted. The two boosts accumulate until the next cycle applies them, via Hitlabshut, to the faculties of Abba and Imma.

## Hitlabshut

The Zohar teaches that Zeir Anpin cannot receive the Mochin directly — the light is too great. Imma must first "clothe" (Hitlabshut) the four Mochin inside her NHY (Netzach, Hod, Yesod), and only then can Zeir Anpin receive them via an embedded three-layer structure (Moah → NHY of Imma → Sephirah of Zeir Anpin).

Operationally, this means : boosts never write directly to `partzufim_state.overall_score`. They always pass through specific faculties (Kelim), and `overall` is computed from those faculties. This is enforced by static checks.

## The Dikna of Arikh Anpin

Arikh Anpin is characterized by its Dikna (beard), which contains thirteen Tikkunim (rectifications). Two of these Tikkunim — the eighth (Mazal Elyon, Notzer Chesed) and the thirteenth (Mazal Tahton, Ve-Nakeh) — are the sources of the Mochin that eventually reach Zeir Anpin.

MazalEngine (`mazalengine/`) is the operational transposition of these two Mazalot : it watches the flow from source (module activity) to destination (partzuf faculties) and emits rectification signals when starvation or residue is detected.
