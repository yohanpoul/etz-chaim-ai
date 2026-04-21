"""Tests — KavanahPlanner : l'intention pilotée par SelfMap."""

from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest

from intentkeeper.kavanah_planner import (
    KavanahPlanner,
    _parse_domain_subtasks,
)
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


@pytest.fixture(scope="session", autouse=True)
def apply_schemas():
    """Ensure test DB and schemas exist."""
    import subprocess

    conn = psycopg2.connect("postgresql://localhost/postgres")
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'etz_chaim_test'")
    if not cur.fetchone():
        cur.execute("CREATE DATABASE etz_chaim_test")
    cur.close()
    conn.close()

    conn = psycopg2.connect(TEST_DB_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    cur.close()
    conn.close()

    for schema in [
        "epistememory/schema.sql",
        "selfmap/schema.sql",
        "intentkeeper/schema.sql",
        "causalengine/schema.sql",
    ]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )


@pytest.fixture
def conn():
    """Connection to test DB, cleaned after each test."""
    c = psycopg2.connect(TEST_DB_URL)
    c.autocommit = True
    yield c
    with c.cursor() as cur:
        cur.execute("TRUNCATE selfmap_competence CASCADE")
        cur.execute("TRUNCATE causal_claims CASCADE")
        cur.execute("TRUNCATE epistememory CASCADE")
    c.close()


@pytest.fixture
def planner():
    return KavanahPlanner(TEST_DB_URL)


# ── Parser tests ────────────────────────────────────────────────

def test_parse_domain_subtasks():
    descs = [
        "Domaine 'kabbale_lurianique' de 0.665 → 0.75",
        "Domaine 'qliphoth' de 0.673 → 0.75",
        "Domaine 'sentiers' de 0.684 → 0.75",
    ]
    result = _parse_domain_subtasks(descs)
    assert len(result) == 3
    assert result[0] == ("kabbale_lurianique", 0.75)
    assert result[1] == ("qliphoth", 0.75)
    assert result[2] == ("sentiers", 0.75)


def test_parse_domain_subtasks_empty():
    assert _parse_domain_subtasks([]) == []
    assert _parse_domain_subtasks(["Something unrelated"]) == []


# ── derive_plan: domaines faibles ───────────────────────────────

def test_derive_plan_domains_all_above(conn, planner):
    """Si tous les domaines dépassent la cible → progrès 100%."""
    with conn.cursor() as cur:
        for domain, score in [
            ("kabbale_lurianique", 0.80),
            ("qliphoth", 0.78),
            ("sentiers", 0.82),
        ]:
            cur.execute(
                "INSERT INTO selfmap_competence (domain, model_id, score, n_evals) "
                "VALUES (%s, 'test', %s, 5) "
                "ON CONFLICT (domain, model_id) DO UPDATE SET score = EXCLUDED.score",
                (domain, score),
            )

    subtasks = [
        "Domaine 'kabbale_lurianique' de 0.665 → 0.75",
        "Domaine 'qliphoth' de 0.673 → 0.75",
        "Domaine 'sentiers' de 0.684 → 0.75",
    ]
    plan = planner.derive_plan(
        "Maîtriser les domaines faibles — seuil 0.75",
        subtasks,
    )
    assert plan.progress == 1.0
    assert plan.n_reached == 3
    assert all(s.reached for s in plan.subgoals)


def test_derive_plan_domains_partial(conn, planner):
    """Certains domaines au-dessus, d'autres en-dessous."""
    with conn.cursor() as cur:
        for domain, score in [
            ("kabbale_lurianique", 0.70),  # below
            ("qliphoth", 0.80),            # above
            ("sentiers", 0.82),            # above
        ]:
            cur.execute(
                "INSERT INTO selfmap_competence (domain, model_id, score, n_evals) "
                "VALUES (%s, 'test', %s, 5) "
                "ON CONFLICT (domain, model_id) DO UPDATE SET score = EXCLUDED.score",
                (domain, score),
            )

    subtasks = [
        "Domaine 'kabbale_lurianique' de 0.665 → 0.75",
        "Domaine 'qliphoth' de 0.673 → 0.75",
        "Domaine 'sentiers' de 0.684 → 0.75",
    ]
    plan = planner.derive_plan(
        "Maîtriser les domaines faibles — seuil 0.75",
        subtasks,
    )
    # 2/3 above threshold
    assert abs(plan.progress - 2 / 3) < 0.01
    assert plan.n_reached == 2
    assert "kabbale_lurianique" in plan.suggested_action


def test_derive_plan_domains_none_above(conn, planner):
    """Aucun domaine au-dessus → progrès 0."""
    with conn.cursor() as cur:
        for domain, score in [
            ("kabbale_lurianique", 0.50),
            ("qliphoth", 0.60),
        ]:
            cur.execute(
                "INSERT INTO selfmap_competence (domain, model_id, score, n_evals) "
                "VALUES (%s, 'test', %s, 5) "
                "ON CONFLICT (domain, model_id) DO UPDATE SET score = EXCLUDED.score",
                (domain, score),
            )

    subtasks = [
        "Domaine 'kabbale_lurianique' de 0.50 → 0.75",
        "Domaine 'qliphoth' de 0.60 → 0.75",
    ]
    plan = planner.derive_plan(
        "Maîtriser les domaines faibles — seuil 0.75",
        subtasks,
    )
    assert plan.progress == 0.0
    assert plan.n_reached == 0


# ── derive_plan: claims causaux ─────────────────────────────────

