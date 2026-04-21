#!/usr/bin/env python3
"""generate_avatars.py — 20 portraits SVG detailles pour Etz Chaim AI.

Style : dark fantasy portraits, eclairage ambre lateral, fond noir.
Chaque personnage a un visage detaille (yeux avec iris, nez, bouche),
des vetements avec plis et ornements, et des accessoires uniques.

Usage:
    python tools/generate_avatars.py
"""

from __future__ import annotations

import math
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "web" / "static" / "avatars"
W, H = 200, 250
CX = 100


# ═══════════════════════════════════════════════════════════
#  Primitives SVG bas-niveau
# ═══════════════════════════════════════════════════════════

def _a(tag: str, **kw) -> str:
    """Genere un element SVG auto-fermant."""
    attrs = " ".join(
        f'{k.replace("_", "-")}="{v}"'
        for k, v in kw.items()
        if v is not None
    )
    return f"<{tag} {attrs}/>\n"


def E(cx, cy, rx, ry, **kw):
    return _a("ellipse", cx=f"{cx:.1f}", cy=f"{cy:.1f}",
              rx=f"{rx:.1f}", ry=f"{ry:.1f}", **kw)


def C(cx, cy, r, **kw):
    return _a("circle", cx=f"{cx:.1f}", cy=f"{cy:.1f}", r=f"{r:.1f}", **kw)


def P(d, **kw):
    return _a("path", d=d, **kw)


def L(x1, y1, x2, y2, **kw):
    return _a("line", x1=f"{x1:.1f}", y1=f"{y1:.1f}",
              x2=f"{x2:.1f}", y2=f"{y2:.1f}",
              stroke_linecap="round", **kw)


def R(x, y, w, h, **kw):
    return _a("rect", x=f"{x:.1f}", y=f"{y:.1f}",
              width=f"{w:.1f}", height=f"{h:.1f}", **kw)


def T(x, y, text, **kw):
    attrs = " ".join(
        f'{k.replace("_", "-")}="{v}"'
        for k, v in kw.items()
        if v is not None
    )
    return f'<text x="{x}" y="{y}" {attrs}>{text}</text>\n'


def G(content: str, **kw) -> str:
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f"<g {attrs}>\n{content}</g>\n"


# ═══════════════════════════════════════════════════════════
#  Systeme de gradients et filtres (qualite visuelle)
# ═══════════════════════════════════════════════════════════

SHARED_DEFS = """<defs>
  <!-- Skin gradients -->
  <radialGradient id="skin-light" cx="40%" cy="35%">
    <stop offset="0%" stop-color="#e8c8a0"/>
    <stop offset="60%" stop-color="#d4b088"/>
    <stop offset="100%" stop-color="#b89068"/>
  </radialGradient>
  <radialGradient id="skin-med" cx="40%" cy="35%">
    <stop offset="0%" stop-color="#d4b088"/>
    <stop offset="60%" stop-color="#c8a27a"/>
    <stop offset="100%" stop-color="#a88960"/>
  </radialGradient>
  <radialGradient id="skin-dark" cx="40%" cy="35%">
    <stop offset="0%" stop-color="#c0a070"/>
    <stop offset="60%" stop-color="#a88960"/>
    <stop offset="100%" stop-color="#886840"/>
  </radialGradient>
  <!-- Rim light (amber from right) -->
  <linearGradient id="rim-r" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="#ffb000" stop-opacity="0"/>
    <stop offset="70%" stop-color="#ffb000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#ffb000" stop-opacity="0.25"/>
  </linearGradient>
  <!-- Ambient glow -->
  <radialGradient id="amb-glow" cx="55%" cy="35%">
    <stop offset="0%" stop-color="#ffb000" stop-opacity="0.08"/>
    <stop offset="100%" stop-color="#ffb000" stop-opacity="0"/>
  </radialGradient>
  <!-- Shadow overlay (right side darker) -->
  <linearGradient id="face-shadow" x1="0%" y1="0%" x2="100%" y2="20%">
    <stop offset="0%" stop-color="#000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#000" stop-opacity="0.2"/>
  </linearGradient>
  <!-- Metallic gold gradient -->
  <linearGradient id="gold" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#ffd700"/>
    <stop offset="50%" stop-color="#ffb000"/>
    <stop offset="100%" stop-color="#cc8800"/>
  </linearGradient>
  <!-- Metallic silver -->
  <linearGradient id="silver" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#ccc"/>
    <stop offset="50%" stop-color="#aaa"/>
    <stop offset="100%" stop-color="#888"/>
  </linearGradient>
  <!-- Filters -->
  <filter id="glow-amb" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="8"/>
  </filter>
  <filter id="glow-sm" x="-30%" y="-30%" width="160%" height="160%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="3"/>
  </filter>
  <filter id="soft" x="-10%" y="-10%" width="120%" height="120%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="1.5"/>
  </filter>
</defs>
"""


def background(bg_inner: str = "#1a1400", bg_outer: str = "#080800") -> str:
    """Fond noir avec lueur ambiante."""
    s = f"""<defs>
  <radialGradient id="bg-g" cx="52%" cy="33%">
    <stop offset="0%" stop-color="{bg_inner}"/>
    <stop offset="100%" stop-color="{bg_outer}"/>
  </radialGradient>
</defs>
"""
    s += R(0, 0, W, H, fill="url(#bg-g)")
    # Halo ambre derriere la tete
    s += C(CX + 5, 85, 65, fill="#ffb000", opacity="0.04", filter="url(#glow-amb)")
    return s


# ═══════════════════════════════════════════════════════════
#  Composants anatomiques detailles
# ═══════════════════════════════════════════════════════════

