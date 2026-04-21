"""tests/test_sprint_runtime_cleanup.py — Sprint runtime-cleanup (2026-04-20).

Deux quick-wins observés dans les logs runtime post-kickstart Sprint 6.x :

- Bug A — daemon.task_concept_harvest levait NameError sur `state`.
  La fonction locale daemon.py:972-998 shadow l'import daemon.py:340
  (daemon_tasks.task_concept_harvest) qui, elle, définit correctement
  `state = load_state()`. Le fix ajoute la même ligne à la version locale.

- Bug B — daemon.run_cycle._daemon_emit faisait
  `_emit("daemon_task", task=task_name, **data)` avec `data` possiblement
  porteur d'une clé `task` → TypeError "got multiple values for keyword
  argument 'task'". Le fix dédupe la clé réservée via
  daemon._filter_reserved_kwargs.

Les tests doivent échouer avant application du fix, passer après.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


# ─── Bug A — ConceptHarvester state NameError ───────────────────

def test_task_concept_harvest_defines_state_in_scope():
    """T1 : daemon.task_concept_harvest doit avoir `state` défini dans
    sa portée locale avant `state.get(...)`.

    Reproduction du runtime log `[ERROR] ConceptHarvester error:
    name 'state' is not defined`. Sans fix, la fonction retourne un
    report avec error="name 'state' is not defined".
    """
    from daemon import task_concept_harvest

    # ConceptHarvester mocké pour isoler le scope du wrapper daemon
    # (sinon le test dépendrait de la DB locale).
    fake_ch_cls = MagicMock()
    fake_instance = MagicMock()
    fake_instance.harvest.return_value = {
        "harvested": 0,
        "deduped": 0,
        "rejected": 0,
        "errors": 0,
        "pruned": 0,
        "sources": {},
    }
    fake_ch_cls.return_value = fake_instance

    with patch("kabbalah.concept_harvester.ConceptHarvester", fake_ch_cls):
        report = task_concept_harvest({})

    # Le report contient toujours `task` (défini avant le try/except)
    assert report.get("task") == "concept_harvest"

    # Et surtout, PAS d'erreur "name 'state' is not defined"
    error = report.get("error", "") or ""
    assert "'state' is not defined" not in error, (
        f"Bug A non fixé : state toujours absent du scope. report={report}"
    )


# ─── Bug B — SSE emit task kwarg conflict ───────────────────────

def test_filter_reserved_kwargs_strips_conflicting_keys():
    """T2 : le helper daemon._filter_reserved_kwargs doit retirer les
    clés réservées d'un dict de données avant qu'elles ne soient
    expansées par `**data` à un call site qui a déjà des kwargs
    explicites du même nom.
    """
    from daemon import _filter_reserved_kwargs

    data = {"task": "concept_harvest", "harvested": 5, "status": "running"}
    safe = _filter_reserved_kwargs(data, ("task",))

    assert "task" not in safe
    assert safe["harvested"] == 5
    assert safe["status"] == "running"
    # Le dict d'origine n'est pas muté (contrat pur : retourne une copie)
    assert "task" in data


def test_emit_daemon_task_pattern_no_kwargs_collision():
    """T2 : reproduction du pattern `_daemon_emit` avec la clé
    `task` présente dans data. Après fix (filter), l'appel à
    web.events.emit() ne doit plus lever TypeError "multiple values
    for keyword argument 'task'".
    """
    from daemon import _filter_reserved_kwargs
    from web.events import emit

    # Un payload typique de `_safe_emit_data(results["concept_harvest"])` :
    # le dict retourné par task_concept_harvest contient
    # {"task": "concept_harvest", "harvested": ..., ...}
    payload = {"task": "concept_harvest", "harvested": 3}

    # Simuler le pattern `_daemon_emit("concept_harvest_done", **payload)` :
    # _daemon_emit appelle _emit("daemon_task", task=task_name, **data),
    # où `data` est le payload. Avant fix : TypeError. Après fix : dédup.
    safe_payload = _filter_reserved_kwargs(payload, ("task",))

    # Ne doit PAS lever TypeError
    emit("daemon_task", task="concept_harvest_done", **safe_payload)
