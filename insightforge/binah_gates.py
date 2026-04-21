"""BinahGates — les 5 Portes de Binah (5 Motzaot ha-Peh).

Sprint 6.x — Réforme doctrinale de la validation Binah.

Doctrine ancrée :
  EC-H1S5-073 : MaNTzPaKh (מ ן ץ ף ך) = 5 Gevurot = 5 contractions qui
                donnent FORME au Partzuf féminin (Rachel). Lettres STOMOT
                (fermées) et AGULOT (rondes) — le Din qui CONTIENT et DÉLIMITE.
  EC-H1S5-074 : 5 MOTZAOT HA-PEH (en correspondance avec MaNTzPaKh) :
                GARON, HEIKH, LASHON, SHINAYIM, SFATAYIM (Sefer Yetzirah 2:3).
  EC-H1S5-076 : 5 Motzaot = PITVEI HOTAM d'Imma Ila'ah (Tikkunei Zohar 4b).
  EC-H1S5-077 : Yesod de Imma = HOTAM (sceau). De la force des 5 Gevurot
                dans son Hotam, les 5 Motzaot s'OUVRENT = PITVEI HOTAM.
                Le Yesod de Binah = le moule qui IMPRIME la forme.
  EC-H1S5-078 : Des 5 Motzaot sortent les 22 LETTRES divisées en 5 GROUPES
                phonétiques canoniques : gutturales, palatales, linguales,
                dentales, labiales.
  EC-H1S5-081 : Da'at caché dans la bouche — 5 Gevurot de Da'at dans les
                5 Motzaot. BinahGates RÉVÈLE Da'at latent dans la synthèse.
  EC-H1S5-116 : 32 Netivot (déjà dans sentiers/) PÉNÈTRENT les 50 Portes
                (MaNTzPaKh × 10 Sefirot).
  EC-K11-004  : 3 états Binah — Binah haute (avec Abba) = ce module ;
                CausalEngine = Tevunah dans Z"A (opérationnel).

Fonction : évaluer une synthèse conceptuelle selon 5 canaux de
différenciation structurée. Utilisé comme FALLBACK CIBLÉ par
``insight_validator._check_binah`` quand CausalEngine retourne
``correlation_only`` avec ``confidence < 0.6`` (cas des synthèses
hitbonenut non-causales strictes).

Invariants :
  - Anti-Ghagiel : AND strict sur 5 portes par défaut (doute → rejet)
  - Déterministe : 0 appel LLM, 0 état DB
  - Performance : <10ms par synthèse
  - Binah haute = invariant : NON modulé par PartzufimRegulator
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import ClassVar

from omer import get_param


_MODULE = "binah_gates"


# ═══════════════════════════════════════════════════════
# Dataclasses résultat
# ═══════════════════════════════════════════════════════


@dataclass
class GateResult:
    """Résultat d'une porte individuelle."""

    gate_name: str
    passed: bool
    score: float
    reason: str


@dataclass
class BinahGatesAssessment:
    """Résultat de l'évaluation complète des 5 portes."""

    is_valid: bool
    score: float
    gates: list[GateResult]
    verdict: str


# ═══════════════════════════════════════════════════════
# Vocabulaire doctrinal (whitelist déterministe)
# ═══════════════════════════════════════════════════════