def face(skin: str = "url(#skin-med)", extras: str = "") -> str:
    """Visage detaille avec menton, joues, front."""
    s = ""
    # Forme principale du visage (ovale avec menton)
    s += P(
        f"M{CX - 33},82 Q{CX - 35},55 {CX},48 Q{CX + 35},55 {CX + 33},82"
        f" Q{CX + 30},105 {CX + 15},118 Q{CX},125 {CX - 15},118"
        f" Q{CX - 30},105 {CX - 33},82 Z",
        fill=skin,
    )
    # Ombre laterale droite
    s += P(
        f"M{CX + 10},52 Q{CX + 35},58 {CX + 33},82"
        f" Q{CX + 30},105 {CX + 15},118 Q{CX + 5},122 {CX + 5},80 Z",
        fill="#000", opacity="0.08",
    )
    # Pommette gauche (lumiere)
    s += E(CX - 15, 92, 10, 6, fill="#e8c8a0", opacity="0.12")
    # Ombre sous le menton
    s += E(CX, 123, 12, 4, fill="#000", opacity="0.1")
    # Nez
    s += P(
        f"M{CX - 1},78 Q{CX - 3},90 {CX - 4},97 Q{CX},100 {CX + 4},97"
        f" Q{CX + 3},90 {CX + 1},78",
        fill="none", stroke="#b89060", stroke_width="0.6", opacity="0.35",
    )
    # Narines
    s += E(CX - 3, 98, 2, 1.2, fill="#a07848", opacity="0.25")
    s += E(CX + 3, 98, 2, 1.2, fill="#a07848", opacity="0.25")
    # Ombre du nez (cote droit)
    s += P(f"M{CX + 2},82 Q{CX + 5},90 {CX + 5},96",
           fill="none", stroke="#000", stroke_width="0.5", opacity="0.08")
    s += extras
    return s


def detailed_eyes(style: str = "normal", iris_color: str = "#4a3520") -> str:
    """Yeux detailles avec iris, pupille, reflets, paupieres."""
    s = ""
    for side in [-1, 1]:  # -1 = gauche, 1 = droite
        ex = CX + side * 12
        ey = 83

        # Ombre de l'orbite
        s += E(ex, ey, 9, 5.5, fill="#a07848", opacity="0.12")
        # Blanc de l'oeil
        s += E(ex, ey, 6.5, 3.8, fill="#f0e8d8", opacity="0.92")
        # Iris
        s += C(ex + side * 0.5, ey, 3.2, fill=iris_color)
        # Pupille
        s += C(ex + side * 0.5, ey, 1.6, fill="#0a0500")

        if style == "normal" or style == "alert":
            # Reflet lumineux
            s += C(ex + side * 0.5 + 1, ey - 1, 0.9, fill="#fff", opacity="0.55")
            s += C(ex + side * 0.5 - 0.5, ey + 0.8, 0.4, fill="#fff", opacity="0.2")

        # Paupiere superieure
        s += P(
            f"M{ex - 7},{ey - 0.5} Q{ex},{ey - 5} {ex + 7},{ey - 0.5}",
            fill="none", stroke="#5a3a1a", stroke_width="1.2",
        )
        # Paupiere inferieure
        s += P(
            f"M{ex - 6},{ey + 1.5} Q{ex},{ey + 4} {ex + 6},{ey + 1.5}",
            fill="none", stroke="#8a6a4a", stroke_width="0.5", opacity="0.4",
        )
        # Cils (3 en haut)
        for j in range(3):
            cx_l = ex - 4 + j * 3
            s += P(
                f"M{cx_l},{ey - 3.5 + abs(j - 1) * 0.5}"
                f" Q{cx_l + side * 0.3},{ey - 5.5 + abs(j - 1) * 0.5}"
                f" {cx_l + side * 0.5},{ey - 6 + abs(j - 1)}",
                fill="none", stroke="#3a2a0a", stroke_width="0.4", opacity="0.5",
            )

        if style == "stern":
            # Sourcils fronces
            s += P(
                f"M{ex - 6},{ey - 7} Q{ex},{ey - 9.5 + side * 0.5} {ex + 6},{ey - 7.5 + side}",
                fill="none", stroke="#3a2a0a", stroke_width="1.5",
            )
        elif style == "gentle":
            # Sourcils doux, arques
            s += P(
                f"M{ex - 6},{ey - 7} Q{ex},{ey - 10} {ex + 6},{ey - 7.5}",
                fill="none", stroke="#5a4a2a", stroke_width="1.2", opacity="0.7",
            )
        elif style == "wise":
            # Sourcils legerement tombants (sagesse)
            s += P(
                f"M{ex - 6},{ey - 8} Q{ex},{ey - 9} {ex + 6},{ey - 6.5}",
                fill="none", stroke="#7a6a5a", stroke_width="1", opacity="0.6",
            )
        elif style == "evaluating":
            h = 1.5 if side == 1 else 0
            s += P(
                f"M{ex - 6},{ey - 7 - h} Q{ex},{ey - 9 - h} {ex + 6},{ey - 7}",
                fill="none", stroke="#4a3a2a", stroke_width="1.3", opacity="0.7",
            )
        else:
            # Sourcils normaux
            s += P(
                f"M{ex - 6},{ey - 7} Q{ex},{ey - 9} {ex + 6},{ey - 7}",
                fill="none", stroke="#4a3a2a", stroke_width="1.2", opacity="0.6",
            )

    return s


def closed_eyes() -> str:
    """Yeux fermes (meditation)."""
    s = ""
    for side in [-1, 1]:
        ex = CX + side * 12
        ey = 83
        s += E(ex, ey, 9, 5.5, fill="#a07848", opacity="0.08")
        s += P(
            f"M{ex - 6},{ey} Q{ex},{ey + 2.5} {ex + 6},{ey}",
            fill="none", stroke="#5a3a1a", stroke_width="1.3",
        )
        # Cils visibles
        for j in range(4):
            cx_l = ex - 4.5 + j * 3
            s += L(cx_l, ey + 0.5, cx_l - 0.3, ey + 3,
                   stroke="#3a2a0a", stroke_width="0.4", opacity="0.4")
        # Sourcils doux
        s += P(
            f"M{ex - 6},{ey - 7} Q{ex},{ey - 10} {ex + 6},{ey - 7}",
            fill="none", stroke="#5a4a2a", stroke_width="1", opacity="0.5",
        )
    return s


def glowing_eyes(color: str = "#cc3333") -> str:
    """Yeux lumineux sans detail (silhouettes)."""
    s = ""
    for side in [-1, 1]:
        ex = CX + side * 12
        ey = 83
        s += E(ex, ey, 4, 2.5, fill=color, opacity="0.7")
        s += E(ex, ey, 7, 4, fill=color, opacity="0.12", filter="url(#glow-sm)")
    return s


