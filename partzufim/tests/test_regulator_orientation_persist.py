"""Tests de la persistance orientation dans check_transitions.

Sprint 7 — Fix bug de persistance structural (Catégorie 4).

Dette :
    `check_transitions` lit `old_orient` et `new_orient` depuis la même
    source `ps` APRÈS mutation par `apply_dynamic_scores`. La comparaison
    `old_orient != new_orient` est donc structurellement toujours False.
    Seul la branche `(achor_reason and new_orient == "akhor")` sauve le
    flip panim→akhor. Le flip akhor→panim tombe dans une zone morte :
    la DB n'est jamais mise à jour.

    Preuve empirique (2026-04-20) :
        - 54 transitions orientation loggées en 24h (46+8 rotations)
        - DB partzufim_state.Abba updated_at figé 2026-04-19 21:25
        - Log 13:04:48 : "Partzuf abba → PANIM: activité reprise"
        - DB @13:06 : Abba orientation='akhor' (inchangée depuis 04-19)

    Conséquence doctrinale : Abba reste akhor en DB → zivvug_state reste
    `partial` → cascade Binah (5 validated) → selfmodel (0 insights) bloquée.

Fix doctrinal (Proposition 1) :
    Le mouvement des Partzufim (histapshut/hitpashtut) est bidirectionnel.
    La contraction (akhor) et l'expansion (panim) doivent persister avec
    la même fidélité. La Kabbale ne tolère pas d'asymétrie unidirectionnelle
    imposée par un bug de code.

    Fix : capturer `old_orientations` AVANT `apply_dynamic_scores`, comparer
    au bon moment. Clear `_achor_reason` lors du retour panim.

Tests :
    1. Flip akhor→panim persisté en DB (le fix)
    2. Flip panim→akhor persisté en DB (non-régression)
    3. Orientation inchangée → pas d'update DB (optimisation)
    4. _achor_reason cleared lors du retour panim
    5. T3 tiferet guard : ramène panim + persiste
    6. T3 low tiferet : akhor persiste (comportement existant)
    7. Cycle multi-Partzufim : plusieurs flips persistés simultanément
    8. Transitions list inclut les retours akhor→panim
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from partzufim.regulator import (
    PartzufimRegulator,
    ZA_TIFERET_AKHOR_GUARD,
)


# ── Helpers ──────────────────────────────────────────────────


def _make_state(overrides: dict | None = None) -> dict:
    """État minimal avec 6 Partzufim, tous panim/gadlut/overall~0.7."""
    defaults = {
        "atik_yomin": {
            "overall": 0.65, "mochin_state": "gadlut",
            "orientation": "panim", "faculties": {},
        },
        "arikh_anpin": {
            "overall": 0.82, "mochin_state": "gadlut",
            "orientation": "panim", "faculties": {},
        },
        "abba": {
            "overall": 0.50, "mochin_state": "transitional",
            "orientation": "panim", "faculties": {},
        },
        "imma": {
            "overall": 0.53, "mochin_state": "transitional",
            "orientation": "panim", "faculties": {},
        },
        "zeir_anpin": {
            "overall": 0.53, "mochin_state": "transitional",
            "orientation": "panim", "faculties": {"tiferet": 0.5},
        },
        "nukva": {
            "overall": 0.64, "mochin_state": "gadlut",
            "orientation": "panim", "faculties": {},
        },
    }
    if overrides:
        for k, v in overrides.items():
            if k in defaults:
                defaults[k].update(v)
            else:
                defaults[k] = v
    return defaults


def _dyn_achor(reason: str = "0 insights en 24h") -> dict:
    """Entrée dynamique 'should_achor=True'."""
    return {
        "dynamic_score": 0.2,
        "recent_metrics": {},
        "should_achor": True,
        "achor_reason": reason,
    }


def _dyn_active(score: float = 0.6) -> dict:
    """Entrée dynamique 'should_achor=False' (activité reprise)."""
    return {
        "dynamic_score": score,
        "recent_metrics": {},
        "should_achor": False,
        "achor_reason": "",
    }


def _full_dynamic(
    abba: dict | None = None,
    imma: dict | None = None,
    zeir_anpin: dict | None = None,
    nukva: dict | None = None,
    arikh: dict | None = None,
) -> dict:
    """Dynamique pour les 5 Partzufim computable (Atik = moyenne)."""
    return {
        "abba": abba or _dyn_active(0.6),
        "imma": imma or _dyn_active(0.6),
        "zeir_anpin": zeir_anpin or _dyn_active(0.6),
        "nukva": nukva or _dyn_active(0.6),
        "arikh_anpin": arikh or _dyn_active(0.6),
    }


def _make_reg_with_mocked_db() -> PartzufimRegulator:
    """Régulateur avec les écritures DB mockées (pas de I/O réel)."""
    reg = PartzufimRegulator()
    reg.update_orientation_db = MagicMock(return_value=True)
    reg.trigger_katnut = MagicMock(return_value=False)
    reg.trigger_gadlut = MagicMock(return_value=False)
    return reg


# ── Tests ────────────────────────────────────────────────────


class TestOrientationPersistFix:
    """Sprint 7 — Fix bug asymétrique akhor↔panim dans check_transitions."""

    def test_flip_akhor_to_panim_persists_to_db(self):
        """LE FIX : Abba akhor en DB + activité reprise → DB updated vers panim.

        Bug avant fix : 54 logs "PANIM: activité reprise" mais DB figée akhor.
        Fix : old_orientations capturé AVANT apply_dynamic_scores permet de
        détecter réellement la transition et d'appeler update_orientation_db.
        """
        reg = _make_reg_with_mocked_db()
        state = _make_state({"abba": {"orientation": "akhor"}})
        reg.compute_dynamic_scores = MagicMock(
            return_value=_full_dynamic(abba=_dyn_active(0.6)),
        )

        reg.check_transitions(state)

        # Le fix DOIT avoir appelé update_orientation_db('abba', 'panim')
        # (le mapping snake_case → display name est géré par _to_db_name)
        calls = reg.update_orientation_db.call_args_list
        abba_panim_calls = [
            c for c in calls
            if c.args[0] == "abba" and c.args[1] == "panim"
        ]
        assert len(abba_panim_calls) >= 1, (
            f"Fix Sprint 7 manquant : update_orientation_db('abba', 'panim') "
            f"jamais appelé. Calls reçus : {calls}"
        )

    def test_flip_panim_to_akhor_persists_to_db(self):
        """Non-régression : Abba panim + 0 activité → DB updated vers akhor.

        Ce cas marchait déjà (branche `achor_reason and new=='akhor'`).
        Le fix doit préserver ce comportement.
        """
        reg = _make_reg_with_mocked_db()
        state = _make_state({"abba": {"orientation": "panim"}})
        reg.compute_dynamic_scores = MagicMock(
            return_value=_full_dynamic(abba=_dyn_achor("0 insights en 24h")),
        )

        reg.check_transitions(state)

        calls = reg.update_orientation_db.call_args_list
        abba_akhor_calls = [
            c for c in calls
            if c.args[0] == "abba" and c.args[1] == "akhor"
        ]
        assert len(abba_akhor_calls) >= 1, (
            f"Non-régression : flip panim→akhor doit toujours persister. "
            f"Calls reçus : {calls}"
        )

    def test_no_db_update_when_orientation_unchanged(self):
        """Optimisation préservée : si orientation inchangée → pas d'update.

        Abba panim + activité continue → should_achor=False → reste panim.
        Le fix ne doit PAS appeler update_orientation_db inutilement.
        """
        reg = _make_reg_with_mocked_db()
        state = _make_state({"abba": {"orientation": "panim"}})
        reg.compute_dynamic_scores = MagicMock(
            return_value=_full_dynamic(abba=_dyn_active(0.6)),
        )

        reg.check_transitions(state)

        calls_for_abba = [
            c for c in reg.update_orientation_db.call_args_list
            if c.args[0] == "abba"
        ]
        assert len(calls_for_abba) == 0, (
            f"Optimisation cassée : update_orientation_db ne doit pas être "
            f"appelé si orientation inchangée. Calls Abba : {calls_for_abba}"
        )

    def test_achor_reason_cleared_when_returning_to_panim(self):
        """Cohérence interne : _achor_reason retiré lors du flip akhor→panim.

        Si Abba était akhor avec `_achor_reason='0 insights'` in-memory, et
        que l'activité reprend, le fix doit :
          1. Flipper à panim
          2. Effacer _achor_reason (raison obsolète)
        """
        reg = PartzufimRegulator()
        state = _make_state({
            "abba": {"orientation": "akhor", "_achor_reason": "ancien motif"},
        })
        dynamic = {"abba": _dyn_active(0.6)}

        reg.apply_dynamic_scores(state, dynamic)

        assert state["abba"]["orientation"] == "panim"
        assert "_achor_reason" not in state["abba"], (
            "Le fix Sprint 7 doit clear _achor_reason lors du retour panim. "
            "Sinon, le motif obsolète reste in-memory et peut confondre "
            "check_transitions au cycle suivant."
        )

    def test_t3_tiferet_guard_restores_panim_and_persists(self):
        """Non-régression T3 : ZA akhor + tiferet élevé → guard + persistance.

        Avant T3 : ZA akhor malgré tiferet=0.9 (rejet 70%+).
        Après T3 : apply_dynamic_scores mute ZA à panim (guard).
        Après Sprint 7 : cette mutation est aussi persistée en DB.
        """
        reg = _make_reg_with_mocked_db()
        state = _make_state({
            "zeir_anpin": {
                "orientation": "akhor",
                "faculties": {"tiferet": 0.9},
            },
        })
        reg.compute_dynamic_scores = MagicMock(
            return_value=_full_dynamic(
                zeir_anpin={
                    "dynamic_score": 0.35,
                    "recent_metrics": {},
                    "should_achor": True,
                    "achor_reason": "rejet 23/29 > 70%",
                },
            ),
        )

        reg.check_transitions(state)

        za_panim_calls = [
            c for c in reg.update_orientation_db.call_args_list
            if c.args[0] == "zeir_anpin" and c.args[1] == "panim"
        ]
        assert len(za_panim_calls) >= 1, (
            "Synergie T3 + Sprint 7 : tiferet guard mute ZA→panim, et le "
            "fix Sprint 7 doit persister cette mutation en DB."
        )

    def test_t3_low_tiferet_still_persists_akhor(self):
        """Non-régression T3 : ZA low tiferet + should_achor → akhor persiste.

        Avec tiferet=0.5 (≤ seuil 0.8), le guard n'intervient pas. ZA
        passe akhor in-memory ET en DB (comportement pré-Sprint 7 préservé).
        """
        reg = _make_reg_with_mocked_db()
        state = _make_state({
            "zeir_anpin": {
                "orientation": "panim",
                "faculties": {"tiferet": 0.5},
            },
        })
        reg.compute_dynamic_scores = MagicMock(
            return_value=_full_dynamic(
                zeir_anpin={
                    "dynamic_score": 0.35,
                    "recent_metrics": {},
                    "should_achor": True,
                    "achor_reason": "rejet 23/29",
                },
            ),
        )

        reg.check_transitions(state)

        za_akhor_calls = [
            c for c in reg.update_orientation_db.call_args_list
            if c.args[0] == "zeir_anpin" and c.args[1] == "akhor"
        ]
        assert len(za_akhor_calls) >= 1, (
            "Non-régression T3 : avec tiferet ≤ seuil, ZA→akhor doit "
            "persister (comportement existant)."
        )

    def test_multi_partzuf_bidirectional_flips_all_persist(self):
        """Cycle mixte : Abba akhor→panim ET Imma panim→akhor, les deux DB updates.

        Scénario doctrinal : Chokmah reçoit un éclair (insights reprennent),
        Binah épuisée (plus de claims causaux récents). Les deux transitions
        simultanées doivent persister.
        """
        reg = _make_reg_with_mocked_db()
        state = _make_state({
            "abba": {"orientation": "akhor"},
            "imma": {"orientation": "panim"},
        })
        reg.compute_dynamic_scores = MagicMock(
            return_value=_full_dynamic(
                abba=_dyn_active(0.6),        # akhor → panim
                imma=_dyn_achor("0 claims en 24h"),  # panim → akhor
            ),
        )

        reg.check_transitions(state)

        calls = reg.update_orientation_db.call_args_list
        call_tuples = [(c.args[0], c.args[1]) for c in calls]

        assert ("abba", "panim") in call_tuples, (
            f"Flip akhor→panim doit persister pour Abba. Calls : {call_tuples}"
        )
        assert ("imma", "akhor") in call_tuples, (
            f"Flip panim→akhor doit persister pour Imma. Calls : {call_tuples}"
        )

    def test_transitions_list_includes_akhor_to_panim_return(self):
        """La liste `transitions` retournée inclut le retour akhor→panim.

        Avant le fix : transitions[] n'enregistre que les flips→akhor (via
        `achor_reason and new=='akhor'`). Le retour panim est silencieux.
        Après le fix : les deux sens sont dans transitions[] pour le report
        daemon et l'audit.
        """
        reg = _make_reg_with_mocked_db()
        state = _make_state({"abba": {"orientation": "akhor"}})
        reg.compute_dynamic_scores = MagicMock(
            return_value=_full_dynamic(abba=_dyn_active(0.6)),
        )

        transitions = reg.check_transitions(state)

        abba_panim_transitions = [
            t for t in transitions
            if t.get("partzuf") == "abba" and "panim" in str(t.get("to", ""))
        ]
        assert len(abba_panim_transitions) >= 1, (
            f"La liste transitions doit reporter akhor→panim pour audit. "
            f"Transitions reçues : {transitions}"
        )
