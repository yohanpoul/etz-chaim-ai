"""sofer.py — Pipeline d'ingestion YAML → PostgreSQL pour les Sifrei Yesod.

Le Sofer (scribe) lit les fichiers YAML transposés et les ingère dans la base,
de manière idempotente (même fichier relancé = pas de doublons).

Usage:
    python -m sifrei_yesod.pipeline.sofer --all
    python -m sifrei_yesod.pipeline.sofer --path sefarim/etz_chaim/
    python -m sifrei_yesod.pipeline.sofer --file sefarim/etz_chaim/shaar_01_klalim/perek_01.yaml
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import psycopg2
import psycopg2.extras
import yaml

from .validator import validate_perek, validate_meta_sefer, validate_meta_heikhal, validate_meta_shaar

SEFARIM_DIR = Path(__file__).parent.parent / "sefarim"
DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))


@dataclass
class IngestionReport:
    """Rapport d'ingestion d'un perek."""
    filepath: str = ""
    assertions_upserted: int = 0
    relations_upserted: int = 0
    principes_upserted: int = 0
    concepts_created: int = 0
    skipped: bool = False
    errors: list[str] = field(default_factory=list)


def file_sha256(path: Path) -> str:
    """Compute SHA256 of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


class Sofer:
    """Pipeline Sofer : YAML → PostgreSQL."""

    def __init__(self, db_url: str = DB_URL) -> None:
        self.db_url = db_url
        self._conn: psycopg2.extensions.connection | None = None

    @property
    def conn(self) -> psycopg2.extensions.connection:
        if self._conn is None or self._conn.closed:
            # Pipeline batch standalone — connexion DIRECTE volontaire
            # (audit cycle 4, C5). Long-lived avec contrôle transactionnel
            # manuel (commit/rollback explicite). Le pool est pour le code
            # daemon-actif ; ces scripts sont CLI/pipelines one-shot.

            self._conn = psycopg2.connect(self.db_url)
            self._conn.autocommit = False
        return self._conn

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()

    # ── Meta ingestion ──────────────────────────────────────────

    def ensure_heikhal(self, meta: dict) -> None:
        """UPSERT a heikhal from its meta.yaml."""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO sifrei_yesod_heikhalot
                (sefer_id, heikhal_number, heikhal_name_he, heikhal_name_fr,
                 nombre_shaarim, description)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (sefer_id, heikhal_number) DO UPDATE SET
                heikhal_name_he = EXCLUDED.heikhal_name_he,
                heikhal_name_fr = EXCLUDED.heikhal_name_fr,
                nombre_shaarim = EXCLUDED.nombre_shaarim,
                description = EXCLUDED.description,
                updated_at = NOW()
            """,
            (
                meta["sefer_id"],
                meta["heikhal_number"],
                meta["heikhal_name_he"],
                meta["heikhal_name_fr"],
                meta.get("nombre_shaarim"),
                meta.get("description"),
            ),
        )
        self.conn.commit()

    def ensure_sefer(self, meta: dict) -> None:
        """UPSERT a sefer from its meta.yaml."""
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO sifrei_yesod_sefarim
                (sefer_id, titre_he, titre_fr, auteur, maitre,
                 edition_base, date_composition, structure_type,
                 nombre_shaarim, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (sefer_id) DO UPDATE SET
                titre_he = EXCLUDED.titre_he,
                titre_fr = EXCLUDED.titre_fr,
                auteur = EXCLUDED.auteur,
                maitre = EXCLUDED.maitre,
                edition_base = EXCLUDED.edition_base,
                date_composition = EXCLUDED.date_composition,
                structure_type = EXCLUDED.structure_type,
                nombre_shaarim = EXCLUDED.nombre_shaarim,
                description = EXCLUDED.description,
                updated_at = NOW()
            """,
            (
                meta["sefer_id"],
                meta["titre_he"],
                meta["titre_fr"],
                meta["auteur"],
                meta.get("maitre"),
                meta["edition_base"],
                meta.get("date_composition"),
                meta.get("structure", {}).get("type"),
                meta.get("structure", {}).get("nombre_shaarim"),
                meta.get("description"),
            ),
        )
        self.conn.commit()

    def ensure_shaar(self, meta: dict) -> None:
        """UPSERT a sha'ar from its meta.yaml."""
        cur = self.conn.cursor()
        connexions = meta.get("connexions_systeme", {})
        heikhal = meta.get("heikhal", 0)
        cur.execute(
            """
            INSERT INTO sifrei_yesod_shaarim
                (sefer_id, heikhal_number, shaar_number, shaar_name_he, shaar_name_fr,
                 nombre_perakim, sujet_principal, concepts_cles,
                 connexions_modules, connexions_domaines)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (sefer_id, heikhal_number, shaar_number)
            DO UPDATE SET
                shaar_name_he = EXCLUDED.shaar_name_he,
                shaar_name_fr = EXCLUDED.shaar_name_fr,
                nombre_perakim = EXCLUDED.nombre_perakim,
                sujet_principal = EXCLUDED.sujet_principal,
                concepts_cles = EXCLUDED.concepts_cles,
                connexions_modules = EXCLUDED.connexions_modules,
                connexions_domaines = EXCLUDED.connexions_domaines,
                updated_at = NOW()
            """,
            (
                meta["sefer_id"],
                heikhal,
                meta["shaar_number"],
                meta["shaar_name_he"],
                meta["shaar_name_fr"],
                meta.get("nombre_perakim", 0),
                meta.get("sujet_principal"),
                meta.get("concepts_cles"),
                connexions.get("modules"),
                connexions.get("domaines"),
            ),
        )
        self.conn.commit()

    # ── Perek ingestion ─────────────────────────────────────────

    def ingest_perek(self, filepath: Path) -> IngestionReport:
        """Ingest a single perek YAML file into PostgreSQL."""
        report = IngestionReport(filepath=str(filepath))

        # Load YAML
        with open(filepath) as f:
            data = yaml.safe_load(f)

        if data is None:
            report.errors.append("Fichier vide")
            return report

        # Validate
        errors = validate_perek(data, str(filepath))
        if errors:
            report.errors = errors
            return report

        # Check hash — skip if unchanged
        current_hash = file_sha256(filepath)
        meta = data["meta"]
        heikhal = meta.get("heikhal", 0)
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute(
            """SELECT id, yaml_hash FROM sifrei_yesod_perakim
               WHERE sefer_id = %s AND heikhal_number = %s
                     AND shaar_number = %s AND perek_number = %s""",
            (meta["sefer"], heikhal, meta["shaar"], meta["perek"]),
        )
        existing = cur.fetchone()

        if existing and existing["yaml_hash"] == current_hash:
            report.skipped = True
            return report

        try:
            # UPSERT perek
            cur.execute(
                """
                INSERT INTO sifrei_yesod_perakim
                    (sefer_id, heikhal_number, shaar_number, perek_number,
                     source_edition, transposed_by, version, strates, yaml_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (sefer_id, heikhal_number, shaar_number, perek_number)
                DO UPDATE SET
                    source_edition = EXCLUDED.source_edition,
                    transposed_by = EXCLUDED.transposed_by,
                    version = EXCLUDED.version,
                    strates = EXCLUDED.strates,
                    yaml_hash = EXCLUDED.yaml_hash,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    meta["sefer"],
                    heikhal,
                    meta["shaar"],
                    meta["perek"],
                    meta["source_edition"],
                    meta["transposed_by"],
                    meta["version"],
                    meta["strates"],
                    current_hash,
                ),
            )
            perek_id = cur.fetchone()["id"]

            # Ingest assertions (Couche Peshat-Machine)
            for assertion in data["assertions"]:
                strate = assertion.get("strate", "base")
                mapping = assertion.get("mapping", {})
                cur.execute(
                    """
                    INSERT INTO sifrei_yesod_assertions
                        (assertion_id, perek_id, source_he, source_ref, assertion,
                         assertion_type, concepts, mapping_modules, mapping_tables,
                         mapping_partzufim, mapping_relevance, strate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (assertion_id) DO UPDATE SET
                        perek_id = EXCLUDED.perek_id,
                        source_he = EXCLUDED.source_he,
                        source_ref = EXCLUDED.source_ref,
                        assertion = EXCLUDED.assertion,
                        assertion_type = EXCLUDED.assertion_type,
                        concepts = EXCLUDED.concepts,
                        mapping_modules = EXCLUDED.mapping_modules,
                        mapping_tables = EXCLUDED.mapping_tables,
                        mapping_partzufim = EXCLUDED.mapping_partzufim,
                        mapping_relevance = EXCLUDED.mapping_relevance,
                        strate = EXCLUDED.strate,
                        embedding = NULL,
                        updated_at = NOW()
                    """,
                    (
                        assertion["id"],
                        perek_id,
                        assertion["source_he"],
                        assertion["source_ref"],
                        assertion["assertion"],
                        assertion["type"],
                        json.dumps(assertion["concepts"]),
                        mapping.get("modules"),
                        mapping.get("tables"),
                        mapping.get("partzufim"),
                        mapping.get("relevance"),
                        strate,
                    ),
                )
                report.assertions_upserted += 1

                # Auto-create concepts
                for concept in assertion["concepts"]:
                    cur.execute(
                        """
                        INSERT INTO sifrei_yesod_concepts (concept_id, premiere_apparition)
                        VALUES (%s, %s)
                        ON CONFLICT (concept_id) DO NOTHING
                        """,
                        (concept["id"], assertion["id"]),
                    )
                    if cur.rowcount > 0:
                        report.concepts_created += 1

            # Ingest relations (Couche Remez-Relational)
            for relation in data["relations"]:
                strate = relation.get("strate", "base")
                cur.execute(
                    """
                    INSERT INTO sifrei_yesod_relations
                        (relation_id, perek_id, relation_type, concept_from, concept_to,
                         paire, via, nature, pattern, assertions_source,
                         bidirectionnel, strate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (relation_id) DO UPDATE SET
                        perek_id = EXCLUDED.perek_id,
                        relation_type = EXCLUDED.relation_type,
                        concept_from = EXCLUDED.concept_from,
                        concept_to = EXCLUDED.concept_to,
                        paire = EXCLUDED.paire,
                        via = EXCLUDED.via,
                        nature = EXCLUDED.nature,
                        pattern = EXCLUDED.pattern,
                        assertions_source = EXCLUDED.assertions_source,
                        bidirectionnel = EXCLUDED.bidirectionnel,
                        strate = EXCLUDED.strate,
                        updated_at = NOW()
                    """,
                    (
                        relation["id"],
                        perek_id,
                        relation["type"],
                        relation.get("from"),
                        relation.get("to"),
                        relation.get("paire"),
                        relation.get("via"),
                        relation["nature"],
                        relation.get("pattern"),
                        relation["assertions_source"],
                        relation.get("bidirectionnel", False),
                        strate,
                    ),
                )
                report.relations_upserted += 1

            # Ingest principes (Couche Sod-Generative)
            for principe in data["principes_generatifs"]:
                strate = principe.get("strate", "base")
                cur.execute(
                    """
                    INSERT INTO sifrei_yesod_principes
                        (principe_id, perek_id, nom, source_assertions,
                         formalisation, applications_ia, questions_ouvertes, strate)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (principe_id) DO UPDATE SET
                        perek_id = EXCLUDED.perek_id,
                        nom = EXCLUDED.nom,
                        source_assertions = EXCLUDED.source_assertions,
                        formalisation = EXCLUDED.formalisation,
                        applications_ia = EXCLUDED.applications_ia,
                        questions_ouvertes = EXCLUDED.questions_ouvertes,
                        strate = EXCLUDED.strate,
                        embedding = NULL,
                        updated_at = NOW()
                    """,
                    (
                        principe["id"],
                        perek_id,
                        principe["nom"],
                        principe["source_assertions"],
                        principe["formalisation"],
                        principe["applications_ia"],
                        principe.get("questions_ouvertes"),
                        strate,
                    ),
                )
                report.principes_upserted += 1

            self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            report.errors.append(f"Erreur PostgreSQL: {e}")

        return report

    # ── Scanning ────────────────────────────────────────────────

    def scan_and_ingest(self, base_path: Path | None = None) -> list[IngestionReport]:
        """Scan for YAML files and ingest them.

        4-pass algorithm:
          1. Sefer meta.yaml
          2. Heikhal meta.yaml
          3. Sha'ar meta.yaml
          4. Perek YAML files
        """
        base = base_path or SEFARIM_DIR
        if not base.exists():
            print(f"  ⚠ Dossier introuvable: {base}")
            return []

        reports: list[IngestionReport] = []

        # Collect all meta.yaml files once
        all_metas = sorted(base.rglob("meta.yaml"))

        # Pass 1: ingest sefer meta.yaml files
        for meta_path in all_metas:
            with open(meta_path) as f:
                data = yaml.safe_load(f)
            if data is None:
                continue

            if "structure" in data and "sefer_id" in data:
                errors = validate_meta_sefer(data)
                if errors:
                    print(f"  ✗ {meta_path}: {errors}")
                    continue
                self.ensure_sefer(data)
                print(f"  ✦ Sefer: {data['sefer_id']}")

        # Pass 2: ingest heikhal meta.yaml files
        for meta_path in all_metas:
            with open(meta_path) as f:
                data = yaml.safe_load(f)
            if data is None:
                continue

            if "heikhal_number" in data and "sefer_id" in data:
                errors = validate_meta_heikhal(data)
                if errors:
                    print(f"  ✗ {meta_path}: {errors}")
                    continue
                self.ensure_heikhal(data)
                print(f"  ✦ Heikhal {data['heikhal_number']}: {data['heikhal_name_he']}")

        # Pass 3: ingest sha'ar meta.yaml files
        for meta_path in all_metas:
            with open(meta_path) as f:
                data = yaml.safe_load(f)
            if data is None:
                continue

            if "shaar_number" in data and "structure" not in data:
                errors = validate_meta_shaar(data)
                if errors:
                    print(f"  ✗ {meta_path}: {errors}")
                    continue
                self.ensure_shaar(data)
                heikhal_tag = f" (H{data['heikhal']})" if data.get("heikhal") else ""
                print(f"  ✦ Sha'ar: {data['shaar_name_he']}{heikhal_tag}")

        # Pass 4: ingest perek YAML files
        for yaml_path in sorted(base.rglob("perek_*.yaml")):
            report = self.ingest_perek(yaml_path)
            reports.append(report)

            if report.errors:
                print(f"  ✗ {yaml_path}")
                for err in report.errors:
                    print(f"    {err}")
            elif report.skipped:
                print(f"  ○ {yaml_path} (inchangé)")
            else:
                print(
                    f"  ✓ {yaml_path} — "
                    f"{report.assertions_upserted}A "
                    f"{report.relations_upserted}R "
                    f"{report.principes_upserted}P "
                    f"{report.concepts_created}C"
                )

        return reports


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sifrei_yesod.pipeline.sofer",
        description="Sofer — Ingestion YAML → PostgreSQL pour Sifrei Yesod",
    )
    parser.add_argument("--all", action="store_true", help="Ingérer tous les sefarim")
    parser.add_argument("--path", type=Path, help="Dossier spécifique à ingérer")
    parser.add_argument("--file", type=Path, help="Fichier YAML unique à ingérer")
    parser.add_argument(
        "--db",
        default=DB_URL,
        help="URL PostgreSQL",
    )
    args = parser.parse_args()

    if not args.all and not args.path and not args.file:
        parser.error("--all, --path ou --file requis")

    sofer = Sofer(db_url=args.db)

    try:
        if args.file:
            filepath = args.file if args.file.is_absolute() else SEFARIM_DIR.parent / args.file
            report = sofer.ingest_perek(filepath)
            if report.errors:
                for err in report.errors:
                    print(f"  ✗ {err}")
                sys.exit(1)
            elif report.skipped:
                print("  ○ Fichier inchangé")
            else:
                print(
                    f"  ✓ {report.assertions_upserted} assertions, "
                    f"{report.relations_upserted} relations, "
                    f"{report.principes_upserted} principes, "
                    f"{report.concepts_created} concepts créés"
                )
        else:
            base = None
            if args.path:
                base = args.path if args.path.is_absolute() else SEFARIM_DIR.parent / args.path
            reports = sofer.scan_and_ingest(base)

            total_a = sum(r.assertions_upserted for r in reports)
            total_r = sum(r.relations_upserted for r in reports)
            total_p = sum(r.principes_upserted for r in reports)
            total_c = sum(r.concepts_created for r in reports)
            total_err = sum(1 for r in reports if r.errors)
            total_skip = sum(1 for r in reports if r.skipped)

            print(f"\n{'=' * 50}")
            print(f"  Perakim: {len(reports)} ({total_skip} inchangés, {total_err} erreurs)")
            print(f"  Assertions: {total_a}  Relations: {total_r}  Principes: {total_p}")
            print(f"  Concepts créés: {total_c}")

            if total_err:
                sys.exit(1)
    finally:
        sofer.close()


if __name__ == "__main__":
    main()
