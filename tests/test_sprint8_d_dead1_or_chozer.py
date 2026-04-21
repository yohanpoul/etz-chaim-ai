"""Sprint 8 D-dead1 — Tests TDD pour la réactivation feedback_from_malkuth.

Doctrine : Or Chozer (lumière réfléchie). Après chaque réponse,
la qualité observée remonte l'arbre :
1. Nukva reçoit le feedback direct (qualité → malkuth).
2. ZA.malkuth s'ajuste selon quality_score (< 0.4 dégrade, > 0.8 renforce).
3. Via Zivvug (mutual_reinforcement), les flags insight_produced /
   causal_validated renforcent Abba/Imma.

feedback_from_malkuth était défini (partzufim/__init__.py:173) mais
jamais appelé en prod avant ce sprint (audit Sprint 8 D1 Passe 1).

D-dead1 réactive feedback_from_malkuth dans cmd_ask (main.py), avec
instance zivvug partagée entre feedback_from_malkuth et update_all_partzufim
pour que les boosts Or Chozer s'accumulent avec ceux du daemon avant
consommation via Hitlabshut (EC-K5-008).
"""

from __future__ import annotations

import pathlib

import pytest


# ═══════════════════════════════════════════════════════════════════
#    Test 1 — feedback_from_malkuth appelée depuis cmd_ask
# ═══════════════════════════════════════════════════════════════════