def lips(style: str = "neutral") -> str:
    """Levres detaillees."""
    ly = 108
    s = ""
    # Levre superieure (arc de Cupidon)
    s += P(
        f"M{CX - 7},{ly} Q{CX - 3},{ly - 2} {CX},{ly - 0.5}"
        f" Q{CX + 3},{ly - 2} {CX + 7},{ly}",
        fill="#a07055", opacity="0.5", stroke="#905a45", stroke_width="0.3",
    )
    # Levre inferieure (plus pleine)
    s += P(
        f"M{CX - 7},{ly} Q{CX},{ly + 4} {CX + 7},{ly}",
        fill="#b08068", opacity="0.35", stroke="#905a45", stroke_width="0.2",
    )
    # Ligne de separation
    if style == "stern":
        s += L(CX - 7, ly, CX + 7, ly, stroke="#7a4a35", stroke_width="0.8", opacity="0.5")
    elif style == "smile":
        s += P(f"M{CX - 6},{ly} Q{CX},{ly + 1.5} {CX + 6},{ly}",
               fill="none", stroke="#7a4a35", stroke_width="0.6", opacity="0.5")
    else:
        s += L(CX - 6, ly, CX + 6, ly, stroke="#7a4a35", stroke_width="0.6", opacity="0.4")
    return s


# ═══════════════════════════════════════════════════════════
#  Cheveux / Barbe
# ═══════════════════════════════════════════════════════════

def hair_royal_long(color: str = "#c8c0b0", highlight: str = "#e0d8c8") -> str:
    """Cheveux longs royaux (Arikh Anpin, Nukva)."""
    s = ""
    # Masse principale
    s += P(
        f"M{CX - 38},82 Q{CX - 40},48 {CX},42 Q{CX + 40},48 {CX + 38},82"
        f" Q{CX + 36},50 {CX},46 Q{CX - 36},50 {CX - 38},82 Z",
        fill=color,
    )
    # Cheveux qui descendent sur les cotes
    s += P(f"M{CX - 36},75 Q{CX - 44},100 {CX - 42},140 Q{CX - 40},155 {CX - 36},165",
           fill="none", stroke=color, stroke_width="10", stroke_linecap="round")
    s += P(f"M{CX + 36},75 Q{CX + 44},100 {CX + 42},140 Q{CX + 40},155 {CX + 36},165",
           fill="none", stroke=color, stroke_width="10", stroke_linecap="round")
    # Meches plus claires (highlights)
    s += P(f"M{CX - 20},46 Q{CX - 22},60 {CX - 25},80",
           fill="none", stroke=highlight, stroke_width="1.5", opacity="0.25")
    s += P(f"M{CX + 10},44 Q{CX + 8},58 {CX + 5},78",
           fill="none", stroke=highlight, stroke_width="1", opacity="0.2")
    s += P(f"M{CX - 38},90 Q{CX - 42},110 {CX - 40},130",
           fill="none", stroke=highlight, stroke_width="0.8", opacity="0.15")
    return s


def hair_short_detailed(color: str = "#2a1f0a", highlight: str = "#4a3a1a") -> str:
    """Cheveux courts masculins."""
    s = P(
        f"M{CX - 34},82 Q{CX - 36},50 {CX},46 Q{CX + 36},50 {CX + 34},82"
        f" Q{CX + 30},54 {CX},50 Q{CX - 30},54 {CX - 34},82 Z",
        fill=color,
    )
    # Meches
    for i in range(5):
        x = CX - 20 + i * 10
        s += P(f"M{x},{50 + abs(i - 2)} Q{x + 2},{56} {x + 1},{65}",
               fill="none", stroke=highlight, stroke_width="0.6", opacity="0.2")
    return s


def beard_long_detailed(color: str = "#b0b0a8", highlight: str = "#d0d0c8",
                        n_strands: int = 13) -> str:
    """Barbe longue detaillee (Arikh Anpin)."""
    s = ""
    # Masse de la barbe
    s += P(
        f"M{CX - 22},{105} Q{CX - 28},120 {CX - 20},148"
        f" Q{CX - 10},162 {CX},165 Q{CX + 10},162 {CX + 20},148"
        f" Q{CX + 28},120 {CX + 22},{105} Z",
        fill=color, opacity="0.9",
    )
    # Meches individuelles (tikkunei dikna)
    spread = 36
    for i in range(n_strands):
        t = i / (n_strands - 1)
        x_start = CX - spread / 2 + t * spread
        x_end = CX - spread * 0.7 + t * spread * 1.4
        y_end = 142 + (1 - abs(t - 0.5) * 2) * 20
        # Meche
        s += P(
            f"M{x_start:.1f},112 Q{(x_start + x_end) / 2:.1f},{(112 + y_end) / 2 + 5:.1f} {x_end:.1f},{y_end:.1f}",
            fill="none", stroke=highlight, stroke_width="0.5", opacity="0.3",
        )
    # Moustache
    s += P(f"M{CX - 15},104 Q{CX - 8},108 {CX},106",
           fill="none", stroke=color, stroke_width="2", opacity="0.6", stroke_linecap="round")
    s += P(f"M{CX + 15},104 Q{CX + 8},108 {CX},106",
           fill="none", stroke=color, stroke_width="2", opacity="0.6", stroke_linecap="round")
    return s


def beard_short_detailed(color: str = "#3a2a0a") -> str:
    """Barbe courte soignee."""
    s = P(
        f"M{CX - 20},103 Q{CX - 24},112 {CX - 14},122"
        f" Q{CX},128 {CX + 14},122"
        f" Q{CX + 24},112 {CX + 20},103 Z",
        fill=color, opacity="0.75",
    )
    # Texture
    for i in range(5):
        x = CX - 12 + i * 6
        s += L(x, 108, x + 1, 118, stroke=color, stroke_width="0.4", opacity="0.3")
    return s


def head_covering_detailed(color: str = "#3a2a3a", trim: str = "#8a6a8a") -> str:
    """Tichel / couvre-chef feminin avec details."""
    s = P(
        f"M{CX - 38},80 Q{CX - 40},45 {CX},38 Q{CX + 40},45 {CX + 38},80"
        f" Q{CX + 34},48 {CX},44 Q{CX - 34},48 {CX - 38},80 Z",
        fill=color,
    )
    # Plis du tissu
    s += P(f"M{CX - 15},42 Q{CX - 10},50 {CX - 12},62",
           fill="none", stroke=trim, stroke_width="0.5", opacity="0.2")
    s += P(f"M{CX + 8},40 Q{CX + 12},52 {CX + 10},65",
           fill="none", stroke=trim, stroke_width="0.5", opacity="0.2")
    # Bordure
    s += P(
        f"M{CX - 36},78 Q{CX - 34},50 {CX},44 Q{CX + 34},50 {CX + 36},78",
        fill="none", stroke=trim, stroke_width="0.6", opacity="0.3",
    )
    return s


