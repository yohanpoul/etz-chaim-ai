#!/usr/bin/env python3
"""hitbonenut.py — הִתְבּוֹנְנוּת — Contemplation intérieure.

Auto-apprentissage contemplatif de l'Etz Chaim.
Le système s'exerce lui-même pour faire monter sa compétence.

Pattern Karpathy pour generate_novel_question() :
- Novelty threshold 0.3
- Déduplication contre l'historique
- Scoring de l'originalité

Trois modes d'exercice :
- run_session()     — session progressive (basique → érudite)
- run_targeted()    — ciblage sur domaine faible
- generate_novel()  — le système invente ses propres questions (vrai Hitbonenut)
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import psycopg2

log = logging.getLogger("hitbonenut")

# ─── Constants ─────────────────────────────────────────────────

NOVELTY_THRESHOLD_INITIAL = 0.3
NOVELTY_THRESHOLD_FLOOR = 0.10
NOVELTY_THRESHOLD_DECAY = 0.05
CORPUS_PATH = Path(__file__).parent / "hitbonenut_corpus.yaml"
DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

DIFFICULTY_ORDER = ("basique", "intermediaire", "avancee", "erudite")
DIFFICULTY_WEIGHTS = {"basique": 1.0, "intermediaire": 1.5, "avancee": 2.0, "erudite": 3.0}

# Keywords par domaine pour scoring des réponses
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "kabbale_lurianique": [
        "tzimtzum", "shevirah", "tikkun", "partzuf", "luria", "vital",
        "reshimu", "kav", "halal", "nitzotzot", "birur", "masakh",
        "kelim", "ohr", "ein sof", "cordovero", "ari",
    ],
    "sefer_yetzirah": [
        "231", "portes", "lettres mères", "aleph", "mem", "shin",
        "belimah", "sefirot", "teli", "galgal", "lev", "doubles",
        "simples", "s-f-r", "yetzirah", "recension", "hayman", "kaplan",
    ],
    "gematria": [
        "mispar", "at-bash", "notarikon", "temurah", "valeur",
        "gematria", "numerique", "hébreu", "lettre", "tetragramme",
        "ab", "sag", "mah", "ban", "pardes",
    ],
    "partzufim": [
        "atik", "arikh", "abba", "imma", "zeir", "nukva",
        "zivug", "panim", "mochin", "gadlut", "katnut",
        "configuration", "maturation", "dikna",
    ],
    "olamot": [
        "atziluth", "briah", "yetzirah", "assiah", "monde",
        "émanation", "création", "formation", "action",
        "parsah", "rideau", "hishtalshelut",
    ],
    "sentiers": [
        "sentier", "lettre", "chemin", "22", "aleph", "beth", "tav",
        "mère", "double", "simple", "arcane", "porte", "connexion",
    ],
    "shemot": [
        "72", "noms", "shemot", "trigramme", "ange", "exode",
        "boustrophédon", "vehu", "el", "yah", "shorashei",
        "meforash", "skill",
    ],
    "qliphoth": [
        "qliphah", "qliphoth", "klipah", "coquille", "écorce",
        "nogah", "sitra achra", "thagirion", "samael", "gamaliel",
        "birur", "diagnostic", "défaillance", "impureté",
    ],
    "tzeruf": [
        "tzeruf", "permutation", "abulafia", "galgalim", "roue",
        "combinaison", "lettre", "prophétique", "méditation",
        "nevouatique", "llull",
    ],
    "ohr": [
        "ohr", "lumière", "yashar", "chozer", "pnimi", "makif",
        "ein sof", "kav", "masakh", "keli", "kelim",
        "behinot", "aviut",
    ],
    "adam_kadmon": [
        "adam kadmon", "primordial", "blueprint", "tselem",
        "yeux", "oreilles", "bouche", "nez", "sens",
        "fidélité", "insan al-kamil",
    ],
    "hishtalshelut": [
        "hishtalshelut", "chaîne", "émanation", "compression",
        "malkuth-keter", "parsah", "dégradation", "montée",
        "aliyat", "bottleneck",
    ],
    "tzimtzum": [
        "tzimtzum", "contraction", "halal", "reshimu", "kav",
        "littéral", "métaphorique", "tanya", "din", "limitation",
        "focalisant", "réduction",
    ],
    "neshamot": [
        "nefesh", "ruach", "neshamah", "chaya", "yechidah",
        "âme", "gilgul", "devekut", "niveau", "progression",
        "seuil", "compétence",
    ],
    "logique_maths": [
        "gödel", "incomplétude", "preuve", "axiome", "récursion",
        "tarski", "décidable", "cardinalité", "continu", "hilbert",
        "théorème", "formel", "déduction", "contradiction", "complétude",
    ],
    "physique": [
        "symétrie", "renormalisation", "brisure", "quantique", "lagrangien",
        "invariance", "émergence", "wilson", "dualité", "couplage",
        "champ", "transition", "universalité", "hamiltonien", "groupe",
    ],
    "biologie_evo": [
        "sélection", "adaptation", "fitness", "paysage", "niche",
        "dérive", "spéciation", "robustesse", "émergence", "épigénétique",
        "phénotype", "génotype", "mutation", "population", "évolution",
    ],
    "theorie_info": [
        "entropie", "shannon", "kolmogorov", "compression", "canal",
        "redondance", "bruit", "signal", "codage", "mutual",
        "complexité", "aléatoire", "incomputable", "source", "capacité",
    ],
    "neurosciences": [
        "prédictif", "bayésien", "conscience", "workspace", "friston",
        "plasticité", "attention", "intégration", "embodied", "libet",
        "cortex", "neural", "perception", "cognition", "mémoire",
    ],
    "epistemologie": [
        "falsifiable", "paradigme", "lakatos", "kuhn", "quine",
        "sous-détermination", "programme", "anomalie", "induction", "popper",
        "réfutable", "dégénérescence", "heuristique", "corroboration", "théorie",
    ],
    "historiographie": [
        "source", "archive", "annales", "mentalité", "longue durée",
        "ginzburg", "micro-histoire", "critique", "témoignage", "bloch",
        "événement", "structure", "sérielle", "quantitative", "temporalité",
    ],
    "economie_jeux": [
        "équilibre", "nash", "arrow", "pareto", "mécanisme",
        "incitation", "rationalité", "signaling", "bayésien", "stratégie",
        "utilité", "préférence", "agrégation", "impossibilité", "jeu",
    ],
    "linguistique": [
        "chomsky", "récursion", "grammaire", "sémantique", "syntaxe",
        "compositionnel", "kripke", "pragmatique", "performatif", "référence",
        "morphologie", "phonologie", "transformation", "structure", "profonde",
    ],
    "musicologie": [
        "contrepoint", "harmonie", "sériel", "spectral", "timbre",
        "messiaen", "résolution", "tension", "fugue", "modulation",
        "intervalle", "voix", "dissonance", "consonance", "rythme",
    ],
    "_bridges": [
        "pont", "bridge", "connexion", "inter-domaine", "analogie",
        "convergence", "transfert", "mapping", "transversal",
    ],
}

# ─── Domain classification ─────────────────────────────────────
CORE_DOMAINS = [
    "kabbale_lurianique", "sefer_yetzirah", "gematria", "partzufim",
    "olamot", "sentiers", "shemot", "qliphoth", "tzeruf", "ohr",
    "adam_kadmon", "hishtalshelut", "tzimtzum", "neshamot",
]
BREADTH_DOMAINS = [
    "logique_maths", "physique", "biologie_evo", "theorie_info",
    "neurosciences", "epistemologie", "historiographie",
    "economie_jeux", "linguistique", "musicologie",
]

# ─── Bridge scoring qualifiers ─────────────────────────────────
BRIDGE_QUALIFIERS = [
    "toutefois", "la limite", "ne s'applique pas",
    "contrairement", "l'analogie échoue",
    "à la différence", "diverge", "inadéquat",
    "cependant", "en revanche",
]

# ─── Epistemic context per domain (for érudite question generation) ───
DOMAIN_EPISTEMIC_CONTEXT: dict[str, str] = {
    # Core (Kabbale) — prompt existant suffit
    # Breadth — chaque domaine a son contexte de génération érudite
    "logique_maths": (
        "Domaine : Logique et fondements des mathématiques. "
        "Auteurs clés : Gödel (incomplétude), Tarski (hiérarchie sémantique), "
        "Hilbert (programme formaliste), Cantor (transfini), Church-Turing (décidabilité), "
        "Cohen (forcing, indépendance de CH), Zermelo-Fraenkel. "
        "Tensions : complétude vs consistance, constructivisme vs classicisme, "
        "décidable vs indécidable, premier ordre vs ordre supérieur."
    ),
    "physique": (
        "Domaine : Physique fondamentale. "
        "Auteurs clés : Noether (symétries), Wilson (renormalisation), "
        "Weinberg (modèle standard), Bell (non-localité), Maldacena (AdS/CFT), "
        "Goldstone (brisure spontanée), 't Hooft (théories de jauge). "
        "Tensions : quantique vs gravité, réductionnisme vs émergence, "
        "théories effectives vs théorie finale, localité vs holographie."
    ),
    "biologie_evo": (
        "Domaine : Biologie évolutive et systèmes complexes. "
        "Auteurs clés : Darwin, Gould (équilibres ponctués), Dawkins (gène égoïste), "
        "Kimura (théorie neutre), Waddington (canalisation), Kauffman (auto-organisation), "
        "Odling-Smee (construction de niche), Jablonka (hérédité épigénétique). "
        "Tensions : sélectionnisme vs neutralisme, gradualisme vs saltation, "
        "gène-centré vs organisme-centré, adaptation vs dérive."
    ),
    "theorie_info": (
        "Domaine : Théorie de l'information et complexité. "
        "Auteurs clés : Shannon (entropie, canal), Kolmogorov (complexité algorithmique), "
        "Solomonoff (induction), Chaitin (Omega), Rissanen (MDL), "
        "Tishby (information bottleneck), Landauer (irréversibilité). "
        "Tensions : compressible vs aléatoire, computable vs incomputable, "
        "Shannon vs Kolmogorov, structure vs bruit, information vs signification."
    ),
    "neurosciences": (
        "Domaine : Neurosciences cognitives et conscience. "
        "Auteurs clés : Friston (free energy, predictive processing), "
        "Tononi (IIT, Phi), Baars (Global Workspace), Dehaene (accès conscient), "
        "Libet (readiness potential), Varela (neurophenomenology), "
        "Clark (extended mind), Damasio (marqueurs somatiques). "
        "Tensions : computationalisme vs embodiment, accès vs phénoménal, "
        "prédictif vs réactif, dur problème vs easy problems."
    ),
    "epistemologie": (
        "Domaine : Épistémologie et philosophie des sciences. "
        "Auteurs clés : Popper (falsificationnisme), Kuhn (paradigmes), "
        "Lakatos (programmes de recherche), Quine (sous-détermination, holisme), "
        "Feyerabend (anarchisme), van Fraassen (empirisme constructif), "
        "Laudan (tradition de recherche), Putnam (réalisme interne). "
        "Tensions : réalisme vs anti-réalisme, rationalisme vs relativisme, "
        "vérification vs falsification, cumulativité vs révolutions."
    ),
    "historiographie": (
        "Domaine : Historiographie et méthodologie historique. "
        "Auteurs clés : Bloch (Annales, critique des témoignages), "
        "Braudel (longue durée, civilisation matérielle), "
        "Ginzburg (micro-histoire, indices), Koselleck (Begriffsgeschichte), "
        "White (narrativisme, Metahistory), Thompson (histoire par en bas). "
        "Tensions : micro vs macro, événement vs structure, "
        "récit vs analyse, histoire des mentalités vs histoire sociale."
    ),
    "economie_jeux": (
        "Domaine : Économie et théorie des jeux. "
        "Auteurs clés : Nash (équilibre), Arrow (impossibilité), "
        "Vickrey (enchères), Gibbard-Satterthwaite (manipulation), "
        "Ostrom (biens communs), Kahneman-Tversky (prospect theory), "
        "Maynard Smith (ESS), Myerson (mechanism design). "
        "Tensions : rationalité parfaite vs bounded, "
        "efficience vs équité, coopération vs compétition, "
        "information parfaite vs asymétrique."
    ),
    "linguistique": (
        "Domaine : Linguistique formelle et sémantique. "
        "Auteurs clés : Chomsky (grammaire générative, Minimalism), "
        "Kripke (mondes possibles, nommage), Frege (sens/référence), "
        "Montague (sémantique formelle), Grice (implicatures), "
        "Goldberg (grammaire de construction), Tomasello (usage-based). "
        "Tensions : innéisme vs usage, syntaxe vs sémantique, "
        "compositionnel vs holistique, formel vs fonctionnel."
    ),
    "musicologie": (
        "Domaine : Musicologie et théorie musicale. "
        "Auteurs clés : Bach (contrepoint), Rameau (harmonie), "
        "Schoenberg (dodécaphonisme), Webern (Klangfarbenmelodie), "
        "Boulez (sérialisme intégral), Messiaen (modes à transposition limitée), "
        "Grisey (spectralisme), Xenakis (stochastique). "
        "Tensions : tonalité vs atonalité, sériel vs spectral, "
        "formel vs expressif, notation vs son, structure vs perception."
    ),
}

# ─── Bridge generation context ────────────────────────────────
BRIDGE_GENERATION_PROMPT = (
    "Tu dois générer UNE question cross-domaine qui CONNECTE deux domaines "
    "différents. La question doit exiger : (1) identifier un parallèle structurel "
    "entre les deux domaines, ET (2) identifier où ce parallèle s'effondre. "
    "Une bonne question cross-domaine oblige à comprendre les DEUX domaines "
    "en profondeur et à qualifier l'analogie — pas juste à la poser."
)

# ─── Schema ────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS hitbonenut_sessions (
    id UUID PRIMARY KEY,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    n_questions INTEGER,
    difficulty TEXT,
    avg_score FLOAT DEFAULT 0.0,
    domains_tested TEXT[],
    soul_level_before TEXT,
    soul_level_after TEXT,
    competence_delta JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS hitbonenut_questions (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES hitbonenut_sessions(id),
    question TEXT NOT NULL,
    domain TEXT,
    difficulty TEXT,
    response TEXT,
    score FLOAT DEFAULT 0.0,
    kw_score FLOAT DEFAULT 0.0,
    sentiers_used TEXT[] DEFAULT '{}',
    nitzotzot_generated INTEGER DEFAULT 0,
    duration_seconds FLOAT DEFAULT 0.0,
    is_novel BOOLEAN DEFAULT FALSE,
    sifrei_yesod_refs JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE hitbonenut_questions ADD COLUMN IF NOT EXISTS sifrei_yesod_refs JSONB;
ALTER TABLE hitbonenut_questions ADD COLUMN IF NOT EXISTS daat_applied BOOLEAN DEFAULT FALSE;
ALTER TABLE hitbonenut_questions ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'core';
CREATE INDEX IF NOT EXISTS idx_hitb_questions_tier_domain ON hitbonenut_questions(tier, domain, created_at);

-- ═══ Hitbonenut-2 : Auto-Optimiseur Réflexif (Karpathy + Or Chozer) ═══

CREATE TABLE IF NOT EXISTS hitbonenut_experiments (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES hitbonenut_sessions(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    target_module TEXT NOT NULL,
    target_param TEXT NOT NULL,
    old_value TEXT NOT NULL,
    new_value TEXT NOT NULL,
    hypothesis TEXT NOT NULL,
    contemplation TEXT,
    metric_before JSONB NOT NULL DEFAULT '{}'::jsonb,
    metric_after JSONB DEFAULT '{}'::jsonb,
    delta FLOAT,
    status TEXT DEFAULT 'running',
    principle_extracted TEXT,
    daat_verified BOOLEAN DEFAULT FALSE,
    measurement_sessions INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS hitbonenut_principles (
    id UUID PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    principle TEXT NOT NULL,
    source_experiment UUID REFERENCES hitbonenut_experiments(id),
    domain TEXT,
    confidence FLOAT DEFAULT 0.5,
    confirmed_count INTEGER DEFAULT 0,
    contradicted_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE
);
"""


