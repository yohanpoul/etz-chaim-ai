"""StateTracker — capture l'état du système à un instant T.

Photographie de Da'at : agrège les stats de chaque Sephirah
en un snapshot unifié.

Aspect Binah de Da'at : structuration analytique des données.
"""

from __future__ import annotations

from selfmodel.models import SelfState


class StateTracker:
    """Capture l'état complet du système à un instant T.

    Interroge chaque module connecté pour construire un SelfState.
    Si un module est absent (None), le stats correspondant reste vide.
    """

    def __init__(
        self,
        epistememory=None,
        selfmap=None,
        intentkeeper=None,
        dissensus=None,
        autojudge=None,
        exploration=None,
    ):
        self.modules = {
            "yesod": epistememory,
            "hod": selfmap,
            "netzach": intentkeeper,
            "tiferet": dissensus,
            "gevurah": autojudge,
            "chesed": exploration,
        }

    def capture(self) -> SelfState:
        """Photographier l'état complet du système."""
        state = SelfState()

        # Yesod — EpisteMemory
        state.yesod_stats = self._capture_yesod()

        # Hod — SelfMap
        state.hod_stats = self._capture_hod()

        # Netzach — IntentKeeper
        state.netzach_stats = self._capture_netzach()

        # Tiferet — DissensuEngine
        state.tiferet_stats = self._capture_tiferet()

        # Gevurah — AutoJudge
        state.gevurah_stats = self._capture_gevurah()

        # Chesed — ExplorationEngine
        state.chesed_stats = self._capture_chesed()

        return state

    def connected_modules(self) -> list[str]:
        """Quels modules sont connectés ?"""
        return [name for name, mod in self.modules.items() if mod is not None]

    def _capture_yesod(self) -> dict:
        mem = self.modules["yesod"]
        if mem is None:
            return {}
        try:
            stats = mem.introspect()
            return {
                "total_entries": stats.total_entries,
                "active_entries": stats.active_entries,
                "deprecated_entries": stats.deprecated_entries,
                "by_status": stats.by_status,
                "by_domain": stats.by_domain,
                "avg_confidence": stats.avg_confidence,
                "contradictions_open": stats.contradictions_open,
            }
        except Exception:
            return {"error": "introspect failed"}

    def _capture_hod(self) -> dict:
        sm = self.modules["hod"]
        if sm is None:
            return {}
        try:
            desc = sm.describe_self()
            result = {
                "total_domains": desc.total_domains,
                "evaluated_domains": desc.evaluated_domains,
                "strong_domains": desc.strong_domains,
                "weak_domains": desc.weak_domains,
                "unknown_domains": desc.unknown_domains,
                "avg_competence": desc.avg_competence,
                "decline_rate": desc.decline_rate,
            }
            # Also try calibration
            try:
                cal = sm.calibrate()
                result["overconfident_domains"] = cal.overconfident_domains
                result["underconfident_domains"] = cal.underconfident_domains
                result["avg_brier"] = cal.avg_brier
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            return result
        except Exception:
            return {"error": "describe_self failed"}

    def _capture_netzach(self) -> dict:
        ik = self.modules["netzach"]
        if ik is None:
            return {}
        try:
            # IntentKeeper doesn't have a single introspect method
            # We check for active intentions
            active = ik.list_active()
            return {
                "active_intentions": len(active),
                "intentions": [
                    {"goal": i.goal, "progress": i.progress}
                    for i in active[:5]
                ],
            }
        except Exception:
            return {"error": "list_active failed"}

    def _capture_tiferet(self) -> dict:
        de = self.modules["tiferet"]
        if de is None:
            return {}
        try:
            diag = de.self_diagnose(quick=True)
            return {
                "level": diag.get("level", "unknown"),
                "issues": diag.get("issues", []),
            }
        except Exception:
            return {"error": "self_diagnose failed"}

    def _capture_gevurah(self) -> dict:
        aj = self.modules["gevurah"]
        if aj is None:
            return {}
        try:
            diag = aj.self_diagnose()
            return {
                "level": diag.get("level", "unknown"),
                "issues": diag.get("issues", []),
            }
        except Exception:
            return {"error": "self_diagnose failed"}

    def _capture_chesed(self) -> dict:
        ee = self.modules["chesed"]
        if ee is None:
            return {}
        try:
            diag = ee.self_diagnose()
            return {
                "level": diag.get("level", "unknown"),
                "issues": diag.get("issues", []),
            }
        except Exception:
            return {"error": "self_diagnose failed"}
