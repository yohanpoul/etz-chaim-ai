"""Fixtures de test — Chokmah (InsightForge)."""

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import psycopg2
import pytest

from insightforge.core import InsightForge
from insightforge.db import InsightDB
from insightforge.emergence_detector import EmergenceDetector
from insightforge.insight_validator import InsightValidator
from insightforge.novelty_assessor import NoveltyAssessor
from insightforge.orchestrator import Orchestrator
from tests._psql import require_psql

TEST_DB_URL = "postgresql://localhost/etz_chaim_test"
PROJECT_ROOT = str(Path(__file__).resolve().parents[2])


# --- Stubs pour les 8 modules ---

@dataclass
class StubConnection:
    description: str = "Connection between A and B"
    domain_a: str = "physics"
    domain_b: str = "biology"
    novelty_score: float = 0.6


@dataclass
class StubExplorationResult:
    connections: list = field(default_factory=list)


class StubExploration:
    """Stub pour ExplorationEngine (Chesed)."""

    def __init__(self, connections=None):
        self._connections = connections if connections is not None else [
            StubConnection(
                description="Pattern X in physics mirrors pattern Y in biology",
                domain_a="physics",
                domain_b="biology",
                novelty_score=0.7,
            ),
            StubConnection(
                description="Feedback loop in ecology resembles backpropagation",
                domain_a="ecology",
                domain_b="machine_learning",
                novelty_score=0.8,
            ),
            StubConnection(
                description="Simple observation in physics about gravity",
                domain_a="physics",
                domain_b="physics",
                novelty_score=0.3,
            ),
        ]

    def explore(self, query, seed_domain="general", max_connections=10,
                target_domains=None):
        result = StubExplorationResult()
        result.connections = self._connections[:max_connections]
        return result


@dataclass
class StubCausalClaim:
    evidence_level: str = "probable_causation"
    confidence: float = 0.7


@dataclass
class StubCausalAssessment:
    claim: StubCausalClaim = field(default_factory=StubCausalClaim)


class StubCausal:
    """Stub pour CausalEngine (Binah)."""

    def __init__(self, evidence_level="probable_causation", confidence=0.7):
        self._evidence_level = evidence_level
        self._confidence = confidence

    def check_claim(self, cause, effect, domain="", direction=None):
        return StubCausalAssessment(
            claim=StubCausalClaim(
                evidence_level=self._evidence_level,
                confidence=self._confidence,
            ),
        )


@dataclass
class StubErrorPrediction:
    description: str = "Possible error in domain"
    confidence: float = 0.3


class StubSelfModel:
    """Stub pour SelfModel (Da'at)."""

    def __init__(self, predictions=None, high_risk=False):
        if predictions is not None:
            self._predictions = predictions
        elif high_risk:
            self._predictions = [
                StubErrorPrediction(
                    description="High risk error predicted",
                    confidence=0.9,
                ),
            ]
        else:
            self._predictions = [
                StubErrorPrediction(
                    description="Minor concern",
                    confidence=0.3,
                ),
            ]

    def predict_error(self, task_description):
        return self._predictions


class StubAutoJudge:
    """Stub pour AutoJudge (Gevurah)."""
    pass


@dataclass
class StubMemoryItem:
    content: str = "Known fact about the domain"


class StubEpisteMemory:
    """Stub pour EpisteMemory (Yesod)."""

    def __init__(self, memories=None):
        self._memories = memories if memories is not None else [
            StubMemoryItem("The universe is expanding"),
            StubMemoryItem("Neural networks learn via gradient descent"),
        ]

    def recall(self, query, min_confidence=0.3):
        return self._memories

    def remember(self, content, source_sephirah="", confidence=0.5,
                 domain=""):
        pass


@dataclass
class StubDomainEval:
    competence: float = 0.7
    score: float = 0.0

    def __post_init__(self):
        self.score = self.competence


class StubSelfMap:
    """Stub pour SelfMap (Hod)."""

    def __init__(self, competence=0.7):
        self._competence = competence

    def read_competence(self, domain):
        return StubDomainEval(competence=self._competence)

    def should_answer(self, domain):
        return self._competence >= 0.4


@dataclass
class StubConsistencyResult:
    has_contradiction: bool = False


class StubDissensus:
    """Stub pour DissensuEngine (Tiferet)."""

    def __init__(self, has_contradiction=False):
        self._has_contradiction = has_contradiction

    def analyze_consistency(self, claims):
        return StubConsistencyResult(
            has_contradiction=self._has_contradiction,
        )


class StubIntentKeeper:
    """Stub pour IntentKeeper (Netzach)."""
    pass


# --- Fixtures de schéma ---

