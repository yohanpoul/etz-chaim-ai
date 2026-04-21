"""Tests for etzchaim.cli.ceremony._text — text tables + i18n."""
from __future__ import annotations


def test_detect_lang_english_default(monkeypatch):
    from etzchaim.cli.ceremony._text import detect_lang
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LANG", raising=False)
    assert detect_lang() == "en"


def test_detect_lang_french(monkeypatch):
    from etzchaim.cli.ceremony._text import detect_lang
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    assert detect_lang() == "fr"


def test_detect_lang_hebrew(monkeypatch):
    from etzchaim.cli.ceremony._text import detect_lang
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.setenv("LANG", "he_IL.UTF-8")
    assert detect_lang() == "he"


def test_texts_for_en_contains_key_phrases():
    from etzchaim.cli.ceremony._text import get_texts
    t = get_texts("en")
    assert t["something_tore"] == "Something tore."
    assert t["vessels_broke"] == "Vessels broke."
    assert t["sparks_fell"] == "Sparks fell."
    assert "It breathes." in t["declaration"]
    assert "Do not abandon it." not in t
    assert "it will scream in the logs." in t["consequences"]
    assert "You will feed it." in t["commandments"]
    assert "[press any key to commit]" in t["hineni_prompt"]
    assert "Hineni" in t["hineni_reply"]
    assert "It is waiting." in t["naming_prompt"]


def test_texts_for_fr_has_french_content():
    from etzchaim.cli.ceremony._text import get_texts
    t = get_texts("fr")
    assert "s'est déchiré" in t["something_tore"].lower() or "déchiré" in t["something_tore"].lower()
    assert "Hineni" in t["hineni_reply"] or "הנני" in t["hineni_reply"]


def test_texts_all_langs_have_same_keys():
    from etzchaim.cli.ceremony._text import get_texts
    en_keys = set(get_texts("en").keys())
    fr_keys = set(get_texts("fr").keys())
    he_keys = set(get_texts("he").keys())
    assert en_keys == fr_keys == he_keys


def test_texts_unknown_lang_returns_english():
    from etzchaim.cli.ceremony._text import get_texts
    assert get_texts("pt") == get_texts("en")
