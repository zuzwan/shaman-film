"""Display lettering for the show title: big carved capitals, drawn as polygons.

Woodcut capitals 32 px tall: thick and thin strokes, wedge serifs, an S
drawn as a swelling stroke. Only the letters the title needs are drawn; add
a glyph here (polygons in a 32-unit box, holes listed separately) to set
other words. `mask(text, scale)` returns the lettering as a boolean array,
`carve(canvas, m, x, y, ...)` paints it lit from the top left with an ink
outline and drop shadow. Everything is whole pixels; tones mix by Bayer
dither only.
"""
import numpy as np

from .dither import threshold
from .palette import RGB

CAP = 32
GAP = 4          # between letters, at scale 1

# name: (advance width, [polygons], [holes], [strokes]); a stroke is [(x, y, radius), ...]
GLYPHS = {
    "T": (26, [[(0, 0), (26, 0), (26, 9), (23, 5), (16, 5), (16, 28), (19, 32), (7, 32), (10, 28), (10, 5),
                (3, 5), (0, 9)]], [], []),
    "H": (28, [[(0, 0), (12, 0), (9, 3), (9, 29), (12, 32), (0, 32), (3, 29), (3, 3)],
               [(16, 0), (28, 0), (25, 3), (25, 29), (28, 32), (16, 32), (19, 29), (19, 3)],
               [(9, 13), (19, 13), (19, 18), (9, 18)]], [], []),
    "E": (23, [[(0, 0), (23, 0), (23, 8), (20, 4), (9, 4), (9, 14), (15, 14), (16, 11), (16, 21), (15, 18),
                (9, 18), (9, 28), (20, 28), (23, 23), (23, 32), (0, 32), (3, 29), (3, 3)]], [], []),
    "S": (24, [[(19, 0), (23, 0), (23, 9), (20, 9)], [(1, 23), (4, 23), (4, 32), (1, 32)]], [],
          [[(21, 6, 1.6), (18, 2.5, 2.0), (12, 1.8, 2.2), (6, 3, 2.6), (3.5, 8, 3.0), (6, 13.5, 3.2),
            (12, 16, 3.4), (18, 19, 3.2), (20.5, 24, 3.0), (18, 29.5, 2.6), (12, 30.6, 2.2),
            (6, 29.5, 2.0), (3, 26, 1.6)]]),
    "A": (30, [[(12, 0), (18, 0), (27, 29), (30, 32), (19, 32), (21, 29), (19, 23), (10, 23), (8, 29), (10, 32),
                (0, 32), (3, 29)]], [[(15, 7), (11, 18), (18, 18)]], []),
    "M": (36, [[(0, 0), (10, 0), (18, 19), (26, 0), (36, 0), (33, 3), (33, 29), (36, 32), (24, 32), (27, 29),
                (27, 11), (19, 32), (16, 32), (8, 11), (8, 29), (11, 32), (1, 32), (4, 29), (4, 3)]], [], []),
    "N": (30, [[(0, 0), (9, 0), (22, 21), (22, 3), (19, 0), (30, 0), (27, 3), (27, 32), (22, 32), (8, 11),
                (8, 29), (11, 32), (0, 32), (3, 29), (3, 3)]], [], []),
    " ": (12, [], [], []),
}


