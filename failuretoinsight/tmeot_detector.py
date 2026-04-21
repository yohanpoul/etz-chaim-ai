"""TmeotDetector — Qliphoth Tmeot: détecteur d'erreurs irrécupérables.

Tanya ch. 6-7 : le Tmeot désigne ce qui est irrémédiablement souillé — il ne peut
pas être relevé (birur) comme les nitzotzot ordinaires. Réessayer une erreur Tmeot
n'est pas de la résilience : c'est de l'obstination qui amplifie la rupture.

Trois patterns de condamnation :
  1. Sévérité mamash  → arrêt immédiat (Tmeot par définition).
  2. Même erreur répétée ≥ MAX_SAME_ERROR_RETRIES fois → le pattern est verrouillé.
  3. Sévérités strictement croissantes sur les 3 dernières entrées → escalade systémique.
"""

from __future__ import annotations

from dataclasses import dataclass

# Ordre croissant des sévérités
SEVERITY_ORDER: dict[str, int] = {
    "nogah": 0,
    "ruach": 1,
    "anan": 2,
    "mamash": 3,
}

MAX_SAME_ERROR_RETRIES: int = 2


@dataclass
class RetryDecision:
    retry: bool
    reason: str


class TmeotDetector:
    """Décide si une erreur peut être réessayée ou doit être abandonnée."""

    def __init__(self) -> None:
        self._history: list[tuple[str, str]] = []   # (description, severity)
        self._retries_prevented: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_retry(
        self,
        error_description: str,
        severity: str,
        attempt: int,  # noqa: ARG002  (utilisé pour la sémantique, pas le calcul)
    ) -> RetryDecision:
        """Évalue si l'erreur est réessayable et met à jour l'historique."""

        decision = self._evaluate(error_description, severity)
        # Toujours enregistrer APRÈS évaluation (l'appel courant compte pour les suivants)
        self._history.append((error_description, severity))
        if not decision.retry:
            self._retries_prevented += 1
        return decision

    @property
    def retries_prevented(self) -> int:
        """Nombre de retries bloqués depuis la création ou le dernier reset()."""
        return self._retries_prevented

    def reset(self) -> None:
        """Réinitialise l'historique et le compteur."""
        self._history = []
        self._retries_prevented = 0

    # ------------------------------------------------------------------
    # Internal logic — règles dans l'ordre de priorité
    # ------------------------------------------------------------------

    def _evaluate(self, description: str, severity: str) -> RetryDecision:
        # Règle 1 : mamash = Tmeot absolu
        if severity == "mamash":
            return RetryDecision(
                retry=False,
                reason="Erreur irrecuperable (mamash) — le Tmeot ne peut être relevé.",
            )

        # Règle 2 : même description répétée ≥ MAX_SAME_ERROR_RETRIES fois dans l'historique
        same_count = sum(1 for desc, _ in self._history if desc == description)
        if same_count >= MAX_SAME_ERROR_RETRIES:
            return RetryDecision(
                retry=False,
                reason=(
                    f"Pattern verrouillé : '{description}' est apparu "
                    f"{same_count} fois — répétition Tmeot détectée."
                ),
            )

        # Règle 3 : escalade stricte sur les 3 dernières entrées de l'historique
        # On inclut l'entrée courante pour former la fenêtre [h[-2], h[-1], courant]
        if len(self._history) >= 2:
            prev2_sev = self._history[-2][1]
            prev1_sev = self._history[-1][1]
            if self._is_strictly_escalating(prev2_sev, prev1_sev, severity):
                return RetryDecision(
                    retry=False,
                    reason=(
                        f"Escalade systémique détectée : "
                        f"{prev2_sev} → {prev1_sev} → {severity}."
                    ),
                )

        return RetryDecision(retry=True, reason="Erreur récupérable — retry autorisé.")

    @staticmethod
    def _is_strictly_escalating(sev1: str, sev2: str, sev3: str) -> bool:
        """Retourne True si les trois sévérités sont strictement croissantes."""
        order = SEVERITY_ORDER
        v1 = order.get(sev1, -1)
        v2 = order.get(sev2, -1)
        v3 = order.get(sev3, -1)
        return v1 < v2 < v3
