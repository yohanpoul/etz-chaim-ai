"""Tests détection de domaine — Binah-de-Hod : classifier correctement."""

import pytest

from selfmap.domain_detector import detect_domain


def test_detect_python():
    domain, conf = detect_domain("How do I use pandas DataFrame in Python?")
    assert domain == "python"
    assert conf > 0.3


def test_detect_kabbalah():
    domain, conf = detect_domain("What are the 10 Sephiroth in the Tree of Life?")
    assert domain == "kabbalah"


def test_detect_medicine():
    domain, conf = detect_domain("What are the symptoms of a heart disease?")
    assert domain == "medicine"


def test_detect_math():
    domain, conf = detect_domain("What is the derivative of x squared?")
    assert domain == "math"


def test_detect_unknown():
    domain, conf = detect_domain("qwertyuiop asdfghjkl")
    assert domain == "general"
    assert conf < 0.5


def test_detect_french_health():
    domain, conf = detect_domain("Le jeûne intermittent améliore le sommeil")
    assert domain == "health"
