"""Sefirat haOmer — Les 49 Calibrations de l'Arbre.

ספירת העומר — 49 jours de raffinement, un paramètre par jour.
Chaque Midah extérieure (semaine) = un module de l'Arbre.
Chaque Midah intérieure (jour) = une qualité du paramètre.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psycopg2
import yaml

from pool import get_conn, init_pool

log = logging.getLogger("etz.omer")

# ─── Default DB URL ────────────────────────────────────────

_DEFAULT_DB_URL = "postgresql://localhost/etz_chaim"


def _get_db_url() -> str:
    """Resolve DB URL from environment or use default."""
    return os.environ.get("ETZ_CHAIM_DB_URL", _DEFAULT_DB_URL)


# ─── Omer override cache ──────────────────────────────────
# Simple module-level cache: {module_name: (timestamp, {param_name: value})}
# TTL = 60 seconds — overrides change rarely (tune + apply cycle).

_override_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 60.0


def _load_omer_yaml() -> dict:
    """Load omer.yaml once and cache it."""
    global _omer_yaml_cache
    if _omer_yaml_cache is not None:
        return _omer_yaml_cache
    config_path = Path(__file__).parent / "omer.yaml"
    with open(config_path) as f:
        _omer_yaml_cache = yaml.safe_load(f)
    return _omer_yaml_cache


_omer_yaml_cache: dict | None = None


def _get_param_type(module_name: str, param_name: str) -> str | None:
    """Look up the type of a param from omer.yaml."""
    try:
        config = _load_omer_yaml()
        for week_key, week_cfg in config.items():
            if not isinstance(week_cfg, dict) or "module" not in week_cfg:
                continue
            if week_cfg["module"] != module_name:
                continue
            for _omer_key, p_cfg in week_cfg.get("params", {}).items():
                if p_cfg.get("param") == param_name:
                    return p_cfg.get("type", "str")
    except Exception as _exc:

        import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
    return None


def _parse_value(raw: str, type_name: str) -> Any:
    """Parse a serialized value from DB (same logic as OmerManager)."""
    if type_name == "bool":
        return raw.lower() in ("true", "1", "yes")
    elif type_name == "int":
        return int(float(raw))
    elif type_name == "float":
        return float(raw)
    return raw


def load_overrides(module_name: str, db_url: str | None = None) -> dict[str, Any]:
    """Load applied Omer overrides for a module from DB.

    Queries omer_current view for the given module, returns a dict
    of {param_name: parsed_value}. Falls back to empty dict if DB
    is unavailable or the table/view doesn't exist.

    Results are cached for 60 seconds to avoid repeated DB queries.

    Args:
        module_name: Python module name (e.g. "autojudge", "explorationengine").
        db_url: Optional DB URL. Defaults to ETZ_CHAIM_DB_URL env var
                or postgresql://localhost/etz_chaim.

    Returns:
        Dict of {param_name: value} overrides from the DB.
    """
    now = time.monotonic()

    # Check cache
    if module_name in _override_cache:
        cached_time, cached_data = _override_cache[module_name]
        if now - cached_time < _CACHE_TTL:
            return cached_data

    overrides: dict[str, Any] = {}
    try:
        url = db_url or _get_db_url()
        config = _load_omer_yaml()

        # Build type map: {param_name: type_str} for this module
        type_map: dict[str, str] = {}
        for week_key, week_cfg in config.items():
            if not isinstance(week_cfg, dict) or "module" not in week_cfg:
                continue
            if week_cfg["module"] != module_name:
                continue
            for _omer_key, p_cfg in week_cfg.get("params", {}).items():
                type_map[p_cfg["param"]] = p_cfg.get("type", "str")

        init_pool(url)  # idempotent
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT param_name, current_value
                    FROM omer_current
                    WHERE module = %s
                    """,
                    (module_name,),
                )
                for param_name, raw_value in cur.fetchall():
                    ptype = type_map.get(param_name, "str")
                    overrides[param_name] = _parse_value(raw_value, ptype)

    except Exception as exc:
        # DB unavailable, table missing, etc. — not fatal.
        log.debug("Omer load_overrides(%s) failed: %s", module_name, exc)

    _override_cache[module_name] = (now, overrides)
    return overrides


