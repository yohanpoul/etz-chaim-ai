"""Tests for etzchaim.cli._age.human_age."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def test_human_age_just_now_under_10_seconds():
    from etzchaim.cli._age import human_age
    t = _now_utc() - timedelta(seconds=5)
    assert human_age(t) == "just now"


def test_human_age_seconds_under_a_minute():
    from etzchaim.cli._age import human_age
    t = _now_utc() - timedelta(seconds=45)
    assert human_age(t) == "45s"


def test_human_age_minutes_under_an_hour():
    from etzchaim.cli._age import human_age
    t = _now_utc() - timedelta(seconds=90)
    assert human_age(t) == "1m"
    t = _now_utc() - timedelta(minutes=30)
    assert human_age(t) == "30m"


def test_human_age_hours_minutes_under_a_day():
    from etzchaim.cli._age import human_age
    t = _now_utc() - timedelta(hours=3, minutes=22)
    assert human_age(t) == "3h 22m"


def test_human_age_days_hours_over_a_day():
    from etzchaim.cli._age import human_age
    t = _now_utc() - timedelta(hours=50)  # 2d 2h
    assert human_age(t) == "2d 2h"


def test_human_age_naive_datetime_raises():
    from etzchaim.cli._age import human_age
    with pytest.raises(ValueError):
        human_age(datetime(2026, 1, 1))  # no tzinfo


def test_human_age_future_timestamp_returns_just_now():
    """Defensive: clock skew etc. shouldn't break status output."""
    from etzchaim.cli._age import human_age
    t = _now_utc() + timedelta(seconds=5)
    assert human_age(t) == "just now"
