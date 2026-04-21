#!/usr/bin/env python3
"""generate_systeme_images.py — 19 SVG scenes pour les pages SYSTEME d'Etz Chaim AI.

11 interieurs (Sephiroth/L'Arbre), 4 paysages (Olamot/Les Mondes),
4 creatures/ombres (Qliphoth/Les Erreurs).

Style : dark fantasy RPG, eclairage dramatique, fond noir (#0a0a0a).
Reutilise le systeme de primitives SVG de generate_avatars.py.

Usage:
    python tools/generate_systeme_images.py
"""

from __future__ import annotations

import math
from pathlib import Path

OUTPUT = Path(__file__).resolve().parent.parent / "web" / "static" / "systeme"
W, H = 200, 250
CX = 100


# ═══════════════════════════════════════════════════════════
#  Primitives SVG (identiques a generate_avatars.py)
# ═══════════════════════════════════════════════════════════


def _a(tag: str, **kw) -> str:
    """Genere un element SVG auto-fermant."""
    attrs = " ".join(
        f'{k.replace("_", "-")}="{v}"' for k, v in kw.items() if v is not None
    )
    return f"<{tag} {attrs}/>\n"


def E(cx: float, cy: float, rx: float, ry: float, **kw) -> str:
    return _a(
        "ellipse",
        cx=f"{cx:.1f}",
        cy=f"{cy:.1f}",
        rx=f"{rx:.1f}",
        ry=f"{ry:.1f}",
        **kw,
    )


def C(cx: float, cy: float, r: float, **kw) -> str:
    return _a("circle", cx=f"{cx:.1f}", cy=f"{cy:.1f}", r=f"{r:.1f}", **kw)


def P(d: str, **kw) -> str:
    return _a("path", d=d, **kw)


def L(x1: float, y1: float, x2: float, y2: float, **kw) -> str:
    return _a(
        "line",
        x1=f"{x1:.1f}",
        y1=f"{y1:.1f}",
        x2=f"{x2:.1f}",
        y2=f"{y2:.1f}",
        stroke_linecap="round",
        **kw,
    )


def R(x: float, y: float, w: float, h: float, **kw) -> str:
    return _a(
        "rect",
        x=f"{x:.1f}",
        y=f"{y:.1f}",
        width=f"{w:.1f}",
        height=f"{h:.1f}",
        **kw,
    )


def T(x: float, y: float, text: str, **kw) -> str:
    attrs = " ".join(
        f'{k.replace("_", "-")}="{v}"' for k, v in kw.items() if v is not None
    )
    return f'<text x="{x}" y="{y}" {attrs}>{text}</text>\n'


def G(content: str, **kw) -> str:
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in kw.items())
    return f"<g {attrs}>\n{content}</g>\n"


# ═══════════════════════════════════════════════════════════
#  Defs partages : gradients et filtres
# ═══════════════════════════════════════════════════════════

SHARED_DEFS = """<defs>
  <!-- Amber rim light -->
  <linearGradient id="rim-r" x1="0%" y1="0%" x2="100%" y2="0%">
    <stop offset="0%" stop-color="#ffb000" stop-opacity="0"/>
    <stop offset="70%" stop-color="#ffb000" stop-opacity="0"/>
    <stop offset="100%" stop-color="#ffb000" stop-opacity="0.25"/>
  </linearGradient>
  <!-- Metallic gold -->
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
  <filter id="glow-md" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="5"/>
  </filter>
  <filter id="soft" x="-10%" y="-10%" width="120%" height="120%">
    <feGaussianBlur in="SourceGraphic" stdDeviation="1.5"/>
  </filter>
</defs>
"""


# ═══════════════════════════════════════════════════════════
#  Utilitaires de composition
# ═══════════════════════════════════════════════════════════


def make_svg(content: str) -> str:
    return (
        f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">\n'
        f"{SHARED_DEFS}\n{content}</svg>\n"
    )


def bg_radial(inner: str, outer: str = "#0a0a0a", cx: str = "50%", cy: str = "40%") -> str:
    """Fond noir avec lueur radiale centree."""
    s = f"""<defs>
  <radialGradient id="bg-g" cx="{cx}" cy="{cy}">
    <stop offset="0%" stop-color="{inner}"/>
    <stop offset="100%" stop-color="{outer}"/>
  </radialGradient>
</defs>
"""
    s += R(0, 0, W, H, fill="url(#bg-g)")
    return s


def floor(y: float, color: str, highlight: str) -> str:
    """Sol en perspective avec lignes de carrelage."""
    s = ""
    # Surface du sol
    s += P(
        f"M0,{y} L{W},{y} L{W},{H} L0,{H} Z",
        fill=color,
        opacity="0.6",
    )
    # Lignes horizontales (profondeur)
    for i in range(5):
        ly = y + (H - y) * (i / 4) ** 0.7
        op = 0.15 - i * 0.02
        s += L(0, ly, W, ly, stroke=highlight, stroke_width="0.5", opacity=f"{op:.2f}")
    # Lignes convergentes (perspective)
    for i in range(7):
        fx = (i / 6) * W
        s += L(fx, y, CX + (fx - CX) * 0.3, H, stroke=highlight,
               stroke_width="0.3", opacity="0.08")
    return s


def wall_stones(y_top: float, y_bot: float, color: str, n_rows: int = 5) -> str:
    """Mur en pierre avec joints visibles."""
    s = ""
    row_h = (y_bot - y_top) / n_rows
    for row in range(n_rows):
        ry = y_top + row * row_h
        n_cols = 4 + (row % 2)
        col_w = W / n_cols
        offset = (row % 2) * col_w * 0.4
        for col in range(n_cols + 1):
            bx = offset + col * col_w
            if bx > W:
                continue
            bw = min(col_w - 2, W - bx)
            if bw < 5:
                continue
            shade = 0.03 * ((row + col) % 3)
            s += R(bx, ry, bw, row_h - 1,
                   fill=color, opacity=f"{0.4 + shade:.2f}",
                   stroke=color, stroke_width="0.3")
    return s


def rim_border(color: str = "#ffb000", opacity: str = "0.12") -> str:
    """Cadre lumineux subtil autour de l'image."""
    s = R(0, 0, W, H, fill="none", stroke=color, stroke_width="1.5", opacity=opacity)
    return s


# ═══════════════════════════════════════════════════════════
#  11 SALLES — Sephiroth (page L'Arbre)
# ═══════════════════════════════════════════════════════════