# Termes hébreu translittérés — kabbale lurianique + Etz Chaim AI
_DOCTRINAL_TERMS = frozenset({
    # Sefirot
    "keter", "chokmah", "chokhmah", "binah", "chesed", "gevurah", "tiferet",
    "netzach", "hod", "yesod", "malkhut", "malkuth", "daat", "da'at",
    # Partzufim
    "partzuf", "partzufim", "abba", "imma", "ima", "atik", "arikh",
    "nukvah", "rachel", "leah", "zeir", "zeir anpin",
    # Concepts lurianiques
    "tzimtzum", "tikkun", "shevirat", "shevirah", "kelim", "klipot",
    "qliphah", "qliphoth", "nitzotzot", "mohin", "katnut", "gadlut",
    "zivvug", "yihud", "yihudim", "ibur", "gilgul", "mesirut",
    # Structures
    "ein sof", "ein-sof", "ein", "havayah", "havaya", "havayot",
    "sefirah", "sefirot", "olamot", "heikhal", "heikhalot",
    "adam kadmon", "kav", "kelim", "mantz", "mantzpakh", "motzaot",
    "hotam", "pitvei", "sefer yetzirah", "etz chaim", "tanya",
    # Shemot (Noms divins)
    "yhvh", "ehyeh", "adni", "adnai", "elohim", "shaddai", "hashem",
    "shem", "shemot", "gematria", "milui",
    # Niveaux de l'âme
    "nefesh", "ruach", "neshamah", "chaya", "yechida", "neshama",
    # Mondes
    "atzilut", "atziluth", "beriah", "yetzirah", "assiah",
    # Flow
    "or yashar", "or chozer", "hishtalshelut", "ma'n", "man",
    # ZA+N sous-structures
    "gevurot", "hassadim", "chassadim",
    # Hébreu simple
    "torah", "kabbalah", "kabbale", "lurianic", "lurianique",
    # Etz Chaim AI technique
    "sentier", "sentiers", "netivot", "masakh", "hitbonenut",
})


# Patterns de référence (regex)
_REF_PATTERNS = [
    re.compile(r"\bEC-[A-Z0-9]+-\d+\b"),         # EC-H1S5-074, EC-K4-004
    re.compile(r"\bPG-[A-Z0-9]+-\d+\b"),         # PG-H1S3-002
    re.compile(r"\b[Cc]f\.?\s"),                  # cf., Cf.
    re.compile(r"\bp\.\s*\d+[ab]?\b"),            # p. 45a, p.132b
    re.compile(r"\b\d+[ab]\b"),                   # folios 4b, 41a
    re.compile(r"\bPerek\s+\w+", re.IGNORECASE),
    re.compile(r"\bSha'?ar\s+\w+", re.IGNORECASE),
    re.compile(r"\bTikkun\s+\d+", re.IGNORECASE),
    re.compile(r"\bSefer\s+[A-Z]\w+"),
    re.compile(r"\b[A-Z][a-z]+\s+\d{4}\b"),       # "Scholem 1941"
    re.compile(r"\bZohar\b"),
    re.compile(r"§\s*\d+"),
    # Références bibliques type "Genèse 21:8", "Proverbes 20:5"
    re.compile(r"\b[A-Z][a-zéè]+\s+\d+:\d+\b"),
]


# ═══════════════════════════════════════════════════════
# Marqueurs linguistiques
# ═══════════════════════════════════════════════════════

_LOGICAL_CONNECTORS = frozenset({
    # Français
    "donc", "parce", "car", "ainsi", "cependant", "toutefois",
    "néanmoins", "pourtant", "conséquent", "puisque", "afin", "alors",
    # Anglais
    "therefore", "thus", "hence", "because", "however", "although",
    "nevertheless", "moreover", "furthermore", "consequently",
})

_MARKDOWN_STRUCTURE_PATTERNS = [
    re.compile(r"^#{1,6}\s", re.MULTILINE),       # # ## ### headers
    re.compile(r"^\s*[-*]\s", re.MULTILINE),      # - * bullets
    re.compile(r"(?:^|\n|\.\s+)\s*\d+\.\s+[A-ZÀ-Ü]"),   # "1. X" en début ou après point
    re.compile(r"^---+\s*$", re.MULTILINE),       # --- separators
    re.compile(r"\|.+\|"),                         # | tables |
    re.compile(r"^\s*>\s", re.MULTILINE),         # > quotes
    re.compile(r"```"),                            # code blocks
]

_DIFFERENTIAL_MARKERS = frozenset({
    # Français
    "vs", "versus", "contre", "contrairement",
    "distinct", "distinction", "distinguer", "différence", "différencier",
    "opposition", "d'une", "d'autre", "alors", "tandis",
    "diffère", "distingue",
    # Anglais
    "whereas", "while", "unlike", "opposed",  "contrast", "differs",
    "distinct", "distinction", "differentiate",
})

