"""Masakh — L'écran entre Yesod et Malkuth.

מָסָךְ — Le Masakh est l'écran qui filtre la Lumière (Or) selon
la capacité du Kli (récipient) à la recevoir. Sans Masakh, le Kli
se brise (Shevirat HaKelim).

En IA : le Masakh filtre le prompt AVANT l'appel au LLM, selon
le niveau d'Aviut (épaisseur) déterminé par l'Olam demandé.
Un Olam élevé (Atziluth) reçoit moins de tokens bruts — il opère
sur l'essence. Un Olam bas (Assiah) reçoit davantage — il opère
sur le détail.

Architecture Rosh-Toch-Sof (EC-SHK-018..031, PG-SHK-007) :
  Rosh : décision — calcule les paramètres de filtrage, ne touche pas au contexte
  Toch : assemblage — applique le filtrage effectif selon le mode d'Aviut
  Sof  : gestion du rejet — documente ce qui a été exclu (Reshimo de Aviut)

5 niveaux de Masakh (PG-SHK-010, EC-SHK-018..020) :

  Dalet  (Atziluth) — kashiut=0.8, compression forte, budget 20%
  Gimel  (Briah)    — kashiut=0.7, compression modérée, budget 30%
  Bet    (Yetzirah) — kashiut=0.6, résumé, budget 40%
  Aleph  (Assiah)   — kashiut=0.5, troncation simple, budget 60%
  Shoresh (debug)   — kashiut=0.0, aucun filtrage, budget 85%

Double propriété (EC-SHK-020) :
  Kashiut (קָשִׁיוּת) = dureté = seuil de pertinence pour REJETER
  Aviut   (עֲבִיוּת) = épaisseur = capacité de TRANSFORMATION

Hizdakchut (הִזְדַּכְּכוּת) = amincissement dynamique du Masakh :
  Si la qualité se dégrade → descendre d'un niveau (moins de filtrage)
  Si la qualité est haute → monter d'un niveau (plus de filtrage)

Usage:
    from masakh import Masakh

    m = Masakh("briah")                        # niveau gimel par défaut
    params = m.rosh(prompt, context_window=32768)
    filtered = m.toch(prompt, params["budget_tokens"], query=question)
    log = m.sof(prompt, filtered)

    m.set_level("aleph")                       # changer dynamiquement
    m.hizdakchut(quality_score=0.2)            # auto-ajustement
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── Constantes ──────────────────────────────────────────────

# Approximation grossière : ~4 caractères par token pour les modèles Ollama.
CHARS_PER_TOKEN = 4

# Ordre des niveaux du plus filtrant au moins filtrant
LEVEL_ORDER = ("dalet", "gimel", "bet", "aleph", "shoresh")

# Définition complète des 5 niveaux de Masakh
MASAKH_LEVELS: dict[str, dict] = {
    # Dalet/Gimel/Bet : extraction via masakh.compression (pas de head/tail)
    "dalet": {
        "kashiut": 0.8,
        "aviut_mode": "compression_forte",
        "budget_ratio": 0.20,
    },
    "gimel": {
        "kashiut": 0.7,
        "aviut_mode": "compression_moderee",
        "budget_ratio": 0.30,
    },
    "bet": {
        "kashiut": 0.6,
        "aviut_mode": "resume",
        "budget_ratio": 0.40,
    },
    # Aleph/Shoresh : troncation positionnelle (head_ratio utilisé par toch())
    "aleph": {
        "kashiut": 0.5,
        "aviut_mode": "troncation",
        "budget_ratio": 0.60,
        "head_ratio": 0.80,
    },
    "shoresh": {
        "kashiut": 0.0,
        "aviut_mode": "aucune",
        "budget_ratio": 0.85,
    },
}

# Mapping Olam → niveau par défaut
OLAM_DEFAULT_LEVEL: dict[str, str] = {
    "atziluth": "dalet",
    "briah": "gimel",
    "yetzirah": "bet",
    "assiah": "aleph",
}

# Compat : ancien dict pour le code qui importe AVIUT_LEVELS
AVIUT_LEVELS: dict[str, dict] = {
    olam: {"level": level, "budget_ratio": MASAKH_LEVELS[level]["budget_ratio"]}
    for olam, level in OLAM_DEFAULT_LEVEL.items()
}

# Seuils de Hizdakchut (amincissement dynamique)
HIZDAKCHUT_DEGRADE_THRESHOLD = 0.3   # qualité < 0.3 → descendre
HIZDAKCHUT_UPGRADE_THRESHOLD = 0.8   # qualité > 0.8 → monter

# ── Hizdakchut persistant ──────────────────────────────────
# Stocke les niveaux ajustés par hizdakchut entre les appels.
# Clé = olam, valeur = niveau courant après ajustement.
# Le Masakh est recréé à chaque appel (ContextAssembler) —
# ce dict assure la continuité du feedback qualité→niveau.
#
# Audit F06 / R4 : le dict sert de CACHE ; la source de vérité
# est la table hizdakchut_state en PostgreSQL. Si la DB est
# indisponible, le cache en mémoire continue de fonctionner.
_HIZDAKCHUT_LEVELS: dict[str, str] = {}
_HIZDAKCHUT_LOADED_FROM_DB: bool = False


# ── Hizdakchut DB helpers (audit F06 / R4) ─────────────────


def _hizdakchut_db_load() -> dict[str, str] | None:
    """Load all hizdakchut levels from PostgreSQL.

    Returns:
        Dict {olam: level} or None if DB is unavailable.
    """
    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT olam, level FROM hizdakchut_state"
                )
                rows = cur.fetchall()
                return {row[0]: row[1] for row in rows}
    except Exception as exc:
        logger.warning("hizdakchut_db_load: DB indisponible (%s), fallback mémoire", exc)
        return None


def _hizdakchut_db_set(olam: str, level: str) -> bool:
    """Write-through: persist a single hizdakchut level to PostgreSQL.

    Returns:
        True if persisted, False if DB is unavailable.
    """
    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO hizdakchut_state (olam, level, updated_at)
                       VALUES (%s, %s, NOW())
                       ON CONFLICT (olam)
                       DO UPDATE SET level = EXCLUDED.level,
                                     updated_at = EXCLUDED.updated_at""",
                    (olam, level),
                )
        return True
    except Exception as exc:
        logger.warning("hizdakchut_db_set: DB indisponible (%s), mémoire seule", exc)
        return False


