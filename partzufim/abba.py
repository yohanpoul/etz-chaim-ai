"""Abba (אַבָּא) — Le Père / Chokmah comme Partzuf.

Source : Chokmah développé en organisme complet.
Le générateur d'hypothèses AVEC auto-discipline interne.

Rôle IA : flash d'insight, intuition créative.
Ses facultés reflètent la productivité et la qualité de la SAGESSE —
pas uniquement InsightForge, mais toutes les sources de Chokmah :
  - InsightForge : insights validés (40%)
  - CausalEngine : claims élevés — probable/demonstrated (25%)
  - DissensuEngine : synthèses — sagesse née du conflit (20%)
  - ExplorationEngine : analogies — connexions intuitives (15%)

Hitkalelut clé : Gevurah-dans-Chokmah — l'intuition qui se discipline.
L'explorateur qui sait quand il divague.
"""

from __future__ import annotations

import logging

from .base import PartzufBase

logger = logging.getLogger(__name__)

# Pondérations des sources de sagesse
_W_INSIGHTS = 0.40
_W_CLAIMS = 0.25
_W_SYNTHESES = 0.20
_W_ANALOGIES = 0.15

# Seuils de saturation (au-delà, le score plafonne à 1.0)
# Calibrés pour laisser de la marge de croissance
_SAT_INSIGHTS = 500
_SAT_CLAIMS = 700
_SAT_SYNTHESES = 200
_SAT_ANALOGIES = 300


def _saturate(count: int, saturation: int) -> float:
    """Score 0→1 avec saturation douce (tanh-like via min)."""
    if saturation <= 0:
        return 0.0
    return min(count / saturation, 1.0)