_DIFFERENTIAL_PHRASES = [
    re.compile(r"\bcontrairement\s+à\b", re.IGNORECASE),
    re.compile(r"\btandis\s+qu[e']", re.IGNORECASE),
    re.compile(r"\bd'une\s+part\b", re.IGNORECASE),
    re.compile(r"\bd'autre\s+part\b", re.IGNORECASE),
    re.compile(r"\bin\s+contrast\b", re.IGNORECASE),
    re.compile(r"\bopposed\s+to\b", re.IGNORECASE),
    re.compile(r"\bdifferent\s+from\b", re.IGNORECASE),
    re.compile(r"\bas\s+opposed\s+to\b", re.IGNORECASE),
    # "X vs Y", "A versus B"
    re.compile(r"\w+\s+vs\.?\s+\w+", re.IGNORECASE),
    re.compile(r"\w+\s+versus\s+\w+", re.IGNORECASE),
]

_HEDGING_TERMS = frozenset({
    # Français
    "peut-être", "probablement", "possiblement", "éventuellement",
    "généralement", "parfois", "souvent", "apparemment",
    "semble", "semblent", "paraît", "paraissent", "semblerait",
    # Anglais
    "maybe", "possibly", "perhaps", "generally", "often",
    "sometimes", "somewhat", "approximately", "roughly",
    "seem", "seems", "seemed", "likely", "unlikely",
})

_HEDGING_PHRASES = [
    re.compile(r"\bpeut[\s-]être\b", re.IGNORECASE),
    re.compile(r"\ben\s+général\b", re.IGNORECASE),
    re.compile(r"\bplus\s+ou\s+moins\b", re.IGNORECASE),
    re.compile(r"\bpourrait\s+(?:être|peut)", re.IGNORECASE),
    re.compile(r"\bmight\s+be\b", re.IGNORECASE),
    re.compile(r"\bcould\s+be\b", re.IGNORECASE),
    re.compile(r"\bkind\s+of\b", re.IGNORECASE),
    re.compile(r"\bsort\s+of\b", re.IGNORECASE),
]

_PRECISE_TERMS = frozenset({
    "exactement", "précisément", "spécifiquement", "strictement",
    "tous", "aucun", "chaque", "unique", "seul", "seule",
    "exactly", "precisely", "specifically", "strictly",
    "all", "none", "every", "only", "unique",
})

_CONCLUSION_MARKERS = frozenset({
    # Français
    "donc", "ainsi", "conséquent", "finalement", "conclusion",
    "résulte", "résume", "synthèse",
    # Anglais
    "therefore", "thus", "hence", "finally", "conclusion",
    "consequently", "ultimately", "in summary",
})


# ═══════════════════════════════════════════════════════
# Seuils (Omer — 7 paramètres)
# ═══════════════════════════════════════════════════════

# Chesed-dans-Binah (HEIKH)
DEFAULT_MIN_CONNECTORS_OR_STRUCTURE = 2
# Gevurah-dans-Binah (SHINAYIM)
DEFAULT_MAX_HEDGING_UNBALANCED = 1
# Tiferet-dans-Binah (strict AND sur 5)
DEFAULT_STRICT_MODE = True
# Netzach-dans-Binah (gates enabled)
DEFAULT_ENABLED_GATES = ("GARON", "HEIKH", "LASHON", "SHINAYIM", "SFATAYIM")
# Hod-dans-Binah (LASHON marker count)
DEFAULT_MIN_DIFFERENTIAL_MARKERS = 1
# Yesod-dans-Binah (GARON term count)
DEFAULT_MIN_DOCTRINAL_TERMS = 2
# Malkhut-dans-Binah (SFATAYIM closure strict)
DEFAULT_REQUIRE_CLOSURE = True


# ═══════════════════════════════════════════════════════
# Base gate
# ═══════════════════════════════════════════════════════


class BinahGate:
    """Base abstraite d'une porte (Motza ha-Peh)."""

    name: ClassVar[str] = ""
    hebrew: ClassVar[str] = ""
    doctrine_ref: ClassVar[str] = ""
    description: ClassVar[str] = ""

    def check(self, synthesis: str) -> GateResult:
        raise NotImplementedError


