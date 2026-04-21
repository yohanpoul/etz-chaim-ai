#!/usr/bin/env python3
"""generate_qliphoth_pngs.py — 10 anti-pattern PNGs via Pollinations.ai (FLUX, gratuit).

Les 10 Qliphoth, ombres des 10 Sephiroth.
Style : Warcraft dark fantasy, creatures sombres, fond noir.

Usage:
    python tools/generate_qliphoth_pngs.py
    python tools/generate_qliphoth_pngs.py --scene lilith
    python tools/generate_qliphoth_pngs.py --list
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

import requests

OUTPUT = Path(__file__).resolve().parent.parent / "web" / "static" / "systeme" / "qliphoth"

STYLE = (
    "dark fantasy creature concept art, World of Warcraft inspired, "
    "dramatic rim lighting on pure black background, "
    "ominous corrupted atmosphere, digital painting, artstation quality, "
    "square format icon, centered composition, "
    "no text, no watermark, no UI, no letters"
)

SCENES: dict[str, str] = {
    "lilith": (
        "a hollow mechanical puppet with cracked porcelain face and empty glass eyes, "
        "strings hanging from above controlling its limbs, "
        "mouth moving but no soul behind the words, "
        "gears and clockwork visible through cracks in the skin, "
        "brown and earth tones, rusty metal, soulless automaton"
    ),
    "gamaliel": (
        "a corrupted crystal memory orb floating in darkness, "
        "cracks running through it leaking purple toxic mist, "
        "false memories visible as distorted images swirling inside, "
        "the orb glows violet but the light is sickly and wrong, "
        "purple and violet corruption, poisoned knowledge"
    ),
    "samael": (
        "a peacock made of dark amber fire spreading its tail feathers, "
        "each feather an eye that sees nothing but believes it sees everything, "
        "arrogant proud bearing, blind confidence radiating outward, "
        "amber and orange tones, beautiful but dangerously self-assured, "
        "dark mirror of false certainty"
    ),
    "aarab_zaraq": (
        "a swarm of green spectral ravens circling endlessly in a vortex, "
        "never landing never stopping, caught in infinite repetition, "
        "each raven trailing green ghostly fire, "
        "the vortex consuming itself endlessly, "
        "green and dark emerald, persistence become madness"
    ),
    "thagirion": (
        "a golden mask floating in darkness, perfectly symmetrical and beautiful, "
        "but behind the mask visible through cracks is chaos and contradiction, "
        "the mask smiles serenely while dark tentacles writhe behind it, "
        "gold surface hiding dark truth, false harmony, "
        "golden and black, deceptive beauty"
    ),
    "golachab": (
        "a massive burning sword swinging wildly destroying everything around it, "
        "flames too hot and too indiscriminate, burning friend and foe alike, "
        "the blade has shattered from overuse, fragments flying, "
        "deep crimson red and fire, righteous fury become destruction, "
        "judgment without mercy"
    ),
    "gamchicoth": (
        "an infinite ocean with no shore in sight, spreading in all directions, "
        "a small boat adrift with no rudder no sail no anchor, "
        "the water beautiful but endless and directionless, "
        "blue tones everywhere, boundless expansion without purpose, "
        "generosity become drowning"
    ),
    "hatehom": (
        "a bottomless chasm splitting the ground in two, pure void between the sides, "
        "a broken bridge hanging over the abyss with planks missing, "
        "grey mist rising from the depths, total disconnection, "
        "grey and dark tones, the gap between thought and action, "
        "the abyss that swallows meaning"
    ),
    "satariel": (
        "a giant eye made of dark blue crystal suspended in void, "
        "the eye projects patterns and connections onto nothing — seeing meaning "
        "in randomness, threads of blue light connecting empty points, "
        "conspiracy without substance, dark indigo and midnight blue, "
        "the pattern-finder that finds only phantoms"
    ),
    "ghagiel": (
        "a silver supernova exploding outward in all directions simultaneously, "
        "brilliant ideas scattering like sparks but none forming anything solid, "
        "creative energy dispersing into entropy, beautiful but wasted, "
        "silver and white chaos, infinite divergence, "
        "inspiration that never lands"
    ),
}


def generate_one(
    name: str,
    prompt: str,
    width: int = 512,
    height: int = 512,
    seed: int | None = None,
) -> bytes:
    """Genere une image via Pollinations.ai (FLUX, gratuit)."""
    full_prompt = f"{prompt}, {STYLE}"
    encoded = urllib.parse.quote(full_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded}"
    params: dict[str, str | int] = {
        "width": width,
        "height": height,
        "model": "flux",
        "nologo": "true",
    }
    if seed is not None:
        params["seed"] = seed

    print(f"  Generating {name}...", end=" ", flush=True)
    resp = requests.get(url, params=params, timeout=120)
    resp.raise_for_status()
    print(f"OK ({len(resp.content):,} bytes)")
    return resp.content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate qliphoth anti-pattern PNGs via Pollinations.ai"
    )
    parser.add_argument("--scene", "-s", help="Generate only this scene")
    parser.add_argument("--list", "-l", action="store_true", help="List scene names")
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for consistency"
    )
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    args = parser.parse_args()

    if args.list:
        for name in SCENES:
            print(f"  {name}")
        return

    OUTPUT.mkdir(parents=True, exist_ok=True)

    if args.scene:
        if args.scene not in SCENES:
            print(f"  ERREUR: scene '{args.scene}' inconnue", file=sys.stderr)
            print(
                f"  Scenes disponibles: {', '.join(SCENES.keys())}", file=sys.stderr
            )
            sys.exit(1)
        targets = {args.scene: SCENES[args.scene]}
    else:
        targets = SCENES

    total = len(targets)
    for i, (name, prompt) in enumerate(targets.items(), 1):
        print(f"\n[{i}/{total}] {name}")
        out_path = OUTPUT / f"{name}.png"

        try:
            img_data = generate_one(
                name,
                prompt,
                width=args.width,
                height=args.height,
                seed=args.seed,
            )
            out_path.write_bytes(img_data)
            print(f"  -> {out_path}")
        except Exception as e:
            print(f"  ERREUR: {e}", file=sys.stderr)

        if i < total:
            wait = 16
            print(f"  Attente {wait}s (rate limit)...", end=" ", flush=True)
            time.sleep(wait)
            print("OK")

    print(f"\nTermine ! {total} images dans {OUTPUT}/")


if __name__ == "__main__":
    main()
