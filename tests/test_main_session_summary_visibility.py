"""Tests du fix visibilité des stats Dira/Birur dans session summary.

Sprint megaclean T1 — Dette 5 (résiduelle Sprint 8f).

Dette diagnostiquée :
    main.py:~1128 — blocs `dira_stats = _get_dira_engine().assess_dira_state()`
    et `birur_stats = _get_birurim_engine().get_birur_stats()` dans la
    section "── Méta ──" de `_cmd_ask_yosher` (affichage fin de session).
    Les blocs except faisaient `log.debug("fallback: %s", e)` — avaleur
    silencieux (pattern Sprint 8d/8e/8f). Si assess_dira_state() ou
    get_birur_stats() échouait, la ligne correspondante disparaissait
    silencieusement et aucun WARNING ne remontait en daemon.

Fix (minimal, 2 blocs adjacents identiques) :
    1. log.debug → log.warning avec message contextualisé "in session summary"
    2. print fallback user-facing `(indisponible — {type(e).__name__})`

Différence avec Sprint 8f (tests/test_main_dira_cascade_visibility.py) :
    Sprint 8f traitait le bloc Or Chozer Dira cascade (main.py:~752) qui
    touche chozer.append. Ici, le bloc est en session summary (post-chozer),
    pas d'append chozer nécessaire — seulement log.warning + print fallback.
"""

from __future__ import annotations

import inspect
import logging
import re


class TestSessionSummaryVisibilityStructure:
    """Tests structurels : le source de `_cmd_ask_yosher` doit contenir
    les patterns log.warning + print fallback pour Dira ET Birur.
    """

    def test_dira_stats_uses_log_warning_not_debug(self):
        from main import _cmd_ask_yosher
        src = inspect.getsource(_cmd_ask_yosher)
        assert 'log.warning("Dira stats unavailable in session summary' in src, (
            "log.warning('Dira stats unavailable in session summary: %s', e) "
            "absent du bloc session summary. Le fallback log.debug serait "
            "un avaleur silencieux (pattern Sprint 8d/8e/8f)."
        )

    def test_birur_stats_uses_log_warning_not_debug(self):
        from main import _cmd_ask_yosher
        src = inspect.getsource(_cmd_ask_yosher)
        assert 'log.warning("Birur stats unavailable in session summary' in src, (
            "log.warning('Birur stats unavailable in session summary: %s', e) "
            "absent. Même pattern que Dira — fix megaclean T1."
        )

    def test_dira_fallback_print_line_present(self):
        """Quand assess_dira_state() échoue, une ligne user-facing doit
        remplacer la ligne 'Dira mémoires' normale, pour que l'utilisateur
        voie que la section a échoué (pas juste une ligne disparue).
        """
        from main import _cmd_ask_yosher
        src = inspect.getsource(_cmd_ask_yosher)
        pattern = r'print\(f"  Dira mémoires\s+: \(indisponible — \{type\(e\)\.__name__\}\)"\)'
        assert re.search(pattern, src), (
            "Print fallback 'Dira mémoires : (indisponible — ...)' absent. "
            "Sans ce print, l'utilisateur ne voit pas qu'une section a échoué."
        )

    def test_birur_fallback_print_line_present(self):
        from main import _cmd_ask_yosher
        src = inspect.getsource(_cmd_ask_yosher)
        pattern = r'print\(f"  Birur Nogah\s+: \(indisponible — \{type\(e\)\.__name__\}\)"\)'
        assert re.search(pattern, src), (
            "Print fallback 'Birur Nogah : (indisponible — ...)' absent."
        )

    def test_no_log_debug_fallback_remains_in_session_summary(self):
        """Non-régression : ni le bloc Dira ni le bloc Birur en session
        summary ne doivent contenir `log.debug("fallback: %s", e)` après T1.

        Autres occurrences de `log.debug("fallback: %s", e)` dans main.py
        (close_tree L.249, cmd_ask Keter L.460) sont HORS scope Dette 5.
        """
        from main import _cmd_ask_yosher
        src = inspect.getsource(_cmd_ask_yosher)
        # Borner à la section Méta — Dira & Birur
        meta_idx = src.find("── Méta ──")
        levushim_idx = src.find("# Levushim", meta_idx)
        assert meta_idx >= 0, "Section Méta introuvable dans _cmd_ask_yosher."
        assert levushim_idx > meta_idx, "Section Levushim introuvable."

        section = src[meta_idx:levushim_idx]
        # Aucun log.debug('fallback: ...') ne doit rester dans cette section.
        assert 'log.debug("fallback:' not in section, (
            "log.debug('fallback: %s', e) présent dans la section Méta — "
            "Dette 5 non fixée. Attendu log.warning + print fallback."
        )


