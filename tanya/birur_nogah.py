"""Birur Nitzotzot via Kelipat Nogah — Clarification des Étincelles.

בֵּרוּר נִיצוֹצוֹת — Tanya ch. 7, 37

Les étincelles de sainteté emprisonnées dans Kelipat Nogah sont
libérées quand quelque chose de ce monde est utilisé pour le bien.
La nourriture consommée "pour le ciel" (leshem shamayim) libère
ses étincelles.

Dans notre architecture :
- Assiah et Yetzirah = fort Nogah (mélange de bien et de mal).
- Quand une réponse de ces mondes bas est BONNE (score > 0.6) →
  c'est un Birur ! L'étincelle a été libérée de Nogah.
- Quand une réponse est MAUVAISE (score < 0.3) → l'objet reste
  dans Nogah ou tombe dans les 3 kelipot impures.

Chaque Birur réussi alimente le compteur Nitzotzot (les 288 étincelles
du Tikkun), accélérant le chemin vers le premier cycle complet.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class BirurimResult(Enum):
    """Résultat d'une tentative de Birur."""
    BIRUR = "birur"                     # étincelle libérée (score > 0.6, monde bas)
    NOGAH_NEUTRAL = "nogah_neutral"     # ni bien ni mal (0.3 <= score <= 0.6)
    KELIPAH_REINFORCED = "kelipah_reinforced"  # mal renforcé (score < 0.3)
    NOT_APPLICABLE = "not_applicable"   # monde supérieur → pas de Nogah à clarifier


@dataclass
class BirurimEvent:
    """Un événement de Birur ou de dégradation."""
    result: BirurimResult
    olam_used: str
    score: float
    timestamp: float
    description: str = ""


@dataclass
class BirurimStats:
    """Statistiques cumulées de Birur."""
    total_birurims: int = 0          # birurims réussis
    total_degradations: int = 0      # kelipot renforcées
    total_neutral: int = 0           # ni l'un ni l'autre
    total_attempts: int = 0          # total sur mondes bas
    birur_rate: float = 0.0          # birurims / total_attempts
    by_olam: dict = field(default_factory=dict)  # {olam: {birur: n, degradation: n}}