@pytest.fixture(scope="session", autouse=True)
def apply_schemas():
    """Apply all schemas once."""
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
        "failuretoinsight/schema.sql",
        "dissensuengine/schema.sql",
        "autojudge/schema.sql",
        "explorationengine/schema.sql",
        "selfmodel/schema.sql",
        "causalengine/schema.sql",
        "insightforge/schema.sql",
        "masakh/schema.sql",
    ]:
        subprocess.run(
            [require_psql(), "-d", "etz_chaim_test",
             "-f", schema],
            cwd=PROJECT_ROOT, check=True, capture_output=True,
        )

    # InsightDB now borrows from the shared pool — init before tests touch it.
    from pool import init_pool
    init_pool(TEST_DB_URL)


# --- Fixtures de base ---

@pytest.fixture
def db():
    """Fresh InsightDB, truncated between tests."""
    database = InsightDB(TEST_DB_URL)
    yield database
    _truncate_via_pool()
    database.close()


@pytest.fixture
def novelty():
    """NoveltyAssessor nu."""
    return NoveltyAssessor()


@pytest.fixture
def novelty_with_history():
    """NoveltyAssessor avec connaissances existantes et insights passés."""
    return NoveltyAssessor(
        existing_knowledge=[
            "The universe is expanding",
            "Neural networks learn via gradient descent",
            "DNA encodes genetic information",
        ],
        past_insights=[
            "Astrocyte computation mirrors attention mechanisms in transformers",
            "Information bottleneck formalizes the Tzimtzum concept",
        ],
        min_novelty=0.65,
        similarity_threshold=0.60,
    )


@pytest.fixture
def validator():
    """InsightValidator avec stubs pour les 3 modules de la triple validation."""
    return InsightValidator(
        binah=StubCausal(),
        gevurah=StubAutoJudge(),
        daat=StubSelfModel(),
        yesod=StubEpisteMemory(),
        hod=StubSelfMap(),
        tiferet=StubDissensus(),
    )


@pytest.fixture
def validator_strict():
    """InsightValidator strict — tous les modules, triple obligatoire."""
    return InsightValidator(
        binah=StubCausal(),
        gevurah=StubAutoJudge(),
        daat=StubSelfModel(),
        yesod=StubEpisteMemory(),
        hod=StubSelfMap(),
        tiferet=StubDissensus(),
        require_triple=True,
    )


@pytest.fixture
def validator_no_modules():
    """InsightValidator sans aucun module — mode dégradé total."""
    return InsightValidator()


@pytest.fixture
def orchestrator():
    """Orchestrator avec stubs Chesed + Binah + Da'at."""
    return Orchestrator(
        exploration=StubExploration(),
        causal=StubCausal(),
        selfmodel=StubSelfModel(),
        db_url=TEST_DB_URL,
    )


@pytest.fixture
def orchestrator_full():
    """Orchestrator avec tous les 8 stubs."""
    return Orchestrator(
        epistememory=StubEpisteMemory(),
        selfmap=StubSelfMap(),
        intentkeeper=StubIntentKeeper(),
        dissensus=StubDissensus(),
        autojudge=StubAutoJudge(),
        exploration=StubExploration(),
        selfmodel=StubSelfModel(),
        causal=StubCausal(),
        db_url=TEST_DB_URL,
    )


@pytest.fixture
def emergence():
    """EmergenceDetector nu."""
    return EmergenceDetector()


@pytest.fixture
def forge():
    """InsightForge complète avec stubs et DB."""
    f = InsightForge(
        db_url=TEST_DB_URL,
        epistememory=StubEpisteMemory(),
        selfmap=StubSelfMap(),
        intentkeeper=StubIntentKeeper(),
        dissensus=StubDissensus(),
        autojudge=StubAutoJudge(),
        exploration=StubExploration(),
        selfmodel=StubSelfModel(),
        causal=StubCausal(),
    )
    yield f
    _truncate_via_pool()
    f.close()


@pytest.fixture
def forge_minimal():
    """InsightForge avec seulement Chesed — minimum vital."""
    f = InsightForge(
        db_url=TEST_DB_URL,
        exploration=StubExploration(),
        min_modules_consulted=1,
        hallucination_triple_check=False,
    )
    yield f
    _truncate_via_pool()
    f.close()


def _truncate_via_pool():
    """Clean state between tests via the shared pool (post-migration)."""
    from pool import get_conn
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE novelty_assessments CASCADE")
        cur.execute("TRUNCATE candidate_insights CASCADE")
        cur.execute("TRUNCATE insight_sessions CASCADE")


def _truncate(_legacy_conn=None):
    """Backward-compat shim — ignore the legacy conn arg and use the pool.

    Some tests import `_truncate` directly and pass `forge.db.conn` which no
    longer exists after the pool migration. Route to `_truncate_via_pool`.
    """
    _truncate_via_pool()
