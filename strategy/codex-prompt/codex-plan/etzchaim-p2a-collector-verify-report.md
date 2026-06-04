# Etz Chaim AI - Phase 2A collector verify report

Date: 2026-06-04
Répertoire cible: `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`
Branche locale: `codex/phase-2a-pytest-collector-verify`
Base: `929d714 feat: add safe improve surface and psql regression fix`

## Mini-plan exécuté

1. Ajouter un module read-only `verify.run_verification()` pour capturer les preuves d'exécution locale.
2. Étendre `MetacognitionEvent` avec `verified` et `verification_result`, sans casser les tests P1A.
3. Ajouter un collecteur pytest borné, exécuté via `.venv/bin/python -m pytest`, qui observe les failures sans réparation.
4. Afficher les résultats de vérification dans le JSON et le rapport markdown `improve`.
5. Ajouter une cible `make doctor` read-only.
6. Relancer uniquement les validations bornées demandées.
7. Micro-correction Hermès: rendre l'exécution pytest réellement read-only en forçant `PYTHONDONTWRITEBYTECODE=1` et `PYTEST_ADDOPTS` avec `-p no:cacheprovider`.

Le plan Co-work indiqué (`workspace/_plans/2026-06-04-etz-chaim-phase2-cowork-plan.md`) n'existe pas dans ce checkout; les instructions utilisateur ont fourni le périmètre décision-complet utilisé.

## Fichiers réellement touchés

Code modifié:

- `etzchaim/metacognition/events.py`
- `etzchaim/metacognition/collectors.py`
- `etzchaim/metacognition/report.py`
- `etzchaim/metacognition/verify.py`
- `Makefile`

Tests modifiés/créés:

- `tests/test_metacognition_verify.py`
- `tests/test_metacognition_collectors.py`
- `tests/test_metacognition_first_loop.py`
- `tests/test_install/test_cli_improve.py`

Rapport:

- `strategy/codex-prompt/codex-plan/etzchaim-p2a-collector-verify-report.md`

Non modifié: `tests/test_install/test_cli_version_info.py`. Le test version/interpréteur demandé passe sans changement, donc aucune réconciliation de code n'a été nécessaire.

## Code modifié vs état venv

Code modifié:

- ajout de `run_verification(command, cwd, timeout_seconds=...)`;
- ajout des champs `verified` / `verification_result`;
- ajout de `collect_pytest_events()` avec subset pytest borné;
- rendu markdown des résultats de vérification;
- cible `doctor` dans le Makefile;
- pour les commandes pytest uniquement, environnement subprocess avec `PYTHONDONTWRITEBYTECODE=1` et `PYTEST_ADDOPTS` préservé + `-p no:cacheprovider`.

État venv:

- aucune commande `.venv/bin/python -m pip install -e .` n'a été lancée;
- aucun changement de packaging, version globale ou environnement système.

## Commandes de validation lancées

```bash
git status --short
```

Avant P2A: propre.

```bash
git log -1 --oneline
```

Résultat: `929d714 feat: add safe improve surface and psql regression fix`.

```bash
git switch -c codex/phase-2a-pytest-collector-verify 929d714
```

Résultat: branche créée.

```bash
.venv/bin/python -m pytest tests/test_metacognition_verify.py::test_verify_makes_pytest_environment_read_only -q
```

Résultat micro-correction: `1 passed in 0.03s`. Avant patch, ce test échouait car `subprocess.run()` ne recevait pas d'environnement `env`.

```bash
.venv/bin/python -m pytest tests/test_metacognition_verify.py -q
```

Résultat: `3 passed in 0.07s`.

```bash
.venv/bin/python -m pytest tests/test_metacognition_verify.py tests/test_metacognition_collectors.py tests/test_metacognition_first_loop.py tests/test_install/test_cli_improve.py tests/test_install/test_cli_version_info.py -q
```

Résultat final: `21 passed in 0.16s`.

```bash
.venv/bin/etzchaim improve --once --dry-run --json
```

Résultat: exit `0`. Le JSON contient `verified` et `verification_result` dans les events. Le collecteur pytest borné observe `pytest-bounded-subset-failed` avec `verified=false`.

Micro-correction read-only appliquée pendant ce smoke: le runner pytest utilise `.venv/bin/python -m pytest` avec environnement `PYTHONDONTWRITEBYTECODE=1` et `PYTEST_ADDOPTS` incluant `-p no:cacheprovider`.

Vérification complémentaire du dry-run:

```bash
test ! -e /Users/fffff/.etz-chaim/runs/improve-20260604T095935Z.md && test ! -e /Users/fffff/.etz-chaim/state/last_improve_run.json
```

Résultat: `dry-run wrote no announced report/state`.

```bash
TMP_HOME=$(mktemp -d); HOME="$TMP_HOME" .venv/bin/etzchaim improve --once --json
```

Résultat: exit `0`; rapport et state écrits sous HOME temporaire:

- report: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.zphOtBoEcX/.etz-chaim/runs/improve-20260604T095941Z.md`
- state: `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.zphOtBoEcX/.etz-chaim/state/last_improve_run.json`
- ledger: absent

```bash
make doctor
```

Résultat: exit `2` via `make`, car la CLI doctor retourne non-zéro avec `n_fail=3`:

- `docker_running`: false
- `compose_services_up`: false
- `postgres_healthy`: false
- `ollama_reachable`: true
- `etz_chaim_api_key_present`: true
- `dashboard_port`: true

Accepté pour P2A: cible présente, read-only, aucun service démarré.

```bash
.venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q
```

Résultat: `17 passed in 0.16s`.

```bash
git diff --check
```

Résultat: exit `0`.

```bash
launchctl list | grep etzchaim || true
```

Résultat: aucune sortie; aucun LaunchAgent Etz Chaim actif observé.

```bash
git status --short
```

Résultat: uniquement des fichiers du périmètre autorisé P2A.

## Failures Idra observées, non corrigées

Le collecteur pytest borné observe les deux failures corpus Idra suivantes sans les modifier:

- `sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s1_each_tikkun_has_zohar_and_vital`
- `sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s3_see_also_bidirectional`

Ces failures sont converties en événement `source="pytest"`, `id="pytest-bounded-subset-failed"`, `verified=false`, avec `verification_result` rempli. Aucun corpus `sifrei_yesod` n'a été modifié.

## Invariants confirmés

- Aucun commit.
- Aucun push.
- Aucune PR.
- Aucun Docker/PostgreSQL lancé.
- Aucun service compose lancé ou arrêté.
- Aucune migration.
- Aucun daemon permanent, cron, LaunchAgent ou autopilot PR/push.
- Aucun secret, `.env`, credential ou hook touché.
- Aucun miroir Obsidian modifié.
- Aucune faculté FailureToInsight / Guardian / IntentKeeper réécrite.
- Aucun ledger JSONL implémenté.
- `applies_patch=False` reste invariant dans les actions proposées.

PRÊT POUR VALIDATION HERMÈS / YOHAN — PHASE 2A TERMINÉE
