#!/usr/bin/env python3
"""daemon_bridge.py — Masakh HaMavdil : pont Daemon → Pipeline Ask.

מָסָךְ הַמַּבְדִּיל — L'écran séparateur qui devient transparent.

Le Daemon travaille la nuit : il synthétise, forge des insights, tisse
des analogies, construit des graphes causaux. Mais ces Mokhin (lumières
intellectuelles) restent piégées dans les mondes supérieurs — elles ne
descendent pas vers Zeir Anpin (le pipeline Ask qui répond à l'utilisateur).

Ce module est le Masakh qui régule le flux :
- Il cherche dans les 4 productions du Daemon ce qui est PERTINENT
  à la question posée.
- Il respecte un budget tokens (le Masakh ne laisse pas passer un
  flux infini — il dose, comme le Tsimtsum dose l'Or Ein Sof).
- Il retourne un dict structuré prêt à être injecté dans le prompt
  de génération Malkuth.

Principe de conception : timeout 200ms par fetch, fallback gracieux,
aucun crash ne doit remonter au pipeline.
"""

from __future__ import annotations

import logging
import re
import time
from contextlib import contextmanager
from typing import Any

import psycopg2

from pool import get_conn, init_pool

logger = logging.getLogger("daemon_bridge")


def _extract_keywords(text: str, min_len: int = 3) -> list[str]:
    """Extraire les mots-clés significatifs d'une query.

    Filtre les mots trop courts et les stop-words français courants.
    Retourne les mots en minuscule, dédupliqués, dans l'ordre d'apparition.
    """
    stop = {
        "les", "des", "une", "est", "que", "qui", "dans", "pour", "par",
        "sur", "avec", "son", "ses", "aux", "pas", "plus", "tout", "tous",
        "mais", "comme", "être", "avoir", "fait", "peut", "sans", "entre",
        "cette", "ces", "quoi", "comment", "quand", "quel", "quelle",
        "quels", "quelles", "sont", "ont", "était", "elle", "nous", "vous",
        "leur", "aussi", "bien", "même", "très", "trop", "peu", "donc",
        "encore", "car", "cela", "dont", "ici", "après", "avant",
        "the", "and", "for", "that", "with", "this", "from", "are",
        "was", "not", "but", "what", "how", "when", "which", "where",
    }
    words = re.findall(r"[a-zA-ZÀ-ÿ\u0590-\u05FF\u0600-\u06FF]+", text.lower())
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        if len(w) >= min_len and w not in stop and w not in seen:
            seen.add(w)
            result.append(w)
    return result


def _estimate_tokens(text: str) -> int:
    """Estimation grossière : ~4 caractères par token."""
    return len(text) // 4


