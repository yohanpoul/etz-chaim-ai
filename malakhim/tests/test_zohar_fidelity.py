"""Tests priorité zoharique — fidélité > puissance."""

from malakhim.memuneh.router import Memuneh, OLAM_TO_MODEL, OLAM_TO_MODEL_FIDELITY


class TestZoharFidelity:
    """Zohar II:43a — la fidélité de transmission prime."""

    def test_fidelity_task_gets_faithful_model(self):
        """Tâche format-strict → modèle fidèle, pas puissant."""
        m = Memuneh()
        decision = m.route(
            "Extrais les données en format JSON de ce texte",
            kavvanah={"nature": "execution"},
        )
        # JSON → fidelity keyword → doit utiliser le modèle fidèle
        assert any("fidélité" in w.lower() or "Zohar" in w for w in decision.warnings)

    def test_creative_task_gets_powerful_model(self):
        """Tâche créative → modèle puissant (pas de fidelity keywords)."""
        m = Memuneh()
        decision = m.route(
            "Conçois une architecture innovante pour le système de cache distribué avec "
            "une analyse des arbitrages performance versus cohérence",
            kavvanah={"nature": "strategic"},
        )
        # Pas de fidelity keywords → modèle standard (puissant)
        fidelity_warnings = [w for w in decision.warnings if "Zohar" in w]
        assert len(fidelity_warnings) == 0

    def test_code_task_prefers_fidelity(self):
        """Code → fidélité (le code doit être EXACT)."""
        m = Memuneh()
        decision = m.route(
            "Écris le code Python pour parser ce fichier CSV",
            kavvanah={"nature": "execution"},
        )
        assert any("Zohar" in w for w in decision.warnings)

    def test_fidelity_model_differs_from_standard(self):
        """Les tables fidélité et standard divergent pour atziluth."""
        assert OLAM_TO_MODEL["atziluth"]["model"] != OLAM_TO_MODEL_FIDELITY["atziluth"]["model"]
