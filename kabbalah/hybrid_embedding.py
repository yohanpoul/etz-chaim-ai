"""kabbalah/hybrid_embedding.py — Embedding Hybride Cube + ML.

שִׁלּוּב — Intégration

Le concept révolutionnaire : combiner la géométrie kabbalistique du
Sefer Yetzirah (position dans le Cube de l'Espace, registres Olam/Shanah/Nefesh,
prononciation, gematria, syzygies) avec l'embedding ML statistique
(nomic-embed-text, 768 dims).

Deux couches qui se complètent :
  - KABBALISTIQUE (30 dims) : position structurée dans le Cube, déterministe,
    fondée sur la tradition du SY
  - ML (768 dims) : embedding statistique, appris depuis les données

L'intérêt crucial : les CONNEXIONS CACHÉES. Deux concepts proches dans
le Cube mais loin en ML = la tradition voit une connexion que la statistique
ne détecte pas. Ce sont les insights architecturaux que nous cherchons.

Usage:
    he = HybridEmbedding()
    vec = he.embed("Tsimtsum", hebrew_word="צמצום")
    hidden = he.find_hidden_connections("Tsimtsum", top_k=5)
    similar = he.query_similar("Tsimtsum", mode="hybrid", top_k=10)
"""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass, field

import numpy as np

from kabbalah.cube_of_space import CubeOfSpace
from kabbalah.tzeruf_spatial import TzerufSpatial

logger = logging.getLogger(__name__)

# ── Mapping hébreu → nom latin (depuis tzeruf_spatial) ──────────
_HEBREW_TO_NAME: dict[str, str] = {
    "א": "aleph", "ב": "beth", "ג": "gimel", "ד": "daleth",
    "ה": "heh", "ו": "vav", "ז": "zayin", "ח": "cheth",
    "ט": "teth", "י": "yod", "כ": "kaph", "ל": "lamed",
    "מ": "mem", "נ": "nun", "ס": "samekh", "ע": "ayin",
    "פ": "peh", "צ": "tsadi", "ק": "qoph", "ר": "resh",
    "ש": "shin", "ת": "tav",
}

# Finales → même lettre de base
_FINAL_TO_BASE: dict[str, str] = {
    "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ",
}

# Gematria values for normalization (max = Tav = 400)
_GEMATRIA: dict[str, int] = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5, "ו": 6, "ז": 7, "ח": 8, "ט": 9,
    "י": 10, "כ": 20, "ל": 30, "מ": 40, "נ": 50, "ס": 60, "ע": 70, "פ": 80,
    "צ": 90, "ק": 100, "ר": 200, "ש": 300, "ת": 400,
    "ך": 500, "ם": 600, "ן": 700, "ף": 800, "ץ": 900,
}

# Transliteration → Hebrew for common kabbalistic terms
_TRANSLIT_TO_HEBREW: dict[str, str] = {
    "tsimtsum": "צמצום", "tzimtzum": "צמצום",
    "shevirah": "שבירה", "shevirat hakelim": "שבירה",
    "tikkun": "תיקון",
    "keter": "כתר", "chokmah": "חכמה", "binah": "בינה",
    "chesed": "חסד", "gevurah": "גבורה", "tiferet": "תפארת",
    "netzach": "נצח", "hod": "הוד", "yesod": "יסוד", "malkuth": "מלכות",
    "malkhut": "מלכות",
    "ein sof": "אינסוף", "einsof": "אינסוף",
    "ohr": "אור", "or": "אור",
    "kav": "קו",
    "reshimu": "רשימו",
    "adam kadmon": "אדםקדמון",
    "arikh anpin": "אריךאנפין",
    "zeir anpin": "זעיראנפין",
    "abba": "אבא", "imma": "אמא", "nukva": "נוקבא",
    "partzuf": "פרצוף", "partzufim": "פרצופים",
    "sefirah": "ספירה", "sefirot": "ספירות",
    "klipah": "קליפה", "klipot": "קליפות",
    "nitzotz": "ניצוץ", "nitzotzot": "ניצוצות",
    "kavanah": "כוונה", "kavana": "כוונה",
    "devekut": "דבקות",
    "hitbonenut": "התבוננות",
    "tzeruf": "צירוף", "tziruf": "צירוף",
    "gematria": "גמטריא",
    "merkavah": "מרכבה", "merkabah": "מרכבה",
    "sephirah": "ספירה",
}