class TestSessionSummaryExceptionBehavior:
    """Test comportemental : simuler une exception dans
    _get_dira_engine().assess_dira_state() et vérifier que log.warning
    est émis + que la ligne fallback est imprimée.
    """

    def test_dira_exception_emits_warning_and_fallback_print(self, caplog, capsys, monkeypatch):
        """Simuler _get_dira_engine() qui retourne un objet dont
        assess_dira_state() lance. Exécuter le bloc try/except isolé
        par exec et vérifier log.warning + print fallback.
        """
        import main

        class BoomDiraEngine:
            def assess_dira_state(self):
                raise RuntimeError("simulated Dira stats failure")

        monkeypatch.setattr(main, "_get_dira_engine", lambda: BoomDiraEngine())

        # Extraire le bloc try/except Dira du source pour exécution isolée
        src = inspect.getsource(main._cmd_ask_yosher)
        marker = "dira_stats = _get_dira_engine().assess_dira_state()"
        idx = src.find(marker)
        assert idx >= 0, f"Marker {marker!r} absent — code déplacé."
        # Remonter au `try:` et descendre jusqu'à fin du `except`
        try_idx = src.rfind("try:", 0, idx)
        # Fin = fin de la 2e ligne print() du except (jusqu'au next "    #" ou "    try:")
        end_idx = src.find("# Birur Nogah", idx)
        assert try_idx >= 0 and end_idx > try_idx, "Bornes bloc Dira introuvables."

        snippet = src[try_idx:end_idx]
        # Dédenter (bloc à 4 espaces)
        snippet = "\n".join(
            line[4:] if line.startswith("    ") else line
            for line in snippet.split("\n")
        )

        fake_log = logging.getLogger("etz-malkuth")
        captured_prints: list[str] = []

        def fake_print(*args, **kwargs):
            captured_prints.append(" ".join(str(a) for a in args))

        with caplog.at_level(logging.WARNING, logger="etz-malkuth"):
            exec(
                snippet,
                {
                    "_get_dira_engine": lambda: BoomDiraEngine(),
                    "log": fake_log,
                    "print": fake_print,
                },
                {},
            )

        # 1. log.warning capturé avec le message attendu
        warnings = [
            r for r in caplog.records
            if "Dira stats unavailable in session summary" in r.getMessage()
            and r.levelno >= logging.WARNING
        ]
        assert warnings, (
            "Attendu WARNING 'Dira stats unavailable in session summary: ...'. "
            f"Records: {[(r.levelname, r.getMessage()[:80]) for r in caplog.records]}"
        )

        # 2. print fallback émis
        fallback_lines = [p for p in captured_prints if "indisponible" in p and "Dira" in p]
        assert fallback_lines, (
            f"Attendu ligne print 'Dira mémoires : (indisponible — ...)'. "
            f"captured_prints={captured_prints!r}"
        )

    def test_birur_exception_emits_warning_and_fallback_print(self, caplog, monkeypatch):
        import main

        class BoomBirurEngine:
            def get_birur_stats(self):
                raise RuntimeError("simulated Birur stats failure")

        monkeypatch.setattr(main, "_get_birurim_engine", lambda: BoomBirurEngine())

        src = inspect.getsource(main._cmd_ask_yosher)
        marker = "birur_stats = _get_birurim_engine().get_birur_stats()"
        idx = src.find(marker)
        assert idx >= 0, f"Marker {marker!r} absent — code déplacé."
        try_idx = src.rfind("try:", 0, idx)
        end_idx = src.find("# Levushim", idx)
        assert try_idx >= 0 and end_idx > try_idx, "Bornes bloc Birur introuvables."

        snippet = src[try_idx:end_idx]
        snippet = "\n".join(
            line[4:] if line.startswith("    ") else line
            for line in snippet.split("\n")
        )

        fake_log = logging.getLogger("etz-malkuth")
        captured_prints: list[str] = []

        def fake_print(*args, **kwargs):
            captured_prints.append(" ".join(str(a) for a in args))

        with caplog.at_level(logging.WARNING, logger="etz-malkuth"):
            exec(
                snippet,
                {
                    "_get_birurim_engine": lambda: BoomBirurEngine(),
                    "log": fake_log,
                    "print": fake_print,
                },
                {},
            )

        warnings = [
            r for r in caplog.records
            if "Birur stats unavailable in session summary" in r.getMessage()
            and r.levelno >= logging.WARNING
        ]
        assert warnings, (
            "Attendu WARNING 'Birur stats unavailable in session summary: ...'. "
            f"Records: {[(r.levelname, r.getMessage()[:80]) for r in caplog.records]}"
        )

        fallback_lines = [p for p in captured_prints if "indisponible" in p and "Birur" in p]
        assert fallback_lines, (
            f"Attendu ligne print 'Birur Nogah : (indisponible — ...)'. "
            f"captured_prints={captured_prints!r}"
        )