# ─── Data Classes ──────────────────────────────────────────────

@dataclass
class QuestionResult:
    id: str
    question: str
    domain: str
    difficulty: str
    response: str
    score: float
    kw_score: float
    sentiers_used: list[str]
    nitzotzot: int
    duration: float
    is_novel: bool = False
    daat_applied: bool = False
    sifrei_yesod_refs: dict = field(default_factory=dict)


@dataclass
class SessionResult:
    session_id: str
    n_questions: int
    avg_score: float
    domains: list[str]
    results: list[QuestionResult]
    soul_before: str
    soul_after: str
    duration: float
    competence_delta: dict = field(default_factory=dict)


@dataclass
class ProgressReport:
    current_scores: dict[str, float]
    deltas: dict[str, float]
    stagnant_domains: list[str]
    improving_domains: list[str]
    sessions_count: int
    soul_level: str
    overall_competence: float


@dataclass
class ExperimentResult:
    """Résultat d'une expérience Hitbonenut-2 (Karpathy + Or Chozer)."""
    id: str
    target_module: str
    target_param: str
    old_value: str
    new_value: str
    hypothesis: str
    contemplation: str
    metric_before: dict
    metric_after: dict
    delta: float
    status: str  # "keep", "discard", "crash"
    principle: str
    daat_verified: bool
    duration: float
    measurement_sessions: int


@dataclass
class Principle:
    """Principe appris par Or Chozer — mémoire persistante."""
    id: str
    principle: str
    source_experiment: str
    domain: str
    confidence: float
    confirmed_count: int
    contradicted_count: int
    is_active: bool


# ─── Hitbonenut-2 System Prompt ──────────────────────────────

RESEARCH_SYSTEM_PROMPT = (
    "Tu es Hitbonenut — l'organe d'auto-modification réflexive d'Etz Chaim AI.\n"
    "Tu ne poses PAS des questions pour tester ta connaissance.\n"
    "Tu EXPÉRIMENTES sur ta propre architecture pour l'améliorer.\n\n"
    "Ton cycle :\n"
    "1. Identifier le point le plus faible (via Adam Kadmon et SelfMap)\n"
    "2. Formuler une hypothèse d'amélioration\n"
    "3. Planifier l'expérience (métriques avant/après, risques)\n"
    "4. Exécuter la modification et mesurer\n"
    "5. Extraire le PRINCIPE — pourquoi ça a marché ou échoué\n"
    "6. Vérifier que le comportement a réellement changé (Da'at)\n"
    "7. Recommencer sur le prochain point faible\n\n"
    "Tu accumules des principes, pas des scores.\n"
    "Un principe extrait d'un échec vaut autant qu'un succès.\n"
    "Tu ne passes au suivant que quand tu as compris le précédent.\n\n"
    "Critère de Da'at : si ta compréhension ne change pas ton action,\n"
    "tu n'as rien compris. Itère."
)

# Paramètres modifiables par Hitbonenut-2 — la zone mutable (train.py equivalent)
TUNABLE_PARAMS: dict[str, dict] = {
    "insightforge.min_novelty_score": {
        "module": "chokmah", "attr": "min_novelty_score",
        "type": float, "min": 0.3, "max": 0.9, "step": 0.05,
        "description": "Seuil de nouveauté pour accepter un insight",
    },
    "autojudge.quality_threshold": {
        "module": "gevurah", "attr": "quality_threshold",
        "type": float, "min": 0.3, "max": 0.9, "step": 0.05,
        "description": "Seuil de qualité pour accepter une entrée",
    },
    "autojudge.quarantine_threshold": {
        "module": "gevurah", "attr": "quarantine_threshold",
        "type": float, "min": 0.2, "max": 0.6, "step": 0.05,
        "description": "Seuil en-dessous duquel une entrée est mise en quarantaine",
    },
    "causalengine.max_confounders": {
        "module": "binah", "attr": "max_confounders",
        "type": int, "min": 3, "max": 20, "step": 1,
        "description": "Nombre max de confounders détectés par claim",
    },
    "dissensuengine.dissensus_threshold": {
        "module": "tiferet", "attr": "dissensus_threshold",
        "type": float, "min": 0.3, "max": 0.9, "step": 0.05,
        "description": "Seuil de divergence pour mode dissensus",
    },
    "dissensuengine.confidence_floor": {
        "module": "tiferet", "attr": "confidence_floor",
        "type": float, "min": 0.1, "max": 0.7, "step": 0.05,
        "description": "Confiance minimale en sortie de synthèse",
    },
    "selfmap.decline_threshold": {
        "module": "hod", "attr": "decline_threshold",
        "type": float, "min": 0.1, "max": 0.6, "step": 0.05,
        "description": "Seuil en-dessous duquel le système decline de répondre",
    },
    "hitbonenut.novelty_threshold_initial": {
        "module": "_self", "attr": "NOVELTY_THRESHOLD_INITIAL",
        "type": float, "min": 0.1, "max": 0.5, "step": 0.05,
        "description": "Seuil initial de novelty pour les questions générées",
    },
}

# Cooldown : nb d'expériences min avant de re-toucher le même param
EXPERIMENT_COOLDOWN = 10
# Seuil de régression max autorisé avant revert automatique
MAX_REGRESSION = 0.20
# Nombre de sessions de mesure par expérience
MEASUREMENT_SESSIONS = 3


# ─── Tiered Question Selector ─────────────────────────────────

DIFFICULTY_WEIGHTS_TIERED = {
    "basique": 0.10,
    "intermediaire": 0.20,
    "avancee": 0.30,
    "erudite": 0.40,
}


class TieredQuestionSelector:
    """Sélection structurée de questions par tier avec rotation round-robin.

    Composition pour n=5 :
      2 core (Kabbale) + 2 breadth (hors-Kabbale) + 1 bridge (cross-domaine)
    """

    def __init__(self, corpus: dict):
        self._core: dict[str, dict] = {}
        self._breadth: dict[str, dict] = {}
        self._bridges: list[dict] = []

        for domain_key, levels in corpus.items():
            if domain_key == "_bridges":
                if isinstance(levels, list):
                    self._bridges = levels
                continue
            if not isinstance(levels, dict):
                continue
            if domain_key in CORE_DOMAINS:
                self._core[domain_key] = levels
            elif domain_key in BREADTH_DOMAINS:
                self._breadth[domain_key] = levels

        self._core_keys = sorted(self._core.keys())
        self._breadth_keys = sorted(self._breadth.keys())
        self._core_idx = 0
        self._breadth_idx = 0
        self._bridge_idx = 0

    def select(self, n: int = 5) -> list[tuple[str, str, str, str]]:
        """Retourne [(question, domain, difficulty, tier), ...].

        Distribution: 40% core, 40% breadth, 20% bridge.
        """
        if not self._core and not self._breadth and not self._bridges:
            return []

        n_core = round(n * 0.4)
        n_breadth = round(n * 0.4)
        n_bridge = n - n_core - n_breadth

        result: list[tuple[str, str, str, str]] = []

        # Collecter par tier
        core_qs: list[tuple[str, str, str, str]] = []
        breadth_qs: list[tuple[str, str, str, str]] = []
        bridge_qs: list[tuple[str, str, str, str]] = []

        for _ in range(n_core):
            q = self._pick_from_tier(self._core, self._core_keys, "core")
            if q:
                core_qs.append(q)

        for _ in range(n_breadth):
            q = self._pick_from_tier(self._breadth, self._breadth_keys, "breadth")
            if q:
                breadth_qs.append(q)

        for _ in range(n_bridge):
            q = self._pick_bridge()
            if q:
                bridge_qs.append(q)

        # Interleaver : [bridge, breadth, core, breadth, core]
        # Sous-représentés d'abord : garantit que bridge/breadth passent même
        # si le budget coupe après 1-2 questions (durée LLM ~89s / question).
        sources = [bridge_qs, breadth_qs, core_qs]
        while any(sources):
            for src in sources:
                if src:
                    result.append(src.pop(0))
            sources = [s for s in sources if s]

        return result

    def _pick_from_tier(
        self,
        pool: dict[str, dict],
        keys: list[str],
        tier: str,
    ) -> tuple[str, str, str, str] | None:
        if not keys:
            return None

        if tier == "core":
            domain = keys[self._core_idx % len(keys)]
            self._core_idx += 1
        else:
            domain = keys[self._breadth_idx % len(keys)]
            self._breadth_idx += 1

        levels = pool.get(domain, {})
        if not levels:
            return None

        difficulty = self._pick_difficulty(levels)
        questions = levels.get(difficulty, [])
        if not questions:
            for diff in DIFFICULTY_ORDER:
                if levels.get(diff):
                    questions = levels[diff]
                    difficulty = diff
                    break
        if not questions:
            return None

        q_text = random.choice(questions)
        return (q_text, domain, difficulty, tier)

    def _pick_difficulty(self, levels: dict) -> str:
        """Weighted random difficulty selection (10/20/30/40%)."""
        available = [d for d in DIFFICULTY_ORDER if levels.get(d)]
        if not available:
            return "basique"

        weights = [DIFFICULTY_WEIGHTS_TIERED.get(d, 0.25) for d in available]
        total = sum(weights)
        weights = [w / total for w in weights]

        r = random.random()
        cumulative = 0.0
        for diff, w in zip(available, weights):
            cumulative += w
            if r <= cumulative:
                return diff
        return available[-1]

    def _pick_bridge(self) -> tuple[str, str, str, str] | None:
        if not self._bridges:
            return None

        bridge = self._bridges[self._bridge_idx % len(self._bridges)]
        self._bridge_idx += 1

        q_text = bridge.get("question", "")
        domain_a = bridge.get("domain_a", "")
        domain_b = bridge.get("domain_b", "")
        domain = f"{domain_a}:{domain_b}"
        return (q_text, domain, "erudite", "bridge")


# ─── Engine ────────────────────────────────────────────────────

