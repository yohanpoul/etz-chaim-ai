"""Tests de completude de SCHEMA_ORDER dans init_db.py.

Garantit que tout schema.sql du repo est bien reference dans SCHEMA_ORDER,
pour eviter qu'un nouveau module oublie d'etre ajoute et que init_db.py
cree une DB incomplete de zero.

Note : les schemas embarques (ex. hitbonenut via SCHEMA_SQL inline) ne
sont pas comptes ici — ils sont geres separement dans main() de init_db.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


# Modules de SCHEMA_ORDER attendus pour les dettes connues (Sprint 6).
_SPRINT_6_MANDATORY = {"chat", "malakhim"}

# Chemins a exclure du scan (venvs, externes).
_EXCLUDED_PATH_PARTS = {
    ".venv",
    ".garak-venv",
    "node_modules",
    "site-packages",
    ".git",
}


def _load_schema_order() -> list[str]:
    """Charge SCHEMA_ORDER depuis init_db.py sans executer le script."""
    import importlib.util
    init_db_path = REPO_ROOT / "init_db.py"
    spec = importlib.util.spec_from_file_location("init_db_module", init_db_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.SCHEMA_ORDER)


def _find_repo_schemas() -> set[str]:
    """Trouve tous les modules ayant un schema.sql dans le repo.

    Retourne l'ensemble des noms de modules (nom du repertoire parent).
    """
    modules: set[str] = set()
    for path in REPO_ROOT.rglob("schema.sql"):
        if any(part in _EXCLUDED_PATH_PARTS for part in path.parts):
            continue
        # path est .../<module>/schema.sql → module = parent.name
        module_name = path.parent.name
        modules.add(module_name)
    return modules


class TestSchemaOrderCompleteness:
    """SCHEMA_ORDER doit contenir tous les schemas du repo."""

    def test_chat_in_schema_order(self):
        """chat/schema.sql doit etre dans SCHEMA_ORDER (Sprint 6)."""
        order = _load_schema_order()
        assert "chat" in order, (
            "chat/schema.sql existe mais n'est pas dans SCHEMA_ORDER. "
            "Un init_db.py --drop creerait une DB sans chat_messages."
        )

    def test_malakhim_in_schema_order(self):
        """malakhim/schema.sql doit etre dans SCHEMA_ORDER (Sprint 6)."""
        order = _load_schema_order()
        assert "malakhim" in order, (
            "malakhim/schema.sql existe mais n'est pas dans SCHEMA_ORDER. "
            "Un init_db.py --drop creerait une DB sans pekidah_agents."
        )

    def test_no_schema_drift(self):
        """Test generique anti-drift : tout schema.sql du repo doit etre ref'd.

        Previent automatiquement la meme dette si un nouveau module est
        ajoute sans mise a jour de SCHEMA_ORDER.
        """
        order_set = set(_load_schema_order())
        repo_schemas = _find_repo_schemas()

        missing = repo_schemas - order_set
        assert not missing, (
            f"Les schemas suivants existent dans le repo mais manquent "
            f"de SCHEMA_ORDER : {sorted(missing)}. "
            f"Ajouter les noms dans init_db.py SCHEMA_ORDER a la bonne "
            f"position (avant tout module qui les reference par FK)."
        )

    def test_no_stale_in_schema_order(self):
        """SCHEMA_ORDER ne doit pas reference un module sans schema.sql.

        Protege contre le cas d'un module supprime mais toujours liste.
        """
        order = _load_schema_order()
        stale = [
            name for name in order
            if not (REPO_ROOT / name / "schema.sql").exists()
        ]
        assert not stale, (
            f"SCHEMA_ORDER reference des modules sans schema.sql : "
            f"{stale}. Retirer de init_db.py ou ajouter le schema.sql."
        )
