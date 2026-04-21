"""sentiers/base.py — Classe de base pour les 22 sentiers.

Chaque lettre hébraïque encode un programme de passage entre deux Sephiroth.
Les 3 mères sont élémentaires, les 7 doubles sont bimodales (dagesh/rafeh),
les 12 simples sont fonctionnelles.

Étape 7 — Le Sod des lettres :
  Les lettres ne sont pas des labels mais des OPÉRATEURS ACTIFS.
  Chaque sentier charge ses correspondances du Sefer Yetzirah
  (version du Gra) et les applique comme modificateurs comportementaux.
  Les correspondances sont structurées selon les 4 mondes (Olamot).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ─── Chargement du Sefer Yetzirah ────────────────────────────
# Le YAML est chargé UNE FOIS au niveau module. Les correspondances
# sont immuables — elles viennent du SY, pas du runtime.

_SY_PATH = Path(__file__).parent / "sefer_yetzirah.yaml"
_SY_DATA: dict = {}


def _load_sefer_yetzirah() -> dict:
    """Charger sefer_yetzirah.yaml — une seule fois."""
    global _SY_DATA
    if _SY_DATA:
        return _SY_DATA
    if not _SY_PATH.exists():
        logger.warning("sefer_yetzirah.yaml introuvable — correspondances désactivées")
        return {}
    with open(_SY_PATH, encoding="utf-8") as f:
        _SY_DATA = yaml.safe_load(f) or {}
    return _SY_DATA


def _find_letter_data(letter_name: str) -> dict:
    """Trouver les données SY pour une lettre par son nom latin."""
    sy = _load_sefer_yetzirah()
    for category in ("mothers", "doubles", "simples"):
        section = sy.get(category, {})
        if letter_name in section:
            data = dict(section[letter_name])
            data["_category"] = category
            return data
    return {}


@dataclass
class SentierResult:
    """Résultat d'exécution d'un sentier."""
    sentier: str                    # Nom du sentier (ex: "tav")
    letter: str                     # Lettre hébraïque
    source: str                     # Sephirah source
    target: str                     # Sephirah cible
    success: bool = True
    mode: str | None = None         # dagesh/rafeh pour les doubles
    data: dict = field(default_factory=dict)
    message: str = ""
    errors: list[str] = field(default_factory=list)
    sy_context: dict = field(default_factory=dict)
    # sy_context contient les correspondances SY actives pour cette exécution :
    #   - "element" / "sense" / "planet" / "zodiac" / etc.
    #   - "modifiers" : les modificateurs numériques actifs (yetzirah)
    #   - "archetype" : le texte archétypal (atziluth)


class Sentier:
    """Programme de passage entre deux Sephiroth.

    Sous-classer et implémenter run().

    Le Sod des lettres : chaque Sentier porte les correspondances
    de sa lettre (SY version du Gra) comme opérateurs actifs.
    Appeler self.yetzirah_modifiers() pour obtenir les modificateurs
    numériques, et self.enrich_result(result) pour injecter les
    correspondances dans le résultat.
    """

    # ── Identité ─────────────────────────────────────────────
    name: str = ""                  # Nom du programme (ex: "OutputMode")
    letter: str = ""                # Lettre hébraïque (ex: "ת")
    letter_name: str = ""           # Nom latin (ex: "tav")
    number: int = 0                 # Numéro du sentier (32 = premier initiatique)
    source: str = ""                # Sephirah source (clé tree)
    target: str = ""                # Sephirah cible (clé tree)

    # ── Classification (Sefer Yetzirah) ──────────────────────
    letter_type: str = "simple"     # "mother", "double", "simple"
    element: str | None = None      # Pour les mères : air/eau/feu
    sense: str | None = None        # Pour les simples : vue/ouïe/etc.

    # ── Bimodalité (doubles uniquement) ──────────────────────
    dagesh_desc: str = ""           # Description mode dur
    rafeh_desc: str = ""            # Description mode doux
    mode: str = "rafeh"             # Mode actif : "dagesh" ou "rafeh"

    # ── Description ──────────────────────────────────────────
    description: str = ""

    # ── Cache des correspondances SY ─────────────────────────
    _sy_cache: dict | None = None

    def set_mode(self, mode: str) -> None:
        """Changer le mode dagesh/rafeh (doubles uniquement)."""
        if self.letter_type != "double":
            raise ValueError(f"{self.letter_name} n'est pas une lettre double")
        if mode not in ("dagesh", "rafeh"):
            raise ValueError(f"Mode invalide: {mode} (dagesh/rafeh)")
        self.mode = mode

    # ── Correspondances SY ───────────────────────────────────

    @property
    def correspondences(self) -> dict:
        """Retourner les correspondances SY complètes pour cette lettre.

        Inclut : element/sense, planet/zodiac/month/direction/organ,
        archetype, et les 4 niveaux d'olamot.
        """
        if self._sy_cache is None:
            self._sy_cache = _find_letter_data(self.letter_name)
        return self._sy_cache

    def yetzirah_modifiers(self) -> dict:
        """Retourner les modificateurs numériques actifs (niveau Yetzirah).

        Pour les mères et simples : retourne olamot.yetzirah.
        Pour les doubles : retourne dagesh_modifiers ou rafeh_modifiers
        selon le mode actif.
        """
        corr = self.correspondences
        if not corr:
            return {}

        olamot = corr.get("olamot", {})

        if self.letter_type == "double":
            # Les doubles ont des profils séparés par mode
            key = f"{self.mode}_modifiers"
            return dict(olamot.get(key, {}))
        else:
            # Mères et simples : profil unique
            return dict(olamot.get("yetzirah", {}))

    def enrich_result(self, result: SentierResult) -> SentierResult:
        """Injecter les correspondances SY dans le résultat.

        Ajoute à result.sy_context :
          - Les correspondances statiques (element, sense, planet, etc.)
          - Les modificateurs numériques actifs
          - L'archétype (atziluth)
        Ajoute à result.data["sy_influence"] un résumé des effets.
        """
        corr = self.correspondences
        if not corr:
            return result

        # Construire le contexte SY
        ctx: dict[str, Any] = {}

        # Identité de la lettre
        ctx["letter"] = corr.get("letter", self.letter)
        ctx["gematria"] = corr.get("gematria")
        ctx["archetype"] = corr.get("archetype", "")
        ctx["category"] = corr.get("_category", self.letter_type)

        # Correspondances spécifiques par type
        if self.letter_type == "mother":
            ctx["element"] = corr.get("element")
            ctx["body"] = corr.get("body")
            ctx["season"] = corr.get("season")
            ctx["quality"] = corr.get("quality")
        elif self.letter_type == "double":
            ctx["planet"] = corr.get("planet")
            ctx["day"] = corr.get("day")
            ctx["gate"] = corr.get("gate")
            ctx["direction"] = corr.get("direction")
            opposites = corr.get("opposites", {})
            ctx["opposites"] = opposites
            ctx["active_quality"] = opposites.get(self.mode, "")
        elif self.letter_type == "simple":
            ctx["sense"] = corr.get("sense")
            ctx["zodiac"] = corr.get("zodiac")
            ctx["month"] = corr.get("month")
            ctx["direction"] = corr.get("direction")
            ctx["organ"] = corr.get("organ")

        # Modificateurs numériques actifs
        modifiers = self.yetzirah_modifiers()
        ctx["modifiers"] = modifiers

        result.sy_context = ctx

        # Résumé d'influence dans data
        if modifiers:
            influence = {}
            if self.letter_type == "mother":
                influence["element"] = corr.get("element")
                influence["dominant_force"] = max(modifiers, key=modifiers.get)
            elif self.letter_type == "double":
                influence["mode"] = self.mode
                influence["active_quality"] = ctx.get("active_quality", "")
                influence["dominant_force"] = max(modifiers, key=modifiers.get)
            elif self.letter_type == "simple":
                influence["sense"] = corr.get("sense")
                influence["dominant_force"] = max(modifiers, key=modifiers.get)
            result.data["sy_influence"] = influence

        return result

    def traverse_quick(self, ctx: dict, direction: str = "yashar") -> dict:
        """Traversée rapide pour le pipeline cmd_ask — zéro I/O.

        Injecte les modificateurs Yetzirah et les correspondances SY
        dans le ctx du pipeline. Pour les doubles, détermine le mode
        dagesh/rafeh heuristiquement depuis le ctx.

        Phase 2 (transformationnelle) : appelle _compute_effects(ctx, direction)
        pour calculer des effets structurés (ctx_additions, module_modifiers,
        warnings). Le routeur appliquera ces effets.

        Kabbalistiquement : la lettre COLORE la lumière (Ohr) qui
        traverse le sentier. En yashar elle prépare, en chozer elle
        valide. Les modificateurs numériques du SY ajustent les
        paramètres comportementaux du pipeline.

        Args:
            ctx: contexte accumulé du pipeline cmd_ask
            direction: 'yashar' (descente) ou 'chozer' (remontée)

        Returns:
            ctx enrichi avec les clés sentier_* ajoutées
        """
        # Déterminer le mode pour les doubles (heuristique rapide)
        if self.letter_type == "double":
            confidence = ctx.get("response_confidence",
                                 ctx.get("mochin", {}).get("competence_score", 0.5))
            # Haute confiance → dagesh (rigoureux), basse → rafeh (créatif)
            self.mode = "dagesh" if confidence >= 0.5 else "rafeh"

        # Charger les modificateurs Yetzirah (pure data, pas d'I/O)
        mods = self.yetzirah_modifiers()

        # Construire l'enrichissement
        enrichment: dict[str, Any] = {
            "letter": self.letter,
            "letter_name": self.letter_name,
            "number": self.number,
            "type": self.letter_type,
            "direction": direction,
            "source": self.source,
            "target": self.target,
            "program": self.name,
        }

        # Correspondances SY (archétype, élément/sens, etc.)
        corr = self.correspondences
        if corr:
            enrichment["archetype"] = corr.get("archetype", "")
            enrichment["gematria"] = corr.get("gematria")
            if self.letter_type == "mother":
                enrichment["element"] = corr.get("element")
            elif self.letter_type == "double":
                enrichment["mode"] = self.mode
                opposites = corr.get("opposites", {})
                enrichment["active_quality"] = opposites.get(self.mode, "")
            elif self.letter_type == "simple":
                enrichment["sense"] = corr.get("sense")

        # Injecter les modificateurs dans le ctx
        if mods:
            current_mods = ctx.get("sentier_modifiers", {})
            current_mods.update(mods)
            ctx["sentier_modifiers"] = current_mods

        # Ajouter au journal des traversées
        ctx.setdefault("sentier_enrichments", []).append(enrichment)

        # ── Phase 2 : effets transformationnels ──────────────
        # Chaque sentier peut surcharger _compute_effects() pour
        # retourner des effets structurés que le routeur appliquera.
        effects = self._compute_effects(ctx, direction)
        if effects and effects.get("applied"):
            enrichment["applied"] = True
            enrichment["effects_summary"] = {
                "n_ctx_additions": len(effects.get("ctx_additions", {})),
                "n_module_modifiers": len(effects.get("module_modifiers", {})),
                "n_warnings": len(effects.get("warnings", [])),
            }
        ctx["_last_sentier_effects"] = effects

        return ctx

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Calculer les effets transformationnels du sentier.

        Surcharger dans les sous-classes pour les 8 sentiers prioritaires.
        Les sentiers non-enrichis retournent applied=False (informatif pur).

        Returns:
            {
                'ctx_additions': {},       # clés à ajouter au ctx
                'module_modifiers': {},    # {attr_name: value} pour le module cible
                'warnings': [],            # avertissements pour le prompt
                'applied': False           # True si le sentier a eu un effet réel
            }
        """
        return {
            "ctx_additions": {},
            "module_modifiers": {},
            "warnings": [],
            "applied": False,
        }

    def run(self, tree: dict, **kwargs: Any) -> SentierResult:
        """Exécuter le programme du sentier.

        Args:
            tree: dict {sephirah_key: module_instance} de init_tree()
            **kwargs: paramètres spécifiques au sentier

        Returns:
            SentierResult avec les données de transition
        """
        raise NotImplementedError(f"{self.letter_name} — run() non implémenté")

    def _require(self, tree: dict, *keys: str) -> list:
        """Vérifier que les modules nécessaires sont dans l'arbre."""
        modules = []
        for key in keys:
            mod = tree.get(key)
            if mod is None:
                raise RuntimeError(f"{key} non initialisé — requis pour {self.letter_name}")
            modules.append(mod)
        return modules

    def __repr__(self) -> str:
        mode_str = f" [{self.mode}]" if self.letter_type == "double" else ""
        return f"<Sentier {self.number}e {self.letter} {self.letter_name}{mode_str} : {self.source}→{self.target}>"
