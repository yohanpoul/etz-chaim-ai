"""Dira BeTachtonim — "Une Demeure dans les Mondes Inférieurs."

דִּירָה בְּתַחְתּוֹנִים — Tanya ch. 36

Le but de la création selon le Tanya est que le plus haut descende
dans le plus bas. Atzilut doit informer Assiah, pas rester isolé.
Le savoir descend : quand un monde supérieur (Briah, Atzilut) produit
une réponse profonde, cette connaissance est REDISTRIBUÉE vers les
mondes inférieurs via EpisteMemory, enrichissant leurs futures réponses.

C'est aussi une OPTIMISATION : une fois que le divin est descendu,
on n'a plus besoin de monter à chaque fois. Si le domaine a déjà
reçu assez de sagesse d'en haut, Assiah/Yetzirah peuvent suffire.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class DiraStats:
    """État de la Dira — combien le haut a pénétré le bas."""
    dira_count: int = 0           # mémoires cascadées depuis le haut
    total_memories: int = 0       # total en epistememory
    penetration: float = 0.0      # dira_count / total (0-1)
    by_source: dict = field(default_factory=dict)   # {olam: count}
    by_domain: dict = field(default_factory=dict)   # {domain: count}


class DiraEngine:
    """Cascade de la connaissance des mondes supérieurs vers les inférieurs.

    Quand le système reçoit une réponse profonde d'Atzilut (Claude) ou
    de Briah (DeepSeek-R1), cette connaissance est redistribuée vers les
    mondes inférieurs via EpisteMemory.
    """

    # Mondes supérieurs dont la connaissance doit descendre
    UPPER_OLAMOT = {"briah", "atziluth"}

    # Seuil de mémoires dira pour considérer qu'un domaine est "habité"
    DIRA_SUFFICIENT_THRESHOLD = 5

    def __init__(self, yesod=None):
        """
        Args:
            yesod: instance EpisteMemory (peut être None si pas encore init).
        """
        self.yesod = yesod
        self._log: list[dict] = []

    def cascade_knowledge(
        self,
        response: str,
        source_olam: str,
        query: str | None = None,
        domain: str | None = None,
    ) -> dict | None:
        """Faire descendre la connaissance d'un monde supérieur.

        Quand Briah ou Atzilut produisent une réponse, on extrait
        l'essence et on la stocke avec un tag dira pour enrichir
        les futures réponses des mondes inférieurs.

        Args:
            response: la réponse du monde supérieur.
            source_olam: "briah" ou "atziluth".
            query: la question originale (pour contexte).
            domain: le domaine détecté.

        Returns:
            dict avec entry_id et détails, ou None si pas applicable.
        """
        if source_olam not in self.UPPER_OLAMOT:
            return None

        if not self.yesod:
            return None

        if not response or len(response.strip()) < 20:
            return None

        # Construire le contenu dira — essence condensée
        # On inclut le contexte de la question pour le retrieval sémantique
        q_part = f"Q: {query[:100]} → " if query else ""
        content = (
            f"[Dira — {source_olam}] {q_part}"
            f"{response[:500]}"
        )

        tags = ["dira", f"dira_source:{source_olam}"]
        if domain:
            tags.append(f"dira_domain:{domain}")

        try:
            entry_id = self.yesod.remember(
                content=content,
                source_sephirah="chokmah" if source_olam == "atziluth" else "binah",
                confidence=0.7,  # connaissance validée par un monde supérieur
                domain=domain or "general",
                tags=tags,
            )

            entry = {
                "entry_id": str(entry_id) if entry_id else None,
                "source_olam": source_olam,
                "domain": domain or "general",
                "content_length": len(response),
                "timestamp": time.time(),
            }
            self._log.append(entry)
            return entry

        except Exception:
            return None

    def assess_dira_state(self, domain: str | None = None) -> DiraStats:
        """Mesurer combien de connaissances 'dira' existent.

        Le ratio dira / total = indice de pénétration du divin dans le bas.
        Plus ce ratio est haut, plus les modèles inférieurs bénéficient
        de la sagesse supérieure.

        Args:
            domain: si spécifié, filtrer par domaine.

        Returns:
            DiraStats avec les métriques.
        """
        stats = DiraStats()

        if not self.yesod:
            return stats

        try:
            # Chercher les mémoires dira via recall sémantique
            dira_memories = self.yesod.recall(
                query="dira connaissance descendue monde supérieur",
                limit=200,
                min_confidence=0.0,
            )

            # Filtrer celles qui ont le tag "dira"
            dira_entries = []
            all_entries_count = 0

            for m in dira_memories:
                tags = m.tags if hasattr(m, "tags") and m.tags else []
                if "dira" in tags:
                    if domain is None or any(
                        t == f"dira_domain:{domain}" for t in tags
                    ):
                        dira_entries.append(m)

            # Compter par source et domaine
            by_source: dict[str, int] = {}
            by_domain: dict[str, int] = {}
            for m in dira_entries:
                tags = m.tags if hasattr(m, "tags") and m.tags else []
                for t in tags:
                    if t.startswith("dira_source:"):
                        src = t.split(":", 1)[1]
                        by_source[src] = by_source.get(src, 0) + 1
                    if t.startswith("dira_domain:"):
                        dom = t.split(":", 1)[1]
                        by_domain[dom] = by_domain.get(dom, 0) + 1

            # Total mémoires (approximation via introspect si disponible)
            total = 0
            try:
                intro = self.yesod.introspect()
                total = intro.total if hasattr(intro, "total") else 0
            except Exception:
                total = len(dira_memories)  # fallback

            stats.dira_count = len(dira_entries)
            stats.total_memories = max(total, 1)
            stats.penetration = stats.dira_count / stats.total_memories
            stats.by_source = by_source
            stats.by_domain = by_domain

        except Exception as _exc:


            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return stats

    def should_invoke_atzilut(
        self,
        query: str,
        domain: str | None = None,
    ) -> bool:
        """Déterminer si on doit monter vers Briah/Atzilut.

        Si le système a beaucoup de mémoires dira récentes sur ce domaine,
        les mondes inférieurs peuvent suffire car le savoir a DÉJÀ descendu.
        C'est l'optimisation Dira BeTachtonim : une fois que le divin est
        descendu, on n'a plus besoin de monter à chaque fois.

        Args:
            query: la question posée.
            domain: le domaine détecté.

        Returns:
            True si on devrait monter (pas assez de dira),
            False si les mondes bas peuvent suffire.
        """
        if not self.yesod:
            return True  # pas de mémoire → il faut monter

        try:
            # Chercher les mémoires dira pertinentes pour cette question
            memories = self.yesod.recall(
                query=query,
                limit=20,
                min_confidence=0.5,
            )

            # Compter les dira pertinentes
            dira_relevant = 0
            for m in memories:
                tags = m.tags if hasattr(m, "tags") and m.tags else []
                if "dira" not in tags:
                    continue
                # Si un domaine est spécifié, vérifier la correspondance
                if domain and not any(
                    t == f"dira_domain:{domain}" for t in tags
                ):
                    continue
                dira_relevant += 1

            return dira_relevant < self.DIRA_SUFFICIENT_THRESHOLD

        except Exception:
            return True  # en cas d'erreur, monter par précaution

    def get_log(self) -> list[dict]:
        """Retourner le log des cascades effectuées dans cette session."""
        return list(self._log)