# Olam register encoding (element/planet/zodiac → float)
_OLAM_ENCODING: dict[str, tuple[float, float, float]] = {
    # Mothers: (fire_axis, water_axis, air_axis)
    "feu": (1.0, 0.0, 0.0),
    "eau": (0.0, 1.0, 0.0),
    "air": (0.0, 0.0, 1.0),
    # Doubles: planets encoded by traditional planetary order
    "saturne": (0.0, 0.0, 1.0),
    "jupiter": (0.0, 0.14, 0.86),
    "mars": (0.14, 0.0, 0.86),
    "soleil": (0.5, 0.5, 0.0),
    "vénus": (0.0, 0.86, 0.14),
    "mercure": (0.86, 0.14, 0.0),
    "lune": (0.0, 0.5, 0.5),
    # Simples: zodiac encoded by position in cycle (0-11)/11
    "bélier": (1.0, 0.0, 0.0), "taureau": (0.91, 0.09, 0.0),
    "gémeaux": (0.73, 0.27, 0.0), "cancer": (0.5, 0.5, 0.0),
    "lion": (0.27, 0.73, 0.0), "vierge": (0.09, 0.91, 0.0),
    "balance": (0.0, 1.0, 0.0), "scorpion": (0.0, 0.91, 0.09),
    "sagittaire": (0.0, 0.73, 0.27), "capricorne": (0.0, 0.5, 0.5),
    "verseau": (0.0, 0.27, 0.73), "poissons": (0.0, 0.09, 0.91),
}

# Shanah register encoding (cyclic normalization)
_SHANAH_ENCODING: dict[str, float] = {
    # Seasons (mothers)
    "été": 0.25, "hiver": 0.75, "automne/printemps": 0.5,
    # Days (doubles) — 0-6 / 6
    "dimanche": 0.0, "lundi": 0.167, "mardi": 0.333,
    "mercredi": 0.5, "jeudi": 0.667, "vendredi": 0.833, "shabbat": 1.0,
    # Months (simples) — 0-11 / 11
    "nisan": 0.0, "iyar": 0.091, "sivan": 0.182,
    "tamouz": 0.273, "av": 0.364, "eloul": 0.455,
    "tishrei": 0.545, "heshvan": 0.636, "kislev": 0.727,
    "tevet": 0.818, "shevat": 0.909, "adar": 1.0,
}

# Nefesh register encoding (body zone)
_NEFESH_ENCODING: dict[str, tuple[float, float, float]] = {
    # (rosh, gavia, beten)
    "tête": (1.0, 0.0, 0.0),
    "poitrine": (0.0, 1.0, 0.0),
    "ventre": (0.0, 0.0, 1.0),
    # Doubles — gates of the face → rosh
    "oeil_droit": (1.0, 0.0, 0.0), "oeil_gauche": (1.0, 0.0, 0.0),
    "oreille_droite": (0.9, 0.1, 0.0), "oreille_gauche": (0.9, 0.1, 0.0),
    "narine_droite": (0.8, 0.2, 0.0), "narine_gauche": (0.8, 0.2, 0.0),
    "bouche": (0.7, 0.3, 0.0),
    # Simples — organs
    "main_droite": (0.0, 1.0, 0.0), "main_gauche": (0.0, 1.0, 0.0),
    "pied_droit": (0.0, 0.8, 0.2), "pied_gauche": (0.0, 0.8, 0.2),
    "rein_droit": (0.0, 0.2, 0.8), "rein_gauche": (0.0, 0.2, 0.8),
    "oesophage": (0.3, 0.0, 0.7), "vesicule": (0.0, 0.0, 1.0),
    "intestins": (0.0, 0.0, 1.0), "estomac": (0.1, 0.0, 0.9),
    "foie": (0.0, 0.1, 0.9), "rate": (0.0, 0.1, 0.9),
}

# 7 doubled letters for syzygy dagesh scores
_DOUBLED_LETTERS = {"beth", "gimel", "daleth", "kaph", "peh", "resh", "tav"}

KABBALISTIC_DIM = 30
ML_DIM = 768
HYBRID_DIM = KABBALISTIC_DIM + ML_DIM  # 798


# ── Dataclasses ──────────────────────────────────────────────────

