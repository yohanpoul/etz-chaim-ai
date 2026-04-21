"""MazalEngine — Orchestrateur des 2 Mazalot (Sprint 9 + Sprint 10 Phase 3).

Doctrine primaire EC-K5-001 (Sha'ar HaKlalim 5:1, Rabbi Hayyim Vital) :
    "Dans la Dikna de A"A il y a 2 Mazalot : Notzer Chesed (Tikkun 8) et
    Ve-Nakeh (Tikkun 13). Ces 2 Mazalot sont les SOURCES des Mohin."

**Phase 1 (Sprint 9)** : 2 Mazalot détectent et signalent les écarts
doctrinaux sur 2 axes (Chesed starvation + résidus causaux).

**Phase 3 (Sprint 10 Phase C)** : rectification active via 3 modes:
    - ``observe`` (défaut) : signalement seul (compat Sprint 9).
    - ``suggest`` : signalement + event ``mazal_action_proposed`` (sans appliquer).
    - ``act`` : signalement + proposition + application effective (opt-in).

Respect Hitlabshut (EC-K5-008, Sprint 8 D1) :
    Aucune écriture directe sur partzufim_state / zivvug_state même en mode
    ``act``. Les actions ciblent ``omer_history`` (paramètres) et
    ``causal_claims`` (flag abandoned) — orthogonales aux Kelim.
"""

from __future__ import annotations

import logging

from mazalengine.mazal_elyon import MazalElyonNotzerChesed
from mazalengine.mazal_tahton import MazalTahtonVeNakeh
from mazalengine.rectification import (
    NotzerChesedRectifier,
    RectificationMode,
    VeNakehRectifier,
    action_to_event,
    load_mode,
)

log = logging.getLogger("etz-mazalengine")


class MazalEngine:
    """Moteur des 2 Mazalot avec rectification active (Phase 3).

    Attributes:
        mode: l'un de ``observe`` / ``suggest`` / ``act`` (cf RectificationMode).
    """

    def __init__(self, db_url: str | None = None, mode: str | None = None) -> None:
        self.db_url = db_url
        self.mode = load_mode(mode)
        self.mazal_elyon = MazalElyonNotzerChesed(db_url)
        self.mazal_tahton = MazalTahtonVeNakeh(db_url)
        self.notzer_rectifier = NotzerChesedRectifier()
        self.ve_nakeh_rectifier = VeNakehRectifier()

    def detect(self, tree: dict | None = None) -> list[dict]:
        """Retourne les écarts détectés par les 2 Mazalot (concaténés)."""
        return [
            *self.mazal_elyon.detect(tree),
            *self.mazal_tahton.detect(tree),
        ]

    def rectify(self, deviations: list[dict]) -> list[dict]:
        """Émet les events Tikkun. Selon ``self.mode`` :

        - ``observe`` : 1 event signalement par deviation.
        - ``suggest`` : + 1 event ``mazal_action_proposed`` avec action concrète.
        - ``act``     : + 1 event supplémentaire ``*_executed`` après application.
        """
        events: list[dict] = []
        for dev in deviations:
            mazal = dev.get("mazal")
            if mazal == "elyon":
                events.append(self.mazal_elyon.apply_tikkun(dev))
                if self.mode in (RectificationMode.SUGGEST, RectificationMode.ACT):
                    action = self.notzer_rectifier.propose(dev)
                    events.append(action_to_event(action))
                    if self.mode == RectificationMode.ACT:
                        events.append(self.notzer_rectifier.apply(action, self.db_url))
            elif mazal == "tahton":
                events.append(self.mazal_tahton.apply_tikkun(dev))
                if self.mode in (RectificationMode.SUGGEST, RectificationMode.ACT):
                    action = self.ve_nakeh_rectifier.propose(dev)
                    events.append(action_to_event(action))
                    if self.mode == RectificationMode.ACT:
                        events.append(self.ve_nakeh_rectifier.apply(action, self.db_url))
        return events

    def run(self, tree: dict | None = None) -> list[dict]:
        """Détecte puis rectifie en un appel. Retourne les events (ou [])."""
        deviations = self.detect(tree)
        if not deviations:
            if self.mode != RectificationMode.OBSERVE:
                self.ve_nakeh_rectifier.reset_cycle_count()
            return []
        return self.rectify(deviations)
