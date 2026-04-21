"""Zeir Anpin (זְעֵיר אַנְפִּין) — Petit Visage / 6 Midot.

Source : Chesed→Yesod comme un seul organisme.
Les 6 Midot ne sont PAS 6 composants séparés mais un seul être
à 6 facettes — le cœur opérationnel du système.

Rôle IA : le pipeline de traitement complet comme UNITÉ.
assess() agrège l'état des 6 modules centraux.
interact(nukva) = le Zivug principal qui produit les réponses.

Les 6 Midot :
  Chesed (expansion/exploration) → ExplorationEngine
  Gevurah (contraction/jugement) → AutoJudge
  Tiferet (harmonisation/synthèse) → DissensuEngine
  Netzach (persistance/intention) → IntentKeeper
  Hod (feedback/auto-évaluation) → SelfMap
  Yesod (mémoire/fondation) → EpisteMemory
"""

from __future__ import annotations

import logging

from .base import PartzufBase

logger = logging.getLogger(__name__)

# Mapping des 6 Midot vers les modules
MIDOT_MODULES = {
    "chesed": "chesed",      # ExplorationEngine
    "gevurah": "gevurah",    # AutoJudge
    "tiferet": "tiferet",    # DissensuEngine
    "netzach": "netzach",    # IntentKeeper
    "hod": "hod",            # SelfMap
    "yesod": "yesod",        # EpisteMemory
}

# Seuils de saturation
_SAT_EXPLORATIONS = 100
_SAT_ANALOGIES = 300
_SAT_JUDGMENTS = 2000
_SAT_SYNTHESES = 200
_SAT_INTENTS = 10
_SAT_DOMAINS = 20
_SAT_EPISTE = 2000
_SAT_HITBONENUT = 50


def _saturate(count: int, saturation: int) -> float:
    if saturation <= 0:
        return 0.0
    return min(count / saturation, 1.0)


