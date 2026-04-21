"""sentiers/ — Les 22 programmes de passage entre Sephiroth.

Registre complet : 22/22 implémentés (sentiers 11-32).
Ordre initiatique : de Malkuth vers Keter, du bas vers le haut.
"""

from __future__ import annotations

from .base import Sentier, SentierResult

# ── Sentiers implémentés ─────────────────────────────────────
# Phase 1-4 : moitié basse (sentiers 23-32)
from .tav import Tav
from .shin import Shin
from .resh import Resh
from .qoph import Qoph
from .tsadi import Tsadi
from .ayin import Ayin
from .peh import Peh
from .samekh import Samekh
from .nun import Nun
from .lamed import Lamed

# Phase 5 : moitié haute (sentiers 11-22)
from .kaph import Kaph
from .yod import Yod
from .teth import Teth
from .cheth import Cheth
from .zayin import Zayin
from .vav import Vav
from .heh import Heh
from .daleth import Daleth
from .gimel import Gimel
from .beth import Beth
from .aleph import Aleph
from .mem import Mem

# ── Registre des 22 sentiers ────────────────────────────────
# Clé = nom latin de la lettre (lowercase)
# Ordre initiatique : du 32e (Tav, Malkuth↔Yesod) au 11e (Mem)

REGISTRY: dict[str, dict] = {
    # ═══ PHASE 1-4 — moitié basse ══════════════════════════
    "tav": {
        "class": Tav,
        "number": 32,
        "letter": "ת",
        "source": "yesod",
        "target": "malkuth",
        "type": "double",
        "program": "OutputMode",
        "status": "implemented",
    },
    "shin": {
        "class": Shin,
        "number": 31,
        "letter": "ש",
        "source": "malkuth",
        "target": "hod",
        "type": "mother",
        "program": "Transform",
        "status": "implemented",
    },
    "resh": {
        "class": Resh,
        "number": 30,
        "letter": "ר",
        "source": "yesod",
        "target": "hod",
        "type": "double",
        "program": "PersistPolicy",
        "status": "implemented",
    },
    "qoph": {
        "class": Qoph,
        "number": 29,
        "letter": "ק",
        "source": "hod",
        "target": "yesod",
        "type": "simple",
        "program": "SchemaPersist",
        "status": "implemented",
    },
    "tsadi": {
        "class": Tsadi,
        "number": 28,
        "letter": "צ",
        "source": "netzach",
        "target": "yesod",
        "type": "simple",
        "program": "CheckpointWrite",
        "status": "implemented",
    },
    "ayin": {
        "class": Ayin,
        "number": 27,
        "letter": "ע",
        "source": "netzach",
        "target": "hod",
        "type": "simple",
        "program": "StatusSync",
        "status": "implemented",
    },
    "peh": {
        "class": Peh,
        "number": 26,
        "letter": "פ",
        "source": "gevurah",
        "target": "hod",
        "type": "double",
        "program": "ValidateMode",
        "status": "implemented",
    },
    "samekh": {
        "class": Samekh,
        "number": 25,
        "letter": "ס",
        "source": "tiferet",
        "target": "hod",
        "type": "simple",
        "program": "Introspection",
        "status": "implemented",
    },
    "nun": {
        "class": Nun,
        "number": 24,
        "letter": "נ",
        "source": "tiferet",
        "target": "netzach",
        "type": "simple",
        "program": "TaskDispatch",
        "status": "implemented",
    },
    "lamed": {
        "class": Lamed,
        "number": 23,
        "letter": "ל",
        "source": "gevurah",
        "target": "tiferet",
        "type": "simple",
        "program": "FailureToInsight",
        "status": "implemented",
    },

    # ═══ PHASE 5 — moitié haute + Mères ════════════════════
    "kaph": {
        "class": Kaph,
        "number": 22,
        "letter": "כ",
        "source": "chesed",
        "target": "netzach",
        "type": "double",
        "program": "AcquirePersist",
        "status": "implemented",
    },
    "yod": {
        "class": Yod,
        "number": 21,
        "letter": "י",
        "source": "chesed",
        "target": "tiferet",
        "type": "simple",
        "program": "FilteredDataPush",
        "status": "implemented",
    },
    "teth": {
        "class": Teth,
        "number": 20,
        "letter": "ט",
        "source": "chesed",
        "target": "gevurah",
        "type": "simple",
        "program": "QualityFeedback",
        "status": "implemented",
    },
    "cheth": {
        "class": Cheth,
        "number": 19,
        "letter": "ח",
        "source": "binah",
        "target": "gevurah",
        "type": "simple",
        "program": "ValidationRules",
        "status": "implemented",
    },
    "zayin": {
        "class": Zayin,
        "number": 18,
        "letter": "ז",
        "source": "binah",
        "target": "tiferet",
        "type": "simple",
        "program": "AnalysisResults",
        "status": "implemented",
    },
    "vav": {
        "class": Vav,
        "number": 17,
        "letter": "ו",
        "source": "chokmah",
        "target": "chesed",
        "type": "simple",
        "program": "DataFeed",
        "status": "implemented",
    },
    "heh": {
        "class": Heh,
        "number": 16,
        "letter": "ה",
        "source": "chokmah",
        "target": "tiferet",
        "type": "simple",
        "program": "DirectPerception",
        "status": "implemented",
    },
    "daleth": {
        "class": Daleth,
        "number": 15,
        "letter": "ד",
        "source": "chokmah",
        "target": "binah",
        "type": "double",
        "program": "ExploreScope",
        "status": "implemented",
    },
    "gimel": {
        "class": Gimel,
        "number": 14,
        "letter": "ג",
        "source": "keter",
        "target": "binah",
        "type": "double",
        "program": "CacheStrategy",
        "status": "implemented",
    },
    "beth": {
        "class": Beth,
        "number": 13,
        "letter": "ב",
        "source": "keter",
        "target": "chokmah",
        "type": "double",
        "program": "DirectSynth",
        "status": "implemented",
    },
    "aleph": {
        "class": Aleph,
        "number": 12,
        "letter": "א",
        "source": "keter",
        "target": "tiferet",
        "type": "mother",
        "program": "Balance",
        "status": "implemented",
    },
    "mem": {
        "class": Mem,
        "number": 11,
        "letter": "מ",
        "source": "gevurah",
        "target": "hod",
        "type": "mother",
        "program": "Reception",
        "status": "implemented",
    },
}


