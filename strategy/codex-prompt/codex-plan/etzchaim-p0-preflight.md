# Etz Chaim AI - P0 preflight technique

Date: 2026-06-04
Répertoire inspecté: `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`
Mission: préflight uniquement, avant implémentation du premier métier opérationnel.

Premier métier cible:

> Etz Chaim est le daemon de métacognition des agents : il observe erreurs, dérives, tests, specs et décisions, puis transforme chaque faiblesse en règle, test, patch ou alerte vérifiable.

Niveau de preuve utilisé dans ce rapport:

- `[E1]` sortie de commande locale ou lecture directe d'un fichier du repo.
- `[E2]` inférence directe à partir du code ou de la combinaison code + sortie de test.
- `[E3]` recommandation de plan pour la phase suivante.

## 1. État réel observé

Le repo attendu existe et a été inspecté depuis `/Users/fffff/Desktop/developper/claude/etz-chaim-ai`. Le `git status --short` initial était vide. [E1]

La surface CLI réelle ne correspond pas entièrement à la documentation. `README.md` mentionne `etzchaim improve --once`, mais `etzchaim --help` ne liste pas de commande `improve`; `etzchaim/cli/app.py` importe les commandes existantes (`doctor`, `status`, `start`, `stop`, etc.) sans module `improve`. [E1]

Le comportement `--once` existe bien, mais aujourd'hui il vit dans `daemon.py` comme interface script (`python daemon.py --once`, `python daemon.py --task auto-improve`) et non dans la CLI canonique `etzchaim`. [E1]

`make doctor` est documenté dans les instructions projet, mais le `Makefile` ne contient pas de cible `doctor`. Les cibles présentes incluent notamment `test`, `test-core`, `lint`, `format`, `docs`, `demo`, `clean`, `release`, `check-model-leaks`. [E1]

`etzchaim doctor --json` échoue partiellement dans l'environnement local actuel: Docker, les services compose et PostgreSQL sont absents/down; Ollama est joignable, la clé API locale est présente, et le port dashboard canonique est déclaré. Le doctor implémenté est un doctor MVP à 6 checks, alors que la documentation évoque 20 checks. [E1]

`etzchaim status --json` répond correctement mais signale une liste de services vide: `{"profile":"hybrid-host-ollama","services":[]}`. [E1]

L'autopilot possède un dry-run fonctionnel via `python3 -m etzchaim.autopilot.loop --dry-run` et `.venv/bin/python -m etzchaim.autopilot.loop --dry-run`. Le dry-run retourne une tâche de spec (`04_rectifiers/07`, type `implement-rectifier`) et ne déclenche pas de worker. Cette boucle est donc utile, mais elle n'est pas encore le collecteur du métier "daemon de métacognition". [E1][E2]

Les tests ciblés liés à CLI/install, daemon, daemon bridge, guardian, autopilot, FailureToInsight, SelfModel et SelfMap passent: `156 passed in 1.16s`. [E1]

Le gate complet `make test` échoue: `4 failed, 1511 passed, 8 skipped, 4 warnings, 50 errors in 12.06s`. Les 50 erreurs observées viennent des tests `sifrei_yesod` qui tentent d'utiliser `/my/psql`. Une reproduction ciblée montre que `tests/test_install/test_psql_helper.py::test_require_psql_returns_path_when_found` pollue `tests._psql.PSQL_BIN` avec `/my/psql`, puis les tests suivants réutilisent cette valeur. [E1][E2]

Les 4 failures distincts du full test sont:

- `tests/test_olamot_temperature_warning.py::TestTemperatureWarning::test_real_config_briah_warns_under_claude_max`: warning attendu non observé. [E1]
- `tests/test_sprint8_d1_hitlabshut.py::test_delta_overall_matches_doctrinal_calibration`: delta attendu environ `0.02`, delta observé `0.12909090909090906`. [E1]
- `tests/test_sprint8_d1_hitlabshut.py::test_multiple_mutual_reinforcements_accumulate_correctly`: delta attendu environ `0.06`, delta observé `0.1690909090909091`. [E1]
- `partzufim/tests/test_zivvug_refactor_l.py::test_no_duplicate_load_or_create_pattern`: pattern legacy détecté dans `build/lib/partzufim/zivvug.py` et dans `build/lib/partzufim/tests/test_zivvug_refactor_l.py`. [E1]

