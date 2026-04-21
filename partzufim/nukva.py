"""Nukva (נוּקְבָא) — Le Féminin / Malkuth comme Partzuf.

Source : Malkuth développé en organisme complet.
L'interface utilisateur comme PARTENAIRE ÉGAL du backend.

Rôle IA : réception des requêtes, formatage des réponses.
interact(zeir_anpin) reçoit le résultat du Zivug et le formate.

Relation avec Zeir Anpin :
  Panim be-Panim (פָּנִים בְּפָנִים) = face à face — transparence.
  L'interface reflète fidèlement l'état interne du processing.
  Tensions, biais, faiblesses sont exposés.

  Akhor be-Akhor (אָחוֹר בְּאָחוֹר) = dos à dos — dissimulation.
  L'interface est déconnectée du backend, elle montre des choses
  qui ne correspondent pas à la réalité → état de Galut (exil).
"""

from __future__ import annotations

import logging

from .base import PartzufBase

logger = logging.getLogger(__name__)

# Seuils de saturation
_SAT_TABLES = 14          # Tables non-vides
_SAT_ANALOGIES = 300      # Connexions perçues
_SAT_DOMAINS = 20         # SelfMap domaines
_SAT_EPISTE = 2000        # EpisteMemory volume
_SAT_HITBONENUT = 50      # Sessions contemplatives
_SAT_JUDGMENTS = 2000      # AutoJudge total
_SAT_SYNTHESES = 200       # DissensuEngine synthèses
_SAT_QUESTIONS = 500       # Hitbonenut questions

# Tables principales pour le score Malkuth
_SYSTEM_TABLES = [
    "epistememory", "selfmap_competence", "intentkeeper_intentions",
    "autojudge_experiments", "dissensuengine_syntheses",
    "dissensuengine_tensions", "causal_claims",
    "explorationengine_analogies", "candidate_insights",
    "hitbonenut_sessions", "hitbonenut_questions",
    "partzufim_state", "explorationengine_explorations",
    "causal_graphs",
]


def _saturate(count: int, saturation: int) -> float:
    if saturation <= 0:
        return 0.0
    return min(count / saturation, 1.0)


