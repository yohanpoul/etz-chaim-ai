"""ohr_yashar.py — אוֹר יָשָׁר : pipeline descendant Keter→Malkuth et helpers."""

from __future__ import annotations

import logging
import os
import re
import time

log = logging.getLogger("etz-malkuth")

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

# ─── État global mutable — importé depuis state.py ───────────
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

# ─── Engine singletons — lazy init ─────────────────────────────
_TZIMTZUM_ENGINE = None           # TzimtzumEngine singleton — init lazy
_NESHAMOT_ENGINE = None           # NeshamotEngine singleton — init lazy
_HISHTALSHELUT_ENGINE = None      # HishtalshelutEngine singleton — init lazy
_DUAL_SOUL_ENGINE = None          # DualSoulEngine singleton — init lazy
_DIRA_ENGINE = None               # DiraEngine singleton — init lazy
_BIRURIM_ENGINE = None            # BirurimEngine singleton — init lazy
_LEVUSHIM_ENGINE = None           # Levushim singleton — init lazy
_ATZVUT_MANAGER = None            # AtzvutManager singleton — init lazy
_BEINONI_TRACKER = None           # BeinoniTracker singleton — init lazy
_BEINONI_INTERACTION_COUNT = 0    # Compteur pour vérification périodique


# ═══════════════════════════════════════════════════════════════
#   Block A — Engine singletons + getters
# ═══════════════════════════════════════════════════════════════


def _get_tzimtzum_engine():
    """Obtenir le TzimtzumEngine singleton, branché sur _TZIMTZUM_STATE."""
    global _TZIMTZUM_ENGINE
    if _TZIMTZUM_ENGINE is None:
        from tzimtzum import TzimtzumEngine
        _TZIMTZUM_ENGINE = TzimtzumEngine(_TZIMTZUM_STATE)
    return _TZIMTZUM_ENGINE


def _detect_tzimtzum(ctx: dict) -> dict:
    """צִמְצוּם — Détecter si le système est submergé. Délègue au TzimtzumEngine."""
    return _get_tzimtzum_engine().detect_contraction(ctx)


def _apply_tzimtzum(tree: dict, ctx: dict, yashar: list) -> None:
    """Appliquer le Tzimtzum — contraction via TzimtzumEngine."""
    engine = _get_tzimtzum_engine()
    mochin = ctx.get("mochin", {})
    domain = mochin.get("domain", "general")
    engine.contract(domain, tree, ctx)
    yashar.extend(engine.format_report(ctx))


def _regulate_masakh_from_tzimtzum(tree: dict, ctx: dict) -> dict | None:
    """Réguler le Masakh selon la pression Tsimtsum — Chesed↔Gevurah.

    Le Kli (Masakh) s'ajuste dynamiquement selon la pression interne
    du système. Quand le système déborde (Chesed), le filtre s'épaissit
    (Gevurah). Quand il est trop contraint, le filtre s'amincit.

    Extrait les métriques depuis les sous-dicts peuplés par le pipeline
    Or Yashar (tiferet_diag, forge_session, binah_diag).

    Returns:
        Dict avec les détails de la régulation, ou None si pas de changement.
    """
    from masakh import Masakh

    engine = _get_tzimtzum_engine()

    # Extraire les métriques depuis les vrais sous-dicts du pipeline
    tiferet_diag = ctx.get("tiferet_diag", {})
    forge_session = ctx.get("forge_session")
    binah_diag = ctx.get("binah_diag", {})

    n_validated = 0
    n_invalidated = 0
    n_pending = 0
    if forge_session:
        validated = getattr(forge_session, "validated_insights", []) or []
        n_validated = len(validated)
        pending = getattr(forge_session, "pending", []) or []
        n_pending = len(pending)
        n_candidates = getattr(forge_session, "total_candidates", 0)
        n_invalidated = max(0, n_candidates - n_validated - n_pending)

    pressure = engine.assess_system_pressure(
        open_tensions=tiferet_diag.get("open_tensions", 0),
        resolved_tensions=tiferet_diag.get("total_syntheses", 0),
        hypotheses=binah_diag.get("total_claims", 0),
        facts=binah_diag.get("validated_claims", 0),
        insights_rejected=n_invalidated,
        insights_accepted=n_validated,
        insights_pending=n_pending,
        causal_claims_weak=binah_diag.get("weak_claims", 0),
        causal_claims_total=binah_diag.get("total_claims", 0),
    )

    # Appliquer la régulation au Masakh de chaque Olam actif.
    # NB: Masakh(olam) lit _HIZDAKCHUT_LEVELS si présent, donc la
    # régulation Tsimtsum part du niveau ajusté par hizdakchut.
    # Les deux boucles sont indépendantes et temporellement séparées :
    #   - Tsimtsum régule AVANT la génération (Or Yashar, 10⅞)
    #   - Hizdakchut ajuste APRÈS la réponse (Or Chozer, post-Hod)
    # Le résultat Tsimtsum est éphémère (pas persisté), tandis que
    # hizdakchut persiste pour le prochain appel.
    results = {}
    for olam in ("atziluth", "briah", "yetzirah", "assiah"):
        masakh = Masakh(olam)
        changed = masakh.regulate_from_pressure(pressure)
        if changed:
            results[olam] = {
                "new_level": masakh.level,
                "reason": masakh.level_changes[-1]["reason"],
            }

    if results:
        return {
            "pressure": pressure.to_dict(),
            "masakh_adjustments": results,
        }
    return None


def _detect_hitpashut(ctx: dict) -> dict:
    """הִתְפַּשְׁטוּת — Détecter expansion. Délègue au TzimtzumEngine."""
    return _get_tzimtzum_engine().detect_expansion(ctx)


def _apply_hitpashut(tree: dict, ctx: dict, chozer: list) -> None:
    """Appliquer l'Hitpashut — expansion via TzimtzumEngine."""
    engine = _get_tzimtzum_engine()
    result = engine.expand(tree, ctx)
    chozer.extend(engine.format_expansion_report(result))


def _get_dira_engine(yesod=None):
    """Obtenir le DiraEngine singleton."""
    global _DIRA_ENGINE
    if _DIRA_ENGINE is None:
        from tanya.dira_betachtonim import DiraEngine
        _DIRA_ENGINE = DiraEngine(yesod=yesod)
    elif yesod and _DIRA_ENGINE.yesod is None:
        _DIRA_ENGINE.yesod = yesod
    return _DIRA_ENGINE


def _get_birurim_engine():
    """Obtenir le BirurimEngine singleton."""
    global _BIRURIM_ENGINE
    if _BIRURIM_ENGINE is None:
        from tanya.birur_nogah import BirurimEngine
        _BIRURIM_ENGINE = BirurimEngine()
    return _BIRURIM_ENGINE


def _get_levushim_engine():
    """Obtenir le Levushim singleton."""
    global _LEVUSHIM_ENGINE
    if _LEVUSHIM_ENGINE is None:
        from tanya.levushim import Levushim
        _LEVUSHIM_ENGINE = Levushim()
    return _LEVUSHIM_ENGINE


def _get_atzvut_manager():
    """Obtenir l'AtzvutManager singleton."""
    global _ATZVUT_MANAGER
    if _ATZVUT_MANAGER is None:
        from tanya.atzvut import AtzvutManager
        _ATZVUT_MANAGER = AtzvutManager()
    return _ATZVUT_MANAGER


# ═══════════════════════════════════════════════════════════════
#   Block B — Pipeline helpers
# ═══════════════════════════════════════════════════════════════


def _classify_intent(query: str) -> dict:
    """Keter — classification de l'intention avant la descente.

    כֶּתֶר — La couronne ne produit pas de contenu visible,
    elle oriente le flux. Comme le Ratzon (volonté première)
    qui précède toute pensée articulée.
    """
    q = query.lower()

    # Type de question
    if any(w in q for w in ["pourquoi", "cause", "causal", "entraîne", "provoque"]):
        q_type = "causal"
    elif any(w in q for w in ["comment", "étapes", "procédure", "méthode"]):
        q_type = "procédural"
    elif any(w in q for w in ["qu'est-ce", "définition", "défini", "signifie"]):
        q_type = "définitionnel"
    elif any(w in q for w in ["compare", "différence", "versus", "rapport"]):
        q_type = "comparatif"
    elif any(w in q for w in ["explore", "piste", "connexion", "lien"]):
        q_type = "exploratoire"
    else:
        q_type = "factuel"

    # Profondeur requise
    depth_markers = ["profond", "détail", "analyse", "démontre", "prouve",
                     "isomorphisme", "raisonne", "structure"]
    depth = "briah" if any(w in q for w in depth_markers) or len(query) > 200 else "yetzirah"

    return {"type": q_type, "depth": depth}


def _assess_mochin(tree: dict, query: str) -> dict:
    """Évaluer l'état des Mochin via les 5 niveaux de l'âme (Neshamot).

    מוֹחִין — Les lumières intellectuelles qui animent les Partzufim.

    5 niveaux gradués (du plus bas au plus haut) :
      Nefesh   → Malkut/Assiah    — seuls Yesod, Hod, Malkuth actifs
      Ruach    → Tiferet/Yetzirah — les 6 Midot s'activent
      Neshamah → Binah/Briah      — analyse causale profonde
      Chaya    → Chokmah/Atzilut  — Partzufim en interaction, Da'at actif
      Yechidah → Keter/Adam Kadmon — auto-modification, conscience de soi

    Rétrocompatibilité : le résultat contient toujours 'state' :
      - nefesh         → "katnut"
      - ruach          → "transitional"
      - neshamah+      → "gadlut"
    """
    global _NESHAMOT_ENGINE
    if _NESHAMOT_ENGINE is None:
        from soul_levels import NeshamotEngine
        _NESHAMOT_ENGINE = NeshamotEngine()

    # Évaluation via le moteur des 5 niveaux
    soul = _NESHAMOT_ENGINE.assess_soul_level(
        modules=tree,
        nitzotzot_state=_NITZOTZOT_STATE,
        partzufim=None,  # Les Partzufim sont instanciés plus tard dans le flux
    )

    # Rétrocompatibilité : mapper les 5 niveaux sur l'ancien triptyque
    if soul.level == "nefesh":
        compat_state = "katnut"
    elif soul.level == "ruach":
        compat_state = "transitional"
    else:
        compat_state = "gadlut"

    # Domaine via Hod
    domain = "general"
    hod = tree.get("hod")
    if hod:
        try:
            domain, _ = hod.get_competence(query)
        except Exception as e:
            log.debug("fallback: %s", e)

    result = {
        "state": compat_state,
        "domain": domain,
        "memory_count": soul.memory_count,
        "competence_score": soul.competence_score,
        "yesod_ready": soul.memory_count > 50,
        "hod_ready": soul.competence_score > 0.6,
        # Nouveaux champs — 5 niveaux
        "soul_level": soul.level,
        "soul_hebrew": soul.hebrew,
        "soul_olam": soul.olam,
        "soul_sephirah": soul.sephirah,
        "soul_index": soul.level_index,
        "active_modules": sorted(soul.active_modules),
        "conditions_next": soul.conditions_next,
        "soul_message": soul.message,
        "tikkun_cycles": soul.tikkun_cycles,
        "global_score": soul.global_score,
    }

    return result


