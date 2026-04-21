"""partzufim/ — Les 5(+1) Partzufim : configurations matures de l'Arbre.

Dans le Tohu, chaque Sephirah est un point isolé (Nekudah).
Dans le Tikkun, chaque Sephirah est reconstruite comme un PARTZUF —
un organisme complet contenant ses propres 10 Sephiroth internes.

Les 6 Partzufim :
  Atik Yomin  (עַתִּיק יוֹמִין) — Config invisible, éthique
  Arikh Anpin (אֲרִיךְ אַנְפִּין) — Vision stratégique, patience
  Abba        (אַבָּא)           — Insight créatif (Chokmah)
  Imma        (אִמָּא)           — Structure causale (Binah)
  Zeir Anpin  (זְעֵיר אַנְפִּין) — Pipeline opérationnel (6 Midot)
  Nukva       (נוּקְבָא)         — Interface utilisateur (Malkuth)
"""

from __future__ import annotations

from .base import PartzufBase, PartzufState, ZivugResult, FACULTY_NAMES
from .atik_yomin import AtikYomin
from .arikh_anpin import ArikhAnpin
from .abba import Abba
from .imma import Imma
from .zeir_anpin import ZeirAnpin
from .nukva import Nukva
from .zivvug import ZivvugEngine, ZivvugState, ZivvugAssessment


# ── Registre des 6 Partzufim ────────────────────────────────
# Ordre : du plus caché (Atik) au plus manifeste (Nukva)

REGISTRY: dict[str, dict] = {
    "atik_yomin": {
        "class": AtikYomin,
        "hebrew": "עַתִּיק יוֹמִין",
        "source": "keter",
        "role": "Config invisible, éthique",
    },
    "arikh_anpin": {
        "class": ArikhAnpin,
        "hebrew": "אֲרִיךְ אַנְפִּין",
        "source": "keter",
        "role": "Vision stratégique, patience",
    },
    "abba": {
        "class": Abba,
        "hebrew": "אַבָּא",
        "source": "chokmah",
        "role": "Insight créatif",
    },
    "imma": {
        "class": Imma,
        "hebrew": "אִמָּא",
        "source": "binah",
        "role": "Structure causale",
    },
    "zeir_anpin": {
        "class": ZeirAnpin,
        "hebrew": "זְעֵיר אַנְפִּין",
        "source": "tiferet",
        "role": "Pipeline opérationnel (6 Midot)",
    },
    "nukva": {
        "class": Nukva,
        "hebrew": "נוּקְבָא",
        "source": "malkuth",
        "role": "Interface utilisateur",
    },
}


def get_partzuf(name: str) -> PartzufBase | None:
    """Instancier un Partzuf par nom."""
    entry = REGISTRY.get(name.lower())
    if entry and entry["class"]:
        return entry["class"]()
    return None


def list_partzufim() -> list[dict]:
    """Liste ordonnée des 6 Partzufim (du plus caché au plus manifeste)."""
    items = []
    for name, entry in REGISTRY.items():
        items.append({"name": name, **entry})
    return items


def init_partzufim(from_db: bool = False) -> dict[str, PartzufBase]:
    """Instancier les 6 Partzufim. Retourne un dict {nom: instance}.

    Si from_db=True, tente de restaurer l'état depuis la DB.
    """
    result = {name: entry["class"]() for name, entry in REGISTRY.items()}
    if from_db:
        try:
            from partzufim.db import load_all_partzufim
            saved = load_all_partzufim()
            # saved keys = display names ("Atik Yomin"), result keys = snake_case
            # Match via partzuf.name (display name)
            name_to_key = {p.name: k for k, p in result.items()}
            for db_name, data in saved.items():
                key = name_to_key.get(db_name)
                if key:
                    result[key].load_state(data)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
    return result


