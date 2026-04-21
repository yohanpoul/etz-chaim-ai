"""ConfounderDetector — détection de variables confondantes.

Le gardien de Binah : trouver ce qui se cache derrière
une corrélation apparente.

"Le jeûne améliore la HRV" — mais les gens qui jeûnent
font aussi plus de sport, dorment mieux, et sont plus
éduqués. Le ConfounderDetector liste ces variables cachées.

Deux niveaux de détection :
  1. Statique : dictionnaire de confounders communs par domaine
  2. Contextuel (LLM) : confounders spécifiques à la paire cause/effet

Anti-Satariel Anan : un pattern dans du bruit est un faux confounder
qui masque l'absence de causalité réelle.
"""

from __future__ import annotations

import json
import logging
import re

from causalengine.models import Confounder

log = logging.getLogger("etz-daemon")


# Base de connaissances des confounders communs par domaine
COMMON_CONFOUNDERS: dict[str, list[dict]] = {
    "health": [
        {"name": "age", "plausibility": 0.9},
        {"name": "socioeconomic_status", "plausibility": 0.8},
        {"name": "genetics", "plausibility": 0.7},
        {"name": "exercise", "plausibility": 0.7},
        {"name": "diet", "plausibility": 0.7},
        {"name": "sleep", "plausibility": 0.6},
        {"name": "stress", "plausibility": 0.6},
        {"name": "smoking", "plausibility": 0.5},
        {"name": "alcohol", "plausibility": 0.5},
        {"name": "education", "plausibility": 0.5},
    ],
    "economics": [
        {"name": "inflation", "plausibility": 0.8},
        {"name": "population_growth", "plausibility": 0.7},
        {"name": "technology_change", "plausibility": 0.7},
        {"name": "policy_change", "plausibility": 0.6},
        {"name": "seasonality", "plausibility": 0.5},
        {"name": "global_events", "plausibility": 0.5},
    ],
    "psychology": [
        {"name": "selection_bias", "plausibility": 0.8},
        {"name": "placebo_effect", "plausibility": 0.7},
        {"name": "demand_characteristics", "plausibility": 0.7},
        {"name": "personality_traits", "plausibility": 0.6},
        {"name": "cultural_context", "plausibility": 0.6},
        {"name": "socioeconomic_status", "plausibility": 0.5},
    ],
    "technology": [
        {"name": "user_expertise", "plausibility": 0.7},
        {"name": "hardware_variation", "plausibility": 0.6},
        {"name": "network_conditions", "plausibility": 0.6},
        {"name": "software_version", "plausibility": 0.5},
        {"name": "sample_size", "plausibility": 0.5},
    ],
}

# Confounders universels (toujours plausibles)
UNIVERSAL_CONFOUNDERS = [
    {"name": "reverse_causation", "plausibility": 0.6},
    {"name": "common_cause", "plausibility": 0.5},
    {"name": "measurement_error", "plausibility": 0.4},
    {"name": "selection_bias", "plausibility": 0.4},
]


