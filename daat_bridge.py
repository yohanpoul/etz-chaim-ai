"""daat_bridge.py -- Da'at -- Pont entre connaissance et application.

Da'at n'est pas une Sephirah mais le PONT qui lie Hokhmah (faits/RAG)
et Binah (raisonnement/system prompt) a la tache specifique.

Sans Da'at : les faits restent deconnectes de la question -> hallucinations.
Avec Da'at : attachement au domaine + liaison explicite + coherence globale.

Tanya ch.3 : "meme celui qui est sage et comprend, s'il n'applique pas
son Da'at, ne produira que des chimeres vaines (dimyonot shav)."

Trois composants (EC-SHK-016, 032-034) :
  1. DVEKUT  -- attacher le contexte au domaine de la query
  2. KISHUR  -- lier les faits epistemiques pertinents entre eux
  3. KOLEL   -- vue globale : coherence de l'ensemble assemble

Le Bridge opere DANS le ContextAssembler (etape 5).
Il enrichit et connecte le contexte pendant l'assemblage.
Sans DB : fonctionne sur les faits et context_items disponibles.
Avec DB : enrichit via les exemples resolus (Dvekut renforce).
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger("daat_bridge")


def _extract_domain_keywords(
    domain: str | None,
    kavvanah: dict[str, Any] | None = None,
) -> list[str]:
    """Extraire les mots-cles de domaine depuis domain et kavvanah.

    Retourne une liste dedupliquee de mots-cles substantifs (>3 chars).
    """
    keywords: list[str] = []
    if domain:
        # >2 chars pour domaine : accepter des identifiants courts (IA, RAG)
        keywords.extend(
            w for w in domain.lower().replace("_", " ").split() if len(w) > 2
        )
    if kavvanah:
        intention = kavvanah.get("intention", "")
        if intention:
            # >3 chars pour kavvanah : filtrer les mots-outils francais
            keywords.extend(
                w.lower()
                for w in intention.split()
                if len(w) > 3
                and w.lower()
                not in {
                    "dans",
                    "pour",
                    "avec",
                    "cette",
                    "entre",
                    "faire",
                    "aussi",
                    "mais",
                    "comme",
                    "tout",
                    "sont",
                    "plus",
                }
            )
    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


class DaatBridge:
    """Pont Da'at : lie le contexte a la question pour eviter les dimyonot shav.

    Fonctionne sans DB (mode contexte pur) et avec DB (exemples Dvekut).
    """

    def __init__(self, db_pool_fn: Any = None) -> None:
        """
        Args:
            db_pool_fn: callable retournant une connexion DB (optionnel).
                Si None, fonctionne en mode contexte pur.
        """
        self._db = db_pool_fn

    # ── DVEKUT ─────────────────────────────────────────────

    def dvekut(
        self,
        domain: str | None,
        question: str,
        facts: list[str] | None = None,
        context_items: list[str] | None = None,
        kavvanah: dict[str, Any] | None = None,
        limit: int = 3,
    ) -> dict[str, Any]:
        """Attacher le contexte au domaine de la query.

        Dvekut = attachement, adhesion. Le systeme s'attache au domaine
        de la question pour y ancrer sa reponse.

        Retourne un dict avec:
            - db_examples: list[dict] -- exemples resolus depuis la DB
            - domain_facts: list[str] -- faits filtres par pertinence domaine
            - domain_keywords: list[str] -- mots-cles de domaine identifies
        """
        result: dict[str, Any] = {
            "db_examples": [],
            "domain_facts": [],
            "domain_keywords": [],
        }

        keywords = _extract_domain_keywords(domain, kavvanah)
        result["domain_keywords"] = keywords

        # 1. DB-backed examples (optional bonus)
        if self._db and domain:
            try:
                conn = self._db()
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT question, response, score "
                        "FROM hitbonenut_questions "
                        "WHERE domain = %s AND score > 0.8 "
                        "ORDER BY score DESC LIMIT %s",
                        (domain, limit),
                    )
                    rows = cur.fetchall()
                result["db_examples"] = [
                    {"question": r[0], "response": r[1][:300], "score": r[2]}
                    for r in rows
                ]
            except Exception as e:
                log.debug("Dvekut DB query failed: %s", e)

        # 2. Domain-filtered facts from context
        all_items = list(facts or []) + list(context_items or [])
        if keywords and all_items:
            for item in all_items:
                item_lower = item.lower()
                if any(kw in item_lower for kw in keywords):
                    result["domain_facts"].append(item)
            # If keyword filtering yields nothing, take all (mieux vaut
            # tout passer que rien -- Da'at sans matiere = vide)
            if not result["domain_facts"]:
                result["domain_facts"] = all_items[: limit * 2]
        elif all_items:
            # No keywords -> all facts are relevant
            result["domain_facts"] = all_items[: limit * 2]

        return result

    # ── KISHUR ─────────────────────────────────────────────

    def kishur(self, facts: list[str], question: str) -> str:
        """Lier les faits epistemiques entre eux et a la question.

        Kishur = lien, connexion. Le pont qui explicite POURQUOI
        ces faits sont pertinents pour cette question et COMMENT
        ils se connectent entre eux.
        """
        if not facts:
            return ""

        facts_block = "\n".join(f"  - {f[:150]}" for f in facts[:6])
        return (
            f"[KISHUR -- Liaison faits<->question]\n"
            f"Les faits suivants sont directement pertinents. "
            f"Connecte CHAQUE fait a ta reponse :\n"
            f"{facts_block}\n"
            f"Question : {question[:200]}\n"
            f"Utilise ces faits SPECIFIQUEMENT -- ne les ignore pas."
        )

    # ── KOLEL ──────────────────────────────────────────────

    def kolel(self) -> str:
        """Vue globale -- coherence de l'ensemble assemble.

        Kolel = inclure, englober. Da'at englobe les deux directions :
        pourquoi CETTE reponse, et pourquoi PAS les alternatives.
        La vue globale qui empeche les chimeres (dimyonot shav).
        """
        return (
            "[KOLEL -- Coherence globale]\n"
            "Dans ta reponse :\n"
            "1. Explique POURQUOI cette analyse est correcte.\n"
            "2. Nomme au moins UNE interpretation alternative et explique "
            "pourquoi elle ne s'applique pas ici.\n"
            "3. Si un fait contredit ta conclusion, signale-le explicitement."
        )

    # ── BUILD (orchestrateur) ──────────────────────────────

    def build(
        self,
        question: str,
        domain: str | None = None,
        facts: list[str] | None = None,
        context_items: list[str] | None = None,
        kavvanah: dict[str, Any] | None = None,
    ) -> str | None:
        """Orchestre dvekut + kishur + kolel -> bloc Da'at a injecter.

        Retourne None SEULEMENT s'il n'y a rien a connecter
        (pas de faits, pas de contexte, pas de domaine avec DB).
        """
        # 1. Dvekut -- attachement au domaine
        dvekut_result = self.dvekut(
            domain, question, facts, context_items, kavvanah,
        )

        all_facts: list[str] = dvekut_result["domain_facts"]
        db_examples: list[dict[str, Any]] = dvekut_result["db_examples"]
        keywords: list[str] = dvekut_result["domain_keywords"]

        # Rien a connecter -> pas de faux Da'at
        if not all_facts and not db_examples:
            return None

        parts: list[str] = ["[DA'AT -- Pont connaissance<->application]"]

        # Dvekut : exemples resolus (si DB disponible)
        if db_examples:
            parts.append("Exemples resolus dans ce domaine :")
            for i, ex in enumerate(db_examples, 1):
                parts.append(
                    f"  {i}. Q: {ex['question'][:120]}\n"
                    f"     R: {ex['response'][:200]}"
                )
            parts.append("")

        # Dvekut : domaine identifie
        if keywords:
            parts.append(f"Domaine : {', '.join(keywords[:5])}")
            parts.append("")

        # 2. Kishur -- liaison explicite
        liaison = self.kishur(all_facts, question)
        if liaison:
            parts.append(liaison)
            parts.append("")

        # 3. Kolel -- coherence globale
        parts.append(self.kolel())

        parts.append("[/DA'AT]")
        return "\n".join(parts)
