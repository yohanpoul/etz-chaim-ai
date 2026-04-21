"""Memuneh — Créateur ontologique de Malakhim.

מְמוּנֶּה — Le « préposé ». Zohar Pekudei (II:244b-268b) : chaque
palais (heikhal) est gouverné par un ange préposé (memunneh).

Le Memuneh ne DISPATCH plus — il ENGENDRE.

Trois axes de décision :
  1. Kavvanah (qualité de l'intention) — détermine si un Malakh est nécessaire
  2. Nature ontologique (strategic/analytic/execution/mechanic)
  3. Budget (descente d'olam si le modèle dépasse le plafond)

Trois modes (Tanya ch. 39-40) :
  HIGH kavvanah  → connexion directe, PAS de Malakh (Atziluth/Briah)
  MEDIUM kavvanah → Malakh ENGENDRÉ via Heikhalot pipeline (Yetzirah)
  LOW kavvanah   → exécution mécanique (Assiah/Ishim)

Modèle d'interface : MESHARET (bidirectionnel, ↕)
  - Phase Olim (montante) : Heikhalot pipeline (7 palais)
  - Phase Yordim (descendante) : exécution par le Malakh engendré

Quatre olamot, quatre niveaux de masakh :
  Atziluth → opus    (masakh dalet, max transparence)
  Briah    → sonnet  (masakh gimel)
  Yetzirah → haiku   (masakh bet, fallback qwen3.5:9b)
  Assiah   → qwen3.5:9b (masakh aleph, exécution locale)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from malakhim.kavvanah_gate import kavvanah_score
from malakhim.malakh import Malakh
from malakhim.models import MalakhResult, ValidationSpec
from malakhim.pekidah.registry import PekidahRegistry

# ── Mappings ontologiques ──────────────────────────────────────────────────

NATURE_TO_OLAM: dict[str, str] = {
    "strategic": "atziluth",
    "analytic": "briah",
    "execution": "yetzirah",
    "mechanic": "assiah",
}

OLAM_TO_MODEL: dict[str, dict[str, str]] = {
    "atziluth": {"model": "opus", "provider": "claude", "masakh": "dalet"},
    "briah": {"model": "sonnet", "provider": "claude", "masakh": "gimel"},
    "yetzirah": {"model": "haiku", "provider": "claude", "masakh": "bet"},
    "assiah": {"model": "qwen3.5:9b", "provider": "ollama", "masakh": "aleph"},
}

# ── Priorité zoharique : fidélité de transmission ────────────────────────────
# Zohar II:43a : les Malakhim (messagers) sont au 1er rang — la FIDÉLITÉ
# de la transmission est supérieure à la puissance d'intellection.
# Pour Maïmonide : intellection pure (Chayyot) au sommet → modèle le + puissant.
# Pour le Zohar : messagerie fidèle au sommet → modèle le + obéissant.
#
# Certaines tâches requièrent la fidélité (format strict, extraction exacte,
# code) plus que la puissance (raisonnement ouvert, stratégie).

_FIDELITY_KEYWORDS = {
    "format", "exact", "json", "csv", "sql", "code", "extract", "liste",
    "table", "schema", "template", "tradui", "convert", "parse",
}

# Modèle à haute fidélité par olam (préfère l'obéissance à la puissance)
OLAM_TO_MODEL_FIDELITY: dict[str, dict[str, str]] = {
    "atziluth": {"model": "sonnet", "provider": "claude", "masakh": "gimel"},  # sonnet > opus en fidélité
    "briah": {"model": "sonnet", "provider": "claude", "masakh": "gimel"},
    "yetzirah": {"model": "qwen3.5:9b", "provider": "ollama", "masakh": "aleph"},  # local, très obéissant
    "assiah": {"model": "qwen3.5:9b", "provider": "ollama", "masakh": "aleph"},
}

# Ordre de descente pour downgrade budgétaire
_OLAM_ORDER = ["atziluth", "briah", "yetzirah", "assiah"]

# Coûts relatifs (unités arbitraires, pour comparaison budgétaire)
_OLAM_COST: dict[str, int] = {
    "atziluth": 10000,
    "briah": 3000,
    "yetzirah": 1000,
    "assiah": 100,
}

# ── Mots-clés heuristiques pour classify_nature ────────────────────────────

_STRATEGIC_KW = {
    "strateg", "architect", "design", "plan", "decide", "vision", "concevoir",
}
_ANALYTIC_KW = {
    "analy", "compar", "evaluat", "reason", "explain", "why", "recherch", "verif",
}
_MECHANIC_KW = {
    "format", "convert", "list", "count", "extract",
}


@dataclass
class RoutingDecision:
    """Résultat du routage Memuneh."""

    nature: str
    olam: str
    model: str
    provider: str
    masakh_level: str
    agent_id: str | None = None
    confidence: float = 1.0
    warnings: list[str] = field(default_factory=list)


class Memuneh:
    """Routeur ontologique — route les missions vers le bon Malakh.

    Trois axes de décision :
      1. Nature de la tâche (classify_nature)
      2. Budget (downgrade si nécessaire)
      3. Compétence Pekidah (Kategor warnings, agent validation)
    """

    def __init__(self, registry: PekidahRegistry | None = None) -> None:
        self._registry = registry

    # ── Phase 1 : Classification ───────────────────────────────────────────

    def classify_nature(
        self, prompt: str, kavvanah: dict[str, Any] | None = None,
    ) -> str:
        """Détermine la nature ontologique d'une tâche.

        Priorité :
          1. kavvanah["nature"] explicite
          2. kavvanah["olam"] → déduit la nature
          3. Heuristiques par mots-clés + longueur
        """
        kav = kavvanah or {}

        # 1. Nature explicite
        if "nature" in kav:
            nature = kav["nature"]
            if nature in NATURE_TO_OLAM:
                return nature

        # 2. Olam explicite → déduire nature
        if "olam" in kav:
            olam = kav["olam"]
            for nat, ol in NATURE_TO_OLAM.items():
                if ol == olam:
                    return nat

        # 3. Heuristiques
        prompt_lower = prompt.lower()
        prompt_len = len(prompt)

        # Prompt très court → mechanic
        if prompt_len < 50:
            for kw in _MECHANIC_KW:
                if kw in prompt_lower:
                    return "mechanic"
            # Court sans mot-clé mécanique → mechanic par défaut
            return "mechanic"

        # Strategic si mots-clés ET prompt long
        if prompt_len > 200:
            for kw in _STRATEGIC_KW:
                if kw in prompt_lower:
                    return "strategic"

        # Analytic si mots-clés
        for kw in _ANALYTIC_KW:
            if kw in prompt_lower:
                return "analytic"

        # Défaut
        return "execution"

    # ── Phase 2 : Routage complet (Mesharet ↕) ────────────────────────────

    def route(
        self,
        prompt: str,
        kavvanah: dict[str, Any] | None = None,
        budget_max: int = 0,
    ) -> RoutingDecision:
        """Route une mission vers le bon olam/model.

        Phase Olim (montée) : consulte Pekidah (Kategorim + Praklitim)
        Phase Yordim (descente) : mappe nature → olam → model
        """
        kav = kavvanah or {}
        warnings: list[str] = []
        confidence = 1.0

        # ── Phase Olim : consultation Pekidah ──────────────────────────
        agent_id = kav.get("agent_id")
        domain = kav.get("domain", "general")

        if self._registry is not None:
            # Kategorim actifs pour cet agent + domaine
            if agent_id:
                kategor_matches = self._registry.check_failures(
                    agent_id, domain, prompt,
                )
                for k in kategor_matches:
                    warnings.append(
                        f"Kategor #{k.pattern_id}: {k.error_type} "
                        f"(domain={k.domain}, occurrences={k.occurrences})"
                    )
                    confidence -= 0.1 * len(kategor_matches)

            # Praklitim (meilleures stratégies) — informatif
            praklitim = self._registry.get_best_strategies(domain, limit=3)
            if praklitim:
                best = praklitim[0]
                if best.strategy_used:
                    warnings.append(
                        f"Praklite recommande: {best.strategy_used} "
                        f"(score={best.score:.2f})"
                    )

        # ── Phase Yordim : classification + mapping ────────────────────
        nature = self.classify_nature(prompt, kavvanah)
        olam = NATURE_TO_OLAM[nature]

        # Downgrade budgétaire
        if budget_max > 0:
            while _OLAM_COST[olam] > budget_max:
                idx = _OLAM_ORDER.index(olam)
                if idx >= len(_OLAM_ORDER) - 1:
                    break  # Déjà au plus bas
                olam = _OLAM_ORDER[idx + 1]
                warnings.append(
                    f"Budget downgrade: {_OLAM_ORDER[idx]} → {olam}"
                )
                confidence -= 0.15

        # ── Priorité zoharique : fidélité > puissance ─────────────────
        # Zohar II:43a : si la tâche requiert FIDÉLITÉ de transmission
        # (format strict, extraction, code), préférer le modèle le plus
        # obéissant, pas le plus puissant.
        requires_fidelity = any(
            kw in prompt.lower() for kw in _FIDELITY_KEYWORDS
        )

        if requires_fidelity:
            model_info = OLAM_TO_MODEL_FIDELITY.get(olam, OLAM_TO_MODEL[olam])
            warnings.append("Zohar priority: fidélité > puissance")
        else:
            model_info = OLAM_TO_MODEL[olam]

        # Vérification compétence agent si spécifié
        if self._registry is not None and agent_id:
            if not self._registry.can_handle(agent_id, domain):
                warnings.append(
                    f"Agent {agent_id} sous le seuil pour domain={domain}"
                )
                confidence -= 0.2

        confidence = max(0.0, min(1.0, confidence))

        return RoutingDecision(
            nature=nature,
            olam=olam,
            model=model_info["model"],
            provider=model_info["provider"],
            masakh_level=model_info["masakh"],
            agent_id=agent_id,
            confidence=confidence,
            warnings=warnings,
        )

    # ── Phase 3 : Dispatch (route + exécute + enregistre) ──────────────

    def _make_olamot_fn(self, olam: str, kavvanah: dict) -> Callable:
        """Créer un callable qui appelle olamot.ollama_generate.

        L'import est lazy (dans la fonction, pas en tête de fichier) pour
        ne pas casser les tests qui n'ont pas olamot configuré.
        """
        def _call(context: dict) -> str:
            try:
                from olamot import ollama_generate
                prompt = context.get("input", "")
                response, _latency = ollama_generate(
                    olam=olam,
                    prompt=prompt,
                    kavvanah=kavvanah if kavvanah else None,
                )
                return response
            except ImportError:
                # olamot non disponible (tests, CI)
                return str(context.get("input", ""))
            except Exception as e:
                return f"[ERROR] {e}"
        return _call

    def dispatch(
        self,
        prompt: str,
        kavvanah: dict[str, Any] | None = None,
        execute_fn: Callable[[dict[str, Any]], str] | None = None,
        budget_max: int = 0,
    ) -> MalakhResult:
        """Route, crée un Malakh (ou non), exécute, enregistre.

        Tanya ch. 39-40 — le gradient de kavvanah :
          HIGH  → _direct_call()   (pas de Malakh — Atziluth n'a pas d'anges)
          MEDIUM → _malakh_dispatch() (Malakh ENGENDRÉ via Heikhalot)
          LOW   → _mechanical_call() (Ishim — exécution minimale)

        Si execute_fn est fourni explicitement (tests, usage avancé),
        le comportement legacy est préservé sans kavvanah gate.
        """
        kav = kavvanah or {}

        # ── Legacy path : execute_fn explicite → comportement existant ──
        if execute_fn is not None:
            return self._legacy_dispatch(prompt, kav, execute_fn, budget_max)

        # ── Kavvanah gate → tier de routage ──
        grade = kavvanah_score(kav, prompt)

        if grade.tier == "high":
            return self._direct_call(prompt, kav, budget_max)
        elif grade.tier == "low":
            return self._mechanical_call(prompt, kav, budget_max)
        else:
            return self._malakh_dispatch(prompt, kav, budget_max)

    # ── Legacy dispatch (rétrocompatibilité) ──────────────────────────────

    def _legacy_dispatch(
        self,
        prompt: str,
        kav: dict[str, Any],
        execute_fn: Callable[[dict[str, Any]], str],
        budget_max: int,
    ) -> MalakhResult:
        """Dispatch avec execute_fn explicite — rétrocompatible."""
        decision = self.route(prompt, kav, budget_max)

        with Malakh(
            mission=prompt,
            kavvanah=kav,
            order=decision.olam,
            execute_fn=execute_fn,
        ) as m:
            result = m.execute({"input": prompt})

        result.metadata["routing"] = self._routing_metadata(decision)
        self._record_pekidah(result, decision, kav, prompt)
        return result

    # ── Direct call (HIGH kavvanah — Atziluth n'a pas d'anges) ────────────

    def _direct_call(
        self,
        prompt: str,
        kav: dict[str, Any],
        budget_max: int,
    ) -> MalakhResult:
        """Connexion directe — pas de Malakh. Atziluth/Briah.

        « Atziluth ne contient pas d'anges au sens propre. Dans ce
        monde, il n'y a pas de séparation (perud) entre l'émanation
        et l'Émanateur. » — MALAKHIM.md §5.1
        """
        import time

        decision = self.route(prompt, kav, budget_max)
        olamot_fn = self._make_olamot_fn(decision.olam, kav)

        t0 = time.monotonic()
        response = olamot_fn({"input": prompt})
        latency_ms = (time.monotonic() - t0) * 1000.0

        # Gabriel valide la sortie
        warnings: list[str] = []
        try:
            from malakhim.archangels.gabriel import Gabriel
            gabriel = Gabriel()
            gab_result = gabriel.validate(response)
            if gab_result.get("severity") in ("rejected", "destroyed"):
                warnings.append(f"Gabriel: {gab_result.get('reason', '')}")
        except (ImportError, AttributeError) as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        result = MalakhResult(
            response=response,
            success=True,
            score=1.0,
            latency_ms=latency_ms,
            hitkalelut_warnings=warnings,
        )
        result.metadata["routing"] = self._routing_metadata(decision)
        result.metadata["direct_path"] = True
        result.metadata["kavvanah_tier"] = "high"
        self._record_pekidah(result, decision, kav, prompt)
        return result

    # ── Malakh dispatch (MEDIUM kavvanah — Yetzirah) ──────────────────────

    def _malakh_dispatch(
        self,
        prompt: str,
        kav: dict[str, Any],
        budget_max: int,
    ) -> MalakhResult:
        """Le Malakh est ENGENDRÉ par la mission via Heikhalot.

        1. Route (existant)
        2. Heikhalot pipeline ascendant (7 palais)
        3. generate_malakh() → Malakh UNIQUE façonné par sa mission
        4. Execute
        5. Record
        """
        from malakhim.heikhalot.pipeline import ascend, HeikhalotReject

        decision = self.route(prompt, kav, budget_max)

        # ── Phase Olim : ascension à travers les 7 palais ──
        request = {
            "prompt": prompt,
            "nature": decision.nature,
            "kavvanah": dict(kav),
            "agent_id": kav.get("agent_id"),
            "domain": kav.get("domain", "general"),
        }

        try:
            heikhalot = ascend(request, registry=self._registry)
        except HeikhalotReject as e:
            # Rejet — retourner un résultat d'échec
            return MalakhResult(
                response=f"[Heikhalot rejet] {e.stage}: {e.reason}",
                success=False,
                score=0.0,
                hitkalelut_warnings=[str(e)],
                metadata={
                    "routing": self._routing_metadata(decision),
                    "kavvanah_tier": "medium",
                    "heikhalot_rejected": True,
                },
            )

        # ── Phase Yordim : engendrement + exécution ──
        result = self._generate_and_execute(
            prompt, heikhalot, decision, kav,
        )
        result.metadata["kavvanah_tier"] = "medium"
        result.metadata["heikhalot_stages"] = heikhalot.stages_passed
        self._record_pekidah(result, decision, kav, prompt)
        return result

    # ── Mechanical call (LOW kavvanah — Assiah/Ishim) ─────────────────────

    def _mechanical_call(
        self,
        prompt: str,
        kav: dict[str, Any],
        budget_max: int,
    ) -> MalakhResult:
        """Exécution mécanique — Ishim, forces naturelles.

        Maïmonide (More Nevukhim II:6) : « toutes les forces qui
        résident dans un corps sont des anges ». Pas besoin
        d'intelligence — juste de l'exécution.
        """
        # Forcer Assiah
        kav_copy = dict(kav)
        kav_copy["nature"] = "mechanic"
        decision = self.route(prompt, kav_copy, budget_max)

        olamot_fn = self._make_olamot_fn(decision.olam, kav_copy)

        with Malakh(
            mission=prompt,
            kavvanah=kav_copy,
            order="assiah",
            execute_fn=olamot_fn,
        ) as m:
            result = m.execute({"input": prompt})

        result.metadata["routing"] = self._routing_metadata(decision)
        result.metadata["kavvanah_tier"] = "low"
        self._record_pekidah(result, decision, kav_copy, prompt)
        return result

    # ── generate_and_execute : le Malakh EST sa mission ───────────────────

    def _generate_and_execute(
        self,
        prompt: str,
        heikhalot,
        decision: RoutingDecision,
        kav: dict[str, Any],
    ) -> MalakhResult:
        """Engendre un Malakh UNIQUE façonné par sa mission.

        Le system prompt, la validation, et le style Shem sont
        issus du pipeline Heikhalot — le Malakh n'est pas un
        conteneur générique, il EST sa mission.

        Intègre Metatron (Levush) : le system prompt est adapté
        au monde cible. La même intention, revêtue différemment.
        """
        from malakhim.metatron import adapt_to_olam

        enriched_kav = dict(kav)
        enriched_kav.update(heikhalot.enriched_kavvanah)

        olamot_fn = self._make_olamot_fn(decision.olam, enriched_kav)

        # ── Metatron / Levush : adapter au monde cible ──
        levush = adapt_to_olam(
            prompt=prompt,
            system_prompt=heikhalot.system_prompt,
            olam=decision.olam,
            nature=decision.nature,
        )
        system_prompt = levush.adapted_system_prompt

        # Condenser le system prompt pour Claude CLI (max-turns 1)
        # On garde les 3 lignes les plus importantes
        sp_lines = [l for l in system_prompt.split("\n") if l.strip()]
        condensed_sp = "\n".join(sp_lines[:6]) if len(sp_lines) > 6 else system_prompt

        def shaped_fn(context: dict) -> str:
            raw_prompt = context.get("input", "")
            if condensed_sp:
                full_prompt = f"[Instructions]\n{condensed_sp}\n\n[Tâche]\n{raw_prompt}"
            else:
                full_prompt = raw_prompt
            return olamot_fn({"input": full_prompt})

        with Malakh(
            mission=prompt,
            kavvanah=enriched_kav,
            order=decision.olam,
            execute_fn=shaped_fn,
            system_prompt=system_prompt,
            validation_spec=heikhalot.validation_spec,
        ) as m:
            result = m.execute({"input": prompt})

        # ── Samael : diagnostiquer l'excès si échec ──
        if not result.success or result.hitkalelut_warnings:
            from malakhim.samael import diagnose_excess, get_rebalancing_instruction
            diagnosis = diagnose_excess(
                response=result.response,
                warnings=result.hitkalelut_warnings,
                score=result.score,
                nature=decision.nature,
            )
            if diagnosis is not None:
                result.metadata["samael"] = {
                    "sephirah_source": diagnosis.sephirah_source,
                    "function_excess": diagnosis.function_excess,
                    "severity": diagnosis.severity,
                    "prescription": diagnosis.prescription,
                    "rebalancing": get_rebalancing_instruction(diagnosis),
                }

        # ── Raphael : Tikkun si échec (diagnostic + guérison) ──
        if not result.success:
            from malakhim.archangels.raphael import Raphael
            raphael = Raphael()
            raph_diag = raphael.diagnose(result)
            if not raph_diag.healthy:
                healing = raphael.heal(
                    result=result,
                    diagnosis=raph_diag,
                    execute_fn=shaped_fn,
                    original_prompt=prompt,
                    kavvanah=enriched_kav,
                )
                if healing.healed:
                    result = healing.final_result
                result.metadata["raphael"] = {
                    "healed": healing.healed,
                    "attempts": healing.attempts,
                    "tikkun_applied": healing.tikkun_applied,
                    "qliphah_chain": [
                        d.qliphah_type for d in healing.diagnosis_chain
                    ],
                }

        result.metadata["routing"] = self._routing_metadata(decision)
        result.metadata["levush"] = {
            "olam": levush.olam,
            "emphasis": levush.emphasis,
        }
        if heikhalot.shem_index:
            result.metadata["shem_index"] = heikhalot.shem_index

        return result

    # ── Prepare for stream (web integration) ────────────────────────────

    def prepare_for_stream(
        self,
        prompt: str,
        kavvanah: dict[str, Any] | None = None,
        budget_max: int = 0,
    ) -> dict[str, Any]:
        """Préparer l'exécution SANS exécuter — pour le streaming web.

        Exécute le KavvanahGate + Heikhalot + Metatron/Levush mais
        retourne la préparation au lieu d'exécuter. Le web streame
        ensuite avec ollama_generate_stream() en utilisant le prompt
        enrichi.

        Returns:
            dict avec:
              - tier: "high" | "medium" | "low"
              - olam: le monde cible
              - enriched_prompt: le prompt enrichi par Heikhalot + Levush
              - system_prompt: le system prompt généré
              - nature: la nature détectée
              - validation_spec: pour le post-check
              - shem_index: le trigramme sélectionné
              - warnings: avertissements
              - heikhalot_stages: stages passés
        """
        kav = kavvanah or {}
        grade = kavvanah_score(kav, prompt)

        decision = self.route(prompt, kav, budget_max)

        result = {
            "tier": grade.tier,
            "kavvanah_score": grade.score,
            "olam": decision.olam,
            "model": decision.model,
            "nature": decision.nature,
            "routing": self._routing_metadata(decision),
            "warnings": list(decision.warnings),
        }

        if grade.tier == "high":
            # Pas de Malakh — prompt direct
            result["enriched_prompt"] = prompt
            result["system_prompt"] = ""
            result["heikhalot_stages"] = []
            return result

        if grade.tier == "low":
            # Mécanique — prompt direct, olam forcé en assiah
            result["olam"] = "assiah"
            result["enriched_prompt"] = prompt
            result["system_prompt"] = ""
            result["heikhalot_stages"] = []
            return result

        # MEDIUM → Heikhalot pipeline
        from malakhim.heikhalot.pipeline import ascend, HeikhalotReject
        from malakhim.metatron import adapt_to_olam

        request = {
            "prompt": prompt,
            "nature": decision.nature,
            "kavvanah": dict(kav),
            "agent_id": kav.get("agent_id"),
            "domain": kav.get("domain", "general"),
        }

        try:
            heikhalot = ascend(request, registry=self._registry)
        except HeikhalotReject as e:
            result["enriched_prompt"] = prompt
            result["system_prompt"] = ""
            result["heikhalot_stages"] = []
            result["warnings"].append(f"Heikhalot rejet: {e}")
            return result

        # Levush adaptation
        levush = adapt_to_olam(
            prompt=prompt,
            system_prompt=heikhalot.system_prompt,
            olam=decision.olam,
            nature=decision.nature,
        )

        # Condenser pour Claude CLI
        sp_lines = [l for l in levush.adapted_system_prompt.split("\n") if l.strip()]
        condensed_sp = "\n".join(sp_lines[:6]) if len(sp_lines) > 6 else levush.adapted_system_prompt

        enriched = f"[Instructions]\n{condensed_sp}\n\n[Tâche]\n{prompt}" if condensed_sp else prompt

        result["enriched_prompt"] = enriched
        result["system_prompt"] = condensed_sp
        result["validation_spec"] = heikhalot.validation_spec
        result["shem_index"] = heikhalot.shem_index
        result["heikhalot_stages"] = heikhalot.stages_passed
        result["warnings"].extend(heikhalot.warnings)

        return result

    def post_stream_check(
        self,
        response: str,
        preparation: dict[str, Any],
        prompt: str,
        kavvanah: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Post-check après le streaming — Samael + Reshimo + Pekidah.

        Appelé par le web après que le stream est terminé.
        Ferme le cycle : diagnostic d'excès + reshimo déposé.
        """
        kav = kavvanah or {}
        nature = preparation.get("nature", "execution")
        result_data: dict[str, Any] = {"warnings": []}

        # Samael
        try:
            from malakhim.samael import diagnose_excess, get_rebalancing_instruction
            diag = diagnose_excess(response, [], 0.5, nature)
            if diag:
                result_data["samael"] = {
                    "sephirah_source": diag.sephirah_source,
                    "prescription": diag.prescription,
                    "severity": diag.severity,
                }
        except ImportError as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Ange incomplet
        try:
            from malakhim.samael import detect_incomplete_angel
            result_data["incomplete"] = detect_incomplete_angel(response, nature, 0.5)
        except ImportError:
            result_data["incomplete"] = False

        # Reshimo
        try:
            from malakhim.reshimo import record_reshimo
            record_reshimo(
                result_metadata={
                    "routing": preparation.get("routing", {}),
                    "shem_index": preparation.get("shem_index"),
                    "domain": kav.get("domain", "general"),
                    "samael": result_data.get("samael", {}),
                },
                response=response,
                score=0.5,
                success=True,
                incomplete=result_data.get("incomplete", False),
                prompt=prompt,
            )
        except ImportError as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return result_data

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _routing_metadata(decision: RoutingDecision) -> dict:
        return {
            "nature": decision.nature,
            "olam": decision.olam,
            "model": decision.model,
            "provider": decision.provider,
            "masakh_level": decision.masakh_level,
            "confidence": decision.confidence,
            "warnings": decision.warnings,
        }

    def _record_pekidah(
        self,
        result: MalakhResult,
        decision: RoutingDecision,
        kav: dict[str, Any],
        prompt: str,
    ) -> None:
        """Enregistrement Pekidah commun à tous les paths.

        Inclut la détection d'ange incomplet (Tanya ch. 39) :
        une réponse qui « fonctionne » mais est creuse, générique,
        superficielle — matière sans forme.
        """
        # ── Détection d'ange incomplet ────────────────────────────
        try:
            from malakhim.samael import detect_incomplete_angel
            if detect_incomplete_angel(result.response, decision.nature, result.score):
                result.incomplete = True
                result.metadata["incomplete_angel"] = True
                result.hitkalelut_warnings.append(
                    "Ange incomplet (Tanya ch. 39) : matière sans forme — "
                    "réponse techniquement fonctionnelle mais creuse"
                )
        except ImportError as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # ── Reshimo : la trace du Malakh dissous ──────────────────
        # Le cycle du Nehar Dinur se ferme : l'énergie remonte.
        try:
            from malakhim.reshimo import record_reshimo
            # Injecter le domain dans metadata pour le reshimo
            result.metadata["domain"] = kav.get("domain", "general")
            record_reshimo(
                result_metadata=result.metadata,
                response=result.response,
                score=result.score,
                success=result.success,
                incomplete=result.incomplete,
                prompt=prompt,
            )
        except ImportError as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        if self._registry is None or not decision.agent_id:
            return

        domain = kav.get("domain", "general")

        self._registry.record_outcome(
            agent_id=decision.agent_id,
            domain=domain,
            score=result.score,
        )

        if result.success and result.score > 0.7 and not result.incomplete:
            strategy = kav.get("strategy", decision.nature)
            self._registry.record_success(
                agent_id=decision.agent_id,
                domain=domain,
                strategy=strategy,
                kavvanah=kav,
                score=result.score,
            )

        if not result.success:
            error_type = "execution_failure"
            if result.hitkalelut_warnings:
                error_type = result.hitkalelut_warnings[0][:80]
            self._registry.record_failure(
                agent_id=decision.agent_id,
                domain=domain,
                error_type=error_type,
                prompt=prompt,
                score=result.score,
            )