def _hizdakchut_db_log_transition(
    olam: str,
    from_level: str,
    to_level: str,
    quality_score: float,
    reason: str | None = None,
) -> bool:
    """Append a row to hizdakchut_transitions (audit cycle 4, I3).

    Le write-through dans hizdakchut_state n'écrase que l'état courant.
    Pour prouver l'activité de la boucle Hizdakchut en prod et exposer
    une métrique transitions/h, on log chaque transition ici.

    Returns:
        True if logged, False if DB unavailable (best-effort, ne casse
        jamais la boucle d'auto-régulation).
    """
    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO hizdakchut_transitions
                       (olam, from_level, to_level, quality_score, reason)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (olam, from_level, to_level, float(quality_score), reason),
                )
        return True
    except Exception as exc:
        logger.warning(
            "hizdakchut_db_log_transition: %s (transition non loggée)", exc
        )
        return False


def _hizdakchut_db_reset() -> bool:
    """Reset all hizdakchut levels in PostgreSQL to defaults.

    Returns:
        True if reset, False if DB is unavailable.
    """
    try:
        from pool import get_conn

        with get_conn() as conn:
            with conn.cursor() as cur:
                for olam, level in OLAM_DEFAULT_LEVEL.items():
                    cur.execute(
                        """UPDATE hizdakchut_state
                           SET level = %s, updated_at = NOW()
                           WHERE olam = %s""",
                        (level, olam),
                    )
        return True
    except Exception as exc:
        logger.warning("hizdakchut_db_reset: DB indisponible (%s)", exc)
        return False


def _ensure_hizdakchut_loaded() -> None:
    """Load hizdakchut levels from DB into cache on first access.

    Idempotent: only loads once per process lifetime. If DB is
    unavailable, the in-memory cache remains authoritative.
    """
    global _HIZDAKCHUT_LOADED_FROM_DB
    if _HIZDAKCHUT_LOADED_FROM_DB:
        return

    db_levels = _hizdakchut_db_load()
    if db_levels is not None:
        # Only populate cache entries that differ from OLAM defaults
        # (i.e. entries that represent actual hizdakchut adjustments).
        for olam, level in db_levels.items():
            default = OLAM_DEFAULT_LEVEL.get(olam)
            if level != default:
                _HIZDAKCHUT_LEVELS[olam] = level
        _HIZDAKCHUT_LOADED_FROM_DB = True
        logger.debug("hizdakchut: chargé depuis DB — %s", _HIZDAKCHUT_LEVELS)
    else:
        # DB unavailable — keep using in-memory dict as-is.
        # Do NOT set _HIZDAKCHUT_LOADED_FROM_DB so we retry next time.
        pass


# ── Régulation Partzufim → Masakh (EC-SHK-057, EC-SHK-083) ──
# Offset appliqué par le constructeur Masakh quand aucun level
# explicite n'est fourni. Recalculé à chaque pipeline par
# regulate_masakh_from_partzufim().
# -1 = katnut → plus de filtrage (monte vers dalet)
# +1 = gadlut → moins de filtrage (descend vers shoresh)
#  0 = transitional → pas d'ajustement
_PARTZUFIM_MASAKH_OFFSET: dict[str, int] = {}