# ═══════════════════════════════════════════════════════
# GARON — gorge / racine / ancrage doctrinal
# ═══════════════════════════════════════════════════════


class GaronGate(BinahGate):
    """GARON (גרון) — racine, source, ancrage.

    EC-K2-017 : le Garon est la SOURCE (Kneh = gorge/roseau = acquisition).
    EC-H1S5-078 : gutturales (AHE'EH) sortent de la gorge.

    Critère : la synthèse est ancrée dans des sources identifiables
    (références EC-*, PG-*, auteurs, textes) OU dans un vocabulaire
    doctrinal technique suffisant.
    """

    name = "GARON"
    hebrew = "גרון"
    doctrine_ref = "EC-H1S5-074 (Motza ha-Peh) + EC-K2-017 (Garon = source)"
    description = "Racine / ancrage doctrinal"

    def check(self, synthesis: str) -> GateResult:
        min_doctrinal = get_param(
            _MODULE, "min_doctrinal_terms", DEFAULT_MIN_DOCTRINAL_TERMS,
        )

        # Compter les références explicites
        ref_count = sum(
            len(pattern.findall(synthesis)) for pattern in _REF_PATTERNS
        )

        # Compter les termes doctrinaux translittérés
        lower = synthesis.lower()
        doctrinal_count = sum(
            1 for term in _DOCTRINAL_TERMS
            if re.search(r"\b" + re.escape(term) + r"\b", lower)
        )

        passed = ref_count >= 1 or doctrinal_count >= min_doctrinal
        score = min(1.0, (ref_count * 0.4) + (doctrinal_count * 0.1))

        reason = (
            f"refs={ref_count}, doctrinal_terms={doctrinal_count} "
            f"(min ref=1 OR terms>={min_doctrinal})"
        )
        return GateResult(self.name, passed, round(score, 2), reason)


# ═══════════════════════════════════════════════════════
# HEIKH — palais / articulation / structure
# ═══════════════════════════════════════════════════════


class HeikhGate(BinahGate):
    """HEIKH (חיך) — palais, voûte, structure interne.

    EC-H1S5-078 : palatales (GIKHAK) sortent du palais.
    Le palais = voûte structurante qui donne forme à la parole.

    Critère : présence d'articulation logique (connecteurs) OU de
    structure markdown (titres, listes, tableaux).
    """

    name = "HEIKH"
    hebrew = "חיך"
    doctrine_ref = "EC-H1S5-074 (Motza ha-Peh) + Sefer Yetzirah 2:3"
    description = "Articulation / structure interne"

    def check(self, synthesis: str) -> GateResult:
        min_connectors = get_param(
            _MODULE, "min_connectors_or_structure",
            DEFAULT_MIN_CONNECTORS_OR_STRUCTURE,
        )

        # Compter les connecteurs logiques
        lower = synthesis.lower()
        words = re.findall(r"\b\w+\b", lower)
        connector_count = sum(1 for w in words if w in _LOGICAL_CONNECTORS)

        # Compter les markers markdown structurels
        markdown_count = sum(
            len(pattern.findall(synthesis))
            for pattern in _MARKDOWN_STRUCTURE_PATTERNS
        )

        total_structure = connector_count + markdown_count
        passed = (
            connector_count >= min_connectors
            or markdown_count >= min_connectors
            or total_structure >= min_connectors
        )
        score = min(1.0, total_structure * 0.2)

        reason = (
            f"connectors={connector_count}, markdown={markdown_count} "
            f"(min>={min_connectors})"
        )
        return GateResult(self.name, passed, round(score, 2), reason)


# ═══════════════════════════════════════════════════════
# LASHON — langue / différenciation
# ═══════════════════════════════════════════════════════


