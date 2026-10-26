#!/usr/bin/env python3
"""Extract high-quality seamless hyprbars titlebar tiles from hyprframes Gemini borders.

For each source JPEG (square frame on black):
  1. Detect the top border band (non-black fringe).
  2. Crop the full top strip (decorative banner).
  3. Find the best-matching seamless horizontal tile period in the rail.
  4. Emit PNG tiles into examples/titlebars/ (and ~/.local share).

Requires: Pillow, numpy (use a venv if needed).
"""
from __future__ import annotations

import argparse
import re
import shutil
import struct
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
# Sibling package: Packages/hyprframes/borders
DEFAULT_SRC = HERE.parent.parent / "hyprframes" / "borders"
OUT = HERE / "titlebars"
SHARE = Path.home() / ".local/share/neuronix/hyprbars/titlebars"

# Friendly names in source order (sorted by gemini filename).
NAMES = [
    "scales-teal",       # 9a4xf9 — dragon scales
    "rune-iron",         # hxih9x — orange runes / rivets
    "hexmesh-cyan",      # i3ixy3 — sci-fi hex glow
    "stone-runes",       # l59ck6 — red runes on stone
    "rivet-copper",      # ngleyt — steampunk rivets
    "forge-orange",      # pnc1pn — orange glow industrial
    "bark-green",        # syr0n2 — bioluminescent wood
    "neon-bezel",        # yiawgw — orange neon rounded
    "plasma-violet",     # ythnx6 — electric blue/purple
]


