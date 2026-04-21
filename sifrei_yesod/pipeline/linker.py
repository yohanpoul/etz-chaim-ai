"""linker.py — Résolution des cross-références inter-sefarim.

Résout les liens entre assertions de différents sefarim et perakim.

Usage:
    python -m sifrei_yesod.pipeline.linker --all
"""

from __future__ import annotations

import argparse
import os
import sys

import psycopg2
import psycopg2.extras

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))


class Linker:
    """Résolution des cross-références entre sefarim."""

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

    def resolve_cross_refs(self) -> int:
        """Resolve target_assertion_id for cross-refs where target exists."""
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE sifrei_yesod_cross_refs cr
            SET target_assertion_id = a.assertion_id
            FROM sifrei_yesod_assertions a
            WHERE cr.target_assertion_id IS NULL
              AND a.assertion_id = cr.target_ref
            """
        )
        count = cur.rowcount
        self.conn.commit()
        return count


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sifrei_yesod.pipeline.linker",
        description="Linker — Résolution des cross-références inter-sefarim",
    )
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--db", default=DB_URL)
    args = parser.parse_args()

    linker = Linker(db_url=args.db)
    try:
        resolved = linker.resolve_cross_refs()
        print(f"  {resolved} cross-références résolues")
    finally:
        linker.close()


if __name__ == "__main__":
    main()
