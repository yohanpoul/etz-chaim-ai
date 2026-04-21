"""query.py — API pour interroger les Sifrei Yesod.

Interface unifiée pour les 3 couches (Peshat, Remez, Sod) et le registre des concepts.
"""

from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
import psycopg2.extras

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))


class SifreiYesodQuery:
    """Interface pour interroger la bibliothèque sacrée."""

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
            try:
                from pgvector.psycopg2 import register_vector
                register_vector(self._conn)
            except ImportError as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            self._conn.commit()
            self._conn.autocommit = True
        return self._conn

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()

    def _fetchone(self, query: str, params: tuple = ()) -> dict | None:
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None

    def _fetchall(self, query: str, params: tuple = ()) -> list[dict]:
        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    # ── Sefarim & Shaarim ────────────────────────────────────────

    def get_sefer(self, sefer_id: str) -> dict | None:
        """Récupérer un sefer par son ID."""
        return self._fetchone(
            "SELECT * FROM sifrei_yesod_sefarim WHERE sefer_id = %s",
            (sefer_id,),
        )

    def get_shaarim(self, sefer_id: str) -> list[dict]:
        """Récupérer tous les shaarim d'un sefer, ordonnés par numéro."""
        return self._fetchall(
            "SELECT * FROM sifrei_yesod_shaarim WHERE sefer_id = %s ORDER BY shaar_number",
            (sefer_id,),
        )

    # ── Navigation hiérarchique (sefer → heikhalot → shaarim → perakim) ──

    def get_heikhalot(self, sefer_id: str) -> list[dict]:
        """Lister tous les heikhalot (palais) d'un sefer, ordonnés par numéro."""
        return self._fetchall(
            """SELECT * FROM sifrei_yesod_heikhalot
               WHERE sefer_id = %s
               ORDER BY heikhal_number""",
            (sefer_id,),
        )

    def get_shaarim_by_heikhal(self, sefer_id: str, heikhal_number: int) -> list[dict]:
        """Lister les shaarim d'un heikhal spécifique, ordonnés par numéro."""
        return self._fetchall(
            """SELECT * FROM sifrei_yesod_shaarim
               WHERE sefer_id = %s AND heikhal_number = %s
               ORDER BY shaar_number""",
            (sefer_id, heikhal_number),
        )

    def get_perakim(self, sefer_id: str, shaar_number: int) -> list[dict]:
        """Lister les perakim d'un shaar, ordonnés par numéro.

        Retourne les perakim de tous les heikhalot pour ce shaar_number.
        """
        return self._fetchall(
            """SELECT * FROM sifrei_yesod_perakim
               WHERE sefer_id = %s AND shaar_number = %s
               ORDER BY heikhal_number, perek_number""",
            (sefer_id, shaar_number),
        )

    def get_hierarchy(self, sefer_id: str) -> dict | None:
        """Arbre complet : sefer → heikhalot → shaarim → perakim (nested).

        Returns:
            dict avec clés sefer + heikhalot[], chaque heikhal contenant
            shaarim[], chaque shaar contenant perakim[].
            Les shaarim standalone (heikhal_number=0) apparaissent sous
            un heikhal virtuel {heikhal_number: 0, heikhal_name_fr: "Standalone"}.
            None si le sefer n'existe pas.
        """
        sefer = self.get_sefer(sefer_id)
        if not sefer:
            return None

        # Récupérer toutes les données en 3 requêtes
        heikhalot = self.get_heikhalot(sefer_id)
        shaarim = self._fetchall(
            """SELECT * FROM sifrei_yesod_shaarim
               WHERE sefer_id = %s
               ORDER BY heikhal_number, shaar_number""",
            (sefer_id,),
        )
        perakim = self._fetchall(
            """SELECT * FROM sifrei_yesod_perakim
               WHERE sefer_id = %s
               ORDER BY heikhal_number, shaar_number, perek_number""",
            (sefer_id,),
        )

        # Indexer perakim par (heikhal_number, shaar_number)
        perakim_by_shaar: dict[tuple[int, int], list[dict]] = {}
        for p in perakim:
            key = (p["heikhal_number"], p["shaar_number"])
            perakim_by_shaar.setdefault(key, []).append(p)

        # Indexer shaarim par heikhal_number
        shaarim_by_heikhal: dict[int, list[dict]] = {}
        for s in shaarim:
            h_num = s["heikhal_number"]
            shaarim_by_heikhal.setdefault(h_num, [])
            s_copy = dict(s)
            s_copy["perakim"] = perakim_by_shaar.get((h_num, s["shaar_number"]), [])
            shaarim_by_heikhal[h_num].append(s_copy)

        # Construire les heikhalot avec shaarim imbriqués
        heikhal_nums_in_db = {h["heikhal_number"] for h in heikhalot}
        result_heikhalot: list[dict] = []

        # Ajouter les shaarim standalone (heikhal_number=0) si présents
        if 0 in shaarim_by_heikhal and 0 not in heikhal_nums_in_db:
            result_heikhalot.append({
                "heikhal_number": 0,
                "heikhal_name_he": "",
                "heikhal_name_fr": "Standalone",
                "shaarim": shaarim_by_heikhal[0],
            })

        for h in heikhalot:
            h_copy = dict(h)
            h_copy["shaarim"] = shaarim_by_heikhal.get(h["heikhal_number"], [])
            result_heikhalot.append(h_copy)

        sefer["heikhalot"] = result_heikhalot
        return sefer

    # ── Assertions (Couche Peshat-Machine) ──────────────────────

    def get_assertion(self, assertion_id: str) -> dict | None:
        """Récupérer une assertion par son ID canonique."""
        return self._fetchone(
            "SELECT * FROM sifrei_yesod_assertions WHERE assertion_id = %s",
            (assertion_id,),
        )

    def search_assertions(self, query: str, limit: int = 10) -> list[dict]:
        """Recherche sémantique dans les assertions (via embedding)."""
        from epistememory.embedding import embed

        vec = embed(query)
        return self._fetchall(
            """
            SELECT *, 1 - (embedding <=> %s::vector) AS similarity
            FROM sifrei_yesod_assertions
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vec, vec, limit),
        )

    # ── Concepts ────────────────────────────────────────────────

    def get_concept(self, concept_id: str) -> dict | None:
        """Récupérer un concept avec toutes ses assertions et relations."""
        concept = self._fetchone(
            "SELECT * FROM sifrei_yesod_concepts WHERE concept_id = %s",
            (concept_id,),
        )
        if not concept:
            return None

        concept["assertions"] = self._fetchall(
            """SELECT * FROM sifrei_yesod_assertions
               WHERE concepts @> %s::jsonb""",
            (json.dumps([{"id": concept_id}]),),
        )

        concept["relations"] = self.get_relations_for_concept(concept_id)
        return concept

    def get_relations_for_concept(self, concept_id: str) -> list[dict]:
        """Toutes les relations où ce concept apparaît (from ou to)."""
        return self._fetchall(
            """
            SELECT * FROM sifrei_yesod_relations
            WHERE concept_from = %s OR concept_to = %s
               OR %s = ANY(paire)
            ORDER BY relation_id
            """,
            (concept_id, concept_id, concept_id),
        )

    # ── Principes (Couche Sod-Generative) ───────────────────────

    def get_principe(self, principe_id: str) -> dict | None:
        """Récupérer un principe génératif."""
        return self._fetchone(
            "SELECT * FROM sifrei_yesod_principes WHERE principe_id = %s",
            (principe_id,),
        )

    def search_principes(self, query: str, limit: int = 5) -> list[dict]:
        """Recherche sémantique dans les principes génératifs."""
        from epistememory.embedding import embed

        vec = embed(query)
        return self._fetchall(
            """
            SELECT *, 1 - (embedding <=> %s::vector) AS similarity
            FROM sifrei_yesod_principes
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (vec, vec, limit),
        )

    # ── Perek complet ───────────────────────────────────────────

    def get_perek_complet(self, sefer: str, shaar: int, perek: int) -> dict | None:
        """Récupérer un perek complet avec ses 3 couches."""
        perek_row = self._fetchone(
            """SELECT * FROM sifrei_yesod_perakim
               WHERE sefer_id = %s AND shaar_number = %s AND perek_number = %s""",
            (sefer, shaar, perek),
        )
        if not perek_row:
            return None

        perek_id = perek_row["id"]
        perek_row["assertions"] = self._fetchall(
            "SELECT * FROM sifrei_yesod_assertions WHERE perek_id = %s ORDER BY assertion_id",
            (perek_id,),
        )
        perek_row["relations"] = self._fetchall(
            "SELECT * FROM sifrei_yesod_relations WHERE perek_id = %s ORDER BY relation_id",
            (perek_id,),
        )
        perek_row["principes"] = self._fetchall(
            "SELECT * FROM sifrei_yesod_principes WHERE perek_id = %s ORDER BY principe_id",
            (perek_id,),
        )
        return perek_row

    # ── Traversée de graphe ─────────────────────────────────────

    def traverse_relations(self, concept_id: str, depth: int = 2) -> dict:
        """Traverser le graphe relationnel depuis un concept."""
        visited: set[str] = set()
        result: dict[str, Any] = {"root": concept_id, "nodes": {}, "edges": []}

        def _traverse(cid: str, current_depth: int) -> None:
            if cid in visited or current_depth > depth:
                return
            visited.add(cid)

            concept = self._fetchone(
                "SELECT concept_id, nom_he, nom_fr, domaine FROM sifrei_yesod_concepts WHERE concept_id = %s",
                (cid,),
            )
            if concept:
                result["nodes"][cid] = concept

            relations = self.get_relations_for_concept(cid)
            for rel in relations:
                edge = {
                    "id": rel["relation_id"],
                    "type": rel["relation_type"],
                    "from": rel.get("concept_from"),
                    "to": rel.get("concept_to"),
                    "nature": rel["nature"],
                }
                if edge not in result["edges"]:
                    result["edges"].append(edge)

                # Traverse neighbors
                neighbor = None
                if rel.get("concept_from") == cid:
                    neighbor = rel.get("concept_to")
                elif rel.get("concept_to") == cid:
                    neighbor = rel.get("concept_from")

                if neighbor:
                    _traverse(neighbor, current_depth + 1)

        _traverse(concept_id, 0)
        return result

    # ── Cross-références ────────────────────────────────────────

    def get_cross_refs(self, assertion_id: str) -> list[dict]:
        """Récupérer les cross-références inter-sefarim."""
        return self._fetchall(
            "SELECT * FROM sifrei_yesod_cross_refs WHERE source_assertion_id = %s",
            (assertion_id,),
        )

    # ── Mapping module ──────────────────────────────────────────

    def get_mapping_for_module(self, module_path: str) -> list[dict]:
        """Quelles assertions sont liées à ce module Python ?"""
        return self._fetchall(
            "SELECT * FROM sifrei_yesod_assertions WHERE %s = ANY(mapping_modules)",
            (module_path,),
        )

    # ── Consultation pour Hitbonenut ───────────────────────────

    def consult_for_hitbonenut(self, question: str) -> dict:
        """Retourne principes et assertions pertinents pour une question contemplée.

        Recherche sémantique via embedding cosine similarity dans les
        couches Peshat (assertions) et Sod (principes génératifs).

        Returns:
            {
                "principes": [top 3 principes avec similarity],
                "assertions": [top 5 assertions avec similarity],
                "concepts_lies": [concepts extraits des résultats]
            }
        """
        principes = self.search_principes(question, limit=3)
        assertions = self.search_assertions(question, limit=5)

        # Extraire les concepts liés depuis les assertions
        concepts_set: set[str] = set()
        for a in assertions:
            for c in (a.get("concepts") or []):
                if isinstance(c, dict) and c.get("id"):
                    concepts_set.add(c["id"])
                elif isinstance(c, str):
                    concepts_set.add(c)

        # Enrichir les concepts avec nom_he/nom_fr
        concepts_lies = []
        for cid in list(concepts_set)[:10]:
            concept = self._fetchone(
                "SELECT concept_id, nom_he, nom_fr, domaine FROM sifrei_yesod_concepts WHERE concept_id = %s",
                (cid,),
            )
            if concept:
                concepts_lies.append(concept)

        return {
            "principes": principes,
            "assertions": assertions,
            "concepts_lies": concepts_lies,
        }

    # ── Statistiques ────────────────────────────────────────────

    def stats(self) -> dict:
        """Statistiques : nb assertions, concepts, relations, principes par sefer."""
        global_stats = self._fetchone(
            """
            SELECT
                (SELECT COUNT(*) FROM sifrei_yesod_sefarim) AS sefarim,
                (SELECT COUNT(*) FROM sifrei_yesod_shaarim) AS shaarim,
                (SELECT COUNT(*) FROM sifrei_yesod_perakim) AS perakim,
                (SELECT COUNT(*) FROM sifrei_yesod_assertions) AS assertions,
                (SELECT COUNT(*) FROM sifrei_yesod_concepts) AS concepts,
                (SELECT COUNT(*) FROM sifrei_yesod_relations) AS relations,
                (SELECT COUNT(*) FROM sifrei_yesod_principes) AS principes,
                (SELECT COUNT(*) FROM sifrei_yesod_cross_refs) AS cross_refs
            """
        )

        per_sefer = self._fetchall(
            """
            SELECT
                p.sefer_id,
                COUNT(DISTINCT p.id) AS perakim,
                COUNT(DISTINCT a.id) AS assertions,
                COUNT(DISTINCT r.id) AS relations,
                COUNT(DISTINCT pr.id) AS principes
            FROM sifrei_yesod_perakim p
            LEFT JOIN sifrei_yesod_assertions a ON a.perek_id = p.id
            LEFT JOIN sifrei_yesod_relations r ON r.perek_id = p.id
            LEFT JOIN sifrei_yesod_principes pr ON pr.perek_id = p.id
            GROUP BY p.sefer_id
            """
        )

        return {"global": global_stats, "per_sefer": per_sefer}