L'environnement Python est incohérent:

- `python --version` échoue car `python` n'est pas dans le PATH. [E1]
- `python3 --version` retourne Python `3.9.6`. [E1]
- `.venv/bin/python --version` retourne Python `3.13.12`. [E1]
- `pyproject.toml` déclare `requires-python = ">=3.10"`, tandis que les règles projet demandent Python 3.12+. [E1]

La version package est également incohérente:

- `pyproject.toml` déclare `0.3.0`. [E1]
- `.venv/bin/etzchaim` affiche `0.2.3`. [E1]
- `.venv/bin/python -m pip show etzchaim` affiche `0.2.0` en editable install. [E1]
- Le CLI global `/Users/fffff/.local/bin/etzchaim` affiche `0.2.18`. [E1]

Les modules nécessaires au premier métier existent en fragments, mais ils ne sont pas encore reliés dans une boucle minimale unique, testée, non destructive et exposée par CLI. [E2]

## 2. Commandes lancées et résultats résumés

| Commande | Résultat résumé | Interprétation |
|---|---:|---|
| `git status --short` | sortie vide au départ | repo propre avant le rapport [E1] |
| `python --version` | `zsh: command not found: python` | la commande documentée `python -m ...` n'est pas portable localement [E1] |
| `python3 --version` | `Python 3.9.6` | Python système sous le niveau projet visé [E1] |
| `.venv/bin/python --version` | `Python 3.13.12` | l'environnement de dev utilisable est la venv [E1] |
| `etzchaim --help` | pas de commande `improve` | drift README/CLI [E1] |
| `.venv/bin/etzchaim --help` | pas de commande `improve` | drift aussi dans la CLI locale [E1] |
| `etzchaim --version` | `0.2.18` | CLI globale différente du repo [E1] |
| `.venv/bin/etzchaim --version` | `0.2.3` | CLI venv différente de `pyproject.toml` [E1] |
| `.venv/bin/python -m pip show etzchaim` | version `0.2.0` | metadata install incohérente [E1] |
| `etzchaim doctor --json` | exit `1`, 3 failures sur 6 checks | Docker/services/PostgreSQL down; Ollama/key/port OK [E1] |
| `.venv/bin/etzchaim doctor --json` | même résultat | problème environnemental, pas seulement CLI globale [E1] |
| `etzchaim status --json` | exit `0`, services `[]` | status fonctionne, services absents [E1] |
| `.venv/bin/etzchaim status --json` | même résultat | status local cohérent [E1] |
| `python -m etzchaim.autopilot.loop --dry-run` | échec: `python` absent | utiliser `python3` ou `.venv/bin/python` [E1] |
| `python3 -m etzchaim.autopilot.loop --dry-run` | `status: dry-run`, tâche `04_rectifiers/07` | dry-run autopilot opérationnel [E1] |
| `.venv/bin/python -m etzchaim.autopilot.loop --dry-run` | même résultat | dry-run opérationnel dans la venv [E1] |
| targeted pytest CLI/daemon/autopilot/facultés | `156 passed in 1.16s` | socle local ciblé sain [E1] |
| `make test` | `4 failed`, `50 errors`, `1511 passed` | gate complet non vert [E1] |
| reproduction psql ciblée | un test helper puis un test `sifrei_yesod` reproduisent `/my/psql` | bug de pollution inter-tests [E1][E2] |

Note: le dry-run autopilot journalise un cycle dans l'état utilisateur hors repo (`~/.etz-chaim/autopilot/cycle_log.db`). Cette commande était explicitement listée comme diagnostic sûr; aucun fichier de code du repo n'a été modifié par ce dry-run. [E1]