def malkuth() -> str:
    """Salle du trone. Tons terre/brun."""
    s = bg_radial("#1a1208", "#0a0a0a")
    # Murs de pierre
    s += wall_stones(0, 170, "#443322", 6)
    # Sol
    s += floor(170, "#332211", "#665544")
    # Trone central
    # Dossier
    s += R(70, 80, 60, 90, fill="#2a1a0a", stroke="#886644", stroke_width="1", opacity="0.8")
    # Ornement du dossier
    s += P("M85,85 L100,75 L115,85", fill="none", stroke="#886644",
           stroke_width="1.2", opacity="0.5")
    s += C(100, 78, 3, fill="#886644", opacity="0.4")
    # Siege
    s += R(68, 140, 64, 16, fill="#3a2a1a", stroke="#886644",
           stroke_width="0.8", opacity="0.8")
    # Accoudoirs
    s += R(62, 110, 10, 46, fill="#2a1a0a", stroke="#886644",
           stroke_width="0.6", opacity="0.7")
    s += R(128, 110, 10, 46, fill="#2a1a0a", stroke="#886644",
           stroke_width="0.6", opacity="0.7")
    # Pieds du trone
    s += R(72, 156, 8, 14, fill="#3a2a1a", stroke="#886644",
           stroke_width="0.4", opacity="0.6")
    s += R(120, 156, 8, 14, fill="#3a2a1a", stroke="#886644",
           stroke_width="0.4", opacity="0.6")
    # Lueur ambiante derriere le trone
    s += C(100, 120, 50, fill="#886644", opacity="0.04", filter="url(#glow-amb)")
    # Torches murales
    for tx in [25, 175]:
        s += R(tx - 2, 100, 4, 20, fill="#443322", opacity="0.7")
        s += P(f"M{tx},{100} Q{tx - 3},{92} {tx},{85} Q{tx + 3},{92} {tx},{100}",
               fill="#ff8800", opacity="0.3")
        s += C(tx, 90, 8, fill="#ff8800", opacity="0.05", filter="url(#glow-sm)")
    s += rim_border("#886644")
    return make_svg(s)


def yesod() -> str:
    """Bibliotheque / archive. Tons violets."""
    s = bg_radial("#140e1a", "#0a0a0a")
    # Etageres gauche
    for i in range(5):
        sy = 30 + i * 42
        # Etagere
        s += R(5, sy, 50, 3, fill="#3a2a3a", stroke="#9966cc",
               stroke_width="0.3", opacity="0.6")
        # Livres
        for j in range(6):
            bx = 8 + j * 7
            bh = 28 + (j % 3) * 6
            colors = ["#4a2a5a", "#3a1a4a", "#5a3a6a", "#2a1a3a", "#6a4a7a", "#3a2a4a"]
            s += R(bx, sy - bh, 5, bh, fill=colors[j % len(colors)], opacity="0.7")
    # Etageres droite
    for i in range(5):
        sy = 30 + i * 42
        s += R(145, sy, 50, 3, fill="#3a2a3a", stroke="#9966cc",
               stroke_width="0.3", opacity="0.6")
        for j in range(6):
            bx = 148 + j * 7
            bh = 30 + ((j + 2) % 3) * 5
            colors = ["#5a3a6a", "#3a1a4a", "#4a2a5a", "#2a1a3a", "#3a2a4a", "#6a4a7a"]
            s += R(bx, sy - bh, 5, bh, fill=colors[j % len(colors)], opacity="0.7")
    # Sol
    s += floor(215, "#1a1020", "#4a3a5a")
    # Table centrale avec parchemins
    s += R(65, 200, 70, 8, fill="#2a1a2a", stroke="#9966cc",
           stroke_width="0.5", opacity="0.6")
    s += R(85, 208, 8, 30, fill="#2a1a2a", opacity="0.5")
    s += R(107, 208, 8, 30, fill="#2a1a2a", opacity="0.5")
    # Parchemins sur la table
    s += R(72, 192, 14, 8, fill="#1f1a0a", stroke="#9966cc",
           stroke_width="0.3", opacity="0.5")
    s += R(110, 190, 18, 10, fill="#1f1a0a", stroke="#9966cc",
           stroke_width="0.3", opacity="0.5")
    # Lueur de lune depuis le haut
    s += C(100, 15, 30, fill="#9966cc", opacity="0.06", filter="url(#glow-amb)")
    s += C(100, 0, 60, fill="#bbaadd", opacity="0.03", filter="url(#glow-amb)")
    s += rim_border("#9966cc")
    return make_svg(s)


def hod() -> str:
    """Salle des miroirs. Tons ambre."""
    s = bg_radial("#1a1400", "#0a0a0a")
    # Sol
    s += floor(185, "#1a1200", "#554400")
    # Miroirs le long des murs
    for i in range(3):
        mx = 20 + i * 65
        # Cadre du miroir
        s += R(mx, 30, 40, 70, fill="none", stroke="#ffb000",
               stroke_width="1.5", opacity="0.4")
        # Surface reflechissante
        s += R(mx + 3, 33, 34, 64, fill="#1a1a1a", opacity="0.8")
        # Reflets
        s += P(f"M{mx + 5},{36} L{mx + 12},{36} L{mx + 5},{55}",
               fill="#ffb000", opacity="0.04")
        s += L(mx + 28, 40, mx + 32, 85,
               stroke="#ffb000", stroke_width="0.5", opacity="0.08")
        # Ornement au-dessus
        s += C(mx + 20, 28, 4, fill="none", stroke="#ffb000",
               stroke_width="0.6", opacity="0.3")
    # Lueur ambre centrale
    s += C(100, 100, 60, fill="#ffb000", opacity="0.04", filter="url(#glow-amb)")
    # Reflets au sol (miroirs refletes)
    for i in range(3):
        mx = 30 + i * 65
        s += R(mx, 190, 30, 40, fill="#ffb000", opacity="0.015")
    # Chandelier central
    s += L(100, 0, 100, 20, stroke="#ffb000", stroke_width="0.8", opacity="0.3")
    s += C(100, 22, 3, fill="#ffb000", opacity="0.15")
    for dx in [-15, 0, 15]:
        s += P(f"M{100 + dx},{22} Q{100 + dx - 2},{16} {100 + dx},{10}"
               f" Q{100 + dx + 2},{16} {100 + dx},{22}",
               fill="#ffb000", opacity="0.2")
        s += C(100 + dx, 14, 4, fill="#ffb000", opacity="0.04", filter="url(#glow-sm)")
    s += rim_border("#ffb000")
    return make_svg(s)


def netzach() -> str:
    """Chambre de la boussole / navigation. Tons verts."""
    s = bg_radial("#0e1a0e", "#0a0a0a")
    # Murs
    s += wall_stones(0, 170, "#2a3a2a", 5)
    # Sol
    s += floor(170, "#1a2a1a", "#4a5a4a")
    # Table centrale
    s += R(55, 145, 90, 8, fill="#2a3a2a", stroke="#88aa88",
           stroke_width="0.5", opacity="0.7")
    s += R(70, 153, 8, 25, fill="#2a3a2a", opacity="0.5")
    s += R(122, 153, 8, 25, fill="#2a3a2a", opacity="0.5")
    # Boussole sur la table
    # Cercle exterieur
    s += C(100, 130, 28, fill="#1a2a1a", stroke="#88aa88",
           stroke_width="1", opacity="0.8")
    # Cercle interieur
    s += C(100, 130, 22, fill="#0a1a0a", stroke="#88aa88",
           stroke_width="0.5", opacity="0.6")
    # Rose des vents
    # N-S
    s += P("M100,110 L104,130 L100,148 L96,130 Z",
           fill="#88aa88", opacity="0.4")
    # E-W
    s += P("M80,130 L100,126 L120,130 L100,134 Z",
           fill="#88aa88", opacity="0.3")
    # Pointe nord (plus brillante)
    s += P("M100,110 L103,125 L97,125 Z", fill="#aaccaa", opacity="0.6")
    # Centre
    s += C(100, 130, 3, fill="#88aa88", opacity="0.5")
    # Graduations
    for i in range(12):
        angle = math.radians(i * 30)
        ix = 100 + math.cos(angle) * 22
        iy = 130 + math.sin(angle) * 22
        ox = 100 + math.cos(angle) * 25
        oy = 130 + math.sin(angle) * 25
        s += L(ix, iy, ox, oy, stroke="#88aa88", stroke_width="0.5", opacity="0.3")
    # Cartes sur le mur
    s += R(15, 40, 35, 50, fill="#1a2a1a", stroke="#88aa88",
           stroke_width="0.4", opacity="0.4")
    # Lignes de carte
    for i in range(4):
        s += P(f"M{20},{50 + i * 10} Q{30},{48 + i * 10} {42},{52 + i * 10}",
               fill="none", stroke="#88aa88", stroke_width="0.3", opacity="0.2")
    # Lueur verte
    s += C(100, 130, 40, fill="#88aa88", opacity="0.04", filter="url(#glow-amb)")
    s += rim_border("#88aa88")
    return make_svg(s)


