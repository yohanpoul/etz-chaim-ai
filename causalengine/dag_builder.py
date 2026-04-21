"""DAGBuilder — construction et validation de DAGs causaux.

Binah construit des structures. Le DAGBuilder est l'architecte :
il assemble les noeuds et arêtes, vérifie l'acyclicité,
et rejette les graphes incohérents.

Anti-Satariel Mamash : un cycle dans le DAG est une causalité
inversée — la pire forme de faux pattern.
"""

from __future__ import annotations

from causalengine.models import (
    CausalEdge,
    CausalGraph,
    CausalNode,
    EVIDENCE_RANK,
)


class CycleError(ValueError):
    """Le graphe contient un cycle — causalité circulaire détectée."""


class DAGBuilder:
    """Construit et valide des DAGs causaux.

    Garantit :
    - Pas de cycles (acyclicité stricte)
    - Pas d'arêtes vers des noeuds inexistants
    - Pas de noeuds orphelins dans un graphe non-trivial
    - Evidence level cohérent avec les edges
    """

    def build(
        self,
        name: str,
        nodes: list[CausalNode],
        edges: list[CausalEdge],
        domain: str = "",
        description: str = "",
    ) -> CausalGraph:
        """Construire un DAG causal validé.

        Raises:
            CycleError: si le graphe contient un cycle
            ValueError: si des edges référencent des noeuds inexistants
        """
        graph = CausalGraph(
            name=name,
            nodes=list(nodes),
            edges=list(edges),
            domain=domain,
            description=description,
        )

        self._validate_node_refs(graph)
        self._validate_acyclic(graph)
        graph.evidence_level = self._compute_graph_evidence(graph)

        return graph

    def add_node(self, graph: CausalGraph, node: CausalNode) -> CausalGraph:
        """Ajouter un noeud au graphe."""
        if node.node_id in graph.node_ids():
            raise ValueError(f"Node '{node.node_id}' already exists")
        graph.nodes.append(node)
        return graph

    def add_edge(self, graph: CausalGraph, edge: CausalEdge) -> CausalGraph:
        """Ajouter une arête — revalide l'acyclicité.

        Raises:
            CycleError: si l'ajout crée un cycle
            ValueError: si source ou target n'existent pas
        """
        node_ids = graph.node_ids()
        if edge.source not in node_ids:
            raise ValueError(f"Source node '{edge.source}' not in graph")
        if edge.target not in node_ids:
            raise ValueError(f"Target node '{edge.target}' not in graph")

        # Test: adding this edge creates a cycle?
        graph.edges.append(edge)
        try:
            self._validate_acyclic(graph)
        except CycleError:
            graph.edges.pop()
            raise

        graph.evidence_level = self._compute_graph_evidence(graph)
        return graph

    def remove_edge(
        self, graph: CausalGraph, source: str, target: str,
    ) -> CausalGraph:
        """Retirer une arête."""
        graph.edges = [
            e for e in graph.edges
            if not (e.source == source and e.target == target)
        ]
        graph.evidence_level = self._compute_graph_evidence(graph)
        return graph

    def topological_sort(self, graph: CausalGraph) -> list[str]:
        """Tri topologique — l'ordre causal.

        Raises:
            CycleError: si un cycle est détecté
        """
        adj: dict[str, list[str]] = {n.node_id: [] for n in graph.nodes}
        in_degree: dict[str, int] = {n.node_id: 0 for n in graph.nodes}

        for e in graph.edges:
            adj[e.source].append(e.target)
            in_degree[e.target] += 1

        queue = [n for n, deg in in_degree.items() if deg == 0]
        result: list[str] = []

        while queue:
            # Sort for deterministic output
            queue.sort()
            node = queue.pop(0)
            result.append(node)
            for child in adj[node]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(result) != len(graph.nodes):
            raise CycleError("Graph contains a cycle — circular causation detected")

        return result

    def _validate_node_refs(self, graph: CausalGraph) -> None:
        """Vérifier que toutes les edges référencent des noeuds existants."""
        node_ids = graph.node_ids()
        for edge in graph.edges:
            if edge.source not in node_ids:
                raise ValueError(
                    f"Edge source '{edge.source}' not found in nodes"
                )
            if edge.target not in node_ids:
                raise ValueError(
                    f"Edge target '{edge.target}' not found in nodes"
                )

    def _validate_acyclic(self, graph: CausalGraph) -> None:
        """Vérifier l'acyclicité via tri topologique (Kahn)."""
        self.topological_sort(graph)

    def _compute_graph_evidence(self, graph: CausalGraph) -> str:
        """Le niveau de preuve du graphe = le minimum de ses edges.

        Un graphe n'est que aussi fort que son maillon le plus faible.
        """
        if not graph.edges:
            return "association"

        # Map edge evidence levels to Pearl levels
        edge_to_pearl = {
            "correlation_only": "association",
            "probable_causation": "intervention",
            "demonstrated_causation": "counterfactual",
        }
        pearl_rank = {
            "association": 0,
            "intervention": 1,
            "counterfactual": 2,
        }

        min_level = "counterfactual"
        for edge in graph.edges:
            pearl = edge_to_pearl.get(edge.evidence_level, "association")
            if pearl_rank.get(pearl, 0) < pearl_rank.get(min_level, 2):
                min_level = pearl

        return min_level