# Seuils pour la logique de cascade Partzufim
# (dupliqués ici pour éviter l'import circulaire depuis partzufim.regulator)
_PARTZUF_KATNUT_THRESHOLD = 0.4
_PARTZUF_ATIK_CASCADE = 0.5


def get_hizdakchut_levels() -> dict[str, str]:
    """Lire les niveaux hizdakchut persistants (copie).

    Charge depuis PostgreSQL au premier appel (audit F06/R4).
    """
    _ensure_hizdakchut_loaded()
    return dict(_HIZDAKCHUT_LEVELS)


def reset_hizdakchut_levels() -> None:
    """Réinitialiser tous les niveaux hizdakchut (retour aux défauts).

    Remet aussi la DB à jour si disponible (audit F06/R4).
    """
    global _HIZDAKCHUT_LOADED_FROM_DB
    _HIZDAKCHUT_LEVELS.clear()
    _HIZDAKCHUT_LOADED_FROM_DB = False
    _hizdakchut_db_reset()


# ── Partzufim → Masakh : fonctions module ──────────────────


def _effective_mochin_for_masakh(
    partzuf_state: dict[str, dict],
) -> tuple[str, str]:
    """Calcule le mochin effectif de ZA et Nukva avec cascades.

    Applique la même logique de cascade que PartzufimRegulator :
      Atik.overall < 0.5 → ZA + Nukva forcés en katnut
      Imma katnut (ou score < 0.4) → ZA forcé en katnut
      Score direct < 0.4 → katnut

    Returns:
        (za_mochin, nukva_mochin) — valeurs effectives après cascades.
    """
    za = partzuf_state.get("zeir_anpin", {})
    nukva = partzuf_state.get("nukva", {})
    atik = partzuf_state.get("atik_yomin", {})
    imma = partzuf_state.get("imma", {})

    za_mochin = za.get("mochin_state", "transitional")
    nukva_mochin = nukva.get("mochin_state", "transitional")
    atik_score = atik.get("overall", 0.5)

    # Cascade Atik → tous
    if atik_score < _PARTZUF_ATIK_CASCADE:
        return ("katnut", "katnut")

    # Cascade Imma → ZA
    imma_mochin = imma.get("mochin_state", "transitional")
    imma_score = imma.get("overall", 0.5)
    if imma_mochin == "katnut" or imma_score < _PARTZUF_KATNUT_THRESHOLD:
        za_mochin = "katnut"

    # Score direct
    if za.get("overall", 0.5) < _PARTZUF_KATNUT_THRESHOLD:
        za_mochin = "katnut"
    if nukva.get("overall", 0.5) < _PARTZUF_KATNUT_THRESHOLD:
        nukva_mochin = "katnut"

    return (za_mochin, nukva_mochin)


def regulate_masakh_from_partzufim(
    partzuf_state: dict[str, dict],
) -> dict[str, dict]:
    """Réguler le Masakh de tous les Olamot selon l'état des Partzufim.

    EC-SHK-057, EC-SHK-083 — Le Katnut/Gadlut des Partzufim influence
    le niveau du Masakh via un offset appliqué par le constructeur.

    L'offset est recalculé à chaque appel (pas d'accumulation).
    Appelé dans cmd_ask après le PartzufimRegulator.

    Args:
        partzuf_state: {partzuf_key: {overall, mochin_state, ...}}

    Returns:
        {olam: {from, to, offset, reason}} pour les olamot affectés.
    """
    if not partzuf_state:
        _PARTZUFIM_MASAKH_OFFSET.clear()
        return {}

    za_mochin, nukva_mochin = _effective_mochin_for_masakh(partzuf_state)

    # Déterminer l'offset désiré
    if za_mochin == "katnut" or nukva_mochin == "katnut":
        desired_offset = -1
        parts = []
        if za_mochin == "katnut":
            parts.append("ZA katnut")
        if nukva_mochin == "katnut":
            parts.append("Nukva katnut")
        reason = f"partzufim: {', '.join(parts)} → +filtrage"
    elif za_mochin == "gadlut" and nukva_mochin == "gadlut":
        desired_offset = 1
        reason = "partzufim: ZA+Nukva gadlut → -filtrage"
    else:
        desired_offset = 0
        reason = "partzufim: transitional → neutre"

    # Charger les niveaux depuis DB au premier accès (audit F06/R4)
    _ensure_hizdakchut_loaded()

    results: dict[str, dict] = {}
    for olam in OLAM_DEFAULT_LEVEL:
        old_offset = _PARTZUFIM_MASAKH_OFFSET.get(olam, 0)

        # Calculer les niveaux effectifs pour le log
        base = _HIZDAKCHUT_LEVELS.get(olam) or OLAM_DEFAULT_LEVEL[olam]
        base_idx = LEVEL_ORDER.index(base)
        old_eff_idx = max(0, min(len(LEVEL_ORDER) - 1, base_idx + old_offset))
        new_eff_idx = max(0, min(len(LEVEL_ORDER) - 1, base_idx + desired_offset))

        _PARTZUFIM_MASAKH_OFFSET[olam] = desired_offset

        if old_eff_idx != new_eff_idx:
            results[olam] = {
                "from": LEVEL_ORDER[old_eff_idx],
                "to": LEVEL_ORDER[new_eff_idx],
                "offset": desired_offset,
                "reason": reason,
            }

    if results:
        logger.info("regulate_masakh_from_partzufim: %s", results)

    return results


