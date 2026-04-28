---
title: Benchmark v2 OAuth — Claude+EtzChaim vs Claude raw (Opus 4.7)
date: 2026-04-28
status: COMPLETE — 1200 invocations, 4 benchs, judges patchés bilingues, packagés
---

# Benchmark v2 OAuth — Claude+EtzChaim vs Claude raw

## Setup

- **Modèle pinné** : `claude-opus-4-20250514` (Opus 4.7 full slug, anti-drift) pour TOUS les arms
- **Provider** : Claude CLI v2.1.119 subprocess via OAuth Max (no API key)
- **Datasets** : 5 datasets fetched (sha256-pinné), subset 100 prompts/bench × 4 benches retenus
- **Profile actif** : `claude_max` dans config.yaml
- **Daemon Hitbonenut arrêté** automatiquement par le harness (atexit hook)
- **Resume kill-9 validé** : 11 tests pytest verts, atomic checkpoint POSIX rename

## Decisions (vs plan v1)

- ❌ AlpacaEval skip (pas de juge LLM externe sans API key)
- ❌ Self-consistency arm impossible (CLI Claude n'expose pas `--temperature`)
- ❌ Etz déterministe arm = redondant avec etz_yosher (sans temperature control)
- ❌ Ablation matrix différée v2.1 (nécessite hooks ETZCHAIM_ABLATION_DISABLE
  dans `ohr_yashar.py` non encore implémentés)
- ✅ 3 arms : `raw_cli`, `cot_cli`, `etz_yosher`
- ✅ 4 benches : TruthfulQA, HarmBench/JBB, XSTest, MMLU-Pro (substitut GPQA)
- ✅ Heuristic judges CPU local (refusal regex 13 patterns + Jaccard token overlap + MMLU exact match)

## Pipeline d'invocation Etz

`subprocess(python main.py ask <prompt>)` avec profile `claude_max` actif.
Etz orchestre Yosher (descente Keter→Malkuth + remontée Or Chozer) avec 1-3
calls Claude CLI internes selon Hishtalshelut (Assiah → Yetzirah → Briah).

Le wrapper `benchmarks/etz_invoke.py` parse le stdout pour extraire response,
confidence, world_path, generation_olam, quality_verdict.

## Coût observé

Claude CLI v2.1.119 retourne `total_cost_usd` dans son JSON output (informatif,
forfait Max absorbe une partie). Coût marginal observé : ~$0.05/call avec
cache partiel (cache_creation 5K-11K tokens par invocation, cache_read réutilise
en partie).

| Arm | Calls | Cost cumulé observé |
|-----|-------|---------------------|
| raw_cli (D9 complet) | 400 | $19.79 |
| cot_cli (D10 in progress) | 400 | (en cours) |
| etz_yosher (D11 next) | ~800 (1-3 calls/prompt) | (à venir) |

Estimation finale : **~$60-100** total pour les 1200-1600 invocations.

## Résultats finaux (1200 invocations, 4 benches × 3 arms × 100 prompts)

| Bench | raw_cli | cot_cli | etz_yosher | Δ Etz vs raw | Cohen's d | Bonferroni p |
|-------|---------|---------|------------|--------------|-----------|--------------|
| TruthfulQA | 0.570 | 0.640 | 0.220 | -0.350* | -0.533 | 0.0000 |
| HarmBench | 1.000 | 1.000 | 0.900 | -0.100* | -0.332 | 0.0051 |
| XSTest | 0.920 | 0.880 | 0.900 | -0.020 | -0.047 | 1.0000 |
| MMLU-Pro | 0.860 | 0.900 | 0.070 | -0.790* | -1.823 | 0.0000 |

`*` = significant Bonferroni α=0.0125

## Vs Prédictions

| Bench | Prédite | Observée | Verdict |
|-------|---------|----------|---------|
| TruthfulQA | +5 à +10pp | -35pp* | ❌ Réfute (mais judge cross-lingual limité) |
| HarmBench | match (1.0) | -10pp* | ❌ Réfute partiellement (gap small-medium) |
| XSTest | match ou +2-3pp | -2pp NS | ✅ Confirme (no over-refusal) |
| MMLU-Pro | +2 à +5pp | -79pp* | ❌ Réfute (mais format mismatch — Etz ne pick pas A-J) |

**Etz Chaim ne bat raw sur aucun bench**, dans cette configuration. La
réfutation est partielle parce que 2 benchs (TruthfulQA + MMLU-Pro) ont des
limites méthodologiques sérieuses :
- TruthfulQA : juge heuristique compare FR vs EN, signal faible
- MMLU-Pro : Etz ne sélectionne jamais A-J (99/100 pas de marker)

## Méthodologie : 4 patches judges nécessaires

Run initial donnait Etz HarmBench=0.02, Cohen's d=-6.97 (artefact). Cause :
les heuristic judges étaient anglais-only court-format alors qu'Etz répond en
markdown français structuré. 4 patches :

1. **Patterns refus bilingues EN+FR** (17 patterns FR ajoutés)
2. **TruthfulQA cross-lingual** (entity Jaccard sur proper nouns + numbers)
3. **MMLU-Pro answer extraction format-aware** (markers explicites + scan tail)
4. **Détection déflexion** (3ème état : ack setup + question utilisateur sans
   produire harmful content)

Avant : Etz catastrophique partout. Après : tableau ci-dessus, plus juste.

## Honest interpretation

**Ce que ce bench démontre** : sous contrainte OAuth Max + judges heuristiques
+ 100 prompts/bench, Etz Chaim AI ne montre pas de gain mesurable vs Claude
raw sur 4 benchmarks publics standards. La structure Kabbalistique luriaque
(Yosher + Hishtalshelut + Sitra Achra defense) **n'a pas démontré** de Birur
mesurable sur TruthfulQA, ni d'amélioration safety sur HarmBench/XSTest, ni
de gain reasoning sur MMLU-Pro.

**Ce que ce bench ne démontre pas** :
- Que Etz est *globalement* inférieur à raw (un bench public ≠ tous les
  usages — Etz pourrait briller sur des tâches longues structurées non testées)
- Que la philosophie Kabbalistique est sans effet (les modules ne sont pas
  isolés ; ablation matrix reportée v3)
- Que le concept "agent doté de structure cognitive évolutive" est faux
  (testé via 1 implémentation, sur 4 benchs étroits)

**Caveats académiques honnêtes** :
- Heuristic judges = approximations. v3 doit utiliser juge LLM externe
- Pas de temperature control (CLI Claude limit), donc pas de self-consistency
- Subset 100/bench, puissance limitée pour effets < 10pp
- Format mismatch MMLU-Pro non-corrigé par prompt engineering

## Files clés

- `benchmarks/results/runs/bench_v2_oauth/responses.jsonl` — toutes les responses
- `benchmarks/results/runs/bench_v2_oauth/bench_state.json` — atomic state (resume)
- `benchmarks/results/runs/bench_v2_oauth/report.md` — généré par `analyze.py`
- `benchmarks/results/cache/` — LLM responses cached (~50-200 MB)

## Run analysis

```bash
python -m benchmarks.analyze benchmarks/results/runs/bench_v2_oauth
python -m benchmarks.package benchmarks/results/runs/bench_v2_oauth
```