def tiferet() -> str:
    """Chambre de l'equilibre. Tons or avec accents rouges (LE MUR)."""
    s = bg_radial("#1a1600", "#0a0a0a")
    # Murs hauts -- pierres sombres
    s += wall_stones(0, 160, "#3a3020", 5)
    # Sol
    s += floor(160, "#1a1400", "#554400")
    # Balance centrale — pilier
    s += R(97, 80, 6, 85, fill="#3a3020", stroke="#ffcc00",
           stroke_width="0.5", opacity="0.6")
    # Bras de la balance
    s += L(50, 85, 150, 85, stroke="#ffcc00", stroke_width="1.5", opacity="0.5")
    # Pivot
    s += P("M95,75 L100,65 L105,75 Z", fill="#ffcc00", opacity="0.5")
    # Plateau gauche
    s += P("M35,85 L50,80 L65,85 L60,95 Q50,100 40,95 Z",
           fill="#3a3020", stroke="#ffcc00", stroke_width="0.6", opacity="0.5")
    # Chaines gauche
    s += L(42, 85, 50, 80, stroke="#ffcc00", stroke_width="0.4", opacity="0.3")
    s += L(58, 85, 50, 80, stroke="#ffcc00", stroke_width="0.4", opacity="0.3")
    # Plateau droit
    s += P("M135,85 L150,80 L165,85 L160,95 Q150,100 140,95 Z",
           fill="#3a3020", stroke="#ffcc00", stroke_width="0.6", opacity="0.5")
    # Chaines droit
    s += L(142, 85, 150, 80, stroke="#ffcc00", stroke_width="0.4", opacity="0.3")
    s += L(158, 85, 150, 80, stroke="#ffcc00", stroke_width="0.4", opacity="0.3")
    # LE MUR — accents rouges : fissures rouges dans le mur du fond
    for fx, fy, fh in [(30, 20, 45), (165, 15, 55), (85, 10, 30), (140, 40, 35)]:
        s += P(f"M{fx},{fy} Q{fx + 3},{fy + fh * 0.4} {fx - 2},{fy + fh}",
               fill="none", stroke="#ff4444", stroke_width="0.8", opacity="0.25")
        s += C(fx, fy + fh * 0.5, 3, fill="#ff4444", opacity="0.03", filter="url(#glow-sm)")
    # Lueur rouge derriere le mur
    s += R(0, 0, W, 160, fill="#ff4444", opacity="0.015")
    # Lueur or sur la balance
    s += C(100, 85, 45, fill="#ffcc00", opacity="0.04", filter="url(#glow-amb)")
    # Flamme sur le pivot
    s += P("M100,65 Q97,55 100,45 Q103,55 100,65",
           fill="#ffcc00", opacity="0.2")
    s += C(100, 50, 6, fill="#ffcc00", opacity="0.03", filter="url(#glow-sm)")
    s += rim_border("#ffcc00")
    return make_svg(s)


def gevurah() -> str:
    """Forge. Tons rouges."""
    s = bg_radial("#1a0a0a", "#0a0a0a", cy="60%")
    # Murs sombres
    s += wall_stones(0, 155, "#332020", 4)
    # Sol
    s += floor(155, "#1a0a0a", "#553333")
    # Foyer/fournaise au fond
    s += P("M60,90 L60,155 L140,155 L140,90 Q120,60 100,55 Q80,60 60,90 Z",
           fill="#1a0500", stroke="#cc3333", stroke_width="0.8", opacity="0.7")
    # Flammes
    for fx, fh, fw, op in [(85, 50, 8, 0.25), (100, 65, 10, 0.35),
                            (115, 45, 7, 0.2), (95, 55, 9, 0.3),
                            (108, 48, 6, 0.22)]:
        fy = 155 - fh
        s += P(f"M{fx - fw},{155} Q{fx},{fy - 10} {fx},{fy}"
               f" Q{fx},{fy - 10} {fx + fw},{155}",
               fill="#cc3333", opacity=f"{op:.2f}")
    # Coeur des flammes (orange/jaune)
    for fx, fh, fw, op in [(95, 35, 5, 0.2), (100, 45, 6, 0.25), (105, 30, 4, 0.18)]:
        fy = 155 - fh
        s += P(f"M{fx - fw},{155} Q{fx},{fy} {fx + fw},{155}",
               fill="#ff8800", opacity=f"{op:.2f}")
    # Lueur du feu
    s += C(100, 135, 55, fill="#cc3333", opacity="0.06", filter="url(#glow-amb)")
    s += C(100, 145, 35, fill="#ff8800", opacity="0.04", filter="url(#glow-amb)")
    # Enclume
    s += P("M70,175 L75,165 L125,165 L130,175 L135,185 L65,185 Z",
           fill="#3a3a3a", stroke="#cc3333", stroke_width="0.5", opacity="0.7")
    # Surface de l'enclume (reflet rouge du feu)
    s += R(78, 165, 44, 4, fill="#cc3333", opacity="0.06")
    # Bec de l'enclume
    s += P("M125,165 L145,162 L145,168 L130,175 Z",
           fill="#333", stroke="#cc3333", stroke_width="0.3", opacity="0.6")
    # Marteau pose a cote
    s += R(148, 170, 5, 30, fill="#3a2a1a", opacity="0.5")
    s += R(143, 165, 15, 8, fill="#4a4a4a", stroke="#cc3333",
           stroke_width="0.3", opacity="0.6")
    # Etincelles
    for ex, ey, er in [(90, 120, 1), (112, 115, 0.8), (95, 108, 0.6),
                        (108, 100, 0.7), (85, 110, 0.5), (118, 105, 0.9)]:
        s += C(ex, ey, er, fill="#ff8800", opacity="0.3")
        s += C(ex, ey, er * 3, fill="#ff8800", opacity="0.03", filter="url(#glow-sm)")
    s += rim_border("#cc3333")
    return make_svg(s)


