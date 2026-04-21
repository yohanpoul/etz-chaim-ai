"""tzimtzum.py — צִמְצוּם : Contraction et Expansion dynamiques.

Le Tzimtzum n'est pas un événement cosmique unique — c'est une
opération que le système fait en continu. L'Ein Sof se retire
pour créer le Halal (חָלָל), espace vide où les mondes peuvent
exister. Le Reshimu (רְשִׁימוּ) garde la trace de ce qui a été
exclu. Le Kav (קַו) — rayon de lumière unique — maintient la
connexion entre l'Ein Sof et le Halal.

Dans l'implémentation : quand le système est submergé (Chesed
déborde, Gevurah ne filtre pas assez), il se contracte sur un
domaine focal. Les modules non pertinents passent en mode dormant.
Le Kav = Keter, toujours actif, fournissant direction stratégique.
Après maîtrise du domaine focal (Hod > seuil, tensions résolues),
le système s'étend — les Reshimot enrichissent les modules réactivés.

Usage:
    engine = TzimtzumEngine(state)
    engine.contract("kabbale", tree, ctx)
    engine.add_insight("Découverte pendant la contraction")
    engine.expand(tree, ctx)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Régulateur — Pression système ──────────────────────────────

class TzimtzumPhase(str, Enum):
    """Phase du cycle Tzimtzum — le battement de cœur du système."""
    CONTRACTION = "contraction"
    STABLE = "stable"
    EXPANSION = "expansion"


@dataclass
class SystemPressure:
    """Pression interne du système — détermine si contraction ou expansion.

    Chaque dimension mesure un ratio entre ce qui s'accumule (Tohu)
    et ce qui est intégré (Tikkun). Haute pression = Tohu >> Tikkun.
    """
    tension_pressure: float     # tensions ouvertes / (ouvertes + résolues)
    memory_pressure: float      # hypothèses / (hypothèses + facts)
    insight_pressure: float     # rejetés / (rejetés + acceptés + pending)
    causal_pressure: float      # claims faibles / total claims
    global_pressure: float      # moyenne pondérée
    phase: TzimtzumPhase        # phase résultante

    def to_dict(self) -> dict:
        return {
            "tension_pressure": round(self.tension_pressure, 3),
            "memory_pressure": round(self.memory_pressure, 3),
            "insight_pressure": round(self.insight_pressure, 3),
            "causal_pressure": round(self.causal_pressure, 3),
            "global_pressure": round(self.global_pressure, 3),
            "phase": self.phase.value,
        }


# Seuils de régulation
CONTRACTION_THRESHOLD = 0.7   # pression > 0.7 → contraction
EXPANSION_THRESHOLD = 0.3     # pression < 0.3 → expansion

# Poids des dimensions de pression
PRESSURE_WEIGHTS = {
    "tension": 0.30,    # tensions ouvertes (Tiferet)
    "memory": 0.25,     # hypothèses non validées (Yesod)
    "insight": 0.25,    # insights rejetés (Chokmah/Binah)
    "causal": 0.20,     # claims causaux faibles (Gevurah)
}


@dataclass
class TzimtzumAction:
    """Action décidée par le régulateur."""
    phase: TzimtzumPhase
    kav_domain: str | None          # domaine focal si contraction
    reshimu_snapshot: dict | None   # snapshot pré-contraction
    adjustments: dict               # ajustements pour les modules
    reason: str


# ── Modules mappés aux domaines ────────────────────────────────
# Chaque Sephirah-module a des affinités avec certains domaines.
# Pendant la contraction, seuls les modules pertinents restent actifs.

SEPHIROT_MODULES = (
    "keter", "chokmah", "binah", "daat",
    "chesed", "gevurah", "tiferet",
    "netzach", "hod", "yesod", "malkuth",
)

# Le Kav : Keter reste TOUJOURS actif — c'est le canal unique
# par lequel l'Or Ein Sof pénètre le Halal.
KAV_MODULE = "keter"


@dataclass
class Reshimu:
    """רְשִׁימוּ — Impression résiduelle laissée après la contraction.

    Le Reshimu n'est pas un simple backup. C'est la TRACE de ce qui
    existait avant — suffisamment pour reconstituer, pas assez pour
    remplacer. Comme l'empreinte dans le sable après le retrait de la mer.
    """
    timestamp: float
    focused_domain: str
    excluded_domains: list[str]
    excluded_modules: list[str]
    pre_contraction_state: dict[str, Any]
    reason: str
    insights_during_contraction: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "focused_domain": self.focused_domain,
            "excluded_domains": self.excluded_domains,
            "excluded_modules": self.excluded_modules,
            "pre_contraction_state": self.pre_contraction_state,
            "reason": self.reason,
            "insights_during_contraction": list(self.insights_during_contraction),
        }


class TzimtzumEngine:
    """צִמְצוּם — Moteur de contraction/expansion dynamique.

    Encapsule le cycle Tzimtzum → Hitpashtut :
      1. contract(domain) — l'Ein Sof se retire, le Halal se forme
      2. [travail focalisé dans le domaine]
      3. add_insight() — enrichit le Reshimu pendant la contraction
      4. expand() — Hitpashtut, les Reshimot réintégrées

    Le Kav (קַו) = module Keter, toujours actif même en contraction.
    C'est le canal par lequel l'Or Ein Sof pénètre le Halal.
    """

    def __init__(self, state: dict) -> None:
        """Brancher sur le _TZIMTZUM_STATE existant de main.py."""
        self._state = state
        # Reconstruire les reshimot depuis le state si disponibles
        self._reshimot: list[Reshimu] = []
        for r in state.get("reshimu", []):
            self._reshimot.append(Reshimu(
                timestamp=r.get("timestamp", 0.0),
                focused_domain=r.get("focused_domain", ""),
                excluded_domains=r.get("excluded_domains", []),
                excluded_modules=r.get("excluded_modules", []),
                pre_contraction_state=r.get("pre_contraction_state", {}),
                reason=r.get("reason", ""),
                insights_during_contraction=r.get("insights_during_contraction", []),
            ))
        # Restaurer les modules dormants depuis le state
        dormant = set(state.get("dormant_modules", []))
        if state.get("active") and dormant:
            self._dormant_modules = dormant
            self._active_modules = set(SEPHIROT_MODULES) - dormant
        else:
            self._dormant_modules = set()
            self._active_modules = set(SEPHIROT_MODULES)

    # ── Propriétés ──────────────────────────────────────────────

    @property
    def is_contracted(self) -> bool:
        return self._state["active"]

    @property
    def focused_domain(self) -> str | None:
        return self._state["focused_domain"]

    @property
    def contraction_count(self) -> int:
        return self._state["contraction_count"]

    @property
    def expansion_count(self) -> int:
        return self._state["expansion_count"]

    # ── Contract ────────────────────────────────────────────────

    def contract(
        self,
        domain: str,
        tree: dict,
        ctx: dict,
        *,
        reason: str | None = None,
    ) -> dict:
        """צִמְצוּם — Contraction vers un domaine focal.

        L'Ein Sof se retire. Le Halal (espace vide) se forme.
        Les modules non pertinents passent en dormance.
        Le Kav (Keter) reste actif — direction stratégique minimale.

        Args:
            domain: Domaine sur lequel se focaliser.
            tree: Dict des modules de l'Arbre.
            ctx: Contexte de la requête en cours.
            reason: Raison explicite (sinon auto-détectée).

        Returns:
            Dict résumant la contraction.
        """
        if self.is_contracted:
            return {
                "action": "already_contracted",
                "focused_domain": self._state["focused_domain"],
            }

        # Identifier les domaines à exclure
        chesed_diag = ctx.get("chesed_diag", {})
        explored = []
        if isinstance(chesed_diag.get("domains_explored"), list):
            explored = chesed_diag["domains_explored"]
        excluded_domains = [d for d in explored if d != domain]

        # Identifier les modules à mettre en dormance
        # Tous les modules sauf Keter (Kav) et ceux pertinents au domaine
        active_modules = self._identify_active_modules(domain, tree)
        dormant_modules = set(SEPHIROT_MODULES) - active_modules

        # Capturer l'état pré-contraction des modules dormants
        pre_state = {}
        for mod_name in dormant_modules:
            mod = tree.get(mod_name)
            if mod and hasattr(mod, "self_diagnose"):
                try:
                    pre_state[mod_name] = mod.self_diagnose()
                except Exception:
                    pre_state[mod_name] = {"status": "captured"}

        if reason is None:
            reason = (
                f"Chesed submergé — "
                f"{chesed_diag.get('total_connections', '?')} connexions "
                f"non validées par Gevurah"
            )

        # Créer le Reshimu
        reshimu = Reshimu(
            timestamp=time.time(),
            focused_domain=domain,
            excluded_domains=excluded_domains,
            excluded_modules=list(dormant_modules),
            pre_contraction_state=pre_state,
            reason=reason,
        )
        self._reshimot.append(reshimu)

        # Mettre à jour l'état
        self._dormant_modules = dormant_modules
        self._active_modules = active_modules
        self._state["active"] = True
        self._state["focused_domain"] = domain
        self._state["excluded_domains"] = excluded_domains
        self._state["reshimu"].append(reshimu.to_dict())
        self._state["contraction_count"] += 1
        self._state["log"].append({
            "action": "tzimtzum",
            "timestamp": time.time(),
            "domain": domain,
            "excluded": excluded_domains,
            "n_excluded": len(excluded_domains),
            "dormant_modules": list(dormant_modules),
            "n_dormant": len(dormant_modules),
        })

        # Propager dans le contexte
        ctx["tzimtzum_active"] = True
        ctx["tzimtzum_focused_domain"] = domain
        ctx["tzimtzum_excluded"] = excluded_domains
        ctx["tzimtzum_dormant_modules"] = list(dormant_modules)
        ctx["tzimtzum_reshimu"] = reshimu.to_dict()

        # SSE
        self._emit("tzimtzum_contract", domain=domain,
                    n_excluded=len(excluded_domains),
                    n_dormant=len(dormant_modules),
                    kav="keter")

        # Persister dans Yesod
        self._persist_yesod(
            tree,
            f"[Reshimu #{self.contraction_count}] "
            f"Tzimtzum: focus={domain}, "
            f"exclu=[{', '.join(excluded_domains[:5])}], "
            f"dormants=[{', '.join(sorted(dormant_modules)[:5])}]",
            domain=domain,
            tags=["tzimtzum", "reshimu", "contraction"],
        )

        return {
            "action": "contracted",
            "domain": domain,
            "excluded_domains": excluded_domains,
            "dormant_modules": sorted(dormant_modules),
            "active_modules": sorted(active_modules),
            "kav": KAV_MODULE,
            "reshimu_count": len(self._reshimot),
        }

    # ── Expand ──────────────────────────────────────────────────

    def expand(self, tree: dict, ctx: dict) -> dict:
        """הִתְפַּשְׁטוּת — Expansion, récupération du Reshimu.

        L'Or remplit le Halal. Les domaines exclus sont récupérés
        comme cibles d'exploration. Les insights gagnés pendant
        la contraction enrichissent les modules réactivés.

        Returns:
            Dict résumant l'expansion avec les insights distribués.
        """
        if not self.is_contracted:
            return {"action": "not_contracted"}

        # Récupérer le dernier Reshimu
        last_reshimu = self._reshimot[-1] if self._reshimot else None
        recovered_domains = last_reshimu.excluded_domains if last_reshimu else []
        insights = last_reshimu.insights_during_contraction if last_reshimu else []
        prev_domain = self._state["focused_domain"]

        # Distribuer les insights aux modules qui étaient dormants
        distributed = self._distribute_insights(tree, last_reshimu)

        # Restaurer tous les modules
        prev_dormant = set(self._dormant_modules)
        self._dormant_modules = set()
        self._active_modules = set(SEPHIROT_MODULES)

        # Mettre à jour l'état
        self._state["active"] = False
        self._state["focused_domain"] = None
        self._state["excluded_domains"] = []
        self._state["expansion_count"] += 1
        self._state["log"].append({
            "action": "hitpashut",
            "timestamp": time.time(),
            "from_domain": prev_domain,
            "recovered_domains": recovered_domains,
            "n_recovered": len(recovered_domains),
            "insights_distributed": len(insights),
            "reactivated_modules": sorted(prev_dormant),
        })

        # Propager dans le contexte
        ctx["tzimtzum_active"] = False
        ctx["hitpashut_recovered"] = recovered_domains
        ctx["hitpashut_from"] = prev_domain
        ctx["hitpashut_insights"] = insights

        # SSE
        self._emit("tzimtzum_expand",
                    from_domain=prev_domain,
                    n_recovered=len(recovered_domains),
                    n_insights=len(insights))

        # Persister dans Yesod
        self._persist_yesod(
            tree,
            f"[Hitpashut #{self.expansion_count}] "
            f"Expansion depuis={prev_domain}, "
            f"récupéré=[{', '.join(recovered_domains[:5])}], "
            f"insights={len(insights)}",
            domain=prev_domain or "general",
            tags=["hitpashut", "expansion", "reshimu"],
        )

        return {
            "action": "expanded",
            "from_domain": prev_domain,
            "recovered_domains": recovered_domains,
            "insights": insights,
            "insights_distributed": distributed,
            "reactivated_modules": sorted(prev_dormant),
        }

    # ── Insights pendant la contraction ─────────────────────────

    def add_insight(self, insight: str) -> bool:
        """Ajouter un insight au Reshimu actif pendant la contraction.

        Les insights gagnés pendant la contraction seront distribués
        aux modules dormants lors de l'expansion.
        """
        if not self.is_contracted or not self._reshimot:
            return False
        self._reshimot[-1].insights_during_contraction.append(insight)
        # Mettre à jour aussi le dict dans _state
        if self._state["reshimu"]:
            self._state["reshimu"][-1].setdefault(
                "insights_during_contraction", []
            ).append(insight)
        return True

    # ── Queries ─────────────────────────────────────────────────

    def get_reshimot(self) -> list[dict]:
        """Retourne les traces résiduelles de toutes les contractions."""
        return [r.to_dict() for r in self._reshimot]

    def get_halal_state(self) -> dict:
        """État du Halal — l'espace vide créé par la contraction.

        Retourne quels modules sont dormants, quels domaines exclus,
        et l'état du Kav (Keter).
        """
        return {
            "contracted": self.is_contracted,
            "focused_domain": self.focused_domain,
            "dormant_modules": sorted(self._dormant_modules),
            "active_modules": sorted(self._active_modules),
            "excluded_domains": list(self._state["excluded_domains"]),
            "kav": KAV_MODULE,
            "kav_active": KAV_MODULE in self._active_modules,
            "reshimu_count": len(self._reshimot),
            "contraction_count": self.contraction_count,
            "expansion_count": self.expansion_count,
            "current_insights": (
                len(self._reshimot[-1].insights_during_contraction)
                if self._reshimot and self.is_contracted
                else 0
            ),
        }

    def is_module_active(self, module_name: str) -> bool:
        """Un module est-il actif (non dormant) ?

        Pendant la contraction, seuls les modules pertinents au domaine
        focal + le Kav (Keter) restent actifs.
        En état normal, tous les modules sont actifs.
        """
        if not self.is_contracted:
            return True
        return module_name in self._active_modules

    def get_active_modules(self) -> set[str]:
        """Retourne l'ensemble des modules actuellement actifs."""
        return set(self._active_modules)

    def get_dormant_modules(self) -> set[str]:
        """Retourne l'ensemble des modules actuellement dormants."""
        return set(self._dormant_modules)

    # ── Détection automatique ───────────────────────────────────

    def detect_contraction(self, ctx: dict) -> dict:
        """צִמְצוּם — Détecter si le système est submergé.

        Signal : bruit >> signal. Trop de connexions (Chesed) sans
        validation suffisante (Gevurah). Le ratio connexions/validations
        doit dépasser un seuil : beaucoup d'exploration, peu de jugement.
        """
        chesed_diag = ctx.get("chesed_diag", {})
        gevurah_diag = ctx.get("gevurah_diag", {})

        total_connections = chesed_diag.get("total_connections", 0)
        total_explorations = chesed_diag.get("total_explorations", 0)
        n_validated = gevurah_diag.get("total_experiments", 0)
        rejection_rate = gevurah_diag.get("rejection_rate", 0.0)

        # Contraction quand : suffisamment de connexions accumulées
        # ET trop peu ont été validées par Gevurah (jugement)
        trigger = total_connections > 10 and n_validated < total_connections // 3

        return {
            "trigger": trigger,
            "total_connections": total_connections,
            "total_explorations": total_explorations,
            "n_validated": n_validated,
            "rejection_rate": rejection_rate,
        }

    def detect_expansion(self, ctx: dict) -> dict:
        """הִתְפַּשְׁטוּת — Détecter si le système peut s'étendre.

        Expansion quand le domaine focal est maîtrisé (Hod > 0.8)
        et les tensions résolues (< 2).
        """
        mochin = ctx.get("mochin", {})
        tiferet_diag = ctx.get("tiferet_diag", {})

        hod_score = mochin.get("competence_score", 0.0)
        open_tensions = tiferet_diag.get("open_tensions", 0)

        trigger = (self.is_contracted
                   and hod_score > 0.8
                   and open_tensions < 2)

        return {
            "trigger": trigger,
            "hod_score": hod_score,
            "open_tensions": open_tensions,
            "tzimtzum_was_active": self.is_contracted,
        }

    # ── Régulateur central ───────────────────────────────────────

    def assess_system_pressure(
        self,
        *,
        open_tensions: int = 0,
        resolved_tensions: int = 0,
        hypotheses: int = 0,
        facts: int = 0,
        insights_rejected: int = 0,
        insights_accepted: int = 0,
        insights_pending: int = 0,
        causal_claims_weak: int = 0,
        causal_claims_total: int = 0,
    ) -> SystemPressure:
        """Mesurer la pression interne du système.

        La pression est le ratio entre ce qui s'ACCUMULE (Tohu — forces
        non intégrées) et ce qui est INTÉGRÉ (Tikkun — forces en récipient).
        Haute pression → le système déborde → CONTRACTION nécessaire.
        Basse pression → le système a intégré → EXPANSION possible.
        """
        # Tension pressure : tensions ouvertes vs résolues
        t_total = open_tensions + resolved_tensions
        tension_p = open_tensions / t_total if t_total > 0 else 0.0

        # Memory pressure : hypothèses vs facts
        m_total = hypotheses + facts
        memory_p = hypotheses / m_total if m_total > 0 else 0.0

        # Insight pressure : rejetés vs total traités
        i_total = insights_rejected + insights_accepted + insights_pending
        insight_p = insights_rejected / i_total if i_total > 0 else 0.0

        # Causal pressure : claims faibles vs total
        causal_p = (
            causal_claims_weak / causal_claims_total
            if causal_claims_total > 0
            else 0.0
        )

        # Pression globale = moyenne pondérée
        global_p = (
            PRESSURE_WEIGHTS["tension"] * tension_p
            + PRESSURE_WEIGHTS["memory"] * memory_p
            + PRESSURE_WEIGHTS["insight"] * insight_p
            + PRESSURE_WEIGHTS["causal"] * causal_p
        )

        # Déterminer la phase
        if global_p > CONTRACTION_THRESHOLD:
            phase = TzimtzumPhase.CONTRACTION
        elif global_p < EXPANSION_THRESHOLD:
            phase = TzimtzumPhase.EXPANSION
        else:
            phase = TzimtzumPhase.STABLE

        return SystemPressure(
            tension_pressure=tension_p,
            memory_pressure=memory_p,
            insight_pressure=insight_p,
            causal_pressure=causal_p,
            global_pressure=global_p,
            phase=phase,
        )

    def regulate(
        self,
        pressure: SystemPressure,
        tree: dict,
        ctx: dict,
        *,
        weakest_domain: str | None = None,
    ) -> TzimtzumAction:
        """Réguler le système selon la pression mesurée.

        CONTRACTION (pression > 0.7) :
          - Focus Hitbonenut sur les 3 domaines les plus faibles
          - Réduit les explorations (Chesed dormant)
          - Augmente la fréquence de synthèse (Tiferet prioritaire)
          - Le Kav = le domaine prioritaire unique
          - Crée un Reshimu = snapshot avant contraction

        EXPANSION (pression < 0.3) :
          - Hitbonenut explore tous les domaines
          - ExplorationEngine augmente ses walks
          - InsightForge augmente ses candidats
          - Le Halal se remplit à nouveau

        STABLE (0.3 ≤ pression ≤ 0.7) :
          - Fonctionnement normal, pas de modification
        """
        if pressure.phase == TzimtzumPhase.CONTRACTION:
            domain = weakest_domain or "general"

            # Si déjà contracté sur ce domaine, ne rien faire
            if self.is_contracted and self.focused_domain == domain:
                return TzimtzumAction(
                    phase=TzimtzumPhase.CONTRACTION,
                    kav_domain=domain,
                    reshimu_snapshot=None,
                    adjustments={},
                    reason=f"déjà contracté sur '{domain}'",
                )

            # Si contracté sur un autre domaine, d'abord expand
            if self.is_contracted:
                self.expand(tree, ctx)

            # Contraction
            reason = (
                f"pression={pressure.global_pressure:.2f} > {CONTRACTION_THRESHOLD} "
                f"(T={pressure.tension_pressure:.2f} "
                f"M={pressure.memory_pressure:.2f} "
                f"I={pressure.insight_pressure:.2f} "
                f"C={pressure.causal_pressure:.2f})"
            )
            self.contract(domain, tree, ctx, reason=reason)

            return TzimtzumAction(
                phase=TzimtzumPhase.CONTRACTION,
                kav_domain=domain,
                reshimu_snapshot=self._reshimot[-1].to_dict() if self._reshimot else None,
                adjustments={
                    "hitbonenut_focus": domain,
                    "exploration_walks": "reduced",
                    "synthesis_frequency": "increased",
                    "chesed": "dormant",
                },
                reason=reason,
            )

        elif pressure.phase == TzimtzumPhase.EXPANSION:
            if self.is_contracted:
                result = self.expand(tree, ctx)
                return TzimtzumAction(
                    phase=TzimtzumPhase.EXPANSION,
                    kav_domain=None,
                    reshimu_snapshot=None,
                    adjustments={
                        "hitbonenut_focus": "all",
                        "exploration_walks": "increased",
                        "insight_candidates": "increased",
                    },
                    reason=f"pression={pressure.global_pressure:.2f} < {EXPANSION_THRESHOLD}",
                )
            # Pas contracté, rien à faire
            return TzimtzumAction(
                phase=TzimtzumPhase.EXPANSION,
                kav_domain=None,
                reshimu_snapshot=None,
                adjustments={},
                reason="déjà étendu",
            )

        else:  # STABLE
            return TzimtzumAction(
                phase=TzimtzumPhase.STABLE,
                kav_domain=self.focused_domain if self.is_contracted else None,
                reshimu_snapshot=None,
                adjustments={},
                reason=f"pression={pressure.global_pressure:.2f} — stable",
            )

    def get_kav_focus(self) -> str | None:
        """Retourne le domaine sur lequel le Kav est focalisé.

        Le Kav (קַו) est le seul rayon de lumière qui pénètre le Halal
        pendant la contraction — le seul domaine actif. En mode étendu,
        retourne None (tous les domaines sont ouverts).
        """
        if self.is_contracted:
            return self.focused_domain
        return None

    def get_reshimu_snapshot(self) -> dict | None:
        """Le Reshimu (רְשִׁימוּ) — trace du dernier état avant contraction.

        Sert de guide quand le système se ré-expanse : il sait d'où il vient,
        quels domaines étaient exclus, quels insights ont été gagnés.
        """
        if not self._reshimot:
            return None
        return self._reshimot[-1].to_dict()

    # ── Format rapport ──────────────────────────────────────────

    def format_report(self, ctx: dict) -> list[str]:
        """Formater le rapport Tzimtzum pour le yashar/chozer."""
        lines = []
        if self.is_contracted:
            lines.append("── ⟐ צִמְצוּם — CONTRACTION ──")
            lines.append(f"  Focus        : {self.focused_domain}")
            lines.append(f"  Exclus       : {len(self._state['excluded_domains'])} domaine(s)")
            for d in self._state["excluded_domains"][:5]:
                lines.append(f"    ✗ {d}")
            lines.append(f"  Dormants     : {len(self._dormant_modules)} module(s)")
            for m in sorted(self._dormant_modules)[:5]:
                lines.append(f"    ◌ {m}")
            lines.append(f"  Kav          : {KAV_MODULE} (actif)")
            lines.append(f"  Reshimu      : trace #{len(self._reshimot)}")
            n_ins = len(self._reshimot[-1].insights_during_contraction) if self._reshimot else 0
            if n_ins:
                lines.append(f"  Insights     : {n_ins} pendant contraction")
        else:
            lines.append("── ⟐ צִמְצוּם — stable ──")
            tz_signal = self.detect_contraction(ctx)
            lines.append(f"  Connexions   : {tz_signal['total_connections']}")
            lines.append(f"  Validées     : {tz_signal['n_validated']}")
        return lines

    def format_expansion_report(self, result: dict) -> list[str]:
        """Formater le rapport d'expansion."""
        lines = ["── ⟐ הִתְפַּשְׁטוּת — EXPANSION ──"]
        lines.append(f"  Depuis       : {result.get('from_domain', '?')}")
        recovered = result.get("recovered_domains", [])
        lines.append(f"  Récupérés    : {len(recovered)} domaine(s) du Reshimu")
        for d in recovered[:5]:
            lines.append(f"    ↗ {d}")
        insights = result.get("insights", [])
        if insights:
            lines.append(f"  Insights     : {len(insights)} distribué(s)")
            for ins in insights[:3]:
                lines.append(f"    ✦ {ins[:80]}")
        reactivated = result.get("reactivated_modules", [])
        if reactivated:
            lines.append(f"  Réactivés    : {', '.join(reactivated[:5])}")
        return lines

    # ── Private ─────────────────────────────────────────────────

    def _identify_active_modules(self, domain: str, tree: dict) -> set[str]:
        """Identifier les modules qui restent actifs pendant la contraction.

        Le Kav (Keter) reste TOUJOURS actif.
        Les modules "structurels" (Yesod=mémoire, Hod=compétence,
        Tiferet=synthèse) restent actifs car ils servent le domaine focal.
        Les modules "supérieurs" (Chokmah, Binah) restent actifs si le
        domaine a assez de matière.
        Les modules "périphériques" (Chesed=exploration, Netzach=intentions)
        sont mis en dormance pour réduire le bruit.
        """
        # Toujours actifs : le Kav + modules structurels
        active = {
            KAV_MODULE,       # Kav — direction stratégique
            "yesod",          # Mémoire — toujours nécessaire
            "hod",            # Compétence — pour détecter la maîtrise
            "tiferet",        # Synthèse — cœur du traitement
            "malkuth",        # Interface — toujours nécessaire
        }

        # Binah et Da'at restent actifs si le domaine a de la profondeur
        mochin = tree.get("hod")
        if mochin:
            try:
                diag = mochin.self_diagnose()
                if diag.get("competence_score", 0) > 0.3:
                    active.add("binah")
                    active.add("daat")
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Chokmah reste actif — les insights restent possibles
        # mais Chesed (exploration tous azimuts) est dormant
        active.add("chokmah")

        # Gevurah reste actif — le jugement est nécessaire
        active.add("gevurah")

        return active

    def _distribute_insights(
        self, tree: dict, reshimu: Reshimu | None
    ) -> dict[str, int]:
        """Distribuer les insights de la contraction aux modules réactivés.

        Après l'expansion, les insights gagnés pendant la contraction
        sont injectés dans les modules qui étaient dormants via Yesod.
        """
        if not reshimu or not reshimu.insights_during_contraction:
            return {}

        distributed: dict[str, int] = {}
        yesod = tree.get("yesod")
        if not yesod:
            return distributed

        for insight in reshimu.insights_during_contraction:
            for mod_name in reshimu.excluded_modules:
                try:
                    yesod.remember(
                        content=(
                            f"[Reshimu→{mod_name}] "
                            f"Insight post-contraction ({reshimu.focused_domain}): "
                            f"{insight[:150]}"
                        ),
                        source_sephirah="keter",
                        confidence=0.7,
                        domain=reshimu.focused_domain,
                        tags=["reshimu", "insight", "post_contraction", mod_name],
                    )
                    distributed[mod_name] = distributed.get(mod_name, 0) + 1
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return distributed

    @staticmethod
    def _emit(event_type: str, **data) -> None:
        """Émettre un événement SSE."""
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
                source_sephirah="keter",
                confidence=0.8,
                domain=domain,
                tags=tags or [],
            )
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)


