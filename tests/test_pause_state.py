"""Tests for pause_state — etz pause / etz go."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from pause_state import (
    _DEFAULTS,
    get_all,
    is_paused,
    set_paused,
)


@pytest.fixture
def tmp_pause_file(tmp_path):
    fake_file = tmp_path / "pause_state.json"
    with patch("pause_state.PAUSE_FILE", fake_file):
        yield fake_file


class TestPauseState:
    def test_defaults_when_no_file(self, tmp_pause_file):
        assert get_all() == _DEFAULTS

    def test_set_and_get_hitbonenut(self, tmp_pause_file):
        set_paused("hitbonenut", True)
        assert is_paused("hitbonenut") is True
        assert is_paused("karpathy") is False

    def test_set_and_get_karpathy(self, tmp_pause_file):
        set_paused("karpathy", True)
        assert is_paused("karpathy") is True
        assert is_paused("hitbonenut") is False

    def test_set_both(self, tmp_pause_file):
        set_paused("hitbonenut", True)
        set_paused("karpathy", True)
        state = get_all()
        assert state["hitbonenut_paused"] is True
        assert state["karpathy_paused"] is True

    def test_resume(self, tmp_pause_file):
        set_paused("hitbonenut", True)
        assert is_paused("hitbonenut") is True
        set_paused("hitbonenut", False)
        assert is_paused("hitbonenut") is False

    def test_file_persisted_as_json(self, tmp_pause_file):
        set_paused("karpathy", True)
        data = json.loads(tmp_pause_file.read_text())
        assert data["karpathy_paused"] is True

    def test_corrupt_file_returns_defaults(self, tmp_pause_file):
        tmp_pause_file.write_text("not json!!!")
        assert get_all() == _DEFAULTS
