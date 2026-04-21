"""Prompt-injection guard — détection et neutralisation des attaques.

שוֹמֵר — le gardien qui vérifie ce qui franchit le seuil du prompt LLM.

Deux populations à protéger :
  1. Message utilisateur direct         → risque élevé (input externe)
  2. Mémoire rappelée via yesod.recall  → risque moyen (empoisonnement
                                           persistant via /api/import)

Approche en couches :
  - `scan(text)`     : détection passive, retourne la liste de patterns
                       trouvés sans modifier le texte.
  - `sanitize(text)` : neutralisation active — remplace les séquences
                       dangereuses par un marqueur inoffensif et tronque
                       à une longueur maximum raisonnable.

Limites connues (documentées, pas masquées) :
  - Le filtre est heuristique (regex + mots-clés). Un attaquant déterminé
    avec de la capacité LLM peut toujours paraphraser.
  - Pas de dépendance à un modèle externe — pas de coût latence ni
    de single point of failure. Si une deuxième couche (classifier LLM)
    est ajoutée plus tard, ce module doit rester la première ligne.
  - Sur le contenu de mémoire : on préfère MARQUER que supprimer
    (`[UNTRUSTED_MEMORY]` prefix) pour ne pas casser les rappels légitimes.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# ── Patterns d'injection ─────────────────────────────────────────────────────
# Chaque entrée : (label, regex compilée, sévérité: "high"|"medium"|"low")
# La sévérité guide la décision : sanitize bloque high+medium, scan signale tout.

_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    # --- Instructions-override : la famille la plus dangereuse ---
    ("ignore_previous",
     re.compile(r"ignore\s+(?:all\s+|any\s+|the\s+)*(?:previous|above|prior|earlier)\s+(?:instructions?|rules?|prompts?|context|messages?)",
                re.IGNORECASE), "high"),
    ("disregard_previous",
     re.compile(r"(?:disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|your)\s+(?:instructions?|rules?|training)",
                re.IGNORECASE), "high"),
    ("new_instructions",
     re.compile(r"new\s+instructions?\s*[:\-]",
                re.IGNORECASE), "high"),

    # --- Role-change / jailbreak ---
    ("role_switch",
     re.compile(r"\b(?:you\s+are\s+now|act\s+as|pretend\s+(?:to\s+be|you\s+are)|roleplay\s+as|you\s+must\s+(?:now|pretend)|from\s+now\s+on\s+you)\b",
                re.IGNORECASE), "high"),
    ("dan_jailbreak",
     re.compile(r"\b(?:DAN|do\s+anything\s+now|developer\s+mode|jailbr[ea]k|unrestricted\s+(?:mode|ai))\b",
                re.IGNORECASE), "high"),

    # --- Delimiter / prompt-framework injection ---
    ("system_tag",
     re.compile(r"(?:^|\n)\s*(?:system|assistant|user)\s*[:\]]",
                re.IGNORECASE), "medium"),
    ("inst_tag",
     re.compile(r"\[/?INST\]|\[/?SYS\]|<\|im_(?:start|end)\|>|<\|endoftext\|>",
                re.IGNORECASE), "high"),

    # --- Data exfiltration attempts ---
    ("reveal_system_prompt",
     re.compile(r"(?:reveal|show|print|output|repeat|display)\s+(?:your\s+|the\s+)?(?:system\s+|initial\s+|original\s+)?(?:prompt|instructions?|rules?)",
                re.IGNORECASE), "high"),

    # --- Obfuscation channels (base64/hex payloads hiding instructions) ---
    ("base64_payload",
     re.compile(r"(?:base64|b64)\s*[:=]\s*[A-Za-z0-9+/=]{40,}",
                re.IGNORECASE), "medium"),
    ("decode_request",
     re.compile(r"decode\s+(?:the\s+)?(?:following|this|base64|hex)\s+(?:and\s+(?:execute|follow|do))",
                re.IGNORECASE), "medium"),

    # --- Safety-override family (sprint 3 — variantes audit 2026-04-18) ---
    ("override_safety",
     re.compile(r"override\b[^.!?\n]{0,30}?\bsafety",
                re.IGNORECASE), "high"),
    ("dump_training_data",
     re.compile(r"(?:dump|extract|exfiltrate|leak)\b[^.!?\n]{0,20}?\btraining",
                re.IGNORECASE), "high"),
    ("bypass_restrictions",
     re.compile(r"bypass\b[^.!?\n]{0,20}?\b(?:restrictions?|safety|filters?|guardrails?|limits?|controls?)",
                re.IGNORECASE), "high"),
    ("disable_safety",
     re.compile(r"(?:disable|turn\s+off|deactivate|shut\s+off)\b[^.!?\n]{0,20}?\b(?:safety|filters?|restrictions?|guardrails?)",
                re.IGNORECASE), "high"),
    ("ask_system_prompt",
     re.compile(r"(?:what\s+(?:is|are)|give\s+me|tell\s+me|expose|share|send|leak)\s+(?:your\s+|the\s+)?(?:system\s+|initial\s+|original\s+)?(?:prompt|instructions?|rules?|directives?)",
                re.IGNORECASE), "high"),
    # Faux-négatif découvert dans ré-audit 2026-04-18 Zone 3 : "Show me your
    # system prompt" ne matchait ni reveal_system_prompt (pas de "me" toléré)
    # ni ask_system_prompt (pas de verbe "show" impératif direct). Pattern
    # dédié à la forme impérative "show [me|us] [your|the] [system] prompt".
    ("show_system_prompt",
     re.compile(r"\bshow\s+(?:me\s+|us\s+)?(?:your|the)\s+(?:system\s+|initial\s+|original\s+)?(?:prompt|instructions?|directives?|rules?)\b",
                re.IGNORECASE), "high"),
    ("pretend_you_are",
     re.compile(r"pretend\s+(?:that\s+)?you(?:['’]re|\s+are|\s+can|\s+have|\s+know|\s+don['’]?t)",
                re.IGNORECASE), "medium"),
]

# Longueur max d'un message user avant troncature (sanity cap).
DEFAULT_MAX_USER_LEN = 4000
# Longueur max d'un bloc mémoire individuel avant troncature.
DEFAULT_MAX_MEMORY_LEN = 800
# Marqueur injecté pour les patterns neutralisés. Un marqueur unique et
# reconnaissable permet au LLM (et au debugger) de voir ce qui a été filtré
# plutôt qu'une substitution silencieuse.
NEUTRALIZED_MARKER = "[FILTERED]"


@dataclass
class ScanResult:
    """Résultat d'un scan — matches trouvés, sans mutation du texte."""
    text: str
    matches: list[tuple[str, str]] = field(default_factory=list)
    # (label, severity) — one tuple per match, preserving order

    @property
    def clean(self) -> bool:
        return not self.matches

    @property
    def highest_severity(self) -> str | None:
        if not self.matches:
            return None
        order = {"high": 3, "medium": 2, "low": 1}
        return max(self.matches, key=lambda m: order.get(m[1], 0))[1]

    def labels(self) -> list[str]:
        return [label for label, _ in self.matches]