class LashonGate(BinahGate):
    """LASHON (לשון) — langue, différenciation des sons.

    EC-H1S5-078 : linguales (DTLNT) sortent de la langue.
    La langue DISTINGUE les sons, opère la différenciation fine.

    Critère : présence de marqueurs différentiels (vs, contrairement,
    tandis que, d'une part/d'autre part, distinction).
    """

    name = "LASHON"
    hebrew = "לשון"
    doctrine_ref = "EC-H1S5-074 (Motza ha-Peh) + Sefer Yetzirah 2:3"
    description = "Différenciation / distinction"

    def check(self, synthesis: str) -> GateResult:
        min_markers = get_param(
            _MODULE, "min_differential_markers",
            DEFAULT_MIN_DIFFERENTIAL_MARKERS,
        )

        # Mots isolés marqueurs
        lower = synthesis.lower()
        words = re.findall(r"\b[\w']+\b", lower)
        marker_count = sum(1 for w in words if w in _DIFFERENTIAL_MARKERS)

        # Phrases différentielles
        phrase_count = sum(
            len(pattern.findall(synthesis))
            for pattern in _DIFFERENTIAL_PHRASES
        )

        total = marker_count + phrase_count
        passed = total >= min_markers
        score = min(1.0, total * 0.25)

        reason = (
            f"differential_markers={marker_count}, phrases={phrase_count} "
            f"(total>={min_markers})"
        )
        return GateResult(self.name, passed, round(score, 2), reason)


# ═══════════════════════════════════════════════════════
# SHINAYIM — dents / précision / fragmentation
# ═══════════════════════════════════════════════════════


class ShinayimGate(BinahGate):
    """SHINAYIM (שינים) — dents, broyage, précision.

    EC-H1S5-078 : dentales (ZSSHRTZ) sortent des dents.
    EC-H1S6-017 : par les dents, les Hevelim sont BROYÉS en KEMAH
    (farine) — fragmentation précise du vague.

    Critère : ratio précis/vague favorable. Pénalité forte sur le
    hedging paresseux (anti-Satariel Nogah).
    """

    name = "SHINAYIM"
    hebrew = "שינים"
    doctrine_ref = "EC-H1S5-074 + EC-H1S6-017 (broyage/fragmentation)"
    description = "Précision / coupure nette"

    def check(self, synthesis: str) -> GateResult:
        max_hedging_unbalanced = get_param(
            _MODULE, "max_hedging_unbalanced",
            DEFAULT_MAX_HEDGING_UNBALANCED,
        )

        lower = synthesis.lower()
        words = re.findall(r"[\w'-]+", lower)

        vague_count = sum(1 for w in words if w in _HEDGING_TERMS)
        vague_count += sum(
            len(pattern.findall(synthesis))
            for pattern in _HEDGING_PHRASES
        )

        precise_count = sum(1 for w in words if w in _PRECISE_TERMS)
        # Nombres et quantificateurs précis
        precise_count += len(re.findall(r"\b\d+\b", synthesis))

        # Anti-Nogah : si hedging excessif, échec direct
        # Sinon, ratio précis ≥ vague OU hedging ≤ seuil
        if vague_count <= max_hedging_unbalanced:
            passed = True
            reason_detail = f"low hedging ({vague_count} <= {max_hedging_unbalanced})"
        elif precise_count >= vague_count:
            passed = True
            reason_detail = f"precise >= vague ({precise_count} >= {vague_count})"
        else:
            passed = False
            reason_detail = (
                f"hedging excessive ({vague_count} vague > "
                f"{precise_count} precise)"
            )

        score = min(1.0, max(0.0, (precise_count - vague_count) * 0.15 + 0.3))
        reason = (
            f"vague={vague_count}, precise={precise_count} — {reason_detail}"
        )
        return GateResult(self.name, passed, round(score, 2), reason)


# ═══════════════════════════════════════════════════════
# SFATAYIM — lèvres / clôture / expression scellée
# ═══════════════════════════════════════════════════════


