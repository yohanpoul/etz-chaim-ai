"""hishtalshelut.py — סֵדֶר הִשְׁתַּלְשְׁלוּת : Chaîne de descente entre les 4 Mondes.

Le Seder Hishtalshelut n'est pas un simple routing — c'est la
mécanique même de la création. Chaque monde contient un Arbre
complet de 10 Sephiroth. Le Malkut d'un monde supérieur EST le
Keter du monde inférieur — ce n'est pas une métaphore, c'est
le protocole de transmission.

Descente (Or Yashar) :
  Atzilut  → spécification conceptuelle / direction stratégique
  Briah    → design, architecture, interfaces
  Yetzirah → implémentation concrète
  Assiah   → exécution, persistance, résultat final

Remontée (Or Chozer) :
  Les insights d'Assiah remontent pour enrichir chaque monde traversé.
  Ce n'est pas un feedback loop — c'est l'Or Chozer, la lumière
  qui remonte pour compléter ce que la descente a initié.

Usage:
    engine = HishtalshelutEngine(state, olamot_chain)
    result = engine.descend(query, tree, starting_world="atzilut")
    ascent = engine.ascend(result, insights, tree)
    world = engine.detect_world(query)
    state = engine.get_chain_state()
"""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass, field
from typing import Any

from olamot import ollama_generate, get_provider


# ── Les 4 Mondes dans l'ordre de descente ───────────────────────
# Atzilut → Briah → Yetzirah → Assiah
# (l'ordre INVERSE de _OLAMOT_CHAIN dans main.py qui est ascendant)

OLAMOT_DESCENDING = ("atzilut", "briah", "yetzirah", "assiah")

OLAM_HEBREW = {
    "atzilut":  "אֲצִילוּת",
    "briah":    "בְּרִיאָה",
    "yetzirah": "יְצִירָה",
    "assiah":   "עֲשִׂיָּה",
}

OLAM_SEPHIRAH = {
    "atzilut":  "keter",       # Keter/Chokmah — concept pur
    "briah":    "binah",       # Binah/Chokmah — design
    "yetzirah": "tiferet",     # Chesed→Tiferet — implémentation
    "assiah":   "malkuth",     # Netzach+Yesod — exécution
}

# Mapping vers les noms dans _OLAMOT_CHAIN de main.py
# (main.py utilise "atziluth" avec h, nous "atzilut" sans h)
OLAM_TO_CHAIN = {
    "atzilut":  "atziluth",
    "briah":    "briah",
    "yetzirah": "yetzirah",
    "assiah":   "assiah",
}

CHAIN_TO_OLAM = {v: k for k, v in OLAM_TO_CHAIN.items()}

# ── Mots-clés pour la détection du monde d'entrée ──────────────

_WORLD_KEYWORDS = {
    "atzilut": [
        "stratégie", "stratégique", "vision", "direction", "concept",
        "architecture globale", "philosophie", "principe", "fondement",
        "pourquoi", "sens", "signification", "mission", "but",
    ],
    "briah": [
        "design", "architecture", "interface", "structure", "plan",
        "analyse", "modèle", "système", "schéma", "diagramme",
        "compare", "différence", "cause", "causal",
    ],
    "yetzirah": [
        "implémente", "code", "fonction", "méthode", "classe",
        "comment", "étapes", "procédure", "configure", "installe",
        "crée", "ajoute", "modifie", "refactor",
    ],
    "assiah": [
        "exécute", "lance", "run", "test", "déploie", "status",
        "liste", "montre", "affiche", "combien", "quel",
        "rapide", "simple", "court",
    ],
}


@dataclass
class DescentStep:
    """Résultat d'une étape de descente dans un monde."""
    world: str
    hebrew: str
    input_text: str        # Ce que ce monde a reçu (Keter = Malkut du monde supérieur)
    output_text: str       # Ce que ce monde a produit (son Malkut)
    latency_ms: float = 0.0
    tokens_est: int = 0    # Estimation grossière du nombre de tokens
    status: str = "ok"     # "ok" | "error" | "skipped"
    error: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "world": self.world,
            "hebrew": self.hebrew,
            "input_len": len(self.input_text),
            "output_len": len(self.output_text),
            "latency_ms": self.latency_ms,
            "tokens_est": self.tokens_est,
            "status": self.status,
            "error": self.error,
            "confidence": self.confidence,
        }


