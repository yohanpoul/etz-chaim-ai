"""shemot/reasoning.py — Skills 41-50 : raisonnement.

Analogie, syllogisme, contrefactuel, fallacies, niveaux de preuve.
"""

from __future__ import annotations

from .base import Shem, ShemResult


class DetectAnalogy(Shem):
    """#41 HHH — Révélation : détecter une analogie structurelle."""
    name = "Detect Analogy"
    skill_id = "detect_analogy"
    trigram = "ההה"
    trigram_name = "HHH"
    number = 41
    category = "reasoning"
    quality = "Révélation"
    description = "Détecter et analyser une analogie structurelle entre deux domaines"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        domain_b = kwargs.get("domain_b", "")
        if not text:
            return self._fail("Pas de description du premier domaine")
        prompt = (
            f"Analyse l'analogie structurelle entre ces deux domaines. "
            f"Identifie: 1) éléments correspondants, 2) structure commune, "
            f"3) où l'analogie s'effondre, 4) niveau de preuve (E1-E6).\n\n"
            f"DOMAINE A: {text[:1500]}\n"
            f"DOMAINE B: {domain_b[:1500] if domain_b else '[non spécifié — identifier le domaine implicite]'}"
        )
        try:
            analysis = self._llm(prompt)
            return self._ok({"analysis": analysis}, "Analogie analysée")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class CheckSyllogism(Shem):
    """#42 MYK — Humilité : vérifier la validité logique."""
    name = "Check Syllogism"
    skill_id = "check_syllogism"
    trigram = "מיכ"
    trigram_name = "MYK"
    number = 42
    category = "reasoning"
    quality = "Humilité"
    description = "Vérifier la validité formelle d'un syllogisme"

    VALID_FORMS = {
        "AAA-1": ("Barbara", True), "EAE-1": ("Celarent", True),
        "AII-1": ("Darii", True), "EIO-1": ("Ferio", True),
        "AEE-2": ("Camestres", True), "EAE-2": ("Cesare", True),
        "EIO-2": ("Festino", True), "AOO-2": ("Baroco", True),
        "AII-3": ("Datisi", True), "IAI-3": ("Disamis", True),
        "EIO-3": ("Ferison", True), "OAO-3": ("Bocardo", True),
    }

    def run(self, text: str = "", **kwargs) -> ShemResult:
        major = kwargs.get("major", "")
        minor = kwargs.get("minor", "")
        conclusion = kwargs.get("conclusion", "")
        if not (major and minor and conclusion):
            if text:
                return self._ok(
                    {"note": "Fournir major=, minor=, conclusion= pour validation formelle",
                     "raw_text": text[:500]},
                    "Arguments non structurés — utiliser les kwargs",
                )
            return self._fail("Fournir major=, minor=, conclusion=")
        return self._ok(
            {"major": major, "minor": minor, "conclusion": conclusion,
             "valid_forms": list(self.VALID_FORMS.keys()),
             "note": "Validation formelle — vérifier la figure et le mode"},
            "Syllogisme structuré pour vérification",
        )