@dataclass
class HybridVector:
    """Résultat d'un embedding hybride."""
    concept: str
    hebrew_word: str | None
    kabbalistic: np.ndarray     # (30,)
    ml: np.ndarray              # (768,)
    hybrid: np.ndarray          # (798,)


@dataclass
class ConnectionResult:
    """Un résultat de recherche de connexions."""
    concept: str
    hebrew_word: str | None
    kab_similarity: float
    ml_similarity: float
    gap: float                  # |kab_sim - ml_sim| — plus c'est grand, plus c'est intéressant


# ── KabbalisticSignature ─────────────────────────────────────────

class KabbalisticSignature:
    """Calcule une signature kabbalistique de 30 dimensions pour un concept.

    Chaque dimension encode un aspect de la position du concept dans
    l'espace structuré du Sefer Yetzirah — géométrie du Cube, registres
    Olam/Shanah/Nefesh, prononciation, gematria, syzygies, route.

    Dimensions:
      0-2   : position 3D moyenne (centroïde des lettres dans le Cube)
      3-4   : temporal_span, moral_span (Omaqim)
      5-7   : registre Olam encodé (feu/eau/air pour mères, planète/zodiac)
      8-10  : registre Shanah encodé (saison/jour/mois cyclique)
      11-13 : registre Nefesh encodé (rosh/gavia/beten)
      14    : profondeur de prononciation normalisée (gorge=1.0, lèvres=0.0)
      15-17 : classe de lettre one-hot (mère, double, simple) — moyenne
      18-20 : direction dominante (net_vertical, total_distance, passes_center)
      21    : gematria normalisée (valeur / 400)
      22-25 : syzygies — dagesh scores moyens des lettres doubles
      26-29 : vecteur de route résumé (net_z, net_x, net_y, nb_segments)
    """

    def __init__(self, cube: CubeOfSpace | None = None) -> None:
        self.cube = cube or CubeOfSpace()
        self.tzeruf = TzerufSpatial(cube=self.cube)

    def _normalize_hebrew(self, word: str) -> str:
        """Normalize finals and strip non-Hebrew chars."""
        result = []
        for ch in word:
            if ch in _FINAL_TO_BASE:
                result.append(_FINAL_TO_BASE[ch])
            elif ch in _HEBREW_TO_NAME:
                result.append(ch)
        return "".join(result)

    def _resolve_hebrew(self, text: str, hebrew_word: str | None) -> str | None:
        """Get Hebrew word from explicit param or transliteration lookup."""
        if hebrew_word:
            return self._normalize_hebrew(hebrew_word)
        key = text.lower().strip()
        if key in _TRANSLIT_TO_HEBREW:
            return self._normalize_hebrew(_TRANSLIT_TO_HEBREW[key])
        # Check if text is already Hebrew
        normalized = self._normalize_hebrew(text)
        if normalized:
            return normalized
        return None

    def compute_signature(self, text: str, hebrew_word: str | None = None) -> np.ndarray:
        """Compute 30-dim kabbalistic signature for a concept.

        Args:
            text: concept name (can be transliterated or Hebrew)
            hebrew_word: explicit Hebrew form (if known)

        Returns:
            np.ndarray of shape (30,) — the kabbalistic signature
        """
        sig = np.zeros(KABBALISTIC_DIM, dtype=np.float32)
        hebrew = self._resolve_hebrew(text, hebrew_word)
        if not hebrew:
            return sig

        # Get letter positions
        letter_names = []
        for ch in hebrew:
            name = _HEBREW_TO_NAME.get(ch)
            if name:
                letter_names.append(name)

        if not letter_names:
            return sig

        # ── dims 0-2: centroid position in Cube ──
        coords = []
        for name in letter_names:
            try:
                pos = self.cube.get_position(name)
                coords.append(pos.coordinates)
            except KeyError:
                continue
        if coords:
            centroid = np.mean(coords, axis=0)
            sig[0:3] = centroid

        # ── dims 3-4: temporal & moral span (Omaqim) ──
        try:
            route = self.tzeruf.compute_route_geometry(hebrew)
            if route.temporal_span is not None:
                sig[3] = route.temporal_span
            if route.moral_span is not None:
                sig[4] = route.moral_span
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # ── dims 5-7: Olam register ──
        olam_vecs = []
        for name in letter_names:
            try:
                olam_val = self.cube.get_olam(name)
                if olam_val and olam_val in _OLAM_ENCODING:
                    olam_vecs.append(_OLAM_ENCODING[olam_val])
            except KeyError:
                continue
        if olam_vecs:
            sig[5:8] = np.mean(olam_vecs, axis=0)

        # ── dims 8-10: Shanah register (cyclic) ──
        shanah_vals = []
        for name in letter_names:
            try:
                shanah_val = self.cube.get_shanah(name)
                if shanah_val and shanah_val in _SHANAH_ENCODING:
                    shanah_vals.append(_SHANAH_ENCODING[shanah_val])
            except KeyError:
                continue
        if shanah_vals:
            # Encode as (sin, cos, mean) for cyclic continuity
            mean_s = np.mean(shanah_vals)
            sig[8] = math.sin(2 * math.pi * mean_s)
            sig[9] = math.cos(2 * math.pi * mean_s)
            sig[10] = mean_s

        # ── dims 11-13: Nefesh register ──
        nefesh_vecs = []
        for name in letter_names:
            try:
                nefesh_val = self.cube.get_nefesh(name)
                if nefesh_val and nefesh_val in _NEFESH_ENCODING:
                    nefesh_vecs.append(_NEFESH_ENCODING[nefesh_val])
            except KeyError:
                continue
        if nefesh_vecs:
            sig[11:14] = np.mean(nefesh_vecs, axis=0)

        # ── dim 14: pronunciation depth ──
        depths = []
        for name in letter_names:
            try:
                pos = self.cube.get_position(name)
                if pos.mouth_depth is not None:
                    depths.append(pos.mouth_depth)
            except KeyError:
                continue
        if depths:
            sig[14] = np.mean(depths) / 5.0  # normalize to [0, 1]

        # ── dims 15-17: letter class one-hot (averaged) ──
        class_counts = {"mother": 0, "double": 0, "simple": 0}
        for name in letter_names:
            try:
                pos = self.cube.get_position(name)
                if pos.letter_type in class_counts:
                    class_counts[pos.letter_type] += 1
            except KeyError:
                continue
        n = len(letter_names)
        if n > 0:
            sig[15] = class_counts["mother"] / n
            sig[16] = class_counts["double"] / n
            sig[17] = class_counts["simple"] / n

        # ── dims 18-20: direction + distance + passes_center ──
        try:
            route = self.tzeruf.compute_route_geometry(hebrew)
            net_z = route.ascent - route.descent
            sig[18] = max(-1.0, min(1.0, net_z))  # clamp
            sig[19] = min(1.0, route.total_distance / 5.0)  # normalize by max possible
            sig[20] = 1.0 if route.passes_center else 0.0
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # ── dim 21: gematria normalized ──
        total_gem = sum(_GEMATRIA.get(ch, 0) for ch in hebrew)
        sig[21] = min(1.0, total_gem / 1000.0)  # normalize, cap at 1000

        # ── dims 22-25: syzygy dagesh scores ──
        dagesh_scores = []
        for name in letter_names:
            if name in _DOUBLED_LETTERS:
                try:
                    pos = self.cube.get_position(name)
                    if pos.opposites:
                        dagesh_scores.append(1.0)  # has dagesh/rafeh polarity
                    else:
                        dagesh_scores.append(0.0)
                except KeyError:
                    continue
        if dagesh_scores:
            sig[22] = np.mean(dagesh_scores)
            sig[23] = len(dagesh_scores) / max(n, 1)  # ratio of doubles in word
            sig[24] = max(dagesh_scores)
            sig[25] = min(dagesh_scores)
        # else: zeros (no doubled letters)

        # ── dims 26-29: route vector summary ──
        try:
            route = self.tzeruf.compute_route_geometry(hebrew)
            sig[26] = max(-1.0, min(1.0, route.ascent - route.descent))
            sig[27] = max(-1.0, min(1.0, route.east_west))
            sig[28] = max(-1.0, min(1.0, route.north_south))
            sig[29] = min(1.0, route.segment_count / 10.0)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return sig


