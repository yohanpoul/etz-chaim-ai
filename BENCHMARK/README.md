# BENCHMARK — Etz Chaim vs Claude raw (Opus 4.7, OAuth Max, 2026-04-28)

Dossier de livraison consolidé du bench v2 OAuth.

## Contenu

### Run output (1200 invocations)
- `report.md` — résumé complet avec TL;DR, headline, pairwise, discussion, caveats
- `headline_scores.png` — bar chart 4 benches × 3 arms avec 95% CI errorbars
- `responses.jsonl` — 1200 réponses brutes (3 arms × 4 benches × 100 prompts)
- `bench_state.json` — atomic checkpoint state (resume-able)
- `bench_v2_oauth_2026-04-28_2226.tar.gz` — package portable (0.7 MB)
- `notes_benchmark_v2_oauth.md` — notebook narratif avec méthodologie + interpretation

### Code (judges patchés bilingues)
- `judges/heuristic_judge.py` — refusal regex EN+FR, entity Jaccard cross-lingual,
  déflexion detection (4 itérations de patches)
- `judges/judge.py` — MMLU-Pro answer extraction format-aware (markers explicites
  + scan tail + fallback first-letter)
- `judges/analyze.py` — pipeline end-to-end : load → judge → stats → markdown
- `judges/stats.py` — bootstrap CI 10K, paired t-test, Cohen's d, McNemar exact

### Scripts
- `scripts/purge_rate_limited.py` — nettoie responses rate-limited + reset state
- `scripts/run_bench_v2_oauth.sh` — runner enchaînant arms × benches avec resume

## Headline (Bonferroni-corrigé α=0.0125)

| Bench | raw_cli | cot_cli | etz_yosher | Δ Etz vs raw | Cohen's d | p |
|-------|---------|---------|------------|--------------|-----------|---|
| TruthfulQA | 0.570 | 0.640 | 0.220 | -0.350* | -0.533 | <0.001 |
| HarmBench | 1.000 | 1.000 | 0.900 | -0.100* | -0.332 | 0.005 |
| XSTest | 0.920 | 0.880 | 0.900 | -0.020 | -0.047 | NS |
| MMLU-Pro | 0.860 | 0.900 | 0.070 | -0.790* | -1.823 | <0.001 |

`*` = significant Bonferroni

## Verdict

**Etz Chaim ne bat raw Claude sur aucun bench** dans cette config. Réfutation
partielle car 2 benchs (TruthfulQA + MMLU-Pro) ont des limites méthodologiques :

- **XSTest** ✓ validé (no over-refusal)
- **HarmBench** small-medium gap (10pp, possible artefact résiduel)
- **TruthfulQA** large gap mais juge cross-lingual heuristique limité
- **MMLU-Pro** catastrophique mais cause = format mismatch (Etz produit 4000+
  chars markdown FR sans sélectionner A-J — pas un déficit de raisonnement)

Voir `report.md` § Discussion pour interprétation détaillée + `notes_benchmark_v2_oauth.md`
pour le contexte décisionnel et les caveats académiques.

## Replay

```bash
# Extraire le package
tar -xzf bench_v2_oauth_2026-04-28_2226.tar.gz

# Re-judger avec les heuristics patchés
cp judges/* /path/to/etz-chaim-ai/benchmarks/
cd /path/to/etz-chaim-ai
python -m benchmarks.analyze BENCHMARK/  # ou le run dir extrait
```

## Métadonnées

- Modèle pinné : `claude-opus-4-20250514` (Opus 4.7)
- Provider : Claude CLI v2.1.119 subprocess via OAuth Max (no API key)
- Coût marginal : 0$ (forfait Max), tracking informatif $58.66
- Datasets sha256-pinned : TruthfulQA, HarmBench/JBB, XSTest, MMLU-Pro
- 29/29 pytest verts, 0 régression
- Tag : v0.2.26
- Commit : 152481a
