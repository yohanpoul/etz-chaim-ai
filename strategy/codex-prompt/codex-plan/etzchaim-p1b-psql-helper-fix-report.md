# Etz Chaim AI - Phase 1B psql helper fix report

Date: 2026-06-04
Répertoire cible: `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`
Branche locale: `codex/phase-1a-improve-safe-surface`

## Fichiers modifiés

- `tests/_psql.py`
- `tests/test_install/test_psql_helper.py`
- `strategy/codex-prompt/codex-plan/etzchaim-p1b-psql-helper-fix-report.md`

Les changements P1A non commités ont été préservés.

## Cause racine confirmée

`tests/_psql.py` initialisait `PSQL_BIN` au chargement du module:

```python
PSQL_BIN = os.environ.get("ETZ_PSQL_BIN") or shutil.which("psql")
```

Le test `tests/test_install/test_psql_helper.py::test_require_psql_returns_path_when_found` posait `ETZ_PSQL_BIN=/my/psql` puis rechargeait `tests._psql`. Comme `PSQL_BIN` restait une globale figée, les fixtures `sifrei_yesod` réutilisaient ensuite `/my/psql` dans `require_psql()`, même après restauration de l'environnement par `monkeypatch`.

Reproduction avant patch:

```bash
.venv/bin/python -m pytest tests/test_install/test_psql_helper.py::test_require_psql_returns_path_when_found sifrei_yesod/tests/test_folio_map.py::test_folio_map_exists -q
```

Résultat avant patch: `1 passed, 1 error`, avec `FileNotFoundError: [Errno 2] No such file or directory: '/my/psql'`.

## Patch appliqué

Patch minimal:

- ajout de `resolve_psql_bin()` dans `tests/_psql.py`;
- conservation de `PSQL_BIN` comme snapshot d'import pour les tests existants;
- modification de `require_psql()` pour relire l'environnement courant à chaque appel et mettre `PSQL_BIN` à jour;
- ajout d'un test de non-régression prouvant que `require_psql()` ne conserve pas `/my/psql` après suppression de `ETZ_PSQL_BIN`.

Aucun code produit, service, secret, config sensible, daemon, autopilot ou surface `improve` n'a été modifié pour cette phase.

## Commandes lancées et sorties résumées

```bash
git status --short
```

État initial scoped Desktop: changements P1A non commités attendus à préserver (`etzchaim/cli/app.py`, commande `improve`, modules `metacognition`, tests P1A, dossier `strategy/`).

```bash
.venv/bin/python -m pytest tests/test_install/test_psql_helper.py::test_require_psql_returns_path_when_found sifrei_yesod/tests/test_folio_map.py::test_folio_map_exists -q
```

Avant patch: `1 passed, 1 error`, erreur `/my/psql`.
Après patch: `2 passed in 0.18s`.

```bash
.venv/bin/python -m pytest tests/test_install/test_psql_helper.py::test_require_psql_re_resolves_after_env_override_removed -q
```

Avant patch: échec attendu, `'/my/psql' != '/real/psql'`.
Après patch: `1 passed in 0.01s`.

```bash
.venv/bin/python -m pytest tests/test_install/test_psql_helper.py -q
```

Résultat: `6 passed in 0.01s`.

```bash
.venv/bin/python -m pytest sifrei_yesod/tests/test_folio_map.py -q
```

Résultat: `11 passed in 0.15s`.

```bash
.venv/bin/python -m pytest sifrei_yesod/tests -q
```

Résultat: `2 failed, 46 passed, 2 skipped, 4 warnings in 2.38s`.

Les 2 failures restantes sont hors scope Phase 1B:

- `sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s1_each_tikkun_has_zohar_and_vital`
- `sifrei_yesod/tests/test_idra_corpus_fidelity.py::test_s3_see_also_bidirectional`

Important: la suite `sifrei_yesod` ne produit plus d'erreur `/my/psql`.

```bash
.venv/bin/python -m pytest tests/test_install/test_cli_improve.py tests/test_metacognition_events.py tests/test_metacognition_collectors.py tests/test_metacognition_first_loop.py -q
```

Résultat: `14 passed in 0.12s`. P1A n'a pas régressé.

```bash
git diff --check
```

Résultat: exit `0`, aucune erreur whitespace.

## Tests passés/échoués

Passés:

- `tests/test_install/test_psql_helper.py`: `6 passed`.
- reproduction P0 ciblée: `2 passed`.
- `sifrei_yesod/tests/test_folio_map.py`: `11 passed`.
- tests P1A improve/metacognition: `14 passed`.
- `git diff --check`: OK.

Échoués hors scope:

- `sifrei_yesod/tests`: `2 failed, 46 passed, 2 skipped, 4 warnings`.
- Les failures restantes concernent la fidélité corpus Idra, pas le helper `psql`.

Le full `make test` n'a pas été lancé: P0 a déjà documenté d'autres failures hors scope et Phase 1B se limite au bug `/my/psql`.

## Éléments explicitement non touchés

- Pas de Docker/PostgreSQL lancé.
- Pas de service compose lancé ou arrêté.
- Pas de migration.
- Pas de `.env`, secret, credential, hook ou LaunchAgent touché.
- Pas de `daemon.py`.
- Pas de README, Makefile, packaging global/version CLI.
- Pas de modification de la surface `improve`.
- Pas de correction température, hitlabshut/calibration, duplicate load/create.
- Pas de modification du miroir Obsidian `/Users/fffff/Documents/mon-cerveau/projets/etz-chaim-ai`.
- Pas de commit.
- Pas de PR.
- Pas de `git push`.

## Prochaine étape proposée

Phase 1C proposée, non exécutée: traiter les 2 failures `sifrei_yesod/tests/test_idra_corpus_fidelity.py` restantes comme une dette corpus séparée, avec validation doctrinale dédiée. Ne pas les mélanger avec le helper `psql`.

PRÊT POUR VALIDATION HERMÈS / YOHAN — PHASE 1B TERMINÉE
