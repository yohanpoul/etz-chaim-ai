"""Tests maturation Yesod — promotion automatique des mémoires mûres."""

from pool import get_conn


def test_mature_hypothesis_to_verified_once(mem):
    """hypothesis → verified_once quand confiance >= 0.6 et access_count >= 2."""
    entry_id = mem.remember(
        content="Hypothèse mature",
        source_sephirah="chokmah",
        confidence=0.65,
        generate_embedding=False,
    )
    # Simuler 2 accès
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE epistememory SET access_count = 3 WHERE id = %s",
            (entry_id,),
        )

    result = mem.mature()
    assert entry_id in result["to_verified_once"]

    entry = mem.get(entry_id)
    assert entry.epistemic_status.value == "verified_once"


def test_mature_skips_low_confidence_hypothesis(mem):
    """hypothesis avec confiance < 0.6 n'est pas promue."""
    entry_id = mem.remember(
        content="Hypothèse faible",
        source_sephirah="chokmah",
        confidence=0.4,
        generate_embedding=False,
    )
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE epistememory SET access_count = 5 WHERE id = %s",
            (entry_id,),
        )

    result = mem.mature()
    assert entry_id not in result["to_verified_once"]


def test_mature_skips_low_access_hypothesis(mem):
    """hypothesis avec access_count < 2 n'est pas promue."""
    entry_id = mem.remember(
        content="Hypothèse non consultee",
        source_sephirah="chokmah",
        confidence=0.8,
        generate_embedding=False,
    )
    # access_count reste à 0

    result = mem.mature()
    assert entry_id not in result["to_verified_once"]


def test_mature_verified_once_to_fact(mem):
    """verified_once → fact quand confiance >= 0.8, > 24h, non contradictee."""
    entry_id = mem.remember(
        content="Memoire verifiee",
        source_sephirah="tiferet",
        confidence=0.85,
        generate_embedding=False,
    )
    # Forcer le statut et l'anciennete
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """UPDATE epistememory
               SET epistemic_status = 'verified_once',
                   created_at = NOW() - INTERVAL '48 hours'
               WHERE id = %s""",
            (entry_id,),
        )

    result = mem.mature()
    assert entry_id in result["to_fact"]

    entry = mem.get(entry_id)
    assert entry.epistemic_status.value == "fact"


def test_mature_skips_recent_verified_once(mem):
    """verified_once < 24h n'est pas promu en fact."""
    entry_id = mem.remember(
        content="Memoire recente",
        source_sephirah="tiferet",
        confidence=0.9,
        generate_embedding=False,
    )
    # Forcer verified_once mais garder created_at recent
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE epistememory SET epistemic_status = 'verified_once' WHERE id = %s",
            (entry_id,),
        )

    result = mem.mature()
    assert entry_id not in result["to_fact"]


def test_mature_skips_contradicted(mem):
    """verified_once contradictee n'est pas promue en fact."""
    e1 = mem.remember("Claim A", source_sephirah="chokmah", confidence=0.85,
                      generate_embedding=False)
    e2 = mem.remember("Claim B contre A", source_sephirah="gevurah", confidence=0.7,
                      generate_embedding=False)
    mem.contradict(e1, e2)

    # Forcer le statut et l'anciennete
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """UPDATE epistememory
               SET epistemic_status = 'verified_once',
                   created_at = NOW() - INTERVAL '48 hours'
               WHERE id = %s""",
            (e1,),
        )

    result = mem.mature()
    assert e1 not in result["to_fact"]


def test_mature_max_per_level(mem):
    """Respecte la limite max_per_level."""
    ids = []
    for i in range(5):
        eid = mem.remember(
            content=f"Hypothese batch {i}",
            source_sephirah="chokmah",
            confidence=0.65,
            generate_embedding=False,
        )
        ids.append(eid)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE epistememory SET access_count = 3 WHERE id = ANY(%s)",
            (ids,),
        )

    result = mem.mature(max_per_level=3)
    assert len(result["to_verified_once"]) == 3
