"""Sprint 8 D1 — Tests TDD pour le fix Hitlabshut (EC-K5-008).

Doctrine : Sha'ar HaKlalim 5:2 (Etz Chaim, Rabbi Hayyim Vital).
"Z'A ne peut PAS recevoir les Mohin directement car leur Ohr est TROP GRAND
— il faut l'HABILLAGE dans NHY d'Imma."

Par analogie structurelle (E3), le boost Zivvug sur Abba/Imma doit passer
par les facultés (Kelim), pas directement sur overall_score.

Avant ce fix :
- daemon.py:_apply_zivvug_to_partzufim écrivait +0.02 DIRECT sur overall_score
- partzuf.save_state() écrasait overall_score avec la valeur calculée depuis facultés
- Dual-write race → boost daemon perdu à chaque cmd_ask/ohr_yashar

Après ce fix :
- _apply_zivvug_to_partzufim SUPPRIMÉ (viole EC-K5-008)
- BOOST_AMOUNT recalibré 0.02 → 0.055 pour ΔOverall ≈ 0.02 via 3 facultés
- Les 4 callers prod de update_all_partzufim(persist=True) injectent zivvug_engine
- Flux : daemon accumule dans zivvug_state → cmd_ask consume via facultés → reset
"""

from __future__ import annotations

import pathlib

import pytest


# ═══════════════════════════════════════════════════════════════════
#    Test 1 — BOOST_AMOUNT doctrinal calibration
# ═══════════════════════════════════════════════════════════════════

