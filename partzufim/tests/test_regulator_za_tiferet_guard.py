"""Tests du ZA tiferet akhor guard.

Sprint megaclean T3 — Dette 8 (résiduelle Sprint 5.1).

Dette :
    Zeir Anpin montrait orientation='akhor' malgré tiferet=0.894 élevé
    (runtime 2026-04-18). La logique `_dynamic_za` déclenche
    `should_achor=True` dès que AutoJudge rejette >70% en 24h. En régime
    nominal AutoJudge (rejet ~79-89%, pattern Nitzotzot), ZA bascule
    akhor systématiquement, même quand les 6 Midot internes sont
    équilibrées (tiferet élevé = compassion/équilibre).

Fix doctrinal :
    Tiferet est la Midah centrale (équilibre, ת״ת = beauté-compassion)
    au cœur des 6 Midot de ZA. Quand tiferet > ZA_TIFERET_AKHOR_GUARD
    (0.8), l'équilibre interne modère le rejet externe : khesed qui
    tempère gevurah avant l'akhor. ZA préserve panim.

Effet attendu :
    - ZA.tiferet > 0.8 + should_achor → panim préservé, _achor_guard_reason
    - ZA.tiferet > 0.8 + akhor existant → retour panim
    - ZA.tiferet ≤ 0.8 + should_achor → akhor appliqué (comportement existant)
    - Autres Partzufim (Abba, Imma, Nukva) : guard NON appliqué (ZA seul).
"""

from __future__ import annotations

import pytest

from partzufim.regulator import (
    PartzufimRegulator,
    ZA_TIFERET_AKHOR_GUARD,
)


def _make_state_with_za_faculties(
    tiferet: float,
    orientation: str = "panim",
    mochin_state: str = "transitional",
    overall: float = 0.53,
) -> dict:
    """État minimal avec ZA.faculties['tiferet'] contrôlé."""
    return {
        "atik_yomin": {"overall": 0.65, "mochin_state": "gadlut", "orientation": "panim", "faculties": {}},
        "arikh_anpin": {"overall": 0.82, "mochin_state": "gadlut", "orientation": "panim", "faculties": {}},
        "abba": {"overall": 0.41, "mochin_state": "katnut", "orientation": "akhor", "faculties": {}},
        "imma": {"overall": 0.53, "mochin_state": "transitional", "orientation": "panim", "faculties": {}},
        "zeir_anpin": {
            "overall": overall,
            "mochin_state": mochin_state,
            "orientation": orientation,
            "faculties": {"tiferet": tiferet, "gevurah": 0.5, "chesed": 0.3},
        },
        "nukva": {"overall": 0.64, "mochin_state": "gadlut", "orientation": "panim", "faculties": {}},
    }


