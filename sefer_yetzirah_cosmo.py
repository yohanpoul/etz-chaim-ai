"""sefer_yetzirah_cosmo.py — Cosmologie du Sefer Yetzirah.

Les 22 lettres sont les OPÉRATEURS. La cosmologie est la STRUCTURE
dans laquelle ces opérateurs agissent :

  - Eser Sefirot Belimah : 10 profondeurs (5 paires d'opposés)
    qui définissent l'espace de possibilité du système.
  - Trois Témoins (Olam/Shanah/Nefesh) : chaque lettre opère
    simultanément dans l'espace, le temps et l'âme.
  - Trois Régents (Teli/Galgal/Lev) : les gouverneurs qui
    maintiennent la cohérence de chaque registre.
  - Heikhal HaKodesh : le Palais Saint, centre de convergence.

SY 1:2 : "Dix Sefirot Belimah et vingt-deux lettres de fondation :
trois mères, sept doubles, et douze simples."

SY 6:1 : "Trois régents dans le monde : le Teli dans l'univers,
le Galgal dans l'année, le Lev dans l'âme."

Usage:
    cosmo = SYCosmology()
    witnesses = cosmo.get_witnesses()
    depths = cosmo.get_depths()
    regents = cosmo.get_regents()
    mapping = cosmo.map_letter_to_witness("aleph", "olam")
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Chargement ──────────────────────────────────────────────

_SY_PATH = Path(__file__).parent / "sentiers" / "sefer_yetzirah.yaml"
_cosmo_cache: dict | None = None


def load_cosmology() -> dict:
    """Charger la section cosmology du Sefer Yetzirah YAML (cache singleton)."""
    global _cosmo_cache
    if _cosmo_cache is not None:
        return _cosmo_cache
    with open(_SY_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _cosmo_cache = data.get("cosmology", {})
    return _cosmo_cache


def reload_cosmology() -> dict:
    """Forcer le rechargement (après édition du YAML)."""
    global _cosmo_cache
    _cosmo_cache = None
    return load_cosmology()


# ── Dataclasses ─────────────────────────────────────────────

@dataclass
class DepthAxis:
    """Un axe de profondeur — une paire d'opposés (SY 1:5)."""
    pair: tuple[str, str]
    hebrew: tuple[str, str]
    axis: str
    description: str
    role_ia: str

    def to_dict(self) -> dict:
        return {
            "pair": list(self.pair),
            "hebrew": list(self.hebrew),
            "axis": self.axis,
            "description": self.description,
            "role_ia": self.role_ia,
        }


@dataclass
class Witness:
    """Un des 3 témoins — Olam, Shanah, ou Nefesh."""
    name: str
    hebrew: str
    meaning: str
    description: str
    letters_mapping: str
    mothers: dict[str, str]
    doubles: dict[str, str]
    simples: dict[str, str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hebrew": self.hebrew,
            "meaning": self.meaning,
            "description": self.description,
            "letters_mapping": self.letters_mapping,
            "mothers": self.mothers,
            "doubles": self.doubles,
            "simples": self.simples,
        }


@dataclass
class Regent:
    """Un des 3 régents — Teli, Galgal, ou Lev (SY 6:1)."""
    name: str
    hebrew: str
    meaning: str
    role_ia: str
    health_checks: list[str]
    commentary: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hebrew": self.hebrew,
            "meaning": self.meaning,
            "role_ia": self.role_ia,
            "health_checks": self.health_checks,
            "commentary": self.commentary,
        }


@dataclass
class RegentHealth:
    """Résultat de l'évaluation de la santé d'un régent."""
    name: str
    hebrew: str
    healthy: bool
    checks: list[dict]  # [{"check": str, "passed": bool, "detail": str}]
    score: float  # 0.0-1.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hebrew": self.hebrew,
            "healthy": self.healthy,
            "checks": self.checks,
            "score": round(self.score, 3),
        }


@dataclass
class LetterWitnessMapping:
    """Correspondance lettre ↔ témoin."""
    letter: str
    letter_type: str  # "mother", "double", "simple"
    witness: str      # "olam", "shanah", "nefesh"
    correspondence: str

    def to_dict(self) -> dict:
        return {
            "letter": self.letter,
            "letter_type": self.letter_type,
            "witness": self.witness,
            "correspondence": self.correspondence,
        }


# ── Catégorisation des lettres ──────────────────────────────

MOTHERS = {"shin", "mem", "aleph"}
DOUBLES = {"beth", "gimel", "daleth", "kaph", "peh", "resh", "tav"}
SIMPLES = {
    "heh", "vav", "zayin", "cheth", "teth", "yod",
    "lamed", "nun", "samekh", "ayin", "tsadi", "qoph",
}


