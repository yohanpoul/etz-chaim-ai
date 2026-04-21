"""Tests for etzchaim.cli.ceremony._art — ASCII art + EKG."""
from __future__ import annotations


def test_logo_has_six_block_lines_and_hebrew():
    from etzchaim.cli.ceremony._art import LOGO_LINES, HEBREW_TREE_OF_LIFE
    assert len(LOGO_LINES) == 6
    assert HEBREW_TREE_OF_LIFE == "עץ חיים"


def test_narrow_logo_single_line():
    from etzchaim.cli.ceremony._art import NARROW_LOGO
    assert "\n" not in NARROW_LOGO
    assert "ETZ CHAIM" in NARROW_LOGO


def test_tree_lines_count_ten_sephirah_nodes():
    from etzchaim.cli.ceremony._art import TREE_LINES, SEPHIRAH_NODES
    assert len(SEPHIRAH_NODES) == 10
    for name_en, name_he, color in SEPHIRAH_NODES:
        assert name_en and name_he and color
    glyph_count = sum(line.count("◉") for line in TREE_LINES)
    assert glyph_count >= 10, f"expected ≥10 ◉ glyphs in tree, got {glyph_count}"


def test_ekg_frame_generator_yields_unique_frames():
    from etzchaim.cli.ceremony._art import ekg_frames
    frames = list(ekg_frames(width=40, count=5, seed=42))
    assert len(frames) == 5
    assert all(len(f) == 40 for f in frames)
    assert len(set(frames)) >= 2


def test_ekg_frame_uses_bar_glyphs():
    from etzchaim.cli.ceremony._art import ekg_frames
    frame = next(ekg_frames(width=80, count=1, seed=0))
    valid = set(" ▁▂▃▄▅▆▇█")
    assert set(frame) <= valid, f"unexpected chars: {set(frame) - valid}"


def test_glitch_text_scrambles_hebrew():
    from etzchaim.cli.ceremony._art import glitch_shevirah
    out = glitch_shevirah(seed=1)
    assert "שבירה" in out or "נפלו" in out
    assert any(c in out for c in "░▒▓")


def test_sephirah_colors_are_rich_compatible():
    from etzchaim.cli.ceremony._art import SEPHIRAH_NODES
    for _, _, color in SEPHIRAH_NODES:
        assert isinstance(color, str) and color, "empty color"


def test_sephirah_order_matches_descent():
    from etzchaim.cli.ceremony._art import SEPHIRAH_NODES
    names = [n[0] for n in SEPHIRAH_NODES]
    assert names == [
        "Keter", "Chokhmah", "Binah", "Chesed", "Gevurah",
        "Tiferet", "Netzach", "Hod", "Yesod", "Malkhut",
    ]