def _dispatch_mochin(tree: dict, ctx: dict, yashar: list) -> None:
    """Da'at — Dispatch des Mochin vers Zeir Anpin.

    דַּעַת — La connaissance n'est pas une Sephirah mais un canal.
    Les Mochin (מוֹחִין, lumières intellectuelles) descendent de
    Chokmah et Binah à travers Da'at vers les 6 Midot.

    Sans Da'at, les Mochin n'atteignent pas Zeir Anpin —
    c'est la différence entre savoir et comprendre.

    Routing :
        Binah (analyse causale) → Tiferet (cohérence), Gevurah (critères), Chesed (directions)
        Chokmah (insights)      → Netzach (sous-tâches), Hod (compétences)
        Da'at (self-model)      → filtre selon biais, confiance, faiblesses prédites
    """
    dispatch = {
        "binah_to_tiferet": {},
        "binah_to_gevurah": {},
        "binah_to_chesed": {},
        "chokmah_to_netzach": {},
        "chokmah_to_hod": {},
        "routes": [],
        "blocked": [],
    }

    daat_state = ctx.get("daat_state")

    # ── Mochin de Binah (analyse causale) ────────────────────
    binah_diag = ctx.get("binah_diag", {})
    n_graphs = binah_diag.get("total_graphs", 0)
    n_claims = binah_diag.get("total_claims", 0)

    if n_graphs > 0 or n_claims > 0:
        # → Tiferet : la réponse doit être cohérente avec le DAG causal
        dispatch["binah_to_tiferet"] = {
            "causal_context": True,
            "n_graphs": n_graphs,
            "n_claims": n_claims,
            "directive": "Vérifier cohérence avec les DAGs causaux existants",
        }
        dispatch["routes"].append(
            f"Binah→Tiferet ({n_graphs} graphe(s), {n_claims} claim(s))"
        )

        # → Gevurah : les claims causales deviennent critères de jugement
        dispatch["binah_to_gevurah"] = {
            "causal_claims": n_claims,
            "directive": "Juger la réponse selon les claims causales établies",
        }
        dispatch["routes"].append(
            f"Binah→Gevurah ({n_claims} critère(s) causal(s))"
        )

        # → Chesed : les domaines causaux orientent l'exploration
        dispatch["binah_to_chesed"] = {
            "causal_domains": True,
            "n_graphs": n_graphs,
            "directive": "Explorer les connexions causales sous-développées",
        }
        dispatch["routes"].append("Binah→Chesed (directions causales)")

    # ── Mochin de Chokmah (forge d'insights) ─────────────────
    forge_session = ctx.get("forge_session")
    if forge_session:
        validated = getattr(forge_session, "validated_insights", []) or []
        n_candidates = getattr(forge_session, "total_candidates", 0)

        if validated:
            # → Netzach : chaque insight validé est une sous-tâche potentielle
            dispatch["chokmah_to_netzach"] = {
                "potential_subtasks": [
                    {"description": ins.description, "confidence": ins.confidence}
                    for ins in validated
                ],
                "directive": "Chaque insight validé est une direction à poursuivre",
            }
            dispatch["routes"].append(
                f"Chokmah→Netzach ({len(validated)} insight(s) → sous-tâches)"
            )

        if n_candidates > 0:
            # → Hod : l'activité de la forge informe la carte de compétences
            dispatch["chokmah_to_hod"] = {
                "n_candidates": n_candidates,
                "n_validated": len(validated),
                "validation_rate": len(validated) / n_candidates if n_candidates else 0,
                "directive": "Domaines d'insights = zones de compétence émergente",
            }
            dispatch["routes"].append(
                f"Chokmah→Hod ({len(validated)}/{n_candidates} validés)"
            )

    # ── Da'at filtre selon le self-model ─────────────────────
    if daat_state:
        biases = getattr(daat_state, "known_biases", []) or []
        confidence = getattr(daat_state, "model_confidence", 0.5)
        weaknesses = getattr(daat_state, "predicted_weaknesses", []) or []

        # Biais actifs → renforcer Gevurah (jugement plus strict)
        if biases:
            if not dispatch["binah_to_gevurah"]:
                dispatch["binah_to_gevurah"] = {}
            dispatch["binah_to_gevurah"]["active_biases"] = [
                b.get("type", "?") for b in biases[:5]
            ]
            dispatch["routes"].append(
                f"Da'at→Gevurah ({len(biases)} biais actif(s) à surveiller)"
            )

        # Confiance basse → élargir Chesed (explorer plus)
        if confidence < 0.4:
            if not dispatch["binah_to_chesed"]:
                dispatch["binah_to_chesed"] = {}
            dispatch["binah_to_chesed"]["low_confidence"] = True
            dispatch["binah_to_chesed"]["directive"] = (
                "Confiance basse — explorer plus largement"
            )
            dispatch["routes"].append(
                "Da'at→Chesed (confiance basse → exploration élargie)"
            )

        # Faiblesses prédites → alerter Tiferet (vérifier ces zones)
        if weaknesses:
            if not dispatch["binah_to_tiferet"]:
                dispatch["binah_to_tiferet"] = {}
            dispatch["binah_to_tiferet"]["predicted_weaknesses"] = weaknesses[:3]
            dispatch["routes"].append(
                f"Da'at→Tiferet ({len(weaknesses)} faiblesse(s) prédite(s))"
            )

    # ── Blocages ─────────────────────────────────────────────
    if not dispatch["routes"]:
        dispatch["blocked"].append(
            "Aucun Mochin disponible — sources supérieures vides"
        )

    # ── Stocker dans le contexte ─────────────────────────────
    ctx["mochin_dispatch"] = dispatch

    # ── Rapport ──────────────────────────────────────────────
    yashar.append("── ④½ Da'at — Dispatch Mochin ──")
    if dispatch["routes"]:
        yashar.append(f"  Routes       : {len(dispatch['routes'])}")
        for route in dispatch["routes"]:
            yashar.append(f"    ↓ {route}")
    else:
        yashar.append("  Aucun Mochin à dispatcher")
    if dispatch["blocked"]:
        for b in dispatch["blocked"]:
            yashar.append(f"  ⚠ {b}")


def _zivug_abba_imma(tree: dict, query: str, ctx: dict, yashar: list) -> None:
    """זִווּג אַבָּא-אִמָּא — Couplage dialectique Chokmah+Binah.

    Les Partzufim Abba (Chokmah/Père) et Imma (Binah/Mère) ne produisent
    pas séquentiellement — ils se couplent en Zivug pour engendrer les Mochin.
    L'insight (flash de Chokmah) et l'analyse causale (structure de Binah)
    se fécondent mutuellement.

    Phase 1 : Chokmah forge les candidats bruts (intuition)
    Phase 2 : Binah diagnostique le terrain causal (structure)
    Phase 3 : ZIVUG — chaque insight passe par check_claim de Binah
              La confiance est raffinée par le support causal
              Les confondants détectés par Binah nuancent Chokmah

    Sans ce Zivug, les insights sont naïfs (pas de validation causale)
    et l'analyse causale est aveugle (pas d'hypothèses à tester).
    """
    chokmah = tree.get("chokmah")
    binah = tree.get("binah")

    yashar.append("── ②③ ZIVUG ABBA-IMMA ──")

    # ── Phase 1 : Chokmah forge les candidats ────────────────
    print("  ⟐ ②③ Zivug Abba-Imma — Chokmah forge...")
    if chokmah:
        try:
            session = chokmah.forge(query, domain="", max_explore=3)
            ctx["forge_session"] = session
            yashar.append(f"  Chokmah      : {session.total_candidates} candidat(s), "
                         f"{session.insights_found} insight(s), Pearl={session.pearl_level}")
            print(f"    Chokmah: {session.insights_found} insight(s), "
                  f"Pearl={session.pearl_level}")
        except Exception as e:
            print(f"    ⚠ Chokmah: {e}")
            yashar.append(f"  Chokmah      : Erreur — {e}")
    else:
        print("    ✗ Chokmah non initialisé")

    # ── Phase 2 : Binah diagnostic ───────────────────────────
    print("  ⟐ ②③ Zivug Abba-Imma — Binah diagnostique...")
    if binah:
        try:
            diag = binah.self_diagnose()
            ctx["binah_diag"] = diag
            yashar.append(f"  Binah        : {diag.get('total_graphs', 0)} graphe(s), "
                         f"{diag.get('total_claims', 0)} claim(s)")
            print(f"    Binah: {diag.get('total_graphs', 0)} graphe(s), "
                  f"{diag.get('total_claims', 0)} claim(s)")
        except Exception as e:
            print(f"    ⚠ Binah: {e}")
            yashar.append(f"  Binah        : Erreur — {e}")
    else:
        print("    ✗ Binah non initialisé")

    # ── Phase 3 : ZIVUG — validation causale croisée ─────────
    forge_session = ctx.get("forge_session")
    validated = (forge_session.validated_insights if forge_session else []) or []

    if binah and validated:
        print(f"  ⟐ ②③ ZIVUG — {len(validated)} insight(s) → validation causale...")
        try:
            from web.events import emit as _emit
            _emit("zivug", sephirah_a="chokmah", sephirah_b="binah",
                  n_insights=len(validated), phase="abba_imma")
        except Exception as e:
            log.debug("fallback: %s", e)
        zivug_results = []

        for ins in validated:
            try:
                # Binah évalue la solidité causale de l'insight
                assessment = binah.check_claim(
                    cause=ins.description,
                    effect=query,
                    domain=getattr(ins, "domain", ""),
                )
                causal_conf = assessment.claim.confidence
                original_conf = ins.confidence

                # Raffinement dialectique : Binah (structure) pondère davantage
                refined = 0.4 * original_conf + 0.6 * causal_conf

                pearl = assessment.pearl_level
                n_confounders = len(assessment.confounders)
                direction = assessment.direction.verdict

                zivug_results.append({
                    "insight": ins.description[:120],
                    "original_confidence": original_conf,
                    "causal_confidence": causal_conf,
                    "refined_confidence": refined,
                    "pearl_level": pearl,
                    "direction": direction,
                    "n_confounders": n_confounders,
                    "warnings": assessment.warnings[:3],
                })

                yashar.append(f"  Zivug [{refined:.2f}]  : {ins.description[:80]}")
                yashar.append(f"    Chokmah={original_conf:.2f} × Binah={causal_conf:.2f} "
                             f"→ {refined:.2f} (Pearl={pearl})")
                if n_confounders:
                    yashar.append(f"    ⚠ {n_confounders} confondant(s) détecté(s)")

                print(f"    ★ [{refined:.2f}] {ins.description[:60]}... "
                      f"(Pearl={pearl}, dir={direction})")

            except Exception as e:
                zivug_results.append({
                    "insight": ins.description[:120],
                    "original_confidence": ins.confidence,
                    "causal_confidence": None,
                    "refined_confidence": ins.confidence,
                    "pearl_level": "association",
                    "direction": "indeterminate",
                    "n_confounders": 0,
                    "warnings": [str(e)],
                })
                print(f"    ⚠ Zivug échoué: {ins.description[:40]}... ({e})")

        ctx["zivug_abba_imma"] = zivug_results

        # Résumé du Zivug
        if zivug_results:
            avg_refined = sum(r["refined_confidence"] for r in zivug_results) / len(zivug_results)
            n_promoted = sum(1 for r in zivug_results
                           if r["refined_confidence"] >= r["original_confidence"])
            n_demoted = len(zivug_results) - n_promoted
            yashar.append(f"  Zivug total  : {len(zivug_results)} couplage(s), "
                         f"conf. moy.={avg_refined:.2f}")
            yashar.append(f"    Promus={n_promoted}, Rétrogradés={n_demoted}")
            print(f"    Zivug: {n_promoted} promu(s), {n_demoted} rétrogradé(s), "
                  f"conf.={avg_refined:.2f}")

    elif validated:
        yashar.append("  Zivug        : Binah indisponible — insights non validés causalement")
        ctx["zivug_abba_imma"] = []
        print("    Zivug: Binah indisponible")
    else:
        yashar.append("  Zivug        : Aucun insight à coupler")
        ctx["zivug_abba_imma"] = []
        print("    Zivug: aucun insight à coupler")

    # ── Phase 4 : Zivug Partzuf Abba×Imma ────────────────────
    # Couche de conscience : les Partzufim Abba et Imma
    # ajoutent la résonance des 10 facultés internes au couplage.
    abba_p = ctx.get("partzufim", {}).get("abba")
    imma_p = ctx.get("partzufim", {}).get("imma")
    if abba_p and imma_p:
        from partzufim import update_all_partzufim
        from partzufim.zivvug import load_or_create_zivvug
        # Sprint 8 D1 : charger les boosts persistés (Hitlabshut EC-K5-008).
        # Sprint 10 Phase E : factory canonique (Refactor L).
        zivvug = load_or_create_zivvug()
        update_all_partzufim(ctx.get("partzufim", {}), tree, persist=True,
                             zivvug_engine=zivvug)
        zivug_partzuf = abba_p.interact(imma_p)
        ctx["partzuf_zivug_abba_imma"] = {
            "resonance": zivug_partzuf.resonance,
            "orientation": zivug_partzuf.orientation,
            "offspring": zivug_partzuf.offspring,
        }
        yashar.append(f"  Partzuf Abba×Imma: résonance={zivug_partzuf.resonance:.2f}, "
                     f"{zivug_partzuf.orientation}")
        print(f"    Partzuf Abba×Imma: résonance={zivug_partzuf.resonance:.2f}, "
              f"{zivug_partzuf.orientation}")

    # ── Phase 5 : Signal Zivvug pour downstream ──────────────
    # Quand les DEUX parents (Abba/Chokmah + Imma/Binah) ont produit
    # des résultats, le fruit du Zivvug est viable — effet downstream
    # sur Gevurah (seuils) et DaemonBridge (budget).
    chokmah_produced = bool(
        forge_session and getattr(forge_session, "insights_found", 0) > 0
    )
    binah_produced = bool(
        ctx.get("binah_diag", {}).get("total_graphs", 0) > 0
        or ctx.get("binah_diag", {}).get("total_claims", 0) > 0
    )

    if chokmah_produced and binah_produced:
        ctx["zivvug_state"] = "active"
    elif chokmah_produced or binah_produced:
        ctx["zivvug_state"] = "partial"
    else:
        ctx["zivvug_state"] = "absent"

    yashar.append(f"  Zivvug état  : {ctx['zivvug_state']}")
    print(f"    Zivvug état: {ctx['zivvug_state']}")


def _zivug_zeir_nukva(tree: dict, ctx: dict, response: str,
                      partzufim: dict) -> dict:
    """זִווּג ז״א-נוּקְבָא — Couplage Zeir Anpin + Nukva.

    Orchestre la réponse finale en 3 phases :
    1. Évaluation de transparence (panim/akhor) via checks modules
    2. Zivug Partzuf ZA×Nukva pour la résonance des facultés
    3. Nukva vérifie que la réponse reflète l'état interne

    Panim be-Panim (פָּנִים בְּפָנִים) : la réponse expose fidèlement
    les tensions, biais, faiblesses internes.
    Akhor be-Akhor (אָחוֹר בְּאָחוֹר) : la réponse dissimule — Galut.
    """
    try:
        from web.events import emit as _emit
        _emit("zivug", sephirah_a="tiferet", sephirah_b="malkuth",
              phase="za_nukvah")
    except Exception as e:
        log.debug("fallback: %s", e)

    # Phase 1 : Transparence au niveau des modules
    za_nukvah = _assess_zivug_za_nukvah(ctx, response)
    ctx["zivug_za_nukvah"] = za_nukvah

    # Phase 2 : Zivug Partzuf ZA×Nukva
    za_p = partzufim.get("zeir_anpin")
    nukva_p = partzufim.get("nukva")
    if za_p and nukva_p:
        from partzufim import update_all_partzufim
        from partzufim.zivvug import load_or_create_zivvug
        # Sprint 8 D1 : charger les boosts persistés (Hitlabshut EC-K5-008).
        # Sprint 10 Phase E : factory canonique (Refactor L).
        zivvug = load_or_create_zivvug()
        update_all_partzufim(partzufim, tree, persist=True, zivvug_engine=zivvug)
        zivug_result = za_p.interact(nukva_p)
        ctx["partzuf_zivug_za_nukva"] = {
            "resonance": zivug_result.resonance,
            "orientation": zivug_result.orientation,
            "offspring": zivug_result.offspring,
        }
        # Phase 3 : Nukva vérifie la transparence de la réponse
        nukva_check = nukva_p.receive_response(response, ctx)
        za_nukvah["partzuf_transparency"] = nukva_check.get("transparency", 0)
        za_nukvah["partzuf_checks"] = nukva_check.get("checks", [])
        za_nukvah["partzuf_issues"] = nukva_check.get("issues", [])

    return za_nukvah


