"""Façade Malakhim — point d'entrée unique.

L'interface publique du système Malakhim pour le reste du projet.
main.py et web/app.py appellent cette façade au lieu de
olamot.ollama_generate() directement.

Le gradient de kavvanah détermine le mode :
  - Kavvanah pleine → connexion directe (pas de Malakh)
  - Kavvanah partielle → Malakh engendré via Heikhalot
  - Kavvanah minimale → exécution mécanique (Ishim)
"""

from __future__ import annotations

from typing import Any, Callable

from malakhim.memuneh.router import Memuneh
from malakhim.models import MalakhResult
from malakhim.pekidah.registry import PekidahRegistry

# ── Singleton registry (lazy init) ───────────────────────────────────────────

_registry: PekidahRegistry | None = None
_memuneh: Memuneh | None = None


def _get_memuneh(db_url: str | None = None) -> Memuneh:
    """Lazy init du Memuneh singleton."""
    global _registry, _memuneh
    if _memuneh is None:
        _registry = PekidahRegistry(db_url=db_url)
        _memuneh = Memuneh(registry=_registry)
    return _memuneh


def malakhim_generate(
    prompt: str,
    kavvanah: dict[str, Any] | None = None,
    budget_max: int = 0,
    agent_id: str | None = None,
    domain: str = "general",
    db_url: str | None = None,
) -> MalakhResult:
    """Point d'entrée principal du système Malakhim.

    Remplace les appels directs à olamot.ollama_generate() avec
    un routage kavvanah-aware :
      HIGH  → connexion directe (pas de Malakh)
      MEDIUM → Malakh engendré via Heikhalot
      LOW   → exécution mécanique (Ishim)

    Args:
        prompt: la requête utilisateur
        kavvanah: dict d'intention (optionnel)
        budget_max: plafond budgétaire (0 = pas de plafond)
        agent_id: identifiant de l'agent (pour Pekidah)
        domain: domaine de la tâche
        db_url: URL PostgreSQL pour la persistence (optionnel)

    Returns:
        MalakhResult avec réponse, score, warnings, et metadata
    """
    memuneh = _get_memuneh(db_url)

    # Injecter agent_id et domain dans kavvanah
    kav = dict(kavvanah or {})
    if agent_id:
        kav["agent_id"] = agent_id
    if domain != "general":
        kav["domain"] = domain

    return memuneh.dispatch(
        prompt=prompt,
        kavvanah=kav,
        budget_max=budget_max,
    )


def reset() -> None:
    """Reset les singletons (pour les tests)."""
    global _registry, _memuneh
    if _registry is not None:
        _registry.close()
    _registry = None
    _memuneh = None