def test_boost_amount_doctrinal_calibration():
    """BOOST_AMOUNT=0.055 cohérent avec ΔOverall≈0.02 via 3 facultés (EC-K5-008).

    Calcul :
      ΔOverall = BOOST_AMOUNT × (w_chokhmah + w_tiferet + w_malkuth) / total_weight
               = 0.055 × (1 + 2 + 1) / 11
               = 0.055 × 4 / 11
               ≈ 0.02
    """
    from partzufim.base import FACULTY_NAMES
    from partzufim.zivvug import ZivvugEngine

    assert ZivvugEngine.BOOST_AMOUNT == pytest.approx(0.055, abs=0.001), (
        f"BOOST_AMOUNT={ZivvugEngine.BOOST_AMOUNT} ≠ 0.055 "
        "— recalibrage requis pour préserver ΔOverall≈0.02 via Hitlabshut"
    )

    weights = {n: 1.0 for n in FACULTY_NAMES}
    weights["tiferet"] = 2.0
    total = sum(weights.values())
    boosted_weight = weights["chokhmah"] + weights["tiferet"] + weights["malkuth"]
    delta_overall = ZivvugEngine.BOOST_AMOUNT * boosted_weight / total

    assert delta_overall == pytest.approx(0.02, abs=0.002), (
        f"ΔOverall={delta_overall:.4f} ≠ 0.02 — calibrage BOOST_AMOUNT incohérent"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 2 — Boost propagates via faculties (Hitlabshut)
# ═══════════════════════════════════════════════════════════════════

def test_boost_propagates_via_faculties_not_direct_overall():
    """EC-K5-008 : le boost doit affecter les facultés spécifiques, pas overall direct.

    Analogie structurelle avec NHY d'Imma :
    - boost abba → (chokhmah, tiferet, malkuth) d'Abba [Kelim]
    - boost imma → (binah, tiferet, malkuth) d'Imma [Kelim]
    - overall = résultante calculée depuis facultés [pas une entrée]

    Pattern : 1er update_all stabilise les facultés (Phase 1), 2e applique le boost.
    """
    from partzufim import init_partzufim, update_all_partzufim
    from partzufim.zivvug import ZivvugEngine

    ps = init_partzufim()
    abba = ps["abba"]

    # Stabiliser les facultés via Phase 1 (sans boost)
    update_all_partzufim(ps, {}, zivvug_engine=ZivvugEngine())

    chokhmah_before = abba.get_faculty("chokhmah")
    tiferet_before = abba.get_faculty("tiferet")
    malkuth_before = abba.get_faculty("malkuth")
    binah_before = abba.get_faculty("binah")  # ne doit PAS être boostée

    # Appliquer boost via un nouveau cycle
    boosted = ZivvugEngine()
    boosted.mutual_reinforcement(causal_validated=True)  # abba_boost = 0.055

    update_all_partzufim(ps, {}, zivvug_engine=boosted)

    # Facultés boostées (Hitlabshut via chokhmah, tiferet, malkuth)
    assert abba.get_faculty("chokhmah") > chokhmah_before, (
        f"chokhmah non boostée : avant={chokhmah_before:.4f}, "
        f"après={abba.get_faculty('chokhmah'):.4f}"
    )
    assert abba.get_faculty("tiferet") > tiferet_before, "tiferet non boostée"
    assert abba.get_faculty("malkuth") > malkuth_before, "malkuth non boostée"

    # Facultés NON boostées (binah) : changent si Phase 1 les recalcule depuis
    # modules vides, mais NE devraient PAS recevoir directement le boost.
    # Vérifier que la différence avec before n'inclut PAS le boost 0.055.
    binah_after = abba.get_faculty("binah")
    assert abs(binah_after - binah_before) < 0.01, (
        f"binah changée plus que tolérable : {binah_before:.4f} → {binah_after:.4f} "
        f"(le boost doit se limiter à chokhmah/tiferet/malkuth)"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 3 — Delta Overall matches doctrinal calibration
# ═══════════════════════════════════════════════════════════════════

def test_delta_overall_matches_doctrinal_calibration():
    """ΔOverall ≈ 0.02 après 1 cycle mutual_reinforcement (recalibrage C2).

    Pattern : 1er update_all stabilise, 2e applique le boost, mesurer le delta.
    """
    from partzufim import init_partzufim, update_all_partzufim
    from partzufim.zivvug import ZivvugEngine

    ps = init_partzufim()
    abba = ps["abba"]

    # Stabiliser
    update_all_partzufim(ps, {}, zivvug_engine=ZivvugEngine())
    overall_before = abba.overall

    # Appliquer boost
    engine = ZivvugEngine()
    engine.mutual_reinforcement(causal_validated=True)
    update_all_partzufim(ps, {}, zivvug_engine=engine)

    overall_after = abba.overall
    delta = overall_after - overall_before

    assert delta == pytest.approx(0.02, abs=0.003), (
        f"ΔOverall={delta:.4f} ≠ 0.02 — recalibrage BOOST_AMOUNT incorrect"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 4 — _apply_zivvug_to_partzufim removed from daemon
# ═══════════════════════════════════════════════════════════════════

def test_apply_zivvug_to_partzufim_removed_from_daemon():
    """EC-K5-008 : daemon ne doit plus écrire directement sur overall_score.

    _apply_zivvug_to_partzufim violait Hitlabshut en faisant
    UPDATE partzufim_state SET overall_score = overall_score + boost,
    bypassant les facultés (Kelim). Suppression obligatoire.
    """
    import daemon as _daemon_module

    assert not hasattr(_daemon_module, "_apply_zivvug_to_partzufim"), (
        "_apply_zivvug_to_partzufim viole EC-K5-008 (Hitlabshut). "
        "Le daemon ne doit plus écrire directement sur partzufim_state.overall_score. "
        "Les boosts doivent être persistés dans zivvug_state puis consommés "
        "par update_all_partzufim Phase 2 (application aux facultés)."
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 5 — No regression orientation Sprint 7
# ═══════════════════════════════════════════════════════════════════

def test_no_regression_orientation_persistence_sprint7():
    """Le boost ne déclenche pas de transition panim→akhor distincte.

    Sprint 7 fix (check_transitions persistance symétrique) doit rester
    indépendant du mécanisme de boost Zivvug. Deux runs update_all_partzufim
    avec mêmes modules — un avec boost, un sans — doivent donner la même
    orientation finale (le boost n'influence pas _update_orientation).
    """
    from partzufim import init_partzufim, update_all_partzufim
    from partzufim.zivvug import ZivvugEngine

    # Run 1 : sans boost
    ps_empty = init_partzufim()
    update_all_partzufim(ps_empty, {}, zivvug_engine=ZivvugEngine())
    orientation_without_boost = ps_empty["abba"]._orientation

    # Run 2 : avec boost
    ps_boost = init_partzufim()
    boosted = ZivvugEngine()
    boosted.mutual_reinforcement(causal_validated=True)
    update_all_partzufim(ps_boost, {}, zivvug_engine=boosted)
    orientation_with_boost = ps_boost["abba"]._orientation

    assert orientation_with_boost == orientation_without_boost, (
        f"Le boost a changé l'orientation : sans={orientation_without_boost}, "
        f"avec={orientation_with_boost} — le boost ne doit PAS impacter orientation"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 6 — Multiple mutual_reinforcements accumulate correctly
# ═══════════════════════════════════════════════════════════════════

def test_multiple_mutual_reinforcements_accumulate_correctly():
    """3 calls mutual_reinforcement → boost = 3 × 0.055 → ΔOverall ≈ 3 × 0.02.

    Scénario : le daemon tourne 3 cycles avant qu'un cmd_ask ne consume.
    Les boosts s'accumulent dans zivvug_engine sans overflow.
    """
    from partzufim import init_partzufim, update_all_partzufim
    from partzufim.zivvug import ZivvugEngine

    ps = init_partzufim()
    abba = ps["abba"]

    # Stabiliser Phase 1
    update_all_partzufim(ps, {}, zivvug_engine=ZivvugEngine())
    overall_before = abba.overall

    engine = ZivvugEngine()
    for _ in range(3):
        engine.mutual_reinforcement(causal_validated=True)

    assert engine.abba_boost == pytest.approx(0.165, abs=0.001), (
        f"3 × BOOST_AMOUNT(0.055) = 0.165, observé {engine.abba_boost}"
    )

    update_all_partzufim(ps, {}, zivvug_engine=engine)

    delta = abba.overall - overall_before
    assert delta == pytest.approx(0.06, abs=0.015), (
        f"ΔOverall={delta:.4f} ≠ 0.06 (3 cycles × 0.02)"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 7 — Doctrinal reference EC-K5-008 present in code
# ═══════════════════════════════════════════════════════════════════

def test_hitlabshut_doctrinal_reference_present():
    """EC-K5-008 explicitement référencé dans zivvug.py et partzufim/__init__.py.

    Principe Etz Chaim AI : tout fix doctrinal doit citer l'assertion EC-*
    qui le justifie, traçabilité doctrine → code.
    """
    root = pathlib.Path(__file__).resolve().parent.parent
    zivvug_src = (root / "partzufim" / "zivvug.py").read_text(encoding="utf-8")
    init_src = (root / "partzufim" / "__init__.py").read_text(encoding="utf-8")

    assert "EC-K5-008" in zivvug_src, (
        "partzufim/zivvug.py doit référencer EC-K5-008 (BOOST_AMOUNT calibration)"
    )
    assert "EC-K5-008" in init_src, (
        "partzufim/__init__.py doit référencer EC-K5-008 (Phase 2 Hitlabshut)"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 8 — Reset after application (update_all_partzufim)
# ═══════════════════════════════════════════════════════════════════

def test_boosts_reset_after_update_all_partzufim():
    """Après consommation via update_all_partzufim, les boosts sont reset à 0.

    Sémantique reset_boosts : "après application aux Partzufim" (docstring).
    Le cycle se termine par reset — prêt pour le prochain cycle.
    """
    from partzufim import init_partzufim, update_all_partzufim
    from partzufim.zivvug import ZivvugEngine

    ps = init_partzufim()
    engine = ZivvugEngine()
    engine.mutual_reinforcement(insight_produced=True)
    engine.mutual_reinforcement(causal_validated=True)

    assert engine.abba_boost > 0
    assert engine.imma_boost > 0

    update_all_partzufim(ps, {}, zivvug_engine=engine)

    assert engine.abba_boost == pytest.approx(0.0), (
        "abba_boost non reset après application — viole la sémantique reset_boosts"
    )
    assert engine.imma_boost == pytest.approx(0.0), (
        "imma_boost non reset après application"
    )