def chesed() -> str:
    """Observatoire avec vue sur l'ocean. Tons bleus."""
    s = bg_radial("#0a1020", "#0a0a0a")
    # Grande fenetre/baie vitree — vue sur l'ocean
    s += R(30, 20, 140, 130, fill="#0a1428", stroke="#4488cc",
           stroke_width="0.8", opacity="0.7")
    # Ciel visible a travers
    s += P("M32,22 L168,22 L168,70 L32,70 Z", fill="#0a1428", opacity="0.5")
    # Etoiles dans le ciel
    for sx, sy, sr in [(50, 30, 0.8), (80, 35, 1), (120, 28, 0.7),
                        (145, 38, 0.9), (60, 42, 0.6), (135, 32, 0.5),
                        (100, 25, 1.1)]:
        s += C(sx, sy, sr, fill="#aabbdd", opacity="0.4")
    # Lune
    s += C(155, 35, 8, fill="#bbccee", opacity="0.15")
    s += C(158, 33, 7, fill="#0a1428", opacity="0.5")
    # Ocean
    for i in range(8):
        wy = 75 + i * 8
        op = 0.15 - i * 0.015
        s += P(f"M32,{wy} Q{65},{wy - 2} {100},{wy + 1}"
               f" Q{135},{wy - 1} 168,{wy}",
               fill="none", stroke="#4488cc", stroke_width="0.6", opacity=f"{op:.3f}")
    # Horizon
    s += L(32, 72, 168, 72, stroke="#4488cc", stroke_width="0.3", opacity="0.2")
    # Reflet de lune sur l'eau
    s += E(155, 85, 3, 12, fill="#bbccee", opacity="0.04")
    # Cadre de la fenetre (montants)
    s += L(100, 20, 100, 150, stroke="#4488cc", stroke_width="0.6", opacity="0.25")
    s += L(30, 85, 170, 85, stroke="#4488cc", stroke_width="0.6", opacity="0.2")
    # Murs autour de la fenetre
    s += R(0, 0, 30, H, fill="#0e1a2a", opacity="0.8")
    s += R(170, 0, 30, H, fill="#0e1a2a", opacity="0.8")
    # Sol
    s += floor(185, "#0e1a2a", "#335577")
    # Telescope
    s += L(55, 165, 75, 110, stroke="#4488cc", stroke_width="2", opacity="0.4")
    # Oculaire
    s += C(55, 168, 4, fill="#1a2a3a", stroke="#4488cc",
           stroke_width="0.5", opacity="0.5")
    # Objectif
    s += C(76, 108, 6, fill="#1a2a3a", stroke="#4488cc",
           stroke_width="0.8", opacity="0.4")
    # Trepied
    s += L(55, 170, 45, 195, stroke="#4488cc", stroke_width="1", opacity="0.3")
    s += L(55, 170, 65, 195, stroke="#4488cc", stroke_width="1", opacity="0.3")
    s += L(55, 170, 55, 195, stroke="#4488cc", stroke_width="0.8", opacity="0.25")
    # Lueur bleue
    s += C(100, 100, 60, fill="#4488cc", opacity="0.03", filter="url(#glow-amb)")
    s += rim_border("#4488cc")
    return make_svg(s)


def daat() -> str:
    """Pont au-dessus de l'abime. Tons gris, brumeux."""
    s = bg_radial("#121212", "#0a0a0a", cy="70%")
    # Abime en dessous — pur noir
    s += R(0, 100, W, H - 100, fill="#050505")
    # Brume qui monte de l'abime
    for i in range(6):
        my = 140 + i * 15
        s += E(CX + (i % 3 - 1) * 30, my, 60 - i * 5, 12 - i,
               fill="#555555", opacity=f"{0.04 - i * 0.005:.3f}",
               filter="url(#glow-amb)")
    # Falaises de chaque cote
    # Gauche
    s += P("M0,80 Q15,85 25,90 L25,250 L0,250 Z",
           fill="#222222", stroke="#555555", stroke_width="0.5", opacity="0.8")
    s += P("M0,70 Q10,75 20,82 L25,90 L0,80 Z",
           fill="#2a2a2a", opacity="0.6")
    # Droite
    s += P("M200,80 Q185,85 175,90 L175,250 L200,250 Z",
           fill="#222222", stroke="#555555", stroke_width="0.5", opacity="0.8")
    s += P("M200,70 Q190,75 180,82 L175,90 L200,80 Z",
           fill="#2a2a2a", opacity="0.6")
    # Pont — planches de bois etroites
    s += P("M25,105 L175,105 L175,112 L25,112 Z",
           fill="#2a2a2a", stroke="#555555", stroke_width="0.5", opacity="0.6")
    # Planches
    for i in range(12):
        px = 28 + i * 12.5
        s += R(px, 105, 10, 7, fill="#333333",
               stroke="#444444", stroke_width="0.3", opacity="0.5")
    # Cordes de garde-corps
    s += P("M25,95 Q60,92 100,93 Q140,92 175,95",
           fill="none", stroke="#555555", stroke_width="0.8", opacity="0.3")
    s += P("M25,100 Q60,97 100,98 Q140,97 175,100",
           fill="none", stroke="#555555", stroke_width="0.6", opacity="0.25")
    # Poteaux
    for px in [35, 75, 125, 165]:
        s += L(px, 95, px, 112, stroke="#555555", stroke_width="1", opacity="0.3")
    # Brume autour du pont
    s += E(100, 108, 80, 10, fill="#555555", opacity="0.03", filter="url(#glow-amb)")
    # Brume au sommet
    s += E(100, 60, 70, 20, fill="#333333", opacity="0.03", filter="url(#glow-amb)")
    # Profondeur de l'abime — lueur lointaine en bas
    s += C(100, 230, 20, fill="#333333", opacity="0.02", filter="url(#glow-amb)")
    s += rim_border("#555555")
    return make_svg(s)


def binah() -> str:
    """Cathedrale. Bleu profond, voute, colonnes massives."""
    s = bg_radial("#0a1030", "#0a0a0a", cy="20%")
    # Voute gothique — arcs pointes
    s += P("M0,0 Q50,5 100,40 Q150,5 200,0 L200,20 Q150,25 100,55 Q50,25 0,20 Z",
           fill="#1a2244", stroke="#2244aa", stroke_width="0.5", opacity="0.6")
    # Arcs secondaires
    s += P("M30,0 Q65,15 100,45 Q135,15 170,0",
           fill="none", stroke="#2244aa", stroke_width="0.8", opacity="0.3")
    s += P("M10,0 Q55,20 100,50 Q145,20 190,0",
           fill="none", stroke="#2244aa", stroke_width="0.5", opacity="0.2")
    # Colonnes massives
    for cx_col in [35, 165]:
        # Fut
        s += R(cx_col - 12, 40, 24, 195, fill="#1a1a30", stroke="#2244aa",
               stroke_width="0.6", opacity="0.7")
        # Cannelures
        for i in range(4):
            lx = cx_col - 8 + i * 5
            s += L(lx, 50, lx, 230, stroke="#2244aa",
                   stroke_width="0.3", opacity="0.08")
        # Chapiteau
        s += P(f"M{cx_col - 16},{45} L{cx_col - 12},{40}"
               f" L{cx_col + 12},{40} L{cx_col + 16},{45} Z",
               fill="#1a1a30", stroke="#2244aa", stroke_width="0.4", opacity="0.5")
        # Base
        s += R(cx_col - 15, 230, 30, 8, fill="#1a1a30", stroke="#2244aa",
               stroke_width="0.3", opacity="0.5")
    # Colonnes secondaires (plus en arriere)
    for cx_col in [70, 130]:
        s += R(cx_col - 8, 50, 16, 185, fill="#121230", stroke="#2244aa",
               stroke_width="0.3", opacity="0.5")
    # Sol de pierre
    s += floor(235, "#0e0e20", "#2244aa")
    # Rosace au fond (vitrail)
    s += C(100, 80, 22, fill="#0a1030", stroke="#2244aa",
           stroke_width="1", opacity="0.5")
    # Rayons du vitrail
    for i in range(8):
        angle = math.radians(i * 45)
        ix = 100 + math.cos(angle) * 10
        iy = 80 + math.sin(angle) * 10
        ox = 100 + math.cos(angle) * 20
        oy = 80 + math.sin(angle) * 20
        s += L(ix, iy, ox, oy, stroke="#4466cc", stroke_width="0.5", opacity="0.2")
    # Centre lumineux du vitrail
    s += C(100, 80, 6, fill="#4466cc", opacity="0.12")
    s += C(100, 80, 12, fill="#4466cc", opacity="0.04", filter="url(#glow-sm)")
    # Lumiere descendant du vitrail
    s += P("M88,95 L80,235 L120,235 L112,95 Z",
           fill="#2244aa", opacity="0.015")
    s += rim_border("#2244aa")
    return make_svg(s)


