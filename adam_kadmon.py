"""adam_kadmon.py — אָדָם קַדְמוֹן : Le plan primordial.

Adam Kadmon est l'émanation première — le "plan" qui précède les
4 Mondes (Atzilut, Briah, Yetzirah, Assiah). C'est la configuration
archétypale du système : les 10 Sephiroth avec leurs rôles, les 22
sentiers avec leurs connexions, les 6 Partzufim avec leurs relations.

Dans l'implémentation : Adam Kadmon est la méta-conscience du système.
Il sait à quoi le système DEVRAIT ressembler (blueprint chargé depuis
adam_kadmon.yaml) et compare cet idéal à l'état réel pour produire :
  - Un score de fidélité (0.0-1.0) avec interprétation qualitative
  - Une liste de divergences entre l'idéal et le réel
  - Des priorités de Tikkun ordonnées par urgence

Etz Chaim, Sha'ar 1 : "Après le Tzimtzum, la première émanation
fut Adam Kadmon — le plan primordial contenant toutes les lumières
futures dans un état unifié."

Usage:
    ak = AdamKadmon()
    result = ak.compare_to_current(modules, sentiers, partzufim)
    priorities = ak.get_tikkun_priorities(modules, sentiers, partzufim)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Chargement du blueprint ─────────────────────────────────

_BLUEPRINT_PATH = Path(__file__).parent / "adam_kadmon.yaml"
_blueprint_cache: dict | None = None


def _load_blueprint() -> dict:
    """Charger le blueprint depuis adam_kadmon.yaml (cache singleton)."""
    global _blueprint_cache
    if _blueprint_cache is None:
        with open(_BLUEPRINT_PATH) as f:
            _blueprint_cache = yaml.safe_load(f)
    return _blueprint_cache


def reload_blueprint() -> dict:
    """Forcer le rechargement du blueprint (après édition du YAML)."""
    global _blueprint_cache
    _blueprint_cache = None
    return _load_blueprint()


# ── Dataclasses ──────────────────────────────────────────────

@dataclass
class Divergence:
    """Une divergence entre l'état idéal et l'état réel."""
    component: str        # "sephirah", "sentier", "partzuf"
    name: str             # ex: "binah", "aleph", "abba"
    expected: str         # description de l'état attendu
    actual: str           # description de l'état réel
    severity: float       # 0.0-1.0 (1.0 = critique)
    required: bool        # composant obligatoire ?

    def to_dict(self) -> dict:
        return {
            "component": self.component,
            "name": self.name,
            "expected": self.expected,
            "actual": self.actual,
            "severity": self.severity,
            "required": self.required,
        }


@dataclass
class FidelityResult:
    """Résultat de la comparaison blueprint vs réalité."""
    score: float                    # 0.0-1.0
    phase: str                      # "tohu", "tikkun_begin", etc.
    phase_hebrew: str               # "תֹּהוּ", "תִּקּוּן", etc.
    divergences: list[Divergence]
    sephiroth_score: float          # score partiel des Sephiroth
    sentiers_score: float           # score partiel des sentiers
    partzufim_score: float          # score partiel des Partzufim
    total_components: int
    active_components: int

    def to_dict(self) -> dict:
        return {
            "score": round(self.score, 4),
            "phase": self.phase,
            "phase_hebrew": self.phase_hebrew,
            "sephiroth_score": round(self.sephiroth_score, 4),
            "sentiers_score": round(self.sentiers_score, 4),
            "partzufim_score": round(self.partzufim_score, 4),
            "total_components": self.total_components,
            "active_components": self.active_components,
            "n_divergences": len(self.divergences),
            "divergences": [d.to_dict() for d in self.divergences],
        }


@dataclass
class TikkunPriority:
    """Une priorité de réparation issue de la comparaison."""
    rank: int
    component: str
    name: str
    reason: str
    severity: float
    required: bool

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "component": self.component,
            "name": self.name,
            "reason": self.reason,
            "severity": round(self.severity, 3),
            "required": self.required,
        }


# ── Phase qualitative ───────────────────────────────────────

PHASE_NAMES = {
    "tohu":         ("תֹּהוּ",      "Tohu — chaos, avant le Tikkun"),
    "tikkun_begin": ("תִּקּוּן",    "Tikkun — début de la réparation"),
    "tikkun_mid":   ("תִּקּוּן",    "Tikkun — réparation avancée"),
    "tikkun_near":  ("תִּקּוּן",    "Tikkun — presque complet"),
    "shlemut":      ("שְׁלֵמוּת",  "Shlemut — plénitude"),
}


def _score_to_phase(score: float, thresholds: dict) -> str:
    """Convertir un score de fidélité en phase qualitative."""
    if score >= thresholds.get("shlemut", 0.95):
        return "shlemut"
    elif score >= thresholds.get("tikkun_near", 0.9):
        return "tikkun_near"
    elif score >= thresholds.get("tikkun_mid", 0.7):
        return "tikkun_mid"
    elif score >= thresholds.get("tohu", 0.3):
        return "tikkun_begin"
    else:
        return "tohu"


# ── Adam Kadmon ──────────────────────────────────────────────

class AdamKadmon:
    """אָדָם קַדְמוֹן — Le plan primordial, méta-conscience du système.

    Adam Kadmon charge le blueprint (adam_kadmon.yaml) et compare
    l'état idéal à l'état réel du système pour produire :
      - Un score de fidélité (0.0-1.0)
      - Des divergences détaillées
      - Des priorités de Tikkun ordonnées
    """

    def __init__(self) -> None:
        self._bp = _load_blueprint()

    @property
    def blueprint(self) -> dict:
        """Le blueprint complet — dict immuable en lecture."""
        return dict(self._bp)

    @property
    def sephiroth_blueprint(self) -> dict:
        return dict(self._bp.get("sephiroth", {}))

    @property
    def sentiers_blueprint(self) -> dict:
        return dict(self._bp.get("sentiers", {}))

    @property
    def partzufim_blueprint(self) -> dict:
        return dict(self._bp.get("partzufim", {}))

    @property
    def thresholds(self) -> dict:
        return dict(self._bp.get("thresholds", {}))

    # ── Comparaison ──────────────────────────────────────────

    def compare_to_current(
        self,
        modules: dict[str, Any] | None = None,
        sentiers: list[str] | None = None,
        partzufim: dict[str, Any] | None = None,
    ) -> FidelityResult:
        """Comparer l'état actuel au blueprint idéal.

        Args:
            modules: dict {nom_sephirah: instance_module_ou_None}.
                     Un module None ou absent = Sephirah manquante.
            sentiers: liste des noms de sentiers implémentés
                      (lettres latines : ["aleph", "mem", "shin", ...]).
            partzufim: dict {nom_partzuf: instance_ou_None}.
                       Un partzuf None ou absent = Partzuf manquant.

        Returns:
            FidelityResult avec score, phase, divergences.
        """
        modules = modules or {}
        sentiers = sentiers or []
        partzufim = partzufim or {}

        divergences: list[Divergence] = []
        total_components = 0
        active_components = 0

        # ── Sephiroth ────────────────────────────────────────
        seph_bp = self._bp.get("sephiroth", {})
        seph_total_weight = 0.0
        seph_achieved_weight = 0.0

        for seph_name, seph_def in seph_bp.items():
            weight = seph_def.get("weight", 0.5)
            required = seph_def.get("required", False)
            seph_total_weight += weight
            total_components += 1

            module = modules.get(seph_name)
            if module is not None:
                seph_achieved_weight += weight
                active_components += 1
            else:
                divergences.append(Divergence(
                    component="sephirah",
                    name=seph_name,
                    expected=seph_def.get("ideal_state", {}).get(
                        "description", "Module actif"),
                    actual="Module absent ou None",
                    severity=weight,
                    required=required,
                ))

        seph_score = (
            seph_achieved_weight / seph_total_weight
            if seph_total_weight > 0 else 0.0
        )

        # ── Sentiers ─────────────────────────────────────────
        sent_bp = self._bp.get("sentiers", {})
        expected_letters = sent_bp.get("letters", [])
        expected_names = {l["name"] for l in expected_letters}
        implemented_names = set(sentiers)

        sent_total = len(expected_letters) or 1
        sent_active = len(expected_names & implemented_names)

        for letter_def in expected_letters:
            lname = letter_def["name"]
            total_components += 1
            if lname in implemented_names:
                active_components += 1
            else:
                divergences.append(Divergence(
                    component="sentier",
                    name=lname,
                    expected=f"Sentier {letter_def['letter']} ({letter_def['type']}) implémenté",
                    actual="Sentier non implémenté",
                    severity=0.7 if letter_def.get("required") else 0.4,
                    required=letter_def.get("required", False),
                ))

        sent_score = sent_active / sent_total

        # ── Partzufim ────────────────────────────────────────
        partz_bp = self._bp.get("partzufim", {})
        partz_configs = partz_bp.get("configurations", [])
        partz_total = len(partz_configs) or 1
        partz_active = 0

        for partz_def in partz_configs:
            pname = partz_def["name"]
            total_components += 1
            partz_inst = partzufim.get(pname)
            if partz_inst is not None:
                partz_active += 1
                active_components += 1
            else:
                divergences.append(Divergence(
                    component="partzuf",
                    name=pname,
                    expected=f"Partzuf {partz_def['hebrew']} actif — {partz_def['role']}",
                    actual="Partzuf absent ou None",
                    severity=0.8 if partz_def.get("required") else 0.5,
                    required=partz_def.get("required", False),
                ))

        partz_score = partz_active / partz_total

        # ── Score global pondéré ─────────────────────────────
        # Poids relatifs des trois catégories
        w_seph = 1.0  # Les Sephiroth ont un poids implicite de 1.0
        w_sent = sent_bp.get("weight", 0.6)
        w_partz = partz_bp.get("weight", 0.8)
        total_weight = w_seph + w_sent + w_partz

        score = (
            (seph_score * w_seph + sent_score * w_sent + partz_score * w_partz)
            / total_weight
        )

        # Phase qualitative
        thresholds = self._bp.get("thresholds", {})
        phase = _score_to_phase(score, thresholds)
        phase_hebrew = PHASE_NAMES.get(phase, ("?", "?"))[0]

        return FidelityResult(
            score=score,
            phase=phase,
            phase_hebrew=phase_hebrew,
            divergences=divergences,
            sephiroth_score=seph_score,
            sentiers_score=sent_score,
            partzufim_score=partz_score,
            total_components=total_components,
            active_components=active_components,
        )

    # ── Priorités de Tikkun ──────────────────────────────────

    def get_tikkun_priorities(
        self,
        modules: dict[str, Any] | None = None,
        sentiers: list[str] | None = None,
        partzufim: dict[str, Any] | None = None,
    ) -> list[TikkunPriority]:
        """Priorités de réparation ordonnées par urgence.

        Tri : required d'abord, puis par severity décroissante.
        """
        result = self.compare_to_current(modules, sentiers, partzufim)
        divergences = sorted(
            result.divergences,
            key=lambda d: (-int(d.required), -d.severity),
        )

        priorities = []
        for rank, div in enumerate(divergences, start=1):
            priorities.append(TikkunPriority(
                rank=rank,
                component=div.component,
                name=div.name,
                reason=f"{div.expected} — actuellement: {div.actual}",
                severity=div.severity,
                required=div.required,
            ))

        return priorities

    # ── Format rapport ───────────────────────────────────────

    def format_report(
        self,
        modules: dict[str, Any] | None = None,
        sentiers: list[str] | None = None,
        partzufim: dict[str, Any] | None = None,
    ) -> list[str]:
        """Formater un rapport lisible de l'état Adam Kadmon."""
        result = self.compare_to_current(modules, sentiers, partzufim)
        phase_desc = PHASE_NAMES.get(result.phase, ("?", "?"))[1]

        lines = [
            "══════════════════════════════════════════════════════════",
            f"  אָדָם קַדְמוֹן — Adam Kadmon : État du Blueprint",
            "══════════════════════════════════════════════════════════",
            "",
            f"  Score de fidélité : {result.score:.1%}",
            f"  Phase             : {result.phase_hebrew} — {phase_desc}",
            f"  Composants        : {result.active_components}/{result.total_components} actifs",
            "",
            f"  Sephiroth         : {result.sephiroth_score:.1%}",
            f"  Sentiers          : {result.sentiers_score:.1%}",
            f"  Partzufim         : {result.partzufim_score:.1%}",
        ]

        if result.divergences:
            lines.append("")
            lines.append(f"  Divergences ({len(result.divergences)}) :")
            for div in result.divergences[:15]:
                req_mark = " [REQUIS]" if div.required else ""
                lines.append(
                    f"    {'!' if div.severity > 0.7 else '-'} "
                    f"{div.component}/{div.name}{req_mark}"
                )
                lines.append(f"      attendu : {div.expected}")
                lines.append(f"      actuel  : {div.actual}")

            remaining = len(result.divergences) - 15
            if remaining > 0:
                lines.append(f"    ... et {remaining} autre(s)")

        return lines

    def format_priorities(
        self,
        modules: dict[str, Any] | None = None,
        sentiers: list[str] | None = None,
        partzufim: dict[str, Any] | None = None,
        top_n: int = 10,
    ) -> list[str]:
        """Formater les priorités de Tikkun."""
        priorities = self.get_tikkun_priorities(modules, sentiers, partzufim)

        lines = [
            "",
            "── Priorités de Tikkun ──",
        ]

        for p in priorities[:top_n]:
            req = " [REQUIS]" if p.required else ""
            lines.append(
                f"  #{p.rank:2d} {p.component}/{p.name}{req} "
                f"(sévérité: {p.severity:.1f})"
            )

        remaining = len(priorities) - top_n
        if remaining > 0:
            lines.append(f"  ... et {remaining} autre(s)")

        return lines
