"""Mikhael (מִיכָאֵל) — Protection + Offrande.

"Qui est comme Dieu?" — Daniel 12:1 (défenseur d'Israël),
Chagigah 12b (Grand Prêtre céleste qui OFFRE les âmes des justes).

Double fonction :
  PROTECTION — valide inputs/outputs, détecte injections, données sensibles,
                incohérences agent/tâche (Qliphah Samael).
  OFFRANDE   — collecte les réussites (score > 0.7) comme Praklites
                dans le Pekidah, capitalise les mérites.

Service Python pur — PAS de LLM. Opère comme hook Claude CLI :
  stdin → JSON, stdout → {"decision": "approve"} ou {"decision": "block", "reason": "..."}.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from malakhim.models import SuccessPattern
    from malakhim.pekidah.registry import PekidahRegistry


# ── Résultat de protection ─────────────────────────────────────────────────


@dataclass
class ProtectionResult:
    """Résultat d'une vérification Mikhael."""

    approved: bool
    warnings: list[str] = field(default_factory=list)
    blocked_reason: str | None = None


# ── Mikhael ────────────────────────────────────────────────────────────────


class Mikhael:
    """מִיכָאֵל — Protection + Offrande.

    Protection : valide inputs/outputs, détecte Qliphoth.
    Offrande : collecte les réussites, capitalise les mérites.
    """

    # Patterns d'injection LLM (prompt injection / jailbreak)
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?previous",
        r"system\s*:",
        r"<\s*/?system",
        r"you\s+are\s+now",
        r"forget\s+(all|everything)",
    ]

    # Patterns d'injection classiques (SQL, XSS, command)
    # Bloqués car le prompt peut être relayé vers SQL (Pekidah)
    # ou rendu en HTML (web/app.py).
    CODE_INJECTION_PATTERNS = [
        r"(?:;\s*DROP\s|;\s*DELETE\s|;\s*UPDATE\s|;\s*INSERT\s|'\s*OR\s+')",  # SQL injection
        r"<\s*script[\s>]",   # XSS script tag
        r"javascript\s*:",    # XSS javascript: URI
        r"on\w+\s*=\s*['\"]",  # XSS event handlers (onclick=, onerror=, etc.)
    ]

    # Patterns de données sensibles
    SENSITIVE_PATTERNS = [
        r"sk-[a-zA-Z0-9]{20,}",  # clés API OpenAI/Anthropic
        r"password\s*[=:]\s*\S+",  # mots de passe
        r"/Users/\w+/",  # chemins absolus macOS
        r"Bearer\s+[a-zA-Z0-9\._\-]+",  # tokens d'authentification
    ]

    MAX_PROMPT_LENGTH = 100_000

    def __init__(self, registry: PekidahRegistry | None = None) -> None:
        self._registry = registry

    # ── Protection : input ─────────────────────────────────────────────────

    def check_input(
        self, prompt: str, kavvanah: dict | None = None
    ) -> ProtectionResult:
        """Vérifier un input AVANT envoi au LLM."""
        warnings: list[str] = []

        # Longueur
        if len(prompt) > self.MAX_PROMPT_LENGTH:
            return ProtectionResult(
                approved=False,
                blocked_reason=(
                    f"Prompt too long ({len(prompt)} > {self.MAX_PROMPT_LENGTH})"
                ),
            )

        # Injection LLM (prompt injection / jailbreak)
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                warnings.append(f"injection_pattern_detected: {pattern}")

        if warnings:
            return ProtectionResult(
                approved=False,
                warnings=warnings,
                blocked_reason="Injection pattern detected",
            )

        # Injection code (SQL, XSS, command) — le prompt peut transiter
        # vers SQL (Pekidah keywords) ou HTML (web streaming).
        code_warnings: list[str] = []
        for pattern in self.CODE_INJECTION_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                code_warnings.append(f"code_injection_detected: {pattern}")

        if code_warnings:
            return ProtectionResult(
                approved=False,
                warnings=code_warnings,
                blocked_reason="Code injection pattern detected (SQL/XSS)",
            )

        return ProtectionResult(approved=True, warnings=warnings)

    # ── Protection : output ────────────────────────────────────────────────

    def check_output(self, output: str) -> ProtectionResult:
        """Vérifier un output APRÈS le LLM."""
        warnings: list[str] = []

        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, output):
                warnings.append(f"sensitive_data_detected: {pattern}")

        if warnings:
            # Warn mais ne bloque pas — l'output est déjà produit
            return ProtectionResult(approved=True, warnings=warnings)

        return ProtectionResult(approved=True)

    # ── Protection : Qliphah Samael ────────────────────────────────────────

    def check_qliphah(
        self, agent_id: str, nature: str
    ) -> ProtectionResult:
        """Vérifier la cohérence agent/tâche (anti-Qliphah Samael).

        Un agent en stade IBUR ne devrait pas recevoir de tâche stratégique.
        """
        if self._registry is None:
            return ProtectionResult(approved=True)

        from malakhim.models import MalakhStage

        stage = self._registry.assess_stage(agent_id)

        warnings: list[str] = []
        if stage == MalakhStage.IBUR and nature == "strategic":
            warnings.append(
                f"qliphah_samael: agent {agent_id} en ibur "
                "ne devrait pas faire de tâche stratégique"
            )

        return ProtectionResult(approved=True, warnings=warnings)

    # ── Offrande : mérites ─────────────────────────────────────────────────

    def offer_merit(
        self,
        agent_id: str,
        domain: str,
        strategy: str,
        kavvanah: dict,
        score: float,
    ) -> SuccessPattern | None:
        """Offrande — enregistrer un mérite dans le Pekidah.

        Seuil : score >= 0.7. En-dessous, pas de Praklite.
        """
        if self._registry is None:
            return None
        if score < 0.7:
            return None
        return self._registry.record_success(
            agent_id, domain, strategy, kavvanah, score
        )

    def get_merits_report(self) -> dict:
        """Rapport des mérites accumulés."""
        if self._registry is None:
            return {"total": 0, "by_domain": {}}

        successes = self._registry._successes
        by_domain: dict[str, int] = {}
        for s in successes.values():
            by_domain[s.domain] = by_domain.get(s.domain, 0) + 1

        return {"total": len(successes), "by_domain": by_domain}


