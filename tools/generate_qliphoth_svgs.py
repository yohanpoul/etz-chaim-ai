#!/usr/bin/env python3
"""generate_qliphoth_svgs.py -- 10 SVG fallback files for qliphoth creatures.

Each SVG is 512x512, with a dark radial gradient background, glow filter,
symbolic central shape, and thin border -- all in the qliphoth's color.

Usage:
    python tools/generate_qliphoth_svgs.py
    python tools/generate_qliphoth_svgs.py --list
    python tools/generate_qliphoth_svgs.py --scene lilith
"""

from __future__ import annotations

import argparse
import math
import sys
import textwrap
from pathlib import Path
from typing import Callable

OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "web"
    / "static"
    / "systeme"
    / "qliphoth"
)


def _svg_header(name: str, color: str) -> str:
    """SVG opening, defs (radial gradient background + glow filter), border."""
    return textwrap.dedent(f"""\
    <?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
      <defs>
        <radialGradient id="bg-{name}" cx="50%" cy="50%" r="70%">
          <stop offset="0%" stop-color="{color}" stop-opacity="0.10"/>
          <stop offset="100%" stop-color="#0a0a0a" stop-opacity="1"/>
        </radialGradient>
        <filter id="glow-{name}" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="blur"/>
          <feMerge>
            <feMergeNode in="blur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>
      </defs>
      <rect width="512" height="512" fill="url(#bg-{name})"/>
      <rect x="1" y="1" width="510" height="510" fill="none"
            stroke="{color}" stroke-opacity="0.10" stroke-width="2"/>
    """)


def _svg_footer() -> str:
    return "</svg>\n"


