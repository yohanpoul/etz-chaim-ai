"""CausalTreeBuilder — Hashgachah Pratit, la providence des causes.

השגחה פרטית — chaque cause a un effet, chaque effet une cause,
l'ensemble forme un Seder Hishtalshelut causal.

CausalEngine a 1000+ claims individuels mais 0 graphes construits.
Le moteur voit des liens, jamais la structure globale.

CausalTreeBuilder lit tous les claims et construit le graphe causal
complet : composantes connexes, causes racines, chaînes causales,
chemins les plus fiables.

Anti-Satariel : le graphe DIRIGÉ n'est pas symétrisé par erreur.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from uuid import UUID

from causalengine.db import CausalDB
from causalengine.models import (
    CausalEdge,
    CausalGraph,
    CausalNode,
)

log = logging.getLogger("etz-daemon")


@dataclass
class Community:
    """Cluster thématique de causalité — composante connexe."""
    nodes: list[str]
    edges: list[tuple[str, str, float]]  # (source, target, confidence)
    size: int = 0

    def __post_init__(self):
        self.size = len(self.nodes)


@dataclass
class Chain:
    """Chaîne cause -> effet -> effet — Hishtalshelut causal."""
    path: list[str]
    confidences: list[float]
    length: int = 0

    def __post_init__(self):
        self.length = len(self.path)

    @property
    def product_confidence(self) -> float:
        """Produit des confiances le long de la chaîne."""
        result = 1.0
        for c in self.confidences:
            result *= c
        return result


@dataclass
class CausalTreeSummary:
    """Résumé du graphe causal global."""
    total_nodes: int = 0
    total_edges: int = 0
    connected_components: int = 0
    top_root_causes: list[tuple[str, int]] = field(default_factory=list)
    top_terminal_effects: list[tuple[str, int]] = field(default_factory=list)
    longest_chains: list[Chain] = field(default_factory=list)
    strongest_paths: list[Chain] = field(default_factory=list)


class CausalTreeBuilder:
    """Construit le graphe causal global depuis les claims en DB.

    Le graphe est DIRIGÉ : cause -> effect.
    Pas de NetworkX — BFS/DFS pur, le graphe est petit.
    """

    def __init__(self, db: CausalDB):
        self.db = db
        # Adjacency lists (directed)
        self._adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
        # Reverse adjacency (for tracing back)
        self._radj: dict[str, list[tuple[str, float]]] = defaultdict(list)
        # All node names
        self._nodes: set[str] = set()
        # Edge data for persistence
        self._edges: list[tuple[str, str, float]] = []

    def build_graph(self, min_confidence: float = 0.3) -> CausalGraph:
        """Construire le graphe causal global depuis tous les claims.

        1. Récupère les claims avec confiance >= min_confidence
        2. Chaque claim = arête dirigée (cause -> effect)
        3. Déduplique les arêtes (garde la confiance max)
        4. Stocke le graphe en DB
        """
        claims = self._fetch_claims(min_confidence)
        if not claims:
            log.info("CausalTreeBuilder: 0 claims above threshold %.2f", min_confidence)
            return CausalGraph(name="global_causal_tree", description="Empty — no claims above threshold")

        # Build adjacency — deduplicate edges keeping max confidence
        edge_map: dict[tuple[str, str], float] = {}
        for claim in claims:
            cause = self._normalize(claim["cause"])
            effect = self._normalize(claim["effect"])
            if cause == effect:
                continue  # Skip self-loops
            key = (cause, effect)
            edge_map[key] = max(edge_map.get(key, 0.0), claim["confidence"])

        # Build internal structures
        self._adj.clear()
        self._radj.clear()
        self._nodes.clear()
        self._edges.clear()

        for (cause, effect), conf in edge_map.items():
            self._nodes.add(cause)
            self._nodes.add(effect)
            self._adj[cause].append((effect, conf))
            self._radj[effect].append((cause, conf))
            self._edges.append((cause, effect, conf))

        # Build CausalGraph model
        nodes = [
            CausalNode(node_id=n, name=n, node_type="variable")
            for n in sorted(self._nodes)
        ]
        edges = [
            CausalEdge(
                source=src, target=tgt,
                confidence=conf, edge_type="causes",
            )
            for src, tgt, conf in self._edges
        ]
        graph = CausalGraph(
            name="global_causal_tree",
            domain="global",
            description=(
                f"Graphe causal global: {len(nodes)} noeuds, {len(edges)} aretes, "
                f"seuil confidence >= {min_confidence}"
            ),
            nodes=nodes,
            edges=edges,
            evidence_level="association",
            source_data={
                "min_confidence": min_confidence,
                "total_claims_fetched": len(claims),
                "deduplicated_edges": len(edges),
            },
        )

        # Persist
        saved = self.db.save_graph(graph)
        log.info(
            "CausalTreeBuilder: built graph %s — %d nodes, %d edges",
            saved.id, len(nodes), len(edges),
        )
        return saved

    def detect_communities(self) -> list[Community]:
        """Composantes connexes du graphe NON-DIRIGÉ.

        Chaque composante = un cluster thématique de causalité.
        BFS sur le graphe symétrisé.
        """
        if not self._nodes:
            return []

        # Symmetrize adjacency for connected components
        undirected: dict[str, set[str]] = defaultdict(set)
        for src, tgt, _ in self._edges:
            undirected[src].add(tgt)
            undirected[tgt].add(src)

        visited: set[str] = set()
        communities: list[Community] = []

        for start in sorted(self._nodes):
            if start in visited:
                continue
            # BFS
            component_nodes: list[str] = []
            queue = deque([start])
            while queue:
                node = queue.popleft()
                if node in visited:
                    continue
                visited.add(node)
                component_nodes.append(node)
                for neighbor in sorted(undirected.get(node, set())):
                    if neighbor not in visited:
                        queue.append(neighbor)

            # Collect edges within this component
            node_set = set(component_nodes)
            component_edges = [
                (s, t, c) for s, t, c in self._edges
                if s in node_set and t in node_set
            ]

            communities.append(Community(
                nodes=component_nodes,
                edges=component_edges,
            ))

        # Sort by size descending
        communities.sort(key=lambda c: c.size, reverse=True)
        return communities

    def find_root_causes(self, effect: str | None = None) -> list[tuple[str, int]]:
        """Trouver les causes racines — noeuds sans parent dans le graphe.

        Si effect est donné : remonte depuis cet effect spécifique.
        Sinon : toutes les causes racines globales, triées par out-degree.
        """
        if effect is not None:
            return self._trace_roots(effect)

        # Global root causes: nodes with no incoming edges
        roots = []
        for node in self._nodes:
            if not self._radj.get(node):
                out_degree = len(self._adj.get(node, []))
                roots.append((node, out_degree))
        roots.sort(key=lambda x: x[1], reverse=True)
        return roots

    def find_causal_chains(self, min_length: int = 3) -> list[Chain]:
        """Chaînes cause -> effet -> effet de longueur >= min_length.

        DFS depuis chaque cause racine, collecte les chemins sans cycle.
        """
        roots = [n for n, _ in self.find_root_causes()]
        if not roots:
            # No roots = possible cycles; start from all nodes
            roots = sorted(self._nodes)

        all_chains: list[Chain] = []

        for root in roots:
            self._dfs_chains(root, [root], [], set(), min_length, all_chains)

        # Sort by length desc, then confidence desc
        all_chains.sort(key=lambda c: (c.length, c.product_confidence), reverse=True)
        return all_chains

    def get_strongest_paths(self, top_n: int = 10) -> list[Chain]:
        """Chemins avec le produit de confiance le plus élevé.

        = les chaînes causales les plus fiables du système.
        """
        chains = self.find_causal_chains(min_length=2)
        chains.sort(key=lambda c: c.product_confidence, reverse=True)
        return chains[:top_n]

    def summary(self) -> CausalTreeSummary:
        """Résumé du graphe causal global."""
        communities = self.detect_communities()
        roots = self.find_root_causes()
        chains = self.find_causal_chains(min_length=3)
        strongest = self.get_strongest_paths(top_n=5)

        # Terminal effects: nodes with no outgoing edges
        terminals = []
        for node in self._nodes:
            if not self._adj.get(node):
                in_degree = len(self._radj.get(node, []))
                terminals.append((node, in_degree))
        terminals.sort(key=lambda x: x[1], reverse=True)

        return CausalTreeSummary(
            total_nodes=len(self._nodes),
            total_edges=len(self._edges),
            connected_components=len(communities),
            top_root_causes=roots[:5],
            top_terminal_effects=terminals[:5],
            longest_chains=chains[:5],
            strongest_paths=strongest,
        )

    # ── Private ──────────────────────────────────────

    def _fetch_claims(self, min_confidence: float) -> list[dict]:
        """Fetch all claims with confidence >= threshold from DB."""
        with self.db._cursor() as cur:
            cur.execute(
                "SELECT cause, effect, confidence FROM causal_claims "
                "WHERE confidence >= %s ORDER BY confidence DESC",
                (min_confidence,),
            )
            cols = [desc[0] for desc in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    def _normalize(self, text: str) -> str:
        """Normalize node names — trim, collapse whitespace."""
        return " ".join(text.strip().split())

    def _trace_roots(self, effect: str) -> list[tuple[str, int]]:
        """BFS en arrière depuis un effect pour trouver ses causes racines."""
        effect = self._normalize(effect)
        if effect not in self._nodes:
            return []

        visited: set[str] = set()
        roots: list[tuple[str, int]] = []
        queue = deque([effect])

        while queue:
            node = queue.popleft()
            if node in visited:
                continue
            visited.add(node)

            parents = self._radj.get(node, [])
            if not parents and node != effect:
                out_degree = len(self._adj.get(node, []))
                roots.append((node, out_degree))
            else:
                for parent, _ in parents:
                    if parent not in visited:
                        queue.append(parent)

        roots.sort(key=lambda x: x[1], reverse=True)
        return roots

    def _dfs_chains(
        self,
        node: str,
        path: list[str],
        confidences: list[float],
        visited: set[str],
        min_length: int,
        results: list[Chain],
    ) -> None:
        """DFS pour collecter les chaînes causales."""
        visited.add(node)
        children = self._adj.get(node, [])

        if not children:
            # Leaf — record chain if long enough
            if len(path) >= min_length:
                results.append(Chain(
                    path=list(path),
                    confidences=list(confidences),
                ))
        else:
            for child, conf in children:
                if child not in visited:
                    path.append(child)
                    confidences.append(conf)
                    self._dfs_chains(child, path, confidences, visited, min_length, results)
                    path.pop()
                    confidences.pop()
                elif len(path) >= min_length:
                    # Can't continue (cycle), but path is long enough
                    results.append(Chain(
                        path=list(path),
                        confidences=list(confidences),
                    ))

        visited.discard(node)
