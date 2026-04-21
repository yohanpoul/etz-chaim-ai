"""Génération d'embeddings via Ollama — Assiah-level computation.

Passe par olamot.py pour tout accès Ollama.
"""

from __future__ import annotations


def embed(text: str, model: str | None = None) -> list[float]:
    """Generate an embedding vector using Ollama local server.

    Args:
        text: The text to embed.
        model: Ollama model name (default from config or nomic-embed-text).

    Returns:
        List of floats (embedding vector).
    """
    from olamot import ollama_embed
    return ollama_embed(text, model=model)


def embed_batch(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Generate embeddings for multiple texts in one call."""
    from olamot import ollama_embed_batch
    return ollama_embed_batch(texts, model=model)
