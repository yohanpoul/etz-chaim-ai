# Etz Chaim AI - P2C-bis Faculty Bridge Hardening

## Etat initial

- Repo cible: `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`
- Branche: `codex/phase-2c-faculties-bridge`
- HEAD: `2bae437 feat: add p2b action synthesis ledger`
- `git status --short --branch` initial:

```text
## codex/phase-2c-faculties-bridge
 M etzchaim/metacognition/report.py
 M tests/test_install/test_cli_improve.py
 M tests/test_metacognition_first_loop.py
?? etzchaim/metacognition/faculties.py
?? strategy/codex-prompt/codex-plan/etzchaim-p2c-faculties-bridge-report.md
?? tests/test_metacognition_faculties.py
```

Les changements presents correspondaient a la P2C en cours. Aucun reset, stash,
restore, clean ou suppression n'a ete execute.

## Fichiers modifies

- `etzchaim/metacognition/faculties.py`
- `tests/test_metacognition_faculties.py`
- `tests/test_install/test_cli_improve.py`
- `strategy/codex-prompt/codex-plan/etzchaim-p2c-bis-hardening-report.md`

Fichiers P2C preserves, non supprimes:

- `etzchaim/metacognition/report.py`
- `tests/test_metacognition_first_loop.py`
- `strategy/codex-prompt/codex-plan/etzchaim-p2c-faculties-bridge-report.md`

## Changements realises

- FailureToInsight:
  - aucune instanciation de `FailureToInsight`, `FailureToInsightDB`, Postgres ou DB par defaut;
  - sans adaptateur injecte, retour degrade documente;
  - avec adaptateur injecte, `guide_next_hypothesis()` reste le chemin lecture sure;
  - un adaptateur exposant seulement `analyze_failure()` n'est plus appele implicitement, car cette methode peut persister.
- Guardian:
  - aucun `Guardian()` implicite sans adaptateur explicite;
  - sans adaptateur explicite/contexte reel, verdict `unavailable` avec raison claire;
  - les adaptateurs injectes conservent `evaluate_confidence(domain, query)`.
- IntentKeeper:
  - aucune instanciation de `IntentKeeper` ou `IntentKeeperDB` par defaut;
  - sans adaptateur injecte, statut `no_active_intent`.
- Tests:
  - ajout de tests anti-import runtime DB sans adaptateurs;
  - ajout d'un test prouvant que `analyze_failure()` seul n'est pas appele;
  - ajout d'un test Guardian sans adaptateur explicite: pas de `proceed`;
  - conservation des fakes injectes et de l'invariant `applies_patch=False`;
  - neutralisation de `ETZCHAIM_STATE_DIR` dans le test CLI dry-run.

## Validations lancees

Variables utilisees pour pytest:

```bash
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_ADDOPTS="${PYTEST_ADDOPTS:-} -p no:cacheprovider"
```

- Rouge TDD cible:
  - Commande: `.venv/bin/python -m pytest tests/test_metacognition_faculties.py -q`
  - Resultat avant patch: `2 failed, 4 passed`
  - Echecs attendus: Guardian implicite `proceed`; `analyze_failure()` appele implicitement.
- Vert cible:
  - Commande: `.venv/bin/python -m pytest tests/test_metacognition_faculties.py -q`
  - Resultat: `6 passed in 0.03s`
- Validation metacognition/CLI:
  - Commande: `.venv/bin/python -m pytest tests/test_metacognition_events.py tests/test_metacognition_collectors.py tests/test_metacognition_first_loop.py tests/test_metacognition_verify.py tests/test_metacognition_faculties.py tests/test_install/test_cli_improve.py tests/test_install/test_cli_version_info.py -q`
  - Resultat: `34 passed in 0.21s`
- Non-regression P1B:
  - Commande: `.venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q`
  - Resultat: `17 passed in 0.50s`
- Smoke dry-run:
  - Commande: `.venv/bin/etzchaim improve --once --dry-run --json`
  - Resultat: exit `0`, `status="dry-run"`, `faculty_evaluation.guardian.verdict="unavailable"`, aucune ecriture durable.
- Smoke write-mode sous HOME temporaire:
  - Commande: `TMP_HOME=$(mktemp -d); HOME="$TMP_HOME" .venv/bin/etzchaim improve --once --json`
  - Resultat: exit `0`, report + state + ledger ecrits sous:
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.qoth1J6YzV/.etz-chaim/runs/improve-20260604T115820Z.md`
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.qoth1J6YzV/.etz-chaim/state/last_improve_run.json`
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.qoth1J6YzV/.etz-chaim/state/improve_ledger.jsonl`
- Whitespace:
  - Commande: `git diff --check`
  - Resultat: OK, aucune sortie.
- LaunchAgent:
  - Commande: `launchctl list | grep etzchaim || true`
  - Resultat: aucune sortie.
- Status final avant rapport:
  - Commande: `git status --short --branch`
  - Resultat limite aux fichiers P2C/P2C-bis.
- Fichiers non suivis avant rapport:
  - Commande: `git ls-files --others --exclude-standard`
  - Resultat:

```text
etzchaim/metacognition/faculties.py
strategy/codex-prompt/codex-plan/etzchaim-p2c-faculties-bridge-report.md
tests/test_metacognition_faculties.py
```

## Confirmations

- Aucune suppression de fichier, dossier, module, test, document, corpus, strategie ou fonctionnalite.
- Aucun `rm`, `git clean`, `git reset --hard`, nettoyage global ou restauration destructive.
- Aucun daemon, LaunchAgent, Docker, PostgreSQL, compose, cron, migration ou service permanent lance.
- Aucun commit.
- Aucun push.
- Aucune PR.
- Aucun corpus `sifrei_yesod` modifie.
- Aucun miroir Obsidian modifie.
- Aucun module profond `failuretoinsight/**`, `intentkeeper/**`, `selfmodel/**` modifie.
- `autopilot/git_integration/pr.py` non touche.
- Aucune action proposee par `improve` appliquee.
- `applies_patch=False` reste invariant.

## Dettes restantes

- FailureToInsight et IntentKeeper restent volontairement non branches a une DB reelle.
- Guardian necessite maintenant un adaptateur explicite pour produire autre chose que `unavailable`.
- Les failures Idra restent observees seulement, non corrigees.
- P2C-bis ne cree pas de checkpoint; attente validation Hermes/Yohan.

PRET POUR VALIDATION HERMES / YOHAN - P2C-BIS TERMINEE
