#!/usr/bin/env python3
"""init_db.py — Bereshit : créer toutes les tables de l'Arbre.

Usage:
    python init_db.py                          # DB par défaut (etz_chaim)
    python init_db.py --db postgresql://...     # DB custom
    python init_db.py --drop                    # Tout supprimer et recréer
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Ordre d'exécution des schémas — respecte les dépendances FK.
# epistememory en premier (Yesod, fondation), le reste n'a pas de FK inter-modules.
# chat + malakhim : modules de persistance/registre, FK internes uniquement.
SCHEMA_ORDER = [
    "epistememory",
    "selfmap",
    "intentkeeper",
    "failuretoinsight",
    "dissensuengine",
    "autojudge",
    "explorationengine",
    "selfmodel",
    "causalengine",
    "insightforge",
    "omer",
    "partzufim",
    "tanya",
    "sifrei_yesod",
    "kabbalah",
    "masakh",
    "gematria",
    "chat",
    "malakhim",
]

BASE_DIR = Path(__file__).parent


def ensure_database(db_url: str) -> None:
    """Crée la base de données si elle n'existe pas."""
    # Parse le nom de la DB depuis l'URL
    # Format: postgresql://[user[:pass]@]host[:port]/dbname
    db_name = db_url.rstrip("/").rsplit("/", 1)[-1]
    base_url = db_url.rstrip("/").rsplit("/", 1)[0] + "/postgres"

    # init_db.py:52 — connexion DIRECTE volontaire (audit cycle 4, C5).
    # La DB cible n'existe pas encore : impossible de l'utiliser via le
    # pool. Ce psycopg2.connect direct est légitime et conservé pour la
    # phase de bootstrap pré-création.
    try:
        conn = psycopg2.connect(base_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        if not cur.fetchone():
            cur.execute(f'CREATE DATABASE "{db_name}"')
            print(f"  ✦ Base de données '{db_name}' créée")
        else:
            print(f"  ✦ Base de données '{db_name}' existe déjà")
        cur.close()
        conn.close()
    except psycopg2.OperationalError as e:
        print(f"  ⚠ Impossible de créer la DB automatiquement: {e}")
        print(f"    Assurez-vous que PostgreSQL tourne et que '{db_name}' existe.")
        sys.exit(1)


def enable_extensions(conn) -> None:
    """Active les extensions requises."""
    cur = conn.cursor()

    # pgvector — requis pour EpisteMemory
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        print("  ✦ Extension pgvector activée")
    except Exception as e:
        conn.rollback()
        print(f"  ⚠ pgvector non disponible: {e}")
        print("    → Les embeddings ne fonctionneront pas.")
        print("    → Installez pgvector: brew install pgvector")

    # TimescaleDB — optionnel, pour les hypertables
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")
        conn.commit()
        print("  ✦ Extension TimescaleDB activée")
        return  # success
    except Exception:
        conn.rollback()
        print("  ⚠ TimescaleDB non disponible — les hypertables seront des tables normales")

    cur.close()


def execute_schema(conn, module_name: str, drop: bool = False) -> bool:
    """Exécute le schema.sql d'un module."""
    schema_path = BASE_DIR / module_name / "schema.sql"
    if not schema_path.exists():
        print(f"  ⚠ {module_name}/schema.sql introuvable — ignoré")
        return False

    sql = schema_path.read_text()
    cur = conn.cursor()

    if drop:
        # Extraire les noms de tables pour les supprimer
        import re
        tables = re.findall(
            r'CREATE TABLE IF NOT EXISTS\s+(\w+)', sql
        )
        for table in reversed(tables):
            try:
                cur.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')
            except Exception:
                conn.rollback()
        conn.commit()

    # Exécuter le schéma complet
    try:
        cur.execute(sql)
        conn.commit()
        print(f"  ✦ {module_name:20s} — OK")
        return True
    except Exception as e:
        conn.rollback()
        error_msg = str(e).strip()

        # Si l'erreur vient de create_hypertable (TimescaleDB absent),
        # réessayer sans les lignes create_hypertable
        if "create_hypertable" in error_msg or "function create_hypertable" in error_msg:
            sql_no_hyper = "\n".join(
                line for line in sql.split("\n")
                if "create_hypertable" not in line.lower()
            )
            try:
                cur.execute(sql_no_hyper)
                conn.commit()
                print(f"  ✦ {module_name:20s} — OK (sans hypertables)")
                return True
            except Exception as e2:
                conn.rollback()
                print(f"  ✗ {module_name:20s} — ÉCHEC: {e2}")
                return False
        else:
            print(f"  ✗ {module_name:20s} — ÉCHEC: {error_msg}")
            return False
    finally:
        cur.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="init_db",
        description="Bereshit — Créer toutes les tables de l'Arbre Etz Chaim",
    )
    parser.add_argument(
        "--db",
        default=(os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim")),
        help="URL PostgreSQL (défaut: postgresql://localhost/etz_chaim)",
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Supprimer et recréer toutes les tables",
    )
    args = parser.parse_args()

    print("═══════════════════════════════════════════════════")
    print("  Bereshit — Création des tables de l'Arbre")
    print("═══════════════════════════════════════════════════")
    print()

    # 1. Créer la DB si nécessaire
    print("1. Base de données")
    ensure_database(args.db)
    print()

    # 2. Connexion via pool (audit cycle 4, C5) — DB existe maintenant
    from pool import get_conn, init_pool
    init_pool(args.db)
    _conn_ctx = get_conn(autocommit=False)
    conn = _conn_ctx.__enter__()

    # 3. Extensions
    print("2. Extensions")
    enable_extensions(conn)
    print()

    # 4. Schémas des 10 Sephiroth
    print("3. Schémas des 10 modules")
    if args.drop:
        print("   (mode --drop : suppression puis recréation)")
    success = 0
    failed = 0
    for module in SCHEMA_ORDER:
        if execute_schema(conn, module, drop=args.drop):
            success += 1
        else:
            failed += 1

    # 5. Hitbonenut (tables inline — pas de schema.sql séparé)
    print()
    print("4. Hitbonenut-2 (expériences + principes)")
    try:
        from hitbonenut import SCHEMA_SQL as HITBONENUT_SCHEMA
        cur = conn.cursor()
        cur.execute(HITBONENUT_SCHEMA)
        conn.commit()
        cur.close()
        print("  ✦ hitbonenut            — OK (sessions + questions + experiments + principles)")
        success += 1
    except Exception as e:
        conn.rollback()
        print(f"  ✗ hitbonenut            — ÉCHEC: {e}")
        failed += 1

    _conn_ctx.__exit__(None, None, None)

    print()
    print("═══════════════════════════════════════════════════")
    print(f"  Résultat : {success}/{len(SCHEMA_ORDER) + 1} modules initialisés")
    if failed:
        print(f"  ⚠ {failed} module(s) en échec")
    else:
        print("  L'Arbre est planté. Les racines sont en place.")
    print("═══════════════════════════════════════════════════")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
