"""AnalogyEngine — Génération d'analogies structurelles.

Détecte les isomorphismes de structure entre domaines :
- Hiérarchies parallèles
- Cycles homologues
- Flux bidirectionnels
- Relations partie/tout

"Ce qui est en haut est comme ce qui est en bas."
"""

from __future__ import annotations

import re

from explorationengine.models import Connection


# Base de connaissances de patterns structurels par domaine
# Chaque domaine a des concepts-clés et des structures
DOMAIN_PATTERNS: dict[str, dict] = {
    "neuroscience": {
        "concepts": ["neuron", "synapse", "cortex", "hippocampus", "attention",
                      "memory", "plasticity", "network", "firing", "inhibition"],
        "structures": ["hierarchy", "network", "cycle", "flow"],
        "description": "brain architecture, neural networks, synaptic plasticity",
    },
    "machine_learning": {
        "concepts": ["model", "training", "loss", "gradient", "attention",
                      "layer", "transformer", "embedding", "weight", "optimization"],
        "structures": ["hierarchy", "flow", "cycle"],
        "description": "deep learning architectures, training loops, optimization",
    },
    "kabbale": {
        "concepts": ["sefirot", "tsimtsum", "tikkun", "shevirah", "partzuf",
                      "olamot", "klipot", "nitzotzot", "kav", "reshimu"],
        "structures": ["hierarchy", "cycle", "flow"],
        "description": "tree of life, emanation, contraction, repair",
    },
    "soufisme": {
        "concepts": ["tajalli", "barzakh", "fana", "baqa", "kashf",
                      "maqam", "hal", "dhikr", "insan", "wahdat"],
        "structures": ["hierarchy", "cycle"],
        "description": "divine manifestation, stations, states, unity of being",
    },
    "biology": {
        "concepts": ["cell", "organism", "evolution", "gene", "protein",
                      "metabolism", "homeostasis", "adaptation", "selection", "mutation"],
        "structures": ["hierarchy", "cycle", "network"],
        "description": "living systems, evolution, cellular processes",
    },
    "physics": {
        "concepts": ["energy", "entropy", "field", "symmetry", "conservation",
                      "quantum", "wave", "particle", "force", "equilibrium"],
        "structures": ["flow", "cycle"],
        "description": "fundamental forces, conservation laws, symmetry",
    },
    "writing": {
        "concepts": ["narrative", "structure", "voice", "rhythm", "clarity",
                      "argument", "thesis", "revision", "editing", "style"],
        "structures": ["hierarchy", "flow"],
        "description": "text quality, narrative structure, argumentation",
    },
    "code": {
        "concepts": ["function", "module", "abstraction", "recursion", "pattern",
                      "interface", "refactoring", "testing", "architecture", "complexity"],
        "structures": ["hierarchy", "flow", "network"],
        "description": "software architecture, design patterns, code quality",
    },
    "auto_improve": {
        "concepts": ["exploration", "hypothesis", "evaluation", "novelty", "improvement",
                      "insight", "connection", "learning", "feedback", "iteration"],
        "structures": ["cycle", "flow"],
        "description": "autonomous self-improvement loop, hypothesis generation and evaluation",
    },
    "hitbonenut": {
        "concepts": ["contemplation", "question", "answer", "domain", "competence",
                      "depth", "understanding", "self-assessment", "mastery", "practice"],
        "structures": ["cycle", "hierarchy"],
        "description": "contemplative self-study, question-answer loops, domain mastery",
    },
    "failure_analysis": {
        "concepts": ["failure", "insight", "pattern", "cause", "remedy",
                      "nitzotzot", "spark", "rejection", "learning", "guidance"],
        "structures": ["flow", "cycle"],
        "description": "extracting insights from failures, sparks from broken vessels",
    },
    "gematria": {
        "concepts": ["value", "equivalence", "root", "letter", "word",
                      "number", "permutation", "combination", "cipher", "structure"],
        "structures": ["network"],
        "description": "numerical values of Hebrew letters, structural equivalences",
    },
    "tzimtzum": {
        "concepts": ["contraction", "expansion", "focus", "reshimu", "kav",
                      "void", "concealment", "revelation", "bottleneck", "compression"],
        "structures": ["cycle", "flow"],
        "description": "contraction-expansion dynamics, information bottleneck",
    },
    "sefirot": {
        "concepts": ["emanation", "attribute", "balance", "channel", "vessel",
                      "light", "chesed", "gevurah", "tiferet", "tree"],
        "structures": ["hierarchy", "network", "flow"],
        "description": "divine attributes as computational nodes, tree architecture",
    },
    "partzufim": {
        "concepts": ["configuration", "face", "persona", "interaction", "zivug",
                      "coupling", "masculine", "feminine", "integration", "maturation"],
        "structures": ["network", "hierarchy"],
        "description": "complex configurations of sefirot, interaction patterns",
    },
}


