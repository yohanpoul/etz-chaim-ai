"""Ratzo v'Shov — les rejets nourrissent la génération suivante.

רצוא ושוב — Ratzo (élan, montée) et Shov (retour, intégration).
Le Zohar (Ezéchiel 1:14) : "Les Hayot courent et reviennent"
(והחיות רצוא ושוב).

L'insight est un mouvement de Ratzo — l'intuition brute monte.
Mais 80% des candidats sont rejetés comme doublons et OUBLIÉS.
Le Shov manque : les patterns de rejet doivent informer le cycle
suivant pour que l'apprentissage opère.

Diagnostic empirique (498 rejets / 730 candidats = 68%) :
  - 80% des rejets = doublons intra-batch (Jaccard trop élevé)
  - hitbonenut : 336 rejets / 486 total — ratio le pire
  - failuretoinsight : 120 rejets / 130 total — quasi-stérile
  - Aucune validation binah/gevurah sur les rejetés
"""

from __future__ import annotations

import logging
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field

import psycopg2

log = logging.getLogger(__name__)


# --- Catégories de rejet ---

REJECTION_DUPLICATE = "duplicate"
REJECTION_NOT_CAUSAL = "not_causal"
REJECTION_NOT_NOVEL = "not_novel"
REJECTION_TRIVIAL = "trivial"
REJECTION_MAX_REACHED = "max_reached"
REJECTION_VALIDATION_FAILED = "validation_failed"
REJECTION_OTHER = "other"

# Tikkun Ghagiel: prevent Shov from over-constraining
MAX_AVOIDED_PAIRS = 5       # Max domain pairs to avoid (was unlimited)
SHOV_RESET_DAYS = 7         # Reset avoided pairs every 7 days (Shabbat du Shov)


@dataclass
class RejectionPattern:
    """Pattern de rejet agrégé sur un ensemble de candidats."""
    total_rejected: int = 0
    total_candidates: int = 0
    by_category: dict[str, int] = field(default_factory=dict)
    by_source: dict[str, int] = field(default_factory=dict)
    by_domain_pair: dict[str, int] = field(default_factory=dict)
    top_rejection_reasons: list[str] = field(default_factory=list)

    @property
    def rejection_rate(self) -> float:
        if self.total_candidates == 0:
            return 0.0
        return self.total_rejected / self.total_candidates


def _categorize_rejection(reason: str) -> str:
    """Catégorise un motif de rejet textuel."""
    reason_lower = reason.lower()
    if "duplicate" in reason_lower or "reformulation" in reason_lower:
        return REJECTION_DUPLICATE
    if "max insights" in reason_lower:
        return REJECTION_MAX_REACHED
    if "triple validation" in reason_lower:
        return REJECTION_VALIDATION_FAILED
    if "binah" in reason_lower and "not" not in reason_lower:
        return REJECTION_NOT_CAUSAL
    if "trivial" in reason_lower:
        return REJECTION_TRIVIAL
    if "not novel" in reason_lower or "not new" in reason_lower:
        return REJECTION_NOT_NOVEL
    if "already" in reason_lower:
        return REJECTION_NOT_NOVEL
    return REJECTION_OTHER