def test_derive_plan_causal(conn, planner):
    """Claims causaux — progress basé sur la fraction élevée."""
    with conn.cursor() as cur:
        for i in range(10):
            level = "probable_causation" if i < 3 else "correlation_only"
            cur.execute(
                "INSERT INTO causal_claims (cause, effect, evidence_level, confidence) "
                "VALUES (%s, %s, %s, 0.5)",
                (f"cause_{i}", f"effect_{i}", level),
            )

    plan = planner.derive_plan(
        "Élever 50% des claims causaux au-delà de correlation_only",
        [],
    )
    # 3/10 elevated, target 50% → progress = 0.3/0.5 = 0.6
    assert abs(plan.progress - 0.6) < 0.01


# ── derive_plan: Ohr Pnimi ──────────────────────────────────────

def test_derive_plan_ohr(conn, planner):
    """Ohr Pnimi — ratio de mémoire intégrée."""
    with conn.cursor() as cur:
        for i in range(10):
            conf = 0.8 if i < 6 else 0.3
            cur.execute(
                "INSERT INTO epistememory (content, source_sephirah, confidence, "
                "epistemic_status, domain) VALUES (%s, 'hod', %s, 'fact', 'test')",
                (f"fact_{i}", conf),
            )

    plan = planner.derive_plan(
        "Intégrer la mémoire — ratio Ohr Pnimi > 0.80",
        [],
    )
    # 6/10 pnimi = 0.6, target 0.8 → progress = 0.6/0.8 = 0.75
    assert abs(plan.progress - 0.75) < 0.01


# ── update_progress ──────────────────────────────────────────────

def test_update_progress_domains(conn, planner):
    """update_progress retourne le même résultat que derive_plan."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO selfmap_competence (domain, model_id, score, n_evals) "
            "VALUES ('kabbale_lurianique', 'test', 0.80, 5) "
            "ON CONFLICT (domain, model_id) DO UPDATE SET score = EXCLUDED.score",
        )

    subtasks = ["Domaine 'kabbale_lurianique' de 0.665 → 0.75"]
    progress = planner.update_progress(
        "Maîtriser les domaines faibles — seuil 0.75",
        subtasks,
    )
    assert progress == 1.0


# ── suggest_next_action ──────────────────────────────────────────

def test_suggest_next_action(conn, planner):
    """suggest retourne une action concrète."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO selfmap_competence (domain, model_id, score, n_evals) "
            "VALUES ('sentiers', 'test', 0.60, 5) "
            "ON CONFLICT (domain, model_id) DO UPDATE SET score = EXCLUDED.score",
        )

    subtasks = ["Domaine 'sentiers' de 0.60 → 0.75"]
    action = planner.suggest_next_action(
        "Maîtriser les domaines faibles — seuil 0.75",
        subtasks,
    )
    assert "sentiers" in action
    assert "Hitbonenut" in action


# ── Integration: les 3 intentions à 0% bougent ──────────────────

def test_three_zero_intentions_now_have_progress(conn, planner):
    """Test intégré : si les métriques ont bougé, progress > 0."""
    with conn.cursor() as cur:
        # Domaines: 4/7 au-dessus de 0.75
        for domain, score in [
            ("kabbale_lurianique", 0.704),
            ("qliphoth", 0.756),
            ("sefer_yetzirah", 0.739),
            ("partzufim", 0.797),
            ("hishtalshelut", 0.738),
            ("sentiers", 0.821),
            ("adam_kadmon", 0.752),
        ]:
            cur.execute(
                "INSERT INTO selfmap_competence (domain, model_id, score, n_evals) "
                "VALUES (%s, 'test', %s, 5) "
                "ON CONFLICT (domain, model_id) DO UPDATE SET score = EXCLUDED.score",
                (domain, score),
            )

        # Claims: 3/10 élevés
        for i in range(10):
            level = "probable_causation" if i < 3 else "correlation_only"
            cur.execute(
                "INSERT INTO causal_claims (cause, effect, evidence_level, confidence) "
                "VALUES (%s, %s, %s, 0.5)",
                (f"c{i}", f"e{i}", level),
            )

        # Mémoire: 6/10 intégrés
        for i in range(10):
            conf = 0.8 if i < 6 else 0.3
            cur.execute(
                "INSERT INTO epistememory (content, source_sephirah, confidence, "
                "epistemic_status, domain) VALUES (%s, 'hod', %s, 'fact', 'test')",
                (f"m{i}", conf),
            )

    subtasks_domains = [
        "Domaine 'kabbale_lurianique' de 0.665 → 0.75",
        "Domaine 'qliphoth' de 0.673 → 0.75",
        "Domaine 'sefer_yetzirah' de 0.675 → 0.75",
        "Domaine 'partzufim' de 0.676 → 0.75",
        "Domaine 'hishtalshelut' de 0.683 → 0.75",
        "Domaine 'sentiers' de 0.684 → 0.75",
        "Domaine 'adam_kadmon' de 0.700 → 0.75",
    ]

    # 1. Domaines faibles: 4/7 above → ~57%
    p1 = planner.update_progress(
        "Maîtriser les domaines faibles — seuil 0.75",
        subtasks_domains,
    )
    assert p1 > 0, "domaines faibles devrait avoir un progrès > 0"
    assert abs(p1 - 4 / 7) < 0.01

    # 2. Claims causaux: 3/10 élevés, target 50% → 60%
    p2 = planner.update_progress(
        "Élever 50% des claims causaux au-delà de correlation_only",
        [],
    )
    assert p2 > 0, "claims causaux devrait avoir un progrès > 0"

    # 3. Ohr Pnimi: 6/10 intégrés = 60%, target 80% → 75%
    p3 = planner.update_progress(
        "Intégrer la mémoire — ratio Ohr Pnimi > 0.80",
        [],
    )
    assert p3 > 0, "Ohr Pnimi devrait avoir un progrès > 0"
