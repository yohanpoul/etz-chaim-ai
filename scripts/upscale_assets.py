#!/usr/bin/env python3
"""
Upscale web assets with Real-ESRGAN x4plus.

Generates @2x and @4x variants alongside the originals for use with HTML srcset.
Originals are backed up to web/static/_originals/ on first run.

Usage:
    scripts/upscale_assets.py --files avatars/samael.png
    scripts/upscale_assets.py --dirs systeme avatars
    scripts/upscale_assets.py --dirs avatars --limit 1 --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STATIC = REPO / "web" / "static"
ORIG = STATIC / "_originals"
MODEL_DIR = REPO / ".upscale-venv" / "weights"
MODEL_URL = "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth"
MODEL_PATH = MODEL_DIR / "RealESRGAN_x4plus.pth"


def ensure_model() -> Path:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if MODEL_PATH.exists():
        return MODEL_PATH
    print(f"[dl] model → {MODEL_PATH.name}")
    t0 = time.time()
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print(f"[dl] done in {time.time() - t0:.1f}s ({MODEL_PATH.stat().st_size / 1e6:.1f} MB)")
    return MODEL_PATH


def load_upscaler():
    import torch
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer

    model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    half = False
    up = RealESRGANer(
        scale=4,
        model_path=str(ensure_model()),
        model=model,
        tile=512,
        tile_pad=32,
        pre_pad=0,
        half=half,
        device=device,
    )
    print(f"[model] loaded on {device}, tile=512")
    return up


def backup_original(src: Path) -> None:
    rel = src.relative_to(STATIC)
    dst = ORIG / rel
    if dst.exists():
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"[backup] {rel} → _originals/")


def upscale_one(up, src: Path, scales=(2, 4), dry_run=False) -> None:
    import numpy as np
    from PIL import Image

    stem = src.with_suffix("")
    targets = {s: Path(f"{stem}@{s}x.png") for s in scales}
    need = [s for s, p in targets.items() if not p.exists()]
    if not need:
        print(f"[skip] {src.name} — all variants exist")
        return

    if dry_run:
        print(f"[dry] would upscale {src.name} → {[targets[s].name for s in need]}")
        return

    backup_original(src)

    t0 = time.time()
    img = Image.open(src).convert("RGB")
    arr = np.array(img)
    print(f"[run] {src.name} ({img.width}×{img.height}) → x4 ...")
    out4, _ = up.enhance(arr, outscale=4)
    Image.fromarray(out4).save(targets[4], optimize=True)
    print(
        f"[out] {targets[4].name} ({out4.shape[1]}×{out4.shape[0]}, "
        f"{targets[4].stat().st_size / 1e6:.2f} MB)"
    )

    if 2 in need:
        img4 = Image.fromarray(out4)
        img2 = img4.resize((img.width * 2, img.height * 2), Image.LANCZOS)
        img2.save(targets[2], optimize=True)
        print(
            f"[out] {targets[2].name} ({img2.width}×{img2.height}, "
            f"{targets[2].stat().st_size / 1e6:.2f} MB)"
        )

    print(f"[time] {time.time() - t0:.1f}s total")


def collect(dirs: list[str] | None, files: list[str] | None) -> list[Path]:
    out: list[Path] = []
    if files:
        for f in files:
            p = STATIC / f
            if not p.exists():
                print(f"[warn] not found: {f}", file=sys.stderr)
                continue
            out.append(p)
    if dirs:
        for d in dirs:
            root = STATIC / d
            for p in sorted(root.rglob("*.png")):
                name = p.name
                # skip already-upscaled variants + backed up originals
                if "@" in name or "_originals" in p.parts:
                    continue
                out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dirs", nargs="+", help="subdirs under web/static/ to scan")
    ap.add_argument("--files", nargs="+", help="specific files under web/static/")
    ap.add_argument("--scales", nargs="+", type=int, default=[2, 4])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.dirs and not args.files:
        ap.error("specify --dirs or --files")

    targets = collect(args.dirs, args.files)
    if args.limit:
        targets = targets[: args.limit]

    print(f"[plan] {len(targets)} image(s) to process")
    if not targets:
        return

    up = None if args.dry_run else load_upscaler()
    for i, src in enumerate(targets, 1):
        print(f"\n── [{i}/{len(targets)}] {src.relative_to(STATIC)}")
        upscale_one(up, src, scales=tuple(args.scales), dry_run=args.dry_run)

    print(f"\n[done] {len(targets)} image(s)")


if __name__ == "__main__":
    main()