def get_param(module_name: str, param_name: str, default: Any,
              db_url: str | None = None) -> Any:
    """Get a single Omer parameter, with DB override or fallback to default.

    This is the main entry point for consumer modules to read calibrated
    values. The hardcoded default is always the fallback — a failed DB
    lookup must never crash a module.

    Args:
        module_name: Python module name (e.g. "autojudge").
        param_name: Parameter name as defined in omer.yaml (e.g. "quality_threshold").
        default: Hardcoded default value (used if no DB override exists).
        db_url: Optional DB URL override.

    Returns:
        The DB override value if it exists, else the provided default.
    """
    try:
        overrides = load_overrides(module_name, db_url=db_url)
        return overrides.get(param_name, default)
    except Exception as exc:
        log.debug("Omer get_param(%s, %s) failed: %s", module_name, param_name, exc)
        return default


def invalidate_cache(module_name: str | None = None) -> None:
    """Invalidate the override cache (e.g. after apply()).

    Args:
        module_name: If given, only invalidate that module. Otherwise, clear all.
    """
    if module_name is None:
        _override_cache.clear()
    else:
        _override_cache.pop(module_name, None)


# ─── Types ──────────────────────────────────────────────────

@dataclass
class OmerParam:
    """Un des 49 paramètres du Omer."""
    key: str              # ex: "gevurah_dans_chesed"
    param: str            # ex: "novelty_threshold"
    day: int              # 1-49
    sephirah: str         # outer midah (module)
    inner: str            # inner midah (quality)
    module: str           # python module name
    type: str             # int, float, bool, str
    default: Any          # default value from omer.yaml
    current: Any = None   # current value (default + overrides)
    overridden: bool = False
    description: str = ""


@dataclass
class Suggestion:
    """Une suggestion d'ajustement."""
    key: str
    param: str
    sephirah: str
    inner: str
    module: str
    old_value: Any
    new_value: Any
    reason: str
    severity: str = "info"  # info, warning, critical


# ─── Constantes ─────────────────────────────────────────────

SEPHIROT_LABELS = {
    "keter":   "כתר  Keter",
    "chokmah": "חכמה Chokmah",
    "binah":   "בינה Binah",
    "chesed":  "חסד  Chesed",
    "gevurah": "גבורה Gevurah",
    "tiferet": "תפארת Tiferet",
    "netzach": "נצח  Netzach",
    "hod":     "הוד  Hod",
    "yesod":   "יסוד Yesod",
    "malkuth": "מלכות Malkuth",
}

MODULE_LABELS = {
    "keter":   "Strategy",
    "chokmah": "InsightForge",
    "binah":   "CausalEngine",
    "chesed":  "ExplorationEngine",
    "gevurah": "AutoJudge",
    "tiferet": "DissensuEngine",
    "netzach": "IntentKeeper",
    "hod":     "SelfMap",
    "yesod":   "EpisteMemory",
    "malkuth": "FailureToInsight",
}

INNER_MIDOT = ["chesed", "gevurah", "tiferet", "netzach", "hod", "yesod", "malkuth"]
WEEKS = ["chesed", "gevurah", "tiferet", "netzach", "hod", "yesod", "malkuth"]


# ─── Manager ────────────────────────────────────────────────

