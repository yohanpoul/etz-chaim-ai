# Etz Chaim AI - Phase 2B Action Synthesis + Ledger

## Base et branche

- Repo cible: `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`
- Base verifiee: `1ca0585 feat: add p2a pytest verification observer`
- Branche creee: `codex/phase-2b-action-synthesis-ledger`
- Etat initial: propre avant creation de branche
- Branche P2B inexistante avant creation: oui

## Plan execute

1. Ajouter des tests rouges pour la synthese d'actions et le ledger append-only.
2. Implementer `synthesize_actions(events)` avec mapping minimal P2B.
3. Enforcer `applies_patch=False` dans `ProposedAction`.
4. Ajouter le chemin ledger dans `would_write` et `written`.
5. Append une seule ligne JSONL par run non-dry dans `state/improve_ledger.jsonl`.
6. Relancer les validations bornees demandees, sans full `make test`.

## Fichiers modifies

- `etzchaim/metacognition/actions.py`
- `etzchaim/metacognition/events.py`
- `etzchaim/metacognition/report.py`
- `tests/test_install/test_cli_improve.py`
- `tests/test_metacognition_events.py`
- `tests/test_metacognition_first_loop.py`
- `strategy/codex-prompt/codex-plan/etzchaim-p2b-action-synthesis-ledger-report.md`

## Implementation

- `synthesize_actions(events) -> list[ProposedAction]` ajoute une surface explicite de synthese.
- `propose_actions(events)` reste disponible comme alias retrocompatible.
- Mapping P2B:
  - `source="pytest"` -> action `test`
  - `source="doctor"` / `source="status"` -> action `alert`
  - `source="python"` -> action `rule`
  - `known-p0-psql-helper-pollution` -> action `patch` proposee seulement
- `ProposedAction(applies_patch=True)` est rejete: l'invariant P2B reste non destructif.
- Les runs dry-run retournent `would_write.report`, `would_write.state`, `would_write.ledger` sans creer de repertoire.
- Les runs non-dry ecrivent:
  - rapport markdown
  - `state/last_improve_run.json`
  - une ligne JSONL append-only dans `state/improve_ledger.jsonl`
- Le ledger contient: `timestamp`, `top_issue_id`, `action_id`, `action_type`, `applies_patch`, `verified`, `verification_result`, `guardian_verdict="not_evaluated_p2b"`.

## Tests et validations

- Rouge TDD initial:
  - `.venv/bin/python -m pytest tests/test_metacognition_events.py tests/test_metacognition_first_loop.py tests/test_install/test_cli_improve.py -q`
  - Resultat attendu: `5 failed, 10 passed`
  - Causes: `synthesize_actions` absent, ledger absent, chemins `ledger` absents.
- Vert cible apres patch:
  - meme commande
  - Resultat: `15 passed in 0.11s`
- Validation P2A/P2B:
  - `.venv/bin/python -m pytest tests/test_metacognition_events.py tests/test_metacognition_collectors.py tests/test_metacognition_first_loop.py tests/test_metacognition_verify.py tests/test_install/test_cli_improve.py tests/test_install/test_cli_version_info.py -q`
  - Resultat: `28 passed in 0.15s`
- Non-regression P1B:
  - `.venv/bin/python -m pytest tests/test_install/test_psql_helper.py sifrei_yesod/tests/test_folio_map.py -q`
  - Resultat: `17 passed in 0.25s`
- Smoke dry-run:
  - `.venv/bin/etzchaim improve --once --dry-run --json`
  - Resultat: exit `0`, JSON valide, `would_write.ledger` present, aucune ecriture durable.
- Smoke non-dry sous HOME temporaire:
  - `TMP_HOME=$(mktemp -d); HOME="$TMP_HOME" .venv/bin/etzchaim improve --once --json`
  - Resultat: exit `0`, report + state + ledger ecrits sous:
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.8p8tlWalFa/.etz-chaim/runs/improve-20260604T102319Z.md`
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.8p8tlWalFa/.etz-chaim/state/last_improve_run.json`
    - `/var/folders/6x/7kkcg3j57c5_zplrqbmsv2xw0000gp/T/tmp.8p8tlWalFa/.etz-chaim/state/improve_ledger.jsonl`
- Whitespace:
  - `git diff --check`
  - Resultat: OK, aucune sortie.
- LaunchAgent:
  - `launchctl list | grep etzchaim || true`
  - Resultat: aucune sortie.

## Observations conservees

- Les deux failures Idra restent observees par le collecteur pytest borne:
  - `test_s1_each_tikkun_has_zohar_and_vital`
  - `test_s3_see_also_bidirectional`
- Elles ne sont pas corrigees en P2B.
- Le bug P0 `/my/psql` reste un evenement documentaire/statique si le rapport P0 le mentionne; P2B propose seulement une action `patch` non appliquee.
- Les alertes Docker/PostgreSQL/services down restent des observations locales; aucun service n'a ete demarre.

## Invariants respectes

- Aucun commit.
- Aucun push.
- Aucune PR.
- Aucun Docker/PostgreSQL/compose/migration/daemon/cron/LaunchAgent demarre.
- Aucun ledger JSONL cree en dry-run.
- Ledger cree uniquement en run non-dry sous HOME temporaire pendant validation.
- Pas de P2C.
- Pas de modification du corpus `sifrei_yesod`.
- Pas de reecriture FailureToInsight / Guardian / IntentKeeper.
- `applies_patch=False` reste invariant pour toutes les actions proposees.
- Aucune modification P2B conservee dans le miroir Obsidian; les fichiers P2B sont uniquement dans le repo Desktop cible.

## Dette restante

- Le ledger P2B est volontairement minimal et ne branche pas encore Guardian/SelfModel.
- `guardian_verdict` reste `not_evaluated_p2b`.
- Le ledger append-only n'a pas encore de schema versionne ni de rotation; c'est attendu pour P2B minimal.
- Les failures Idra observees devront rester hors scope jusqu'a une phase explicitement validee.

## Prochaine etape proposee

- Faire valider P2B par Hermes/Yohan.
- Ensuite seulement, preparer P2C pour brancher les facultes/Guardian en lecture et enrichir le verdict sans auto-reparation.

PRET POUR VALIDATION HERMES / YOHAN - PHASE 2B TERMINEE