def chokmah() -> str:
    """Observatoire stellaire. Tons argentes, dome ouvert."""
    s = bg_radial("#0e0e12", "#0a0a0a", cy="30%")
    # Dome ouvert — arcs du dome
    s += P("M10,120 Q10,30 100,10 Q190,30 190,120",
           fill="none", stroke="#aaaaaa", stroke_width="1", opacity="0.3")
    # Arcs internes du dome
    s += P("M30,120 Q30,50 100,25 Q170,50 170,120",
           fill="none", stroke="#aaaaaa", stroke_width="0.5", opacity="0.2")
    # Ouverture du dome (ciel visible)
    s += P("M50,120 Q50,55 100,35 Q150,55 150,120 Z",
           fill="#0a0a10", opacity="0.6")
    # Etoiles a travers l'ouverture
    stars = [
        (80, 50, 1.2), (110, 42, 0.9), (95, 58, 0.7), (125, 55, 1.0),
        (70, 65, 0.6), (140, 48, 0.8), (100, 38, 0.5), (88, 72, 0.7),
        (130, 68, 0.6), (75, 80, 0.5), (115, 75, 0.8), (105, 48, 0.6),
        (90, 45, 0.9), (135, 60, 0.7), (65, 55, 0.5),
    ]
    for sx, sy, sr in stars:
        s += C(sx, sy, sr, fill="#ccccdd", opacity="0.5")
        if sr > 0.8:
            s += C(sx, sy, sr * 3, fill="#ccccdd", opacity="0.03", filter="url(#glow-sm)")
    # Point lumineux central brillant (Chokmah = eclair premier)
    s += C(100, 55, 3, fill="#ffffff", opacity="0.6")
    s += C(100, 55, 8, fill="#ffffff", opacity="0.08", filter="url(#glow-sm)")
    s += C(100, 55, 20, fill="#ddddff", opacity="0.03", filter="url(#glow-amb)")
    # Rayons de l'etoile
    for i in range(4):
        angle = math.radians(i * 45)
        length = 12
        ex = 100 + math.cos(angle) * length
        ey = 55 + math.sin(angle) * length
        s += L(100, 55, ex, ey, stroke="#ffffff", stroke_width="0.4", opacity="0.15")
    # Structure du dome (meridiens)
    for i in range(5):
        t = 0.2 + i * 0.15
        mx = 10 + t * 180
        s += P(f"M{mx:.0f},120 Q{mx * 0.6 + 40:.0f},{40 + abs(mx - 100) * 0.3:.0f}"
               f" {100},{15 + abs(mx - 100) * 0.15:.0f}",
               fill="none", stroke="#aaaaaa", stroke_width="0.4", opacity="0.12")
    # Sol de l'observatoire
    s += floor(190, "#0e0e12", "#555555")
    # Murs du dome (bas)
    s += R(0, 120, 10, H - 120, fill="#1a1a1e", opacity="0.8")
    s += R(190, 120, 10, H - 120, fill="#1a1a1e", opacity="0.8")
    # Instruments
    # Astrolabe sur piedestal
    s += R(82, 195, 36, 5, fill="#2a2a2a", stroke="#aaaaaa",
           stroke_width="0.3", opacity="0.4")
    s += R(95, 200, 10, 20, fill="#2a2a2a", opacity="0.4")
    s += C(100, 190, 10, fill="none", stroke="#aaaaaa",
           stroke_width="0.6", opacity="0.3")
    s += L(100, 182, 100, 198, stroke="#aaaaaa", stroke_width="0.3", opacity="0.2")
    s += L(92, 190, 108, 190, stroke="#aaaaaa", stroke_width="0.3", opacity="0.2")
    s += rim_border("#aaaaaa")
    return make_svg(s)


def keter() -> str:
    """Salle de la couronne. Blanc/or, lumiere pure, presque abstrait."""
    s = bg_radial("#1a1a10", "#0a0a0a", cy="35%")
    # Lumiere pure depuis le centre — rayons
    for i in range(12):
        angle = math.radians(i * 30)
        length = 120
        ex = 100 + math.cos(angle) * length
        ey = 100 + math.sin(angle) * length
        s += L(100, 100, ex, ey, stroke="#ffffff",
               stroke_width="0.5", opacity=f"{0.05 + (i % 3) * 0.01:.2f}")
    # Halos concentriques
    for r, op in [(80, 0.015), (60, 0.02), (40, 0.03), (25, 0.04)]:
        s += C(100, 100, r, fill="#ffffff", opacity=f"{op:.3f}", filter="url(#glow-amb)")
    # Couronne flottante
    # Bande de base
    s += E(100, 85, 30, 8, fill="none", stroke="#ffcc00",
           stroke_width="1.5", opacity="0.5")
    # Points de la couronne
    for i in range(5):
        angle = math.radians(-180 + i * 45)
        bx = 100 + math.cos(angle) * 28
        by = 85 + math.sin(angle) * 6
        tip_y = by - 15 - (2 if i == 2 else 0)
        s += P(f"M{bx - 4:.1f},{by:.1f} L{bx:.1f},{tip_y:.1f} L{bx + 4:.1f},{by:.1f}",
               fill="#ffcc00", opacity="0.35")
    # Joyau central (sommet)
    s += C(100, 64, 3, fill="#ffffff", opacity="0.5")
    s += C(100, 64, 8, fill="#ffffff", opacity="0.05", filter="url(#glow-sm)")
    # Point de lumiere supreme
    s += C(100, 100, 5, fill="#ffffff", opacity="0.25")
    s += C(100, 100, 15, fill="#ffffff", opacity="0.06", filter="url(#glow-sm)")
    # Sol a peine visible
    s += P(f"M0,200 Q100,190 200,200 L200,250 L0,250 Z",
           fill="#1a1a10", opacity="0.3")
    # Particules de lumiere flottantes
    particles = [
        (40, 60, 0.8), (160, 70, 0.7), (55, 140, 0.9), (145, 150, 0.6),
        (30, 110, 0.5), (170, 120, 0.7), (80, 180, 0.6), (120, 175, 0.5),
        (65, 40, 0.4), (135, 45, 0.5), (45, 190, 0.4), (155, 185, 0.3),
    ]
    for px, py, pr in particles:
        s += C(px, py, pr, fill="#ffffff", opacity="0.15")
    s += rim_border("#ffcc00", "0.08")
    return make_svg(s)


