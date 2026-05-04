"""Fetch Sefaria API v3 ressources needed for Sprint 10 + future sprints.

Caches JSON responses locally under sifrei_yesod/external/sefaria_cache/.
No rate-limiting concerns at setup time (one-off) and the cache is reused
by T4 tests (offline) and folio_map construction.

Usage:
    python scripts/fetch_sefaria_cache.py [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CACHE = REPO / "sifrei_yesod" / "external" / "sefaria_cache"


SPRINT_10_RESOURCES: list[tuple[str, str]] = [
    # (endpoint path, cache filename)
    # --- Zohar Idra Rabba, toutes sections utiles ---
    *[(f"Zohar,_Idra_Rabba.{i}", f"zohar_idra_rabba_{i:02d}.json") for i in range(1, 31)],
    # --- Sefer Etz Chaim Shaar 13 (Sha'ar Arikh Anpin) ---
    *[(f"Sefer_Etz_Chaim.13.{i}", f"sefer_etz_chaim_13_{i:02d}.json") for i in range(1, 15)],
    # --- Sulam on Zohar Idra Rabba (commentaire Ashlag) ---
    *[(f"Sulam_on_Zohar,_Idra_Rabba.{i}", f"sulam_idra_rabba_{i:03d}.json") for i in range(1, 31)],
    # --- Sha'ar Ma'amarei Rashbi Commentary on Holy Idra Rabba (Vital) ---
    (
        "Sha'ar_Ma'amarei_Rashbi,_Commentary_on_the_Holy_Idra_Rabba",
        "shaar_maamarei_rashbi_commentary_idra_rabba.json",
    ),
]


API_BASE = "https://www.sefaria.org/api/v3/texts"


def fetch_one(endpoint: str, output: Path) -> dict:
    url = f"{API_BASE}/{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "etz-chaim-ai-sprint10/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-fetch even if cached")
    parser.add_argument("--throttle", type=float, default=0.5, help="Seconds between requests")
    args = parser.parse_args(argv[1:])

    CACHE.mkdir(parents=True, exist_ok=True)

    total = len(SPRINT_10_RESOURCES)
    fetched = 0
    skipped = 0
    errors = 0

    for i, (endpoint, filename) in enumerate(SPRINT_10_RESOURCES, start=1):
        target = CACHE / filename
        if target.exists() and not args.force:
            skipped += 1
            continue
        try:
            print(f"[{i}/{total}] {endpoint}")
            fetch_one(endpoint, target)
            fetched += 1
            time.sleep(args.throttle)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            errors += 1

    print(f"\nFetched: {fetched} / Cached (skipped): {skipped} / Errors: {errors}")
    return 0 if errors == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
