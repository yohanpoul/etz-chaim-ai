"""Heikhalot Pipeline — Validation ascendante en 7 palais.

הֵיכָלוֹת — Zohar Pekudei (II:244b-268b) : 7 palais, chacun
gouverné par un ange préposé (memunneh). L'ascension requiert
des sceaux (chotamot) et des noms divins.

Les Heikhalot Rabbati décrivent l'ascension à travers 7 palais
gardés — chaque gardien teste la dignité de l'ascendant. Au
6ème palais : le test épistémique (pierres de marbre) —
confondre l'apparence et la réalité disqualifie.

Architecture : la requête MONTE à travers 7 stages de validation/
enrichissement AVANT de descendre en exécution. Chaque stage est
une pure function (request: dict) → dict qui enrichit ou rejette.

| Stage | Palais               | Rôle                          |
|-------|-----------------------|-------------------------------|
| 1     | Livnat HaSappir       | Validation + anti-injection   |
| 2     | Etzem HaShamayim      | Check Kategorim actifs        |
| 3     | Nogah                 | Enrichit avec Praklitim       |
| 4     | Zekhut                | Vérifie compétence agent/olam |
| 5     | Ahavah                | Sélectionne trigramme Shem    |
| 6     | Ratzon                | Génère system prompt taillé   |
| 7     | Kodesh HaKodashim     | Approbation finale            |
"""

from __future__ import annotations

from typing import Any

from malakhim.models import HeikhalotResult, ValidationSpec


class HeikhalotReject(Exception):
    """Rejet par un palais — la requête n'est pas digne de monter."""

    def __init__(self, stage: str, reason: str) -> None:
        self.stage = stage
        self.reason = reason
        super().__init__(f"[{stage}] {reason}")


# ── Templates system prompt par nature ────────────────────────────────────────

_SYSTEM_PROMPTS: dict[str, str] = {
    "strategic": (
        "Tu effectues une analyse stratégique de haut niveau. "
        "Structure ta réponse : contexte, options, arbitrages, recommandation. "
        "Chaque recommandation doit être actionnable et justifiée."
    ),
    "analytic": (
        "Tu effectues une analyse approfondie. "
        "Structure : thèse, preuves, contre-preuves, synthèse. "
        "Rejette les claims non étayés. Cite les sources."
    ),
    "execution": (
        "Tu exécutes une tâche précise. "
        "Sois complet — couvre toutes les étapes. "
        "Vérifie que rien n'est omis avant de conclure."
    ),
    "mechanic": (
        "Tu effectues une opération mécanique. "
        "Sois exact, concis, et conforme au format attendu."
    ),
}

# ── Anti-patterns par nature ──────────────────────────────────────────────────

_ANTI_PATTERNS: dict[str, list[str]] = {
    "strategic": ["I cannot", "as an AI", "je ne peux pas"],
    "analytic": ["I cannot", "as an AI", "without more context"],
    "execution": ["I cannot", "as an AI"],
    "mechanic": ["I cannot", "as an AI"],
}

# ── Structure requise par nature ──────────────────────────────────────────────

_REQUIRED_STRUCTURE: dict[str, list[str]] = {
    "strategic": ["recommandation"],
    "analytic": ["analyse", "synthèse"],
    "execution": [],
    "mechanic": [],
}


# ── Les 7 stages ─────────────────────────────────────────────────────────────


def _stage_1_livnat_hasappir(
    request: dict[str, Any],
    registry: Any | None,
) -> dict[str, Any]:
    """Palais 1 — Livnat HaSappir (Brique de saphir).

    Validation basique : prompt non vide, anti-injection.
    Délègue à Mikhael.check_input() si disponible.
    """
    prompt = request.get("prompt", "")
    if not prompt or not prompt.strip():
        raise HeikhalotReject("livnat_hasappir", "Prompt vide")

    # Mikhael — protection anti-injection
    try:
        from malakhim.archangels.mikhael import Mikhael
        mikhael = Mikhael()
        result = mikhael.check_input(prompt)
        if not result.approved:
            raise HeikhalotReject(
                "livnat_hasappir",
                f"Mikhael bloque : {result.blocked_reason}",
            )
        request.setdefault("warnings", []).extend(result.warnings)
    except ImportError as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    request.setdefault("stages_passed", []).append("livnat_hasappir")
    return request