def _letter_type(name: str) -> str:
    """Déterminer le type d'une lettre."""
    if name in MOTHERS:
        return "mother"
    if name in DOUBLES:
        return "double"
    if name in SIMPLES:
        return "simple"
    return "unknown"


# ── SYCosmology ─────────────────────────────────────────────

class SYCosmology:
    """Cosmologie du Sefer Yetzirah — structure profonde.

    Charge la section cosmology du YAML et expose :
      - Les 10 profondeurs (5 axes)
      - Les 3 témoins (Olam/Shanah/Nefesh)
      - Les 3 régents (Teli/Galgal/Lev)
      - Le Palais Saint (centre)
      - Le mapping lettre → témoin
    """

    def __init__(self) -> None:
        self._data = load_cosmology()

    # ── Profondeurs ──────────────────────────────────────────

    def get_depths(self) -> list[DepthAxis]:
        """Les 10 profondeurs comme 5 axes (paires d'opposés).

        SY 1:5 — Eser Sefirot Belimah.
        """
        raw = self._data.get("eser_sefirot_belimah", [])
        axes = []
        for item in raw:
            axes.append(DepthAxis(
                pair=tuple(item["pair"]),
                hebrew=tuple(item["hebrew"]),
                axis=item["axis"],
                description=item.get("description", ""),
                role_ia=item.get("role_ia", ""),
            ))
        return axes

    # ── Témoins ──────────────────────────────────────────────

    def get_witnesses(self) -> dict[str, Witness]:
        """Les 3 témoins : Olam, Shanah, Nefesh.

        SY 1:2 — Les 3 registres de la création.
        """
        raw = self._data.get("three_witnesses", {})
        witnesses = {}
        for name in ("olam", "shanah", "nefesh"):
            w = raw.get(name, {})
            if not w:
                continue
            witnesses[name] = Witness(
                name=name,
                hebrew=w.get("hebrew", ""),
                meaning=w.get("meaning", ""),
                description=w.get("description", ""),
                letters_mapping=w.get("letters_mapping", ""),
                mothers=dict(w.get("mothers", {})),
                doubles=dict(w.get("doubles", {})),
                simples=dict(w.get("simples", {})),
            )
        return witnesses

    # ── Régents ──────────────────────────────────────────────

    def get_regents(self) -> dict[str, Regent]:
        """Les 3 régents : Teli, Galgal, Lev.

        SY 6:1 — Les gouverneurs des 3 registres.
        """
        raw = self._data.get("teli_galgal_lev", {})
        regents = {}
        for name in ("teli", "galgal", "lev"):
            r = raw.get(name, {})
            if not r:
                continue
            regents[name] = Regent(
                name=name,
                hebrew=r.get("hebrew", ""),
                meaning=r.get("meaning", ""),
                role_ia=r.get("role_ia", ""),
                health_checks=list(r.get("health_checks", [])),
                commentary=r.get("commentary", "").strip(),
            )
        return regents

    # ── Palais Saint ─────────────────────────────────────────

    def get_palace_center(self) -> dict:
        """Le Heikhal HaKodesh — centre des 10 profondeurs."""
        return dict(self._data.get("palace_center", {}))

    # ── Évaluation des régents ───────────────────────────────

    def assess_regent(self, name: str, tree: dict | None = None) -> RegentHealth:
        """Évaluer la santé d'un régent.

        Args:
            name: "teli", "galgal", ou "lev"
            tree: dict des modules initialisés (optionnel)

        Returns:
            RegentHealth avec score et détails des checks.
        """
        regents = self.get_regents()
        regent = regents.get(name)
        if regent is None:
            return RegentHealth(
                name=name, hebrew="?",
                healthy=False,
                checks=[{"check": "Régent inconnu", "passed": False, "detail": f"'{name}' n'est pas un régent valide"}],
                score=0.0,
            )

        tree = tree or {}
        checks = []

        if name == "teli":
            checks = self._assess_teli(tree)
        elif name == "galgal":
            checks = self._assess_galgal(tree)
        elif name == "lev":
            checks = self._assess_lev(tree)

        passed = sum(1 for c in checks if c["passed"])
        total = len(checks) or 1
        score = passed / total

        return RegentHealth(
            name=name,
            hebrew=regent.hebrew,
            healthy=score >= 0.5,
            checks=checks,
            score=score,
        )

    def _assess_teli(self, tree: dict) -> list[dict]:
        """Teli — l'Axe : intégrité structurelle (DB, schéma, connexions)."""
        checks = []

        # Check 1 : DB accessible
        db_ok = False
        detail = "Non vérifié"
        db_url = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", ""))
        if db_url:
            try:
                from pool import get_conn, init_pool
                init_pool(db_url)  # idempotent
                with get_conn() as _conn:
                    pass  # borrow + return to verify connectivity
                db_ok = True
                detail = "Connexion DB réussie"
            except Exception as e:
                detail = f"Connexion DB échouée: {e}"
        else:
            detail = "ETZ_CHAIM_DB non défini"
        checks.append({"check": "Tables de la DB accessibles", "passed": db_ok, "detail": detail})

        # Check 2 : modules structurels présents
        structural = {"yesod", "hod", "netzach"}
        present = sum(1 for s in structural if tree.get(s) is not None)
        ok = present == len(structural)
        checks.append({
            "check": "Modules structurels présents",
            "passed": ok,
            "detail": f"{present}/{len(structural)} modules structurels actifs",
        })

        # Check 3 : Yesod (hub) a self_diagnose
        yesod = tree.get("yesod")
        if yesod and hasattr(yesod, "self_diagnose"):
            try:
                diag = yesod.self_diagnose()
                ok = diag.get("status") != "error" if isinstance(diag, dict) else True
                checks.append({"check": "Yesod self_diagnose OK", "passed": ok, "detail": str(diag.get("status", "ok"))})
            except Exception as e:
                checks.append({"check": "Yesod self_diagnose OK", "passed": False, "detail": str(e)})
        else:
            checks.append({"check": "Yesod self_diagnose OK", "passed": False, "detail": "Yesod absent ou sans self_diagnose"})

        return checks

    def _assess_galgal(self, tree: dict) -> list[dict]:
        """Galgal — la Roue : les cycles tournent-ils ?"""
        checks = []

        # Check 1 : daemon PID file
        pid_path = Path(__file__).parent / "daemon.pid"
        daemon_running = pid_path.exists()
        if daemon_running:
            try:
                pid = int(pid_path.read_text().strip())
                os.kill(pid, 0)  # Signal 0 = check if alive
                detail = f"Daemon PID {pid} actif"
            except (ProcessLookupError, ValueError):
                daemon_running = False
                detail = "PID file présent mais daemon mort"
        else:
            detail = "daemon.pid absent"
        checks.append({"check": "Daemon actif", "passed": daemon_running, "detail": detail})

        # Check 2 : Omer table accessible (cycle temporel)
        omer_ok = False
        detail = "Non vérifié"
        db_url = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", ""))
        if db_url:
            try:
                from pool import get_conn, init_pool
                init_pool(db_url)  # idempotent
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT count(*) FROM omer_log LIMIT 1")
                        count = cur.fetchone()[0]
                omer_ok = True
                detail = f"omer_log: {count} entrée(s)"
            except Exception as e:
                detail = f"omer_log inaccessible: {e}"
        else:
            detail = "ETZ_CHAIM_DB non défini"
        checks.append({"check": "Cycle Omer accessible", "passed": omer_ok, "detail": detail})

        # Check 3 : au moins un module temporel actif
        temporal_modules = {"tiferet", "binah"}
        present = sum(1 for m in temporal_modules if tree.get(m) is not None)
        ok = present > 0
        checks.append({
            "check": "Modules temporels actifs",
            "passed": ok,
            "detail": f"{present}/{len(temporal_modules)} modules temporels",
        })

        return checks

    def _assess_lev(self, tree: dict) -> list[dict]:
        """Lev — le Coeur : le hub central fonctionne-t-il ?"""
        checks = []

        # Check 1 : main.py existe et est exécutable
        main_path = Path(__file__).parent / "main.py"
        ok = main_path.exists()
        checks.append({"check": "main.py existant", "passed": ok, "detail": str(main_path)})

        # Check 2 : Yesod (hub) présent
        yesod = tree.get("yesod")
        ok = yesod is not None
        checks.append({"check": "Yesod (hub) présent", "passed": ok, "detail": "Yesod actif" if ok else "Yesod absent"})

        # Check 3 : routing entre modules (au moins 3 modules actifs)
        active = sum(1 for v in tree.values() if v is not None)
        ok = active >= 3
        checks.append({
            "check": "Routing inter-modules",
            "passed": ok,
            "detail": f"{active} modules actifs (minimum: 3)",
        })

        return checks

    # ── Mapping lettre → témoin ──────────────────────────────

    def map_letter_to_witness(self, letter: str, witness: str) -> LetterWitnessMapping:
        """Pour une lettre et un témoin, retourner la correspondance.

        Args:
            letter: nom latin (ex: "aleph", "shin", "beth")
            witness: "olam", "shanah", ou "nefesh"

        Returns:
            LetterWitnessMapping avec la correspondance.

        Raises:
            ValueError: si la lettre ou le témoin est inconnu.
        """
        witnesses = self.get_witnesses()
        if witness not in witnesses:
            raise ValueError(f"Témoin inconnu: '{witness}'. Valides: olam, shanah, nefesh")

        w = witnesses[witness]
        lt = _letter_type(letter)

        if lt == "mother" and letter in w.mothers:
            return LetterWitnessMapping(
                letter=letter, letter_type=lt,
                witness=witness, correspondence=w.mothers[letter],
            )
        elif lt == "double" and letter in w.doubles:
            return LetterWitnessMapping(
                letter=letter, letter_type=lt,
                witness=witness, correspondence=w.doubles[letter],
            )
        elif lt == "simple" and letter in w.simples:
            return LetterWitnessMapping(
                letter=letter, letter_type=lt,
                witness=witness, correspondence=w.simples[letter],
            )

        raise ValueError(
            f"Lettre '{letter}' ({lt}) non trouvée dans le témoin '{witness}'"
        )

    def map_all_witnesses(self, letter: str) -> list[LetterWitnessMapping]:
        """Retourner la correspondance d'une lettre dans les 3 témoins."""
        mappings = []
        for witness in ("olam", "shanah", "nefesh"):
            try:
                mappings.append(self.map_letter_to_witness(letter, witness))
            except ValueError as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        return mappings

    # ── Factorielles créatrices — SY 4:12 ─────────────────────

    @staticmethod
    def calculate_houses(n_stones: int) -> int:
        """Nombre de 'maisons' (permutations) bâties par n 'pierres' (lettres).

        SY 4:12 : "2 pierres bâtissent 2 maisons, 3→6, 4→24, 5→120, 6→720, 7→5040."
        C'est la fonction factorielle — la combinatoire de la création.

        Args:
            n_stones: nombre de pierres (lettres/concepts), >= 0.

        Returns:
            n_stones! (factorielle).
        """
        if n_stones < 0:
            raise ValueError(f"n_stones doit être >= 0, reçu {n_stones}")
        return math.factorial(n_stones)

    @staticmethod
    def domain_complexity(concepts: list[str]) -> int:
        """Complexité combinatoire d'un croisement de concepts.

        Quand une question croise N domaines, la complexité
        est N! — l'explosion factorielle du Sefer Yetzirah.

        Args:
            concepts: liste de domaines/concepts croisés.

        Returns:
            len(concepts)! — la complexité factorielle.
        """
        return math.factorial(len(concepts))

    # ── Format rapport ───────────────────────────────────────

    def format_report(self, tree: dict | None = None) -> list[str]:
        """Formater un rapport complet de la cosmologie."""
        lines = [
            "══════════════════════════════════════════════════════════",
            "  סֵפֶר יְצִירָה — Cosmologie : Structure Profonde",
            "══════════════════════════════════════════════════════════",
        ]

        # Profondeurs
        depths = self.get_depths()
        lines.append("")
        lines.append("  ── Eser Sefirot Belimah — 10 Profondeurs (5 axes) ──")
        for d in depths:
            lines.append(f"    {d.hebrew[0]} ←→ {d.hebrew[1]}  ({d.axis})")
            lines.append(f"      {d.pair[0]} / {d.pair[1]} — {d.description}")

        # Palais
        palace = self.get_palace_center()
        if palace:
            lines.append("")
            lines.append(f"  ── {palace.get('hebrew', 'הֵיכַל הַקֹּדֶשׁ')} — Palais Saint (centre) ──")
            lines.append(f"    {palace.get('description', '')}")

        # Témoins
        witnesses = self.get_witnesses()
        lines.append("")
        lines.append("  ── Trois Témoins (עֵדוּת) ──")
        for name, w in witnesses.items():
            lines.append(f"    {w.hebrew} {w.meaning}")
            lines.append(f"      {w.description}")
            lines.append(f"      Mères  : {', '.join(f'{k}→{v}' for k, v in w.mothers.items())}")
            lines.append(f"      Doubles : {', '.join(f'{k}→{v}' for k, v in list(w.doubles.items())[:3])}...")
            lines.append(f"      Simples : {', '.join(f'{k}→{v}' for k, v in list(w.simples.items())[:3])}...")

        # Régents
        regents = self.get_regents()
        lines.append("")
        lines.append("  ── Trois Régents (שָׁלוֹשׁ מוֹשְׁלִים) — SY 6:1 ──")
        for name, r in regents.items():
            health = self.assess_regent(name, tree)
            status = "✓" if health.healthy else "✗"
            lines.append(f"    {r.hebrew} {r.meaning}")
            lines.append(f"      IA : {r.role_ia}")
            lines.append(f"      Santé : [{status}] {health.score:.0%}")
            for c in health.checks:
                mark = "✓" if c["passed"] else "✗"
                lines.append(f"        {mark} {c['check']} — {c['detail']}")

        return lines