def get_partzufim_masakh_offset() -> dict[str, int]:
    """Lire les offsets Partzufim→Masakh courants (copie)."""
    return dict(_PARTZUFIM_MASAKH_OFFSET)


def reset_partzufim_masakh_offset() -> None:
    """Réinitialiser les offsets Partzufim→Masakh (retour à 0)."""
    _PARTZUFIM_MASAKH_OFFSET.clear()


def auto_hizdakchut(olam: str, quality_score: float) -> dict | None:
    """Boucle Hizdakchut automatique — ajuster le Masakh selon la qualité.

    הִזְדַּכְּכוּת אוטומטי — Après chaque réponse, le score de qualité
    (AutoJudge, BeinoniTracker, confiance Hod) est injecté ici.
    Le niveau ajusté persiste pour le prochain appel.

    Args:
        olam: Le monde dont le Masakh doit être ajusté.
        quality_score: Score de qualité de la dernière réponse (0.0–1.0).

    Returns:
        Dict avec détails du changement, ou None si pas de changement.
    """
    if olam not in OLAM_DEFAULT_LEVEL:
        return None

    # Charger depuis DB au premier appel (audit F06/R4)
    _ensure_hizdakchut_loaded()

    # Créer un Masakh au niveau courant (persisté ou défaut)
    current_level = _HIZDAKCHUT_LEVELS.get(olam)
    masakh = Masakh(olam, level=current_level)

    changed = masakh.hizdakchut(quality_score)
    if not changed:
        return None

    # Persister le nouveau niveau (mémoire + DB write-through)
    _HIZDAKCHUT_LEVELS[olam] = masakh.level
    _hizdakchut_db_set(olam, masakh.level)
    from_level = masakh.level_changes[-1]["from"]
    reason = masakh.level_changes[-1]["reason"]
    # I3 : log historique des transitions (best-effort, ne bloque pas).
    _hizdakchut_db_log_transition(
        olam, from_level, masakh.level, quality_score, reason
    )
    result = {
        "olam": olam,
        "from": from_level,
        "to": masakh.level,
        "quality_score": quality_score,
        "reason": reason,
    }
    logger.info(
        "Auto-hizdakchut %s: %s → %s (qualité=%.2f)",
        olam, result["from"], result["to"], quality_score,
    )
    return result


# ── Log en mémoire ─────────────────────────────────────────

_MASAKH_LOG: list[dict] = []


def get_log() -> list[dict]:
    """Accéder au log en mémoire (Reshimo de Aviut)."""
    return list(_MASAKH_LOG)


def clear_log() -> None:
    """Vider le log en mémoire."""
    _MASAKH_LOG.clear()


# ── Masakh ──────────────────────────────────────────────────

