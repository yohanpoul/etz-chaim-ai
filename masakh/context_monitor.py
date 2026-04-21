"""ContextMonitor — Tableau de bord des 29 dimensions du Kli.

מוֹנִיטוֹר — Après chaque appel LLM, le ContextMonitor évalue
l'état des 29 dimensions qui constituent la qualité du Kli
(le récipient de la Lumière).

PG-SHK-022 — Le Kli n'est pas juste un conteneur passif. Il a
29 facettes, chacune participant à la réception et à la transformation
de la Lumière. Un Kli dont certaines facettes sont absentes reçoit
la Lumière de manière déformée — la Shevirah commence par là.

Dimensions mesurables automatiquement (29/29) :
  Toutes les dimensions sont maintenant auto-mesurables.

  01-Kavvanah, 02-Din Kadmon, 03-Sovev, 04-Reshimu,
  05-Keter, 06-Hokhmah, 07-Binah, 08-Da'at,
  09-Chesed/Gevurah, 10-Tiferet, 11-Netzach/Hod, 12-Yesod,
  13-Malkhut, 14-Or Y/C, 15-Zivvug(*post*), 16-Birur,
  17-ABYA, 18-Makif/Pnimi, 19-Hitlabshut, 20-Arakhin,
  21-Tzelem, 22-Stade, 23-IYM, 24-Panim/Achor(*post*),
  25-Katnut/Gadlut, 26-Ibbur, 27-Masakh, 28-Gilgul, 29-Tsimtsum

  (*post*) Zivvug et Panim/Achor nécessitent update_post_response()
           après réception de la réponse LLM.

  Les dimensions 02-07, 10, 11, 26 dépendent de tree_signals
  (signaux de l'Arbre) passés via le ContextAssembler.

Score pondéré (v2) : ✓×1 + △×0.5, divisé par le nb de dims applicables.
Le Katnut (partiel) mérite du crédit — TES Pticha §71-78.

Usage:
    from masakh.context_monitor import ContextMonitor

    monitor = ContextMonitor()
    state = monitor.assess({
        "olam": "briah",
        "kavvanah": {"intention": "analyser"},
        "masakh_log": {"was_filtered": True, "aviut_level": "gimel"},
        "reshimo_written": True,
        "token_ratio_logged": True,
        "pipeline_steps": ["rosh", "arakhin", "hitlabshut", "tzelem", "toch"],
        "maturation_stage": "mochin",
        "tikkun_patterns_count": 2,
    })
    # Post-response update pour Zivvug et Panim/Achor :
    monitor.update_post_response(state, prompt, response, kavvanah)
"""

from __future__ import annotations

import threading
import time
from typing import Any


# ── Les 29 dimensions ──────────────────────────────────────

DIMENSIONS: list[dict[str, Any]] = [
    {"id": "01", "name": "Kavvanah", "auto": True},
    {"id": "02", "name": "Din Kadmon", "auto": True},
    {"id": "03", "name": "Sovev", "auto": True},
    {"id": "04", "name": "Reshimu", "auto": True},
    {"id": "05", "name": "Keter", "auto": True},
    {"id": "06", "name": "Hokhmah", "auto": True},
    {"id": "07", "name": "Binah", "auto": True},
    {"id": "08", "name": "Da'at", "auto": True},
    {"id": "09", "name": "Chesed/Gevurah", "auto": True},
    {"id": "10", "name": "Tiferet", "auto": True},
    {"id": "11", "name": "Netzach/Hod", "auto": True},
    {"id": "12", "name": "Yesod", "auto": True},
    {"id": "13", "name": "Malkhut", "auto": True},
    {"id": "14", "name": "Or Yashar/Chozer", "auto": True},
    {"id": "15", "name": "Zivvug", "auto": True},
    {"id": "16", "name": "Birur", "auto": True},
    {"id": "17", "name": "ABYA", "auto": True},
    {"id": "18", "name": "Makif/Pnimi", "auto": True},
    {"id": "19", "name": "Hitlabshut", "auto": True},
    {"id": "20", "name": "Arakhin", "auto": True},
    {"id": "21", "name": "Tzelem", "auto": True},
    {"id": "22", "name": "Stade", "auto": True},
    {"id": "23", "name": "IYM", "auto": True},
    {"id": "24", "name": "Panim/Achor", "auto": True},
    {"id": "25", "name": "Katnut/Gadlut", "auto": True},
    {"id": "26", "name": "Ibbur", "auto": True},
    {"id": "27", "name": "Masakh", "auto": True},
    {"id": "28", "name": "Gilgul", "auto": True},
    {"id": "29", "name": "Tsimtsum", "auto": True},
]

