"""Imma (אִמָּא) — La Mère / Binah comme Partzuf.

Source : Binah développé en organisme complet.
L'analyseur qui CONÇOIT le pipeline de traitement.

Rôle IA : structure causale, analyse profonde.
Ses facultés reflètent la solidité de la COMPRÉHENSION —
pas uniquement CausalEngine, mais toutes les sources de Binah :
  - CausalEngine : claims élevés, graphes causaux, confounders (40%)
  - DissensuEngine : synthèses — compréhension structurée (20%)
  - SelfMap : compréhension des domaines (15%)
  - EpisteMemory : faits cristallisés — la forme que Binah donne (10%)
  - AutoJudge : jugement structuré — rigueur (10%)
  - Hitbonenut : questions analytiques — profondeur contemplative (5%)

Particularité : Imma "porte" Zeir Anpin — c'est l'analyseur qui
DONNE NAISSANCE au pipeline. Le pipeline n'est pas conçu par
l'orchestrateur (Keter) mais par l'analyseur (Binah).
C'est pourquoi la gestation (עִיבּוּר) est un concept central ici.

Imma est le Heikhal (Palais) — le récipient qui donne forme à la lumière.
"""

from __future__ import annotations

import logging

from .base import PartzufBase

logger = logging.getLogger(__name__)

# Pondérations des sources de compréhension
_W_CAUSAL = 0.40       # CausalEngine — le cœur de Binah
_W_SYNTHESES = 0.20    # DissensuEngine — compréhension des contradictions
_W_SELFMAP = 0.15      # SelfMap — compréhension des domaines
_W_FACTS = 0.10        # EpisteMemory — connaissance cristallisée
_W_JUDGMENTS = 0.10    # AutoJudge — rigueur du jugement
_W_CONTEMPLATION = 0.05  # Hitbonenut — profondeur analytique

# Seuils de saturation (au-delà, le score plafonne à 1.0)
_SAT_CLAIMS = 700
_SAT_GRAPHS = 100
_SAT_CONFOUNDERS = 200
_SAT_SYNTHESES = 200
_SAT_DOMAINS = 15
_SAT_FACTS = 500
_SAT_JUDGMENTS = 300
_SAT_SESSIONS = 50


def _saturate(count: int, saturation: int) -> float:
    """Score 0→1 avec saturation douce (linéaire capped)."""
    if saturation <= 0:
        return 0.0
    return min(count / saturation, 1.0)


