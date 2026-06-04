---
type: codex-prompt
status: ready
created: 2026-06-04
updated: 2026-06-04
tags: [etz-chaim-ai, codex, checkpoint, p1a, p1b]
---

# Codex — checkpoint local P1A + P1B validées

Copier-coller le bloc ci-dessous dans Codex uniquement si Yohan valide le checkpoint local.

Repo cible : `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`

```text
Tu es Codex, lancé dans le repo local Etz Chaim AI :
/Users/fffff/Desktop/developper/claude/etz-chaim-ai

Objectif : créer un checkpoint local propre des phases P1A + P1B déjà validées par Hermès, sans push et sans élargir le périmètre.

Contexte validé :
- P0 preflight : `strategy/codex-prompt/codex-plan/etzchaim-p0-preflight.md`.
- P1A improve safe surface : validée par Hermès.
- P1B psql helper fix : validée par Hermès.
- Vérifications Hermès P1B : reproduction `/my/psql` OK, helper psql OK, P1A non-régression OK, `git diff --check` OK.

Contraintes strictes :
- Ne modifie plus le code fonctionnel sauf si une vérification échoue pour une raison directement liée au checkpoint.
- Ne touche pas Docker, PostgreSQL, services compose, secrets, `.env`, hooks, LaunchAgents, daemon permanent, README, Makefile, packaging global/version CLI.
- Ne modifie pas le miroir Obsidian `/Users/fffff/Documents/mon-cerveau/projets/etz-chaim-ai`.
- Ne supprime rien.
- Ne fais pas de PR.
- Ne fais pas de `git push`.

Étapes :
1. Lire `AGENTS.md`.
2. Afficher `git status --short` et confirmer que les changements correspondent aux phases P1A/P1B + rapports/prompts sous `strategy/codex-prompt/`.
3. Relancer ces vérifications :
   - `.venv/bin/python -m pytest tests/test_install/test_psql_helper.py -q`
   - `.venv/bin/python -m pytest sifrei_yesod/tests/test_folio_map.py -q`
   - `.venv/bin/python -m pytest tests/test_install/test_cli_improve.py tests/test_metacognition_events.py tests/test_metacognition_collectors.py tests/test_metacognition_first_loop.py -q`
   - `git diff --check`
4. Si tout passe, écrire un court rapport de checkpoint :
   `strategy/codex-prompt/codex-plan/etzchaim-p1ab-local-checkpoint-report.md`
   avec : fichiers inclus, tests relancés, statut, contraintes respectées.
5. Stager uniquement les fichiers P1A/P1B et les prompts/rapports associés :
   - `etzchaim/cli/app.py`
   - `etzchaim/cli/commands/improve.py`
   - `etzchaim/metacognition/`
   - `tests/test_install/test_cli_improve.py`
   - `tests/test_metacognition_events.py`
   - `tests/test_metacognition_collectors.py`
   - `tests/test_metacognition_first_loop.py`
   - `tests/_psql.py`
   - `tests/test_install/test_psql_helper.py`
   - `strategy/codex-prompt/`
6. Créer un commit local, sans push, avec le message :
   `feat: add safe improve surface and psql regression fix`
7. Afficher le commit SHA, puis `git status --short`.

À la fin : pas de PR, pas de push. Termine par :
`CHECKPOINT LOCAL P1A/P1B CRÉÉ — PRÊT POUR VALIDATION HERMÈS / YOHAN`.
```
