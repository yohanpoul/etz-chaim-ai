"""validator.py — Validation des fichiers perek YAML avant ingestion.

Usage:
    python -m sifrei_yesod.pipeline.validator --file sefarim/etz_chaim/shaar_01_klalim/perek_01.yaml
    python -m sifrei_yesod.pipeline.validator --dir sefarim/etz_chaim/
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    import jsonschema
except ImportError:
    print("jsonschema requis: pip install jsonschema")
    sys.exit(1)

SCHEMA_DIR = Path(__file__).parent.parent / "schema"
SEFARIM_DIR = Path(__file__).parent.parent / "sefarim"


def load_schema(name: str) -> dict:
    """Load a YAML schema file by name."""
    path = SCHEMA_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Schema introuvable: {path}")
    with open(path) as f:
        return yaml.safe_load(f)


def validate_perek(data: dict, filepath: str = "<unknown>") -> list[str]:
    """Validate a perek YAML against the schema and internal consistency.

    Returns a list of error messages (empty = valid).
    Cross-perek references (assertions_source pointing to IDs from other perakim)
    are reported as warnings to stderr but not counted as errors.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # 1. JSON Schema validation
    schema = load_schema("perek_schema")
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[schema] {path}: {error.message}")

    if errors:
        return errors

    # 2. Internal consistency checks
    # Collect all assertion IDs
    assertion_ids: set[str] = set()
    for i, a in enumerate(data.get("assertions", [])):
        aid = a.get("id", "")
        if aid in assertion_ids:
            errors.append(f"[duplicate] assertions[{i}].id: '{aid}' apparaît plus d'une fois")
        assertion_ids.add(aid)

    # Check relation IDs unique + assertions_source valid
    relation_ids: set[str] = set()
    for i, r in enumerate(data.get("relations", [])):
        rid = r.get("id", "")
        if rid in relation_ids:
            errors.append(f"[duplicate] relations[{i}].id: '{rid}' apparaît plus d'une fois")
        relation_ids.add(rid)

        for src_id in r.get("assertions_source", []):
            if src_id not in assertion_ids:
                warnings.append(
                    f"[xref] relations[{i}].assertions_source: '{src_id}' "
                    f"est une référence inter-perek (non présente dans ce fichier)"
                )

    # Check principe IDs unique + source_assertions valid
    principe_ids: set[str] = set()
    for i, p in enumerate(data.get("principes_generatifs", [])):
        pid = p.get("id", "")
        if pid in principe_ids:
            errors.append(f"[duplicate] principes_generatifs[{i}].id: '{pid}' apparaît plus d'une fois")
        principe_ids.add(pid)

        for src_id in p.get("source_assertions", []):
            if src_id not in assertion_ids:
                warnings.append(
                    f"[xref] principes_generatifs[{i}].source_assertions: '{src_id}' "
                    f"est une référence inter-perek (non présente dans ce fichier)"
                )

    # Check relation from/to reference known concepts
    concept_ids: set[str] = set()
    for a in data.get("assertions", []):
        for c in a.get("concepts", []):
            concept_ids.add(c.get("id", ""))

    for i, r in enumerate(data.get("relations", [])):
        if r.get("from") and r["from"] not in concept_ids:
            errors.append(
                f"[ref] relations[{i}].from: concept '{r['from']}' "
                f"n'apparaît dans aucune assertion de ce perek"
            )
        if r.get("to") and r["to"] not in concept_ids:
            errors.append(
                f"[ref] relations[{i}].to: concept '{r['to']}' "
                f"n'apparaît dans aucune assertion de ce perek"
            )

    # Print warnings to stderr (informational, not blocking)
    if warnings:
        import sys as _sys
        for w in warnings:
            _sys.stderr.write(f"  ⚠ {filepath}: {w}\n")

    return errors


def validate_meta_sefer(data: dict) -> list[str]:
    """Validate a sefer meta.yaml."""
    schema = load_schema("meta_sefer_schema")
    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[schema] {path}: {error.message}")
    return errors


def validate_meta_heikhal(data: dict) -> list[str]:
    """Validate a heikhal meta.yaml."""
    schema = load_schema("meta_heikhal_schema")
    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[schema] {path}: {error.message}")
    return errors


def validate_meta_shaar(data: dict) -> list[str]:
    """Validate a sha'ar meta.yaml."""
    schema = load_schema("meta_shaar_schema")
    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(f"[schema] {path}: {error.message}")
    return errors


def validate_file(filepath: Path) -> tuple[bool, list[str]]:
    """Validate a YAML file (auto-detect type).

    Returns (is_valid, errors).
    """
    if not filepath.exists():
        return False, [f"Fichier introuvable: {filepath}"]

    with open(filepath) as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            return False, [f"Erreur YAML: {e}"]

    if data is None:
        return False, ["Fichier vide"]

    # Detect file type by name and content
    name = filepath.name
    if name == "meta.yaml":
        if "sefer_id" in data and "structure" in data:
            errors = validate_meta_sefer(data)
        elif "heikhal_number" in data:
            errors = validate_meta_heikhal(data)
        elif "shaar_number" in data:
            errors = validate_meta_shaar(data)
        else:
            errors = ["meta.yaml: impossible de déterminer le type (sefer, heikhal ou sha'ar)"]
    else:
        errors = validate_perek(data, str(filepath))

    return len(errors) == 0, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sifrei_yesod.pipeline.validator",
        description="Valider les fichiers YAML Sifrei Yesod",
    )
    parser.add_argument("--file", type=Path, help="Fichier YAML à valider")
    parser.add_argument("--dir", type=Path, help="Dossier à scanner récursivement")
    args = parser.parse_args()

    if not args.file and not args.dir:
        parser.error("--file ou --dir requis")

    files: list[Path] = []
    if args.file:
        files.append(args.file)
    if args.dir:
        base = args.dir if args.dir.is_absolute() else SEFARIM_DIR.parent / args.dir
        files.extend(sorted(base.rglob("*.yaml")))

    total = 0
    valid = 0
    for f in files:
        total += 1
        ok, errors = validate_file(f)
        if ok:
            valid += 1
            print(f"  ✓ {f}")
        else:
            print(f"  ✗ {f}")
            for err in errors:
                print(f"    {err}")

    print(f"\n{'=' * 40}")
    print(f"  {valid}/{total} fichiers valides")
    if valid < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
