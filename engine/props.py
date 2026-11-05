"""Procedural set pieces drawn as silhouettes into a backdrop layer.

    props:
      - {type: moon, pos: [250, 40], r: 12, halo: 30}
      - {type: tree, pos: [60, 150], height: 60, seed: 4, color: ink1, parallax: 0.8}
      - {type: ruin, pos: [180, 150], width: 70, height: 55, arches: 3, seed: 2, color: ink2, parallax: 0.4}
      - {type: fire, pos: [120, 158]}            # flickering flame; pair with a light
      # ambient supernatural scenery (never explained, never the subject of a shot)
      - {type: eyes, pos: [60, 140], pairs: 4, spread: [70, 14], color: ember2, seed: 1}
      - {type: wanderlight, pos: [240, 130], count: 3, spread: [60, 24], color: fern4, seed: 2}
      - {type: presence, pos: [200, 152], height: 46, color: ink0, amount: 0.55, seed: 3}

`pos` is the base (feet) in world pixels; `parallax` as for layers.
Props draw in list order, after the ridge layers and ground.
"""
import numpy as np

from .dither import mask, threshold
from .palette import RGB


def _put(c, x, y, col):
    H, W = c.shape[:2]
    if 0 <= x < W and 0 <= y < H:
        c[y, x] = col


def _line(c, x0, y0, x1, y1, col, thick=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n):
        f = i / max(1, n - 1)
        x, y = int(round(x0 + (x1 - x0) * f)), int(round(y0 + (y1 - y0) * f))
        for dx in range(thick):
            _put(c, x + dx, y, col)


def moon(c, p, ox, t):
    cx, cy = p["pos"][0] - ox, p["pos"][1]
    r, halo = p.get("r", 10), p.get("halo", 28)
    H, W = c.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    glow = np.clip(1 - (d - r) / halo, 0, 1) ** 2 * p.get("glow", 0.5)
    c[(threshold(H, W) < glow) & (d > r)] = RGB[p.get("halo_color", "night3")]
    c[d <= r] = RGB[p.get("color", "moon")]
    # a few dark maria
    rng = np.random.default_rng(p.get("seed", 1))
    for _ in range(4):
        mx, my = rng.uniform(-r * .5, r * .5, 2)
        mr = rng.uniform(r * .15, r * .35)
        c[np.sqrt((xx - cx - mx) ** 2 + (yy - cy - my) ** 2) <= mr] = RGB[p.get("shade", "ash4")]
    c[(d > r - 1) & (d <= r) & (xx > cx)] = RGB[p.get("shade", "ash4")]


def tree(c, p, ox, t):
    """Dead tree: recursive branching, thinning with depth, slight wind sway at the tips."""
    rng = np.random.default_rng(p.get("seed", 0))
    col = RGB[p.get("color", "ink1")]
    sway = p.get("sway", 0.6)

    def branch(x, y, ang, length, thick, depth):
        if depth == 0 or length < 2:
            return
        a = ang + np.sin(t * 1.3 + depth) * 0.02 * sway * (6 - depth)
        x1, y1 = x + np.cos(a) * length, y - np.sin(a) * length
        _line(c, x, y, x1, y1, col, max(1, thick))
        for _ in range(2 if depth > 1 else 1):
            branch(x1, y1, a + rng.uniform(-0.75, 0.75), length * rng.uniform(0.55, 0.78),
                   thick - 1, depth - 1)

    x, y = p["pos"][0] - ox, p["pos"][1]
    branch(x, y, np.pi / 2 + rng.uniform(-0.1, 0.1), p.get("height", 50) * 0.38,
           p.get("thick", 3), p.get("depth", 6))


