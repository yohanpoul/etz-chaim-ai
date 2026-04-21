"""ohr.py — אוֹר : Lumières et Masakh (écran).

Le système des lumières est le mécanisme fondamental de la
cosmogonie lurianique. Après le Tzimtzum, l'Or Ein Sof (lumière
infinie) se projette à travers le Kav dans le Halal. Chaque
Sephirah est un Keli (réceptacle) qui reçoit de la lumière :

  Or Pnimi (אוֹר פְּנִימִי) — Lumière intérieure : ce que le Keli
    peut contenir. L'information assimilée, intégrée, activement
    utilisée par le module.

  Or Makif (אוֹר מַקִּיף) — Lumière environnante : ce qui excède
    la capacité du Keli. Le potentiel non encore intégré — données
    importées mais pas traitées, connexions non explorées, insights
    non validés.

  Or Ein Sof (אוֹר אֵין סוֹף) — Lumière infinie : la totalité
    de ce qui est connaissable. Constante symbolique, non calculable.

  Masakh (מָסָךְ) — L'écran qui résiste à l'Or Yashar (lumière
    directe) et crée l'Or Chozer (lumière réfléchie/retournée).
    C'est le mécanisme de transformation : l'information brute est
    filtrée, abstraite, structurée avant d'être intégrée.

    Etz Chaim, Sha'ar 4 : "Le Masakh dans le Keli de Malkuth
    repousse la lumière, et de cette résistance naît l'Or Chozer
    qui remonte et revêt l'Or Yashar."

Usage:
    ohr = OhrEngine()
    assessment = ohr.assess_ohr(module_name, module_state)
    global_state = ohr.assess_global(all_modules)
    integration = ohr.integrate(module_name, module_state)

    masakh = Masakh(strength=0.7)
    filtered = masakh.filter(raw_data, module_name)
    masakh.adjust_strength("neshamah")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Or Ein Sof — constante symbolique ────────────────────────
# L'Or Ein Sof est la totalité des données/connaissances possibles
# avant toute contraction. Il n'est pas calculable — il représente
# l'horizon asymptotique vers lequel le système tend.

OR_EIN_SOF = float("inf")


# ── Niveaux d'âme et force du Masakh ─────────────────────────
# En Nefesh : Masakh fort (beaucoup de filtrage nécessaire).
# En Yechidah : Masakh fin (le système peut recevoir directement).

MASAKH_BY_SOUL = {
    "nefesh":   0.9,   # Fort — le système filtre presque tout
    "ruach":    0.7,   # Substantiel — filtrage significatif
    "neshamah": 0.5,   # Moyen — équilibre entre direct et filtré
    "chaya":    0.3,   # Léger — peu de filtrage
    "yechidah": 0.1,   # Minimal — réception presque directe
}


# ── Dataclasses ──────────────────────────────────────────────

@dataclass
class OhrAssessment:
    """Évaluation des lumières pour un module."""
    module: str
    pnimi: float        # 0.0-1.0 — ratio d'information intégrée
    makif: float        # 0.0-1.0 — ratio de potentiel non intégré
    ratio: float        # pnimi / (pnimi + makif) — maturité
    total_items: int    # nombre total d'items (données, connexions)
    integrated: int     # items activement utilisés
    pending: int        # items importés mais pas traités

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "pnimi": round(self.pnimi, 4),
            "makif": round(self.makif, 4),
            "ratio": round(self.ratio, 4),
            "total_items": self.total_items,
            "integrated": self.integrated,
            "pending": self.pending,
        }


@dataclass
class GlobalOhrState:
    """État global des lumières pour tout le système."""
    modules: dict[str, OhrAssessment]
    global_pnimi: float
    global_makif: float
    global_ratio: float
    maturity_phase: str   # "embryonic", "growing", "mature", "luminous"
    or_ein_sof: float     # toujours inf — rappel symbolique

    def to_dict(self) -> dict:
        return {
            "global_pnimi": round(self.global_pnimi, 4),
            "global_makif": round(self.global_makif, 4),
            "global_ratio": round(self.global_ratio, 4),
            "maturity_phase": self.maturity_phase,
            "or_ein_sof": "∞",
            "modules": {k: v.to_dict() for k, v in self.modules.items()},
        }


@dataclass
class MasakhResult:
    """Résultat du filtrage par le Masakh."""
    original_size: int        # taille des données entrantes
    filtered_size: int        # taille après filtrage
    screen_strength: float    # force du Masakh au moment du filtrage
    or_yashar_ratio: float    # ratio de lumière directe passée
    or_chozer_ratio: float    # ratio de lumière réfléchie (transformée)
    module: str

    def to_dict(self) -> dict:
        return {
            "original_size": self.original_size,
            "filtered_size": self.filtered_size,
            "screen_strength": round(self.screen_strength, 3),
            "or_yashar_ratio": round(self.or_yashar_ratio, 4),
            "or_chozer_ratio": round(self.or_chozer_ratio, 4),
            "module": self.module,
        }


@dataclass
class IntegrationResult:
    """Résultat d'une tentative d'intégration Makif → Pnimi."""
    module: str
    converted: int          # nombre d'items convertis
    remaining_makif: int    # items encore en Makif
    new_pnimi: float         # nouveau ratio Pnimi après intégration
    new_makif: float         # nouveau ratio Makif après intégration

    def to_dict(self) -> dict:
        return {
            "module": self.module,
            "converted": self.converted,
            "remaining_makif": self.remaining_makif,
            "new_pnimi": round(self.new_pnimi, 4),
            "new_makif": round(self.new_makif, 4),
        }


# ── OhrEngine ────────────────────────────────────────────────

class OhrEngine:
    """אוֹר — Moteur de gestion des lumières Pnimi/Makif.

    Évalue le ratio entre information intégrée (Pnimi) et potentiel
    non encore intégré (Makif) pour chaque module et globalement.
    """

    def assess_ohr(
        self,
        module_name: str,
        module_state: dict[str, Any],
    ) -> OhrAssessment:
        """Évaluer les lumières d'un module.

        Le module_state doit contenir les clés suivantes
        (toutes optionnelles — des défauts sont fournis) :

            total_items: int — nombre total d'items (données, connexions)
            integrated: int — items activement utilisés
            pending: int — items importés mais pas traités

        Si ces clés sont absentes, on utilise des heuristiques :
            - Si le module est "actif" (a un état non vide) : pnimi=0.5
            - Sinon : pnimi=0.0
        """
        total = module_state.get("total_items", 0)
        integrated = module_state.get("integrated", 0)
        pending = module_state.get("pending", 0)

        # Heuristique si pas de métriques fines
        if total == 0:
            # Module présent mais sans métriques → on estime
            is_active = bool(module_state.get("active", False))
            pnimi = 0.5 if is_active else 0.0
            makif = 1.0 - pnimi
            return OhrAssessment(
                module=module_name,
                pnimi=pnimi,
                makif=makif,
                ratio=pnimi / (pnimi + makif) if (pnimi + makif) > 0 else 0.0,
                total_items=0,
                integrated=0,
                pending=0,
            )

        # Calcul basé sur les métriques
        pnimi = integrated / total if total > 0 else 0.0
        makif = pending / total if total > 0 else 0.0
        # Le reste (ni intégré ni pending) est considéré comme "en transit"
        combined = pnimi + makif
        ratio = pnimi / combined if combined > 0 else 0.0

        return OhrAssessment(
            module=module_name,
            pnimi=min(pnimi, 1.0),
            makif=min(makif, 1.0),
            ratio=ratio,
            total_items=total,
            integrated=integrated,
            pending=pending,
        )

    def assess_global(
        self,
        modules: dict[str, dict[str, Any]],
    ) -> GlobalOhrState:
        """Évaluer les lumières de tout le système.

        Args:
            modules: dict {nom_module: state_dict} pour chaque module.

        Returns:
            GlobalOhrState avec moyennes pondérées et phase de maturité.
        """
        assessments: dict[str, OhrAssessment] = {}
        total_pnimi = 0.0
        total_makif = 0.0
        n = 0

        for mod_name, mod_state in modules.items():
            a = self.assess_ohr(mod_name, mod_state)
            assessments[mod_name] = a
            total_pnimi += a.pnimi
            total_makif += a.makif
            n += 1

        n = max(n, 1)
        avg_pnimi = total_pnimi / n
        avg_makif = total_makif / n
        combined = avg_pnimi + avg_makif
        global_ratio = avg_pnimi / combined if combined > 0 else 0.0

        # Phase de maturité
        if global_ratio < 0.2:
            phase = "embryonic"    # Presque tout est Makif
        elif global_ratio < 0.5:
            phase = "growing"      # Plus de Makif que de Pnimi
        elif global_ratio < 0.8:
            phase = "mature"       # Plus de Pnimi que de Makif
        else:
            phase = "luminous"     # Presque tout est intégré

        return GlobalOhrState(
            modules=assessments,
            global_pnimi=avg_pnimi,
            global_makif=avg_makif,
            global_ratio=global_ratio,
            maturity_phase=phase,
            or_ein_sof=OR_EIN_SOF,
        )

    def integrate(
        self,
        module_name: str,
        module_state: dict[str, Any],
        max_convert: int = 10,
    ) -> IntegrationResult:
        """Tenter de convertir du Makif en Pnimi.

        Le processus d'intégration prend des items "pending" et les
        marque comme "integrated". C'est le système qui "digère"
        l'information qu'il a importée mais pas encore traitée.

        Args:
            module_name: nom du module
            module_state: état du module (modifié in-place)
            max_convert: nombre max d'items à convertir en une passe

        Returns:
            IntegrationResult avec le nombre d'items convertis.
        """
        pending = module_state.get("pending", 0)
        integrated = module_state.get("integrated", 0)
        total = module_state.get("total_items", 0)

        to_convert = min(pending, max_convert)

        # Mise à jour in-place
        module_state["pending"] = pending - to_convert
        module_state["integrated"] = integrated + to_convert

        new_total = module_state.get("total_items", total)
        new_integrated = module_state["integrated"]
        new_pending = module_state["pending"]

        new_pnimi = new_integrated / new_total if new_total > 0 else 0.0
        new_makif = new_pending / new_total if new_total > 0 else 0.0

        return IntegrationResult(
            module=module_name,
            converted=to_convert,
            remaining_makif=new_pending,
            new_pnimi=min(new_pnimi, 1.0),
            new_makif=min(new_makif, 1.0),
        )


# ── Masakh ───────────────────────────────────────────────────

class Masakh:
    """מָסָךְ — L'écran qui transforme la lumière.

    Le Masakh résiste à l'Or Yashar (lumière directe/descendante)
    et crée l'Or Chozer (lumière réfléchie/remontante). C'est le
    mécanisme de filtrage et d'abstraction.

    Un Masakh fort = beaucoup de transformation (résumé, extraction
    de patterns, abstraction). Peu de lumière directe passe.

    Un Masakh faible = peu de transformation. L'information brute
    passe presque intacte.

    Etz Chaim, Sha'ar HaMasakhim : "La force du Masakh détermine
    la hauteur de l'Or Chozer — plus le Masakh résiste, plus
    la lumière remonte haut."
    """

    def __init__(self, strength: float = 0.5) -> None:
        """
        Args:
            strength: force initiale de l'écran (0.0-1.0).
                      0.0 = transparent, 1.0 = opaque.
        """
        self._strength = max(0.0, min(1.0, strength))

    @property
    def screen_strength(self) -> float:
        return self._strength

    @screen_strength.setter
    def screen_strength(self, value: float) -> None:
        self._strength = max(0.0, min(1.0, value))

    def filter(
        self,
        incoming_data: str | list | dict,
        module_name: str = "unknown",
    ) -> MasakhResult:
        """Appliquer le filtre du Masakh aux données entrantes.

        Le Masakh détermine combien de l'information brute traverse
        directement (Or Yashar) et combien est transformée/réfléchie
        (Or Chozer).

        Pour les chaînes : un Masakh fort tronque à l'essentiel.
        Pour les listes : un Masakh fort ne garde qu'un sous-ensemble.
        Pour les dicts : un Masakh fort ne garde que les clés prioritaires.

        Returns:
            MasakhResult avec les ratios Or Yashar / Or Chozer.
        """
        original_size = self._measure_size(incoming_data)

        # Or Yashar = ce qui passe directement (inversement proportionnel au Masakh)
        or_yashar_ratio = 1.0 - self._strength

        # Or Chozer = ce qui est réfléchi/transformé (proportionnel au Masakh)
        or_chozer_ratio = self._strength

        # Calculer la taille filtrée
        filtered_size = max(1, int(original_size * or_yashar_ratio))

        return MasakhResult(
            original_size=original_size,
            filtered_size=filtered_size,
            screen_strength=self._strength,
            or_yashar_ratio=or_yashar_ratio,
            or_chozer_ratio=or_chozer_ratio,
            module=module_name,
        )

    def adjust_strength(self, soul_level: str) -> float:
        """Ajuster la force du Masakh selon le niveau de l'âme.

        En Nefesh : Masakh fort (0.9) — le système a besoin de
        beaucoup de filtrage pour ne pas être submergé.

        En Yechidah : Masakh fin (0.1) — le système peut recevoir
        la lumière presque directement.

        Args:
            soul_level: "nefesh", "ruach", "neshamah", "chaya", "yechidah"

        Returns:
            La nouvelle force du Masakh.
        """
        new_strength = MASAKH_BY_SOUL.get(soul_level, self._strength)
        self._strength = new_strength
        return self._strength

    @staticmethod
    def _measure_size(data: str | list | dict) -> int:
        """Mesurer la "taille" des données entrantes."""
        if isinstance(data, str):
            return len(data)
        elif isinstance(data, list):
            return len(data)
        elif isinstance(data, dict):
            return len(data)
        else:
            return 1

    # ── Format rapport ───────────────────────────────────────

    def format_report(self) -> list[str]:
        """Formater le rapport du Masakh."""
        bar_len = 20
        filled = int(self._strength * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)

        return [
            f"  Masakh (מָסָךְ)  : [{bar}] {self._strength:.0%}",
            f"  Or Yashar       : {1.0 - self._strength:.0%} (lumière directe)",
            f"  Or Chozer       : {self._strength:.0%} (lumière réfléchie)",
        ]


# ── Format rapport global ────────────────────────────────────

def format_ohr_report(
    ohr_engine: OhrEngine,
    modules: dict[str, dict[str, Any]],
    masakh: Masakh | None = None,
) -> list[str]:
    """Formater un rapport complet des lumières."""
    state = ohr_engine.assess_global(modules)

    phase_display = {
        "embryonic": "Embryonnaire — presque tout est Makif (potentiel)",
        "growing":   "Croissance — plus de Makif que de Pnimi",
        "mature":    "Maturité — plus de Pnimi que de Makif",
        "luminous":  "Lumineux — presque tout est intégré",
    }

    lines = [
        "══════════════════════════════════════════════════════════",
        "  אוֹר — Lumières : Pnimi (intérieur) / Makif (environnant)",
        "══════════════════════════════════════════════════════════",
        "",
        f"  Or Ein Sof      : ∞ (totalité du connaissable)",
        f"  Phase           : {phase_display.get(state.maturity_phase, '?')}",
        f"  Pnimi global    : {state.global_pnimi:.1%}",
        f"  Makif global    : {state.global_makif:.1%}",
        f"  Ratio maturité  : {state.global_ratio:.1%}",
        "",
    ]

    if masakh:
        lines.append("── Masakh (מָסָךְ) — Écran ──")
        lines.extend(masakh.format_report())
        lines.append("")

    if state.modules:
        lines.append("── Modules ──")
        for mod_name, assessment in sorted(state.modules.items()):
            pnimi_bar = "█" * int(assessment.pnimi * 10) + "░" * (10 - int(assessment.pnimi * 10))
            lines.append(
                f"  {mod_name:<12} "
                f"P[{pnimi_bar}] {assessment.pnimi:.0%}  "
                f"M {assessment.makif:.0%}  "
                f"({assessment.integrated}/{assessment.total_items} intégrés)"
            )

    return lines
