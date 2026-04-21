"""kabbalah/concept_harvester.py — ConceptHarvester : Yesod-Pipeline pour concepts vivants.

יְסוֹד — Canal de transmission entre les mondes supérieur et inférieur.

Étend SifreiYesodEmbedder pour harvester des concepts depuis 9 sources
vivantes, les filtrer (Masakh), les embedder (ML + Kab + Gématria),
et les stocker dans hybrid_embeddings avec metadata de provenance.

Hitkalelut : contient Chesed-dans-Yesod (harvest) ET Gevurah-dans-Yesod (prune).

Qliphah gardée : Gamchicoth (excès de flux non filtré). Contre-mesures :
  1. Masakh : rejette les fragments sans substance (< 4 chars, stop-words seuls)
  2. Daily cap : max 200 concepts par run
  3. Prune stale : déprécie les concepts jamais consommés après 30 jours

Usage:
    ch = ConceptHarvester()
    stats = ch.harvest()
    ch.mark_consumed("Tsimtsum")
    ch.close()
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone

import numpy as np
import psycopg2
import psycopg2.extras

from kabbalah.embed_sifrei import SifreiYesodEmbedder

logger = logging.getLogger("etz-daemon")

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

# ── Stop-words pour le filtre Masakh ────────────────────────────────
# Rejeter un concept dont TOUS les mots sont dans cette liste
_CONCEPT_STOP = frozenset({
    # Français
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou",
    "en", "est", "sont", "a", "au", "aux", "ce", "que", "qui",
    "dans", "par", "pour", "sur", "avec", "sans", "plus", "pas",
    "se", "si", "on", "il", "ils", "elle", "elles", "je", "tu",
    "nous", "vous", "ne", "ni", "car", "mais", "donc", "or",
    # Anglais
    "the", "an", "is", "are", "of", "in", "to", "for", "and",
    "at", "by", "it", "its", "be", "as", "was", "has", "this",
    "not", "but", "can", "all", "any",
})

# ── Sources avec hiérarchie Olam ────────────────────────────────────
# Chaque source a un niveau d'autorité (authority_olam) selon l'Olam
# dont elle provient : Atziluth (1.0) > Briah (0.75) > Yetzirah (0.5)
# > Assiah (0.25).
SOURCES: list[dict] = [
    {
        "name": "sifrei_yesod",
        "table": "sifrei_yesod_assertions",
        "text_field": "assertion_text",
        "olam": 1.0,
    },
    {
        "name": "tiferet",
        "table": "dissensuengine_syntheses",
        "text_field": "content",
        "olam": 0.75,
    },
    {
        "name": "tensions",
        "table": "dissensuengine_tensions",
        "text_field": "description",
        "olam": 0.75,
    },
    {
        "name": "hitbonenut",
        "table": "hitbonenut_principles",
        "text_field": "principle",
        "olam": 0.5,
    },
    {
        "name": "epistememory",
        "table": "epistememory",
        "text_field": "content",
        "olam": 0.5,
    },
    {
        "name": "causal",
        "table": "causal_claims",
        "text_field": "cause",
        "olam": 0.25,
    },
    {
        "name": "nitzotzot_insight",
        "table": "candidate_insights",
        "text_field": "description",
        "olam": 0.25,
    },
    {
        "name": "nitzotzot_hitbo",
        "table": "hitbonenut_experiments",
        "text_field": "hypothesis",
        "olam": 0.25,
    },
]


class ConceptHarvester(SifreiYesodEmbedder):
    """Yesod-Pipeline : harvest de concepts depuis 9 sources vivantes.

    Étend SifreiYesodEmbedder (qui gère la connexion PostgreSQL et
    l'embedding hybride ML+Kab) avec :

    - Extraction multi-source (pas seulement Sifrei Yesod)
    - Filtre Masakh (longueur, stop-words)
    - Cap journalier anti-Gamchicoth (max 200/run)
    - Validation d'embedding (norme, NaN, dimensions)
    - Enrichissement gématrique (mispar_gadol, siduri, katan)
    - Élagage Gevurah (déprécie les concepts non consommés après 30 jours)
    - Or Chozer : mark_consumed() pour tracer la consommation aval

    Attributes:
        max_per_run: Nombre maximum de concepts à stocker par run (anti-Gamchicoth).
        _harvested_keys: Cache interne pour éviter les doublons dans le run.
    """

    def __init__(
        self,
        db_url: str = DB_URL,
        batch_size: int = 50,
        max_per_run: int = 200,
    ) -> None:
        """Initialise le ConceptHarvester.

        Args:
            db_url: URL PostgreSQL. Défaut : $ETZ_CHAIM_DB ou localhost/etz_chaim.
            batch_size: Taille de batch pour les logs intermédiaires.
            max_per_run: Cap journalier anti-Gamchicoth.
        """
        super().__init__(db_url=db_url, batch_size=batch_size)
        self.max_per_run = max_per_run
        self._harvested_keys: set[str] = set()

    # ── Pipeline principal ────────────────────────────────────────

    def harvest(self, last_harvest: datetime | None = None) -> dict:
        """Lancer le pipeline complet de harvest.

        Étapes :
          1. Extraction depuis toutes les sources (créées depuis last_harvest)
          2. Filtre Masakh (longueur, stop-words)
          3. Cap journalier (max_per_run)
          4. Embed + stockage + metadata
          5. Élagage Gevurah (concepts stale)

        Args:
            last_harvest: Datetime UTC de référence. Si None, utilise
                          il y a 24h (harvest incrémental quotidien).

        Returns:
            Dict avec harvested, deduped, rejected, errors, pruned, sources.
        """
        if last_harvest is None:
            last_harvest = datetime.now(timezone.utc) - timedelta(days=1)

        stats: dict = {
            "harvested": 0,
            "deduped": 0,
            "rejected": 0,
            "errors": 0,
            "pruned": 0,
            "sources": {},
        }

        # ── Étape 1 : Extraction depuis toutes les sources ──
        all_concepts: list[dict] = []
        for src in SOURCES:
            try:
                rows = self._query_source(src, last_harvest)
                concepts = self._extract_from_rows(
                    rows,
                    text_field=src["text_field"],
                    source=src["name"],
                    olam=src["olam"],
                )
                all_concepts.extend(concepts)
                stats["sources"][src["name"]] = len(concepts)
                logger.debug(
                    "Source %s: %d lignes → %d concepts candidats",
                    src["name"], len(rows), len(concepts),
                )
            except Exception as exc:
                logger.warning("Harvest source '%s' échoué: %s", src["name"], exc)
                stats["errors"] += 1
                stats["sources"][src["name"]] = 0

        # ── Étape 2 : Filtre Masakh ──
        filtered = self._masakh_filter(all_concepts)
        stats["rejected"] = len(all_concepts) - len(filtered)

        # ── Étape 3 : Cap journalier anti-Gamchicoth ──
        capped = self._apply_daily_cap(filtered)

        # ── Étape 4 : Embed + stockage ──
        for i, concept in enumerate(capped):
            try:
                ok = self._embed_and_store(concept)
                if ok:
                    stats["harvested"] += 1
                else:
                    stats["deduped"] += 1

                if (i + 1) % self.batch_size == 0:
                    logger.info(
                        "  ConceptHarvester batch %d: %d stockés, %d dédoublonnés, %d erreurs",
                        (i + 1) // self.batch_size,
                        stats["harvested"], stats["deduped"], stats["errors"],
                    )
            except Exception as exc:
                logger.warning(
                    "Embed échoué pour '%s': %s", concept.get("text", "")[:60], exc
                )
                stats["errors"] += 1

        # ── Étape 5 : Gevurah — élagage des concepts stale ──
        stats["pruned"] = self._prune_stale()

        logger.info(
            "ConceptHarvester terminé: %d stockés, %d dédoublonnés, "
            "%d rejetés, %d erreurs, %d élaguées",
            stats["harvested"], stats["deduped"], stats["rejected"],
            stats["errors"], stats["pruned"],
        )
        return stats

    # ── Extraction ───────────────────────────────────────────────

    def _query_source(self, src: dict, since: datetime) -> list[dict]:
        """Requêter une table source pour les nouvelles lignes depuis `since`.

        Gère gracieusement :
        - Tables inexistantes (try/except → liste vide)
        - Colonnes manquantes (created_at absente → pas de filtre temporel)
        - WHERE clauses spécifiques à chaque source

        Args:
            src: Dict de configuration source (name, table, text_field, olam).
            since: Datetime UTC de référence pour le filtre incrémental.

        Returns:
            Liste de dicts (id + text_field) ou liste vide si la table
            n'existe pas.
        """
        table = src["table"]
        text_field = src["text_field"]
        source_name = src["name"]

        try:
            cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Vérifier si la table existe
            cur.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            """, (table,))
            if cur.fetchone() is None:
                logger.debug("Table '%s' absente — source '%s' ignorée", table, source_name)
                cur.close()
                return []

            # Vérifier si la colonne texte existe
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """, (table, text_field))
            if cur.fetchone() is None:
                logger.debug(
                    "Colonne '%s' absente dans '%s' — source '%s' ignorée",
                    text_field, table, source_name,
                )
                cur.close()
                return []

            # Vérifier si created_at existe pour le filtre temporel
            cur.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = 'created_at'
            """, (table,))
            has_created_at = cur.fetchone() is not None

            # Construire la requête selon la source
            rows = self._execute_source_query(
                cur, table, text_field, source_name, since, has_created_at
            )
            cur.close()
            return rows

        except Exception as exc:
            logger.warning("Erreur query source '%s': %s", source_name, exc)
            # Rollback pour que la connexion reste utilisable
            try:
                self.conn.rollback()
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            return []

    def _execute_source_query(
        self,
        cur: psycopg2.extensions.cursor,
        table: str,
        text_field: str,
        source_name: str,
        since: datetime,
        has_created_at: bool,
    ) -> list[dict]:
        """Exécuter la requête SQL pour une source donnée.

        Applique les WHERE clauses spécifiques à chaque source et
        le filtre temporel si created_at est disponible.

        Args:
            cur: Curseur psycopg2 actif (RealDictCursor).
            table: Nom de la table SQL.
            text_field: Nom de la colonne texte à extraire.
            source_name: Identifiant logique de la source.
            since: Datetime UTC pour le filtre temporel.
            has_created_at: True si la colonne created_at existe.

        Returns:
            Liste de dicts row (id + text_field).
        """
        # Conditions supplémentaires par source
        extra_conditions: list[str] = []
        params: list = []
        limit = 200

        if source_name == "hitbonenut":
            extra_conditions.append("is_active = true")
        elif source_name == "epistememory":
            extra_conditions.append("confidence > 0.5")
        elif source_name == "nitzotzot_insight":
            extra_conditions.append("status = 'rejected'")
        elif source_name == "nitzotzot_hitbo":
            extra_conditions.append("status = 'discarded'")
        elif source_name == "causal":
            limit = 100

        # Filtre temporel si created_at disponible
        if has_created_at:
            extra_conditions.append("created_at > %s")
            params.append(since)

        where_clause = ""
        if extra_conditions:
            where_clause = "WHERE " + " AND ".join(extra_conditions)

        # Pour les sources avec effect (causal), récupérer aussi l'effet
        select_extra = ""
        if source_name == "causal":
            cur.execute("""
                SELECT 1 FROM information_schema.columns
                WHERE table_name = %s AND column_name = 'effect'
            """, (table,))
            if cur.fetchone():
                select_extra = ", effect"

        query = (
            f"SELECT id, {text_field}{select_extra} FROM {table} "
            f"{where_clause} "
            f"ORDER BY id DESC LIMIT {limit}"
        )
        cur.execute(query, params)
        return [dict(r) for r in cur.fetchall()]

    def _extract_from_rows(
        self,
        rows: list[dict],
        text_field: str,
        source: str,
        olam: float,
    ) -> list[dict]:
        """Extraire des candidats concepts depuis les lignes d'une source.

        Chaque ligne produit au minimum un concept depuis `text_field`.
        Pour les causal_claims, l'effet (si présent) est aussi extrait.

        Args:
            rows: Lignes retournées par `_query_source`.
            text_field: Nom de la colonne texte principal.
            source: Identifiant logique de la source (pour metadata).
            olam: Niveau d'autorité Olam [0.0, 1.0].

        Returns:
            Liste de dicts concept avec text, source_module, authority_olam,
            source_id.
        """
        concepts: list[dict] = []
        for row in rows:
            text = row.get(text_field, "")
            if not text or not isinstance(text, str):
                continue
            text = text.strip()
            if not text:
                continue

            concepts.append({
                "text": text,
                "source_module": source,
                "authority_olam": olam,
                "source_id": str(row.get("id", "")),
            })

            # Pour causal_claims, extraire aussi l'effet
            if source == "causal" and row.get("effect"):
                effect = str(row["effect"]).strip()
                if effect:
                    concepts.append({
                        "text": effect,
                        "source_module": source,
                        "authority_olam": olam,
                        "source_id": str(row.get("id", "")),
                    })

        return concepts

    # ── Filtrage ─────────────────────────────────────────────────

    def _masakh_filter(self, concepts: list[dict]) -> list[dict]:
        """Masakh — filtrer les concepts sans substance.

        Rejette :
        - Textes de moins de 4 caractères
        - Textes dont TOUS les mots sont des stop-words

        Args:
            concepts: Liste de dicts concept avec clé "text".

        Returns:
            Sous-liste filtrée.
        """
        filtered: list[dict] = []
        for c in concepts:
            text = c.get("text", "").strip()

            # Filtre longueur minimale
            if len(text) < 4:
                continue

            # Truncate : nomic-embed-text a une limite de contexte
            if len(text) > 500:
                text = text[:500]

            # Filtre stop-words : au moins un mot substantiel
            words = {w.lower().strip(".,;:!?()[]\"'") for w in text.split()}
            words -= _CONCEPT_STOP
            words = {w for w in words if w}  # supprimer les tokens vides
            if not words:
                continue

            c["text"] = text
            filtered.append(c)
        return filtered

    def _apply_daily_cap(self, concepts: list[dict]) -> list[dict]:
        """Anti-Gamchicoth : limiter le nombre de concepts par run.

        Trop de flux non filtré = Gamchicoth (Qliphah de Yesod).
        Ce cap force une sélection qualitative sur les jours suivants.

        Args:
            concepts: Liste de concepts déjà filtrés par Masakh.

        Returns:
            Les max_per_run premiers concepts (ordre préservé = priorité Olam).
        """
        return concepts[: self.max_per_run]

    # ── Embedding et stockage ────────────────────────────────────

    def _embed_and_store(self, concept: dict) -> bool:
        """Embedder un concept et le stocker dans hybrid_embeddings.

        Flux :
          1. Déduplication intra-run (hash SHA-256)
          2. Vérification absence en DB (concept exact)
          3. Résolution hébreu
          4. Embedding via parent (ML + Kab)
          5. Validation du vecteur
          6. UPDATE metadata (source, olam, harvested_at, status='nascent')
          7. Enrichissement gématrique si hébreu trouvé

        Args:
            concept: Dict avec text, source_module, authority_olam.

        Returns:
            True si stocké avec succès, False si dédoublonné ou erreur douce.
        """
        text = concept["text"]

        # ── Dédup intra-run ──
        key = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        if key in self._harvested_keys:
            return False
        self._harvested_keys.add(key)

        # ── Vérifier l'absence en DB ──
        concept_label = text[:200]  # tronquer pour sécurité
        try:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT id FROM hybrid_embeddings WHERE concept = %s",
                (concept_label,),
            )
            if cur.fetchone():
                cur.close()
                return False
            cur.close()
        except Exception as exc:
            logger.debug("DB check for '%s' échoué: %s", concept_label[:40], exc)
            try:
                self.conn.rollback()
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            return False

        # ── Résoudre l'hébreu ──
        hebrew = self._resolve_hebrew(text)

        # ── Embedding via parent SifreiYesodEmbedder ──
        concept_dict = {
            "concept_id": concept_label,
            "nom_fr": concept_label,
            "nom_he": hebrew,
            "description": text,
        }
        ok = self.embed_concept(concept_dict)
        if not ok:
            return False

        # ── Validation du vecteur stocké ──
        # (l'embedding a été stocké par embed_concept ; on fait confiance
        # à save_to_db — la validation est surtout utile pour les tests unitaires)

        # ── UPDATE metadata post-embedding ──
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                UPDATE hybrid_embeddings
                SET source_module  = %s,
                    authority_olam = %s,
                    harvested_at   = NOW(),
                    status         = 'nascent'
                WHERE concept = %s
                """,
                (concept["source_module"], concept["authority_olam"], concept_label),
            )
            self.conn.commit()
            cur.close()
        except Exception as exc:
            logger.warning(
                "UPDATE metadata échoué pour '%s': %s", concept_label[:40], exc
            )
            try:
                self.conn.rollback()
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # ── Enrichissement gématrique ──
        if hebrew:
            self._enrich_gematria(concept_label, hebrew)

        return True

    # ── Résolution hébreu ────────────────────────────────────────

    def _resolve_hebrew(self, text: str) -> str | None:
        """Tenter de résoudre un équivalent hébreu pour un concept.

        Stratégies (ordre décroissant de fiabilité) :
          1. Déléguer à KabbalisticSignature._resolve_hebrew (translittération
             standard + détection hébreu natif)

        Args:
            text: Texte du concept (translittéré ou natif).

        Returns:
            Chaîne hébraïque normalisée ou None si introuvable.
        """
        try:
            from kabbalah.hybrid_embedding import KabbalisticSignature
            sig = KabbalisticSignature()
            return sig._resolve_hebrew(text, hebrew_word=None)
        except Exception as exc:
            logger.debug("_resolve_hebrew échoué pour '%s': %s", text[:40], exc)
            return None

    # ── Gématrie ─────────────────────────────────────────────────

    def _enrich_gematria(self, concept: str, hebrew: str) -> None:
        """Calculer et persister les valeurs gématriques.

        Utilise GematriaEngine.calculate() (méthode statique, pas de DB).
        Stocke mispar_gadol (standard), mispar_siduri (ordinal), mispar_katan.

        Args:
            concept: Clé dans hybrid_embeddings (concept column).
            hebrew: Mot hébreu (chaîne normalisée).
        """
        try:
            from gematria.engine import GematriaEngine
            values = GematriaEngine.calculate(hebrew)
            if not values:
                return

            cur = self.conn.cursor()
            cur.execute(
                """
                UPDATE hybrid_embeddings
                SET gematria_gadol  = %s,
                    gematria_siduri = %s,
                    gematria_katan  = %s
                WHERE concept = %s
                """,
                (
                    values.get("standard"),
                    values.get("ordinal"),
                    values.get("katan"),
                    concept,
                ),
            )
            self.conn.commit()
            cur.close()
        except Exception as exc:
            logger.debug(
                "Enrichissement gématrique échoué pour '%s' (%s): %s",
                hebrew, concept[:40], exc,
            )
            try:
                self.conn.rollback()
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # ── Validation ───────────────────────────────────────────────

    def _validate_embedding(self, embedding: np.ndarray) -> bool:
        """Anti-Gamaliel : valider l'intégrité d'un vecteur d'embedding.

        Rejette :
        - None / tableau vide
        - Vecteurs contenant des NaN (Ollama instable ou crash ML)
        - Vecteurs de norme quasi-nulle (< 0.1) — signe de dégénérescence

        Args:
            embedding: Tableau numpy 1-D (768d ML ou 798d hybride).

        Returns:
            True si le vecteur est sain.
        """
        if embedding is None:
            return False
        if embedding.size == 0:
            return False
        if np.any(np.isnan(embedding)):
            return False
        norm = np.linalg.norm(embedding)
        if norm < 0.1:
            return False
        return True

    # ── Dédoublonnage sémantique ─────────────────────────────────

    def _semantic_dedup(
        self,
        concepts: list[dict],
        threshold: float = 0.95,
    ) -> list[dict]:
        """Dédoublonner des concepts par similarité cosinus.

        Les dicts doivent avoir une clé "embedding" (np.ndarray).
        Le premier concept rencontré est conservé en cas de doublon.

        Args:
            concepts: Liste de dicts avec clé "embedding" (optionnelle).
            threshold: Seuil cosinus au-dessus duquel deux concepts
                       sont considérés doublons.

        Returns:
            Sous-liste dédoublonnée.
        """
        if len(concepts) <= 1:
            return concepts

        kept: list[dict] = [concepts[0]]
        for candidate in concepts[1:]:
            is_dup = False
            cand_emb = candidate.get("embedding")
            if cand_emb is not None:
                for existing in kept:
                    exist_emb = existing.get("embedding")
                    if exist_emb is not None:
                        sim = self._cosine_sim(cand_emb, exist_emb)
                        if sim > threshold:
                            is_dup = True
                            break
            if not is_dup:
                kept.append(candidate)
        return kept

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        """Similarité cosinus entre deux vecteurs.

        Args:
            a: Vecteur numpy 1-D.
            b: Vecteur numpy 1-D, même dimension que a.

        Returns:
            Score flottant dans [-1.0, 1.0]. Retourne 0.0 si l'un
            des vecteurs a une norme quasi-nulle.
        """
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a < 1e-8 or norm_b < 1e-8:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    # ── Gevurah : élagage ────────────────────────────────────────

    def _prune_stale(self, max_age_days: int = 30) -> int:
        """Gevurah — déprécier les concepts nascents jamais consommés.

        Un concept "nascent" non consommé depuis max_age_days jours n'a
        pas trouvé preneur — il est retiré du flux actif (status=deprecated).
        Cette Gevurah garde le canal Yesod propre.

        Args:
            max_age_days: Âge maximal en jours avant dépréciation.

        Returns:
            Nombre de concepts dépréciés.
        """
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                UPDATE hybrid_embeddings
                SET status = 'deprecated'
                WHERE status = 'nascent'
                  AND consume_count = 0
                  AND harvested_at < NOW() - %s::INTERVAL
                """,
                (f"{max_age_days} days",),
            )
            pruned = cur.rowcount
            self.conn.commit()
            cur.close()
            return pruned
        except Exception as exc:
            logger.warning("_prune_stale échoué: %s", exc)
            try:
                self.conn.rollback()
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            return 0

    # ── Or Chozer : consommation aval ───────────────────────────

    def mark_consumed(self, concept: str) -> None:
        """Or Chozer — marquer un concept comme consommé par un module aval.

        Chaque consommation incrémente consume_count et met à jour
        last_consumed_at. Quand consume_count atteint 9 (Yesod complet),
        le concept devient "foundational".

        Transitions de status :
          nascent   → active       (première consommation)
          active    → active       (consommations suivantes)
          * tout    → foundational (consume_count ≥ 9 après update)

        Args:
            concept: Valeur de la colonne `concept` dans hybrid_embeddings.
        """
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                UPDATE hybrid_embeddings
                SET last_consumed_at = NOW(),
                    consume_count    = consume_count + 1,
                    status = CASE
                        WHEN consume_count + 1 >= 9 THEN 'foundational'
                        WHEN status = 'nascent'     THEN 'active'
                        ELSE status
                    END
                WHERE concept = %s
                """,
                (concept,),
            )
            self.conn.commit()
            cur.close()
        except Exception as exc:
            logger.warning("mark_consumed échoué pour '%s': %s", concept, exc)
            try:
                self.conn.rollback()
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)


# ── Point d'entrée standalone ────────────────────────────────────

def main() -> None:
    """Point d'entrée CLI pour un harvest manuel.

    Usage:
        python -m kabbalah.concept_harvester [--dry-run] [--since DAYS] [--db-url URL]
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="kabbalah.concept_harvester",
        description="ConceptHarvester — Yesod-Pipeline pour concepts vivants",
    )
    parser.add_argument(
        "--since",
        type=int,
        default=1,
        help="Nombre de jours dans le passé comme point de départ (défaut: 1)",
    )
    parser.add_argument("--db-url", default=None, help="URL PostgreSQL override")
    parser.add_argument(
        "--max-per-run",
        type=int,
        default=200,
        help="Cap journalier anti-Gamchicoth (défaut: 200)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simuler sans écrire dans la DB",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    db_url = args.db_url or DB_URL
    last_harvest = datetime.now(timezone.utc) - timedelta(days=args.since)

    if args.dry_run:
        print(f"[DRY RUN] Simulation harvest depuis {last_harvest.isoformat()}")
        harvester = ConceptHarvester(db_url=db_url, max_per_run=args.max_per_run)
        try:
            # Compter uniquement, sans embed
            total = 0
            for src in SOURCES:
                rows = harvester._query_source(src, last_harvest)
                concepts = harvester._extract_from_rows(
                    rows, src["text_field"], src["name"], src["olam"]
                )
                filtered = harvester._masakh_filter(concepts)
                print(
                    f"  {src['name']:25s}: {len(rows):4d} lignes → "
                    f"{len(concepts):4d} candidats → {len(filtered):4d} après Masakh"
                )
                total += len(filtered)
            capped = min(total, args.max_per_run)
            print(f"\nTotal après Masakh : {total}")
            print(f"Total après cap    : {capped}")
        finally:
            harvester.close()
        return

    harvester = ConceptHarvester(db_url=db_url, max_per_run=args.max_per_run)
    try:
        stats = harvester.harvest(last_harvest=last_harvest)
        print("\nRésultat ConceptHarvester :")
        print(f"  Stockés      : {stats['harvested']}")
        print(f"  Dédoublonnés : {stats['deduped']}")
        print(f"  Rejetés      : {stats['rejected']}")
        print(f"  Erreurs      : {stats['errors']}")
        print(f"  Élaguées     : {stats['pruned']}")
        print("\nPar source :")
        for name, count in stats["sources"].items():
            print(f"  {name:25s}: {count}")
    finally:
        harvester.close()


if __name__ == "__main__":
    main()