def ruin(c, p, ox, t):
    """Broken arcade: a wall pierced by round arches, with a ragged, crumbled top."""
    rng = np.random.default_rng(p.get("seed", 0))
    x0, base = int(p["pos"][0] - ox), int(p["pos"][1])
    w, h, n = p.get("width", 60), p.get("height", 50), p.get("arches", 3)
    H, W = c.shape[:2]
    top = base - h + np.cumsum(rng.integers(-2, 3, w)).clip(-h // 3, h // 2)
    top[: w // 6] += rng.integers(0, h // 2)  # one end collapsed
    bay = w / n
    ar = int(bay * 0.32)
    for i in range(w):
        x = x0 + i
        if not (0 <= x < W):
            continue
        k = (i % bay) - bay / 2
        for y in range(max(0, int(top[i])), min(H, base)):
            # arch opening: rectangle below a semicircle
            spring = base - int(h * 0.55)
            open_ = abs(k) < ar and (y > spring or (k * k + (y - spring) ** 2) < ar * ar)
            if not open_:
                c[y, x] = RGB[p.get("color", "ink2")]
    if p.get("rim"):
        for i in range(w):
            y = int(top[i])
            if 0 <= x0 + i < W and 0 <= y < H:
                c[y, x0 + i] = RGB[p["rim"]]


def fire(c, p, ox, t):
    """Small flickering flame, a few pixels across. Deterministic per frame."""
    x, y = int(p["pos"][0] - ox), int(p["pos"][1])
    rng = np.random.default_rng(int(t * 12) + p.get("seed", 0))
    s = p.get("size", 1.0)
    for row in range(int(7 * s)):
        half = max(0, int((2.5 * s) * (1 - row / (7 * s)) + rng.uniform(-0.6, 0.6)))
        jitter = int(rng.integers(-1, 2)) if row > 2 else 0
        for dx in range(-half, half + 1):
            core = abs(dx) < half * 0.5 and row < 4 * s
            col = "flame" if core else ("ember2" if row < 4 * s else "ember1")
            _put(c, x + dx + jitter, y - row, RGB[col])
    for k in range(2):  # sparks
        if rng.random() < 0.6:
            _put(c, x + int(rng.integers(-3, 4)), y - int(rng.integers(8, 16) * s), RGB["ember2"])


def eyes(c, p, ox, t):
    """Pairs of eyes in the dark: each pair opens, holds, blinks and goes, on its own slow cycle."""
    rng = np.random.default_rng(p.get("seed", 0))
    sx, sy = p.get("spread", [60, 12])
    col = RGB[p.get("color", "ember2")]
    for i in range(p.get("pairs", 3)):
        x = p["pos"][0] - ox + rng.uniform(-sx / 2, sx / 2)
        y = p["pos"][1] + rng.uniform(-sy / 2, sy / 2)
        period, phase = rng.uniform(5, 11), rng.uniform(0, 11)
        u = ((t + phase) % period) / period
        if u > 0.55:                       # gone for the rest of the cycle
            continue
        if int((t + phase) * 12) % 37 == 0:  # an occasional blink
            continue
        gap = 2 if rng.random() < 0.6 else 3
        _put(c, int(x), int(y), col)
        _put(c, int(x) + gap, int(y), col)


def wanderlight(c, p, ox, t):
    """Drifting lights over marsh or forest: a bright core and a dithered halo, wandering slowly."""
    rng = np.random.default_rng(p.get("seed", 0))
    sx, sy = p.get("spread", [60, 20])
    col = p.get("color", "fern4")
    H, W = c.shape[:2]
    for i in range(p.get("count", 3)):
        a, b, ph = rng.uniform(0.15, 0.4), rng.uniform(0.2, 0.5), rng.uniform(0, 6.28)
        x = p["pos"][0] - ox + np.sin(t * a + ph) * sx / 2 + np.sin(t * a * 2.7 + ph) * 3
        y = p["pos"][1] + np.cos(t * b + ph * 1.3) * sy / 2
        pulse = 0.6 + 0.4 * np.sin(t * 1.7 + ph * 4)
        r = p.get("radius", 6)
        x0, y0 = int(x) - r, int(y) - r
        for yy in range(max(0, y0), min(H, y0 + 2 * r + 1)):
            for xx in range(max(0, x0), min(W, x0 + 2 * r + 1)):
                d = np.hypot(xx - x, yy - y) / r
                if d < 1 and threshold(1, 1, xx, yy)[0, 0] < (1 - d) ** 2 * pulse * 0.8:
                    c[yy, xx] = RGB[p.get("halo", "fern3")]
        _put(c, int(x), int(y), RGB[col])
        if pulse > 0.8:
            _put(c, int(x), int(y) - 1, RGB[col])


def presence(c, p, ox, t):
    """Something tall at the edge of things: a dithered dark shape, half there, swaying."""
    rng = np.random.default_rng(p.get("seed", 0))
    H, W = c.shape[:2]
    h = p.get("height", 40)
    w = p.get("width", h * 0.28)
    cx = p["pos"][0] - ox + np.sin(t * 0.3 + rng.uniform(0, 6)) * 2
    base = p["pos"][1]
    amount = p.get("amount", 0.5) * (0.75 + 0.25 * np.sin(t * 0.5 + rng.uniform(0, 6)))
    col = RGB[p.get("color", "ink0")]
    for yy in range(max(0, int(base - h)), min(H, int(base))):
        f = (base - yy) / h                     # 0 at the feet, 1 at the top
        half = w / 2 * (0.55 + 0.45 * np.sin(np.pi * min(1, f * 1.15))) * (1 - f ** 6)
        for xx in range(max(0, int(cx - half)), min(W, int(cx + half) + 1)):
            edge = 1 - abs(xx - cx) / max(half, 1)
            if threshold(1, 1, xx, yy)[0, 0] < amount * min(1, edge * 2.2):
                c[yy, xx] = col


EMISSIVE = {"fire", "eyes", "wanderlight"}
DRAW = {"moon": moon, "tree": tree, "ruin": ruin, "fire": fire,
        "eyes": eyes, "wanderlight": wanderlight, "presence": presence}


def draw(c, props, cam_x, t):
    for p in props:
        DRAW[p["type"]](c, p, cam_x * p.get("parallax", 1.0), t)