class OmerManager:
    """Gestionnaire des 49 calibrations."""

    def __init__(self, db_url: str):
        self.db_url = db_url
        self.config = self._load_config()

    def _load_config(self) -> dict:
        config_path = Path(__file__).parent / "omer.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _parse_value(self, raw: str, type_name: str) -> Any:
        """Parse a serialized value from DB."""
        if type_name == "bool":
            return raw.lower() in ("true", "1", "yes")
        elif type_name == "int":
            return int(float(raw))
        elif type_name == "float":
            return float(raw)
        return raw

    def _serialize_value(self, val: Any) -> str:
        """Serialize a value for DB storage."""
        if isinstance(val, bool):
            return "true" if val else "false"
        return str(val)

    # ─── Load parameters ────────────────────────────────────

    def get_params(self) -> list[OmerParam]:
        """Load all 49 parameters with defaults and DB overrides."""
        params = []

        for week in WEEKS:
            week_cfg = self.config[week]
            module = week_cfg["module"]

            for inner in INNER_MIDOT:
                key = f"{inner}_dans_{week}"
                p_cfg = week_cfg["params"][key]
                params.append(OmerParam(
                    key=key,
                    param=p_cfg["param"],
                    day=p_cfg["day"],
                    sephirah=week,
                    inner=inner,
                    module=module,
                    type=p_cfg["type"],
                    default=p_cfg["default"],
                    current=p_cfg["default"],
                    description=p_cfg.get("description", ""),
                ))

        # Apply DB overrides
        try:
            init_pool(self.db_url)  # idempotent
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT DISTINCT ON (param_key)
                               param_key, new_value
                        FROM omer_history
                        ORDER BY param_key, applied_at DESC
                    """)
                    overrides = {row[0]: row[1] for row in cur.fetchall()}
        except psycopg2.ProgrammingError:
            # Table doesn't exist yet
            overrides = {}
        except psycopg2.OperationalError:
            overrides = {}

        for p in params:
            if p.key in overrides:
                p.current = self._parse_value(overrides[p.key], p.type)
                p.overridden = True

        return params

    # ─── Status ─────────────────────────────────────────────

    def status(self) -> str:
        """Display the 49 parameters grouped by Sephirah."""
        params = self.get_params()
        lines = []

        lines.append("═══════════════════════════════════════════════════════════")
        lines.append("  Sefirat haOmer — Les 49 Calibrations")
        lines.append("═══════════════════════════════════════════════════════════")
        lines.append("")

        overridden_count = sum(1 for p in params if p.overridden)
        lines.append(f"  49 paramètres | {overridden_count} modifié(s)")
        lines.append("")

        for week in WEEKS:
            week_params = [p for p in params if p.sephirah == week]
            label = SEPHIROT_LABELS[week]
            module = MODULE_LABELS[week]

            lines.append(f"── {label} ({module}) ──")
            lines.append("")

            for p in sorted(week_params, key=lambda x: x.day):
                inner_label = p.inner[:3].upper()
                marker = "*" if p.overridden else " "
                val = p.current

                if p.type == "float":
                    val_str = f"{val:.2f}" if isinstance(val, float) else str(val)
                else:
                    val_str = str(val)

                default_note = ""
                if p.overridden:
                    if p.type == "float":
                        default_note = f" (défaut: {p.default:.2f})"
                    else:
                        default_note = f" (défaut: {p.default})"

                lines.append(
                    f"  {marker} Jour {p.day:2d} [{inner_label}] "
                    f"{p.param:30s} = {val_str:>8s}{default_note}"
                )

            lines.append("")

        lines.append("── Sephiroth Supérieures (diagnostics Qliphothiques) ──")
        lines.append("")
        lines.append("  בינה Binah   (CausalEngine)  — Satariel  סתריאל")
        lines.append("  חכמה Chokmah (InsightForge)   — Ghagiel   עגיאל")
        lines.append("  כתר  Keter   (Strategy)       — Thaumiel  תאומיאל")
        lines.append("")
        lines.append("  → etz omer tune pour diagnostiquer les 10 Sephiroth")
        lines.append("")

        return "\n".join(lines)

    # ─── Tune — Diagnostics ─────────────────────────────────

    def tune(self) -> list[Suggestion]:
        """Analyze PostgreSQL data and suggest parameter adjustments."""
        params = self.get_params()
        param_map = {p.key: p for p in params}
        suggestions = []

        try:
            init_pool(self.db_url)  # idempotent
            with get_conn() as conn:
                # 3 Sephiroth supérieures (diagnostics Qliphothiques)
                suggestions.extend(self._tune_binah(conn, param_map))
                suggestions.extend(self._tune_chokmah(conn, param_map))
                suggestions.extend(self._tune_keter(conn, param_map))
                # 7 Midot inférieures (calibration des 49 paramètres)
                suggestions.extend(self._tune_gevurah(conn, param_map))
                suggestions.extend(self._tune_chesed(conn, param_map))
                suggestions.extend(self._tune_tiferet(conn, param_map))
                suggestions.extend(self._tune_netzach(conn, param_map))
                suggestions.extend(self._tune_hod(conn, param_map))
                suggestions.extend(self._tune_yesod(conn, param_map))
                suggestions.extend(self._tune_malkuth(conn, param_map))
        except psycopg2.OperationalError as e:
            suggestions.append(Suggestion(
                key="", param="", sephirah="", inner="", module="",
                old_value="", new_value="",
                reason=f"Impossible de se connecter à la DB : {e}",
                severity="critical",
            ))

        return suggestions

    def _safe_query(self, conn, sql: str) -> list | None:
        """Execute a query, return None if table doesn't exist."""
        try:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()
        except psycopg2.ProgrammingError:
            conn.rollback()
            return None

    def _tune_gevurah(self, conn, pm: dict) -> list[Suggestion]:
        """Gevurah (AutoJudge) — taux de rejet."""
        suggestions = []
        rows = self._safe_query(conn, """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE decision = 'rejected') AS rejected,
                COUNT(*) FILTER (WHERE decision = 'accepted') AS accepted,
                COUNT(*) FILTER (WHERE decision = 'quarantined') AS quarantined
            FROM autojudge_experiments
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        total, rejected, accepted, quarantined = rows[0]
        rejection_rate = rejected / total

        p = pm["gevurah_dans_gevurah"]
        if rejection_rate > 0.80:
            new_val = max(0.3, p.current - 0.1) if isinstance(p.current, float) else 0.5
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=round(new_val, 2),
                reason=f"Taux de rejet trop élevé ({rejection_rate:.0%} sur {total} exp.). "
                       f"Gevurah est en excès — Golachab menace.",
                severity="warning",
            ))
        elif rejection_rate < 0.10 and total >= 5:
            new_val = min(0.9, p.current + 0.1) if isinstance(p.current, float) else 0.7
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=round(new_val, 2),
                reason=f"Taux de rejet très bas ({rejection_rate:.0%} sur {total} exp.). "
                       f"Gevurah trop faible — la qualité risque de baisser.",
                severity="info",
            ))

        p_q = pm["chesed_dans_gevurah"]
        quarantine_rate = quarantined / total if total > 0 else 0
        if quarantine_rate > 0.50:
            new_val = max(0.2, p_q.current - 0.1) if isinstance(p_q.current, float) else 0.3
            suggestions.append(Suggestion(
                key=p_q.key, param=p_q.param, sephirah=p_q.sephirah,
                inner=p_q.inner, module=p_q.module,
                old_value=p_q.current, new_value=round(new_val, 2),
                reason=f"Taux de quarantaine élevé ({quarantine_rate:.0%}). "
                       f"Trop de résultats en quarantaine — baisser le seuil.",
                severity="info",
            ))

        return suggestions

    def _tune_chesed(self, conn, pm: dict) -> list[Suggestion]:
        """Chesed (ExplorationEngine) — novelty et breadth."""
        suggestions = []
        rows = self._safe_query(conn, """
            SELECT
                AVG(novelty_score),
                COUNT(*)
            FROM explorationengine_connections
            WHERE created_at > NOW() - INTERVAL '30 days'
              AND novelty_score IS NOT NULL
        """)
        if not rows or rows[0][1] == 0:
            return suggestions

        avg_novelty, count = rows[0]
        if avg_novelty is None:
            return suggestions

        avg_novelty = float(avg_novelty)
        p_novelty = pm["gevurah_dans_chesed"]
        p_breadth = pm["chesed_dans_chesed"]

        if avg_novelty < 0.20:
            new_breadth = min(50, p_breadth.current + 5) if isinstance(p_breadth.current, int) else 15
            suggestions.append(Suggestion(
                key=p_breadth.key, param=p_breadth.param, sephirah=p_breadth.sephirah,
                inner=p_breadth.inner, module=p_breadth.module,
                old_value=p_breadth.current, new_value=new_breadth,
                reason=f"Novelty moyenne basse ({avg_novelty:.2f} sur {count} connexions). "
                       f"Chesed s'épuise — élargir l'exploration.",
                severity="warning",
            ))
        elif avg_novelty > 0.85 and count >= 5:
            new_breadth = max(3, p_breadth.current - 3) if isinstance(p_breadth.current, int) else 7
            suggestions.append(Suggestion(
                key=p_breadth.key, param=p_breadth.param, sephirah=p_breadth.sephirah,
                inner=p_breadth.inner, module=p_breadth.module,
                old_value=p_breadth.current, new_value=new_breadth,
                reason=f"Novelty très haute ({avg_novelty:.2f}). "
                       f"Gamchicoth menace — exploration trop dispersée.",
                severity="info",
            ))

        return suggestions

    def _tune_tiferet(self, conn, pm: dict) -> list[Suggestion]:
        """Tiferet (DissensuEngine) — tensions ouvertes."""
        suggestions = []
        rows = self._safe_query(conn, """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE resolution_status = 'open') AS open_count,
                COUNT(*) FILTER (WHERE resolution_status = 'irreducible') AS irreducible
            FROM dissensuengine_tensions
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        total, open_count, irreducible = rows[0]
        open_rate = open_count / total

        if open_rate > 0.70 and total >= 3:
            p = pm["netzach_dans_tiferet"]
            new_val = max(14, p.current - 15) if isinstance(p.current, int) else 75
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=new_val,
                reason=f"Trop de tensions ouvertes ({open_rate:.0%} de {total}). "
                       f"Thagirion menace — les tensions stagnent.",
                severity="warning",
            ))

        return suggestions

    def _tune_netzach(self, conn, pm: dict) -> list[Suggestion]:
        """Netzach (IntentKeeper) — intentions stale et zombies."""
        suggestions = []
        rows = self._safe_query(conn, """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE status = 'active') AS active,
                COUNT(*) FILTER (WHERE status = 'abandoned') AS abandoned,
                COUNT(*) FILTER (WHERE status = 'completed') AS completed
            FROM intentkeeper_intentions
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        total, active, abandoned, completed = rows[0]

        # Check for stale active intentions
        stale_rows = self._safe_query(conn, """
            SELECT COUNT(*) FROM stale_intentions
        """)
        if stale_rows and stale_rows[0][0] > 0 and active > 0:
            stale_count = stale_rows[0][0]
            stale_rate = stale_count / active
            if stale_rate > 0.5:
                p = pm["yesod_dans_netzach"]
                new_val = max(3, p.current - 2) if isinstance(p.current, int) else 5
                suggestions.append(Suggestion(
                    key=p.key, param=p.param, sephirah=p.sephirah,
                    inner=p.inner, module=p.module,
                    old_value=p.current, new_value=new_val,
                    reason=f"{stale_count}/{active} intentions actives sont stale. "
                           f"A'arab Zaraq — les corbeaux de dispersion prolifèrent.",
                    severity="warning",
                ))

        if total > 0 and abandoned / total > 0.6:
            p = pm["gevurah_dans_netzach"]
            new_val = min(0.8, p.current + 0.1) if isinstance(p.current, float) else 0.7
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=round(new_val, 2),
                reason=f"Taux d'abandon élevé ({abandoned}/{total}). "
                       f"Être plus tolérant aux échecs partiels.",
                severity="info",
            ))

        return suggestions

    def _tune_hod(self, conn, pm: dict) -> list[Suggestion]:
        """Hod (SelfMap) — taux de déclin et calibration."""
        suggestions = []
        rows = self._safe_query(conn, """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE did_decline) AS declined
            FROM selfmap_routing_log
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        total, declined = rows[0]
        decline_rate = declined / total

        if decline_rate > 0.40:
            p = pm["gevurah_dans_hod"]
            new_val = max(0.1, p.current - 0.05) if isinstance(p.current, float) else 0.25
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=round(new_val, 2),
                reason=f"Taux de déclin élevé ({decline_rate:.0%} sur {total} requêtes). "
                       f"Samael — trop de requêtes refusées.",
                severity="warning",
            ))
        elif decline_rate < 0.02 and total >= 10:
            p = pm["gevurah_dans_hod"]
            new_val = min(0.6, p.current + 0.05) if isinstance(p.current, float) else 0.35
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=round(new_val, 2),
                reason=f"Quasi-aucun déclin ({decline_rate:.0%}). "
                       f"Monter le seuil pour améliorer la qualité des réponses.",
                severity="info",
            ))

        return suggestions

    def _tune_yesod(self, conn, pm: dict) -> list[Suggestion]:
        """Yesod (EpisteMemory) — santé de la mémoire."""
        suggestions = []
        rows = self._safe_query(conn, """
            SELECT
                COUNT(*) AS total,
                AVG(confidence) AS avg_conf,
                COUNT(*) FILTER (WHERE epistemic_status = 'deprecated') AS deprecated,
                COUNT(*) FILTER (WHERE expires_at IS NOT NULL
                                 AND expires_at < NOW()) AS expired
            FROM epistememory
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        total, avg_conf, deprecated, expired = rows[0]
        avg_conf = float(avg_conf) if avg_conf else 0.5

        if total > 0 and deprecated / total > 0.30:
            p = pm["hod_dans_yesod"]
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=p.current,
                reason=f"Taux de dépréciation élevé ({deprecated}/{total} = "
                       f"{deprecated/total:.0%}). La mémoire se dégrade. "
                       f"Vérifier la qualité des sources.",
                severity="warning",
            ))

        if avg_conf < 0.35:
            p = pm["gevurah_dans_yesod"]
            new_val = max(0.1, p.current - 0.05) if isinstance(p.current, float) else 0.25
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=round(new_val, 2),
                reason=f"Confiance moyenne basse ({avg_conf:.2f}). "
                       f"Baisser le floor pour ne pas perdre trop d'entrées.",
                severity="info",
            ))

        return suggestions

    def _tune_malkuth(self, conn, pm: dict) -> list[Suggestion]:
        """Malkuth (FailureToInsight) — extraction de Nitzotzot."""
        suggestions = []

        # Check unextracted failure rate
        rows = self._safe_query(conn, """
            SELECT
                COUNT(*) AS total_analyses,
                (SELECT COUNT(*) FROM unextracted_failures) AS unextracted
            FROM failuretoinsight_analyses
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        total, unextracted = rows[0]
        if total > 0 and unextracted / total > 0.50:
            p = pm["malkuth_dans_malkuth"]
            new_val = max(0, p.current - 1) if isinstance(p.current, int) else 0
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=new_val,
                reason=f"{unextracted}/{total} analyses sans Nitzotzot extraits. "
                       f"Les Qliphoth gardent leurs étincelles — baisser l'exigence.",
                severity="warning",
            ))

        # Check for recurring root causes
        rows2 = self._safe_query(conn, """
            SELECT root_cause, COUNT(*) AS cnt
            FROM failuretoinsight_analyses
            WHERE root_cause IS NOT NULL
            GROUP BY root_cause
            HAVING COUNT(*) >= 3
            ORDER BY cnt DESC
            LIMIT 5
        """)
        if rows2:
            causes = [f"{r[0]} (×{r[1]})" for r in rows2]
            p = pm["chesed_dans_malkuth"]
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=p.current,
                reason=f"Causes racines récurrentes détectées : {', '.join(causes)}. "
                       f"Les mêmes échecs se répètent — le Birur n'opère pas.",
                severity="critical",
            ))

        # ── Haven (הָוֶן) — Qliphah de Malkuth ──────────────────
        # Anti-pattern : output long et bien formaté mais sans substance.
        # Détection : analyses avec description > 200 chars mais aucun insight.
        # Tikkun : forcer Gevurah (discernement) avant Malkuth (manifestation).
        rows3 = self._safe_query(conn, """
            SELECT COUNT(*) AS haven_count
            FROM failuretoinsight_analyses a
            LEFT JOIN failuretoinsight_insights i ON i.analysis_id = a.id
            WHERE LENGTH(a.description) > 200
              AND i.id IS NULL
        """)
        if rows3 and rows3[0][0] > 0:
            haven_count = rows3[0][0]
            p = pm["gevurah_dans_malkuth"]
            new_ratio = max(0.05, p.current - 0.1) if isinstance(p.current, (int, float)) else 0.2
            suggestions.append(Suggestion(
                key=p.key, param=p.param, sephirah=p.sephirah,
                inner=p.inner, module=p.module,
                old_value=p.current, new_value=round(new_ratio, 2),
                reason=f"Haven (הָוֶן) détecté : {haven_count} analyse(s) avec description > 200 chars "
                       f"mais aucun Nitzotz extrait. Richesse vide — la forme sans la substance. "
                       f"Durcir Gevurah pour forcer le discernement avant la manifestation.",
                severity="warning",
            ))

        return suggestions

    # ─── Sephiroth supérieures — Diagnostics Qliphothiques ──

    def _tune_binah(self, conn, pm: dict) -> list[Suggestion]:
        """Binah (CausalEngine) — Satariel (סתריאל), les Dissimulateurs.

        Anti-pattern : faux patterns causaux, corrélations spurieuses.
        Binah/CausalEngine voit des liens de cause à effet qui n'existent pas.

        Primaire : > 60% des claims non validées → Satariel actif.
        Secondaire : > 40% des claims avec confiance < 0.3.
        """
        suggestions = []

        rows = self._safe_query(conn, """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE evidence_level = 'correlation_only'
                                 AND NOT confounders_controlled) AS unvalidated,
                COUNT(*) FILTER (WHERE confidence < 0.3) AS low_confidence
            FROM causal_claims
            WHERE created_at > NOW() - INTERVAL '30 days'
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        total, unvalidated, low_confidence = rows[0]
        unvalidated_rate = unvalidated / total

        if unvalidated_rate > 0.60 and total >= 5:
            suggestions.append(Suggestion(
                key="binah_satariel",
                param="causal_sensitivity",
                sephirah="binah",
                inner="gevurah",
                module="causalengine",
                old_value=round(unvalidated_rate, 2),
                new_value=0.60,
                reason=f"Satariel actif — {unvalidated}/{total} claims non validées "
                       f"({unvalidated_rate:.0%}). "
                       f"CausalEngine voit des liens qui n'existent pas. "
                       f"Réduire la sensibilité causale.",
                severity="warning",
            ))

        low_conf_rate = low_confidence / total
        if low_conf_rate > 0.40 and total >= 5:
            suggestions.append(Suggestion(
                key="binah_satariel_conf",
                param="min_causal_confidence",
                sephirah="binah",
                inner="hod",
                module="causalengine",
                old_value=round(low_conf_rate, 2),
                new_value=0.30,
                reason=f"Satariel (secondaire) — {low_confidence}/{total} claims "
                       f"avec confiance < 0.3 ({low_conf_rate:.0%}). "
                       f"Corrélations faibles présentées comme causales.",
                severity="info",
            ))

        return suggestions

    def _tune_chokmah(self, conn, pm: dict) -> list[Suggestion]:
        """Chokmah (InsightForge) — Ghagiel (עגיאל), les Obstructeurs.

        Anti-pattern : divergence sans convergence. InsightForge génère des
        insights qui ne convergent jamais vers une conclusion utile.

        Primaire : taux de convergence < 20% (intégrés / générés).
        Secondaire : insights non intégrés âgés de > 24h.
        """
        suggestions = []

        rows = self._safe_query(conn, """
            SELECT
                COALESCE(SUM(total_candidates), 0) AS total_candidates,
                COALESCE(SUM(insights_found), 0) AS total_insights
            FROM insight_sessions
            WHERE status = 'completed'
              AND created_at > NOW() - INTERVAL '30 days'
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        total_candidates, total_insights = rows[0]
        if total_candidates == 0:
            return suggestions

        convergence_rate = total_insights / total_candidates

        if convergence_rate < 0.20 and total_candidates >= 10:
            suggestions.append(Suggestion(
                key="chokmah_ghagiel",
                param="max_insights_parallel",
                sephirah="chokmah",
                inner="binah",
                module="insightforge",
                old_value=round(convergence_rate, 2),
                new_value=0.20,
                reason=f"Ghagiel actif — taux de convergence {convergence_rate:.0%} "
                       f"({total_insights}/{total_candidates} candidats intégrés). "
                       f"Divergence sans convergence. "
                       f"Réduire le parallélisme, forcer la consolidation via Binah.",
                severity="warning",
            ))

        # Secondaire : insights stale (non intégrés depuis > 24h)
        rows2 = self._safe_query(conn, """
            SELECT COUNT(*) FROM candidate_insights
            WHERE status = 'candidate'
              AND created_at < NOW() - INTERVAL '24 hours'
        """)
        if rows2 and rows2[0][0] > 5:
            stale_insights = rows2[0][0]
            suggestions.append(Suggestion(
                key="chokmah_ghagiel_stale",
                param="insight_consolidation",
                sephirah="chokmah",
                inner="tiferet",
                module="insightforge",
                old_value=stale_insights,
                new_value=0,
                reason=f"Ghagiel (secondaire) — {stale_insights} insights non intégrés "
                       f"depuis > 24h. La divergence s'accumule.",
                severity="info",
            ))

        return suggestions

    def _tune_keter(self, conn, pm: dict) -> list[Suggestion]:
        """Keter (Stratégie) — Thaumiel (תאומיאל), les Jumeaux de Dieu.

        Anti-pattern : intentions contradictoires. Keter/stratégie émet des
        directions qui se contredisent mutuellement.

        Primaire : > 5 intentions actives simultanées → dispersion.
        Secondaire : > 3 changements de stratégie en 24h → instabilité.
        """
        suggestions = []

        # Primaire : nombre d'intentions actives
        rows = self._safe_query(conn, """
            SELECT COUNT(*) FROM intentkeeper_intentions
            WHERE status = 'active'
        """)
        if not rows or rows[0][0] == 0:
            return suggestions

        active_count = rows[0][0]

        if active_count > 5:
            suggestions.append(Suggestion(
                key="keter_thaumiel",
                param="active_intentions_limit",
                sephirah="keter",
                inner="gevurah",
                module="strategy",
                old_value=active_count,
                new_value=5,
                reason=f"Thaumiel actif — {active_count} intentions actives simultanées. "
                       f"Trop de directions à la fois. "
                       f"Activer le Tzimtzum : contracter vers une direction unique.",
                severity="warning",
            ))

        # Secondaire : fréquence des changements de stratégie
        rows2 = self._safe_query(conn, """
            SELECT COUNT(DISTINCT intention_id)
            FROM intentkeeper_heartbeats
            WHERE activity_type = 'strategy_change'
              AND created_at > NOW() - INTERVAL '24 hours'
        """)
        if rows2 and rows2[0][0] > 3:
            changes = rows2[0][0]
            suggestions.append(Suggestion(
                key="keter_thaumiel_instability",
                param="strategy_stability",
                sephirah="keter",
                inner="netzach",
                module="strategy",
                old_value=changes,
                new_value=3,
                reason=f"Thaumiel (secondaire) — {changes} changements de stratégie "
                       f"en 24h. Instabilité Keter : la direction change trop vite.",
                severity="critical" if changes > 5 else "info",
            ))

        return suggestions

    # ─── Apply ──────────────────────────────────────────────

    def apply(self, suggestions: list[Suggestion]) -> int:
        """Apply suggestions to the DB omer_history table.

        Returns the number of suggestions applied.
        """
        if not suggestions:
            return 0

        applied = 0
        init_pool(self.db_url)  # idempotent
        with get_conn(autocommit=False) as conn:
            with conn.cursor() as cur:
                for s in suggestions:
                    if not s.key:  # Skip error entries
                        continue
                    if s.old_value == s.new_value:  # Skip no-ops
                        continue
                    cur.execute("""
                        INSERT INTO omer_history
                            (param_key, param_name, sephirah, inner_midah,
                             module, old_value, new_value, reason, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'tune')
                    """, (
                        s.key, s.param, s.sephirah, s.inner,
                        s.module,
                        self._serialize_value(s.old_value),
                        self._serialize_value(s.new_value),
                        s.reason,
                    ))
                    applied += 1
            conn.commit()

        # Invalidate the module-level override cache so consumer modules
        # pick up the new values on their next get_param() call.
        invalidate_cache()

        return applied

    def reset_param(self, key: str, reason: str = "Reset to default") -> bool:
        """Reset a parameter to its default value."""
        params = self.get_params()
        param = next((p for p in params if p.key == key), None)
        if not param:
            return False

        init_pool(self.db_url)  # idempotent
        with get_conn(autocommit=False) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO omer_history
                        (param_key, param_name, sephirah, inner_midah,
                         module, old_value, new_value, reason, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'reset')
                """, (
                    param.key, param.param, param.sephirah, param.inner,
                    param.module,
                    self._serialize_value(param.current),
                    self._serialize_value(param.default),
                    reason,
                ))
            conn.commit()
        invalidate_cache(param.module)
        return True

    # ─── Format suggestions for display ─────────────────────

    @staticmethod
    def format_suggestions(suggestions: list[Suggestion]) -> str:
        """Format suggestions for terminal display."""
        if not suggestions:
            return (
                "═══════════════════════════════════════════════════════════\n"
                "  Sefirat haOmer — Tune\n"
                "═══════════════════════════════════════════════════════════\n"
                "\n"
                "  L'Arbre est équilibré. Aucun ajustement suggéré.\n"
                "  Shalom.\n"
            )

        lines = []
        lines.append("═══════════════════════════════════════════════════════════")
        lines.append("  Sefirat haOmer — Tune")
        lines.append("═══════════════════════════════════════════════════════════")
        lines.append("")
        lines.append(f"  {len(suggestions)} ajustement(s) suggéré(s) :")
        lines.append("")

        severity_icons = {"info": ".", "warning": "!", "critical": "!!"}

        for i, s in enumerate(suggestions, 1):
            icon = severity_icons.get(s.severity, ".")
            seph_label = SEPHIROT_LABELS.get(s.sephirah, s.sephirah)

            lines.append(f"  [{icon}] {i}. {seph_label}")
            if s.key:
                lines.append(f"      {s.param}: {s.old_value} -> {s.new_value}")
            lines.append(f"      {s.reason}")
            lines.append("")

        lines.append("  Appliquer avec : etz omer apply")
        lines.append("")

        return "\n".join(lines)