class Masakh:
    """מָסָךְ — Écran de filtrage entre Yesod et Malkuth.

    Chaque instance est liée à un Olam, qui détermine le niveau
    d'Aviut initial. Le niveau peut changer dynamiquement via
    set_level() ou hizdakchut().

    Double propriété (EC-SHK-020) :
      kashiut = seuil de pertinence (dureté du filtre)
      aviut   = mode de transformation (épaisseur du filtre)
    """

    def __init__(self, olam: str, *, level: str | None = None) -> None:
        if olam not in OLAM_DEFAULT_LEVEL:
            raise ValueError(
                f"Olam inconnu: {olam!r}. "
                f"Attendu: {', '.join(OLAM_DEFAULT_LEVEL)}"
            )
        self.olam = olam
        # Charger les niveaux depuis DB au premier accès (audit F06/R4)
        _ensure_hizdakchut_loaded()
        # Priorité : level explicite > hizdakchut persisté > défaut olam
        base = (
            level
            or _HIZDAKCHUT_LEVELS.get(olam)
            or OLAM_DEFAULT_LEVEL[olam]
        )
        # Appliquer l'offset Partzufim (EC-SHK-057, EC-SHK-083)
        # Seulement si aucun level explicite n'est fourni, pour ne pas
        # interférer avec auto_hizdakchut() qui passe level=current.
        if level is None:
            offset = _PARTZUFIM_MASAKH_OFFSET.get(olam, 0)
            if offset != 0:
                base_idx = LEVEL_ORDER.index(base)
                adj_idx = max(0, min(len(LEVEL_ORDER) - 1, base_idx + offset))
                base = LEVEL_ORDER[adj_idx]
        self._level_name = base
        if self._level_name not in MASAKH_LEVELS:
            raise ValueError(
                f"Niveau inconnu: {self._level_name!r}. "
                f"Attendu: {', '.join(MASAKH_LEVELS)}"
            )
        self._level_changes: list[dict] = []
        self._kashiut_rejected: list[dict] = []

    # ── Propriétés ──────────────────────────────────────────

    @property
    def level(self) -> str:
        """Niveau courant : dalet, gimel, bet, aleph, ou shoresh."""
        return self._level_name

    @property
    def budget_ratio(self) -> float:
        """Fraction du ctx_window allouée au prompt."""
        return MASAKH_LEVELS[self._level_name]["budget_ratio"]

    @property
    def kashiut(self) -> float:
        """Seuil de pertinence (0.0–1.0). Plus haut = plus strict."""
        return MASAKH_LEVELS[self._level_name]["kashiut"]

    @property
    def aviut_mode(self) -> str:
        """Mode de transformation : compression_forte, compression_moderee,
        resume, troncation, aucune."""
        return MASAKH_LEVELS[self._level_name]["aviut_mode"]

    @property
    def level_index(self) -> int:
        """Index dans LEVEL_ORDER (0=dalet le plus filtrant, 4=shoresh)."""
        return LEVEL_ORDER.index(self._level_name)

    # ── Changement dynamique ────────────────────────────────

    def set_level(self, level: str) -> None:
        """Changer le niveau du Masakh manuellement.

        Args:
            level: dalet, gimel, bet, aleph, ou shoresh
        """
        if level not in MASAKH_LEVELS:
            raise ValueError(
                f"Niveau inconnu: {level!r}. "
                f"Attendu: {', '.join(MASAKH_LEVELS)}"
            )
        old = self._level_name
        if old != level:
            self._level_name = level
            change = {
                "timestamp": time.time(),
                "from": old,
                "to": level,
                "reason": "manual",
            }
            self._level_changes.append(change)
            logger.info(
                "Masakh %s: niveau %s → %s (manual)",
                self.olam, old, level,
            )

    def hizdakchut(self, quality_score: float) -> bool:
        """Amincissement dynamique — ajuster le niveau selon la qualité.

        הִזְדַּכְּכוּת — Quand le Masakh est trop épais pour la lumière
        reçue, il s'amincit. Quand la lumière est forte et pure,
        le Masakh s'épaissit pour la contenir.

        Args:
            quality_score: Score de qualité de la dernière réponse (0.0–1.0)

        Returns:
            True si le niveau a changé.
        """
        old = self._level_name
        old_idx = self.level_index

        if quality_score < HIZDAKCHUT_DEGRADE_THRESHOLD and old_idx < len(LEVEL_ORDER) - 1:
            # Qualité basse → descendre (moins de filtrage)
            new_level = LEVEL_ORDER[old_idx + 1]
            reason = f"hizdakchut: qualité={quality_score:.2f} < {HIZDAKCHUT_DEGRADE_THRESHOLD}"
        elif quality_score > HIZDAKCHUT_UPGRADE_THRESHOLD and old_idx > 0:
            # Qualité haute → monter (plus de filtrage)
            new_level = LEVEL_ORDER[old_idx - 1]
            reason = f"hizdakchut: qualité={quality_score:.2f} > {HIZDAKCHUT_UPGRADE_THRESHOLD}"
        else:
            return False

        self._level_name = new_level
        self._level_changes.append({
            "timestamp": time.time(),
            "from": old,
            "to": new_level,
            "reason": reason,
        })
        logger.info(
            "Masakh %s: hizdakchut %s → %s (qualité=%.2f)",
            self.olam, old, new_level, quality_score,
        )
        return True

    @property
    def level_changes(self) -> list[dict]:
        """Historique des changements de niveau dans cette session."""
        return list(self._level_changes)

    def regulate_from_pressure(self, pressure) -> bool:
        """Ajuster le niveau du Masakh selon la pression Tsimtsum.

        Chesed (expansion) ↔ Gevurah (contraction) — la dimension 9
        de l'Arbre. Le Masakh est le Kli qui médiatise cette tension.

        Pression élevée (CONTRACTION) → plus de filtrage (Gevurah)
        Pression basse  (EXPANSION)   → moins de filtrage (Chesed)
        Pression stable               → pas de changement

        Args:
            pressure: SystemPressure (from tzimtzum.py) ou tout objet
                avec .phase (str ou TzimtzumPhase) et .global_pressure (float)

        Returns:
            True si le niveau a changé.
        """
        phase = pressure.phase
        if hasattr(phase, "value"):
            phase = phase.value

        old = self._level_name
        old_idx = self.level_index

        if phase == "contraction" and old_idx > 0:
            new_level = LEVEL_ORDER[old_idx - 1]
            reason = (
                f"tsimtsum: pression={pressure.global_pressure:.2f} "
                f"→ contraction → plus de filtrage (Gevurah)"
            )
        elif phase == "expansion" and old_idx < len(LEVEL_ORDER) - 1:
            new_level = LEVEL_ORDER[old_idx + 1]
            reason = (
                f"tsimtsum: pression={pressure.global_pressure:.2f} "
                f"→ expansion → moins de filtrage (Chesed)"
            )
        else:
            return False

        self._level_name = new_level
        self._level_changes.append({
            "timestamp": time.time(),
            "from": old,
            "to": new_level,
            "reason": reason,
        })
        logger.info(
            "Masakh %s: tsimtsum %s → %s (pression=%.2f, phase=%s)",
            self.olam, old, new_level, pressure.global_pressure, phase,
        )
        return True

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimation du nombre de tokens (~4 chars/token)."""
        return max(1, len(text) // CHARS_PER_TOKEN)

    # ── Rosh : décision ─────────────────────────────────────

    def rosh(self, prompt: str, context_window: int) -> dict:
        """Phase Rosh — calcule les paramètres, ne touche pas au prompt.

        Args:
            prompt: Le prompt original
            context_window: Taille du contexte du modèle (en tokens)

        Returns:
            Dict avec budget, niveau, kashiut, aviut_mode, et si le filtrage est nécessaire.
        """
        tokens_prompt = self.estimate_tokens(prompt)
        budget_tokens = int(context_window * self.budget_ratio)

        return {
            "olam": self.olam,
            "aviut_level": self.level,
            "kashiut": self.kashiut,
            "aviut_mode": self.aviut_mode,
            "budget_ratio": self.budget_ratio,
            "context_window": context_window,
            "budget_tokens": budget_tokens,
            "prompt_tokens": tokens_prompt,
            "needs_filtering": tokens_prompt > budget_tokens,
        }

    # ── Toch : assemblage ───────────────────────────────────

    def toch(self, prompt: str, budget_tokens: int, *, query: str | None = None) -> str:
        """Phase Toch — applique Kashiut (pertinence) puis Aviut (compression).

        Double propriété du Masakh (EC-SHK-020, EC-SHK-085) :
          1. Kashiut — rejet des blocs non pertinents vs la query
             (opère AVANT la compression, indépendamment du budget)
          2. Aviut — compression selon le mode du niveau :
             compression_forte, compression_moderee, resume, troncation, aucune

        Args:
            prompt: Le prompt original
            budget_tokens: Budget en tokens
            query: La question de l'utilisateur (pour le scoring Kashiut).
                Si None, le Kashiut est désactivé (rétro-compatible).

        Returns:
            Le prompt filtré (ou original si dans le budget et pertinent).
        """
        # ── Phase 1 : Kashiut — rejet par pertinence ──────────
        # Opère AVANT la compression. Un bloc non pertinent est éliminé
        # entièrement, pas compressé. Shoresh (kashiut=0.0) laisse tout
        # passer (mode debug).
        if query and self.kashiut > 0.0:
            from masakh.kashiut import filter_by_kashiut
            prompt, self._kashiut_rejected = filter_by_kashiut(
                prompt, query, self.kashiut,
            )
        else:
            self._kashiut_rejected = []

        # ── Phase 2 : Aviut — compression par budget ──────────
        prompt_tokens = self.estimate_tokens(prompt)

        if prompt_tokens <= budget_tokens:
            return prompt

        mode = self.aviut_mode

        # Shoresh / aucune : pas de filtrage quel que soit le budget
        if mode == "aucune":
            return prompt

        # Convertir le budget en caractères
        budget_chars = budget_tokens * CHARS_PER_TOKEN
        # Réserver de la place pour le marker de traçabilité (~80 chars)
        marker_reserve = 80

        # Modes extractifs (F10 fix: chaque mode produit un résultat DIFFÉRENT)
        if mode == "compression_forte":
            from masakh.compression import compression_forte
            extracted = compression_forte(prompt, budget_chars - marker_reserve)
            rejected_tokens = max(0, prompt_tokens - self.estimate_tokens(extracted))
            marker = (
                f"\n\n[Masakh {self.level} — compression forte, "
                f"{rejected_tokens} tokens élagués, Olam {self.olam}]\n"
            )
            return extracted + marker

        if mode == "compression_moderee":
            from masakh.compression import compression_moderee
            extracted = compression_moderee(prompt, budget_chars - marker_reserve)
            rejected_tokens = max(0, prompt_tokens - self.estimate_tokens(extracted))
            marker = (
                f"\n\n[Masakh {self.level} — compression modérée, "
                f"{rejected_tokens} tokens filtrés, Olam {self.olam}]\n"
            )
            return extracted + marker

        if mode == "resume":
            from masakh.compression import resume
            extracted = resume(prompt, budget_chars - marker_reserve)
            rejected_tokens = max(0, prompt_tokens - self.estimate_tokens(extracted))
            marker = (
                f"\n\n[Masakh {self.level} — résumé extractif, "
                f"{rejected_tokens} tokens condensés, Olam {self.olam}]\n"
            )
            return extracted + marker

        # troncation : head seulement (inchangé)
        level_cfg = MASAKH_LEVELS[self._level_name]
        head_ratio = level_cfg["head_ratio"]
        head_chars = max(int(budget_chars * head_ratio), 20)
        head = prompt[:head_chars]
        kept_tokens = self.estimate_tokens(head)
        middle_tokens = max(0, prompt_tokens - kept_tokens)

        separator = (
            f"\n\n[... {middle_tokens} tokens tronqués par "
            f"Masakh {self.level} — troncation simple ...]\n\n"
        )
        return head + separator

    # ── Sof : gestion du rejet ──────────────────────────────

    def sof(self, original: str, filtered: str) -> dict:
        """Phase Sof — documente ce qui a été exclu.

        Produit le Reshimo de Aviut : la trace du filtrage,
        stockée pour le méta-apprentissage futur.

        Documente les deux mécanismes de rejet :
          - Kashiut : blocs rejetés par pertinence (avant compression)
          - Aviut   : tokens rejetés par budget (compression/troncation)

        Args:
            original: Le prompt original
            filtered: Le prompt après filtrage

        Returns:
            Entrée de log avec métriques du filtrage.
        """
        tokens_before = self.estimate_tokens(original)
        tokens_after = self.estimate_tokens(filtered)
        tokens_rejected = max(0, tokens_before - tokens_after)
        was_filtered = tokens_rejected > 0

        # Kashiut rejection metrics (set by toch() before sof() is called)
        kashiut_rejected = self._kashiut_rejected
        kashiut_tokens = sum(r["tokens_est"] for r in kashiut_rejected)

        # Build rejection reason including both mechanisms
        reasons: list[str] = []
        if kashiut_rejected:
            reasons.append(
                f"kashiut {self.kashiut:.1f}: {len(kashiut_rejected)} blocs "
                f"rejetés ({kashiut_tokens} tok)"
            )
        if was_filtered and tokens_rejected > kashiut_tokens:
            aviut_tokens = tokens_rejected - kashiut_tokens
            reasons.append(
                f"aviut ({self.aviut_mode}): {aviut_tokens} tok compressés"
            )
        if not reasons:
            reason_str = "within budget"
        else:
            reason_str = f"Masakh {self.level} — " + " + ".join(reasons)

        return {
            "timestamp": time.time(),
            "olam": self.olam,
            "aviut_level": self.level,
            "kashiut": self.kashiut,
            "aviut_mode": self.aviut_mode,
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "tokens_rejected": tokens_rejected,
            "rejection_ratio": tokens_rejected / max(tokens_before, 1),
            "was_filtered": was_filtered or bool(kashiut_rejected),
            "rejection_reason": reason_str,
            "level_changes": list(self._level_changes),
            # Kashiut-specific metrics (F1 fix)
            "kashiut_rejected_count": len(kashiut_rejected),
            "kashiut_rejected_tokens": kashiut_tokens,
            "kashiut_rejected_blocks": kashiut_rejected,
        }

    def __repr__(self) -> str:
        return (
            f"Masakh(olam={self.olam!r}, level={self.level!r}, "
            f"kashiut={self.kashiut}, aviut={self.aviut_mode!r}, "
            f"budget={self.budget_ratio:.0%})"
        )


# ── Logging PostgreSQL (optionnel) ──────────────────────────

def log_to_db(conn, entry: dict) -> None:
    """Persister une entrée de log dans masakh_log (PostgreSQL).

    NOTE: non utilisé par le pipeline — _persist_post_response()
    dans olamot.py fait son propre INSERT directement.

    Args:
        conn: Connexion psycopg2
        entry: Dict retourné par Masakh.sof()
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO masakh_log
            (olam, aviut_level, kashiut, aviut_mode,
             tokens_before, tokens_after,
             tokens_rejected, rejection_reason)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            entry["olam"],
            entry["aviut_level"],
            entry.get("kashiut", 0.0),
            entry.get("aviut_mode", "unknown"),
            entry["tokens_before"],
            entry["tokens_after"],
            entry["tokens_rejected"],
            entry["rejection_reason"],
        ),
    )
    conn.commit()
    cur.close()


