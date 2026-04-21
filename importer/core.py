"""Importer — Chesed-de-Yesod : nourrir EpisteMemory avec des sources externes.

חֶסֶד שֶׁבְּיְסוֹד — L'expansion (Chesed) dans la fondation (Yesod).
Recevoir la connaissance du monde extérieur et la stocker
avec métadonnées épistémiques, classification, et détection de doublons.

Usage:
    engine = ImportEngine(yesod=epistememory_instance)
    result = engine.import_book("traite_astrologie.pdf")
    result = engine.import_url("https://...")
    result = engine.import_youtube("https://youtube.com/watch?v=...")
"""

from __future__ import annotations

import hashlib
import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal
from uuid import UUID


# ─── Data Classes ───────────────────────────────────────────

SourceType = Literal["book", "url", "youtube", "site"]

CONFIDENCE_MAP: dict[SourceType, float] = {
    "book": 0.7,       # Livre = source fiable
    "url": 0.5,        # Article web = moins vérifié
    "youtube": 0.4,    # Vidéo = non vérifié
    "site": 0.5,       # Site crawlé = même confiance qu'un article
}

SEPHIRAH_MAP: dict[SourceType, str] = {
    "book": "chesed",
    "url": "chesed",
    "youtube": "chesed",
    "site": "chesed",
}


@dataclass
class Chunk:
    """Un morceau de texte extrait d'une source."""
    text: str
    index: int
    source_title: str = ""
    source_path: str = ""
    section_title: str = ""
    page_or_time: str = ""


@dataclass
class DuplicateInfo:
    """Doublon potentiel détecté dans EpisteMemory."""
    existing_id: UUID
    existing_content: str
    similarity: float
    is_contradiction: bool = False
    contradiction_detail: str = ""


