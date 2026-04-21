"""Accès base de données — Yesod de Binah."""

from __future__ import annotations

from contextlib import contextmanager

import json
from uuid import UUID

import psycopg2
import psycopg2.extras

from pool import get_conn, init_pool

from causalengine.models import (
    CausalClaim,
    CausalEdge,
    CausalGraph,
    CausalNode,
    Confounder,
)

psycopg2.extras.register_uuid()


def _row_to_graph(row: dict) -> CausalGraph:
    nodes_raw = row.get("nodes") or []
    edges_raw = row.get("edges") or []
    nodes = [
        CausalNode(
            node_id=n["id"], name=n["name"],
            node_type=n.get("type", "variable"),
            domain=n.get("domain", ""),
        )
        for n in nodes_raw
    ]
    edges = [
        CausalEdge(
            source=e["source"], target=e["target"],
            edge_type=e.get("edge_type", "causes"),
            confidence=e.get("confidence", 0.5),
            evidence_level=e.get("evidence_level", "correlation_only"),
        )
        for e in edges_raw
    ]
    return CausalGraph(
        id=row["id"],
        name=row["name"],
        domain=row.get("domain", ""),
        description=row.get("description", ""),
        nodes=nodes,
        edges=edges,
        confounders_checked=row.get("confounders_checked", False),
        evidence_level=row.get("evidence_level", "association"),
        source_data=row.get("source_data") or {},
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _row_to_claim(row: dict) -> CausalClaim:
    return CausalClaim(
        id=row["id"],
        graph_id=row.get("graph_id"),
        cause=row["cause"],
        effect=row["effect"],
        evidence_level=row.get("evidence_level", "correlation_only"),
        known_confounders=row.get("known_confounders") or [],
        confounders_controlled=row.get("confounders_controlled", False),
        direction_verified=row.get("direction_verified", False),
        reverse_plausible=row.get("reverse_plausible"),
        appropriate_language=row.get("appropriate_language", ""),
        confidence=row.get("confidence", 0.5),
        created_at=row.get("created_at"),
    )


def _row_to_confounder(row: dict) -> Confounder:
    return Confounder(
        id=row["id"],
        claim_id=row.get("claim_id"),
        confounder_name=row["confounder_name"],
        confounder_domain=row.get("confounder_domain", ""),
        plausibility=row.get("plausibility", 0.5),
        controlled=row.get("controlled", False),
        how_controlled=row.get("how_controlled", ""),
        created_at=row.get("created_at"),
    )


class CausalDB:
    """CRUD pour CausalEngine — Binah persiste ses DAGs causaux."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        init_pool(db_url)  # idempotent

    def close(self):
        pass  # pool gère les connexions

    @contextmanager
    def _cursor(self, cursor_factory=None):
        """Emprunte une conn + cursor au pool, puis rend."""
        with get_conn() as conn:
            if cursor_factory:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
            else:
                with conn.cursor() as cur:
                    yield cur

    # --- Graphs ---

    def save_graph(self, graph: CausalGraph) -> CausalGraph:
        nodes_json = json.dumps([n.to_dict() for n in graph.nodes])
        edges_json = json.dumps([e.to_dict() for e in graph.edges])
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO causal_graphs
                   (name, domain, description, nodes, edges,
                    confounders_checked, evidence_level, source_data)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    graph.name, graph.domain, graph.description,
                    nodes_json, edges_json,
                    graph.confounders_checked, graph.evidence_level,
                    json.dumps(graph.source_data),
                ),
            )
            return _row_to_graph(cur.fetchone())

    def get_graph(self, graph_id: UUID) -> CausalGraph | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM causal_graphs WHERE id = %s", (graph_id,))
            row = cur.fetchone()
            return _row_to_graph(row) if row else None

    def get_graphs(self, domain: str | None = None, limit: int = 50) -> list[CausalGraph]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if domain:
                cur.execute(
                    "SELECT * FROM causal_graphs WHERE domain = %s "
                    "ORDER BY created_at DESC LIMIT %s",
                    (domain, limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM causal_graphs ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
            return [_row_to_graph(r) for r in cur.fetchall()]

    def update_graph(self, graph: CausalGraph) -> CausalGraph | None:
        if graph.id is None:
            return None
        nodes_json = json.dumps([n.to_dict() for n in graph.nodes])
        edges_json = json.dumps([e.to_dict() for e in graph.edges])
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE causal_graphs
                   SET nodes = %s, edges = %s,
                       confounders_checked = %s, evidence_level = %s,
                       updated_at = NOW()
                   WHERE id = %s RETURNING *""",
                (
                    nodes_json, edges_json,
                    graph.confounders_checked, graph.evidence_level,
                    graph.id,
                ),
            )
            row = cur.fetchone()
            return _row_to_graph(row) if row else None

    # --- Claims ---

    def save_claim(self, claim: CausalClaim) -> CausalClaim:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO causal_claims
                   (graph_id, cause, effect, evidence_level,
                    known_confounders, confounders_controlled,
                    direction_verified, reverse_plausible,
                    appropriate_language, confidence)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    claim.graph_id, claim.cause, claim.effect,
                    claim.evidence_level, claim.known_confounders,
                    claim.confounders_controlled,
                    claim.direction_verified, claim.reverse_plausible,
                    claim.appropriate_language, claim.confidence,
                ),
            )
            return _row_to_claim(cur.fetchone())

    def get_claims(
        self,
        graph_id: UUID | None = None,
        evidence_level: str | None = None,
        limit: int = 50,
    ) -> list[CausalClaim]:
        clauses: list[str] = []
        params: list = []
        if graph_id:
            clauses.append("graph_id = %s")
            params.append(graph_id)
        if evidence_level:
            clauses.append("evidence_level = %s")
            params.append(evidence_level)

        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"SELECT * FROM causal_claims {where} "
                f"ORDER BY created_at DESC LIMIT %s",
                params,
            )
            return [_row_to_claim(r) for r in cur.fetchall()]

    def update_claim(self, claim: CausalClaim) -> CausalClaim | None:
        if claim.id is None:
            return None
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE causal_claims
                   SET evidence_level = %s, known_confounders = %s,
                       confounders_controlled = %s,
                       direction_verified = %s, reverse_plausible = %s,
                       appropriate_language = %s, confidence = %s
                   WHERE id = %s RETURNING *""",
                (
                    claim.evidence_level, claim.known_confounders,
                    claim.confounders_controlled,
                    claim.direction_verified, claim.reverse_plausible,
                    claim.appropriate_language, claim.confidence,
                    claim.id,
                ),
            )
            row = cur.fetchone()
            return _row_to_claim(row) if row else None

    # --- Confounders ---

    def save_confounder(self, confounder: Confounder) -> Confounder:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO causal_confounders
                   (claim_id, confounder_name, confounder_domain,
                    plausibility, controlled, how_controlled)
                   VALUES (%s, %s, %s, %s, %s, %s)
                   RETURNING *""",
                (
                    confounder.claim_id, confounder.confounder_name,
                    confounder.confounder_domain,
                    confounder.plausibility, confounder.controlled,
                    confounder.how_controlled,
                ),
            )
            return _row_to_confounder(cur.fetchone())

    def get_claims_without_contextual_confounders(
        self, limit: int = 20,
    ) -> list[CausalClaim]:
        """Claims qui n'ont pas encore de confounders contextuels (LLM)."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT c.* FROM causal_claims c
                   WHERE NOT EXISTS (
                       SELECT 1 FROM causal_confounders cf
                       WHERE cf.claim_id = c.id
                       AND cf.confounder_domain = 'contextual'
                   )
                   ORDER BY c.created_at DESC
                   LIMIT %s""",
                (limit,),
            )
            return [_row_to_claim(r) for r in cur.fetchall()]

    def get_confounders(self, claim_id: UUID) -> list[Confounder]:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM causal_confounders WHERE claim_id = %s "
                "ORDER BY plausibility DESC",
                (claim_id,),
            )
            return [_row_to_confounder(r) for r in cur.fetchall()]

    def mark_confounder_controlled(
        self, confounder_id: UUID, how: str,
    ) -> Confounder | None:
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """UPDATE causal_confounders
                   SET controlled = true, how_controlled = %s
                   WHERE id = %s RETURNING *""",
                (how, confounder_id),
            )
            row = cur.fetchone()
            return _row_to_confounder(row) if row else None

    # --- Elevator queries ---

    def get_all_claims(self, evidence_level: str | None = None) -> list[CausalClaim]:
        """Tous les claims, optionnellement filtrés par niveau."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if evidence_level:
                cur.execute(
                    "SELECT * FROM causal_claims WHERE evidence_level = %s "
                    "ORDER BY confidence DESC",
                    (evidence_level,),
                )
            else:
                cur.execute("SELECT * FROM causal_claims ORDER BY confidence DESC")
            return [_row_to_claim(r) for r in cur.fetchall()]

    def get_cause_frequencies(self) -> dict[str, int]:
        """Nombre de claims par cause (pour détection multi-contexte)."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT cause, COUNT(*) FROM causal_claims GROUP BY cause"
            )
            return {row[0]: row[1] for row in cur.fetchall()}

    def get_effect_frequencies(self) -> dict[str, int]:
        """Nombre de claims par effect (pour détection multi-contexte)."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT effect, COUNT(*) FROM causal_claims GROUP BY effect"
            )
            return {row[0]: row[1] for row in cur.fetchall()}

    def get_contextual_confounder_count(self, claim_id: UUID) -> int:
        """Nombre de confounders contextuels pour un claim."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM causal_confounders "
                "WHERE claim_id = %s AND confounder_domain = 'contextual'",
                (claim_id,),
            )
            return cur.fetchone()[0]

    def bulk_update_evidence(
        self,
        updates: list[tuple[str, float, str]],
    ) -> int:
        """Mise à jour en batch de evidence_level et confidence.

        updates: list of (evidence_level, confidence, appropriate_language, claim_id)
        Returns: number of rows updated.
        """
        if not updates:
            return 0
        with self._cursor() as cur:
            psycopg2.extras.execute_batch(
                cur,
                """UPDATE causal_claims
                   SET evidence_level = %s, confidence = %s,
                       appropriate_language = %s
                   WHERE id = %s""",
                updates,
            )
            return len(updates)