@dataclass
class AscentStep:
    """Résultat d'une étape de remontée (Or Chozer)."""
    world: str
    hebrew: str
    insight: str
    enrichment: str      # Ce que le monde a reçu de la remontée
    status: str = "ok"

    def to_dict(self) -> dict:
        return {
            "world": self.world,
            "hebrew": self.hebrew,
            "insight_len": len(self.insight),
            "enrichment_len": len(self.enrichment),
            "status": self.status,
        }


@dataclass
class DescentResult:
    """Résultat complet d'une chaîne de descente."""
    starting_world: str
    ending_world: str
    steps: list[DescentStep] = field(default_factory=list)
    final_output: str = ""
    total_latency_ms: float = 0.0
    query: str = ""

    def to_dict(self) -> dict:
        return {
            "starting_world": self.starting_world,
            "ending_world": self.ending_world,
            "n_steps": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "final_output_len": len(self.final_output),
            "total_latency_ms": self.total_latency_ms,
            "query": self.query[:200],
        }


class HishtalshelutEngine:
    """סֵדֶר הִשְׁתַּלְשְׁלוּת — Moteur de descente/remontée entre les 4 Mondes.

    Gère le flux complet :
      1. detect_world(query) — déterminer le monde d'entrée
      2. descend(query, ...) — chaîne de descente Or Yashar
      3. ascend(result, ...) — chaîne de remontée Or Chozer
      4. get_chain_state() — état de la chaîne

    Chaque monde reçoit comme input le Malkut du monde supérieur,
    formaté via _format_descent() (interpénétration Malkut↔Keter).
    """

    def __init__(self, state: dict, olamot_chain: list[str] | None = None) -> None:
        """Brancher sur le _HISHTALSHELUT_STATE existant de main.py.

        Args:
            state: Le dict _HISHTALSHELUT_STATE de main.py.
            olamot_chain: La chaîne ascendante (par défaut _OLAMOT_CHAIN).
        """
        self._state = state
        self._olamot_chain = olamot_chain or list(OLAMOT_DESCENDING[::-1])
        self._descent_history: list[DescentResult] = []
        self._ascent_history: list[list[AscentStep]] = []

    # ── Propriétés ──────────────────────────────────────────────

    @property
    def current_world(self) -> str:
        chain_world = self._state.get("current_world", "assiah")
        return CHAIN_TO_OLAM.get(chain_world, chain_world)

    @property
    def descent_count(self) -> int:
        return self._state.get("descents", 0)

    @property
    def ascent_count(self) -> int:
        return self._state.get("ascents", 0)

    @property
    def highest_reached(self) -> str:
        chain_world = self._state.get("highest_reached", "assiah")
        return CHAIN_TO_OLAM.get(chain_world, chain_world)

    @property
    def history(self) -> list[DescentResult]:
        return list(self._descent_history)

    # ── detect_world ────────────────────────────────────────────

    def detect_world(self, query: str) -> str:
        """Déterminer le monde d'entrée le plus approprié pour une requête.

        Critères :
          - Mots-clés détectés dans la requête
          - Longueur et complexité apparente
          - Marqueurs de profondeur

        Returns:
            Le monde ("atzilut", "briah", "yetzirah", "assiah").
        """
        q = query.lower()
        qlen = len(query)

        # Compter les hits par monde
        scores: dict[str, float] = {w: 0.0 for w in OLAMOT_DESCENDING}
        for world, keywords in _WORLD_KEYWORDS.items():
            for kw in keywords:
                if kw in q:
                    scores[world] += 1.0

        # Bonus par longueur et complexité
        if qlen > 500:
            scores["atzilut"] += 2.0
            scores["briah"] += 1.0
        elif qlen > 200:
            scores["briah"] += 1.5
            scores["yetzirah"] += 0.5
        elif qlen < 50:
            scores["assiah"] += 1.5

        # Bonus pour les questions à marqueurs de profondeur
        depth_markers = [
            "isomorphisme", "formel", "preuve", "démontre",
            "formalise", "théorème", "architecture complète",
        ]
        if any(m in q for m in depth_markers):
            scores["atzilut"] += 2.0

        # Le monde avec le score le plus haut
        best = max(scores, key=lambda w: scores[w])

        # Si aucun score significatif, défaut = yetzirah
        if scores[best] < 0.5:
            return "yetzirah"

        return best

    # ── descend ─────────────────────────────────────────────────

    def descend(
        self,
        query: str,
        tree: dict,
        *,
        starting_world: str = "atzilut",
        timeout: int = 300,
    ) -> DescentResult:
        """סֵדֶר הִשְׁתַּלְשְׁלוּת — Chaîne de descente complète.

        Le query entre par starting_world et descend jusqu'à Assiah.
        À chaque étape, le résultat du monde supérieur (son Malkut)
        est formaté comme input pour le Keter du monde suivant.

        Args:
            query: La requête originale.
            tree: Dict des modules de l'Arbre.
            starting_world: Monde d'entrée (défaut: atzilut).
            timeout: Timeout par monde en secondes.

        Returns:
            DescentResult avec toutes les étapes et le résultat final.
        """
        start_idx = OLAMOT_DESCENDING.index(starting_world) \
            if starting_world in OLAMOT_DESCENDING else 0

        result = DescentResult(
            starting_world=starting_world,
            ending_world="assiah",
            query=query,
        )

        current_input = query
        for idx in range(start_idx, len(OLAMOT_DESCENDING)):
            world = OLAMOT_DESCENDING[idx]

            # Générer dans ce monde
            step = self._generate_in_world(
                world, current_input, query, timeout,
            )
            result.steps.append(step)
            result.total_latency_ms += step.latency_ms

            if step.status == "error":
                # En cas d'erreur, passer le texte brut au monde suivant
                current_input = self._format_descent(
                    current_input, world,
                    OLAMOT_DESCENDING[idx + 1] if idx + 1 < len(OLAMOT_DESCENDING) else "assiah",
                )
                continue

            # Log la transition
            if idx + 1 < len(OLAMOT_DESCENDING):
                next_world = OLAMOT_DESCENDING[idx + 1]
                self._log_transition(
                    "descent", world, next_world,
                    f"descente {world}→{next_world}", query,
                )
                # Interpénétration Malkut↔Keter
                current_input = self._format_descent(
                    step.output_text, world, next_world,
                )
            else:
                # Dernier monde — le résultat final
                result.final_output = step.output_text

        result.ending_world = OLAMOT_DESCENDING[-1]

        # Si pas de résultat final (tout en erreur), prendre le dernier output disponible
        if not result.final_output:
            for step in reversed(result.steps):
                if step.output_text:
                    result.final_output = step.output_text
                    result.ending_world = step.world
                    break

        self._descent_history.append(result)

        # SSE
        self._emit("hishtalshelut_descent",
                    starting_world=starting_world,
                    ending_world=result.ending_world,
                    n_steps=len(result.steps),
                    total_latency_ms=result.total_latency_ms)

        return result

    # ── ascend ──────────────────────────────────────────────────

    def ascend(
        self,
        descent_result: DescentResult,
        insights: list[str],
        tree: dict,
    ) -> list[AscentStep]:
        """אוֹר חוֹזֵר — Chaîne de remontée avec enrichissement.

        Les insights d'Assiah remontent à travers chaque monde,
        enrichissant les modules traversés.

        Args:
            descent_result: Le résultat de la descente précédente.
            insights: Insights extraits du résultat final.
            tree: Dict des modules de l'Arbre.

        Returns:
            Liste d'AscentStep documentant chaque enrichissement.
        """
        ascent_steps: list[AscentStep] = []

        if not insights:
            return ascent_steps

        # Remonter dans l'ordre inverse de la descente
        worlds_traversed = [s.world for s in descent_result.steps if s.status == "ok"]
        if not worlds_traversed:
            return ascent_steps

        combined_insight = " | ".join(insights[:5])

        for world in reversed(worlds_traversed):
            # Enrichir le module associé au monde
            sephirah = OLAM_SEPHIRAH.get(world, "yesod")
            enrichment = self._enrich_world(
                tree, world, sephirah, combined_insight,
            )

            step = AscentStep(
                world=world,
                hebrew=OLAM_HEBREW.get(world, ""),
                insight=combined_insight[:300],
                enrichment=enrichment,
            )
            ascent_steps.append(step)

            # Log la transition de remontée
            world_idx = OLAMOT_DESCENDING.index(world)
            if world_idx > 0:
                prev_world = OLAMOT_DESCENDING[world_idx - 1]
                self._log_transition(
                    "ascent", world, prev_world,
                    f"remontée Or Chozer {world}→{prev_world}",
                    descent_result.query,
                )

        self._ascent_history.append(ascent_steps)

        # SSE
        self._emit("hishtalshelut_ascent",
                    n_worlds=len(ascent_steps),
                    n_insights=len(insights))

        return ascent_steps

    # ── get_chain_state ─────────────────────────────────────────

    def get_chain_state(self) -> dict:
        """Retourner l'état complet de la chaîne.

        Returns:
            Dict avec monde courant, compteurs, historique récent.
        """
        return {
            "current_world": self.current_world,
            "current_hebrew": OLAM_HEBREW.get(self.current_world, ""),
            "highest_reached": self.highest_reached,
            "highest_hebrew": OLAM_HEBREW.get(self.highest_reached, ""),
            "ascents": self.ascent_count,
            "descents": self.descent_count,
            "total_descents_full": len(self._descent_history),
            "total_ascents_full": len(self._ascent_history),
            "log_count": len(self._state.get("log", [])),
            "forced_world": self._state.get("forced_world"),
            "worlds": {
                w: {
                    "hebrew": OLAM_HEBREW[w],
                    "sephirah": OLAM_SEPHIRAH[w],
                    "chain_name": OLAM_TO_CHAIN[w],
                }
                for w in OLAMOT_DESCENDING
            },
        }

    # ── _format_descent (interpénétration Malkut↔Keter) ─────────

    @staticmethod
    def _format_descent(
        result: str,
        from_world: str,
        to_world: str,
    ) -> str:
        """Formater le Malkut d'un monde comme Keter du monde suivant.

        מַלְכוּת שֶׁל עֶלְיוֹן = כֶּתֶר שֶׁל תַּחְתּוֹן
        Le Malkut du supérieur est le Keter de l'inférieur.

        Le formatage adapte le registre :
          Atzilut→Briah : concept pur → directives de design
          Briah→Yetzirah : design → spécifications techniques
          Yetzirah→Assiah : implémentation → instructions d'exécution

        Args:
            result: Output du monde supérieur (son Malkut).
            from_world: Monde d'origine.
            to_world: Monde de destination.

        Returns:
            Texte reformaté comme Keter du monde de destination.
        """
        from_heb = OLAM_HEBREW.get(from_world, from_world)
        to_heb = OLAM_HEBREW.get(to_world, to_world)

        # Tronquer si trop long (chaque monde reçoit max 1000 chars)
        truncated = result[:1000] if len(result) > 1000 else result

        if from_world == "atzilut" and to_world == "briah":
            return (
                f"[Keter de {to_heb} — reçu du Malkut d'{from_heb}]\n"
                f"Direction stratégique :\n{truncated}\n\n"
                f"[Instruction: Traduis cette direction en design concret. "
                f"Définis les interfaces, les composants, l'architecture.]"
            )
        elif from_world == "briah" and to_world == "yetzirah":
            return (
                f"[Keter de {to_heb} — reçu du Malkut de {from_heb}]\n"
                f"Design et architecture :\n{truncated}\n\n"
                f"[Instruction: Implémente ce design. Code concret, "
                f"paramètres, configuration.]"
            )
        elif from_world == "yetzirah" and to_world == "assiah":
            return (
                f"[Keter de {to_heb} — reçu du Malkut de {from_heb}]\n"
                f"Implémentation :\n{truncated}\n\n"
                f"[Instruction: Exécute. Persiste le résultat. "
                f"Retourne le résultat final.]"
            )
        else:
            # Cas générique
            return (
                f"[Keter de {to_heb} — reçu du Malkut de {from_heb}]\n"
                f"{truncated}"
            )

    # ── Private ─────────────────────────────────────────────────

    def _generate_in_world(
        self,
        world: str,
        input_text: str,
        original_query: str,
        timeout: int,
    ) -> DescentStep:
        """Générer dans un monde spécifique via Ollama/API.

        Args:
            world: Le monde ("atzilut", "briah", "yetzirah", "assiah").
            input_text: Le texte d'entrée (Keter de ce monde).
            original_query: La requête originale.
            timeout: Timeout en secondes.

        Returns:
            DescentStep avec le résultat.
        """
        import os

        chain_world = OLAM_TO_CHAIN.get(world, world)
        hebrew = OLAM_HEBREW.get(world, "")

        # Construire le prompt
        prompt = (
            f"You are operating at the level of {world.upper()} ({hebrew}).\n"
            f"Original query: {original_query[:300]}\n\n"
            f"{input_text}\n\n"
            f"Respond in French. Be precise and structured."
        )

        try:
            # Vérifier l'accès au monde
            if chain_world == "atziluth":
                provider = get_provider("atziluth")
                if provider == "anthropic" and not os.environ.get("ANTHROPIC_API_KEY"):
                    return DescentStep(
                        world=world,
                        hebrew=hebrew,
                        input_text=input_text[:300],
                        output_text="",
                        status="skipped",
                        error="no ANTHROPIC_API_KEY",
                    )

            chain_kavvanah = {
                "intention": f"Générer au niveau {world.upper()} ({hebrew}) dans la chaîne de descente",
                "critere_succes": f"réponse structurée, pertinente à la requête, au niveau de {world}",
                "anti_pattern": "ne pas répéter le contenu du monde précédent — chaque monde apporte sa propre perspective",
            }
            t0 = time.monotonic()
            response, latency = ollama_generate(
                chain_world, prompt, timeout=timeout,
                kavvanah=chain_kavvanah,
            )
            elapsed = (time.monotonic() - t0) * 1000

            # Estimation grossière des tokens (1 token ~ 4 chars)
            tokens_est = len(response) // 4

            # Confiance heuristique
            confidence = self._estimate_confidence(response)

            return DescentStep(
                world=world,
                hebrew=hebrew,
                input_text=input_text[:300],
                output_text=response,
                latency_ms=elapsed,
                tokens_est=tokens_est,
                status="ok",
                confidence=confidence,
            )

        except Exception as e:
            return DescentStep(
                world=world,
                hebrew=hebrew,
                input_text=input_text[:300],
                output_text="",
                status="error",
                error=str(e)[:200],
            )

    def _enrich_world(
        self,
        tree: dict,
        world: str,
        sephirah: str,
        insight: str,
    ) -> str:
        """Enrichir un monde avec un insight de la remontée.

        Stocke l'insight dans Yesod avec les tags appropriés.

        Returns:
            Description de l'enrichissement effectué.
        """
        yesod = tree.get("yesod")
        if not yesod:
            return f"[{world}] Yesod non disponible — insight non persisté"

        try:
            yesod.remember(
                content=(
                    f"[Or Chozer → {world}] "
                    f"Insight post-descente: {insight[:200]}"
                ),
                source_sephirah=sephirah,
                confidence=0.65,
                domain="general",
                tags=["hishtalshelut", "or_chozer", f"world:{world}", sephirah],
            )
            return f"[{world}/{sephirah}] Insight persisté via Yesod"
        except Exception as e:
            return f"[{world}] Erreur enrichissement: {str(e)[:100]}"

    def _log_transition(
        self,
        direction: str,
        from_world: str,
        to_world: str,
        reason: str,
        query: str,
    ) -> None:
        """Logger une transition dans _HISHTALSHELUT_STATE."""
        entry = {
            "direction": direction,
            "from": from_world,
            "to": to_world,
            "reason": reason,
            "timestamp": time.time(),
            "query": query[:200],
        }
        self._state.setdefault("log", []).append(entry)

        if direction == "descent":
            self._state["descents"] = self._state.get("descents", 0) + 1
        else:
            self._state["ascents"] = self._state.get("ascents", 0) + 1
            # Mettre à jour highest_reached
            chain_to = OLAM_TO_CHAIN.get(to_world, to_world)
            chain = self._olamot_chain
            current_highest = self._state.get("highest_reached", "assiah")
            if chain_to in chain and current_highest in chain:
                if chain.index(chain_to) > chain.index(current_highest):
                    self._state["highest_reached"] = chain_to

        chain_to = OLAM_TO_CHAIN.get(to_world, to_world)
        self._state["current_world"] = chain_to

    @staticmethod
    def _estimate_confidence(response: str) -> float:
        """Estimer la confiance d'une réponse (heuristique)."""
        if not response:
            return 0.1
        low = response.lower()
        if "[erreur" in low or "error" in low:
            return 0.05
        if len(response.strip()) < 20:
            return 0.1
        uncertainty = [
            "je ne sais pas", "pas sûr", "incertain",
            "impossible de", "aucune information",
        ]
        hits = sum(1 for m in uncertainty if m in low)
        if hits >= 2:
            return 0.15
        if hits == 1:
            return 0.25
        if len(response.strip()) < 80:
            return 0.3
        return 0.55

    @staticmethod
    def _emit(event_type: str, **data) -> None:
        """Emettre un evenement SSE."""
        try:
            from web.events import emit as _emit
            _emit(event_type, **data)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    @staticmethod
    def _persist_yesod(
        tree: dict,
        content: str,
        *,
        domain: str = "general",
        tags: list[str] | None = None,
    ) -> None:
        """Persister dans Yesod (EpisteMemory)."""
        yesod = tree.get("yesod")
        if not yesod:
            return
        try:
            yesod.remember(
                content=content,
                source_sephirah="malkuth",
                confidence=0.7,
                domain=domain,
                tags=tags or [],
            )
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