class ConfounderDetector:
    """Détecte les variables confondantes potentielles.

    Utilise une base de connaissances par domaine + confounders universels.
    La plausibilité est ajustée en fonction du contexte.
    """

    def __init__(self, max_confounders: int = 10):
        self.max_confounders = max_confounders
        self._consecutive_failures = 0

    def detect(
        self,
        cause: str,
        effect: str,
        domain: str = "",
    ) -> list[Confounder]:
        """Identifier les variables confondantes possibles.

        Returns:
            Liste de Confounder triés par plausibilité décroissante,
            limités à max_confounders.
        """
        confounders: list[Confounder] = []

        # 1. Confounders spécifiques au domaine
        confounders.extend(self._domain_confounders(cause, effect, domain))

        # 2. Confounders universels
        confounders.extend(self._universal_confounders(cause, effect))

        # 3. Dédupliquer par nom
        seen: set[str] = set()
        unique: list[Confounder] = []
        for c in confounders:
            if c.confounder_name not in seen:
                seen.add(c.confounder_name)
                unique.append(c)

        # 4. Filtrer : ne pas garder cause ou effect comme confounder
        cause_lower = cause.lower()
        effect_lower = effect.lower()
        unique = [
            c for c in unique
            if c.confounder_name.lower() != cause_lower
            and c.confounder_name.lower() != effect_lower
        ]

        # 5. Trier et limiter
        unique.sort(key=lambda c: c.plausibility, reverse=True)
        return unique[:self.max_confounders]

    def assess_control(
        self, confounders: list[Confounder],
    ) -> dict:
        """Évaluer si les confounders sont suffisamment contrôlés.

        Returns:
            {"all_controlled": bool, "uncontrolled": list, "control_ratio": float}
        """
        if not confounders:
            return {
                "all_controlled": True,
                "uncontrolled": [],
                "control_ratio": 1.0,
            }

        uncontrolled = [c for c in confounders if not c.controlled]
        high_plausibility_uncontrolled = [
            c for c in uncontrolled if c.plausibility >= 0.6
        ]

        controlled_count = sum(1 for c in confounders if c.controlled)
        ratio = controlled_count / len(confounders)

        return {
            "all_controlled": len(uncontrolled) == 0,
            "uncontrolled": [c.confounder_name for c in uncontrolled],
            "high_plausibility_uncontrolled": [
                c.confounder_name for c in high_plausibility_uncontrolled
            ],
            "control_ratio": round(ratio, 2),
        }

    def _domain_confounders(
        self, cause: str, effect: str, domain: str,
    ) -> list[Confounder]:
        """Confounders spécifiques au domaine."""
        domain_key = self._resolve_domain(domain)
        entries = COMMON_CONFOUNDERS.get(domain_key, [])

        return [
            Confounder(
                confounder_name=entry["name"],
                confounder_domain=domain_key,
                plausibility=entry["plausibility"],
            )
            for entry in entries
        ]

    def _universal_confounders(
        self, cause: str, effect: str,
    ) -> list[Confounder]:
        """Confounders universels — toujours plausibles."""
        return [
            Confounder(
                confounder_name=entry["name"],
                confounder_domain="universal",
                plausibility=entry["plausibility"],
            )
            for entry in UNIVERSAL_CONFOUNDERS
        ]

    def detect_contextual(
        self,
        cause: str,
        effect: str,
        domain: str = "",
        timeout: int = 30,
        **kwargs,
    ) -> list[Confounder]:
        """Détection contextuelle via LLM — confounders spécifiques.

        Demande au LLM de générer des confounders propres à la paire
        cause/effet, au-delà du dictionnaire statique.
        Passe par olamot.py (Binah → Briah).

        Returns:
            Liste de Confounder générés par le LLM, filtrés et validés.
            Liste vide si le LLM échoue (fail-safe).
        """
        prompt = (
            f"Given the causal claim: '{cause}' causes '{effect}'"
            f"{f' (domain: {domain})' if domain else ''}.\n\n"
            "List 3-5 specific confounding variables that could explain "
            "this correlation WITHOUT a direct causal link.\n"
            "For each, give a plausibility score 0.0-1.0.\n\n"
            "Reply ONLY with a JSON array, no explanation:\n"
            '[{"name": "...", "plausibility": 0.X, "domain": "..."}, ...]'
        )

        try:
            from olamot import ollama_generate

            # Enrichissement Sod HaKli : confounders statiques comme référence
            _static = self.detect(cause, effect, domain)
            _context_items = []
            if _static:
                _context_items.append(f"Confounders statiques: {', '.join(c.confounder_name for c in _static[:5])}")
            if domain:
                _context_items.append(f"Domaine causal: {domain}")

            raw, _ = ollama_generate(
                "yetzirah", prompt, timeout=timeout,
                temperature=0.3, num_predict=300,
                kavvanah={
                    "intention": "Identifier les confounders potentiels dans la relation causale analysée",
                    "critere_succes": "Confounders listés avec leur mécanisme d'influence",
                    "anti_pattern": "Ne pas inventer de confounders sans lien logique avec les variables",
                },
                context_items=_context_items or None,
                domain=domain or None,
                facts=[f"Cause: {cause}", f"Effet: {effect}"],
            )
            # Detect soft failures (timeout returns error string, not exception)
            if raw and ("[Erreur:" in raw or "timeout" in raw.lower()):
                log.warning("ConfounderDetector LLM soft-fail: %s", raw[:100])
                self._consecutive_failures += 1
                return self._domain_confounders("", "", domain) + self._universal_confounders("", "")

            confounders = self._parse_llm_confounders(raw, cause, effect, domain)
            if not confounders:
                # Parse returned nothing — use static fallback
                log.info("ConfounderDetector LLM: 0 parsed, falling back to static")
                return self._domain_confounders(cause, effect, domain) + self._universal_confounders(cause, effect)

            log.info(
                "ConfounderDetector LLM: %d confounders for '%s'→'%s'",
                len(confounders), cause[:50], effect[:50],
            )
            self._consecutive_failures = 0  # Reset on success
            return confounders

        except Exception as e:
            log.warning("ConfounderDetector LLM failed: %s", e)
            self._consecutive_failures += 1
            if self._consecutive_failures >= 3:
                log.error(
                    "ConfounderDetector: %d consecutive LLM failures",
                    self._consecutive_failures,
                )
            # Fallback: return static confounders instead of nothing
            return self._domain_confounders("", "", domain) + self._universal_confounders("", "")

    def detect_enriched(
        self,
        cause: str,
        effect: str,
        domain: str = "",
        use_llm: bool = True,
        **llm_kwargs,
    ) -> list[Confounder]:
        """Détection combinée : statique + contextuel LLM.

        Fusionne les confounders du dictionnaire et ceux du LLM,
        déduplique, et retourne le top max_confounders.
        """
        # 1. Statique
        static = self.detect(cause, effect, domain)

        # 2. Contextuel LLM
        contextual: list[Confounder] = []
        if use_llm:
            contextual = self.detect_contextual(cause, effect, domain, **llm_kwargs)

        # 3. Fusionner (LLM prioritaire pour le contexte)
        all_confs = contextual + static

        # 4. Dédupliquer par nom (garder le premier = LLM si disponible)
        seen: set[str] = set()
        unique: list[Confounder] = []
        for c in all_confs:
            key = c.confounder_name.lower().replace(" ", "_")
            if key not in seen:
                seen.add(key)
                unique.append(c)

        # 5. Filtrer cause/effect
        cause_lower = cause.lower()
        effect_lower = effect.lower()
        unique = [
            c for c in unique
            if c.confounder_name.lower() != cause_lower
            and c.confounder_name.lower() != effect_lower
        ]

        # 6. Trier et limiter
        unique.sort(key=lambda c: c.plausibility, reverse=True)
        return unique[:self.max_confounders]

    def diagnose(self) -> dict:
        """Test the LLM call with a known case — Or Chozer of Binah."""
        test_result = self.detect_contextual("stress", "illness", "health", timeout=30)
        return {
            "llm_working": len(test_result) > 0,
            "confounders_found": len(test_result),
            "details": [c.confounder_name for c in test_result],
            "consecutive_failures": self._consecutive_failures,
        }

    def _parse_llm_confounders(
        self,
        raw: str,
        cause: str,
        effect: str,
        domain: str,
    ) -> list[Confounder]:
        """Parser la réponse JSON du LLM en liste de Confounder."""
        if not raw or not raw.strip():
            log.debug("ConfounderDetector parse: empty response")
            return []

        # 1. Retirer les tags <think>...</think> (qwen3.5 thinking mode)
        cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()

        # 2. Extraire du code block markdown si présent (```json ... ```)
        code_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', cleaned, re.DOTALL)
        if code_match:
            cleaned = code_match.group(1)

        # 3. Extraire le JSON array d'objets
        match = re.search(r'\[\s*\{.*\}\s*\]', cleaned, re.DOTALL)
        if not match:
            log.debug(
                "ConfounderDetector parse: no JSON array found in response (%d chars): %.200s",
                len(cleaned), cleaned,
            )
            return []

        try:
            items = json.loads(match.group())
        except json.JSONDecodeError:
            log.debug(
                "ConfounderDetector parse: JSON decode failed: %.200s",
                match.group(),
            )
            return []

        confounders: list[Confounder] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = item.get("name", "").strip()
            if not name:
                continue
            plausibility = item.get("plausibility", 0.5)
            if not isinstance(plausibility, (int, float)):
                plausibility = 0.5
            plausibility = max(0.0, min(1.0, float(plausibility)))

            confounders.append(Confounder(
                confounder_name=name.lower().replace(" ", "_"),
                confounder_domain="contextual",
                plausibility=plausibility,
                controlled=True,
                how_controlled="llm_acknowledged",
            ))

        return confounders

    def _resolve_domain(self, domain: str) -> str:
        """Résoudre un domaine vers les catégories connues."""
        domain_lower = domain.lower()

        health_terms = {
            "health", "medicine", "medical", "biology", "nutrition",
            "fitness", "wellness", "pharmacology",
        }
        econ_terms = {
            "economics", "finance", "business", "market", "trade",
        }
        psych_terms = {
            "psychology", "cognitive", "behavior", "mental",
            "neuroscience", "social",
        }
        tech_terms = {
            "technology", "software", "computing", "ml",
            "machine_learning", "ai", "engineering",
        }

        for term in health_terms:
            if term in domain_lower:
                return "health"
        for term in econ_terms:
            if term in domain_lower:
                return "economics"
        for term in psych_terms:
            if term in domain_lower:
                return "psychology"
        for term in tech_terms:
            if term in domain_lower:
                return "technology"

        return domain_lower