def _poly_mask(pts, h, w, s, ox):
    ys, xs = np.mgrid[0:h, 0:w]
    px, py = (xs + 0.5) / s - ox, (ys + 0.5) / s
    inside = np.zeros((h, w), dtype=bool)
    n = len(pts)
    for i in range(n):
        (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
        if y0 == y1:
            continue
        cross = ((y0 > py) != (y1 > py)) & (px < (x1 - x0) * (py - y0) / (y1 - y0) + x0)
        inside ^= cross
    return inside


def _stroke_mask(pts, h, w, s, ox, steps=12):
    ys, xs = np.mgrid[0:h, 0:w]
    px, py = (xs + 0.5) / s - ox, (ys + 0.5) / s
    m = np.zeros((h, w), dtype=bool)
    for (x0, y0, r0), (x1, y1, r1) in zip(pts, pts[1:]):
        for k in range(steps + 1):
            f = k / steps
            cx, cy, r = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, r0 + (r1 - r0) * f
            m |= (px - cx) ** 2 + (py - cy) ** 2 <= r * r
    return m


def width(text, scale=1.0):
    adv = [GLYPHS[ch][0] for ch in text]
    return int(round((sum(adv) + GAP * (len(adv) - 1)) * scale))


def mask(text, scale=1.0, spacing=GAP):
    """The word as a boolean array, CAP * scale tall."""
    text = text.upper()
    h = int(round(CAP * scale))
    w = int(round((sum(GLYPHS[c][0] for c in text) + spacing * (len(text) - 1)) * scale)) + 1
    m = np.zeros((h, w), dtype=bool)
    ox = 0.0
    for ch in text:
        adv, polys, holes, strokes = GLYPHS[ch]
        g = np.zeros_like(m)
        for p in polys:
            g |= _poly_mask(p, h, w, scale, ox)
        for st in strokes:
            g |= _stroke_mask(st, h, w, scale, ox)
        for p in holes:
            g &= ~_poly_mask(p, h, w, scale, ox)
        m |= g
        ox += adv + spacing
    return m


def _shift(m, dy, dx):
    out = np.zeros_like(m)
    h, w = m.shape
    out[max(0, dy):h + min(0, dy), max(0, dx):w + min(0, dx)] = m[max(0, -dy):h - max(0, dy), max(0, -dx):w - max(0, dx)]
    return out


def carve(c, m, x, y, amount=1.0, ramp=("bone_hi", "bone", "ash4"), edge_hi="bone_hi", edge_lo="ash3",
          outline="ink0", shadow=2, reveal=None):
    """Paint mask `m` at (x, y): a dithered top-to-bottom ramp, light on the top-left
    edges, shade on the bottom-right, ink outline, drop shadow down-right.
    `amount` dithers the whole thing in; `reveal` (bool array like m) limits what shows."""
    H, W = c.shape[:2]
    h, w = m.shape
    pad = shadow + 2
    big = np.zeros((h + 2 * pad, w + 2 * pad), dtype=bool)
    big[pad:pad + h, pad:pad + w] = m if reveal is None else (m & reveal)
    x0, y0 = x - pad, y - pad
    # clip to the canvas
    sx0, sy0 = max(0, -x0), max(0, -y0)
    sx1, sy1 = min(big.shape[1], W - x0), min(big.shape[0], H - y0)
    if sx0 >= sx1 or sy0 >= sy1:
        return
    on = big & (threshold(*big.shape, x0, y0) < amount)
    grown = on.copy()
    for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        grown |= _shift(on, dy, dx)
    shadow_m = np.zeros_like(on)
    for k in range(1, shadow + 1):
        shadow_m |= _shift(grown, k, k)
    region = c[y0 + sy0:y0 + sy1, x0 + sx0:x0 + sx1]
    sl = (slice(sy0, sy1), slice(sx0, sx1))
    region[(shadow_m | grown)[sl]] = RGB[outline]
    # body: a vertical ramp in three bands, dithered at the seams
    fy = (np.arange(big.shape[0])[:, None] - pad) / max(1, h - 1)
    fy = np.broadcast_to(fy, big.shape)
    t = threshold(*big.shape, x0, y0)
    band = np.where(fy * 2 < 1 - 0.0, np.where(t < fy * 2, 1, 0), np.where(t < (fy - 0.5) * 2, 2, 1))
    for i, name in enumerate(ramp):
        region[(on & (band == i))[sl]] = RGB[name]
    lo = on & ~_shift(on, -1, -1)       # bottom-right edge
    hi = on & ~_shift(on, 1, 1)         # top-left edge
    region[lo[sl]] = RGB[edge_lo]
    region[hi[sl]] = RGB[edge_hi]
