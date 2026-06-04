---
type: codex-prompt
status: ready
created: 2026-06-04
updated: 2026-06-04
tags: [etz-chaim-ai, codex, p1b, psql-helper, targeted-fix]
---

# Codex — GO P1B — fix ciblé `/my/psql`

Copier-coller le bloc ci-dessous dans Codex depuis le repo cible.

Repo cible : `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`

```text
Tu es Codex, lancé dans le repo local Etz Chaim AI :
/Users/fffff/Desktop/developper/claude/etz-chaim-ai

Objectif Phase 1B : corriger uniquement le bug reproductible de pollution inter-tests `/my/psql` identifié en P0, sans élargir le périmètre.

Contexte déjà validé :
- Phase P0 : `strategy/codex-prompt/codex-plan/etzchaim-p0-preflight.md`.
- Phase P1A : `strategy/codex-prompt/codex-plan/etzchaim-p1-improve-safe-surface-report.md`.
- P1A est validée par Hermès : commande `etzchaim improve` OK, dry-run OK, écriture sous HOME temporaire OK, 14 tests ciblés OK.
- Le repo a des changements non commités attendus de P1A. Ne les annule pas.

Bug à corriger :
- `tests/test_install/test_psql_helper.py::test_require_psql_returns_path_when_found` met `ETZ_PSQL_BIN=/my/psql`, recharge `tests._psql`, puis `tests._psql.PSQL_BIN` garde `/my/psql` pour des tests ultérieurs.
- Les tests `sifrei_yesod` réutilisent ensuite `/my/psql`, ce qui produit de nombreuses erreurs dans le full test.

Fichiers à inspecter en priorité :
- `tests/_psql.py`
- `tests/test_install/test_psql_helper.py`
- les tests `sifrei_yesod/tests/*` qui appellent `tests._psql.require_psql()` ou `PSQL_BIN`
- les rapports P0/P1A cités ci-dessus

Contraintes strictes :
- Ne touche pas à Docker, PostgreSQL, services compose, secrets, `.env`, hooks, LaunchAgents, daemon permanent, autopilot PR/push.
- Ne lance pas Docker/PostgreSQL.
- Ne fais pas de `git push`.
- Ne supprime aucun fichier.
- Ne modifie pas le miroir Obsidian : `/Users/fffff/Documents/mon-cerveau/projets/etz-chaim-ai`.
- Reste dans le repo cible Desktop uniquement.
- Ne nettoie pas les doublons du miroir Obsidian : c’est hors scope.
- Ne corrige pas les 4 autres failures du rapport P0 : température, hitlabshut/calibration, duplicate load/create. Hors scope.
- Ne modifie pas `daemon.py`, README, Makefile, packaging global/version CLI, ni la surface `improve`, sauf si un import/test strictement nécessaire l’exige.

Méthode demandée :
1. Commence par lire `AGENTS.md`, puis les deux rapports P0/P1A.
2. Fais un état path-scoped :
   - `git status --short`
   - note explicitement que les changements P1A existants sont à préserver.
3. Reproduis le bug avec le plus petit test ciblé possible. Si besoin, utilise une commande du type :
   `.venv/bin/python -m pytest tests/test_install/test_psql_helper.py::test_require_psql_returns_path_when_found sifrei_yesod/tests/test_folio_map.py -q`
   Ajuste uniquement si ce test précis n’est pas le bon fichier de reproduction.
4. Ajoute d’abord un test de non-régression qui échoue avant patch ou qui démontre clairement la pollution.
5. Applique le patch minimal.
   Piste probable : éviter que `tests._psql` conserve un cache global pollué entre tests, ou rendre `require_psql()` résolutif/idempotent par rapport à l’environnement courant, sans casser l’override explicite `ETZ_PSQL_BIN` dans le test qui le vérifie.
6. Relance les tests ciblés :
   - `tests/test_install/test_psql_helper.py`
   - le ou les tests `sifrei_yesod` impliqués dans la reproduction
   - si rapide, tous les tests `sifrei_yesod/tests/*`
7. Relance aussi :
   - `.venv/bin/python -m pytest tests/test_install/test_cli_improve.py tests/test_metacognition_events.py tests/test_metacognition_collectors.py tests/test_metacognition_first_loop.py -q`
   pour vérifier que P1A n’a pas régressé.
8. Lance `git diff --check`.
9. Écris un rapport final ici :
   `strategy/codex-prompt/codex-plan/etzchaim-p1b-psql-helper-fix-report.md`

Le rapport final doit contenir :
- fichiers modifiés ;
- cause racine confirmée ;
- patch appliqué ;
- commandes lancées et sorties résumées ;
- tests passés/échoués ;
- éléments explicitement non touchés ;
- prochaine étape proposée ;
- mention `PRÊT POUR VALIDATION HERMÈS / YOHAN — PHASE 1B TERMINÉE` si tout est OK.

À la fin, ne pousse rien. Ne crée pas de PR. Ne fais pas de commit sauf si Yohan l’a explicitement demandé dans Codex.
```