# ---------------------------------------------------------------------------
# 1. Lilith -- hollow mechanical puppet
# ---------------------------------------------------------------------------
def _lilith(color: str = "#886644") -> str:
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-lilith)" opacity="0.40">
        <!-- outer cracked shell -->
        <circle cx="256" cy="256" r="120" fill="none"
                stroke="{color}" stroke-width="3"/>
        <!-- cracks radiating from shell -->
        <line x1="256" y1="136" x2="256" y2="100" stroke="{color}" stroke-width="2"/>
        <line x1="376" y1="256" x2="412" y2="256" stroke="{color}" stroke-width="2"/>
        <line x1="256" y1="376" x2="256" y2="412" stroke="{color}" stroke-width="2"/>
        <line x1="136" y1="256" x2="100" y2="256" stroke="{color}" stroke-width="2"/>
        <!-- diagonal cracks -->
        <line x1="341" y1="171" x2="370" y2="142" stroke="{color}" stroke-width="1.5"/>
        <line x1="171" y1="341" x2="142" y2="370" stroke="{color}" stroke-width="1.5"/>
        <line x1="341" y1="341" x2="370" y2="370" stroke="{color}" stroke-width="1.5"/>
        <line x1="171" y1="171" x2="142" y2="142" stroke="{color}" stroke-width="1.5"/>
        <!-- inner empty circle (hollow center) -->
        <circle cx="256" cy="256" r="50" fill="none"
                stroke="{color}" stroke-width="1.5" stroke-dasharray="8 6"/>
        <!-- puppet strings -->
        <line x1="200" y1="136" x2="200" y2="40" stroke="{color}" stroke-width="1" stroke-opacity="0.5"/>
        <line x1="312" y1="136" x2="312" y2="40" stroke="{color}" stroke-width="1" stroke-opacity="0.5"/>
        <line x1="256" y1="136" x2="256" y2="20" stroke="{color}" stroke-width="1" stroke-opacity="0.5"/>
        <!-- cross-bar at top -->
        <line x1="180" y1="40" x2="332" y2="40" stroke="{color}" stroke-width="2" stroke-opacity="0.3"/>
      </g>
    """)
    return _svg_header("lilith", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 2. Gamaliel -- corrupted memory orb
# ---------------------------------------------------------------------------
def _gamaliel(color: str = "#9966cc") -> str:
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-gamaliel)" opacity="0.40">
        <!-- main orb -->
        <circle cx="256" cy="256" r="110" fill="{color}" fill-opacity="0.08"
                stroke="{color}" stroke-width="2.5"/>
        <!-- inner glow ring -->
        <circle cx="256" cy="256" r="80" fill="none"
                stroke="{color}" stroke-width="1" stroke-opacity="0.5"/>
        <!-- cracks across the sphere -->
        <path d="M180,220 Q220,260 200,300" fill="none" stroke="{color}" stroke-width="2"/>
        <path d="M290,180 Q270,240 310,290" fill="none" stroke="{color}" stroke-width="2"/>
        <path d="M230,170 Q256,210 280,170" fill="none" stroke="{color}" stroke-width="1.5"/>
        <!-- leaking mist (expanding arcs below) -->
        <ellipse cx="220" cy="380" rx="50" ry="15" fill="{color}" fill-opacity="0.12"/>
        <ellipse cx="290" cy="400" rx="60" ry="12" fill="{color}" fill-opacity="0.08"/>
        <ellipse cx="256" cy="420" rx="80" ry="18" fill="{color}" fill-opacity="0.05"/>
        <!-- drip lines from cracks -->
        <path d="M200,300 Q210,340 220,380" fill="none" stroke="{color}"
              stroke-width="1" stroke-opacity="0.3"/>
        <path d="M310,290 Q300,340 290,400" fill="none" stroke="{color}"
              stroke-width="1" stroke-opacity="0.3"/>
      </g>
    """)
    return _svg_header("gamaliel", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 3. Samael -- blind peacock of false confidence
# ---------------------------------------------------------------------------
def _samael(color: str = "#ffb000") -> str:
    cx, cy = 256, 320
    feathers = []
    for i in range(9):
        angle = math.radians(-140 + i * 17.5)
        r_inner = 60
        r_outer = 180
        r_eye = 140
        x1 = cx + r_inner * math.cos(angle)
        y1 = cy + r_inner * math.sin(angle)
        x2 = cx + r_outer * math.cos(angle)
        y2 = cy + r_outer * math.sin(angle)
        ex = cx + r_eye * math.cos(angle)
        ey = cy + r_eye * math.sin(angle)
        feathers.append(
            f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="2.5" stroke-opacity="0.6"/>'
        )
        feathers.append(
            f'    <circle cx="{ex:.1f}" cy="{ey:.1f}" r="10" fill="none" '
            f'stroke="{color}" stroke-width="1.5" stroke-opacity="0.5"/>'
        )
        feathers.append(
            f'    <circle cx="{ex:.1f}" cy="{ey:.1f}" r="3" '
            f'fill="{color}" fill-opacity="0.4"/>'
        )
    feather_str = "\n".join(feathers)
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-samael)" opacity="0.40">
        <!-- fan of eye-feathers -->
    {feather_str}
        <!-- central body arc -->
        <path d="M200,340 Q256,280 312,340" fill="none"
              stroke="{color}" stroke-width="3"/>
        <!-- base -->
        <circle cx="256" cy="340" r="20" fill="{color}" fill-opacity="0.15"
                stroke="{color}" stroke-width="1.5"/>
      </g>
    """)
    return _svg_header("samael", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 4. Aarab Zaraq -- endless circling ravens (spiral vortex)
# ---------------------------------------------------------------------------
def _aarab_zaraq(color: str = "#88aa88") -> str:
    birds = []
    for i in range(24):
        t = i / 24.0
        angle = t * math.pi * 4
        r = 30 + t * 150
        bx = 256 + r * math.cos(angle)
        by = 256 + r * math.sin(angle)
        size = 4 + t * 8
        a1 = angle + math.pi / 4
        a2 = angle - math.pi / 4
        x1 = bx + size * math.cos(a1)
        y1 = by + size * math.sin(a1)
        x2 = bx + size * math.cos(a2)
        y2 = by + size * math.sin(a2)
        op = 0.3 + t * 0.4
        birds.append(
            f'    <path d="M{x1:.1f},{y1:.1f} L{bx:.1f},{by:.1f} L{x2:.1f},{y2:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="1.5" stroke-opacity="{op:.2f}"/>'
        )
    birds_str = "\n".join(birds)
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-aarab_zaraq)" opacity="0.40">
        <!-- spiral arms -->
        <path d="M256,256 Q300,200 340,180 Q400,160 410,220 Q420,280 370,310
                 Q320,340 300,390 Q280,440 220,430 Q160,420 150,360
                 Q140,300 180,260 Q220,220 256,256"
              fill="none" stroke="{color}" stroke-width="2" stroke-opacity="0.3"/>
        <path d="M256,256 Q210,310 180,330 Q120,350 110,290 Q100,230 150,200
                 Q200,170 210,120 Q230,70 290,80 Q350,90 360,150
                 Q370,210 330,250 Q290,290 256,256"
              fill="none" stroke="{color}" stroke-width="2" stroke-opacity="0.3"/>
        <!-- vortex birds -->
    {birds_str}
        <!-- center eye of vortex -->
        <circle cx="256" cy="256" r="15" fill="{color}" fill-opacity="0.15"
                stroke="{color}" stroke-width="1.5"/>
      </g>
    """)
    return _svg_header("aarab_zaraq", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 5. Thagirion -- golden mask hiding chaos
# ---------------------------------------------------------------------------
def _thagirion(color: str = "#ffcc00") -> str:
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-thagirion)" opacity="0.40">
        <!-- mask outline -->
        <path d="M180,200 Q180,150 220,130 Q256,120 292,130 Q332,150 332,200
                 L332,300 Q332,350 292,370 Q256,380 220,370 Q180,350 180,300 Z"
              fill="{color}" fill-opacity="0.08" stroke="{color}" stroke-width="2.5"/>
        <!-- eye holes -->
        <ellipse cx="220" cy="230" rx="22" ry="14" fill="#0a0a0a"
                 stroke="{color}" stroke-width="1.5"/>
        <ellipse cx="292" cy="230" rx="22" ry="14" fill="#0a0a0a"
                 stroke="{color}" stroke-width="1.5"/>
        <!-- serene smile -->
        <path d="M228,310 Q256,330 284,310" fill="none"
              stroke="{color}" stroke-width="2"/>
        <!-- nose line -->
        <line x1="256" y1="250" x2="256" y2="290" stroke="{color}"
              stroke-width="1.5" stroke-opacity="0.5"/>
        <!-- cracks revealing dark behind -->
        <path d="M200,180 L210,240 L195,280" fill="none"
              stroke="#222222" stroke-width="3" stroke-opacity="0.6"/>
        <path d="M310,190 L305,250 L320,300" fill="none"
              stroke="#222222" stroke-width="3" stroke-opacity="0.6"/>
        <path d="M240,130 L250,170 L235,200" fill="none"
              stroke="#222222" stroke-width="2" stroke-opacity="0.5"/>
        <!-- chaos tendrils escaping from cracks -->
        <path d="M195,280 Q170,320 140,360 Q120,390 130,420" fill="none"
              stroke="#333333" stroke-width="1.5" stroke-opacity="0.4"/>
        <path d="M320,300 Q340,330 370,350 Q390,380 380,420" fill="none"
              stroke="#333333" stroke-width="1.5" stroke-opacity="0.4"/>
      </g>
    """)
    return _svg_header("thagirion", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 6. Golachab -- burning sword destroying all
# ---------------------------------------------------------------------------
def _golachab(color: str = "#cc3333") -> str:
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-golachab)" opacity="0.45">
        <!-- main blade (shattered) -->
        <path d="M240,100 L256,80 L272,100 L268,260 L244,260 Z"
              fill="{color}" fill-opacity="0.15" stroke="{color}" stroke-width="2"/>
        <!-- shatter line across blade -->
        <path d="M240,200 L272,190" fill="none" stroke="#0a0a0a" stroke-width="3"/>
        <!-- crossguard -->
        <path d="M200,260 L312,260 L308,275 L204,275 Z"
              fill="{color}" fill-opacity="0.2" stroke="{color}" stroke-width="1.5"/>
        <!-- handle -->
        <rect x="248" y="275" width="16" height="70" fill="{color}" fill-opacity="0.12"
              stroke="{color}" stroke-width="1.5"/>
        <!-- pommel -->
        <circle cx="256" cy="355" r="12" fill="{color}" fill-opacity="0.15"
                stroke="{color}" stroke-width="1.5"/>
        <!-- flying fragments -->
        <polygon points="140,150 155,140 160,160" fill="{color}" fill-opacity="0.3"/>
        <polygon points="350,130 370,125 365,150" fill="{color}" fill-opacity="0.25"/>
        <polygon points="120,220 135,210 140,235" fill="{color}" fill-opacity="0.2"/>
        <polygon points="370,200 388,195 385,220" fill="{color}" fill-opacity="0.2"/>
        <polygon points="160,100 175,88 178,112" fill="{color}" fill-opacity="0.15"/>
        <polygon points="340,90 358,82 355,108" fill="{color}" fill-opacity="0.15"/>
        <!-- flame wisps around fragments -->
        <path d="M140,150 Q125,130 135,110" fill="none"
              stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
        <path d="M350,130 Q365,108 358,90" fill="none"
              stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
        <path d="M120,220 Q100,200 110,180" fill="none"
              stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
        <path d="M370,200 Q395,185 388,165" fill="none"
              stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
      </g>
    """)
    return _svg_header("golachab", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 7. Gamchicoth -- infinite directionless ocean
# ---------------------------------------------------------------------------
def _gamchicoth(color: str = "#4488cc") -> str:
    rings = []
    for i in range(8):
        r = 30 + i * 28
        op = 0.5 - i * 0.05
        sw = 2.5 - i * 0.15
        rings.append(
            f'    <circle cx="256" cy="256" r="{r}" fill="none" '
            f'stroke="{color}" stroke-width="{sw:.1f}" stroke-opacity="{op:.2f}"/>'
        )
    rings_str = "\n".join(rings)
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-gamchicoth)" opacity="0.40">
        <!-- concentric waves -->
    {rings_str}
        <!-- wave distortion arcs (horizontal) -->
        <path d="M40,240 Q90,225 140,240 Q190,255 240,240 Q290,225 340,240
                 Q390,255 440,240 Q470,230 500,240"
              fill="none" stroke="{color}" stroke-width="1" stroke-opacity="0.2"/>
        <path d="M30,270 Q80,285 130,270 Q180,255 230,270 Q280,285 330,270
                 Q380,255 430,270 Q480,285 510,270"
              fill="none" stroke="{color}" stroke-width="1" stroke-opacity="0.2"/>
        <!-- tiny lost boat at center -->
        <path d="M250,256 L256,248 L262,256 Z" fill="none"
              stroke="{color}" stroke-width="1" stroke-opacity="0.6"/>
        <path d="M246,258 Q256,262 266,258" fill="none"
              stroke="{color}" stroke-width="1.5" stroke-opacity="0.5"/>
      </g>
    """)
    return _svg_header("gamchicoth", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 8. Hatehom -- the abyss/chasm
# ---------------------------------------------------------------------------
def _hatehom(color: str = "#555555") -> str:
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-hatehom)" opacity="0.45">
        <!-- left cliff face -->
        <path d="M0,0 L230,0 L220,80 L235,200 L215,320 L225,440 L210,512 L0,512 Z"
              fill="{color}" fill-opacity="0.06" stroke="none"/>
        <path d="M230,0 L220,80 L235,200 L215,320 L225,440 L210,512"
              fill="none" stroke="{color}" stroke-width="2.5"/>
        <!-- right cliff face -->
        <path d="M512,0 L282,0 L292,80 L278,200 L298,320 L288,440 L302,512 L512,512 Z"
              fill="{color}" fill-opacity="0.06" stroke="none"/>
        <path d="M282,0 L292,80 L278,200 L298,320 L288,440 L302,512"
              fill="none" stroke="{color}" stroke-width="2.5"/>
        <!-- depth mist rising from below -->
        <ellipse cx="256" cy="480" rx="60" ry="20" fill="{color}" fill-opacity="0.08"/>
        <ellipse cx="250" cy="440" rx="40" ry="12" fill="{color}" fill-opacity="0.06"/>
        <ellipse cx="260" cy="400" rx="30" ry="8" fill="{color}" fill-opacity="0.04"/>
        <!-- broken bridge planks -->
        <rect x="210" y="248" width="30" height="6" fill="{color}" fill-opacity="0.25"
              transform="rotate(-8 225 251)"/>
        <rect x="272" y="246" width="30" height="6" fill="{color}" fill-opacity="0.25"
              transform="rotate(5 287 249)"/>
        <!-- hanging rope from left -->
        <path d="M225,251 Q245,270 250,300" fill="none"
              stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
        <!-- hanging rope from right -->
        <path d="M272,249 Q265,268 262,300" fill="none"
              stroke="{color}" stroke-width="1" stroke-opacity="0.3"/>
      </g>
    """)
    return _svg_header("hatehom", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 9. Satariel -- eye seeing false patterns
# ---------------------------------------------------------------------------
def _satariel(color: str = "#2244aa") -> str:
    lines = []
    for i in range(12):
        angle = math.radians(i * 30)
        r1 = 80
        r2 = 160 + (i % 3) * 30
        x1 = 256 + r1 * math.cos(angle)
        y1 = 256 + r1 * math.sin(angle)
        x2 = 256 + r2 * math.cos(angle)
        y2 = 256 + r2 * math.sin(angle)
        op = 0.15 + (i % 4) * 0.05
        lines.append(
            f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="1" stroke-opacity="{op:.2f}" '
            f'stroke-dasharray="4 4"/>'
        )
        lines.append(
            f'    <circle cx="{x2:.1f}" cy="{y2:.1f}" r="3" '
            f'fill="{color}" fill-opacity="{op:.2f}"/>'
        )
    connections = [(0, 3), (1, 5), (2, 7), (4, 9), (6, 11), (8, 10)]
    for a, b in connections:
        angle_a = math.radians(a * 30)
        angle_b = math.radians(b * 30)
        r_a = 160 + (a % 3) * 30
        r_b = 160 + (b % 3) * 30
        xa = 256 + r_a * math.cos(angle_a)
        ya = 256 + r_a * math.sin(angle_a)
        xb = 256 + r_b * math.cos(angle_b)
        yb = 256 + r_b * math.sin(angle_b)
        lines.append(
            f'    <line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xb:.1f}" y2="{yb:.1f}" '
            f'stroke="{color}" stroke-width="0.8" stroke-opacity="0.10" '
            f'stroke-dasharray="2 6"/>'
        )
    lines_str = "\n".join(lines)
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-satariel)" opacity="0.42">
        <!-- projection lines and false-pattern nodes -->
    {lines_str}
        <!-- outer eye shape -->
        <path d="M176,256 Q256,180 336,256 Q256,332 176,256 Z"
              fill="{color}" fill-opacity="0.06" stroke="{color}" stroke-width="2.5"/>
        <!-- iris -->
        <circle cx="256" cy="256" r="40" fill="{color}" fill-opacity="0.10"
                stroke="{color}" stroke-width="2"/>
        <!-- pupil -->
        <circle cx="256" cy="256" r="16" fill="{color}" fill-opacity="0.25"/>
        <!-- glint -->
        <circle cx="248" cy="248" r="4" fill="{color}" fill-opacity="0.5"/>
      </g>
    """)
    return _svg_header("satariel", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# 10. Ghagiel -- supernova dispersing
# ---------------------------------------------------------------------------
def _ghagiel(color: str = "#aaaaaa") -> str:
    fragments = []
    for i in range(20):
        angle = math.radians(i * 18)
        r = 60 + (i % 4) * 20
        r2 = r + 30 + (i % 3) * 20
        x1 = 256 + r * math.cos(angle)
        y1 = 256 + r * math.sin(angle)
        x2 = 256 + r2 * math.cos(angle)
        y2 = 256 + r2 * math.sin(angle)
        op = 0.15 + (i % 5) * 0.06
        fragments.append(
            f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{color}" stroke-width="2" stroke-opacity="{op:.2f}"/>'
        )
        dot_r = 2 + (i % 3)
        fragments.append(
            f'    <circle cx="{x2:.1f}" cy="{y2:.1f}" r="{dot_r}" '
            f'fill="{color}" fill-opacity="{op:.2f}"/>'
        )
    for i in range(16):
        angle = math.radians(i * 22.5 + 9)
        r = 150 + (i % 3) * 25
        x = 256 + r * math.cos(angle)
        y = 256 + r * math.sin(angle)
        op = 0.08 + (i % 4) * 0.03
        fragments.append(
            f'    <circle cx="{x:.1f}" cy="{y:.1f}" r="1.5" '
            f'fill="{color}" fill-opacity="{op:.2f}"/>'
        )
    fragments_str = "\n".join(fragments)
    body = textwrap.dedent(f"""\
      <g filter="url(#glow-ghagiel)" opacity="0.42">
        <!-- radiating fragments -->
    {fragments_str}
        <!-- core explosion rings -->
        <circle cx="256" cy="256" r="35" fill="{color}" fill-opacity="0.12"
                stroke="{color}" stroke-width="2"/>
        <circle cx="256" cy="256" r="20" fill="{color}" fill-opacity="0.20"
                stroke="{color}" stroke-width="1.5"/>
        <circle cx="256" cy="256" r="8" fill="{color}" fill-opacity="0.35"/>
        <!-- shockwave ring -->
        <circle cx="256" cy="256" r="140" fill="none"
                stroke="{color}" stroke-width="1" stroke-opacity="0.12"
                stroke-dasharray="6 8"/>
      </g>
    """)
    return _svg_header("ghagiel", color) + body + _svg_footer()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

GENERATORS: dict[str, tuple[Callable[[str], str], str]] = {
    "lilith": (_lilith, "#886644"),
    "gamaliel": (_gamaliel, "#9966cc"),
    "samael": (_samael, "#ffb000"),
    "aarab_zaraq": (_aarab_zaraq, "#88aa88"),
    "thagirion": (_thagirion, "#ffcc00"),
    "golachab": (_golachab, "#cc3333"),
    "gamchicoth": (_gamchicoth, "#4488cc"),
    "hatehom": (_hatehom, "#555555"),
    "satariel": (_satariel, "#2244aa"),
    "ghagiel": (_ghagiel, "#aaaaaa"),
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate 10 qliphoth SVG fallback files (512x512)."
    )
    parser.add_argument("--scene", "-s", help="Generate only this scene")
    parser.add_argument("--list", "-l", action="store_true", help="List scene names")
    args = parser.parse_args()

    if args.list:
        for name, (_, color) in GENERATORS.items():
            print(f"  {name:16s}  {color}")
        return

    OUTPUT.mkdir(parents=True, exist_ok=True)

    if args.scene:
        if args.scene not in GENERATORS:
            print(f"  ERROR: unknown scene '{args.scene}'", file=sys.stderr)
            print(
                f"  Available: {', '.join(GENERATORS.keys())}", file=sys.stderr
            )
            sys.exit(1)
        targets = {args.scene: GENERATORS[args.scene]}
    else:
        targets = GENERATORS

    total = len(targets)
    for i, (name, (gen_fn, color)) in enumerate(targets.items(), 1):
        out_path = OUTPUT / f"{name}.svg"
        svg_content = gen_fn(color)
        out_path.write_text(svg_content, encoding="utf-8")
        size = len(svg_content)
        print(f"  [{i:2d}/{total}] {name:16s} -> {out_path.name}  ({size:,} bytes)")

    print(f"\nDone. {total} SVGs written to {OUTPUT}/")


if __name__ == "__main__":
    main()