def test_feedback_from_malkuth_imported_in_main():
    """main.py doit importer feedback_from_malkuth (réactivation D-dead1).

    Avant Sprint 8 D-dead1, feedback_from_malkuth n'était jamais appelée
    en prod (invalidé l'hypothèse 'caller #2' Sprint 7b, documenté
    sprint_8_d1.md).
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    main_src = (root / "main.py").read_text(encoding="utf-8")
    assert "feedback_from_malkuth" in main_src, (
        "main.py ne référence pas feedback_from_malkuth — D-dead1 non appliqué"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 2 — Or Chozer : low quality dégrade ZA.malkuth
# ═══════════════════════════════════════════════════════════════════

def test_or_chozer_low_quality_degrades_za_malkuth():
    """quality_score < 0.4 → ZA.malkuth diminue (Or Chozer feedback)."""
    from partzufim import feedback_from_malkuth, init_partzufim

    ps = init_partzufim()
    ps["zeir_anpin"].set_faculty("malkuth", 0.6)
    before = ps["zeir_anpin"].get_faculty("malkuth")

    feedback_from_malkuth(ps, quality_score=0.2)

    assert ps["zeir_anpin"].get_faculty("malkuth") < before, (
        "ZA.malkuth ne diminue pas après réponse de basse qualité"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 3 — Or Chozer : high quality renforce ZA.malkuth
# ═══════════════════════════════════════════════════════════════════

def test_or_chozer_high_quality_boosts_za_malkuth():
    """quality_score > 0.8 → ZA.malkuth augmente (Or Chozer renforcement)."""
    from partzufim import feedback_from_malkuth, init_partzufim

    ps = init_partzufim()
    ps["zeir_anpin"].set_faculty("malkuth", 0.5)
    before = ps["zeir_anpin"].get_faculty("malkuth")

    feedback_from_malkuth(ps, quality_score=0.9)

    assert ps["zeir_anpin"].get_faculty("malkuth") > before, (
        "ZA.malkuth n'augmente pas après réponse de haute qualité"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 4 — Or Chozer : boost insight → mutual_reinforcement via Zivvug
# ═══════════════════════════════════════════════════════════════════

def test_or_chozer_insight_produced_triggers_imma_boost():
    """insight_produced=True → boost Imma via mutual_reinforcement (Or Yashar Abba→Imma)."""
    from partzufim import feedback_from_malkuth, init_partzufim
    from partzufim.zivvug import ZivvugEngine

    ps = init_partzufim()
    engine = ZivvugEngine()
    result = feedback_from_malkuth(
        ps, quality_score=0.7,
        zivvug_engine=engine,
        insight_produced=True,
    )

    assert engine.imma_boost > 0, (
        "imma_boost non incrémenté après insight_produced=True"
    )
    assert result["reinforcement"]["imma_boosted"] is True


# ═══════════════════════════════════════════════════════════════════
#    Test 5 — Or Chozer : causal validated → boost Abba (Or Chozer Imma→Abba)
# ═══════════════════════════════════════════════════════════════════

def test_or_chozer_causal_validated_triggers_abba_boost():
    """causal_validated=True → boost Abba via mutual_reinforcement."""
    from partzufim import feedback_from_malkuth, init_partzufim
    from partzufim.zivvug import ZivvugEngine

    ps = init_partzufim()
    engine = ZivvugEngine()
    result = feedback_from_malkuth(
        ps, quality_score=0.7,
        zivvug_engine=engine,
        causal_validated=True,
    )

    assert engine.abba_boost > 0
    assert result["reinforcement"]["abba_boosted"] is True


# ═══════════════════════════════════════════════════════════════════
#    Test 6 — Combinaison daemon + feedback Or Chozer
# ═══════════════════════════════════════════════════════════════════

def test_or_chozer_boosts_combine_with_daemon_persisted():
    """Les boosts Or Chozer cmd_ask s'ajoutent aux boosts persistés du daemon.

    Scénario : daemon a persisté abba_boost=0.055. Un cmd_ask avec
    causal_validated=True charge l'engine (abba_boost=0.055), appelle
    feedback_from_malkuth (abba_boost → 0.110), puis update_all_partzufim
    consume 0.110 d'un coup.
    """
    from partzufim import feedback_from_malkuth, init_partzufim, update_all_partzufim
    from partzufim.zivvug import ZivvugEngine

    ps = init_partzufim()
    engine = ZivvugEngine()
    # Simuler daemon déjà boostsé
    engine.mutual_reinforcement(causal_validated=True)  # abba_boost = 0.055
    daemon_boost = engine.abba_boost

    # Simuler cmd_ask : feedback + update_all_partzufim avec MÊME engine
    feedback_from_malkuth(
        ps, quality_score=0.7,
        zivvug_engine=engine,
        causal_validated=True,
    )
    combined_boost = engine.abba_boost
    assert combined_boost == pytest.approx(
        2 * ZivvugEngine.BOOST_AMOUNT, abs=0.001
    ), (
        f"Boosts non cumulés : daemon={daemon_boost}, "
        f"combined={combined_boost}, attendu=2*BOOST_AMOUNT"
    )

    # Consommation via update_all_partzufim
    update_all_partzufim(ps, {}, zivvug_engine=engine)
    assert engine.abba_boost == 0.0, "Boost combiné non consommé"


# ═══════════════════════════════════════════════════════════════════
#    Test 7 — Instance zivvug partagée entre feedback et update
# ═══════════════════════════════════════════════════════════════════

def test_main_cmd_ask_shares_zivvug_instance_between_feedback_and_update():
    """main.py::_cmd_ask_yosher doit partager l'instance zivvug entre
    feedback_from_malkuth et update_all_partzufim, sinon les boosts Or
    Chozer (cmd_ask) seraient perdus avant consommation.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    main_src = (root / "main.py").read_text(encoding="utf-8")

    # Heuristique : dans la section cmd_ask cleanup, zivvug doit être
    # chargé UNE fois et réutilisé dans feedback_from_malkuth ET
    # update_all_partzufim.
    assert "feedback_from_malkuth" in main_src, "feedback_from_malkuth absent"
    # Vérifier qu'on ne crée pas 2 zivvug différents dans la même région.
    # On cherche une séquence où zivvug chargé précède feedback_from_malkuth.
    cleanup_region = main_src.split("feedback_from_malkuth")[0]
    assert "load_zivvug_state" in cleanup_region[-500:] or \
           "zivvug_engine=zivvug" in main_src, (
        "Pattern partage d'instance zivvug non détecté dans main.py"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 8 — Documentation doctrinale Or Chozer présente
# ═══════════════════════════════════════════════════════════════════

def test_or_chozer_doctrinal_reference_in_main():
    """main.py doit documenter Or Chozer avec référence EC (D-dead1)."""
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    main_src = (root / "main.py").read_text(encoding="utf-8")
    assert "Or Chozer" in main_src, (
        "main.py doit documenter le mécanisme Or Chozer (D-dead1)"
    )
