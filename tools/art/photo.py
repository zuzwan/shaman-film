#!/usr/bin/env python3
"""Portraits from reference photos: crop, shrink, quantise to the palette with
Bayer dither, mask out the background, then cut expression states by editing
the eye and mouth regions.

    python tools/art/photo.py            # writes auk_close.yaml and teal_close.yaml

The references are drew's (assets/ref/). The sprite is the source of truth
afterwards; regions (eyes, mouth) are in sprite pixels and are set by hand
below after looking at the quantised result.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine.palette import RGB  # noqa: E402
from raster import Canvas, write_sprite  # noqa: E402

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16


def quantise(img, names, gamma=1.0, contrast=1.0, lift=0.0):
    """RGB array -> array of palette names, dithering between the two nearest colours."""
    pal = np.array([RGB[n] for n in names], dtype=np.float32)
    px = img.astype(np.float32)
    # tone curve on luminance, applied to all channels
    lum = (0.3 * px[..., 0] + 0.59 * px[..., 1] + 0.11 * px[..., 2]) / 255
    t = np.clip(((lum - 0.5) * contrast + 0.5 + lift), 0, 1) ** gamma
    scale = np.where(lum > 1e-3, t / np.maximum(lum, 1e-3), 1.0)
    px = np.clip(px * scale[..., None], 0, 255)
    H, W = px.shape[:2]
    d = ((px[:, :, None, :] - pal[None, None, :, :]) ** 2).sum(-1)  # H W P
    order = np.argsort(d, axis=-1)
    a, b = order[..., 0], order[..., 1]
    da = np.take_along_axis(d, a[..., None], -1)[..., 0] ** 0.5
    db = np.take_along_axis(d, b[..., None], -1)[..., 0] ** 0.5
    frac = da / np.maximum(da + db, 1e-6)  # 0 = exactly colour a
    thr = np.tile(BAYER, (H // 4 + 1, W // 4 + 1))[:H, :W]
    pick = np.where(thr < frac * 0.9, b, a)
    return np.array(names, dtype=object)[pick]


def ellipse_mask(H, W, cx, cy, rx, ry):
    yy, xx = np.mgrid[0:H, 0:W]
    return ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 <= 1


def to_canvas(names, mask):
    H, W = names.shape
    c = Canvas(W, H)
    for y in range(H):
        for x in range(W):
            if mask[y, x]:
                c.px[y][x] = names[y, x]
    return c


class Face:
    """A quantised portrait plus the regions needed to cut expressions."""

    def __init__(self, base, eyes, mouth, brow_y, skin):
        self.base = base          # Canvas
        self.eyes = eyes          # list of (x0, y0, x1, y1) boxes, the open eye incl. lids
        self.mouth = mouth        # (x0, y0, x1, y1)
        self.brow_y = brow_y
        self.skin = skin          # palette name for painted lids

    def copy(self):
        c = Canvas(self.base.w, self.base.h)
        c.px = [row[:] for row in self.base.px]
        return c

    def shift(self, c, dy):
        out = Canvas(c.w, c.h)
        for y in range(c.h):
            for x in range(c.w):
                v = c.px[y][x]
                if v is not None:
                    out.put(x, y + dy, v)
        return out

    def close_eyes(self, c, amount=1.0):
        """The lid comes down over the eye: the top `amount` of the box takes the
        cheek's texture (mirrored up from below the box), with a lash line at its edge."""
        for x0, y0, x1, y1 in self.eyes:
            h = y1 - y0
            n = int(round(h * amount))
            if n <= 0:
                continue
            for x in range(x0, x1):
                for y in range(y0, y0 + n):
                    src = c.px[min(c.h - 1, y1 + 1 + (y - y0))][x] or self.skin
                    c.px[y][x] = {"ink0": self.skin, "bone": "ash4"}.get(src, src)
            for x in range(x0 + 2, x1 - 2):
                c.px[y0 + n - 1][x] = "ink0" if amount >= 1 else "ink1"
        return c

    def gaze(self, c, dx):
        for x0, y0, x1, y1 in self.eyes:
            row = [c.px[y][x0:x1] for y in range(y0, y1)]
            for i, y in enumerate(range(y0, y1)):
                src = row[i]
                for j, x in enumerate(range(x0, x1)):
                    k = j - dx
                    c.px[y][x] = src[min(max(k, 0), len(src) - 1)]
        return c

    def mouth_open(self, c, h):
        x0, y0, x1, y1 = self.mouth
        # the chin drops: rows below the mouth slide down by h, the gap is dark
        for x in range(x0, x1):
            col = [c.px[y][x] for y in range(c.h)]
            for y in range(c.h - 1, y1 - 1, -1):
                src = y - h
                c.px[y][x] = col[src] if src >= y1 else None
            for y in range(y1 - 1, y1 - 1 + h):
                if y < c.h and not ((x < x0 + 2 or x >= x1 - 2) and (y == y1 - 1 or y == y1 - 2 + h)):
                    c.px[y][x] = "ink0"
            if h >= 4 and x0 + 3 <= x < x1 - 3:
                c.px[y1][x] = "ash3"  # teeth
        # fill the hole left under the chin shift with the lowest row of the face
        for x in range(x0, x1):
            for y in range(c.h - h, c.h):
                if c.px[y][x] is None and c.px[y - h][x] is not None:
                    c.px[y][x] = c.px[y - h][x]
        return c

    def brow(self, c, amount):
        """Darken or lift the brow line: negative = angry (press down and darken)."""
        for x0, y0, x1, y1 in self.eyes:
            for x in range(x0 - 1, x1 + 1):
                if amount < 0:
                    for y in range(self.brow_y, y0 - 1):
                        if c.px[y][x] not in (None, "ink0"):
                            c.px[y][x] = {"ash5": "ash3", "ash4": "ash2", "ash3": "ash1", "ash2": "ash0", "ash1": "ink2", "ash0": "ink1", "bone": "ash4"}.get(c.px[y][x], c.px[y][x])
                else:
                    y = self.brow_y - 1
                    if 0 <= y < c.h and c.px[y][x] is not None:
                        c.px[y][x] = {"ash1": "ash2", "ash2": "ash3", "ash0": "ash1", "ink2": "ash0"}.get(c.px[y][x], c.px[y][x])
        return c

    def states(self):
        F = self
        idle = [F.copy(), F.shift(F.copy(), -1), F.copy(), F.close_eyes(F.copy(), 1.0)]
        speak = [F.mouth_open(F.copy(), 2), F.mouth_open(F.shift(F.copy(), -1), 4), F.mouth_open(F.copy(), 5), F.mouth_open(F.copy(), 2)]
        return {
            "idle": idle,
            "speak": speak,
            "glare": [F.brow(F.close_eyes(F.copy(), 0.35), -1)],
            "flinch": [F.shift(F.brow(F.close_eyes(F.copy(), 1.0), 1), 2)],
            "look_down": [F.shift(F.close_eyes(F.copy(), 0.6), 2)],
            "look_away": [F.gaze(F.copy(), -3), F.gaze(F.shift(F.copy(), -1), -3)],
            "closed": [F.shift(F.close_eyes(F.copy(), 1.0), 1)],
            "grim": [F.brow(F.close_eyes(F.copy(), 0.2), -1)],
        }


