"""Tests DAGBuilder — l'architecte de Binah.

Anti-Satariel Mamash : un cycle dans le DAG est une causalité
inversée — la pire forme de faux pattern.
"""

import pytest

from causalengine.dag_builder import CycleError, DAGBuilder
from causalengine.models import CausalEdge, CausalGraph, CausalNode


@pytest.fixture
def builder():
    return DAGBuilder()


@pytest.fixture
def simple_nodes():
    return [
        CausalNode(node_id="A", name="Fasting"),
        CausalNode(node_id="B", name="HRV"),
        CausalNode(node_id="C", name="Exercise"),
    ]


@pytest.fixture
def simple_edges():
    return [
        CausalEdge(source="A", target="B", evidence_level="correlation_only"),
        CausalEdge(source="C", target="B", evidence_level="probable_causation"),
    ]


# ── Build ──────────────────────────────────────────────

class TestBuild:
    def test_build_simple_dag(self, builder, simple_nodes, simple_edges):
        graph = builder.build("test", simple_nodes, simple_edges)
        assert graph.name == "test"
        assert len(graph.nodes) == 3
        assert len(graph.edges) == 2

    def test_build_single_node(self, builder):
        nodes = [CausalNode(node_id="X", name="Alone")]
        graph = builder.build("solo", nodes, [])
        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0

    def test_build_with_domain(self, builder, simple_nodes, simple_edges):
        graph = builder.build(
            "test", simple_nodes, simple_edges,
            domain="health", description="HRV study",
        )
        assert graph.domain == "health"
        assert graph.description == "HRV study"

    def test_build_evidence_level_is_minimum(self, builder, simple_nodes, simple_edges):
        """Le graphe est aussi fort que son maillon le plus faible."""
        graph = builder.build("test", simple_nodes, simple_edges)
        # correlation_only < probable_causation → association
        assert graph.evidence_level == "association"

    def test_build_all_high_evidence(self, builder, simple_nodes):
        edges = [
            CausalEdge(source="A", target="B", evidence_level="demonstrated_causation"),
            CausalEdge(source="C", target="B", evidence_level="demonstrated_causation"),
        ]
        graph = builder.build("test", simple_nodes, edges)
        assert graph.evidence_level == "counterfactual"

    def test_build_empty_edges_gives_association(self, builder, simple_nodes):
        graph = builder.build("test", simple_nodes, [])
        assert graph.evidence_level == "association"


# ── Acyclicité ─────────────────────────────────────────

class TestAcyclicity:
    def test_cycle_detection_simple(self, builder):
        nodes = [
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
        ]
        edges = [
            CausalEdge(source="A", target="B"),
            CausalEdge(source="B", target="A"),
        ]
        with pytest.raises(CycleError):
            builder.build("cycle", nodes, edges)

    def test_cycle_detection_triangle(self, builder):
        nodes = [
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
            CausalNode(node_id="C", name="C"),
        ]
        edges = [
            CausalEdge(source="A", target="B"),
            CausalEdge(source="B", target="C"),
            CausalEdge(source="C", target="A"),
        ]
        with pytest.raises(CycleError):
            builder.build("triangle_cycle", nodes, edges)

    def test_self_loop_detection(self, builder):
        nodes = [CausalNode(node_id="A", name="A")]
        edges = [CausalEdge(source="A", target="A")]
        with pytest.raises(CycleError):
            builder.build("self_loop", nodes, edges)

    def test_no_cycle_in_diamond(self, builder):
        """A→B, A→C, B→D, C→D est un DAG valide (diamant)."""
        nodes = [
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
            CausalNode(node_id="C", name="C"),
            CausalNode(node_id="D", name="D"),
        ]
        edges = [
            CausalEdge(source="A", target="B"),
            CausalEdge(source="A", target="C"),
            CausalEdge(source="B", target="D"),
            CausalEdge(source="C", target="D"),
        ]
        graph = builder.build("diamond", nodes, edges)
        assert len(graph.edges) == 4


# ── Validation ─────────────────────────────────────────

class TestValidation:
    def test_invalid_edge_source(self, builder, simple_nodes):
        edges = [CausalEdge(source="NONEXISTENT", target="B")]
        with pytest.raises(ValueError, match="source"):
            builder.build("bad_source", simple_nodes, edges)

    def test_invalid_edge_target(self, builder, simple_nodes):
        edges = [CausalEdge(source="A", target="NONEXISTENT")]
        with pytest.raises(ValueError, match="target"):
            builder.build("bad_target", simple_nodes, edges)