## 3. Carte des fichiers/modules pertinents

Surface racine et packaging:

- `README.md`: quick start, mention `etzchaim improve --once`, claims opérationnelles.
- `Makefile`: gate test/lint existants, absence de `doctor`.
- `pyproject.toml`: metadata, dépendances, entrypoint `etzchaim = "etzchaim.cli.app:app"`, version `0.3.0`.
- `AGENTS.md` et `.claude/rules/*`: invariants, provider-agnostic core, règles de tests et neutralité publique.

CLI:

- `etzchaim/cli/app.py`: application Typer, commandes importées, pas de commande `improve`.
- `etzchaim/cli/commands/doctor.py`: commande `doctor --json`.
- `etzchaim/cli/doctor/checks.py`: 6 checks MVP actuels.
- `etzchaim/cli/commands/status.py`: commande `status --json`.
- `etzchaim/cli/compose.py`, `etzchaim/cli/detect.py`, `etzchaim/cli/runtime.py`: détection runtime et services compose.

Daemon et tâches:

- `daemon.py`: boucle principale, lock PID, state/report, `--once`, `--task`, auto-improve, auto-dev.
- `daemon_tasks/auto_dev.py`: tâche auto-dev optionnelle.
- `daemon_tasks/chokmah.py`: recyclage de rejets AutoJudge/InsightForge vers FailureToInsight.
- `daemon_tasks/daat.py`: maintenance/prediction SelfModel.
- `daemon_tasks/exploration.py`: tâches d'exploration.

Autopilot:

- `etzchaim/autopilot/loop.py`: boucle dry-run/worker, choix de tâche spec, journal SQLite.
- `etzchaim/autopilot/config.py`: config, budget, chemins exclus, enabled flag.
- `etzchaim/autopilot/state.py`: cycle log SQLite et compteur d'échecs.
- `etzchaim/autopilot/curator.py`: sélection de specs non implémentées.
- `etzchaim/autopilot/delegation/*`: worker/subagent.
- `etzchaim/autopilot/runners/*`: exécution locale et skill Claude.
- `etzchaim/autopilot/git_integration/*`: branch/commit/PR; attention au push par défaut dans `pr.py`.

Facultés métier déjà présentes:

- `failuretoinsight/core.py`, `failuretoinsight/models.py`, `failuretoinsight/classifier.py`, `failuretoinsight/cli.py`, `failuretoinsight/db.py`.
- `selfmap/core.py`, `selfmap/models.py`, `selfmap/domain_detector.py`, `selfmap/cli.py`.
- `selfmodel/core.py`, `selfmodel/guardian.py`, `selfmodel/predictor.py`, `selfmodel/models.py`, `selfmodel/cli.py`.
- `intentkeeper/core.py`, `intentkeeper/models.py`, `intentkeeper/cli.py`.

Tests pertinents:

- `tests/test_daemon_sprint0.py`, `tests/test_daemon_bridge.py`.
- `tests/test_daat_guardian.py`.
- `etzchaim/autopilot/tests/*`.
- `failuretoinsight/tests/*`.
- `selfmap/tests/*`.
- `selfmodel/tests/*`.
- `intentkeeper/tests/*`.
- `tests/test_install/test_cli_version_info.py`, `tests/test_install/test_cli_detect.py`, `tests/test_install/test_psql_helper.py`.
- `sifrei_yesod/tests/*`, pour le bug de pollution `/my/psql`.

## 4. Ce qui existe déjà pour le premier métier

Le repo possède déjà une boucle daemon scriptable: `daemon.py` sait exécuter un cycle unique, gérer un lock PID, écrire un état, produire un rapport, choisir des tâches périodiques et déclencher `auto-improve`/`auto-dev`. [E1]

FailureToInsight possède la logique la plus proche du métier cible: analyse d'une erreur, classification, extraction d'insights, graphe de patterns, guidance de prochaine hypothèse et autodiagnostic. [E1]