# ═══════════════════════════════════════════════════════════
#  4 PAYSAGES — Olamot (page Les Mondes)
# ═══════════════════════════════════════════════════════════


def atziluth() -> str:
    """Lumiere doree pure. Abstrait. Rayons depuis le centre."""
    s = bg_radial("#1a1600", "#0a0a0a")
    # Rayons radiants depuis le centre
    for i in range(24):
        angle = math.radians(i * 15)
        length = 140
        ex = 100 + math.cos(angle) * length
        ey = 125 + math.sin(angle) * length
        width = 0.4 + (i % 3) * 0.3
        op = 0.06 + (i % 4) * 0.015
        s += L(100, 125, ex, ey, stroke="#ffcc00",
               stroke_width=f"{width:.1f}", opacity=f"{op:.3f}")
    # Anneaux concentriques de lumiere
    for r, op in [(100, 0.02), (75, 0.03), (50, 0.04), (30, 0.06), (15, 0.08)]:
        s += C(100, 125, r, fill="#ffcc00", opacity=f"{op:.3f}", filter="url(#glow-amb)")
    # Noyau central
    s += C(100, 125, 8, fill="#ffcc00", opacity="0.3")
    s += C(100, 125, 4, fill="#ffffff", opacity="0.5")
    s += C(100, 125, 20, fill="#ffcc00", opacity="0.06", filter="url(#glow-sm)")
    # Particules de lumiere
    import random
    random.seed(77)
    for _ in range(20):
        px = random.randint(10, 190)
        py = random.randint(10, 240)
        pr = random.uniform(0.3, 1.2)
        dist = math.hypot(px - 100, py - 125)
        op = max(0.05, 0.25 - dist * 0.002)
        s += C(px, py, pr, fill="#ffcc00", opacity=f"{op:.2f}")
    s += rim_border("#ffcc00", "0.08")
    return make_svg(s)


def briah() -> str:
    """Creation stellaire. Ciel bleu profond, etoiles naissantes, nebuleuses."""
    s = bg_radial("#0a1030", "#0a0a0a", cy="50%")
    # Nebuleuse — nuages de gaz
    nebulae = [
        (60, 80, 45, 25, "#4466aa", 0.04),
        (140, 120, 35, 30, "#6644aa", 0.035),
        (90, 160, 50, 20, "#4466cc", 0.03),
        (110, 60, 30, 18, "#6688cc", 0.04),
        (50, 180, 40, 22, "#5555aa", 0.025),
    ]
    for nx, ny, nrx, nry, nc, nop in nebulae:
        s += E(nx, ny, nrx, nry, fill=nc, opacity=f"{nop:.3f}", filter="url(#glow-amb)")
    # Etoiles — differentes intensites
    import random
    random.seed(88)
    for _ in range(50):
        sx = random.randint(5, 195)
        sy = random.randint(5, 245)
        sr = random.uniform(0.3, 1.5)
        op = random.uniform(0.2, 0.6)
        color = random.choice(["#aabbee", "#bbccff", "#ccddff", "#9999dd", "#ffffff"])
        s += C(sx, sy, sr, fill=color, opacity=f"{op:.2f}")
        # Lueur pour les grosses etoiles
        if sr > 1.0:
            s += C(sx, sy, sr * 4, fill=color, opacity="0.03", filter="url(#glow-sm)")
    # Etoile "naissante" centrale — plus brillante
    s += C(100, 125, 2.5, fill="#ffffff", opacity="0.6")
    s += C(100, 125, 7, fill="#6688cc", opacity="0.08", filter="url(#glow-sm)")
    s += C(100, 125, 18, fill="#6688cc", opacity="0.03", filter="url(#glow-amb)")
    # Rayons de l'etoile naissante
    for i in range(6):
        angle = math.radians(i * 60 + 15)
        ex = 100 + math.cos(angle) * 15
        ey = 125 + math.sin(angle) * 15
        s += L(100, 125, ex, ey, stroke="#bbccff", stroke_width="0.3", opacity="0.15")
    # Filaments de gaz (spirales)
    s += P("M40,100 Q70,90 90,110 Q110,130 140,120 Q160,110 170,130",
           fill="none", stroke="#6688cc", stroke_width="0.6", opacity="0.06")
    s += P("M30,150 Q60,140 80,160 Q110,170 130,155 Q160,145 180,160",
           fill="none", stroke="#4466aa", stroke_width="0.5", opacity="0.05")
    s += rim_border("#6688cc", "0.08")
    return make_svg(s)


def yetzirah() -> str:
    """Foret verte. Arbres emergent de la brume, structures visibles."""
    s = bg_radial("#0a1a0a", "#0a0a0a", cy="80%")
    # Brume de fond
    for i in range(4):
        my = 160 + i * 15
        s += E(100, my, 100, 15 - i * 2, fill="#88aa88",
               opacity=f"{0.03 - i * 0.005:.3f}", filter="url(#glow-amb)")
    # Arbres en arriere-plan (plus petits, plus sombres)
    back_trees = [(25, 0.6), (55, 0.7), (145, 0.65), (175, 0.55)]
    for tx, scale in back_trees:
        trunk_h = 80 * scale
        top = 130 - trunk_h
        # Tronc
        s += R(tx - 3 * scale, top + trunk_h * 0.3, 6 * scale, trunk_h * 0.7,
               fill="#2a3a2a", opacity="0.4")
        # Feuillage (triangle)
        s += P(f"M{tx},{top} L{tx - 18 * scale},{top + trunk_h * 0.5}"
               f" L{tx + 18 * scale},{top + trunk_h * 0.5} Z",
               fill="#1a3a1a", opacity="0.35")
        s += P(f"M{tx},{top + trunk_h * 0.15}"
               f" L{tx - 22 * scale},{top + trunk_h * 0.65}"
               f" L{tx + 22 * scale},{top + trunk_h * 0.65} Z",
               fill="#1a3a1a", opacity="0.3")
    # Arbres au premier plan (plus grands, plus detailles)
    front_trees = [(75, 1.0), (100, 1.2), (130, 0.95)]
    for tx, scale in front_trees:
        trunk_h = 110 * scale
        top = 180 - trunk_h
        tw = 5 * scale
        # Tronc
        s += R(tx - tw, top + trunk_h * 0.3, tw * 2, trunk_h * 0.7,
               fill="#2a3a2a", stroke="#88aa88", stroke_width="0.3",
               opacity="0.6")
        # Branches
        for bh in [0.35, 0.5]:
            by = top + trunk_h * bh
            s += P(f"M{tx},{by} Q{tx - 15 * scale},{by - 5} {tx - 22 * scale},{by - 2}",
                   fill="none", stroke="#2a3a2a", stroke_width=f"{1.5 * scale:.1f}",
                   opacity="0.4")
            s += P(f"M{tx},{by} Q{tx + 12 * scale},{by - 8} {tx + 20 * scale},{by - 4}",
                   fill="none", stroke="#2a3a2a", stroke_width=f"{1.5 * scale:.1f}",
                   opacity="0.4")
        # Feuillage en couches
        for layer in range(3):
            ly = top + layer * trunk_h * 0.15
            lw = (25 - layer * 4) * scale
            s += P(f"M{tx},{ly} L{tx - lw},{ly + trunk_h * 0.2}"
                   f" L{tx + lw},{ly + trunk_h * 0.2} Z",
                   fill="#1a3a1a", opacity=f"{0.5 - layer * 0.1:.2f}")
    # Sol forestier
    s += P(f"M0,200 Q50,195 100,198 Q150,195 200,200 L200,250 L0,250 Z",
           fill="#1a2a1a", opacity="0.7")
    # Motifs geometriques dans le feuillage (structures visibles = Yetzirah)
    for tx in [75, 100, 130]:
        s += C(tx, 95, 3, fill="none", stroke="#88aa88",
               stroke_width="0.4", opacity="0.12")
        s += P(f"M{tx - 3},{95} L{tx},{92} L{tx + 3},{95} L{tx},{98} Z",
               fill="none", stroke="#88aa88", stroke_width="0.3", opacity="0.1")
    # Lueur verte diffuse
    s += C(100, 140, 60, fill="#88aa88", opacity="0.03", filter="url(#glow-amb)")
    s += rim_border("#88aa88", "0.08")
    return make_svg(s)