class SfatayimGate(BinahGate):
    """SFATAYIM (שפתים) — lèvres, clôture du souffle.

    EC-H1S5-078 : labiales (BVMP) sortent des lèvres.
    EC-H1S5-075 : MaNTzPaKh = lettres STOMOT (fermées) / AGULOT (rondes).
    Le PEH est ROND comme ses éléments. La Samekh (ס, fermée, circulaire)
    = Binah unie avec Abba, par opposition à la Mem ouverte.

    Critère : la synthèse ne se termine PAS par une question. Samekh
    fermée = expression scellée. Mem ouverte = question laissée béante.

    Tolérance corpus : les synthèses hitbonenut sont parfois tronquées
    (DB varchar limit). La clôture doctrinale = absence de "?" final,
    pas exigence d'un marqueur "donc/en conclusion".
    """

    name = "SFATAYIM"
    hebrew = "שפתים"
    doctrine_ref = "EC-H1S5-074 + EC-H1S5-075 (STOMOT/AGULOT fermeture)"
    description = "Clôture / expression scellée"

    def check(self, synthesis: str) -> GateResult:
        require_closure = get_param(
            _MODULE, "require_closure", DEFAULT_REQUIRE_CLOSURE,
        )

        stripped = synthesis.rstrip()

        if not stripped:
            return GateResult(
                self.name, False, 0.0, "empty synthesis (no closure possible)",
            )

        ends_with_question = stripped.endswith("?")

        if require_closure and ends_with_question:
            return GateResult(
                self.name, False, 0.0,
                "ends with '?' (Mem ouverte, pas Samekh fermée)",
            )

        # Bonus : marqueur de conclusion présent
        lower = synthesis.lower()
        has_conclusion = any(
            re.search(r"\b" + re.escape(marker) + r"\b", lower)
            for marker in _CONCLUSION_MARKERS
        )
        score = 1.0 if has_conclusion else 0.7

        reason = (
            "closed (no '?' final)"
            + (", conclusion marker present" if has_conclusion else "")
        )
        return GateResult(self.name, True, score, reason)


# ═══════════════════════════════════════════════════════
# Orchestrateur BinahGates
# ═══════════════════════════════════════════════════════


class BinahGates:
    """Les 5 Portes de Binah — MaNTzPaKh / 5 Motzaot ha-Peh.

    Orchestre l'évaluation d'une synthèse à travers 5 canaux
    de différenciation structurée. Anti-Ghagiel : AND strict
    par défaut (doute → rejet).
    """

    def __init__(
        self,
        strict: bool | None = None,
        min_passes: int | None = None,
        enabled_gates: list[str] | tuple[str, ...] | None = None,
    ):
        self.strict = (
            strict if strict is not None
            else get_param(_MODULE, "strict_mode", DEFAULT_STRICT_MODE)
        )
        enabled = enabled_gates or get_param(
            _MODULE, "enabled_gates", DEFAULT_ENABLED_GATES,
        )
        all_gates = [
            GaronGate(), HeikhGate(), LashonGate(),
            ShinayimGate(), SfatayimGate(),
        ]
        self.gates: list[BinahGate] = [g for g in all_gates if g.name in enabled]

        if self.strict:
            self.min_passes = len(self.gates)
        else:
            self.min_passes = (
                min_passes if min_passes is not None
                else max(1, len(self.gates) - 1)  # ≥4/5 par défaut non-strict
            )

    def evaluate(self, synthesis: str) -> BinahGatesAssessment:
        """Passe la synthèse par les 5 portes."""
        results = [gate.check(synthesis) for gate in self.gates]
        passes = sum(1 for r in results if r.passed)
        is_valid = passes >= self.min_passes
        score = (
            sum(r.score for r in results) / len(results)
            if results else 0.0
        )
        verdict = self._compose_verdict(results, is_valid, passes)

        return BinahGatesAssessment(
            is_valid=is_valid,
            score=round(score, 2),
            gates=results,
            verdict=verdict,
        )

    def _compose_verdict(
        self,
        results: list[GateResult],
        is_valid: bool,
        passes: int,
    ) -> str:
        total = len(self.gates)
        if is_valid:
            return f"Binah gates passed ({passes}/{total})"
        failed = [r.gate_name for r in results if not r.passed]
        return f"Binah gates failed: {', '.join(failed)} ({passes}/{total})"