IntentKeeper sait représenter des intentions, sous-tâches, échecs, retries, abandon criteria, progression et adaptation de stratégie. Il peut devenir le registre des remédiations proposées ou suivies. [E1][E2]

SelfModel fournit une capacité de prédiction/évaluation d'erreur et de confiance; Guardian ajoute un garde-fou conceptuel de risque avant action. [E1]

SelfMap sait estimer compétence et routage par domaine; il peut contextualiser les faiblesses détectées par type de tâche ou domaine. [E1]

Le doctor/status CLI fournit déjà des signaux observables non destructifs: environnement, services, Ollama, clé API, dashboard. [E1]

Le full test a déjà produit un exemple exploitable du métier cible: une faiblesse technique (`/my/psql` pollué par un test helper) qui peut être transformée en règle, test de non-régression, patch ciblé et alerte vérifiable. [E1][E2]

L'autopilot dry-run sait sélectionner une tâche sans dispatch worker; c'est une brique utile de planification, mais il cible aujourd'hui l'implémentation de specs et non l'observation des faiblesses agent/test/doctor. [E1][E2]

## 5. Ce qui manque vraiment

Il manque la commande canonique `etzchaim improve --once` documentée, avec mode `--dry-run` et sortie `--json`, reliée au daemon ou à une boucle métier minimale. [E2]

Il manque un modèle d'événement de métacognition stable: source (`doctor`, `pytest`, `spec`, `decision`, `daemon`, `autopilot`), sévérité, preuve, cause probable, action proposée (`rule`, `test`, `patch`, `alert`) et commande de vérification. [E3]

Il manque un collecteur local non destructif capable d'agréger `doctor`, `status`, tests ciblés et erreurs connues sans nécessiter Docker/PostgreSQL. [E2]

Il manque une passerelle simple entre événements observés et facultés existantes: FailureToInsight pour transformer l'erreur en insight, SelfModel/Guardian pour estimer le risque, SelfMap pour contextualiser le domaine, IntentKeeper pour suivre la remédiation. [E2]

Il manque un fallback local quand PostgreSQL ou Docker sont down. Le premier métier doit fonctionner en mode minimal même quand les services sont absents, sinon il ne peut pas observer correctement les pannes d'environnement. [E2]

Il manque des tests qui garantissent que la première boucle ne démarre aucun service, ne pousse rien, ne lance aucune migration destructive et ne modifie pas le code en mode dry-run. [E3]

Il manque une séparation stricte entre proposition et exécution: la phase 1 doit produire un plan/action report vérifiable, pas appliquer automatiquement des patchs. [E3]

Il manque un alignement packaging/version avant de faire confiance à la CLI installée: `pyproject.toml`, venv, egg-info et CLI globale ne racontent pas la même version. [E1][E2]

Il manque l'alignement Makefile/docs autour de `make doctor`, et potentiellement autour de `make verify-bidirectional` / `make check-public-surface` si ces commandes restent publiées comme standards. [E1][E2]

Il manque la résolution des blockers du full test, en priorité le bug de pollution `/my/psql`, car il est petit, reproductible et directement aligné avec le premier métier. [E1][E3]

## 6. Proposition de plan d'implémentation en 3 à 5 PR/commits maximum

### PR 1 - Surface opérationnelle sûre

Objectif: aligner la CLI et les commandes documentées sans activer encore de mutation automatique.

Changements proposés:

- Ajouter `etzchaim improve --once --dry-run --json`.
- Brancher cette commande sur une boucle minimale non destructive.
- Ajouter `make doctor`.
- Corriger le README pour refléter la vraie commande et le mode sûr.
- Ajouter des tests CLI help/version/commande.

Critère de sortie: `etzchaim improve --once --dry-run --json` retourne un JSON valide, ne démarre aucun service, ne modifie pas de code, ne pousse rien. [E3]

### PR 2 - Modèle d'événement et collecteurs de métacognition

Objectif: créer le coeur métier minimal indépendant des services.

Changements proposés:

- Créer `etzchaim/metacognition/`.
- Définir `MetacognitionEvent`, `Evidence`, `ProposedAction`.
- Ajouter collecteurs `doctor`, `status`, `pytest summary`, `known test failures`.
- Produire une sortie JSON + markdown interne.

Critère de sortie: les échecs doctor et le bug `/my/psql` deviennent des événements structurés avec action proposée et commande de vérification. [E3]

### PR 3 - Pont vers les facultés existantes

Objectif: relier la boucle métier aux modules existants sans les réécrire.

Changements proposés:

- Envoyer les événements de failure vers FailureToInsight quand la DB est disponible.
- Utiliser SelfModel/Guardian pour annoter le risque de dérive.
- Utiliser SelfMap pour annoter le domaine.
- Utiliser IntentKeeper pour créer/suivre une intention de remédiation.
- Prévoir fallback local si DB/services indisponibles.

Critère de sortie: la boucle fonctionne en mode dégradé local et en mode enrichi si les services sont up. [E3]

### PR 4 - Stabilisation du gate test P0

Objectif: faire passer les tests nécessaires à l'activation de la boucle et documenter les blockers restants.

Changements proposés:

- Corriger la pollution `tests._psql.PSQL_BIN = /my/psql`.
- Corriger ou isoler le scan legacy qui lit `build/lib`.
- Corriger le warning de température attendu.
- Triage du delta calibration hitlabshut.

Critère de sortie: le targeted suite reste vert, le full `make test` ne contient plus l'erreur inter-tests `/my/psql`; les failures restants sont soit fixés, soit documentés avec cause et owner. [E3]

### PR 5 - Hygiène packaging/public surface

Objectif: rendre la CLI testable et installable sans ambiguïté.

Changements proposés:

- Unifier version package, entrypoint, metadata venv/global.
- Aligner `requires-python` avec les règles projet.
- Ajouter ou corriger les targets publiques réellement utilisées.
- Lancer le scan de neutralité publique si README/CLI/docs sont touchés.

Critère de sortie: une seule version source de vérité et une surface publique cohérente. [E3]

## 7. Risques techniques

Le plus gros risque immédiat est de brancher la première boucle sur des services qui sont souvent down localement. Le métier cible doit observer ces pannes, pas dépendre d'elles pour démarrer. [E2]

Le second risque est l'ambiguïté entre daemon, autopilot et CLI. `daemon.py` a le `--once`, autopilot a le dry-run, mais `etzchaim improve --once` n'existe pas. Une intégration naïve peut dupliquer les boucles ou masquer le vrai point d'entrée. [E2]

L'autopilot contient des chemins git/PR où le push peut être vrai par défaut. Toute intégration au premier métier doit imposer un mode no-push/no-PR par défaut jusqu'à validation explicite. [E1][E3]

La version packaging incohérente peut faire tester un code différent de celui exécuté par l'utilisateur. La phase suivante doit toujours privilégier `.venv/bin/etzchaim` ou `python -m` depuis le repo tant que l'installation globale n'est pas réconciliée. [E1][E2]

Le full test mélange des tests unitaires, intégration DB et artefacts `build/lib`. Le résultat actuel n'est pas un signal simple; il faut séparer le gate P0 rapide du gate complet. [E2]

Guardian/SelfModel peut avoir des mismatches d'API non couverts par les tests actuels: `selfmodel/guardian.py` appelle une API de SelfMap qui ne semble pas correspondre exactement au `selfmap/core.py` réel. [E2]

La neutralité de surface publique est un risque si les nouveaux noms CLI/docs exposent des termes internes. Les nouvelles commandes publiques doivent rester neutres. [E3]

Les appels LLM externes doivent rester derrière circuit breaker et résolution de profil, même pour une boucle de métacognition minimale. [E3]

## 8. Critères d'acceptation de la phase 1

La commande `.venv/bin/etzchaim improve --once --dry-run --json` existe et retourne un JSON stable. [E3]