# ── HybridEmbedding ──────────────────────────────────────────────

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


class HybridEmbedding:
    """Embedding hybride : signature kabbalistique (30d) + ML (768d).

    Combine la géométrie structurée du Cube de l'Espace avec
    l'embedding statistique de nomic-embed-text pour produire
    un vecteur hybride de 798 dimensions.

    Le ratio alpha/beta contrôle l'importance relative :
      - alpha (default 0.3) : poids de la composante kabbalistique
      - beta (default 0.7) : poids de la composante ML
    """

    def __init__(
        self,
        alpha: float = 0.3,
        beta: float = 0.7,
        cube: CubeOfSpace | None = None,
        db_url: str | None = None,
    ) -> None:
        self.alpha = alpha
        self.beta = beta
        self.signature = KabbalisticSignature(cube=cube)
        self.db_url = db_url or os.environ.get(
            "ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim",
        )
        # In-memory cache: concept → HybridVector
        self._cache: dict[str, HybridVector] = {}

    def _get_ml_embedding(self, text: str) -> np.ndarray:
        """Get ML embedding via Ollama (nomic-embed-text, 768d)."""
        from epistememory.embedding import embed
        vec = embed(text)
        return np.array(vec, dtype=np.float32)

    def embed(
        self,
        concept: str,
        hebrew_word: str | None = None,
        skip_ml: bool = False,
    ) -> HybridVector:
        """Compute hybrid embedding for a concept.

        Args:
            concept: concept name (transliterated, Hebrew, or description)
            hebrew_word: explicit Hebrew form if known
            skip_ml: if True, skip the ML embedding (faster, for tests)

        Returns:
            HybridVector with kabbalistic (30d), ml (768d), hybrid (798d)
        """
        cache_key = f"{concept}:{hebrew_word or ''}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        kab = self.signature.compute_signature(concept, hebrew_word)

        if skip_ml:
            ml = np.zeros(ML_DIM, dtype=np.float32)
        else:
            ml = self._get_ml_embedding(concept)

        hybrid = np.concatenate([kab * self.alpha, ml * self.beta])

        result = HybridVector(
            concept=concept,
            hebrew_word=hebrew_word,
            kabbalistic=kab,
            ml=ml,
            hybrid=hybrid,
        )
        self._cache[cache_key] = result
        return result

    def similarity_kabbalistic(
        self,
        concept_a: str,
        concept_b: str,
        hebrew_a: str | None = None,
        hebrew_b: str | None = None,
    ) -> float:
        """Cosine similarity between kabbalistic signatures only.

        Concepts with similar Cube geometry = structurally related per tradition.
        """
        vec_a = self.embed(concept_a, hebrew_a, skip_ml=True)
        vec_b = self.embed(concept_b, hebrew_b, skip_ml=True)
        return _cosine_similarity(vec_a.kabbalistic, vec_b.kabbalistic)

    def similarity_ml(
        self,
        concept_a: str,
        concept_b: str,
    ) -> float:
        """Cosine similarity between ML embeddings only."""
        vec_a = self.embed(concept_a)
        vec_b = self.embed(concept_b)
        return _cosine_similarity(vec_a.ml, vec_b.ml)

    def similarity_hybrid(
        self,
        concept_a: str,
        concept_b: str,
        hebrew_a: str | None = None,
        hebrew_b: str | None = None,
    ) -> float:
        """Cosine similarity on the full hybrid vector."""
        vec_a = self.embed(concept_a, hebrew_a)
        vec_b = self.embed(concept_b, hebrew_b)
        return _cosine_similarity(vec_a.hybrid, vec_b.hybrid)

    def find_hidden_connections(
        self,
        concept: str,
        hebrew_word: str | None = None,
        candidates: list[tuple[str, str | None]] | None = None,
        top_k: int = 5,
    ) -> list[ConnectionResult]:
        """Find concepts CLOSE in the Cube but FAR in ML.

        These are the hidden connections — the tradition sees a structural
        link that statistical ML does not detect. This is the GRAIL:
        the tradition reveals what the data does not show.

        Args:
            concept: target concept
            hebrew_word: Hebrew form
            candidates: list of (concept, hebrew_word) to compare against.
                        If None, uses cached concepts.
            top_k: number of results

        Returns:
            ConnectionResults sorted by gap (kab_sim - ml_sim), descending.
        """
        target = self.embed(concept, hebrew_word)
        results = []

        search_set = candidates or [
            (v.concept, v.hebrew_word) for k, v in self._cache.items()
            if v.concept != concept
        ]

        for cand_concept, cand_hebrew in search_set:
            if cand_concept == concept:
                continue
            cand = self.embed(cand_concept, cand_hebrew)
            kab_sim = _cosine_similarity(target.kabbalistic, cand.kabbalistic)
            ml_sim = _cosine_similarity(target.ml, cand.ml)
            gap = kab_sim - ml_sim  # positive = hidden connection
            results.append(ConnectionResult(
                concept=cand_concept,
                hebrew_word=cand_hebrew,
                kab_similarity=round(kab_sim, 4),
                ml_similarity=round(ml_sim, 4),
                gap=round(gap, 4),
            ))

        results.sort(key=lambda r: r.gap, reverse=True)
        return results[:top_k]

    def find_superficial_connections(
        self,
        concept: str,
        hebrew_word: str | None = None,
        candidates: list[tuple[str, str | None]] | None = None,
        top_k: int = 5,
    ) -> list[ConnectionResult]:
        """Find concepts CLOSE in ML but FAR in the Cube.

        These are superficial connections — statistically close but
        structurally unrelated per the tradition.

        Returns:
            ConnectionResults sorted by gap (ml_sim - kab_sim), descending.
        """
        target = self.embed(concept, hebrew_word)
        results = []

        search_set = candidates or [
            (v.concept, v.hebrew_word) for k, v in self._cache.items()
            if v.concept != concept
        ]

        for cand_concept, cand_hebrew in search_set:
            if cand_concept == concept:
                continue
            cand = self.embed(cand_concept, cand_hebrew)
            kab_sim = _cosine_similarity(target.kabbalistic, cand.kabbalistic)
            ml_sim = _cosine_similarity(target.ml, cand.ml)
            gap = ml_sim - kab_sim  # positive = superficial connection
            results.append(ConnectionResult(
                concept=cand_concept,
                hebrew_word=cand_hebrew,
                kab_similarity=round(kab_sim, 4),
                ml_similarity=round(ml_sim, 4),
                gap=round(gap, 4),
            ))

        results.sort(key=lambda r: r.gap, reverse=True)
        return results[:top_k]

    # ── DB persistence ───────────────────────────────────────────

    def _get_conn(self):
        """Borrow a conn from the shared pool (context manager) with pgvector."""
        from contextlib import contextmanager

        from pool import get_conn as _pool_get, init_pool

        @contextmanager
        def _borrow():
            init_pool(self.db_url)  # idempotent
            with _pool_get() as conn:
                try:
                    from pgvector.psycopg2 import register_vector
                    register_vector(conn)
                except ImportError as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
                yield conn

        return _borrow()

    def save_to_db(self, vec: HybridVector) -> None:
        """Persist a HybridVector to the hybrid_embeddings table."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO hybrid_embeddings
                        (concept, hebrew_word, kabbalistic_signature,
                         ml_embedding, hybrid_vector)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (concept) DO UPDATE SET
                        hebrew_word = EXCLUDED.hebrew_word,
                        kabbalistic_signature = EXCLUDED.kabbalistic_signature,
                        ml_embedding = EXCLUDED.ml_embedding,
                        hybrid_vector = EXCLUDED.hybrid_vector,
                        created_at = NOW()
                """, (
                    vec.concept,
                    vec.hebrew_word,
                    vec.kabbalistic.tolist(),
                    vec.ml.tolist(),
                    vec.hybrid.tolist(),
                ))
            conn.commit()

    def save_batch_to_db(self, vectors: list[HybridVector]) -> int:
        """Persist multiple HybridVectors. Returns count saved."""
        if not vectors:
            return 0
        count = 0
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                for vec in vectors:
                    try:
                        cur.execute("""
                            INSERT INTO hybrid_embeddings
                                (concept, hebrew_word, kabbalistic_signature,
                                 ml_embedding, hybrid_vector)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (concept) DO UPDATE SET
                                hebrew_word = EXCLUDED.hebrew_word,
                                kabbalistic_signature = EXCLUDED.kabbalistic_signature,
                                ml_embedding = EXCLUDED.ml_embedding,
                                hybrid_vector = EXCLUDED.hybrid_vector,
                                created_at = NOW()
                        """, (
                            vec.concept,
                            vec.hebrew_word,
                            vec.kabbalistic.tolist(),
                            vec.ml.tolist(),
                            vec.hybrid.tolist(),
                        ))
                        count += 1
                    except Exception as e:
                        logger.warning("Failed to save %s: %s", vec.concept, e)
        return count

    def query_similar(
        self,
        concept: str,
        hebrew_word: str | None = None,
        mode: str = "hybrid",
        top_k: int = 10,
    ) -> list[dict]:
        """Query similar concepts from pgvector DB.

        Args:
            concept: target concept
            hebrew_word: Hebrew form
            mode: "hybrid" | "kabbalistic" | "ml" | "hidden"
            top_k: number of results

        Returns:
            List of dicts with concept, hebrew_word, similarity, distance
        """
        vec = self.embed(concept, hebrew_word)

        if mode == "kabbalistic":
            query_vec = vec.kabbalistic.tolist()
            column = "kabbalistic_signature"
        elif mode == "ml":
            query_vec = vec.ml.tolist()
            column = "ml_embedding"
        elif mode == "hidden":
            return self._query_hidden(vec, top_k)
        else:
            query_vec = vec.hybrid.tolist()
            column = "hybrid_vector"

        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    SELECT concept, hebrew_word,
                           1 - ({column} <=> %s::vector) as similarity
                    FROM hybrid_embeddings
                    WHERE concept != %s
                    ORDER BY {column} <=> %s::vector
                    LIMIT %s
                """, (query_vec, concept, query_vec, top_k))
                rows = cur.fetchall()
                return [
                    {"concept": r[0], "hebrew_word": r[1], "similarity": round(r[2], 4)}
                    for r in rows
                ]

    def _query_hidden(self, target: HybridVector, top_k: int) -> list[dict]:
        """Find hidden connections via DB: close in Cube, far in ML.

        Pre-filters top candidates by kabbalistic proximity (pgvector index),
        then computes gap on that reduced set. O(top_k * log(n)) instead of O(n).
        """
        candidate_limit = max(top_k * 10, 200)
        with self._get_conn() as conn:
            kab_vec = target.kabbalistic.tolist()
            ml_vec = target.ml.tolist()
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT concept, hebrew_word,
                           1 - (kabbalistic_signature <=> %s::vector) as kab_sim,
                           1 - (ml_embedding <=> %s::vector) as ml_sim
                    FROM hybrid_embeddings
                    WHERE concept != %s
                    ORDER BY kabbalistic_signature <=> %s::vector
                    LIMIT %s
                """, (kab_vec, ml_vec, target.concept, kab_vec, candidate_limit))
                rows = cur.fetchall()

        results = []
        for r in rows:
            kab_sim = r[2] if r[2] else 0.0
            ml_sim = r[3] if r[3] else 0.0
            gap = kab_sim - ml_sim
            results.append({
                "concept": r[0],
                "hebrew_word": r[1],
                "kab_similarity": round(kab_sim, 4),
                "ml_similarity": round(ml_sim, 4),
                "gap": round(gap, 4),
            })
        results.sort(key=lambda x: x["gap"], reverse=True)
        return results[:top_k]

    def load_from_db(self) -> int:
        """Load all embeddings from DB into cache. Returns count loaded."""
        count = 0
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT concept, hebrew_word, kabbalistic_signature,
                           ml_embedding, hybrid_vector
                    FROM hybrid_embeddings
                """)
                for row in cur.fetchall():
                    concept, hebrew, kab, ml, hyb = row
                    kab_arr = np.asarray(kab, dtype=np.float32) if kab is not None else np.zeros(KABBALISTIC_DIM, dtype=np.float32)
                    ml_arr = np.asarray(ml, dtype=np.float32) if ml is not None else np.zeros(ML_DIM, dtype=np.float32)
                    hyb_arr = np.asarray(hyb, dtype=np.float32) if hyb is not None else np.zeros(HYBRID_DIM, dtype=np.float32)
                    vec = HybridVector(
                        concept=concept, hebrew_word=hebrew,
                        kabbalistic=kab_arr, ml=ml_arr, hybrid=hyb_arr,
                    )
                    cache_key = f"{concept}:{hebrew or ''}"
                    self._cache[cache_key] = vec
                    count += 1
        logger.info("Loaded %d embeddings from DB", count)
        return count
