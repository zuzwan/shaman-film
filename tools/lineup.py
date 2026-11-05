#!/usr/bin/env python3
"""Sprite contact sheet: every frame of every state, for review before a sprite
enters the library.

    python tools/lineup.py                    # all sprites -> out/lineup.png
    python tools/lineup.py shaman rig         # just these
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.palette import RGB  # noqa: E402
from engine.sprites import load  # noqa: E402

S, PAD, LABEL = 6, 6, 14
BGS = ["sky2", "night1"]  # each frame shown on a light and a dark ground


def main(names):
    names = names or sorted(p.stem for p in Path("assets/sprites").glob("*.yaml"))
    rows = []
    for n in names:
        spr = load(n)
        frames = [(st, i, f) for st, fs in spr.states.items() for i, f in enumerate(fs)]
        rows.append((n, frames))
    cell_w = max(f[2][1].shape[1] for _, fr in rows for f in fr) * S + PAD
    cell_h = max(f[2][1].shape[0] for _, fr in rows for f in fr) * S + PAD
    cols = max(len(fr) for _, fr in rows) * len(BGS)
    sheet = Image.new("RGB", (cols * cell_w + 120, len(rows) * (cell_h + LABEL)), (20, 19, 17))
    d = ImageDraw.Draw(sheet)
    for r, (n, frames) in enumerate(rows):
        y = r * (cell_h + LABEL)
        d.text((4, y + LABEL + cell_h // 2), n, fill=(190, 184, 170))
        for b, bg in enumerate(BGS):
            for c, (st, i, (rgb, alpha)) in enumerate(frames):
                x = 120 + (b * len(frames) + c) * cell_w
                tile = Image.new("RGB", (cell_w - PAD, cell_h - PAD), tuple(RGB[bg]))
                im = Image.fromarray(rgb).resize((rgb.shape[1] * S, rgb.shape[0] * S), Image.NEAREST)
                m = Image.fromarray(alpha.astype("uint8") * 255).resize(im.size, Image.NEAREST)
                tile.paste(im, (0, tile.height - im.height), m)
                sheet.paste(tile, (x, y + LABEL))
                if b == 0:
                    d.text((x, y + 2), f"{st} {i}", fill=(150, 144, 130))
    Path("out").mkdir(exist_ok=True)
    sheet.save("out/lineup.png")
    print("out/lineup.png")


if __name__ == "__main__":
    main(sys.argv[1:])
