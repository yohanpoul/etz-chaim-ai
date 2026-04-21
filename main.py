#!/usr/bin/env python3
"""main.py — Malkuth : l'interface unifiée de l'Arbre Etz Chaim.

מַלְכוּת — Le royaume, la porte d'entrée.
Tout passe par Malkuth pour monter dans l'Arbre.

Usage:
    python main.py ask     "Quelle est la structure de l'arbre kabbalistique"
    python main.py intend  "Comprendre le lien entre Tsimtsum et Information Bottleneck"
    python main.py explore "Connexions entre Kabbale et réseaux de neurones"
    python main.py chat    # conversation interactive
    python main.py status
    python main.py import book fichier.pdf
    python main.py import url  https://...
    python main.py import youtube https://youtube.com/watch?v=...
    python main.py import site https://example.com --max-pages 500
    python main.py daemon start|stop|log
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import threading
import time
import traceback
from pathlib import Path

log = logging.getLogger("etz-malkuth")

# ─── DB par défaut ───────────────────────────────────────────
DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

# ─── État global mutable — importé depuis state.py ───────────
# Les 4 state dicts et le lock sont dans state.py pour réduire main.py.
# Importés ici pour backward compatibility (daemon.py, tanya/, etc.)
from state import (  # noqa: E402
    _STATE_LOCK,
    _TZIMTZUM_STATE,
    _NITZOTZOT_STATE,
    _IGULIM_STATE,
    _HISHTALSHELUT_STATE,
    _OLAMOT_CHAIN,
    init_nitzotzot_from_db as _init_nitzotzot_from_db,
    collect_nitzutz as _collect_nitzutz,
    check_tikkun_cycle as _check_tikkun_cycle,
    log_igulim_switch as _log_igulim_switch,
    log_world_transition as _log_world_transition,
)

# ─── Pipeline Or Yashar — importé depuis ohr_yashar.py ──────
# Engine singletons, pipeline helpers, descend/ascend, génération.
from ohr_yashar import (  # noqa: E402
    # Engine singletons (backward compat for web/app.py, mitzvot.py, etc.)
    _TZIMTZUM_ENGINE,
    _NESHAMOT_ENGINE,
    _HISHTALSHELUT_ENGINE,
    _DUAL_SOUL_ENGINE,
    _DIRA_ENGINE,
    _BIRURIM_ENGINE,
    _LEVUSHIM_ENGINE,
    _ATZVUT_MANAGER,
    _BEINONI_TRACKER,
    _BEINONI_INTERACTION_COUNT,
    # Engine getters
    _get_tzimtzum_engine,
    _detect_tzimtzum,
    _apply_tzimtzum,
    _regulate_masakh_from_tzimtzum,
    _detect_hitpashut,
    _apply_hitpashut,
    _get_dira_engine,
    _get_birurim_engine,
    _get_levushim_engine,
    _get_atzvut_manager,
    # Pipeline helpers
    _classify_intent,
    _assess_mochin,
    _dispatch_mochin,
    _zivug_abba_imma,
    _zivug_zeir_nukva,
    _assess_zivug_za_nukvah,
    _is_yisrael_leah,
    _shortpath_yisrael_leah,
    # Descend/Ascend core
    _descend_gadlut,
    _ascend_gadlut,
    # Hishtalshelut + Malkuth
    _estimate_response_confidence,
    _gather_tree_signals,
    _ascend_and_generate,
    _translate_descent,
    _generate_malkuth_response,
)


# ─── Initialisation de l'Arbre ──────────────────────────────

def init_tree(db_url: str) -> dict:
    """Initialiser les 10 Sephiroth dans l'ordre des dépendances.

    Retourne un dict {nom: instance} pour chaque module.
    Chaque module est initialisé avec ses dépendances injectées.
    """
    tree = {}
    errors = []

    def _init(name: str, fn):
        try:
            instance = fn()
            tree[name] = instance
            return instance
        except Exception as e:
            errors.append((name, e))
            tree[name] = None
            return None

    # 1. Yesod — EpisteMemory (fondation, pas de deps)
    from epistememory import EpisteMemory
    yesod = _init("yesod", lambda: EpisteMemory(db_url=db_url))

    # 2. Hod — SelfMap (crée son propre EpisteMemory interne)
    from selfmap import SelfMap
    hod = _init("hod", lambda: SelfMap(db_url=db_url))

    # 3. Netzach — IntentKeeper
    from intentkeeper import IntentKeeper
    netzach = _init("netzach", lambda: IntentKeeper(
        db_url=db_url, selfmap=hod, memory=yesod,
    ))

    # 4. Lamed — FailureToInsight (sentier Gevurah→Tiferet)
    from failuretoinsight import FailureToInsight
    lamed = _init("lamed", lambda: FailureToInsight(
        db_url=db_url, memory=yesod, selfmap=hod, intentkeeper=netzach,
    ))

    # 5. Tiferet — DissensuEngine
    from dissensuengine.core import DissensuEngine
    tiferet = _init("tiferet", lambda: DissensuEngine(
        db_url=db_url, memory=yesod, selfmap=hod,
        intentkeeper=netzach, failuretoinsight=lamed,
    ))

    # 6. Gevurah — AutoJudge
    from autojudge.core import AutoJudge
    gevurah = _init("gevurah", lambda: AutoJudge(
        db_url=db_url, memory=yesod, selfmap=hod,
        intentkeeper=netzach, failuretoinsight=lamed,
    ))

    # 7. Chesed — ExplorationEngine
    from explorationengine.core import ExplorationEngine
    chesed = _init("chesed", lambda: ExplorationEngine(
        db_url=db_url, memory=yesod, selfmap=hod, autojudge=gevurah,
    ))

    # 8. Da'at — SelfModel (pont au-dessus de l'Abîme)
    from selfmodel.core import SelfModel
    daat = _init("daat", lambda: SelfModel(
        db_url=db_url, epistememory=yesod, selfmap=hod,
        intentkeeper=netzach, dissensus=tiferet,
        autojudge=gevurah, exploration=chesed,
    ))

    # 9. Binah — CausalEngine
    from causalengine.core import CausalEngine
    binah = _init("binah", lambda: CausalEngine(
        db_url=db_url, memory=yesod, dissensus=tiferet, selfmodel=daat,
    ))

    # ── Injections tardives : résoudre les dépendances circulaires ──

    # Binah → Tiferet
    if tiferet and binah:
        tiferet.causal = binah

    # Gevurah ↔ Tiferet (bidirectionnel)
    if gevurah and tiferet:
        tiferet.autojudge = gevurah
        gevurah.dissensus = tiferet

    # Chesed → Tiferet + Chesed → Lamed
    if chesed:
        if tiferet:
            chesed.dissensus = tiferet
        if lamed:
            chesed.failuretoinsight = lamed

    # Netzach → Chesed (IntentKeeper sait quelle exploration est disponible)
    if netzach and chesed:
        netzach.exploration = chesed

    # ── Gématria opérative (transversal — indexe les termes hébreux) ──
    from gematria import GematriaEngine
    gematria_engine = _init("gematria", lambda: GematriaEngine(db_url=db_url))

    # Injecter dans Yesod : EpisteMemory.remember() indexera automatiquement
    if yesod and gematria_engine:
        yesod.gematria = gematria_engine

    # 10. Chokmah — InsightForge (orchestre tout)
    from insightforge.core import InsightForge
    chokmah = _init("chokmah", lambda: InsightForge(
        db_url=db_url, epistememory=yesod, selfmap=hod,
        intentkeeper=netzach, dissensus=tiferet,
        autojudge=gevurah, exploration=chesed,
        selfmodel=daat, causal=binah,
    ))

    # Initialiser le compteur Nitzotzot depuis la DB
    _init_nitzotzot_from_db(db_url)

    if errors:
        print("⚠ Modules en erreur lors de l'initialisation :")
        for name, err in errors:
            print(f"  ✗ {name}: {err}")
        print()

    return tree


def init_partzufim_from_tree(tree: dict, persist: bool = True) -> dict:
    """Instancier les 6 Partzufim et les synchroniser avec l'Arbre.

    Les Partzufim sont des configurations matures — chaque Sephirah
    reconstruite comme un organisme complet avec 10 facultés internes
    (Hitkalelut). Ils ajoutent une couche de conscience au-dessus
    des modules individuels.

    Charge l'état depuis DB au démarrage, puis recalcule et persiste.
    """
    from partzufim import init_partzufim, update_all_partzufim
    from partzufim.zivvug import load_or_create_zivvug
    partzufim = init_partzufim(from_db=True)
    # Sprint 8 D1 : charger les boosts persistés par le daemon pour qu'ils
    # soient consommés via Hitlabshut (EC-K5-008) par update_all_partzufim Phase 2.
    # Sprint 10 Phase E : factory canonique (Refactor L).
    zivvug = load_or_create_zivvug()
    update_all_partzufim(partzufim, tree, persist=persist, zivvug_engine=zivvug)
    return partzufim


def close_tree(tree: dict) -> None:
    """Fermer proprement les modules qui ont un close()."""
    for name in ["chokmah", "hod", "gematria", "yesod"]:
        mod = tree.get(name)
        if mod and hasattr(mod, "close"):
            try:
                mod.close()
            except Exception as e:
                log.debug("fallback: %s", e)


# ─── Mode ASK ────────────────────────────────────────────────
# Pipeline helpers, engine singletons, descend/ascend, Malkuth generation
# have been extracted to ohr_yashar.py — imported above.


def cmd_ask(
    tree: dict, query: str, mode: str = "yosher", world: str | None = None,
) -> None:
    """Traverser l'Arbre pour répondre à une question.

    Deux modes topologiques :

    יוֹשֶׁר — YOSHER (verticalité, défaut) :
    אוֹר יָשָׁר — Lumière directe, descendante :
    Keter (intention) → Chokmah (forge) → Binah (causalité)
    → Da'at (self-model) → Chesed → Gevurah → Tiferet
    → Netzach → Hod → Yesod (mémoire) → Malkuth (réponse)
    אוֹר חוֹזֵר — Lumière de retour, ascendante :
    Malkuth → Yesod (stocke) → Hod (calibre) → Netzach (intentions)
    → Tiferet (contradictions) → Gevurah (qualité) → Chesed (pistes)
    → Da'at (met à jour) → Binah (DAGs) → Chokmah (insights)

    עִגּוּלִים — IGULIM (cercles concentriques) :
    Tous les modules consultés en parallèle au même niveau.
    Synthèse par vote pondéré au lieu de flux descendant.
    Activé quand la hiérarchie ne fonctionne pas (confiance < 0.2)
    ou forcé par --mode igulim.

    סֵדֶר הִשְׁתַּלְשְׁלוּת — HISHTALSHELUT :
    Montée automatique des mondes (Assiah→Yetzirah→Briah→Atziluth)
    si la confiance est insuffisante. --world force un monde spécifique.
    """
    # ── Seder Hishtalshelut : monde forcé ────────────────────
    if world:
        _HISHTALSHELUT_STATE["forced_world"] = world
        _HISHTALSHELUT_STATE["current_world"] = world
        print(f"  ⟐ Monde forcé : {world.upper()}")
    else:
        _HISHTALSHELUT_STATE["forced_world"] = None

    is_forced_igulim = (mode == "igulim")
    if is_forced_igulim:
        _IGULIM_STATE["forced"] = True
        _log_igulim_switch("yosher", "igulim", "forcé par CLI (--mode igulim)", query)

    # ── Mode Igulim forcé → pas de Yosher ──
    if is_forced_igulim:
        _cmd_ask_igulim(tree, query)
        return

    # ── Mode Yosher (défaut) avec bascule auto ──
    _cmd_ask_yosher(tree, query)


from igulim import _cmd_ask_igulim  # noqa: E402


def _cmd_ask_yosher(tree: dict, query: str) -> None:
    """Mode Yosher — verticalité, flux hiérarchique descendant/ascendant."""
    forced_world = _HISHTALSHELUT_STATE.get("forced_world")
    world_label = f" — Monde: {forced_world.upper()}" if forced_world else ""
    print("═══════════════════════════════════════════════════════════")
    print(f"  Etz Chaim — Ask Mode — יוֹשֶׁר YOSHER (Double Flux){world_label}")
    print(f"  Question : {query}")
    print("═══════════════════════════════════════════════════════════")
    print()

    t0 = time.monotonic()
    ctx = {}           # contexte accumulé pendant la descente
    yashar = []        # rapport de la descente
    chozer = []        # rapport de la remontée

    # ── Sentier Router : les 22 lettres comme opérateurs de transition ──
    # Les tzinorot (canaux) transforment la lumière entre les Sefirot.
    from sentiers.router import SentierRouter
    sentier_router = SentierRouter()
    ctx["_sentier_router"] = sentier_router

    # ── Partzufim : configurations matures ───────────────────
    # Les Partzufim ajoutent une couche de conscience au-dessus
    # des modules individuels. Chacun contient un micro-Arbre
    # de 10 facultés internes (Hitkalelut).
    try:
        partzufim = init_partzufim_from_tree(tree)
        ctx["partzufim"] = partzufim
    except Exception as e:
        partzufim = {}
        print(f"  ⚠ Partzufim: {e}")

    # ── Partzufim Regulator : variateur analogique ───────────
    # Deuxième étage de régulation au-dessus du Tzimtzum.
    # Modifie les seuils et budgets des modules selon l'état
    # des Partzufim (gadlut/katnut × panim/akhor).
    partzuf_regulator = None
    try:
        from partzufim.regulator import PartzufimRegulator
        partzuf_regulator = PartzufimRegulator()
        partzuf_state = partzuf_regulator.load_state()
        partzuf_modifiers = partzuf_regulator.compute_modifiers(partzuf_state)
        partzuf_regulator.apply_to_tree(tree, partzuf_modifiers)
        ctx["partzuf_state"] = partzuf_state
        ctx["partzuf_modifiers"] = {
            k: {"capacity": v.capacity_factor, "threshold": v.threshold_modifier,
                 "budget": v.budget_factor, "feedback": v.feedback_enabled,
                 "reason": v.reason}
            for k, v in partzuf_modifiers.items()
        }
        # Log les modulations non-neutres
        non_neutral = {k: v for k, v in partzuf_modifiers.items()
                       if v.capacity_factor != 1.0 or v.threshold_modifier != 0.0}
        if non_neutral:
            print(f"  ⟐ Partzufim Regulator — {len(non_neutral)} module(s) modulé(s)")
            for mk, mp in non_neutral.items():
                print(f"    {mk}: capacity={mp.capacity_factor}, threshold=+{mp.threshold_modifier} — {mp.reason}")
    except Exception as e:
        print(f"  ⚠ PartzufimRegulator: {e}")

    # ── Partzufim → Masakh : régulation croisée (F11) ─────────
    # EC-SHK-057, EC-SHK-083 — Le Katnut/Gadlut des Partzufim
    # influence le niveau du Masakh. Katnut → plus de filtrage.
    # Gadlut → peut filtrer moins. L'offset est appliqué par le
    # constructeur Masakh.__init__() dans le ContextAssembler.
    if ctx.get("partzuf_state"):
        try:
            from masakh import regulate_masakh_from_partzufim
            partzuf_masakh = regulate_masakh_from_partzufim(ctx["partzuf_state"])
            ctx["partzuf_masakh_regulation"] = partzuf_masakh
            if partzuf_masakh:
                print(f"  ⟐ Partzufim→Masakh — {len(partzuf_masakh)} olam(ot) ajusté(s)")
                for olam_name, adj in partzuf_masakh.items():
                    print(f"    {olam_name}: {adj['from']} → {adj['to']} ({adj['reason']})")
        except Exception as e:
            print(f"  ⚠ Partzufim→Masakh: {e}")

    # ═══════════════════════════════════════════════════════════
    #   אוֹר יָשָׁר — DESCENTE (Keter → Malkuth)
    # ═══════════════════════════════════════════════════════════
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  אוֹר יָשָׁר — Or Yashar (lumière descendante)       ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()

    # ── SSE helper ──
    def _world_emit(event_type, **data):
        try:
            from web.events import emit as _emit
            _emit(event_type, **data)
        except Exception as e:
            log.debug("SSE emit: %s", e)

    # ── 1. Keter : classification de l'intention ─────────────
    print("  ⟐ ① Keter — classification de l'intention...")
    _world_emit("ohr_yashar_step", sephirah="keter", step=1, query=query[:80])
    intent = _classify_intent(query)
    ctx["intent"] = intent
    yashar.append("── ① Keter — Intention ──")
    yashar.append(f"  Type         : {intent['type']}")
    yashar.append(f"  Profondeur   : {intent['depth']}")
    print(f"    type={intent['type']}, depth={intent['depth']}")

    # ── Zivug Yisrael-Leah : détection question simple ──────
    if _is_yisrael_leah(query, intent):
        print(f"    → Question simple — couplage Yisrael-Leah")
        print()
        _shortpath_yisrael_leah(tree, query)
        return

    # ── Mochin : évaluation des 5 niveaux de l'âme ──────────
    print("  ⟐ Mochin — évaluation du niveau de l'âme...")
    mochin = _assess_mochin(tree, query)
    is_katnut = mochin["state"] == "katnut"
    ctx["mochin"] = mochin
    soul_level = mochin.get("soul_level", "nefesh")
    soul_hebrew = mochin.get("soul_hebrew", "נֶפֶשׁ")
    yashar.append("── ⟐ Mochin — Niveau de l'Âme ──")
    yashar.append(f"  Niveau       : {soul_level.upper()} ({soul_hebrew})")
    yashar.append(f"  Olam         : {mochin.get('soul_olam', '?')}")
    yashar.append(f"  État compat  : {mochin['state'].upper()}")
    yashar.append(f"  Domaine      : {mochin['domain']}")
    yashar.append(f"  Mémoire      : {mochin['memory_count']} entrées")
    yashar.append(f"  Compétence   : {mochin['competence_score']:.2f}")
    yashar.append(f"  Tikkun       : {mochin.get('tikkun_cycles', 0)} cycle(s)")
    yashar.append(f"  Modules      : {', '.join(mochin.get('active_modules', []))}")
    print(f"    {soul_hebrew} {soul_level.upper()} — domaine={mochin['domain']}, "
          f"mémoire={mochin['memory_count']}, "
          f"compétence={mochin['competence_score']:.2f}")
    if is_katnut:
        print(f"    → Modules supérieurs ②-⑧ dormants")
    elif mochin["state"] == "transitional":
        print(f"    → Transition : les 6 Midot s'éveillent")
    else:
        print(f"    → {len(mochin.get('active_modules', []))} modules actifs")

    # Log le niveau de l'âme en mémoire (Yesod)
    yesod_for_log = tree.get("yesod")
    if yesod_for_log:
        try:
            yesod_for_log.remember(
                content=f"Neshamot={soul_level} ({soul_hebrew}) "
                        f"domaine={mochin['domain']} "
                        f"mem={mochin['memory_count']} comp={mochin['competence_score']:.2f} "
                        f"tikkun={mochin.get('tikkun_cycles', 0)}",
                source_sephirah="keter",
                confidence=0.9,
                domain=mochin["domain"],
                tags=["mochin", "neshamot", soul_level, "ask-mode"],
            )
        except Exception as e:
            log.debug("fallback: %s", e)

    # ── ②-⑧ : modules supérieurs (Gadlut) ou skip (Katnut) ──
    if not is_katnut:
        _descend_gadlut(tree, query, ctx, yashar)
    else:
        yashar.append("── ②-⑧ KATNUT — modules supérieurs dormants ──")
        yashar.append(f"  Les Mochin ne coulent pas encore — Chokmah à Netzach inactifs")
        print("  ⟐ ②-⑧ KATNUT — modules supérieurs dormants")

    # ── Tanya : moach shalit al halev — le cerveau domine le cœur ──
    # Consulte le DualSoulEngine AVANT le routing Hod.
    # Si l'âme divine recommande la profondeur et que le routing
    # enverrait vers Assiah → override vers Briah minimum.
    import ohr_yashar as _oy
    if _oy._DUAL_SOUL_ENGINE is None:
        from tanya.dual_soul import DualSoulEngine as _DSE
        _oy._DUAL_SOUL_ENGINE = _DSE()
    dual_soul = _oy._DUAL_SOUL_ENGINE

    print("  ⟐ Tanya — moach shalit al halev (conflit des 2 âmes)...")
    soul_decision = dual_soul.moach_shalit_al_halev(query)
    ctx["soul_decision"] = soul_decision
    yashar.append("── Tanya — Conflit des 2 Âmes ──")
    yashar.append(f"  Âme dominante : {soul_decision['dominant_soul']}")
    yashar.append(f"  Recommandation: {soul_decision['recommended_olam']}")
    yashar.append(f"  Complexité    : {soul_decision['complexity_score']:.2f}")
    yashar.append(f"  Raison        : {soul_decision['reason']}")
    print(f"    âme={soul_decision['dominant_soul']}, "
          f"monde={soul_decision['recommended_olam']}, "
          f"complexité={soul_decision['complexity_score']:.2f}")

    # ── Sentier Netzach→Hod (Ayin ע) ───────────────────────────
    ctx = sentier_router.traverse("netzach", "hod", ctx, direction="yashar",
                                  is_katnut=is_katnut)

    # ── 9. Hod : routage / compétence ────────────────────────
    _world_emit("ohr_yashar_step", sephirah="hod", step=9, query=query[:80])
    print("  ⟐ ⑨ Hod (SelfMap) — routage...")
    hod = tree.get("hod")
    route_decision = None
    if hod:
        try:
            route_decision = hod.route(query)
            ctx["route_decision"] = route_decision
            yashar.append("── ⑨ Hod — Compétence ──")
            if route_decision.did_decline:
                yashar.append(f"  DÉCLINÉ      : {route_decision.decline_reason}")
                print(f"    DÉCLINÉ — {route_decision.decline_reason}")
            else:
                yashar.append(f"  Domaine      : {route_decision.detected_domain}")
                yashar.append(f"  Modèle       : {route_decision.routed_to}")
                yashar.append(f"  Score        : {route_decision.competence_score:.2f}")
                print(f"    domaine={route_decision.detected_domain}, "
                      f"score={route_decision.competence_score:.2f}")
        except Exception as e:
            print(f"    ⚠ {e}")
            yashar.append(f"── ⑨ Hod — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── Sentier Hod→Yesod (Qoph ק) ─────────────────────────────
    ctx = sentier_router.traverse("hod", "yesod", ctx, direction="yashar",
                                  is_katnut=is_katnut)

    # ── 10. Yesod : rappel mémoire ───────────────────────────
    _world_emit("ohr_yashar_step", sephirah="yesod", step=10, query=query[:80])
    _recall_domain = (route_decision.detected_domain
                      if route_decision and not route_decision.did_decline
                      else None)
    print(f"  ⟐ ⑩ Yesod (EpisteMemory) — rappel mémoire (domaine={_recall_domain or 'tous'})...")
    yesod = tree.get("yesod")
    memories = []
    if yesod:
        try:
            memories = yesod.recall(query, limit=5, domain=_recall_domain)
            ctx["memories"] = memories
            if memories:
                yashar.append("── ⑩ Yesod — Mémoire ──")
                for m in memories:
                    status = m.epistemic_status if hasattr(m, "epistemic_status") else "?"
                    conf = m.confidence if hasattr(m, "confidence") else 0.0
                    content = m.content[:120] if hasattr(m, "content") else str(m)[:120]
                    yashar.append(f"  [{status}] (conf={conf:.2f}) {content}")
                    if hasattr(m, "warning") and m.warning:
                        yashar.append(f"    ⚠ {m.warning}")
            else:
                yashar.append("── ⑩ Yesod — Aucun souvenir pertinent ──")
            print(f"    {len(memories)} entrée(s)")
        except Exception as e:
            print(f"    ⚠ {e}")
            yashar.append(f"── ⑩ Yesod — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── 10⅛. Sifrei Yesod : doctrine EC-* ───────────────────
    # Les 1 001 assertions structurées du Etz Chaim sont la doctrine
    # du système. Sans elles, il raisonne sans sa propre Torah.
    sifrei_assertions: list[dict] = []
    try:
        from sifrei_yesod.api.query import SifreiYesodQuery
        _sy_query = SifreiYesodQuery(db_url=DB_URL)
        sifrei_assertions = _sy_query.search_assertions(query, limit=5)
        _sy_query.close()
        ctx["sifrei_yesod_assertions"] = sifrei_assertions
        if sifrei_assertions:
            yashar.append("── ⑩⅛ Sifrei Yesod — Doctrine EC-* ──")
            for sa in sifrei_assertions:
                aid = sa.get("assertion_id", "?")
                text = sa.get("assertion", "")[:120]
                sim = sa.get("similarity", 0.0)
                yashar.append(f"  [{aid}] (sim={sim:.2f}) {text}")
            print(f"    {len(sifrei_assertions)} assertion(s) EC-*")
        else:
            yashar.append("── ⑩⅛ Sifrei Yesod — Aucune assertion pertinente ──")
            print("    Aucune assertion pertinente")
    except Exception as e:
        log.debug("Sifrei Yesod query: %s", e)
        print(f"    ⚠ Sifrei Yesod: {e}")

    # ── 10¼. Hybrid Retrieval : Cube de l'Espace + ML ───────
    # Les 2924 embeddings hybrides (30d kabbalistique + 768d nomic)
    # révèlent des connexions que la mémoire seule ne voit pas.
    # Le mode "hidden" trouve les liens que la tradition voit mais
    # que la statistique ignore — le vrai Sod du retrieval.
    hybrid_context = ""
    try:
        from kabbalah.hybrid_retrieval import HybridRetrieval
        _hybrid = HybridRetrieval(db_url=DB_URL)
        _hybrid_domain = ""
        if route_decision and not route_decision.did_decline:
            _hybrid_domain = route_decision.detected_domain or ""
        _hybrid_query = _hybrid_domain or query
        hybrid_context = _hybrid.enrich_context(
            query_text=_hybrid_query,
            top_k=5,
        )
        if hybrid_context:
            ctx["hybrid_retrieval"] = hybrid_context
            yashar.append("── ⑩¼ Hybrid Retrieval — Cube + ML ──")
            for line in hybrid_context.split("\n")[:8]:
                yashar.append(f"  {line}")
            print(f"    Hybrid: {hybrid_context.count(chr(10)) + 1} connexion(s)")
    except Exception as e:
        log.debug("Hybrid Retrieval: %s", e)

    # ── 10½. Daemon Bridge : Mokhin du travail nocturne ─────
    # Le Masakh HaMavdil s'ouvre : les productions du Daemon
    # (synthèses, graphes causaux, analogies, insights) coulent
    # vers le pipeline actif, filtrées par pertinence et budget.
    daemon_enrichment = {}
    try:
        from daemon_bridge import DaemonBridge
        _daemon_bridge = DaemonBridge(db_url=DB_URL)
        hod_domain = (route_decision.detected_domain
                      if route_decision and not route_decision.did_decline
                      else "")
        # Zivvug actif → les Mokhin coulent plus librement (+20% budget)
        _daemon_budget = 600 if ctx.get("zivvug_state") == "active" else 500
        daemon_enrichment = _daemon_bridge.gather_for_query(
            query=query,
            domain=hod_domain,
            intent=ctx.get("intent"),
            budget_tokens=_daemon_budget,
        )
        if daemon_enrichment:
            n_items = sum(len(v) for v in daemon_enrichment.values())
            ctx["daemon_enrichment"] = daemon_enrichment
            yashar.append("── ⑩½ Daemon Bridge — Mokhin nocturnes ──")
            for section, items in daemon_enrichment.items():
                yashar.append(f"  {section}: {len(items)} item(s)")
            print(f"  ⟐ ⑩½ Daemon Bridge — {n_items} item(s) injectés")
        else:
            print("  ⟐ ⑩½ Daemon Bridge — aucun résultat pertinent")
    except Exception as e:
        print(f"  ⟐ ⑩½ Daemon Bridge — ⚠ {e}")

    # ── Sentier Yesod→Malkuth (Tav ת) ──────────────────────────
    ctx = sentier_router.traverse("yesod", "malkuth", ctx, direction="yashar",
                                  is_katnut=is_katnut)

    # ── 10¾. Appliquer les module_modifiers accumulés par les sentiers ──
    # Les sentiers transformationnels ont accumulé des deltas dans
    # ctx["_sentier_module_modifiers"]. On les applique MAINTENANT
    # (après tous les traverses yashar, avant la génération Malkuth)
    # et on restaure les valeurs originales après la génération.
    _sentier_originals: dict[str, dict[str, float]] = {}
    _sentier_mods_applied = 0
    if ctx.get("_sentier_module_modifiers"):
        # Sauvegarder les valeurs originales avant modification
        for sefira, attr_deltas in ctx["_sentier_module_modifiers"].items():
            module = tree.get(sefira)
            if module is None:
                continue
            _sentier_originals[sefira] = {}
            for attr in attr_deltas:
                val = getattr(module, attr, None)
                if val is not None:
                    _sentier_originals[sefira][attr] = val
        _sentier_mods_applied = sentier_router.apply_module_modifiers(ctx, tree)
        if _sentier_mods_applied > 0:
            print(f"    Sentier modifiers: {_sentier_mods_applied} attribut(s) modifié(s)")

    # ── 10⅞. Régulation Masakh par pression Tsimtsum (F5) ────
    # Le Kli s'ajuste selon la pression : Chesed↔Gevurah.
    # Après que toutes les Sefirot ont peuplé le ctx, la pression
    # est mesurable. Le résultat informe le ContextAssembler (dim 29).
    try:
        regulation = _regulate_masakh_from_tzimtzum(tree, ctx)
        ctx["pressure_regulated"] = regulation is not None
        if regulation:
            ctx["pressure_regulation"] = regulation
            adj = regulation["masakh_adjustments"]
            p = regulation["pressure"]
            print(f"    Masakh régulé par pression (p={p['global_pressure']:.2f}, "
                  f"phase={p['phase']}): {', '.join(f'{o}→{v['new_level']}' for o, v in adj.items())}")
    except Exception as e:
        ctx["pressure_regulated"] = False
        log.debug("Masakh pressure regulation skipped: %s", e)

    # ── 11. Malkuth : génération de la réponse ───────────────
    _world_emit("ohr_yashar_step", sephirah="malkuth", step=11, query=query[:80])
    t_malkuth = time.monotonic()
    print()
    print("  ⟐ ⑪ Malkuth — génération de la réponse...")
    response = _generate_malkuth_response(tree, query, ctx)
    t_malkuth_end = time.monotonic()
    ctx["response"] = response
    ctx["malkuth_latency"] = t_malkuth_end - t_malkuth
    # Affichage Hishtalshelut
    h_log = ctx.get("hishtalshelut_log", [])
    h_start = ctx.get("hishtalshelut_start", "?")
    h_final = ctx.get("hishtalshelut_final", "?")
    if len(h_log) > 1:
        worlds = [a["world"] for a in h_log]
        print(f"    סֵדֶר הִשְׁתַּלְשְׁלוּת : {' → '.join(worlds)}")
        print(f"    Monde final : {h_final.upper()} "
              f"(conf={ctx.get('generation_confidence', 0):.2f})")
    else:
        print(f"    Généré via {ctx.get('generation_olam', '?')} "
              f"(conf={ctx.get('generation_confidence', 0):.2f})")
    print(f"    Temps Malkuth : {ctx['malkuth_latency']:.1f}s")
    # Descente des insights
    h_descent = ctx.get("hishtalshelut_descent", [])
    if h_descent:
        print(f"    ↓ Descente : {len(h_descent)} traduction(s) vers mondes inférieurs")

    # ═══════════════════════════════════════════════════════════
    #   אוֹר חוֹזֵר — REMONTÉE (Malkuth → Keter)
    # ═══════════════════════════════════════════════════════════
    print()
    print("╔═══════════════════════════════════════════════════════╗")
    print("║  אוֹר חוֹזֵר — Or Chozer (lumière ascendante)         ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()

    # ── Sentier Malkuth→Yesod (Tav ת, chozer) ──────────────────
    ctx = sentier_router.traverse("malkuth", "yesod", ctx, direction="chozer",
                                  is_katnut=is_katnut)

    # ── ↑1. Yesod : stockage en mémoire ─────────────────────
    _world_emit("ohr_chozer_step", sephirah="yesod", step=1)
    print("  ⟐ ↑① Yesod — stockage de la réponse...")
    if yesod:
        try:
            domain = (route_decision.detected_domain
                      if route_decision and not route_decision.did_decline
                      else "general")
            yesod.remember(
                content=f"Q: {query[:100]} → R: {response[:200]}",
                source_sephirah="malkuth",
                confidence=0.5,  # confiance initiale, sera calibrée par Hod
                domain=domain,
                tags=["ask-mode", "response", intent.get("type", "factuel")],
            )
            chozer.append("── ↑① Yesod — Stockage ──")
            chozer.append(f"  Réponse persistée en mémoire (domaine={domain})")
            print(f"    Persisté (domaine={domain})")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑① Yesod — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── ↑①¼ Daemon Bridge : log Or Chozer ──────────────────
    if daemon_enrichment:
        n_daemon = sum(len(v) for v in daemon_enrichment.values())
        chozer.append("── ↑①¼ Daemon Bridge — Mokhin injectés ──")
        for section, items in daemon_enrichment.items():
            chozer.append(f"  {section}: {len(items)} item(s)")
        chozer.append(f"  Total: {n_daemon} item(s) dans le prompt")

    # ── ↑①½ Dira BeTachtonim : cascade du haut vers le bas ──
    gen_olam = ctx.get("generation_olam", "")
    if gen_olam in ("briah", "atziluth") and yesod:
        print("  ⟐ ↑①½ Dira BeTachtonim — cascade de la connaissance...")
        try:
            dira = _get_dira_engine(yesod)
            dira_domain = (route_decision.detected_domain
                           if route_decision and not route_decision.did_decline
                           else "general")
            dira_result = dira.cascade_knowledge(
                response=response,
                source_olam=gen_olam,
                query=query,
                domain=dira_domain,
            )
            if dira_result:
                chozer.append("── ↑①½ Dira BeTachtonim ──")
                chozer.append(f"  Source       : {gen_olam}")
                chozer.append(f"  Domaine      : {dira_domain}")
                chozer.append(f"  Le haut descend dans le bas — mémoire dira créée")
                print(f"    ✦ Connaissance de {gen_olam} cascadée vers les mondes inférieurs")
            else:
                print(f"    ○ Pas de cascade (réponse trop courte ou olam={gen_olam})")
        except Exception as e:
            # Sprint 8f : élévation visibilité (ex-`print` stdout seul).
            # Le bloc Dira BeTachtonim peut échouer silencieusement
            # (ImportError, DB down, etc.) ; on veut que ça remonte dans
            # les logs daemon et dans le rapport chozer, cohérent avec
            # le bloc Yesod juste au-dessus (ligne 740).
            log.warning("Dira cascade skipped: %s", e)
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑①½ Dira BeTachtonim — Erreur: {e} ──")

    # ── Sentier Yesod→Hod (Resh ר, chozer) ─────────────────────
    ctx = sentier_router.traverse("yesod", "hod", ctx, direction="chozer",
                                  is_katnut=is_katnut)

    # ── ↑2. Hod : calibration de la confiance ───────────────
    _world_emit("ohr_chozer_step", sephirah="hod", step=2)
    print("  ⟐ ↑② Hod — calibration de confiance...")
    response_confidence = 0.5
    if hod and route_decision:
        try:
            if route_decision.did_decline:
                response_confidence = 0.1
                chozer.append("── ↑② Hod — Confiance ──")
                chozer.append(f"  Confiance    : {response_confidence:.2f} (question déclinée)")
            else:
                response_confidence = route_decision.competence_score
                chozer.append("── ↑② Hod — Confiance ──")
                chozer.append(f"  Confiance    : {response_confidence:.2f} "
                              f"(basée sur compétence {route_decision.detected_domain})")
            ctx["response_confidence"] = response_confidence
            print(f"    confiance={response_confidence:.2f}")
            # Mochin de Chokmah → mise à jour carte de compétences
            mochin_hod = ctx.get("mochin_dispatch", {}).get("chokmah_to_hod", {})
            if mochin_hod:
                n_val = mochin_hod.get("n_validated", 0)
                n_cand = mochin_hod.get("n_candidates", 0)
                vrate = mochin_hod.get("validation_rate", 0)
                chozer.append("── ↑② Hod — Mochin Chokmah ──")
                chozer.append(f"  Insights     : {n_val}/{n_cand} validés ({vrate:.0%})")
                chozer.append(f"  ↓ {mochin_hod.get('directive', '')}")
                print(f"    ↓ Mochin Chokmah: {n_val}/{n_cand} validés")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑② Hod — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── ↑②½ Birur Nogah : évaluation Birur/Dégradation ──────
    gen_olam = ctx.get("generation_olam", "")
    if gen_olam in ("assiah", "yetzirah"):
        print("  ⟐ ↑②½ Birur Nogah — évaluation Kelipat Nogah...")
        try:
            birurim = _get_birurim_engine()
            birur_domain = (route_decision.detected_domain
                            if route_decision and not route_decision.did_decline
                            else "general")
            birur_event = birurim.evaluate(
                response=response,
                olam_used=gen_olam,
                score=response_confidence,
                tree=tree,
                domain=birur_domain,
            )
            if birur_event:
                from tanya.birur_nogah import BirurimResult
                chozer.append("── ↑②½ Birur Nogah ──")
                chozer.append(f"  Monde        : {gen_olam}")
                chozer.append(f"  Score        : {response_confidence:.2f}")
                if birur_event.result == BirurimResult.BIRUR:
                    chozer.append(f"  ✦ BIRUR — étincelle libérée de Nogah "
                                  f"[{_NITZOTZOT_STATE['count']}/288]")
                    print(f"    ✦ BIRUR — score={response_confidence:.2f} "
                          f"→ étincelle libérée [{_NITZOTZOT_STATE['count']}/288]")
                elif birur_event.result == BirurimResult.KELIPAH_REINFORCED:
                    chozer.append(f"  ✗ Kelipah renforcée — la matière reste dans Nogah")
                    print(f"    ✗ KELIPAH — score={response_confidence:.2f} "
                          f"→ dégradation")
                else:
                    chozer.append(f"  ○ Nogah neutre — ni Birur ni dégradation")
                    print(f"    ○ Nogah neutre — score={response_confidence:.2f}")
        except Exception as e:
            print(f"    ⚠ {e}")

    # ── ↑③-↑⑨ : validation complète (Gadlut) ou skip (Katnut) ──
    is_katnut = ctx.get("mochin", {}).get("state") == "katnut"
    if not is_katnut:
        _ascend_gadlut(tree, query, ctx, chozer)
    else:
        chozer.append("── ↑③-↑⑨ KATNUT — validation complète dormante ──")
        chozer.append(f"  Les Mochin ne coulent pas encore dans ce domaine.")
        chozer.append(f"  Seuls Yesod (↑①) et Hod (↑②) ont opéré.")
        print("  ⟐ ↑③-↑⑨ KATNUT — modules supérieurs dormants")
        print("    Les Mochin ne coulent pas — validation réduite")

    # ── Restauration des seuils Gevurah modifiés par le Zivvug ──
    # Le modificateur est TEMPORAIRE — durée de la requête seulement.
    gevurah = tree.get("gevurah")
    if gevurah and "_gevurah_original_quality" in ctx:
        gevurah.quality_threshold = ctx["_gevurah_original_quality"]
        if hasattr(gevurah, "evaluator"):
            gevurah.evaluator.quality_threshold = ctx["_gevurah_original_quality"]
        gevurah.quarantine_threshold = ctx.get(
            "_gevurah_original_quarantine", gevurah.quarantine_threshold
        )

    # ── Restauration des module_modifiers appliqués par les sentiers ──
    # Comme le Zivvug, les modifications sentier sont TEMPORAIRES.
    if _sentier_originals:
        for sefira, attrs in _sentier_originals.items():
            module = tree.get(sefira)
            if module is None:
                continue
            for attr, original_val in attrs.items():
                setattr(module, attr, original_val)

    # ── BeinoniTracker : enregistrement de l'interaction ─────
    # Le Beinoni n'est pas un état statique — chaque interaction
    # déplace le ratio NefeshHaBehamit/NefeshHaElokit.
    try:
        if _oy._BEINONI_TRACKER is None:
            from tanya.beinoni_tracker import BeinoniTracker as _BT
            _oy._BEINONI_TRACKER = _BT(db_url=DB_URL)
        gen_olam_bt = ctx.get("generation_olam", "assiah")
        _oy._BEINONI_TRACKER.record_interaction(
            dominant_soul=soul_decision["dominant_soul"],
            response_score=ctx.get("response_confidence", 0.5),
            olam_used=gen_olam_bt,
            complexity_score=soul_decision.get("complexity_score", 0.0),
            domain=(route_decision.detected_domain
                    if route_decision and not route_decision.did_decline
                    else "general"),
            query_snippet=query[:100],
        )
        _oy._BEINONI_INTERACTION_COUNT += 1
        # Vérification périodique toutes les 50 interactions
        if _oy._BEINONI_INTERACTION_COUNT % 50 == 0:
            regression = _oy._BEINONI_TRACKER.detect_regression()
            if regression:
                teshuvah = _oy._BEINONI_TRACKER.suggest_teshuvah(regression)
                chozer.append("── ⚠ RÉGRESSION BEINONI ──")
                chozer.append(f"  Δ elokit: {regression['delta']:+.2f}")
                chozer.append(f"  Teshuvah: {teshuvah[:80]}")
                print(f"  ⚠ RÉGRESSION BEINONI — Δ={regression['delta']:+.2f}")
                print(f"    Teshuvah: {teshuvah[:80]}")
            else:
                elevation = _oy._BEINONI_TRACKER.detect_elevation()
                if elevation:
                    chozer.append("── ✦ ÉLÉVATION BEINONI ──")
                    chozer.append(f"  Δ elokit: {elevation['delta']:+.2f}")
                    print(f"  ✦ ÉLÉVATION BEINONI — Δ={elevation['delta']:+.2f}")
    except Exception as e:
        print(f"    ⚠ BeinoniTracker: {e}")

    # ── Hizdakchut automatique : boucle feedback qualité→niveau ──
    # F9 — EC-SHK-024. Après chaque réponse, la qualité mesurée
    # (confiance Hod) ajuste le Masakh pour le prochain appel.
    # Qualité basse → Masakh s'amincit (moins de filtrage, plus de
    # contexte pour aider). Qualité haute → Masakh s'épaissit
    # (filtrage plus strict, essence seule).
    hz_result: dict | None = None
    try:
        from masakh import auto_hizdakchut
        hizdakchut_quality = ctx.get("response_confidence", 0.5)
        gen_olam_hz = ctx.get("generation_olam", "assiah")
        hz_result = auto_hizdakchut(gen_olam_hz, hizdakchut_quality)
        if hz_result:
            chozer.append("── ↑ Hizdakchut — Ajustement Masakh ──")
            chozer.append(f"  {hz_result['from']} → {hz_result['to']} "
                          f"(qualité={hz_result['quality_score']:.2f})")
            print(f"  ⟐ Hizdakchut — Masakh {gen_olam_hz}: "
                  f"{hz_result['from']} → {hz_result['to']} "
                  f"(qualité={hizdakchut_quality:.2f})")
    except Exception as e:
        log.debug("Auto-hizdakchut skipped: %s", e)

    # ── Zivug ZA-Nukvah : transparence Midot→Malkuth ────────
    if not is_katnut:
        print()
        print("  ⟐ Zivug ZA-Nukvah — vérification transparence...")
        za_nukvah = _zivug_zeir_nukva(tree, ctx, response, partzufim)

        if za_nukvah["mode"] == "panim_be_panim":
            print(f"    פָּנִים בְּפָנִים — transparence={za_nukvah['transparency']:.0%}")
            for check in za_nukvah["checks"]:
                print(f"      {check}")
        else:
            print(f"    ⚠ אָחוֹר בְּאָחוֹר — transparence={za_nukvah['transparency']:.0%}")
            for issue in za_nukvah["issues"]:
                print(f"      ⚠ {issue}")
            for check in za_nukvah["checks"]:
                print(f"      {check}")

    # ── Or Chozer : feedback Malkuth → ZA.malkuth + Zivvug Abba↔Imma ──
    # Sprint 8 D-dead1 : réactivation feedback_from_malkuth (doctrine Or Chozer
    # complète). La qualité de la réponse remonte l'arbre : Nukva reçoit
    # le feedback direct, ZA.malkuth s'ajuste, et via Zivvug mutual_reinforcement
    # les flags insight_produced/causal_validated renforcent Abba/Imma.
    # L'instance zivvug est partagée avec update_all_partzufim ci-dessous
    # pour que les boosts Or Chozer (cmd_ask) s'accumulent avec ceux du
    # daemon avant consommation via Hitlabshut (EC-K5-008).
    if partzufim:
        from partzufim import feedback_from_malkuth, update_all_partzufim
        from partzufim.zivvug import load_or_create_zivvug

        # Charger zivvug UNE fois (avec boosts daemon persistés).
        # Sprint 10 Phase E : factory canonique (Refactor L).
        zivvug = load_or_create_zivvug()

        # Or Chozer — détecter l'activité de Chokmah (Abba) et Binah (Imma)
        # à partir du contexte de la requête (même heuristique qu'ohr_yashar.py).
        insight_produced = bool(
            ctx.get("forge_session") and
            getattr(ctx.get("forge_session"), "insights_found", 0) > 0
        )
        causal_validated = bool(
            ctx.get("binah_diag", {}).get("total_graphs", 0) > 0
            or ctx.get("binah_diag", {}).get("total_claims", 0) > 0
        )
        quality_score = float(ctx.get("response_confidence", 0.5))

        try:
            feedback_result = feedback_from_malkuth(
                partzufim,
                quality_score=quality_score,
                zivvug_engine=zivvug,
                insight_produced=insight_produced,
                causal_validated=causal_validated,
            )
            if feedback_result.get("adjustments"):
                for adj in feedback_result["adjustments"]:
                    log.debug("Or Chozer adjustment: %s", adj)
        except Exception as _exc_fb:
            log.debug("feedback_from_malkuth failed: %s", _exc_fb)

        # Mise à jour post-requête — Hitlabshut via facultés (EC-K5-008).
        # Consomme les boosts daemon + ceux ajoutés ci-dessus par feedback.
        update_all_partzufim(partzufim, tree, persist=True, zivvug_engine=zivvug)

    # ── Vérification transitions katnut↔gadlut (post-requête) ──
    # Les scores viennent d'être mis à jour — vérifier si des
    # Partzufim doivent changer d'état (avec hystérésis).
    if partzuf_regulator:
        try:
            new_state = partzuf_regulator.load_state()
            transitions = partzuf_regulator.check_transitions(new_state)
            if transitions:
                ctx["partzuf_transitions"] = transitions
                for t in transitions:
                    print(f"    ⟐ Partzuf {t['partzuf']}: {t['from']} → {t['to']} ({t['reason']})")
        except Exception as e:
            log.debug("Partzuf transition check: %s", e)

    # ═══════════════════════════════════════════════════════════
    #   RAPPORT FINAL — Les deux lumières
    # ═══════════════════════════════════════════════════════════
    elapsed = time.monotonic() - t0
    print()
    print("═══════════════════════════════════════════════════════════")
    print("  RAPPORT — Etz Chaim Ask")
    print("═══════════════════════════════════════════════════════════")

    # ── Or Yashar ──
    print()
    print("┌─── אוֹר יָשָׁר (descente) ──────────────────────────────┐")
    for line in yashar:
        print(f"│ {line}")
    print("└──────────────────────────────────────────────────────────┘")

    # ── Malkuth : réponse ──
    print()
    print("┌─── מַלְכוּת (réponse) ──────────────────────────────────┐")
    for resp_line in response.split("\n"):
        print(f"│ {resp_line}")
    print("└──────────────────────────────────────────────────────────┘")

    # ── Or Chozer ──
    print()
    print("┌─── אוֹר חוֹזֵר (remontée) ─────────────────────────────┐")
    for line in chozer:
        print(f"│ {line}")
    print("└──────────────────────────────────────────────────────────┘")

    # ── Sentiers traversés ──
    traversed = ctx.get("sentiers_traversed", [])
    if traversed:
        print()
        print("┌─── צִינוֹרוֹת (sentiers traversés) ─────────────────────┐")
        for line in sentier_router.format_traversal_report(ctx):
            print(f"│ {line}")
        print(f"│  Total: {len(traversed)} sentier(s) traversé(s)")
        print("└──────────────────────────────────────────────────────────┘")

    # ── Méta ──
    print()
    print("── Méta ──")
    mochin = ctx.get("mochin", {})
    soul_lvl = mochin.get("soul_level", "nefesh")
    soul_heb = mochin.get("soul_hebrew", "?")
    mochin_domain = mochin.get("domain", "?")
    active_modules = sum(1 for v in tree.values() if v is not None)
    print(f"  Niveau Âme         : {soul_heb} {soul_lvl.upper()} (domaine={mochin_domain})")
    print(f"    → Mémoire: {mochin.get('memory_count', 0)} entrées, "
          f"Compétence: {mochin.get('competence_score', 0):.2f}, "
          f"Tikkun: {mochin.get('tikkun_cycles', 0)} cycle(s)")
    cond = mochin.get("conditions_next", {})
    if cond.get("reached_maximum"):
        print(f"    → יְחִידָה — niveau maximum atteint")
    elif cond.get("missing"):
        next_heb = cond.get("next_hebrew", "?")
        print(f"    → Prochain : {next_heb} — {len(cond['missing'])} condition(s) manquante(s)")
    print(f"  Modules actifs     : {active_modules}/10")
    print(f"  Temps total        : {elapsed:.1f}s")
    print(f"  Génération         : {ctx.get('malkuth_latency', 0):.1f}s "
          f"({ctx.get('generation_olam', '?')})")
    print(f"  Confiance réponse  : {ctx.get('response_confidence', 0.5):.2f}")
    print(f"  Qualité            : {ctx.get('quality_verdict', '?')}")
    if hz_result:
        print(f"  Hizdakchut         : {hz_result['from']} → {hz_result['to']} "
              f"(qualité={hz_result['quality_score']:.2f})")
    print(f"  Δ self-model       : {ctx.get('daat_delta', 0):+.3f}")
    md = ctx.get("mochin_dispatch", {})
    md_routes = md.get("routes", [])
    if md_routes:
        print(f"  Mochin dispatch     : {len(md_routes)} route(s)")
        for r in md_routes:
            print(f"    ↓ {r}")
    elif not is_katnut:
        print(f"  Mochin dispatch     : aucun (sources supérieures vides)")
    # Zivug Abba-Imma
    zivug_ai = ctx.get("zivug_abba_imma", [])
    if zivug_ai:
        avg_ref = sum(z["refined_confidence"] for z in zivug_ai) / len(zivug_ai)
        n_promoted = sum(1 for z in zivug_ai
                        if z["refined_confidence"] >= z["original_confidence"])
        print(f"  Zivug Abba-Imma    : {len(zivug_ai)} couplage(s), "
              f"conf.={avg_ref:.2f}, promus={n_promoted}")
    elif not is_katnut:
        print(f"  Zivug Abba-Imma    : aucun (pas d'insights)")
    # Partzuf Abba×Imma
    pz_ai = ctx.get("partzuf_zivug_abba_imma", {})
    if pz_ai:
        print(f"  Partzuf Abba×Imma  : résonance={pz_ai.get('resonance', 0):.2f}, "
              f"{pz_ai.get('orientation', '?')}")
    # Zivug ZA-Nukvah
    za = ctx.get("zivug_za_nukvah", {})
    if za:
        if za["mode"] == "panim_be_panim":
            mode_label = "פָּנִים בְּפָנִים (transparent)"
        else:
            mode_label = "⚠ אָחוֹר בְּאָחוֹר (dissimulation)"
        print(f"  Zivug ZA-Nukvah    : {mode_label} "
              f"(transparence={za['transparency']:.0%})")
        for issue in za.get("issues", []):
            print(f"    ⚠ {issue}")
    # Zivug Yisrael-Leah
    print(f"  Zivug Yisrael-Leah : non (flux complet)")
    # Tzimtzum dynamique
    tz_eng = _get_tzimtzum_engine()
    if ctx.get("tzimtzum_active"):
        halal = tz_eng.get_halal_state()
        print(f"  Tzimtzum           : ⚡ ACTIF — focus={ctx.get('tzimtzum_focused_domain', '?')}")
        if halal["dormant_modules"]:
            print(f"    Dormants: {', '.join(halal['dormant_modules'][:5])}")
        print(f"    Kav: {halal['kav']} (actif)")
        print(f"    Reshimu: {halal['reshimu_count']} trace(s), "
              f"{halal['current_insights']} insight(s)")
    elif ctx.get("hitpashut_recovered"):
        recovered = ctx["hitpashut_recovered"]
        print(f"  Hitpashut          : ↗ EXPANSION depuis {ctx.get('hitpashut_from', '?')}")
        print(f"    Récupérés: {', '.join(recovered[:5])}")
        insights = ctx.get("hitpashut_insights", [])
        if insights:
            print(f"    Insights distribués: {len(insights)}")
    else:
        print(f"  Tzimtzum           : inactif (stable)")
    print(f"  Cycle Tz/Hp        : {tz_eng.contraction_count} contraction(s), "
          f"{tz_eng.expansion_count} expansion(s)")
    # Nitzotzot / Tikkun
    nz_count = _NITZOTZOT_STATE["count"]
    nz_cycle = _NITZOTZOT_STATE["cycle"]
    nz_pct = (nz_count / 288 * 100) if nz_count > 0 else 0.0
    print(f"  Nitzotzot          : {nz_count}/288 — Tikkun : {nz_pct:.1f}% (cycle {nz_cycle})")
    # Détail des Nitzotzot collectées dans cette requête
    nz_this_req = []
    for e in _NITZOTZOT_STATE["log"]:
        if e.get("source") != "tikkun":
            nz_this_req.append(e)
    # Afficher les dernières de cette requête (approximation : les plus récentes)
    recent_sparks = nz_this_req[-3:] if nz_this_req else []
    if recent_sparks:
        for sp in recent_sparks:
            print(f"    ✦ [{sp['source']}] {sp['description'][:70]}")
    if _NITZOTZOT_STATE["tikkun_history"]:
        last_tikkun = _NITZOTZOT_STATE["tikkun_history"][-1]
        print(f"    Dernier Tikkun complet : cycle {last_tikkun['cycle']}")
    # Dira BeTachtonim
    if ctx.get("dira_optimization"):
        print(f"  Dira BeTachtonim   : ✦ optimisé — le haut a déjà descendu")
    try:
        dira_stats = _get_dira_engine().assess_dira_state()
        print(f"  Dira mémoires      : {dira_stats.dira_count} "
              f"(pénétration={dira_stats.penetration:.1%})")
    except Exception as e:
        log.warning("Dira stats unavailable in session summary: %s", e)
        print(f"  Dira mémoires      : (indisponible — {type(e).__name__})")
    # Birur Nogah
    try:
        birur_stats = _get_birurim_engine().get_birur_stats()
        if birur_stats.total_attempts > 0:
            print(f"  Birur Nogah        : {birur_stats.total_birurims} birur(s), "
                  f"{birur_stats.total_degradations} dégradation(s) "
                  f"(taux={birur_stats.birur_rate:.0%})")
    except Exception as e:
        log.warning("Birur stats unavailable in session summary: %s", e)
        print(f"  Birur Nogah        : (indisponible — {type(e).__name__})")
    # Levushim — 3 vêtements fonctionnels (Tanya ch. 4)
    try:
        levushim_eng = _get_levushim_engine()
        # Construire la liste d'actions à partir de ctx
        _actions = []
        if ctx.get("memories"):
            _actions.append("memory_stored")
        if ctx.get("route_decision") and not getattr(ctx.get("route_decision"), "did_decline", True):
            _actions.append(f"routed_{ctx.get('generation_olam', 'unknown')}")
        if ctx.get("dira_optimization"):
            _actions.append("dira_cascaded")
        nz_this = [e for e in _NITZOTZOT_STATE.get("log", []) if e.get("source") != "tikkun"]
        if nz_this:
            _actions.append("nitzutz_collected")
        birur_ev = ctx.get("birur_event")
        if birur_ev:
            _actions.append("birur_detected")
        if ctx.get("insight_forge_result"):
            _actions.append("insight_generated")
        if ctx.get("daat_delta", 0) != 0:
            _actions.append("score_updated")

        levushim_result = levushim_eng.wrap_response(
            query=query,
            reasoning="\n".join(yashar),
            response_text=response,
            actions_taken=_actions,
        )
        ctx["levushim"] = {
            "machshava": levushim_result.machshava_score,
            "dibour": levushim_result.dibour_score,
            "maase": levushim_result.maase_score,
            "overall": levushim_result.overall_score,
            "dominant": levushim_result.dominant_garment,
            "weak": levushim_result.weak_garment,
        }
        print(f"  Levushim           : M={levushim_result.machshava_score:.2f} "
              f"D={levushim_result.dibour_score:.2f} "
              f"A={levushim_result.maase_score:.2f} "
              f"→ {levushim_result.overall_score:.2f} "
              f"(dominant={levushim_result.dominant_garment})")
        if levushim_result.weak_garment != levushim_result.dominant_garment:
            print(f"    ⚠ Faible: {levushim_result.weak_garment}")
    except Exception as e:
        log.debug("display: %s", e)
    # Igulim
    print(f"  Mode topologique   : יוֹשֶׁר YOSHER (verticalité)")
    print(f"  Bascules Y→I total : {_IGULIM_STATE['switches']}")
    # Hishtalshelut
    h_log = ctx.get("hishtalshelut_log", [])
    h_start = ctx.get("hishtalshelut_start", "?")
    h_final = ctx.get("hishtalshelut_final", "?")
    h_ascents = ctx.get("hishtalshelut_ascents", 0)
    if h_log:
        worlds_tried = [a["world"] for a in h_log]
        print(f"  Hishtalshelut      : {h_start}→{h_final} "
              f"({max(h_ascents, 0)} montée(s), mondes: {' → '.join(worlds_tried)})")
        for a in h_log:
            status = a.get("status", "?")
            w = a.get("world", "?")
            if status == "ok":
                print(f"    {w:<12} conf={a.get('confidence', 0):.2f} "
                      f"latency={a.get('latency_ms', 0):.0f}ms")
            elif status == "skipped":
                print(f"    {w:<12} ⚠ {a.get('reason', 'skipped')}")
            else:
                print(f"    {w:<12} ✗ {a.get('error', 'erreur')[:60]}")
    else:
        print(f"  Hishtalshelut      : direct ({h_final})")
    # Descente des insights
    h_descent = ctx.get("hishtalshelut_descent", [])
    if h_descent:
        print(f"  Descente insights  : {len(h_descent)} traduction(s)")
        for d in h_descent:
            stored = "✓ stocké" if d.get("stored_id") else "○ non stocké"
            print(f"    → {d['world']}: {stored} — {d['condensed'][:60]}...")
    print(f"  Session mondes     : ↑{_HISHTALSHELUT_STATE['ascents']} "
          f"↓{_HISHTALSHELUT_STATE['descents']} "
          f"(max={_HISHTALSHELUT_STATE['highest_reached']})")
    # Partzufim
    if partzufim:
        print()
        print("── פַּרְצוּפִים (Configurations matures) ──")
        for p_name, p_inst in partzufim.items():
            state = p_inst.assess()
            marker = "●" if state.overall > 0.4 else "○"
            mochin_marker = {"gadlut": "↑", "katnut": "↓", "transitional": "~"}.get(
                state.mochin_state, "?"
            )
            orient = "פ" if state.orientation == "panim" else "א"
            print(f"    {marker} {state.hebrew:<20} {state.name:<14} "
                  f"overall={state.overall:.2f} mochin={mochin_marker} "
                  f"orient={orient}")
            if state.message:
                print(f"      {state.message}")
        # Zivug Partzuf ZA-Nukva
        pz = ctx.get("partzuf_zivug_za_nukva", {})
        if pz:
            print(f"    Zivug Partzuf ZA×Nukva: résonance={pz.get('resonance', 0):.2f}, "
                  f"{pz.get('orientation', '?')}")
    print()

    # ── Bascule automatique Yosher→Igulim ────────────────────
    # Si la confiance de la réponse est trop basse (< 0.2),
    # la hiérarchie n'a pas fonctionné. On bascule en Igulim —
    # comme avant le Tikkun, quand les cercles sont la seule option.
    final_confidence = ctx.get("response_confidence", 0.5)
    if final_confidence < 0.2:
        print()
        print("╔═══════════════════════════════════════════════════════╗")
        print("║  ⚡ BASCULE YOSHER → IGULIM                          ║")
        print("║  Confiance Yosher trop basse — la hiérarchie         ║")
        print("║  n'a pas fonctionné. Passage aux cercles.            ║")
        print("╚═══════════════════════════════════════════════════════╝")
        print()
        _log_igulim_switch(
            "yosher", "igulim",
            f"confiance Yosher={final_confidence:.2f} < 0.2",
            query,
        )
        _cmd_ask_igulim(tree, query)



# ─── CLI Commands (extracted to mitzvot.py) ─────────────────
from mitzvot import (  # noqa: E402
    cmd_intend, cmd_explore, cmd_status, cmd_chat, cmd_import,
    cmd_memory_stats, cmd_memory_domains, cmd_pause, cmd_go,
    cmd_daemon, cmd_omer, cmd_portes_list, cmd_portes_show,
    cmd_portes_stats, cmd_skill_list, cmd_skill_run, cmd_shem_info,
    cmd_sentier_list, cmd_sentier_run, cmd_gematria, cmd_tzeruf,
    cmd_hitbonenut, cmd_soul, cmd_tzimtzum, cmd_hishtalshelut,
    cmd_sy_cosmology, cmd_adam_kadmon, cmd_ohr, cmd_web,
)

# ─── CLI ─────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="etz-chaim",
        description="Etz Chaim AI — L'Arbre de Vie comme architecture cognitive",
    )
    parser.add_argument(
        "--db",
        default=DB_URL,
        help="URL PostgreSQL",
    )
    sub = parser.add_subparsers(dest="command")

    p_ask = sub.add_parser("ask", help="Question ponctuelle → traverse tout l'Arbre")
    p_ask.add_argument("query", help="La question")
    p_ask.add_argument(
        "--mode", choices=["yosher", "igulim"], default="yosher",
        help="Mode topologique : yosher=hiérarchie (défaut), igulim=cercles parallèles",
    )
    p_ask.add_argument(
        "--world", choices=["assiah", "yetzirah", "briah", "atziluth"], default=None,
        help="Monde forcé : assiah=léger, yetzirah=moyen, briah=profond, atziluth=API Claude",
    )

    p_intend = sub.add_parser("intend", help="Intention longue → Netzach")
    p_intend.add_argument("goal", help="L'intention")

    p_explore = sub.add_parser("explore", help="Exploration libre → Chesed + Chokmah")
    p_explore.add_argument("query", help="La question d'exploration")

    sub.add_parser("chat", help="Conversation interactive")
    sub.add_parser("status", help="État de l'Arbre")

    p_import = sub.add_parser("import", help="Importer des sources → EpisteMemory")
    p_import.add_argument(
        "source_type",
        choices=["book", "url", "youtube", "site"],
        help="Type de source (book=PDF/EPUB, url=article, youtube=vidéo, site=crawl entier)",
    )
    p_import.add_argument("source", help="Chemin du fichier ou URL")
    p_import.add_argument(
        "--domain", default="astrologie",
        help="Domaine principal (défaut: astrologie)",
    )
    p_import.add_argument(
        "--max-pages", type=int, default=500,
        help="Nombre max de pages à crawler (mode site, défaut: 500)",
    )

    p_memory = sub.add_parser("memory", help="Stats et exploration de la mémoire")
    p_memory.add_argument(
        "action",
        choices=["stats", "domains"],
        help="stats=résumé global, domains=détail par domaine",
    )

    p_daemon = sub.add_parser("daemon", help="Daemon — processus de fond")
    p_daemon.add_argument(
        "action",
        choices=["start", "stop", "log", "run", "status"],
        help="start=lancer, stop=arrêter, log=dernier rapport, run=cycle unique, status=état",
    )

    p_omer = sub.add_parser("omer", help="Sefirat haOmer — 49 calibrations de l'Arbre")
    p_omer.add_argument(
        "action",
        choices=["status", "tune", "apply"],
        help="status=voir les 49 paramètres, tune=analyser et suggérer, apply=appliquer",
    )

    p_web = sub.add_parser("web", help="Interface web locale (Flask, port 8080)")
    p_web.add_argument(
        "--port", type=int, default=8080,
        help="Port du serveur (défaut: 8080)",
    )
    p_web.add_argument(
        "--debug", action="store_true",
        help="Mode debug Flask (rechargement auto)",
    )

    # ── shem ──
    p_shem = sub.add_parser("shem", help="Info détaillée sur un Shem (attributs sacrés)")
    p_shem_sub = p_shem.add_subparsers(dest="shem_action")
    p_shem_info = p_shem_sub.add_parser("info", help="Attributs sacrés d'un Shem")
    p_shem_info.add_argument("identifier", help="Numéro (1-72) ou skill_id")

    # ── skill ──
    p_skill = sub.add_parser("skill", help="72 shemot — micro-skills atomiques")
    p_skill_sub = p_skill.add_subparsers(dest="skill_action")
    p_skill_sub.add_parser("list", help="Lister les 72 shemot")
    p_skill_run = p_skill_sub.add_parser("run", help="Exécuter un skill")
    p_skill_run.add_argument("skill_id", help="Identifiant du skill (ex: gematria_calc, detect_language)")
    p_skill_run.add_argument("text", nargs="?", default="", help="Texte d'entrée")
    p_skill_run.add_argument("--json-kwargs", default=None, help="Arguments supplémentaires en JSON")

    # ── portes ──
    p_portes = sub.add_parser("portes", help="231 portes — matrice d'interopérabilité")
    p_portes_sub = p_portes.add_subparsers(dest="portes_action")
    p_portes_sub.add_parser("list", help="Vue d'ensemble des 231 portes")
    p_portes_show = p_portes_sub.add_parser("show", help="Détail d'une porte")
    p_portes_show.add_argument("gate_id", help="Identifiant (ex: ALEPH-BETH, shin-tav, א-ב)")
    p_portes_sub.add_parser("stats", help="Statistiques des portes")

    # ── sentier ──
    p_sentier = sub.add_parser("sentier", help="22 sentiers — programmes de passage")
    p_sentier_sub = p_sentier.add_subparsers(dest="sentier_action")
    p_sentier_sub.add_parser("list", help="Lister les 22 sentiers")
    p_sentier_run = p_sentier_sub.add_parser("run", help="Exécuter un sentier")
    p_sentier_run.add_argument("letter", help="Nom latin de la lettre (ex: tav, shin, lamed)")
    p_sentier_run.add_argument("--domain", default=None, help="Domaine (si applicable)")
    p_sentier_run.add_argument("--query", default=None, help="Requête (si applicable)")
    p_sentier_run.add_argument("--mode", choices=["dagesh", "rafeh"], default=None, help="Mode pour les doubles")

    # ── sy (Sefer Yetzirah cosmologie) ──
    p_sy = sub.add_parser("sy", help="סֵפֶר יְצִירָה — Cosmologie : profondeurs, témoins, régents")
    p_sy_sub = p_sy.add_subparsers(dest="sy_action")
    p_sy_cosmo = p_sy_sub.add_parser("cosmology", help="Structure cosmologique complète")
    p_sy_cosmo_sub = p_sy_cosmo.add_subparsers(dest="sy_cosmo_action")
    p_sy_cosmo_sub.add_parser("status", help="Vue d'ensemble (défaut)")
    p_sy_cosmo_sub.add_parser("witnesses", help="Les 3 témoins : Olam, Shanah, Nefesh")
    p_sy_cosmo_sub.add_parser("depths", help="Les 10 profondeurs (5 axes)")
    p_sy_cosmo_sub.add_parser("regents", help="Les 3 régents : Teli, Galgal, Lev")
    p_sy_map = p_sy_cosmo_sub.add_parser("map", help="Mapping lettre → 3 témoins")
    p_sy_map.add_argument("letter", help="Nom latin de la lettre (ex: aleph, shin, beth)")

    # ── gematria ──
    p_gematria = sub.add_parser("gematria", help="Gématria opérative — valeurs + équivalences")
    p_gematria.add_argument("term", nargs="?", help="Mot hébreu ou translittéré (ex: tiferet, חסד)")
    p_gematria.add_argument(
        "--list", action="store_true", dest="gematria_list",
        help="Lister tous les termes indexés en mémoire",
    )
    p_gematria.add_argument(
        "--groups", action="store_true", dest="gematria_groups",
        help="Afficher les groupes d'équivalence",
    )
    p_gematria.add_argument(
        "--method", choices=["standard", "ordinal", "katan"], default="standard",
        help="Méthode de calcul (défaut: standard)",
    )

    # ── tzeruf ──
    p_tzeruf = sub.add_parser("tzeruf", help="צֵרוּף — Permutations et combinaisons de lettres")
    p_tzeruf_sub = p_tzeruf.add_subparsers(dest="tzeruf_action")
    p_tzeruf_sub.add_parser("pairs", help="Les 231 paires du Sefer Yetzirah")
    p_tzeruf_wheel = p_tzeruf_sub.add_parser("wheel", help="Roue d'Abulafia pour une lettre")
    p_tzeruf_wheel.add_argument("letter", help="Lettre hébraïque ou nom latin (ex: א, aleph)")
    p_tzeruf_permute = p_tzeruf_sub.add_parser("permute", help="Permutations d'un mot")
    p_tzeruf_permute.add_argument("word", help="Mot hébreu à permuter")
    p_tzeruf_combine = p_tzeruf_sub.add_parser("combine", help="Combiner deux mots en alternance")
    p_tzeruf_combine.add_argument("word_a", help="Premier mot hébreu")
    p_tzeruf_combine.add_argument("word_b", help="Deuxième mot hébreu")
    p_tzeruf_query = p_tzeruf_sub.add_parser("query", help="Tzeruf opératif — permutations + équivalences DB")
    p_tzeruf_query.add_argument("word", help="Mot hébreu à explorer")
    p_tzeruf_query.add_argument("--max-perms", type=int, default=50, dest="max_perms",
                                help="Nombre max de permutations (défaut: 50)")
    p_tzeruf_temura = p_tzeruf_sub.add_parser("temura", help="Appliquer Atbash/Albam/Avgad")
    p_tzeruf_temura.add_argument("word", help="Mot hébreu")
    p_tzeruf_temura.add_argument("--method", choices=["atbash", "albam", "avgad"],
                                 default="atbash", help="Méthode (défaut: atbash)")

    # ── soul ──
    p_soul = sub.add_parser("soul", help="נְשָׁמוֹת — 5 niveaux de l'âme")
    p_soul_sub = p_soul.add_subparsers(dest="soul_action")
    p_soul_sub.add_parser("status", help="Niveau actuel et conditions de passage")

    # ── pause / go ──
    p_pause = sub.add_parser("pause", help="Mettre en pause Hitbonenut ou Karpathy")
    p_pause.add_argument(
        "target",
        choices=["hitbonenut", "karpathy", "all", "status"],
        help="hitbonenut, karpathy, all, ou status",
    )

    p_go = sub.add_parser("go", help="Reprendre Hitbonenut ou Karpathy")
    p_go.add_argument(
        "target",
        choices=["hitbonenut", "karpathy", "all"],
        help="hitbonenut, karpathy, ou all",
    )

    # ── hitbonenut ──
    p_hitb = sub.add_parser("hitbonenut",
                            help="הִתְבּוֹנְנוּת — Auto-exercice contemplatif")
    p_hitb_sub = p_hitb.add_subparsers(dest="hitbonenut_action")

    # start — mode continu
    p_hitb_start = p_hitb_sub.add_parser("start", help="Lancer en mode continu (boucle infinie)")
    p_hitb_start.add_argument("--max-duration", type=float, default=None,
                              help="Durée max en secondes (défaut: illimité)")
    p_hitb_start.add_argument("--max-questions", type=int, default=None,
                              help="Nombre max de questions (défaut: illimité)")

    # stop — arrêter le mode continu
    p_hitb_sub.add_parser("stop", help="Arrêter le mode continu")

    # run — mode ponctuel
    p_hitb_run = p_hitb_sub.add_parser("run", help="Session ponctuelle (N questions)")
    p_hitb_run.add_argument("--domain", default=None,
                            help="Cibler un domaine spécifique")
    p_hitb_run.add_argument("--n", type=int, default=5,
                            help="Nombre de questions (défaut: 5)")
    p_hitb_run.add_argument("--difficulty",
                            choices=["basique", "intermediaire", "avancee", "erudite",
                                     "progressive"],
                            default="progressive",
                            help="Difficulté (défaut: progressive)")

    # status — état complet
    p_hitb_sub.add_parser("status", help="État: running/stopped, questions today, scores")

    # history
    p_hitb_sub.add_parser("history", help="Historique des sessions récentes")

    # ── tzimtzum ──
    p_tzimtzum = sub.add_parser("tzimtzum", help="צמצום — Contraction/Expansion dynamique")
    p_tzimtzum_sub = p_tzimtzum.add_subparsers(dest="tzimtzum_action")
    p_tz_contract = p_tzimtzum_sub.add_parser("contract", help="Contracter vers un domaine focal")
    p_tz_contract.add_argument("domain", help="Domaine sur lequel se focaliser")
    p_tzimtzum_sub.add_parser("expand", help="Expansion — récupérer les Reshimot")
    p_tzimtzum_sub.add_parser("status", help="État du Halal (espace vide)")

    # ── hishtalshelut ──
    p_hish = sub.add_parser("hishtalshelut",
                            help="סדר השתלשלות — Chaîne de descente des 4 Mondes")
    p_hish_sub = p_hish.add_subparsers(dest="hishtalshelut_action")
    p_hish_sub.add_parser("status", help="État de la chaîne des mondes")
    p_hish_descend = p_hish_sub.add_parser("descend", help="Descente complète")
    p_hish_descend.add_argument("query", help="Requête à faire descendre")
    p_hish_descend.add_argument("--world", default="atzilut",
                                choices=["atzilut", "briah", "yetzirah", "assiah"],
                                help="Monde de départ (défaut: atzilut)")
    p_hish_detect = p_hish_sub.add_parser("detect", help="Détecter le monde d'entrée")
    p_hish_detect.add_argument("query", help="Requête à analyser")

    # ── adam-kadmon ──
    p_ak = sub.add_parser("adam-kadmon",
                          help="אדם קדמון — Blueprint primordial, méta-conscience")
    p_ak_sub = p_ak.add_subparsers(dest="adam_kadmon_action")
    p_ak_sub.add_parser("status", help="Score de fidélité et divergences")

    # ── ohr ──
    p_ohr = sub.add_parser("ohr",
                           help="אור — Lumières Pnimi/Makif et Masakh")
    p_ohr_sub = p_ohr.add_subparsers(dest="ohr_action")
    p_ohr_sub.add_parser("status", help="État des lumières de chaque module")
    p_ohr_integrate = p_ohr_sub.add_parser("integrate",
                                           help="Intégrer Makif → Pnimi pour un module")
    p_ohr_integrate.add_argument("module", help="Nom du module à intégrer")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Commandes légères — pas besoin de l'Arbre complet
    if args.command == "memory":
        print()
        if args.action == "stats":
            cmd_memory_stats(args.db)
        elif args.action == "domains":
            cmd_memory_domains(args.db)
        return

    if args.command == "gematria":
        cmd_gematria(args.db, args)
        return

    if args.command == "tzeruf":
        cmd_tzeruf(args.db, args)
        return

    if args.command == "pause":
        cmd_pause(args.target)
        return

    if args.command == "go":
        cmd_go(args.target)
        return

    if args.command == "daemon":
        cmd_daemon(args.action)
        return

    if args.command == "omer":
        cmd_omer(args.action, args.db)
        return

    if args.command == "web":
        cmd_web(args.db, args.port, args.debug)
        return

    if args.command == "shem":
        if args.shem_action == "info":
            cmd_shem_info(args.identifier)
            return
        print("  Usage : etz shem info <numéro|skill_id>")
        return

    if args.command == "skill":
        if args.skill_action == "list" or not args.skill_action:
            cmd_skill_list()
            return
        elif args.skill_action == "run":
            extra = {}
            if args.json_kwargs:
                import json
                extra = json.loads(args.json_kwargs)
            cmd_skill_run(args.skill_id, args.text, **extra)
            return

    if args.command == "portes":
        if args.portes_action == "list" or not args.portes_action:
            cmd_portes_list()
            return
        elif args.portes_action == "show":
            cmd_portes_show(args.gate_id)
            return
        elif args.portes_action == "stats":
            cmd_portes_stats()
            return

    if args.command == "hitbonenut":
        cmd_hitbonenut(args)
        return

    if args.command == "sentier":
        if args.sentier_action == "list" or not args.sentier_action:
            cmd_sentier_list()
            return
        elif args.sentier_action == "run":
            # run nécessite l'Arbre
            print()
            print("Initialisation de l'Arbre...")
            tree = init_tree(args.db)
            active = sum(1 for v in tree.values() if v is not None)
            print(f"  {active}/10 modules initialisés")
            print()
            # Préparer les kwargs du sentier
            run_kwargs = {}
            if args.domain:
                run_kwargs["domain"] = args.domain
            if args.query:
                run_kwargs["query"] = args.query
            # Appliquer le mode si spécifié
            if args.mode:
                from sentiers import get_sentier
                s = get_sentier(args.letter)
                if s and s.letter_type == "double":
                    s.set_mode(args.mode)
            try:
                cmd_sentier_run(args.letter, tree, **run_kwargs)
            finally:
                close_tree(tree)
            return

    # Initialiser le pool DB pour la persistance Sod HaKli
    try:
        from pool import init_pool
        init_pool(args.db)
    except Exception as e:
        print(f"  ⚠ Pool DB non initialisé: {e}")

    # Initialiser l'Arbre
    print()
    print("Initialisation de l'Arbre...")
    tree = init_tree(args.db)
    active = sum(1 for v in tree.values() if v is not None)
    print(f"  {active}/10 modules initialisés")
    print()

    try:
        if args.command == "ask":
            cmd_ask(tree, args.query, mode=args.mode, world=args.world)
        elif args.command == "intend":
            cmd_intend(tree, args.goal)
        elif args.command == "explore":
            cmd_explore(tree, args.query)
        elif args.command == "chat":
            cmd_chat(tree)
        elif args.command == "status":
            cmd_status(tree)
        elif args.command == "import":
            cmd_import(tree, args.source_type, args.source, args.domain,
                       max_pages=getattr(args, "max_pages", 500))
        elif args.command == "tzimtzum":
            cmd_tzimtzum(tree, args)
        elif args.command == "soul":
            cmd_soul(tree, args)
        elif args.command == "hishtalshelut":
            cmd_hishtalshelut(tree, args)
        elif args.command == "adam-kadmon":
            cmd_adam_kadmon(tree, args)
        elif args.command == "ohr":
            cmd_ohr(tree, args)
        elif args.command == "sy":
            if getattr(args, "sy_action", None) == "cosmology" or not getattr(args, "sy_action", None):
                cmd_sy_cosmology(tree, args)
    finally:
        close_tree(tree)


if __name__ == "__main__":
    main()