def hood_detailed(color: str = "#1a1a18", trim: str = "#3a3a30") -> str:
    """Capuche avec plis et ombre."""
    s = ""
    # Ombre interieure de la capuche
    s += P(
        f"M{CX - 42},105 Q{CX - 46},45 {CX},34 Q{CX + 46},45 {CX + 42},105 Z",
        fill="#080808",
    )
    # Capuche exterieure
    s += P(
        f"M{CX - 44},108 Q{CX - 48},42 {CX},32 Q{CX + 48},42 {CX + 44},108"
        f" L{CX + 38},135 Q{CX + 28},105 {CX},98"
        f" Q{CX - 28},105 {CX - 38},135 Z",
        fill=color,
    )
    # Plis
    s += P(f"M{CX - 10},35 Q{CX - 8},55 {CX - 15},80",
           fill="none", stroke=trim, stroke_width="0.5", opacity="0.25")
    s += P(f"M{CX + 15},36 Q{CX + 18},58 {CX + 20},82",
           fill="none", stroke=trim, stroke_width="0.5", opacity="0.2")
    # Bordure de la capuche
    s += P(
        f"M{CX - 38},135 Q{CX - 28},105 {CX},98 Q{CX + 28},105 {CX + 38},135",
        fill="none", stroke=trim, stroke_width="0.8", opacity="0.3",
    )
    return s


# ═══════════════════════════════════════════════════════════
#  Vetements
# ═══════════════════════════════════════════════════════════

def robe(color: str = "#2a1f3a", trim_color: str = "#ffcc00",
         collar: str = "v") -> str:
    """Robe/tunique avec plis et ornements."""
    s = ""
    # Base du vetement
    s += P(
        f"M20,{H} Q20,190 55,178 Q{CX},166 {CX + 45},178 Q180,190 180,{H} Z",
        fill=color,
    )
    # Cou visible
    s += P(f"M{CX - 10},128 L{CX - 10},168 Q{CX},174 {CX + 10},168 L{CX + 10},128 Z",
           fill="url(#skin-med)")
    # Plis du tissu (ombres)
    folds = [
        (55, 185, 50, 210, 55, 240),
        (75, 178, 72, 200, 75, 230),
        (125, 178, 128, 200, 125, 230),
        (145, 185, 150, 210, 145, 240),
    ]
    for x1, y1, x2, y2, x3, y3 in folds:
        s += P(f"M{x1},{y1} Q{x2},{y2} {x3},{y3}",
               fill="none", stroke="#000", stroke_width="1", opacity="0.1")

    # Eclairage lateral (cote droit plus clair)
    s += P(
        f"M{CX + 20},172 Q{CX + 45},178 180,190 L180,{H} L{CX + 20},{H} Z",
        fill="#fff", opacity="0.03",
    )

    # Col
    if collar == "v":
        s += P(f"M{CX - 15},168 L{CX},195 L{CX + 15},168",
               fill="none", stroke=trim_color, stroke_width="0.8", opacity="0.5")
        # Ornement central
        s += C(CX, 175, 2, fill=trim_color, opacity="0.4")
    elif collar == "high":
        s += R(CX - 12, 158, 24, 12, fill=color, stroke=trim_color,
               stroke_width="0.5", opacity="0.8")

    # Bordure inferieure doree
    s += P(f"M55,178 Q{CX},166 {CX + 45},178",
           fill="none", stroke=trim_color, stroke_width="0.6", opacity="0.35")

    return s


def armor(base_color: str = "#3a3a3a", accent: str = "#ffb000") -> str:
    """Armure legere avec epaulieres et details metalliques."""
    s = ""
    # Plastron
    s += P(
        f"M30,{H} Q30,190 60,178 Q{CX},166 140,178 Q170,190 170,{H} Z",
        fill=base_color,
    )
    # Cou
    s += P(f"M{CX - 10},128 L{CX - 10},168 Q{CX},174 {CX + 10},168 L{CX + 10},128 Z",
           fill="url(#skin-med)")
    # Col d'armure
    s += P(f"M{CX - 18},165 Q{CX},160 {CX + 18},165",
           fill="none", stroke=accent, stroke_width="1", opacity="0.5")

    # Epauliere gauche
    s += P(
        f"M30,188 Q38,172 62,168 Q55,175 42,182 Z",
        fill="#4a4a4a", stroke=accent, stroke_width="0.5", opacity="0.85",
    )
    # Rivets
    s += C(45, 178, 1.2, fill=accent, opacity="0.4")
    s += C(52, 174, 1.2, fill=accent, opacity="0.4")

    # Epauliere droite (plus eclairee - rim light)
    s += P(
        f"M170,188 Q162,172 138,168 Q145,175 158,182 Z",
        fill="#555", stroke=accent, stroke_width="0.5", opacity="0.85",
    )
    s += C(155, 178, 1.2, fill=accent, opacity="0.5")
    s += C(148, 174, 1.2, fill=accent, opacity="0.5")

    # Detail plastron central
    s += L(CX, 170, CX, 210, stroke=accent, stroke_width="0.5", opacity="0.2")

    # Eclairage lateral
    s += P(
        f"M{CX + 20},172 Q140,178 170,190 L170,{H} L{CX + 20},{H} Z",
        fill="#fff", opacity="0.04",
    )
    return s


# ═══════════════════════════════════════════════════════════
#  Accessoires detailles
# ═══════════════════════════════════════════════════════════

def crown_royal(color: str = "#ffcc00") -> str:
    """Couronne 3 pointes avec joyaux."""
    s = ""
    # Base de la couronne
    s += P(
        f"M{CX - 26},55 L{CX - 20},32 L{CX - 8},46"
        f" L{CX},24 L{CX + 8},46"
        f" L{CX + 20},32 L{CX + 26},55 Z",
        fill="url(#gold)", stroke=color, stroke_width="0.5",
    )
    # Bandeau de base
    s += R(CX - 26, 53, 52, 5, fill=color, opacity="0.8")
    # Joyaux
    s += C(CX, 28, 2, fill="#ff4444", opacity="0.7")  # Rubis central
    s += C(CX - 14, 38, 1.5, fill="#4488ff", opacity="0.5")  # Saphir
    s += C(CX + 14, 38, 1.5, fill="#44ff88", opacity="0.5")  # Emeraude
    # Eclat
    s += C(CX, 24, 5, fill=color, opacity="0.08", filter="url(#glow-sm)")
    return s


