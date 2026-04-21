"""sentiers/router.py — Routeur de sentiers pour le pipeline cmd_ask.

Les 22 lettres hébraïques sont les canaux (tzinorot) par lesquels
la lumière (Ohr) coule d'une Sefirah à l'autre. Sans les sentiers,
la lumière saute directement — avec les sentiers, elle est TRANSFORMÉE
pendant la traversée.

Dans le pipeline Yosher :
  Or Yashar (descente) : le sentier prépare/colore le contexte
  Or Chozer (remontée) : le sentier valide/transforme le résultat

Le routeur utilise traverse_quick() — zéro I/O, zéro LLM.
Timeout de 500ms par sentier, fallback gracieux sur échec.
"""

from __future__ import annotations

import logging
import signal
import time
from typing import Any

from . import REGISTRY

logger = logging.getLogger(__name__)

# Timeout par sentier en secondes
_SENTIER_TIMEOUT_S = 0.5


class _SentierTimeout(Exception):
    """Raised when a sentier traverse_quick exceeds timeout."""


class SentierRouter:
    """Route les transitions entre Sefirot vers le sentier approprié.

    La table de routing est bidirectionnelle : chaque sentier connecte
    deux Sefirot, et peut être traversé dans les deux sens (yashar/chozer).
    """

    def __init__(self) -> None:
        self._sentier_instances: dict[str, Any] = {}
        self._routes: dict[tuple[str, str], str] = {}
        self._all_names: set[str] = set()
        self._build_routing_table()

    def _build_routing_table(self) -> None:
        """Construire la table (from, to) → sentier_name depuis le REGISTRY.

        Quand deux sentiers connectent la même paire de Sefirot
        (ex: Resh et Qoph pour yesod↔hod, Peh et Mem pour gevurah↔hod),
        chacun est routé dans sa direction canonique (source→target).
        La direction inverse n'est assignée que si aucun autre sentier
        ne la couvre déjà.
        """
        for name, entry in REGISTRY.items():
            if entry["status"] != "implemented":
                continue
            src = entry["source"]
            tgt = entry["target"]
            self._all_names.add(name)
            # Direction canonique : source → target (toujours assignée)
            self._routes[(src, tgt)] = name
            # Direction inverse : seulement si pas déjà prise
            if (tgt, src) not in self._routes:
                self._routes[(tgt, src)] = name

    def _get_sentier(self, name: str):
        """Instancier un sentier (lazy, cache)."""
        if name not in self._sentier_instances:
            entry = REGISTRY.get(name)
            if entry and entry["class"]:
                self._sentier_instances[name] = entry["class"]()
        return self._sentier_instances.get(name)

    @property
    def routes(self) -> dict[tuple[str, str], str]:
        """Table de routing exposée pour diagnostic."""
        return dict(self._routes)

    def has_route(self, from_sefira: str, to_sefira: str) -> bool:
        """Vérifie si un sentier couvre cette transition."""
        return (from_sefira, to_sefira) in self._routes

    def get_letter(self, from_sefira: str, to_sefira: str) -> str | None:
        """Retourne la lettre hébraïque du sentier pour cette transition."""
        name = self._routes.get((from_sefira, to_sefira))
        if name:
            entry = REGISTRY.get(name)
            return entry["letter"] if entry else None
        return None

    def traverse(
        self,
        from_sefira: str,
        to_sefira: str,
        ctx: dict,
        direction: str = "yashar",
        is_katnut: bool = False,
    ) -> dict:
        """Activer le sentier entre deux Sefirot.

        Args:
            from_sefira: Sefirah de départ (lowercase)
            to_sefira: Sefirah d'arrivée (lowercase)
            ctx: contexte accumulé du pipeline cmd_ask
            direction: 'yashar' (descente) ou 'chozer' (remontée)
            is_katnut: si True, seuls les sentiers du chemin court
                       (Keter→Hod→Yesod→Malkuth) sont activés

        Returns:
            ctx enrichi/transformé par le sentier.
            Si aucun sentier ne couvre la transition, retourne ctx inchangé.
        """
        key = (from_sefira, to_sefira)
        name = self._routes.get(key)
        if name is None:
            return ctx

        # En Katnut, seuls les sentiers du chemin court sont actifs
        if is_katnut:
            katnut_pairs = {
                ("hod", "yesod"), ("yesod", "hod"),
                ("yesod", "malkuth"), ("malkuth", "yesod"),
            }
            if key not in katnut_pairs:
                return ctx

        sentier = self._get_sentier(name)
        if sentier is None:
            return ctx

        t0 = time.monotonic()
        try:
            enriched = sentier.traverse_quick(ctx, direction=direction)
            elapsed = time.monotonic() - t0

            # Timeout check (non-preemptive — traverse_quick est CPU-bound)
            if elapsed > _SENTIER_TIMEOUT_S:
                logger.warning(
                    "Sentier %s %s→%s slow: %.0fms (limit=%dms)",
                    sentier.letter, from_sefira, to_sefira,
                    elapsed * 1000, _SENTIER_TIMEOUT_S * 1000,
                )

            # ── Appliquer les effets transformationnels ──────
            effects = enriched.pop("_last_sentier_effects", None)
            if effects and effects.get("applied"):
                self._apply_effects(enriched, effects, to_sefira)

            # Journal des sentiers traversés
            enriched.setdefault("sentiers_traversed", []).append({
                "letter": sentier.letter,
                "letter_name": sentier.letter_name,
                "from": from_sefira,
                "to": to_sefira,
                "direction": direction,
                "program": sentier.name,
                "elapsed_ms": round(elapsed * 1000, 1),
                "applied": bool(effects and effects.get("applied")),
            })

            return enriched

        except Exception as e:
            logger.warning(
                "Sentier %s %s→%s failed: %s",
                name, from_sefira, to_sefira, e,
            )
            return ctx

    def traverse_multiple(
        self,
        transitions: list[tuple[str, str]],
        ctx: dict,
        direction: str = "yashar",
        is_katnut: bool = False,
    ) -> dict:
        """Traverser plusieurs sentiers séquentiellement.

        Utile pour les transitions composées (ex: Keter→Chokmah puis
        Chokmah→Binah dans le zivug Abba-Imma).
        """
        for from_s, to_s in transitions:
            ctx = self.traverse(from_s, to_s, ctx, direction, is_katnut)
        return ctx

    def _apply_effects(self, ctx: dict, effects: dict, target_sefira: str) -> None:
        """Appliquer les effets transformationnels d'un sentier au ctx.

        Les sentiers produisent trois types d'effets :
          - ctx_additions : clés mergées dans le ctx du pipeline
          - module_modifiers : modifications ADDITIVES aux attributs du module cible
          - warnings : avertissements injectés pour la génération Malkuth
        """
        # 1. ctx_additions → merge dans ctx
        additions = effects.get("ctx_additions", {})
        if additions:
            ctx.update(additions)

        # 2. module_modifiers → modification additive sur le module cible
        modifiers = effects.get("module_modifiers", {})
        if modifiers:
            # Les modifiers sont stockés pour application par apply_to_tree
            # ou directement si le tree est accessible
            existing = ctx.get("_sentier_module_modifiers", {})
            target_mods = existing.get(target_sefira, {})
            for attr, delta in modifiers.items():
                # Cumulatif : si plusieurs sentiers modifient le même attr
                target_mods[attr] = target_mods.get(attr, 0) + delta
            existing[target_sefira] = target_mods
            ctx["_sentier_module_modifiers"] = existing

        # 3. warnings → accumulés dans ctx['sentier_warnings']
        warnings = effects.get("warnings", [])
        if warnings:
            ctx.setdefault("sentier_warnings", []).extend(warnings)

    def apply_module_modifiers(self, ctx: dict, tree: dict) -> int:
        """Appliquer les module_modifiers accumulés par les sentiers aux modules.

        Appelé APRÈS que tous les sentiers d'une phase ont été traversés.
        Les modifiers sont ADDITIFS (delta ajouté à la valeur courante).

        Returns:
            Nombre d'attributs modifiés.
        """
        mods = ctx.get("_sentier_module_modifiers", {})
        if not mods:
            return 0

        n_applied = 0
        for sefira, attr_deltas in mods.items():
            module = tree.get(sefira)
            if module is None:
                continue
            for attr, delta in attr_deltas.items():
                current = getattr(module, attr, None)
                if current is not None and isinstance(current, (int, float)):
                    new_val = current + delta
                    # Clamp raisonnable
                    if isinstance(current, float):
                        new_val = max(0.0, min(1.0, round(new_val, 4)))
                    else:
                        new_val = max(0, int(round(new_val)))
                    setattr(module, attr, new_val)
                    n_applied += 1
                    logger.debug(
                        "Sentier modifier: %s.%s = %s → %s (delta=%s)",
                        sefira, attr, current, new_val, delta,
                    )

        return n_applied

    def format_traversal_report(self, ctx: dict) -> list[str]:
        """Formater le journal des sentiers traversés pour le rapport."""
        traversed = ctx.get("sentiers_traversed", [])
        if not traversed:
            return ["  Aucun sentier traversé"]

        lines = []
        for t in traversed:
            arrow = "↓" if t["direction"] == "yashar" else "↑"
            lines.append(
                f"  {arrow} {t['letter']} {t['letter_name']} "
                f"({t['from']}→{t['to']}) — {t['program']} "
                f"[{t['elapsed_ms']:.0f}ms]"
            )
        return lines