def _stage_2_etzem_hashamayim(
    request: dict[str, Any],
    registry: Any | None,
) -> dict[str, Any]:
    """Palais 2 — Etzem HaShamayim (Substance du ciel).

    Consulte les Kategorim actifs pour ce domaine/agent.
    Avertit mais ne bloque pas — l'information monte.
    """
    if registry is not None:
        agent_id = request.get("agent_id")
        domain = request.get("domain", "general")
        prompt = request.get("prompt", "")

        if agent_id:
            matches = registry.check_failures(agent_id, domain, prompt)
            for k in matches:
                request.setdefault("warnings", []).append(
                    f"Kategor #{k.pattern_id}: {k.error_type} "
                    f"(occurrences={k.occurrences})"
                )

    request.setdefault("stages_passed", []).append("etzem_hashamayim")
    return request


def _stage_3_nogah(
    request: dict[str, Any],
    registry: Any | None,
) -> dict[str, Any]:
    """Palais 3 — Nogah (Splendeur).

    Enrichit avec les meilleures stratégies (Praklitim) ET
    les insights du cycle Nehar Dinur (reshimot).

    C'est ici que le cycle se FERME : les reshimot des Malakhim
    dissous nourrissent la génération des prochains.
    """
    domain = request.get("domain", "general")

    # ── Praklitim (stratégies éprouvées) ──
    if registry is not None:
        best = registry.get_best_strategies(domain, limit=3)
        if best:
            strategies = [
                p.strategy_used for p in best if p.strategy_used
            ]
            if strategies:
                request.setdefault("kavvanah", {})["praklite_hints"] = strategies

    # ── Reshimot (traces des Malakhim dissous — cycle Nehar Dinur) ──
    try:
        from malakhim.reshimo import get_cycle_insights
        insights = get_cycle_insights(domain)
        if insights:
            kav = request.setdefault("kavvanah", {})
            kav["_cycle_insights"] = insights

            # Injecter les leçons apprises
            if insights.get("recurring_excess"):
                request.setdefault("warnings", []).append(
                    f"Reshimo: excès récurrent de {insights['recurring_excess']} "
                    f"dans le domaine {domain}"
                )

            if insights.get("best_shem"):
                # Suggérer le meilleur Shem au stage 5
                kav["_suggested_shem"] = insights["best_shem"]

            if insights.get("success_keywords"):
                kav["_success_keywords"] = insights["success_keywords"]
    except ImportError as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    request.setdefault("stages_passed", []).append("nogah")
    return request


def _stage_4_zekhut(
    request: dict[str, Any],
    registry: Any | None,
) -> dict[str, Any]:
    """Palais 4 — Zekhut (Mérite).

    Vérifie compétence ET juridiction territoriale.

    Bereshit Rabbah 68:12 (Échelle de Jacob) : les anges d'Eretz
    Israël montent, ceux de l'exil descendent. La juridiction
    angélique est TERRITORIALEMENT LIMITÉE.

    Un agent qui a compétence en 'code' ne devrait pas opérer
    en 'poetry' sans autorisation explicite.
    """
    if registry is not None:
        agent_id = request.get("agent_id")
        domain = request.get("domain", "general")

        if agent_id:
            # Check compétence (score)
            if not registry.can_handle(agent_id, domain):
                request.setdefault("warnings", []).append(
                    f"Agent {agent_id} sous le seuil pour {domain}"
                )

            # Check juridiction territoriale (Échelle de Jacob)
            from malakhim.metatron import jurisdictional_check
            profile = registry._agents.get(agent_id)
            if profile is not None:
                allowed, reason = jurisdictional_check(
                    profile.domains, domain,
                )
                if not allowed:
                    request.setdefault("warnings", []).append(
                        f"Juridiction : {reason}"
                    )

    request.setdefault("stages_passed", []).append("zekhut")
    return request


