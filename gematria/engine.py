"""GematriaEngine — Gématria opérative.

Dans la Kabbale érudite, la gématria n'est pas un jeu de nombres —
c'est un outil de RÉVÉLATION. Quand deux mots partagent la même valeur,
c'est un signal que la Torah (ou la réalité qu'elle encode) les lie
par un canal invisible. Le Zohar (III, 223a) : "Les lettres montent
et descendent, et les nombres les connectent."

Ce module transforme le calculateur passif (shemot/language.py, Shem #26)
en un système opératif qui :
  1. Indexe automatiquement les termes hébreux rencontrés
  2. Détecte les équivalences (même valeur = connexion cachée)
  3. Crée des connexions dans ExplorationEngine
  4. Rapporte les découvertes pendant l'Ohr Chozer

Trois méthodes de calcul :
  - Standard (Mispar Gadol) : la valeur directe de chaque lettre
  - Ordinal (Mispar Siduri) : position dans l'alphabet (1-22)
  - Katan (Mispar Katan) : réduction au chiffre des unités
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

import psycopg2
import psycopg2.extras

from shemot.language import ATBASH_MAP, HEBREW_GEMATRIA, HEBREW_ORDINAL

from .hebrew_terms import TRANSLITERATION_TO_HEBREW, lookup_hebrew

psycopg2.extras.register_uuid()

# ── Regex pour détecter les mots hébreux dans un texte ──────────
_HEBREW_WORD_RE = re.compile(r"[\u0590-\u05FF]+")

# ── Regex pour détecter les termes translittérés ────────────────
# On cherche les mots connus du dictionnaire dans le texte latin
_TRANSLIT_KEYS_SORTED = sorted(TRANSLITERATION_TO_HEBREW.keys(), key=len, reverse=True)


@dataclass
class GematriaEntry:
    """Un terme indexé avec ses valeurs gématriques."""
    term_hebrew: str
    term_transliteration: str | None
    val_standard: int
    val_ordinal: int
    val_katan: int
    val_milui: int = 0
    val_katan_mispari: int = 0
    val_hakadmi: int = 0
    val_perati: int = 0
    val_meruba_haklali: int = 0
    val_musafi: int = 0
    id: UUID | None = None
    source_entry_id: UUID | None = None


@dataclass
class GematriaEquivalence:
    """Deux termes partageant la même valeur gématrique."""
    term_a: str
    translit_a: str | None
    term_b: str
    translit_b: str | None
    shared_value: int
    method: str  # cf. VALID_METHODS : standard, ordinal, katan, milui, etc.


def calc_standard(hebrew: str) -> int:
    """Calculer la gématria standard (Mispar Gadol)."""
    return sum(HEBREW_GEMATRIA.get(ch, 0) for ch in hebrew)


def calc_ordinal(hebrew: str) -> int:
    """Calculer la gématria ordinale (Mispar Siduri)."""
    return sum(HEBREW_ORDINAL.get(ch, 0) for ch in hebrew)


def calc_katan(hebrew: str) -> int:
    """Calculer la gématria Katan (réduction aux unités).

    Chaque lettre → sa valeur standard modulo 10.
    Sauf si mod 10 == 0 (pour les dizaines et centaines pures),
    on utilise le chiffre significatif.
    """
    total = 0
    for ch in hebrew:
        val = HEBREW_GEMATRIA.get(ch, 0)
        if val == 0:
            continue
        # Réduction : 1-9 → 1-9, 10-90 → 1-9, 100-900 → 1-9
        while val >= 10:
            val = sum(int(d) for d in str(val))
        total += val
    return total


# ── Milui (Mispar Gadol Mispari) — épellation des lettres ──────
# Milui de Mah (מ"ה) — le plus courant, associé à Zeir Anpin.
# Les 4 variantes (Ab/עב, Sag/סג, Mah/מה, Ban/בן) diffèrent dans
# l'épellation de ה, ו et א. Mah utilise הא et ואו.

MILUI_MAH_SPELLINGS: dict[str, str] = {
    "א": "אלף",   "ב": "בית",   "ג": "גימל",  "ד": "דלת",
    "ה": "הא",    "ו": "ואו",   "ז": "זין",   "ח": "חית",
    "ט": "טית",   "י": "יוד",   "כ": "כף",    "ל": "למד",
    "מ": "מם",    "נ": "נון",   "ס": "סמך",   "ע": "עין",
    "פ": "פא",    "צ": "צדי",   "ק": "קוף",   "ר": "ריש",
    "ש": "שין",   "ת": "תו",
    # Finales → même épellation que la forme standard
    "ך": "כף",    "ם": "מם",    "ן": "נון",   "ף": "פא",    "ץ": "צדי",
}

# Valeurs pré-calculées (gématria standard des épellations, formes NON-finales).
# Nécessaire car calc_standard attribue 500-900 aux finales, alors que la
# tradition kabbalistique utilise les valeurs standard (20-90) dans les épellations.
MILUI_MAH_VALUES: dict[str, int] = {
    "א": 111,  "ב": 412,  "ג": 83,   "ד": 434,
    "ה": 6,    "ו": 13,   "ז": 67,   "ח": 418,
    "ט": 419,  "י": 20,   "כ": 100,  "ל": 74,
    "מ": 80,   "נ": 106,  "ס": 120,  "ע": 130,
    "פ": 81,   "צ": 104,  "ק": 186,  "ר": 510,
    "ש": 360,  "ת": 406,
    # Finales
    "ך": 100,  "ם": 80,   "ן": 106,  "ף": 81,   "ץ": 104,
}

# Ordinal étendu aux finales (même position que la forme standard)
_ORDINAL_WITH_FINALS: dict[str, int] = {**HEBREW_ORDINAL}
_ORDINAL_WITH_FINALS.update({
    "ך": HEBREW_ORDINAL["כ"],  # 11
    "ם": HEBREW_ORDINAL["מ"],  # 13
    "ן": HEBREW_ORDINAL["נ"],  # 14
    "ף": HEBREW_ORDINAL["פ"],  # 17
    "ץ": HEBREW_ORDINAL["צ"],  # 18
})

# ── Al-Bam (permutation des 2 moitiés de l'alphabet) ──────────
# Les 11 premières lettres échangent avec les 11 suivantes.
# א↔ל, ב↔מ, ג↔נ, ד↔ס, ה↔ע, ו↔פ, ז↔צ, ח↔ק, ט↔ר, י↔ש, כ↔ת
ALBAM_MAP: dict[str, str] = {}
for _a, _b in zip("אבגדהוזחטיכ", "למנסעפצקרשת"):
    ALBAM_MAP[_a] = _b
    ALBAM_MAP[_b] = _a

# ── At-Bach (permutation miroir par magnitude) ────────────────
# Unités : א↔ט, ב↔ח, ג↔ז, ד↔ו | ה point fixe
# Dizaines : י↔צ, כ↔פ, ל↔ע, מ↔ס | נ point fixe
# Centaines : ק↔ת, ר↔ש
ATBACH_MAP: dict[str, str] = {"ה": "ה", "נ": "נ"}
for _a, _b in [("א", "ט"), ("ב", "ח"), ("ג", "ז"), ("ד", "ו"),
               ("י", "צ"), ("כ", "פ"), ("ל", "ע"), ("מ", "ס"),
               ("ק", "ת"), ("ר", "ש")]:
    ATBACH_MAP[_a] = _b
    ATBACH_MAP[_b] = _a

# Méthodes valides pour la recherche d'équivalences en DB
VALID_METHODS = frozenset({
    "standard", "ordinal", "katan", "milui", "katan_mispari",
    "hakadmi", "perati", "meruba_haklali", "musafi",
    "albam", "atbach",
})


def calc_milui(hebrew: str) -> int:
    """Mispar Gadol Mispari (Milui de Mah).

    Chaque lettre est épelée en toutes lettres, puis on somme
    la gématria standard de chaque épellation.
    Ex: א → אלף → 1+30+80 = 111.
    """
    return sum(MILUI_MAH_VALUES.get(ch, 0) for ch in hebrew)


def calc_katan_mispari(hebrew: str) -> int:
    """Mispar Katan Mispari (double réduction).

    Applique la réduction Katan au résultat du Milui.
    Le total Milui est réduit à un chiffre unique par sommation
    itérative des chiffres.
    """
    total = calc_milui(hebrew)
    if total == 0:
        return 0
    while total >= 10:
        total = sum(int(d) for d in str(total))
    return total


def calc_hakadmi(hebrew: str) -> int:
    """Mispar HaKadmi (triangulaire).

    Chaque lettre prend la valeur triangulaire T(n) = n*(n+1)/2
    de son ordinal. Aleph (1) = 1, Bet (2) = 3, Gimel (3) = 6, etc.
    """
    total = 0
    for ch in hebrew:
        n = _ORDINAL_WITH_FINALS.get(ch, 0)
        if n > 0:
            total += n * (n + 1) // 2
    return total


def calc_perati(hebrew: str) -> int:
    """Mispar Perati (carré).

    Chaque lettre prend le carré de sa valeur standard.
    Aleph = 1² = 1, Bet = 2² = 4, Yod = 10² = 100, Qof = 100² = 10000.
    """
    return sum(HEBREW_GEMATRIA.get(ch, 0) ** 2 for ch in hebrew)


def calc_meruba_haklali(hebrew: str) -> int:
    """Mispar HaMeruba HaKlali (carré du total).

    Gématria standard du mot entier, puis résultat élevé au carré.
    """
    return calc_standard(hebrew) ** 2


def calc_musafi(hebrew: str) -> int:
    """Mispar Musafi (standard + nombre de lettres).

    Gématria standard + le nombre de lettres hébraïques dans le mot.
    """
    letters = [ch for ch in hebrew if ch in HEBREW_GEMATRIA]
    return calc_standard(hebrew) + len(letters)


def calc_kolel(hebrew: str) -> int:
    """Kolel (standard + 1 pour le mot)."""
    v = calc_standard(hebrew)
    return v + 1 if v else 0


def calc_atbash(hebrew: str) -> int:
    """Gématria Atbash (permutation miroir de l'alphabet).

    Chaque lettre est remplacée par son miroir (א↔ת, ב↔ש, etc.),
    puis on calcule la gématria standard du résultat.
    """
    transformed = "".join(ATBASH_MAP.get(ch, ch) for ch in hebrew)
    return calc_standard(transformed)


def calc_albam(hebrew: str) -> int:
    """Gématria Al-Bam (permutation des 2 moitiés de l'alphabet).

    Les 11 premières lettres (א-כ) échangent avec les 11 suivantes (ל-ת),
    puis on calcule la gématria standard du résultat.
    """
    transformed = "".join(ALBAM_MAP.get(ch, ch) for ch in hebrew)
    return calc_standard(transformed)


def calc_atbach(hebrew: str) -> int:
    """Gématria At-Bach (permutation miroir par magnitude).

    Chaque lettre échange avec son miroir dans son groupe de magnitude :
    unités (א↔ט, ב↔ח, ג↔ז, ד↔ו), dizaines (י↔צ, כ↔פ, ל↔ע, מ↔ס),
    centaines (ק↔ת, ר↔ש). ה et נ sont des points fixes.
    """
    transformed = "".join(ATBACH_MAP.get(ch, ch) for ch in hebrew)
    return calc_standard(transformed)


def extract_hebrew_terms(text: str) -> list[tuple[str, str | None]]:
    """Extraire les termes hébreux d'un texte (hébreu direct + translittérations).

    Retourne une liste de (terme_hébreu, translittération_ou_None).
    """
    found: dict[str, str | None] = {}

    # 1. Mots hébreux directs dans le texte
    for match in _HEBREW_WORD_RE.finditer(text):
        word = match.group()
        # Filtrer les mots trop courts (prépositions, etc.)
        hebrew_letters = [ch for ch in word if ch in HEBREW_GEMATRIA or ch in HEBREW_ORDINAL]
        if len(hebrew_letters) >= 2:
            found[word] = None

    # 2. Termes translittérés connus
    text_lower = text.lower()
    for key in _TRANSLIT_KEYS_SORTED:
        # Chercher le terme comme mot entier (pas comme sous-chaîne)
        pattern = r'\b' + re.escape(key) + r'\b'
        if re.search(pattern, text_lower):
            hebrew = TRANSLITERATION_TO_HEBREW[key]
            if hebrew not in found:
                found[hebrew] = key

    return list(found.items())


def _entry_from_row(row: dict) -> GematriaEntry:
    """Construire un GematriaEntry depuis un dict DB (RealDictCursor)."""
    return GematriaEntry(
        id=row["id"],
        term_hebrew=row["term_hebrew"],
        term_transliteration=row["term_transliteration"],
        val_standard=row["val_standard"],
        val_ordinal=row["val_ordinal"],
        val_katan=row["val_katan"],
        val_milui=row.get("val_milui", 0),
        val_katan_mispari=row.get("val_katan_mispari", 0),
        val_hakadmi=row.get("val_hakadmi", 0),
        val_perati=row.get("val_perati", 0),
        val_meruba_haklali=row.get("val_meruba_haklali", 0),
        val_musafi=row.get("val_musafi", 0),
        source_entry_id=row.get("source_entry_id"),
    )


class GematriaEngine:
    """Moteur de gématria opérative.

    Indexe les termes, détecte les équivalences, crée les connexions.
    """

    def __init__(self, db_url: str) -> None:
        self.db_url = db_url
        from pool import init_pool
        init_pool(db_url)  # idempotent

    def close(self) -> None:
        pass  # pool gère

    from contextlib import contextmanager as _cm

    @_cm
    def _cursor(self, cursor_factory=None):
        """Emprunte une conn + cursor au pool."""
        from pool import get_conn
        with get_conn() as conn:
            if cursor_factory:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
            else:
                with conn.cursor() as cur:
                    yield cur

    # ── Indexation ──────────────────────────────────────────────

    def index_term(
        self,
        term_hebrew: str,
        term_transliteration: str | None = None,
        source_entry_id: UUID | None = None,
        source_snippet: str | None = None,
    ) -> GematriaEntry | None:
        """Indexer un terme hébreu avec ses 3 valeurs gématriques.

        Retourne l'entrée créée, ou None si le terme existe déjà.
        Si le terme existe, met à jour la translittération si absente.
        """
        # Calculer les 9 valeurs
        v_std = calc_standard(term_hebrew)
        v_ord = calc_ordinal(term_hebrew)
        v_kat = calc_katan(term_hebrew)
        v_mil = calc_milui(term_hebrew)
        v_km = calc_katan_mispari(term_hebrew)
        v_hak = calc_hakadmi(term_hebrew)
        v_per = calc_perati(term_hebrew)
        v_mhk = calc_meruba_haklali(term_hebrew)
        v_mus = calc_musafi(term_hebrew)

        if v_std == 0:
            return None  # pas de lettres hébraïques valides

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # UPSERT : insérer ou mettre à jour
            cur.execute(
                """INSERT INTO gematria_index
                       (term_hebrew, term_transliteration, val_standard, val_ordinal,
                        val_katan, val_milui, val_katan_mispari, val_hakadmi,
                        val_perati, val_meruba_haklali, val_musafi,
                        source_entry_id, source_content_snippet)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (term_hebrew) DO UPDATE
                       SET term_transliteration = COALESCE(
                               gematria_index.term_transliteration,
                               EXCLUDED.term_transliteration
                           ),
                           val_milui = EXCLUDED.val_milui,
                           val_katan_mispari = EXCLUDED.val_katan_mispari,
                           val_hakadmi = EXCLUDED.val_hakadmi,
                           val_perati = EXCLUDED.val_perati,
                           val_meruba_haklali = EXCLUDED.val_meruba_haklali,
                           val_musafi = EXCLUDED.val_musafi
                   RETURNING *""",
                (term_hebrew, term_transliteration, v_std, v_ord, v_kat,
                 v_mil, v_km, v_hak, v_per, v_mhk, v_mus,
                 source_entry_id, (source_snippet or "")[:200]),
            )
            row = cur.fetchone()

        return _entry_from_row(row)

    def index_content(
        self,
        content: str,
        source_entry_id: UUID | None = None,
    ) -> list[GematriaEntry]:
        """Extraire et indexer tous les termes hébreux d'un contenu.

        Appelé automatiquement par EpisteMemory.remember().
        Retourne la liste des termes nouvellement indexés.
        """
        terms = extract_hebrew_terms(content)
        entries = []
        snippet = content[:200]

        for hebrew, translit in terms:
            entry = self.index_term(
                term_hebrew=hebrew,
                term_transliteration=translit,
                source_entry_id=source_entry_id,
                source_snippet=snippet,
            )
            if entry:
                entries.append(entry)

        return entries

    # ── Recherche d'équivalences ────────────────────────────────

    def find_equivalences(
        self,
        term_hebrew: str,
        method: str = "standard",
    ) -> list[GematriaEquivalence]:
        """Trouver tous les termes partageant la même valeur gématrique.

        Args:
            term_hebrew: le terme hébreu à chercher
            method: cf. VALID_METHODS (standard, ordinal, katan, milui, etc.)
        """
        if method not in VALID_METHODS:
            method = "standard"
        col = f"val_{method}"

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT b.term_hebrew, b.term_transliteration, a.{col} AS shared_value
                    FROM gematria_index a
                    JOIN gematria_index b ON a.{col} = b.{col} AND a.id != b.id
                    WHERE a.term_hebrew = %s
                    ORDER BY b.term_hebrew""",
                (term_hebrew,),
            )
            rows = cur.fetchall()

        return [
            GematriaEquivalence(
                term_a=term_hebrew,
                translit_a=None,
                term_b=row["term_hebrew"],
                translit_b=row["term_transliteration"],
                shared_value=row["shared_value"],
                method=method,
            )
            for row in rows
        ]

    def find_all_equivalences_for_entry(
        self,
        entries: list[GematriaEntry],
    ) -> list[GematriaEquivalence]:
        """Trouver toutes les équivalences pour un ensemble de termes indexés.

        Cherche sur les 3 méthodes, priorise standard.
        """
        all_equivs: list[GematriaEquivalence] = []
        seen: set[tuple[str, str, str]] = set()

        for entry in entries:
            for method in ("standard", "ordinal", "katan"):
                equivs = self.find_equivalences(entry.term_hebrew, method=method)
                for eq in equivs:
                    key = (eq.term_a, eq.term_b, eq.method)
                    if key not in seen:
                        eq.translit_a = entry.term_transliteration
                        seen.add(key)
                        all_equivs.append(eq)

        return all_equivs

    # ── Lookup ──────────────────────────────────────────────────

    def get_term(self, term_hebrew: str) -> GematriaEntry | None:
        """Récupérer un terme indexé par sa forme hébraïque."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM gematria_index WHERE term_hebrew = %s",
                (term_hebrew,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return _entry_from_row(row)

    def lookup(self, term: str) -> GematriaEntry | None:
        """Chercher un terme par forme hébraïque OU translittération.

        Si le terme est en hébreu, cherche directement.
        Si en latin, tente la conversion via hebrew_terms.
        """
        # Vérifier si c'est de l'hébreu
        if _HEBREW_WORD_RE.search(term):
            return self.get_term(term)

        # Tenter la translittération
        hebrew = lookup_hebrew(term)
        if hebrew:
            return self.get_term(hebrew)

        # Chercher par translittération dans la DB
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM gematria_index WHERE LOWER(term_transliteration) = LOWER(%s)",
                (term,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return _entry_from_row(row)

    def list_all(self, limit: int = 100) -> list[GematriaEntry]:
        """Lister tous les termes indexés."""
        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM gematria_index ORDER BY val_standard, term_hebrew LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
        return [_entry_from_row(row) for row in rows]

    def get_equivalence_groups(self, method: str = "standard") -> list[dict]:
        """Récupérer tous les groupes d'équivalence (termes partageant une valeur)."""
        if method not in VALID_METHODS:
            method = "standard"
        col = f"val_{method}"

        with self._cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                f"""SELECT {col} AS shared_value,
                           COUNT(*) AS n_terms,
                           ARRAY_AGG(term_hebrew ORDER BY term_hebrew) AS terms_hebrew,
                           ARRAY_AGG(term_transliteration ORDER BY term_hebrew) AS terms_translit
                    FROM gematria_index
                    GROUP BY {col}
                    HAVING COUNT(*) > 1
                    ORDER BY COUNT(*) DESC, {col}""",
            )
            return [dict(row) for row in cur.fetchall()]

    # ── Indexation + connexions (point d'entrée principal) ──────

    def index_and_connect(
        self,
        content: str,
        source_entry_id: UUID | None = None,
    ) -> dict:
        """Point d'entrée principal — indexer le contenu et créer les connexions.

        Appelé par EpisteMemory.remember() après stockage.
        1. Extrait et indexe les termes hébreux
        2. Cherche les équivalences pour chaque terme
        3. Crée des connexions gematria_equivalence dans ExplorationEngine

        Retourne un rapport : {indexed: [...], equivalences: [...], connections_created: int}
        """
        entries = self.index_content(content, source_entry_id)
        if not entries:
            return {"indexed": [], "equivalences": [], "connections_created": 0}

        equivs = self.find_all_equivalences_for_entry(entries)
        n_created = 0

        for eq in equivs:
            try:
                self._create_gematria_connection(eq)
                n_created += 1
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # doublon ou erreur DB — non bloquant

        return {
            "indexed": [
                {"hebrew": e.term_hebrew, "translit": e.term_transliteration,
                 "standard": e.val_standard}
                for e in entries
            ],
            "equivalences": [
                {"a": eq.term_a, "b": eq.term_b, "value": eq.shared_value,
                 "method": eq.method}
                for eq in equivs
            ],
            "connections_created": n_created,
        }

    def _create_gematria_connection(self, eq: GematriaEquivalence) -> None:
        """Insérer une connexion gematria_equivalence dans ExplorationEngine.

        Insertion directe dans explorationengine_connections avec exploration_id=NULL
        (le schema le permet — ces connexions ne proviennent pas d'une exploration).
        """
        desc = (
            f"Équivalence gématrique ({eq.method}={eq.shared_value}) : "
            f"{eq.term_a}"
            f"{' (' + eq.translit_a + ')' if eq.translit_a else ''}"
            f" = {eq.term_b}"
            f"{' (' + eq.translit_b + ')' if eq.translit_b else ''}"
        )

        with self._cursor() as cur:
            # Vérifier qu'on n'a pas déjà cette connexion
            cur.execute(
                """SELECT 1 FROM explorationengine_connections
                   WHERE connection_type = 'gematria_equivalence'
                   AND (
                       (concept_a = %s AND concept_b = %s)
                       OR (concept_a = %s AND concept_b = %s)
                   )
                   AND description LIKE %s
                   LIMIT 1""",
                (eq.term_a, eq.term_b, eq.term_b, eq.term_a, f"%{eq.method}%"),
            )
            if cur.fetchone():
                return  # déjà créée

            cur.execute(
                """INSERT INTO explorationengine_connections
                   (exploration_id, concept_a, domain_a, concept_b, domain_b,
                    connection_type, description, novelty_score, relevance_score,
                    confidence)
                   VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    eq.term_a, "gematria",
                    eq.term_b, "gematria",
                    "gematria_equivalence",
                    desc,
                    0.7,  # novelty modérée — les équivalences gématriques sont classiques
                    0.8,  # relevance haute dans le contexte kabbalistique
                    0.9,  # confidence haute — c'est un CALCUL, pas une interprétation
                ),
            )

    # ── Calcul pur (sans DB) ────────────────────────────────────

    @staticmethod
    def calculate(term: str) -> dict[str, int | str] | None:
        """Calculer la gématria d'un terme (hébreu ou translittéré).

        Ne touche pas à la DB — calcul pur.
        Retourne None si aucune lettre hébraïque.
        """
        # Convertir si translittéré
        hebrew = term
        translit = None
        if not _HEBREW_WORD_RE.search(term):
            converted = lookup_hebrew(term)
            if not converted:
                return None
            hebrew = converted
            translit = term.lower()

        v_std = calc_standard(hebrew)
        if v_std == 0:
            return None

        # Textes permutés pour affichage
        atbash_text = "".join(ATBASH_MAP.get(ch, ch) for ch in hebrew)
        albam_text = "".join(ALBAM_MAP.get(ch, ch) for ch in hebrew)
        atbach_text = "".join(ATBACH_MAP.get(ch, ch) for ch in hebrew)
        # Épellation Milui pour affichage
        milui_detail = " + ".join(
            MILUI_MAH_SPELLINGS[ch] for ch in hebrew if ch in MILUI_MAH_SPELLINGS
        )

        return {
            "hebrew": hebrew,
            "transliteration": translit,
            # 13 méthodes de gématria
            "standard": v_std,
            "ordinal": calc_ordinal(hebrew),
            "katan": calc_katan(hebrew),
            "kolel": calc_kolel(hebrew),
            "atbash": calc_atbash(hebrew),
            "atbash_text": atbash_text,
            "milui": calc_milui(hebrew),
            "milui_detail": milui_detail,
            "katan_mispari": calc_katan_mispari(hebrew),
            "hakadmi": calc_hakadmi(hebrew),
            "perati": calc_perati(hebrew),
            "meruba_haklali": calc_meruba_haklali(hebrew),
            "musafi": calc_musafi(hebrew),
            "albam": calc_albam(hebrew),
            "albam_text": albam_text,
            "atbach": calc_atbach(hebrew),
            "atbach_text": atbach_text,
        }