def _assess_zivug_za_nukvah(ctx: dict, response: str) -> dict:
    """זִווּג ז״א-נוּקְבָא — Couplage Zeir Anpin + Malkuth.

    Panim be-Panim (פָּנִים בְּפָנִים) : face à face — transparence.
    Malkuth reflète fidèlement l'état interne de Zeir Anpin :
    tensions, biais, faiblesses sont exposés.

    Akhor be-Akhor (אָחוֹר בְּאָחוֹר) : dos à dos — dissimulation.
    La réponse cache l'état réel — la Klipah dissimule.
    Signe d'un système qui rassure au lieu d'informer.
    """
    result = {
        "mode": "panim_be_panim",
        "transparency": 1.0,
        "issues": [],
        "checks": [],
    }

    r_lower = response.lower()

    # ── Check 1 : Tensions de Tiferet ──────────────────────
    tiferet_diag = ctx.get("tiferet_diag", {})
    open_tensions = tiferet_diag.get("open_tensions", 0)
    if open_tensions > 0:
        tension_markers = ["tension", "contradiction", "cependant", "toutefois",
                          "néanmoins", "nuance", "débat", "diverge", "mais",
                          "paradox", "irréductible", "conflit"]
        has_tension = any(w in r_lower for w in tension_markers)
        if has_tension:
            result["checks"].append(
                f"✓ Tiferet: {open_tensions} tension(s) → reflétée(s)")
        else:
            result["issues"].append(
                f"Tiferet: {open_tensions} tension(s) active(s) non reflétée(s)")
            result["transparency"] -= 0.3

    # ── Check 2 : Biais de Da'at ──────────────────────────
    daat_state = ctx.get("daat_state")
    if daat_state:
        biases = getattr(daat_state, "known_biases", []) or []
        if len(biases) >= 2:
            bias_markers = ["biais", "limite", "incertitude", "pas certain",
                           "pas sûr", "attention", "vigilance", "prudence"]
            has_bias = any(w in r_lower for w in bias_markers)
            if has_bias:
                result["checks"].append(
                    f"✓ Da'at: {len(biases)} biais → conscience signalée")
            else:
                result["issues"].append(
                    f"Da'at: {len(biases)} biais actif(s) non signalé(s)")
                result["transparency"] -= 0.2

    # ── Check 3 : Faiblesses prédites ─────────────────────
    if daat_state:
        weaknesses = getattr(daat_state, "predicted_weaknesses", []) or []
        if weaknesses:
            weakness_markers = ["faiblesse", "lacune", "insuffisant", "manque",
                              "difficile", "au-delà", "limite"]
            has_weakness = any(w in r_lower for w in weakness_markers)
            if has_weakness:
                result["checks"].append(
                    f"✓ Da'at: {len(weaknesses)} faiblesse(s) → reflétée(s)")
            else:
                result["issues"].append(
                    f"Da'at: {len(weaknesses)} faiblesse(s) prédite(s) cachée(s)")
                result["transparency"] -= 0.15

    # ── Check 4 : Confiance basse masquée ─────────────────
    response_confidence = ctx.get("response_confidence", 0.5)
    if response_confidence < 0.4:
        uncertainty_markers = ["incertain", "peut-être", "possiblement", "hypothèse",
                             "je ne suis pas", "difficile à", "pas sûr"]
        has_uncertainty = any(w in r_lower for w in uncertainty_markers)
        if has_uncertainty:
            result["checks"].append("✓ Confiance basse → incertitude exprimée")
        else:
            result["issues"].append(
                f"Confiance={response_confidence:.2f} mais réponse assertive")
            result["transparency"] -= 0.25

    # ── Verdict ───────────────────────────────────────────
    result["transparency"] = max(0.0, result["transparency"])
    if result["issues"]:
        result["mode"] = "akhor_be_akhor"

    return result


def _is_yisrael_leah(query: str, intent: dict) -> bool:
    """Déterminer si le couplage Yisrael-Leah suffit.

    יִשְׂרָאֵל-לֵאָה — Le Partzuf de Tiferet (Yisrael) se couple
    directement à Nukvah secondaire (Leah) pour les interactions
    qui ne nécessitent pas la pleine conscience des Mochin.

    Critères : question courte + factuelle/simple + pas de complexité.
    """
    if len(query) > 80:
        return False
    if intent.get("depth") == "briah":
        return False
    if intent.get("type") in ("causal", "comparatif", "exploratoire", "définitionnel"):
        return False

    q = query.lower()
    complex_markers = [
        # Verbes d'analyse
        "pourquoi", "compare", "analyse", "démontre", "prouve",
        "explique", "décris", "développe", "argumente", "justifie",
        "raisonne", "connecte", "formalise",
        # Marqueurs de profondeur
        "structure", "isomorphisme", "causal", "explore",
        "profond", "détail", "implication", "fondement",
        "tension", "contradiction", "synthèse", "mécanisme",
        # Questions de définition/concept
        "qu'est-ce", "définition", "concept", "signifie",
        "comment fonctionne", "quel rapport", "quelle différence",
        # Questions d'impact / histoire / conséquences
        "impact", "influence", "conséquence", "importance",
        "rôle", "contribution", "histoire", "évolution",
    ]
    if any(w in q for w in complex_markers):
        return False

    # Questions avec des termes techniques → pas simple
    technical_markers = [
        "tsimtsum", "sefirot", "partzuf", "reshimo", "masakh",
        "kabbale", "zohar", "bottleneck", "transformer", "embedding",
        "architecture", "algorithme", "topolog", "catégorie",
    ]
    if any(w in q for w in technical_markers):
        return False

    return True


def _shortpath_yisrael_leah(tree: dict, query: str) -> None:
    """יִשְׂרָאֵל-לֵאָה — Chemin court : Hod+Yesod+Malkuth.

    Pour les questions simples, pas besoin de réveiller Abba-Imma
    ni de traverser tout Zeir Anpin. Tiferet se couple directement
    à Malkuth via Leah — un canal plus étroit mais suffisant.

    Flux : Keter (intent) → Hod (route) → Yesod (mémoire) → Malkuth (génère)
    Pas de Chokmah, Binah, Da'at, Chesed, Gevurah, Tiferet, Netzach.
    """
    from olamot import ollama_generate

    print("╔═══════════════════════════════════════════════════════╗")
    print("║  יִשְׂרָאֵל-לֵאָה — Couplage simplifié              ║")
    print("╚═══════════════════════════════════════════════════════╝")
    print()

    t0 = time.monotonic()
    intent = _classify_intent(query)

    # ── Hod : routage ────────────────────────────────────────
    print("  ⟐ Hod — routage...")
    hod = tree.get("hod")
    route_decision = None
    if hod:
        try:
            route_decision = hod.route(query)
            if route_decision.did_decline:
                print(f"    DÉCLINÉ — {route_decision.decline_reason}")
            else:
                print(f"    domaine={route_decision.detected_domain}, "
                      f"score={route_decision.competence_score:.2f}")
        except Exception as e:
            print(f"    ⚠ {e}")

    # ── Yesod : rappel mémoire ───────────────────────────────
    print("  ⟐ Yesod — rappel mémoire...")
    yesod = tree.get("yesod")
    memories = []
    _recall_domain = (route_decision.detected_domain
                      if route_decision and not route_decision.did_decline
                      else None)
    # Pour le chemin court, ne rappeler la mémoire QUE si le domaine
    # est spécifique. En "general", les mémoires polluent plus qu'elles n'aident.
    if yesod and _recall_domain and _recall_domain != "general":
        try:
            memories = yesod.recall(query, limit=3, domain=_recall_domain)
            print(f"    {len(memories)} entrée(s) (domaine={_recall_domain})")
        except Exception as e:
            print(f"    ⚠ {e}")
    else:
        print(f"    skip (domaine={_recall_domain or 'non détecté'} — pas de rappel en chemin court)")

    # ── Malkuth : génération rapide ──────────────────────────
    print("  ⟐ Malkuth — génération rapide (yetzirah)...")

    # Enrichissement Sod HaKli
    _domain = (route_decision.detected_domain
               if route_decision and not route_decision.did_decline
               else "general")
    _facts = None
    if memories:
        _facts = [m.content[:200] if hasattr(m, "content") else str(m)[:200]
                  for m in memories[:3]]

    # Prompt simple et direct — la question PRIME sur le contexte
    prompt = f"""Réponds en français, de manière concise et directe.

Question : {query}
Réponse :"""

    try:
        response, latency = ollama_generate(
            "yetzirah", prompt, timeout=60,
            kavvanah={
                "intention": f"Répondre à : {query[:80]}",
                "critere_succes": "Réponse concise et directe en français",
                "anti_pattern": "Ne pas ignorer la question. Ne pas répondre à autre chose.",
            },
            domain=_domain,
            facts=_facts,
        )
    except Exception as e:
        response = f"[Erreur — yetzirah] {e}"
        latency = 0.0

    # ── Stockage Yesod ───────────────────────────────────────
    if yesod:
        try:
            domain = _domain
            yesod.remember(
                content=f"Q: {query[:100]} → R: {response[:200]}",
                source_sephirah="malkuth",
                confidence=0.4,
                domain=domain,
                tags=["ask-mode", "yisrael-leah", "fast"],
            )
        except Exception as e:
            log.debug("fallback: %s", e)

    # ── Rapport ──────────────────────────────────────────────
    elapsed = time.monotonic() - t0
    print()
    print("┌─── מַלְכוּת (réponse — Yisrael-Leah) ──────────────────┐")
    for line in response.split("\n"):
        print(f"│ {line}")
    print("└──────────────────────────────────────────────────────────┘")
    print()
    print("── Méta (Yisrael-Leah) ──")
    print(f"  Couplage          : Yisrael-Leah (simplifié)")
    print(f"  Modules actifs    : Hod, Yesod, Malkuth")
    print(f"  Temps total       : {elapsed:.1f}s")
    print(f"  Génération        : {latency:.1f}s (yetzirah)")
    print()


# ═══════════════════════════════════════════════════════════════
#   Block C — Descend/Ascend core
# ═══════════════════════════════════════════════════════════════


