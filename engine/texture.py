"""Surface texture for the hyper-detailed style: every flat fill becomes a
dithered field of tones around its colour, driven by value noise. Nothing
here blends; it only picks neighbouring tones in the colour's own ramp and
lets Bayer settle the fractions, so the rules of the palette hold.

    texture(canvas, mask, "rock", ox=cam_x, seed=3)   # retone the masked pixels in place

Kinds: rock (ridges), earth (ground), cloud (sky), bark (trees, trunks),
stone (ruins, blocks and mortar), cloth (coats, cloaks), wool (heavy cloth),
skin, hair, leather, wood.
"""
import numpy as np

from .dither import threshold
from .palette import PALETTE, RGB

# tone ramps: a colour is retoned only within its family
FAMILIES = [
    ["ink0", "ink1", "ink2", "ash0", "ash1", "ash2", "ash3", "ash4", "ash5", "bone", "bone_hi"],
    ["sky0", "sky1", "sky2", "sky3"], ["cold0", "cold1", "cold2"], ["blood0", "rust0", "rust1", "blood3", "blood4"],
    ["moss0", "moss1"], ["night0", "night1", "night2", "night3"], ["mauve0", "mauve1", "mauve2", "mauve3", "mauve4"],
    ["tide0", "tide1", "tide2", "tide3", "tide4"], ["blood0", "blood1", "blood2", "blood3", "blood4"],
    ["fern0", "fern1", "fern2", "fern3", "fern4"], ["ember0", "ember1", "ember2", "flame"],
]
_FAMILY = {}
for fam in FAMILIES:
    for i, n in enumerate(fam):
        _FAMILY.setdefault(n, (fam, i))
_RGB2NAME = {tuple(int(v) for v in RGB[n]): n for n in PALETTE}

_NOISE = {}
UNIT = 1  # density (engine/units.py): features keep their size in the frame, drawn with more pixels


def _value_noise(h, w, scale_x, scale_y, seed, octaves=3):
    """Tileable-enough value noise in [-1, 1], cached by its parameters."""
    scale_x, scale_y = scale_x * UNIT, scale_y * UNIT
    key = (h, w, scale_x, scale_y, seed, octaves)
    if key in _NOISE:
        return _NOISE[key]
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for o in range(octaves):
        sx, sy = max(1.0, scale_x / (2 ** o)), max(1.0, scale_y / (2 ** o))
        gw, gh = int(w / sx) + 2, int(h / sy) + 2
        grid = rng.random((gh, gw), np.float32)
        xs = np.arange(w) / sx
        ys = np.arange(h) / sy
        x0, y0 = xs.astype(int), ys.astype(int)
        fx, fy = (xs - x0)[None, :], (ys - y0)[:, None]
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a = grid[y0][:, x0]
        b = grid[y0][:, x0 + 1]
        c = grid[y0 + 1][:, x0]
        d = grid[y0 + 1][:, x0 + 1]
        out += amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)
        total += amp
        amp *= 0.5
    out = (out / total - 0.5) * 2
    _NOISE[key] = out
    return out


def field(kind, h, w, ox=0, oy=0, seed=0):
    """A texture field in [-1, 1] over an (h, w) window at world offset (ox, oy)."""
    big_w = w + 2048
    ox = int(ox) % 2048
    yy, xx = np.mgrid[0:h, 0:w]
    if kind == "rock":
        n = _value_noise(h, big_w, 7, 5, seed, 3)[:, ox:ox + w]
        n = n * 0.8 + 0.4 * _value_noise(h, big_w, 24, 3, seed + 1, 1)[:, ox:ox + w]
    elif kind == "earth":
        n = _value_noise(h, big_w, 5, 3, seed, 3)[:, ox:ox + w] * 0.7
        n = n + 0.5 * _value_noise(h, big_w, 1.5, 1.5, seed + 2, 1)[:, ox:ox + w]
    elif kind == "cloud":
        n = _value_noise(h, big_w, 28, 16, seed, 2)[:, ox:ox + w] * 0.9
    elif kind == "bark":
        n = _value_noise(h, big_w, 1.8, 9, seed, 2)[:, ox:ox + w]
        n = n * 0.9 + 0.3 * np.sign(np.sin((xx * 2.1 + yy * 0.2) / UNIT))
    elif kind == "stone":
        bw, bh = 9 * UNIT, 5 * UNIT
        row = (yy + oy) // bh
        bx = (xx + ox + (row % 2) * (bw // 2)) % bw
        mortar = (bx < UNIT) | (((yy + oy) % bh) < UNIT)
        n = _value_noise(h, big_w, 4, 3, seed, 2)[:, ox:ox + w] * 0.6
        n = np.where(mortar, -1.4, n + 0.2)
    elif kind == "cloth":
        weave = (((xx + yy) // UNIT) % 2) * 0.5 - 0.25
        n = _value_noise(h, big_w, 4, 4, seed, 2)[:, ox:ox + w] * 0.8 + weave
    elif kind == "wool":
        n = _value_noise(h, big_w, 2.5, 2.5, seed, 3)[:, ox:ox + w] * 1.1
    elif kind == "skin":
        n = _value_noise(h, big_w, 2.5, 2.5, seed, 2)[:, ox:ox + w] * 0.6
    elif kind == "hair":
        n = _value_noise(h, big_w, 1.2, 6, seed, 2)[:, ox:ox + w] * 1.2
    elif kind == "leather":
        n = _value_noise(h, big_w, 3, 3, seed, 3)[:, ox:ox + w] * 0.7 + 0.2 * ((((xx * 3 + yy * 5) // UNIT) % 7) / 7 - 0.5)
    elif kind == "wood":
        n = _value_noise(h, big_w, 2, 14, seed, 2)[:, ox:ox + w] * 1.0
    else:
        raise ValueError(f"unknown texture {kind!r}")
    return n.astype(np.float32)


def retone(canvas, mask, n, amp=1.2, bias=0.0, frame=0):
    """Move each masked pixel along its colour's ramp by amp * n (dithered)."""
    if not mask.any():
        return
    H, W = canvas.shape[:2]
    ys, xs = np.nonzero(mask)
    cols = canvas[ys, xs]
    keys = cols[:, 0].astype(np.int64) * 65536 + cols[:, 1].astype(np.int64) * 256 + cols[:, 2]
    thr = threshold(H, W, 0, 0)[ys, xs]
    v = amp * n[ys, xs] + bias
    out = cols.copy()
    for key in np.unique(keys):
        sel = keys == key
        c = cols[sel][0]
        name = _RGB2NAME.get((int(c[0]), int(c[1]), int(c[2])))
        if name is None or name not in _FAMILY:
            continue
        fam, i = _FAMILY[name]
        vv = i + v[sel]
        lo = np.floor(vv)
        frac = vv - lo
        idx = (lo + (thr[sel] < frac)).astype(int).clip(0, len(fam) - 1)
        ramp = np.array([RGB[f] for f in fam], np.uint8)
        out[sel] = ramp[idx]
    canvas[ys, xs] = out


def texture(canvas, mask, kind, ox=0, oy=0, seed=0, amp=1.2, bias=0.0):
    H, W = canvas.shape[:2]
    retone(canvas, mask, field(kind, H, W, ox, oy, seed), amp, bias)
