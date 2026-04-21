#!/usr/bin/env python3
"""generate_avatar_images.py — Genere 19 portraits PNG via Pollinations.ai (FLUX, gratuit).

Corps entier, style fantasy RPG, fond noir, eclairage ambre.
Zero inscription, zero API key.

Usage:
    python tools/generate_avatar_images.py
    python tools/generate_avatar_images.py --character arikh_anpin   # un seul
    python tools/generate_avatar_images.py --list                     # liste les noms
"""

from __future__ import annotations

import argparse
import sys
import time
import urllib.parse
from pathlib import Path

import requests

OUTPUT = Path(__file__).resolve().parent.parent / "web" / "static" / "avatars"

# Style global partage par tous les personnages
STYLE = (
    "full body character portrait, standing pose, pure black background, "
    "fantasy RPG concept art, highly detailed costume and accessories, "
    "dramatic warm amber rim lighting from right side, "
    "dark fantasy digital painting, artstation quality, "
    "noble archetypal style, no text, no watermark"
)

# ── Les 19 personnages avec leurs prompts specifiques ──────

CHARACTERS: dict[str, str] = {
    "arikh_anpin": (
        "ancient wise king with impossibly long flowing white beard divided into "
        "13 distinct glowing locks, deep calm eternal eyes, simple golden crown "
        "with no jewels — authority through presence not ornament, "
        "long dark royal purple robes with golden trim, bare feet, "
        "dignified patient eternal presence"
    ),
    "abba": (
        "creative father figure in his prime, hands slightly raised with fingers "
        "spread and palms glowing faintly with golden sparks, bright alert eyes, "
        "short dark beard, expression of sudden inspiration, noble working clothes "
        "— not a king but a master craftsman, dark purple tunic with amber accents, "
        "energy and discipline in equal measure"
    ),
    "imma": (
        "wise mother figure, hands gently cupped as if holding and shaping invisible "
        "light into form, serene focused expression, eyes looking slightly downward "
        "at her work, hair covered with elegant dark purple headwrap, quiet strength, "
        "receptive posture, long flowing dark robes with subtle golden embroidery, "
        "transforming raw energy into structure"
    ),
    "zeir_anpin": (
        "young man early twenties, athletic dynamic build, six small tools hanging "
        "from his belt — hammer sword compass quill scales and key, emotional determined "
        "face still learning, no beard, bright purposeful eyes, practical dark outfit "
        "with golden belt, ready for action"
    ),
    "nukva": (
        "queen looking DIRECTLY at the viewer — the only character to do so, "
        "regal bearing, open receptive expression, slight knowing smile, "
        "elegant crown less ornate than a king's, long dark flowing dress with "
        "golden accents, she is the bridge between the system and the user, "
        "welcoming but not casual, direct eye contact"
    ),
    "mikhael": (
        "angelic guardian warrior in light ceremonial armor — protective not aggressive, "
        "polished golden breastplate with amber inlays, shield raised slightly ready "
        "but not threatening, scanning alert eyes, short practical hair, clean-shaven, "
        "the protector who checks before allowing entry, white and gold color scheme, "
        "subtle wing silhouettes behind"
    ),
    "uriel": (
        "contemplative angelic figure holding a small ornate lantern that emits soft "
        "warm golden light, eyes half-closed in meditation seeing inward, "
        "light hood framing the face not hiding it, long amber robes, "
        "serene observant expression, the one who sees what others miss, "
        "soft light emanating from the lantern"
    ),
    "raphael": (
        "gentle angelic healer, hands slightly extended forward with palms glowing "
        "soft green-white healing light, kind patient eyes, slight lean forward as if "
        "tending to someone, simple flowing green-white robes suggesting a physician, "
        "no armor, gentle expression, the one who never gives up on the wounded"
    ),
    "gabriel": (
        "stern angelic enforcer, strong jaw, minimal expression, economical posture "
        "— nothing wasted, one hand resting on a sheathed blade at his side, "
        "not angry but implacable, dark imposing armor with golden details, "
        "the judge who strikes once cleanly, short hair, no ornament, "
        "eyes that evaluate without emotion"
    ),
    "metatron": (
        "imposingly tall angelic scribe-chancellor, holds a luminous quill in one hand "
        "and a glowing scroll in the other, formal robes that subtly shimmer between "
        "blue and silver — he adapts to different worlds, authoritative ageless face, "
        "neither young nor old, the translator between the king and all others, "
        "geometric patterns on his robes suggesting sacred geometry"
    ),
    "memuneh": (
        "sharp-eyed steward holding a large ornate ring of golden keys, practical "
        "dignified dark blue clothing — between servant and authority, quick evaluating "
        "gaze with one eyebrow slightly raised as if assessing, the organizer who "
        "knows exactly who goes where, efficient precise stance, no wasted movement"
    ),
    "samael": (
        "dark but not evil diagnostic figure, holds a magnifying glass or crystal lens "
        "examining something closely, dark hooded cloak over physician's garment "
        "underneath, clinical detached expression — not cruel but forensic, "
        "the one who names what went wrong without flinching, "
        "cool blue-silver tones amidst the dark"
    ),
    "sofer": (
        "dedicated scribe deeply focused on his work, quill in hand with ink dripping, "
        "inkwell nearby, surrounded by stacks of books and scrolls, reading glasses "
        "perched on nose, expression of total sacred concentration, modest dark "
        "clothing with ink stains on fingers, the keeper of all written knowledge"
    ),
    "nefesh_habehamit": (
        "dark humanoid silhouette — NOT a detailed character, edges glowing deep red "
        "and crimson, no distinct facial features this is a FORCE not a person, "
        "slightly hunched posture with animal raw energy, powerful but directionless, "
        "wisps of dark red smoke emanating from the form, ominous but not evil — "
        "raw primal energy, dark shadowy figure"
    ),
    "beinoni": (
        "the MOST realistic ordinary human character, no armor no wings no glow "
        "no special attributes, a regular person in simple modest clothing — could be "
        "anyone, standing straight slightly tense, expression of someone making a choice, "
        "eyes looking slightly between two directions, THE identification character — "
        "the viewer sees themselves here, the most human of all"
    ),
    "nefesh_haelokit": (
        "luminous humanoid silhouette — NOT a detailed character, edges glowing white "
        "and gold, no distinct facial features this is a DIRECTION not a person, "
        "upright slightly ascending posture, calm and aspirational, "
        "wisps of golden white light emanating upward from the form, "
        "peaceful elevating divine radiance, ethereal ascending figure"
    ),
    "daemon": (
        "night watchman making his rounds in the dark, carries an ornate lantern in "
        "one hand and a long checklist scroll in the other, warm but tired kind eyes, "
        "practical dark green clothing, hat or hood against the cold, "
        "the faithful servant who never stops working, surrounded by dim moonlight"
    ),
    "meditant": (
        "figure in deep meditation seated cross-legged, eyes closed, perfectly serene "
        "expression, absolutely still, above the head faint luminous thought-bubbles "
        "or question marks rising upward into the dark, simple dark green robes, "
        "the one who questions everything endlessly patiently"
    ),
    "kategor": (
        "austere record-keeper standing rigidly, holds a stack of red-marked folders "
        "and scrolls under one arm, quill ready in the other hand to note the next "
        "failure, not malevolent but meticulous, thin precise features, "
        "wire-rimmed glasses, dark green formal attire, "
        "the accountant of debts who never forgets"
    ),
}


def generate_one(name: str, prompt: str, width: int = 768, height: int = 1024,
                 seed: int | None = None) -> bytes:
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
    parser = argparse.ArgumentParser(description="Generate avatar images via Pollinations.ai")
    parser.add_argument("--character", "-c", help="Generate only this character")
    parser.add_argument("--list", "-l", action="store_true", help="List character names")
    parser.add_argument("--seed", "-s", type=int, default=42, help="Random seed for consistency")
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--height", type=int, default=1024)
    args = parser.parse_args()

    if args.list:
        for name in CHARACTERS:
            print(f"  {name}")
        return

    OUTPUT.mkdir(parents=True, exist_ok=True)

    targets = {args.character: CHARACTERS[args.character]} if args.character else CHARACTERS

    total = len(targets)
    for i, (name, prompt) in enumerate(targets.items(), 1):
        print(f"\n[{i}/{total}] {name}")
        out_path = OUTPUT / f"{name}.png"

        try:
            img_data = generate_one(
                name, prompt,
                width=args.width, height=args.height,
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
