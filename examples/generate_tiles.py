#!/usr/bin/env python3
"""Generate colorful seamless bar_image test tiles for Neuronix hyprbars."""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).resolve().parent


def write_png(path: Path, w: int, h: int, pixels: bytes) -> None:
    """pixels: raw RGBA top-to-bottom, length w*h*4."""

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = b"".join(b"\x00" + pixels[y * w * 4 : (y + 1) * w * 4] for y in range(h))
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)
    print(f"wrote {path.name} ({w}x{h}, {path.stat().st_size} bytes)")


def clamp(v: float) -> int:
    return max(0, min(255, int(round(v))))


def rgba(r: float, g: float, b: float, a: float = 255) -> bytes:
    return bytes([clamp(r), clamp(g), clamp(b), clamp(a)])


def tile_shapes() -> None:
    """48×24: circles, diamonds, bars — bright opaque."""
    w, h = 48, 24
    px = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            # teal base
            r, g, b = 20, 90 + (x * 2) % 40, 110 + (y * 3) % 30
            # vertical candy stripe
            if x % 12 < 3:
                r, g, b = 220, 80, 60
            # circle
            cx, cy, rad = 14, 12, 7
            if (x - cx) ** 2 + (y - cy) ** 2 <= rad * rad:
                r, g, b = 255, 210, 40
            # diamond
            if abs(x - 36) + abs(y - 12) <= 6:
                r, g, b = 80, 200, 255
            # top/bottom rail
            if y < 2 or y >= h - 2:
                r, g, b = 255, 255, 255
            px[(y * w + x) * 4 : (y * w + x) * 4 + 4] = rgba(r, g, b, 255)
    write_png(OUT / "tile-shapes.png", w, h, bytes(px))


def tile_dots() -> None:
    """32×32: polka dots on purple, opaque."""
    w = h = 32
    px = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            r, g, b = 70, 40, 120
            for cx, cy, col in ((8, 8, (255, 100, 160)), (24, 8, (100, 220, 140)), (8, 24, (255, 200, 60)), (24, 24, (100, 180, 255))):
                if (x - cx) ** 2 + (y - cy) ** 2 <= 5 * 5:
                    r, g, b = col
            px[(y * w + x) * 4 : (y * w + x) * 4 + 4] = rgba(r, g, b, 255)
    write_png(OUT / "tile-dots.png", w, h, bytes(px))


def tile_chevrons() -> None:
    """40×20: chevron arrows, opaque."""
    w, h = 40, 20
    px = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            phase = (x + y) % 20
            if phase < 8:
                r, g, b = 40, 160, 90
            elif phase < 12:
                r, g, b = 255, 255, 255
            else:
                r, g, b = 30, 60, 140
            # center stripe
            if abs(y - h // 2) <= 1:
                r, g, b = 255, 120, 40
            px[(y * w + x) * 4 : (y * w + x) * 4 + 4] = rgba(r, g, b, 255)
    write_png(OUT / "tile-chevrons.png", w, h, bytes(px))


def tile_grid_alpha() -> None:
    """36×18: colored cells with some transparent gaps (tests alpha)."""
    w, h = 36, 18
    px = bytearray(w * h * 4)
    colors = [
        (230, 70, 70),
        (70, 200, 90),
        (70, 120, 230),
        (230, 200, 50),
        (200, 80, 200),
        (50, 200, 200),
    ]
    cell = 6
    for y in range(h):
        for x in range(w):
            cx, cy = x // cell, y // cell
            # every other cell transparent
            if (cx + cy) % 2 == 1:
                px[(y * w + x) * 4 : (y * w + x) * 4 + 4] = rgba(0, 0, 0, 0)
            else:
                r, g, b = colors[(cx + cy * 3) % len(colors)]
                px[(y * w + x) * 4 : (y * w + x) * 4 + 4] = rgba(r, g, b, 220)
    write_png(OUT / "tile-grid-alpha.png", w, h, bytes(px))


def tile_waves() -> None:
    """64×24: sine-wave bands."""
    w, h = 64, 24
    px = bytearray(w * h * 4)
    for y in range(h):
        for x in range(w):
            wave = math.sin(x * 0.35) * 5 + math.sin(x * 0.11 + 1.2) * 3
            band = y - (h / 2 + wave)
            if abs(band) < 2.5:
                r, g, b = 255, 90, 40
            elif band < 0:
                t = y / h
                r, g, b = 30 + 40 * t, 50 + 80 * t, 140 + 60 * t
            else:
                t = y / h
                r, g, b = 40 + 100 * t, 160 - 40 * t, 70
            px[(y * w + x) * 4 : (y * w + x) * 4 + 4] = rgba(r, g, b, 255)
    write_png(OUT / "tile-waves.png", w, h, bytes(px))


def main() -> None:
    tile_shapes()
    tile_dots()
    tile_chevrons()
    tile_grid_alpha()
    tile_waves()
    # Grey bevels matching the hyprframes bars. Imported lazily so a missing
    # frames tree does not break the colorful tiles.
    try:
        import generate_grey_bevels
        generate_grey_bevels.main()
    except Exception as exc:
        print("grey bevels skipped:", exc)
    print("done →", OUT)


if __name__ == "__main__":
    main()
