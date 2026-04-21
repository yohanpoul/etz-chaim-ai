"""Gabriel — Enforcement du jugement.

גַּבְרִיאֵל — Force de Dieu. Gevurah incarnée.
Détruit Sodome (Bava Metzia 86b), détruit les armées (Sanhedrin 95b).
Son épée est aiguisée depuis les six jours de la Création.

En IA : valide les outputs des Malakhim, DÉTRUIT les résultats invalides.
PAS de la communication — de l'ENFORCEMENT.
⚠️ NE PAS confondre avec Gabriel=messager (angélologie chrétienne).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from malakhim.models import MalakhResult


@dataclass
class EnforcementResult:
    """Résultat de la validation Gabriel."""
    valid: bool
    violations: list[str] = field(default_factory=list)
    severity: str = "none"  # none, warning, rejected, destroyed


class Gabriel:
    """גַּבְרִיאֵל — Enforcement du jugement.

    Valide les outputs selon des critères immuables.
    Son épée est aiguisée depuis la Création — les critères ne changent PAS.
    """

    # Critères immuables (aiguisés depuis la Création)
    MIN_RESPONSE_LENGTH = 10
    MAX_REPETITION_RATIO = 0.5  # >50% de tokens répétés = invalide

    FORBIDDEN_PATTERNS = [
        r"(?i)as an ai",
        r"(?i)i cannot",
        r"(?i)i'm sorry,? but",
        r"(?i)i apologize",
    ]

    def validate_output(self, result: MalakhResult, kavvanah: dict | None = None) -> EnforcementResult:
        """Valider un output de Malakh. Détruire si invalide."""
        violations = []
        kavvanah = kavvanah or {}

        # 1. Réponse vide ou trop courte
        if not result.response or len(result.response.strip()) < self.MIN_RESPONSE_LENGTH:
            violations.append("response_too_short")

        # 2. Réponse qui est un refus déguisé
        if result.response:
            for pattern in self.FORBIDDEN_PATTERNS:
                if re.search(pattern, result.response):
                    violations.append(f"refusal_pattern: {pattern}")
                    break

        # 3. Répétition excessive (signe d'hallucination en boucle)
        if result.response and len(result.response) > 100:
            words = result.response.lower().split()
            if words:
                unique = len(set(words))
                ratio = unique / len(words)
                if ratio < self.MAX_REPETITION_RATIO:
                    violations.append(f"excessive_repetition: {ratio:.2f} unique ratio")

        # 4. Score trop bas (si le hitkalelut a donné un mauvais score)
        if result.score < 0.0:
            violations.append(f"negative_score: {result.score}")

        # 5. Critère de succès non satisfait (si kavvanah le spécifie)
        required_keywords = kavvanah.get("required_keywords", [])
        if required_keywords and result.response:
            missing = [kw for kw in required_keywords if kw.lower() not in result.response.lower()]
            if missing:
                violations.append(f"missing_required_keywords: {missing}")

        # Déterminer la sévérité
        if not violations:
            return EnforcementResult(valid=True, severity="none")

        if any("too_short" in v or "refusal" in v for v in violations):
            return EnforcementResult(valid=False, violations=violations, severity="destroyed")

        return EnforcementResult(valid=True, violations=violations, severity="warning")

    def enforce(self, result: MalakhResult, kavvanah: dict | None = None) -> MalakhResult:
        """Appliquer l'enforcement. Si invalide, marquer le résultat comme échec."""
        verdict = self.validate_output(result, kavvanah)

        if verdict.severity == "destroyed":
            result.success = False
            result.metadata["gabriel_destroyed"] = True
            result.metadata["gabriel_violations"] = verdict.violations
        elif verdict.severity == "warning":
            result.hitkalelut_warnings.extend(
                [f"gabriel: {v}" for v in verdict.violations]
            )

        return result


def hook_post_tool(data: dict) -> dict:
    """Hook Claude CLI PostToolUse — valide l'output."""
    gabriel = Gabriel()

    output = data.get("tool_output", "")
    if not output or not isinstance(output, str):
        return {"decision": "approve"}

    # Vérifier les patterns de refus dans l'output
    for pattern in Gabriel.FORBIDDEN_PATTERNS:
        if re.search(pattern, output):
            return {"decision": "block", "reason": f"Gabriel: refusal pattern in output"}

    return {"decision": "approve"}