class GenerateCounterfactual(Shem):
    """#43 VVL — Élévation : générer un contrefactuel."""
    name = "Generate Counterfactual"
    skill_id = "generate_counterfactual"
    trigram = "וול"
    trigram_name = "VVL"
    number = 43
    category = "reasoning"
    quality = "Élévation"
    description = "Générer le contrefactuel d'un argument ou scénario"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas d'argument")
        prompt = (
            f"Génère le contrefactuel de cet argument/scénario. "
            f"Si [X] n'avait pas été le cas, que se serait-il passé ?\n\n{text[:2000]}"
        )
        try:
            cf = self._llm(prompt)
            return self._ok({"counterfactual": cf}, "Contrefactuel généré")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class DetectFallacy(Shem):
    """#44 YLH — Ascension : détecter les erreurs de raisonnement."""
    name = "Detect Fallacy"
    skill_id = "detect_fallacy"
    trigram = "ילה"
    trigram_name = "YLH"
    number = 44
    category = "reasoning"
    quality = "Ascension"
    description = "Détecter les sophismes et erreurs logiques dans un argument"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas d'argument")
        prompt = (
            f"Analyse cet argument pour détecter des sophismes/fallacies. "
            f"Liste courante: ad hominem, strawman, appeal to authority, "
            f"false dichotomy, slippery slope, circular reasoning, "
            f"equivocation, hasty generalization, post hoc, confirmation bias.\n\n"
            f"Argument: {text[:2500]}"
        )
        try:
            analysis = self._llm(prompt)
            return self._ok({"analysis": analysis}, "Analyse de fallacies")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class RateEvidenceLevel(Shem):
    """#45 SAL — Soutien : attribuer un niveau de preuve E1-E6."""
    name = "Rate Evidence Level"
    skill_id = "rate_evidence_level"
    trigram = "סאל"
    trigram_name = "SAL"
    number = 45
    category = "reasoning"
    quality = "Soutien"
    description = "Attribuer un niveau E1-E6 à un claim"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de claim à évaluer")
        prompt = (
            f"Évalue ce claim selon l'échelle:\n"
            f"E1: Fait empirique (paper peer-reviewed, données réplicables)\n"
            f"E2: Formalisation mathématique (définitions, théorèmes, preuves)\n"
            f"E3: Analogie structurelle documentée (parallèle avec structure commune)\n"
            f"E4: Hypothèse de travail (conjecture plausible, non testée)\n"
            f"E5: Métaphore heuristique (éclaire, ne prouve rien)\n"
            f"E6: Spéculation métaphysique (non falsifiable)\n\n"
            f"Claim: {text[:2000]}\n\nRéponds: E[N] — [justification en 2 phrases]"
        )
        try:
            rating = self._llm(prompt)
            return self._ok({"rating": rating}, "Niveau de preuve attribué")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class FindDivergence(Shem):
    """#46 ORI — Mélange : trouver où un mapping diverge."""
    name = "Find Divergence"
    skill_id = "find_divergence"
    trigram = "ערי"
    trigram_name = "ORI"
    number = 46
    category = "reasoning"
    quality = "Mélange"
    description = "Identifier où une analogie/mapping s'effondre"
    requires_llm = True
    olam = "briah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de mapping à analyser")
        prompt = (
            f"Ce mapping/analogie est présenté comme une convergence. "
            f"Cherche ACTIVEMENT les divergences :\n"
            f"1. Où l'analogie s'effondre-t-elle ?\n"
            f"2. Qu'est-ce que le concept A a que B n'a PAS ?\n"
            f"3. Qu'est-ce que B a que A n'a PAS ?\n"
            f"4. Y a-t-il cherry-picking ?\n\n{text[:3000]}"
        )
        try:
            analysis = self._llm(prompt)
            return self._ok({"divergences": analysis}, "Divergences identifiées")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class SteelmanArgument(Shem):
    """#47 OShL — Jeu : reformuler un argument dans sa version la plus forte."""
    name = "Steelman Argument"
    skill_id = "steelman_argument"
    trigram = "עשל"
    trigram_name = "OShL"
    number = 47
    category = "reasoning"
    quality = "Jeu"
    description = "Reformuler un argument dans sa version la plus forte (steelman)"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas d'argument")
        prompt = (
            f"Reformule cet argument dans sa version la plus forte possible (steelman). "
            f"Principe de charité maximale : interprète dans le meilleur sens, "
            f"corrige les faiblesses, renforce les prémisses.\n\nArgument: {text[:2500]}"
        )
        try:
            steelman = self._llm(prompt)
            return self._ok({"steelman": steelman}, "Argument renforcé (steelman)")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class DecomposeClaim(Shem):
    """#48 MYH — Source : décomposer un claim en sous-claims testables."""
    name = "Decompose Claim"
    skill_id = "decompose_claim"
    trigram = "מיה"
    trigram_name = "MYH"
    number = 48
    category = "reasoning"
    quality = "Source"
    description = "Décomposer un claim complexe en sous-claims testables"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de claim")
        prompt = (
            f"Décompose ce claim en sous-claims testables indépendamment. "
            f"Pour chaque sous-claim, indique comment il pourrait être testé/falsifié:\n\n"
            f"Claim: {text[:2000]}"
        )
        try:
            decomposition = self._llm(prompt)
            return self._ok({"decomposition": decomposition}, "Claim décomposé")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class IdentifyAssumptions(Shem):
    """#49 VHV2 — Renouveau : lister les présupposés implicites."""
    name = "Identify Assumptions"
    skill_id = "identify_assumptions"
    trigram = "והו"
    trigram_name = "VHV2"
    number = 49
    category = "reasoning"
    quality = "Renouveau"
    description = "Identifier les présupposés implicites d'un argument"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas d'argument")
        prompt = (
            f"Liste les présupposés implicites de cet argument — "
            f"ce qui est tenu pour acquis sans être démontré:\n\n{text[:2500]}"
        )
        try:
            assumptions = self._llm(prompt)
            return self._ok({"assumptions": assumptions}, "Présupposés identifiés")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class MapStructure(Shem):
    """#50 DNY — Jugement : mapper la structure formelle d'un concept."""
    name = "Map Structure"
    skill_id = "map_structure"
    trigram = "דני"
    trigram_name = "DNY"
    number = 50
    category = "reasoning"
    quality = "Jugement"
    description = "Mapper la structure formelle d'un concept (graphe, relations)"
    requires_llm = True
    olam = "briah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de concept")
        prompt = (
            f"Formalise la structure de ce concept :\n"
            f"1. Éléments constitutifs (nœuds)\n"
            f"2. Relations entre éléments (arêtes typées)\n"
            f"3. Propriétés structurelles (symétrie, transitivité, hiérarchie)\n"
            f"4. Type de structure mathématique (graphe, treillis, catégorie, groupe)\n\n"
            f"Concept: {text[:2500]}"
        )
        try:
            structure = self._llm(prompt)
            return self._ok({"structure": structure}, "Structure formelle mappée")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")
