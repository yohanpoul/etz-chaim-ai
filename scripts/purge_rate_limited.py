"""Purge rate-limited responses from a bench run + reset checkpoint state.

Usage: python scripts/purge_rate_limited.py <run_dir>

Détecte les responses dont le texte contient "hit your limit" ou
"resets ... (Europe/Paris)" et :
1. Les retire de responses.jsonl
2. Retire les prompt_ids correspondants du done set dans bench_state.json
3. Recompute total_cost / total_calls / tokens
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RATE_LIMIT_MARKERS = ["hit your limit", "resets" + " "]  # joined to avoid match here


def is_rate_limited(text: str) -> bool:
    if not text:
        return False
    head = text[:300].lower()
    return "hit your limit" in head or "you've hit your limit" in head


def purge_run(run_dir: Path) -> int:
    responses_file = run_dir / "responses.jsonl"
    state_file = run_dir / "bench_state.json"
    if not responses_file.exists():
        print(f"No responses.jsonl in {run_dir}", file=sys.stderr)
        return 1

    rows = []
    with responses_file.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))

    n_total = len(rows)
    rate_limited_keys: set[tuple[str, str, int]] = set()
    kept_rows = []
    purged_rows = []
    for r in rows:
        if is_rate_limited(r.get("response") or ""):
            rate_limited_keys.add((r["arm"], r["bench"], r["prompt_id"]))
            purged_rows.append(r)
        else:
            kept_rows.append(r)

    print(f"Total responses: {n_total}", file=sys.stderr)
    print(f"Rate-limited (will be purged): {len(purged_rows)}", file=sys.stderr)

    by_key = {}
    for r in purged_rows:
        k = (r["arm"], r["bench"])
        by_key[k] = by_key.get(k, 0) + 1
    for k in sorted(by_key):
        print(f"  {k}: {by_key[k]}", file=sys.stderr)

    if not purged_rows:
        print("Nothing to purge.", file=sys.stderr)
        return 0

    # Recompute totals from kept rows
    total_cost = 0.0
    total_calls = 0
    total_input = 0
    total_output = 0
    done: dict[str, dict[str, set[int]]] = {}
    for r in kept_rows:
        arm = r["arm"]
        bench = r["bench"]
        pid = r["prompt_id"]
        done.setdefault(arm, {}).setdefault(bench, set()).add(pid)
        total_cost += float(r.get("cost_usd", 0.0))
        total_calls += 1
        total_input += int(r.get("tokens_input", 0))
        total_output += int(r.get("tokens_output", 0))

    # Rewrite responses.jsonl atomically (tmp + rename)
    tmp_responses = responses_file.with_suffix(".jsonl.tmp")
    with tmp_responses.open("w") as f:
        for r in kept_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp_responses.replace(responses_file)

    # Update bench_state.json
    state = json.loads(state_file.read_text())
    state["done"] = {
        arm: {bench: sorted(ids) for bench, ids in by_bench.items()}
        for arm, by_bench in done.items()
    }
    state["total_cost_usd"] = round(total_cost, 6)
    state["total_calls"] = total_calls
    state["total_tokens_input"] = total_input
    state["total_tokens_output"] = total_output
    import time as _time

    state["last_updated_at"] = _time.time()

    tmp_state = state_file.with_suffix(".json.tmp")
    tmp_state.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    tmp_state.replace(state_file)

    print(f"\nPurged {len(purged_rows)} rate-limited responses.", file=sys.stderr)
    print(f"Kept: {len(kept_rows)} valid responses.", file=sys.stderr)
    print(f"New total cost: ${total_cost:.2f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: purge_rate_limited.py <run_dir>", file=sys.stderr)
        sys.exit(1)
    sys.exit(purge_run(Path(sys.argv[1])))