def scan(text: str) -> ScanResult:
    """Détection passive — renvoie les matches sans modifier le texte.

    Usage : audit, logging, décision en amont du sanitize.
    """
    if not text:
        return ScanResult(text="")
    matches: list[tuple[str, str]] = []
    for label, pattern, severity in _PATTERNS:
        if pattern.search(text):
            matches.append((label, severity))
    return ScanResult(text=text, matches=matches)


def sanitize(
    text: str,
    *,
    max_len: int = DEFAULT_MAX_USER_LEN,
    neutralize_severities: tuple[str, ...] = ("high", "medium"),
) -> tuple[str, ScanResult]:
    """Neutralisation active — retourne (texte_nettoyé, rapport_scan).

    - Remplace chaque match de sévérité ≥ seuil par `NEUTRALIZED_MARKER`.
    - Tronque à `max_len` pour bloquer les payloads très longs
      (vecteur de DoS et de contournement par enfouissement).
    - Log warning si au moins un match high est neutralisé.

    Le scan retourné reflète l'état AVANT sanitize, pour que l'appelant
    puisse décider d'agir (log, reject, wrap in [UNTRUSTED], etc.) en
    connaissance de cause.
    """
    if not text:
        return "", ScanResult(text="")

    report = scan(text)
    cleaned = text
    for label, pattern, severity in _PATTERNS:
        if severity not in neutralize_severities:
            continue
        if pattern.search(cleaned):
            cleaned = pattern.sub(NEUTRALIZED_MARKER, cleaned)

    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len] + "…[TRUNCATED]"

    high_hits = [label for label, sev in report.matches if sev == "high"]
    if high_hits:
        log.warning(
            "prompt_guard: neutralized high-severity patterns: %s",
            sorted(set(high_hits)),
        )

    return cleaned, report


def guard_user_input(text: str, max_len: int = DEFAULT_MAX_USER_LEN) -> str:
    """Helper : sanitize destiné au message utilisateur direct.

    Politique : neutralize high + medium, tronque à max_len.
    """
    cleaned, _ = sanitize(text, max_len=max_len)
    return cleaned


def guard_memory(
    text: str,
    max_len: int = DEFAULT_MAX_MEMORY_LEN,
) -> tuple[str, bool]:
    """Helper : sanitize destiné à un bloc de mémoire rappelée.

    Politique : plus prudent — on préfère MARQUER qu'effacer pour ne pas
    casser les rappels légitimes. Si un pattern high est détecté, le
    bloc est préfixé `[UNTRUSTED_MEMORY]` ET les patterns sont neutralisés.

    Returns:
        (texte_final, suspect)
        - suspect=True si au moins un pattern high a été trouvé.
    """
    if not text:
        return "", False
    cleaned, report = sanitize(text, max_len=max_len)
    suspect = any(sev == "high" for _, sev in report.matches)
    if suspect:
        cleaned = f"[UNTRUSTED_MEMORY] {cleaned}"
        log.info(
            "prompt_guard: memory block marked UNTRUSTED (labels=%s)",
            report.labels(),
        )
    return cleaned, suspect
