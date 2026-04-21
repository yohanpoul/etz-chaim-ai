"""kabbalah/embed_initial.py — Embed all foundational concepts.

Embeds the 22 letters, 10 Sephiroth, 6 Partzufim, SelfMap domains,
and Sifrei Yesod concepts into the hybrid_embeddings table.

Usage:
    python -m kabbalah.embed_initial [--skip-ml] [--db-url URL]
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── The 22 Letters ───────────────────────────────────────────────
LETTERS = [
    ("Aleph", "א"), ("Beth", "ב"), ("Gimel", "ג"), ("Daleth", "ד"),
    ("Heh", "ה"), ("Vav", "ו"), ("Zayin", "ז"), ("Cheth", "ח"),
    ("Teth", "ט"), ("Yod", "י"), ("Kaph", "כ"), ("Lamed", "ל"),
    ("Mem", "מ"), ("Nun", "נ"), ("Samekh", "ס"), ("Ayin", "ע"),
    ("Peh", "פ"), ("Tsadi", "צ"), ("Qoph", "ק"), ("Resh", "ר"),
    ("Shin", "ש"), ("Tav", "ת"),
]

# ── The 10 Sephiroth ────────────────────────────────────────────
SEPHIROTH = [
    ("Keter", "כתר"), ("Chokmah", "חכמה"), ("Binah", "בינה"),
    ("Chesed", "חסד"), ("Gevurah", "גבורה"), ("Tiferet", "תפארת"),
    ("Netzach", "נצח"), ("Hod", "הוד"), ("Yesod", "יסוד"),
    ("Malkuth", "מלכות"),
]

# ── The 6 Partzufim ──────────────────────────────────────────────
PARTZUFIM = [
    ("Arikh Anpin", "אריך"), ("Abba", "אבא"), ("Imma", "אמא"),
    ("Zeir Anpin", "זעיר"), ("Nukva", "נוקבא"),
    ("Adam Kadmon", "אדם"),
]

# ── Core kabbalistic concepts ───────────────────────────────────
CORE_CONCEPTS = [
    ("Tsimtsum", "צמצום"), ("Shevirah", "שבירה"), ("Tikkun", "תיקון"),
    ("Ein Sof", "אינסוף"), ("Ohr", "אור"), ("Kav", "קו"),
    ("Reshimu", "רשימו"), ("Klipah", "קליפה"), ("Nitzotz", "ניצוץ"),
    ("Kavanah", "כוונה"), ("Devekut", "דבקות"), ("Hitbonenut", "התבוננות"),
    ("Tzeruf", "צירוף"), ("Gematria", "גמטריא"), ("Merkavah", "מרכבה"),
    ("Or Yashar", "אורישר"), ("Or Chozer", "אורחוזר"),
    ("Or Pnimi", "אורפנימי"), ("Or Makif", "אורמקיף"),
    ("Masakh", "מסך"), ("Zivvug", "זיווג"), ("Birur", "בירור"),
    ("Mochin", "מוחין"), ("Katnut", "קטנות"), ("Gadlut", "גדלות"),
]

# ── SelfMap domains ──────────────────────────────────────────────
SELFMAP_DOMAINS = [
    ("epistememory", "זכרון"), ("explorationengine", "חקירה"),
    ("insightforge", "תובנה"), ("causalengine", "סיבה"),
    ("dissensuengine", "מחלוקת"), ("autojudge", "משפט"),
    ("selfmodel", "עצמי"), ("selfmap", "מפה"),
    ("hitbonenut", "התבוננות"),
]


def embed_all(skip_ml: bool = False, db_url: str | None = None) -> dict:
    """Embed all foundational concepts. Returns stats dict."""
    from kabbalah.hybrid_embedding import HybridEmbedding

    he = HybridEmbedding(db_url=db_url)
    stats = {"letters": 0, "sephiroth": 0, "partzufim": 0,
             "core": 0, "selfmap": 0, "sifrei_yesod": 0, "total": 0}

    all_vectors = []

    # Letters
    for name, hebrew in LETTERS:
        vec = he.embed(f"Letter {name}", hebrew_word=hebrew, skip_ml=skip_ml)
        all_vectors.append(vec)
        stats["letters"] += 1
    logger.info("Embedded %d letters", stats["letters"])

    # Sephiroth
    for name, hebrew in SEPHIROTH:
        vec = he.embed(f"Sephirah {name}", hebrew_word=hebrew, skip_ml=skip_ml)
        all_vectors.append(vec)
        stats["sephiroth"] += 1
    logger.info("Embedded %d sephiroth", stats["sephiroth"])

    # Partzufim
    for name, hebrew in PARTZUFIM:
        vec = he.embed(f"Partzuf {name}", hebrew_word=hebrew, skip_ml=skip_ml)
        all_vectors.append(vec)
        stats["partzufim"] += 1
    logger.info("Embedded %d partzufim", stats["partzufim"])

    # Core concepts
    for name, hebrew in CORE_CONCEPTS:
        vec = he.embed(name, hebrew_word=hebrew, skip_ml=skip_ml)
        all_vectors.append(vec)
        stats["core"] += 1
    logger.info("Embedded %d core concepts", stats["core"])

    # SelfMap domains
    for name, hebrew in SELFMAP_DOMAINS:
        vec = he.embed(f"Domain {name}", hebrew_word=hebrew, skip_ml=skip_ml)
        all_vectors.append(vec)
        stats["selfmap"] += 1
    logger.info("Embedded %d selfmap domains", stats["selfmap"])

    # Sifrei Yesod concepts from DB — pool (audit cycle 4, C5)
    try:
        from pool import get_conn, init_pool
        db = db_url or (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))
        init_pool(db)
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT concept_id, nom_he, nom_fr
                    FROM sifrei_yesod_concepts
                    ORDER BY concept_id
                """)
                for row in cur.fetchall():
                    concept_id, nom_he, nom_fr = row
                    label = nom_fr or concept_id
                    hebrew = nom_he
                    vec = he.embed(label, hebrew_word=hebrew, skip_ml=skip_ml)
                    all_vectors.append(vec)
                    stats["sifrei_yesod"] += 1
        logger.info("Embedded %d sifrei_yesod concepts", stats["sifrei_yesod"])
    except Exception as e:
        logger.warning("Could not load sifrei_yesod concepts: %s", e)

    stats["total"] = sum(v for k, v in stats.items() if k != "total")

    # Save to DB
    try:
        saved = he.save_batch_to_db(all_vectors)
        logger.info("Saved %d/%d vectors to DB", saved, stats["total"])
    except Exception as e:
        logger.warning("Could not save to DB: %s", e)

    return stats


def main():
    parser = argparse.ArgumentParser(description="Embed foundational concepts")
    parser.add_argument("--skip-ml", action="store_true",
                        help="Skip ML embeddings (kabbalistic only)")
    parser.add_argument("--db-url", default=None,
                        help="PostgreSQL URL (default: ETZ_CHAIM_DB env)")
    args = parser.parse_args()

    stats = embed_all(skip_ml=args.skip_ml, db_url=args.db_url)
    print(f"\nEmbedded {stats['total']} concepts:")
    for k, v in stats.items():
        if k != "total":
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