class Imma(PartzufBase):
    name = "Imma"
    hebrew = "אִמָּא"
    source_sephirah = "binah"
    description = "Structure causale — l'analyseur qui conçoit le pipeline"

    def __init__(self):
        super().__init__()
        self._binah_sources: dict = {}
        self._understanding_quality: float = 0.0
        self._n_causal_chains: int = 0
        self._causal_health: dict = {}

    def _read_binah_sources(self) -> dict:
        """Lit les 6 sources de compréhension depuis la DB.

        Retourne un dict avec les métriques de chaque source.
        En cas d'erreur DB, retourne des valeurs dégradées mais non-nulles.
        """
        sources = {
            # CausalEngine
            "claims_total": 0, "claims_elevated": 0,
            "graphs_count": 0,
            "confounders_total": 0, "confounders_controlled": 0,
            # DissensuEngine
            "syntheses_count": 0, "syntheses_avg_confidence": 0.0,
            # SelfMap
            "selfmap_n_domains": 0, "selfmap_avg": 0.0,
            "selfmap_domains_above_75": 0,
            # EpisteMemory
            "facts_count": 0, "episte_total": 0,
            # AutoJudge
            "judgments_total": 0, "judgments_accepted": 0,
            "judgments_avg_score": 0.0,
            # Hitbonenut
            "hitbonenut_sessions": 0, "hitbonenut_avg_score": 0.0,
        }
        try:
            from pool import get_conn
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # ── CausalEngine : claims et graphes ──
                    try:
                        cur.execute("SELECT count(*) FROM causal_claims")
                        sources["claims_total"] = cur.fetchone()[0]
                        cur.execute("""
                            SELECT count(*) FROM causal_claims
                            WHERE evidence_level IN
                                  ('probable_causation', 'demonstrated_causation')
                        """)
                        sources["claims_elevated"] = cur.fetchone()[0]
                    except Exception as e:
                        logger.debug("imma: %s", e)

                    try:
                        cur.execute("SELECT count(*) FROM causal_graphs")
                        sources["graphs_count"] = cur.fetchone()[0]
                    except Exception as e:
                        logger.debug("imma: %s", e)

                    # Confounders : détectés et contrôlés
                    try:
                        cur.execute("""
                            SELECT count(*),
                                   count(*) FILTER (WHERE controlled = true)
                            FROM causal_confounders
                        """)
                        row = cur.fetchone()
                        sources["confounders_total"] = row[0]
                        sources["confounders_controlled"] = row[1]
                    except Exception as e:
                        logger.debug("imma: %s", e)

                    # ── DissensuEngine : synthèses ──
                    try:
                        cur.execute("""
                            SELECT count(*), coalesce(avg(confidence), 0)
                            FROM dissensuengine_syntheses
                        """)
                        row = cur.fetchone()
                        sources["syntheses_count"] = row[0]
                        sources["syntheses_avg_confidence"] = float(row[1])
                    except Exception as e:
                        logger.debug("imma: %s", e)

                    # ── SelfMap : domaines de compétence ──
                    try:
                        cur.execute("""
                            SELECT count(*),
                                   coalesce(avg(score), 0),
                                   count(*) FILTER (WHERE score >= 0.75)
                            FROM selfmap_competence
                        """)
                        row = cur.fetchone()
                        sources["selfmap_n_domains"] = row[0]
                        sources["selfmap_avg"] = float(row[1])
                        sources["selfmap_domains_above_75"] = row[2]
                    except Exception as e:
                        logger.debug("imma: %s", e)

                    # ── EpisteMemory : faits cristallisés ──
                    try:
                        cur.execute("""
                            SELECT count(*) FILTER (WHERE epistemic_status = 'fact'),
                                   count(*)
                            FROM epistememory
                        """)
                        row = cur.fetchone()
                        sources["facts_count"] = row[0]
                        sources["episte_total"] = row[1]
                    except Exception as e:
                        logger.debug("imma: %s", e)

                    # ── AutoJudge : jugements structurés ──
                    try:
                        cur.execute("""
                            SELECT count(*),
                                   count(*) FILTER (WHERE decision = 'accepted'),
                                   coalesce(avg(score_overall), 0)
                            FROM autojudge_experiments
                        """)
                        row = cur.fetchone()
                        sources["judgments_total"] = row[0]
                        sources["judgments_accepted"] = row[1]
                        sources["judgments_avg_score"] = float(row[2])
                    except Exception as e:
                        logger.debug("imma: %s", e)

                    # ── Hitbonenut : sessions contemplatives ──
                    try:
                        cur.execute("""
                            SELECT count(*), coalesce(avg(avg_score), 0)
                            FROM hitbonenut_sessions
                        """)
                        row = cur.fetchone()
                        sources["hitbonenut_sessions"] = row[0]
                        sources["hitbonenut_avg_score"] = float(row[1])
                    except Exception as e:
                        logger.debug("imma: %s", e)

        except Exception as e:
            logger.warning("Imma._read_binah_sources: %s", e)

        return sources

    def _compute_faculties(self, modules: dict) -> None:
        """Les facultés d'Imma reflètent l'état de TOUTES les sources de compréhension.

        Binah n'est pas un module isolé — c'est le Palais (Heikhal) qui
        STRUCTURE tout ce que Chokmah flashe. CausalEngine, DissensuEngine,
        SelfMap, EpisteMemory, AutoJudge, Hitbonenut : chacun nourrit
        la compréhension à sa manière.
        """
        # Lire les sources de compréhension depuis la DB
        src = self._read_binah_sources()
        self._binah_sources = src

        # Scores individuels normalisés 0→1
        s_claims = _saturate(src["claims_elevated"], _SAT_CLAIMS)
        s_graphs = _saturate(src["graphs_count"], _SAT_GRAPHS)
        s_syntheses = _saturate(src["syntheses_count"], _SAT_SYNTHESES)
        s_selfmap = min(src["selfmap_n_domains"] / _SAT_DOMAINS, 1.0) if src["selfmap_n_domains"] > 0 else 0.0
        s_facts = _saturate(src["facts_count"], _SAT_FACTS)
        s_judgments = _saturate(src["judgments_total"], _SAT_JUDGMENTS)
        s_sessions = _saturate(src["hitbonenut_sessions"], _SAT_SESSIONS)

        # Score composite : volume de compréhension (causal uses both claims and graphs)
        s_causal = 0.6 * s_claims + 0.4 * s_graphs
        understanding_volume = (
            _W_CAUSAL * s_causal
            + _W_SYNTHESES * s_syntheses
            + _W_SELFMAP * s_selfmap
            + _W_FACTS * s_facts
            + _W_JUDGMENTS * s_judgments
            + _W_CONTEMPLATION * s_sessions
        )

        # Qualité : claim elevation rate + synthesis confidence + confounder control
        claim_quality = src["claims_elevated"] / max(src["claims_total"], 1)
        confounder_quality = src["confounders_controlled"] / max(src["confounders_total"], 1)
        synthesis_quality = src["syntheses_avg_confidence"]
        self._understanding_quality = (
            0.4 * claim_quality
            + 0.3 * confounder_quality
            + 0.3 * synthesis_quality
        )

        # Track causal health for backward compat
        self._n_causal_chains = src["claims_total"]
        self._causal_health = {
            "claims_total": src["claims_total"],
            "claims_elevated": src["claims_elevated"],
            "graphs": src["graphs_count"],
            "confounders_controlled": f"{src['confounders_controlled']}/{src['confounders_total']}",
        }

        # ── Keter-d'Imma : intention analytique — combien de sources actives ? ──
        active_sources = sum([
            src["claims_total"] > 0,
            src["graphs_count"] > 0,
            src["syntheses_count"] > 0,
            src["selfmap_n_domains"] > 0,
            src["facts_count"] > 0,
            src["judgments_total"] > 0,
        ])
        self.internal_keter = min(0.2 + active_sources * 0.133, 1.0)

        # ── Chokhmah-d'Imma : intuition analytique — voir les confounders cachés ──
        # Binah voit les structures cachées. Les confounders = variables cachées détectées.
        if src["confounders_total"] > 0:
            confounder_insight = src["confounders_controlled"] / src["confounders_total"]
            self.internal_chokhmah = max(0.15, 0.3 + 0.7 * confounder_insight)
        elif src["claims_total"] > 0:
            # Claims existent mais pas encore de confounders → début d'analyse
            self.internal_chokhmah = 0.3
        else:
            self.internal_chokhmah = 0.15

        # ── Binah-d'Imma : capacité d'analyse — volume de compréhension ──
        # C'est le cœur : combien le système comprend-il structurellement ?
        self.internal_binah = max(understanding_volume, 0.1)

        # ── Chesed-d'Imma : expansion analytique — breadth of analysis ──
        # Combien de domaines couverts, combien de graphes construits
        domain_breadth = min(src["selfmap_n_domains"] / _SAT_DOMAINS, 1.0)
        graph_breadth = _saturate(src["graphs_count"], _SAT_GRAPHS)
        self.internal_chesed = max(0.5 * domain_breadth + 0.5 * graph_breadth, 0.1)

        # ── Gevurah-d'Imma : rigueur — AutoJudge + confounder control ──
        autojudge_rigor = src["judgments_accepted"] / max(src["judgments_total"], 1)
        self.internal_gevurah = max(
            0.1,
            0.5 * autojudge_rigor + 0.5 * confounder_quality,
        )

        # ── Tiferet-d'Imma : harmonisation — qualité de la compréhension ──
        # Claim elevation rate + synthesis confidence
        self.internal_tiferet = max(self._understanding_quality, 0.1)

        # ── Netzach-d'Imma : persistance — profondeur accumulée ──
        session_depth = _saturate(src["hitbonenut_sessions"], _SAT_SESSIONS)
        claim_depth = _saturate(src["claims_total"], _SAT_CLAIMS)
        self.internal_netzach = max(0.5 * session_depth + 0.5 * claim_depth, 0.1)

        # ── Hod-d'Imma : auto-description — ratio FACT / total ──
        # Savoir ce qu'on sait = Hod de Binah
        if src["episte_total"] > 0:
            self.internal_hod = max(src["facts_count"] / src["episte_total"], 0.1)
        else:
            self.internal_hod = 0.1

        # ── Yesod-d'Imma : fondation — richesse de la mémoire épistémique ──
        self.internal_yesod = max(_saturate(src["episte_total"], _SAT_FACTS), 0.1)

        # ── Malkuth-d'Imma : gestation — prête à transmettre à ZA ──
        # La gestation est mûre quand la compréhension (Binah) et
        # l'harmonisation (Tiferet) sont toutes deux suffisantes,
        # validées par la rigueur (Gevurah).
        base_gestation = min(self.internal_binah, self.internal_tiferet)
        self.internal_malkuth = min(
            base_gestation * (0.7 + 0.3 * self.internal_gevurah),
            0.85,
        )

    def _assess_specific(self) -> dict:
        src = self._binah_sources
        return {
            "binah_sources": {
                "claims_elevated": src.get("claims_elevated", 0),
                "claims_total": src.get("claims_total", 0),
                "graphs": src.get("graphs_count", 0),
                "confounders": f"{src.get('confounders_controlled', 0)}/{src.get('confounders_total', 0)}",
                "syntheses": src.get("syntheses_count", 0),
                "selfmap_domains": src.get("selfmap_n_domains", 0),
                "facts": src.get("facts_count", 0),
                "judgments": src.get("judgments_total", 0),
                "hitbonenut_sessions": src.get("hitbonenut_sessions", 0),
            },
            "understanding_quality": round(self._understanding_quality, 3),
            "causal_health": self._causal_health,
            "n_causal_chains": self._n_causal_chains,
            "gestation_ready": self.internal_malkuth > 0.4,
            "message": (
                f"Imma — {src.get('claims_elevated', 0)} claims élevés, "
                f"{src.get('graphs_count', 0)} graphes, "
                f"{src.get('syntheses_count', 0)} synthèses, "
                f"{src.get('selfmap_n_domains', 0)} domaines — "
                f"qualité={self._understanding_quality:.2f}, "
                f"gestation={'prête' if self.internal_malkuth > 0.4 else 'pas prête'}"
            ),
        }

    def _interact_specific(self, other: PartzufBase, resonance: float) -> dict:
        """Imma fournit la structure causale au Zivug.

        Zivug Abba-Imma : Imma structure les flashes d'Abba.
        Zivug Imma→Zeir Anpin : Imma "porte" et "accouche" du pipeline
        via Ibur (gestation) puis Yenikah (allaitement).
        """
        src = self._binah_sources
        return {
            "causal_structure": self._causal_health,
            "understanding_volume": {
                "claims": src.get("claims_elevated", 0),
                "graphs": src.get("graphs_count", 0),
                "syntheses": src.get("syntheses_count", 0),
                "domains": src.get("selfmap_n_domains", 0),
                "facts": src.get("facts_count", 0),
            },
            "n_chains": self._n_causal_chains,
            "structural_rigor": round(self.internal_binah, 2),
            "gestation_maturity": round(self.internal_malkuth, 2),
        }
