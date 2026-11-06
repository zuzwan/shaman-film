#!/usr/bin/env python3
"""Sprite sheet for review: one row per state, frames across, on a mid ground.

    python tools/sheet.py auk_med            # -> out/sheet_auk_med.png
    python tools/sheet.py auk --scale 6
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.palette import RGB  # noqa: E402
from engine.sprites import load  # noqa: E402


def main(argv):
    scale = 4
    if "--scale" in argv:
        i = argv.index("--scale")
        scale = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    for name in argv:
        spr = load(name)
        h, w = next(iter(spr.states.values()))[0][1].shape
        cols = max(len(f) for f in spr.states.values())
        cw, ch = w * scale + 4, h * scale + 4
        sheet = Image.new("RGB", (80 + cols * cw, len(spr.states) * (ch + 12)), (20, 19, 17))
        d = ImageDraw.Draw(sheet)
        for r, (st, frames) in enumerate(spr.states.items()):
            y = r * (ch + 12) + 10
            d.text((4, y + ch // 2), st, fill=(190, 184, 170))
            for c, (rgb, alpha) in enumerate(frames):
                x = 80 + c * cw
                tile = Image.new("RGB", (w * scale, h * scale), tuple(int(v) for v in RGB["sky1"]))
                im = Image.fromarray(rgb).resize((w * scale, h * scale), Image.NEAREST)
                m = Image.fromarray((alpha * 255).astype("uint8")).resize((w * scale, h * scale), Image.NEAREST)
                tile.paste(im, (0, 0), m)
                sheet.paste(tile, (x, y))
        out = Path("out") / f"sheet_{name}.png"
        out.parent.mkdir(exist_ok=True)
        sheet.save(out)
        print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
