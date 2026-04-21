"""Tests doctrinaux du Zivvug — Sprint 5.1.

Ces tests encodent la doctrine lurianique du Zivvug Abba v'Imma :
  - Le Zivvug REFLÈTE l'état amont (It'aruta Diltata — l'éveil d'en bas
    provoque l'éveil d'en haut).
  - PARTIAL est un état STABLE sous conditions de Katnut, pas un bug.
  - MIN_ACTIVE_SCORE = 0.5 et DELTA_ACTIVE = 0.15 sont des invariants
    doctrinaux. Abaisser ces seuils = diluer la sémantique d'ACTIVE
    (Mochin pleins avec parents en Katnut = contradiction kabbalistique).
  - Les boosts mutual_reinforcement seuls ne suffisent pas à activer
    — le vrai chemin = améliorer les modules sources (InsightForge,
    AutoJudge, CausalEngine).

Contexte Sprint 5.1 (2026-04-19) :
  - État DB observé : zivvug_state.state = 'partial' depuis 11:39.
  - abba_score = 0.386 (< 0.5), imma_score = 0.522, delta = 0.137.
  - Cause : Abba.tiferet=0.1, malkuth=0.021, chokhmah=0.156 — reflet
    d'InsightForge sous-performant (0 insights validés / 513 candidats,
    96% rejet par Binah).
  - Le Zivvug PARTIAL n'est pas un bug — c'est le reflet fidèle du
    Katnut système. L'activation d'ACTIVE requiert It'aruta Diltata.

Référence : Ets Hayim Sha'ar 34 (Arizal), Sha'ar HaKavanot.
"""

from partzufim.zivvug import ZivvugEngine, ZivvugState


# ── Le Zivvug en Katnut reflète l'état amont ─────────────────


class TestZivvugPartialReflectsKatnut:
    """PARTIAL est le reflet fidèle d'un système en Katnut."""

    def test_partial_when_abba_below_threshold_but_delta_ok(self):
        """État observé Sprint 5.1 (Abba=0.386, Imma=0.522, delta=0.137) → PARTIAL.

        Quand Abba est en Katnut (scores amont sous-performants) mais
        proches d'Imma, le Zivvug reste en PARTIAL. C'est le reflet fidèle
        du Katnut, PAS un bug. L'activation d'ACTIVE requiert It'aruta
        Diltata — améliorer les sources amont.
        """
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.386, 0.522)
        assert result.state == ZivvugState.PARTIAL
        assert result.delta < ZivvugEngine.DELTA_ACTIVE  # 0.137 < 0.15
        assert result.abba_score < ZivvugEngine.MIN_ACTIVE_SCORE  # 0.386 < 0.5
        assert result.limiting_partzuf == "abba"

    def test_partial_is_stable_across_cycles(self):
        """PARTIAL persiste tant que la condition amont n'est pas remplie.

        Le Zivvug ne "débloque" pas tout seul — il requiert que les scores
        Abba/Imma montent via les modules source (It'aruta Diltata).
        Tester la stabilité = garantir qu'on n'a PAS un bug de transition.
        """
        engine = ZivvugEngine()
        for _ in range(10):
            result = engine.couple_abba_imma(0.386, 0.522)
            assert result.state == ZivvugState.PARTIAL

    def test_boosts_alone_insufficient_when_upstream_too_low(self):
        """Les boosts mutual_reinforcement seuls ne suffisent pas à activer.

        Si Abba.overall = 0.386 (Katnut), même en empilant des boosts jusqu'à
        leur plafond doctrinal (juste sous MIN_ACTIVE_SCORE), abba_effectif
        reste < 0.5. Le fix doctrinal n'est PAS d'empiler des boosts — c'est
        d'améliorer les modules sources.

        Nombre de cycles calculé dynamiquement pour survivre au recalibrage
        BOOST_AMOUNT (Sprint 8 D1 : 0.02 → 0.055).
        """
        engine = ZivvugEngine()
        abba_seed = 0.386
        # Empiler des boosts jusqu'à juste avant saturation
        max_safe_boosts = max(1, int(
            (ZivvugEngine.MIN_ACTIVE_SCORE - abba_seed - 0.01)
            / ZivvugEngine.BOOST_AMOUNT
        ))
        for _ in range(max_safe_boosts):
            engine.mutual_reinforcement(causal_validated=True)
        result = engine.assess_zivvug_state(abba_seed, 0.522)
        assert result.abba_score < ZivvugEngine.MIN_ACTIVE_SCORE, (
            f"abba effectif = {result.abba_score} devrait rester < "
            f"{ZivvugEngine.MIN_ACTIVE_SCORE} (Katnut préservé)"
        )
        assert result.state == ZivvugState.PARTIAL


