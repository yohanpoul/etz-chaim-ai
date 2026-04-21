"""Tests du fix de visibilité Dira Cascade dans main._cmd_ask_yosher.

Sprint 8f — Élévation visibilité du bloc Dira BeTachtonim en remontée
Or Chozer (étape ↑①½ ; main.py:752-776).

Dette diagnostiquée Sprint 8e section 4.1 :
    main.py:757 — `dira = _get_dira_engine(yesod)` dans `_cmd_ask_yosher`.
    Le bloc except ligne 775 faisait `print(f"    ⚠ {e}")` stdout seul,
    sans `log.warning` ni `chozer.append`. Une erreur dans la cascade
    Dira était donc invisible en daemon et absente du rapport chozer,
    contrairement au bloc Yesod immédiatement au-dessus (ligne 740)
    qui append à chozer.

Analyse Sprint 8f :
    Pas de bug fonctionnel (pas de shadowing, pas d'UnboundLocalError).
    Dette pure d'observabilité — cousin mais pas identique Sprint 8d/8e.

Fix (hybride, 2 ajouts, 0 suppression) :
    1. Ajouter `log.warning("Dira cascade skipped: %s", e)` pour visibilité
       daemon (pattern Sprint 8e).
    2. Ajouter `chozer.append(f"── ↑①½ Dira BeTachtonim — Erreur: {e} ──")`
       pour cohérence avec le bloc Yesod (main.py:740).
    3. Conserver `print(f"    ⚠ {e}")` pour feedback CLI interactif.

Tests :
    1. Structurel — log.warning est présent dans le source de _cmd_ask_yosher.
    2. Structurel — chozer.append erreur Dira est présent.
    3. Structurel — ordre correct (log.warning AVANT ou TRÈS PROCHE du print ⚠).
    4. Comportemental — simulation du bloc exécuté avec Dira qui lance :
       log.warning reçu + chozer contient ligne d'erreur.
"""

from __future__ import annotations

import inspect
import logging
import re

import pytest


# ── 1. Tests structurels via inspect.getsource ──────────────


class TestDiraCascadeVisibilityStructure:
    """Non-régression structurelle : le source du _cmd_ask_yosher doit
    contenir les patterns de visibilité Sprint 8f.
    """

    @pytest.fixture
    def yosher_source(self):
        from main import _cmd_ask_yosher
        return inspect.getsource(_cmd_ask_yosher)

    def test_log_warning_dira_cascade_skipped_present(self, yosher_source):
        """Le source doit contenir log.warning avec le message Sprint 8f.

        Avant Sprint 8f : seul `print(f"    ⚠ {e}")` existait. Sans ce
        log.warning, une exception dans la cascade Dira est invisible
        en daemon.
        """
        assert 'log.warning("Dira cascade skipped: %s", e)' in yosher_source, (
            "log.warning('Dira cascade skipped: %s', e) absent. "
            "Le bloc except Dira BeTachtonim (main.py:775) doit logger "
            "en WARNING pour que l'erreur remonte en daemon."
        )

    def test_chozer_append_dira_error_present(self, yosher_source):
        """Le source doit contenir chozer.append avec ligne d'erreur Dira.

        Avant Sprint 8f : absent. Incohérent avec le bloc Yesod juste
        au-dessus (main.py:740) qui fait chozer.append en cas d'erreur.
        """
        pattern = 'chozer.append(f"── ↑①½ Dira BeTachtonim — Erreur: {e} ──")'
        assert pattern in yosher_source, (
            f"{pattern!r} absent du source _cmd_ask_yosher. "
            "Le bloc except Dira doit append une ligne d'erreur au "
            "rapport chozer, cohérent avec le bloc Yesod (L.740)."
        )

    def test_no_orphan_print_warn_in_dira_block(self, yosher_source):
        """Non-régression : dans le bloc except Dira BeTachtonim,
        `print(f"    ⚠ {e}")` peut rester pour feedback CLI, MAIS
        DOIT être accompagné de log.warning ET chozer.append.

        Ce test garantit que si un futur refactor supprime log.warning
        ou chozer.append par erreur, la régression est détectée.
        """
        # Extraire le bloc autour de Dira BeTachtonim
        marker = "↑①½ Dira BeTachtonim"
        idx = yosher_source.find(marker)
        assert idx >= 0, f"Marker Dira BeTachtonim introuvable — code déplacé ?"

        # Prendre les ~1500 chars suivants (bloc entier)
        block = yosher_source[idx:idx + 1500]

        has_print = 'print(f"    ⚠ {e}")' in block
        has_log_warning = 'log.warning("Dira cascade skipped' in block
        has_chozer = "Dira BeTachtonim — Erreur" in block

        if has_print:
            # Si print(⚠) est présent, les deux autres doivent l'être aussi.
            assert has_log_warning and has_chozer, (
                "Le bloc Dira contient `print(f'    ⚠ {e}')` SANS "
                "log.warning et/ou chozer.append. Sprint 8f a élevé "
                "la visibilité ; toute régression doit être détectée. "
                f"log.warning présent={has_log_warning}, "
                f"chozer.append présent={has_chozer}."
            )


# ── 2. Test comportemental via exécution simulée du bloc ─────