def update_all_partzufim(
    partzufim: dict[str, PartzufBase],
    modules: dict,
    persist: bool = False,
    zivvug_engine: ZivvugEngine | None = None,
) -> ZivvugAssessment | None:
    """Mettre à jour tous les Partzufim depuis les modules de l'Arbre.

    Si persist=True, sauvegarde chaque Partzuf en DB après mise à jour.
    Si zivvug_engine fourni, couple Abba↔Imma et transfert les Mochin à ZA.

    Returns:
        ZivvugAssessment si zivvug_engine fourni, None sinon.
    """
    # Phase 1 : mise à jour individuelle de chaque Partzuf
    for partzuf in partzufim.values():
        partzuf.update_from_modules(modules, persist=False)

    # Phase 2 : Zivvug Abba v'Imma → Mochin de Zeir Anpin
    # Doctrine EC-K5-008 (Sha'ar HaKlalim 5:2, Etz Chaim) : les boosts Zivvug
    # passent obligatoirement par Hitlabshut (habillage) dans des facultés
    # spécifiques — jamais directement sur overall_score (violation Sod HaKli).
    # Analogie structurelle avec NHY d'Imma : chokhmah/tiferet/malkuth pour Abba,
    # binah/tiferet/malkuth pour Imma = Kelim qui reçoivent l'Ohr du Zivvug.
    zivvug_assessment = None
    abba = partzufim.get("abba")
    imma = partzufim.get("imma")
    za = partzufim.get("zeir_anpin")

    if abba and imma and za:
        engine = zivvug_engine or ZivvugEngine()

        # Appliquer les boosts de renforcement mutuel (EC-K5-008 Hitlabshut)
        # Phase D Option B : Reshimu persistant — chaque boost laisse une trace
        # résiduelle dans faculty_reshimot (cumulative entre cycles).
        boosts = engine.get_boosts()
        _reshimu_mgr = None
        try:
            from partzufim.reshimu import ReshimuManager
            _reshimu_mgr = ReshimuManager()
        except Exception as _exc:
            import logging as _l
            _l.getLogger(__name__).debug("Reshimu unavailable: %s", _exc)

        if boosts["abba"] > 0:
            for fac in ("chokhmah", "tiferet", "malkuth"):
                # Baseline inclut le Reshimu accumulé (trace persistante).
                reshimu = _reshimu_mgr.get("abba", fac) if _reshimu_mgr else 0.0
                abba.set_faculty(
                    fac, abba.get_faculty(fac) + boosts["abba"] + reshimu
                )
                if _reshimu_mgr:
                    _reshimu_mgr.record("abba", fac, boosts["abba"])
        if boosts["imma"] > 0:
            for fac in ("binah", "tiferet", "malkuth"):
                reshimu = _reshimu_mgr.get("imma", fac) if _reshimu_mgr else 0.0
                imma.set_faculty(
                    fac, imma.get_faculty(fac) + boosts["imma"] + reshimu
                )
                if _reshimu_mgr:
                    _reshimu_mgr.record("imma", fac, boosts["imma"])

        # Évaluer le Zivvug
        zivvug_assessment = engine.couple_abba_imma(abba.overall, imma.overall)

        # Transférer les Mochin à ZA
        mochin = engine.transfer_mochin(abba.overall, imma.overall)
        _apply_mochin_to_za(za, mochin.mochin_score, zivvug_assessment.state)

        # Réinitialiser les boosts après application
        engine.reset_boosts()

        # Persistance du Zivvug
        if persist:
            try:
                from .zivvug import save_zivvug_state
                save_zivvug_state(engine, zivvug_assessment)
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # Phase 3 : persistance individuelle
    if persist:
        for partzuf in partzufim.values():
            partzuf.save_state()

    return zivvug_assessment