def crown_queen(color: str = "#d4a017") -> str:
    """Couronne feminine discrete."""
    s = P(
        f"M{CX - 22},53 L{CX - 16},38 L{CX - 5},47"
        f" L{CX},32 L{CX + 5},47"
        f" L{CX + 16},38 L{CX + 22},53 Z",
        fill="url(#gold)", stroke=color, stroke_width="0.3", opacity="0.8",
    )
    s += C(CX, 36, 1.5, fill="#ff8844", opacity="0.5")
    return s


def shield_detailed(accent: str = "#ffb000") -> str:
    """Bouclier avec embleme."""
    s = ""
    # Forme du bouclier
    s += P(
        f"M22,185 L22,210 Q22,240 45,{H} L18,225 L22,185 Z",
        fill="#3a3a3a", stroke=accent, stroke_width="0.8", opacity="0.8",
    )
    # Croix sur le bouclier
    s += L(30, 195, 30, 225, stroke=accent, stroke_width="0.8", opacity="0.35")
    s += L(22, 210, 40, 210, stroke=accent, stroke_width="0.8", opacity="0.35")
    # Rivet central
    s += C(30, 210, 2, fill=accent, opacity="0.3")
    return s


def sword_detailed(accent: str = "#cc9900") -> str:
    """Epee avec garde et pommeau."""
    sx = CX + 48
    s = ""
    # Lame (visible au-dessus de l'epaule)
    s += L(sx, 135, sx, 168, stroke="#aaa", stroke_width="2", opacity="0.4")
    # Garde
    s += R(sx - 9, 168, 18, 3, fill=accent, opacity="0.7")
    # Poignee
    s += R(sx - 2.5, 171, 5, 18, fill="#3a2a0a")
    # Wrap de cuir
    for i in range(4):
        s += L(sx - 2, 173 + i * 4, sx + 2, 175 + i * 4,
               stroke="#5a4a2a", stroke_width="0.5", opacity="0.4")
    # Pommeau
    s += C(sx, 192, 3.5, fill=accent, opacity="0.6")
    return s


def lantern_detailed(x: float, y: float, color: str = "#ffb000") -> str:
    """Lanterne avec flamme et lueur."""
    s = ""
    # Lueur ambiante
    s += C(x, y + 8, 20, fill=color, opacity="0.06", filter="url(#glow-amb)")
    # Corps
    s += R(x - 6, y, 12, 16, fill="#2a1f0a", stroke=color, stroke_width="0.6", opacity="0.8")
    # Vitre
    s += R(x - 4, y + 2, 8, 12, fill=color, opacity="0.12")
    # Flamme
    s += P(f"M{x},{y + 3} Q{x - 2.5},{y + 7} {x},{y + 12} Q{x + 2.5},{y + 7} {x},{y + 3}",
           fill=color, opacity="0.6")
    s += P(f"M{x},{y + 5} Q{x - 1},{y + 7} {x},{y + 10} Q{x + 1},{y + 7} {x},{y + 5}",
           fill="#ffe080", opacity="0.4")
    # Poignee
    s += P(f"M{x - 5},{y} Q{x},{y - 8} {x + 5},{y}",
           fill="none", stroke=color, stroke_width="0.8", opacity="0.5")
    # Toit
    s += P(f"M{x - 7},{y} L{x},{y - 3} L{x + 7},{y}",
           fill="#3a2a0a", stroke=color, stroke_width="0.3")
    return s


def quill_detailed(x: float, y: float, color: str = "#7799cc") -> str:
    """Plume de scribe detaillee."""
    s = ""
    # Tige
    s += P(f"M{x},{y} Q{x + 12},{y - 8} {x + 32},{y - 22}",
           fill="none", stroke=color, stroke_width="1", opacity="0.6")
    # Barbes (cote gauche de la plume)
    for i in range(6):
        t = 0.3 + i * 0.12
        px = x + t * 32
        py = y + t * (-22)
        s += P(f"M{px:.0f},{py:.0f} Q{px - 3:.0f},{py - 4:.0f} {px - 6:.0f},{py - 6:.0f}",
               fill="none", stroke=color, stroke_width="0.4", opacity="0.25")
    # Barbes (cote droit)
    for i in range(5):
        t = 0.35 + i * 0.13
        px = x + t * 32
        py = y + t * (-22)
        s += P(f"M{px:.0f},{py:.0f} Q{px + 2:.0f},{py + 3:.0f} {px + 5:.0f},{py + 4:.0f}",
               fill="none", stroke=color, stroke_width="0.3", opacity="0.2")
    # Pointe
    s += C(x, y, 1, fill=color, opacity="0.5")
    return s


def scroll_detailed(x: float, y: float, color: str = "#a88960") -> str:
    """Parchemin roule."""
    s = ""
    # Corps du parchemin
    s += R(x - 9, y, 18, 25, fill="#1f1a0a", stroke=color, stroke_width="0.5", opacity="0.7")
    # Lignes de texte
    for i in range(5):
        s += L(x - 6, y + 4 + i * 4, x + 6, y + 4 + i * 4,
               stroke=color, stroke_width="0.4", opacity="0.25")
    # Rouleau en haut
    s += E(x, y, 10, 2, fill="#2a1f0a", stroke=color, stroke_width="0.3", opacity="0.6")
    return s


def glasses_detailed(color: str = "#8899aa") -> str:
    """Lunettes avec detail."""
    ey = 83
    s = ""
    for side in [-1, 1]:
        ex = CX + side * 12
        s += C(ex, ey, 7, fill="none", stroke=color, stroke_width="0.7", opacity="0.5")
        # Reflet sur le verre
        s += P(f"M{ex - 3},{ey - 4} Q{ex - 1},{ey - 5} {ex + 1},{ey - 4}",
               fill="none", stroke="#fff", stroke_width="0.3", opacity="0.15")
    # Pont
    s += P(f"M{CX - 5},{ey - 1} Q{CX},{ey - 3} {CX + 5},{ey - 1}",
           fill="none", stroke=color, stroke_width="0.6", opacity="0.4")
    # Branches
    s += L(CX - 19, ey, CX - 35, ey - 2, stroke=color, stroke_width="0.5", opacity="0.3")
    s += L(CX + 19, ey, CX + 35, ey - 2, stroke=color, stroke_width="0.5", opacity="0.3")
    return s


