"""portes/analysis.py — Auto-analyse des connexions entre sentiers implémentés.

Dérive automatiquement les propriétés de chaque porte en analysant
les sephiroth connectées, les types de données, et les flux possibles.
"""

from __future__ import annotations


# ── Signatures des sentiers implémentés ─────────────────────
# Dérivées par analyse statique du code (shemot/sentiers/*.py)

SENTIER_OUTPUTS: dict[str, list[str]] = {
    "tav":    ["entries", "count", "avg_confidence", "warnings"],
    "shin":   ["domain", "competence_score", "routed_to", "declined", "decline_reason"],
    "resh":   ["domain", "score", "n_evals", "persisted", "policy"],
    "qoph":   ["domain", "score", "n_evals", "recalled", "n_recalled"],
    "tsadi":  ["action", "intention_id", "goal", "status", "reason"],
    "ayin":   ["intention_id", "goal", "status", "domain", "competence", "sync", "verdict"],
    "peh":    ["domain_id", "hypothesis", "score", "threshold", "verdict", "policy", "analysis_id"],
    "samekh": ["domain", "n_conclusions", "n_tensions", "consistency_score", "tensions"],
    "nun":    ["domain", "mode", "content", "n_sources", "intention_id", "dispatched", "dissensus_reason"],
    "lamed":  ["analysis_id", "qliphah", "severity", "root_cause", "nitzotzot", "n_nitzotzot"],
}

SENTIER_INPUTS: dict[str, list[str]] = {
    "tav":    ["query", "limit"],
    "shin":   ["query"],
    "resh":   ["domain", "min_confidence"],
    "qoph":   ["domain", "query"],
    "tsadi":  ["action", "goal", "intention_id", "reason", "max_duration_days", "strategy"],
    "ayin":   ["intention_id", "query"],
    "peh":    ["domain_id", "hypothesis", "score", "threshold", "explanation", "original", "modified"],
    "samekh": ["domain", "conclusion_ids"],
    "nun":    ["domain", "conclusion_ids", "auto_intent"],
    "lamed":  ["description", "source_type", "source_id", "context", "domain", "extract"],
}


def analyze_pair(reg_a: dict, reg_b: dict, name_a: str, name_b: str) -> dict:
    """Analyser la communication possible entre deux sentiers.

    Retourne un dict avec les champs :
        can_communicate, protocol, shared_sephiroth,
        direction, data_format, description
    """
    seph_a = {reg_a["source"], reg_a["target"]}
    seph_b = {reg_b["source"], reg_b["target"]}
    shared = sorted(seph_a & seph_b)

    if not shared:
        return {
            "can_communicate": False,
            "protocol": None,
            "shared_sephiroth": [],
            "direction": "",
            "data_format": {},
            "description": "Pas de sephirah commune — porte silencieuse",
        }

    # ── Direction du flux ────────────────────────────────────
    a_feeds_b = reg_a["target"] in seph_b and reg_a["target"] == reg_b["source"]
    b_feeds_a = reg_b["target"] in seph_a and reg_b["target"] == reg_a["source"]
    both_target = reg_a["target"] == reg_b["target"] and reg_a["target"] in shared
    both_source = reg_a["source"] == reg_b["source"] and reg_a["source"] in shared

    # Pour les doubles, vérifier aussi la direction inverse
    if reg_a.get("type") == "double":
        a_feeds_b = a_feeds_b or (reg_a["source"] == reg_b["source"] and reg_a["source"] in shared)
    if reg_b.get("type") == "double":
        b_feeds_a = b_feeds_a or (reg_b["source"] == reg_a["source"] and reg_b["source"] in shared)

    if a_feeds_b and b_feeds_a:
        direction = "a\u2194b"  # ↔
    elif a_feeds_b:
        direction = "a\u2192b"  # →
    elif b_feeds_a:
        direction = "b\u2192a"  # →
    elif both_target:
        direction = "convergent"
    elif both_source:
        direction = "divergent"
    else:
        # Adjacents par une sephirah intermédiaire
        direction = "adjacent"

    # ── Protocole ────────────────────────────────────────────
    type_a = reg_a.get("type", "simple")
    type_b = reg_b.get("type", "simple")
    if "mother" in (type_a, type_b):
        protocol = "stream"
    elif "a\u2194b" in direction:
        protocol = "sync"
    else:
        protocol = "sync"

    # ── Compatibilité des données ────────────────────────────
    outputs_a = set(SENTIER_OUTPUTS.get(name_a, []))
    outputs_b = set(SENTIER_OUTPUTS.get(name_b, []))
    inputs_a = set(SENTIER_INPUTS.get(name_a, []))
    inputs_b = set(SENTIER_INPUTS.get(name_b, []))

    data_format: dict[str, list[str]] = {}
    a_to_b_keys = sorted(outputs_a & inputs_b)
    b_to_a_keys = sorted(outputs_b & inputs_a)
    if a_to_b_keys:
        data_format["a\u2192b"] = a_to_b_keys
    if b_to_a_keys:
        data_format["b\u2192a"] = b_to_a_keys

    # ── Description ──────────────────────────────────────────
    via = ", ".join(shared)
    if direction == "a\u2192b":
        detail = f"{name_a} alimente {name_b}"
    elif direction == "b\u2192a":
        detail = f"{name_b} alimente {name_a}"
    elif direction == "a\u2194b":
        detail = "\u00e9change bidirectionnel"
    elif direction == "convergent":
        detail = f"convergent vers {via}"
    elif direction == "divergent":
        detail = f"divergent depuis {via}"
    else:
        detail = f"adjacents via {via}"
    description = f"Via {via} \u2014 {detail}"

    return {
        "can_communicate": True,
        "protocol": protocol,
        "shared_sephiroth": shared,
        "direction": direction,
        "data_format": data_format,
        "description": description,
    }