GREYS = ["ink0", "ink1", "ink2", "ash0", "ash1", "ash2", "ash3", "ash4", "ash5", "bone"]


def build_auk():
    im = Image.open(ROOT / "assets/ref/auk_face.png").convert("RGB")
    im = im.crop((30, 0, 570, 700)).resize((96, 124), Image.LANCZOS)
    arr = np.array(im)
    names = quantise(arr, GREYS, gamma=1.15, contrast=1.1, lift=-0.04)
    H, W = names.shape
    # mask: head egg plus the hood and shoulders; the bokeh background goes
    m = ellipse_mask(H, W, 48, 52, 36, 50)
    yy, xx = np.mgrid[0:H, 0:W]
    m |= (yy > 78) & (xx > 6 - (yy - 78) * 0.3) & (xx < 90 + (yy - 78) * 0.3)
    m |= (yy > 100)
    c = to_canvas(names, m)
    # the hood: everything outside the face but inside the mask reads darker, like cloth
    for y in range(H):
        for x in range(W):
            v = c.px[y][x]
            if v is None:
                continue
            in_face = ((x - 48) / 32) ** 2 + ((y - 56) / 46) ** 2 <= 1
            if not in_face and y < 96:
                c.px[y][x] = {"ash5": "ash1", "ash4": "ash0", "ash3": "ash0", "ash2": "ink2", "ash1": "ink1", "ash0": "ink1", "bone": "ash1"}.get(v, v)
    for y in range(112, H):  # the hoodie's grommet goes; plain cloth at the bottom
        for x in range(W):
            if c.px[y][x] is not None:
                c.px[y][x] = "ink1"
    c.outline("ink0")
    return Face(c, eyes=[(27, 45, 44, 52), (54, 43, 73, 50)], mouth=(34, 84, 62, 88), brow_y=38, skin="ash1")