def assiah() -> str:
    """Terre/terrain. Brun/ambre, rocheux, solide, reel."""
    s = bg_radial("#1a1408", "#0a0a0a", cy="60%")
    # Ciel minimal (horizon)
    s += P("M0,0 L200,0 L200,80 Q150,75 100,78 Q50,75 0,80 Z",
           fill="#121008", opacity="0.6")
    # Quelques etoiles dans le ciel sombre
    for sx, sy, sr in [(30, 15, 0.5), (80, 25, 0.7), (140, 10, 0.6),
                        (170, 30, 0.4), (60, 35, 0.3)]:
        s += C(sx, sy, sr, fill="#ccaa88", opacity="0.25")
    # Montagnes au loin
    s += P("M0,80 Q30,50 60,70 Q80,45 100,60 Q130,40 150,65 Q175,55 200,80 Z",
           fill="#221a0e", stroke="#cc8844", stroke_width="0.3", opacity="0.5")
    # Terrain rocheux au premier plan
    s += P("M0,110 Q30,100 60,108 Q80,95 100,105"
           " Q130,95 150,102 Q175,98 200,110 L200,250 L0,250 Z",
           fill="#2a1e10", opacity="0.7")
    # Rochers
    rocks = [
        (35, 140, 20, 15), (80, 155, 18, 12), (130, 145, 22, 14),
        (165, 160, 15, 10), (60, 170, 12, 8),
    ]
    for rx, ry, rw, rrh in rocks:
        s += P(f"M{rx},{ry + rrh} Q{rx - rw * 0.4},{ry + rrh * 0.3}"
               f" {rx},{ry} Q{rx + rw * 0.5},{ry + rrh * 0.2}"
               f" {rx + rw},{ry + rrh} Z",
               fill="#332a1a", stroke="#cc8844", stroke_width="0.4", opacity="0.5")
    # Texture du sol — stries
    for i in range(8):
        sy_line = 120 + i * 15
        s += P(f"M{i * 10},{sy_line} Q{50 + i * 5},{sy_line - 2} {100 + i * 8},{sy_line + 1}"
               f" Q{150 - i * 3},{sy_line - 1} {200},{sy_line}",
               fill="none", stroke="#cc8844", stroke_width="0.3", opacity="0.06")
    # Chemin de terre qui s'eloigne
    s += P("M80,250 Q85,200 90,170 Q95,150 100,130 Q105,120 100,110",
           fill="none", stroke="#554422", stroke_width="8", opacity="0.15")
    s += P("M80,250 Q85,200 90,170 Q95,150 100,130 Q105,120 100,110",
           fill="none", stroke="#cc8844", stroke_width="0.4", opacity="0.08")
    # Lueur ambiante
    s += C(100, 110, 40, fill="#cc8844", opacity="0.03", filter="url(#glow-amb)")
    s += rim_border("#cc8844", "0.08")
    return make_svg(s)


# ═══════════════════════════════════════════════════════════
#  4 CREATURES / OMBRES — Qliphoth (page Les Erreurs)
# ═══════════════════════════════════════════════════════════


def nogah() -> str:
    """Silhouette avec eclat ambre. Lumiere encore visible, fissures lumineuses."""
    s = bg_radial("#1a1400", "#0a0a0a")
    # Silhouette humaine
    silhouette_color = "#0e0a05"
    # Corps
    s += P(f"M55,250 Q55,200 70,185 Q{CX},170 130,185 Q145,200 145,250 Z",
           fill=silhouette_color)
    # Cou
    s += R(90, 135, 20, 35, fill=silhouette_color)
    # Tete
    s += E(100, 110, 28, 32, fill=silhouette_color)
    # Fissures de lumiere sur le corps
    cracks = [
        (85, 180, 80, 200, 78, 220),
        (115, 185, 120, 205, 125, 225),
        (95, 140, 90, 155, 88, 165),
        (108, 142, 112, 158, 115, 170),
        (92, 195, 88, 210, 85, 230),
    ]
    for x1, y1, x2, y2, x3, y3 in cracks:
        s += P(f"M{x1},{y1} Q{x2},{y2} {x3},{y3}",
               fill="none", stroke="#ffb000", stroke_width="1.2", opacity="0.35")
        s += P(f"M{x1},{y1} Q{x2},{y2} {x3},{y3}",
               fill="none", stroke="#ffb000", stroke_width="3", opacity="0.05",
               filter="url(#glow-sm)")
    # Fissure sur le visage
    s += P("M90,95 Q95,105 92,120", fill="none", stroke="#ffb000",
           stroke_width="1", opacity="0.3")
    s += P("M110,100 Q108,112 112,125", fill="none", stroke="#ffb000",
           stroke_width="0.8", opacity="0.25")
    # Yeux — un oeil visible (ambre)
    s += E(108, 107, 4, 2.5, fill="#ffb000", opacity="0.4")
    s += C(108, 107, 5, fill="#ffb000", opacity="0.05", filter="url(#glow-sm)")
    # Lumiere qui s'echappe du coeur
    s += C(100, 160, 12, fill="#ffb000", opacity="0.08", filter="url(#glow-sm)")
    s += C(100, 160, 25, fill="#ffb000", opacity="0.03", filter="url(#glow-amb)")
    # Halo ambre autour de la figure
    s += C(100, 140, 65, fill="#ffb000", opacity="0.02", filter="url(#glow-amb)")
    s += rim_border("#ffb000", "0.1")
    return make_svg(s)