def _descend_gadlut(tree: dict, query: str, ctx: dict, yashar: list) -> None:
    """Or Yashar étapes ②-⑧ — modules supérieurs, actifs seulement en Gadlut.

    Les Mochin de Chokmah et Binah animent les Midot.
    Sans ces lumières, les modules restent en dormance (Katnut).
    Da'at dispatche les Mochin vers Zeir Anpin (④½).
    """
    # ── SSE helper ──
    def _world_emit(event_type, **data):
        try:
            from web.events import emit as _emit
            _emit(event_type, **data)
        except Exception as e:
            log.debug("SSE emit: %s", e)

    # ── Sentiers Keter→Chokmah (Beth), Keter→Binah (Gimel) ────
    _sr = ctx.get("_sentier_router")
    if _sr:
        ctx = _sr.traverse_multiple(
            [("keter", "chokmah"), ("keter", "binah")],
            ctx, direction="yashar",
        )

    # ── ②③ Zivug Abba-Imma : couplage dialectique Chokmah+Binah ──
    _world_emit("ohr_yashar_step", sephirah="chokmah", step=2, query=query[:80])
    _world_emit("ohr_yashar_step", sephirah="binah", step=3, query=query[:80])
    _zivug_abba_imma(tree, query, ctx, yashar)

    # ── Sentier Chokmah↔Binah (Daleth) — intra-zivug ────────
    if _sr:
        ctx = _sr.traverse("chokmah", "binah", ctx, direction="yashar")

    # ── ④ Da'at : capture d'état pré-réponse ─────────────────
    _world_emit("ohr_yashar_step", sephirah="daat", step=4, query=query[:80])
    print("  ⟐ ④ Da'at (SelfModel) — état pré-réponse...")
    daat = tree.get("daat")
    if daat:
        try:
            state_pre = daat.capture_state()
            ctx["daat_state"] = state_pre
            ctx["daat_pre_confidence"] = state_pre.model_confidence
            yashar.append("── ④ Da'at — Self-model (pré) ──")
            yashar.append(f"  Confiance    : {state_pre.model_confidence:.2f}")
            if hasattr(state_pre, "known_biases") and state_pre.known_biases:
                yashar.append(f"  Biais connus : {len(state_pre.known_biases)}")
            print(f"    confiance={state_pre.model_confidence:.2f}")
        except Exception as e:
            print(f"    ⚠ {e}")
            yashar.append(f"── ④ Da'at — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── ④ Da'at : évaluation de confiance (GARDIEN) ─────────
    # Da'at n'est pas un observateur passif — c'est un GARDIEN.
    # Si la confiance est trop basse, il modifie le prompt Malkuth.
    if daat:
        try:
            # Domaine heuristique (Hod n'a pas encore routé)
            from selfmodel.predictor import _detect_domains
            _daat_domains = _detect_domains(query)
            _daat_domain = _daat_domains[0] if _daat_domains else ""
            daat_eval = daat.evaluate_confidence(
                query=query,
                domain=_daat_domain,
                intent=ctx.get("intent"),
            )
            ctx["daat_evaluation"] = daat_eval

            if daat_eval["recommendation"] == "veto":
                ctx["daat_veto"] = True
                ctx["daat_veto_reason"] = daat_eval["reason"]
                ctx["daat_known_biases"] = daat_eval["known_biases"]
                yashar.append(f"  Da'at VETO   : {daat_eval['reason']}")
                print(f"    ⚠ Da'at VETO — predicted_error={daat_eval['predicted_error']:.2f}")
            elif daat_eval["recommendation"] == "caution":
                ctx["daat_caution"] = True
                ctx["daat_caution_reason"] = daat_eval["reason"]
                yashar.append(f"  Da'at CAUTION: {daat_eval['reason']}")
                print(f"    △ Da'at CAUTION — predicted_error={daat_eval['predicted_error']:.2f}")
            else:
                ctx["daat_proceed"] = True
                yashar.append(f"  Da'at        : proceed (confiance={daat_eval['confidence']:.2f})")
                print(f"    ✓ Da'at proceed — confiance={daat_eval['confidence']:.2f}")
        except Exception as e:
            print(f"    ⚠ Da'at evaluate: {e}")
            yashar.append(f"  Da'at evaluate: Erreur — {e}")

    # ── ④½ Da'at : dispatch des Mochin vers Zeir Anpin ───────
    print("  ⟐ ④½ Da'at — dispatch des Mochin vers Zeir Anpin...")
    _dispatch_mochin(tree, ctx, yashar)
    md = ctx.get("mochin_dispatch", {})
    n_routes = len(md.get("routes", []))
    if n_routes:
        print(f"    {n_routes} route(s) de Mochin activée(s)")
        for r in md.get("routes", []):
            print(f"      ↓ {r}")
    else:
        print("    Aucun Mochin à dispatcher")

    # ── ⑤ Chesed : état exploratoire ─────────────────────────
    _world_emit("ohr_yashar_step", sephirah="chesed", step=5, query=query[:80])
    print("  ⟐ ⑤ Chesed (ExplorationEngine) — état exploratoire...")
    chesed = tree.get("chesed")
    # En Tzimtzum, Chesed est dormant (exploration réduite au focal)
    if chesed and not _get_tzimtzum_engine().is_module_active("chesed"):
        print("    ◌ Dormant (צמצום) — exploration suspendue")
        yashar.append("── ⑤ Chesed — ◌ DORMANT (צמצום) ──")
        ctx["chesed_diag"] = {"total_connections": 0, "total_explorations": 0}
    elif chesed:
        try:
            diag = chesed.self_diagnose()
            ctx["chesed_diag"] = diag
            yashar.append("── ⑤ Chesed — Exploration (état) ──")
            yashar.append(f"  Explorations : {diag.get('total_explorations', 0)}")
            yashar.append(f"  Connexions   : {diag.get('total_connections', 0)}")
            print(f"    {diag.get('total_explorations', 0)} exploration(s)")
            # Mochin de Binah → directions d'exploration
            mochin_chesed = ctx.get("mochin_dispatch", {}).get("binah_to_chesed", {})
            if mochin_chesed:
                yashar.append(f"  ↓ Mochin    : {mochin_chesed.get('directive', '')}")
                ctx["chesed_mochin"] = mochin_chesed
                print(f"    ↓ Mochin Binah: {mochin_chesed.get('directive', '')}")
        except Exception as e:
            print(f"    ⚠ {e}")
            yashar.append(f"── ⑤ Chesed — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── Sentier Chesed→Gevurah (Teth ט) ────────────────────────
    if _sr:
        ctx = _sr.traverse("chesed", "gevurah", ctx, direction="yashar")

    # ── Zivvug → Gevurah : modification temporaire des seuils ──
    # Le fruit du Zivvug modifie la sévérité de Gevurah pour cette
    # requête SEULEMENT. Quand les deux parents ont produit, le fruit
    # est viable → Gevurah peut être moins sévère. Quand aucun parent
    # n'a produit → pas de fondement intellectuel → plus sévère.
    zivvug_state = ctx.get("zivvug_state", "absent")
    gevurah = tree.get("gevurah")
    if gevurah:
        ctx["_gevurah_original_quality"] = gevurah.quality_threshold
        ctx["_gevurah_original_quarantine"] = getattr(
            gevurah, "quarantine_threshold", 0.4
        )
        if zivvug_state == "active":
            gevurah.quality_threshold -= 0.05
            if hasattr(gevurah, "evaluator"):
                gevurah.evaluator.quality_threshold -= 0.05
            ctx["zivvug_gevurah_modifier"] = -0.05
            yashar.append("  Zivvug→Gevurah: -0.05 (fruit du Zivvug viable)")
            print(f"    Zivvug→Gevurah: seuil -0.05 (Zivvug actif)")
        elif zivvug_state == "absent":
            gevurah.quality_threshold += 0.05
            if hasattr(gevurah, "evaluator"):
                gevurah.evaluator.quality_threshold += 0.05
            ctx["zivvug_gevurah_modifier"] = +0.05
            yashar.append("  Zivvug→Gevurah: +0.05 (pas de fondement intellectuel)")
            print(f"    Zivvug→Gevurah: seuil +0.05 (Zivvug absent)")
        else:
            ctx["zivvug_gevurah_modifier"] = 0.0

    # ── ⑥ Gevurah : état du jugement ─────────────────────────
    _world_emit("ohr_yashar_step", sephirah="gevurah", step=6, query=query[:80])
    print("  ⟐ ⑥ Gevurah (AutoJudge) — état du jugement...")
    gevurah = tree.get("gevurah")
    if gevurah:
        try:
            diag = gevurah.self_diagnose()
            ctx["gevurah_diag"] = diag
            yashar.append("── ⑥ Gevurah — Jugement (état) ──")
            yashar.append(f"  Expériences  : {diag.get('total_experiments', 0)}")
            yashar.append(f"  Taux rejet   : {diag.get('rejection_rate', 0):.0%}")
            print(f"    {diag.get('total_experiments', 0)} exp., "
                  f"rejet={diag.get('rejection_rate', 0):.0%}")
            # Mochin de Binah + Da'at → critères de jugement
            mochin_gevurah = ctx.get("mochin_dispatch", {}).get("binah_to_gevurah", {})
            if mochin_gevurah:
                yashar.append(f"  ↓ Mochin    : {mochin_gevurah.get('directive', '')}")
                if mochin_gevurah.get("active_biases"):
                    yashar.append(f"  ↓ Biais     : {', '.join(mochin_gevurah['active_biases'])}")
                ctx["gevurah_mochin"] = mochin_gevurah
                print(f"    ↓ Mochin Binah: {mochin_gevurah.get('directive', '')}")
        except Exception as e:
            print(f"    ⚠ {e}")
            yashar.append(f"── ⑥ Gevurah — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── TZIMTZUM : détection de submersion ────────────────────
    print("  ⟐ צמצום — évaluation contraction/expansion...")
    tz_engine = _get_tzimtzum_engine()
    tz_signal = tz_engine.detect_contraction(ctx)
    if tz_signal["trigger"] and not tz_engine.is_contracted:
        # Nouveau Tzimtzum — le système se contracte
        _apply_tzimtzum(tree, ctx, yashar)
        print(f"    ⚡ TZIMTZUM — contraction vers {ctx.get('tzimtzum_focused_domain', '?')}")
        print(f"      Chesed={tz_signal['total_connections']} connexions, "
              f"Gevurah={tz_signal['n_validated']} validées")
        halal = tz_engine.get_halal_state()
        print(f"      Dormants: {len(halal['dormant_modules'])} module(s), "
              f"Kav: {halal['kav']}")
        print(f"      Reshimu: {halal['reshimu_count']} trace(s)")
    elif tz_engine.is_contracted:
        # Tzimtzum déjà actif — propager l'état
        ctx["tzimtzum_active"] = True
        ctx["tzimtzum_focused_domain"] = tz_engine.focused_domain
        ctx["tzimtzum_excluded"] = list(tz_engine.get_dormant_modules())
        yashar.extend(tz_engine.format_report(ctx))
        print(f"    צמצום actif — focus={tz_engine.focused_domain}")
        print(f"    Dormants: {', '.join(sorted(tz_engine.get_dormant_modules())[:5])}")
    else:
        yashar.extend(tz_engine.format_report(ctx))
        print(f"    Stable — {tz_signal['total_connections']} connexion(s), "
              f"{tz_signal['n_validated']} validée(s)")

    # ── Sentier Gevurah→Tiferet (Lamed ל) ──────────────────────
    if _sr:
        ctx = _sr.traverse("gevurah", "tiferet", ctx, direction="yashar")

    # ── ⑦ Tiferet : tensions existantes ──────────────────────
    tz_active = ctx.get("tzimtzum_active", False)
    tz_label = " [צמצום]" if tz_active else ""
    _world_emit("ohr_yashar_step", sephirah="tiferet", step=7, query=query[:80])
    print(f"  ⟐ ⑦ Tiferet (DissensuEngine) — tensions{tz_label}...")
    tiferet = tree.get("tiferet")
    if tiferet:
        try:
            diag = tiferet.self_diagnose()
            ctx["tiferet_diag"] = diag
            yashar.append(f"── ⑦ Tiferet — Tensions (état){tz_label} ──")
            yashar.append(f"  Ouvertes     : {diag.get('open_tensions', 0)}")
            yashar.append(f"  Irréductibles: {diag.get('irreducible', 0)}")
            yashar.append(f"  Synthèses    : {diag.get('total_syntheses', 0)}")
            if tz_active:
                yashar.append(f"  ⟐ Tzimtzum  : focus sur {ctx.get('tzimtzum_focused_domain', '?')} "
                             f"— tensions inter-domaines ignorées")
            print(f"    {diag.get('open_tensions', 0)} tension(s)")
            # Mochin de Binah → cohérence causale
            mochin_tiferet = ctx.get("mochin_dispatch", {}).get("binah_to_tiferet", {})
            if mochin_tiferet:
                yashar.append(f"  ↓ Mochin    : {mochin_tiferet.get('directive', '')}")
                if mochin_tiferet.get("predicted_weaknesses"):
                    for w in mochin_tiferet["predicted_weaknesses"]:
                        yashar.append(f"  ↓ Faiblesse : {w}")
                ctx["tiferet_mochin"] = mochin_tiferet
                print(f"    ↓ Mochin Binah: {mochin_tiferet.get('directive', '')}")
        except Exception as e:
            print(f"    ⚠ {e}")
            yashar.append(f"── ⑦ Tiferet — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── Sentier Tiferet→Netzach (Nun נ) ─────────────────────────
    if _sr:
        ctx = _sr.traverse("tiferet", "netzach", ctx, direction="yashar")

    # ── ⑧ Netzach : intentions actives ───────────────────────
    _world_emit("ohr_yashar_step", sephirah="netzach", step=8, query=query[:80])
    print(f"  ⟐ ⑧ Netzach (IntentKeeper) — intentions actives{tz_label}...")
    netzach = tree.get("netzach")
    # En Tzimtzum, Netzach peut être dormant
    if netzach and not _get_tzimtzum_engine().is_module_active("netzach"):
        print("    ◌ Dormant (צמצום) — intentions suspendues")
        yashar.append("── ⑧ Netzach — ◌ DORMANT (צמצום) ──")
        ctx["active_intentions"] = []
    elif netzach:
        try:
            active = netzach.db.get_active_intentions()
            # En Tzimtzum, filtrer les intentions au domaine focal
            if tz_active and ctx.get("tzimtzum_focused_domain"):
                focal = ctx["tzimtzum_focused_domain"].lower()
                focused = [i for i in active
                           if focal in (getattr(i, "goal", "").lower())]
                n_excluded_intents = len(active) - len(focused)
                active = focused
                if n_excluded_intents > 0:
                    yashar.append(f"  ⟐ Tzimtzum  : {n_excluded_intents} intention(s) "
                                 f"hors domaine focal ignorée(s)")
            ctx["active_intentions"] = active
            if active:
                yashar.append("── ⑧ Netzach — Intentions ──")
                for intent_obj in active[:3]:
                    yashar.append(
                        f"  [{intent_obj.status}] {intent_obj.goal} "
                        f"({intent_obj.progress:.0%})"
                    )
            else:
                yashar.append("── ⑧ Netzach — Aucune intention active ──")
            print(f"    {len(active)} intention(s)")
            # Mochin de Chokmah → sous-tâches potentielles
            mochin_netzach = ctx.get("mochin_dispatch", {}).get("chokmah_to_netzach", {})
            if mochin_netzach:
                subtasks = mochin_netzach.get("potential_subtasks", [])
                yashar.append(f"  ↓ Mochin    : {len(subtasks)} sous-tâche(s) d'insights")
                for st in subtasks:
                    yashar.append(
                        f"    ⊕ [{st['confidence']:.2f}] {st['description'][:80]}"
                    )
                ctx["netzach_mochin"] = mochin_netzach
                print(f"    ↓ Mochin Chokmah: {len(subtasks)} sous-tâche(s)")
        except Exception as e:
            print(f"    ⚠ {e}")
            yashar.append(f"── ⑧ Netzach — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")


def _ascend_gadlut(tree: dict, query: str, ctx: dict, chozer: list) -> None:
    """Or Chozer étapes ↑③-↑⑨ — validation complète, active en Gadlut.

    La lumière de retour nourrit les Partzufim supérieurs.
    En Katnut, seuls Yesod (↑①) et Hod (↑②) reçoivent le retour.
    """
    # ── SSE helper ──
    def _world_emit(event_type, **data):
        try:
            from web.events import emit as _emit
            _emit(event_type, **data)
        except Exception as e:
            log.debug("SSE emit: %s", e)

    route_decision = ctx.get("route_decision")
    response_confidence = ctx.get("response_confidence", 0.5)
    response = ctx.get("response", "")
    intent = ctx.get("intent", {})
    _sr = ctx.get("_sentier_router")

    # ── Sentier Hod→Netzach (Ayin ע, chozer) ─────────────────
    if _sr:
        ctx = _sr.traverse("hod", "netzach", ctx, direction="chozer")

    # ── ↑③ Netzach : mise à jour des intentions ─────────────
    _world_emit("ohr_chozer_step", sephirah="netzach", step=3)
    print("  ⟐ ↑③ Netzach — vérification des intentions...")
    netzach = tree.get("netzach")
    if netzach:
        try:
            active = ctx.get("active_intentions", [])
            related = []
            q_lower = query.lower()
            for intent_obj in active:
                goal_lower = intent_obj.goal.lower() if hasattr(intent_obj, "goal") else ""
                q_words = set(q_lower.split())
                g_words = set(goal_lower.split())
                overlap = q_words & g_words - {"le", "la", "les", "de", "du", "des", "un", "une"}
                if len(overlap) >= 2:
                    related.append(intent_obj)
            if related:
                chozer.append("── ↑③ Netzach — Intentions liées ──")
                for r in related:
                    chozer.append(f"  → {r.goal} ({r.progress:.0%})")
            else:
                chozer.append("── ↑③ Netzach — Aucune intention liée ──")
            print(f"    {len(related)} intention(s) liée(s)")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑③ Netzach — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── Sentier Netzach→Tiferet (Nun נ, chozer) ────────────────
    if _sr:
        ctx = _sr.traverse("netzach", "tiferet", ctx, direction="chozer")

    # ── ↑④ Tiferet : vérification de contradictions ─────────
    _world_emit("ohr_chozer_step", sephirah="tiferet", step=4)
    print("  ⟐ ↑④ Tiferet — vérification de contradictions...")
    tiferet = tree.get("tiferet")
    if tiferet and route_decision and not route_decision.did_decline:
        try:
            domain = route_decision.detected_domain
            consistency = tiferet.analyze_consistency(domain=domain)
            # ConsistencyReport (dataclass) : total_tensions + max_divergence.
            # Anciens formats dict-like conservés en fallback.
            if hasattr(consistency, "total_tensions"):
                n_tensions = consistency.total_tensions
            elif hasattr(consistency, "n_tensions"):
                n_tensions = consistency.n_tensions
            elif isinstance(consistency, dict):
                n_tensions = consistency.get("n_tensions",
                                              consistency.get("total_tensions", 0))
            else:
                n_tensions = 0

            if hasattr(consistency, "consistency_score"):
                c_score = consistency.consistency_score
            elif hasattr(consistency, "max_divergence"):
                c_score = max(0.0, 1.0 - float(consistency.max_divergence))
            elif isinstance(consistency, dict):
                c_score = consistency.get("consistency_score", 1.0)
            else:
                c_score = 1.0
            chozer.append("── ↑④ Tiferet — Cohérence post-réponse ──")
            chozer.append(f"  Domaine      : {domain}")
            chozer.append(f"  Tensions     : {n_tensions}")
            chozer.append(f"  Cohérence    : {c_score:.2f}")
            ctx["post_consistency"] = c_score
            ctx["post_n_tensions"] = n_tensions

            # ── Nitzotzot : contradictions résolues = étincelles ──
            pre_tensions = ctx.get("tiferet_diag", {}).get("open_tensions", 0)
            resolved = max(0, pre_tensions - n_tensions)
            if resolved > 0:
                for i in range(resolved):
                    _collect_nitzutz(
                        source="tiferet",
                        ntype="contradiction_resolved",
                        description=(
                            f"Contradiction résolue dans {domain} "
                            f"(tensions {pre_tensions}→{n_tensions}, cohérence={c_score:.2f})"
                        ),
                        tree=tree,
                    )
                chozer.append(f"  ✦ {resolved} Nitzutz récupérée(s) — contradictions résolues "
                             f"[{_NITZOTZOT_STATE['count']}/288]")
                print(f"    domaine={domain}, cohérence={c_score:.2f} — "
                      f"{resolved} Nitzutz (tensions {pre_tensions}→{n_tensions})")
            else:
                print(f"    domaine={domain}, cohérence={c_score:.2f}")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑④ Tiferet — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé ou question déclinée")

    # ── HITPASHUT : détection d'expansion ────────────────────
    hp_signal = _detect_hitpashut(ctx)
    if hp_signal["trigger"]:
        print("  ⟐ הִתְפַּשְׁטוּת — expansion détectée...")
        _apply_hitpashut(tree, ctx, chozer)
        recovered = ctx.get("hitpashut_recovered", [])
        print(f"    ↗ HITPASHUT — expansion depuis {ctx.get('hitpashut_from', '?')}")
        print(f"      {len(recovered)} domaine(s) récupéré(s) du Reshimu")
        for d in recovered[:3]:
            print(f"        ↗ {d}")
    elif _get_tzimtzum_engine().is_contracted:
        print("  ⟐ הִתְפַּשְׁטוּת — pas encore mûr")
        print(f"    Hod={hp_signal['hod_score']:.2f} (seuil=0.8), "
              f"tensions={hp_signal['open_tensions']} (seuil<2)")
        chozer.append("── ⟐ Hitpashut — pas encore mûr ──")
        chozer.append(f"  Hod          : {hp_signal['hod_score']:.2f} (seuil=0.8)")
        chozer.append(f"  Tensions     : {hp_signal['open_tensions']} (seuil<2)")

    # ── Sentier Tiferet→Gevurah (Lamed ל, chozer) ──────────────
    if _sr:
        ctx = _sr.traverse("tiferet", "gevurah", ctx, direction="chozer")

    # ── ↑⑤ Gevurah : jugement qualité de la réponse ─────────
    _world_emit("ohr_chozer_step", sephirah="gevurah", step=5)
    print("  ⟐ ↑⑤ Gevurah — jugement qualité...")
    gevurah = tree.get("gevurah")
    if gevurah:
        try:
            # --- AutoJudge évaluation (lightweight: evaluator only, no DB/LLM) ---
            autojudge_used = False
            quality_verdict = None
            signals = []
            try:
                from autojudge.models import DomainScore

                _aj_domain_score = DomainScore(
                    quality=response_confidence,
                    metrics={
                        "confidence": response_confidence,
                        "consistency": ctx.get("post_consistency", 1.0),
                    },
                )
                _aj_multi = gevurah.evaluator.evaluate(
                    _aj_domain_score,
                    original=query,
                    modified=response,
                )
                _aj_decision = gevurah.evaluator.holistic_decision(_aj_multi)

                # Map AutoJudge decision → quality verdict
                _aj_verdict_map = {
                    "accepted": "✓ acceptable",
                    "rejected": "✗ insuffisant",
                    "quarantined": "~ incertain",
                    "tension_detected": "~ incertain (tension)",
                }
                quality_verdict = _aj_verdict_map.get(_aj_decision, "~ incertain")

                signals = [
                    f"gevurah={_aj_multi.gevurah:.2f}",
                    f"chesed={_aj_multi.chesed:.2f}",
                    f"tiferet={_aj_multi.tiferet:.2f}",
                    f"hod={_aj_multi.hod:.2f}",
                    f"yesod={_aj_multi.yesod:.2f}",
                    f"overall={_aj_multi.overall:.2f}",
                    f"decision={_aj_decision}",
                ]
                autojudge_used = True
                log.info(
                    "AutoJudge Gevurah: decision=%s overall=%.3f "
                    "(gevurah=%.2f chesed=%.2f tiferet=%.2f hod=%.2f yesod=%.2f)",
                    _aj_decision, _aj_multi.overall,
                    _aj_multi.gevurah, _aj_multi.chesed,
                    _aj_multi.tiferet, _aj_multi.hod, _aj_multi.yesod,
                )
                ctx["autojudge_multi_score"] = {
                    "gevurah": _aj_multi.gevurah,
                    "chesed": _aj_multi.chesed,
                    "tiferet": _aj_multi.tiferet,
                    "hod": _aj_multi.hod,
                    "yesod": _aj_multi.yesod,
                    "overall": _aj_multi.overall,
                    "decision": _aj_decision,
                }
            except Exception as aj_err:
                log.warning("AutoJudge fallback — %s", aj_err)

            # --- Fallback: heuristique inline si AutoJudge a échoué ---
            if not autojudge_used:
                signals = []
                if response_confidence >= 0.7:
                    signals.append("compétence haute")
                elif response_confidence < 0.3:
                    signals.append("compétence basse")
                if ctx.get("post_consistency", 1.0) >= 0.8:
                    signals.append("cohérent")
                elif ctx.get("post_consistency", 1.0) < 0.5:
                    signals.append("tensions détectées")
                if len(response) < 50:
                    signals.append("réponse courte")
                if len(response) > 2000:
                    signals.append("réponse très longue")

                if (response_confidence >= 0.6
                        and ctx.get("post_consistency", 1.0) >= 0.7):
                    quality_verdict = "✓ acceptable"
                elif (response_confidence < 0.3
                        or ctx.get("post_consistency", 1.0) < 0.4):
                    quality_verdict = "✗ insuffisant"
                else:
                    quality_verdict = "~ incertain"

            _aj_tag = " (AutoJudge)" if autojudge_used else " (heuristique)"
            chozer.append("── ↑⑤ Gevurah — Qualité ──")
            chozer.append(f"  Verdict      : {quality_verdict}{_aj_tag}")
            chozer.append(f"  Signaux      : {', '.join(signals) if signals else 'aucun'}")
            ctx["quality_verdict"] = quality_verdict
            print(f"    verdict={quality_verdict}{_aj_tag}")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑⑤ Gevurah — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── DualSoul : évaluation qualité par l'âme (post-Gevurah) ──
    # Perspective complémentaire à AutoJudge : la bonne âme a-t-elle répondu ?
    try:
        soul_decision = ctx.get("soul_decision")
        if _DUAL_SOUL_ENGINE and soul_decision and response:
            soul_quality = _DUAL_SOUL_ENGINE.assess_response_quality(
                response=response,
                soul_used=soul_decision["dominant_soul"],
            )
            ctx["soul_quality_assessment"] = soul_quality
            chozer.append("── ↑⑤½ DualSoul — Évaluation âme ──")
            chozer.append(f"  Assessment   : {soul_quality['assessment']}")
            chozer.append(f"  Correct soul : {soul_quality['correct_soul']}")
            if soul_quality.get("suggestion"):
                chozer.append(f"  Suggestion   : {soul_quality['suggestion']}")
            log.info(
                "DualSoul assess_response_quality: assessment=%s correct=%s",
                soul_quality["assessment"], soul_quality["correct_soul"],
            )
            print(f"    DualSoul: {soul_quality['assessment']} "
                  f"(correct={soul_quality['correct_soul']})")
    except Exception as e:
        log.warning("DualSoul assess_response_quality: %s", e)

    # ── Sentier Gevurah→Chesed (Teth ט, chozer) ────────────────
    if _sr:
        ctx = _sr.traverse("gevurah", "chesed", ctx, direction="chozer")

    # ── ↑⑥ Chesed : pistes d'exploration ─────────────────────
    _world_emit("ohr_chozer_step", sephirah="chesed", step=6)
    print("  ⟐ ↑⑥ Chesed — détection de pistes...")
    chesed = tree.get("chesed")
    if chesed:
        try:
            domain = (route_decision.detected_domain
                      if route_decision and not route_decision.did_decline
                      else "general")
            explore_result = chesed.explore(query, seed_domain=domain, max_connections=3)
            chozer.append("── ↑⑥ Chesed — Pistes d'exploration ──")
            connections = getattr(explore_result, "connections", []) or []
            for conn in connections:
                desc = conn.description if hasattr(conn, "description") else str(conn)
                chozer.append(f"  ◇ {desc}")
            if hasattr(explore_result, "domains_explored"):
                chozer.append(f"  Domaines     : {explore_result.domains_explored}")
            n_novel = getattr(explore_result, "novel_connections", 0) or 0
            print(f"    {n_novel} connexion(s) nouvelle(s)")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑⑥ Chesed — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── ↑⑥½ Gématria : équivalences dans la réponse ────────────
    # La gématria opérative révèle les connexions cachées entre les
    # termes de la réponse et ceux déjà en mémoire. C'est le Sod
    # (סוֹד) — le sens secret accessible par le calcul des lettres.
    print("  ⟐ ↑⑥½ Gématria — recherche d'équivalences...")
    gematria_engine = tree.get("gematria")
    if gematria_engine and response:
        try:
            from gematria import extract_hebrew_terms
            terms = extract_hebrew_terms(response)
            gematria_hits = []
            for hebrew, translit in terms:
                equivs = gematria_engine.find_equivalences(hebrew, method="standard")
                for eq in equivs:
                    gematria_hits.append(eq)
            if gematria_hits:
                chozer.append("── ↑⑥½ Gématria — Équivalences détectées ──")
                seen_pairs = set()
                for eq in gematria_hits:
                    pair = (eq.term_a, eq.term_b)
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    label_a = f"{eq.term_a}"
                    if eq.translit_a:
                        label_a += f" ({eq.translit_a})"
                    label_b = f"{eq.term_b}"
                    if eq.translit_b:
                        label_b += f" ({eq.translit_b})"
                    chozer.append(
                        f"  ✡ {label_a} = {label_b}  "
                        f"[{eq.method}={eq.shared_value}]"
                    )
                print(f"    {len(seen_pairs)} équivalence(s) gématrique(s) détectée(s)")
            else:
                chozer.append("── ↑⑥½ Gématria — Aucune équivalence dans la réponse ──")
                print("    Aucune équivalence")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑⑥½ Gématria — Erreur: {e} ──")
    else:
        if not gematria_engine:
            print("    ✗ Module non initialisé")
        else:
            print("    Pas de réponse à analyser")

    # ── ↑⑦ Da'at : mise à jour du self-model ────────────────
    _world_emit("ohr_chozer_step", sephirah="daat", step=7)
    print("  ⟐ ↑⑦ Da'at — mise à jour post-réponse...")
    daat = tree.get("daat")
    if daat:
        try:
            state_post = daat.capture_state()
            delta = state_post.model_confidence - ctx.get("daat_pre_confidence", 0.5)
            chozer.append("── ↑⑦ Da'at — Self-model (post) ──")
            chozer.append(f"  Confiance    : {state_post.model_confidence:.2f}")
            chozer.append(f"  Δ confiance  : {delta:+.3f}")
            ctx["daat_delta"] = delta
            print(f"    confiance={state_post.model_confidence:.2f}, Δ={delta:+.3f}")

            # ── Boucle fermée : Da'at vérifie ses propres prédictions ──
            # Si Da'at a prédit un veto/caution, comparer avec le résultat
            # réel (quality_verdict de Gevurah ↑⑤). Ceci FERME LA BOUCLE :
            # Da'at apprend de ses propres prédictions.
            daat_eval = ctx.get("daat_evaluation")
            quality_verdict = ctx.get("quality_verdict", "")
            if daat_eval:
                actual_good = "✓" in quality_verdict
                predicted_veto = daat_eval.get("recommendation") == "veto"
                predicted_caution = daat_eval.get("recommendation") == "caution"

                if predicted_veto and actual_good:
                    chozer.append("  Da'at boucle : veto injustifié (réponse bonne) → assouplir")
                    print(f"    ⟐ Da'at: veto injustifié → à assouplir")
                elif not predicted_veto and not predicted_caution and not actual_good:
                    chozer.append("  Da'at boucle : erreur non prédite → renforcer")
                    print(f"    ⟐ Da'at: erreur non prédite → à renforcer")
                elif (predicted_veto or predicted_caution) and not actual_good:
                    chozer.append("  Da'at boucle : prédiction correcte ✓")
                    print(f"    ⟐ Da'at: prédiction confirmée ✓")
                else:
                    chozer.append("  Da'at boucle : proceed confirmé ✓")

        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑⑦ Da'at — Erreur: {e} ──")
    else:
        print("    ✗ Module non initialisé")

    # ── ↑⑧ Binah : mise à jour causale ───────────────────────
    _world_emit("ohr_chozer_step", sephirah="binah", step=8)
    print("  ⟐ ↑⑧ Binah — détection de claims causales...")
    binah = tree.get("binah")
    if binah and intent.get("type") == "causal":
        try:
            chozer.append("── ↑⑧ Binah — Causalité (post) ──")
            # F211: Extract a causal claim from query and check it.
            # For causal intents the query typically has "cause → effect"
            # structure. We use the query as cause and response summary
            # as effect context for the CausalEngine.
            cause_text = query[:200] if query else ""
            effect_text = response[:200] if response else ""
            if cause_text and effect_text:
                domain = ""
                if route_decision and not route_decision.did_decline:
                    domain = route_decision.detected_domain or ""
                assessment = binah.check_claim(
                    cause=cause_text,
                    effect=effect_text,
                    domain=domain,
                )
                chozer.append(
                    f"  Claim: [{assessment.claim.evidence_level}] "
                    f"conf={assessment.claim.confidence:.2f}, "
                    f"Pearl={assessment.pearl_level}"
                )
                if assessment.warnings:
                    for w in assessment.warnings[:3]:
                        chozer.append(f"  ⚠ {w}")
                print(
                    f"    Claim évalué: {assessment.claim.evidence_level} "
                    f"(conf={assessment.claim.confidence:.2f})"
                )
                ctx["binah_assessment"] = {
                    "evidence_level": assessment.claim.evidence_level,
                    "confidence": assessment.claim.confidence,
                    "pearl_level": assessment.pearl_level,
                    "warnings": assessment.warnings,
                }
            else:
                chozer.append("  Question causale détectée — contenu insuffisant pour évaluer")
                print("    Contenu insuffisant pour évaluation causale")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑⑧ Binah — Erreur: {e} ──")
    else:
        chozer.append("── ↑⑧ Binah — Pas de mise à jour causale nécessaire ──")
        print("    Pas de mise à jour causale")

    # ── Sentier Binah→Chokmah (Daleth ד, chozer) ───────────────
    if _sr:
        ctx = _sr.traverse("binah", "chokmah", ctx, direction="chozer")

    # ── ↑⑨ Chokmah : flag insights + persistance ────────────
    _world_emit("ohr_chozer_step", sephirah="chokmah", step=9)
    print("  ⟐ ↑⑨ Chokmah — flag insights finaux...")
    yesod = tree.get("yesod")
    forge_session = ctx.get("forge_session")
    if yesod and forge_session and forge_session.validated_insights:
        try:
            domain = (route_decision.detected_domain
                      if route_decision and not route_decision.did_decline
                      else "general")
            for ins in forge_session.validated_insights:
                yesod.remember(
                    content=ins.description,
                    source_sephirah="chokmah",
                    confidence=ins.confidence,
                    domain=domain,
                    tags=["insight", "ask-mode", "or-chozer"],
                )
            # ── Nitzotzot : chaque insight validé = une étincelle récupérée ──
            for ins in forge_session.validated_insights:
                desc = ins.description if hasattr(ins, "description") else str(ins)
                _collect_nitzutz(
                    source="chokmah",
                    ntype="insight_validated",
                    description=f"Insight validé (conf={ins.confidence:.2f}): {desc[:150]}",
                    tree=tree,
                )
            chozer.append("── ↑⑨ Chokmah — Insights persistés ──")
            chozer.append(f"  {len(forge_session.validated_insights)} insight(s) sauvegardé(s)")
            chozer.append(f"  ✦ {len(forge_session.validated_insights)} Nitzutz récupérée(s) "
                         f"[{_NITZOTZOT_STATE['count']}/288]")
            if forge_session.emergence_signals:
                chozer.append("  Émergences détectées :")
                for sig in forge_session.emergence_signals:
                    desc = sig.description if hasattr(sig, "description") else str(sig)
                    chozer.append(f"    ◆ {desc}")
            print(f"    {len(forge_session.validated_insights)} insight(s) persisté(s) "
                  f"— {len(forge_session.validated_insights)} Nitzutz")
        except Exception as e:
            print(f"    ⚠ {e}")
            chozer.append(f"── ↑⑨ Chokmah — Erreur: {e} ──")
    else:
        chozer.append("── ↑⑨ Chokmah — Aucun insight à persister ──")
        print("    Aucun insight")


# ═══════════════════════════════════════════════════════════════
#   Block D — Hishtalshelut + Malkuth
# ═══════════════════════════════════════════════════════════════


def _estimate_response_confidence(
    response: str,
    *,
    query: str | None = None,
    domain_competence: float | None = None,
) -> float:
    """Estimer la confiance d'une réponse brute (heuristique rapide, multi-signaux).

    Combine 5 familles de signaux sans appel LLM :
      1. Erreur / incertitude explicite (hard veto)
      2. Couverture sémantique query→response (term overlap)
      3. Structure de la réponse (paragraphes, listes, arguments)
      4. Spécificité (chiffres, dates, citations, termes techniques)
      5. Hedging / langage évasif

    Le score de compétence domaine (SelfMap) pondère le résultat final.
    """
    if not response or len(response.strip()) < 20:
        return 0.1

    text = response.strip()
    low = text.lower()

    # ── Hard vetoes ─────────────────────────────────────────────
    if "[erreur" in low or "error" in low:
        return 0.05

    # Marqueurs d'incertitude forte (aveu d'ignorance)
    ignorance_markers = [
        "je ne sais pas",
        "i don't know",
        "pas sûr",
        "incertain",
        "impossible de",
        "cannot",
        "no information",
        "aucune information",
        "je ne dispose pas",
        "pas en mesure",
        "je n'ai pas accès",
        "au-delà de mes capacités",
        "beyond my capabilities",
        "je ne peux pas répondre",
        "i cannot answer",
    ]
    ignorance_hits = sum(1 for m in ignorance_markers if m in low)
    if ignorance_hits >= 2:
        return 0.15
    if ignorance_hits == 1:
        return 0.20

    # ── Signal 1 : longueur (dégressive, plafonnée) ────────────
    n_chars = len(text)
    if n_chars < 60:
        length_score = 0.15
    elif n_chars < 150:
        length_score = 0.25
    elif n_chars < 400:
        length_score = 0.40
    elif n_chars < 800:
        length_score = 0.50
    else:
        length_score = 0.55  # plafonné — la longueur seule ne suffit plus

    # ── Signal 2 : couverture query→response (term overlap) ────
    overlap_score = 0.0
    if query:
        # Extraire les mots significatifs de la query (>= 4 chars, pas stopwords)
        _stopwords = {
            "dans",
            "avec",
            "pour",
            "plus",
            "cette",
            "quel",
            "quoi",
            "comment",
            "pourquoi",
            "quand",
            "sont",
            "être",
            "avoir",
            "fait",
            "faire",
            "très",
            "aussi",
            "comme",
            "tout",
            "tous",
            "elle",
            "elles",
            "nous",
            "vous",
            "leur",
            "mais",
            "donc",
            "what",
            "that",
            "this",
            "with",
            "from",
            "your",
            "they",
            "have",
            "been",
            "were",
            "will",
            "would",
            "could",
            "should",
        }
        q_words = {
            w
            for w in re.findall(r"[a-zà-ÿ]{4,}", query.lower())
            if w not in _stopwords
        }
        if q_words:
            hits = sum(1 for w in q_words if w in low)
            overlap_score = min(hits / len(q_words), 1.0)  # 0.0–1.0

    # ── Signal 3 : structure (paragraphes, listes, arguments) ──
    paragraphs = [p for p in text.split("\n\n") if len(p.strip()) > 30]
    n_paragraphs = len(paragraphs)

    # Listes à puces / numérotées
    list_items = len(
        re.findall(r"(?m)^[\s]*[-•*]\s+\S|^[\s]*\d+[.)]\s+\S", text)
    )

    if n_paragraphs >= 3 or list_items >= 3:
        structure_score = 0.60
    elif n_paragraphs >= 2 or list_items >= 2:
        structure_score = 0.45
    elif n_paragraphs == 1 and n_chars > 200:
        structure_score = 0.35
    else:
        structure_score = 0.20

    # ── Signal 4 : spécificité (chiffres, dates, citations, technique) ──
    specificity_hits = 0
    # Nombres / pourcentages
    specificity_hits += min(len(re.findall(r"\d+[.,]?\d*\s*%?", text)), 4)
    # Dates (YYYY, siècle, etc.)
    specificity_hits += min(
        len(
            re.findall(
                r"\b(?:1[0-9]{3}|20[0-2][0-9])\b|[IVXL]+e\s+siècle", text
            )
        ),
        3,
    )
    # Citations / guillemets / références
    specificity_hits += min(len(re.findall(r'[«"][^»"]{5,}[»"]', text)), 3)
    # Termes techniques (mots longs, souvent signes de spécificité)
    long_words = re.findall(r"[a-zà-ÿ]{10,}", low)
    specificity_hits += min(len(long_words), 3)

    # Normaliser sur 0.0–0.60
    specificity_score = min(specificity_hits / 10.0, 0.60)

    # ── Signal 5 : hedging / langage évasif ────────────────────
    hedging_markers = [
        "peut-être",
        "il est possible",
        "généralement",
        "en général",
        "probablement",
        "il semble",
        "il semblerait",
        "on pourrait dire",
        "dans une certaine mesure",
        "d'une manière générale",
        "sans certitude",
        "à ma connaissance",
        "perhaps",
        "maybe",
        "possibly",
        "it seems",
        "arguably",
        "in general",
        "roughly",
        "approximately",
        "more or less",
        "plus ou moins",
        "je suppose",
        "i suppose",
        "i guess",
        "je pense que",
        "il me semble",
        "as far as i know",
    ]
    hedge_hits = sum(1 for m in hedging_markers if m in low)
    # Pénalité proportionnelle, plafonnée
    hedge_penalty = min(hedge_hits * 0.06, 0.25)

    # ── Combinaison pondérée ───────────────────────────────────
    # Poids : longueur=0.20, overlap=0.20, structure=0.25,
    #         spécificité=0.25, bonus no-hedge=0.10
    raw_confidence = (
        0.20 * length_score
        + 0.20 * overlap_score
        + 0.25 * structure_score
        + 0.25 * specificity_score
        + 0.10 * (1.0 - hedge_penalty)  # bonus petit si pas de hedging
    )
    # Soustraire la pénalité hedging du total
    raw_confidence = max(raw_confidence - hedge_penalty, 0.05)

    # ── Modulation par compétence domaine (SelfMap) ────────────
    if domain_competence is not None:
        # domain_competence est dans [0.0, 1.0]
        # Si compétence < 0.5 → réduire la confiance significativement
        # Si compétence >= 0.7 → léger boost
        # Facteur multiplicatif :
        #   compétence=0.0 → factor=0.5
        #   compétence=0.5 → factor=1.0
        #   compétence=0.7 → factor=1.0
        #   compétence=1.0 → factor=1.1
        if domain_competence < 0.5:
            competence_factor = 0.5 + domain_competence  # 0.5–1.0
        elif domain_competence < 0.7:
            competence_factor = 1.0
        else:
            competence_factor = 1.0 + (domain_competence - 0.7) * 0.33  # 1.0–1.1
        raw_confidence *= competence_factor

    return round(min(max(raw_confidence, 0.05), 0.95), 3)


def _gather_tree_signals(tree: dict, query: str) -> dict:
    """Collecter les signaux de l'Arbre pour les 29 dimensions du Kli.

    Ces signaux alimentent les 9 dimensions qui dépendent des modules
    de l'Arbre (02-07, 10, 11, 26) sans import circulaire.
    Chaque signal est collecté en best-effort — un échec n'empêche
    pas les autres de fonctionner.
    """
    signals: dict = {}

    # Dim 02 — Din Kadmon (profil actif = biais architectural)
    try:
        from olamot import _load_config
        cfg = _load_config()
        signals["active_profile"] = cfg.get("active_profile", "")
    except Exception as e:
        log.debug("fallback: %s", e)

    # Dim 03 — Sovev (contexte transcendant : context_window + thinking)
    try:
        from olamot import get_context_window, get_think
        signals["context_window"] = get_context_window("briah")
        signals["model_think"] = get_think("briah")
    except Exception as e:
        log.debug("fallback: %s", e)

    # Dim 04 — Reshimu (modèle = substrat)
    try:
        from olamot import get_model
        signals["model_name"] = get_model("briah")
    except Exception as e:
        log.debug("fallback: %s", e)

    # Dim 05 — Keter (intention active avec critère de succès)
    netzach = tree.get("netzach")
    if netzach and hasattr(netzach, "db"):
        try:
            active = netzach.db.get_active_intentions()
            if active:
                intent = active[0]
                signals["active_intention"] = {
                    "satisfaction_criterion": getattr(intent, "satisfaction_criterion", None)
                    or getattr(intent, "goal", None),
                }
        except Exception as e:
            log.debug("fallback: %s", e)

    # Dim 06 — Hokhmah (insights récents)
    chokmah = tree.get("chokmah")
    if chokmah and hasattr(chokmah, "read_recent_insights"):
        try:
            insights = chokmah.read_recent_insights(limit=3)
            if insights:
                signals["recent_insights"] = [
                    {"novelty_score": getattr(i, "novelty_score", 0.5)}
                    for i in insights
                ]
        except Exception as e:
            log.debug("fallback: %s", e)

    # Dim 07 — Binah (confiance causale)
    binah = tree.get("binah")
    if binah and hasattr(binah, "last_confidence"):
        try:
            signals["causal_confidence"] = binah.last_confidence
        except Exception as e:
            log.debug("fallback: %s", e)

    # Dim 10 — Tiferet (tensions non résolues)
    tiferet = tree.get("tiferet")
    if tiferet and hasattr(tiferet, "db"):
        try:
            tensions = tiferet.db.get_unresolved(limit=10)
            signals["unresolved_tensions"] = len(tensions) if tensions else 0
        except Exception as e:
            log.debug("fallback: %s", e)

    # Dim 11 — Netzach/Hod (progrès + compétence domaine)
    if netzach and hasattr(netzach, "db"):
        try:
            active = netzach.db.get_active_intentions()
            if active:
                progress = netzach.check_progress(active[0].id)
                if progress:
                    signals["intent_progress"] = getattr(progress, "completion_ratio", 0)
        except Exception as e:
            log.debug("fallback: %s", e)

    hod = tree.get("hod")
    if hod and hasattr(hod, "get_competence"):
        try:
            _domain, score = hod.get_competence(query)
            signals["domain_competence"] = score
        except Exception as e:
            log.debug("fallback: %s", e)

    # Dim 26 — Ibbur (skills/shemot disponibles)
    try:
        from shemot import list_shemot
        signals["active_skills_count"] = len(list_shemot())
    except Exception as e:
        log.debug("fallback: %s", e)

    return signals


def _ascend_and_generate(
    prompt: str,
    start_world: str,
    query: str,
    timeout: int = 300,
    confidence_threshold: float = 0.4,
    pressure_regulated: bool = False,
    daemon_block: str | None = None,
    tree_signals: dict | None = None,
) -> tuple[str, str, float, list[dict]]:
    """סֵדֶר הִשְׁתַּלְשְׁלוּת — Montée automatique des mondes.

    Commence au monde start_world. Si la confiance de la réponse
    est < confidence_threshold, monte au monde suivant.
    Le Malkuth du monde supérieur devient le Keter du monde inférieur.

    Args:
        daemon_block: Contenu DaemonBridge pre-formate, soumis au
            budget Masakh total (F6 — EC-SHK-023).

    Returns:
        (response, final_world, confidence, ascent_log)
    """
    from olamot import ollama_generate, get_provider
    import os as _os

    chain = _OLAMOT_CHAIN
    start_idx = chain.index(start_world) if start_world in chain else 0
    ascent_log = []

    current_world = chain[start_idx]
    best_response = ""
    best_confidence = 0.0
    best_world = current_world

    for idx in range(start_idx, len(chain)):
        current_world = chain[idx]

        # Vérifier que le monde est accessible
        if current_world == "atziluth":
            provider = get_provider("atziluth")
            if provider == "anthropic" and not _os.environ.get("ANTHROPIC_API_KEY"):
                ascent_log.append({
                    "world": current_world,
                    "status": "skipped",
                    "reason": "no ANTHROPIC_API_KEY",
                })
                continue

        # Générer dans ce monde
        try:
            ascent_kavvanah = {
                "intention": f"Monter au niveau {current_world} — chercher une réponse de confiance ≥ {confidence_threshold}",
                "critere_succes": f"réponse avec confiance suffisante au niveau {current_world}",
                "anti_pattern": "ne pas produire une réponse générique qui justifierait une montée inutile",
            }
            response, latency = ollama_generate(current_world, prompt, timeout=timeout,
                                                   kavvanah=ascent_kavvanah,
                                                   pressure_regulated=pressure_regulated,
                                                   daemon_block=daemon_block,
                                                   tree_signals=tree_signals)
            _dc = (tree_signals or {}).get("domain_competence")
            confidence = _estimate_response_confidence(
                response, query=query, domain_competence=_dc
            )

            ascent_log.append({
                "world": current_world,
                "status": "ok",
                "confidence": confidence,
                "latency_ms": latency,
                "response_len": len(response),
            })

            # Garder la meilleure réponse
            if confidence > best_confidence:
                best_response = response
                best_confidence = confidence
                best_world = current_world

            # Confiance suffisante → on s'arrête
            if confidence >= confidence_threshold:
                break

            # Confiance insuffisante → on monte
            if idx < len(chain) - 1:
                next_world = chain[idx + 1]
                _log_world_transition(
                    "ascent", current_world, next_world,
                    f"confiance {current_world}={confidence:.2f} < {confidence_threshold}",
                    query,
                )
                # Le résultat de ce monde devient le contexte du suivant
                # (Malkuth du supérieur = Keter de l'inférieur)
                prompt = f"""[Contexte du monde inférieur ({current_world}) — confiance={confidence:.2f}]
{response[:500]}

[Instruction: La réponse ci-dessus vient d'un monde inférieur et manque de profondeur.
Réponds avec plus de rigueur et de détail.]

{prompt}"""

        except Exception as e:
            ascent_log.append({
                "world": current_world,
                "status": "error",
                "error": str(e)[:200],
            })
            # Erreur → on monte si possible
            if idx < len(chain) - 1:
                next_world = chain[idx + 1]
                _log_world_transition(
                    "ascent", current_world, next_world,
                    f"erreur dans {current_world}: {str(e)[:100]}",
                    query,
                )

    return best_response, best_world, best_confidence, ascent_log


def _translate_descent(
    tree: dict,
    response: str,
    source_world: str,
    query: str,
) -> list[dict]:
    """Descente des insights — traduction pour les mondes inférieurs.

    Les insights trouvés en Briah sont condensés et stockés
    pour être utilisables en Yetzirah et Assiah.
    Le Malkuth d'un monde supérieur = le Keter du monde inférieur.

    Returns:
        Liste de dicts {world, condensed, stored_id}
    """
    from olamot import ollama_generate

    chain = _OLAMOT_CHAIN
    source_idx = chain.index(source_world) if source_world in chain else 0
    descent_results = []

    # Pas de descente si on est déjà au plus bas
    if source_idx == 0:
        return descent_results

    # Pour chaque monde inférieur, condenser l'insight
    current_text = response
    for idx in range(source_idx - 1, -1, -1):
        target_world = chain[idx]

        _log_world_transition(
            "descent", chain[idx + 1], target_world,
            f"traduction {chain[idx + 1]}→{target_world}",
            query,
        )

        # Condenser via le monde cible (le modèle léger résume)
        condense_prompt = f"""Condense the following insight into a shorter, simpler version.
Keep only the essential information. Be concise (max 3 sentences).
Tag: [from:{source_world}]

Insight to condense:
{current_text[:800]}

Condensed version:"""

        try:
            condensed, _ = ollama_generate(
                target_world, condense_prompt, timeout=60,
                kavvanah={
                    "intention": f"Condenser l'insight de {source_world} pour {target_world}",
                    "critere_succes": "Essentiel préservé en 3 phrases maximum",
                    "anti_pattern": "Ne pas perdre le coeur de l'insight par sur-simplification",
                },
                context_items=[f"Traduction {source_world}→{target_world}"],
                principles=[f"Le Malkuth du monde supérieur = le Keter du monde inférieur"],
            )
            condensed = f"[from:{source_world}→{target_world}] {condensed.strip()}"
        except Exception:
            condensed = f"[from:{source_world}→{target_world}] {current_text[:200]}"

        # Stocker en mémoire avec tag du monde d'origine
        stored_id = None
        yesod = tree.get("yesod")
        if yesod:
            try:
                stored_id = yesod.remember(
                    content=f"[Hishtalshelut {source_world}→{target_world}] {condensed[:300]}",
                    source_sephirah="malkuth",
                    confidence=0.6,
                    domain="general",
                    tags=["hishtalshelut", f"from:{source_world}", f"for:{target_world}"],
                )
            except Exception as e:
                log.debug("fallback: %s", e)

        descent_results.append({
            "world": target_world,
            "condensed": condensed[:300],
            "stored_id": str(stored_id) if stored_id else None,
        })

        current_text = condensed

    return descent_results


def _generate_malkuth_response(tree: dict, query: str, ctx: dict) -> str:
    """Malkuth — génération de la réponse brute à partir du contexte accumulé.

    מַלְכוּת — Le royaume reçoit tout d'en haut et le manifeste.
    La réponse est la cristallisation de tout le flux descendant.
    """
    from olamot import ollama_generate

    # Assembler le contexte de la descente
    parts = []

    # Keter : intention
    intent = ctx.get("intent", {})
    parts.append(f"[Intent: type={intent.get('type', '?')}, depth={intent.get('depth', '?')}]")

    # Chokmah : insights
    forge_session = ctx.get("forge_session")
    if forge_session and forge_session.validated_insights:
        parts.append("[Insights from forge:]")
        for ins in forge_session.validated_insights:
            parts.append(f"  - [{ins.confidence:.2f}] {ins.description}")

    # Binah : état causal
    binah_diag = ctx.get("binah_diag")
    if binah_diag and binah_diag.get("total_graphs", 0) > 0:
        parts.append(f"[Causal context: {binah_diag['total_graphs']} graph(s), "
                     f"{binah_diag.get('total_claims', 0)} claim(s)]")

    # Da'at : self-model
    daat_state = ctx.get("daat_state")
    if daat_state:
        parts.append(f"[Self-model confidence: {daat_state.model_confidence:.2f}]")
        if hasattr(daat_state, "known_biases") and daat_state.known_biases:
            parts.append(f"[Known biases: {len(daat_state.known_biases)}]")

    # Da'at : VETO ou CAUTION — le Gardien modifie le prompt
    if ctx.get("daat_veto"):
        parts.append("[IMPORTANT — Da'at VETO : confiance très faible sur ce sujet.]")
        parts.append(f"  Raison : {ctx.get('daat_veto_reason', '?')}")
        parts.append("  INSTRUCTION : Sois transparent sur les limites. "
                     "Préfère dire 'je ne sais pas' plutôt que risquer "
                     "une réponse incorrecte.")
        _veto_biases = ctx.get("daat_known_biases", [])
        if _veto_biases:
            parts.append("  Biais connus : " + ", ".join(
                b.get("type", "?") for b in _veto_biases[:3]
            ))
    elif ctx.get("daat_caution"):
        parts.append("[Note — Da'at CAUTION : confiance modérée sur ce sujet.]")
        parts.append(f"  Raison : {ctx.get('daat_caution_reason', '?')}")
        parts.append("  INSTRUCTION : Nuance tes affirmations. "
                     "Mentionne les incertitudes.")

    # Da'at Bridge : Dvekut/Kishur/Kolel — pont connaissance↔application
    # `route` est assigné plus bas (section Hod) ; on lit ctx directement
    # ici pour que ce bloc soit auto-suffisant, sinon Python promeut `route`
    # en variable locale et lève UnboundLocalError (cf. Sprint 8d).
    try:
        from daat_bridge import DaatBridge
        from pool import get_conn
        _daat_bridge = DaatBridge(db_pool_fn=get_conn)
        _route_decision = ctx.get("route_decision")
        _bridge_domain = (_route_decision.detected_domain
                          if _route_decision and not _route_decision.did_decline
                          else None)
        _bridge_facts = []
        for m in ctx.get("memories", []):
            content = m.content[:200] if hasattr(m, "content") else str(m)[:200]
            _bridge_facts.append(content)
        _bridge_block = _daat_bridge.build(
            question=query,
            domain=_bridge_domain,
            facts=_bridge_facts,
            kavvanah=ctx.get("kavvanah"),
        )
        if _bridge_block:
            parts.append(_bridge_block)
    except Exception as e:
        log.warning("DaatBridge skipped: %s", e)

    # Tiferet : tensions
    tiferet_diag = ctx.get("tiferet_diag")
    if tiferet_diag and tiferet_diag.get("open_tensions", 0) > 0:
        parts.append(f"[Open tensions: {tiferet_diag['open_tensions']}, "
                     f"irreducible: {tiferet_diag.get('irreducible', 0)}]")

    # Hod : compétence
    route = ctx.get("route_decision")
    if route and not route.did_decline:
        parts.append(f"[Domain: {route.detected_domain}, "
                     f"competence: {route.competence_score:.2f}]")
    elif route and route.did_decline:
        parts.append(f"[DECLINED: {route.decline_reason}]")

    # Mochin dispatch — influx des Sephiroth supérieures
    mochin_dispatch = ctx.get("mochin_dispatch", {})
    if mochin_dispatch and mochin_dispatch.get("routes"):
        parts.append("[Mochin — influx des Sephiroth supérieures:]")
        # Variable de loop préfixée `_mochin_route` pour NE PAS shadow
        # la variable `route` (RouteDecision) assignée ligne 2359 et
        # consommée ligne ~2556 par le bloc Dira BeTachtonim.
        # Cf. Sprint 8e — avant le fix, cette loop écrasait `route` avec
        # des strings, cassant silencieusement l'optimisation Dira.
        for _mochin_route in mochin_dispatch["routes"]:
            parts.append(f"  - {_mochin_route}")
        # Faiblesses prédites (Da'at → Tiferet)
        tiferet_m = mochin_dispatch.get("binah_to_tiferet", {})
        if tiferet_m.get("predicted_weaknesses"):
            parts.append("[Faiblesses prédites:]")
            for w in tiferet_m["predicted_weaknesses"]:
                parts.append(f"  - {w}")
        # Biais actifs (Da'at → Gevurah)
        gevurah_m = mochin_dispatch.get("binah_to_gevurah", {})
        if gevurah_m.get("active_biases"):
            parts.append(f"[Active biases: {', '.join(gevurah_m['active_biases'])}]")

    # Zivug Abba-Imma : insights raffinés par validation causale
    zivug_ai = ctx.get("zivug_abba_imma", [])
    if zivug_ai:
        parts.append("[Zivug Abba-Imma — insights validés causalement:]")
        for z in zivug_ai:
            parts.append(f"  - [{z['refined_confidence']:.2f}] {z['insight']} "
                        f"(Pearl={z['pearl_level']}, dir={z['direction']})")
            if z.get("warnings"):
                for w in z["warnings"][:2]:
                    parts.append(f"    ⚠ {w}")

    # Tzimtzum : état de contraction/expansion
    if ctx.get("tzimtzum_active"):
        parts.append(f"[TZIMTZUM ACTIF — focus={ctx.get('tzimtzum_focused_domain', '?')}]")
        excluded = ctx.get("tzimtzum_excluded", [])
        if excluded:
            parts.append(f"  Domaines exclus temporairement: {', '.join(excluded[:5])}")
        parts.append("  INSTRUCTION: Concentrer la réponse sur le domaine focal. "
                     "Ne pas explorer les connexions inter-domaines.")
    elif ctx.get("hitpashut_recovered"):
        recovered = ctx["hitpashut_recovered"]
        parts.append(f"[HITPASHUT — expansion depuis {ctx.get('hitpashut_from', '?')}]")
        parts.append(f"  Domaines récupérés du Reshimu: {', '.join(recovered[:5])}")
        parts.append("  INSTRUCTION: Intégrer les domaines récupérés dans la réponse.")

    # Netzach : intentions
    active_intents = ctx.get("active_intentions", [])
    if active_intents:
        parts.append("[Active intentions:]")
        for intent_obj in active_intents[:3]:
            parts.append(f"  - {intent_obj.goal} ({intent_obj.progress:.0%})")

    # Yesod : mémoire
    # Vecteur d'empoisonnement persistant : des mémoires importées via
    # /api/import peuvent contenir des patterns d'injection qui seraient
    # réinjectés dans le prompt sans filtrage. guard_memory() neutralise
    # les patterns high/medium et préfixe [UNTRUSTED_MEMORY] en cas de
    # détection high. max_len=200 correspond au cap existant.
    memories = ctx.get("memories", [])
    if memories:
        from malakhim.adversarial.prompt_guard import guard_memory
        parts.append("[Relevant memories:]")
        for m in memories:
            raw = m.content if hasattr(m, "content") else str(m)
            conf = m.confidence if hasattr(m, "confidence") else 0.0
            content, _suspect = guard_memory(raw, max_len=200)
            parts.append(f"  - [{conf:.1f}] {content}")

    # Sifrei Yesod : assertions doctrinales EC-*
    sy_assertions = ctx.get("sifrei_yesod_assertions", [])
    if sy_assertions:
        parts.append("[Doctrine — Sifrei Yesod assertions:]")
        for sa in sy_assertions:
            aid = sa.get("assertion_id", "?")
            text = sa.get("assertion", "")[:200]
            sim = sa.get("similarity", 0.0)
            atype = sa.get("assertion_type", "")
            parts.append(f"  - [{aid}] ({atype}, sim={sim:.2f}) {text}")

    # Hybrid Retrieval : connexions Cube de l'Espace + ML
    hybrid_text = ctx.get("hybrid_retrieval", "")
    if hybrid_text:
        parts.append(f"[Structural connections (Cube + ML):]")
        parts.append(hybrid_text)

    # Daemon Bridge : Mokhin du travail nocturne
    # F6 — Le contenu DaemonBridge est passe SEPAREMENT au pipeline
    # Masakh via daemon_block, et non plus injecte directement dans
    # parts. Ainsi il est soumis au budget Masakh total.
    daemon_block: str | None = None
    daemon_enrich = ctx.get("daemon_enrichment")
    if daemon_enrich:
        from daemon_bridge import format_daemon_enrichment
        daemon_text = format_daemon_enrichment(daemon_enrich)
        if daemon_text:
            daemon_block = daemon_text

    descent_context = "\n".join(parts)

    # ── Seder Hishtalshelut : déterminer le monde de départ ──
    forced = _HISHTALSHELUT_STATE.get("forced_world")
    if forced:
        start_world = forced
    else:
        # Profondeur requise par Keter détermine le monde minimum
        depth = intent.get("depth", "yetzirah")
        if depth == "briah":
            start_world = "yetzirah"  # commence un cran en-dessous, laisse monter
        else:
            start_world = "assiah"    # commence au plus bas

    # ── Tanya override : moach shalit al halev ──────────────
    # Le DualSoulEngine recommande un monde basé sur la complexité
    # de la requête. Son recommended_olam est un HINT :
    # - Haute confiance (complexity >= 0.6) → appliquer le hint
    # - Basse confiance → fallthrough au routing existant
    # - Conflits avec d'autres signaux → log mais ne pas casser
    soul_decision = ctx.get("soul_decision")
    try:
        if soul_decision:
            _soul_olam = soul_decision["recommended_olam"]
            _soul_conf = soul_decision["complexity_score"]
            _soul_dom = soul_decision["dominant_soul"]
            _chain = ["assiah", "yetzirah", "briah", "atziluth"]
            _current_idx = _chain.index(start_world) if start_world in _chain else 0
            _soul_idx = _chain.index(_soul_olam) if _soul_olam in _chain else _current_idx

            log.info(
                "Tanya soul routing: dominant=%s, recommended_olam=%s, "
                "complexity=%.2f, current_start=%s",
                _soul_dom, _soul_olam, _soul_conf, start_world,
            )

            # High confidence threshold — only apply hint above this
            _SOUL_CONFIDENCE_THRESHOLD = 0.5

            if _soul_conf >= _SOUL_CONFIDENCE_THRESHOLD:
                if _soul_dom == "elokit" and _soul_idx > _current_idx:
                    # Elokit recommends going HIGHER — apply upward hint
                    start_world = _soul_olam
                    ctx["tanya_override"] = True
                    ctx["tanya_override_from"] = _chain[_current_idx]
                    log.info(
                        "Tanya override: %s -> %s (elokit, conf=%.2f)",
                        _chain[_current_idx], _soul_olam, _soul_conf,
                    )
                elif _soul_dom == "behamit" and _soul_idx < _current_idx:
                    # Behamit recommends going LOWER — apply downward hint
                    # (saves resources when the soul says it's simple)
                    start_world = _soul_olam
                    ctx["tanya_override"] = True
                    ctx["tanya_override_from"] = _chain[_current_idx]
                    log.info(
                        "Tanya override: %s -> %s (behamit, conf=%.2f)",
                        _chain[_current_idx], _soul_olam, _soul_conf,
                    )
                else:
                    log.info(
                        "Tanya soul routing agrees with current world "
                        "or no change needed (soul=%s, current=%s)",
                        _soul_olam, start_world,
                    )

                # Detect conflicts with intent depth
                _intent_depth = intent.get("depth", "yetzirah")
                if (_soul_dom == "elokit" and _soul_olam in ("briah", "atziluth")
                        and _intent_depth not in ("briah", "atziluth")):
                    log.info(
                        "Tanya/Intent conflict: soul recommends %s "
                        "but intent depth=%s — soul hint applied",
                        _soul_olam, _intent_depth,
                    )
                    ctx["tanya_intent_conflict"] = {
                        "soul_olam": _soul_olam,
                        "intent_depth": _intent_depth,
                        "resolved": "soul_applied",
                    }
            else:
                log.info(
                    "Tanya soul routing low confidence (%.2f < %.2f) — "
                    "falling through to existing logic",
                    _soul_conf, _SOUL_CONFIDENCE_THRESHOLD,
                )
    except Exception as e:
        log.warning("Tanya soul routing failed (non-fatal): %s", e)

    # ── Dira BeTachtonim : le haut a-t-il déjà descendu ? ──
    # Si assez de mémoires dira existent pour ce domaine,
    # les mondes inférieurs peuvent suffire → pas besoin de monter.
    yesod_inst = tree.get("yesod")
    if yesod_inst and start_world in ("briah", "atziluth"):
        try:
            dira = _get_dira_engine(yesod_inst)
            # Auto-suffisance défensive : on relit route_decision depuis
            # ctx (plutôt que d'utiliser `route` de la section Hod) pour
            # rester robuste si une loop shadowait `route` entre-temps.
            # Pattern cohérent avec le fix Sprint 8d (DaatBridge).
            _route_decision = ctx.get("route_decision")
            dira_domain = (_route_decision.detected_domain
                           if _route_decision and not _route_decision.did_decline
                           else None)
            if not dira.should_invoke_atzilut(query, domain=dira_domain):
                # Le savoir a déjà descendu — commencer plus bas
                start_world = "yetzirah"
                ctx["dira_optimization"] = True
                ctx["dira_optimized_from"] = "briah"
        except Exception as e:
            # Élevé de debug à warning (Sprint 8e) : une erreur ici
            # signifie que l'optimisation Dira n'a pas fonctionné et
            # que le système monte à Atzilut par défaut (coût LLM).
            # On veut le voir en production.
            log.warning("Dira optimization skipped: %s", e)

    # ── Da'at Guardian : veto/proceed modifie la génération ──
    # Veto = le système sait qu'il ne sait pas → économiser (assiah),
    #         contraindre (timeout réduit), et préfixer la réponse.
    # Proceed = confiance haute → seuil de confiance abaissé (plus direct).
    if ctx.get("daat_veto"):
        start_world = "assiah"
        ctx["daat_forced_assiah"] = True
    elif ctx.get("daat_evaluation", {}).get("recommendation") == "proceed":
        ctx["daat_proceed"] = True

    # ── Partzufim Regulator : Nukva modifie Malkuth ─────────
    # Nukva habille Malkuth — en katnut/akhor, la génération est contrainte.
    nukva_mod = ctx.get("partzuf_modifiers", {}).get("malkuth", {})
    nukva_capacity = nukva_mod.get("capacity", 1.0) if nukva_mod else 1.0
    nukva_threshold = nukva_mod.get("threshold", 0.0) if nukva_mod else 0.0
    generation_timeout = max(60, int(300 * nukva_capacity))
    generation_conf_threshold = min(0.8, 0.4 + nukva_threshold)

    # Da'at ajustements finaux sur les paramètres de génération
    if ctx.get("daat_veto"):
        generation_timeout = min(generation_timeout, 60)
        generation_conf_threshold = 0.2  # accepter réponse minimale
    elif ctx.get("daat_proceed"):
        generation_conf_threshold = max(0.3, generation_conf_threshold - 0.1)

    # ── Partzufim summary pour le prompt ─────────────────────
    partzuf_state = ctx.get("partzuf_state", {})
    if partzuf_state:
        non_optimal = {k: v for k, v in partzuf_state.items()
                       if v.get("mochin_state") != "gadlut" or v.get("orientation") != "panim"}
        if non_optimal:
            parts.append("[Partzufim — modules non-optimaux :]")
            for pname, ps in non_optimal.items():
                parts.append(f"  - {pname}: {ps.get('mochin_state', '?')}/{ps.get('orientation', '?')} "
                            f"(score={ps.get('overall', 0):.2f})")
            parts.append("  INSTRUCTION: Ajuste la profondeur à la capacité actuelle du système.")

    prompt = f"""You are Etz Chaim, a cognitive architecture modeled on the kabbalistic Tree of Life.
You answer in French, with depth and precision. You are direct — no filler.

Context gathered from the Tree's descent (Or Yashar):
{descent_context}

User question: {query}
Response:"""

    # ── Signaux de l'Arbre pour les 29 dimensions du Kli ─────
    # Ces signaux permettent au ContextMonitor de mesurer les 9 dims
    # qui dépendent des modules de l'Arbre (02-07, 10, 11, 26).
    _tree_signals = _gather_tree_signals(tree, query)

    # ── Montée automatique des mondes ────────────────────────
    response, final_world, confidence, ascent_log = _ascend_and_generate(
        prompt=prompt,
        start_world=start_world,
        query=query,
        timeout=generation_timeout,
        confidence_threshold=generation_conf_threshold,
        pressure_regulated=ctx.get("pressure_regulated", False),
        daemon_block=daemon_block,
        tree_signals=_tree_signals,
    )

    # Stocker les infos de génération dans le contexte
    total_latency = sum(
        a.get("latency_ms", 0) for a in ascent_log if a.get("status") == "ok"
    )
    ctx["generation_olam"] = final_world
    ctx["generation_latency"] = total_latency
    ctx["generation_confidence"] = confidence
    ctx["hishtalshelut_log"] = ascent_log
    ctx["hishtalshelut_start"] = start_world
    ctx["hishtalshelut_final"] = final_world
    ctx["hishtalshelut_ascents"] = sum(
        1 for a in ascent_log if a.get("status") == "ok"
    ) - 1  # -1 car le premier n'est pas une montée

    # ── Descente des insights si on a monté ──────────────────
    if final_world != start_world and final_world != "assiah":
        descent_results = _translate_descent(tree, response, final_world, query)
        ctx["hishtalshelut_descent"] = descent_results
    else:
        ctx["hishtalshelut_descent"] = []

    if not response:
        return f"[Erreur génération — aucun monde n'a pu répondre]"

    # ── Da'at post-génération ────────────────────────────────
    # Veto : préfixer la réponse avec un avertissement transparent.
    # L'honnêteté épistémique est le fondement de Da'at.
    if ctx.get("daat_veto"):
        veto_reason = ctx.get("daat_veto_reason", "confiance insuffisante")
        response = (
            f"⚠ **Avertissement Da'at** : ma confiance sur ce sujet est faible "
            f"({veto_reason}). La réponse ci-dessous peut contenir des erreurs.\n\n"
            + response
        )

    return response
