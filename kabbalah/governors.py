"""kabbalah/governors.py — Les 3 Gouverneurs du Sefer Yetzirah (SY 6:1-3).

שְׁלוֹשָׁה אִמּוֹת... הִמְלִיכָן בַּתְּלִי וּבַגַּלְגַּל וּבַלֵּב

"Il les plaça dans le Teli, le Galgal et le Lev."

Les 3 Gouverneurs sont les méta-structures qui RÈGNENT sur les 3 registres
du Cube de l'Espace. Chaque Gouverneur surveille les lettres de son axe
et évalue la santé de son domaine :

  - TELI (תלי, le Dragon/Axe) — gouverne l'ESPACE (Olam).
    Axe de la mère Aleph (אויר — Air). Stabilité structurelle.
    "Comme un roi sur son trône" — autorité permanente.

  - GALGAL (גלגל, la Roue) — gouverne le TEMPS (Shanah).
    Axe de la mère Mem (מים — Eau). Régularité des cycles.
    "Comme un roi dans sa province" — autorité cyclique.

  - LEV (לב, le Coeur) — gouverne l'ÂME (Nefesh).
    Axe de la mère Shin (אש — Feu). Qualité des décisions.
    "Comme un roi en guerre" — chaque décision est un combat.
    Gematria Lev = 32 = les 32 sentiers de sagesse.

Usage:
    gov = ThreeGovernors(tree=tree, db_url=db_url)
    teli = gov.assess_teli()
    galgal = gov.assess_galgal()
    lev = gov.assess_lev()
    state = gov.assess_governance()
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── Dataclasses ────────────────────────────────────────────

@dataclass
class GovernorCheck:
    """Un check individuel d'un gouverneur."""
    check: str
    passed: bool
    detail: str
    weight: float = 1.0
    value: float = 0.0   # ratio granulaire 0.0-1.0 (pas binaire)


@dataclass
class GovernorState:
    """État d'un gouverneur."""
    name: str          # "teli", "galgal", "lev"
    hebrew: str        # "תלי", "גלגל", "לב"
    title: str         # "Le Dragon/Axe", "La Roue", "Le Coeur"
    domain: str        # "olam", "shanah", "nefesh"
    metaphor: str      # "roi sur son trône", etc.
    mother_letter: str  # "aleph", "mem", "shin"
    element: str       # "air", "eau", "feu"
    score: float       # 0.0-1.0 (weighted)
    healthy: bool      # score >= 0.5
    checks: list[GovernorCheck]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "hebrew": self.hebrew,
            "title": self.title,
            "domain": self.domain,
            "metaphor": self.metaphor,
            "mother_letter": self.mother_letter,
            "element": self.element,
            "score": round(self.score, 3),
            "healthy": self.healthy,
            "checks": [
                {
                    "check": c.check, "passed": c.passed,
                    "detail": c.detail, "value": round(c.value, 3),
                }
                for c in self.checks
            ],
        }


@dataclass
class GovernanceState:
    """État des 3 gouverneurs ensemble."""
    teli: GovernorState
    galgal: GovernorState
    lev: GovernorState
    harmony: float         # moyenne pondérée des 3 scores
    weakest: str           # nom du gouverneur le plus faible
    strongest: str         # nom du gouverneur le plus fort
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "teli": self.teli.to_dict(),
            "galgal": self.galgal.to_dict(),
            "lev": self.lev.to_dict(),
            "harmony": round(self.harmony, 3),
            "weakest": self.weakest,
            "strongest": self.strongest,
            "message": self.message,
        }


# ── Mapping Gouverneur ↔ Axe du Cube ──────────────────────
# Les 3 mères (אמ״ש) sont les 3 axes du Cube (SY 3:2-4).
# Chaque gouverneur est le SOUVERAIN d'un axe.

