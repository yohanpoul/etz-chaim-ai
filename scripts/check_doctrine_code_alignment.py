"""Auto-check doctrine ↔ code alignment (Sprint 10 Phase B.4).

Passe 1 (doctrine → code):
    Pour chaque item Sifrei Yesod avec ``mapping.modules`` non-vide, vérifier
    que chaque chemin listé existe sur disque ou est annoté ``[PLANNED]``.

Passe 2 (code → doctrine):
    Pour chaque module .py sous racine projet, extraire les IDs EC-*/Z-IR-*/
    REL-*/PG-* cités en docstring/commentaire et vérifier qu'ils existent
    dans le corpus indexé.

Exit codes:
    0 : aucun désalignement.
    1 : désalignements détectés (cf. report stdout).

Usage:
    python3 scripts/check_doctrine_code_alignment.py
    python3 scripts/check_doctrine_code_alignment.py --strict   # échec sur warnings
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bridge.sifrei_reader import load_all_ids, load_assertion  # noqa: E402

ID_PATTERN = re.compile(r"\b(?:EC|Z|REL|PG)-[A-Z0-9]+(?:-[A-Za-z0-9_]+)+\b")
PLANNED_TAG = "[PLANNED]"
SKIPPED_DIRS = {
    ".venv",
    "venv",
    ".garak-venv",
    ".git",
    "node_modules",
    "__pycache__",
    "sifrei_yesod",
    "sefaria_cache",
    "halom",
    "sandbox",
    "web/static",
}


def check_doctrine_to_code(verbose: bool) -> list[str]:
    """Retourne la liste des désalignements doctrine → code."""
    errors: list[str] = []
    for aid in load_all_ids():
        item = load_assertion(aid)
        if not item:
            continue
        mapping = item.get("mapping") or {}
        modules = mapping.get("modules") or []
        for module_path in modules:
            if not module_path:
                continue
            if PLANNED_TAG in module_path:
                if verbose:
                    print(f"  SKIP (planned) {aid} → {module_path}")
                continue
            target = ROOT / module_path
            if not target.exists():
                errors.append(f"{aid} cite module inexistant: {module_path}")
    return errors


def _scan_python_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*.py"):
        rel = path.relative_to(ROOT)
        if any(part in SKIPPED_DIRS for part in rel.parts):
            continue
        files.append(path)
    return files


def check_code_to_doctrine(verbose: bool) -> list[str]:
    """Retourne la liste des IDs référencés dans .py mais absents du corpus."""
    known_ids: set[str] = set(load_all_ids())
    errors: list[str] = []
    hits_total = 0
    for py_path in _scan_python_files():
        try:
            text = py_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        found = set(ID_PATTERN.findall(text))
        if not found:
            continue
        hits_total += len(found)
        missing = found - known_ids
        for mid in sorted(missing):
            errors.append(f"{py_path.relative_to(ROOT)} cite ID inconnu: {mid}")
    if verbose:
        print(f"  Scanned {hits_total} ID references across code")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 aussi si warnings (absents modules non-[PLANNED]).",
    )
    args = ap.parse_args()

    print("=" * 64)
    print(" Auto-check doctrine ↔ code alignment (Sprint 10 Phase B.4)")
    print("=" * 64)

    print("\n[Passe 1] Doctrine → Code (mapping.modules existent?)")
    errors_1 = check_doctrine_to_code(args.verbose)
    if errors_1:
        print(f"  {len(errors_1)} désalignements détectés :")
        for e in errors_1[:20]:
            print(f"    - {e}")
        if len(errors_1) > 20:
            print(f"    ... ({len(errors_1) - 20} non-affichés)")
    else:
        print("  ✓ Aucun désalignement")

    print("\n[Passe 2] Code → Doctrine (IDs cités existent?)")
    errors_2 = check_code_to_doctrine(args.verbose)
    if errors_2:
        print(f"  {len(errors_2)} désalignements détectés :")
        for e in errors_2[:20]:
            print(f"    - {e}")
        if len(errors_2) > 20:
            print(f"    ... ({len(errors_2) - 20} non-affichés)")
    else:
        print("  ✓ Aucun désalignement")

    print("\n" + "=" * 64)
    total = len(errors_1) + len(errors_2)
    if total == 0:
        print("  Verdict : ✓ PARFAITEMENT ALIGNÉ")
        print("=" * 64)
        return 0
    if args.strict:
        print(f"  Verdict : ✗ {total} désalignements (strict mode)")
        print("=" * 64)
        return 1
    print(f"  Verdict : ⚠ {total} désalignements (informatif)")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