def luminance(rgb: np.ndarray) -> np.ndarray:
    """rgb …x3 uint8 → float luminance."""
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def detect_top_thickness(arr: np.ndarray, black_thr: float = 18.0) -> int:
    """Return height of the top border band in pixels."""
    h, w, _ = arr.shape
    # Center third — ignore ornate corner flares that stick out.
    x0, x1 = w // 3, 2 * w // 3
    band = arr[:, x0:x1, :]
    lum = luminance(band).mean(axis=1)
    # From top: still "content" while mean lum is above black.
    thick = 0
    for y, v in enumerate(lum):
        if v > black_thr:
            thick = y + 1
        elif thick > 8 and y > thick + 4:
            break
    # Clamp to sane titlebar heights.
    if thick < 24:
        # Fallback: first deep black run in center column.
        mid = luminance(arr[:, w // 2, :])
        for y, v in enumerate(mid):
            if v < black_thr and y > 16:
                thick = y
                break
    return int(np.clip(thick, 32, min(280, h // 3)))


def crop_top_strip(arr: np.ndarray, thick: int) -> np.ndarray:
    h, w, _ = arr.shape
    # Trim a few px of outer margin if the art has a soft black halo.
    y0 = 0
    # Skip leading near-black rows at the very top (letterbox).
    lum = luminance(arr[:thick, w // 4 : 3 * w // 4, :]).mean(axis=1)
    for y, v in enumerate(lum):
        if v > 12:
            y0 = max(0, y - 1)
            break
    strip = arr[y0:thick, :, :].copy()
    return strip


def trim_side_black(strip: np.ndarray, thr: float = 14.0) -> np.ndarray:
    """Drop left/right columns that are almost pure black."""
    lum = luminance(strip).mean(axis=0)
    alive = np.where(lum > thr)[0]
    if alive.size < 8:
        return strip
    pad = 2
    a = max(0, int(alive[0]) - pad)
    b = min(strip.shape[1], int(alive[-1]) + pad + 1)
    return strip[:, a:b, :]


def best_tile_period(strip: np.ndarray, min_p: int = 48, max_p: int = 256) -> tuple[int, int]:
    """Return (start_x, period) for the most seamless horizontal tile in the rail.

    Searches the left-of-center rail (avoids unique center plaques) and scores
    periods by left/right edge agreement + mid-rail self-similarity.
    """
    h, w, _ = strip.shape
    # Prefer the left rail between ~12% and ~38% of width (after left corner).
    x0 = int(w * 0.12)
    x1 = int(w * 0.38)
    if x1 - x0 < min_p * 2:
        x0, x1 = int(w * 0.08), int(w * 0.45)
    rail = strip[:, x0:x1, :].astype(np.float32)
    rh, rw, _ = rail.shape
    max_p = min(max_p, rw // 2)
    min_p = min(min_p, max_p - 8)
    if max_p <= min_p:
        return x0, max(32, rw // 3)

    # Downsample vertically for speed.
    step = max(1, rh // 32)
    sample = rail[::step, :, :]

    best = (1e18, x0, min_p)
    for p in range(min_p, max_p + 1):
        # Compare columns 0..p with columns p..2p inside the rail.
        if 2 * p > rw:
            break
        a = sample[:, :p, :]
        b = sample[:, p : 2 * p, :]
        # Edge seam: last 4 cols of a vs first 4 of b (circular).
        edge = 4 if p >= 16 else 2
        seam = np.mean((a[:, -edge:, :] - b[:, :edge, :]) ** 2)
        body = np.mean((a - b) ** 2)
        # Prefer periods near 64–128 (nice for bar_height ~36).
        pref = 0.0001 * abs(p - 96)
        score = body + 2.5 * seam + pref
        if score < best[0]:
            best = (score, x0, p)

    # Also try right rail (symmetric art).
    x0r = int(w * 0.62)
    x1r = int(w * 0.88)
    rail_r = strip[:, x0r:x1r, :].astype(np.float32)
    rw = rail_r.shape[1]
    sample_r = rail_r[::step, :, :]
    max_p_r = min(max_p, rw // 2)
    for p in range(min_p, max_p_r + 1):
        if 2 * p > rw:
            break
        a = sample_r[:, :p, :]
        b = sample_r[:, p : 2 * p, :]
        edge = 4 if p >= 16 else 2
        seam = np.mean((a[:, -edge:, :] - b[:, :edge, :]) ** 2)
        body = np.mean((a - b) ** 2)
        pref = 0.0001 * abs(p - 96)
        score = body + 2.5 * seam + pref
        if score < best[0]:
            best = (score, x0r, p)

    return best[1], best[2]


def make_seamless(tile: np.ndarray, blend: int | None = None) -> np.ndarray:
    """Crossfade left/right edges so GL_REPEAT has no hard seam."""
    h, w, c = tile.shape
    if blend is None:
        blend = max(4, min(24, w // 8))
    if blend * 2 >= w:
        blend = max(2, w // 6)
    out = tile.astype(np.float32).copy()
    left = tile[:, :blend, :].astype(np.float32)
    right = tile[:, -blend:, :].astype(np.float32)
    for i in range(blend):
        t = (i + 0.5) / blend  # 0 at left edge of blend zone on the right side
        # Soft cosine ramp
        t = 0.5 - 0.5 * np.cos(np.pi * t)
        # Mix right edge toward left content, and left edge toward right content.
        out[:, w - blend + i, :] = (1 - t) * right[:, i, :] + t * left[:, i, :]
        out[:, i, :] = (1 - t) * left[:, i, :] + t * right[:, i, :]
    return np.clip(out, 0, 255).astype(np.uint8)


def enhance_strip(strip: np.ndarray) -> np.ndarray:
    """Mild sharpen + contrast for crisp titlebars at ~36–48px height."""
    im = Image.fromarray(strip, "RGB")
    # Slight unsharp for scale/rivet detail when downscaled by compositor.
    im = im.filter(ImageFilter.UnsharpMask(radius=1.2, percent=120, threshold=2))
    arr = np.asarray(im).astype(np.float32)
    # Gentle contrast around mean (keep blacks).
    mean = arr.mean()
    arr = (arr - mean) * 1.08 + mean
    return np.clip(arr, 0, 255).astype(np.uint8)


def save_png(path: Path, rgb: np.ndarray) -> None:
    """Write RGB or RGBA PNG via Pillow."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if rgb.shape[2] == 3:
        Image.fromarray(rgb, "RGB").save(path, "PNG", optimize=True)
    else:
        Image.fromarray(rgb, "RGBA").save(path, "PNG", optimize=True)


def to_rgba_opaque(rgb: np.ndarray) -> np.ndarray:
    a = np.full((*rgb.shape[:2], 1), 255, dtype=np.uint8)
    return np.concatenate([rgb, a], axis=2)


def extract_one(src: Path, name: str, out_dir: Path) -> dict:
    im = Image.open(src).convert("RGB")
    arr = np.asarray(im)
    thick = detect_top_thickness(arr)
    strip = crop_top_strip(arr, thick)
    strip = trim_side_black(strip)
    strip = enhance_strip(strip)

    # Full top banner (center motif + rails) — good at bar_image_scale that fits height.
    banner = strip
    # Also a mid-height crop focused on the densest detail band (skip outer black fringe).
    h = strip.shape[0]
    y_a = max(0, int(h * 0.05))
    y_b = min(h, int(h * 0.95))
    core = strip[y_a:y_b, :, :]

    start, period = best_tile_period(core)
    tile = core[:, start : start + period, :].copy()
    tile = make_seamless(tile)

    # Upscale 2× with LANCZOS when source border is soft / for retina bars.
    def up2(a: np.ndarray) -> np.ndarray:
        im2 = Image.fromarray(a, "RGB")
        im2 = im2.resize((a.shape[1] * 2, a.shape[0] * 2), Image.Resampling.LANCZOS)
        return np.asarray(im2)

    tile_hi = up2(tile)
    banner_hi = up2(core)

    # If banner is very wide, also emit a compact "plaque" center crop (~3× period).
    bw = core.shape[1]
    cx = bw // 2
    half = min(period * 2, bw // 4)
    plaque = core[:, max(0, cx - half) : min(bw, cx + half), :].copy()
    plaque_hi = up2(plaque)

    base = out_dir / f"titlebar-{name}"
    paths = {
        "tile": base.with_name(base.name + "-tile.png"),
        "banner": base.with_name(base.name + "-banner.png"),
        "plaque": base.with_name(base.name + "-plaque.png"),
    }
    save_png(paths["tile"], to_rgba_opaque(tile_hi))
    save_png(paths["banner"], to_rgba_opaque(banner_hi))
    save_png(paths["plaque"], to_rgba_opaque(plaque_hi))

    return {
        "name": name,
        "source": src.name,
        "border_px": thick,
        "tile": f"{paths['tile'].name} {tile_hi.shape[1]}x{tile_hi.shape[0]}",
        "banner": f"{paths['banner'].name} {banner_hi.shape[1]}x{banner_hi.shape[0]}",
        "plaque": f"{paths['plaque'].name} {plaque_hi.shape[1]}x{plaque_hi.shape[0]}",
        "period": period,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--src",
        type=Path,
        default=DEFAULT_SRC,
        help="Directory with Gemini_Generated_Image_*.jpeg",
    )
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--share", action="store_true", help=f"Also copy to {SHARE}")
    args = ap.parse_args()

    srcs = sorted(args.src.glob("Gemini_Generated_Image_*.jpeg"))
    if not srcs:
        raise SystemExit(f"No Gemini_Generated_Image_*.jpeg in {args.src}")

    args.out.mkdir(parents=True, exist_ok=True)
    print(f"source={args.src}  out={args.out}  count={len(srcs)}")

    results = []
    for i, src in enumerate(srcs):
        name = NAMES[i] if i < len(NAMES) else f"frame-{i+1:02d}"
        # Keep a stable short id from the gemini hash too.
        m = re.search(r"Gemini_Generated_Image_([a-z0-9]{6})", src.name)
        tag = m.group(1) if m else f"{i:02d}"
        full_name = f"{i+1:02d}-{name}"
        info = extract_one(src, full_name, args.out)
        info["tag"] = tag
        results.append(info)
        print(
            f"  {full_name}: border={info['border_px']}px period={info['period']} "
            f"→ {info['tile']}"
        )

    # Index README
    readme = args.out / "README.md"
    lines = [
        "# hyprbars titlebar textures",
        "",
        "Extracted from `hyprframes/borders/Gemini_Generated_Image_*.jpeg`.",
        "",
        "Each set has:",
        "- `*-tile.png` — seamless horizontal repeat (best for `bar_image`)",
        "- `*-banner.png` — full top border strip (motif + rails)",
        "- `*-plaque.png` — center ornament crop",
        "",
        "Apply with the picker or:",
        "",
        "```bash",
        "hyprctl keyword plugin:hyprbars:bar_image /path/to/titlebar-01-scales-teal-tile.png",
        "hyprctl keyword plugin:hyprbars:bar_image_opacity 1.0",
        "hyprctl keyword plugin:hyprbars:bar_image_scale 1.0",
        "```",
        "",
        "| # | name | tile |",
        "|---|------|------|",
    ]
    for r in results:
        lines.append(f"| {r['name']} | {r['source']} | `{r['tile']}` |")
    lines.append("")
    lines.append("Regenerate:")
    lines.append("")
    lines.append("```bash")
    lines.append("python3 extract_titlebars.py --share")
    lines.append("```")
    readme.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if args.share:
        SHARE.mkdir(parents=True, exist_ok=True)
        for p in args.out.glob("titlebar-*.png"):
            shutil.copy2(p, SHARE / p.name)
        shutil.copy2(readme, SHARE / "README.md")
        print(f"copied → {SHARE}")

    print(f"done ({len(results)} sets) → {args.out}")


if __name__ == "__main__":
    main()