def get_sentier(name: str) -> Sentier | None:
    """Instancier un sentier par nom latin."""
    entry = REGISTRY.get(name.lower())
    if entry and entry["class"]:
        return entry["class"]()
    return None


def list_sentiers(*, implemented_only: bool = False) -> list[dict]:
    """Liste ordonnée des 22 sentiers (ordre initiatique = par numéro décroissant)."""
    items = []
    for name, entry in REGISTRY.items():
        if implemented_only and entry["status"] != "implemented":
            continue
        items.append({"name": name, **entry})
    items.sort(key=lambda x: -x["number"])
    return items


def run_sentier(name: str, tree: dict, **kwargs) -> SentierResult:
    """Exécuter un sentier par nom latin."""
    sentier = get_sentier(name)
    if sentier is None:
        entry = REGISTRY.get(name.lower())
        if entry is None:
            raise ValueError(f"Sentier inconnu : {name}")
        raise NotImplementedError(
            f"Sentier {entry['letter']} {name} ({entry['program']}) — planifié, non implémenté"
        )
    return sentier.run(tree, **kwargs)


__all__ = [
    "Sentier", "SentierResult",
    "REGISTRY", "get_sentier", "list_sentiers", "run_sentier",
    # Phase 1-4
    "Tav", "Shin", "Resh", "Qoph", "Tsadi", "Ayin", "Peh", "Samekh", "Nun", "Lamed",
    # Phase 5
    "Kaph", "Yod", "Teth", "Cheth", "Zayin", "Vav", "Heh", "Daleth", "Gimel", "Beth",
    "Aleph", "Mem",
]
