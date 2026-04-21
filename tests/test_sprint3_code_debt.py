"""Tests Sprint 3 — Axe 12 : Dette structurelle du code.

Tests pour : zéro except:pass, state.py extraction, backward compat.
"""

import inspect


# ─── Zéro except:pass ─────────────────────────────────────────


class TestExceptPass:
    """Vérifie qu'il n'y a plus de except:pass dans main.py."""

    def test_zero_except_pass_in_main(self):
        """main.py ne doit plus contenir de except ... : pass."""
        with open("main.py") as f:
            lines = f.readlines()
        count = 0
        for i, line in enumerate(lines):
            if line.strip().startswith("except") and i + 1 < len(lines):
                if lines[i + 1].strip() == "pass":
                    count += 1
        assert count == 0, f"Found {count} except:pass blocks in main.py"

    def test_main_has_logger(self):
        """main.py a un logger (log = logging.getLogger)."""
        with open("main.py") as f:
            content = f.read()
        assert "log = logging.getLogger" in content


# ─── state.py Extraction ──────────────────────────────────────


class TestStateModule:
    """Vérifie que state.py existe et contient les bons éléments."""

    def test_state_module_exists(self):
        """state.py est importable."""
        import state
        assert state is not None

    def test_state_has_lock(self):
        """state.py exporte _STATE_LOCK."""
        from state import _STATE_LOCK
        import threading
        assert isinstance(_STATE_LOCK, type(threading.Lock()))

    def test_state_has_four_dicts(self):
        """state.py exporte les 4 state dicts."""
        from state import (
            _TZIMTZUM_STATE,
            _NITZOTZOT_STATE,
            _IGULIM_STATE,
            _HISHTALSHELUT_STATE,
        )
        assert isinstance(_TZIMTZUM_STATE, dict)
        assert isinstance(_NITZOTZOT_STATE, dict)
        assert isinstance(_IGULIM_STATE, dict)
        assert isinstance(_HISHTALSHELUT_STATE, dict)

    def test_state_has_mutation_functions(self):
        """state.py exporte les 5 fonctions de mutation."""
        from state import (
            collect_nitzutz,
            check_tikkun_cycle,
            log_igulim_switch,
            log_world_transition,
            init_nitzotzot_from_db,
        )
        assert callable(collect_nitzutz)
        assert callable(check_tikkun_cycle)
        assert callable(log_igulim_switch)
        assert callable(log_world_transition)
        assert callable(init_nitzotzot_from_db)

    def test_state_has_olamot_chain(self):
        """state.py exporte _OLAMOT_CHAIN."""
        from state import _OLAMOT_CHAIN
        assert _OLAMOT_CHAIN == ["assiah", "yetzirah", "briah", "atziluth"]


# ─── Backward Compatibility ──────────────────────────────────


class TestBackwardCompat:
    """Vérifie que main.py re-exporte tout depuis state.py."""

    def test_main_reexports_states(self):
        """main.py re-exporte les state dicts."""
        from main import (
            _STATE_LOCK,
            _TZIMTZUM_STATE,
            _NITZOTZOT_STATE,
            _IGULIM_STATE,
            _HISHTALSHELUT_STATE,
        )
        # Vérifier que ce sont les MÊMES objets (pas des copies)
        from state import _STATE_LOCK as sl
        assert _STATE_LOCK is sl

    def test_main_reexports_functions(self):
        """main.py re-exporte les fonctions de mutation."""
        from main import (
            _collect_nitzutz,
            _check_tikkun_cycle,
            _log_igulim_switch,
            _log_world_transition,
        )
        assert callable(_collect_nitzutz)
        assert callable(_check_tikkun_cycle)

    def test_tanya_import_still_works(self):
        """tanya/birur_nogah.py peut toujours importer _collect_nitzutz."""
        from main import _collect_nitzutz
        assert callable(_collect_nitzutz)

    def test_main_py_reduced(self):
        """main.py reste dans une taille raisonnable (< 7500 lignes)."""
        with open("main.py") as f:
            lines = f.readlines()
        assert len(lines) < 7500, f"main.py has {len(lines)} lines, should be < 7500"

    def test_state_py_exists(self):
        """state.py existe comme module séparé."""
        with open("state.py") as f:
            content = f.read()
        assert "STATE_LOCK" in content
        assert "NITZOTZOT" in content