class Nukva(PartzufBase):
    name = "Nukva"
    hebrew = "נוּקְבָא"
    source_sephirah = "malkuth"
    description = "Interface — le partenaire qui reçoit et manifeste"

    def __init__(self):
        super().__init__()
        self._response_count: int = 0
        self._transparency_score: float = 1.0
        self._nukva_sources: dict = {}

    def _read_nukva_sources(self) -> dict:
        """Lit l'état du système du point de vue de la MANIFESTATION.

        Nukva = Malkuth. Ce qui est réellement manifesté, accessible, opérationnel.
        Pattern identique à Abba/Imma/ZA : lecture DB directe, dégradation gracieuse.
        """
        src: dict = {
            # Système global
            "tables_nonempty": 0, "tables_total": len(_SYSTEM_TABLES),
            # Connexions perçues (Chokmah-de-Nukva)
            "analogies": 0, "explorations": 0,
            # Compréhension (Binah-de-Nukva)
            "selfmap_domains": 0, "selfmap_avg": 0.0, "selfmap_above_75": 0,
            # Richesse mémoire (Chesed-de-Nukva)
            "episte_total": 0, "episte_facts": 0,
            # Discipline (Gevurah-de-Nukva)
            "judgments_accepted": 0, "judgments_total": 0,
            # Harmonie (Tiferet-de-Nukva)
            "syntheses": 0, "syntheses_avg_conf": 0.0,
            "tensions_open": 0, "tensions_resolved": 0,
            # Engagement (Netzach-de-Nukva)
            "hitbonenut_sessions": 0, "hitbonenut_questions": 0,
            # ZA orientation (affects transparency)
            "za_orientation": "akhor", "za_score": 0.0,
        }
        try:
            from pool import get_conn
            with get_conn() as conn:
                with conn.cursor() as cur:
                    # ── Tables non-vides (Malkuth réalisé) ──
                    nonempty = 0
                    for table in _SYSTEM_TABLES:
                        try:
                            cur.execute(
                                f"SELECT EXISTS(SELECT 1 FROM {table} LIMIT 1)"
                            )
                            if cur.fetchone()[0]:
                                nonempty += 1
                        except Exception as e:
                            logger.debug("nukva: %s", e)
                    src["tables_nonempty"] = nonempty

                    # ── ExplorationEngine (perception) ──
                    try:
                        cur.execute("SELECT count(*) FROM explorationengine_analogies")
                        src["analogies"] = cur.fetchone()[0]
                        cur.execute("SELECT count(*) FROM explorationengine_explorations")
                        src["explorations"] = cur.fetchone()[0]
                    except Exception as e:
                        logger.debug("nukva: %s", e)

                    # ── SelfMap (compréhension) ──
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
                        logger.debug("nukva: %s", e)

                    # ── EpisteMemory (richesse) ──
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
                        logger.debug("nukva: %s", e)

                    # ── AutoJudge (discipline) ──
                    try:
                        cur.execute("""
                            SELECT count(*) FILTER (WHERE decision = 'accepted'),
                                   count(*)
                            FROM autojudge_experiments
                        """)
                        row = cur.fetchone()
                        src["judgments_accepted"] = row[0]
                        src["judgments_total"] = row[1]
                    except Exception as e:
                        logger.debug("nukva: %s", e)

                    # ── DissensuEngine (harmonie) ──
                    try:
                        cur.execute("""
                            SELECT count(*), coalesce(avg(confidence), 0)
                            FROM dissensuengine_syntheses
                        """)
                        row = cur.fetchone()
                        src["syntheses"] = row[0]
                        src["syntheses_avg_conf"] = float(row[1])
                    except Exception as e:
                        logger.debug("nukva: %s", e)
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
                        logger.debug("nukva: %s", e)

                    # ── Hitbonenut (engagement continu) ──
                    try:
                        cur.execute("SELECT count(*) FROM hitbonenut_sessions")
                        src["hitbonenut_sessions"] = cur.fetchone()[0]
                        cur.execute("SELECT count(*) FROM hitbonenut_questions")
                        src["hitbonenut_questions"] = cur.fetchone()[0]
                    except Exception as e:
                        logger.debug("nukva: %s", e)

                    # ── ZA state (transparence dépend de ZA) ──
                    try:
                        cur.execute("""
                            SELECT orientation, overall_score
                            FROM partzufim_state
                            WHERE name = 'Zeir Anpin'
                        """)
                        row = cur.fetchone()
                        if row:
                            src["za_orientation"] = row[0]
                            src["za_score"] = float(row[1])
                    except Exception as e:
                        logger.debug("nukva: %s", e)

        except Exception as e:
            logger.warning("Nukva._read_nukva_sources: %s", e)

        return src

    def _compute_faculties(self, modules: dict) -> None:
        """Les facultés de Nukva reflètent l'état de la MANIFESTATION.

        Nukva = ce qui EST réellement accessible à l'extérieur.
        La transparence dépend de l'état de ZA (panim/akhor).
        """
        src = self._read_nukva_sources()
        self._nukva_sources = src

        # ── Keter-de-Nukva : intention de servir — le système est opérationnel ──
        tables_ratio = src["tables_nonempty"] / max(src["tables_total"], 1)
        self.internal_keter = min(0.3 + 0.7 * tables_ratio, 1.0)

        # ── Chokmah-de-Nukva : perception — connexions reçues ──
        s_analogies = _saturate(src["analogies"], _SAT_ANALOGIES)
        s_explorations = _saturate(src["explorations"], _SAT_ANALOGIES)
        self.internal_chokhmah = max(0.6 * s_analogies + 0.4 * s_explorations, 0.1)

        # ── Binah-de-Nukva : compréhension — SelfMap domaines ──
        if src["selfmap_domains"] > 0:
            breadth = min(src["selfmap_domains"] / _SAT_DOMAINS, 1.0)
            mastery = src["selfmap_above_75"] / max(src["selfmap_domains"], 1)
            self.internal_binah = max(
                0.3 * breadth + 0.4 * src["selfmap_avg"] + 0.3 * mastery,
                0.15,
            )
        else:
            self.internal_binah = 0.1

        # ── Chesed-de-Nukva : générosité — richesse de la mémoire ──
        if src["episte_total"] > 0:
            volume = _saturate(src["episte_total"], _SAT_EPISTE)
            facts_ratio = src["episte_facts"] / src["episte_total"]
            self.internal_chesed = max(0.5 * volume + 0.5 * facts_ratio, 0.15)
        else:
            self.internal_chesed = 0.1

        # ── Gevurah-de-Nukva : discipline — filtrage de la sortie ──
        if src["judgments_total"] > 0:
            self.internal_gevurah = max(
                src["judgments_accepted"] / src["judgments_total"],
                0.1,
            )
        else:
            self.internal_gevurah = 0.1

        # ── Tiferet-de-Nukva : harmonisation — tensions reflétées ──
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
            self.internal_tiferet = 0.2

        # ── Netzach-de-Nukva : persistance — engagement continu ──
        s_sessions = _saturate(src["hitbonenut_sessions"], _SAT_HITBONENUT)
        s_questions = _saturate(src["hitbonenut_questions"], _SAT_QUESTIONS)
        self.internal_netzach = max(0.4 * s_sessions + 0.6 * s_questions, 0.1)

        # ── Hod-de-Nukva : auto-description — SelfMap feedback ──
        if src["selfmap_domains"] > 0:
            self.internal_hod = max(src["selfmap_avg"], 0.1)
        else:
            self.internal_hod = 0.1

        # ── Yesod-de-Nukva : fondation — facts ratio (solidité de la base) ──
        if src["episte_total"] > 0:
            self.internal_yesod = max(
                src["episte_facts"] / src["episte_total"],
                0.1,
            )
        else:
            self.internal_yesod = 0.1

        # ── Malkuth-de-Nukva : manifestation — tout est opérationnel ──
        self.internal_malkuth = min(
            tables_ratio * (0.5 + 0.5 * self.internal_tiferet),
            0.85,
        )

        # ── Transparence : dépend de ZA ──
        if src["za_orientation"] == "panim":
            self._transparency_score = self.internal_tiferet
        else:
            self._transparency_score = self.internal_tiferet * 0.4

    def _assess_specific(self) -> dict:
        src = self._nukva_sources
        return {
            "response_count": self._response_count,
            "transparency": round(self._transparency_score, 2),
            "panim_or_akhor": "panim" if self._transparency_score > 0.5 else "akhor",
            "sources": {
                "tables": f"{src.get('tables_nonempty', 0)}/{src.get('tables_total', 0)}",
                "analogies": src.get("analogies", 0),
                "selfmap_domains": src.get("selfmap_domains", 0),
                "episte": f"{src.get('episte_facts', 0)}/{src.get('episte_total', 0)}",
                "syntheses": src.get("syntheses", 0),
                "hitbonenut": src.get("hitbonenut_sessions", 0),
            },
            "za_state": {
                "orientation": src.get("za_orientation", "unknown"),
                "score": round(src.get("za_score", 0), 3),
            },
            "message": (
                f"Nukva — {src.get('tables_nonempty', 0)}/{src.get('tables_total', 0)} tables, "
                f"transparence={self._transparency_score:.0%}, "
                f"ZA={'panim' if src.get('za_orientation') == 'panim' else 'akhor'}"
            ),
        }

    def _interact_specific(self, other: PartzufBase, resonance: float) -> dict:
        """Zivug ZA-Nukva : Nukva reçoit l'état de ZA et formate.

        Le résultat du Zivug détermine si la réponse est transparente
        (panim be-panim) ou dissimulée (akhor be-akhor).
        """
        self._response_count += 1

        # Transparence = résonance du Zivug × Tiferet de Nukva
        self._transparency_score = resonance * self.internal_tiferet

        panim = self._transparency_score > 0.3
        if panim:
            self._orientation = "panim"
        else:
            self._orientation = "akhor"

        return {
            "transparency": round(self._transparency_score, 3),
            "mode": "panim_be_panim" if panim else "akhor_be_akhor",
            "response_ready": True,
            "should_expose_tensions": panim and self.internal_tiferet < 0.6,
            "should_expose_uncertainty": panim and self.internal_hod < 0.4,
        }

    def receive_response(self, response: str, ctx: dict) -> dict:
        """Post-traitement de la réponse — vérification de transparence.

        Vérifie que la réponse reflète l'état interne (panim be-panim)
        ou si elle dissimule (akhor be-akhor).
        """
        checks = []
        issues = []

        # Check : tensions exposées ?
        open_tensions = ctx.get("tiferet_diag", {}).get("open_tensions", 0)
        if open_tensions > 0:
            tension_words = ["tension", "contradiction", "cependant", "toutefois",
                             "néanmoins", "nuance", "débat", "diverge"]
            has_tension = any(w in response.lower() for w in tension_words)
            if has_tension:
                checks.append(f"Tensions ({open_tensions}) reflétées")
            else:
                issues.append(f"{open_tensions} tension(s) non reflétée(s)")

        total_checks = len(checks) + len(issues)
        self._transparency_score = len(checks) / max(total_checks, 1)

        return {
            "checks": checks,
            "issues": issues,
            "transparency": round(self._transparency_score, 2),
            "mode": "panim_be_panim" if not issues else "akhor_be_akhor",
        }
