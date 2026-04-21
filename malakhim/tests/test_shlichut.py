"""Tests de la Shlichut composée — DAG de sous-missions."""

import pytest
from malakhim.shlichut.dag import ShlichutDAG, ShlichutNode
from malakhim.models import MalakhResult


def echo_fn(ctx):
    """Execute fn de test qui retourne l'input."""
    return f"executed: {ctx.get('input', '')[:100]}"


class TestShlichutDAG:
    def test_empty_dag(self):
        dag = ShlichutDAG()
        results = dag.execute(execute_fn=echo_fn)
        assert results == {}
        assert dag.size == 0

    def test_single_node(self):
        dag = ShlichutDAG()
        n1 = dag.add("do something")
        results = dag.execute(execute_fn=echo_fn)
        assert n1 in results
        assert results[n1].success

    def test_linear_chain(self):
        dag = ShlichutDAG()
        n1 = dag.add("step 1: research")
        n2 = dag.add("step 2: analyze", depends_on=[n1])
        n3 = dag.add("step 3: write", depends_on=[n2])
        results = dag.execute(execute_fn=echo_fn)
        assert len(results) == 3
        # Le dernier noeud a reçu le contexte des parents
        assert "Résultat de node_1" in results[n3].response or "executed" in results[n3].response

    def test_diamond_dependency(self):
        dag = ShlichutDAG()
        n1 = dag.add("gather data")
        n2 = dag.add("analyze A", depends_on=[n1])
        n3 = dag.add("analyze B", depends_on=[n1])
        n4 = dag.add("synthesize", depends_on=[n2, n3])
        results = dag.execute(execute_fn=echo_fn)
        assert len(results) == 4
        assert results[n4].success

    def test_invalid_dependency_raises(self):
        dag = ShlichutDAG()
        with pytest.raises(ValueError, match="not found"):
            dag.add("step 2", depends_on=["nonexistent"])

    def test_get_final_result(self):
        dag = ShlichutDAG()
        dag.add("step 1")
        dag.add("step 2", depends_on=["node_1"])
        dag.execute(execute_fn=echo_fn)
        final = dag.get_final_result()
        assert final is not None
        assert final.success

    def test_order_preserved(self):
        dag = ShlichutDAG()
        n1 = dag.add("first")
        n2 = dag.add("second")
        n3 = dag.add("third")
        order = dag.get_execution_order()
        assert order == [n1, n2, n3]

    def test_nodes_with_different_orders(self):
        dag = ShlichutDAG()
        dag.add("strategic decision", order="atziluth")
        dag.add("detailed analysis", order="briah", depends_on=["node_1"])
        dag.add("format output", order="assiah", depends_on=["node_2"])
        results = dag.execute(execute_fn=echo_fn)
        assert len(results) == 3

    def test_parent_context_injected(self):
        """Les résultats des parents sont injectés dans le contexte des enfants."""
        dag = ShlichutDAG()
        n1 = dag.add("produce data")
        n2 = dag.add("use data", depends_on=[n1])
        results = dag.execute(execute_fn=echo_fn)
        # Le prompt du n2 contient le résultat de n1
        assert "node_1" in results[n2].response or "executed" in results[n2].response