# ── Double Reshimo (Phase 2c) ────────────────────────────────
#
# Après chaque appel LLM, deux Reshimot sont sauvegardées :
#   reshimo_hitlabshut = CE QUI a été fait (résultat, décision)
#   reshimo_aviut      = COMMENT le filtrage a fonctionné
#
# "Le Reshimu est la trace que la Lumière laisse après son retrait.
#  Il contient l'empreinte de ce qui était — assez pour reconstruire,
#  pas assez pour reproduire." (EC-SHK-026, PG-SHK-008)

_RESHIMOT_LOG: list[dict] = []


def write_reshimo(
    olam: str,
    hitlabshut: dict,
    aviut: dict,
    conn=None,
) -> dict:
    """Écrire un Reshimo après un appel LLM.

    Args:
        olam: L'Olam de l'appel
        hitlabshut: CE QUI a été fait — {response_summary, domain, decision, ...}
        aviut: COMMENT le filtrage a fonctionné — {masakh_level, tokens_before,
            tokens_after, kashiut, aviut_mode, kavvanah, score, ...}
        conn: Connexion PostgreSQL (optionnel) — si fourni, persiste en DB

    Returns:
        Le Reshimo complet (dict)
    """
    import time as _time

    reshimo = {
        "timestamp": _time.time(),
        "olam": olam,
        "reshimo_hitlabshut": hitlabshut,
        "reshimo_aviut": aviut,
    }

    _RESHIMOT_LOG.append(reshimo)

    if conn is not None:
        _write_reshimo_db(conn, reshimo)

    return reshimo


