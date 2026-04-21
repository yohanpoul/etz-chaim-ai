#!/usr/bin/env python3
"""fetch_sefaria.py — Fetch texte hébreu depuis l'API Sefaria v3.

Usage:
    python -m sifrei_yesod.pipeline.fetch_sefaria "Sefer_Etz_Chaim.1.4.1"
    python -m sifrei_yesod.pipeline.fetch_sefaria "Sefer_Etz_Chaim.1.4"   # range = tous les sous-chapitres
    python -m sifrei_yesod.pipeline.fetch_sefaria "Sefer_Etz_Chaim.1.4" --output /path/to/dir

Le texte hébreu est sauvegardé dans /tmp/sefaria_raw/ par défaut.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

API_BASE = "https://www.sefaria.org/api/v3/texts"
DEFAULT_OUTPUT = Path("/tmp/sefaria_raw")


def strip_html(text: str) -> str:
    """Remove HTML tags from Sefaria text."""
    return re.sub(r"<[^>]+>", "", text)


def flatten_text(text) -> list[str]:
    """Flatten nested text structure into a list of strings.

    Sefaria returns:
      - a single string for a specific verse
      - a flat list of strings for a section
      - nested lists for broader ranges
    """
    if isinstance(text, str):
        return [text]
    if isinstance(text, list):
        result = []
        for item in text:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, list):
                result.extend(flatten_text(item))
            # skip None entries
        return result
    return []


def fetch_text(ref: str) -> dict:
    """Fetch a Sefaria reference via API v3.

    Returns dict with keys: ref, heRef, text_parts (list of str), raw_json.
    """
    url = f"{API_BASE}/{ref}"
    req = Request(url, headers={"User-Agent": "EtzChaimAI/1.0"})

    try:
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            print(f"  Ref introuvable sur Sefaria : {ref}", file=sys.stderr)
            sys.exit(1)
        raise
    except URLError as e:
        print(f"  Erreur réseau : {e}", file=sys.stderr)
        sys.exit(1)

    # Extract Hebrew text from versions
    text_raw = None
    for version in data.get("versions", []):
        if version.get("language") == "he" and version.get("text"):
            text_raw = version["text"]
            break

    if text_raw is None:
        print(f"  Aucun texte hébreu trouvé pour : {ref}", file=sys.stderr)
        sys.exit(1)

    parts = flatten_text(text_raw)
    parts = [strip_html(p) for p in parts if p and p.strip()]

    return {
        "ref": data.get("ref", ref),
        "heRef": data.get("heRef", ""),
        "heTitle": data.get("heTitle", ""),
        "next": data.get("next"),
        "prev": data.get("prev"),
        "text_parts": parts,
        "raw_json": data,
    }


def ref_to_filename(ref: str) -> str:
    """Convert a Sefaria ref to a safe filename."""
    return ref.replace(" ", "_").replace(":", "-").replace("/", "_") + ".json"


def save_result(result: dict, output_dir: Path) -> Path:
    """Save fetched result as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = ref_to_filename(result["ref"])
    filepath = output_dir / filename

    save_data = {
        "ref": result["ref"],
        "heRef": result["heRef"],
        "heTitle": result["heTitle"],
        "next": result["next"],
        "prev": result["prev"],
        "text_hebrew": result["text_parts"],
        "num_parts": len(result["text_parts"]),
        "total_chars": sum(len(p) for p in result["text_parts"]),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    return filepath


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sifrei_yesod.pipeline.fetch_sefaria",
        description="Fetch texte hébreu depuis Sefaria API v3",
    )
    parser.add_argument("ref", help='Référence Sefaria (ex: "Sefer_Etz_Chaim.1.4.1")')
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Dossier de sortie (défaut: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--raw", action="store_true", help="Afficher le JSON brut complet")
    args = parser.parse_args()

    print(f"  Fetching: {args.ref}")
    result = fetch_text(args.ref)

    # Save
    filepath = save_result(result, args.output)

    # Summary
    parts = result["text_parts"]
    total_chars = sum(len(p) for p in parts)
    print(f"  Ref:      {result['ref']}")
    print(f"  HeRef:    {result['heRef']}")
    print(f"  Parties:  {len(parts)}")
    print(f"  Chars:    {total_chars}")
    print(f"  Saved:    {filepath}")

    # Preview
    if parts:
        preview = parts[0][:120]
        print(f"  Preview:  {preview}{'...' if len(parts[0]) > 120 else ''}")

    if args.raw:
        print("\n--- RAW JSON ---")
        print(json.dumps(result["raw_json"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
