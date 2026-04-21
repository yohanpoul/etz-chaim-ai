"""Fixtures pour tests sitra_achra.

Reset du pool global avant chaque test : les tests patchent
psycopg2.connect pour mocker la DB. Le pool global etant idempotent,
un pool initialise par un test precedent (ou par conftest d'un autre
module) neutralise le patch. Reset garantit que init_pool(url)
passe effectivement par psycopg2.connect (donc par le mock).
"""

from __future__ import annotations

import pytest

from pool import reset_pool


@pytest.fixture(autouse=True)
def _reset_pool_for_mocks():
    """Reset le pool avant/apres chaque test pour que les mocks s'appliquent."""
    reset_pool()
    yield
    reset_pool()