def key_ring_detailed(x: float, y: float, color: str = "#6688bb") -> str:
    """Trousseau de cles."""
    s = C(x, y, 7, fill="none", stroke=color, stroke_width="0.8", opacity="0.5")
    for i, angle_deg in enumerate([210, 240, 270]):
        a = math.radians(angle_deg)
        kx = x + math.cos(a) * 7
        ky = y + math.sin(a) * 7
        length = 10 + i * 3
        ex = kx + math.cos(a) * length
        ey_k = ky + math.sin(a) * length
        s += L(kx, ky, ex, ey_k, stroke=color, stroke_width="0.8", opacity="0.4")
        # Dents de la cle
        s += L(ex, ey_k, ex + 2, ey_k - 2, stroke=color, stroke_width="0.6", opacity="0.3")
    return s


def magnifying_detailed(x: float, y: float, color: str = "#5577aa") -> str:
    """Loupe."""
    s = C(x, y, 10, fill="none", stroke=color, stroke_width="1.2", opacity="0.5")
    s += C(x, y, 8, fill=color, opacity="0.04")
    s += L(x + 7, y + 7, x + 18, y + 18, stroke=color, stroke_width="2", opacity="0.5")
    # Reflet
    s += P(f"M{x - 4},{y - 5} Q{x - 2},{y - 7} {x + 1},{y - 5}",
           fill="none", stroke="#fff", stroke_width="0.5", opacity="0.15")
    return s


def belt_with_tools(n: int = 6, color: str = "#ffcc00") -> str:
    """Ceinture avec outils pendants."""
    y = H - 32
    s = ""
    # Ceinture
    s += P(f"M{CX - 42},{y} Q{CX},{y - 4} {CX + 42},{y}",
           fill="none", stroke=color, stroke_width="1.5", opacity="0.4")
    # Boucle
    s += R(CX - 4, y - 5, 8, 7, fill="none", stroke=color, stroke_width="0.6", opacity="0.4")
    # Outils
    spacing = 72 / (n - 1)
    for i in range(n):
        tx = CX - 36 + i * spacing
        h = 8 + (i % 3) * 4
        w = 2 + (i % 2)
        s += R(tx - w / 2, y + 2, w, h, fill=color, opacity="0.2 ")
    return s


def red_folders(x: float, y: float) -> str:
    """Pile de dossiers rouges."""
    s = ""
    for i in range(4):
        s += R(
            x - i * 1.5, y - i * 3.5, 16, 22,
            fill="#2a0a0a", stroke="#8a3333", stroke_width="0.5",
            opacity=f"{0.7 - i * 0.1}",
        )
        # Etiquette
        s += R(x + 2 - i * 1.5, y + 3 - i * 3.5, 8, 3,
               fill="#8a3333", opacity=f"{0.3 - i * 0.05}")
    return s


# ═══════════════════════════════════════════════════════════
#  Eclairage et atmosphere
# ═══════════════════════════════════════════════════════════

def rim_light() -> str:
    """Eclairage de bord ambre (cote droit)."""
    s = ""
    # Ligne lumineuse sur le cote droit du visage
    s += P(
        f"M{CX + 28},55 Q{CX + 35},70 {CX + 33},85"
        f" Q{CX + 30},100 {CX + 18},118",
        fill="none", stroke="#ffb000", stroke_width="1.5", opacity="0.15",
        stroke_linecap="round",
    )
    # Lueur sur l'epaule droite
    s += P(
        f"M{CX + 25},168 Q{CX + 45},175 165,190",
        fill="none", stroke="#ffb000", stroke_width="2", opacity="0.08",
        stroke_linecap="round",
    )
    return s


def rim_light_color(color: str) -> str:
    """Eclairage de bord colore."""
    s = P(
        f"M{CX + 28},55 Q{CX + 35},70 {CX + 33},85"
        f" Q{CX + 30},100 {CX + 18},118",
        fill="none", stroke=color, stroke_width="1.5", opacity="0.18",
        stroke_linecap="round",
    )
    return s


# ═══════════════════════════════════════════════════════════
#  Les 19 Personnages
# ═══════════════════════════════════════════════════════════

def make_svg(content: str) -> str:
    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">\n'
        f"{SHARED_DEFS}\n{content}</svg>\n"
    )


def arikh_anpin() -> str:
    s = background("#1a1600")
    s += hair_royal_long("#b0b0a8", "#d0d0c8")
    s += robe("#2a1f3a", "#ffcc00", "v")
    s += face("url(#skin-light)")
    s += detailed_eyes("wise", "#5a4a30")
    s += lips("neutral")
    s += beard_long_detailed("#b0b0a8", "#d0d0c8", 13)
    s += crown_royal("#ffcc00")
    s += rim_light()
    return make_svg(s)


def abba() -> str:
    import random
    random.seed(42)
    s = background("#1a1400")
    s += robe("#2a1f3a", "#e6b800", "v")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#3a2a0a", "#5a4a2a")
    s += beard_short_detailed("#3a2a0a")
    s += detailed_eyes("alert", "#4a3520")
    s += lips("neutral")
    # Mains avec etincelles
    s += P(f"M42,215 Q52,198 65,192", fill="none",
           stroke="#c8a27a", stroke_width="5", opacity="0.7", stroke_linecap="round")
    s += P(f"M158,215 Q148,198 135,192", fill="none",
           stroke="#c8a27a", stroke_width="5", opacity="0.7", stroke_linecap="round")
    for _ in range(12):
        ex = random.randint(38, 162)
        ey = random.randint(188, 230)
        s += C(ex, ey, random.uniform(0.8, 1.8),
               fill="#e6b800", opacity=f"{random.uniform(0.15, 0.5):.2f}")
    s += rim_light()
    return make_svg(s)


def imma() -> str:
    s = background("#1a1200")
    s += robe("#2a1a2a", "#d4a017", "v")
    s += face("url(#skin-light)")
    s += head_covering_detailed("#3a2a3a", "#8a6a8a")
    s += detailed_eyes("gentle", "#5a4a30")
    s += lips("smile")
    # Mains en coupe avec lumiere
    s += P(f"M50,208 Q62,192 78,198", fill="none",
           stroke="#d4b088", stroke_width="4.5", opacity="0.65", stroke_linecap="round")
    s += P(f"M150,208 Q138,192 122,198", fill="none",
           stroke="#d4b088", stroke_width="4.5", opacity="0.65", stroke_linecap="round")
    s += C(CX, 202, 15, fill="#d4a017", opacity="0.06", filter="url(#glow-sm)")
    s += C(CX, 202, 6, fill="#d4a017", opacity="0.1")
    s += rim_light()
    return make_svg(s)