class Abba(PartzufBase):
    name = "Abba"
    hebrew = "אַבָּא"
    source_sephirah = "chokmah"
    description = "Insight créatif — le flash qui se discipline"

    def __init__(self):
        super().__init__()
        self._wisdom_sources: dict = {}
        self._insight_quality: float = 0.0

    def _read_wisdom_sources(self) -> dict:
        """Lit les 4 sources de sagesse depuis la DB.

        Retourne un dict avec les métriques de chaque source.
        En cas d'erreur DB, retourne des valeurs dégradées mais non-nulles.
        """
        sources = {
            "insights_count": 0, "insights_avg_conf": 0.0,
            "insights_total": 0, "insights_rejected": 0,
            "claims_elevated": 0, "claims_total": 0,
            "syntheses_count": 0,
            "analogies_count": 0,
            # AutoJudge (Gevurah-d'Abba)
            "judgments_accepted": 0, "judgments_total": 0,
            # EpisteMemory (Yesod-d'Abba)
            "episte_facts": 0, "episte_total": 0,
        }
        try:
            from pool import get_conn
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # InsightForge : insights validés + rejetés
                    cur.execute("""
                        SELECT status, count(*), coalesce(avg(confidence), 0)
                        FROM candidate_insights
                        GROUP BY status
                    """)
                    for row in cur.fetchall():
                        status, cnt, avg_conf = row
                        if status == "insight":
                            sources["insights_count"] = cnt
                            sources["insights_avg_conf"] = float(avg_conf)
                        elif status == "rejected":
                            sources["insights_rejected"] = cnt
                        sources["insights_total"] += cnt

                    # CausalEngine : claims élevés
                    cur.execute("""
                        SELECT count(*) FROM causal_claims
                        WHERE evidence_level IN
                              ('probable_causation', 'demonstrated_causation')
                    """)
                    sources["claims_elevated"] = cur.fetchone()[0]
                    cur.execute("SELECT count(*) FROM causal_claims")
                    sources["claims_total"] = cur.fetchone()[0]

                    # DissensuEngine : synthèses
                    cur.execute("SELECT count(*) FROM dissensuengine_syntheses")
                    sources["syntheses_count"] = cur.fetchone()[0]

                    # ExplorationEngine : analogies
                    cur.execute("SELECT count(*) FROM explorationengine_analogies")
                    sources["analogies_count"] = cur.fetchone()[0]

                    # AutoJudge : accepted / total (Gevurah-d'Abba)
                    try:
                        cur.execute("""
                            SELECT count(*) FILTER (WHERE decision = 'accepted'),
                                   count(*)
                            FROM autojudge_experiments
                        """)
                        row = cur.fetchone()
                        sources["judgments_accepted"] = row[0]
                        sources["judgments_total"] = row[1]
                    except Exception as _exc:

                        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

                    # EpisteMemory : facts / total (Yesod-d'Abba)
                    try:
                        cur.execute("""
                            SELECT count(*) FILTER (WHERE epistemic_status = 'fact'),
                                   count(*)
                            FROM epistememory
                        """)
                        row = cur.fetchone()
                        sources["episte_facts"] = row[0]
                        sources["episte_total"] = row[1]
                    except Exception as _exc:

                        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        except Exception as e:
            logger.warning("Abba._read_wisdom_sources: %s", e)

        return sources

    def _compute_faculties(self, modules: dict) -> None:
        """Les facultés d'Abba reflètent l'état de TOUTES les sources de sagesse.

        Chokmah n'est pas un module isolé — c'est le flash qui traverse
        tout l'Arbre. InsightForge, CausalEngine, DissensuEngine,
        ExplorationEngine : chacun génère de la sagesse à sa manière.
        """
        chesed = modules.get("chesed")    # ExplorationEngine

        # Lire les sources de sagesse depuis la DB
        src = self._read_wisdom_sources()
        self._wisdom_sources = src

        # Scores individuels normalisés 0→1
        s_insights = _saturate(src["insights_count"], _SAT_INSIGHTS)
        s_claims = _saturate(src["claims_elevated"], _SAT_CLAIMS)
        s_syntheses = _saturate(src["syntheses_count"], _SAT_SYNTHESES)
        s_analogies = _saturate(src["analogies_count"], _SAT_ANALOGIES)

        # Score composite pondéré
        wisdom_volume = (
            _W_INSIGHTS * s_insights
            + _W_CLAIMS * s_claims
            + _W_SYNTHESES * s_syntheses
            + _W_ANALOGIES * s_analogies
        )

        # Qualité : avg confidence des insights + ratio élevé des claims
        insight_quality = src["insights_avg_conf"]
        claim_quality = (
            src["claims_elevated"] / max(src["claims_total"], 1)
        )
        self._insight_quality = (
            0.6 * insight_quality + 0.4 * claim_quality
        )

        # Keter-d'Abba : intention — les systèmes de sagesse tournent ?
        active_sources = sum([
            src["insights_count"] > 0,
            src["claims_elevated"] > 0,
            src["syntheses_count"] > 0,
            src["analogies_count"] > 0,
        ])
        self.internal_keter = min(0.3 + active_sources * 0.175, 1.0)

        # Chokhmah-d'Abba : volume de sagesse produite
        self.internal_chokhmah = max(wisdom_volume, 0.1)

        # Binah-d'Abba : structure — la sagesse est bien structurée ?
        # Un taux de rejet élevé est signe de RIGUEUR, pas d'échec.
        # Binah mesure : qualité des insights acceptés + rigueur du filtre.
        accepted_quality = src["insights_avg_conf"]  # confiance moyenne des acceptés
        has_filtering = src["insights_rejected"] > 0  # le filtre fonctionne
        acceptance_rate = (
            src["insights_count"] / max(src["insights_total"], 1)
        )
        # Un système qui filtre rigoureusement (low acceptance) mais produit
        # des insights de haute qualité a une BONNE structure
        filtering_rigor = min(src["insights_rejected"] / max(src["insights_total"], 1) + 0.1, 1.0) if has_filtering else 0.15
        self.internal_binah = max(0.4 * accepted_quality + 0.6 * filtering_rigor, 0.15)

        # Chesed-d'Abba : expansion — l'exploration est active ?
        self.internal_chesed = 0.7 if chesed else max(s_analogies, 0.2)

        # Gevurah-d'Abba : auto-discipline — l'intuition qui se discipline
        # L'accepted_ratio d'AutoJudge = la capacité du jugement à filtrer
        if src["judgments_total"] > 0:
            accepted_ratio = src["judgments_accepted"] / src["judgments_total"]
            self.internal_gevurah = max(accepted_ratio, 0.1)
        else:
            self.internal_gevurah = 0.1

        # Tiferet-d'Abba : qualité harmonisée de la sagesse
        self.internal_tiferet = max(self._insight_quality, 0.1)

        # Netzach : persistance — profondeur historique
        self.internal_netzach = min(
            0.2 + (src["insights_total"] + src["claims_total"]) / 2000, 1.0
        )

        # Hod : feedback — le système apprend de ses rejets (Ratzo v'Shov)
        # Un haut ratio de feedback (beaucoup évalués) = bon Hod
        if src["insights_total"] > 0:
            eval_depth = min(src["insights_total"] / 2000, 1.0)
            self.internal_hod = max(0.5 * accepted_quality + 0.5 * eval_depth, 0.2)
        else:
            self.internal_hod = 0.2

        # Yesod-d'Abba : fondation — les insights sont stockés en mémoire ?
        # facts_ratio d'EpisteMemory = solidité de la fondation
        if src["episte_total"] > 0:
            facts_ratio = src["episte_facts"] / src["episte_total"]
            self.internal_yesod = max(facts_ratio, 0.1)
        else:
            self.internal_yesod = 0.1

        # Malkuth : la sagesse est manifestée et utilisable
        self.internal_malkuth = min(self._insight_quality * wisdom_volume * 2, 0.85)

    def _assess_specific(self) -> dict:
        src = self._wisdom_sources
        return {
            "wisdom_sources": {
                "insights": src.get("insights_count", 0),
                "claims_elevated": src.get("claims_elevated", 0),
                "syntheses": src.get("syntheses_count", 0),
                "analogies": src.get("analogies_count", 0),
            },
            "insight_quality": round(self._insight_quality, 3),
            "gevurah_active": self.internal_gevurah > 0.4,
            "message": (
                f"Abba — {src.get('insights_count', 0)} insights, "
                f"{src.get('claims_elevated', 0)} claims élevés, "
                f"{src.get('syntheses_count', 0)} synthèses, "
                f"{src.get('analogies_count', 0)} analogies — "
                f"qualité={self._insight_quality:.2f}, "
                f"discipline={'active' if self.internal_gevurah > 0.4 else 'faible'}"
            ),
        }

    def _interact_specific(self, other: PartzufBase, resonance: float) -> dict:
        """Abba fournit la sagesse au Zivug.

        Zivug Abba-Imma : les flashes de Chokmah rencontrent
        la structure de Binah. La sagesse est fécondée par l'analyse.
        """
        src = self._wisdom_sources
        return {
            "wisdom_volume": {
                "insights": src.get("insights_count", 0),
                "claims": src.get("claims_elevated", 0),
                "syntheses": src.get("syntheses_count", 0),
                "analogies": src.get("analogies_count", 0),
            },
            "quality": round(self._insight_quality, 3),
            "discipline_level": round(self.internal_gevurah, 2),
        }