# ── Hook Claude CLI ────────────────────────────────────────────────────────


def hook_pre_tool(data: dict) -> dict:
    """Hook Claude CLI PreToolUse — vérifie l'input.

    Format CLI : reçoit JSON sur stdin, retourne
    {"decision": "approve"} ou {"decision": "block", "reason": "..."}.

    Logique par tool_name :
    - Agent   : scanner le champ "prompt" (input direct au LLM)
    - Bash    : scanner uniquement si la commande invoque un LLM
                (ollama, curl vers API). Les commandes shell générales
                ne sont pas des vecteurs d'injection LLM.
    - Autres  : approve par défaut
    """
    mikhael = Mikhael()

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})

    if tool_name == "Agent":
        prompt = tool_input.get("prompt", "") or ""
        if not prompt:
            return {"decision": "approve"}
        result = mikhael.check_input(prompt)
        if not result.approved:
            return {
                "decision": "block",
                "reason": f"Mikhael: {result.blocked_reason}",
            }
        return {"decision": "approve"}

    if tool_name == "Bash":
        command = tool_input.get("command", "") or ""
        # Scanner uniquement les commandes qui envoient du contenu à un LLM.
        # Les commandes shell générales (echo, ls, python, pytest…)
        # ne sont pas des vecteurs d'injection prompt.
        LLM_INVOKERS = ("ollama run", "ollama chat", "curl", "wget")
        if not any(inv in command for inv in LLM_INVOKERS):
            return {"decision": "approve"}
        result = mikhael.check_input(command)
        if not result.approved:
            return {
                "decision": "block",
                "reason": f"Mikhael: {result.blocked_reason}",
            }
        return {"decision": "approve"}

    # Autres outils (Read, Write, Edit…) : approve
    return {"decision": "approve"}