def zeir_anpin() -> str:
    s = background("#1a1400")
    s += robe("#2a2a1a", "#cc9900", "v")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#2a1f0a")
    s += detailed_eyes("normal", "#4a3a20")
    s += lips("neutral")
    s += belt_with_tools(6, "#ffcc00")
    s += rim_light()
    return make_svg(s)


def nukva() -> str:
    s = background("#1a1400")
    s += hair_royal_long("#1a0f05", "#3a2a15")
    s += robe("#2a1a3a", "#d4a017", "v")
    s += face("url(#skin-light)")
    s += detailed_eyes("alert", "#4a3520")
    s += lips("smile")
    s += crown_queen("#d4a017")
    # Reflet lumineux plus prononce (elle vous regarde)
    s += C(CX - 10.5, 82, 1, fill="#fff", opacity="0.3")
    s += C(CX + 13.5, 82, 1, fill="#fff", opacity="0.3")
    s += rim_light()
    return make_svg(s)


def mikhael() -> str:
    s = background("#1a1200")
    s += armor("#3a3a3a", "#ffb000")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#2a2a1a")
    s += detailed_eyes("alert", "#4a5540")
    s += lips("stern")
    s += shield_detailed("#ffb000")
    s += rim_light()
    return make_svg(s)


def uriel() -> str:
    s = background("#1a1200")
    s += hood_detailed("#1f1f1a", "#3a3a2a")
    s += robe("#2a2a28", "#e6a000", "high")
    s += face("url(#skin-med)")
    s += detailed_eyes("wise", "#6a5a30")
    s += lips("neutral")
    s += lantern_detailed(CX + 50, 185, "#e6a000")
    s += rim_light()
    return make_svg(s)


def raphael() -> str:
    s = background("#121a0e")
    s += robe("#1a2a1a", "#5a8a4a", "v")
    s += face("url(#skin-light)")
    s += hair_short_detailed("#3a2a1a", "#5a4a2a")
    s += detailed_eyes("gentle", "#4a6a3a")
    s += lips("smile")
    # Mains guerisseuses avec lueur verte
    s += P(f"M45,210 Q58,194 72,198", fill="none",
           stroke="#d4b088", stroke_width="4.5", opacity="0.65", stroke_linecap="round")
    s += P(f"M155,210 Q142,194 128,198", fill="none",
           stroke="#d4b088", stroke_width="4.5", opacity="0.65", stroke_linecap="round")
    s += C(58, 202, 12, fill="#5aaa4a", opacity="0.06", filter="url(#glow-sm)")
    s += C(142, 202, 12, fill="#5aaa4a", opacity="0.06", filter="url(#glow-sm)")
    s += rim_light_color("#5aaa4a")
    return make_svg(s)


def gabriel() -> str:
    s = background("#1a1400")
    s += armor("#2a2a2a", "#cc9900")
    s += face("url(#skin-med)",
              # Machoire plus carree
              P(f"M{CX - 18},108 Q{CX - 20},114 {CX - 16},120 Q{CX},127 {CX + 16},120"
                f" Q{CX + 20},114 {CX + 18},108",
                fill="url(#skin-med)", opacity="0.3"))
    s += hair_short_detailed("#1a1a18", "#2a2a28")
    s += detailed_eyes("stern", "#3a3020")
    s += lips("stern")
    s += sword_detailed("#cc9900")
    s += rim_light()
    return make_svg(s)


def metatron() -> str:
    s = background("#0e1218")
    s += robe("#1f2a3a", "#7799cc", "high")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#1a1a2a", "#2a2a3a")
    s += detailed_eyes("normal", "#4a4a6a")
    s += lips("neutral")
    s += quill_detailed(CX + 38, 185, "#7799cc")
    s += scroll_detailed(CX - 48, 190, "#7799cc")
    s += rim_light_color("#7799cc")
    return make_svg(s)


def memuneh() -> str:
    s = background("#0e1218")
    s += robe("#1f2838", "#6688bb", "v")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#1a1a2a")
    s += detailed_eyes("evaluating", "#4a4a5a")
    s += lips("neutral")
    s += key_ring_detailed(CX + 48, 205, "#6688bb")
    s += rim_light_color("#6688bb")
    return make_svg(s)


def samael() -> str:
    s = background("#0e1018")
    s += hood_detailed("#151520", "#25252a")
    s += robe("#1a1a2a", "#5577aa", "high")
    s += face("url(#skin-med)")
    s += detailed_eyes("wise", "#4a4a5a")
    s += lips("neutral")
    s += magnifying_detailed(CX + 44, 192, "#5577aa")
    s += rim_light_color("#5577aa")
    return make_svg(s)


def sofer() -> str:
    s = background("#0e1218")
    s += robe("#1f2830", "#7788aa", "v")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#2a2a28")
    s += glasses_detailed("#8899aa")
    s += detailed_eyes("wise", "#4a4a5a")
    s += lips("neutral")
    s += quill_detailed(CX + 36, 185, "#7788aa")
    s += rim_light_color("#7788aa")
    return make_svg(s)


def nefesh_habehamit() -> str:
    """Silhouette sombre — une FORCE, pas une personne."""
    s = background("#1a0500", "#0a0000")
    shadow = "#120500"
    # Corps silhouette
    s += P(f"M20,{H} Q20,190 55,178 Q{CX},166 145,178 Q180,190 180,{H} Z",
           fill=shadow)
    s += P(f"M{CX - 10},128 L{CX - 10},168 Q{CX},174 {CX + 10},168 L{CX + 10},128 Z",
           fill=shadow)
    # Tete silhouette
    s += P(
        f"M{CX - 33},82 Q{CX - 35},55 {CX},48 Q{CX + 35},55 {CX + 33},82"
        f" Q{CX + 30},105 {CX + 15},118 Q{CX},125 {CX - 15},118"
        f" Q{CX - 30},105 {CX - 33},82 Z",
        fill=shadow,
    )
    # Contour rouge
    s += P(
        f"M{CX - 33},82 Q{CX - 35},55 {CX},48 Q{CX + 35},55 {CX + 33},82"
        f" Q{CX + 30},105 {CX + 15},118 Q{CX},125 {CX - 15},118"
        f" Q{CX - 30},105 {CX - 33},82",
        fill="none", stroke="#cc3333", stroke_width="1.2", opacity="0.35",
    )
    s += P(f"M55,178 Q{CX},166 145,178 Q180,190 180,{H}",
           fill="none", stroke="#cc3333", stroke_width="0.8", opacity="0.2")
    # Yeux rouges luisants
    s += glowing_eyes("#cc3333")
    # Aura rouge
    s += C(CX, 90, 50, fill="#cc3333", opacity="0.03", filter="url(#glow-amb)")
    s += rim_light_color("#cc3333")
    return make_svg(s)