def _write_reshimo_db(conn, reshimo: dict) -> None:
    """Persister un Reshimo en PostgreSQL."""
    import json as _json
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reshimot (olam, reshimo_hitlabshut, reshimo_aviut)
            VALUES (%s, %s, %s)
            """,
            (
                reshimo["olam"],
                _json.dumps(reshimo["reshimo_hitlabshut"]),
                _json.dumps(reshimo["reshimo_aviut"]),
            ),
        )
        conn.commit()
        cur.close()
    except Exception as e:
        import logging
        logging.getLogger("masakh").warning("_write_reshimo_db: %s", e)
        try:
            conn.rollback()
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)


def get_reshimot(
    olam: str | None = None,
    limit: int = 20,
    conn=None,
) -> list[dict]:
    """Récupérer les derniers Reshimot.

    Args:
        olam: Filtrer par Olam (None = tous)
        limit: Nombre max de Reshimot
        conn: Connexion PostgreSQL (None = log en mémoire)

    Returns:
        Liste de Reshimot, du plus récent au plus ancien.
    """
    if conn is not None:
        return _get_reshimot_db(conn, olam, limit)

    # Mémoire
    result = _RESHIMOT_LOG
    if olam:
        result = [r for r in result if r["olam"] == olam]
    return list(reversed(result[-limit:]))


def _get_reshimot_db(conn, olam: str | None, limit: int) -> list[dict]:
    """Lire les Reshimot depuis PostgreSQL."""
    cur = conn.cursor()
    if olam:
        cur.execute(
            """
            SELECT olam, reshimo_hitlabshut, reshimo_aviut, created_at
            FROM reshimot
            WHERE olam = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (olam, limit),
        )
    else:
        cur.execute(
            """
            SELECT olam, reshimo_hitlabshut, reshimo_aviut, created_at
            FROM reshimot
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (limit,),
        )

    rows = cur.fetchall()
    cur.close()
    return [
        {
            "olam": row[0],
            "reshimo_hitlabshut": row[1],
            "reshimo_aviut": row[2],
            "timestamp": row[3].timestamp() if row[3] else 0,
        }
        for row in rows
    ]


def clear_reshimot() -> None:
    """Vider les Reshimot en mémoire."""
    _RESHIMOT_LOG.clear()


__all__ = [
    "Masakh",
    "MASAKH_LEVELS",
    "LEVEL_ORDER",
    "OLAM_DEFAULT_LEVEL",
    "AVIUT_LEVELS",
    "CHARS_PER_TOKEN",
    "HIZDAKCHUT_DEGRADE_THRESHOLD",
    "HIZDAKCHUT_UPGRADE_THRESHOLD",
    "auto_hizdakchut",
    "get_hizdakchut_levels",
    "reset_hizdakchut_levels",
    "regulate_masakh_from_partzufim",
    "get_partzufim_masakh_offset",
    "reset_partzufim_masakh_offset",
    "get_log",
    "clear_log",
    "log_to_db",
    "write_reshimo",
    "get_reshimot",
    "clear_reshimot",
]