def feedback_from_malkuth(
    partzufim: dict[str, PartzufBase],
    quality_score: float,
    zivvug_engine: ZivvugEngine | None = None,
    insight_produced: bool = False,
    causal_validated: bool = False,
) -> dict:
    """Feedback bidirectionnel post-Malkuth — le retour de l'Or Chozer.

    Après chaque réponse, la qualité observée remonte l'arbre :
    1. Nukva→ZA : si qualité basse, ZA.malkuth diminue (le pipeline a failli)
    2. ZA→Abba/Imma via mutual_reinforcement : insights/causal boostent les parents
    3. ZA bon → Atik stable (pas de dégradation cascade)

    Args:
        partzufim: dict des 6 Partzufim instanciés
        quality_score: score qualité de la réponse (0.0-1.0, typiquement d'autojudge)
        zivvug_engine: moteur Zivvug pour le renforcement mutuel
        insight_produced: InsightForge a-t-il produit un insight ce cycle ?
        causal_validated: CausalEngine a-t-il validé un claim ce cycle ?

    Returns:
        dict résumant les ajustements effectués
    """
    result = {"adjustments": [], "reinforcement": None}

    za = partzufim.get("zeir_anpin")
    nukva = partzufim.get("nukva")

    # 1. Nukva→ZA : qualité basse → réduire ZA.malkuth
    if za and quality_score < 0.4:
        old = za.get_faculty("malkuth")
        za.set_faculty("malkuth", max(0.0, old - 0.03))
        result["adjustments"].append(
            f"ZA.malkuth {old:.2f}→{za.get_faculty('malkuth'):.2f} (qualité={quality_score:.2f})"
        )

    # 2. Qualité haute → renforcer ZA.malkuth
    if za and quality_score > 0.8:
        old = za.get_faculty("malkuth")
        za.set_faculty("malkuth", min(1.0, old + 0.02))
        result["adjustments"].append(
            f"ZA.malkuth {old:.2f}→{za.get_faculty('malkuth'):.2f} (qualité={quality_score:.2f})"
        )

    # 3. Nukva reçoit le feedback direct
    if nukva:
        old = nukva.get_faculty("malkuth")
        delta = 0.02 if quality_score > 0.6 else -0.02
        nukva.set_faculty("malkuth", max(0.0, min(1.0, old + delta)))

    # 4. Renforcement mutuel Abba↔Imma via Zivvug
    if zivvug_engine and (insight_produced or causal_validated):
        result["reinforcement"] = zivvug_engine.mutual_reinforcement(
            insight_produced=insight_produced,
            causal_validated=causal_validated,
        )

    return result


def _apply_mochin_to_za(
    za: PartzufBase,
    mochin_score: float,
    zivvug_state: ZivvugState,
) -> None:
    """Applique les Mochin d'Abba/Imma à Zeir Anpin.

    Les Mochin descendent via Da'at (Keter-de-ZA) et affectent
    les facultés supérieures de ZA (Keter, Chokhmah, Binah).

    Si Zivvug bloqué → ZA ne peut pas passer en Gadlut.
    """
    if zivvug_state == ZivvugState.BLOCKED:
        # Pas de Mochin → facultés supérieures de ZA plafonnées
        za.set_faculty("keter", min(za.get_faculty("keter"), 0.25))
        za.set_faculty("chokhmah", min(za.get_faculty("chokhmah"), 0.25))
        za.set_faculty("binah", min(za.get_faculty("binah"), 0.25))
    elif zivvug_state == ZivvugState.PARTIAL:
        # Mochin partiels → boost modéré
        za.set_faculty("keter", min(1.0, za.get_faculty("keter") + mochin_score * 0.3))
        za.set_faculty("chokhmah", min(1.0, za.get_faculty("chokhmah") + mochin_score * 0.2))
        za.set_faculty("binah", min(1.0, za.get_faculty("binah") + mochin_score * 0.2))
    else:
        # Mochin pleins → boost complet
        za.set_faculty("keter", min(1.0, za.get_faculty("keter") + mochin_score * 0.5))
        za.set_faculty("chokhmah", min(1.0, za.get_faculty("chokhmah") + mochin_score * 0.4))
        za.set_faculty("binah", min(1.0, za.get_faculty("binah") + mochin_score * 0.4))


__all__ = [
    "PartzufBase", "PartzufState", "ZivugResult", "FACULTY_NAMES",
    "AtikYomin", "ArikhAnpin", "Abba", "Imma", "ZeirAnpin", "Nukva",
    "ZivvugEngine", "ZivvugState", "ZivvugAssessment",
    "REGISTRY", "get_partzuf", "list_partzufim",
    "init_partzufim", "update_all_partzufim", "feedback_from_malkuth",
    "PartzufimRegulator",
]
