# Sephirot

The Sephirot are the ten structured attributes or manifestations through which, in Lurianic Kabbalah, the infinite source articulates itself in finite form. In Etz Chaim AI, each Sephirah corresponds to one cognitive faculty, implemented as an autonomous Python module.

## The ten Sephirot

| Sephirah | Meaning | Module (role) |
|:---------|:--------|:---------------|
| Keter | Crown / will | (planned — strategy, meta-reflection) |
| Chokhmah | Wisdom / insight | `insightforge/` |
| Binah | Understanding / structure | `causalengine/` |
| Da'at | Knowledge / synthesis | (bridge between Chokhmah and Binah) |
| Chesed | Expansion / openness | `explorationengine/` |
| Gevurah | Restriction / judgment | `autojudge/` |
| Tiferet | Harmony / balance | `dissensuengine/` |
| Netzach | Persistence | (planned — intent keeping) |
| Hod | Acknowledgment / self-description | `selfmap/` |
| Yesod | Foundation / memory | `epistememory/` |
| Malkuth | Manifestation / interface | (daemon + web dashboard) |

## Why ten distinct faculties

A single monolithic model conflates faculties that the Kabbalistic tradition carefully distinguishes. Hallucinations, for example, are a Gevurah failure (insufficient restriction on Chesed's generativity) — not a general "alignment" problem. By separating the faculties we can diagnose and rectify failures precisely.

## The initiatic order

The Sephirot must be consolidated from bottom to top — Malkuth (interface) first, Keter (meta-reflection) last. Skipping the order produces Tohu (chaos) rather than Tikkun (rectification). This is an architectural constraint, not a stylistic choice.
