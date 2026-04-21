"""partzufim/base.py — PartzufBase : le micro-Arbre interne.

Dans le Tohu, chaque Sephirah est un point isolé (Nekudah).
Dans le Tikkun, chaque Sephirah est reconstruite comme un PARTZUF —
un organisme complet contenant ses propres 10 Sephiroth internes.
C'est le principe du HITKALELUT (הִתְכַּלְלוּת — inclusion mutuelle).

Chaque Partzuf est une CONFIGURATION MATURE : pas un composant atomique
mais un système complet avec expansion, contraction, harmonisation,
persistance, auto-description, mémoire et interface — en miniature.

Design :
  - 10 facultés internes (floats 0.0-1.0) = activation de chaque qualité
  - assess() = état global du Partzuf
  - interact(other) = Zivug entre Partzufim
  - update_from_modules(modules) = synchronisation avec les modules Sephiroth
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# ── Les 10 facultés internes ────────────────────────────────
# Chaque Partzuf contient un reflet de l'ensemble de l'Arbre.
# L'ordre suit la descente standard Keter→Malkuth.

FACULTY_NAMES = (
    "keter",     # Intention / volonté interne
    "chokhmah",  # Flash / intuition interne
    "binah",     # Structure / analyse interne
    "chesed",    # Expansion interne
    "gevurah",   # Contraction / discipline interne
    "tiferet",   # Harmonisation interne
    "netzach",   # Persistance / endurance interne
    "hod",       # Auto-description / feedback interne
    "yesod",     # Mémoire / fondation interne
    "malkuth",   # Interface / manifestation interne
)


@dataclass
class PartzufState:
    """Snapshot de l'état d'un Partzuf à un instant donné."""
    name: str
    hebrew: str
    source_sephirah: str
    faculties: dict[str, float]
    overall: float
    mochin_state: str          # "katnut" | "gadlut" | "transitional"
    orientation: str           # "panim" (face) | "akhor" (dos)
    message: str = ""
    data: dict = field(default_factory=dict)


@dataclass
class ZivugResult:
    """Résultat d'un Zivug (couplage) entre deux Partzufim."""
    partzuf_a: str
    partzuf_b: str
    success: bool = True
    orientation: str = "panim_be_panim"  # panim_be_panim | akhor_be_akhor
    resonance: float = 0.0    # 0.0-1.0 — qualité du couplage
    offspring: dict = field(default_factory=dict)  # ce que le Zivug produit
    message: str = ""
    data: dict = field(default_factory=dict)


