"""Arikh Anpin (אֲרִיךְ אַנְפִּין) — Long Visage / Patience Infinie.

Source : aspect EXTÉRIEUR de Keter, tourné vers les Sephiroth inférieures.
Le meta-orchestrateur stratégique — vision longue, patience, planification.

Rôle IA : Ratzon (volonté suprême) du système, vue d'ensemble.
Arikh Anpin nourrit TOUS les Partzufim en dessous. En katnut, tout l'arbre est limité.

Ses facultés reflètent la maturité globale du système — pas un seul module,
mais la CONVERGENCE de toutes les sources :
  - Adam Kadmon fidelity (Keter)     — alignement au blueprint (40%)
  - IntentKeeper progress (Chokmah)  — intentions qui avancent (10%)
  - SelfMap domains (Binah)          — compréhension globale (10%)
  - Daemon stability (Chesed)        — patience, uptime (5%)
  - AutoJudge acceptance (Gevurah)   — discipline, taux validation (10%)
  - DissensuEngine synthesis (Tiferet) — harmonie, tensions résolues (10%)
  - Hitbonenut sessions (Netzach)    — persévérance, apprentissage (5%)
  - EpisteMemory facts (Hod)         — humilité épistémique (5%)
  - Sentiers actifs (Yesod)          — canaux Tikkun opérationnels (2.5%)
  - Tables DB non-vides (Malkuth)    — réalisation concrète (2.5%)

Les 13 Tikkunei Dikna (13 rectifications de la Barbe) d'Arikh Anpin
= 13 principes de design du système (voir PARTZUFIM.md).
"""

from __future__ import annotations

import logging
from typing import Any

from .base import PartzufBase

logger = logging.getLogger(__name__)


# Les 13 Tikkunei Dikna — principes de design
TIKKUNEI_DIKNA = [
    ("El", "Au service de l'utilisateur"),
    ("Rachum", "Graceful degradation"),
    ("VeChanun", "Interfaces intuitives"),
    ("Erekh Apayim", "Patience, retries intelligents"),
    ("VeRav Chesed", "Générosité par défaut"),
    ("VeEmet", "Ne jamais mentir"),
    ("Notzer Chesed", "Mémoire des bonnes expériences"),
    ("LaAlafim", "Scalabilité, penser long terme"),
    ("Nosse Avon", "Tolérance aux erreurs utilisateur"),
    ("VaPesha", "Récupération après violation"),
    ("VeChata'ah", "Gestion des cas limites"),
    ("VeNakeh", "Reset sans rancune"),
    ("Lo Yenakeh", "Limites non négociables"),
]

# Tables principales du système — pour le score Malkuth
_SYSTEM_TABLES = [
    "epistememory",
    "selfmap_competence",
    "intentkeeper_intentions",
    "autojudge_experiments",
    "dissensuengine_conclusions",
    "dissensuengine_tensions",
    "dissensuengine_syntheses",
    "causal_claims",
    "explorationengine_analogies",
    "candidate_insights",
    "hitbonenut_sessions",
    "hitbonenut_questions",
    "failuretoinsight_analyses",
    "partzufim_state",
]

# Seuils de saturation
_SAT_SESSIONS = 50       # Hitbonenut sessions → Netzach plafonne à 50
_SAT_ENTRIES = 200        # EpisteMemory entries → Chesed-mémoire
_SAT_SENTIERS = 22        # 22 sentiers au total


