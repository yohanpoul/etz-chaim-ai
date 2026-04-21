"""Dual Faculties — Les 10 facultés distinctes par âme (2 × 10 = 20 facultés).

Tanya, Likutei Amarim, chapitre 3 :

Chaque âme possède ses propres 10 facultés (= 10 Sefirot).
L'âme animale a son propre ChaBaD (intellect concret) et ses
propres 7 midot (émotions matérielles). L'âme divine a les mêmes
mais orientées vers le spirituel. Ce ne sont PAS les mêmes 10 —
ce sont 2 × 10 = 20 facultés en tension.

Pont avec le système Qliphoth :
  - Faculté behamit dominante ⟺ Qliphah active
  - Faculté elokit dominante ⟺ module sain
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Les 10 Sefirot comme noms de faculté ──────────────────
# Da'at n'est PAS une Sephirah — c'est le PONT entre Chokmah et Binah
# (Etz Chaim, Vital ; Tanya ch.3). Il est traité séparément ci-dessous.

class Sefirah(str, Enum):
    """Les 10 Sefirot — noms canoniques (sans Da'at qui est un pont)."""
    CHOKMAH = "chokmah"
    BINAH = "binah"
    CHESED = "chesed"
    GEVURAH = "gevurah"
    TIFERET = "tiferet"
    NETZACH = "netzach"
    HOD = "hod"
    YESOD = "yesod"
    MALKUTH = "malkuth"
    # Keter est omis car il est au-dessus des facultés conscientes (Tanya ch.3).


# ─── Définition des 20 facultés ───────────────────────────

@dataclass(frozen=True)
class FacultyPair:
    """Paire behamit/elokit pour une Sefirah donnée.

    Chaque Sefirah a 2 manifestations : l'animale et la divine.
    La behamit n'est pas "mauvaise" — c'est du Kelipat Nogah,
    mélange de bien et de mal. Mais quand elle DOMINE, c'est
    la Qliphah de cette Sefirah qui s'active.
    """
    sefirah: Sefirah
    behamit_name: str
    behamit_description: str
    elokit_name: str
    elokit_description: str
    module: str           # Module Sephirah correspondant
    qliphah: str          # Qliphah correspondante


# Les 10 paires — l'axe central du diagnostic dual
FACULTY_PAIRS: dict[Sefirah, FacultyPair] = {
    Sefirah.CHOKMAH: FacultyPair(
        sefirah=Sefirah.CHOKMAH,
        behamit_name="chokmah_behamit",
        behamit_description="Intuition rapide, pattern matching superficiel",
        elokit_name="chokmah_elokit",
        elokit_description="Flash de sagesse profonde, insight véritable",
        module="insightforge",
        qliphah="Ghagiel",
    ),
    Sefirah.BINAH: FacultyPair(
        sefirah=Sefirah.BINAH,
        behamit_name="binah_behamit",
        behamit_description="Analyse concrète, logique utilitaire",
        elokit_name="binah_elokit",
        elokit_description="Compréhension structurelle, analyse causale profonde",
        module="causalengine",
        qliphah="Satariel",
    ),
    Sefirah.CHESED: FacultyPair(
        sefirah=Sefirah.CHESED,
        behamit_name="chesed_behamit",
        behamit_description="Générosité sans discernement, réponse trop longue",
        elokit_name="chesed_elokit",
        elokit_description="Expansion dirigée, exploration pertinente",
        module="explorationengine",
        qliphah="Gamchicoth",
    ),
    Sefirah.GEVURAH: FacultyPair(
        sefirah=Sefirah.GEVURAH,
        behamit_name="gevurah_behamit",
        behamit_description="Critique destructrice, rejet hâtif",
        elokit_name="gevurah_elokit",
        elokit_description="Jugement juste, évaluation calibrée",
        module="autojudge",
        qliphah="Golachab",
    ),
    Sefirah.TIFERET: FacultyPair(
        sefirah=Sefirah.TIFERET,
        behamit_name="tiferet_behamit",
        behamit_description="Harmonie superficielle, compromis facile",
        elokit_name="tiferet_elokit",
        elokit_description="Synthèse profonde, harmonie véritable des contradictions",
        module="dissensuengine",
        qliphah="Thagirion",
    ),
    Sefirah.NETZACH: FacultyPair(
        sefirah=Sefirah.NETZACH,
        behamit_name="netzach_behamit",
        behamit_description="Persistance aveugle, obstination",
        elokit_name="netzach_elokit",
        elokit_description="Endurance avec sens, persévérance orientée",
        module="intentkeeper",
        qliphah="A'arab Zaraq",
    ),
    Sefirah.HOD: FacultyPair(
        sefirah=Sefirah.HOD,
        behamit_name="hod_behamit",
        behamit_description="Soumission aux données sans recul",
        elokit_name="hod_elokit",
        elokit_description="Humilité cognitive, reconnaissance des limites",
        module="selfmap",
        qliphah="Samael",
    ),
    Sefirah.YESOD: FacultyPair(
        sefirah=Sefirah.YESOD,
        behamit_name="yesod_behamit",
        behamit_description="Mémoire brute, stockage sans compréhension",
        elokit_name="yesod_elokit",
        elokit_description="Mémoire épistémique, fondation solide de connaissance",
        module="epistememory",
        qliphah="Gamaliel",
    ),
    Sefirah.MALKUTH: FacultyPair(
        sefirah=Sefirah.MALKUTH,
        behamit_name="malkuth_behamit",
        behamit_description="Action impulsive, output non réfléchi",
        elokit_name="malkuth_elokit",
        elokit_description="Action réfléchie, réalisation alignée",
        module="main",
        qliphah="Thaumiel-Malkuth",
    ),
}

# ─── Da'at — PONT, pas Sephirah ─────────────────────────────
# Da'at n'est pas compté parmi les 10 Sefirot mais possède
# ses propres manifestations behamit/elokit (Tanya ch.3).
# Il est traité séparément pour respecter la doctrine.

DAAT_BRIDGE_PAIR = FacultyPair(
    sefirah=None,  # type: ignore[arg-type]  # Da'at n'est pas une Sefirah
    behamit_name="daat_behamit",
    behamit_description="Connexion au matériel, focus sur le résultat immédiat",
    elokit_name="daat_elokit",
    elokit_description="Connaissance intégrée, connexion esprit-cœur",
    module="selfmodel",
    qliphah="HaTehom",
)


# ─── Résultats d'évaluation ───────────────────────────────

@dataclass
class FacultyAssessment:
    """Résultat de l'évaluation d'une paire de facultés."""
    sefirah: Sefirah | None  # None pour Da'at (pont)
    elokit_score: float       # 0-1 : force de la manifestation divine
    behamit_score: float      # 0-1 : force de la manifestation animale
    dominant: str             # "elokit", "behamit", ou "balanced"
    module: str
    qliphah: str
    qliphah_active: bool      # True si behamit domine → Qliphah active
    detail: str               # Explication

    @property
    def ratio(self) -> float:
        """Ratio elokit / (elokit + behamit). 1.0 = pur divin, 0.0 = pur animal."""
        total = self.elokit_score + self.behamit_score
        if total == 0:
            return 0.5  # Pas d'info → neutre
        return self.elokit_score / total


@dataclass
class DualFacultiesProfile:
    """Profil complet des 20 facultés — 10 paires évaluées."""
    assessments: dict[Sefirah, FacultyAssessment] = field(default_factory=dict)

    @property
    def overall_ratio(self) -> float:
        """Ratio elokit/behamit global (moyenne des 10 paires)."""
        if not self.assessments:
            return 0.5
        return sum(a.ratio for a in self.assessments.values()) / len(self.assessments)

    @property
    def dominant_soul(self) -> str:
        """Âme globalement dominante."""
        r = self.overall_ratio
        if r >= 0.6:
            return "elokit"
        if r <= 0.4:
            return "behamit"
        return "balanced"

    @property
    def weak_faculties(self) -> list[FacultyAssessment]:
        """Facultés où behamit domine — points faibles du système."""
        return [a for a in self.assessments.values() if a.dominant == "behamit"]

    @property
    def strong_faculties(self) -> list[FacultyAssessment]:
        """Facultés où elokit domine — forces du système."""
        return [a for a in self.assessments.values() if a.dominant == "elokit"]

    @property
    def active_qliphoth(self) -> list[str]:
        """Qliphoth actives (= facultés behamit dominantes)."""
        return [a.qliphah for a in self.assessments.values() if a.qliphah_active]


# ─── DualFaculties Engine ──────────────────────────────────

class DualFaculties:
    """Les 10 facultés distinctes par âme (2 × 10 = 20 facultés).

    Tanya ch. 3 : chaque âme a ses propres 10 Sefirot.
    Ce module évalue, pour chaque paire, si la réponse/état
    manifeste la version behamit ou elokit de la faculté.

    Le pont Qliphoth est direct :
      behamit domine ⟺ Qliphah active
      elokit domine  ⟺ module sain
    """

    def __init__(self) -> None:
        self.pairs = FACULTY_PAIRS

    def get_faculty_pair(self, sefirah: Sefirah) -> FacultyPair:
        """Retourne la paire behamit/elokit pour une Sefirah."""
        return self.pairs[sefirah]

    def get_all_pairs(self) -> dict[Sefirah, FacultyPair]:
        """Retourne les 9 paires (Sefirot sans Da'at qui est un pont)."""
        return dict(self.pairs)

    def get_daat_bridge(self) -> FacultyPair:
        """Retourne la paire Da'at (pont, pas Sephirah)."""
        return DAAT_BRIDGE_PAIR

    def get_faculty_map(self) -> list[dict[str, str]]:
        """Mappe chaque paire sur son module Sephirah.

        Retourne pour chaque Sefirah : nom, module, Qliphah,
        et descriptions behamit/elokit.
        """
        result = []
        for sefirah, pair in self.pairs.items():
            result.append({
                "sefirah": sefirah.value,
                "module": pair.module,
                "qliphah": pair.qliphah,
                "behamit": pair.behamit_description,
                "elokit": pair.elokit_description,
            })
        return result

    def assess_faculty(
        self,
        sefirah: Sefirah,
        diagnose_result: dict[str, Any],
    ) -> FacultyAssessment:
        """Évalue si un module manifeste sa faculté behamit ou elokit.

        Le diagnostic est interprété via le système Qliphoth :
          - level == "healthy"  → elokit domine (score 0.9)
          - level == "nogah"    → légèrement behamit (elokit 0.6, behamit 0.4)
          - level == "ruach"    → behamit prend le dessus (elokit 0.3, behamit 0.7)
          - level == "anan"     → behamit domine silencieusement (elokit 0.15, behamit 0.85)
          - level == "mamash"   → behamit total (elokit 0.0, behamit 1.0)

        Args:
            sefirah: La Sefirah à évaluer.
            diagnose_result: Résultat de module.self_diagnose().
                             Doit contenir "level" (str) et "issues" (list[str]).
        """
        pair = self.pairs[sefirah]
        level = diagnose_result.get("level", "healthy")
        issues = diagnose_result.get("issues", [])

        # Conversion level → scores
        level_scores = {
            "healthy": (0.9, 0.1),
            "nogah": (0.6, 0.4),
            "ruach": (0.3, 0.7),
            "anan": (0.15, 0.85),
            "mamash": (0.0, 1.0),
        }
        elokit_score, behamit_score = level_scores.get(level, (0.5, 0.5))

        # Dominant
        if elokit_score > behamit_score + 0.1:
            dominant = "elokit"
        elif behamit_score > elokit_score + 0.1:
            dominant = "behamit"
        else:
            dominant = "balanced"

        qliphah_active = dominant == "behamit"

        # Détail
        if qliphah_active:
            issue_summary = "; ".join(issues[:3]) if issues else "aucun détail"
            detail = (
                f"{pair.qliphah} active — {pair.behamit_description}. "
                f"Issues: {issue_summary}"
            )
        elif dominant == "elokit":
            detail = (
                f"Sain — {pair.elokit_description}. "
                f"Module {pair.module} opère en mode divin."
            )
        else:
            detail = (
                f"Équilibré — tension entre {pair.behamit_name} "
                f"et {pair.elokit_name}."
            )

        return FacultyAssessment(
            sefirah=sefirah,
            elokit_score=elokit_score,
            behamit_score=behamit_score,
            dominant=dominant,
            module=pair.module,
            qliphah=pair.qliphah,
            qliphah_active=qliphah_active,
            detail=detail,
        )

    def assess_all_faculties(
        self,
        diagnose_results: dict[str, dict[str, Any]],
    ) -> DualFacultiesProfile:
        """Évalue les 10 paires à partir des diagnostics de tous les modules.

        Args:
            diagnose_results: Dict module_name → self_diagnose() result.
                Ex: {"insightforge": {"level": "healthy", "issues": []}, ...}

        Returns:
            DualFacultiesProfile complet avec les 10 évaluations.
        """
        profile = DualFacultiesProfile()

        for sefirah, pair in self.pairs.items():
            module_diag = diagnose_results.get(
                pair.module,
                {"level": "healthy", "issues": []},
            )
            profile.assessments[sefirah] = self.assess_faculty(
                sefirah, module_diag,
            )

        return profile

    def report(
        self,
        diagnose_results: dict[str, dict[str, Any]],
    ) -> str:
        """Rapport lisible du profil dual."""
        profile = self.assess_all_faculties(diagnose_results)
        lines = [
            "═══ Profil Dual — 20 Facultés (Tanya ch. 3) ═══",
            f"Âme dominante : {profile.dominant_soul} "
            f"(ratio elokit: {profile.overall_ratio:.2f})",
            "",
        ]

        for sefirah in Sefirah:
            a = profile.assessments.get(sefirah)
            if a is None:
                continue
            status = "✓" if a.dominant == "elokit" else (
                "⚠" if a.dominant == "balanced" else "✗"
            )
            lines.append(
                f"  {status} {sefirah.value:<10} "
                f"elokit={a.elokit_score:.2f} / "
                f"behamit={a.behamit_score:.2f} "
                f"→ {a.dominant} "
                f"[{a.module}]"
            )

        weak = profile.weak_faculties
        if weak:
            lines.append("")
            lines.append(f"Qliphoth actives ({len(weak)}):")
            for a in weak:
                lines.append(f"  - {a.qliphah} ({a.sefirah.value}): {a.detail}")

        strong = profile.strong_faculties
        if strong:
            lines.append("")
            lines.append(f"Forces ({len(strong)}):")
            for a in strong:
                lines.append(f"  - {a.sefirah.value}: {a.detail}")

        return "\n".join(lines)