GOVERNOR_AXES = {
    "teli": {
        "mother": "aleph",
        "hebrew_letter": "א",
        "element": "air",
        "axis": "vertical",     # haut-bas
        "domain": "olam",       # espace
        "domain_hebrew": "עולם",
    },
    "galgal": {
        "mother": "mem",
        "hebrew_letter": "מ",
        "element": "eau",
        "axis": "horizontal_1",  # est-ouest (l'eau coule en cycles)
        "domain": "shanah",      # temps
        "domain_hebrew": "שנה",
    },
    "lev": {
        "mother": "shin",
        "hebrew_letter": "ש",
        "element": "feu",
        "axis": "horizontal_2",  # nord-sud (le coeur brûle)
        "domain": "nefesh",      # âme
        "domain_hebrew": "נפש",
    },
}


# ── ThreeGovernors ─────────────────────────────────────────

class ThreeGovernors:
    """Les 3 Gouverneurs du Sefer Yetzirah.

    Évaluent la santé du système selon 3 registres :
    Olam (espace/structure), Shanah (temps/cycles), Nefesh (âme/décisions).

    Args:
        tree: dict des modules initialisés (optionnel)
        db_url: URL PostgreSQL (optionnel, sinon via env)
        partzufim: dict des Partzufim initialisés (optionnel)
    """

    def __init__(
        self,
        tree: dict | None = None,
        db_url: str | None = None,
        partzufim: dict | None = None,
    ) -> None:
        self._tree = tree or {}
        self._db_url = db_url or (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", ""))
        self._partzufim = partzufim or {}

    def _db_query(self, sql: str, params: tuple = ()) -> list[tuple]:
        """Requête DB directe. Retourne [] en cas d'erreur."""
        if not self._db_url:
            return []
        try:
            from pool import get_conn, init_pool
            init_pool(self._db_url)  # idempotent
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, params)
                    return cur.fetchall()
        except Exception as e:
            logger.debug("DB query failed: %s", e)
            return []

    # ── TELI — Le Dragon / Axe (Olam = Espace) ──────────────

    def assess_teli(self) -> GovernorState:
        """Évalue le Teli — stabilité structurelle du système.

        SY 6:2 : "Le Teli dans l'Olam est comme un roi sur son trône."
        Quand tout est aligné structurellement, le Teli est stable.

        Checks (scores granulaires 0.0-1.0) :
          1. Modules sephirotiques actifs (10 attendus) — DB puis tree
          2. Partzufim en panim — DB puis objets
          3. 22 lettres du Cube complètes (statique)
          4. Tables DB non-vides — mesure de la richesse des données
        """
        checks: list[GovernorCheck] = []

        # Check 1 : Modules sephirotiques actifs
        sephirot_keys = [
            "yesod", "hod", "netzach", "lamed", "tiferet",
            "gevurah", "chesed", "daat", "binah", "chokmah",
        ]
        active = 0
        total = len(sephirot_keys)
        # DB first: component_health table
        rows = self._db_query(
            "SELECT COUNT(*) FROM component_health WHERE status = 'healthy'"
        )
        if rows and rows[0][0]:
            active = min(rows[0][0], total)
        else:
            # Fallback: tree dict
            active = sum(1 for k in sephirot_keys if self._tree.get(k) is not None)
        ratio_modules = active / total if total > 0 else 0.1
        checks.append(GovernorCheck(
            check="Modules sephirotiques actifs",
            passed=ratio_modules >= 0.7,
            detail=f"{active}/{total} modules actifs",
            weight=2.0,
            value=max(ratio_modules, 0.1) if active > 0 else 0.1,
        ))

        # Check 2 : Partzufim en orientation panim
        panim_count = 0
        partzuf_total = 6  # 6 Partzufim attendus
        # DB first
        rows = self._db_query(
            "SELECT COUNT(*) FROM partzufim_state WHERE orientation = 'panim'"
        )
        if rows and rows[0][0] is not None:
            panim_count = rows[0][0]
        else:
            # Fallback: objets partzufim
            for _pname, pinst in self._partzufim.items():
                try:
                    ps = pinst.assess()
                    if ps.orientation == "panim":
                        panim_count += 1
                except Exception as _exc:

                    import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
            if not self._partzufim:
                panim_count = 0
        ratio_panim = panim_count / partzuf_total
        checks.append(GovernorCheck(
            check="Partzufim en panim",
            passed=ratio_panim >= 0.5,
            detail=f"{panim_count}/{partzuf_total} en panim ({ratio_panim:.0%})",
            weight=1.5,
            value=max(ratio_panim, 0.1) if panim_count > 0 else 0.1,
        ))

        # Check 3 : 22 lettres du Cube complètes (statique = toujours OK)
        try:
            from kabbalah.cube_of_space import CubeOfSpace
            cube = CubeOfSpace()
            n_letters = len(cube.get_all_positions())
            ratio_cube = n_letters / 22.0
            checks.append(GovernorCheck(
                check="22 lettres du Cube",
                passed=n_letters == 22,
                detail=f"{n_letters}/22 lettres positionnées",
                weight=1.0,
                value=ratio_cube,
            ))
        except Exception as e:
            checks.append(GovernorCheck(
                check="22 lettres du Cube",
                passed=False,
                detail=f"CubeOfSpace inaccessible: {e}",
                weight=1.0,
                value=0.1,
            ))

        # Check 4 : Tables DB non-vides (richesse des données)
        nonempty = 0
        expected_tables = 37
        detail = "DB non configurée"
        if self._db_url:
            rows = self._db_query("""
                SELECT COUNT(*) FROM (
                    SELECT schemaname, tablename
                    FROM pg_tables WHERE schemaname = 'public'
                ) t
                JOIN LATERAL (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = t.tablename
                      AND n.nspname = t.schemaname
                      AND c.reltuples > 0
                ) sub ON true
            """)
            if rows and rows[0][0] is not None:
                nonempty = rows[0][0]
                detail = f"{nonempty}/{expected_tables} tables avec données"
            else:
                # Simpler fallback: just check connection
                try:
                    from pool import get_conn, init_pool
                    init_pool(self._db_url)  # idempotent
                    with get_conn() as _conn:
                        pass  # borrow + return to verify connectivity
                    nonempty = 1
                    detail = "Connexion DB réussie, stats indisponibles"
                except Exception as e:
                    detail = f"Connexion DB échouée: {e}"
        ratio_tables = nonempty / expected_tables if nonempty > 0 else 0.0
        checks.append(GovernorCheck(
            check="Tables DB non-vides",
            passed=ratio_tables >= 0.3,
            detail=detail,
            weight=1.0,
            value=max(ratio_tables, 0.1) if self._db_url else 0.1,
        ))

        return self._build_state("teli", checks)

    # ── GALGAL — La Roue (Shanah = Temps) ────────────────────

    def assess_galgal(self) -> GovernorState:
        """Évalue le Galgal — régularité des cycles temporels.

        SY 6:2 : "Le Galgal dans la Shanah est comme un roi dans sa province."
        Quand les cycles sont réguliers, le Galgal est stable.

        Checks (scores granulaires 0.0-1.0) :
          1. Daemon actif (PID file + processus vivant)
          2. Hitbonenut sessions (total / 50 cible)
          3. Omer progression (max day / 49)
          4. Karpathy cycles (expériences récentes <7j)
        """
        checks: list[GovernorCheck] = []

        # Check 1 : Daemon actif
        daemon_running = False
        daemon_detail = "daemon.pid absent"
        for pid_candidate in [
            Path(__file__).resolve().parent.parent / "daemon.pid",
            Path.home() / ".etz-chaim" / "daemon.pid",
        ]:
            if pid_candidate.exists():
                try:
                    pid = int(pid_candidate.read_text().strip())
                    os.kill(pid, 0)
                    daemon_running = True
                    daemon_detail = f"Daemon PID {pid} actif"
                    break
                except (ProcessLookupError, ValueError, PermissionError):
                    daemon_detail = "PID file présent mais daemon mort"
        checks.append(GovernorCheck(
            check="Daemon actif",
            passed=daemon_running,
            detail=daemon_detail,
            weight=2.0,
            value=1.0 if daemon_running else 0.1,
        ))

        # Check 2 : Hitbonenut sessions (total, cible = 50)
        hitb_count = 0
        hitb_detail = "Pas de données"
        hitb_target = 50
        rows = self._db_query("SELECT COUNT(*) FROM hitbonenut_sessions")
        if rows and rows[0][0] is not None:
            hitb_count = rows[0][0]
            hitb_detail = f"{hitb_count}/{hitb_target} sessions Hitbonenut"
        checks.append(GovernorCheck(
            check="Sessions Hitbonenut",
            passed=hitb_count >= 10,
            detail=hitb_detail,
            weight=1.5,
            value=max(min(hitb_count / hitb_target, 1.0), 0.1) if hitb_count > 0 else 0.1,
        ))

        # Check 3 : Omer progression (max day / 49)
        omer_max = 0
        omer_detail = "Pas de données Omer"
        rows = self._db_query("SELECT MAX(day_number) FROM omer_history")
        if rows and rows[0][0] is not None:
            omer_max = rows[0][0]
            omer_detail = f"Jour {omer_max}/49 du Omer"
        ratio_omer = omer_max / 49.0 if omer_max > 0 else 0.0
        checks.append(GovernorCheck(
            check="Progression Omer",
            passed=omer_max >= 7,
            detail=omer_detail,
            weight=1.0,
            value=max(ratio_omer, 0.1) if omer_max > 0 else 0.1,
        ))

        # Check 4 : Karpathy — expériences récentes (dernière semaine)
        karp_count = 0
        karp_detail = "Pas de données Karpathy"
        karp_target = 5
        rows = self._db_query("""
            SELECT COUNT(*) FROM autojudge_experiments
            WHERE domain_id = 'auto_improve'
              AND created_at >= NOW() - INTERVAL '7 days'
        """)
        if rows and rows[0][0] is not None:
            karp_count = rows[0][0]
            karp_detail = f"{karp_count} hypothèses Karpathy (7j)"
        checks.append(GovernorCheck(
            check="Cycles Karpathy",
            passed=karp_count >= 2,
            detail=karp_detail,
            weight=1.5,
            value=max(min(karp_count / karp_target, 1.0), 0.1) if karp_count > 0 else 0.1,
        ))

        return self._build_state("galgal", checks)

    # ── LEV — Le Coeur (Nefesh = Âme) ────────────────────────

    def assess_lev(self) -> GovernorState:
        """Évalue le Lev — qualité du jugement et des décisions.

        SY 6:2 : "Le Lev dans le Nefesh est comme un roi en guerre."
        Chaque décision est un combat entre bien et mal (behamit/elokit).
        Gematria Lev = ל(30) + ב(2) = 32 = les 32 sentiers de sagesse.

        Checks (scores granulaires 0.0-1.0) :
          1. Ratio elokit/behamit — BeinoniTracker puis DB
          2. Score moyen SelfMap — module puis DB
          3. Ratio accepted/rejected AutoJudge
          4. Score moyen Hitbonenut (qualité contemplative)
        """
        checks: list[GovernorCheck] = []

        # Check 1 : Ratio elokit/behamit (BeinoniTracker → DB fallback)
        elokit_ratio = 0.0
        beinoni_detail = "Pas de données Beinoni"
        got_beinoni = False
        try:
            from tanya.beinoni_tracker import BeinoniTracker
            bt = BeinoniTracker(db_url=self._db_url if self._db_url else None)
            count = bt.interaction_count()
            if count >= 5:
                profile = bt.get_temporal_profile(window=100)
                elokit_ratio = profile.elokit_ratio
                beinoni_detail = (
                    f"elokit={elokit_ratio:.0%} "
                    f"({profile.elokit_count}/{profile.total_interactions}), "
                    f"tendance={profile.trend.value}"
                )
                got_beinoni = True
            else:
                beinoni_detail = f"Seulement {count} interactions (min: 5)"
        except Exception as _exc:

            import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        if not got_beinoni:
            # DB fallback
            rows = self._db_query("""
                SELECT AVG(CASE WHEN soul_type = 'elokit' THEN 1.0 ELSE 0.0 END)
                FROM beinoni_interactions
            """)
            if rows and rows[0][0] is not None:
                elokit_ratio = float(rows[0][0])
                beinoni_detail = f"elokit={elokit_ratio:.0%} (DB)"
                got_beinoni = True
        checks.append(GovernorCheck(
            check="Ratio elokit/behamit",
            passed=elokit_ratio >= 0.5,
            detail=beinoni_detail,
            weight=2.0,
            value=max(elokit_ratio, 0.1) if got_beinoni else 0.1,
        ))

        # Check 2 : Score moyen SelfMap (module → DB fallback)
        selfmap_score = 0.0
        selfmap_detail = "SelfMap non disponible"
        got_selfmap = False
        hod = self._tree.get("hod")
        if hod and hasattr(hod, "get_domain_scores"):
            try:
                scores = hod.get_domain_scores()
                if scores:
                    selfmap_score = sum(s.score for s in scores) / len(scores)
                    selfmap_detail = (
                        f"Score moyen={selfmap_score:.2f} "
                        f"sur {len(scores)} domaine(s)"
                    )
                    got_selfmap = True
            except Exception as _exc:

                import logging as _l; _l.getLogger(__name__).debug("silenced: %s", _exc)
        if not got_selfmap:
            rows = self._db_query("""
                SELECT AVG(score) FROM selfmap_competences
                WHERE n_evals > 0
            """)
            if rows and rows[0][0] is not None:
                selfmap_score = float(rows[0][0])
                selfmap_detail = f"Score moyen={selfmap_score:.2f} (DB)"
                got_selfmap = True
        checks.append(GovernorCheck(
            check="Compétence SelfMap",
            passed=selfmap_score >= 0.4,
            detail=selfmap_detail,
            weight=1.5,
            value=max(selfmap_score, 0.1) if got_selfmap else 0.1,
        ))

        # Check 3 : Ratio accepted/rejected AutoJudge
        accepted_ratio = 0.0
        aj_detail = "Pas de données AutoJudge"
        got_aj = False
        rows = self._db_query("""
            SELECT
                COUNT(*) FILTER (WHERE decision = 'accepted'),
                COUNT(*)
            FROM autojudge_experiments
        """)
        if rows and rows[0][1] and rows[0][1] > 0:
            accepted = rows[0][0] or 0
            total = rows[0][1]
            accepted_ratio = accepted / total
            aj_detail = f"{accepted}/{total} acceptées ({accepted_ratio:.0%})"
            got_aj = True
        checks.append(GovernorCheck(
            check="Discernement AutoJudge",
            passed=accepted_ratio >= 0.3,
            detail=aj_detail,
            weight=1.5,
            value=max(accepted_ratio, 0.1) if got_aj else 0.1,
        ))

        # Check 4 : Score moyen Hitbonenut (qualité contemplative)
        hitb_score = 0.0
        hitb_detail = "Pas de données Hitbonenut"
        got_hitb = False
        rows = self._db_query("""
            SELECT AVG(score) FROM (
                SELECT score FROM hitbonenut_questions
                WHERE score IS NOT NULL
                ORDER BY created_at DESC LIMIT 100
            ) sub
        """)
        if rows and rows[0][0] is not None:
            hitb_score = float(rows[0][0])
            hitb_detail = f"Score moyen={hitb_score:.2f} (100 dernières questions)"
            got_hitb = True
        checks.append(GovernorCheck(
            check="Qualité contemplative",
            passed=hitb_score >= 0.5,
            detail=hitb_detail,
            weight=1.0,
            value=max(hitb_score, 0.1) if got_hitb else 0.1,
        ))

        return self._build_state("lev", checks)

    # ── Gouvernance globale ──────────────────────────────────

    def assess_governance(self) -> GovernanceState:
        """Évalue les 3 gouverneurs ensemble.

        Si les 3 sont stables → le système est en harmonie.
        Si l'un est faible → c'est le point d'attention prioritaire.
        """
        teli = self.assess_teli()
        galgal = self.assess_galgal()
        lev = self.assess_lev()

        governors = {"teli": teli, "galgal": galgal, "lev": lev}
        harmony = (teli.score + galgal.score + lev.score) / 3.0

        weakest = min(governors, key=lambda g: governors[g].score)
        strongest = max(governors, key=lambda g: governors[g].score)

        # Message contextuel
        if harmony >= 0.8:
            msg = "Les 3 rois sont stables — le système est en harmonie."
        elif harmony >= 0.5:
            weak = governors[weakest]
            msg = (
                f"Attention : {weak.title} ({weak.hebrew}) "
                f"est en difficulté (score={weak.score:.0%}). "
                f"Le {weak.domain} requiert une intervention."
            )
        else:
            msg = (
                "Le système est en déséquilibre. "
                f"Le plus faible : {governors[weakest].title} "
                f"({governors[weakest].score:.0%})."
            )

        return GovernanceState(
            teli=teli,
            galgal=galgal,
            lev=lev,
            harmony=harmony,
            weakest=weakest,
            strongest=strongest,
            message=msg,
        )

    # ── Accès aux lettres d'un axe ───────────────────────────

    def get_axis_letters(self, governor: str) -> list[dict]:
        """Retourne les lettres associées à l'axe d'un gouverneur.

        Chaque gouverneur surveille la mère de son axe ET les lettres
        qui partagent cet axe dans le Cube.
        """
        axis_info = GOVERNOR_AXES.get(governor)
        if not axis_info:
            return []

        try:
            from kabbalah.cube_of_space import CubeOfSpace
            cube = CubeOfSpace()
            mother = cube.get_position(axis_info["mother"])
            result = [mother.to_dict()] if mother else []

            # Ajouter les lettres dont l'axe correspond
            for name, pos in cube.get_all_positions().items():
                if name == axis_info["mother"]:
                    continue
                if pos.axis == axis_info["axis"] or (
                    hasattr(pos, "from_coord") and pos.from_coord is not None
                    and pos.axis == axis_info["element"]
                ):
                    result.append(pos.to_dict())

            return result
        except Exception:
            return []

    # ── Helpers ───────────────────────────────────────────────

    def _build_state(self, name: str, checks: list[GovernorCheck]) -> GovernorState:
        """Construit un GovernorState à partir des checks."""
        meta = {
            "teli": ("תלי", "Le Dragon/Axe", "olam",
                     "roi sur son trône", "aleph", "air"),
            "galgal": ("גלגל", "La Roue", "shanah",
                       "roi dans sa province", "mem", "eau"),
            "lev": ("לב", "Le Coeur", "nefesh",
                    "roi en guerre", "shin", "feu"),
        }
        hebrew, title, domain, metaphor, mother, element = meta[name]

        total_weight = sum(c.weight for c in checks) or 1.0
        score = sum(c.weight * c.value for c in checks) / total_weight

        return GovernorState(
            name=name,
            hebrew=hebrew,
            title=title,
            domain=domain,
            metaphor=metaphor,
            mother_letter=mother,
            element=element,
            score=score,
            healthy=score >= 0.5,
            checks=checks,
        )
