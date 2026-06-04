# Etz Chaim AI - Phase 2C Faculty Bridge

## Base et branche

- Repo cible: `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`
- Base verifiee: `2bae437 feat: add p2b action synthesis ledger`
- Branche creee: `codex/phase-2c-faculties-bridge`
- Etat initial: propre avant creation de branche
- Branche P2C inexistante avant creation: oui

## Plan execute

1. Lire les APIs existantes Guardian, FailureToInsight et IntentKeeper.
2. Ajouter des tests rouges pour le pont facultes P2C et l'enrichissement JSON/report/ledger.
3. Creer `etzchaim/metacognition/faculties.py` avec adaptateurs fins et degradations sans crash.
4. Enrichir `improve` avec `faculty_evaluation`.
5. Propager le verdict Guardian P2C dans le ledger append-only P2B.
6. Relancer les validations bornees demandees.

## Fichiers modifies

- `etzchaim/metacognition/faculties.py`
- `etzchaim/metacognition/report.py`
- `tests/test_metacognition_faculties.py`
- `tests/test_metacognition_first_loop.py`
- `tests/test_install/test_cli_improve.py`
- `strategy/codex-prompt/codex-plan/etzchaim-p2c-faculties-bridge-report.md`

## Implementation

- `evaluate_faculties_for_event(event, action=None, adapters=None) -> dict` expose trois couches:
  - `failure_insight`: `status`, `hypothesis`, `source`
  - `guardian`: `verdict`, `confidence`, `reason`, `active_biases`
  - `intent`: `status`, `intent_id`, `summary`
- FailureToInsight:
  - aucune instanciation DB par defaut;
  - utilise un adaptateur injecte si disponible;
  - supporte `guide_next_hypothesis()` et `analyze_failure()` pour les fakes/adaptateurs explicites;
  - retourne un stub documente si absent ou en erreur.
- Guardian:
  - tente un adaptateur injecte ou `selfmodel.guardian.Guardian`;
  - retourne `proceed|caution|veto|unavailable`;
  - degrade en `unavailable` sans crash si le module n'est pas importable.
- IntentKeeper:
  - aucune instanciation DB par defaut;
  - supporte un adaptateur injecte `summarize_event_intent()`;
  - retourne `no_active_intent` ou `unavailable` sans crash.
- `report.py` ajoute `faculty_evaluation` au payload JSON/state.
- Le markdown ajoute une section `## Faculty Bridge`.
- Le ledger JSONL utilise maintenant `faculty_evaluation.guardian.verdict`.
- `applies_patch=False` reste invariant; P2C n'applique aucune action.

## Tests rouges puis verts

- Rouge initial:
  - `.venv/bin/python -m pytest tests/test_metacognition_faculties.py tests/test_metacognition_first_loop.py tests/test_install/test_cli_improve.py -q`
  - Resultat: `8 failed, 5 passed`
  - Causes attendues: `faculties.py` absent, `faculty_evaluation` absent, ledger encore `not_evaluated_p2b`.
- Vert apres implementation:
  - meme commande
  - Resultat: `13 passed in 0.12s`

## Validations obligatoires

- `git status --short --branch`
  - Branche: `codex/phase-2c-faculties-bridge`
  - Status limite aux fichiers P2C.
- `.venv/bin/python -m pytest tests/test_metacognition_events.py tests/test_metacognition_collectors.py tests/test_metacognition_first_loop.py tests/test_metacognition_verify.py tests/test_metacognition_faculties.py tests/test_install/test_cli_improve.py tests/test_install/test_cli_version_info.py -q`
  - Resultat: `31 passed in 0.17s`
- `.venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q`
  - Resultat: `17 passed in 0.49s`
- `.venv/bin/etzchaim improve --once --dry-run --json`
  - Resultat: exit `0`, JSON valide, `faculty_evaluation` present, aucune ecriture durable.
  - Observation: Guardian degrade en `unavailable` depuis l'entree `.venv/bin/etzchaim` car `selfmodel` n'est pas importable dans ce contexte d'installation; le comportement est sans crash.
- `TMP_HOME=$(mktemp -d); HOME="$TMP_HOME" .venv/bin/etzchaim improve --once --json`
  - Resultat: exit `0`, report + state + ledger ecrits sous HOME temporaire:
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.eq5yzNsUvJ/.etz-chaim/runs/improve-20260604T104902Z.md`
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.eq5yzNsUvJ/.etz-chaim/state/last_improve_run.json`
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.eq5yzNsUvJ/.etz-chaim/state/improve_ledger.jsonl`
- `git diff --check`
  - Resultat: OK, aucune sortie.
- `launchctl list | grep etzchaim || true`
  - Resultat: aucune sortie.
- `git status --short`
  - Status limite aux fichiers P2C et au present rapport.

## Observations conservees

- Les deux failures Idra restent seulement observees par le collecteur pytest borne:
  - `test_s1_each_tikkun_has_zohar_and_vital`
  - `test_s3_see_also_bidirectional`
- Aucun correctif corpus Idra n'a ete applique.
- Les alertes Docker/PostgreSQL/services restent des observations; aucun service n'a ete demarre.
- Le bug P0 `/my/psql` reste une action `patch` proposee si le rapport P0 le documente, jamais appliquee automatiquement.

## Invariants respectes

- Aucun commit.
- Aucun push.
- Aucune PR.
- Aucun Docker/PostgreSQL/compose/migration/daemon/cron/LaunchAgent demarre.
- Pas de P2B hors ajustement ledger P2C.
- Pas de P2C au-dela du pont facultes lecture/degradation.
- Pas de modification du corpus `sifrei_yesod`.
- Pas de modification de `autopilot/git_integration/pr.py`.
- Pas d'ecriture dans le miroir Obsidian.
- Pas d'instanciation DB FailureToInsight/IntentKeeper par defaut.
- `applies_patch=False` reste invariant.

## Dette restante

- Guardian est degrade en `unavailable` via l'entree CLI venv tant que le module top-level `selfmodel` n'est pas expose/importable dans ce contexte.
- FailureToInsight et IntentKeeper ne sont pas branches a une DB reelle; c'est volontaire en P2C.
- Le verdict Guardian est minimal et ne remplace pas une evaluation Guardian/SelfModel complete.
- Les adaptateurs P2C sont prets pour fakes/adaptateurs explicites, pas pour auto-reparation.

## Prochaine etape proposee

- Faire valider P2C par Hermes/Yohan.
- Ensuite seulement, preparer une phase separee pour rendre les imports facultes reproductibles via packaging local ou adapters explicites, sans DB obligatoire.

PRET POUR VALIDATION HERMES / YOHAN - PHASE 2C TERMINEE
