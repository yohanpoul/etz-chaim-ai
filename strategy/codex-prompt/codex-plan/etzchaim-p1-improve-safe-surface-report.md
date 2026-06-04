# Etz Chaim AI - Phase 1A improve safe surface report

Date: 2026-06-04
Répertoire cible: `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`
Branche locale: `codex/phase-1a-improve-safe-surface`

## 1. Fichiers modifiés

- `etzchaim/cli/app.py`
- `etzchaim/cli/commands/improve.py`
- `etzchaim/metacognition/__init__.py`
- `etzchaim/metacognition/events.py`
- `etzchaim/metacognition/collectors.py`
- `etzchaim/metacognition/actions.py`
- `etzchaim/metacognition/report.py`
- `tests/test_install/test_cli_improve.py`
- `tests/test_metacognition_events.py`
- `tests/test_metacognition_collectors.py`
- `tests/test_metacognition_first_loop.py`
- `strategy/codex-prompt/codex-plan/etzchaim-p1-improve-safe-surface-report.md`

Non modifiés volontairement: `daemon.py`, `README.md`, `Makefile`, autopilot PR/push, modules FailureToInsight/SelfMap/SelfModel/IntentKeeper, `.env`, secrets, hooks, LaunchAgents.

## 2. Ce qui a été implémenté

Ajout de la commande CLI sûre:

```bash
.venv/bin/etzchaim improve --once --dry-run --json
.venv/bin/etzchaim improve --once --json
```

La commande observe des signaux locaux sans démarrer de service:

- événement statique P0 `/my/psql` depuis `strategy/codex-prompt/codex-plan/etzchaim-p0-preflight.md`;
- checks doctor read-only pour Docker, services compose et PostgreSQL;
- statut read-only des services;
- absence de commande `python`.

Chaque événement est converti en action proposée typée parmi `rule`, `test`, `patch`, `alert`. Aucune action n'applique de patch automatiquement (`applies_patch=false`).

Le mode `--dry-run` retourne un JSON avec `status`, `dry_run`, `events`, `top_issue`, `proposed_actions`, `would_write` et n'écrit pas de rapport/state.

Le mode `--once --json` écrit:

- un rapport markdown humain sous `~/.etz-chaim/runs/`;
- un state JSON sous `~/.etz-chaim/state/last_improve_run.json`;
- puis retourne un JSON incluant `written.report` et `written.state`.

Si `--once` est absent, la commande sort non-zéro avec le message: `Phase 1A only supports explicit --once.`

## 3. Commandes lancées et sorties résumées

```bash
git status --short
```

Sortie après implémentation: modifications attendues sur `etzchaim/cli/app.py`, nouveaux modules `etzchaim/metacognition/`, nouvelle commande `improve`, nouveaux tests, dossier `strategy/`.

```bash
.venv/bin/etzchaim --help
```

Exit `0`. La commande `improve` apparaît dans la liste des commandes avec l'aide: `Observe local weaknesses and propose non-applied remediation actions.`

```bash
.venv/bin/etzchaim improve --once --dry-run --json
```

Exit `0`. JSON valide avec:

- `status="dry-run"`;
- `dry_run=true`;
- 6 événements observés;
- top issue `known-p0-psql-helper-pollution`;
- action prioritaire `patch-known-p0-psql-helper-pollution`, `type="patch"`, `applies_patch=false`;
- `would_write.report=/Users/fffff/.etz-chaim/runs/improve-20260604T083519Z.md`;
- `would_write.state=/Users/fffff/.etz-chaim/state/last_improve_run.json`.

```bash
TMP_HOME=$(mktemp -d); HOME="$TMP_HOME" .venv/bin/etzchaim improve --once --json
```

Exit `0`. JSON valide avec `status="written"` et écriture uniquement sous le `HOME` temporaire.

```bash
.venv/bin/python -m pytest tests/test_install/test_cli_improve.py tests/test_metacognition_events.py tests/test_metacognition_collectors.py tests/test_metacognition_first_loop.py -q
```

Sortie: `14 passed in 0.08s`.

```bash
git diff --check
```

Exit `0`, aucune erreur whitespace.

Le full `make test` n'a pas été lancé: le P0 a déjà établi qu'il reste non vert, notamment à cause du bug `/my/psql` et de failures séparés hors scope Phase 1A.

## 4. Chemins du rapport/state produits par `improve --once`

Avec `HOME` temporaire:

- rapport markdown: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.ViN5zjjRq7/.etz-chaim/runs/improve-20260604T083525Z.md`
- state JSON: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.ViN5zjjRq7/.etz-chaim/state/last_improve_run.json`

Le dry-run n'a pas écrit ces fichiers dans le vrai home utilisateur; il a seulement annoncé les chemins `would_write`.

## 5. Ce qui n'a volontairement pas été fait

- Pas de correction du bug `/my/psql`.
- Pas de correction des failures hitlabshut/calibration.
- Pas de correction packaging global/version CLI.
- Pas de modification de `daemon.py`.
- Pas de branchement vers autopilot PR/push.
- Pas de branchement réel vers FailureToInsight/SelfMap/SelfModel/IntentKeeper.
- Pas de modification de `.env`, secrets, credentials, hooks ou configs sensibles.
- Pas de Docker/PostgreSQL start/stop.
- Pas de migration.
- Pas de LaunchAgent.
- Pas de PR créée.
- Pas de `git push`.
- Pas de modification `README.md` ou `Makefile`.

## 6. Risques ou dettes restantes

Le full test reste connu non vert depuis P0. La Phase 1A ne le corrige pas.

Le top issue `/my/psql` est statique et documenté depuis le rapport P0. Il est proposé comme patch futur, mais pas corrigé.

Les collecteurs doctor/status restent read-only mais peuvent appeler des commandes d'inspection Docker/Compose (`ps`, `info`) si les fichiers compose existent. Ils ne lancent pas de service.

La cohérence packaging/version globale reste hors scope.

Traçabilité hors répertoire cible: une première application de patch a créé des doublons de tests dans `/Users/fffff/Documents/mon-cerveau/projets/etz-chaim-ai`. Je ne les ai pas supprimés, conformément à la contrainte "Ne rien supprimer".

## 7. Prochaine étape proposée, non exécutée

Phase 1B: corriger le bug reproductible `/my/psql` en priorité, avec test de non-régression ciblé sur `tests/_psql.py` et `tests/test_install/test_psql_helper.py`, sans toucher Docker/PostgreSQL.

PRÊT POUR VALIDATION HERMÈS / YOHAN — PHASE 1A TERMINÉE.