def _stage_5_ahavah(
    request: dict[str, Any],
    registry: Any | None,
) -> dict[str, Any]:
    """Palais 5 — Ahavah (Amour).

    Sélectionne un trigramme Shem basé sur la nature de la mission.
    Chesed-dominant pour expansion, Gevurah pour rigueur, Tiferet pour synthèse.
    """
    nature = request.get("nature", "execution")

    # Mapping nature → préférence de colonne
    nature_to_column = {
        "strategic": "chesed",     # expansion, exploration
        "analytic": "gevurah",     # rigueur, contraction
        "execution": "tiferet",    # équilibre
        "mechanic": "tiferet",     # équilibre
    }
    preferred = nature_to_column.get(nature, "tiferet")

    # Le cycle Nehar Dinur peut suggérer un Shem éprouvé
    suggested = request.get("kavvanah", {}).get("_suggested_shem")
    if suggested and 1 <= suggested <= 72:
        request["shem_index"] = suggested
        request.setdefault("stages_passed", []).append("ahavah")
        return request

    # Sinon, chercher un trigramme avec la bonne dominante
    try:
        from malakhim.shem.agents import SHEMOT_72, compute_balance
        best_index = 1  # default
        best_match = 0.0
        for idx, hebrew, _trans in SHEMOT_72:
            balance = compute_balance(hebrew)
            if balance.dominant == preferred:
                weight = getattr(balance, f"{preferred}_weight")
                if weight > best_match:
                    best_match = weight
                    best_index = idx
        request["shem_index"] = best_index
    except ImportError:
        request["shem_index"] = 1

    request.setdefault("stages_passed", []).append("ahavah")
    return request