class RatzoVShov:
    """Boucle d'apprentissage par l'échec pour InsightForge.

    Après chaque cycle de forge (Ratzo), analyse les rejets
    et construit un contexte (Shov) qui guide le cycle suivant.
    """

    def __init__(self, db_url: str = "postgresql://localhost/etz_chaim"):
        self.db_url = db_url

    @contextmanager
    def _get_conn(self):
        """Connexion DB via pool centralisé (CB-protégé)."""
        from pool import get_conn, init_pool
        init_pool(self.db_url)  # idempotent
        with get_conn() as conn:
            yield conn

    def analyze_rejections(
        self,
        session_ids: list | None = None,
        limit: int = 5,
    ) -> RejectionPattern:
        """Analyser les rejets récents et extraire les patterns.

        Args:
            session_ids: IDs de sessions spécifiques, ou None pour les N dernières.
            limit: Nombre de sessions récentes à analyser si session_ids est None.
        """
        pattern = RejectionPattern()
        category_counter: Counter[str] = Counter()
        source_counter: Counter[str] = Counter()
        domain_pair_counter: Counter[str] = Counter()
        reasons: list[str] = []

        with self._get_conn() as conn:
            cur = conn.cursor()

            if session_ids:
                placeholders = ",".join(["%s"] * len(session_ids))
                where_clause = f"session_id IN ({placeholders})"
                params: list = list(session_ids)
            else:
                # Dernières N sessions
                cur.execute(
                    "SELECT id FROM insight_sessions "
                    "ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                recent_ids = [r[0] for r in cur.fetchall()]
                if not recent_ids:
                    cur.close()
                    return pattern
                placeholders = ",".join(["%s"] * len(recent_ids))
                where_clause = f"session_id IN ({placeholders})"
                params = recent_ids

            # Tous les candidats de ces sessions
            cur.execute(
                f"SELECT status, source_module, domain, "
                f"rejection_reason, connects_domains, "
                f"binah_validated, gevurah_validated, daat_validated "
                f"FROM candidate_insights WHERE {where_clause}",
                params,
            )

            for row in cur.fetchall():
                status, source, domain, reason, connects, binah, gevurah, daat = row
                pattern.total_candidates += 1

                if status != "rejected":
                    continue

                pattern.total_rejected += 1
                source_counter[source] += 1

                # Catégoriser
                cat = _categorize_rejection(reason or "")
                category_counter[cat] += 1

                # Paire de domaines
                if connects and len(connects) >= 2:
                    pair = f"{connects[0]}↔{connects[1]}"
                    domain_pair_counter[pair] += 1

                if reason and reason not in reasons:
                    reasons.append(reason)

            cur.close()

        pattern.by_category = dict(category_counter.most_common())
        pattern.by_source = dict(source_counter.most_common())
        pattern.by_domain_pair = dict(domain_pair_counter.most_common(10))
        pattern.top_rejection_reasons = reasons[:10]

        return pattern

    def build_shov_context(self, pattern: RejectionPattern) -> str:
        """Construire le contexte Shov pour le prochain cycle.

        Le Shov transforme l'échec en guidance :
        - Quels types de candidats éviter (max 3 règles pour ne pas surcontraindre)
        - Quels domaines diversifier
        - Cadrage positif pour maintenir l'exploration
        """
        if pattern.total_rejected == 0:
            return ""

        lines: list[str] = []
        lines.append(
            f"[Shov] Analyse des {pattern.total_rejected} rejets récents "
            f"({pattern.rejection_rate:.0%} de rejet) :"
        )

        # Guidance par catégorie — max 3 règles pour ne pas surcontraindre le LLM
        guidance_rules: list[tuple[int, str]] = []

        dup_count = pattern.by_category.get(REJECTION_DUPLICATE, 0)
        if dup_count > 0:
            dup_pct = dup_count / pattern.total_rejected * 100
            guidance_rules.append((
                dup_count,
                f"  - {dup_count} doublons ({dup_pct:.0f}%) : "
                "DIVERSIFIER les sources, éviter les reformulations."
            ))

        trivial_count = pattern.by_category.get(REJECTION_TRIVIAL, 0)
        if trivial_count > 0:
            guidance_rules.append((
                trivial_count,
                f"  - {trivial_count} triviaux : "
                "APPROFONDIR les connexions, pas de surface."
            ))

        not_novel = pattern.by_category.get(REJECTION_NOT_NOVEL, 0)
        if not_novel > 0:
            guidance_rules.append((
                not_novel,
                f"  - {not_novel} non-nouveaux : "
                "chercher des angles INÉDITS, pas des faits connus."
            ))

        not_causal = pattern.by_category.get(REJECTION_NOT_CAUSAL, 0)
        if not_causal > 0:
            guidance_rules.append((
                not_causal,
                f"  - {not_causal} non-causaux : "
                "PRIVILÉGIER les connexions causales vérifiables."
            ))

        val_failed = pattern.by_category.get(REJECTION_VALIDATION_FAILED, 0)
        if val_failed > 0:
            guidance_rules.append((
                val_failed,
                f"  - {val_failed} échoués à la triple validation : "
                "renforcer la rigueur des claims."
            ))

        # Trier par fréquence, garder max 3 pour ne pas surcontraindre
        guidance_rules.sort(key=lambda x: -x[0])
        for _, rule in guidance_rules[:3]:
            lines.append(rule)

        # Pire source — identifier la source qui génère le plus de rejets
        if pattern.by_source:
            worst_source, worst_count = max(
                pattern.by_source.items(), key=lambda x: x[1]
            )
            if worst_count >= 3:
                lines.append(
                    f"  - Source '{worst_source}' : {worst_count} rejets — "
                    "ÉVITER ou diversifier cette source."
                )

        # Paires de domaines qui échouent — max 3 paires
        if pattern.by_domain_pair:
            failing_pairs = [
                pair for pair, count in sorted(
                    pattern.by_domain_pair.items(), key=lambda x: -x[1]
                )
                if count >= 3
            ]
            if failing_pairs:
                lines.append(
                    f"  - ÉVITER ces paires récurrentes : "
                    f"{', '.join(failing_pairs[:3])}."
                )

        # Cadrage positif — maintenir l'espace d'exploration ouvert
        accepted = pattern.total_candidates - pattern.total_rejected
        if accepted > 0:
            lines.append(
                f"  + {accepted} insights ACCEPTÉS — continuer dans ces directions."
            )
        lines.append(
            "  + Explorer des domaines et angles NON ENCORE TENTÉS."
        )

        return "\n".join(lines)

    def ratzo_cycle(
        self,
        session_id,
        all_candidates: list | None = None,
    ) -> dict:
        """Après un cycle de forge, analyser et stocker les patterns.

        Args:
            session_id: ID de la session qui vient de se terminer.
            all_candidates: Liste optionnelle de candidats (pour les tests).

        Returns:
            Dict avec pattern, context, et métriques.
        """
        pattern = self.analyze_rejections(
            session_ids=[session_id] if session_id else None,
            limit=1,
        )

        context = self.build_shov_context(pattern)

        result = {
            "session_id": str(session_id) if session_id else None,
            "rejection_rate": pattern.rejection_rate,
            "total_rejected": pattern.total_rejected,
            "total_candidates": pattern.total_candidates,
            "categories": pattern.by_category,
            "worst_source": (
                max(pattern.by_source, key=pattern.by_source.get)
                if pattern.by_source else None
            ),
            "shov_context": context,
        }

        if context:
            log.info(
                "Ratzo v'Shov [session %s]: %d/%d rejetés (%.0f%%), "
                "contexte Shov généré (%d lignes)",
                session_id, pattern.total_rejected,
                pattern.total_candidates, pattern.rejection_rate * 100,
                context.count("\n") + 1,
            )

        return result

    def track_improvement(self, n_sessions: int = 10) -> dict:
        """Comparer le taux de rejet entre sessions successives.

        Si le taux baisse → le Shov fonctionne.
        Si le taux stagne → les patterns ne sont pas discriminants.
        """
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, total_candidates, rejected_count, created_at "
                "FROM insight_sessions "
                "ORDER BY created_at DESC LIMIT %s",
                (n_sessions,),
            )
            rows = cur.fetchall()
            cur.close()

        if len(rows) < 2:
            return {
                "trend": "insufficient_data",
                "sessions_analyzed": len(rows),
                "rates": [],
            }

        # Du plus ancien au plus récent
        rows.reverse()
        rates = []
        for sid, total, rejected, created in rows:
            rate = rejected / total if total > 0 else 0.0
            rates.append({
                "session_id": str(sid),
                "total": total,
                "rejected": rejected,
                "rate": round(rate, 3),
                "date": str(created),
            })

        # Tendance : comparer la première moitié à la seconde
        mid = len(rates) // 2
        first_half = [r["rate"] for r in rates[:mid]]
        second_half = [r["rate"] for r in rates[mid:]]

        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0

        if avg_second < avg_first - 0.05:
            trend = "improving"
        elif avg_second > avg_first + 0.05:
            trend = "degrading"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "sessions_analyzed": len(rates),
            "avg_rejection_rate_early": round(avg_first, 3),
            "avg_rejection_rate_recent": round(avg_second, 3),
            "delta": round(avg_second - avg_first, 3),
            "rates": rates,
        }

    def get_shov_context_for_next_cycle(self, n_sessions: int = 5) -> str:
        """Raccourci : analyser les N dernières sessions et retourner le contexte."""
        pattern = self.analyze_rejections(limit=n_sessions)
        return self.build_shov_context(pattern)

    def accumulate_patterns(self, n_sessions: int = 10) -> dict:
        """Persister les patterns de rejet cumulés dans la DB.

        Shov complet : les patterns ne restent pas éphémères —
        ils s'accumulent comme des Reshimot (traces) pour guider
        les futurs cycles. Le convive se souvient de ce qu'il a refusé.
        """
        pattern = self.analyze_rejections(limit=n_sessions)
        improvement = self.track_improvement(n_sessions)

        if pattern.total_rejected == 0:
            return {"accumulated": False, "reason": "no rejections"}

        import json
        accumulated = {
            "rejection_rate": pattern.rejection_rate,
            "by_category": pattern.by_category,
            "by_source": pattern.by_source,
            "by_domain_pair": pattern.by_domain_pair,
            "trend": improvement.get("trend", "unknown"),
            "delta": improvement.get("delta", 0),
            "n_sessions": n_sessions,
        }

        try:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO epistememory (
                        content, source_sephirah, domain, epistemic_status,
                        confidence, source_detail
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s
                    )
                """, (
                    f"Ratzo v'Shov accumulated: {pattern.total_rejected}/{pattern.total_candidates} "
                    f"rejetés ({pattern.rejection_rate:.0%}), trend={improvement.get('trend')}",
                    "gevurah",
                    "auto_improve",
                    "hypothesis",
                    0.5,
                    json.dumps(accumulated),
                ))
                conn.commit()
                cur.close()
            log.info(
                "Ratzo v'Shov: patterns accumulés (%d rejets, trend=%s)",
                pattern.total_rejected, improvement.get("trend"),
            )
            return {"accumulated": True, **accumulated}
        except Exception as e:
            log.warning("Ratzo v'Shov accumulate failed: %s", e)
            return {"accumulated": False, "error": str(e)}

    def get_high_rejection_domains(self, threshold: float = 0.7) -> list[str]:
        """Retourner les paires de domaines à fort taux de rejet.

        Utilisé par Chesed pour éviter les paires stériles.
        """
        pattern = self.analyze_rejections(limit=10)
        if not pattern.by_domain_pair or pattern.total_rejected == 0:
            return []

        high_rej = []
        for pair, count in pattern.by_domain_pair.items():
            pair_rate = count / pattern.total_rejected
            if pair_rate >= threshold:
                high_rej.append(pair)
        return high_rej
