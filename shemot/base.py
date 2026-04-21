"""shemot/base.py — Classe de base pour les 72 Noms (micro-skills atomiques).

Les 72 trigrammes du Shem HaMephorash (Exode 14:19-21).
Chaque Nom = un skill atomique composable.
Contrairement aux sentiers (programmes de passage entre Sephiroth),
les shemot sont des fonctions pures ou quasi-pures.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ShemResult:
    """Résultat d'exécution d'un shem."""
    shem: str               # skill_id (ex: "gematria_calc")
    trigram: str             # Trigramme hébreu (ex: "האא")
    number: int              # 1-72
    success: bool = True
    data: dict = field(default_factory=dict)
    message: str = ""
    errors: list[str] = field(default_factory=list)


class Shem:
    """Micro-skill atomique.

    Sous-classer et implémenter run().
    """

    # ── Identité ─────────────────────────────────────────────
    name: str = ""              # Nom humain (ex: "Gematria Calculator")
    skill_id: str = ""          # ID machine (ex: "gematria_calc")
    trigram: str = ""           # Trigramme hébreu (ex: "האא")
    trigram_name: str = ""      # Nom latin (ex: "HAA")
    number: int = 0             # Position 1-72
    category: str = ""          # Catégorie thématique
    quality: str = ""           # Qualité traditionnelle
    description: str = ""

    # ── Infrastructure ───────────────────────────────────────
    requires_llm: bool = False  # False = pur calcul, True = besoin LLM
    olam: str | None = None     # Monde LLM si requires_llm ("assiah"/"yetzirah"/"briah")

    # ── Attributs sacrés (chargés depuis shemot_72.yaml) ────
    suffix: str | None = None           # "El" (אל) ou "Yah" (יה)
    angel_name: str | None = None       # Nom complet de l'ange (trigram + suffixe)
    choir: str | None = None            # Chœur angélique (Seraphim, Cherubim, etc.)
    sacred_sephirah: str | None = None  # Sephirah d'appartenance selon le chœur
    zodiac_sign: str | None = None      # Signe zodiacal
    zodiac_degrees: str | None = None   # Quinaire (ex: "0-5")
    element: str | None = None          # Feu / Terre / Air / Eau
    calendar_start: str | None = None   # Début période calendaire
    calendar_end: str | None = None     # Fin période calendaire
    psalm_verse: str | None = None      # Verset de psaume associé

    def run(self, text: str = "", **kwargs: Any) -> ShemResult:
        """Exécuter le skill.

        Args:
            text: Input textuel principal
            **kwargs: Paramètres spécifiques au skill

        Returns:
            ShemResult
        """
        raise NotImplementedError(f"{self.skill_id} — run() non implémenté")

    def _ok(self, data: dict, message: str = "") -> ShemResult:
        """Raccourci pour un résultat réussi."""
        return ShemResult(
            shem=self.skill_id, trigram=self.trigram,
            number=self.number, data=data, message=message,
        )

    def _fail(self, message: str, errors: list[str] | None = None) -> ShemResult:
        """Raccourci pour un résultat échoué."""
        return ShemResult(
            shem=self.skill_id, trigram=self.trigram,
            number=self.number, success=False,
            message=message, errors=errors or [],
        )

    def _llm(self, prompt: str, olam: str | None = None, **kwargs) -> str:
        """Appeler un LLM via olamot. Retourne le texte de réponse."""
        from olamot import ollama_generate
        world = olam or self.olam or "assiah"
        if "kavvanah" not in kwargs:
            kwargs["kavvanah"] = {
                "intention": f"Analyser la signification kabbalistique du Shem #{self.number} ({self.trigram})",
                "critere_succes": "Analyse ancrée dans les sources lourianiques",
                "anti_pattern": "Ne pas inventer de correspondances non sourcées",
            }
        # Enrichissement Sod HaKli : attributs sacrés du Shem
        if "context_items" not in kwargs:
            _items = [f"Shem #{self.number}: {self.trigram}"]
            if hasattr(self, "sacred_sephirah") and self.sacred_sephirah:
                _items.append(f"Sephirah: {self.sacred_sephirah}")
            if hasattr(self, "choir") and self.choir:
                _items.append(f"Choeur: {self.choir}")
            if hasattr(self, "element") and self.element:
                _items.append(f"Élément: {self.element}")
            kwargs["context_items"] = _items
        if "domain" not in kwargs:
            kwargs["domain"] = "kabbalah"
        if "principles" not in kwargs and hasattr(self, "category") and self.category:
            kwargs["principles"] = [f"Catégorie thématique: {self.category}"]
        text, _ = ollama_generate(world, prompt, **kwargs)
        return text

    def __repr__(self) -> str:
        llm = f" [LLM:{self.olam}]" if self.requires_llm else ""
        return f"<Shem #{self.number} {self.trigram} {self.skill_id}{llm}>"
