#!/usr/bin/env python3
"""generate_systeme_pngs.py — 19 scene PNGs via Pollinations.ai (FLUX, gratuit).

11 salles (Sephiroth/L'Arbre), 4 paysages (Olamot/Les Mondes),
4 creatures/ombres (Qliphoth/Les Erreurs).

Style : Warcraft dark fantasy, eclairage dramatique, fond noir.
Zero inscription, zero API key.

Usage:
    python tools/generate_systeme_pngs.py
    python tools/generate_systeme_pngs.py --scene yesod      # une seule
    python tools/generate_systeme_pngs.py --list              # liste les noms
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

import requests

OUTPUT = Path(__file__).resolve().parent.parent / "web" / "static" / "systeme"

# Style global : Warcraft dark fantasy, pas de personnages, scenes vides
STYLE_ROOM = (
    "interior scene, no people, no characters, empty room, "
    "dark fantasy environment concept art, World of Warcraft inspired, "
    "dramatic lighting, deep shadows, pure black background vignette, "
    "highly detailed architecture and props, "
    "digital painting, artstation quality, cinematic composition, "
    "no text, no watermark, no UI"
)

STYLE_LANDSCAPE = (
    "wide landscape vista, no people, no characters, "
    "dark fantasy environment concept art, World of Warcraft inspired, "
    "dramatic atmospheric lighting, epic scale, pure black edges vignette, "
    "digital matte painting, artstation quality, cinematic composition, "
    "no text, no watermark, no UI"
)

STYLE_CREATURE = (
    "dark creature concept art, no people, "
    "dark fantasy horror, World of Warcraft inspired, "
    "dramatic rim lighting on pure black background, "
    "ominous atmosphere, digital painting, artstation quality, "
    "no text, no watermark, no UI"
)

# ═══════════════════════════════════════════════════════════
#  11 SEPHIROTH — salles interieures
# ═══════════════════════════════════════════════════════════

SCENES: dict[str, tuple[str, str]] = {
    # (prompt, style_suffix)

    # ── Sephiroth (salles) ──────────────────────────
    "malkuth": (
        "massive stone throne room, a grand throne at the center on a raised platform, "
        "the throne made of dark wood and iron with four distinct colored gemstones "
        "embedded in it — olive green, russet red, citrine yellow, and black onyx, "
        "representing the four elements, heavy stone columns, "
        "the floor is a mosaic of four colors in quadrants, "
        "torches casting warm light, the seat of the earthly kingdom, "
        "brown russet olive and black earth tones, grounded and regal",
        STYLE_ROOM,
    ),
    "yesod": (
        "vast magical library archive, towering bookshelves reaching into darkness above, "
        "ancient leather-bound books and scrolls everywhere, "
        "a central reading table with glowing purple crystal illumination, "
        "scattered parchments and quills, moonlight streaming from above, "
        "purple and violet tones, mystical atmosphere, "
        "arcane symbols faintly glowing on book spines",
        STYLE_ROOM,
    ),
    "hod": (
        "hall of mirrors and reflections, ornate golden framed mirrors on every wall, "
        "each mirror showing a slightly different reflection of the room, "
        "warm amber and golden light bouncing between surfaces, "
        "polished marble floor reflecting the ceiling, "
        "crystal chandeliers, self-referential infinite reflections, "
        "amber and gold color scheme",
        STYLE_ROOM,
    ),
    "netzach": (
        "lush overgrown enchanted greenhouse conservatory, "
        "dense tropical vines and flowering plants reclaiming ancient stone architecture, "
        "glowing green bioluminescent flowers and hanging gardens, "
        "a natural spring or small waterfall in the center, "
        "everything alive and growing and triumphant over stone, "
        "emerald green dominant with touches of copper and rose, "
        "the victory of nature over structure, Venus energy, sensual and alive",
        STYLE_ROOM,
    ),
    "tiferet": (
        "grand chamber of balance, a massive golden scale perfectly balanced in the center, "
        "one side glowing blue-white for mercy, the other glowing red for judgment, "
        "the room split down the middle between warm and cool tones, "
        "ornate pillars on both sides, golden sunlight from a high window, "
        "the heart of the palace, where all paths converge, "
        "gold and amber dominant with red and blue accents",
        STYLE_ROOM,
    ),
    "gevurah": (
        "dark forge and armory, massive anvil in the center glowing red-hot, "
        "chains hanging from the ceiling, weapon racks on the walls, "
        "molten metal in a crucible casting intense red-orange light, "
        "sparks flying, heat shimmer in the air, "
        "heavy iron and dark steel everywhere, "
        "deep red and crimson tones, the place where raw power is shaped",
        STYLE_ROOM,
    ),
    "chesed": (
        "grand observatory tower open to the night sky, "
        "massive arched windows revealing an infinite ocean below under starlight, "
        "a large ornate telescope pointing toward the heavens, "
        "flowing blue curtains, silver and blue tones, "
        "calm expansive feeling of infinite possibility, "
        "water and sky meeting at the horizon, moonlit waves",
        STYLE_ROOM,
    ),
    "daat": (
        "narrow stone bridge spanning a bottomless abyss, "
        "thick grey mist rising from below obscuring the depths, "
        "the bridge cracked and ancient with no railings, "
        "faint ghostly light from an unknown source, "
        "grey and silver tones, liminal space between worlds, "
        "vertigo-inducing perspective looking down into fog, "
        "mysterious and unsettling threshold",
        STYLE_ROOM,
    ),
    "binah": (
        "immense gothic cathedral interior, impossibly tall vaulted ceiling lost in shadow, "
        "massive stone columns with carved symbols, "
        "deep blue stained glass windows filtering dim light, "
        "a single altar at the far end barely visible, "
        "the space itself feels alive and thinking, "
        "deep blue and indigo tones, vast reverberating silence",
        STYLE_ROOM,
    ),
    "chokmah": (
        "domed stellar observatory, the dome cracked open revealing a spectacular starfield, "
        "silver astronomical instruments and orreries, "
        "constellations visible through the opening, "
        "lightning-like flashes of silver inspiration in the air, "
        "argent and platinum tones, cosmic wisdom, "
        "the first flash of an idea before it takes shape",
        STYLE_ROOM,
    ),
    "keter": (
        "transcendent space of pure brilliant WHITE light, almost abstract, "
        "a simple unadorned crown floating in absolute white radiance, "
        "no architecture visible, everything dissolved into pure white luminosity, "
        "the crown barely visible as a silhouette in blinding white light, "
        "PURE WHITE and silver only, no gold, no color, "
        "before all differentiation, the infinite point of origin, "
        "overwhelming white brilliance that erases all form",
        STYLE_ROOM,
    ),

    # ── Olamot (paysages) ──────────────────────────
    "atziluth": (
        "abstract realm of pure golden divine light, "
        "rays of brilliant gold and white emanating from a central point, "
        "no ground no sky just infinite luminous space, "
        "geometric sacred patterns forming and dissolving in the light, "
        "the highest plane of existence where thought is reality, "
        "overwhelming radiance, gold and white only",
        STYLE_LANDSCAPE,
    ),
    "briah": (
        "cosmic creation scene, deep blue nebula giving birth to new stars, "
        "swirling galaxies and stellar nurseries, "
        "brilliant points of light emerging from dark blue cosmic clouds, "
        "the moment of creation frozen in time, "
        "deep sapphire blue and silver starlight, "
        "vast cosmic scale, awe-inspiring stellar panorama",
        STYLE_LANDSCAPE,
    ),
    "yetzirah": (
        "enchanted dark forest at twilight, ancient massive trees with glowing green runes, "
        "mist rising from the forest floor, visible magical ley lines between trees, "
        "structures and patterns emerging from the organic chaos, "
        "bioluminescent mushrooms and plants, "
        "emerald green and forest tones, the realm where forms take shape",
        STYLE_LANDSCAPE,
    ),
    "assiah": (
        "rugged mountain landscape at dawn, solid rock formations and ancient paths, "
        "a winding stone road leading to a distant fortress, "
        "earth and amber tones, dust and gravel, "
        "the material world, solid and real and tangible, "
        "brown and amber warm tones, weathered and ancient terrain",
        STYLE_LANDSCAPE,
    ),

    # ── Qliphoth (creatures/ombres) ──────────────────
    "nogah": (
        "a cracked glowing shell or cocoon emitting amber light through fractures, "
        "the shell is beautiful but breaking apart, "
        "amber and gold light leaking through dark cracks, "
        "still partially luminous, corruption just beginning, "
        "the boundary between holy and profane, "
        "dark background with warm amber fissures of light",
        STYLE_CREATURE,
    ),
    "ruach": (
        "dark smoke entity spreading tendrils across the ground, "
        "formless shadow mass with orange-red embers glowing within, "
        "smoke and dark mist expanding outward, "
        "no distinct shape just spreading contamination, "
        "deep orange and dark red tones against pure black, "
        "corruption spreading like ink in water",
        STYLE_CREATURE,
    ),
    "anan": (
        "a massive thick dark cloud of impenetrable smoke and fog, "
        "dense opaque darkness that smothers and hides everything behind it, "
        "faint traces of light struggling and failing to penetrate, "
        "the cloud is alive and expanding, swallowing visibility, "
        "dark brown-red and grey tones, no figure no shape just FOG, "
        "the obscuring veil that hides truth, suffocating darkness",
        STYLE_CREATURE,
    ),
    "mamash": (
        "formless mass of absolute darkness with two burning red eyes, "
        "pure black void entity barely distinguishable from the background, "
        "tendrils of darkness reaching outward, consuming all light, "
        "the eyes are the only feature, ancient and malevolent, "
        "almost invisible, pure entropy and dissolution, "
        "black on black with crimson red eyes only",
        STYLE_CREATURE,
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
    resp = requests.get(url, params=params, timeout=120)
    resp.raise_for_status()
    print(f"OK ({len(resp.content):,} bytes)")
    return resp.content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate systeme scene PNGs via Pollinations.ai"
    )
    parser.add_argument("--scene", "-s", help="Generate only this scene")
    parser.add_argument("--list", "-l", action="store_true", help="List scene names")
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for consistency"
    )
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--height", type=int, default=512)
    args = parser.parse_args()

    if args.list:
        print("\n  Sephiroth (11 salles):")
        seph = [
            "malkuth",
            "yesod",
            "hod",
            "netzach",
            "tiferet",
            "gevurah",
            "chesed",
            "daat",
            "binah",
            "chokmah",
            "keter",
        ]
        for name in seph:
            print(f"    {name}")
        print("\n  Olamot (4 paysages):")
        for name in ["atziluth", "briah", "yetzirah", "assiah"]:
            print(f"    {name}")
        print("\n  Qliphoth (4 ombres):")
        for name in ["nogah", "ruach", "anan", "mamash"]:
            print(f"    {name}")
        return

    OUTPUT.mkdir(parents=True, exist_ok=True)

    if args.scene:
        if args.scene not in SCENES:
            print(f"  ERREUR: scene '{args.scene}' inconnue", file=sys.stderr)
            print(f"  Scenes disponibles: {', '.join(SCENES.keys())}", file=sys.stderr)
            sys.exit(1)
        targets = {args.scene: SCENES[args.scene]}
    else:
        targets = SCENES

    total = len(targets)
    for i, (name, (prompt, style)) in enumerate(targets.items(), 1):
        print(f"\n[{i}/{total}] {name}")
        out_path = OUTPUT / f"{name}.png"

        try:
            img_data = generate_one(
                name,
                prompt,
                style,
                width=args.width,
                height=args.height,
                seed=args.seed,
            )
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

    print(f"\nTermine ! {total} images dans {OUTPUT}/")


if __name__ == "__main__":
    main()
