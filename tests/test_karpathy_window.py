"""Tests de _in_karpathy_window — fenêtre horaire Karpathy.

Couvre les deux régimes :
  1. Simple (END > START) — mode nuit provisoire avril-juin 2026
     (MacBook Pro éteint la nuit, Karpathy décalé en soirée).
  2. Wrap minuit (END <= START) — mode doctrinal originel, restauré
     quand le Mac mini dédié sera disponible.

Voir audits/mode_nuit_provisoire_avril_juin_2026.md.
"""
from __future__ import annotations

import importlib
import sys
from unittest import mock


def _reload_daemon_with(start: int, end: int):
    """Recharger daemon avec des constantes Karpathy patchées."""
    if "daemon" in sys.modules:
        del sys.modules["daemon"]
    import daemon  # noqa: E402
    daemon.KARPATHY_START_HOUR = start
    daemon.KARPATHY_END_HOUR = end
    return daemon


def test_in_karpathy_window_avril_2026_mode_provisoire():
    """Mode provisoire : START=21, END=23 → fenêtre 21h-22h59."""
    daemon = _reload_daemon_with(21, 23)
    # Heures dans la fenêtre
    for hour in (21, 22):
        for minute in (0, 15, 30, 45, 59):
            assert daemon._in_karpathy_window(hour, minute), (
                f"Attendu True pour {hour}:{minute:02d} (mode provisoire)"
            )
    # Heures hors fenêtre : toute la journée sauf 21, 22
    for hour in list(range(0, 21)) + [23]:
        assert not daemon._in_karpathy_window(hour, 0), (
            f"Attendu False pour {hour}:00 (hors fenêtre provisoire)"
        )


def test_in_karpathy_window_juin_2026_mode_doctrinal():
    """Mode doctrinal : START=23, END=0 → wrap minuit, 23h et 0h00-0h30."""
    daemon = _reload_daemon_with(23, 0)
    # 23h : toute l'heure dans la fenêtre
    for minute in (0, 15, 30, 45, 59):
        assert daemon._in_karpathy_window(23, minute), (
            f"Attendu True pour 23:{minute:02d} (mode doctrinal)"
        )
    # 0h : seulement 0:00 à 0:30 inclus
    for minute in (0, 15, 30):
        assert daemon._in_karpathy_window(0, minute), (
            f"Attendu True pour 0:{minute:02d}"
        )
    # 0:31+ : hors fenêtre
    for minute in (31, 45, 59):
        assert not daemon._in_karpathy_window(0, minute), (
            f"Attendu False pour 0:{minute:02d} (post-0:30)"
        )
    # Toutes autres heures : hors fenêtre
    for hour in range(1, 23):
        assert not daemon._in_karpathy_window(hour, 0), (
            f"Attendu False pour {hour}:00 (hors wrap minuit)"
        )


def test_no_karpathy_during_sleep_window_avril_2026():
    """Pendant le sleep Mac (0h-9h), Karpathy ne se déclenche jamais
    en mode provisoire (START=21, END=23)."""
    daemon = _reload_daemon_with(21, 23)
    for hour in range(0, 9):
        for minute in (0, 30, 59):
            assert not daemon._in_karpathy_window(hour, minute), (
                f"BUG : Karpathy ne doit pas être actif à "
                f"{hour}:{minute:02d} (Mac endormi)"
            )


def test_karpathy_window_boundaries_avril_2026():
    """Frontières exactes du mode provisoire."""
    daemon = _reload_daemon_with(21, 23)
    # 20:59 → hors
    assert not daemon._in_karpathy_window(20, 59)
    # 21:00 → dans
    assert daemon._in_karpathy_window(21, 0)
    # 22:59 → dans (inclusif puisque hour==22 < 23)
    assert daemon._in_karpathy_window(22, 59)
    # 23:00 → hors (exclusif)
    assert not daemon._in_karpathy_window(23, 0)