def build_teal():
    im = Image.open(ROOT / "assets/ref/teal_face.png").convert("RGB")
    im = im.crop((60, 0, 360, 390)).resize((88, 114), Image.LANCZOS)
    arr = np.array(im)
    names = quantise(arr, GREYS + ["rust0", "rust1", "blood3", "blood4"], gamma=1.25, contrast=1.0, lift=-0.06)
    H, W = names.shape
    m = ellipse_mask(H, W, 46, 42, 40, 50)
    yy, xx = np.mgrid[0:H, 0:W]
    m |= (yy > 72) & (xx > 14 - (yy - 72) * 0.4) & (xx < 78 + (yy - 72) * 0.4)
    c = to_canvas(names, m)
    # hair: the painting's bright highlights read as grey hair; pull them down
    for y in range(H):
        for x in range(W):
            v = c.px[y][x]
            in_face = ((x - 46) / 24) ** 2 + ((y - 50) / 34) ** 2 <= 1
            if v is not None and not in_face and y < 84:
                c.px[y][x] = {"bone": "ash3", "ash5": "ash2", "ash4": "ash1", "ash3": "ash0", "blood4": "rust1", "blood3": "rust0"}.get(v, v)
    # the painted collar and coat below the jaw are not our world: a scarf and a jacket instead
    for y in range(70, H):
        for x in range(W):
            if c.px[y][x] is not None and (y >= 86 or x < 28 or x > 64):
                c.px[y][x] = None
    c.poly([(0, 104), (10, 90), (44, 86), (80, 90), (88, 102), (88, H), (0, H)], "ash0", shade=("ink2", "ash0", (1, -0.3), 2.5))
    c.poly([(4, 118), (14, 118), (40, 92), (34, 90)], "rust0")
    c.poly([(8, 78), (30, 82), (46, 84), (62, 82), (80, 78), (84, 90), (74, 100), (44, 104), (12, 100), (4, 90)], "rust1", shade=("rust0", "rust1", (1, -0.5), 2))
    c.stroke(12, 90, 74, 92, "rust0", 1); c.stroke(10, 96, 70, 98, "rust0", 1)
    c.outline("ink0")
    return Face(c, eyes=[(27, 43, 42, 49), (52, 42, 67, 48)], mouth=(37, 69, 59, 73), brow_y=35, skin="ash2")


if __name__ == "__main__":
    out = ROOT / "assets/sprites"
    for name, builder, anchor in (("auk_close", build_auk, (48, 123)), ("teal_close", build_teal, (44, 113))):
        f = builder()
        write_sprite(out / f"{name}.yaml", name,
                     f"# {name}: from drew's reference photo (assets/ref/), quantised to the palette by\n"
                     "# tools/art/photo.py; expressions cut from the eye and mouth regions. Faces camera.",
                     anchor, 4, f.states())
        print(name, f.base.w, f.base.h)