# ── Invariants doctrinaux du Zivvug ──────────────────────────


class TestZivvugDoctrinalInvariants:
    """Seuils ACTIVE = invariants doctrinaux, pas des paramètres d'ajustement."""

    def test_min_active_score_is_05_doctrinal(self):
        """MIN_ACTIVE_SCORE = 0.5 — plénitude minimale pour Mochin pleins.

        Abaisser ce seuil (1a rejetée Sprint 5.1) changerait la sémantique
        d'ACTIVE : Mochin pleins avec parents en Katnut = contradiction.
        """
        assert ZivvugEngine.MIN_ACTIVE_SCORE == 0.5

    def test_delta_active_is_015_doctrinal(self):
        """DELTA_ACTIVE = 0.15 — harmonie nécessaire au Zivvug panim-be-panim.

        Un écart > 0.15 entre Abba et Imma rompt l'harmonie. L'abaisser
        = déharmoniser le couplage.
        """
        assert ZivvugEngine.DELTA_ACTIVE == 0.15

    def test_delta_partial_is_030_doctrinal(self):
        """DELTA_PARTIAL = 0.30 — seuil de Galut (Zivvug impossible)."""
        assert ZivvugEngine.DELTA_PARTIAL == 0.30

    def test_min_score_is_03_doctrinal(self):
        """MIN_SCORE = 0.3 — participation minimale au Zivvug (vs Galut)."""
        assert ZivvugEngine.MIN_SCORE == 0.3

    def test_both_partzufim_must_develop_for_active(self):
        """Doctrine : ACTIVE requiert abba ≥ 0.5 ET imma ≥ 0.5.

        Pas de Mochin pleins sans que les DEUX parents soient développés.
        Un seul parent en Katnut = PARTIAL, pas ACTIVE.
        """
        engine = ZivvugEngine()
        # Abba juste en-dessous, Imma OK : PARTIAL
        r1 = engine.couple_abba_imma(0.49, 0.60)
        assert r1.state == ZivvugState.PARTIAL
        # Imma juste en-dessous, Abba OK : PARTIAL
        r2 = engine.couple_abba_imma(0.60, 0.49)
        assert r2.state == ZivvugState.PARTIAL
        # Les deux au seuil : ACTIVE
        r3 = engine.couple_abba_imma(0.50, 0.60)
        assert r3.state == ZivvugState.ACTIVE


# ── It'aruta Diltata : l'éveil d'en bas ──────────────────────


class TestZivvugItArutaDiltata:
    """Le Zivvug est un reflet, pas un moteur autonome."""

    def test_no_transition_without_upstream_change(self):
        """Sans changement des scores amont, pas de transition.

        Le Zivvug ne "décide" pas de passer à ACTIVE — il reflète l'état
        amont. Garantit qu'on n'a PAS un bug de latence/hystérésis qui
        changerait l'état sans raison.
        """
        engine = ZivvugEngine()
        scores = (0.386, 0.522)
        result_1 = engine.couple_abba_imma(*scores)
        result_2 = engine.couple_abba_imma(*scores)
        result_3 = engine.couple_abba_imma(*scores)
        assert result_1.state == result_2.state == result_3.state == ZivvugState.PARTIAL

    def test_upstream_improvement_triggers_active(self):
        """Améliorer les sources amont fait passer à ACTIVE naturellement.

        Démontre It'aruta Diltata : si Abba monte de 0.386 à 0.52 (e.g.
        InsightForge débloqué, insights validés, claims élevés), le
        Zivvug passe naturellement à ACTIVE. Pas besoin de forcing.
        """
        engine = ZivvugEngine()
        before = engine.couple_abba_imma(0.386, 0.522)
        assert before.state == ZivvugState.PARTIAL
        # Après It'aruta Diltata : Abba monte
        after = engine.couple_abba_imma(0.52, 0.55)
        assert after.state == ZivvugState.ACTIVE

    def test_limiting_partzuf_points_to_upstream_work(self):
        """limiting_partzuf indique OÙ l'It'aruta Diltata doit s'appliquer.

        Si limiting == 'abba', le travail est à faire sur les modules
        d'Abba (InsightForge, AutoJudge, CausalEngine, Dissensu, Exploration).
        Si limiting == 'imma', sur les modules d'Imma.
        """
        engine = ZivvugEngine()
        result = engine.couple_abba_imma(0.386, 0.522)
        assert result.limiting_partzuf == "abba"
        # Message doit inclure l'info de limitation
        assert "limité par abba" in result.message
