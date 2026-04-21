"""Shlichut composée — décomposition en DAG de sous-missions.

שְׁלִיחוּת — La mission (shlichut) complexe est décomposée en sous-missions
mono-agent. Chaque noeud est un Malakh éphémère, les arêtes encodent
les dépendances (la sortie de l'un alimente l'entrée du suivant).

Pattern des 231 Portes (Sefer Yetzirah 2:4) : chaque paire de
programmes a une connexion potentielle typée.

Usage:
    dag = ShlichutDAG()
    n1 = dag.add("rechercher les sources", order="malakhim")
    n2 = dag.add("analyser les sources", order="serafim", depends_on=[n1])
    n3 = dag.add("rédiger la synthèse", order="malakhim", depends_on=[n2])
    results = dag.execute(memuneh)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from malakhim.malakh import Malakh
from malakhim.models import MalakhResult

logger = logging.getLogger(__name__)


@dataclass
class ShlichutNode:
    """Un noeud du DAG — une sous-mission mono-agent."""
    node_id: str
    mission: str
    order: str = "malakhim"
    kavvanah: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    result: MalakhResult | None = None
    executed: bool = False


class ShlichutDAG:
    """DAG de sous-missions — décomposition d'une mission complexe.

    Exécution séquentielle respectant les dépendances.
    Chaque noeud est exécuté par un Malakh éphémère distinct.
    Les résultats des noeuds parents sont injectés dans le contexte des enfants.
    """

    def __init__(self):
        self._nodes: dict[str, ShlichutNode] = {}
        self._order: list[str] = []
        self._counter = 0

    def add(
        self,
        mission: str,
        order: str = "malakhim",
        kavvanah: dict | None = None,
        depends_on: list[str] | None = None,
    ) -> str:
        """Ajouter un noeud au DAG. Retourne le node_id."""
        self._counter += 1
        node_id = f"node_{self._counter}"

        # Vérifier les dépendances
        for dep in (depends_on or []):
            if dep not in self._nodes:
                raise ValueError(f"Dependency {dep} not found in DAG")

        node = ShlichutNode(
            node_id=node_id,
            mission=mission,
            order=order,
            kavvanah=kavvanah or {},
            depends_on=depends_on or [],
        )
        self._nodes[node_id] = node
        self._order.append(node_id)
        return node_id

    def get_execution_order(self) -> list[str]:
        """Retourne l'ordre d'exécution topologique."""
        # Simple : on utilise l'ordre d'insertion car add() vérifie que
        # les dépendances existent déjà (donc l'ordre est topologique)
        return list(self._order)

    def execute(
        self,
        execute_fn: Callable[[dict], str] | None = None,
        memuneh=None,
    ) -> dict[str, MalakhResult]:
        """Exécuter le DAG séquentiellement.

        Args:
            execute_fn: fonction d'exécution (pour tests). Si None et memuneh fourni,
                        utilise memuneh._make_olamot_fn
            memuneh: instance de Memuneh pour le routage LLM réel

        Returns:
            dict node_id → MalakhResult
        """
        results: dict[str, MalakhResult] = {}

        for node_id in self.get_execution_order():
            node = self._nodes[node_id]

            # Construire le contexte avec les résultats des parents
            parent_context = []
            for dep_id in node.depends_on:
                dep_result = results.get(dep_id)
                if dep_result and dep_result.response:
                    parent_context.append(
                        f"[Résultat de {dep_id}]: {dep_result.response}"
                    )

            # Enrichir le prompt avec le contexte parent
            enriched_prompt = node.mission
            if parent_context:
                enriched_prompt = (
                    "\n\n".join(parent_context)
                    + "\n\n---\n\nMission actuelle : "
                    + node.mission
                )

            # Déterminer la fonction d'exécution
            fn = execute_fn
            if fn is None and memuneh is not None:
                fn = memuneh._make_olamot_fn(node.order, node.kavvanah)

            # Exécuter le Malakh éphémère
            with Malakh(
                mission=node.mission,
                kavvanah=node.kavvanah,
                order=node.order,
                execute_fn=fn,
            ) as m:
                result = m.execute({"input": enriched_prompt})

            node.result = result
            node.executed = True
            results[node_id] = result

            logger.info(
                "ShlichutDAG: %s executed (success=%s, score=%.2f)",
                node_id, result.success, result.score,
            )

        return results

    def get_results(self) -> dict[str, MalakhResult]:
        """Récupérer tous les résultats."""
        return {nid: n.result for nid, n in self._nodes.items() if n.result}

    def get_final_result(self) -> MalakhResult | None:
        """Récupérer le résultat du dernier noeud (la sortie finale)."""
        if not self._order:
            return None
        last_id = self._order[-1]
        return self._nodes[last_id].result

    @property
    def size(self) -> int:
        return len(self._nodes)