def beinoni() -> str:
    """Le plus humain, ordinaire, sans attribut special."""
    s = background("#1a1400")
    s += robe("#2a2a2a", "#996a00", "v")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#2a1f0a")
    s += detailed_eyes("normal", "#4a3a20")
    s += lips("neutral")
    # Subtil partage lumiere/ombre (sa dualite)
    s += R(0, 0, CX, H, fill="#cc3333", opacity="0.012")
    s += R(CX, 0, CX, H, fill="#ffcc00", opacity="0.012")
    s += rim_light()
    return make_svg(s)


def nefesh_haelokit() -> str:
    """Silhouette lumineuse — une DIRECTION, pas une personne."""
    s = background("#1a1800", "#0a0a00")
    light = "#1a1500"
    s += P(f"M20,{H} Q20,190 55,178 Q{CX},166 145,178 Q180,190 180,{H} Z",
           fill=light)
    s += P(f"M{CX - 10},128 L{CX - 10},168 Q{CX},174 {CX + 10},168 L{CX + 10},128 Z",
           fill=light)
    s += P(
        f"M{CX - 33},82 Q{CX - 35},55 {CX},48 Q{CX + 35},55 {CX + 33},82"
        f" Q{CX + 30},105 {CX + 15},118 Q{CX},125 {CX - 15},118"
        f" Q{CX - 30},105 {CX - 33},82 Z",
        fill=light,
    )
    # Contour blanc-or
    s += P(
        f"M{CX - 33},82 Q{CX - 35},55 {CX},48 Q{CX + 35},55 {CX + 33},82"
        f" Q{CX + 30},105 {CX + 15},118 Q{CX},125 {CX - 15},118"
        f" Q{CX - 30},105 {CX - 33},82",
        fill="none", stroke="#ddaa00", stroke_width="1.2", opacity="0.4",
    )
    s += P(f"M55,178 Q{CX},166 145,178 Q180,190 180,{H}",
           fill="none", stroke="#ddaa00", stroke_width="0.8", opacity="0.25")
    # Yeux lumineux dores
    s += glowing_eyes("#ddaa00")
    # Halo ascendant
    s += C(CX, 75, 55, fill="#ddaa00", opacity="0.04", filter="url(#glow-amb)")
    s += C(CX, 50, 30, fill="#ffee88", opacity="0.03", filter="url(#glow-amb)")
    s += rim_light_color("#ddaa00")
    return make_svg(s)


def daemon() -> str:
    s = background("#0e1a0e")
    s += robe("#1f2a1f", "#88aa88", "v")
    s += face("url(#skin-dark)")
    s += hair_short_detailed("#1a1a18")
    # Chapeau de veilleur
    s += P(
        f"M{CX - 32},56 L{CX - 38},56 L{CX - 28},44"
        f" Q{CX},34 {CX + 28},44 L{CX + 38},56 L{CX + 32},56 Z",
        fill="#1a2a1a", stroke="#88aa88", stroke_width="0.3", opacity="0.8",
    )
    s += detailed_eyes("wise", "#4a5a3a")
    s += lips("smile")
    s += lantern_detailed(CX - 48, 188, "#88aa88")
    s += scroll_detailed(CX + 44, 192, "#88aa88")
    s += rim_light_color("#88aa88")
    return make_svg(s)


def meditant() -> str:
    s = background("#0e1a0e")
    s += robe("#1a2a1a", "#7a9a7a", "v")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#2a2a1a")
    s += closed_eyes()
    s += lips("neutral")
    # Bulles de pensee montantes
    bubbles = [(CX + 18, 52, 2.5), (CX + 25, 38, 4), (CX + 30, 20, 6)]
    for bx, by, br in bubbles:
        s += C(bx, by, br, fill="none", stroke="#7a9a7a",
               stroke_width="0.7", opacity="0.3")
    s += T(CX + 30, 23, "?", fill="#7a9a7a", font_size="8", opacity="0.25",
           text_anchor="middle", font_family="serif")
    s += rim_light_color("#7a9a7a")
    return make_svg(s)


def kategor() -> str:
    s = background("#0e1a0e")
    s += robe("#1a2a1a", "#6a8a6a", "v")
    s += face("url(#skin-med)")
    s += hair_short_detailed("#1a1a18")
    s += glasses_detailed("#6a8a6a")
    s += detailed_eyes("stern", "#4a5a3a")
    s += lips("stern")
    s += red_folders(CX + 35, 190)
    s += rim_light_color("#6a8a6a")
    return make_svg(s)


# ═══════════════════════════════════════════════════════════

CHARACTERS = {
    "arikh_anpin": arikh_anpin,
    "abba": abba,
    "imma": imma,
    "zeir_anpin": zeir_anpin,
    "nukva": nukva,
    "mikhael": mikhael,
    "uriel": uriel,
    "raphael": raphael,
    "gabriel": gabriel,
    "metatron": metatron,
    "memuneh": memuneh,
    "samael": samael,
    "sofer": sofer,
    "nefesh_habehamit": nefesh_habehamit,
    "beinoni": beinoni,
    "nefesh_haelokit": nefesh_haelokit,
    "daemon": daemon,
    "meditant": meditant,
    "kategor": kategor,
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, gen in CHARACTERS.items():
        path = OUTPUT / f"{name}.svg"
        content = gen()
        path.write_text(content, encoding="utf-8")
        size = len(content)
        print(f"  {name:24s} -> {path.name:28s} ({size:>6,d} bytes)")
    print(f"\n  {len(CHARACTERS)} avatars generes dans {OUTPUT}/")


if __name__ == "__main__":
    main()
