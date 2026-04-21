"""daemon_tasks — Task functions extracted from daemon.py.

Each sub-module groups tasks by Sephirah/function area.
This __init__ re-exports all task_* functions and key helpers
so that daemon.py can do: `from daemon_tasks import task_netzach, ...`
"""
from daemon_tasks.binah import (
    task_binah_causal_graphs,
    task_binah_confounders,
    task_binah_evidence_elevator,
    task_binah_to_yesod,
)
from daemon_tasks.chokmah import (
    _generate_forge_questions,
    _recycle_candidate_rejections_to_fti,
    _recycle_rejections_to_fti,
    task_chesed_analogies,
    task_clustering,
    task_cube_insights,
    task_explore_open_questions,
    task_insightforge,
    task_insightforge_to_selfmodel,
)
from daemon_tasks.daat import (
    _DAAT_DECLINE_THRESHOLD,
    _DAAT_HIGH_VARIANCE_THRESHOLD,
    _DAAT_MIN_QUESTIONS,
    _DAAT_STRONG_THRESHOLD,
    _DAAT_WEAK_THRESHOLD,
    _query_hitbonenut_domain_stats,
    task_daat_correct_biases,
    task_daat_predict,
    task_daat_verify,
    task_selfmodel_maintenance,
    task_snapshot,
)
from daemon_tasks.exploration import (
    EtzDomainJudge,
    task_auto_improve,
    task_concept_harvest,
    task_dira_birur_stats,
    task_explore_full_tree,
    task_gevurah_eval,
    task_hitbonenut,
    task_masakh_health,
    task_sofer_watcher,
    task_tzeruf_spatial,
)
from daemon_tasks.netzach import task_netzach
from daemon_tasks.orphan_validation import (
    INTERVAL_VALIDATE_ORPHAN,
    ORPHAN_BATCH_LIMIT,
    task_validate_orphan_candidates,
)
from daemon_tasks.omer import (
    task_beinoni_check,
    task_beinoni_to_selfmap,
    task_omer_calibrate,
)
from daemon_tasks.tiferet import task_contradictions, task_tiferet_synthesize
from daemon_tasks.tzimtzum import (
    _collect_pressure_metrics,
    _ensure_tzimtzum_table,
    _find_busiest_domain,
    _find_weakest_domain,
    _load_tzimtzum_state_from_db,
    _save_tzimtzum_state_to_db,
    task_autojudge_to_partzuf,
    task_partzuf_regulation,
    task_tzimtzum_detect,
)
from daemon_tasks.yesod import (
    task_gc,
    task_log_retention,
    task_memory_stats,
    task_sifrei_to_yesod,
    task_yesod_mature,
)

__all__ = [
    # daat
    "task_daat_predict",
    "task_daat_verify",
    "task_daat_correct_biases",
    "task_selfmodel_maintenance",
    "task_snapshot",
    "_query_hitbonenut_domain_stats",
    "_DAAT_WEAK_THRESHOLD",
    "_DAAT_STRONG_THRESHOLD",
    "_DAAT_HIGH_VARIANCE_THRESHOLD",
    "_DAAT_DECLINE_THRESHOLD",
    "_DAAT_MIN_QUESTIONS",
    # binah
    "task_binah_confounders",
    "task_binah_causal_graphs",
    "task_binah_evidence_elevator",
    "task_binah_to_yesod",
    # chokmah
    "task_insightforge",
    "task_insightforge_to_selfmodel",
    "_generate_forge_questions",
    "_recycle_rejections_to_fti",
    "_recycle_candidate_rejections_to_fti",
    "task_chesed_analogies",
    "task_explore_open_questions",
    "task_cube_insights",
    "task_clustering",
    # tiferet
    "task_contradictions",
    "task_tiferet_synthesize",
    # yesod
    "task_memory_stats",
    "task_yesod_mature",
    "task_log_retention",
    "task_gc",
    "task_sifrei_to_yesod",
    # netzach
    "task_netzach",
    # orphan validation (Sprint 5.6)
    "task_validate_orphan_candidates",
    "INTERVAL_VALIDATE_ORPHAN",
    "ORPHAN_BATCH_LIMIT",
    # omer
    "task_omer_calibrate",
    "task_beinoni_check",
    "task_beinoni_to_selfmap",
    # tzimtzum
    "task_tzimtzum_detect",
    "_ensure_tzimtzum_table",
    "_load_tzimtzum_state_from_db",
    "_find_busiest_domain",
    "_save_tzimtzum_state_to_db",
    "_collect_pressure_metrics",
    "_find_weakest_domain",
    "task_partzuf_regulation",
    "task_autojudge_to_partzuf",
    # exploration
    "EtzDomainJudge",
    "task_auto_improve",
    "task_explore_full_tree",
    "task_hitbonenut",
    "task_gevurah_eval",
    "task_dira_birur_stats",
    "task_tzeruf_spatial",
    "task_masakh_health",
    "task_sofer_watcher",
    "task_concept_harvest",
]
