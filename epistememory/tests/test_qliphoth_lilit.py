"""Tests anti-Lilit — les 4 niveaux de Qliphoth de Yesod.

Lilit = la séductrice, l'anti-Yesod. Le danger de la mémoire épistémique :
confondre l'illusion avec le souvenir, le confort avec la vérité.

"Lilit refuse de se soumettre" — elle crée des faux fondements
qui séduisent par leur confiance apparente.

4 niveaux :
  Nogah  — faux souvenirs confiants (haute confiance + contested)
  Ruach  — hypothèses stagnantes (accédées mais jamais vérifiées)
  Anan   — mémoire parasitaire (entries inutilisées qui polluent)
  Mamash — illusion de connaissance (faits sans vérification réelle)
"""

import pytest

from pool import get_conn


# ════════════════════════════════════════════════
# 1. Nogah — Faux souvenirs confiants
# ════════════════════════════════════════════════

class TestNogah:
    """Haute confiance + contested = séduction douce de Lilit.
    Le système croit en des mémoires contredites.
    """

    def test_confident_contested_detected(self, mem):
        """Entrée confiante mais contested -> Nogah."""
        id1 = mem.remember(
            "La terre est plate",
            source_sephirah="external",
            confidence=0.85,
            generate_embedding=False,
        )
        id2 = mem.remember(
            "La terre est ronde",
            source_sephirah="external",
            confidence=0.9,
            generate_embedding=False,
        )
        mem.contradict(id1, id2)

        diag = mem.self_diagnose()
        assert any("Nogah" in i for i in diag["issues"])
        assert any("contested" in i for i in diag["issues"])

    def test_low_confidence_contested_no_nogah(self, mem):
        """Contested mais faible confiance -> pas Nogah."""
        id1 = mem.remember(
            "Hypothèse A",
            source_sephirah="external",
            confidence=0.3,
            generate_embedding=False,
        )
        id2 = mem.remember(
            "Hypothèse B",
            source_sephirah="external",
            confidence=0.3,
            generate_embedding=False,
        )
        mem.contradict(id1, id2)

        diag = mem.self_diagnose()
        assert not any("Nogah" in i for i in diag["issues"])


# ════════════════════════════════════════════════
# 2. Ruach — Hypothèses stagnantes
# ════════════════════════════════════════════════

class TestRuach:
    """Hypothèses accédées souvent mais jamais vérifiées.
    La séduction mémorielle : on consulte sans questionner.
    """

    def test_stagnant_hypothesis_detected(self, mem):
        """Hypothèse accédée >= 3 fois sans vérification -> Ruach."""
        entry_id = mem.remember(
            "Les chats sont des liquides",
            source_sephirah="external",
            confidence=0.4,
            generate_embedding=False,
        )
        # Simuler des accès répétés sans vérification
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE epistememory SET access_count = 5 WHERE id = %s",
                (entry_id,),
            )

        diag = mem.self_diagnose()
        assert any("Ruach" in i for i in diag["issues"])

    def test_verified_hypothesis_no_ruach(self, mem):
        """Hypothèse vérifiée -> promue, plus 'hypothesis', pas Ruach."""
        entry_id = mem.remember(
            "L'eau bout à 100°C",
            source_sephirah="external",
            confidence=0.4,
            generate_embedding=False,
        )
        mem.verify(entry_id, "thermodynamics textbook")
        # Après verify: status = verified_once, plus hypothesis

        # Simuler accès
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE epistememory SET access_count = 10 WHERE id = %s",
                (entry_id,),
            )

        diag = mem.self_diagnose()
        assert not any("Ruach" in i for i in diag["issues"])

    def test_rarely_accessed_hypothesis_no_ruach(self, mem):
        """Hypothèse peu accédée (< 3) -> pas Ruach."""
        mem.remember(
            "Hypothèse fraîche",
            source_sephirah="chokmah",
            confidence=0.4,
            generate_embedding=False,
        )
        # access_count = 0 par défaut

        diag = mem.self_diagnose()
        assert not any("Ruach" in i for i in diag["issues"])


# ════════════════════════════════════════════════
# 3. Anan — Mémoire parasitaire
# ════════════════════════════════════════════════