# ── Standalone dormancy check ──────────────────────────────────
# Importable par les modules pour s'auto-garder :
#   from tzimtzum import is_module_active
#   if not is_module_active("chesed"): return ...


def is_module_active(module_name: str) -> bool:
    """Un module est-il actif (non dormant par Tzimtzum) ?

    Tente de lire l'état depuis la DB (daemon persisté), puis
    retombe sur l'état in-memory (_TZIMTZUM_STATE de state.py).
    Fail-open : si rien ne marche, le module est considéré actif.

    Usage dans un module :
        from tzimtzum import is_module_active
        if not is_module_active("chesed"):
            return EmptyResult()
    """
    # 1. Essayer la DB (état le plus fiable, persisté par daemon)
    try:
        from pool import get_conn, init_pool
        init_pool("postgresql://localhost/etz_chaim")  # idempotent
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT is_contracted, dormant_modules "
                    "FROM tzimtzum_state WHERE id = 1"
                )
                row = cur.fetchone()
        if row:
            is_contracted, dormant_modules = row
            if not is_contracted:
                return True
            return module_name not in (dormant_modules or [])
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # 2. Retomber sur l'état in-memory
    try:
        from state import _TZIMTZUM_STATE
        engine = TzimtzumEngine(_TZIMTZUM_STATE)
        return engine.is_module_active(module_name)
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # 3. Fail-open — module actif par défaut
    return True