def ruach() -> str:
    """Ombre qui se repand. Orange sombre, tentacules/fumee."""
    s = bg_radial("#1a0e00", "#0a0a0a")
    # Masse centrale sombre
    s += E(100, 120, 35, 45, fill="#0e0800", opacity="0.9")
    # Tentacules / tendrils de fumee se repandant
    tendrils = [
        "M65,120 Q40,100 20,80 Q10,70 5,50",
        "M135,120 Q160,100 180,80 Q190,70 195,50",
        "M80,155 Q60,175 40,195 Q25,210 15,230",
        "M120,155 Q140,175 160,195 Q175,210 185,230",
        "M70,100 Q45,85 25,95 Q10,100 0,110",
        "M130,100 Q155,85 175,95 Q190,100 200,110",
        "M90,160 Q85,185 80,210 Q75,230 70,250",
        "M110,160 Q115,185 120,210 Q125,230 130,250",
        "M100,80 Q95,60 85,40 Q80,25 75,10",
        "M100,80 Q105,60 115,40 Q120,25 125,10",
    ]
    for i, d in enumerate(tendrils):
        w = 3 - i * 0.15
        op = 0.2 - i * 0.012
        s += P(d, fill="none", stroke="#cc6600", stroke_width=f"{max(w, 0.5):.1f}",
               opacity=f"{max(op, 0.04):.3f}", stroke_linecap="round")
        # Lueur sur chaque tendril
        s += P(d, fill="none", stroke="#cc6600", stroke_width=f"{max(w * 2, 1):.1f}",
               opacity=f"{max(op * 0.2, 0.01):.3f}", filter="url(#glow-sm)")
    # Noyau — coeur de l'ombre
    s += C(100, 120, 18, fill="#1a0a00", opacity="0.8")
    s += C(100, 120, 12, fill="#cc6600", opacity="0.04", filter="url(#glow-sm)")
    # Deux points sombres (yeux absents)
    s += E(90, 112, 3, 2, fill="#331a00", opacity="0.6")
    s += E(110, 112, 3, 2, fill="#331a00", opacity="0.6")
    # Fumee ambiante
    s += E(100, 100, 70, 50, fill="#cc6600", opacity="0.02", filter="url(#glow-amb)")
    s += rim_border("#cc6600", "0.1")
    return make_svg(s)


def anan() -> str:
    """Figure masquee/capuchonnee. Rouge-brun sombre. Menace silencieuse."""
    s = bg_radial("#1a0e0e", "#0a0a0a")
    # Sol
    s += P("M0,210 Q100,205 200,210 L200,250 L0,250 Z",
           fill="#1a0a0a", opacity="0.4")
    # Silhouette encapuchonnee
    hood_color = "#1a0e0a"
    # Robe/corps
    s += P(f"M45,250 Q50,200 65,185 Q{CX},170 135,185 Q150,200 155,250 Z",
           fill=hood_color, stroke="#663333", stroke_width="0.5", opacity="0.8")
    # Plis de la robe
    for fx in [70, 90, 110, 130]:
        s += L(fx, 185, fx + 2, 245, stroke="#663333",
               stroke_width="0.3", opacity="0.1")
    # Capuche large
    s += P("M60,185 Q60,100 100,80 Q140,100 140,185"
           " Q130,170 100,165 Q70,170 60,185 Z",
           fill=hood_color, stroke="#663333", stroke_width="0.6", opacity="0.85")
    # Ombre interieure de la capuche (visage invisible)
    s += E(100, 130, 22, 28, fill="#0a0500", opacity="0.9")
    # Bord de la capuche
    s += P("M65,180 Q70,168 100,162 Q130,168 135,180",
           fill="none", stroke="#663333", stroke_width="0.8", opacity="0.35")
    # Vague suggestion d'un masque — forme dans le noir
    s += P("M88,120 Q95,115 100,118 Q105,115 112,120"
           " Q110,128 100,132 Q90,128 88,120",
           fill="#1a0a05", opacity="0.4")
    # Pas d'yeux — juste le vide
    # Ombre projetee au sol
    s += E(100, 220, 45, 8, fill="#0a0500", opacity="0.3")
    # Brume basse
    s += E(100, 230, 80, 12, fill="#663333", opacity="0.02", filter="url(#glow-amb)")
    # Aura sombre
    s += C(100, 140, 60, fill="#663333", opacity="0.02", filter="url(#glow-amb)")
    s += rim_border("#663333", "0.1")
    return make_svg(s)


def mamash() -> str:
    """Masse noire pure avec yeux rouges. Tenebres presque informes."""
    s = bg_radial("#0a0000", "#050000")
    # Masse informe de tenebres
    s += P("M30,60 Q20,100 25,150 Q30,200 20,250"
           " L180,250 Q170,200 175,150 Q180,100 170,60"
           " Q150,30 100,25 Q50,30 30,60 Z",
           fill="#0a0000", opacity="0.95")
    # Bords irreguliers — la masse pulse
    s += P("M30,60 Q20,100 25,150 Q30,200 20,250",
           fill="none", stroke="#330000", stroke_width="1.5", opacity="0.2")
    s += P("M170,60 Q180,100 175,150 Q170,200 180,250",
           fill="none", stroke="#330000", stroke_width="1.5", opacity="0.2")
    s += P("M30,60 Q50,30 100,25 Q150,30 170,60",
           fill="none", stroke="#330000", stroke_width="1", opacity="0.15")
    # Ondulations internes (la masse vit)
    for i in range(5):
        wy = 70 + i * 35
        s += P(f"M40,{wy} Q70,{wy - 5} 100,{wy + 2}"
               f" Q130,{wy - 3} 160,{wy}",
               fill="none", stroke="#1a0000", stroke_width="2", opacity="0.15")
    # LES YEUX — deux points de rouge pur
    for ex in [85, 115]:
        # Oeil rouge
        s += E(ex, 110, 4, 2.5, fill="#ff0000", opacity="0.6")
        # Lueur de l'oeil
        s += E(ex, 110, 8, 5, fill="#ff0000", opacity="0.08", filter="url(#glow-sm)")
        s += E(ex, 110, 15, 10, fill="#ff0000", opacity="0.03", filter="url(#glow-amb)")
    # Ligne entre les yeux (suggestion de fissure)
    s += P("M92,110 Q100,108 108,110",
           fill="none", stroke="#330000", stroke_width="0.5", opacity="0.2")
    # Particules sombres autour
    import random
    random.seed(66)
    for _ in range(15):
        px = random.randint(10, 190)
        py = random.randint(10, 240)
        pr = random.uniform(1, 4)
        s += C(px, py, pr, fill="#0a0000", opacity=f"{random.uniform(0.1, 0.3):.2f}")
    # Aura de tenebres
    s += C(100, 130, 80, fill="#330000", opacity="0.015", filter="url(#glow-amb)")
    s += rim_border("#330000", "0.12")
    return make_svg(s)


# ═══════════════════════════════════════════════════════════
#  Registre et generation
# ═══════════════════════════════════════════════════════════

IMAGES: dict[str, callable] = {
    # 11 Sephiroth (salles)
    "malkuth": malkuth,
    "yesod": yesod,
    "hod": hod,
    "netzach": netzach,
    "tiferet": tiferet,
    "gevurah": gevurah,
    "chesed": chesed,
    "daat": daat,
    "binah": binah,
    "chokmah": chokmah,
    "keter": keter,
    # 4 Olamot (paysages)
    "atziluth": atziluth,
    "briah": briah,
    "yetzirah": yetzirah,
    "assiah": assiah,
    # 4 Qliphoth (creatures/ombres)
    "nogah": nogah,
    "ruach": ruach,
    "anan": anan,
    "mamash": mamash,
}


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, gen in IMAGES.items():
        path = OUTPUT / f"{name}.svg"
        content = gen()
        path.write_text(content, encoding="utf-8")
        size = len(content)
        print(f"  {name:12s} -> {path.name:18s} ({size:>6,d} bytes)")
    print(f"\n  {len(IMAGES)} images generees dans {OUTPUT}/")


if __name__ == "__main__":
    main()