def _word_set(text: str) -> set[str]:
    return {w for w in re.findall(r'\b[a-zA-ZÀ-ÿ]{3,}\b', text.lower())}


class AnalogyEngine:
    """Génération d'analogies structurelles entre domaines.

    Niveau 1 : Concepts partagés (même mot, domaines différents)
    Niveau 2 : Structures homologues (même pattern, domaines différents)
    Niveau 3 : Relations fonctionnelles (même rôle, domaines différents)
    """

    def __init__(self, extra_domains: dict[str, dict] | None = None):
        """
        extra_domains : dict de domaines supplémentaires au même format
                        que DOMAIN_PATTERNS.
        """
        self.domains = dict(DOMAIN_PATTERNS)
        if extra_domains:
            self.domains.update(extra_domains)

    def find_analogies(
        self,
        concept: str,
        source_domain: str,
        target_domains: list[str] | None = None,
    ) -> list[Connection]:
        """Trouver des analogies structurelles pour un concept.

        Args:
            concept: le concept source
            source_domain: le domaine du concept
            target_domains: domaines cibles (tous si None)

        Returns:
            Liste de connexions de type 'analogy'.
        """
        targets = target_domains or [d for d in self.domains if d != source_domain]
        analogies: list[Connection] = []
        concept_words = _word_set(concept)

        source_info = self.domains.get(source_domain, {})
        source_concepts = set(source_info.get("concepts", []))
        source_structures = set(source_info.get("structures", []))

        for target in targets:
            if target == source_domain:
                continue

            target_info = self.domains.get(target, {})
            if not target_info:
                continue

            target_concepts = set(target_info.get("concepts", []))
            target_structures = set(target_info.get("structures", []))

            # Niveau 1 : Concept partagé
            concept_overlap = concept_words & target_concepts
            if concept_overlap:
                for shared in concept_overlap:
                    analogies.append(Connection(
                        concept_a=concept,
                        domain_a=source_domain,
                        concept_b=shared,
                        domain_b=target,
                        connection_type="analogy",
                        description=(
                            f"'{shared}' exists in both {source_domain} and {target}. "
                            f"In {source_domain}: part of '{concept}'. "
                            f"In {target}: {target_info.get('description', '')}."
                        ),
                        confidence=0.6,
                    ))

            # Niveau 2 : Structure homologue
            shared_structures = source_structures & target_structures
            if shared_structures:
                for struct in shared_structures:
                    analogies.append(Connection(
                        concept_a=f"{struct} structure ({source_domain})",
                        domain_a=source_domain,
                        concept_b=f"{struct} structure ({target})",
                        domain_b=target,
                        connection_type="analogy",
                        description=(
                            f"Both {source_domain} and {target} exhibit {struct} structures. "
                            f"The {struct} in {source_domain} may be functionally analogous "
                            f"to the {struct} in {target}."
                        ),
                        confidence=0.45,
                    ))

            # Niveau 3 : Relation fonctionnelle
            # Chercher si le concept joue un rôle structurel connu
            source_concept_overlap = concept_words & source_concepts
            if source_concept_overlap and target_concepts:
                # Le concept a un rôle connu dans le domaine source
                # Chercher un concept avec un rôle similaire dans le domaine cible
                # Heuristique : même position dans la liste → même rôle
                for sc in source_concept_overlap:
                    src_list = source_info.get("concepts", [])
                    if sc in src_list:
                        idx = src_list.index(sc)
                        tgt_list = target_info.get("concepts", [])
                        if idx < len(tgt_list):
                            target_concept = tgt_list[idx]
                            analogies.append(Connection(
                                concept_a=sc,
                                domain_a=source_domain,
                                concept_b=target_concept,
                                domain_b=target,
                                connection_type="analogy",
                                description=(
                                    f"'{sc}' in {source_domain} may play a role analogous to "
                                    f"'{target_concept}' in {target}. "
                                    f"Both occupy similar functional positions in their domains."
                                ),
                                confidence=0.3,
                            ))

        return analogies

    def detect_cross_domain_analogies(
        self,
        connections: list[Connection],
    ) -> list[dict]:
        """Détecter les patterns récurrents dans les connexions existantes.

        Analyse les connexions pour trouver :
        - Paires de domaines avec plusieurs connexions similaires
        - Patterns structurels partagés entre domaines
        - Concepts qui apparaissent dans 3+ domaines différents

        Returns:
            Liste de dicts {domain_a, domain_b, pattern, explanation, strength,
                           source_ids}
        """
        if len(connections) < 2:
            return []

        analogies: list[dict] = []

        # 1. Grouper par paire de domaines
        domain_pairs: dict[tuple[str, str], list[Connection]] = {}
        for c in connections:
            pair = tuple(sorted([c.domain_a, c.domain_b]))
            domain_pairs.setdefault(pair, []).append(c)

        # 2. Chercher des patterns récurrents dans chaque paire
        for (da, db), conns in domain_pairs.items():
            if len(conns) < 2:
                continue

            # Extraire les mots récurrents dans les descriptions
            from collections import Counter
            all_words: list[str] = []
            for c in conns:
                all_words.extend(_word_set(c.description))
            word_counts = Counter(all_words)
            recurring = [w for w, cnt in word_counts.most_common(10) if cnt >= 2]

            if recurring:
                pattern = f"shared_vocabulary: {', '.join(recurring[:5])}"
                strength = min(len(recurring) / 10, 0.8)
                source_ids = [c.id for c in conns if c.id]

                analogies.append({
                    "domain_a": da,
                    "domain_b": db,
                    "pattern": pattern,
                    "explanation": (
                        f"Recurring concepts between {da} and {db}: "
                        f"{', '.join(recurring[:5])}. "
                        f"Found in {len(conns)} connections."
                    ),
                    "strength": strength,
                    "source_ids": source_ids,
                })

        # 3. Concepts qui traversent 3+ domaines
        concept_domains: dict[str, set[str]] = {}
        for c in connections:
            for word in _word_set(c.concept_a) | _word_set(c.concept_b):
                concept_domains.setdefault(word, set()).update(
                    {c.domain_a, c.domain_b}
                )

        for concept, domains in concept_domains.items():
            if len(domains) >= 3:
                domain_list = sorted(domains)
                for i in range(len(domain_list)):
                    for j in range(i + 1, len(domain_list)):
                        pattern = f"cross_domain_concept: {concept}"
                        analogies.append({
                            "domain_a": domain_list[i],
                            "domain_b": domain_list[j],
                            "pattern": pattern,
                            "explanation": (
                                f"'{concept}' appears across {len(domains)} domains "
                                f"({', '.join(domain_list)}), suggesting a "
                                f"structural invariant."
                            ),
                            "strength": min(len(domains) / 8, 0.7),
                            "source_ids": [],
                        })

        return analogies

    def get_known_domains(self) -> list[str]:
        """Retourner la liste des domaines connus."""
        return sorted(self.domains.keys())

    def get_domain_info(self, domain: str) -> dict:
        """Retourner les infos d'un domaine."""
        return self.domains.get(domain, {})
