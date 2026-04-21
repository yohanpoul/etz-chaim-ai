"""kabbalah/embed_gates.py — Embed the 462 directional gates.

Each gate is a PASSAGE between two letters in the Cube of Space.
The embedding combines the gate's structural properties: direction,
axis traversal, register transitions, interaction class.

Usage:
    python -m kabbalah.embed_gates [--skip-ml] [--db-url URL]
"""

from __future__ import annotations

import argparse
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Olam descriptions for readability
_OLAM_DESC: dict[str, str] = {
    "feu": "fire", "eau": "water", "air": "air",
    "saturne": "Saturn", "jupiter": "Jupiter", "mars": "Mars",
    "soleil": "Sun", "vénus": "Venus", "mercure": "Mercury", "lune": "Moon",
    "bélier": "Aries", "taureau": "Taurus", "gémeaux": "Gemini",
    "cancer": "Cancer", "lion": "Leo", "vierge": "Virgo",
    "balance": "Libra", "scorpion": "Scorpio", "sagittaire": "Sagittarius",
    "capricorne": "Capricorn", "verseau": "Aquarius", "poissons": "Pisces",
}


def _gate_description(gate) -> str:
    """Build a textual description for ML embedding of a gate."""
    vertical = gate.vertical_character
    olam_from = _OLAM_DESC.get(gate.olam_transition[0], gate.olam_transition[0])
    olam_to = _OLAM_DESC.get(gate.olam_transition[1], gate.olam_transition[1])

    axes = ", ".join(gate.axes_traversed) if gate.axes_traversed else "none"

    parts = [
        f"Directional gate from {gate.letter_from} to {gate.letter_to}",
        f"in the Cube of Space.",
        f"Direction: {vertical},",
        f"distance {gate.distance:.3f}.",
        f"Traverses axes: {axes}.",
        f"Olam transition: {olam_from} to {olam_to}.",
        f"Interaction: {gate.interaction_class}.",
    ]
    return " ".join(parts)


def embed_gates(skip_ml: bool = False, db_url: str | None = None) -> dict:
    """Embed all 462 directional gates. Returns stats dict."""
    from kabbalah.gates_462 import Gates462
    from kabbalah.hybrid_embedding import HybridEmbedding

    gates = Gates462()
    he = HybridEmbedding(db_url=db_url)

    all_vectors = []
    stats = {"total": 0, "ascending": 0, "descending": 0, "horizontal": 0}

    for gate in gates.all_gates():
        concept = f"gate_{gate.letter_from}_{gate.letter_to}"
        hebrew = gate.hebrew_from + gate.hebrew_to
        description = _gate_description(gate)

        # Embed using the description for ML, hebrew pair for kabbalistic
        vec = he.embed(description, hebrew_word=hebrew, skip_ml=skip_ml)
        # Override concept name to gate_ format (description was used for ML)
        vec.concept = concept
        vec.hebrew_word = hebrew

        all_vectors.append(vec)
        stats["total"] += 1

        if gate.is_ascending:
            stats["ascending"] += 1
        elif gate.is_descending:
            stats["descending"] += 1
        else:
            stats["horizontal"] += 1

    logger.info(
        "Embedded %d gates (↑%d ↓%d ↔%d)",
        stats["total"], stats["ascending"],
        stats["descending"], stats["horizontal"],
    )

    # Save to DB
    try:
        saved = he.save_batch_to_db(all_vectors)
        logger.info("Saved %d/%d gate vectors to DB", saved, stats["total"])
        stats["saved"] = saved
    except Exception as e:
        logger.warning("Could not save gates to DB: %s", e)
        stats["saved"] = 0

    return stats


def main():
    parser = argparse.ArgumentParser(description="Embed 462 directional gates")
    parser.add_argument("--skip-ml", action="store_true",
                        help="Skip ML embeddings (kabbalistic only)")
    parser.add_argument("--db-url", default=None,
                        help="PostgreSQL URL (default: ETZ_CHAIM_DB env)")
    args = parser.parse_args()

    stats = embed_gates(skip_ml=args.skip_ml, db_url=args.db_url)
    print(f"\nEmbedded {stats['total']} gates:")
    for k, v in stats.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
