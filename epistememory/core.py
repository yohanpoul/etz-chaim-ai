"""EpisteMemory — Malkuth-de-Yesod : l'interface principale.

"Le Tzaddik est la fondation du monde" — Proverbes 10:25
Joseph stocke le blé avec discernement : provenance, confiance, temporalité.
"""

from __future__ import annotations

from uuid import UUID

from .db import Database
from .embedding import embed
from .models import EpistemicStatus, GCReport, MemoryEntry, MemoryStats, SourceSephirah


class EpisteMemory:
    """Interface principale — Malkuth de Yesod.

    Hitkalelut : l'acquisition (Chesed) et l'oubli (Gevurah)
    vivent dans le même composant. La mémoire se décrit elle-même (Hod).
    """

    def __init__(
        self,
        db_url: str = "postgresql://localhost/etz_chaim",
        embedding_model: str | None = None,
    ) -> None:
        self.db = Database(db_url)
        self.gematria = None  # GematriaEngine, injecté par init_tree
        if embedding_model is None:
            try:
                from olamot import get_embedding_model
                embedding_model = get_embedding_model()
            except Exception:
                embedding_model = "nomic-embed-text"
        self.embedding_model = embedding_model

    def close(self) -> None:
        self.db.close()

    # --- Chesed-de-Yesod : acquisition ---

    def remember(
        self,
        content: str,
        source_sephirah: str | SourceSephirah,
        confidence: float = 0.5,
        domain: str | None = None,
        tags: list[str] | None = None,
        ttl_days: int | None = None,
        source_detail: dict | None = None,
        supersedes: UUID | None = None,
        generate_embedding: bool = True,
    ) -> UUID:
        """Stocker une nouvelle entrée avec ses méta-données épistémiques.

        Chesed-de-Yesod : stocker généreusement, ne rien perdre.
        """
        if isinstance(source_sephirah, SourceSephirah):
            source_sephirah = source_sephirah.value

        embedding_vec = None
        if generate_embedding:
            # nomic-embed-text context ~8192 tokens ≈ 6000 chars safe limit
            embed_text = content[:6000] if len(content) > 6000 else content
            try:
                embedding_vec = embed(embed_text, model=self.embedding_model)
            except Exception:
                # Fail-safe : stocker sans embedding plutôt que perdre l'entrée
                pass

        # Determine initial epistemic status from confidence
        if confidence >= 0.9:
            status = EpistemicStatus.FACT.value
        elif confidence >= 0.7:
            status = EpistemicStatus.VERIFIED_ONCE.value
        else:
            status = EpistemicStatus.HYPOTHESIS.value

        entry_id = self.db.insert(
            content=content,
            embedding=embedding_vec,
            source_sephirah=source_sephirah,
            confidence=confidence,
            epistemic_status=status,
            domain=domain,
            tags=tags,
            ttl_days=ttl_days,
            source_detail=source_detail,
            supersedes=supersedes,
        )

        # ── Gématria opérative : indexer les termes hébreux ─────
        # Si le GematriaEngine est connecté, indexer automatiquement
        # les termes hébreux/kabbalistiques et détecter les équivalences.
        if self.gematria is not None:
            try:
                self.gematria.index_and_connect(content, source_entry_id=entry_id)
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Non bloquant — la mémoire prime sur l'indexation

        return entry_id

    # --- Chokmah-de-Yesod : recall avec intuition ---

    def recall(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        epistemic_status: list[str] | None = None,
        domain: str | None = None,
        include_contradictions: bool = True,
    ) -> list[MemoryEntry]:
        """Rechercher dans la mémoire avec filtres épistémiques.

        Chokmah-de-Yesod : trouver les connexions potentielles.
        """
        query_embedding = embed(query, model=self.embedding_model)

        results = self.db.search_by_embedding(
            query_embedding=query_embedding,
            limit=limit,
            min_confidence=min_confidence,
            epistemic_statuses=epistemic_status,
            domain=domain,
        )

        if include_contradictions:
            for entry in results:
                if entry.contradicts:
                    for cid in entry.contradicts:
                        contra = self.db.get(cid)
                        if contra and contra.epistemic_status != EpistemicStatus.DEPRECATED:
                            entry.warning = (
                                f"contested — contredit par {cid} "
                                f"(confidence: {contra.confidence})"
                            )

        return results

    def recall_hybrid(
        self,
        query: str,
        limit: int = 10,
        min_confidence: float = 0.0,
        epistemic_status: list[str] | None = None,
        domain: str | None = None,
        include_contradictions: bool = True,
    ) -> list[MemoryEntry]:
        """Recall enrichi par l'embedding hybride Cube + ML.

        Combine le recall sémantique standard avec les concepts
        structurellement liés dans le Cube de l'Espace. Les concepts
        détectés comme proches par le Cube mais éloignés en ML
        sont ajoutés comme pistes supplémentaires.
        """
        # Standard recall
        results = self.recall(
            query=query, limit=limit, min_confidence=min_confidence,
            epistemic_status=epistemic_status, domain=domain,
            include_contradictions=include_contradictions,
        )

        # Enrich with hybrid retrieval concepts as search expansion
        try:
            from kabbalah.hybrid_retrieval import HybridRetrieval
            retrieval = HybridRetrieval()
            hidden = retrieval.query(query, mode="hidden", top_k=5)

            # Use hidden concepts as additional search terms
            existing_ids = {r.id for r in results}
            for h in hidden:
                expanded = self.recall(
                    query=h.concept, limit=3,
                    min_confidence=min_confidence,
                    epistemic_status=epistemic_status,
                    domain=domain,
                    include_contradictions=include_contradictions,
                )
                for entry in expanded:
                    if entry.id not in existing_ids:
                        entry.warning = (
                            f"via cube_hidden: {h.concept} "
                            f"(gap={h.gap:.3f})"
                        )
                        results.append(entry)
                        existing_ids.add(entry.id)

                        if len(results) >= limit * 2:
                            break
                if len(results) >= limit * 2:
                    break
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # Graceful degradation — standard recall still works

        return results[:limit * 2]

    def get(self, entry_id: UUID) -> MemoryEntry | None:
        """Récupérer une entrée par ID."""
        return self.db.get(entry_id)

    # --- Tiferet-de-Yesod : gestion des contradictions ---

    def contradict(
        self, entry_id: UUID, contradicting_id: UUID, reason: str | None = None
    ) -> None:
        """Marquer deux entrées comme se contredisant.

        Tiferet-de-Yesod : ne pas résoudre, mais LIER et noter la tension.
        """
        self.db.add_contradiction(entry_id, contradicting_id)

    def support(self, entry_id: UUID, supporting_id: UUID) -> None:
        """Marquer une entrée comme soutenant une autre."""
        self.db.add_support(entry_id, supporting_id)

    # --- Gevurah-de-Yesod : validation et oubli ---

    def verify(self, entry_id: UUID, verification_source: str) -> None:
        """Augmenter la confiance d'une entrée après vérification."""
        self.db.verify(entry_id, verification_source)

    def deprecate(self, entry_id: UUID, superseded_by: UUID | None = None) -> None:
        """Marquer une entrée comme obsolète."""
        self.db.deprecate(entry_id, superseded_by)

    def mature(self, max_per_level: int = 50) -> dict:
        """Yesod maturation — promotion automatique des mémoires mûres."""
        return self.db.mature(max_per_level=max_per_level)

    def gc(self) -> GCReport:
        """Gevurah-de-Yesod : garbage collection des entrées périmées."""
        return self.db.gc(remove_expired=True, remove_deprecated=False)

    # --- Diagnostic Qliphothique : Lilit ---

    def self_diagnose(self) -> dict:
        """Auto-diagnostic — les 4 niveaux de Lilit.

        Lilit est la Qliphah de Yesod — la séductrice, l'illusion,
        les faux souvenirs, la mémoire trompeuse.

          Nogah  : faux souvenirs confiants (haute confiance + contested)
          Ruach  : hypothèses stagnantes (accédées mais jamais vérifiées)
          Anan   : mémoire parasitaire (entries inutilisées qui polluent)
          Mamash : illusion de connaissance (faits sans vérification réelle)
        """
        stats = self.introspect()
        if stats.total_entries == 0:
            return {"level": "healthy", "issues": []}

        issues: list[str] = []

        # ── Nogah : faux souvenirs confiants ──────────────────
        confident_contested = self.db.count_confident_contested(min_confidence=0.7)
        if confident_contested > 0:
            issues.append(
                f"Lilit-Nogah: {confident_contested} entrée(s) avec confiance >= 0.7 "
                "mais statut 'contested' — faux souvenirs séduisants"
            )

        # ── Ruach : hypothèses stagnantes ─────────────────────
        stagnant = self.db.count_stagnant_hypotheses(min_access=3)
        if stagnant > 0:
            issues.append(
                f"Lilit-Ruach: {stagnant} hypothèse(s) accédée(s) >= 3 fois "
                "mais jamais vérifiée(s) — séduction mémorielle"
            )

        # ── Anan : mémoire parasitaire ────────────────────────
        never_accessed = self.db.count_never_accessed()
        if stats.active_entries > 5 and never_accessed / stats.active_entries > 0.5:
            issues.append(
                f"Lilit-Anan: {never_accessed}/{stats.active_entries} entrées actives "
                "jamais accédées — mémoire parasitaire, bruit > signal"
            )

        # ── Mamash : illusion de connaissance ─────────────────
        unverified_facts = self.db.count_unverified_facts()
        if unverified_facts > 0:
            issues.append(
                f"Lilit-Mamash: {unverified_facts} 'fact(s)' sans aucune vérification "
                "dans source_detail — illusion de connaissance"
            )

        # Déterminer le niveau (Mamash > Anan > Ruach > Nogah)
        if not issues:
            level = "healthy"
        elif any("Mamash" in i for i in issues):
            level = "mamash"
        elif any("Anan" in i for i in issues):
            level = "anan"
        elif any("Ruach" in i for i in issues):
            level = "ruach"
        else:
            level = "nogah"

        return {"level": level, "issues": issues}

    # --- Hod-de-Yesod : introspection ---

    def introspect(self) -> MemoryStats:
        """Hod-de-Yesod : la mémoire se décrit elle-même.

        Retourne stats, couverture, gaps, contradictions ouvertes.
        """
        return self.db.stats()