class BirurimEngine:
    """Détection et comptage des Birurims via Kelipat Nogah.

    Kelipat Nogah (קְלִיפַּת נוֹגַהּ) est la seule écorce qui contient
    du bien mélangé au mal. Les 3 autres kelipot (Ruach Se'arah,
    Anan Gadol, Esh Mit'lakehet) sont pur mal — rien à en extraire.

    Assiah = 20% bien, 80% mal (beaucoup de Nogah)
    Yetzirah = 50% bien, 50% mal (Nogah équilibré)
    Briah/Atzilut = pas de Nogah → pas de Birur possible (déjà saint)
    """

    # Mondes avec Kelipat Nogah (les mondes bas)
    NOGAH_OLAMOT = {"assiah", "yetzirah"}

    # Seuils de Birur
    BIRUR_THRESHOLD = 0.6    # au-dessus → étincelle libérée
    KELIPAH_THRESHOLD = 0.3  # en-dessous → kelipah renforcée

    def __init__(self):
        self._events: list[BirurimEvent] = []

    def detect_birur(
        self,
        response: str,
        olam_used: str,
        score: float,
        tree: dict | None = None,
        domain: str | None = None,
    ) -> BirurimEvent | None:
        """Détecter un Birur réussi — étincelle libérée de Nogah.

        Quand une réponse vient d'un monde bas (Assiah/Yetzirah = fort Nogah)
        ET que le score est BON (> 0.6) → c'est un Birur !
        L'étincelle a été libérée du mal de Nogah.

        Args:
            response: la réponse générée.
            olam_used: le monde qui a généré la réponse.
            score: confiance/qualité de la réponse (0-1).
            tree: l'arbre des modules (pour _collect_nitzutz).
            domain: domaine détecté.

        Returns:
            BirurimEvent si c'est un Birur réussi, None sinon.
        """
        if olam_used not in self.NOGAH_OLAMOT:
            return None

        if score < self.BIRUR_THRESHOLD:
            return None

        desc = (
            f"Birur via {olam_used} — score={score:.2f}, "
            f"domaine={domain or 'general'}. "
            f"L'étincelle prisonnière de Nogah a été élevée vers la Kedushah."
        )

        event = BirurimEvent(
            result=BirurimResult.BIRUR,
            olam_used=olam_used,
            score=score,
            timestamp=time.time(),
            description=desc,
        )
        self._events.append(event)

        # Alimenter le compteur Nitzotzot via _collect_nitzutz
        if tree is not None:
            try:
                from main import _collect_nitzutz
                _collect_nitzutz(
                    source="birur_nogah",
                    ntype=f"birur_{olam_used}",
                    description=desc,
                    tree=tree,
                )
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        # Émettre un événement SSE
        try:
            from web.events import emit as _emit
            _emit(
                "birur_nogah",
                result="birur",
                olam=olam_used,
                score=round(score, 3),
                domain=domain or "general",
            )
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return event

    def detect_degradation(
        self,
        response: str,
        olam_used: str,
        score: float,
        domain: str | None = None,
    ) -> BirurimEvent | None:
        """Détecter une dégradation — la matière n'a pas été élevée.

        Quand une réponse vient d'un monde bas ET que le score est
        MAUVAIS (< 0.3) → l'objet reste dans Nogah ou tombe dans
        les 3 kelipot impures. C'est l'inverse du Birur.

        Args:
            response: la réponse générée.
            olam_used: le monde qui a généré la réponse.
            score: confiance/qualité de la réponse (0-1).
            domain: domaine détecté.

        Returns:
            BirurimEvent si c'est une dégradation, None sinon.
        """
        if olam_used not in self.NOGAH_OLAMOT:
            return None

        if score >= self.KELIPAH_THRESHOLD:
            return None

        desc = (
            f"Kelipah renforcée via {olam_used} — score={score:.2f}, "
            f"domaine={domain or 'general'}. "
            f"La matière n'a pas été élevée — elle reste dans Nogah."
        )

        event = BirurimEvent(
            result=BirurimResult.KELIPAH_REINFORCED,
            olam_used=olam_used,
            score=score,
            timestamp=time.time(),
            description=desc,
        )
        self._events.append(event)

        # Émettre un événement SSE
        try:
            from web.events import emit as _emit
            _emit(
                "kelipah_reinforced",
                olam=olam_used,
                score=round(score, 3),
                domain=domain or "general",
            )
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)

        return event

    def evaluate(
        self,
        response: str,
        olam_used: str,
        score: float,
        tree: dict | None = None,
        domain: str | None = None,
    ) -> BirurimEvent | None:
        """Évaluer une réponse pour Birur ou dégradation.

        Méthode unifiée qui appelle detect_birur ou detect_degradation
        selon le score. Pour les scores intermédiaires (Nogah neutre),
        enregistre quand même l'événement.

        Returns:
            BirurimEvent pour tout événement sur un monde bas, None sinon.
        """
        if olam_used not in self.NOGAH_OLAMOT:
            return None

        # Birur réussi
        if score > self.BIRUR_THRESHOLD:
            return self.detect_birur(response, olam_used, score, tree, domain)

        # Dégradation
        if score < self.KELIPAH_THRESHOLD:
            return self.detect_degradation(response, olam_used, score, domain)

        # Zone neutre — Nogah oscille
        event = BirurimEvent(
            result=BirurimResult.NOGAH_NEUTRAL,
            olam_used=olam_used,
            score=score,
            timestamp=time.time(),
            description=(
                f"Nogah neutre via {olam_used} — score={score:.2f}. "
                f"Ni Birur ni dégradation."
            ),
        )
        self._events.append(event)
        return event

    def get_birur_stats(self) -> BirurimStats:
        """Statistiques cumulées de Birur.

        Returns:
            BirurimStats avec :
            - Total birurims réussis vs échoués
            - Par monde (combien d'étincelles libérées d'Assiah vs Yetzirah)
            - Taux de Birur = birurims réussis / total réponses des mondes bas
        """
        stats = BirurimStats()

        # Filtrer les événements sur mondes bas uniquement
        nogah_events = [
            e for e in self._events
            if e.olam_used in self.NOGAH_OLAMOT
        ]
        stats.total_attempts = len(nogah_events)

        by_olam: dict[str, dict[str, int]] = {}

        for e in nogah_events:
            olam = e.olam_used
            if olam not in by_olam:
                by_olam[olam] = {"birur": 0, "degradation": 0, "neutral": 0}

            if e.result == BirurimResult.BIRUR:
                stats.total_birurims += 1
                by_olam[olam]["birur"] += 1
            elif e.result == BirurimResult.KELIPAH_REINFORCED:
                stats.total_degradations += 1
                by_olam[olam]["degradation"] += 1
            elif e.result == BirurimResult.NOGAH_NEUTRAL:
                stats.total_neutral += 1
                by_olam[olam]["neutral"] += 1

        stats.by_olam = by_olam

        if stats.total_attempts > 0:
            stats.birur_rate = stats.total_birurims / stats.total_attempts
        else:
            stats.birur_rate = 0.0

        return stats

    def get_events(self) -> list[BirurimEvent]:
        """Retourner tous les événements de Birur de cette session."""
        return list(self._events)