# ── Add/Remove ─────────────────────────────────────────

class TestMutation:
    def test_add_node(self, builder, simple_nodes, simple_edges):
        graph = builder.build("test", simple_nodes, simple_edges)
        new_node = CausalNode(node_id="D", name="Sleep")
        builder.add_node(graph, new_node)
        assert "D" in graph.node_ids()

    def test_add_duplicate_node_raises(self, builder, simple_nodes, simple_edges):
        graph = builder.build("test", simple_nodes, simple_edges)
        dup = CausalNode(node_id="A", name="Duplicate")
        with pytest.raises(ValueError, match="already exists"):
            builder.add_node(graph, dup)

    def test_add_edge(self, builder, simple_nodes, simple_edges):
        graph = builder.build("test", simple_nodes, simple_edges)
        new_edge = CausalEdge(source="A", target="C")
        builder.add_edge(graph, new_edge)
        assert len(graph.edges) == 3

    def test_add_edge_creating_cycle_raises(self, builder):
        nodes = [
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
        ]
        edges = [CausalEdge(source="A", target="B")]
        graph = builder.build("test", nodes, edges)
        with pytest.raises(CycleError):
            builder.add_edge(graph, CausalEdge(source="B", target="A"))
        # L'edge n'a PAS été ajouté
        assert len(graph.edges) == 1

    def test_add_edge_invalid_source(self, builder, simple_nodes, simple_edges):
        graph = builder.build("test", simple_nodes, simple_edges)
        with pytest.raises(ValueError, match="Source"):
            builder.add_edge(graph, CausalEdge(source="Z", target="A"))

    def test_remove_edge(self, builder, simple_nodes, simple_edges):
        graph = builder.build("test", simple_nodes, simple_edges)
        builder.remove_edge(graph, "A", "B")
        assert len(graph.edges) == 1


# ── Topological sort ───────────────────────────────────

class TestTopologicalSort:
    def test_topological_sort_linear(self, builder):
        nodes = [
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
            CausalNode(node_id="C", name="C"),
        ]
        edges = [
            CausalEdge(source="A", target="B"),
            CausalEdge(source="B", target="C"),
        ]
        graph = builder.build("linear", nodes, edges)
        order = builder.topological_sort(graph)
        assert order == ["A", "B", "C"]

    def test_topological_sort_diamond(self, builder):
        nodes = [
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
            CausalNode(node_id="C", name="C"),
            CausalNode(node_id="D", name="D"),
        ]
        edges = [
            CausalEdge(source="A", target="B"),
            CausalEdge(source="A", target="C"),
            CausalEdge(source="B", target="D"),
            CausalEdge(source="C", target="D"),
        ]
        graph = builder.build("diamond", nodes, edges)
        order = builder.topological_sort(graph)
        assert order[0] == "A"
        assert order[-1] == "D"
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_topological_sort_deterministic(self, builder):
        """Doit être déterministe (tri alphabétique des ex-aequo)."""
        nodes = [
            CausalNode(node_id="C", name="C"),
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
        ]
        graph = builder.build("parallel", nodes, [])
        order = builder.topological_sort(graph)
        assert order == ["A", "B", "C"]


# ── DB ─────────────────────────────────────────────────

class TestDAGDB:
    def test_save_and_retrieve_graph(self, db, builder):
        nodes = [
            CausalNode(node_id="A", name="Fasting"),
            CausalNode(node_id="B", name="HRV"),
        ]
        edges = [CausalEdge(source="A", target="B")]
        graph = builder.build("test_persist", nodes, edges, domain="health")
        saved = db.save_graph(graph)
        assert saved.id is not None

        retrieved = db.get_graph(saved.id)
        assert retrieved is not None
        assert retrieved.name == "test_persist"
        assert len(retrieved.nodes) == 2
        assert len(retrieved.edges) == 1

    def test_update_graph(self, db, builder):
        nodes = [
            CausalNode(node_id="A", name="A"),
            CausalNode(node_id="B", name="B"),
        ]
        edges = [CausalEdge(source="A", target="B")]
        graph = builder.build("update_me", nodes, edges)
        saved = db.save_graph(graph)

        saved.evidence_level = "intervention"
        updated = db.update_graph(saved)
        assert updated is not None
        assert updated.evidence_level == "intervention"