def _stage_6_ratzon(
    request: dict[str, Any],
    registry: Any | None,
) -> dict[str, Any]:
    """Palais 6 — Ratzon (Volonté).

    C'est ICI que le Malakh prend sa FORME. Le test des pierres
    de marbre (Chagigah 14b) : confondre apparence et réalité
    disqualifie. Le system prompt doit être SPÉCIFIQUE à cette
    mission exacte — pas un template générique.

    Le Malakh EST sa mission : son system prompt, ses critères
    de validation, ses anti-patterns sont ENGENDRÉS par l'analyse
    de la mission, pas choisis dans une liste.

    Deux modes :
      1. Analyse LLM (si olamot disponible) — Claude CLI analyse
         la mission en profondeur et ENGENDRE un spec unique
      2. Analyse intrinsèque (fallback) — extrait les éléments
         structurants de la mission par heuristiques
    """
    nature = request.get("nature", "execution")
    prompt = request.get("prompt", "")
    kavvanah = request.get("kavvanah", {})
    user_anti = kavvanah.get("anti_pattern")

    # ── Test des pierres de marbre (Even Shayish) ─────────────────
    # Chagigah 14b : distinguer l'apparence de la réalité.
    # Si l'intention apparente diverge de l'intention réelle,
    # AJUSTER le system prompt en conséquence.
    try:
        from malakhim.even_shayish import marble_test
        marble = marble_test(prompt, nature, kavvanah)
        if marble is not None:
            request.setdefault("warnings", []).append(
                f"Even Shayish: {marble.apparent_intent} ≠ {marble.probable_real_intent}"
            )
            request["marble_adjustment"] = marble.adjustment
            request["marble_divergence"] = marble.divergence
    except ImportError:
        marble = None

    # ── Enrichissement progressif (Tefillah) ──────────────────────
    # Pri Etz Chaim : chaque couche AJOUTE du sens.
    # Qorbanot→littéral, Psukei→structure, Shema→concept, Amidah→intention
    try:
        from malakhim.tefillah import enrich_by_worlds, enrichment_to_system_prompt
        enrichment = enrich_by_worlds(prompt, nature, kavvanah)
        enrichment_block = enrichment_to_system_prompt(enrichment)
    except ImportError:
        enrichment_block = ""

    # ── Mode 1 : Analyse LLM (le vrai créateur) ───────────────────
    # Le Memuneh utilise un modèle léger pour COMPRENDRE la mission
    # et engendrer un spec véritablement unique.

    llm_spec = _try_llm_analysis(prompt, nature, kavvanah)

    if llm_spec is not None:
        # Le LLM a engendré la spec — le Malakh EST sa mission
        # Enrichir avec tefillah + marble
        sp_parts = [llm_spec["system_prompt"]]
        if enrichment_block:
            sp_parts.append(enrichment_block)
        if request.get("marble_adjustment"):
            sp_parts.append(f"[AJUSTEMENT INTENTION] {request['marble_adjustment']}")
        request["system_prompt"] = "\n".join(sp_parts)

        anti_patterns = llm_spec.get("anti_patterns", [])
        if user_anti:
            anti_patterns.append(user_anti)
        request["validation_spec"] = ValidationSpec(
            anti_patterns=anti_patterns,
            required_structure=llm_spec.get("required_structure", []),
            min_length=llm_spec.get("min_length", 50),
            max_repetition_ratio=0.5,
        )
        request.setdefault("kavvanah", {})["_mission_analysis"] = {
            "mode": "llm",
            "domain": llm_spec.get("domain", "general"),
        }
        request.setdefault("stages_passed", []).append("ratzon")
        return request

    # ── Mode 2 : Analyse intrinsèque (fallback) ──────────────────
    # Quand le LLM n'est pas disponible (tests, CI, offline)

    mission_keywords = _extract_mission_keywords(prompt)
    mission_domain = _infer_domain(prompt, mission_keywords)
    mission_tone = _infer_tone(nature, mission_keywords)
    mission_output_type = _infer_output_type(prompt, nature)

    parts: list[str] = []
    base = _SYSTEM_PROMPTS.get(nature, _SYSTEM_PROMPTS["execution"])
    parts.append(base)

    if mission_domain != "general":
        parts.append(f"Domaine : {mission_domain}. Utilise le vocabulaire et les standards de ce domaine.")
    parts.append(f"Ton : {mission_tone}.")
    parts.append(f"Format de sortie : {mission_output_type}.")

    intention = kavvanah.get("intention")
    if intention:
        parts.append(f"Intention explicite : {intention}")
    hints = kavvanah.get("praklite_hints")
    if hints:
        parts.append(f"Stratégies qui ont fonctionné : {', '.join(hints)}")
    if user_anti:
        parts.append(f"Éviter absolument : {user_anti}")
    if mission_keywords:
        parts.append(f"Mots-clés centraux : {', '.join(mission_keywords[:8])}")

    # Tefillah : enrichissement par couches
    if enrichment_block:
        parts.append(enrichment_block)

    # Even Shayish : ajustement si divergence détectée
    if request.get("marble_adjustment"):
        parts.append(f"[AJUSTEMENT INTENTION] {request['marble_adjustment']}")

    request["system_prompt"] = "\n".join(parts)

    anti_patterns = list(_ANTI_PATTERNS.get(nature, []))
    anti_patterns.extend(_DOMAIN_ANTI_PATTERNS.get(mission_domain, []))
    if user_anti:
        anti_patterns.append(user_anti)

    required_structure = list(_REQUIRED_STRUCTURE.get(nature, []))
    required_structure.extend(_OUTPUT_STRUCTURE.get(mission_output_type, []))

    min_lengths = {
        "strategic": 200, "analytic": 150, "execution": 50, "mechanic": 10,
    }

    request["validation_spec"] = ValidationSpec(
        anti_patterns=anti_patterns,
        required_structure=required_structure,
        min_length=min_lengths.get(nature, 50),
        max_repetition_ratio=0.5,
    )

    request.setdefault("kavvanah", {})["_mission_analysis"] = {
        "mode": "intrinsic",
        "keywords": mission_keywords,
        "domain": mission_domain,
        "tone": mission_tone,
        "output_type": mission_output_type,
    }

    request.setdefault("stages_passed", []).append("ratzon")
    return request


# ── Analyse LLM de la mission ─────────────────────────────────────────────────