@dataclass
class ChunkResult:
    """Résultat de l'import d'un chunk."""
    chunk_index: int
    memory_id: UUID | None = None
    subdomain: str = ""
    tags: list[str] = field(default_factory=list)
    duplicates: list[DuplicateInfo] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class ImportResult:
    """Résultat global d'un import."""
    source_type: SourceType
    source_path: str
    source_title: str
    total_chunks: int
    imported: int
    skipped: int
    duplicates_found: int
    contradictions_found: int
    subdomains: dict[str, int] = field(default_factory=dict)
    chunk_results: list[ChunkResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ─── Classification prompt (Binah) ─────────────────────────

CLASSIFY_PROMPT = """Tu es un classificateur expert en astrologie érudite.

Analyse ce texte et retourne EXACTEMENT deux lignes :
1. Le sous-domaine principal (UN SEUL parmi cette liste) :
   natale, horaire, mondiale, kabbalistique, medicale, electionnelle, meteorologique, agricole, hermetique, indienne, chinoise, arabe, hellenistique, histoire, technique, philosophique, generale
2. Les tags pertinents séparés par des virgules (3-7 tags max)

Texte :
{text}

Sous-domaine :
Tags :"""

CONTRADICTION_PROMPT = """Compare ces deux textes sur l'astrologie.
Sont-ils contradictoires ? Répondre UNIQUEMENT par "OUI" ou "NON" suivi d'une explication en une phrase.

Texte existant :
{existing}

Nouveau texte :
{new}

Contradictoire :"""


# ─── Extractors ─────────────────────────────────────────────

def extract_pdf(path: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Extraire le texte d'un PDF. Retourne (titre, texte_brut, [(page_label, texte)])."""
    import fitz  # PyMuPDF

    doc = fitz.open(path)
    title = doc.metadata.get("title", "") or Path(path).stem
    pages = []
    for i, page in enumerate(doc):
        text = page.get_text("text")
        if text.strip():
            pages.append((f"p.{i+1}", text))
    doc.close()
    full_text = "\n\n".join(t for _, t in pages)
    return title, full_text, pages


def extract_epub(path: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Extraire le texte d'un EPUB. Retourne (titre, texte_brut, [(chapitre, texte)])."""
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup

    book = epub.read_epub(path, options={"ignore_ncx": True})
    title = book.get_metadata("DC", "title")
    title = title[0][0] if title else Path(path).stem

    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        if len(text.strip()) > 50:
            # Tenter d'extraire le titre du chapitre
            heading = soup.find(["h1", "h2", "h3"])
            ch_title = heading.get_text(strip=True) if heading else item.get_name()
            chapters.append((ch_title, text))

    full_text = "\n\n".join(t for _, t in chapters)
    return title, full_text, chapters


def extract_url(url: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Extraire le contenu d'un article web."""
    import trafilatura

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError(f"Impossible de télécharger : {url}")

    result = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
        output_format="txt",
    )
    if not result:
        raise ValueError(f"Aucun contenu extractible depuis : {url}")

    # Titre
    metadata = trafilatura.extract(downloaded, output_format="xmltei")
    title = url  # fallback
    if metadata:
        import re as _re
        m = _re.search(r"<title[^>]*>([^<]+)</title>", metadata)
        if m:
            title = m.group(1)

    # Pas de sections structurées pour le web — on les créera au chunking
    return title, result, [("article", result)]


def extract_youtube(url: str) -> tuple[str, str, list[tuple[str, str]]]:
    """Extraire la transcription d'une vidéo YouTube."""
    from youtube_transcript_api import YouTubeTranscriptApi

    # Extraire l'ID vidéo
    video_id = _extract_youtube_id(url)
    if not video_id:
        raise ValueError(f"ID YouTube non trouvé dans : {url}")

    # Tenter les transcriptions dans cet ordre
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    transcript = None

    # Préférer les transcriptions manuelles en français ou anglais
    for lang in ["fr", "en"]:
        try:
            transcript = transcript_list.find_transcript([lang])
            break
        except Exception:
            continue

    # Fallback : auto-générée
    if transcript is None:
        try:
            transcript = transcript_list.find_generated_transcript(["fr", "en"])
        except Exception:
            # Dernière tentative : n'importe quelle langue
            for t in transcript_list:
                transcript = t
                break

    if transcript is None:
        raise ValueError(f"Aucune transcription disponible pour : {url}")

    entries = transcript.fetch()

    # Regrouper par segments de ~5 minutes
    segments = []
    current_segment = []
    segment_start = 0.0

    for entry in entries:
        start = entry.get("start", entry.get("offset", 0))
        text = entry.get("text", entry.get("value", ""))
        if not current_segment:
            segment_start = start

        current_segment.append(text)

        # Nouveau segment toutes les ~300 secondes (5 min)
        if start - segment_start >= 300:
            time_label = _format_time(segment_start)
            segments.append((time_label, " ".join(current_segment)))
            current_segment = []

    # Dernier segment
    if current_segment:
        time_label = _format_time(segment_start)
        segments.append((time_label, " ".join(current_segment)))

    full_text = "\n\n".join(t for _, t in segments)
    title = f"YouTube: {video_id}"

    # Tenter de récupérer le vrai titre via les métadonnées
    try:
        import requests
        resp = requests.get(
            f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json",
            timeout=10,
        )
        if resp.ok:
            title = resp.json().get("title", title)
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

    return title, full_text, segments


def _extract_youtube_id(url: str) -> str | None:
    """Extraire l'ID vidéo d'une URL YouTube."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1)
    return None


def _format_time(seconds: float) -> str:
    """Formater des secondes en HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ─── Site Crawler ──────────────────────────────────────────


@dataclass
class CrawledPage:
    """Une page crawlée depuis un site."""
    url: str
    title: str
    text: str
    sections: list[tuple[str, str]]


def crawl_site(
    start_url: str,
    *,
    max_pages: int = 500,
    delay: float = 2.0,
) -> list[CrawledPage]:
    """Crawl BFS d'un site entier (même domaine), respect robots.txt.

    Extrait le contenu de chaque page via trafilatura.
    Délai entre chaque requête pour ne pas surcharger le serveur.
    """
    import time
    import urllib.robotparser
    from collections import deque
    from urllib.parse import urljoin, urlparse, urldefrag

    import trafilatura

    parsed_start = urlparse(start_url)
    base_domain = parsed_start.netloc
    scheme = parsed_start.scheme or "https"

    # ── robots.txt ───────────────────────────────────────────
    rp = urllib.robotparser.RobotFileParser()
    robots_url = f"{scheme}://{base_domain}/robots.txt"
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)  # pas de robots.txt → tout autorisé

    # ── BFS ──────────────────────────────────────────────────
    queue: deque[str] = deque([start_url])
    visited: set[str] = set()
    pages: list[CrawledPage] = []

    print(f"  Crawl de {base_domain} (max {max_pages} pages, délai {delay}s)")

    while queue and len(pages) < max_pages:
        url = queue.popleft()

        # Normaliser : retirer le fragment
        url, _ = urldefrag(url)

        if url in visited:
            continue
        visited.add(url)

        # Vérifier robots.txt
        if not rp.can_fetch("*", url):
            print(f"    [{len(pages):3d}] SKIP (robots.txt) — {url[:80]}")
            continue

        # ── Télécharger et extraire ──────────────────────────
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                continue

            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=True,
                favor_precision=True,
                output_format="txt",
            )

            if not text or len(text.strip()) < 100:
                # Page trop courte — pas de contenu utile, mais on suit les liens
                pass
            else:
                # Extraire le titre
                title = url
                metadata_xml = trafilatura.extract(downloaded, output_format="xmltei")
                if metadata_xml:
                    m = re.search(r"<title[^>]*>([^<]+)</title>", metadata_xml)
                    if m:
                        title = m.group(1)

                page = CrawledPage(
                    url=url,
                    title=title,
                    text=text,
                    sections=[("article", text)],
                )
                pages.append(page)
                print(f"    [{len(pages):3d}/{max_pages}] ✓ {title[:60]}")

            # ── Extraire les liens internes ──────────────────
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(downloaded, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                absolute = urljoin(url, href)
                abs_clean, _ = urldefrag(absolute)
                parsed = urlparse(abs_clean)

                # Même domaine + protocole http(s) + pas déjà visité
                if (
                    parsed.netloc == base_domain
                    and parsed.scheme in ("http", "https")
                    and abs_clean not in visited
                    and not parsed.path.endswith(
                        (".pdf", ".jpg", ".jpeg", ".png", ".gif",
                         ".svg", ".css", ".js", ".zip", ".mp3",
                         ".mp4", ".xml", ".json", ".rss")
                    )
                ):
                    queue.append(abs_clean)

        except Exception as e:
            print(f"    [{len(pages):3d}] ERREUR — {url[:60]} : {e}")

        # ── Délai entre requêtes ─────────────────────────────
        if queue and len(pages) < max_pages:
            time.sleep(delay)

    print(f"  Crawl terminé : {len(pages)} pages extraites sur {len(visited)} visitées")
    return pages


# ─── Chunker ────────────────────────────────────────────────

def chunk_text(
    sections: list[tuple[str, str]],
    source_title: str,
    source_path: str,
    max_chunk_size: int = 2000,
    overlap: int = 200,
) -> list[Chunk]:
    """Découper des sections en chunks de taille raisonnable.

    Stratégie :
    - Si une section fait < max_chunk_size, on la garde entière
    - Sinon, on la découpe en morceaux avec chevauchement
    - Les chunks trop petits (< 100 chars) sont fusionnés avec le suivant
    """
    chunks: list[Chunk] = []
    idx = 0

    for section_title, text in sections:
        text = text.strip()
        if not text:
            continue

        # Section assez courte → un seul chunk
        if len(text) <= max_chunk_size:
            chunks.append(Chunk(
                text=text,
                index=idx,
                source_title=source_title,
                source_path=source_path,
                section_title=section_title,
                page_or_time=section_title,
            ))
            idx += 1
            continue

        # Découpage par paragraphes d'abord
        paragraphs = re.split(r'\n\s*\n', text)
        current = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current) + len(para) + 2 <= max_chunk_size:
                current = current + "\n\n" + para if current else para
            else:
                # Sauver le chunk courant
                if current and len(current) >= 100:
                    chunks.append(Chunk(
                        text=current,
                        index=idx,
                        source_title=source_title,
                        source_path=source_path,
                        section_title=section_title,
                        page_or_time=section_title,
                    ))
                    idx += 1

                # Si le paragraphe seul est trop long, le découper
                if len(para) > max_chunk_size:
                    sub_chunks = _split_long_text(para, max_chunk_size, overlap)
                    for sc in sub_chunks:
                        chunks.append(Chunk(
                            text=sc,
                            index=idx,
                            source_title=source_title,
                            source_path=source_path,
                            section_title=section_title,
                            page_or_time=section_title,
                        ))
                        idx += 1
                    current = ""
                else:
                    # Overlap : reprendre la fin du chunk précédent
                    if current and overlap > 0:
                        tail = current[-overlap:]
                        current = tail + "\n\n" + para
                    else:
                        current = para

        # Dernier morceau
        if current and len(current) >= 100:
            chunks.append(Chunk(
                text=current,
                index=idx,
                source_title=source_title,
                source_path=source_path,
                section_title=section_title,
                page_or_time=section_title,
            ))
            idx += 1

    return chunks


def _split_long_text(text: str, max_size: int, overlap: int) -> list[str]:
    """Découper un texte long sans paragraphes en morceaux."""
    parts = []
    start = 0
    while start < len(text):
        end = start + max_size
        # Couper à un espace ou un point si possible
        if end < len(text):
            cut = text.rfind(". ", start, end)
            if cut == -1 or cut <= start:
                cut = text.rfind(" ", start, end)
            if cut > start:
                end = cut + 1
        parts.append(text[start:end].strip())
        start = max(start + 1, end - overlap)
    return parts


# ─── ImportEngine ───────────────────────────────────────────

class ImportEngine:
    """Chesed-de-Yesod — importer des sources dans EpisteMemory.

    Flux :
    1. Extraction (PDF/EPUB/web/YouTube → texte)
    2. Chunking (texte → morceaux de ~2000 chars)
    3. Classification (Binah → sous-domaine + tags)
    4. Détection de doublons (Yesod recall → similarité)
    5. Détection de contradictions (Gevurah → LLM)
    6. Stockage (Yesod remember → avec embeddings)
    """

    def __init__(
        self,
        yesod,
        duplicate_threshold: float = 0.85,
        max_chunk_size: int = 2000,
    ):
        self.yesod = yesod
        self.duplicate_threshold = duplicate_threshold
        self.max_chunk_size = max_chunk_size

    # ── API publique ─────────────────────────────────────────

    def import_book(self, path: str, domain: str = "astrologie") -> ImportResult:
        """Importer un PDF ou EPUB."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Fichier introuvable : {path}")

        ext = p.suffix.lower()
        if ext == ".pdf":
            title, full_text, sections = extract_pdf(path)
        elif ext in (".epub", ".epub3"):
            title, full_text, sections = extract_epub(path)
        else:
            raise ValueError(f"Format non supporté : {ext} (PDF ou EPUB attendu)")

        return self._process(
            source_type="book",
            source_path=path,
            source_title=title,
            sections=sections,
            domain=domain,
        )

    def import_url(self, url: str, domain: str = "astrologie") -> ImportResult:
        """Importer un article web."""
        title, full_text, sections = extract_url(url)
        return self._process(
            source_type="url",
            source_path=url,
            source_title=title,
            sections=sections,
            domain=domain,
        )

    def import_youtube(self, url: str, domain: str = "astrologie") -> ImportResult:
        """Importer une transcription YouTube."""
        title, full_text, sections = extract_youtube(url)
        return self._process(
            source_type="youtube",
            source_path=url,
            source_title=title,
            sections=sections,
            domain=domain,
        )

    def import_site(
        self,
        url: str,
        domain: str = "astrologie",
        max_pages: int = 500,
        delay: float = 2.0,
    ) -> ImportResult:
        """Importer un site entier par crawl BFS."""
        pages = crawl_site(url, max_pages=max_pages, delay=delay)

        if not pages:
            return ImportResult(
                source_type="site",
                source_path=url,
                source_title=url,
                total_chunks=0,
                imported=0,
                skipped=0,
                duplicates_found=0,
                contradictions_found=0,
                errors=["Aucune page extractible"],
            )

        # Agréger toutes les pages en un seul ImportResult
        total_result = ImportResult(
            source_type="site",
            source_path=url,
            source_title=f"Site: {url}",
            total_chunks=0,
            imported=0,
            skipped=0,
            duplicates_found=0,
            contradictions_found=0,
        )

        for i, page in enumerate(pages):
            print(f"\n  Import page {i+1}/{len(pages)} : {page.title[:60]}")
            try:
                page_result = self._process(
                    source_type="site",
                    source_path=page.url,
                    source_title=page.title,
                    sections=page.sections,
                    domain=domain,
                )
                total_result.total_chunks += page_result.total_chunks
                total_result.imported += page_result.imported
                total_result.skipped += page_result.skipped
                total_result.duplicates_found += page_result.duplicates_found
                total_result.contradictions_found += page_result.contradictions_found
                total_result.chunk_results.extend(page_result.chunk_results)
                for sub, count in page_result.subdomains.items():
                    total_result.subdomains[sub] = (
                        total_result.subdomains.get(sub, 0) + count
                    )
                total_result.errors.extend(page_result.errors)
            except Exception as e:
                total_result.errors.append(f"{page.url}: {e}")

        return total_result

    # ── Pipeline interne ─────────────────────────────────────

    def _process(
        self,
        source_type: SourceType,
        source_path: str,
        source_title: str,
        sections: list[tuple[str, str]],
        domain: str,
    ) -> ImportResult:
        """Pipeline complet : chunk → classify → dedup → store."""
        confidence = CONFIDENCE_MAP[source_type]
        sephirah = SEPHIRAH_MAP[source_type]

        # 1. Chunking
        chunks = chunk_text(
            sections=sections,
            source_title=source_title,
            source_path=source_path,
            max_chunk_size=self.max_chunk_size,
        )

        result = ImportResult(
            source_type=source_type,
            source_path=source_path,
            source_title=source_title,
            total_chunks=len(chunks),
            imported=0,
            skipped=0,
            duplicates_found=0,
            contradictions_found=0,
        )

        if not chunks:
            result.errors.append("Aucun contenu extractible")
            return result

        print(f"  Extraction : {len(chunks)} chunks depuis '{source_title}'")

        # ── SSE : import_start ──
        try:
            from web.events import emit as _emit
            _emit("import_start", title=source_title, total=len(chunks),
                  source_type=source_type)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # 2. Traiter chaque chunk
        for chunk in chunks:
            cr = self._process_chunk(chunk, domain, confidence, sephirah, source_type)
            result.chunk_results.append(cr)

            if cr.skipped:
                result.skipped += 1
            else:
                result.imported += 1

            if cr.duplicates:
                result.duplicates_found += len(cr.duplicates)

            for dup in cr.duplicates:
                if dup.is_contradiction:
                    result.contradictions_found += 1

            if cr.subdomain:
                result.subdomains[cr.subdomain] = (
                    result.subdomains.get(cr.subdomain, 0) + 1
                )

            # ── SSE : import_chunk ──
            try:
                from web.events import emit as _emit
                _emit("import_chunk", index=chunk.index, total=len(chunks),
                      imported=result.imported, skipped=result.skipped,
                      title=source_title[:60])
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # ── SSE : import_done ──
        try:
            from web.events import emit as _emit
            _emit("import_done", title=source_title,
                  imported=result.imported, skipped=result.skipped,
                  contradictions=result.contradictions_found)
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return result

    def _process_chunk(
        self,
        chunk: Chunk,
        domain: str,
        confidence: float,
        sephirah: str,
        source_type: SourceType,
    ) -> ChunkResult:
        """Traiter un chunk : classifier, vérifier, stocker."""
        cr = ChunkResult(chunk_index=chunk.index)

        # ── Binah : classification ───────────────────────────
        subdomain, tags = self._classify(chunk.text, domain)
        cr.subdomain = subdomain
        cr.tags = tags

        # ── Gevurah : détection de doublons ──────────────────
        duplicates = self._check_duplicates(chunk.text, domain)
        cr.duplicates = duplicates

        # Si doublon exact (> 0.95), skip
        for dup in duplicates:
            if dup.similarity > 0.95:
                cr.skipped = True
                cr.skip_reason = f"Doublon quasi-exact (sim={dup.similarity:.2f})"
                print(f"    [{chunk.index:3d}] SKIP — doublon (sim={dup.similarity:.2f})")
                return cr

        # ── Yesod : stockage ─────────────────────────────────
        full_domain = f"{domain}/{subdomain}" if subdomain else domain

        all_tags = list(set(
            tags
            + [source_type, subdomain]
            + ([chunk.section_title] if chunk.section_title else [])
        ))
        # Nettoyer les tags vides
        all_tags = [t for t in all_tags if t]

        source_detail = {
            "source_type": source_type,
            "source_title": chunk.source_title,
            "source_path": chunk.source_path,
            "section": chunk.section_title,
            "chunk_index": chunk.index,
            "page_or_time": chunk.page_or_time,
            "content_hash": hashlib.sha256(chunk.text.encode()).hexdigest()[:16],
        }

        try:
            memory_id = self.yesod.remember(
                content=chunk.text,
                source_sephirah=sephirah,
                confidence=confidence,
                domain=full_domain,
                tags=all_tags,
                source_detail=source_detail,
                generate_embedding=True,
            )
            cr.memory_id = memory_id

            # Marquer les contradictions détectées
            for dup in duplicates:
                if dup.is_contradiction:
                    try:
                        self.yesod.contradict(dup.existing_id, memory_id)
                    except Exception as _exc:

                        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

            status = "CONTRA" if any(d.is_contradiction for d in duplicates) else "OK"
            print(
                f"    [{chunk.index:3d}] {status:5s} "
                f"→ {full_domain:30s} "
                f"| {', '.join(all_tags[:4])}"
            )

        except Exception as e:
            cr.skipped = True
            cr.skip_reason = str(e)
            print(f"    [{chunk.index:3d}] ERR   — {e}")

        return cr

    # ── Binah : classification via Briah ─────────────────────

    def _classify(self, text: str, domain: str) -> tuple[str, list[str]]:
        """Classifier un chunk via Binah (Briah = modèle thinking du profil actif)."""
        try:
            from olamot import ollama_generate

            # Tronquer le texte pour le prompt
            sample = text[:1500] if len(text) > 1500 else text
            prompt = CLASSIFY_PROMPT.format(text=sample)

            response, _ = ollama_generate(
                "briah", prompt, timeout=60,
                kavvanah={
                    "intention": "Classifier le contenu importé selon la taxonomie sephirothique",
                    "critere_succes": "Classification correcte avec Sefirah et domaine identifiés",
                    "anti_pattern": "Ne pas forcer une classification si le contenu est hors scope",
                },
                context_items=[f"Domaine source: {domain}"],
                principles=["Taxonomie: natale, horaire, mondiale, kabbalistique, medicale, etc."],
                domain=domain,
            )
            return self._parse_classification(response)

        except Exception:
            # Fallback : classification heuristique
            return self._classify_heuristic(text)

    def _parse_classification(self, response: str) -> tuple[str, list[str]]:
        """Parser la réponse de classification de Binah."""
        lines = [l.strip() for l in response.strip().split("\n") if l.strip()]

        # Sous-domaines valides
        valid_subdomains = {
            "natale", "horaire", "mondiale", "kabbalistique", "medicale",
            "electionnelle", "meteorologique", "agricole", "hermetique",
            "indienne", "chinoise", "arabe", "hellenistique", "histoire",
            "technique", "philosophique", "generale",
        }

        subdomain = "generale"
        tags = []

        for line in lines:
            # Nettoyer les préfixes courants
            clean = line.lower()
            for prefix in ("sous-domaine :", "sous-domaine:", "subdomain:",
                           "tags :", "tags:", "1.", "2."):
                if clean.startswith(prefix):
                    clean = clean[len(prefix):].strip()
                    break

            # Chercher un sous-domaine valide
            for sd in valid_subdomains:
                if sd in clean and subdomain == "generale":
                    subdomain = sd
                    break

            # Chercher des tags (ligne avec virgules)
            if "," in clean:
                parts = [t.strip().lower().rstrip(".") for t in clean.split(",")]
                tags = [t for t in parts if t and len(t) < 40]

        return subdomain, tags[:7]

    def _classify_heuristic(self, text: str) -> tuple[str, list[str]]:
        """Classification heuristique en fallback."""
        lower = text.lower()
        keywords = {
            "natale": ["thème natal", "carte du ciel", "naissance", "ascendant",
                       "maison natale", "natal chart"],
            "horaire": ["heure", "horary", "question horaire", "horaire"],
            "mondiale": ["mundane", "mondiale", "éclipse", "conjonction",
                         "ingress", "nations"],
            "kabbalistique": ["sephir", "kabbale", "zohar", "arbre de vie",
                              "sefer yetzirah", "hébreu", "lettres hébraïques"],
            "medicale": ["médical", "maladie", "guérison", "humeurs",
                         "decumbiture", "santé"],
            "electionnelle": ["élection", "electionnelle", "moment propice",
                              "choix du moment"],
            "hermetique": ["hermé", "emeraude", "trismégiste", "alchim",
                           "hermès", "corpus hermeticum"],
            "hellenistique": ["ptolé", "vettius", "firmicus", "lots",
                              "hellenist", "antiochus"],
            "indienne": ["jyotish", "vedic", "nakshatra", "rashi", "dasha",
                         "graha", "varga"],
            "arabe": ["arabe", "arabic parts", "al-biruni", "abu ma'shar",
                      "masha'allah"],
        }

        best_match = "generale"
        best_count = 0
        found_tags = []

        for subdomain, kws in keywords.items():
            count = sum(1 for kw in kws if kw in lower)
            if count > best_count:
                best_count = count
                best_match = subdomain
                found_tags = [kw for kw in kws if kw in lower]

        return best_match, found_tags[:5]

    # ── Gevurah : détection de doublons / contradictions ─────

    def _check_duplicates(
        self, text: str, domain: str,
    ) -> list[DuplicateInfo]:
        """Chercher des doublons sémantiques dans EpisteMemory."""
        duplicates = []

        try:
            # Recherche sémantique dans Yesod
            matches = self.yesod.recall(
                query=text[:500],  # Les premiers 500 chars suffisent
                limit=3,
                min_confidence=0.0,
                domain=domain,
            )

            for match in matches:
                content = match.content if hasattr(match, "content") else str(match)
                entry_id = match.id if hasattr(match, "id") else None
                similarity = match.confidence if hasattr(match, "confidence") else 0.0

                # Seuil : si la similarité est élevée, c'est un doublon potentiel
                if similarity >= self.duplicate_threshold and entry_id:
                    dup = DuplicateInfo(
                        existing_id=entry_id,
                        existing_content=content[:300],
                        similarity=similarity,
                    )

                    # Vérifier les contradictions via le LLM
                    if similarity < 0.95:  # Pas un doublon exact → checker la contradiction
                        dup.is_contradiction, dup.contradiction_detail = (
                            self._check_contradiction(content, text, domain)
                        )

                    duplicates.append(dup)

        except Exception as _exc:


            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return duplicates

    def _check_contradiction(
        self, existing_text: str, new_text: str, domain: str = "",
    ) -> tuple[bool, str]:
        """Vérifier si deux textes se contredisent via Yetzirah."""
        try:
            from olamot import ollama_generate

            prompt = CONTRADICTION_PROMPT.format(
                existing=existing_text[:500],
                new=new_text[:500],
            )
            response, _ = ollama_generate(
                "yetzirah", prompt, timeout=30,
                kavvanah={
                    "intention": "Détecter les contradictions entre le nouveau contenu et l'existant",
                    "critere_succes": "Contradictions identifiées avec sources précises",
                    "anti_pattern": "Ne pas signaler de faux positifs — une nuance n'est pas une contradiction",
                },
                context_items=[f"Comparaison dans le domaine: {domain}"] if domain else None,
                principles=["Une nuance ou complément n'est pas une contradiction"],
                domain=domain or None,
            )
            clean = response.strip().upper()

            if clean.startswith("OUI"):
                detail = response.strip()[3:].strip().lstrip(":").lstrip("-").strip()
                return True, detail or "Contradiction détectée"

        except Exception as _exc:


            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return False, ""