La commande n'applique aucun patch, ne démarre aucun service, ne lance aucune migration destructive, ne fait aucun commit, ne crée aucune PR et ne fait aucun push. [E3]

La boucle collecte au minimum `doctor`, `status` et un résumé de tests ciblés ou fourni, même si Docker/PostgreSQL sont down. [E3]

Chaque faiblesse observée est transformée en action typée parmi `rule`, `test`, `patch`, `alert`, avec preuve locale et commande de vérification. [E3]

Le bug `/my/psql` est reconnu comme événement de test reproductible et converti en proposition de patch/test vérifiable. [E3]

La boucle produit une sortie machine-readable et une synthèse humaine courte. [E3]

Les tests unitaires de la nouvelle boucle passent dans la venv sans service externe. [E3]

Le targeted suite CLI/daemon/autopilot/facultés reste vert. [E3]

`make doctor` existe ou la documentation ne le promet plus. [E3]

Les versions CLI/package ne sont plus contradictoires pour l'environnement de développement validé. [E3]

Si `README.md`, `docs/`, surfaces CLI ou specs publiques sont touchés, le scan de neutralité publique est exécuté avant validation. [E3]

## 9. Liste exacte des fichiers proposés pour la phase suivante

Liste proposée à valider avant exécution; ne pas modifier hors de cette liste sans validation supplémentaire.

Surface CLI/docs/build:

- `README.md`
- `Makefile`
- `pyproject.toml`
- `etzchaim/__init__.py`
- `etzchaim/cli/app.py`
- `etzchaim/cli/commands/improve.py`
- `etzchaim/cli/commands/doctor.py`
- `etzchaim/cli/doctor/checks.py`

Nouvelle boucle métier:

- `etzchaim/metacognition/__init__.py`
- `etzchaim/metacognition/events.py`
- `etzchaim/metacognition/collectors.py`
- `etzchaim/metacognition/actions.py`
- `etzchaim/metacognition/report.py`
- `etzchaim/metacognition/faculty_bridge.py`

Pont daemon/autopilot:

- `daemon.py`
- `daemon_tasks/auto_dev.py`
- `etzchaim/autopilot/loop.py`
- `etzchaim/autopilot/git_integration/pr.py`

Tests à créer ou modifier:

- `tests/test_install/test_cli_improve.py`
- `tests/test_metacognition_events.py`
- `tests/test_metacognition_collectors.py`
- `tests/test_metacognition_first_loop.py`
- `tests/test_install/test_psql_helper.py`
- `tests/_psql.py`
- `tests/test_olamot_temperature_warning.py`
- `tests/test_sprint8_d1_hitlabshut.py`
- `partzufim/tests/test_zivvug_refactor_l.py`

Fichiers générés/metadata à ne pas éditer manuellement sans décision explicite:

- `etzchaim.egg-info/*`
- `.venv/lib/python*/site-packages/etzchaim-*.dist-info/*`
- `build/lib/*`

## 10. Confirmation explicite

Aucun fichier de code du repo attendu n'a été modifié pendant ce préflight.

Aucun fichier n'a été supprimé.

Aucun `git push` n'a été lancé.

Aucune migration destructive n'a été lancée.

Aucun service système permanent n'a été démarré.

Aucun LaunchAgent n'a été installé.

La seule écriture volontaire dans le repo attendu pour cette phase est ce rapport markdown:

`strategy/codex-prompt/codex-plan/etzchaim-p0-preflight.md`

Note de traçabilité: une première écriture du même rapport markdown a été faite dans le répertoire initial du thread (`/Users/fffff/Documents/mon-cerveau/projets/etz-chaim-ai`) avant correction vers le chemin Desktop demandé. Je ne l'ai pas supprimée, conformément à la contrainte "ne rien supprimer".

Le dry-run autopilot a pu écrire dans l'état utilisateur hors repo (`~/.etz-chaim/autopilot/cycle_log.db`), conformément à la commande de diagnostic explicitement autorisée.

PRÊT POUR VALIDATION HERMÈS / YOHAN AVANT EXÉCUTION.
