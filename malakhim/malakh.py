"""Malakh — Processus éphémère mono-mission.

מַלְאָךְ — « Ein malakh oseh shtei shlichuyot »
(Bereshit Rabbah 50:2 : un ange n'accomplit pas deux missions.)

Le Malakh EST sa mission. Il naît à l'entrée du context manager,
exécute UNE fois, et meurt à la sortie. Après destruction, ses
attributs internes sont effacés — il traverse le Nehar Dinur
(fleuve de feu, Daniel 7:10) où les anges sont consumés après service.

Architecture :
    - __slots__ pour immutabilité structurelle (pas de __dict__)
    - Context manager pour cycle de vie garanti
    - _self_check = hitkalelut (auto-correction intégrée) :
      chaque Malakh contient son propre contrepoids, son Kategor
      interne qui vérifie la qualité de l'exécution.

Référence kabbalistique :
    Le Zohar (II, 101a) distingue les Malakhim créés par les actes
    humains (éphémères) des Malakhim permanents (Mikhael, Gavriel).
    Cette classe modélise le premier type : créé pour un acte,
    dissous après accomplissement.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from malakhim.models import MalakhResult, ValidationSpec


class Malakh:
    """Processus éphémère mono-mission avec hitkalelut intégré.

    Usage :
        with Malakh("résumer", {"anti_pattern": "VERBOSE"}, "ishim") as m:
            result = m.execute({"input": "texte à résumer"})
            # result.hitkalelut_warnings contient les auto-corrections

        # Ici m est détruit — m.execute() lèverait RuntimeError.
    """

    __slots__ = (
        "_mission",
        "_kavvanah",
        "_order",
        "_execute_fn",
        "_self_check",
        "_system_prompt",
        "_validation_spec",
        "_executed",
        "_destroyed",
    )

    def __init__(
        self,
        mission: str,
        kavvanah: dict[str, Any] | None = None,
        order: str = "ishim",
        execute_fn: Callable[[dict[str, Any]], str] | None = None,
        system_prompt: str | None = None,
        validation_spec: ValidationSpec | None = None,
    ) -> None:
        self._mission = mission
        self._kavvanah = kavvanah or {}
        self._order = order
        self._execute_fn = execute_fn
        self._system_prompt = system_prompt
        self._validation_spec = validation_spec
        self._self_check = self._build_self_check(
            self._kavvanah, self._validation_spec,
        )
        self._executed = False
        self._destroyed = False

    # -- Context manager (cycle naissance → mort) --

    def __enter__(self) -> Malakh:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # noqa: ANN001
        """Nehar Dinur — le fleuve de feu consume le Malakh après service."""
        self._mission = None
        self._kavvanah = None
        self._self_check = None
        self._execute_fn = None
        self._system_prompt = None
        self._validation_spec = None
        self._destroyed = True

    # -- Exécution unique --

    def execute(self, context: dict[str, Any]) -> MalakhResult:
        """Exécuter la mission. Une seule fois. Jamais après destruction."""
        if self._destroyed:
            raise RuntimeError("Malakh destroyed (Nehar Dinur)")
        if self._executed:
            raise RuntimeError("Ein malakh oseh shtei shlichuyot")

        self._executed = True

        t0 = time.monotonic()

        if self._execute_fn is not None:
            response = self._execute_fn(context)
        else:
            response = self._default_execute(context)

        latency_ms = (time.monotonic() - t0) * 1000.0

        result = MalakhResult(
            response=response,
            success=True,
            score=1.0,
            latency_ms=latency_ms,
        )

        result = self._self_check(result)

        return result

    # -- Hitkalelut : auto-correction intégrée --

    @staticmethod
    def _build_self_check(
        kavvanah: dict[str, Any],
        validation_spec: ValidationSpec | None = None,
    ) -> Callable[[MalakhResult], MalakhResult]:
        """Construire le Kategor interne — le contrepoids du Malakh.

        Le hitkalelut (inter-inclusion) signifie que chaque qualité
        contient un reflet de son opposé. Ici : l'exécuteur contient
        son propre juge.

        Deux niveaux :
          1. Checks legacy (kavvanah dict) — rétrocompatibilité
          2. Checks enrichis (ValidationSpec) — quand le Memuneh
             engendre un Malakh façonné par sa mission
        """

        def check(result: MalakhResult) -> MalakhResult:
            # 1. Réponse vide = échec
            if not result.response or not result.response.strip():
                result.hitkalelut_warnings.append(
                    "Réponse vide — le Malakh n'a rien produit"
                )
                result.success = False
                return result

            # ── Legacy checks (kavvanah dict) ─────────────────────────

            # 2a. Anti-pattern singulier (rétrocompatibilité)
            anti = kavvanah.get("anti_pattern")
            if anti and anti in result.response:
                result.hitkalelut_warnings.append(
                    f"Anti-pattern détecté : '{anti}' présent dans la réponse"
                )

            # 3. Critère de succès (longueur minimale, legacy)
            critere = kavvanah.get("critere_succes")
            if critere is not None:
                try:
                    min_len = int(critere)
                    if len(result.response) < min_len:
                        result.hitkalelut_warnings.append(
                            f"Longueur insuffisante : {len(result.response)} < {min_len}"
                        )
                except (ValueError, TypeError) as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

            # ── Enriched checks (ValidationSpec) ──────────────────────

            if validation_spec is not None:
                # 2b. Multi anti-patterns
                for ap in validation_spec.anti_patterns:
                    if ap in result.response:
                        result.hitkalelut_warnings.append(
                            f"Anti-pattern mission : '{ap}'"
                        )

                # 4. Longueur minimale mission
                if (
                    validation_spec.min_length > 0
                    and len(result.response) < validation_spec.min_length
                ):
                    result.hitkalelut_warnings.append(
                        f"Réponse trop courte pour la mission : "
                        f"{len(result.response)} < {validation_spec.min_length}"
                    )

                # 5. Structure requise
                for marker in validation_spec.required_structure:
                    if marker.lower() not in result.response.lower():
                        result.hitkalelut_warnings.append(
                            f"Structure manquante : '{marker}'"
                        )

                # 6. Ratio de répétition
                if validation_spec.max_repetition_ratio < 1.0:
                    words = result.response.split()
                    if words:
                        unique_ratio = len(set(words)) / len(words)
                        if unique_ratio < (1.0 - validation_spec.max_repetition_ratio):
                            result.hitkalelut_warnings.append(
                                f"Trop de répétition : {1.0 - unique_ratio:.0%} "
                                f"(max {validation_spec.max_repetition_ratio:.0%})"
                            )

            return result

        return check

    # -- Exécution par défaut --

    @staticmethod
    def _default_execute(context: dict[str, Any]) -> str:
        """Exécution triviale — retourne l'input tel quel."""
        return str(context.get("input", ""))