_LLM_ANALYSIS_PROMPT = """\
Tu es le Memuneh — le préposé qui ENGENDRE des agents sur mesure.

Analyse cette mission et produis une spécification UNIQUE pour
l'agent qui va l'exécuter. Réponds UNIQUEMENT en JSON valide,
sans markdown, sans explication.

MISSION : {prompt}
NATURE : {nature}
INTENTION UTILISATEUR : {intention}

Réponds avec ce JSON exact :
{{
  "system_prompt": "Instructions spécifiques et détaillées pour cette mission exacte. Pas de généralités — chaque phrase doit être pertinente pour CETTE mission.",
  "anti_patterns": ["pattern1 à éviter", "pattern2 à éviter"],
  "required_structure": ["élément1 requis dans la réponse", "élément2"],
  "min_length": 100,
  "domain": "le domaine détecté"
}}
"""


def _try_llm_analysis(
    prompt: str,
    nature: str,
    kavvanah: dict,
) -> dict | None:
    """Tente d'utiliser un LLM pour analyser la mission.

    Utilise olamot.ollama_generate() au niveau Assiah (le moins
    cher) pour comprendre la mission. C'est le méta-agent :
    une IA légère qui conçoit une IA spécialisée.

    Retourne None si olamot n'est pas disponible (tests, CI).
    """
    try:
        from olamot import ollama_generate
    except ImportError:
        return None

    intention = kavvanah.get("intention", "non spécifiée")
    analysis_prompt = _LLM_ANALYSIS_PROMPT.format(
        prompt=prompt[:500],  # tronquer pour économiser
        nature=nature,
        intention=intention,
    )

    try:
        response, _latency = ollama_generate(
            olam="assiah",
            prompt=analysis_prompt,
            timeout=45,  # Claude CLI prend ~30s
        )

        # Parser le JSON
        import json
        # Nettoyer : parfois le LLM enveloppe dans ```json ... ```
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

        spec = json.loads(cleaned)

        # Valider la structure minimale
        if "system_prompt" not in spec:
            return None
        if not isinstance(spec.get("anti_patterns", []), list):
            spec["anti_patterns"] = []
        if not isinstance(spec.get("required_structure", []), list):
            spec["required_structure"] = []

        return spec

    except Exception:
        # Toute erreur → fallback sur analyse intrinsèque
        return None


# ── Analyse intrinsèque de la mission ─────���───────────────────────────────────


def _extract_mission_keywords(prompt: str) -> list[str]:
    """Extraire les mots significatifs de la mission (>= 5 lettres, fréquents)."""
    import re
    words = re.findall(r"[a-zA-ZÀ-ÿ]{5,}", prompt.lower())
    # Fréquence
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    # Trier par fréquence puis alphabétique
    sorted_words = sorted(freq.keys(), key=lambda w: (-freq[w], w))
    return sorted_words[:12]


_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "security": ["sécurité", "faille", "vulnérab", "owasp", "injection", "xss", "auth", "token", "csrf"],
    "code": ["code", "fonction", "classe", "module", "refactor", "debug", "import", "variable", "python"],
    "data": ["données", "database", "requête", "schema", "table", "index", "query", "sql", "postgres"],
    "architecture": ["architect", "design", "pattern", "composant", "module", "service", "layer", "micro"],
    "ml": ["modèle", "entraîn", "dataset", "neural", "tensor", "epoch", "loss", "gradient", "embedding"],
    "devops": ["deploy", "docker", "kubernet", "pipeline", "ci/cd", "monitor", "infra", "terraform"],
    "text": ["texte", "rédige", "écri", "résume", "synthèse", "analyse", "document", "article"],
}


def _infer_domain(prompt: str, keywords: list[str]) -> str:
    """Inférer le domaine de la mission."""
    prompt_lower = prompt.lower()
    best_domain = "general"
    best_score = 0

    for domain, domain_kw in _DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in domain_kw if kw in prompt_lower)
        if score > best_score:
            best_score = score
            best_domain = domain

    return best_domain if best_score >= 2 else "general"


