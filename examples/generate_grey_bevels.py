#!/usr/bin/env python3
"""Titlebar tiles matching the grey hyprframes bevels.

The bar is 36px tall. Each tile is that height, so bar_image_scale 1 fills
it once. The light edge is the top of the bar; the shadow is the bottom.
The profile does not change along the bar, so the tile repeats cleanly.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hyprframes" / "borders"))

import bevel_frame
import grey_bevels
import grey_frame
from generate_tiles import write_png

OUT = Path(__file__).resolve().parent
SHARE = Path.home() / ".local/share/neuronix/hyprbars"
# Matches plugin:hyprbars:bar_height.
BAR_H = 36
BAR_W = 64

PROFILES = (
    ("tile-grey-round.png", grey_frame.shade, "Round bar. Soft highlight on the outer shoulder."),
    ("tile-grey-bevel.png", bevel_frame.shade, "Stepped bevel. Hard outer light, flat face, inner shadow."),
    ("tile-grey-ridge.png", grey_bevels.ridge, "Ridge. Highlight on the crest."),
    ("tile-grey-cove.png", grey_bevels.cove, "Cove. Lit lips, dark hollow."),
    ("tile-grey-bead.png", grey_bevels.bead, "Double bead. Two highlights and a dark slot."),
)


def render(profile) -> bytes:
    px = bytearray(BAR_W * BAR_H * 4)
    for y in range(BAR_H):
        r, g, b = profile((y + 0.5) / BAR_H)
        R, G, B = int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
        row = bytes((R, G, B, 255)) * BAR_W
        px[y * BAR_W * 4 : (y + 1) * BAR_W * 4] = row
    return bytes(px)


def main() -> None:
    SHARE.mkdir(parents=True, exist_ok=True)
    for name, profile, _blurb in PROFILES:
        raw = render(profile)
        write_png(OUT / name, BAR_W, BAR_H, raw)
        (SHARE / name).write_bytes((OUT / name).read_bytes())


if __name__ == "__main__":
    main()