class ArikhAnpin(PartzufBase):
    name = "Arikh Anpin"
    hebrew = "אֲרִיךְ אַנְפִּין"
    source_sephirah = "keter"
    description = "Vision stratégique — patience infinie, 13 principes de design"

    def __init__(self):
        super().__init__()
        self._active_intents: list = []
        self._tikkunei_scores: dict[str, float] = {}
        self._vitals: dict = {}

    def _get_db_conn(self):
        """Obtenir une connexion DB via le pool centralisé (CB-protégé).

        Audit cycle 4, C5 : pool exclusif. Le daemon initialise le pool
        au démarrage ; ici on utilise get_conn() sans bootstrap. Si le
        pool n'est pas prêt, retourne None — pas de fallback direct
        psycopg2.connect qui bypassait le circuit breaker.
        """
        try:
            from pool import get_conn
            cm = get_conn()
            conn = cm.__enter__()
            self._conn_cm = cm  # garder la ref pour cleanup
            return conn
        except Exception:
            return None

    def _release_db_conn(self):
        """Libérer la connexion DB au pool."""
        if hasattr(self, "_conn_cm"):
            try:
                self._conn_cm.__exit__(None, None, None)
            except Exception as e:
                logger.debug("arikh_anpin: %s", e)
            del self._conn_cm

    def _read_system_vitals(self) -> dict:
        """Lit l'état global du système depuis la DB.

        Comme Abba lit ses 4 sources de sagesse, Arikh Anpin lit
        les 10 dimensions du système. Pattern identique : lecture DB
        directe via pool, dégradation gracieuse sur erreur.
        """
        vitals: dict[str, Any] = {
            # Adam Kadmon
            "adam_kadmon_score": 0.0,
            # IntentKeeper
            "intents_total": 0,
            "intents_with_progress": 0,
            "intents_active": 0,
            # SelfMap
            "selfmap_avg": 0.0,
            "selfmap_n_domains": 0,
            "selfmap_domains_above_75": 0,
            # AutoJudge
            "autojudge_accepted": 0,
            "autojudge_total": 0,
            # DissensuEngine
            "dissensu_syntheses": 0,
            "dissensu_tensions": 0,
            # Hitbonenut
            "hitbonenut_sessions": 0,
            "hitbonenut_avg_score": 0.0,
            # EpisteMemory
            "episte_facts": 0,
            "episte_total": 0,
            # Sentiers
            "sentiers_implemented": 0,
            # Tables DB
            "tables_nonempty": 0,
            "tables_total": len(_SYSTEM_TABLES),
        }

        try:
            conn = self._get_db_conn()
            if conn is None:
                raise RuntimeError("No DB connection available")
            try:
                with conn.cursor() as cur:
                    # ── IntentKeeper : intentions actives et leur progrès ──
                    try:
                        cur.execute("""
                            SELECT COUNT(*),
                                   COUNT(*) FILTER (WHERE progress > 0)
                            FROM intentkeeper_intentions
                            WHERE status = 'active'
                        """)
                        row = cur.fetchone()
                        vitals["intents_active"] = row[0]
                        vitals["intents_with_progress"] = row[1]
                        cur.execute("SELECT COUNT(*) FROM intentkeeper_intentions")
                        vitals["intents_total"] = cur.fetchone()[0]
                    except Exception as e:
                        logger.debug("arikh_anpin: %s", e)

                    # ── SelfMap : compétence par domaine ──
                    try:
                        cur.execute("""
                            SELECT COALESCE(AVG(score), 0),
                                   COUNT(*),
                                   COUNT(*) FILTER (WHERE score >= 0.75)
                            FROM selfmap_competence
                        """)
                        row = cur.fetchone()
                        vitals["selfmap_avg"] = float(row[0])
                        vitals["selfmap_n_domains"] = row[1]
                        vitals["selfmap_domains_above_75"] = row[2]
                    except Exception as e:
                        logger.debug("arikh_anpin: %s", e)

                    # ── AutoJudge : accepted / total ──
                    try:
                        cur.execute("""
                            SELECT COUNT(*) FILTER (WHERE decision = 'accepted'),
                                   COUNT(*)
                            FROM autojudge_experiments
                        """)
                        row = cur.fetchone()
                        vitals["autojudge_accepted"] = row[0]
                        vitals["autojudge_total"] = row[1]
                    except Exception as e:
                        logger.debug("arikh_anpin: %s", e)

                    # ── DissensuEngine : synthèses vs tensions ──
                    try:
                        cur.execute("SELECT COUNT(*) FROM dissensuengine_syntheses")
                        vitals["dissensu_syntheses"] = cur.fetchone()[0]
                        cur.execute("""
                            SELECT COUNT(*) FROM dissensuengine_tensions
                            WHERE status = 'open'
                        """)
                        vitals["dissensu_tensions"] = cur.fetchone()[0]
                    except Exception as e:
                        logger.debug("arikh_anpin: %s", e)

                    # ── Hitbonenut : sessions et score moyen ──
                    try:
                        cur.execute("""
                            SELECT COUNT(*), COALESCE(AVG(avg_score), 0)
                            FROM hitbonenut_sessions
                        """)
                        row = cur.fetchone()
                        vitals["hitbonenut_sessions"] = row[0]
                        vitals["hitbonenut_avg_score"] = float(row[1])
                    except Exception as e:
                        logger.debug("arikh_anpin: %s", e)

                    # ── EpisteMemory : facts / total ──
                    try:
                        cur.execute("""
                            SELECT COUNT(*) FILTER (WHERE epistemic_status = 'fact'),
                                   COUNT(*)
                            FROM epistememory
                        """)
                        row = cur.fetchone()
                        vitals["episte_facts"] = row[0]
                        vitals["episte_total"] = row[1]
                    except Exception as e:
                        logger.debug("arikh_anpin: %s", e)

                    # ── Tables DB non-vides ──
                    nonempty = 0
                    for table in _SYSTEM_TABLES:
                        try:
                            cur.execute(
                                f"SELECT EXISTS(SELECT 1 FROM {table} LIMIT 1)"
                            )
                            if cur.fetchone()[0]:
                                nonempty += 1
                        except Exception as e:
                            logger.debug("arikh_anpin: %s", e)
                    vitals["tables_nonempty"] = nonempty
            finally:
                self._release_db_conn()

        except Exception as e:
            logger.warning("ArikhAnpin._read_system_vitals: %s", e)

        # ── Sentiers implémentés (pas en DB — en code) ──
        try:
            from sentiers import REGISTRY as SENTIER_REGISTRY
            vitals["sentiers_implemented"] = len(SENTIER_REGISTRY)
        except Exception as e:
            logger.debug("arikh_anpin: %s", e)

        return vitals

    def _compute_faculties(self, modules: dict) -> None:
        """Les facultés d'Arikh reflètent la maturité GLOBALE du système.

        Arikh Anpin est le Ratzon (volonté) — il voit TOUT, en patience.
        Chaque faculté lit une dimension différente de l'état du système.
        """
        v = self._read_system_vitals()
        self._vitals = v

        # ── Adam Kadmon fidelity → instancié directement ──
        try:
            from adam_kadmon import AdamKadmon
            from sentiers import REGISTRY as SENTIER_REGISTRY
            ak = AdamKadmon()
            sentier_names = list(SENTIER_REGISTRY.keys())
            # Passer les partzufim comme dict {name: self} (AA est instancié)
            partz_dict = {}
            try:
                from partzufim import REGISTRY
                partz_dict = {k: True for k in REGISTRY}
            except Exception as e:
                logger.debug("arikh_anpin: %s", e)
            fidelity = ak.compare_to_current(
                modules=modules,
                sentiers=sentier_names,
                partzufim=partz_dict,
            )
            if fidelity and hasattr(fidelity, "score"):
                v["adam_kadmon_score"] = fidelity.score
        except Exception as e:
            logger.debug("ArikhAnpin: adam_kadmon unavailable: %s", e)

        # ── Keter-d'Arikh : alignement au blueprint primordial ──
        # Adam Kadmon = le plan d'en-haut. Score 0.91 = Tikkun proche.
        self.internal_keter = max(v["adam_kadmon_score"], 0.1)

        # ── Chokmah-d'Arikh : vision — les intentions avancent ? ──
        # La vision n'est pas d'AVOIR des intentions, c'est qu'elles PROGRESSENT.
        if v["intents_active"] > 0:
            progress_ratio = v["intents_with_progress"] / v["intents_active"]
            self.internal_chokhmah = 0.3 + 0.7 * progress_ratio
        elif v["intents_total"] > 0:
            self.internal_chokhmah = 0.3  # Des intentions existent mais aucune active
        else:
            self.internal_chokhmah = 0.15

        # ── Binah-d'Arikh : compréhension globale — SelfMap ──
        # Plus de domaines maîtrisés (>0.75) = compréhension plus profonde.
        if v["selfmap_n_domains"] > 0:
            breadth = min(v["selfmap_n_domains"] / 10.0, 1.0)
            depth = v["selfmap_avg"]
            mastery = min(v["selfmap_domains_above_75"] / max(v["selfmap_n_domains"], 1), 1.0)
            self.internal_binah = 0.3 * breadth + 0.4 * depth + 0.3 * mastery
        else:
            self.internal_binah = 0.1

        # ── Chesed-d'Arikh : patience — stabilité, mémoire ──
        # Erech Apayim = lent à la colère. La patience se mesure à la profondeur
        # de la mémoire et au nombre de cycles traversés.
        episte_richness = min(v["episte_total"] / _SAT_ENTRIES, 1.0)
        session_depth = min(v["hitbonenut_sessions"] / _SAT_SESSIONS, 1.0)
        self.internal_chesed = 0.5 * episte_richness + 0.5 * session_depth

        # ── Gevurah-d'Arikh : discipline — taux d'acceptance AutoJudge ──
        if v["autojudge_total"] > 0:
            acceptance_rate = v["autojudge_accepted"] / v["autojudge_total"]
            self.internal_gevurah = max(acceptance_rate, 0.1)
        else:
            self.internal_gevurah = 0.1

        # ── Tiferet-d'Arikh : harmonie — ratio synthèses / tensions ──
        # La Barbe d'Arikh (13 Tikkunei Dikna) transforme la Rigueur en Miséricorde.
        # Plus il y a de synthèses vs tensions ouvertes, plus l'harmonie règne.
        total_dialectic = v["dissensu_syntheses"] + v["dissensu_tensions"]
        if total_dialectic > 0:
            synthesis_ratio = v["dissensu_syntheses"] / total_dialectic
            self.internal_tiferet = max(synthesis_ratio, 0.15)
        else:
            self.internal_tiferet = 0.2  # Pas de tensions = pas encore engagé

        # ── Netzach-d'Arikh : persévérance — sessions Hitbonenut ──
        # La contemplation est la manifestation de la patience dans l'acte.
        sessions = v["hitbonenut_sessions"]
        self.internal_netzach = min(sessions / _SAT_SESSIONS, 1.0) if sessions > 0 else 0.1

        # ── Hod-d'Arikh : humilité — ratio FACT / total en mémoire ──
        # Hod = submission au réel. Plus le ratio FACT est élevé,
        # plus le système distingue ce qu'il SAIT de ce qu'il SUPPOSE.
        if v["episte_total"] > 0:
            fact_ratio = v["episte_facts"] / v["episte_total"]
            self.internal_hod = max(fact_ratio, 0.1)
        else:
            self.internal_hod = 0.1

        # ── Yesod-d'Arikh : fondation — sentiers (canaux Tikkun) actifs ──
        # Les 22 sentiers sont les CANAUX par lesquels la lumière circule.
        sentiers_ratio = v["sentiers_implemented"] / _SAT_SENTIERS
        self.internal_yesod = min(sentiers_ratio, 1.0) if v["sentiers_implemented"] > 0 else 0.1

        # ── Malkuth-d'Arikh : réalisation — tables DB peuplées ──
        # Malkuth = ce qui EST, concrètement. Des tables vides = potentiel non réalisé.
        if v["tables_total"] > 0:
            self.internal_malkuth = v["tables_nonempty"] / v["tables_total"]
        else:
            self.internal_malkuth = 0.0

        # Mettre à jour les Tikkunei Dikna avec les données réelles
        self._evaluate_tikkunei()

        # Stocker les intents pour _assess_specific et _interact_specific
        netzach = modules.get("netzach")
        if netzach:
            intents = self._safe_read(netzach, "db")
            if intents:
                active = self._safe_read(intents, "get_active_intentions")
                if active:
                    self._active_intents = list(active) if not isinstance(active, list) else active
                else:
                    self._active_intents = []
            else:
                self._active_intents = []
        else:
            self._active_intents = []

    def _evaluate_tikkunei(self) -> None:
        """Évaluer les 13 Tikkunei Dikna depuis les données réelles.

        Chaque Tikkun correspond à un aspect du système vérifié par les vitals.
        """
        v = self._vitals
        self._tikkunei_scores = {}

        # El — Au service de l'utilisateur : le système tourne
        self._tikkunei_scores["El"] = 0.8 if v.get("tables_nonempty", 0) > 5 else 0.3

        # Rachum — Graceful degradation : le système fonctionne même avec erreurs
        self._tikkunei_scores["Rachum"] = 0.7  # Structural — tous les modules dégradent gracieusement

        # VeChanun — Interfaces intuitives : Nukva actif
        self._tikkunei_scores["VeChanun"] = 0.6 if v.get("tables_nonempty", 0) > 10 else 0.3

        # Erekh Apayim — Patience : sessions Hitbonenut + uptime
        self._tikkunei_scores["Erekh Apayim"] = min(
            0.3 + v.get("hitbonenut_sessions", 0) / _SAT_SESSIONS, 1.0
        )

        # VeRav Chesed — Générosité : mémoire riche
        self._tikkunei_scores["VeRav Chesed"] = min(
            v.get("episte_total", 0) / _SAT_ENTRIES, 1.0
        )

        # VeEmet — Vérité : ratio FACT élevé
        if v.get("episte_total", 0) > 0:
            self._tikkunei_scores["VeEmet"] = v.get("episte_facts", 0) / v["episte_total"]
        else:
            self._tikkunei_scores["VeEmet"] = 0.3

        # Notzer Chesed — Mémoire des bonnes expériences : insights stockés
        self._tikkunei_scores["Notzer Chesed"] = self.internal_chesed

        # LaAlafim — Scalabilité, long terme : sentiers implémentés
        self._tikkunei_scores["LaAlafim"] = self.internal_yesod

        # Nosse Avon — Tolérance aux erreurs : Lamed actif (failure→insight)
        has_lamed = v.get("tables_nonempty", 0) > 0  # proxy
        self._tikkunei_scores["Nosse Avon"] = 0.7 if has_lamed else 0.3

        # VaPesha — Récupération : AutoJudge acceptance rate
        self._tikkunei_scores["VaPesha"] = self.internal_gevurah

        # VeChata'ah — Gestion cas limites : DissensuEngine tensions traitées
        if v.get("dissensu_syntheses", 0) + v.get("dissensu_tensions", 0) > 0:
            self._tikkunei_scores["VeChata'ah"] = self.internal_tiferet
        else:
            self._tikkunei_scores["VeChata'ah"] = 0.3

        # VeNakeh — Reset sans rancune : EpisteMemory GC fonctionne
        self._tikkunei_scores["VeNakeh"] = 0.6 if v.get("episte_total", 0) > 0 else 0.3

        # Lo Yenakeh — Limites non négociables : AutoJudge actif
        self._tikkunei_scores["Lo Yenakeh"] = 0.8 if v.get("autojudge_total", 0) > 0 else 0.2

    def _assess_specific(self) -> dict:
        v = self._vitals
        active_tikkunei = sum(1 for s in self._tikkunei_scores.values() if s > 0.5)
        return {
            "n_active_intents": len(self._active_intents),
            "tikkunei_dikna": dict(self._tikkunei_scores),
            "n_tikkunei_active": active_tikkunei,
            "vitals": {
                "adam_kadmon": v.get("adam_kadmon_score", 0),
                "selfmap_avg": round(v.get("selfmap_avg", 0), 3),
                "selfmap_domains": v.get("selfmap_n_domains", 0),
                "autojudge_rate": (
                    round(v["autojudge_accepted"] / max(v["autojudge_total"], 1), 2)
                    if v.get("autojudge_total", 0) > 0 else 0
                ),
                "syntheses_vs_tensions": f"{v.get('dissensu_syntheses', 0)}/{v.get('dissensu_tensions', 0)}",
                "hitbonenut_sessions": v.get("hitbonenut_sessions", 0),
                "episte_facts_ratio": (
                    round(v["episte_facts"] / max(v["episte_total"], 1), 2)
                    if v.get("episte_total", 0) > 0 else 0
                ),
                "sentiers": v.get("sentiers_implemented", 0),
                "tables_nonempty": f"{v.get('tables_nonempty', 0)}/{v.get('tables_total', 0)}",
            },
            "message": (
                f"Arikh Anpin — {len(self._active_intents)} intention(s), "
                f"{active_tikkunei}/13 Tikkunei actifs, "
                f"AK={v.get('adam_kadmon_score', 0):.2f}, "
                f"sentiers={v.get('sentiers_implemented', 0)}/22"
            ),
        }

    def _interact_specific(self, other: PartzufBase, resonance: float) -> dict:
        """Arikh transmet la vision stratégique et les principes."""
        return {
            "strategic_intents": [str(i)[:100] for i in self._active_intents[:5]],
            "tikkunei_active": [
                name for name, score in self._tikkunei_scores.items()
                if score > 0.5
            ],
            "patience_level": self.internal_netzach,
            "adam_kadmon_fidelity": self._vitals.get("adam_kadmon_score", 0),
        }