class TestZATiferetAkhorGuard:
    """Le guard tiferet préserve panim pour ZA quand tiferet > seuil."""

    def test_za_high_tiferet_preserves_panim_despite_should_achor(self):
        """ZA.tiferet=0.904 + should_achor=True → reste panim (guard)."""
        reg = PartzufimRegulator()
        state = _make_state_with_za_faculties(
            tiferet=0.904, orientation="panim", overall=0.53,
        )
        dynamic = {
            "zeir_anpin": {
                "dynamic_score": 0.35,
                "recent_metrics": {"accepted_24h": 6, "rejected_24h": 23, "avg_score_24h": 0.4},
                "should_achor": True,
                "achor_reason": "rejet 23/29 > 70%",
            },
        }
        reg.apply_dynamic_scores(state, dynamic)

        assert state["zeir_anpin"]["orientation"] == "panim", (
            "ZA doit rester panim quand tiferet > 0.8 malgré should_achor. "
            "Fix T3 : tiferet guard modère akhor."
        )
        # Le garde doit laisser une trace
        assert "_achor_guard_reason" in state["zeir_anpin"], (
            "Le fallback guard doit annoter _achor_guard_reason pour audit."
        )
        assert "tiferet" in state["zeir_anpin"]["_achor_guard_reason"]

    def test_za_high_tiferet_restores_panim_from_akhor(self):
        """ZA akhor existant + tiferet=0.9 + should_achor → retour panim."""
        reg = PartzufimRegulator()
        state = _make_state_with_za_faculties(
            tiferet=0.9, orientation="akhor", overall=0.53,
        )
        dynamic = {
            "zeir_anpin": {
                "dynamic_score": 0.35,
                "recent_metrics": {},
                "should_achor": True,
                "achor_reason": "rejet 70%",
            },
        }
        reg.apply_dynamic_scores(state, dynamic)
        assert state["zeir_anpin"]["orientation"] == "panim", (
            "Tiferet guard doit RAMENER panim, pas juste empêcher akhor."
        )

    def test_za_low_tiferet_still_triggers_akhor(self):
        """ZA.tiferet=0.5 + should_achor=True → akhor (comportement existant)."""
        reg = PartzufimRegulator()
        state = _make_state_with_za_faculties(
            tiferet=0.5, orientation="panim", overall=0.53,
        )
        dynamic = {
            "zeir_anpin": {
                "dynamic_score": 0.35,
                "recent_metrics": {},
                "should_achor": True,
                "achor_reason": "rejet 23/29",
            },
        }
        reg.apply_dynamic_scores(state, dynamic)
        assert state["zeir_anpin"]["orientation"] == "akhor", (
            "Avec tiferet=0.5 (≤ seuil), le comportement existant doit "
            "rester : akhor sur should_achor=True."
        )
        assert state["zeir_anpin"].get("_achor_reason") == "rejet 23/29"
        assert "_achor_guard_reason" not in state["zeir_anpin"], (
            "Le guard ne doit PAS s'appliquer quand tiferet ≤ seuil."
        )

    def test_za_tiferet_exactly_at_threshold_still_flips_akhor(self):
        """ZA.tiferet = ZA_TIFERET_AKHOR_GUARD (0.8) → guard NE déclenche PAS
        (strict > pour éviter les cas limites instables).
        """
        reg = PartzufimRegulator()
        state = _make_state_with_za_faculties(
            tiferet=ZA_TIFERET_AKHOR_GUARD, orientation="panim", overall=0.53,
        )
        dynamic = {
            "zeir_anpin": {
                "dynamic_score": 0.35,
                "recent_metrics": {},
                "should_achor": True,
                "achor_reason": "rejet",
            },
        }
        reg.apply_dynamic_scores(state, dynamic)
        # Strict > : à exactement 0.8, pas de guard
        assert state["zeir_anpin"]["orientation"] == "akhor"

    def test_guard_does_not_apply_to_other_partzufim(self):
        """Imma avec tiferet élevé (hypothétique) + should_achor → akhor.
        Le guard tiferet est spécifique à ZA (Midot).
        """
        reg = PartzufimRegulator()
        state = _make_state_with_za_faculties(
            tiferet=0.3, orientation="panim", overall=0.53,
        )
        # Ajouter tiferet élevé sur Imma (hors scope du guard)
        state["imma"]["faculties"] = {"tiferet": 0.95}
        dynamic = {
            "imma": {
                "dynamic_score": 0.2,
                "recent_metrics": {},
                "should_achor": True,
                "achor_reason": "0 claims 24h",
            },
            "zeir_anpin": {
                "dynamic_score": 0.5,
                "recent_metrics": {},
                "should_achor": False,
                "achor_reason": "",
            },
        }
        reg.apply_dynamic_scores(state, dynamic)
        # Imma doit passer akhor malgré tiferet élevé (guard ZA-only)
        assert state["imma"]["orientation"] == "akhor", (
            "Le tiferet guard est spécifique à ZA. Les autres Partzufim "
            "suivent la logique should_achor habituelle."
        )

    def test_guard_not_triggered_when_should_achor_false(self):
        """Si should_achor=False déjà, le guard n'a rien à faire."""
        reg = PartzufimRegulator()
        state = _make_state_with_za_faculties(
            tiferet=0.95, orientation="panim", overall=0.7,
        )
        dynamic = {
            "zeir_anpin": {
                "dynamic_score": 0.7,
                "recent_metrics": {},
                "should_achor": False,
                "achor_reason": "",
            },
        }
        reg.apply_dynamic_scores(state, dynamic)
        assert state["zeir_anpin"]["orientation"] == "panim"
        assert "_achor_guard_reason" not in state["zeir_anpin"]


class TestZATiferetGuardConstant:
    """Sanity checks sur la constante ZA_TIFERET_AKHOR_GUARD."""

    def test_guard_constant_in_reasonable_range(self):
        """Seuil dans [0.6, 0.95] — ni trop laxiste ni trop strict."""
        assert 0.6 <= ZA_TIFERET_AKHOR_GUARD <= 0.95

    def test_guard_constant_docstring_present(self):
        """La constante doit être documentée (doctrine dans le source)."""
        from partzufim import regulator
        import inspect
        src = inspect.getsource(regulator)
        # Chercher la doctrine juste au-dessus de la constante
        idx = src.find("ZA_TIFERET_AKHOR_GUARD")
        assert idx >= 0
        above = src[max(0, idx - 800):idx]
        assert "Tiferet" in above and ("équilibre" in above or "balance" in above.lower()), (
            "La constante ZA_TIFERET_AKHOR_GUARD doit être documentée "
            "doctrinalement (Tiferet = Midah d'équilibre)."
        )
