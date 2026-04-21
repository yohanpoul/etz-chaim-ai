#!/usr/bin/env python3
"""auto_ingest.py — Pipeline automatique : YAML → destination → validation → ingestion → embeddings.

Lit le bloc meta d'un fichier YAML Sifrei Yesod, détermine automatiquement
le chemin de destination, crée les répertoires si nécessaires, valide,
ingère avec Sofer, et génère les embeddings.

Usage:
    python -m sifrei_yesod.pipeline.auto_ingest perek_draft.yaml
    python -m sifrei_yesod.pipeline.auto_ingest perek_draft.yaml --dry-run
    python -m sifrei_yesod.pipeline.auto_ingest perek_draft.yaml --no-embed
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

from .validator import validate_file
from .sofer import Sofer, SEFARIM_DIR
from .embedder import Embedder

SEFARIM_ROOT = SEFARIM_DIR  # sifrei_yesod/sefarim/


def resolve_destination(meta: dict) -> Path:
    """Determine the destination path from a perek's meta block.

    Resolution strategy:
      1. sefer → sefarim/{sefer}/
      2. heikhal (if present) → glob heikhal_{NN}_* or create heikhal_{NN}/
      3. shaar → glob shaar_{NN}_* or create shaar_{NN}/
      4. perek + part → perek_{NN}.yaml or perek_{NN}{part}.yaml
    """
    sefer = meta.get("sefer", "etz_chaim")
    heikhal = meta.get("heikhal")
    shaar = meta.get("shaar")
    perek = meta.get("perek")
    part = meta.get("part", "")

    if not shaar or not perek:
        raise ValueError("meta doit contenir au moins 'shaar' et 'perek'")

    # Step 1: sefer directory
    sefer_dir = SEFARIM_ROOT / sefer
    if not sefer_dir.exists():
        raise ValueError(f"Sefer introuvable : {sefer_dir}")

    # Step 2: heikhal directory (optional)
    if heikhal and heikhal > 0:
        parent_dir = _find_or_create_numbered_dir(
            sefer_dir, "heikhal", heikhal,
            meta.get("heikhal_name", ""),
        )
    else:
        parent_dir = sefer_dir

    # Step 3: shaar directory
    shaar_name = meta.get("shaar_name_he", "")
    shaar_dir = _find_or_create_numbered_dir(
        parent_dir, "shaar", shaar, shaar_name,
    )

    # Step 4: perek filename
    if part:
        filename = f"perek_{perek:02d}{part}.yaml"
    else:
        filename = f"perek_{perek:02d}.yaml"

    return shaar_dir / filename


def _find_or_create_numbered_dir(
    parent: Path, prefix: str, number: int, name_hint: str = ""
) -> Path:
    """Find an existing directory matching {prefix}_{NN}_* or create one."""
    pattern = f"{prefix}_{number:02d}_*"
    matches = sorted(parent.glob(pattern))

    # Also check without suffix (e.g., shaar_01/)
    exact = parent / f"{prefix}_{number:02d}"
    if exact.is_dir():
        matches.insert(0, exact)

    if matches:
        return matches[0]

    # Create new directory — use number only (user can rename later)
    new_dir = parent / f"{prefix}_{number:02d}"
    return new_dir


def ensure_meta_yaml(shaar_dir: Path, meta: dict) -> bool:
    """Create a minimal meta.yaml in the sha'ar directory if missing.

    Returns True if a new meta.yaml was created.
    """
    meta_path = shaar_dir / "meta.yaml"
    if meta_path.exists():
        return False

    sefer = meta.get("sefer", "etz_chaim")
    heikhal = meta.get("heikhal", 0)
    shaar = meta.get("shaar", 1)
    shaar_name_he = meta.get("shaar_name_he", "")

    meta_data = {
        "sefer_id": sefer,
        "shaar_number": shaar,
        "shaar_name_he": shaar_name_he,
        "shaar_name_fr": "",
        "nombre_perakim": 0,
        "sujet_principal": "",
        "concepts_cles": [],
    }
    if heikhal and heikhal > 0:
        meta_data["heikhal"] = heikhal

    with open(meta_path, "w", encoding="utf-8") as f:
        yaml.dump(meta_data, f, allow_unicode=True, default_flow_style=False)

    return True


def run_pipeline(
    source_path: Path,
    *,
    dry_run: bool = False,
    skip_embed: bool = False,
    db_url: str | None = None,
) -> None:
    """Run the full auto-ingest pipeline."""
    print(f"\n{'=' * 60}")
    print(f"  AUTO-INGEST PIPELINE")
    print(f"  Source: {source_path}")
    print(f"{'=' * 60}\n")

    # ── 1. Load and parse meta ──────────────────────────────
    if not source_path.exists():
        print(f"  ERREUR: Fichier introuvable : {source_path}", file=sys.stderr)
        sys.exit(1)

    with open(source_path) as f:
        data = yaml.safe_load(f)

    if not data or "meta" not in data:
        print("  ERREUR: Pas de bloc 'meta' dans le YAML", file=sys.stderr)
        sys.exit(1)

    meta = data["meta"]
    print(f"  Sefer:   {meta.get('sefer', '?')}")
    print(f"  Heikhal: {meta.get('heikhal', '-')}")
    print(f"  Sha'ar:  {meta.get('shaar', '?')} ({meta.get('shaar_name_he', '')})")
    print(f"  Perek:   {meta.get('perek', '?')}{meta.get('part', '')}")

    # ── 2. Resolve destination ──────────────────────────────
    dest_path = resolve_destination(meta)
    print(f"\n  Destination: {dest_path}")

    if dry_run:
        print("\n  [DRY RUN] Aucune modification effectuée.")
        # Still validate
        print("\n  --- Validation ---")
        is_valid, errors = validate_file(source_path)
        if is_valid:
            print("  VALIDE")
        else:
            for err in errors:
                print(f"    {err}")
        return

    # ── 3. Create directories & meta ────────────────────────
    dest_dir = dest_path.parent
    created_dir = False
    if not dest_dir.exists():
        dest_dir.mkdir(parents=True, exist_ok=True)
        created_dir = True
        print(f"  Repertoire cree: {dest_dir}")

    created_meta = ensure_meta_yaml(dest_dir, meta)
    if created_meta:
        print(f"  meta.yaml cree:  {dest_dir / 'meta.yaml'}")
        print("  (meta.yaml minimal — a completer manuellement)")

    # Also ensure heikhal meta if needed
    heikhal = meta.get("heikhal")
    if heikhal and heikhal > 0:
        heikhal_dir = dest_dir.parent
        heikhal_meta = heikhal_dir / "meta.yaml"
        if not heikhal_meta.exists():
            h_data = {
                "sefer_id": meta.get("sefer", "etz_chaim"),
                "heikhal_number": heikhal,
                "heikhal_name_he": meta.get("heikhal_name", ""),
                "heikhal_name_fr": "",
                "nombre_shaarim": 0,
                "description": "",
            }
            with open(heikhal_meta, "w", encoding="utf-8") as f:
                yaml.dump(h_data, f, allow_unicode=True, default_flow_style=False)
            print(f"  heikhal meta.yaml cree: {heikhal_meta}")

    # ── 4. Copy file ────────────────────────────────────────
    if source_path.resolve() != dest_path.resolve():
        shutil.copy2(source_path, dest_path)
        print(f"  Copie: {source_path.name} -> {dest_path}")
    else:
        print(f"  Fichier deja en place: {dest_path}")

    # ── 5. Validate ─────────────────────────────────────────
    print("\n  --- Validation ---")
    is_valid, errors = validate_file(dest_path)
    if not is_valid:
        print("  ECHEC VALIDATION:")
        for err in errors:
            print(f"    {err}")
        sys.exit(1)
    print("  VALIDE")

    # ── 6. Ingest with Sofer ────────────────────────────────
    print("\n  --- Ingestion (Sofer) ---")
    sofer_kwargs = {}
    if db_url:
        sofer_kwargs["db_url"] = db_url
    sofer = Sofer(**sofer_kwargs)
    try:
        report = sofer.ingest_perek(dest_path)
        if report.errors:
            print("  ECHEC INGESTION:")
            for err in report.errors:
                print(f"    {err}")
            sys.exit(1)
        elif report.skipped:
            print("  Fichier inchange (hash identique)")
        else:
            print(
                f"  {report.assertions_upserted} assertions, "
                f"{report.relations_upserted} relations, "
                f"{report.principes_upserted} principes, "
                f"{report.concepts_created} concepts crees"
            )
    finally:
        sofer.close()

    # ── 7. Generate embeddings ──────────────────────────────
    if skip_embed:
        print("\n  --- Embeddings: SKIP (--no-embed) ---")
    else:
        print("\n  --- Embeddings ---")
        embedder = Embedder(**({"db_url": db_url} if db_url else {}))
        try:
            results = embedder.embed_all()
            total = sum(results.values())
            if total:
                print(
                    f"  {results['assertions']} assertions, "
                    f"{results['concepts']} concepts, "
                    f"{results['principes']} principes"
                )
            else:
                print("  Aucun embedding manquant")
        finally:
            embedder.close()

    # ── Done ────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  PIPELINE TERMINE")
    print(f"  Fichier: {dest_path}")
    print(f"{'=' * 60}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sifrei_yesod.pipeline.auto_ingest",
        description="Auto-ingest — Pipeline complet YAML -> destination -> validation -> DB -> embeddings",
    )
    parser.add_argument("file", type=Path, help="Fichier YAML a ingerer")
    parser.add_argument("--dry-run", action="store_true", help="Valider sans ingerer")
    parser.add_argument("--no-embed", action="store_true", help="Skip la generation d'embeddings")
    parser.add_argument("--db", help="URL PostgreSQL (defaut: ETZ_CHAIM_DB ou localhost)")
    args = parser.parse_args()

    filepath = args.file if args.file.is_absolute() else Path.cwd() / args.file

    run_pipeline(
        filepath,
        dry_run=args.dry_run,
        skip_embed=args.no_embed,
        db_url=args.db,
    )


if __name__ == "__main__":
    main()
