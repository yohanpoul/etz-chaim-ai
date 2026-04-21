#!/usr/bin/env python3
"""generate_extra_pngs.py — 18 images supplementaires via Pollinations.ai (FLUX, gratuit).

1 hero banner (/systeme index)
4 banners de sous-pages (personnages, arbre, mondes, erreurs)
8 sentiers (chemins entre Sephiroth, affichés dans L'Arbre)
5 scenes d'actes (headers des 5 groupes de personnages)

Style : Warcraft dark fantasy, eclairage dramatique, fond noir.
Zero inscription, zero API key.

Usage:
    python tools/generate_extra_pngs.py
    python tools/generate_extra_pngs.py --scene hero_systeme
    python tools/generate_extra_pngs.py --list
    python tools/generate_extra_pngs.py --category banners
    python tools/generate_extra_pngs.py --category sentiers
    python tools/generate_extra_pngs.py --category actes
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent / "web" / "static"

# ═══════════════════════════════════════════════════════════
#  Styles globaux
# ═══════════════════════════════════════════════════════════

STYLE_BANNER = (
    "wide panoramic scene, no people, no characters, "
    "dark fantasy environment concept art, World of Warcraft inspired, "
    "dramatic atmospheric lighting, epic scale, pure black edges vignette, "
    "digital matte painting, artstation quality, ultra wide cinematic composition, "
    "no text, no watermark, no UI, no letters, no words"
)

STYLE_SENTIER = (
    "mystical symbolic concept art, centered single object on pure black background, "
    "dark fantasy, kabbalistic mysticism, glowing golden light, "
    "dramatic rim lighting, highly detailed, digital painting, artstation quality, "
    "no text, no watermark, no UI, no letters, no words, no characters"
)

STYLE_ACTE = (
    "wide scene, dark fantasy environment concept art, World of Warcraft inspired, "
    "dramatic lighting, deep shadows, pure black background vignette, "
    "digital painting, artstation quality, cinematic wide composition, "
    "no text, no watermark, no UI, no letters, no words"
)

# ═══════════════════════════════════════════════════════════
#  SCENES — toutes les images a generer
# ═══════════════════════════════════════════════════════════

# (prompt, style, output_dir, width, height)
SceneDef = tuple[str, str, str, int, int]

SCENES: dict[str, SceneDef] = {
    # ── BANNERS (1 hero + 4 sous-pages) ──────────────────
    "hero_systeme": (
        "majestic dark throne room with a glowing golden tree of life floating above "
        "an ancient altar, ten luminous orbs connected by golden light paths arranged "
        "in the kabbalistic tree pattern, the tree radiates warm amber and gold light "
        "into the vast dark cathedral space, twenty shadowy figures standing in "
        "attendance around the altar in a semicircle, "
        "epic scale, sense of ancient sacred wisdom",
        STYLE_BANNER,
        "systeme/banners", 1200, 500,
    ),
    "banner_personnages": (
        "grand dark throne room seen from above, twenty ornate chairs arranged in "
        "five concentric semicircles around a central golden throne, each chair "
        "has a faintly glowing emblem above it, warm amber candlelight, "
        "sense of a royal court awaiting its members, "
        "ceremonial and hierarchical arrangement, bird eye view",
        STYLE_BANNER,
        "systeme/banners", 1200, 400,
    ),
    "banner_arbre": (
        "a massive ancient tree made of pure golden light growing from dark earth "
        "into infinite darkness above, ten glowing orbs of different colors nested "
        "in its branches like luminous fruit, golden veins of light running through "
        "the trunk connecting all orbs, roots deep in dark soil, "
        "the tree of life as a living structure of light",
        STYLE_BANNER,
        "systeme/banners", 1200, 400,
    ),
    "banner_mondes": (
        "four distinct horizontal layers of reality stacked vertically, "
        "top layer pure golden abstract light, second layer deep blue cosmic nebula, "
        "third layer emerald green enchanted forest, bottom layer brown rocky earth, "
        "each layer bleeds into the next through misty transitions, "
        "four worlds from divine to material, stacked cosmology",
        STYLE_BANNER,
        "systeme/banners", 1200, 400,
    ),
    "banner_erreurs": (
        "a beautiful golden shell cracking open from within, dark red corruption "
        "seeping through the fractures, the shell was once perfect but excess force "
        "has broken it from inside, amber light fighting against dark red shadow, "
        "the boundary between order and chaos, balance disrupted, "
        "dramatic contrast between gold perfection and red corruption",
        STYLE_BANNER,
        "systeme/banners", 1200, 400,
    ),

    # ── SENTIERS (8 chemins entre Sephiroth) ─────────────
    "sentier_tav": (
        "an ancient ornate wax seal stamp pressing into golden wax, "
        "the seal imprint glowing with mystical light, "
        "the moment of sealing a sacred document, "
        "brown and gold tones, earthly and permanent, "
        "the final letter, completion and signature",
        STYLE_SENTIER,
        "systeme/sentiers", 512, 512,
    ),
    "sentier_resh": (
        "a blazing golden sun emerging from absolute darkness, "
        "rays of intense warm light piercing through shadow, "
        "the sun reveals hidden shapes in the darkness below, "
        "pure gold and amber radiance against black void, "
        "illumination, revelation, the head that sees",
        STYLE_SENTIER,
        "systeme/sentiers", 512, 512,
    ),
    "sentier_qof": (
        "the back of an ancient stone head statue seen from behind, "
        "the occiput glowing with hidden inner light seeping through cracks, "
        "mysterious knowledge stored in the unconscious back of the mind, "
        "grey stone with amber light bleeding through fractures, "
        "what persists unseen, the hidden drive",
        STYLE_SENTIER,
        "systeme/sentiers", 512, 512,
    ),
    "sentier_tsade": (
        "a lone figure silhouette standing perfectly balanced between "
        "two massive opposing forces — a wall of red fire on the left "
        "and a wall of blue water on the right, the figure holds both at bay, "
        "the narrow path between extremes, gold and amber silhouette, "
        "the righteous one who holds the balance",
        STYLE_SENTIER,
        "systeme/sentiers", 512, 512,
    ),
    "sentier_peh": (
        "a massive ornate golden mouth sculpture floating in void, "
        "the mouth is open and speaking — visible sound waves of golden light "
        "emanating outward like ripples, the power of spoken judgment, "
        "gold and amber against pure black, "
        "the word that cuts, declaration and decree",
        STYLE_SENTIER,
        "systeme/sentiers", 512, 512,
    ),
    "sentier_yod": (
        "a single infinitely small point of brilliant white-gold light "
        "floating in absolute darkness, from this point thin golden rays "
        "begin to extend outward like the very first moment of creation, "
        "the smallest letter, the initial spark, "
        "pure white gold point against infinite black void",
        STYLE_SENTIER,
        "systeme/sentiers", 512, 512,
    ),
    "sentier_heh": (
        "an ornate gothic window frame floating in darkness, "
        "through the window pours structured blue-white light "
        "that takes geometric shapes as it passes through the frame, "
        "the window gives form to formless light, "
        "deep blue and silver, the frame that shapes understanding",
        STYLE_SENTIER,
        "systeme/sentiers", 512, 512,
    ),
    "sentier_aleph": (
        "a single breath of wind made visible as a spiral of golden mist "
        "in absolute darkness, the first exhalation before any word, "
        "silent and primordial, barely visible but immensely powerful, "
        "the faintest golden vapor against pure black, "
        "the silent letter, breath before speech, origin of all",
        STYLE_SENTIER,
        "systeme/sentiers", 512, 512,
    ),

    # ── SCENES D'ACTES (5 groupes de personnages) ────────
    "acte_cour": (
        "a dark royal court with five ornate thrones arranged in a pyramid, "
        "the highest throne in shadows at the back for the ancient king, "
        "two thrones at mid-level for father and mother figures, "
        "two thrones at front for the young prince and the queen, "
        "warm amber torchlight, ceremonial and hierarchical, "
        "empty thrones waiting for their occupants, gold and purple",
        STYLE_ACTE,
        "systeme/actes", 768, 300,
    ),
    "acte_gardiens": (
        "four massive ornate gates at the four cardinal directions of a dark citadel, "
        "each gate has a distinct style — gold shield gate, amber lantern gate, "
        "green healing gate, dark iron judgment gate, "
        "the gates form a protective perimeter around a central light, "
        "defensive architecture, guardian stations, no figures",
        STYLE_ACTE,
        "systeme/actes", 768, 300,
    ),
    "acte_officiers": (
        "a dark war room with four distinct workstations arranged around "
        "a central illuminated map table, one station has scrolls and a quill, "
        "another has keys hanging on a wall, a third has a magnifying glass, "
        "the fourth has ledgers and red-marked folders, "
        "organized efficient command center, blue and silver tones",
        STYLE_ACTE,
        "systeme/actes", 768, 300,
    ),
    "acte_veilleurs": (
        "three stations in a dark nocturnal watchtower, one station has "
        "a lit lantern and a checklist scroll, another has a meditation cushion "
        "with faint thought bubbles rising, the third has a stack of red folders "
        "and a quill, moonlight streaming through narrow windows, "
        "night watch atmosphere, green and silver tones, vigilant and quiet",
        STYLE_ACTE,
        "systeme/actes", 768, 300,
    ),
    "acte_ame": (
        "three ethereal flames floating in darkness — left flame is deep crimson red "
        "and wild and pulling downward, right flame is pure white-gold and rising upward, "
        "center flame is amber and human-sized caught between the two forces, "
        "the eternal battle between animal impulse and divine aspiration, "
        "the middle flame flickers between red and gold, dramatic tension",
        STYLE_ACTE,
        "systeme/actes", 768, 300,
    ),
}


def generate_one(
    name: str,
    prompt: str,
    style: str,
    width: int = 768,
    height: int = 512,
    seed: int | None = None,
) -> bytes:
    """Genere une image via Pollinations.ai (FLUX, gratuit)."""
    full_prompt = f"{prompt}, {style}"
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
    resp = requests.get(url, params=params, timeout=180)
    resp.raise_for_status()
    print(f"OK ({len(resp.content):,} bytes)")
    return resp.content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate extra PNGs (banners, sentiers, actes) via Pollinations.ai"
    )
    parser.add_argument("--scene", "-s", help="Generate only this scene")
    parser.add_argument("--list", "-l", action="store_true", help="List scene names")
    parser.add_argument(
        "--category",
        "-c",
        choices=["banners", "sentiers", "actes"],
        help="Generate only one category",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for consistency"
    )
    args = parser.parse_args()

    if args.list:
        print("\n  Banners (5):")
        for name in SCENES:
            if name.startswith(("hero_", "banner_")):
                print(f"    {name}")
        print("\n  Sentiers (8):")
        for name in SCENES:
            if name.startswith("sentier_"):
                print(f"    {name}")
        print("\n  Actes (5):")
        for name in SCENES:
            if name.startswith("acte_"):
                print(f"    {name}")
        return

    # Filter by category or scene
    if args.scene:
        if args.scene not in SCENES:
            print(f"  ERREUR: scene '{args.scene}' inconnue", file=sys.stderr)
            sys.exit(1)
        targets = {args.scene: SCENES[args.scene]}
    elif args.category:
        prefix_map = {
            "banners": ("hero_", "banner_"),
            "sentiers": ("sentier_",),
            "actes": ("acte_",),
        }
        prefixes = prefix_map[args.category]
        targets = {k: v for k, v in SCENES.items() if k.startswith(prefixes)}
    else:
        targets = SCENES

    total = len(targets)
    for i, (name, (prompt, style, out_dir, w, h)) in enumerate(targets.items(), 1):
        print(f"\n[{i}/{total}] {name} ({w}x{h})")
        out_path = BASE / out_dir / f"{name}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            img_data = generate_one(name, prompt, style, width=w, height=h, seed=args.seed)
            out_path.write_bytes(img_data)
            print(f"  -> {out_path}")
        except Exception as e:
            print(f"  ERREUR: {e}", file=sys.stderr)

        # Rate limit : 16s entre chaque requete (anonyme)
        if i < total:
            wait = 16
            print(f"  Attente {wait}s (rate limit)...", end=" ", flush=True)
            time.sleep(wait)
            print("OK")

    print(f"\nTermine ! {total} images generees.")


if __name__ == "__main__":
    main()