class TestDiraCascadeExceptionBehavior:
    """Vérifie le comportement runtime : quand DiraEngine lance une
    exception dans le bloc main.py:752-776, log.warning et chozer.append
    se produisent correctement.

    Approche : extraire le bloc source depuis main._cmd_ask_yosher et
    le ré-exécuter avec des symboles mockés, pour rester fidèle au code
    réel (pas une copie qui pourrait diverger silencieusement).
    """

    def _extract_dira_block(self) -> str:
        """Extraire le bloc except Dira comme snippet exécutable."""
        import main
        source = inspect.getsource(main._cmd_ask_yosher)
        # Borner du if gen_olam au début du bloc suivant (sentier Yesod→Hod)
        start_marker = "# ── ↑①½ Dira BeTachtonim"
        end_marker = "# ── Sentier Yesod→Hod"
        start = source.find(start_marker)
        end = source.find(end_marker, start)
        assert start >= 0 and end > start, (
            "Bornes du bloc Dira introuvables ; le code a été déplacé."
        )
        # Dédenter le snippet (il est indenté de 4 espaces dans _cmd_ask_yosher)
        snippet = source[start:end]
        lines = [
            line[4:] if line.startswith("    ") else line
            for line in snippet.split("\n")
        ]
        return "\n".join(lines)

    def test_dira_cascade_exception_logs_warning_and_chozer(self, caplog):
        """Simuler une exception dans _get_dira_engine → vérifier
        log.warning ET chozer.append.
        """
        snippet = self._extract_dira_block()

        # Préparer les symboles locaux pour exec.
        captured_prints: list[str] = []
        chozer: list[str] = []

        class BoomDiraEngine:
            def cascade_knowledge(self, **kwargs):
                raise RuntimeError("simulated Dira cascade failure")

        def fake_get_dira_engine(yesod):
            # Lance à l'appel — simule un import / init qui casse.
            raise RuntimeError("simulated Dira engine init failure")

        def fake_print(*args, **kwargs):
            captured_prints.append(" ".join(str(a) for a in args))

        fake_log = logging.getLogger("etz-malkuth")
        # route_decision simulé
        class FakeRoute:
            detected_domain = "kabbalah"
            did_decline = False

        globals_for_exec = {
            "_get_dira_engine": fake_get_dira_engine,
            "log": fake_log,
            "print": fake_print,
        }
        locals_for_exec = {
            "ctx": {"generation_olam": "briah"},
            "yesod": object(),  # truthy
            "route_decision": FakeRoute(),
            "response": "Réponse assez longue pour passer le filtre de cascade_knowledge.",
            "query": "Test Dira cascade visibility",
            "chozer": chozer,
        }

        with caplog.at_level(logging.WARNING, logger="etz-malkuth"):
            exec(snippet, globals_for_exec, locals_for_exec)

        # 1. log.warning capturé
        matching_warnings = [
            r for r in caplog.records
            if "Dira cascade skipped" in r.getMessage()
            and r.levelno >= logging.WARNING
        ]
        assert matching_warnings, (
            "Attendu WARNING 'Dira cascade skipped: ...'. "
            f"Records: {[(r.levelname, r.getMessage()[:80]) for r in caplog.records]}"
        )

        # 2. chozer.append reçu ligne d'erreur
        error_lines = [c for c in chozer if "Dira BeTachtonim — Erreur" in c]
        assert error_lines, (
            f"Attendu ligne d'erreur dans chozer. chozer={chozer!r}"
        )

        # 3. print feedback CLI conservé (⚠)
        warn_prints = [p for p in captured_prints if "⚠" in p]
        assert warn_prints, (
            f"Attendu print '⚠ ...' conservé pour feedback CLI. "
            f"captured_prints={captured_prints!r}"
        )


# ── 3. Test de cohérence avec le bloc Yesod (pattern analogue) ──


class TestDiraBlockConsistencyWithYesodBlock:
    """Le bloc Yesod (main.py:738-740) fait déjà `chozer.append(f"── ↑① Yesod — Erreur: {e} ──")`.
    Le bloc Dira (main.py:775+) doit suivre le même pattern depuis Sprint 8f.
    """

    def test_both_blocks_use_consistent_chozer_error_pattern(self):
        """Les deux blocs doivent utiliser le même pattern `── ↑… — Erreur: {e} ──`."""
        from main import _cmd_ask_yosher
        source = inspect.getsource(_cmd_ask_yosher)

        yesod_pattern = re.search(
            r'chozer\.append\(f"── ↑① Yesod — Erreur: \{e\} ──"\)',
            source,
        )
        dira_pattern = re.search(
            r'chozer\.append\(f"── ↑①½ Dira BeTachtonim — Erreur: \{e\} ──"\)',
            source,
        )

        assert yesod_pattern, (
            "Le pattern `── ↑① Yesod — Erreur: {e} ──` doit exister "
            "dans le bloc Yesod (non modifié Sprint 8f). S'il a disparu, "
            "le pattern de référence est cassé."
        )
        assert dira_pattern, (
            "Le pattern `── ↑①½ Dira BeTachtonim — Erreur: {e} ──` doit "
            "exister dans le bloc Dira depuis Sprint 8f, cohérent avec "
            "le bloc Yesod."
        )