class DaemonBridge:
    """Pont entre les richesses du Daemon et le Pipeline Ask.

    Kabbalistiquement : le Masakh HaMavdil (écran séparateur) qui devient
    transparent — les Mokhin (lumières intellectuelles) produites par le
    travail nocturne coulent vers Zeir Anpin (le pipeline actif).
    """

    FETCH_TIMEOUT_MS = 200  # ms max par requête DB

    def __init__(self, db_url: str):
        self.db_url = db_url

    @contextmanager
    def _get_conn(self):
        """Emprunte une conn au pool + applique statement_timeout.

        Le timeout est posé au niveau session (autocommit) puis réinitialisé
        à la sortie pour ne pas polluer le prochain emprunteur du pool.
        """
        init_pool(self.db_url)  # idempotent, deferred to first use
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SET statement_timeout = %s",
                    (self.FETCH_TIMEOUT_MS,),
                )
            try:
                yield conn
            finally:
                try:
                    with conn.cursor() as cur:
                        cur.execute("RESET statement_timeout")
                except Exception:
                    # La conn sera fermée par le pool si elle est dans un
                    # état incohérent — on ne rebloque pas le contrôle.
                    pass

    def gather_for_query(
        self,
        query: str,
        domain: str,
        intent: dict | None = None,
        budget_tokens: int = 500,
    ) -> dict[str, list[dict]]:
        """Point d'entrée principal — appelé entre Yesod (⑩) et Malkuth (⑪).

        Cherche dans les 4 sources daemon ce qui est pertinent à la query.
        Respecte le budget tokens (contrôlé par le Masakh).

        Retourne un dict avec les sections pertinentes à injecter dans le prompt.
        Dict vide si rien de pertinent — PAS de remplissage artificiel.
        """
        t0 = time.monotonic()
        result: dict[str, list[dict]] = {}
        remaining = budget_tokens
        keywords = _extract_keywords(query)

        if not keywords:
            logger.debug("DaemonBridge: aucun mot-clé extrait de la query")
            return result

        # 1. Synthèses Tiferet — contradictions/résolutions pertinentes
        synth = self._fetch_relevant_syntheses(keywords, domain, max_tokens=remaining // 4)
        if synth:
            result["tiferet_syntheses"] = synth
            remaining -= sum(_estimate_tokens(s.get("content", "")) for s in synth)

        # 2. Graphes causaux Binah — relations cause→effet pertinentes
        causal = self._fetch_relevant_causal(keywords, domain, max_tokens=remaining // 3)
        if causal:
            result["binah_causal"] = causal
            remaining -= sum(
                _estimate_tokens(f"{c.get('cause', '')} {c.get('effect', '')}")
                for c in causal
            )

        # 3. Analogies Chesed — connexions inter-domaines pertinentes
        analogies = self._fetch_relevant_analogies(keywords, domain, max_tokens=remaining // 2)
        if analogies:
            result["chesed_analogies"] = analogies
            remaining -= sum(_estimate_tokens(a.get("explanation", "")) for a in analogies)

        # 4. Insights Chokmah — insights validés pertinents
        if remaining > 30:
            insights = self._fetch_relevant_insights(keywords, domain, max_tokens=remaining)
            if insights:
                result["chokmah_insights"] = insights

        elapsed = (time.monotonic() - t0) * 1000
        n_total = sum(len(v) for v in result.values())
        logger.info(
            "DaemonBridge: %d items en %.0fms (budget=%d, restant≈%d) — %s",
            n_total, elapsed, budget_tokens, remaining,
            ", ".join(f"{k}:{len(v)}" for k, v in result.items()) or "vide",
        )
        return result

    # ── Fetch methods ─────────────────────────────────────────

    def _fetch_relevant_syntheses(
        self, keywords: list[str], domain: str, max_tokens: int = 125,
    ) -> list[dict]:
        """Synthèses Tiferet — contradictions résolues pertinentes.

        Cherche dans dissensuengine_syntheses les synthèses dont le domaine
        ou le contenu matchent les mots-clés de la query.
        """
        if max_tokens < 20:
            return []
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    # Construire la clause ILIKE pour chaque mot-clé
                    conditions = []
                    params: list[Any] = []
                    if domain:
                        conditions.append("domain ILIKE %s")
                        params.append(f"%{domain}%")
                    if keywords:
                        kw_clauses = " OR ".join(
                            ["content ILIKE %s"] * len(keywords)
                        )
                        conditions.append(f"({kw_clauses})")
                        params.extend(f"%{kw}%" for kw in keywords[:5])

                    where = " OR ".join(conditions) if conditions else "TRUE"
                    cur.execute(
                        f"""
                        SELECT mode, content, domain, confidence
                        FROM dissensuengine_syntheses
                        WHERE {where}
                        ORDER BY confidence DESC, created_at DESC
                        LIMIT 3
                        """,
                        params,
                    )
                    rows = cur.fetchall()

            results = []
            budget = max_tokens
            for mode, content, dom, confidence in rows:
                tokens = _estimate_tokens(content)
                if budget - tokens < 0 and results:
                    break
                results.append({
                    "mode": mode,
                    "content": content[:500],
                    "domain": dom or "",
                    "confidence": round(confidence, 2),
                })
                budget -= tokens
            logger.debug("DaemonBridge/Tiferet: %d synthèse(s)", len(results))
            return results

        except psycopg2.Error as e:
            logger.warning("DaemonBridge/Tiferet: DB error — %s", e)
            return []
        except Exception as e:
            logger.warning("DaemonBridge/Tiferet: error — %s", e)
            return []

    def _fetch_relevant_causal(
        self, keywords: list[str], domain: str, max_tokens: int = 125,
    ) -> list[dict]:
        """Graphes causaux Binah — relations cause→effet pertinentes.

        Filtre : seulement 'probable_causation' ou 'demonstrated_causation'.
        """
        if max_tokens < 20:
            return []
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    kw_clauses = []
                    params: list[Any] = []
                    for kw in keywords[:5]:
                        kw_clauses.append("(cause ILIKE %s OR effect ILIKE %s)")
                        params.extend([f"%{kw}%", f"%{kw}%"])

                    kw_where = (
                        " OR ".join(kw_clauses) if kw_clauses else "TRUE"
                    )
                    cur.execute(
                        f"""
                        SELECT cause, effect, evidence_level, confidence
                        FROM causal_claims
                        WHERE evidence_level IN (
                            'probable_causation', 'demonstrated_causation'
                        )
                        AND ({kw_where})
                        ORDER BY confidence DESC, created_at DESC
                        LIMIT 5
                        """,
                        params,
                    )
                    rows = cur.fetchall()

            results = []
            budget = max_tokens
            for cause, effect, level, confidence in rows:
                text = f"{cause} → {effect}"
                tokens = _estimate_tokens(text)
                if budget - tokens < 0 and results:
                    break
                results.append({
                    "cause": cause,
                    "effect": effect,
                    "evidence_level": level,
                    "confidence": round(confidence, 2),
                })
                budget -= tokens
            logger.debug("DaemonBridge/Binah: %d claim(s)", len(results))
            return results

        except psycopg2.Error as e:
            logger.warning("DaemonBridge/Binah: DB error — %s", e)
            return []
        except Exception as e:
            logger.warning("DaemonBridge/Binah: error — %s", e)
            return []

    def _fetch_relevant_analogies(
        self, keywords: list[str], domain: str, max_tokens: int = 125,
    ) -> list[dict]:
        """Analogies Chesed — connexions inter-domaines pertinentes."""
        if max_tokens < 20:
            return []
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    conditions = []
                    params: list[Any] = []

                    # Match domaine
                    if domain:
                        conditions.append(
                            "(domain_a = %s OR domain_b = %s)"
                        )
                        params.extend([domain, domain])

                    # Match mots-clés dans pattern ou explanation
                    if keywords:
                        kw_clauses = " OR ".join(
                            ["pattern ILIKE %s OR explanation ILIKE %s"]
                            * len(keywords[:5])
                        )
                        conditions.append(f"({kw_clauses})")
                        for kw in keywords[:5]:
                            params.extend([f"%{kw}%", f"%{kw}%"])

                    where = " OR ".join(conditions) if conditions else "TRUE"
                    cur.execute(
                        f"""
                        SELECT domain_a, domain_b, pattern, explanation, strength
                        FROM explorationengine_analogies
                        WHERE {where}
                        ORDER BY strength DESC, created_at DESC
                        LIMIT 3
                        """,
                        params,
                    )
                    rows = cur.fetchall()

            results = []
            budget = max_tokens
            for domain_a, domain_b, pattern, explanation, strength in rows:
                tokens = _estimate_tokens(explanation)
                if budget - tokens < 0 and results:
                    break
                results.append({
                    "domain_a": domain_a,
                    "domain_b": domain_b,
                    "pattern": pattern,
                    "explanation": explanation[:400],
                    "strength": round(strength, 2) if strength else 0.5,
                })
                budget -= tokens
            logger.debug("DaemonBridge/Chesed: %d analogie(s)", len(results))
            return results

        except psycopg2.Error as e:
            logger.warning("DaemonBridge/Chesed: DB error — %s", e)
            return []
        except Exception as e:
            logger.warning("DaemonBridge/Chesed: error — %s", e)
            return []

    def _fetch_relevant_insights(
        self, keywords: list[str], domain: str, max_tokens: int = 125,
    ) -> list[dict]:
        """Insights Chokmah — insights validés (status='insight') pertinents."""
        if max_tokens < 20:
            return []
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cur:
                    match_clauses = []
                    params: list[Any] = []
                    for kw in keywords[:5]:
                        match_clauses.append("description ILIKE %s")
                        params.append(f"%{kw}%")

                    if domain:
                        match_clauses.append("domain ILIKE %s")
                        params.append(f"%{domain}%")

                    match_where = (
                        " OR ".join(match_clauses) if match_clauses else "TRUE"
                    )

                    cur.execute(
                        f"""
                        SELECT description, source_module, confidence,
                               connects_domains
                        FROM candidate_insights
                        WHERE status = 'insight'
                        AND ({match_where})
                        ORDER BY confidence DESC, created_at DESC
                        LIMIT 3
                        """,
                        params,
                    )
                    rows = cur.fetchall()

            results = []
            budget = max_tokens
            for description, source_module, confidence, connects in rows:
                tokens = _estimate_tokens(description)
                if budget - tokens < 0 and results:
                    break
                results.append({
                    "content": description[:400],
                    "source_module": source_module or "",
                    "confidence": round(confidence, 2),
                    "connects_domains": connects or [],
                })
                budget -= tokens
            logger.debug("DaemonBridge/Chokmah: %d insight(s)", len(results))
            return results

        except psycopg2.Error as e:
            logger.warning("DaemonBridge/Chokmah: DB error — %s", e)
            return []
        except Exception as e:
            logger.warning("DaemonBridge/Chokmah: error — %s", e)
            return []


# ── Formatage pour injection dans le prompt Malkuth ────────

def format_daemon_enrichment(enrichment: dict[str, list[dict]]) -> str:
    """Formatter les résultats du DaemonBridge pour le prompt de génération.

    Chaque section a un header clair. Le format est compact pour respecter
    le budget tokens.
    """
    if not enrichment:
        return ""

    parts = []

    # Tiferet — synthèses
    synths = enrichment.get("tiferet_syntheses", [])
    if synths:
        parts.append("[Connaissances accumulées — Synthèses (Tiferet):]")
        for s in synths:
            mode_label = "synthèse" if s["mode"] == "synthesis" else "dissensus"
            parts.append(
                f"  - [{mode_label}, conf={s['confidence']:.2f}] {s['content'][:300]}"
            )

    # Binah — causal
    causal = enrichment.get("binah_causal", [])
    if causal:
        parts.append("[Connaissances accumulées — Relations causales (Binah):]")
        for c in causal:
            parts.append(
                f"  - [{c['evidence_level']}, conf={c['confidence']:.2f}] "
                f"{c['cause']} → {c['effect']}"
            )

    # Chesed — analogies
    analogies = enrichment.get("chesed_analogies", [])
    if analogies:
        parts.append("[Connaissances accumulées — Analogies inter-domaines (Chesed):]")
        for a in analogies:
            parts.append(
                f"  - [{a['domain_a']}↔{a['domain_b']}, force={a['strength']:.2f}] "
                f"{a['pattern']}: {a['explanation'][:200]}"
            )

    # Chokmah — insights
    insights = enrichment.get("chokmah_insights", [])
    if insights:
        parts.append("[Connaissances accumulées — Insights validés (Chokmah):]")
        for i in insights:
            parts.append(
                f"  - [conf={i['confidence']:.2f}] {i['content'][:300]}"
            )

    return "\n".join(parts)