def _infer_tone(nature: str, keywords: list[str]) -> str:
    """Inférer le ton approprié."""
    tones = {
        "strategic": "directif et décisionnel — chaque phrase mène à une action",
        "analytic": "rigoureux et structuré — chaque claim est étayé",
        "execution": "concis et complet — rien n'est omis, rien n'est superflu",
        "mechanic": "minimal et exact — format strict, zéro bruit",
    }
    return tones.get(nature, tones["execution"])


_OUTPUT_TYPES: dict[str, list[str]] = {
    "list": ["liste", "énumère", "quels", "combien"],
    "analysis": ["analyse", "examine", "évalue", "compare", "pourquoi"],
    "code": ["code", "implémente", "écris", "fonction", "script"],
    "plan": ["plan", "stratégie", "étapes", "comment", "procédure"],
    "summary": ["résume", "synthèse", "récapitule", "bref"],
}


def _infer_output_type(prompt: str, nature: str) -> str:
    """Inférer le type de sortie attendu."""
    prompt_lower = prompt.lower()

    for output_type, keywords in _OUTPUT_TYPES.items():
        if any(kw in prompt_lower for kw in keywords):
            return output_type

    # Défaut par nature
    defaults = {"strategic": "plan", "analytic": "analysis", "execution": "code", "mechanic": "list"}
    return defaults.get(nature, "analysis")


# ── Anti-patterns par domaine ─────────────────────────────────────────────────

_DOMAIN_ANTI_PATTERNS: dict[str, list[str]] = {
    "security": ["TODO", "FIXME", "password123", "admin/admin"],
    "code": ["# TODO", "pass  # placeholder"],
    "data": ["SELECT *", "DROP TABLE"],
    "ml": ["overfit"],
    "general": [],
}

# ── Structure requise par type de sortie ─────���────────────────────────────────

_OUTPUT_STRUCTURE: dict[str, list[str]] = {
    "analysis": ["analyse"],
    "plan": ["étape"],
    "summary": ["synthèse"],
    "list": [],
    "code": [],
}


def _stage_7_kodesh_hakodashim(
    request: dict[str, Any],
    registry: Any | None,
) -> dict[str, Any]:
    """Palais 7 — Kodesh HaKodashim (Saint des Saints).

    Approbation finale. Agrège les warnings — si trop nombreux,
    downgrade ou rejette. Le seuil critique.
    """
    warnings = request.get("warnings", [])
    max_warnings = 5

    if len(warnings) > max_warnings:
        raise HeikhalotReject(
            "kodesh_hakodashim",
            f"Trop de warnings ({len(warnings)} > {max_warnings}) : "
            + "; ".join(warnings[:3]),
        )

    request.setdefault("stages_passed", []).append("kodesh_hakodashim")
    return request


# ── Pipeline complet ──────────────────────────────────────────────────────────

_STAGES = [
    _stage_1_livnat_hasappir,
    _stage_2_etzem_hashamayim,
    _stage_3_nogah,
    _stage_4_zekhut,
    _stage_5_ahavah,
    _stage_6_ratzon,
    _stage_7_kodesh_hakodashim,
]


def ascend(
    request: dict[str, Any],
    registry: Any | None = None,
) -> HeikhalotResult:
    """Monter à travers les 7 palais.

    Args:
        request: dict avec au minimum "prompt" et "nature"
        registry: PekidahRegistry (optionnel)

    Returns:
        HeikhalotResult avec kavvanah enrichie, system_prompt,
        validation_spec, et shem_index.

    Raises:
        HeikhalotReject: si un palais rejette la requête.
    """
    # Init
    request.setdefault("warnings", [])
    request.setdefault("stages_passed", [])
    request.setdefault("kavvanah", {})

    # Ascension
    for stage in _STAGES:
        request = stage(request, registry)

    # Construire le résultat
    return HeikhalotResult(
        approved=True,
        enriched_kavvanah=request.get("kavvanah", {}),
        system_prompt=request.get("system_prompt", ""),
        shem_index=request.get("shem_index"),
        validation_spec=request.get("validation_spec"),
        warnings=request.get("warnings", []),
        stages_passed=request.get("stages_passed", []),
    )