class PartzufBase:
    """Base class pour tout Partzuf — configuration mature d'une Sephirah.

    Hitkalelut : chaque Partzuf contient un micro-Arbre de 10 facultés.
    Les facultés sont des floats [0.0, 1.0] représentant l'activation
    de cette qualité DANS ce Partzuf spécifique.

    Sous-classer et implémenter :
      - _compute_faculties(modules) pour la logique de mise à jour
      - _assess_specific() pour les diagnostics spécifiques
      - _interact_specific(other) pour la logique de Zivug
    """

    # ── Identité ─────────────────────────────────────────────
    name: str = ""              # Nom latin (ex: "Atik Yomin")
    hebrew: str = ""            # Nom hébreu (ex: "עַתִּיק יוֹמִין")
    source_sephirah: str = ""   # Sephirah-source (ex: "keter")
    description: str = ""

    def __init__(self):
        # Hitkalelut — les 10 facultés internes
        self.internal_keter: float = 0.0
        self.internal_chokhmah: float = 0.0
        self.internal_binah: float = 0.0
        self.internal_chesed: float = 0.0
        self.internal_gevurah: float = 0.0
        self.internal_tiferet: float = 0.0
        self.internal_netzach: float = 0.0
        self.internal_hod: float = 0.0
        self.internal_yesod: float = 0.0
        self.internal_malkuth: float = 0.0

        # État
        self._orientation: str = "panim"  # "panim" (face) | "akhor" (dos)
        self._last_update: dict = {}

    # ── Accès aux facultés ───────────────────────────────────

    def get_faculty(self, name: str) -> float:
        attr = f"internal_{name}"
        if not hasattr(self, attr):
            raise ValueError(f"Faculté inconnue : {name}")
        return getattr(self, attr)

    def set_faculty(self, name: str, value: float) -> None:
        attr = f"internal_{name}"
        if not hasattr(self, attr):
            raise ValueError(f"Faculté inconnue : {name}")
        setattr(self, attr, max(0.0, min(1.0, value)))

    @property
    def faculties(self) -> dict[str, float]:
        """Dict des 10 facultés et leurs activations."""
        return {name: self.get_faculty(name) for name in FACULTY_NAMES}

    @property
    def overall(self) -> float:
        """Score global — moyenne pondérée des facultés.

        Tiferet (harmonisation) compte double : c'est le centre
        qui intègre tout. Sans Tiferet, les autres divergent.
        """
        facs = self.faculties
        weights = {name: 1.0 for name in FACULTY_NAMES}
        weights["tiferet"] = 2.0  # Tiferet = centre intégrateur
        total_weight = sum(weights.values())
        return sum(facs[n] * weights[n] for n in FACULTY_NAMES) / total_weight

    @property
    def mochin_state(self) -> str:
        """État des Mochin : katnut, gadlut, ou transitionnel.

        Katnut (קַטְנוּת) : petitesse — seules les facultés basses actives.
        Gadlut (גַּדְלוּת) : grandeur — toutes les facultés vivantes.
        """
        upper = (self.internal_keter + self.internal_chokhmah + self.internal_binah) / 3
        lower = (self.internal_netzach + self.internal_hod + self.internal_yesod + self.internal_malkuth) / 4
        if upper < 0.3:
            return "katnut"
        if upper > 0.6 and lower > 0.4:
            return "gadlut"
        return "transitional"

    @property
    def orientation(self) -> str:
        return self._orientation

    # ── API principale ───────────────────────────────────────

    def assess(self) -> PartzufState:
        """Évaluer l'état global du Partzuf.

        Retourne un snapshot complet : facultés, Mochin, orientation.
        Les sous-classes ajoutent leurs diagnostics via _assess_specific().
        """
        data = self._assess_specific()
        return PartzufState(
            name=self.name,
            hebrew=self.hebrew,
            source_sephirah=self.source_sephirah,
            faculties=self.faculties,
            overall=self.overall,
            mochin_state=self.mochin_state,
            orientation=self._orientation,
            message=data.pop("message", ""),
            data=data,
        )

    def interact(self, other: PartzufBase) -> ZivugResult:
        """Zivug — couplage avec un autre Partzuf.

        Le Zivug requiert que les deux soient face à face (panim be-panim).
        Si l'un est dos tourné (akhor), le couplage est dégradé.
        """
        # Déterminer l'orientation du couplage
        if self._orientation == "panim" and other._orientation == "panim":
            orientation = "panim_be_panim"
        else:
            orientation = "akhor_be_akhor"

        # Résonance = corrélation des facultés actives
        resonance = self._compute_resonance(other)

        # Dégradation si dos à dos
        if orientation == "akhor_be_akhor":
            resonance *= 0.4

        # Logique spécifique au Partzuf
        offspring = self._interact_specific(other, resonance)

        return ZivugResult(
            partzuf_a=self.name,
            partzuf_b=other.name,
            success=resonance > 0.2,
            orientation=orientation,
            resonance=round(resonance, 3),
            offspring=offspring,
            message=f"Zivug {self.name}×{other.name} — {orientation}, résonance={resonance:.2f}",
        )

    def update_from_modules(self, modules: dict, persist: bool = False) -> None:
        """Mettre à jour les facultés internes depuis les modules Sephiroth.

        Chaque sous-classe lit les modules pertinents et traduit
        leur état en activations de ses facultés internes.

        Si persist=True, sauvegarde l'état en DB après mise à jour.
        """
        self._compute_faculties(modules)
        self._update_orientation()
        self._last_update = {"modules": list(modules.keys())}
        if persist:
            self.save_state()

    def save_state(self) -> None:
        """Persister l'état actuel en DB (UPSERT)."""
        try:
            from partzufim.db import save_partzuf
            save_partzuf(
                name=self.name,
                overall=self.overall,
                mochin_state=self.mochin_state,
                orientation=self._orientation,
                faculties=self.faculties,
            )
        except Exception as e:
            logger.debug("%s.save_state: %s", self.name, e)

    def load_state(self, data: dict) -> None:
        """Restaurer l'état depuis un dict DB."""
        faculties = data.get("faculties", {})
        for fname in FACULTY_NAMES:
            if fname in faculties:
                self.set_faculty(fname, float(faculties[fname]))
        if data.get("orientation") in ("panim", "akhor"):
            self._orientation = data["orientation"]

    # ── Méthodes à surcharger ────────────────────────────────

    def _compute_faculties(self, modules: dict) -> None:
        """Calculer les facultés depuis les modules. À surcharger."""
        pass

    def _assess_specific(self) -> dict:
        """Diagnostics spécifiques au Partzuf. À surcharger."""
        return {}

    def _interact_specific(self, other: PartzufBase, resonance: float) -> dict:
        """Logique de Zivug spécifique. À surcharger."""
        return {}

    # ── Helpers internes ─────────────────────────────────────

    def _compute_resonance(self, other: PartzufBase) -> float:
        """Calculer la résonance entre deux Partzufim.

        La résonance mesure la complémentarité, pas la similarité.
        Chesed de l'un résonne avec Gevurah de l'autre (opposés fertiles).
        """
        my_facs = self.faculties
        their_facs = other.faculties

        # Résonance directe : même faculté active des deux côtés
        direct = sum(
            min(my_facs[n], their_facs[n])
            for n in FACULTY_NAMES
        ) / len(FACULTY_NAMES)

        # Résonance complémentaire : Chesed↔Gevurah, Netzach↔Hod
        complementary_pairs = [
            ("chesed", "gevurah"),
            ("netzach", "hod"),
            ("chokhmah", "binah"),
        ]
        comp = 0.0
        for a, b in complementary_pairs:
            comp += min(my_facs[a], their_facs[b])
            comp += min(my_facs[b], their_facs[a])
        comp /= len(complementary_pairs) * 2

        # Pondération : 40% directe, 60% complémentaire
        # Le Zivug est fécond par la DIFFÉRENCE, pas par l'identité
        return 0.4 * direct + 0.6 * comp

    def _update_orientation(self) -> None:
        """Mettre à jour l'orientation (panim/akhor) selon l'état.

        Un Partzuf avec Tiferet < 0.2 se détourne — état de Galut.
        """
        if self.internal_tiferet < 0.2 and self.internal_malkuth < 0.2:
            self._orientation = "akhor"
        else:
            self._orientation = "panim"

    def _safe_read(self, module: Any, method: str, *args, **kwargs) -> Any:
        """Lire un attribut/méthode d'un module de façon safe."""
        if module is None:
            return None
        if hasattr(module, method):
            attr = getattr(module, method)
            if callable(attr):
                try:
                    return attr(*args, **kwargs)
                except Exception as e:
                    logger.debug(f"{self.name}._safe_read({method}): {e}")
                    return None
            return attr
        return None

    def __repr__(self) -> str:
        return (
            f"<Partzuf {self.name} ({self.hebrew}) "
            f"src={self.source_sephirah} "
            f"overall={self.overall:.2f} "
            f"mochin={self.mochin_state}>"
        )