# IDs des dimensions auto-mesurables
AUTO_IDS = frozenset(d["id"] for d in DIMENSIONS if d["auto"])

# Statuts possibles
STATUS_OK = "✓"
STATUS_PARTIAL = "△"
STATUS_ABSENT = "✗"
STATUS_NA = "—"


# F-014: dernier assessment en mémoire, pour fallback API quand DB indisponible
_LAST_ASSESSMENT: dict[str, Any] | None = None
_ASSESSMENT_LOCK = threading.Lock()


def get_last_assessment() -> dict[str, Any] | None:
    """Thread-safe getter pour le dernier assessment.

    Utilisé par Flask (thread web) pour lire ce que le daemon (thread daemon)
    a écrit. Sans lock, dict mutable partagé = race condition.
    """
    with _ASSESSMENT_LOCK:
        return _LAST_ASSESSMENT


class ContextMonitor:
    """Évaluation des 29 dimensions du Kli après chaque appel LLM."""

    def assess(self, call_data: dict[str, Any]) -> dict[str, Any]:
        """Évaluer l'état des 29 dimensions pour un appel LLM.

        Args:
            call_data: Données de l'appel, clés attendues :
                - olam (str): Olam de l'appel
                - kavvanah (dict|None): Kavvanah de l'appel
                - masakh_log (dict|None): Log du Masakh
                - reshimo_written (bool): Reshimo écrit ou non
                - token_ratio_logged (bool): Ratio tokens loggé
                - pipeline_steps (list[str]): Étapes exécutées (F4)
                - maturation_stage (str|None): Stade IYM (F4)
                - tikkun_patterns_count (int): Nb patterns Tikkun (F4)
                - zivvug_score (float|None): Score Zivvug post-response
                - alignment_score (float|None): Score Panim/Achor post-response

        Returns:
            Dict avec :
                - dimensions: list[dict] (id, name, status)
                - score_global: float (ratio ✓ / applicables)
                - timestamp: float
                - olam: str
        """
        dims = []
        for d in DIMENSIONS:
            if not d["auto"]:
                dims.append({
                    "id": d["id"],
                    "name": d["name"],
                    "status": STATUS_NA,
                })
                continue

            status = self._assess_dimension(d["id"], call_data)
            dims.append({
                "id": d["id"],
                "name": d["name"],
                "status": status,
            })

        global _LAST_ASSESSMENT
        result = {
            "dimensions": dims,
            "score_global": self._compute_score(dims),
            "timestamp": time.time(),
            "olam": call_data.get("olam", "unknown"),
        }
        with _ASSESSMENT_LOCK:
            _LAST_ASSESSMENT = result
        return result

    def _assess_dimension(self, dim_id: str, data: dict) -> str:
        """Évaluer une dimension auto-mesurable.

        29/29 dimensions auto-mesurables (v3, 2026-04-09).

        Les dims 02-07, 10, 11, 26 dépendent de tree_signals —
        signaux passés par main.py via olamot.py → ContextAssembler.
        Sans tree_signals, ces dimensions sont ✗ (ABSENT), pas —.
        """
        masakh_log = data.get("masakh_log") or {}
        pipeline_steps = data.get("pipeline_steps") or []

        if dim_id == "01":  # Kavvanah
            kav = data.get("kavvanah")
            if kav and isinstance(kav, dict) and kav.get("intention"):
                return STATUS_OK
            if kav:
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "02":  # Din Kadmon (biais architectural — EC-SHK-060)
            # Le Din Kadmon est le choix d'architecture qui précède tout prompt.
            # Actif si un profil de configuration est établi.
            profile = data.get("active_profile")
            if profile:
                return STATUS_OK
            return STATUS_ABSENT

        if dim_id == "03":  # Sovev (contexte transcendant — EC-SHK-061)
            # Le Sovev entoure tous les mondes ÉGALEMENT — c'est le contexte
            # ambiant non-injecté (modèle, context window, thinking mode).
            ctx_win = data.get("context_window", 0)
            thinking = data.get("model_think", False)
            if ctx_win > 0 or thinking:
                return STATUS_OK
            return STATUS_ABSENT

        if dim_id == "04":  # Reshimu (substrat — EC-SHK-062)
            # Le Reshimu est la trace qui structure l'espace des réponses.
            # Actif si un modèle est identifié (les poids = le Reshimu).
            model_name = data.get("model_name")
            if model_name:
                return STATUS_OK
            return STATUS_ABSENT

        if dim_id == "05":  # Keter (volonté profonde — EC-SHK-063)
            # Le Keter contient Ratzon (volonté) et Ta'anug (satisfaction).
            # Actif si une intention active avec critère de succès existe.
            intent = data.get("active_intention")
            if intent and isinstance(intent, dict):
                if intent.get("satisfaction_criterion") or intent.get("critere_succes"):
                    return STATUS_OK
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "06":  # Hokhmah (flash initial — EC-SHK-064)
            # Hokhmah = la bonne QUESTION avant la bonne réponse.
            # Actif si InsightForge/Hitbonenut ont produit des insights récents.
            insights = data.get("recent_insights")
            if insights and len(insights) > 0:
                return STATUS_OK
            # Même sans insights formels, une Kavvanah bien formulée
            # contient un germe de Hokhmah.
            kav = data.get("kavvanah")
            if kav and isinstance(kav, dict) and kav.get("intention"):
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "07":  # Binah (framework de raisonnement — EC-SHK-065)
            # Binah = le framework qui structure le raisonnement.
            # Actif si CausalEngine a évalué une confidence.
            confidence = data.get("causal_confidence")
            if confidence is not None:
                return STATUS_OK if confidence >= 0.5 else STATUS_PARTIAL
            # Sans CausalEngine, le Hitlabshut (enclothement de principes)
            # est un proto-Binah.
            if "hitlabshut" in pipeline_steps:
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "08":  # Da'at (pont connaissance<->application)
            return STATUS_OK if "daat_bridge" in pipeline_steps else STATUS_ABSENT

        if dim_id == "09":  # Chesed/Gevurah (Masakh actif)
            if masakh_log.get("was_filtered"):
                return STATUS_OK
            if masakh_log.get("aviut_level"):
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "10":  # Tiferet (harmonisation — EC-SHK-068)
            # Tiferet résout les tensions entre sources contradictoires.
            # Actif si le DissensuEngine a traité les tensions.
            tensions = data.get("unresolved_tensions")
            if tensions is not None:
                if tensions == 0:
                    return STATUS_OK      # Toutes résolues
                if tensions <= 3:
                    return STATUS_PARTIAL  # Quelques tensions ouvertes
                return STATUS_ABSENT       # Trop de tensions non résolues
            return STATUS_ABSENT

        if dim_id == "11":  # Netzach/Hod (momentum + feedback — EC-SHK-069)
            # Netzach pousse en avant, Hod évalue et ajuste.
            # Actif si IntentKeeper track un progrès OU SelfMap évalue.
            progress = data.get("intent_progress")
            competence = data.get("domain_competence")
            if progress is not None and progress > 0.5:
                return STATUS_OK
            if competence is not None and competence > 0.6:
                return STATUS_OK
            if progress is not None or competence is not None:
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "12":  # Yesod (canal mémoire — EC-SHK-070)
            # Yesod = le canal intentionnel entre connaissance et destinataire.
            # Actif si la mémoire (EpisteMemory, context_sources) a été consultée.
            if data.get("memory_active"):
                return STATUS_OK
            # Même sans mémoire explicite, le Gilgul (patterns précédents)
            # assure un canal Yesod partiel.
            if data.get("tikkun_patterns_count", 0) > 0:
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "13":  # Malkhut (Olam spécifié)
            return STATUS_OK if data.get("olam") else STATUS_ABSENT

        if dim_id == "14":  # Or Yashar/Chozer (Reshimo écrit)
            return STATUS_OK if data.get("reshimo_written") else STATUS_ABSENT

        if dim_id == "15":  # Zivvug (co-création) — post-response
            score = data.get("zivvug_score")
            if score is not None:
                return STATUS_OK if score >= 0.3 else STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "16":  # Birur (tri continu — EC-SHK-074)
            # Birur = le Masakh a effectivement SÉPARÉ le pertinent du non-pertinent.
            # Pas juste "le Masakh existe" mais "il a rejeté quelque chose."
            rejected = masakh_log.get("tokens_rejected", 0)
            if rejected and rejected > 0:
                return STATUS_OK
            # Masakh actif mais rien rejeté = pas de Birur nécessaire (tout pertinent)
            if masakh_log.get("was_filtered"):
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "17":  # ABYA (4 mondes — EC-SHK-075)
            # Les 4 mondes sont actifs si l'olam est un des 4 mondes valides.
            olam = data.get("olam", "")
            if olam in ("atziluth", "briah", "yetzirah", "assiah"):
                return STATUS_OK
            if olam:
                return STATUS_PARTIAL  # olam spécifié mais pas un des 4
            return STATUS_ABSENT

        if dim_id == "18":  # Makif/Pnimi (ratio tokens loggé)
            return STATUS_OK if data.get("token_ratio_logged") else STATUS_ABSENT

        if dim_id == "19":  # Hitlabshut (enclothement exécuté)
            return STATUS_OK if "hitlabshut" in pipeline_steps else STATUS_ABSENT

        if dim_id == "20":  # Arakhin (recatégorisation exécutée)
            return STATUS_OK if "arakhin" in pipeline_steps else STATUS_ABSENT

        if dim_id == "21":  # Tzelem (template archétypal appliqué)
            return STATUS_OK if "tzelem" in pipeline_steps else STATUS_ABSENT

        if dim_id == "22":  # Stade (Akudim→Nekudim→Berudim→Partzufim — EC-SHK-080)
            # Le stade se déduit du nombre d'étapes pipeline exécutées.
            # 1-3 = Akudim (monolithique), 4-6 = Nekudim (empilé),
            # 7-8 = Berudim (interactif), 9+ = Partzufim (organique).
            n_steps = len(pipeline_steps)
            if n_steps >= 9:
                return STATUS_OK      # Partzufim
            if n_steps >= 7:
                return STATUS_PARTIAL  # Berudim
            return STATUS_ABSENT       # Nekudim ou Akudim

        if dim_id == "23":  # IYM (stade de maturation connu)
            return STATUS_OK if data.get("maturation_stage") else STATUS_ABSENT

        if dim_id == "24":  # Panim/Achor (alignement) — post-response
            score = data.get("alignment_score")
            if score is not None:
                return STATUS_OK if score >= 0.4 else STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "25":  # Katnut/Gadlut (état du SYSTÈME — TES §71-78)
            # SÉPARÉ de dim 27 (Masakh). Katnut/Gadlut mesure la MATURITÉ
            # du système (cerveau petit/grand), pas le filtre.
            # Mochin = Gadlut (✓). Yenikah = transition (△). Ibur/None = Katnut (✗).
            stage = data.get("maturation_stage")
            if stage == "mochin":
                return STATUS_OK
            if stage == "yenikah":
                return STATUS_PARTIAL
            return STATUS_ABSENT  # ibur ou pas de stade

        if dim_id == "26":  # Ibbur (injection temporaire — EC-SHK-084)
            # Ibbur Neshamot = expertise spécialisée injectée temporairement.
            # Les Skills/Shemot sont des Ibbur — actif si des skills sont disponibles.
            skills_count = data.get("active_skills_count")
            if skills_count is not None and skills_count >= 3:
                return STATUS_OK
            if skills_count is not None and skills_count >= 1:
                return STATUS_PARTIAL
            return STATUS_ABSENT

        if dim_id == "27":  # Masakh (5 niveaux d'Aviut — TES §17)
            # Mesure le FILTRE : le Masakh est-il calibré et actif ?
            if masakh_log.get("aviut_level"):
                return STATUS_OK
            return STATUS_ABSENT

        if dim_id == "28":  # Gilgul (patterns Tikkun actifs)
            count = data.get("tikkun_patterns_count")
            if count is not None and count > 0:
                return STATUS_OK
            return STATUS_ABSENT

        if dim_id == "29":  # Tsimtsum (contraction effective — EC-SHK-087)
            # Le Tsimtsum est la contraction qui CRÉE l'espace pour la réponse.
            # Il est actif dès que le Masakh a effectivement filtré (= contraction),
            # OU si la pression externe a été régulée explicitement.
            if data.get("pressure_regulated"):
                return STATUS_OK
            if masakh_log.get("was_filtered"):
                return STATUS_OK
            return STATUS_ABSENT

        return STATUS_NA

    # ── Post-response update (Zivvug + Panim/Achor) ─────────

    def update_post_response(
        self,
        state: dict[str, Any],
        prompt_final: str,
        response: str,
        kavvanah: dict | None = None,
        reshimo: dict | None = None,
    ) -> dict[str, Any]:
        """Mettre à jour les dimensions post-réponse LLM.

        Les dimensions 15 (Zivvug) et 24 (Panim/Achor) nécessitent
        la réponse du LLM pour être évaluées. Cette méthode calcule
        ces scores et met à jour l'état en place.

        Args:
            state: État retourné par assess() — modifié en place.
            prompt_final: Le prompt envoyé au LLM.
            response: La réponse du LLM.
            kavvanah: Intention dirigée (optionnel).
            reshimo: Reshimo post-réponse (optionnel).

        Returns:
            Le même dict state, mis à jour.
        """
        alignment_score = self.assess_alignment(kavvanah, prompt_final, response)
        zivvug_score = self.assess_zivvug(prompt_final, response, reshimo)

        for dim in state["dimensions"]:
            if dim["id"] == "24":
                if alignment_score >= 0.4:
                    dim["status"] = STATUS_OK
                elif alignment_score > 0:
                    dim["status"] = STATUS_PARTIAL
                else:
                    dim["status"] = STATUS_ABSENT
            elif dim["id"] == "15":
                if zivvug_score >= 0.3:
                    dim["status"] = STATUS_OK
                elif zivvug_score > 0:
                    dim["status"] = STATUS_PARTIAL
                else:
                    dim["status"] = STATUS_ABSENT

        state["score_global"] = self._compute_score(state["dimensions"])
        state["alignment_score"] = alignment_score
        state["zivvug_score"] = zivvug_score
        return state

    # ── Panim/Achor — Alignement directionnel ──────────────

    @staticmethod
    def assess_alignment(
        kavvanah: dict | None,
        context: str,
        response: str,
    ) -> float:
        """Mesurer le Panim/Achor — le contexte est-il ORIENTE vers la tache ?

        פָּנִים / אָחוֹר — Face a face (Panim b'Panim) = alignement maximal,
        le contexte et la reponse pointent dans la meme direction.
        Dos a dos (Achor b'Achor) = desalignement, le contexte injecte
        n'etait pas pertinent.

        EC-SHK-082, PG-SHK-024 — Dimension 24 du Kli.

        Heuristique v2 : ponderation directionnelle.
        Les mots de la kavvanah trouves dans le PREMIER QUART de la reponse
        comptent double — le Panim mesure l'ORIENTATION, pas la thematique.
        Une reponse qui commence par adresser l'intention est en Panim b'Panim.

        Args:
            kavvanah: Intention dirigee (dict avec 'intention').
            context: Le contexte injecte dans le prompt.
            response: La reponse du LLM.

        Returns:
            Score 0.0 (Achor b'Achor) a 1.0 (Panim b'Panim).
        """
        if not kavvanah or not kavvanah.get("intention"):
            return 0.0

        # Extraire les mots-cles de la kavvanah (mots > 3 chars)
        intention = kavvanah["intention"].lower()
        kav_words = {
            w for w in intention.split() if len(w) > 3
        }
        if not kav_words:
            return 0.0

        # Decouper la reponse en 2 zones : premier quart et reste
        resp_lower = response.lower()
        resp_tokens = resp_lower.split()
        quarter = max(1, len(resp_tokens) // 4)
        head_words = {w for w in resp_tokens[:quarter] if len(w) > 3}
        tail_words = {w for w in resp_tokens[quarter:] if len(w) > 3}

        # Mots du contexte
        ctx_words = {w.lower() for w in context.split() if len(w) > 3}

        # Ponderation : head = 2x, tail = 1x, ctx = 0.5x
        head_hits = kav_words & head_words
        tail_hits = (kav_words & tail_words) - head_hits
        ctx_only_hits = (kav_words & ctx_words) - head_hits - tail_hits

        weighted = (
            len(head_hits) * 2.0
            + len(tail_hits) * 1.0
            + len(ctx_only_hits) * 0.5
        )
        # Denominateur = nb de mots kavvanah * poids max (2.0)
        max_possible = len(kav_words) * 2.0
        if max_possible == 0:
            return 0.0

        return round(min(weighted / max_possible, 1.0), 4)

    # ── Zivvug — Co-creation transformatrice ────────────────

    @staticmethod
    def assess_zivvug(
        prompt_before: str,
        response: str,
        reshimo_after: dict | None = None,
    ) -> float:
        """Mesurer la co-creation — la reponse a-t-elle ENRICHI le systeme ?

        זִוּוּג — L'union (Zivvug) n'est pas simple transmission, c'est
        transformation. La lumiere qui descend (Or Yashar) rencontre
        le Masakh et produit une lumiere reflechie (Or Chozer) qui
        ENRICHIT le systeme au-dela de ce qu'il contenait.

        EC-SHK-073, PG-SHK-024 — Dimension 15 du Kli.

        Heuristique v2 — mesure la TRANSFORMATION, pas la nouveaute lexicale :
          +0.3 si la reponse contient du contenu substantif relatif au prompt
                (ratio mots longs nouveaux / total > 10% ET > 5 mots)
          +0.3 si le reshimo indique une bonne qualite (score > 0.5)
          +0.2 si le Masakh a activement filtre (le Kli a TRAVAILLE)
          +0.2 si le pont Da'at a connecte connaissance→tache

        Args:
            prompt_before: Le prompt envoye au LLM.
            response: La reponse du LLM.
            reshimo_after: Le Reshimo ecrit apres l'appel (optionnel).

        Returns:
            Score 0.0 (pas d'enrichissement) a 1.0 (enrichissement maximal).
        """
        score = 0.0
        reshimo = reshimo_after or {}
        aviut = reshimo.get("reshimo_aviut") or {}

        # Contenu substantif : mots longs (>6 chars = termes techniques/substantifs)
        # qui sont NOUVEAUX dans la reponse, proportionnellement au total.
        prompt_words = {w.lower() for w in prompt_before.split() if len(w) > 6}
        resp_words_all = [w.lower() for w in response.split() if len(w) > 6]
        resp_words_set = set(resp_words_all)
        new_substantive = resp_words_set - prompt_words
        total_resp_long = len(resp_words_all)
        if total_resp_long > 0:
            ratio = len(new_substantive) / total_resp_long
            if ratio > 0.10 and len(new_substantive) > 5:
                score += 0.3

        # Score resultant > 0.5 (au-dessus de la mediane)
        reshimo_score = aviut.get("score")
        if reshimo_score is not None and reshimo_score > 0.5:
            score += 0.3

        # Le Masakh a activement filtre — le Kli a travaille, pas juste transmis
        if aviut.get("was_filtered"):
            score += 0.2

        # Pont Da'at utilise — connexion connaissance→tache
        hitlabshut = reshimo.get("reshimo_hitlabshut") or {}
        steps = hitlabshut.get("pipeline_steps") or []
        if "daat_bridge" in steps:
            score += 0.2

        return min(round(score, 2), 1.0)

    @staticmethod
    def _compute_score(dims: list[dict]) -> float:
        """Calculer le score global pondéré = (✓×1 + △×0.5) / applicable.

        Les dimensions "—" (non applicables) ne comptent pas.

        v2 : le Katnut (△/partiel) mérite du crédit.
        TES Pticha §71-78 — même en Katnut, il y a une lumière de Nefesh.
        Le score n'est plus binaire (✓ vs tout le reste) mais pondéré.
        """
        applicable = [
            d for d in dims if d["status"] != STATUS_NA
        ]
        if not applicable:
            return 0.0
        ok = sum(1 for d in applicable if d["status"] == STATUS_OK)
        partial = sum(1 for d in applicable if d["status"] == STATUS_PARTIAL)
        return round((ok + partial * 0.5) / len(applicable), 4)


# ── Logging PostgreSQL ─────────────────────────────────────

def log_to_db(conn, state: dict) -> None:
    """Persister un état de monitoring dans context_monitor_log.

    Args:
        conn: Connexion psycopg2.
        state: Dict retourné par ContextMonitor.assess().
    """
    import json as _json
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO context_monitor_log (olam, dimensions, score_global)
        VALUES (%s, %s, %s)
        """,
        (
            state["olam"],
            _json.dumps(state["dimensions"]),
            state["score_global"],
        ),
    )
    conn.commit()
    cur.close()