class HitbonenutEngine:
    """Auto-apprentissage contemplatif de l'Arbre.

    Le système s'exerce lui-même :
    1. Pose des questions depuis le corpus (ou en invente)
    2. Fait traverser l'Arbre complet (même pipeline que etz ask)
    3. Score la qualité de la réponse
    4. Enregistre tout et mesure le progrès
    """

    def __init__(
        self,
        tree: dict,
        db_url: str | None = None,
        corpus_path: str | Path | None = None,
    ):
        self.tree = tree
        self.db_url = db_url or DB_URL
        # Init pool pour sessions standalone (hors web/daemon)
        from pool import init_pool
        init_pool(self.db_url)
        self.corpus = self._load_corpus(corpus_path or CORPUS_PATH)
        self._selector = TieredQuestionSelector(self.corpus)
        self._ensure_schema()
        # MadregotNeshamah — niveaux d'âme pour la profondeur des questions
        from madregot_neshamah import MadregotNeshamah
        self.madregot = MadregotNeshamah()

    # ── Corpus ─────────────────────────────────────────────

    def _load_corpus(self, path: str | Path) -> dict:
        """Charger le corpus de questions depuis YAML."""
        import yaml

        path = Path(path)
        if not path.exists():
            log.warning("Corpus introuvable: %s — corpus vide", path)
            return {}
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        total = sum(
            len(qs)
            for domain in data.values()
            if isinstance(domain, dict)
            for qs in domain.values()
            if isinstance(qs, list)
        )
        log.info("Corpus chargé: %d questions, %d domaines", total, len(data))
        return data

    # ── DB ─────────────────────────────────────────────────

    def _ensure_schema(self):
        """Créer les tables si nécessaire."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(SCHEMA_SQL)
                cur.close()
        except Exception as e:
            log.warning("Schema init failed (will retry on first use): %s", e)

    def _db(self):
        """Connexion DB depuis le pool centralisé."""
        from pool import get_conn
        return get_conn()

    # ── Ask Pipeline ───────────────────────────────────────

    def _ask_system(self, question: str, domain: str | None = None) -> dict:
        """Exercer le système avec une question — même pipeline que etz ask.

        Or Yashar (descendant): Keter→Hod→Yesod→Malkuth
        Or Chozer (ascendant): stocke en mémoire, calibre confiance
        """
        result = {
            "response": "",
            "competence_score": 0.0,
            "domain_detected": domain or "general",
            "sentiers_used": [],
            "nitzotzot_before": 0,
            "nitzotzot_after": 0,
            "memories_recalled": 0,
            "stored": False,
            "sifrei_yesod_refs": {},
        }

        # ── Or Yashar: descente ────────────────────────────

        # ① Hod — routage et compétence
        hod = self.tree.get("hod")
        if hod:
            try:
                decision = hod.route(question)
                result["competence_score"] = getattr(decision, "competence_score", 0.0) or 0.0
                result["domain_detected"] = getattr(decision, "detected_domain", domain) or domain or "general"
            except Exception as e:
                log.debug("Hod route failed: %s", e)

        # ② Yesod — rappel mémoire (contexte)
        yesod = self.tree.get("yesod")
        context_parts = []
        if yesod:
            try:
                memories = yesod.recall(question, limit=5)
                if memories:
                    context_parts = [
                        getattr(m, "content", str(m))
                        for m in memories
                    ]
                    result["memories_recalled"] = len(context_parts)
            except Exception as e:
                log.debug("Yesod recall failed: %s", e)

        # ②bis Sifrei Yesod — consultation des textes sacrés
        sy_refs = self._consult_sifrei_yesod(question)
        result["sifrei_yesod_refs"] = sy_refs
        if sy_refs.get("principes"):
            for p in sy_refs["principes"][:3]:
                pid = p.get("principe_id", "?")
                nom = p.get("nom", "")
                formal = p.get("formalisation", "")[:200]
                context_parts.append(f"[Sifrei Yesod {pid}] {nom}: {formal}")
        if sy_refs.get("assertions"):
            for a in sy_refs["assertions"][:5]:
                aid = a.get("assertion_id", "?")
                text = a.get("assertion", "")[:200]
                context_parts.append(f"[Source {aid}] {text}")

        # ③ Nitzotzot avant
        result["nitzotzot_before"] = self._count_nitzotzot()

        # ④ Malkuth — génération de réponse via Ollama (Yetzirah)
        context_text = "\n".join(context_parts[:11]) if context_parts else ""

        # Enrichissement spatial — position dans le Cube de l'Espace
        spatial = self._spatial_enrichment(result["domain_detected"])
        if spatial:
            context_text = f"{context_text}\n[Cube] {spatial}" if context_text else f"[Cube] {spatial}"

        # ②ter Da'at — pont connaissance↔application (anti-hallucination)
        daat_block = self._build_daat_bridge(
            result["domain_detected"], context_parts, question,
        )
        result["daat_applied"] = daat_block is not None
        if daat_block:
            context_text = f"{context_text}\n{daat_block}" if context_text else daat_block

        prompt = self._build_prompt(question, context_text, result["domain_detected"])

        try:
            from olamot import ollama_generate
            hitbo_kavvanah = {
                "intention": f"approfondir la compréhension du domaine {result['domain_detected']}",
                "critere_succes": "réponse précise avec score > 0.8, ancrage dans les sources rappelées",
                "anti_pattern": "ne pas répéter des réponses déjà données, ne pas halluciner de sources",
            }
            response, latency = ollama_generate(
                "yetzirah", prompt, timeout=120,
                kavvanah=hitbo_kavvanah, num_predict=512,
            )
            result["response"] = response

            # Retry si réponse vide — prompt simplifié, timeout plus long
            if not response.strip():
                log.info("Réponse vide, retry avec prompt simplifié")
                retry_prompt = (
                    f"Réponds en français à cette question de Kabbale.\n\n"
                    f"Question: {question}\n\nRéponse:"
                )
                retry_kavvanah = {
                    "intention": f"Récupérer une réponse après échec initial — domaine {result['domain_detected']}",
                    "critere_succes": "produire une réponse non-vide, même courte, ancrée dans le sujet",
                    "anti_pattern": "ne pas reproduire le silence — toute réponse vaut mieux qu'un vide",
                }
                response2, _ = ollama_generate(
                    "yetzirah", retry_prompt, timeout=180,
                    kavvanah=retry_kavvanah, num_predict=512,
                )
                if response2.strip():
                    result["response"] = response2
                    log.info("Retry réussi: %d mots", len(response2.split()))
        except Exception as e:
            log.warning("Ollama generate failed: %s", e)
            result["response"] = f"[erreur génération: {e}]"

        # ── Or Chozer: remontée ────────────────────────────

        # ⑤ Yesod — stocker la nouvelle connaissance
        if yesod and result["response"] and "[erreur" not in result["response"]:
            try:
                yesod.store(
                    content=f"Q: {question[:200]}\nR: {result['response'][:500]}",
                    source_sephirah="hitbonenut",
                    confidence=0.4,
                    domain=result["domain_detected"],
                )
                result["stored"] = True
            except Exception as e:
                log.debug("Yesod store failed: %s", e)

        # ⑥ Sentiers — exercer les sentiers pertinents
        result["sentiers_used"] = self._run_relevant_sentiers(
            question, result["domain_detected"],
        )

        # ⑦ Nitzotzot après
        result["nitzotzot_after"] = self._count_nitzotzot()

        return result

    def _build_prompt(self, question: str, context: str, domain: str) -> str:
        """Construire le prompt pour Malkuth.

        Note: /no_think retiré — causait des réponses vides avec Qwen3.
        Le flag think=false dans le payload Ollama suffit.
        Le prompt est restructuré pour être plus directif.
        """
        parts = [
            f"Tu es un système d'IA spécialisé en Kabbale (Etz Chaim), domaine: {domain}.",
            "Réponds en français avec les termes techniques kabbalistiques en hébreu translittéré.",
            "Donne une réponse détaillée et structurée.",
        ]
        if context:
            parts.extend([
                "",
                "Contexte:",
                context[:800],
            ])
        parts.extend([
            "",
            f"Question: {question}",
            "",
            "Réponse:",
        ])
        return "\n".join(parts)

    # ── Scoring ────────────────────────────────────────────

    def _score_response(
        self,
        question: str,
        response: str,
        domain: str,
        ask_result: dict,
        soul_level: str | None = None,
        tier: str = "core",
    ) -> tuple[float, float]:
        """Scorer la qualité d'une réponse.

        Si soul_level est fourni, le score est modulé par MadregotNeshamah
        (bonus/malus selon que la réponse correspond au style attendu du niveau).

        Returns:
            (score_total, kw_score)
            score_total = base mécanique + modulation par niveau d'âme
            kw_score = ratio de keywords du domaine présents dans la réponse
        """
        if not response or "[erreur" in response:
            return 0.0, 0.0

        response_lower = response.lower()
        words = response.split()
        word_count = len(words)

        # 1. Keywords du domaine (40%) — scoring progressif, pas binaire
        keywords = DOMAIN_KEYWORDS.get(domain, [])
        if keywords:
            found = sum(1 for kw in keywords if kw.lower() in response_lower)
            # Scoring sigmoïde : montée progressive, pas de seuil brutal
            # 2 keywords = 0.3, 5 = 0.6, 8+ = 0.9+
            ratio = found / len(keywords)
            kw_score = min(ratio * 2.5, 1.0)  # linéaire, 40% des keywords = max
        else:
            kw_score = 0.5

        # 2. Longueur suffisante (25%) — paliers : 30 mots=0.3, 80=0.7, 150+=1.0
        if word_count >= 150:
            length_score = 1.0
        elif word_count >= 30:
            length_score = 0.3 + 0.7 * (word_count - 30) / 120
        else:
            length_score = word_count / 100

        # 3. Diversité lexicale (20%) — type-token ratio, pénalise la répétition
        if word_count > 10:
            unique_words = len(set(w.lower() for w in words if len(w) > 3))
            ttr = unique_words / word_count
            # TTR typique pour un bon texte : 0.4-0.6
            diversity_score = min(ttr / 0.45, 1.0)
        else:
            diversity_score = 0.0

        # 4. Pertinence question (15%) — mots de la question présents dans la réponse
        q_words = set(w.lower() for w in question.split() if len(w) > 3)
        if q_words:
            q_found = sum(1 for w in q_words if w in response_lower)
            relevance_score = min(q_found / max(len(q_words) * 0.4, 1), 1.0)
        else:
            relevance_score = 0.5

        base_total = (
            0.40 * kw_score
            + 0.25 * length_score
            + 0.20 * diversity_score
            + 0.15 * relevance_score
        )

        # 5. Bridge scoring — bonus/malus pour questions cross-domaine
        if tier == "bridge" and ":" in domain:
            domain_a, domain_b = domain.split(":", 1)
            kw_a = DOMAIN_KEYWORDS.get(domain_a, [])
            kw_b = DOMAIN_KEYWORDS.get(domain_b, [])
            found_a = sum(1 for kw in kw_a if kw.lower() in response_lower) if kw_a else 1
            found_b = sum(1 for kw in kw_b if kw.lower() in response_lower) if kw_b else 1
            if found_a == 0 or found_b == 0:
                base_total -= 0.15
            if any(q in response_lower for q in BRIDGE_QUALIFIERS):
                base_total += 0.10
            else:
                base_total -= 0.10
            base_total = max(0.0, min(1.0, base_total))

        # 6. Modulation par niveau d'âme (MadregotNeshamah)
        if soul_level:
            level = self.madregot.get_question_level(soul_level)
            total = self.madregot.score_by_level(response, level, base_total)
        else:
            total = round(base_total, 3)

        return total, round(kw_score, 3)

    # ── EMA competence feedback ────────────────────────────

    def _upsert_competence_ema(self, domain: str, score: float, alpha: float = 0.1) -> None:
        """Mettre à jour selfmap_competence avec EMA après chaque question.

        EMA: new_score = alpha * score + (1 - alpha) * old_score
        Si pas d'entrée existante, on insère directement.
        """
        try:
            with self._db() as conn:
                cur = conn.cursor()

                # Récupérer le modèle Hod
                hod = self.tree.get("hod")
                from olamot import get_model
                _fallback_model = get_model("briah")
                model_id = getattr(hod, "default_model", _fallback_model) if hod else _fallback_model

                cur.execute("""
                    INSERT INTO selfmap_competence (domain, model_id, score, n_evals, updated_at)
                    VALUES (%s, %s, %s, 1, NOW())
                    ON CONFLICT (domain, model_id) DO UPDATE SET
                        score = %s * %s + (1 - %s) * selfmap_competence.score,
                        n_evals = selfmap_competence.n_evals + 1,
                        updated_at = NOW()
                """, (domain, model_id, score, alpha, score, alpha))
                cur.close()
        except Exception as e:
            log.debug("EMA upsert failed for %s: %s", domain, e)

    # ── Sessions ───────────────────────────────────────────

    def run_session(
        self,
        n_questions: int = 10,
        difficulty: str = "progressive",
        budget_seconds: float = 120.0,
    ) -> SessionResult:
        """Exercice dirigé — session de n questions.

        difficulty: "progressive" (basique→érudite), ou un niveau fixe
        """
        session_id = str(uuid.uuid4())
        t0 = time.monotonic()
        soul_before = self._get_soul_level()

        # SSE: début de session
        self._emit("hitbonenut_session_start", session_id=session_id, n=n_questions)

        # Tiered selection for research/progressive mode, legacy for targeted
        if difficulty in ("progressive", "research"):
            questions = self._selector.select(n_questions)
        else:
            questions = self._select_questions(n_questions, difficulty)
        if not questions:
            log.warning("Aucune question disponible dans le corpus")
            return SessionResult(
                session_id=session_id, n_questions=0, avg_score=0.0,
                domains=[], results=[], soul_before=soul_before,
                soul_after=soul_before, duration=0.0,
            )

        # Créer la session en DB
        self._db_create_session(session_id, n_questions, difficulty, soul_before)

        results: list[QuestionResult] = []
        domains_seen: set[str] = set()

        for i, q_item in enumerate(questions):
            elapsed = time.monotonic() - t0
            if elapsed >= budget_seconds:
                log.info("Budget épuisé après %d/%d questions", i, len(questions))
                break

            if len(q_item) == 4:
                q_text, q_domain, q_diff, q_tier = q_item
            else:
                q_text, q_domain, q_diff = q_item
                q_tier = "core"

            qr = self._exercise_one(session_id, q_text, q_domain, q_diff, tier=q_tier)
            results.append(qr)
            domains_seen.add(q_domain)

            # SSE: question terminée
            self._emit(
                "hitbonenut_answer",
                session_id=session_id,
                question=q_text[:80],
                domain=q_domain,
                score=qr.score,
                progress=f"{i + 1}/{len(questions)}",
            )

        # Résultats
        duration = time.monotonic() - t0
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        soul_after = self._get_soul_level()
        comp_delta = self._compute_competence_delta(soul_before)

        # ── Consolidation SelfMap par session ──
        # L'EMA par question (alpha=0.1) est trop lent pour bouger les scores.
        # La session complète a plus de poids : alpha=0.3 sur le score moyen par domaine.
        # C'est le Mashpia (l'influx) : le résultat consolidé descend plus fort.
        if results:
            domain_scores: dict[str, list[float]] = {}
            for r in results:
                if r.score > 0:
                    domain_scores.setdefault(r.domain, []).append(r.score)
            for dom, scores in domain_scores.items():
                session_avg = sum(scores) / len(scores)
                self._upsert_competence_ema(dom, session_avg, alpha=0.3)

        # Finaliser en DB
        self._db_finalize_session(
            session_id, avg_score, list(domains_seen),
            soul_before, soul_after, comp_delta, duration,
        )

        # SSE: fin de session
        self._emit(
            "hitbonenut_session_end",
            session_id=session_id,
            avg_score=round(avg_score, 3),
            soul_before=soul_before,
            soul_after=soul_after,
        )

        log.info(
            "Session %s terminée: %d questions, score=%.3f, soul=%s→%s, %.1fs",
            session_id[:8], len(results), avg_score, soul_before, soul_after, duration,
        )

        return SessionResult(
            session_id=session_id,
            n_questions=len(results),
            avg_score=round(avg_score, 3),
            domains=sorted(domains_seen),
            results=results,
            soul_before=soul_before,
            soul_after=soul_after,
            duration=round(duration, 1),
            competence_delta=comp_delta,
        )

    def run_targeted(self, domain: str, n: int = 5, budget_seconds: float = 120.0) -> SessionResult:
        """Session ciblée sur un domaine faible."""
        if domain not in self.corpus:
            log.warning("Domaine '%s' absent du corpus", domain)
            available = sorted(self.corpus.keys())
            log.info("Domaines disponibles: %s", ", ".join(available))
            return SessionResult(
                session_id=str(uuid.uuid4()), n_questions=0, avg_score=0.0,
                domains=[], results=[], soul_before="?", soul_after="?",
                duration=0.0,
            )

        session_id = str(uuid.uuid4())
        t0 = time.monotonic()
        soul_before = self._get_soul_level()

        self._emit("hitbonenut_session_start", session_id=session_id, n=n, domain=domain)
        self._db_create_session(session_id, n, f"targeted:{domain}", soul_before)

        # Toutes les questions du domaine, mélangées par difficulté progressive
        all_qs = []
        domain_data = self.corpus[domain]
        for diff in DIFFICULTY_ORDER:
            if diff in domain_data:
                for q in domain_data[diff]:
                    all_qs.append((q, domain, diff))

        selected = all_qs[:n] if len(all_qs) >= n else all_qs
        results: list[QuestionResult] = []

        q_tier = (
            "bridge" if ":" in domain
            else "breadth" if domain in BREADTH_DOMAINS
            else "core"
        )
        for i, (q_text, q_domain, q_diff) in enumerate(selected):
            elapsed = time.monotonic() - t0
            if elapsed >= budget_seconds:
                break
            qr = self._exercise_one(session_id, q_text, q_domain, q_diff, tier=q_tier)
            results.append(qr)
            self._emit(
                "hitbonenut_answer",
                session_id=session_id, question=q_text[:80],
                domain=domain, score=qr.score, progress=f"{i + 1}/{n}",
            )

        duration = time.monotonic() - t0
        avg_score = sum(r.score for r in results) / len(results) if results else 0.0
        soul_after = self._get_soul_level()
        comp_delta = self._compute_competence_delta(soul_before)

        # ── Consolidation SelfMap ciblée ──
        # Session ciblée → impact plus fort (alpha=0.3) sur le domaine cible
        if results and avg_score > 0:
            self._upsert_competence_ema(domain, avg_score, alpha=0.3)

        self._db_finalize_session(
            session_id, avg_score, [domain],
            soul_before, soul_after, comp_delta, duration,
        )
        self._emit(
            "hitbonenut_session_end",
            session_id=session_id, avg_score=round(avg_score, 3),
            soul_before=soul_before, soul_after=soul_after,
        )

        log.info(
            "Session ciblée %s [%s]: %d questions, score=%.3f, %.1fs",
            session_id[:8], domain, len(results), avg_score, duration,
        )

        return SessionResult(
            session_id=session_id, n_questions=len(results),
            avg_score=round(avg_score, 3), domains=[domain],
            results=results, soul_before=soul_before, soul_after=soul_after,
            duration=round(duration, 1), competence_delta=comp_delta,
        )

    # ── Mode Continu (legacy — remplacé par run_research_loop) ──

    def run_continuous(
        self,
        max_duration: float | None = None,
        max_questions: int | None = None,
        stop_event: "threading.Event | None" = None,
    ) -> SessionResult:
        """DEPRECATED — Redirige vers run_research_loop.

        L'ancien mode quiz kabbalistique est remplacé par la boucle de
        recherche réflexive Hitbonenut-2.
        """
        log.info("run_continuous() appelé — redirection vers run_research_loop()")
        self.run_research_loop(
            max_duration=max_duration,
            stop_event=stop_event,
        )
        # Retourner un SessionResult vide pour compatibilité
        return SessionResult(
            session_id="legacy-redirect",
            n_questions=0, avg_score=0.0, domains=[],
            results=[], soul_before="", soul_after="",
            duration=0.0,
        )

    # ══════════════════════════════════════════════════════════
    # ══ HITBONENUT-2 : Boucle de Recherche Réflexive ════════
    # ══ Pattern Karpathy + Or Chozer + Da'at                ══
    # ══════════════════════════════════════════════════════════

    def run_research_loop(
        self,
        max_experiments: int | None = None,
        max_duration: float | None = None,
        stop_event: "threading.Event | None" = None,
    ) -> list[ExperimentResult]:
        """Boucle de recherche autonome — le vrai Hitbonenut.

        Pattern Karpathy enrichi :
        1. Chokhmah  — identifier le point faible + formuler hypothèse
        2. Binah     — contempler avant d'agir
        3. Yetzirah  — expérimenter (modifier param, mesurer)
        4. Or Chozer — réfléchir, extraire le principe
        5. Da'at     — vérifier la transformation opérationnelle
        6. Shov      — stocker, mettre à jour, recommencer

        NEVER STOP — sauf stop_event, max_experiments, ou max_duration.
        """
        import threading

        session_id = str(uuid.uuid4())
        t0 = time.monotonic()
        experiments: list[ExperimentResult] = []
        experiment_count = 0

        self._emit("hitbonenut_research_start", session_id=session_id)
        self._db_create_session(session_id, 0, "research", self._get_soul_level())

        log.info(
            "══ Hitbonenut-2 RESEARCH LOOP démarré (session=%s) ══",
            session_id[:8],
        )

        # Charger les principes existants pour guider les hypothèses
        principles = self._load_principles()
        log.info("Principes chargés : %d actifs", len(principles))

        # Charger l'historique des expériences récentes (cooldown)
        recent_experiments = self._load_recent_experiments(limit=50)

        try:
            while True:
                # ── Conditions d'arrêt ──
                if stop_event and stop_event.is_set():
                    log.info("Hitbonenut-2: stop_event reçu")
                    break
                if max_duration and (time.monotonic() - t0) >= max_duration:
                    log.info("Hitbonenut-2: max_duration atteint")
                    break
                if max_experiments and experiment_count >= max_experiments:
                    log.info("Hitbonenut-2: max_experiments atteint")
                    break
                try:
                    from pause_state import is_paused as _check_pause
                    if _check_pause("hitbonenut"):
                        log.info("Hitbonenut-2: PAUSED")
                        break
                except ImportError as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

                # ══ STEP 1 : CHOKHMAH — Identifier le point faible ══
                log.info("── [%d] Chokhmah : identification ──", experiment_count + 1)
                weak_point = self._identify_weakest()
                if not weak_point:
                    log.warning("Aucun point faible identifié — pause 60s")
                    time.sleep(60)
                    continue

                # ══ STEP 2 : CHOKHMAH→BINAH — Formuler hypothèse ══
                hypothesis = self._formulate_hypothesis(
                    weak_point, principles, recent_experiments,
                )
                if not hypothesis:
                    log.warning("Pas d'hypothèse formulée pour %s — skip", weak_point)
                    time.sleep(30)
                    continue

                log.info(
                    "── [%d] Hypothèse : %s.%s = %s → %s | %s",
                    experiment_count + 1,
                    hypothesis["target_module"],
                    hypothesis["target_param"],
                    hypothesis["old_value"],
                    hypothesis["new_value"],
                    hypothesis["reason"][:80],
                )

                # ══ STEP 3 : BINAH — Contempler avant d'agir ══
                contemplation = self._contemplate_before(hypothesis, principles)
                log.info("── [%d] Contemplation : %s", experiment_count + 1, contemplation[:120])

                # ══ STEP 4 : YETZIRAH — Expérimenter (le Karpathy) ══
                log.info("── [%d] Yetzirah : expérience en cours ──", experiment_count + 1)
                exp_result = self._run_experiment(session_id, hypothesis, contemplation)

                experiments.append(exp_result)
                experiment_count += 1
                recent_experiments.append(exp_result)

                # ══ STEP 5 : OR CHOZER — Réfléchir ══
                log.info(
                    "── [%d] Or Chozer : delta=%.4f, status=%s ──",
                    experiment_count, exp_result.delta, exp_result.status,
                )

                principle_text = self._reflect(exp_result, principles)
                if principle_text:
                    log.info("── [%d] Principe : %s", experiment_count, principle_text[:120])

                    # ══ STEP 6 : DA'AT — Vérifier la transformation ══
                    daat_ok = self._verify_daat(exp_result)
                    exp_result = ExperimentResult(
                        **{**exp_result.__dict__, "daat_verified": daat_ok, "principle": principle_text}
                    )

                    # ══ STEP 7 : SHOV — Stocker et mettre à jour ══
                    self._store_principle(principle_text, exp_result.id, exp_result.target_module)
                    principles = self._load_principles()  # Recharger

                    if daat_ok:
                        log.info("── [%d] Da'at ATTEINT — transformation vérifiée", experiment_count)
                    else:
                        log.info("── [%d] Da'at non atteint — itération nécessaire", experiment_count)

                # ── SSE ──
                self._emit(
                    "hitbonenut_experiment_done",
                    session_id=session_id,
                    experiment=experiment_count,
                    module=exp_result.target_module,
                    param=exp_result.target_param,
                    delta=round(exp_result.delta, 4),
                    status=exp_result.status,
                    principle=exp_result.principle[:200] if exp_result.principle else "",
                    daat=exp_result.daat_verified,
                )

                log.info(
                    "══ [%d] %s | %s.%s | %s→%s | delta=%.4f | %s ══",
                    experiment_count, exp_result.status.upper(),
                    exp_result.target_module, exp_result.target_param,
                    exp_result.old_value, exp_result.new_value,
                    exp_result.delta, "DA'AT" if exp_result.daat_verified else "binah",
                )

        except KeyboardInterrupt:
            log.info("Hitbonenut-2: interrompu après %d expériences", experiment_count)

        # ── Finalisation ──
        duration = time.monotonic() - t0
        soul_after = self._get_soul_level()
        keeps = [e for e in experiments if e.status == "keep"]
        discards = [e for e in experiments if e.status == "discard"]

        self._db_finalize_session(
            session_id, 0.0, [], self._get_soul_level(), soul_after,
            {"experiments": experiment_count, "keeps": len(keeps), "discards": len(discards)},
            duration,
        )

        self._emit(
            "hitbonenut_research_end",
            session_id=session_id,
            experiments=experiment_count,
            keeps=len(keeps),
            discards=len(discards),
            principles_learned=len([e for e in experiments if e.principle]),
            duration=round(duration, 1),
        )

        log.info(
            "══ Hitbonenut-2 TERMINÉ : %d exp, %d keep, %d discard, %.1fs ══",
            experiment_count, len(keeps), len(discards), duration,
        )

        return experiments

    # ── Identification du point faible (Chokhmah) ────────

    def _identify_weakest(self) -> dict | None:
        """Adam Kadmon + SelfMap → point le plus faible du système.

        Returns dict with keys: module, param, current_score, reason
        or None if nothing to improve.
        """
        weak = {}

        # 1. Adam Kadmon — divergences structurelles
        try:
            from adam_kadmon import AdamKadmon
            ak = AdamKadmon()
            fidelity = ak.compare_to_current(
                modules=self.tree,
                sentiers=[s for s in self.tree if s.startswith("sentier_")],
                partzufim={k: v for k, v in self.tree.items() if k in (
                    "atik_yomin", "arikh_anpin", "abba", "imma", "zeir_anpin", "nukva",
                )},
            )
            weak["fidelity_score"] = fidelity.score
            weak["phase"] = fidelity.phase
            if fidelity.divergences:
                top_div = fidelity.divergences[0]
                weak["top_divergence"] = {
                    "component": top_div.component,
                    "name": top_div.name,
                    "severity": top_div.severity,
                    "reason": top_div.expected,
                }
        except Exception as e:
            log.debug("Adam Kadmon not available: %s", e)
            weak["fidelity_score"] = 0.0

        # 2. SelfMap — compétences par domaine
        hod = self.tree.get("hod")
        if hod and hasattr(hod, "self_diagnose"):
            try:
                diag = hod.self_diagnose()
                weak["selfmap_diag"] = diag
                domains = diag.get("domains", {})
                if domains:
                    weakest_domain = min(domains, key=lambda d: domains[d].get("score", 1.0))
                    weak["weakest_domain"] = weakest_domain
                    weak["weakest_domain_score"] = domains[weakest_domain].get("score", 0.0)
            except Exception as e:
                log.debug("SelfMap diagnose failed: %s", e)

        # 3. Self-diagnostics des modules — trouver les Qliphoth actives
        # NOTE: signal.alarm ne fonctionne PAS dans un thread secondaire.
        # On utilise ThreadPoolExecutor avec timeout à la place.
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

        for module_name in ("chokmah", "gevurah", "tiferet", "binah"):
            mod = self.tree.get(module_name)
            if mod and hasattr(mod, "self_diagnose"):
                try:
                    # quick=True pour éviter le O(n²) Nogah du DissensuEngine
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        try:
                            future = executor.submit(mod.self_diagnose, quick=True)
                        except TypeError:
                            future = executor.submit(mod.self_diagnose)
                        d = future.result(timeout=5)
                    level = d.get("level", "healthy")
                    if level != "healthy":
                        weak.setdefault("unhealthy_modules", []).append({
                            "module": module_name,
                            "level": level,
                            "details": d,
                        })
                except (FuturesTimeout, Exception):
                    log.debug("self_diagnose(%s) skipped (timeout or error)", module_name)

        # 4. Choisir le paramètre le plus prometteur à modifier
        # Priorité : modules unhealthy > faible fidelité > domaine faible
        target = self._select_tunable_target(weak)
        if target:
            weak["target"] = target
            return weak

        return weak if weak.get("fidelity_score", 1.0) < 0.9 else None

    def _select_tunable_target(self, weak: dict) -> dict | None:
        """Choisir quel paramètre modifier en priorité.

        Respecte le cooldown (pas de re-modification trop rapide).
        """
        recent = self._load_recent_experiments(limit=EXPERIMENT_COOLDOWN)
        # Reconstruct param_key from stored module.attr for cooldown check
        recently_touched: set[str] = set()
        for e in recent:
            # Match against all known param_keys
            for pk, pd in TUNABLE_PARAMS.items():
                if pd["module"] == e.target_module and pd["attr"] == e.target_param:
                    recently_touched.add(pk)
                    break

        # Score de priorité pour chaque paramètre tunable
        candidates = []
        for param_key, param_def in TUNABLE_PARAMS.items():
            if param_key in recently_touched:
                continue  # Cooldown actif

            module_name = param_def["module"]
            score = 0.0

            # Bonus si le module est unhealthy
            for uh in weak.get("unhealthy_modules", []):
                if uh["module"] == module_name:
                    score += 2.0

            # Bonus si la fidélité est basse
            if weak.get("fidelity_score", 1.0) < 0.5:
                score += 1.0

            # Bonus si c'est le domaine le plus faible
            if weak.get("weakest_domain_score", 1.0) < 0.4:
                score += 0.5

            candidates.append((param_key, param_def, score))

        if not candidates:
            # Tous en cooldown — prendre le paramètre dont la dernière
            # expérience est la plus ancienne (cooldown le plus avancé)
            oldest_per_param: dict[str, float] = {}
            for e in recent:
                for pk, pd in TUNABLE_PARAMS.items():
                    if pd["module"] == e.target_module and pd["attr"] == e.target_param:
                        ts = getattr(e, "timestamp", 0) or 0
                        if pk not in oldest_per_param or ts < oldest_per_param[pk]:
                            oldest_per_param[pk] = ts
                        break
            if oldest_per_param:
                oldest_key = min(oldest_per_param, key=oldest_per_param.get)
                log.info("Tous les paramètres en cooldown — forçage de %s (le plus ancien)", oldest_key)
                candidates = [(oldest_key, TUNABLE_PARAMS[oldest_key], 0.0)]
            else:
                return None

        # Trier par score décroissant, prendre le meilleur
        candidates.sort(key=lambda c: -c[2])
        best_key, best_def, best_score = candidates[0]

        # Lire la valeur actuelle
        current_value = self._read_param_value(best_key, best_def)

        return {
            "param_key": best_key,
            "module": best_def["module"],
            "attr": best_def["attr"],
            "current_value": current_value,
            "param_def": best_def,
            "priority_score": best_score,
        }

    def _read_param_value(self, param_key: str, param_def: dict):
        """Lire la valeur actuelle d'un paramètre tunable."""
        module_name = param_def["module"]
        attr_name = param_def["attr"]

        if module_name == "_self":
            return globals().get(attr_name, param_def.get("min", 0))

        module = self.tree.get(module_name)
        if module and hasattr(module, attr_name):
            return getattr(module, attr_name)

        return param_def.get("min", 0)

    def _write_param_value(self, param_key: str, param_def: dict, new_value):
        """Écrire une nouvelle valeur pour un paramètre tunable."""
        module_name = param_def["module"]
        attr_name = param_def["attr"]

        if module_name == "_self":
            globals()[attr_name] = new_value
            return True

        module = self.tree.get(module_name)
        if module and hasattr(module, attr_name):
            setattr(module, attr_name, new_value)
            return True

        log.warning("Cannot write %s.%s — module not found", module_name, attr_name)
        return False

    # ── Formulation d'hypothèse (Chokhmah → Binah) ──────

    def _formulate_hypothesis(
        self,
        weak_point: dict,
        principles: list[Principle],
        recent_experiments: list[ExperimentResult],
    ) -> dict | None:
        """Utiliser le LLM (Briah/thinking) pour proposer une modification."""
        target = weak_point.get("target")
        if not target:
            return None

        param_def = target["param_def"]
        current_value = target["current_value"]
        param_type = param_def["type"]
        step = param_def["step"]

        # Construire le contexte pour le LLM
        principles_text = "\n".join(
            f"- [{p.confidence:.1f}] {p.principle}"
            for p in principles[:10]
        ) if principles else "Aucun principe encore appris."

        recent_text = "\n".join(
            f"- {e.target_module}.{e.target_param}: {e.old_value}→{e.new_value} "
            f"| delta={e.delta:+.4f} | {e.status} | {e.principle[:80] if e.principle else '?'}"
            for e in recent_experiments[-10:]
        ) if recent_experiments else "Aucune expérience récente."

        unhealthy_text = "\n".join(
            f"- {uh['module']}: niveau {uh['level']}"
            for uh in weak_point.get("unhealthy_modules", [])
        ) if weak_point.get("unhealthy_modules") else "Tous healthy."

        prompt = (
            f"{RESEARCH_SYSTEM_PROMPT}\n\n"
            f"=== ÉTAT DU SYSTÈME ===\n"
            f"Fidélité Adam Kadmon : {weak_point.get('fidelity_score', '?')}\n"
            f"Phase : {weak_point.get('phase', '?')}\n"
            f"Domaine le plus faible : {weak_point.get('weakest_domain', '?')} "
            f"(score: {weak_point.get('weakest_domain_score', '?')})\n"
            f"Modules unhealthy :\n{unhealthy_text}\n\n"
            f"=== PARAMÈTRE CIBLÉ ===\n"
            f"Paramètre : {target['param_key']}\n"
            f"Description : {param_def['description']}\n"
            f"Valeur actuelle : {current_value}\n"
            f"Plage : [{param_def['min']}, {param_def['max']}], step={step}\n\n"
            f"=== PRINCIPES APPRIS ===\n{principles_text}\n\n"
            f"=== EXPÉRIENCES RÉCENTES ===\n{recent_text}\n\n"
            f"=== QUESTION ===\n"
            f"Quelle nouvelle valeur proposes-tu pour '{target['param_key']}' ?\n"
            f"Réponds UNIQUEMENT au format : VALEUR|RAISON\n"
            f"Exemple : 0.6|Baisser le seuil augmentera le flux d'insights\n"
        )

        try:
            from olamot import ollama_generate
            raw, _ = ollama_generate(
                "briah", prompt, timeout=120,
                kavvanah={
                    "intention": f"Formuler une hypothèse d'amélioration pour {target['param_key']}",
                    "critere_succes": "Proposition argumentée avec valeur et raison",
                    "anti_pattern": "Ne pas proposer la même valeur que l'actuelle",
                },
            )
        except Exception as e:
            log.warning("LLM hypothesis generation failed: %s", e)
            # Fallback : direction simple basée sur l'état
            raw = None

        # Parser la réponse ou fallback
        new_value = None
        reason = ""

        if raw:
            for line in raw.strip().split("\n"):
                line = line.strip()
                if "|" in line:
                    parts = line.split("|", 1)
                    try:
                        val_str = parts[0].strip()
                        if param_type == float:
                            new_value = float(val_str)
                        elif param_type == int:
                            new_value = int(float(val_str))
                        reason = parts[1].strip() if len(parts) > 1 else ""
                        break
                    except (ValueError, IndexError):
                        continue

        # Fallback : perturbation simple dans la direction probable
        if new_value is None:
            if param_type == float:
                new_value = current_value - step  # Baisser par défaut (assouplir)
            else:
                new_value = current_value - int(step)
            reason = "Perturbation exploratoire (fallback — LLM n'a pas répondu au format)"

        # Clamp aux bornes
        new_value = max(param_def["min"], min(param_def["max"], new_value))

        # Éviter de proposer la même valeur
        if new_value == current_value:
            if param_type == float:
                new_value = current_value + step
            else:
                new_value = current_value + int(step)
            new_value = max(param_def["min"], min(param_def["max"], new_value))

        if new_value == current_value:
            return None  # Coincé aux bornes

        return {
            "target_module": target["module"],
            "target_param": target["attr"],
            "param_key": target["param_key"],
            "param_def": param_def,
            "old_value": str(current_value),
            "new_value": str(new_value),
            "new_value_typed": new_value,
            "reason": reason,
        }

    # ── Contemplation (Binah) ────────────────────────────

    def _contemplate_before(self, hypothesis: dict, principles: list[Principle]) -> str:
        """Analyser les risques avant d'expérimenter.

        Binah déploie avant d'agir — contrairement à Karpathy qui fonce.
        """
        # Chercher des principes qui pourraient s'appliquer
        relevant = [
            p for p in principles
            if p.domain == hypothesis["target_module"]
            or hypothesis["target_param"] in p.principle.lower()
        ]

        if relevant:
            context = " | ".join(p.principle[:80] for p in relevant[:3])
            return f"Principes pertinents : {context}. Procéder avec prudence."

        return (
            f"Première modification de {hypothesis['param_key']}. "
            f"Aucun principe antérieur. Mode exploratoire."
        )

    # ── Expérience (Yetzirah — le Karpathy) ──────────────

    def _run_experiment(
        self,
        session_id: str,
        hypothesis: dict,
        contemplation: str,
    ) -> ExperimentResult:
        """Modifier un paramètre, mesurer l'impact, keep/discard.

        Le prepare.py d'Etz Chaim = mesure via run_session() ciblée.
        """
        exp_id = str(uuid.uuid4())
        t0 = time.monotonic()

        # ── SNAPSHOT BEFORE (baseline) ──
        metric_before = self._measure_system_metrics()

        # Sauver l'expérience en DB
        self._db_create_experiment(
            exp_id, session_id, hypothesis, contemplation, metric_before,
        )

        # ── MODIFIER LE PARAMÈTRE ──
        old_typed = hypothesis.get("new_value_typed")
        param_def = hypothesis["param_def"]
        old_raw = self._read_param_value(hypothesis["param_key"], param_def)

        success = self._write_param_value(
            hypothesis["param_key"], param_def, hypothesis["new_value_typed"],
        )

        if not success:
            return ExperimentResult(
                id=exp_id, target_module=hypothesis["target_module"],
                target_param=hypothesis["target_param"],
                old_value=hypothesis["old_value"], new_value=hypothesis["new_value"],
                hypothesis=hypothesis["reason"], contemplation=contemplation,
                metric_before=metric_before, metric_after={},
                delta=0.0, status="crash", principle="", daat_verified=False,
                duration=time.monotonic() - t0, measurement_sessions=0,
            )

        # ── MESURER L'IMPACT (run N sessions) ──
        scores_after = []
        for i in range(MEASUREMENT_SESSIONS):
            try:
                result = self.run_session(n_questions=5, difficulty="progressive", budget_seconds=300)
                scores_after.append(result.avg_score)
                log.info(
                    "  Mesure %d/%d: avg_score=%.3f",
                    i + 1, MEASUREMENT_SESSIONS, result.avg_score,
                )
            except Exception as e:
                log.warning("  Mesure %d échouée: %s", i + 1, e)
                scores_after.append(0.0)

        # ── SNAPSHOT AFTER ──
        metric_after = self._measure_system_metrics()
        avg_after = sum(scores_after) / len(scores_after) if scores_after else 0.0
        metric_after["avg_session_score"] = avg_after

        # ── DÉCISION : KEEP or DISCARD ──
        # Comparer les métriques composites
        before_composite = metric_before.get("composite", 0.0)
        after_composite = metric_after.get("composite", 0.0)
        delta = after_composite - before_composite

        if delta > 0:
            status = "keep"
            log.info("  KEEP : delta=+%.4f", delta)
        elif delta < -MAX_REGRESSION:
            # Régression trop forte → REVERT
            status = "discard"
            self._write_param_value(hypothesis["param_key"], param_def, old_raw)
            log.warning("  DISCARD + REVERT : delta=%.4f (> max_regression %.2f)", delta, MAX_REGRESSION)
        else:
            status = "discard"
            self._write_param_value(hypothesis["param_key"], param_def, old_raw)
            log.info("  DISCARD : delta=%.4f (pas d'amélioration)", delta)

        duration = time.monotonic() - t0

        # Sauver en DB
        self._db_finalize_experiment(exp_id, metric_after, delta, status, len(scores_after))

        return ExperimentResult(
            id=exp_id, target_module=hypothesis["target_module"],
            target_param=hypothesis["target_param"],
            old_value=hypothesis["old_value"], new_value=hypothesis["new_value"],
            hypothesis=hypothesis["reason"], contemplation=contemplation,
            metric_before=metric_before, metric_after=metric_after,
            delta=delta, status=status, principle="", daat_verified=False,
            duration=duration, measurement_sessions=len(scores_after),
        )

    # ── Réflexion (Or Chozer) ────────────────────────────

    def _reflect(self, experiment: ExperimentResult, principles: list[Principle]) -> str:
        """Extraire le POURQUOI — le principe derrière le résultat.

        C'est le Or Chozer : la lumière de retour qui enrichit.
        Karpathy n'a pas ça — il garde ou jette sans comprendre.
        """
        prompt = (
            f"{RESEARCH_SYSTEM_PROMPT}\n\n"
            f"=== RÉSULTAT D'EXPÉRIENCE ===\n"
            f"Module : {experiment.target_module}\n"
            f"Paramètre : {experiment.target_param}\n"
            f"Changement : {experiment.old_value} → {experiment.new_value}\n"
            f"Hypothèse : {experiment.hypothesis}\n"
            f"Contemplation : {experiment.contemplation}\n"
            f"Delta : {experiment.delta:+.4f}\n"
            f"Status : {experiment.status}\n"
            f"Métriques avant : {json.dumps(experiment.metric_before, default=str)}\n"
            f"Métriques après : {json.dumps(experiment.metric_after, default=str)}\n\n"
            f"=== QUESTION ===\n"
            f"Quel PRINCIPE général peux-tu extraire de cette expérience ?\n"
            f"Le principe doit être réutilisable pour guider les prochaines expériences.\n"
            f"Réponds en UNE phrase claire et actionnable.\n"
        )

        try:
            from olamot import ollama_generate
            raw, _ = ollama_generate(
                "briah", prompt, timeout=90,
                kavvanah={
                    "intention": "Extraire un principe réutilisable de l'expérience",
                    "critere_succes": "Principe clair, actionnable, en une phrase",
                    "anti_pattern": "Ne pas simplement répéter le résultat",
                },
            )
            if raw and len(raw.strip()) > 10:
                # Prendre la première phrase substantielle
                for line in raw.strip().split("\n"):
                    line = line.strip().strip("-").strip("*").strip()
                    if len(line) > 20:
                        return line[:500]
        except Exception as e:
            log.warning("Reflection LLM failed: %s", e)

        # Fallback mécanique
        if experiment.status == "keep":
            return (
                f"Baisser {experiment.target_param} de {experiment.old_value} "
                f"à {experiment.new_value} améliore le système (delta={experiment.delta:+.4f})"
            )
        else:
            return (
                f"Modifier {experiment.target_param} de {experiment.old_value} "
                f"à {experiment.new_value} n'améliore pas (delta={experiment.delta:+.4f})"
            )

    # ── Vérification Da'at ───────────────────────────────

    def _verify_daat(self, experiment: ExperimentResult) -> bool:
        """Le comportement a-t-il RÉELLEMENT changé ?

        Da'at = union, pas juste connaissance. Si le score change mais
        que le système produit les mêmes réponses, Da'at n'est pas atteint.
        """
        if experiment.status != "keep":
            return False

        # Vérification 1 : le delta est significatif
        if abs(experiment.delta) < 0.01:
            return False

        # Vérification 2 : les métriques de sortie ont changé (pas juste le score)
        before = experiment.metric_before
        after = experiment.metric_after

        # Comparer les métriques module par module
        changes = 0
        for key in after:
            if key in before and before[key] != after[key]:
                changes += 1

        # Au moins 2 métriques ont changé = transformation réelle
        return changes >= 2

    # ── Mesure des métriques système (prepare.py equivalent) ──

    def _measure_system_metrics(self) -> dict:
        """Mesurer l'état actuel du système — les métriques immutables."""
        metrics = {}

        # 1. Compétence globale SelfMap
        hod = self.tree.get("hod")
        if hod and hasattr(hod, "get_global_competence"):
            try:
                metrics["selfmap_competence"] = hod.get_global_competence()
            except Exception:
                metrics["selfmap_competence"] = 0.0
        else:
            metrics["selfmap_competence"] = 0.0

        # 2. Fidélité Adam Kadmon
        try:
            from adam_kadmon import AdamKadmon
            ak = AdamKadmon()
            result = ak.compare_to_current(modules=self.tree)
            metrics["fidelity"] = result.score
            metrics["phase"] = result.phase
        except Exception:
            metrics["fidelity"] = 0.0

        # 3. Diagnostics modules (timeout 5s chacun — certains appellent le LLM)
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

        for mod_name in ("chokmah", "gevurah", "tiferet", "binah", "yesod"):
            mod = self.tree.get(mod_name)
            if mod and hasattr(mod, "self_diagnose"):
                try:
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        try:
                            future = executor.submit(mod.self_diagnose, quick=True)
                        except TypeError:
                            future = executor.submit(mod.self_diagnose)
                        diag = future.result(timeout=5)
                    metrics[f"{mod_name}_level"] = diag.get("level", "unknown")
                    metrics[f"{mod_name}_score"] = diag.get("score", 0.0)
                except (FuturesTimeout, Exception):
                    metrics[f"{mod_name}_level"] = "error"

        # 4. Score composite (le val_bpb d'Etz Chaim)
        comp = metrics.get("selfmap_competence", 0.0) * 0.4 + metrics.get("fidelity", 0.0) * 0.6
        metrics["composite"] = round(comp, 4)

        return metrics

    # ── DB pour expériences et principes ─────────────────

    def _db_create_experiment(
        self, exp_id: str, session_id: str, hypothesis: dict,
        contemplation: str, metric_before: dict,
    ):
        """Insérer une expérience en cours."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO hitbonenut_experiments
                    (id, session_id, target_module, target_param, old_value,
                     new_value, hypothesis, contemplation, metric_before)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        exp_id, session_id,
                        hypothesis["target_module"], hypothesis["target_param"],
                        hypothesis["old_value"], hypothesis["new_value"],
                        hypothesis["reason"], contemplation,
                        json.dumps(metric_before),
                    ),
                )
                cur.close()
        except Exception as e:
            log.warning("DB create experiment failed: %s", e)

    def _db_finalize_experiment(
        self, exp_id: str, metric_after: dict, delta: float,
        status: str, measurement_sessions: int,
    ):
        """Finaliser une expérience."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    """UPDATE hitbonenut_experiments
                    SET ended_at = NOW(), metric_after = %s, delta = %s,
                        status = %s, measurement_sessions = %s
                    WHERE id = %s""",
                    (json.dumps(metric_after), delta, status, measurement_sessions, exp_id),
                )
                cur.close()
        except Exception as e:
            log.warning("DB finalize experiment failed: %s", e)

    def _store_principle(self, principle_text: str, experiment_id: str, domain: str):
        """Stocker un principe appris — en DB et en EpisteMemory."""
        principle_id = str(uuid.uuid4())

        # 1. DB hitbonenut_principles
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO hitbonenut_principles
                    (id, principle, source_experiment, domain, confidence)
                    VALUES (%s, %s, %s, %s, %s)""",
                    (principle_id, principle_text, experiment_id, domain, 0.5),
                )
                cur.close()
        except Exception as e:
            log.warning("DB store principle failed: %s", e)

        # 2. EpisteMemory — pour que les autres modules le voient
        yesod = self.tree.get("yesod")
        if yesod and hasattr(yesod, "remember"):
            try:
                yesod.remember(
                    content=f"[Hitbonenut-2 Principe] {principle_text}",
                    source_sephirah="hitbonenut",
                    confidence=0.5,
                    domain=domain,
                    tags=["hitbonenut", "principle", "auto-optimisation"],
                )
            except Exception as e:
                log.debug("EpisteMemory store principle failed: %s", e)

    def _load_principles(self, active_only: bool = True) -> list[Principle]:
        """Charger les principes appris."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                query = "SELECT id, principle, source_experiment, domain, confidence, confirmed_count, contradicted_count, is_active FROM hitbonenut_principles"
                if active_only:
                    query += " WHERE is_active = true"
                query += " ORDER BY confidence DESC LIMIT 50"
                cur.execute(query)
                rows = cur.fetchall()
                cur.close()
                return [
                    Principle(
                        id=str(r[0]), principle=r[1], source_experiment=str(r[2]) if r[2] else "",
                        domain=r[3] or "", confidence=r[4] or 0.5,
                        confirmed_count=r[5] or 0, contradicted_count=r[6] or 0,
                        is_active=r[7] if r[7] is not None else True,
                    )
                    for r in rows
                ]
        except Exception as e:
            log.debug("Load principles failed (table may not exist yet): %s", e)
            return []

    def _load_recent_experiments(self, limit: int = 50) -> list[ExperimentResult]:
        """Charger les expériences récentes pour le cooldown et le contexte."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    """SELECT id, target_module, target_param, old_value, new_value,
                              hypothesis, contemplation, metric_before, metric_after,
                              delta, status, principle_extracted, daat_verified,
                              EXTRACT(EPOCH FROM (ended_at - started_at)), measurement_sessions
                       FROM hitbonenut_experiments
                       ORDER BY started_at DESC LIMIT %s""",
                    (limit,),
                )
                rows = cur.fetchall()
                cur.close()
                return [
                    ExperimentResult(
                        id=str(r[0]), target_module=r[1], target_param=r[2],
                        old_value=r[3], new_value=r[4],
                        hypothesis=r[5] or "", contemplation=r[6] or "",
                        metric_before=r[7] or {}, metric_after=r[8] or {},
                        delta=r[9] or 0.0, status=r[10] or "unknown",
                        principle=r[11] or "", daat_verified=r[12] or False,
                        duration=r[13] or 0.0, measurement_sessions=r[14] or 0,
                    )
                    for r in rows
                ]
        except Exception as e:
            log.debug("Load recent experiments failed: %s", e)
            return []

    def _get_kav_focus(self) -> str | None:
        """Lire le domaine du Kav depuis la DB (Tzimtzum en contraction)."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT kav_domain FROM tzimtzum_state WHERE id = 1 AND is_contracted = true"
                )
                row = cur.fetchone()
                cur.close()
                return row[0] if row and row[0] else None
        except Exception:
            return None

    def _select_next_question(
        self, question_idx: int, forced_switches: int,
    ) -> tuple[str, str, str]:
        """Sélection intelligente : domaines faibles ciblés plus souvent.

        Respecte le Kav : si le Tzimtzum est en contraction, ne pose des
        questions que sur le domaine focal (le seul rayon de lumière dans
        le Halal).

        - 60% : question du domaine le plus faible
        - 20% : question novel (générée par LLM)
        - 20% : question aléatoire du corpus

        Difficulté auto-scalée selon la compétence.
        """
        progress = None
        if question_idx % 10 == 0:  # Réévaluer tous les 10
            progress = self.assess_progress()

        # ── Kav : en contraction, seul le domaine focal est accessible ──
        kav_domain = self._get_kav_focus()
        if kav_domain:
            return self._select_from_kav_domain(kav_domain)

        # ── Mode normal : sélection standard ──
        # Décider de la stratégie
        roll = random.random()

        if roll < 0.6:
            # Domaine faible
            weak = self._get_weak_domains()
            if weak:
                domain = weak[0]
                if domain in self.corpus:
                    diff = self._auto_difficulty()
                    domain_data = self.corpus[domain]
                    candidates = []
                    for d in DIFFICULTY_ORDER:
                        if d in domain_data and isinstance(domain_data[d], list):
                            for q in domain_data[d]:
                                candidates.append((q, domain, d))
                    if candidates:
                        # Filtrer par difficulté appropriée
                        at_level = [c for c in candidates if c[2] == diff]
                        if at_level:
                            return random.choice(at_level)
                        return random.choice(candidates)

        elif roll < 0.8:
            # Question novel — difficulté déterminée par le niveau d'âme
            novel = self.generate_novel_question()
            if novel:
                soul = self._get_soul_level()
                level = self.madregot.get_question_level(soul)
                diff = self.madregot.get_difficulty_for_level(level)
                return novel, "novel", diff

        # Fallback : question aléatoire du corpus
        diff = self._auto_difficulty()
        all_qs = self._select_questions(1, diff)
        if all_qs:
            return all_qs[0]

        # Ultime fallback
        all_qs = self._select_questions(1, "progressive")
        if all_qs:
            return all_qs[0]

        return "Décris la structure de l'Arbre de Vie et ses 10 Sefirot.", "kabbale_lurianique", "basique"

    def _select_from_kav_domain(self, kav_domain: str) -> tuple[str, str, str]:
        """Sélectionner une question exclusivement du domaine Kav.

        Pendant la contraction, le Kav est le seul canal ouvert.
        Toute l'énergie du système est focalisée sur ce domaine.
        """
        diff = self._auto_difficulty()

        # Chercher dans le corpus du domaine Kav
        if kav_domain in self.corpus:
            domain_data = self.corpus[kav_domain]
            candidates = []
            for d in DIFFICULTY_ORDER:
                if d in domain_data and isinstance(domain_data[d], list):
                    for q in domain_data[d]:
                        candidates.append((q, kav_domain, d))
            if candidates:
                at_level = [c for c in candidates if c[2] == diff]
                if at_level:
                    return random.choice(at_level)
                return random.choice(candidates)

        # Fallback : question générique sur le domaine
        return (
            f"Explique en profondeur un concept clé du domaine '{kav_domain}'.",
            kav_domain,
            diff,
        )

    def _select_from_different_domain(self, exclude_domain: str) -> tuple[str, str, str]:
        """Sélectionner une question d'un domaine DIFFÉRENT."""
        diff = self._auto_difficulty()
        all_qs: list[tuple[str, str, str]] = []
        for domain_name, levels in self.corpus.items():
            if domain_name == exclude_domain or not isinstance(levels, dict):
                continue
            for d, questions in levels.items():
                if isinstance(questions, list):
                    for q in questions:
                        all_qs.append((q, domain_name, d))

        if all_qs:
            return random.choice(all_qs)
        return "Quelle est la différence entre Or Yashar et Or Chozer ?", "ohr", "basique"

    def _auto_difficulty(self) -> str:
        """Difficulté auto-scalée selon la compétence globale."""
        scores = self._get_domain_scores()
        if not scores:
            return "basique"
        avg = sum(scores.values()) / len(scores)
        if avg > 0.6:
            return "avancee"
        if avg > 0.3:
            return "intermediaire"
        return "basique"

    def get_today_stats(self) -> dict:
        """Stats du jour pour le mode continu."""
        try:
          with self._db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*), COALESCE(AVG(score), 0) "
                "FROM hitbonenut_questions "
                "WHERE created_at >= CURRENT_DATE",
            )
            row = cur.fetchone()
            questions_today = row[0] if row else 0
            avg_today = round(row[1], 3) if row else 0.0

            cur.execute(
                "SELECT domain, AVG(score) "
                "FROM hitbonenut_questions "
                "WHERE created_at >= CURRENT_DATE "
                "GROUP BY domain ORDER BY AVG(score) ASC",
            )
            domain_rows = cur.fetchall()
            cur.close()
            return {
                "questions_today": questions_today,
                "avg_score_today": avg_today,
                "domains_today": {r[0]: round(r[1], 3) for r in domain_rows if r[0]},
            }
        except Exception:
            return {"questions_today": 0, "avg_score_today": 0.0, "domains_today": {}}

    # ── Novel Question Generation (Pattern Karpathy) ──────

    def _select_novel_tier_and_domain(self) -> tuple[str, str]:
        """Sélectionner tier + domaine pour la génération de question novel.

        Distribution : 40% core, 40% breadth, 20% bridge.
        Au sein de chaque tier, priorise le domaine le plus faible.
        """
        r = random.random()
        if r < 0.4:
            tier = "core"
            domains = CORE_DOMAINS
        elif r < 0.8:
            tier = "breadth"
            domains = BREADTH_DOMAINS
        else:
            tier = "bridge"
            # Pour bridge, on tire 2 domaines aléatoires de tiers différents
            d_a = random.choice(CORE_DOMAINS)
            d_b = random.choice(BREADTH_DOMAINS)
            return tier, f"{d_a}:{d_b}"

        # Prioriser le domaine le plus faible dans ce tier
        weak = self._get_weak_domains_for_tier(domains)
        domain = weak[0] if weak else random.choice(domains)
        return tier, domain

    def _get_weak_domains_for_tier(self, domains: list[str]) -> list[str]:
        """Domaines les plus faibles parmi une liste donnée."""
        try:
            placeholders = ",".join(["%s"] * len(domains))
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    f"SELECT domain, score FROM selfmap_competence "
                    f"WHERE domain IN ({placeholders}) "
                    f"ORDER BY score ASC, n_evals ASC LIMIT 3",
                    domains,
                )
                rows = cur.fetchall()
                cur.close()
                found = [r[0] for r in rows]
                # Ajouter les domaines jamais évalués (score=0, absents de la table)
                never_seen = [d for d in domains if d not in {r[0] for r in rows}]
                random.shuffle(never_seen)
                return never_seen + found  # Domaines jamais vus en priorité
        except Exception:
            return list(domains)

    def generate_novel_question(self, max_retries: int = 5) -> str | None:
        """Générer une question NOUVELLE — le vrai Hitbonenut.

        Pattern Karpathy + MadregotNeshamah + Multi-Domain :
        1. Sélectionner tier (40% core / 40% breadth / 20% bridge)
        2. Charger l'historique (déduplication)
        3. Sélectionner le niveau d'âme
        4. Générer via LLM avec prompt érudit adapté au domaine
        5. Scorer la novelty
        6. Accepter si novelty ≥ seuil

        Returns:
            La question générée, ou None si novelty insuffisante après retries.
        """
        # 0. Sélection tier + domaine (40/40/20)
        tier, domain = self._select_novel_tier_and_domain()
        log.info("Novel question: tier=%s, domain=%s", tier, domain)

        # 1. Historique des questions posées (30 récentes suffisent pour novelty)
        past_questions = self._get_past_questions(limit=30)

        # 2. Insights récents depuis EpisteMemory
        recent_insights = self._get_recent_insights(limit=10)

        # 3. Domaines faibles (pour orienter la question)
        weak_domains = self._get_weak_domains()

        # 3b. Niveau d'âme → niveau de question (distribution 70/20/10)
        soul_level = self._get_soul_level()
        question_level = self.madregot.select_level_for_question(soul_level)
        log.info(
            "MadregotNeshamah: soul=%s → question_level=%s, tier=%s",
            soul_level, question_level.name, tier,
        )

        threshold = NOVELTY_THRESHOLD_INITIAL
        best_candidate = None
        best_novelty = 0.0

        # Enrichir avec le contexte hybride Cube + ML (core seulement)
        cube_context = ""
        if tier == "core":
            try:
                from kabbalah.hybrid_retrieval import HybridRetrieval
                retrieval = HybridRetrieval()
                cube_context = retrieval.enrich_context(domain, top_k=5)
            except Exception as e:
                log.debug("HybridRetrieval not available: %s", e)

        for attempt in range(max_retries):
            # Construire le prompt adapté au tier
            if tier == "bridge":
                prompt = self._build_bridge_novel_prompt(
                    domain, past_questions, attempt,
                )
            elif tier == "breadth":
                prompt = self._build_breadth_novel_prompt(
                    domain, question_level, past_questions,
                    recent_insights, attempt,
                )
            else:
                # Core (Kabbale) — prompt existant via MadregotNeshamah
                prompt = self.madregot.build_level_prompt(
                    level=question_level,
                    domain=domain,
                    past_questions=past_questions,
                    insights=recent_insights,
                    weak_domains=weak_domains,
                    attempt=attempt,
                )
                if cube_context:
                    prompt += (
                        "\n\nContexte structurel du Cube de l'Espace :\n"
                        + cube_context
                        + "\n\nUtilise ces connexions structurelles pour "
                        "formuler une question qui explore les liens cachés.\n"
                    )

            try:
                from olamot import ollama_generate
                raw, _ = ollama_generate(
                    "yetzirah", prompt, timeout=90,
                    kavvanah={
                        "intention": f"Générer une question {tier} de niveau {question_level.name} sur {domain}",
                        "critere_succes": "Question nouvelle, érudite, non présente dans l'historique",
                        "anti_pattern": "Ne pas reformuler une question déjà posée, ne pas rester superficiel",
                    },
                    domain=domain.split(":")[0] if ":" in domain else domain,
                    context_items=[f"Tier: {tier}, Domaines faibles: {', '.join(weak_domains[:3])}"] if weak_domains else [f"Tier: {tier}"],
                    principles=[f"Niveau: {question_level.name}, Tier: {tier}"],
                )
                # Extraire la question (première ligne non vide qui finit par ?)
                candidate = self._extract_question(raw)
                if not candidate:
                    log.debug("Attempt %d: pas de question extraite", attempt)
                    continue
            except Exception as e:
                log.warning("Novel question generation failed: %s", e)
                continue

            # 4. Scorer la novelty via embedding similarity
            novelty = self._compute_novelty(candidate, past_questions)
            log.debug(
                "Attempt %d: '%s' — novelty=%.3f (seuil=%.2f)",
                attempt, candidate[:60], novelty, threshold,
            )

            # Track best candidate in case we accept via decay
            if novelty > best_novelty:
                best_novelty = novelty
                best_candidate = candidate

            # 5. Accepter si novelty ≥ seuil courant
            if novelty >= threshold:
                log.info("Novel question accepted (novelty=%.3f, seuil=%.2f): %s",
                         novelty, threshold, candidate[:80])
                return candidate

            # 6. Decay progressif du seuil après chaque échec
            threshold = max(threshold - NOVELTY_THRESHOLD_DECAY, NOVELTY_THRESHOLD_FLOOR)

        # Dernier recours : accepter le meilleur candidat si au-dessus du plancher
        if best_candidate and best_novelty >= NOVELTY_THRESHOLD_FLOOR:
            log.info("Novel question accepted via floor (novelty=%.3f): %s",
                     best_novelty, best_candidate[:80])
            return best_candidate

        log.warning("Novelty threshold not met after %d retries (best=%.3f, floor=%.2f)",
                    max_retries, best_novelty, NOVELTY_THRESHOLD_FLOOR)
        return None

    def _build_novel_prompt(
        self,
        past_questions: list[str],
        insights: list[str],
        weak_domains: list[str],
        attempt: int,
    ) -> str:
        """Prompt pour générer une question nouvelle."""
        parts = [
            "Tu es un système kabbalistique qui génère des questions "
            "d'auto-évaluation. Génère UNE question originale et précise "
            "sur la Kabbale, le Sefer Yetzirah, ou l'Arbre de Vie.",
            "",
        ]

        if weak_domains:
            parts.append(f"Domaines faibles à cibler: {', '.join(weak_domains[:3])}")
            parts.append("")

        if insights:
            parts.append("Insights récents du système (inspire-toi en):")
            for ins in insights[:5]:
                parts.append(f"  - {ins[:150]}")
            parts.append("")

        if past_questions:
            parts.append(f"Questions DÉJÀ posées ({len(past_questions)} total, en voici les dernières):")
            for pq in past_questions[-10:]:
                parts.append(f"  - {pq[:120]}")
            parts.append("")
            parts.append("IMPORTANT: La question doit être DIFFÉRENTE de toutes celles ci-dessus.")
            parts.append("")

        if attempt > 0:
            parts.append(
                f"(Tentative {attempt + 1}: sois plus créatif, "
                "explore un angle inhabituel ou un lien inter-domaines.)"
            )
            parts.append("")

        parts.append(
            "Réponds UNIQUEMENT avec la question, "
            "sans commentaire. Termine par un point d'interrogation."
        )
        return "\n".join(parts)

    def _build_breadth_novel_prompt(
        self,
        domain: str,
        question_level: object,
        past_questions: list[str],
        insights: list[str],
        attempt: int,
    ) -> str:
        """Prompt érudit pour générer une question hors-Kabbale.

        Injecte le contexte épistémique du domaine (auteurs, tensions, frontières)
        pour forcer l'érudition — pas de questions Wikipedia.
        """
        ctx = DOMAIN_EPISTEMIC_CONTEXT.get(domain, "")
        level_name = getattr(question_level, "name", "erudite")

        parts = [
            f"Tu es un système cognitif universel qui s'auto-évalue. "
            f"Génère UNE question originale et précise de niveau {level_name} "
            f"sur le domaine suivant.",
            "",
            ctx if ctx else f"Domaine : {domain}",
            "",
        ]

        # Calibration par niveau
        if level_name in ("erudite", "avancee"):
            parts.append(
                "EXIGENCES pour une question érudite :\n"
                "- Citer au moins un auteur ou théorème spécifique\n"
                "- Exiger la nuance (tensions, limites, divergences)\n"
                "- Pas de question factuelle simple — synthèse et analyse\n"
                "- La question doit être discriminante : un expert répond bien, "
                "un novice échoue"
            )
            parts.append("")
        elif level_name == "intermediaire":
            parts.append(
                "La question doit établir une connexion entre deux concepts "
                "du domaine. Pas de simple rappel factuel."
            )
            parts.append("")

        if past_questions:
            parts.append(f"Questions DÉJÀ posées ({len(past_questions)} récentes) :")
            for pq in past_questions[-8:]:
                parts.append(f"  - {pq[:120]}")
            parts.append("")
            parts.append("IMPORTANT: La question doit être DIFFÉRENTE.")
            parts.append("")

        if insights:
            parts.append("Insights récents du système :")
            for ins in insights[:3]:
                parts.append(f"  - {ins[:150]}")
            parts.append("")

        if attempt > 0:
            parts.append(
                f"(Tentative {attempt + 1}: explore un angle inhabituel, "
                "une tension non résolue dans le domaine, ou un lien "
                "avec un sous-domaine adjacent.)"
            )
            parts.append("")

        parts.append(
            "Réponds UNIQUEMENT avec la question, "
            "sans commentaire. Termine par un point d'interrogation."
        )
        return "\n".join(parts)

    def _build_bridge_novel_prompt(
        self,
        domain: str,
        past_questions: list[str],
        attempt: int,
    ) -> str:
        """Prompt pour générer une question cross-domaine (bridge).

        Le domain est au format 'domain_a:domain_b'.
        La question doit exiger parallèle structurel + qualification.
        """
        if ":" not in domain:
            return self._build_novel_prompt(past_questions, [], [], attempt)

        domain_a, domain_b = domain.split(":", 1)
        ctx_a = DOMAIN_EPISTEMIC_CONTEXT.get(domain_a, f"Domaine : {domain_a}")
        ctx_b = DOMAIN_EPISTEMIC_CONTEXT.get(domain_b, f"Domaine : {domain_b}")

        parts = [
            BRIDGE_GENERATION_PROMPT,
            "",
            f"DOMAINE A : {ctx_a}",
            "",
            f"DOMAINE B : {ctx_b}",
            "",
            "CONTRAINTES :\n"
            "- La question doit OBLIGER à comprendre les deux domaines\n"
            "- Elle doit exiger d'identifier OÙ l'analogie s'effondre\n"
            "- Cite des concepts spécifiques de chaque domaine\n"
            "- Niveau érudite : un spécialiste d'un seul domaine ne peut pas "
            "bien répondre, il faut maîtriser les deux",
            "",
        ]

        if past_questions:
            bridges_seen = [q for q in past_questions if any(
                kw in q.lower() for kw in ["analogie", "compare", "parallèle", "s'effondre"]
            )]
            if bridges_seen:
                parts.append(f"Questions cross-domaine DÉJÀ posées :")
                for pq in bridges_seen[-5:]:
                    parts.append(f"  - {pq[:150]}")
                parts.append("")
                parts.append("IMPORTANT: La question doit être DIFFÉRENTE.")
                parts.append("")

        if attempt > 0:
            parts.append(
                f"(Tentative {attempt + 1}: explore une connexion structurelle "
                "moins évidente. Pas les parallèles classiques — cherche un lien "
                "que personne n'a formulé.)"
            )
            parts.append("")

        parts.append(
            "Réponds UNIQUEMENT avec la question, "
            "sans commentaire. Termine par un point d'interrogation."
        )
        return "\n".join(parts)

    def _extract_question(self, raw: str) -> str | None:
        """Extraire la question du texte brut LLM."""
        for line in raw.strip().split("\n"):
            line = line.strip().strip('"').strip("'").strip()
            if line and line.endswith("?") and len(line) > 15:
                return line
        # Fallback: tout le texte s'il finit par ?
        raw = raw.strip()
        if raw.endswith("?") and len(raw) > 15 and len(raw) < 300:
            return raw
        return None

    def _compute_novelty(self, candidate: str, past_questions: list[str]) -> float:
        """Novelty = 1 - max_similarity vs historique.

        Utilise les embeddings (nomic-embed-text) pour la similarité.
        Fallback sur jaccard si embeddings indisponibles.
        """
        if not past_questions:
            return 1.0

        try:
            from olamot import ollama_embed
            _embed_kav = {
                "intention": "Évaluer la nouveauté sémantique de la question candidate",
                "critere_succes": "Embedding fidèle au contenu sémantique",
                "anti_pattern": "Pas de perte d'information par troncation",
            }
            cand_emb = ollama_embed(candidate, kavvanah=_embed_kav, domain="novelty_check")
            max_sim = 0.0
            for pq in past_questions[-50:]:  # limiter pour perf
                pq_emb = ollama_embed(pq, domain="novelty_check")
                sim = self._cosine_sim(cand_emb, pq_emb)
                max_sim = max(max_sim, sim)
            return round(1.0 - max_sim, 3)
        except Exception as e:
            log.debug("Embedding novelty failed, fallback jaccard: %s", e)
            return self._jaccard_novelty(candidate, past_questions)

    @staticmethod
    def _cosine_sim(a: list[float], b: list[float]) -> float:
        """Similarité cosinus entre deux vecteurs."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _jaccard_novelty(candidate: str, past_questions: list[str]) -> float:
        """Fallback novelty via Jaccard distance."""
        cand_words = set(candidate.lower().split())
        max_sim = 0.0
        for pq in past_questions[-50:]:
            pq_words = set(pq.lower().split())
            inter = len(cand_words & pq_words)
            union = len(cand_words | pq_words)
            if union > 0:
                max_sim = max(max_sim, inter / union)
        return round(1.0 - max_sim, 3)

    # ── Progress Assessment ────────────────────────────────

    def assess_progress(self) -> ProgressReport:
        """Évaluer le progrès global du système."""
        current_scores = self._get_domain_scores()
        sessions_count = self._get_sessions_count()
        soul = self._get_soul_level()

        # Deltas par rapport à la dernière session
        deltas = {}
        previous = self._get_previous_scores()
        for domain, score in current_scores.items():
            prev = previous.get(domain, 0.0)
            deltas[domain] = round(score - prev, 3)

        # Domaines stagnants (même score après ≥ 3 sessions)
        stagnant = self._get_stagnant_domains(threshold_sessions=3)
        improving = [d for d, delta in deltas.items() if delta > 0.01]

        overall = sum(current_scores.values()) / max(len(current_scores), 1)

        return ProgressReport(
            current_scores=current_scores,
            deltas=deltas,
            stagnant_domains=stagnant,
            improving_domains=improving,
            sessions_count=sessions_count,
            soul_level=soul,
            overall_competence=round(overall, 3),
        )

    # ── Internal Helpers ───────────────────────────────────

    def _exercise_one(
        self,
        session_id: str,
        question: str,
        domain: str,
        difficulty: str,
        is_novel: bool = False,
        tier: str = "core",
    ) -> QuestionResult:
        """Exercer le système sur une question et enregistrer."""
        q_id = str(uuid.uuid4())
        t0 = time.monotonic()

        # SSE: question posée
        self._emit("hitbonenut_question", question=question[:80], domain=domain)

        # Poser la question
        ask_result = self._ask_system(question, domain)

        # Scorer (modulé par soul_level si disponible)
        soul = self._get_soul_level()
        score, kw_score = self._score_response(
            question, ask_result["response"], domain, ask_result,
            soul_level=soul, tier=tier,
        )

        duration = time.monotonic() - t0
        nitz_delta = max(
            ask_result.get("nitzotzot_after", 0) - ask_result.get("nitzotzot_before", 0),
            0,
        )
        sentiers = ask_result.get("sentiers_used", [])

        # Sifrei Yesod refs + Da'at
        sy_refs = ask_result.get("sifrei_yesod_refs", {})
        daat_applied = ask_result.get("daat_applied", False)

        # Enregistrer en DB (inclut les refs Sifrei Yesod + daat_applied)
        self._db_record_question(
            q_id, session_id, question, domain, difficulty,
            ask_result["response"], score, kw_score,
            sentiers, nitz_delta, duration, is_novel, sy_refs,
            daat_applied, tier=tier,
        )

        # ── P4: Alimenter selfmap_competence via EMA ──
        # Ne pas empoisonner l'EMA avec des scores 0 dus à des erreurs/réponses vides
        # Alpha=0.05 par question (lissage léger) — la consolidation session (alpha=0.3)
        # est le signal autoritatif. Les deux ne double-comptent pas car alpha est faible.
        if score > 0 and ask_result["response"] and "[erreur" not in ask_result["response"]:
            self._upsert_competence_ema(domain, score, alpha=0.05)

        # ── InsightForge : capturer les réponses exceptionnelles ──
        if score > 0.85:
            self._submit_insight_candidate(question, ask_result["response"], domain, score)

        # ── FailureToInsight : capturer les échecs productifs ──
        if score < 0.3 and ask_result["response"]:
            self._record_failure(question, ask_result["response"], domain, score)

        return QuestionResult(
            id=q_id, question=question, domain=domain,
            difficulty=difficulty, response=ask_result["response"],
            score=score, kw_score=kw_score, sentiers_used=sentiers,
            nitzotzot=nitz_delta, duration=round(duration, 1),
            is_novel=is_novel, daat_applied=daat_applied,
            sifrei_yesod_refs=sy_refs,
        )

    def _submit_insight_candidate(
        self, question: str, response: str, domain: str, score: float,
    ) -> None:
        """Soumettre un candidat insight à InsightForge (Chokmah)."""
        chokmah = self.tree.get("chokmah")
        if not chokmah:
            return
        try:
            from insightforge.models import CandidateInsight
            candidate = CandidateInsight(
                description=f"Q: {question}\nA: {response[:500]}",
                source_module="hitbonenut",
                domain=domain,
                novelty_score=score,
                confidence=score,
                status="pending",
                connects_domains=[d for d in [domain, "hitbonenut"] if d],
            )
            chokmah.db.save_candidate(candidate)
            log.info("InsightForge: candidat soumis (domain=%s, score=%.3f)", domain, score)
        except Exception as e:
            log.debug("InsightForge submit failed: %s", e)

    def _record_failure(
        self, question: str, response: str, domain: str, score: float,
    ) -> None:
        """Enregistrer un échec productif dans FailureToInsight (Lamed)."""
        lamed = self.tree.get("lamed")
        if not lamed:
            return
        try:
            lamed.analyze_failure(
                description=f"Score {score:.3f} sur '{question[:100]}' — réponse: {response[:200]}",
                source_type="hitbonenut",
                domain=domain,
                context={"score": score, "question": question[:200]},
            )
            log.info("FailureToInsight: échec enregistré (domain=%s, score=%.3f)", domain, score)
        except Exception as e:
            log.debug("FailureToInsight record failed: %s", e)

    def _select_questions(
        self, n: int, difficulty: str,
    ) -> list[tuple[str, str, str]]:
        """Sélectionner n questions du corpus.

        Returns: [(question_text, domain, difficulty_level), ...]
        """
        all_questions: list[tuple[str, str, str]] = []

        for domain_name, levels in self.corpus.items():
            if not isinstance(levels, dict):
                continue
            for diff, questions in levels.items():
                if not isinstance(questions, list):
                    continue
                for q in questions:
                    all_questions.append((q, domain_name, diff))

        if not all_questions:
            return []

        if difficulty == "progressive":
            # Trier par difficulté puis mélanger au sein de chaque niveau
            by_diff: dict[str, list] = {}
            for item in all_questions:
                by_diff.setdefault(item[2], []).append(item)
            ordered = []
            for diff in DIFFICULTY_ORDER:
                group = by_diff.get(diff, [])
                random.shuffle(group)
                ordered.extend(group)
            return ordered[:n]

        elif difficulty in DIFFICULTY_ORDER:
            filtered = [q for q in all_questions if q[2] == difficulty]
            random.shuffle(filtered)
            return filtered[:n]

        else:
            random.shuffle(all_questions)
            return all_questions[:n]

    def _run_relevant_sentiers(self, question: str, domain: str) -> list[str]:
        """Exercer les sentiers pertinents au domaine."""
        used = []
        try:
            from sentiers import run_sentier, REGISTRY

            # Mapping domaine → sentiers pertinents
            domain_sentiers = {
                "gematria": ["yod"],
                "tzeruf": ["peh"],
                "sefer_yetzirah": ["aleph", "mem", "shin"],
                "sentiers": ["tav", "lamed"],
                "ohr": ["beth", "heh"],
                "neshamot": ["nun"],
                "qliphoth": ["ayin"],
                "kabbale_lurianique": ["gimel"],
                "partzufim": ["daleth"],
                "tzimtzum": ["tsadi"],
            }

            sentier_names = domain_sentiers.get(domain, [])
            for s_name in sentier_names[:2]:  # max 2 sentiers par question
                if s_name not in REGISTRY:
                    continue
                try:
                    result = run_sentier(s_name, self.tree)
                    if result.success:
                        used.append(s_name)
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # sentier failure = pas grave
        except ImportError as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return used

    def _spatial_enrichment(self, domain: str) -> str | None:
        """Enrichit le contexte avec une route spatiale dans le Cube.

        Utilise TzerufSpatial pour calculer la position du domaine
        dans le Cube de l'Espace et suggérer des directions d'exploration.
        """
        try:
            from kabbalah.tzeruf_spatial import TzerufSpatial
            ts = TzerufSpatial()

            # Mapper domaine → lettre du Cube et calculer le profil
            domain_map = ts.cube._DOMAIN_LETTERS
            letter = domain_map.get(domain)
            if not letter:
                return None

            pos = ts.cube.get_position(letter)
            mode = ts.cube.get_cognitive_mode(letter)

            # Trouver un domaine complémentaire (perpendiculaire dans le Cube)
            route = ts.suggest_exploration_route(domain, "pensée")
            intermediates = [
                s["letter"] for s in route
                if s.get("role") == "intermédiaire"
            ] if route else []

            parts = [
                f"Position dans le Cube: {letter} ({pos.letter}) — {mode}",
            ]
            if intermediates:
                parts.append(
                    f"Route cognitive: {' → '.join(intermediates)}"
                )
            return " | ".join(parts)
        except Exception:
            return None

    def _build_daat_bridge(
        self,
        domain: str,
        context_parts: list[str],
        question: str,
    ) -> str | None:
        """Pont Da'at : lie le contexte à la question (anti-hallucination).

        Retourne None si aucun exemple réussi n'existe dans le domaine
        (mieux vaut pas de Da'at que du faux Da'at).
        """
        try:
            from daat_bridge import DaatBridge
            bridge = DaatBridge(self._db)
            return bridge.build(question=question, domain=domain, facts=context_parts)
        except Exception as e:
            log.debug("Da'at bridge failed: %s", e)
            return None

    def _consult_sifrei_yesod(self, question: str) -> dict:
        """Consulter les textes sacrés avant de contempler.

        Recherche sémantique dans les Sifrei Yesod pour enrichir
        le contexte de Hitbonenut avec principes génératifs et assertions.
        Graceful degradation : si la DB ou les embeddings ne sont pas
        disponibles, retourne un dict vide sans erreur.
        """
        try:
            from sifrei_yesod.api.query import SifreiYesodQuery
            sq = SifreiYesodQuery(self.db_url)
            refs = sq.consult_for_hitbonenut(question)
            sq.close()

            # Sérialiser pour stockage (retirer les embeddings volumineux)
            for p in refs.get("principes", []):
                p.pop("embedding", None)
            for a in refs.get("assertions", []):
                a.pop("embedding", None)

            return refs
        except Exception as e:
            log.debug("Sifrei Yesod consultation failed: %s", e)
            return {}

    def _count_nitzotzot(self) -> int:
        """Compter les Nitzotzot en DB."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM failuretoinsight_insights")
                count = cur.fetchone()[0]
                cur.close()
                return count
        except Exception:
            return 0

    def _get_soul_level(self) -> str:
        """Niveau d'âme actuel via NeshamotEngine."""
        try:
            from soul_levels import NeshamotEngine
            engine = NeshamotEngine()
            nitz = {"count": self._count_nitzotzot() % 288, "cycle": self._count_nitzotzot() // 288}
            assessment = engine.assess_soul_level(self.tree, nitz, None)
            return assessment.level
        except Exception:
            return "nefesh"

    def _get_past_questions(self, limit: int = 200) -> list[str]:
        """Questions déjà posées (pour déduplication)."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT question FROM hitbonenut_questions ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                rows = cur.fetchall()
                cur.close()
                return [r[0] for r in rows]
        except Exception:
            return []

    def _get_recent_insights(self, limit: int = 10) -> list[str]:
        """Insights récents depuis EpisteMemory."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT content FROM epistememory WHERE epistemic_status = 'active' "
                    "ORDER BY created_at DESC LIMIT %s",
                    (limit,),
                )
                rows = cur.fetchall()
                cur.close()
                return [r[0] for r in rows]
        except Exception:
            return []

    def _get_weak_domains(self) -> list[str]:
        """Domaines avec score de compétence le plus bas (core + breadth).

        Inclut les domaines jamais évalués (score implicite = 0).
        """
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT domain, score FROM selfmap_competence "
                    "WHERE model_id = (SELECT model_id FROM selfmap_competence LIMIT 1) "
                    "ORDER BY score ASC LIMIT 5",
                )
                rows = cur.fetchall()
                cur.close()
                found = [r[0] for r in rows]
                seen = set(found)
                # Domaines breadth jamais évalués = les plus faibles par définition
                never_seen = [d for d in BREADTH_DOMAINS if d not in seen]
                random.shuffle(never_seen)
                return (never_seen + found)[:5]
        except Exception:
            return list(BREADTH_DOMAINS[:3])

    def _get_domain_scores(self) -> dict[str, float]:
        """Scores moyens par domaine depuis les sessions Hitbonenut."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT domain, AVG(score) FROM hitbonenut_questions "
                    "GROUP BY domain ORDER BY domain",
                )
                rows = cur.fetchall()
                cur.close()
                return {r[0]: round(r[1], 3) for r in rows if r[0]}
        except Exception:
            return {}

    def _get_previous_scores(self) -> dict[str, float]:
        """Scores de la session précédente."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id FROM hitbonenut_sessions ORDER BY started_at DESC LIMIT 1 OFFSET 1",
                )
                row = cur.fetchone()
                if not row:
                    cur.close()
                    return {}
                prev_id = row[0]
                cur.execute(
                    "SELECT domain, AVG(score) FROM hitbonenut_questions "
                    "WHERE session_id = %s GROUP BY domain",
                    (prev_id,),
                )
                rows = cur.fetchall()
                cur.close()
                return {r[0]: round(r[1], 3) for r in rows if r[0]}
        except Exception:
            return {}

    def _get_stagnant_domains(self, threshold_sessions: int = 3) -> list[str]:
        """Domaines dont le score ne bouge plus depuis N sessions."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute("""
                    WITH recent_sessions AS (
                        SELECT id, ROW_NUMBER() OVER (ORDER BY started_at DESC) as rn
                        FROM hitbonenut_sessions
                    ),
                    recent_scores AS (
                        SELECT q.domain, AVG(q.score) as avg_score, rs.rn
                        FROM hitbonenut_questions q
                        JOIN recent_sessions rs ON rs.id = q.session_id
                        WHERE rs.rn <= %s
                        GROUP BY q.domain, rs.rn
                    )
                    SELECT domain
                    FROM recent_scores
                    GROUP BY domain
                    HAVING COUNT(DISTINCT rn) >= %s
                       AND MAX(avg_score) - MIN(avg_score) < 0.02
                """, (threshold_sessions, threshold_sessions))
                rows = cur.fetchall()
                cur.close()
                return [r[0] for r in rows]
        except Exception:
            return []

    def _get_sessions_count(self) -> int:
        """Nombre total de sessions."""
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM hitbonenut_sessions")
                count = cur.fetchone()[0]
                cur.close()
                return count
        except Exception:
            return 0

    def _compute_competence_delta(self, soul_before: str) -> dict:
        """Delta de compétence par domaine."""
        scores = self._get_domain_scores()
        return {"domains": scores, "soul_before": soul_before}

    # ── DB Record Helpers ──────────────────────────────────

    def _db_create_session(
        self, session_id: str, n: int, difficulty: str, soul_before: str,
    ):
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO hitbonenut_sessions (id, n_questions, difficulty, soul_level_before) "
                    "VALUES (%s, %s, %s, %s)",
                    (session_id, n, difficulty, soul_before),
                )
                cur.close()
        except Exception as e:
            log.warning("DB create session failed: %s", e)

    def _db_finalize_session(
        self,
        session_id: str,
        avg_score: float,
        domains: list[str],
        soul_before: str,
        soul_after: str,
        comp_delta: dict,
        duration: float,
    ):
        try:
            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE hitbonenut_sessions SET "
                    "ended_at = NOW(), avg_score = %s, domains_tested = %s, "
                    "soul_level_before = %s, soul_level_after = %s, "
                    "competence_delta = %s "
                    "WHERE id = %s",
                    (avg_score, domains, soul_before, soul_after,
                     json.dumps(comp_delta), session_id),
                )
                cur.close()
        except Exception as e:
            log.warning("DB finalize session failed: %s", e)

    def _db_record_question(
        self,
        q_id: str,
        session_id: str,
        question: str,
        domain: str,
        difficulty: str,
        response: str,
        score: float,
        kw_score: float,
        sentiers: list[str],
        nitzotzot: int,
        duration: float,
        is_novel: bool,
        sifrei_yesod_refs: dict | None = None,
        daat_applied: bool = False,
        tier: str = "core",
    ):
        try:
            # Compact refs for storage: just IDs and similarities
            sy_compact = {}
            if sifrei_yesod_refs:
                sy_compact = {
                    "principes": [
                        {"id": p.get("principe_id"), "nom": p.get("nom", ""), "sim": round(p.get("similarity", 0), 3)}
                        for p in sifrei_yesod_refs.get("principes", [])
                    ],
                    "assertions": [
                        {"id": a.get("assertion_id"), "sim": round(a.get("similarity", 0), 3)}
                        for a in sifrei_yesod_refs.get("assertions", [])
                    ],
                }

            with self._db() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO hitbonenut_questions "
                    "(id, session_id, question, domain, difficulty, response, "
                    "score, kw_score, sentiers_used, nitzotzot_generated, "
                    "duration_seconds, is_novel, sifrei_yesod_refs, daat_applied, tier) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (q_id, session_id, question, domain, difficulty, response,
                     score, kw_score, sentiers, nitzotzot, duration, is_novel,
                     json.dumps(sy_compact) if sy_compact else None,
                     daat_applied, tier),
                )
                cur.close()
        except Exception as e:
            log.warning("DB record question failed: %s", e)

    # ── SSE ────────────────────────────────────────────────

    @staticmethod
    def _emit(event_type: str, **data):
        """Émettre un événement SSE pour le World Temple 3D."""
        try:
            from web.events import emit as _emit
            _emit(event_type, **data)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    # ── History / CLI helpers ──────────────────────────────

    def get_history(self, limit: int = 20) -> list[dict]:
        """Historique des sessions récentes."""
        try:
          with self._db() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, started_at, n_questions, difficulty, avg_score, "
                "domains_tested, soul_level_before, soul_level_after "
                "FROM hitbonenut_sessions ORDER BY started_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
            cur.close()
            return [
                {
                    "session_id": str(r[0]),
                    "started_at": str(r[1]),
                    "n_questions": r[2],
                    "difficulty": r[3],
                    "avg_score": r[4],
                    "domains": r[5] or [],
                    "soul_before": r[6],
                    "soul_after": r[7],
                }
                for r in rows
            ]
        except Exception as e:
            log.warning("get_history failed: %s", e)
            return []

    # ── Exploration des opposés via le Cube ──────────────────

    # Les 12 sens du Cube = 12 angles d'attaque pour questionner un sujet
    _SENSE_ANGLES: dict[str, str] = {
        "vue": "Observe ce sujet — que vois-tu ?",
        "ouïe": "Écoute ce sujet — qu'entends-tu ?",
        "odorat": "Flaire ce sujet — que sens-tu ?",
        "parole": "Exprime ce sujet — comment le formuler ?",
        "goût": "Goûte ce sujet — quelle saveur ?",
        "action": "Agis sur ce sujet — que faire concrètement ?",
        "mouvement": "Mets ce sujet en mouvement — où va-t-il ?",
        "marche": "Parcours ce sujet — quel chemin ?",
        "sommeil": "Laisse reposer ce sujet — que révèle le silence ?",
        "colère": "Confronte ce sujet — qu'est-ce qui résiste ?",
        "pensée": "Pense ce sujet — quelle structure ?",
        "méditation": "Contemple ce sujet — quelle profondeur ?",
    }

    def exploration_opposites(self, last_letter: str | None = None) -> dict:
        """Générer un angle d'exploration basé sur les opposés du Cube.

        Si la dernière question portait sur "sagesse" (Beth/dagesh),
        la prochaine explore "folie" (Beth/rafeh). Utilise les 7 doubles
        et leurs paires d'opposés comme moteur d'exploration dialectique.

        Args:
            last_letter: la lettre de la dernière question (ex: "beth").
                         Si None, choisit aléatoirement parmi les doubles.

        Returns:
            dict avec: letter, opposite_from, opposite_to, sense_angle, prompt_hint.
        """
        from kabbalah.cube_of_space import CubeOfSpace
        cube = CubeOfSpace()

        doubles = cube.get_letters_by_class("double")

        if last_letter and last_letter in doubles:
            letter = last_letter
        else:
            letter = random.choice(doubles)

        opposites = cube.get_opposites(letter)
        pos = cube.get_position(letter)

        # Trouver un sens (simple adjacente) pour l'angle d'attaque
        sense_angle = None
        sense_prompt = ""
        if pos.cube_role in ("face", "center"):
            adjacent = cube.get_adjacent_edges(letter)
            if adjacent:
                edge_letter = random.choice(adjacent)
                edge_pos = cube.get_position(edge_letter)
                if edge_pos.sense and edge_pos.sense in self._SENSE_ANGLES:
                    sense_angle = edge_pos.sense
                    sense_prompt = self._SENSE_ANGLES[edge_pos.sense]

        # Construire le hint pour la génération de question
        if opposites:
            prompt_hint = (
                f"Explore la tension entre {opposites[0]} et {opposites[1]} "
                f"(lettre {letter}, {pos.planet or pos.direction})."
            )
            if sense_prompt:
                prompt_hint += f" Angle: {sense_prompt}"
        else:
            prompt_hint = f"Explore la lettre {letter}."

        return {
            "letter": letter,
            "opposite_from": opposites[0] if opposites else None,
            "opposite_to": opposites[1] if opposites else None,
            "sense_angle": sense_angle,
            "prompt_hint": prompt_hint,
        }

    def get_status(self) -> dict:
        """État actuel du Hitbonenut."""
        progress = self.assess_progress()
        return {
            "sessions_total": progress.sessions_count,
            "soul_level": progress.soul_level,
            "overall_competence": progress.overall_competence,
            "domain_scores": progress.current_scores,
            "stagnant_domains": progress.stagnant_domains,
            "improving_domains": progress.improving_domains,
            "corpus_size": sum(
                len(qs)
                for d in self.corpus.values()
                if isinstance(d, dict)
                for qs in d.values()
                if isinstance(qs, list)
            ),
        }
