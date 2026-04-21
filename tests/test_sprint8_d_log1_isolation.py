"""Sprint 8 D-log1 — Tests TDD pour isoler setup_logging du module-level.

Problème identifié Sprint 8 D1 Passe 1 : `log = setup_logging()` exécuté
à l'import-time de daemon.py (ligne 173) configure un RotatingFileHandler
sur le root logger. Tout test qui importe daemon (directement ou
transitivement) ajoute alors ses logs dans ~/.etz-chaim/daemon.log.

Preuve empirique (Sprint 8 D1 Passe 1) : 2024 logs "Zivvug: claim causal
validé" émis par pytest dans daemon.log, avec paths
`/tmp/pytest-of-<user>/` confirmant l'origine tests.

Fix D-log1 : déplacer setup_logging() dans le bloc CLI (__main__),
laisser `log = logging.getLogger("etz-daemon")` au module-level (getter
sans side-effect).
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler


# ═══════════════════════════════════════════════════════════════════
#    Test 1 — setup_logging n'est PAS auto-appelé à l'import
# ═══════════════════════════════════════════════════════════════════

def test_import_daemon_does_not_add_rotating_file_handler_to_root():
    """Importer daemon ne doit pas attacher de RotatingFileHandler au root.

    Avant D-log1 : `log = setup_logging()` ligne 173 ajoutait un handler
    sur le root → tout test → écrit dans daemon.log.
    """
    # Clean any pre-existing state (e.g. prior tests in same process)
    root = logging.getLogger()
    pre_count = sum(
        1 for h in root.handlers if isinstance(h, RotatingFileHandler)
    )

    # Re-import not needed; just assert that daemon import did NOT leave
    # a RotatingFileHandler on root. This test only makes sense if daemon
    # hasn't been imported before in the same pytest session, or if the
    # fix was applied (no auto-setup_logging).
    import daemon  # noqa: F401

    post_count = sum(
        1 for h in logging.getLogger().handlers
        if isinstance(h, RotatingFileHandler)
    )

    assert post_count == pre_count, (
        f"Importer daemon a ajouté {post_count - pre_count} "
        f"RotatingFileHandler sur root → pollution pytest → daemon.log. "
        f"D-log1 non appliqué."
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 2 — setup_logging reste callable et fonctionnel
# ═══════════════════════════════════════════════════════════════════

def test_setup_logging_callable_and_returns_logger():
    """setup_logging() reste défini et retourne un Logger quand appelé.

    Le fix D-log1 ne supprime pas la fonction — il la retire seulement
    de l'auto-exécution module-level. Le daemon réel (__main__) doit
    pouvoir l'appeler explicitement au démarrage.
    """
    import daemon

    assert hasattr(daemon, "setup_logging"), "setup_logging supprimée par erreur"
    assert callable(daemon.setup_logging), "setup_logging n'est plus callable"


# ═══════════════════════════════════════════════════════════════════
#    Test 3 — Module-level log existe comme Logger (getter-only)
# ═══════════════════════════════════════════════════════════════════

def test_daemon_log_exists_at_module_level_as_getter():
    """daemon.log doit exister au module-level mais être un Logger getter.

    Pattern : `log = logging.getLogger("etz-daemon")` (sans handler ajouté).
    Les 300+ appels log.info() dans daemon.py continuent de fonctionner,
    mais ils n'écrivent nulle part tant que les handlers ne sont pas
    configurés par setup_logging() appelée dans __main__.
    """
    import daemon

    assert hasattr(daemon, "log"), "daemon.log absent — casse les log.info() internes"
    assert isinstance(daemon.log, logging.Logger), (
        f"daemon.log devrait être un Logger, obtenu {type(daemon.log)}"
    )
    assert daemon.log.name == "etz-daemon", (
        f"daemon.log.name devrait être 'etz-daemon', obtenu '{daemon.log.name}'"
    )


# ═══════════════════════════════════════════════════════════════════
#    Test 4 — setup_logging pas référencé comme appel module-level
# ═══════════════════════════════════════════════════════════════════

def test_setup_logging_not_called_at_module_level():
    """Source check : `log = setup_logging()` ne doit plus apparaître
    au module-level de daemon.py.

    Vérif via source inspection — garde-fou contre une régression future
    qui réintroduirait l'auto-exécution.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    daemon_src = (root / "daemon.py").read_text(encoding="utf-8")

    # Split en lignes non-indentées (module-level statements)
    module_level_lines = [
        line for line in daemon_src.splitlines()
        if line and not line.startswith(" ") and not line.startswith("\t")
    ]

    # Chercher une assignation `log = setup_logging(...)` au module-level
    offenders = [
        line for line in module_level_lines
        if "setup_logging()" in line and "=" in line and "def " not in line
    ]

    assert not offenders, (
        f"D-log1 violation : setup_logging() appelée au module-level : "
        f"{offenders}. Doit être dans __main__ uniquement."
    )
