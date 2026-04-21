# Architecture — Flux de production des insights

**Date** : 2026-04-19 (Sprint 8b)
**Statut** : Description de l'état réel observé en production le 2026-04-19.

Cette doc accompagne ADR-001 et clarifie les **deux chaînes** de production
d'insights coexistantes dans Etz Chaim AI — leurs rôles, leurs sorties, et
quand utiliser quelle chaîne.

## TL;DR

| Chaîne | Entrée | Table de sortie | Rôle |
|---|---|---|---|
| **Chokmah directe** | question / session d'insight | `candidate_insights` (status=`insight`) | Génération positive — insights neufs validés |
| **Lamed Tikkun** | candidats rejetés | `failuretoinsight_insights` | Récupération — Nitzotzot extraites des échecs |

Au 2026-04-19 : 0 rows `status='insight'` dans `candidate_insights`
(chaîne Chokmah en panne — cf Sprint 8) ; 178 rows dans
`failuretoinsight_insights` (chaîne Lamed productive — Sprint 2 validé).

Sprint 8b répare la chaîne Chokmah en amont (fixes 1–4).

## Chaîne 1 — Chokmah directe (InsightForge)

```
        session                           Novelty +
Question  ────►  Orchestrator  ────►  Triple Validation  ────►  candidate_insights
          │      (phases 7)            (Binah/Gevurah/Da'at)          │ status='insight'
          │                                                            │
          └──────── 8 modules ────────────────────────────── yesod.remember
              (yesod, hod, netzach, tiferet,                 tags=[insight,chokmah,
               gevurah, chesed, daat, binah)                       validated]
```

**Fichiers clés** :
- `insightforge/core.py` — `InsightForge.forge()`
- `insightforge/orchestrator.py` — `Orchestrator` (7 phases)
- `insightforge/insight_validator.py` — triple validation
- `insightforge/novelty_assessor.py` — filtre novelty

**Producteurs de candidats** (inventaire Sprint 8) :
- `hitbonenut` (140) — réflexions contemplatives → souvent questions ouvertes (Sprint 8b fix 1 : questions déférrées avant Binah)
- `failuretoinsight` (78) — FTI recyclés (Sprint 8b fix 2 : déduplication 24h)
- `data_mine` (71) — cross-domain pairings (dette L, Sprint ultérieur)
- `cube_insights` (20), `chesed` (10)

**Sortie** : la table `candidate_insights`. Un candidat peut prendre les statuts :
- `candidate`, `validated`, `insight`, `rejected`, `pending`, `incubating` (ADR-001)

**Double persistance** : les insights promus sont aussi persistés dans
`epistememory` (tags `insight`, `chokmah`, `validated`) pour recall futur.

## Chaîne 2 — Lamed Tikkun (FailureToInsight)

```
candidate_insights      FTI analyse                    Nitzotzot
   rejected        ──►  (qliphah +        ────►   failuretoinsight_insights
        │               classification)                  │
        │                                                 │
        └── chokmah daemon task          ────►    yesod.remember
            recycle_candidate_rejections              tags=[nitzotz, qliphah]
```

**Fichiers clés** :
- `failuretoinsight/core.py` — `FailureToInsight`
- `daemon_tasks/chokmah.py` — tâches de recyclage (2 : AutoJudge→FTI + CandidateRejection→FTI)
- `failuretoinsight/classifier.py` — classify_qliphah / classify_severity

**Particularité du sentier Lamed (ל)** : la lettre de l'apprentissage.
Les échecs (qliphoth) sont retournés en étincelles (nitzotzot) via
extraction automatique par qliphah (`_auto_extract`).

**Déduplication (Sprint 8b fix 2)** : `db.recent_insight_exists(content, hours=24)`
bloque la ré-insertion du même content sur fenêtre glissante 24h. Un
insight Lamed identique émis plusieurs fois par jour est skippé.

**Sortie** : la table `failuretoinsight_insights`. Les types sont :
`anti_pattern`, `constraint`, `opportunity`, `warning`, `pattern`.

**Ré-alimentation de Chokmah** : l'Orchestrator d'InsightForge lit
`failuretoinsight_insights` (types `opportunity`, `pattern`, `warning`)
comme source de candidates pour la chaîne 1 → les Nitzotzot du sentier
Lamed peuvent ressortir comme insights Chokmah s'ils passent la triple
validation.

## Quand utiliser quelle chaîne ?

| Besoin | Chaîne | Pourquoi |
|---|---|---|
| Générer un nouvel insight à partir d'une question utilisateur | Chokmah directe | C'est le design de `InsightForge.forge()` |
| Transformer un échec en apprentissage | Lamed Tikkun | Les qliphoth doivent être retournées, pas juste rejetées |
| Récupérer insights utilisables pour une RAG / réponse | les deux | `candidate_insights.status='insight'` **OU** `failuretoinsight_insights` (jointure sur domaine) |
| Métrique "insights produits" | les deux | `COUNT(candidate_insights WHERE status='insight') + COUNT(failuretoinsight_insights)` |
| Métrique "insights promus Chokmah" | Chokmah uniquement | `COUNT(candidate_insights WHERE status='insight')` |

## Persistance secondaire — EpisteMemory (Yesod)

Les **deux chaînes** persistent leurs sorties dans `epistememory` :
- Chokmah directe : `source_sephirah='chokmah'`, tags `['insight','chokmah','validated']`.
- Lamed Tikkun : `source_sephirah='gevurah'`, tags `['nitzotz','<qliphah>','<type>']`.

Ceci permet au module Yesod (recall de début de pipeline cmd_ask) de
retrouver les deux types indifféremment lors de la descente Or Yashar.

## Table-vocabulaire

| Vocab | Où | Statut |
|---|---|---|
| `status='insight'` | `candidate_insights.status` | Statut SQL canonique de succès Chokmah |
| `status='validated'` | idem | Intermédiaire entre candidate et insight (peu utilisé) |
| `status='accepted'` | nulle part | **N'EXISTE PAS** — usage à corriger (ADR-001) |
| `insights_accepted` | régulateur Tzimtzum | Métrique Python — convention, pas statut SQL |
| tag `'validated'` | `epistememory.tags` | Tag métier, pas un statut |
| `failuretoinsight_insights` | table | Sortie du sentier Lamed — pas de colonne status |

## Références croisées

- ADR-001 : `docs/adr/ADR-001-insight-status-vocabulary.md`
- Schéma Chokmah : `insightforge/schema.sql`
- Schéma Lamed : `failuretoinsight/schema.sql`