class TestAnan:
    """Beaucoup d'entries jamais accédées = bruit.
    Le système croit avoir une mémoire riche mais c'est du déchet.
    """

    def test_parasitic_memory_detected(self, mem):
        """Plus de 50% d'entries actives jamais accédées (>5) -> Anan."""
        for i in range(10):
            mem.remember(
                f"Fait inutile numéro {i}",
                source_sephirah="external",
                confidence=0.5,
                generate_embedding=False,
            )
        # Aucune accédée (access_count = 0 par défaut)

        diag = mem.self_diagnose()
        assert any("Anan" in i for i in diag["issues"])

    def test_accessed_entries_no_anan(self, mem):
        """Entries accédées -> pas d'Anan."""
        for i in range(10):
            mem.remember(
                f"Fait utile numéro {i}",
                source_sephirah="external",
                confidence=0.5,
                generate_embedding=False,
            )
        # Simuler des accès sur toutes les entries
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("UPDATE epistememory SET access_count = 1")

        diag = mem.self_diagnose()
        assert not any("Anan" in i for i in diag["issues"])

    def test_few_entries_no_anan(self, mem):
        """<= 5 entries -> pas d'Anan même si jamais accédées."""
        for i in range(3):
            mem.remember(
                f"Entrée {i}",
                source_sephirah="external",
                confidence=0.5,
                generate_embedding=False,
            )

        diag = mem.self_diagnose()
        assert not any("Anan" in i for i in diag["issues"])


# ════════════════════════════════════════════════
# 4. Mamash — Illusion de connaissance
# ════════════════════════════════════════════════

class TestMamash:
    """Des 'faits' sans vérification = l'illusion suprême de Lilit.
    Le système prétend savoir ce qu'il n'a jamais vérifié.
    """

    def test_unverified_fact_detected(self, mem):
        """Fact sans vérification dans source_detail -> Mamash."""
        mem.remember(
            "La vitesse de la lumière est constante",
            source_sephirah="external",
            confidence=0.95,  # Auto -> 'fact' sans vérification
            generate_embedding=False,
        )

        diag = mem.self_diagnose()
        assert any("Mamash" in i for i in diag["issues"])
        assert diag["level"] == "mamash"

    def test_verified_fact_no_mamash(self, mem):
        """Fact avec vérifications réelles -> pas Mamash."""
        entry_id = mem.remember(
            "E = mc²",
            source_sephirah="external",
            confidence=0.6,
            generate_embedding=False,
        )
        # Vérifier 3 fois pour atteindre 'fact'
        mem.verify(entry_id, "Einstein 1905")
        mem.verify(entry_id, "Cockcroft-Walton 1932")
        mem.verify(entry_id, "CERN experiments")

        diag = mem.self_diagnose()
        assert not any("Mamash" in i for i in diag["issues"])

    def test_fact_with_null_source_detail(self, mem):
        """Fact avec source_detail=NULL -> Mamash."""
        mem.remember(
            "Claim sans preuve",
            source_sephirah="external",
            confidence=0.95,
            generate_embedding=False,
            source_detail=None,
        )

        diag = mem.self_diagnose()
        assert any("Mamash" in i for i in diag["issues"])

    def test_fact_with_empty_verifications(self, mem):
        """Fact avec verifications=[] -> Mamash."""
        mem.remember(
            "Claim avec detail mais sans verifications",
            source_sephirah="external",
            confidence=0.95,
            generate_embedding=False,
            source_detail={"origin": "unknown", "verifications": []},
        )

        diag = mem.self_diagnose()
        assert any("Mamash" in i for i in diag["issues"])


# ════════════════════════════════════════════════
# 5. Hiérarchie Qliphoth
# ════════════════════════════════════════════════

class TestQliphothHierarchy:
    """La hiérarchie : Mamash > Anan > Ruach > Nogah."""

    def test_healthy_when_empty(self, mem):
        """Pas d'entrées -> healthy."""
        diag = mem.self_diagnose()
        assert diag["level"] == "healthy"
        assert diag["issues"] == []

    def test_mamash_trumps_all(self, mem):
        """Mamash est le niveau le plus grave, même si Nogah aussi."""
        # Mamash : fact sans vérification
        mem.remember(
            "Faux fait",
            source_sephirah="external",
            confidence=0.95,
            generate_embedding=False,
        )
        # Nogah : contested + confiant
        id1 = mem.remember(
            "A",
            source_sephirah="external",
            confidence=0.85,
            generate_embedding=False,
        )
        id2 = mem.remember(
            "B",
            source_sephirah="external",
            confidence=0.85,
            generate_embedding=False,
        )
        mem.contradict(id1, id2)

        diag = mem.self_diagnose()
        assert diag["level"] == "mamash"

    def test_nogah_is_mildest(self, mem):
        """Nogah seul -> level = nogah."""
        id1 = mem.remember(
            "X",
            source_sephirah="external",
            confidence=0.8,
            generate_embedding=False,
        )
        id2 = mem.remember(
            "Y",
            source_sephirah="external",
            confidence=0.8,
            generate_embedding=False,
        )
        mem.contradict(id1, id2)

        diag = mem.self_diagnose()
        assert diag["level"] == "nogah"