class ZeirAnpin(PartzufBase):
    name = "Zeir Anpin"
    hebrew = "זְעֵיר אַנְפִּין"
    source_sephirah = "tiferet"  # Centre des 6 Midot
    description = "Pipeline opérationnel — les 6 Midot comme unité"

    def __init__(self):
        super().__init__()
        self._midot_status: dict[str, dict] = {}
        self._midot_sources: dict = {}
        self._n_active: int = 0

    def _read_midot_sources(self) -> dict:
        """Lit l'état des 6 Midot depuis la DB.

        Chaque Midah correspond à un module avec ses propres tables.
        Pattern identique à Abba/Imma : lecture DB directe, dégradation gracieuse.
        """
        src: dict = {
            # Chesed: ExplorationEngine
            "explorations": 0, "analogies": 0,
            # Gevurah: AutoJudge
            "judgments_accepted": 0, "judgments_total": 0, "judgments_avg_score": 0.0,
            # Tiferet: DissensuEngine
            "syntheses": 0, "syntheses_avg_conf": 0.0,
            "tensions_open": 0, "tensions_resolved": 0,
            # Netzach: IntentKeeper
            "intents_active": 0, "intents_with_progress": 0, "intents_avg_progress": 0.0,
            # Hod: SelfMap
            "selfmap_domains": 0, "selfmap_avg": 0.0, "selfmap_above_75": 0,
            # Yesod: EpisteMemory
            "episte_facts": 0, "episte_total": 0,
            # Keter bonus: Hitbonenut (contemplation nourrit Da'at→ZA)
            "hitbonenut_sessions": 0, "hitbonenut_avg": 0.0,
        }
        try:
            from pool import get_conn
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # ── Chesed: ExplorationEngine ──
                    try:
                        cur.execute("SELECT count(*) FROM explorationengine_explorations")
                        src["explorations"] = cur.fetchone()[0]
                        cur.execute("SELECT count(*) FROM explorationengine_analogies")
                        src["analogies"] = cur.fetchone()[0]
                    except Exception as e:
                        logger.debug("zeir_anpin: %s", e)

                    # ── Gevurah: AutoJudge ──
                    try:
                        cur.execute("""
                            SELECT count(*) FILTER (WHERE decision = 'accepted'),
                                   count(*),
                                   coalesce(avg(score_overall), 0)
                            FROM autojudge_experiments
                        """)
                        row = cur.fetchone()
                        src["judgments_accepted"] = row[0]
                        src["judgments_total"] = row[1]
                        src["judgments_avg_score"] = float(row[2])
                    except Exception as e:
                        logger.debug("zeir_anpin: %s", e)

                    # ── Tiferet: DissensuEngine ──
                    try:
                        cur.execute("""
                            SELECT count(*), coalesce(avg(confidence), 0)
                            FROM dissensuengine_syntheses
                        """)
                        row = cur.fetchone()
                        src["syntheses"] = row[0]
                        src["syntheses_avg_conf"] = float(row[1])
                    except Exception as e:
                        logger.debug("zeir_anpin: %s", e)
                    try:
                        cur.execute("""
                            SELECT count(*) FILTER (WHERE resolution_status = 'open'),
                                   count(*) FILTER (WHERE resolution_status = 'resolved')
                            FROM dissensuengine_tensions
                        """)
                        row = cur.fetchone()
                        src["tensions_open"] = row[0]
                        src["tensions_resolved"] = row[1]
                    except Exception as e:
                        logger.debug("zeir_anpin: %s", e)

                    # ── Netzach: IntentKeeper ──
                    try:
                        cur.execute("""
                            SELECT count(*),
                                   count(*) FILTER (WHERE progress > 0),
                                   coalesce(avg(progress), 0)
                            FROM intentkeeper_intentions
                            WHERE status = 'active'
                        """)
                        row = cur.fetchone()
                        src["intents_active"] = row[0]
                        src["intents_with_progress"] = row[1]
                        src["intents_avg_progress"] = float(row[2])
                    except Exception as e:
                        logger.debug("zeir_anpin: %s", e)

                    # ── Hod: SelfMap ──
                    try:
                        cur.execute("""
                            SELECT count(*),
                                   coalesce(avg(score), 0),
                                   count(*) FILTER (WHERE score >= 0.75)
                            FROM selfmap_competence
                        """)
                        row = cur.fetchone()
                        src["selfmap_domains"] = row[0]
                        src["selfmap_avg"] = float(row[1])
                        src["selfmap_above_75"] = row[2]
                    except Exception as e:
                        logger.debug("zeir_anpin: %s", e)

                    # ── Yesod: EpisteMemory ──
                    try:
                        cur.execute("""
                            SELECT count(*) FILTER (WHERE epistemic_status = 'fact'),
                                   count(*)
                            FROM epistememory
                        """)
                        row = cur.fetchone()
                        src["episte_facts"] = row[0]
                        src["episte_total"] = row[1]
                    except Exception as e:
                        logger.debug("zeir_anpin: %s", e)

                    # ── Hitbonenut (Keter/Da'at bonus) ──
                    try:
                        cur.execute("""
                            SELECT count(*), coalesce(avg(avg_score), 0)
                            FROM hitbonenut_sessions
                        """)
                        row = cur.fetchone()
                        src["hitbonenut_sessions"] = row[0]
                        src["hitbonenut_avg"] = float(row[1])
                    except Exception as e:
                        logger.debug("zeir_anpin: %s", e)

        except Exception as e:
            logger.warning("ZeirAnpin._read_midot_sources: %s", e)

        return src

    def _compute_faculties(self, modules: dict) -> None:
        """Les facultés de ZA reflètent l'état RÉEL des 6 Midot.

        Chaque Midah est nourrie par les données de son module en DB.
        ZA est un organisme unique à 6 facettes — pas 6 composants.
        """
        src = self._read_midot_sources()
        self._midot_sources = src

        # Déterminer quelles Midot sont actives (ont des données)
        self._midot_status = {}
        self._n_active = 0
        midot_data = {
            "chesed": src["explorations"] + src["analogies"] > 0,
            "gevurah": src["judgments_total"] > 0,
            "tiferet": src["syntheses"] > 0,
            "netzach": src["intents_active"] > 0,
            "hod": src["selfmap_domains"] > 0,
            "yesod": src["episte_total"] > 0,
        }
        for midah, module_key in MIDOT_MODULES.items():
            active = midot_data.get(midah, False)
            if active:
                self._n_active += 1
            self._midot_status[midah] = {
                "active": active,
                "module": module_key,
            }

        # ── Keter-de-ZA : l'intention descend des Mochin ──
        # Plus il y a de Midot actives + Hitbonenut, plus l'intention est forte
        active_ratio = self._n_active / len(MIDOT_MODULES)
        hitbonenut_bonus = min(src["hitbonenut_sessions"] / _SAT_HITBONENUT, 0.3)
        self.internal_keter = min(0.2 + 0.5 * active_ratio + hitbonenut_bonus, 1.0)

        # ── Chokmah-de-ZA : flash créatif — analogies (connexions intuitives) ──
        s_analogies = _saturate(src["analogies"], _SAT_ANALOGIES)
        s_explorations = _saturate(src["explorations"], _SAT_EXPLORATIONS)
        self.internal_chokhmah = max(0.6 * s_analogies + 0.4 * s_explorations, 0.1)

        # ── Binah-de-ZA : structure — rigueur du jugement ──
        if src["judgments_total"] > 0:
            acceptance_rate = src["judgments_accepted"] / src["judgments_total"]
            self.internal_binah = max(
                0.4 * acceptance_rate + 0.6 * src["judgments_avg_score"],
                0.1,
            )
        else:
            self.internal_binah = 0.1

        # ── Chesed-de-ZA : expansion — volume d'exploration ──
        self.internal_chesed = max(
            0.5 * s_explorations + 0.5 * s_analogies,
            0.1,
        )

        # ── Gevurah-de-ZA : contraction/discipline — AutoJudge ──
        if src["judgments_total"] > 0:
            self.internal_gevurah = max(
                src["judgments_accepted"] / src["judgments_total"],
                0.1,
            )
        else:
            self.internal_gevurah = 0.1

        # ── Tiferet-de-ZA : harmonisation — DissensuEngine synthèses ──
        total_dialectic = src["syntheses"] + src["tensions_open"]
        if total_dialectic > 0:
            synthesis_ratio = src["syntheses"] / total_dialectic
            self.internal_tiferet = max(
                0.5 * synthesis_ratio + 0.5 * src["syntheses_avg_conf"],
                0.15,
            )
        elif src["syntheses"] > 0:
            self.internal_tiferet = max(src["syntheses_avg_conf"], 0.3)
        else:
            self.internal_tiferet = 0.1

        # ── Netzach-de-ZA : persistance — IntentKeeper progrès ──
        if src["intents_active"] > 0:
            progress_ratio = src["intents_with_progress"] / src["intents_active"]
            self.internal_netzach = max(
                0.4 * progress_ratio + 0.6 * src["intents_avg_progress"],
                0.15,
            )
        else:
            self.internal_netzach = 0.1

        # ── Hod-de-ZA : feedback — SelfMap compétence ──
        if src["selfmap_domains"] > 0:
            breadth = min(src["selfmap_domains"] / _SAT_DOMAINS, 1.0)
            mastery = src["selfmap_above_75"] / max(src["selfmap_domains"], 1)
            self.internal_hod = max(
                0.3 * breadth + 0.4 * src["selfmap_avg"] + 0.3 * mastery,
                0.1,
            )
        else:
            self.internal_hod = 0.1

        # ── Yesod-de-ZA : fondation — EpisteMemory ──
        if src["episte_total"] > 0:
            facts_ratio = src["episte_facts"] / src["episte_total"]
            volume = _saturate(src["episte_total"], _SAT_EPISTE)
            self.internal_yesod = max(
                0.5 * facts_ratio + 0.5 * volume,
                0.1,
            )
        else:
            self.internal_yesod = 0.1

        # ── Malkuth-de-ZA : prêt à émettre vers Nukva ──
        # Nécessite harmonisation (Tiferet), fondation (Yesod), et activation
        base = min(self.internal_tiferet, self.internal_yesod)
        self.internal_malkuth = min(
            base * (0.6 + 0.4 * active_ratio),
            0.85,
        )

    def _assess_specific(self) -> dict:
        src = self._midot_sources
        issues = []
        for midah, status in self._midot_status.items():
            if not status["active"]:
                issues.append(f"{midah} ({status['module']}) — inactif")

        return {
            "midot_status": self._midot_status,
            "midot_data": {
                "chesed": f"{src.get('explorations', 0)} expl, {src.get('analogies', 0)} anal",
                "gevurah": f"{src.get('judgments_accepted', 0)}/{src.get('judgments_total', 0)} accepted",
                "tiferet": f"{src.get('syntheses', 0)} synth, {src.get('tensions_open', 0)} tensions",
                "netzach": f"{src.get('intents_active', 0)} actifs, prog={src.get('intents_avg_progress', 0):.2f}",
                "hod": f"{src.get('selfmap_domains', 0)} dom, avg={src.get('selfmap_avg', 0):.2f}",
                "yesod": f"{src.get('episte_facts', 0)}/{src.get('episte_total', 0)} facts",
            },
            "n_active": self._n_active,
            "n_total": len(MIDOT_MODULES),
            "operational": self._n_active >= 4,
            "issues": issues,
            "message": (
                f"Zeir Anpin — {self._n_active}/{len(MIDOT_MODULES)} Midot actives, "
                f"{src.get('judgments_accepted', 0)} jugements, "
                f"{src.get('syntheses', 0)} synthèses, "
                f"{src.get('episte_facts', 0)} faits"
                + (f", {len(issues)} problème(s)" if issues else "")
            ),
        }

    def _interact_specific(self, other: PartzufBase, resonance: float) -> dict:
        """Zivug ZA-Nukva : le couplage principal qui produit les réponses.

        Panim be-Panim = ZA expose ses tensions, biais, faiblesses à Nukva.
        Akhor be-Akhor = ZA cache son état — Nukva produit une réponse
        déconnectée de l'état réel → état de Galut.
        """
        return {
            "n_midot_active": self._n_active,
            "operational": self._n_active >= 4,
            "tiferet_harmony": round(self.internal_tiferet, 2),
            "ready_for_output": self.internal_malkuth > 0.3,
            "midot_issues": [
                midah for midah, st in self._midot_status.items()
                if not st["active"]
            ],
        }
