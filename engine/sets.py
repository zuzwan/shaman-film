"""Set pieces for the river country (episode 1 onward): walls, gates, water,
mill machinery, interiors and the inserts the script asks for.

All of them are props (engine/props.py registers this table), so they take
`pos`, `parallax`, `layer` like any prop and draw in palette colours only.
Shapes are hard-edged; anything translucent (silk, glow, haze) is dithered.

    - {type: slab, rect: [x, y, w, h], color: ink2, rim: ash0}         # a wall, a table top, a board
    - {type: poly, points: [[x, y], ...], color: ink1}
    - {type: water, y: [120, 152], color: cold1, shine: cold2, flow: 6}  # river, ford, millrace
    - {type: levee, y: 128, height: 8, color: ash1, top: ash3}
    - {type: wall, x: [0, 320], top: 70, base: 152, kind: mud, gate: {x: 150, w: 30, h: 40, kind: arch}}
    - {type: willow, x: 0, width: 320, depth: 90, layer: front}
    - {type: planks, gaps: [[60, 14], [150, 14], [240, 14]], color: ink0}   # looking up through a bridge
    - {type: town, pos: [160, 132], width: 90}                          # a walled town far off
    - {type: wheel, pos: [160, 90], r: 40, speed: 0.4}                  # the mill wheel, turning
    - {type: gear, pos: [160, 90], r: 70, teeth: 18, speed: 0.3}         # the great gear, close
    - {type: chain, y: 150, links: 9, size: 18, layer: front}           # the measuring chain, near camera
    - {type: facades, x: [0, 320], top: 60, base: 150, doors: 4}        # the street, every door pinned back
    - {type: sheets, x: [20, 300], y: 70, rows: 2}                      # wet silk on lines
    - {type: tent, rect: [80, 60, 160, 92], shadows: [[110, 1], [150, 1], [185, 2], [215, 1]]}
    - inserts: hand, eye_slot, bowl, forearm, cord, clamp, feet, broomheads, scent, slate, ring ...
"""
import numpy as np

from .dither import threshold
from .palette import RGB


def _put(c, x, y, col):
    H, W = c.shape[:2]
    x, y = int(x), int(y)
    if 0 <= x < W and 0 <= y < H:
        c[y, x] = col


def _line(c, x0, y0, x1, y1, col, thick=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n):
        f = i / max(1, n - 1)
        x, y = int(round(x0 + (x1 - x0) * f)), int(round(y0 + (y1 - y0) * f))
        for d in range(int(thick)):
            _put(c, x + d, y, col)
            if thick > 2:
                _put(c, x, y + d, col)


def _rect(c, x, y, w, h, col):
    H, W = c.shape[:2]
    x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(W, int(x + w)), min(H, int(y + h))
    if x0 < x1 and y0 < y1:
        c[y0:y1, x0:x1] = col


def _dither_rect(c, x, y, w, h, col, amount):
    H, W = c.shape[:2]
    x0, y0, x1, y1 = max(0, int(x)), max(0, int(y)), min(W, int(x + w)), min(H, int(y + h))
    if x0 < x1 and y0 < y1:
        m = threshold(y1 - y0, x1 - x0, x0, y0) < amount
        c[y0:y1, x0:x1][m] = col


def _disc(c, cx, cy, r, col, ring=False):
    H, W = c.shape[:2]
    y0, y1 = max(0, int(cy - r - 1)), min(H, int(cy + r + 2))
    x0, x1 = max(0, int(cx - r - 1)), min(W, int(cx + r + 2))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2)
    m = (d <= r) & (d > r - 1.2) if ring else d <= r
    c[y0:y1, x0:x1][m] = col


def _fill_poly(c, pts, col):
    H, W = c.shape[:2]
    pts = np.asarray(pts, dtype=float)
    y0, y1 = max(0, int(pts[:, 1].min())), min(H, int(pts[:, 1].max()) + 1)
    x0, x1 = max(0, int(pts[:, 0].min())), min(W, int(pts[:, 0].max()) + 1)
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    px, py = xx + 0.5, yy + 0.5
    inside = np.zeros(px.shape, bool)
    n = len(pts)
    for i in range(n):
        xa, ya = pts[i]
        xb, yb = pts[(i + 1) % n]
        cond = (ya > py) != (yb > py)
        with np.errstate(divide="ignore", invalid="ignore"):
            xint = (xb - xa) * (py - ya) / (yb - ya + 1e-12) + xa
        inside ^= cond & (px < xint)
    c[y0:y1, x0:x1][inside] = col


def _C(p, key, default):
    return RGB[p.get(key, default)]


# ------------------------------------------------------------------ generic shapes
def slab(c, p, ox, t):
    x, y, w, h = p["rect"]
    _rect(c, x - ox, y, w, h, _C(p, "color", "ink2"))
    if p.get("rim"):
        _rect(c, x - ox, y, w, 1, RGB[p["rim"]])
    if p.get("shade"):  # a dithered darker lower part
        _dither_rect(c, x - ox, y + h * 0.5, w, h * 0.5, RGB[p["shade"]], 0.5)


def poly(c, p, ox, t):
    _fill_poly(c, [(x - ox, y) for x, y in p["points"]], _C(p, "color", "ink1"))


def haze(c, p, ox, t):
    """A dithered veil over part of the frame: mist, dust in a light shaft, the dark of a room."""
    x, y, w, h = p.get("rect", [0, 0, c.shape[1], c.shape[0]])
    _dither_rect(c, x - ox, y, w, h, _C(p, "color", "ink0"), p.get("amount", 0.5))


def stripes(c, p, ox, t):
    """Light falling through boards: slanted dithered bands across a region."""
    x, y, w, h = p.get("rect", [0, 0, c.shape[1], c.shape[0]])
    H, W = c.shape[:2]
    x0, y0, x1, y1 = max(0, int(x - ox)), max(0, int(y)), min(W, int(x - ox + w)), min(H, int(y + h))
    if x0 >= x1 or y0 >= y1:
        return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    period, width, slant = p.get("period", 22), p.get("width", 6), p.get("slant", 0.5)
    band = ((xx + ox * 0 + yy * slant + p.get("offset", 0)) % period) < width
    m = band & (threshold(y1 - y0, x1 - x0, x0, y0) < p.get("amount", 0.45))
    c[y0:y1, x0:x1][m] = _C(p, "color", "ash3")
    if p.get("dust"):  # motes turning in the light
        rng = np.random.default_rng(p.get("seed", 3))
        for i in range(p["dust"]):
            dx = (rng.uniform(0, w) + np.sin(t * 0.3 + i) * 6) % w
            dy = (rng.uniform(0, h) + t * rng.uniform(1, 3)) % h
            _put(c, x - ox + dx, y + dy, _C(p, "dust_color", "ash5"))


# ------------------------------------------------------------------ land and water
def water(c, p, ox, t):
    """A band of water with moving shine lines; `flow` px/s sideways (a millrace runs fast)."""
    H, W = c.shape[:2]
    y0, y1 = p["y"]
    y0, y1 = max(0, int(y0)), min(H, int(y1))
    x0, x1 = p.get("x", [-4000, 4000])
    xa, xb = max(0, int(x0 - ox)), min(W, int(x1 - ox))
    if y0 >= y1 or xa >= xb:
        return
    c[y0:y1, xa:xb] = _C(p, "color", "cold1")
    if p.get("deep"):
        _dither_rect(c, xa, y0 + (y1 - y0) // 2, xb - xa, (y1 - y0) // 2 + 1, RGB[p["deep"]], 0.5)
    rng = np.random.default_rng(p.get("seed", 1))
    shine = _C(p, "shine", "cold2")
    n = int((y1 - y0) * (xb - xa) / 90 * p.get("density", 1.0))
    xs = rng.uniform(0, 4000, n)
    ys = rng.uniform(y0, y1, n)
    ln = rng.integers(2, 7, n)
    ph = rng.uniform(0, 6.28, n)
    flow = p.get("flow", 1.5)
    for i in range(n):
        if np.sin(t * 1.5 + ph[i]) < -0.2:  # glints come and go
            continue
        persp = 0.4 + 0.6 * (ys[i] - y0) / max(1, y1 - y0)
        x = (xs[i] + t * flow * persp - ox * p.get("parallax", 1.0) * 0) % 4000 - 2000 + W / 2
        if xa <= x < xb:
            _line(c, x, ys[i], x + ln[i] * persp, ys[i], shine)
    if p.get("edge"):
        _rect(c, xa, y0, xb - xa, 1, RGB[p["edge"]])


def levee(c, p, ox, t):
    """The levee: a ruled bank across the whole frame, a lit top edge, a slope below."""
    H, W = c.shape[:2]
    y, h = int(p["y"]), int(p.get("height", 8))
    _rect(c, 0, y, W, h, _C(p, "color", "ash1"))
    _rect(c, 0, y, W, 1, _C(p, "top", "ash3"))
    _dither_rect(c, 0, y + h - 3, W, 3, _C(p, "shade", "ink2"), 0.5)
    if p.get("snow"):
        rng = np.random.default_rng(5)
        for x in range(0, W, 3):
            if rng.random() < 0.4:
                _put(c, x, y + h + rng.integers(0, 3), RGB[p["snow"]])


def fields(c, p, ox, t):
    """Flooded winter fields: strips of water between dark furrow lines, going to the horizon."""
    H, W = c.shape[:2]
    y0, y1 = int(p["y"][0]), int(p["y"][1])
    for y in range(max(0, y0), min(H, y1)):
        f = (y - y0) / max(1, y1 - y0)
        k = int(2 + f * 10)
        if (y - y0) % k == 0:
            c[y, :] = _C(p, "furrow", "ink2")
        elif (y - y0) % k == 1:
            row = threshold(1, W, -int(ox * f), y)[0] < 0.35
            c[y, row] = _C(p, "shine", "sky2")


def stubble(c, p, ox, t):
    """Winter stubble: short strokes in rows, bigger near the camera."""
    H, W = c.shape[:2]
    y0 = int(p.get("y", 120))
    col = _C(p, "color", "rust1")
    rng = np.random.default_rng(p.get("seed", 2))
    for y in range(y0, H, 2):
        f = (y - y0) / max(1, H - y0)
        step = max(2, int(9 - f * 6))
        off = rng.integers(0, step)
        h = 1 + int(f * 3)
        for x in range(off - int(ox * (0.5 + f)) % step, W, step):
            _line(c, x, y, x, y - h, col)


def reeds(c, p, ox, t):
    """Dead reeds: thin stems in clumps, swaying; `lean` with a current."""
    rng = np.random.default_rng(p.get("seed", 4))
    col = _C(p, "color", "ash2")
    x0, x1 = p.get("x", [0, 320])
    base, hmax = p.get("y", 150), p.get("height", 24)
    lean = p.get("lean", 0.0)
    if p.get("lean_cycle"):  # lean against the current, then straighten
        lean = p["lean_cycle"] * max(0.0, np.sin(t * 2 * np.pi / p.get("period", 4.0)))
    for _ in range(int((x1 - x0) / 2 * p.get("density", 1.0))):
        x = rng.uniform(x0, x1) - ox
        h = rng.uniform(0.4, 1.0) * hmax
        sw = np.sin(t * 1.2 + x * 0.1) * 0.08
        _line(c, x, base, x + (lean + sw + rng.uniform(-0.15, 0.15)) * h, base - h, col)
        if rng.random() < 0.3:
            _put(c, x + (lean + sw) * h, base - h - 1, _C(p, "head", "ash3"))


def willow(c, p, ox, t):
    """Willow switches hanging from the top of frame, near camera, swaying."""
    rng = np.random.default_rng(p.get("seed", 6))
    col = _C(p, "color", "ink0")
    x0, width, depth = p.get("x", 0) - ox, p.get("width", 320), p.get("depth", 80)
    for i in range(int(width / 3)):
        x = x0 + rng.uniform(0, width)
        L = rng.uniform(0.3, 1.0) * depth
        ph = rng.uniform(0, 6)
        prev = (x, 0)
        for k in range(1, int(L)):
            sway = np.sin(t * 0.8 + ph) * (k / L) ** 2 * 3
            pt = (x + sway + np.sin(k * 0.05 + ph) * 2, k)
            _put(c, pt[0], pt[1], col)
            if rng.random() < 0.15:
                _put(c, pt[0] + 1, pt[1] + 1, col)
            prev = pt
    _rect(c, 0, 0, c.shape[1], p.get("canopy", 3), col)


def frost(c, p, ox, t):
    """Frost glints on the ground: sparse bright pixels that twinkle."""
    H, W = c.shape[:2]
    rng = np.random.default_rng(p.get("seed", 8))
    y0 = p.get("y", 150)
    n = p.get("count", 60)
    xs, ys, ph = rng.uniform(0, W + 200, n), rng.uniform(y0, H, n), rng.uniform(0, 6, n)
    for x, y, f in zip(xs, ys, ph):
        if np.sin(t * 2 + f * 5) > 0.3:
            _put(c, (x - ox) % (W + 200) - 100, y, _C(p, "color", "ash5"))


def sun(c, p, ox, t):
    """A low red sun with a dithered halo."""
    cx, cy, r = p["pos"][0] - ox, p["pos"][1], p.get("r", 9)
    H, W = c.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    glow = np.clip(1 - (d - r) / p.get("halo", 26), 0, 1) ** 2 * 0.7
    c[(threshold(H, W) < glow) & (d > r)] = _C(p, "halo_color", "ember0")
    c[d <= r] = _C(p, "color", "ember1")
    if p.get("streak"):  # its line on the water
        y0 = p["streak"]
        for y in range(int(y0), min(H, int(y0) + 14)):
            w = int(r * (1 - (y - y0) / 16)) + int(np.sin(t * 3 + y) * 1.5)
            if y % 2 == 0:
                _rect(c, cx - w, y, 2 * w, 1, _C(p, "color", "ember1"))


def stars(c, p, ox, t):
    H, W = c.shape[:2]
    rng = np.random.default_rng(p.get("seed", 9))
    for _ in range(p.get("count", 40)):
        x, y = rng.uniform(0, W), rng.uniform(0, p.get("y", 90))
        if np.sin(t * rng.uniform(0.5, 2) + x) > -0.6:
            _put(c, x - ox * 0.05, y, _C(p, "color", "night3"))


# ------------------------------------------------------------------ built things
def wall(c, p, ox, t):
    """A town wall. kind: mud (reed thatch on top) or stone (river stones, iron-banded gate).
    gate: {x, w, h, kind: bar | arch | open}; slot: [x, y] a peep slot; post: x of a gatepost."""
    H, W = c.shape[:2]
    x0, x1 = p.get("x", [0, 320])
    top, base = int(p["top"]), int(p.get("base", 152))
    col = _C(p, "color", "ash1" if p.get("kind", "mud") == "mud" else "ash2")
    dark = _C(p, "dark", "ash0")
    xa, xb = int(x0 - ox), int(x1 - ox)
    _rect(c, xa, top, xb - xa, base - top, col)
    rng = np.random.default_rng(p.get("seed", 3))
    if p.get("kind", "mud") == "mud":
        _dither_rect(c, xa, top + (base - top) * 0.6, xb - xa, (base - top) * 0.4, dark, 0.35)
        for x in range(xa, xb):  # thatch fringe
            h = 3 + int(rng.integers(0, 4))
            _line(c, x, top - h, x, top, _C(p, "thatch", "rust1") if x % 3 else _C(p, "thatch_dark", "rust0"))
    else:
        for y in range(top + 3, base, 5):  # courses of river stone
            sh = int(rng.integers(0, 8))
            for x in range(xa + sh, xb, 9):
                _rect(c, x, y, 7, 1, dark)
                _put(c, x + 1, y - 2, _C(p, "light", "ash3"))
        _rect(c, xa, top, xb - xa, 1, _C(p, "light", "ash3"))
    g = p.get("gate")
    if g:
        gx, gw, gh = int(g["x"] - ox), int(g.get("w", 28)), int(g.get("h", 40))
        gy = base - gh
        inside = _C(g, "inside", "ink0")
        if g.get("kind", "bar") == "bar":
            _rect(c, gx, gy, gw, gh, _C(g, "color", "rust0"))
            for x in range(gx + 2, gx + gw, 4):
                _line(c, x, gy, x, base - 1, _C(g, "plank", "ink2"))
            for by in (gy + gh // 3, gy + 2 * gh // 3):
                _rect(c, gx - 2, by, gw + 4, 2, _C(g, "bar", "ink1"))
        else:  # arch: open, showing what's beyond in `inside` (or nothing: the caller draws through it)
            r = gw / 2
            yy, xx = np.mgrid[max(0, gy - int(r)):base, max(0, gx):min(W, gx + gw)]
            if yy.size:
                cx, cy = gx + r, gy
                m = (yy >= cy) | ((xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r)
                region = c[max(0, gy - int(r)):base, max(0, gx):min(W, gx + gw)]
                if g.get("see_through"):
                    pass
                else:
                    region[m] = inside
                # rusted iron bands at the springing
                if g.get("bands", True):
                    _rect(c, gx - 2, gy + 2, 2, gh - 2, _C(g, "iron", "rust0"))
                    _rect(c, gx + gw, gy + 2, 2, gh - 2, _C(g, "iron", "rust0"))
    if p.get("slot"):
        sx, sy = p["slot"]
        _rect(c, sx - ox, sy, 10, 3, RGB["ink0"])
    if p.get("post") is not None:
        px_ = int(p["post"] - ox)
        _rect(c, px_, top - 10, 6, base - top + 10, _C(p, "post_color", "rust0"))
        # the carved six-legged horse nailed to the post
        hx, hy = px_ - 3, top + 4
        _rect(c, hx + 1, hy, 9, 3, RGB["ash3"])
        _rect(c, hx + 9, hy - 3, 2, 4, RGB["ash3"])
        for k in range(6):
            _line(c, hx + 1 + k * 1.6, hy + 3, hx + 1 + k * 1.6, hy + 6, RGB["ash3"])


def waterstone(c, p, ox, t):
    """The flat water stone outside a gate, with its clay bowl: full, dry (dead gnats) or none."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    w = p.get("width", 16)
    _rect(c, x - w / 2, y - 4, w, 4, _C(p, "color", "ash2"))
    _rect(c, x - w / 2, y - 4, w, 1, RGB["ash4"])
    if p.get("cracked"):
        _line(c, x - 2, y - 4, x + 1, y - 1, RGB["ink2"])
    b = p.get("bowl", "full")
    if b:
        _rect(c, x - 3, y - 7, 7, 3, RGB["rust1"])
        _rect(c, x - 2, y - 7, 5, 1, RGB["cold2"] if b == "full" else RGB["ink2"])


def town(c, p, ox, t):
    """A small walled mill town far off: wall line, slate roofs, the wheel house; no smoke."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    w = p.get("width", 80)
    col, roof = _C(p, "color", "ash1"), _C(p, "roof", "ink2")
    rng = np.random.default_rng(p.get("seed", 11))
    _rect(c, x - w / 2, y - 6, w, 6, col)
    for i in range(int(w / 7)):
        rx = x - w / 2 + 2 + i * 7 + rng.integers(-1, 2)
        rh = rng.integers(4, 9)
        _fill_poly(c, [(rx, y - 6), (rx + 3, y - 6 - rh), (rx + 6, y - 6)], roof)
    _rect(c, x + w / 2 - 12, y - 18, 8, 12, roof)  # the mill
    if p.get("pennant"):
        _line(c, x - 4, y - 7, x - 4, y - 16, RGB["ash3"])
        _rect(c, x - 3, y - 16, 3, 2, RGB["bone"])


def wheel(c, p, ox, t):
    """The mill wheel: rim, spokes and paddles turning, water sheeting off the paddles."""
    cx, cy, r = p["pos"][0] - ox, p["pos"][1], p.get("r", 30)
    col = _C(p, "color", "rust0")
    a0 = t * p.get("speed", 0.5)
    th = max(1, int(r / 14))
    _disc(c, cx, cy, r, col, ring=True)
    _disc(c, cx, cy, r - th, col, ring=True)
    n = p.get("spokes", 8)
    for k in range(n):
        a = a0 + 2 * np.pi * k / n
        _line(c, cx, cy, cx + np.cos(a) * r, cy + np.sin(a) * r, col, th)
    for k in range(n * 2):
        a = a0 + np.pi * k / n
        px_, py_ = cx + np.cos(a) * r, cy + np.sin(a) * r
        _line(c, px_, py_, px_ + np.cos(a) * r * 0.18, py_ + np.sin(a) * r * 0.18, _C(p, "paddle", "rust1"), th + 1)
        if p.get("sheeting", True) and np.sin(a) > 0.2 and np.cos(a) > 0:  # water running off the rising side
            for j in range(int(r * 0.4)):
                if threshold(1, 1, int(px_), int(py_ + j))[0, 0] < 0.5:
                    _put(c, px_ + np.cos(a) * r * 0.2, py_ + j, _C(p, "water", "cold2"))
    _disc(c, cx, cy, max(2, r * 0.12), _C(p, "hub", "ink1"))


def gear(c, p, ox, t):
    """The great gear wheel, close: a toothed rim turning past the camera."""
    cx, cy, r = p["pos"][0] - ox, p["pos"][1], p.get("r", 60)
    col = _C(p, "color", "ink1")
    H, W = c.shape[:2]
    a0 = t * p.get("speed", 0.3)
    n = p.get("teeth", 16)
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    ang = (np.arctan2(yy - cy, xx - cx) - a0) % (2 * np.pi / n)
    tooth = ang < (np.pi / n)
    rim = (d <= r) & (d > r * 0.82)
    teeth = (d > r) & (d <= r * 1.14) & tooth
    spokes = np.zeros_like(rim)
    for k in range(4):
        a = a0 + k * np.pi / 2
        dist = np.abs(-(xx - cx) * np.sin(a) + (yy - cy) * np.cos(a))
        spokes |= (dist < r * 0.07) & (d < r * 0.85)
    c[rim | teeth | spokes | (d < r * 0.15)] = col
    if p.get("rim_light"):
        edge = (d <= r * 1.14) & (d > r * 1.1) & tooth
        c[edge] = RGB[p["rim_light"]]


def chain(c, p, ox, t):
    """The measuring chain in the extreme foreground: big oval links in a sagging line."""
    col = _C(p, "color", "ink0")
    y0, n, s = p.get("y", 150), p.get("links", 8), p.get("size", 20)
    x = p.get("x", -10) - ox
    sag = p.get("sag", 10)
    for i in range(n):
        f = i / max(1, n - 1)
        cx = x + i * s * 0.9
        cy = y0 - sag * 4 * f * (1 - f) + (i % 2) * 1
        H, W = c.shape[:2]
        rx, ry = (s * 0.55, s * 0.3) if i % 2 == 0 else (s * 0.5, s * 0.12)
        yy, xx = np.mgrid[max(0, int(cy - ry - 3)):min(H, int(cy + ry + 3)), max(0, int(cx - rx - 3)):min(W, int(cx + rx + 3))]
        if not yy.size:
            continue
        e = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
        th = 0.55 if i % 2 == 0 else 1.0
        m = (e <= 1.0) & (e >= th) if i % 2 == 0 else e <= 1.0
        c[yy[0, 0]:yy[-1, 0] + 1, xx[0, 0]:xx[0, -1] + 1][m] = col


def pegs(c, p, ox, t):
    """Survey pegs in the ground, with a pale bone rag each."""
    for x in p.get("xs", []):
        _line(c, x - ox, p.get("y", 150), x - ox, p.get("y", 150) - 6, RGB["rust1"])
        _put(c, x - ox + 1, p.get("y", 150) - 6, RGB["bone"])


def tripod(c, p, ox, t):
    """The Survey tripod with its pale bone pennant."""
    x, y, h = p["pos"][0] - ox, p["pos"][1], p.get("height", 40)
    col = _C(p, "color", "ink1")
    _line(c, x, y - h, x - h * 0.3, y, col)
    _line(c, x, y - h, x + h * 0.3, y, col)
    _line(c, x, y - h, x + h * 0.05, y, col)
    flap = int(np.sin(t * 3) * 1.5)
    _fill_poly(c, [(x, y - h - h * 0.4), (x + h * 0.35, y - h - h * 0.32 + flap), (x, y - h - h * 0.22)], _C(p, "pennant", "bone"))
    _line(c, x, y - h, x, y - h - h * 0.42, col)


def awning(c, p, ox, t):
    """The column's trestle under a silk awning, the ledger open on it."""
    x, y, w = p["pos"][0] - ox, p["pos"][1], p.get("width", 60)
    silk = _C(p, "silk", "ash4")
    top = y - p.get("height", 40)
    _fill_poly(c, [(x - w / 2 - 4, top + 6), (x + w / 2 + 4, top + 6), (x + w / 2, top), (x - w / 2, top)], silk)
    for k in range(0, int(w), 6):  # scalloped edge, moving a little
        _put(c, x - w / 2 + k, top + 7 + int(np.sin(t * 2 + k) > 0.5), silk)
    for sx in (x - w / 2, x + w / 2):
        _line(c, sx, top + 6, sx, y, RGB["rust0"])
    _rect(c, x - w / 3, y - 12, w * 2 / 3, 2, RGB["rust0"])  # the trestle top
    _line(c, x - w / 3 + 2, y - 10, x - w / 3 + 4, y, RGB["rust0"])
    _line(c, x + w / 3 - 2, y - 10, x + w / 3 - 4, y, RGB["rust0"])
    _rect(c, x - 6, y - 14, 12, 2, RGB["bone"])  # the ledger
    _put(c, x, y - 14, RGB["ash2"])


def fountain(c, p, ox, t):
    x, y, w = p["pos"][0] - ox, p["pos"][1], p.get("width", 40)
    _rect(c, x - w / 2, y - 7, w, 7, _C(p, "color", "ash2"))
    _rect(c, x - w / 2, y - 7, w, 1, RGB["ash4"])
    _rect(c, x - 3, y - 18, 6, 11, _C(p, "color", "ash2"))
    _rect(c, x - 6, y - 19, 12, 2, RGB["ash3"])


def facades(c, p, ox, t):
    """A street of house fronts: every door pinned back, black inside. `sitters` puts the
    shapes of hosts upright in the dark of each door, all facing one way."""
    x0, x1 = p.get("x", [0, 320])
    top, base = p.get("top", 60), p.get("base", 150)
    col = _C(p, "color", "ash2")
    rng = np.random.default_rng(p.get("seed", 13))
    x = x0
    i = 0
    while x < x1:
        w = int(rng.integers(40, 62))
        hx = x - ox
        h = base - top - rng.integers(0, 14)
        _rect(c, hx, base - h, w - 2, h, col if i % 2 == 0 else _C(p, "alt", "ash1"))
        _fill_poly(c, [(hx - 3, base - h), (hx + w / 2, base - h - 16), (hx + w + 1, base - h)], _C(p, "roof", "ink2"))
        dx = hx + w * 0.3
        dw, dh = 12, 26
        _rect(c, dx, base - dh, dw, dh, _C(p, "inside", "ink0"))
        _rect(c, dx + dw, base - dh, 3, dh, _C(p, "door", "rust0"))  # the door, pinned back
        if p.get("sitters"):
            for k in range(2):
                sx = dx + 3 + k * 5
                _dither_rect(c, sx, base - 15, 3, 9, _C(p, "sitter", "ink2"), 0.6)
                _dither_rect(c, sx, base - 18, 3, 3, _C(p, "sitter", "ink2"), 0.6)
        wx = hx + w * 0.68
        _rect(c, wx, base - h + 8, 9, 8, _C(p, "window", "ink1"))
        if p.get("dish"):
            _rect(c, wx + 2, base - h + 15, 5, 1, RGB["rust1"])
        x += w
        i += 1


def bench(c, p, ox, t):
    """The cobbler's bench, tools laid in a ruled line."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    w = p.get("width", 40)
    _rect(c, x, y - 10, w, 2, RGB["rust0"])
    _rect(c, x + 2, y - 8, 2, 8, RGB["rust0"])
    _rect(c, x + w - 4, y - 8, 2, 8, RGB["rust0"])
    for k in range(p.get("tools", 6)):
        _rect(c, x + 4 + k * (w - 8) / p.get("tools", 6), y - 11, 2, 1, RGB["ash4"])


def cobbles(c, p, ox, t):
    """Cobbles: a grid of rounded stones, bigger near the camera."""
    H, W = c.shape[:2]
    y0 = int(p.get("y", 150))
    col = _C(p, "line", "ink2")
    for y in range(y0, H):
        f = (y - y0) / max(1, H - y0)
        size = 3 + int(f * 9)
        if (y - y0) % size == 0:
            c[y, :] = col
        row_off = ((y - y0) // size) * size // 2
        for x in range(-int(ox * (0.6 + f)) % size - size + row_off % size, W, size):
            _put(c, x, y, col)


def crates(c, p, ox, t):
    """Cricket crates stacked to the rafters: slatted boxes, a dark gap between."""
    x0, x1 = p.get("x", [0, 320])
    top, base, s = p.get("top", 40), p.get("base", 140), p.get("size", 14)
    col, dark = _C(p, "color", "rust0"), _C(p, "dark", "ink1")
    for y in range(int(top), int(base), s):
        for x in range(int(x0), int(x1), s + 2):
            _rect(c, x - ox, y, s, s - 1, col)
            for k in range(2, s, 3):
                _line(c, x - ox + k, y, x - ox + k, y + s - 2, dark)


def quern(c, p, ox, t):
    """A quern stone on the floor (the host turning it is an actor)."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    w = p.get("width", 10)
    _rect(c, x - w / 2, y - 4, w, 4, _C(p, "color", "ash2"))
    _rect(c, x - w / 2, y - 4, w, 1, RGB["ash3"])
    a = t * p.get("speed", 2.5) + p.get("phase", 0)
    _line(c, x + np.cos(a) * w * 0.35, y - 4, x + np.cos(a) * w * 0.35, y - 7, RGB["rust0"])


def grate(c, p, ox, t):
    """An iron grate across the outflow."""
    x, y, w, h = p["rect"]
    col = _C(p, "color", "ink1")
    for k in range(0, int(w), p.get("gap", 6)):
        _rect(c, x - ox + k, y, 2, h, col)
    _rect(c, x - ox, y, w, 2, col)
    _rect(c, x - ox, y + h // 2, w, 1, col)


def steps(c, p, ox, t):
    """Stone steps down to the water, seen side-on."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    n, sw, sh = p.get("n", 6), p.get("tread", 10), p.get("rise", 5)
    for k in range(n):
        _rect(c, x + k * sw, y + k * sh, p.get("width", 60) - k * sw, sh, _C(p, "color", "ash2"))
        _rect(c, x + k * sw, y + k * sh, p.get("width", 60) - k * sw, 1, RGB["ash3"])


def body(c, p, ox, t):
    """A drowned body face down in the water: a dark swollen hump, a bent leg, the coat."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    s = p.get("size", 1.0)
    bob = int(np.sin(t * 1.3) * 1)
    _fill_poly(c, [(x - 14 * s, y + bob), (x - 10 * s, y - 5 * s + bob), (x + 8 * s, y - 6 * s + bob), (x + 14 * s, y - 2 * s + bob), (x + 12 * s, y + bob)],
               _C(p, "coat", "ash3"))
    _disc(c, x - 15 * s, y - 2 * s + bob, 3 * s, _C(p, "skin", "ash1"))
    _line(c, x + 12 * s, y - 2 * s + bob, x + 18 * s, y - 9 * s + bob, _C(p, "coat", "ash3"), max(1, int(2 * s)))
    _line(c, x + 18 * s, y - 9 * s + bob, x + 22 * s, y - 4 * s + bob, RGB["ink2"], max(1, int(2 * s)))


def sheets(c, p, ox, t):
    """Lines of wet silk washing, every sheet the same size, hung the same distance apart.
    Dithered, so a figure behind shows as a shadow."""
    x0, x1 = p.get("x", [0, 320])
    y = p.get("y", 60)
    w, h, gap = p.get("w", 30), p.get("h", 40), p.get("gap", 8)
    for r in range(p.get("rows", 1)):
        yy = y + r * p.get("row_gap", 0)
        _line(c, x0 - ox, yy, x1 - ox, yy, RGB["ink2"])
        x = x0
        while x + w <= x1:
            sway = np.sin(t * 1.6 + x * 0.05) * 2
            snap = 1 if np.sin(t * 5 + x) > 0.95 else 0
            pts = [(x - ox, yy), (x - ox + w, yy), (x - ox + w + sway + snap, yy + h), (x - ox + sway, yy + h)]
            H, W = c.shape[:2]
            tmp = c.copy()
            _fill_poly(tmp, pts, _C(p, "color", "ash4"))
            m = (tmp != c).any(-1) & (threshold(H, W) < p.get("amount", 0.75))
            c[m] = tmp[m]
            x += w + gap


def cart(c, p, ox, t):
    """A handcart on its side, one wheel off; silk bedding still roped on."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    _fill_poly(c, [(x - 20, y), (x - 18, y - 16), (x + 16, y - 20), (x + 20, y - 4)], RGB["rust0"])
    _fill_poly(c, [(x - 14, y - 4), (x - 12, y - 14), (x + 12, y - 17), (x + 14, y - 6)], RGB["ash4"])
    _line(c, x - 12, y - 10, x + 14, y - 12, RGB["ink1"])
    _line(c, x + 20, y - 4, x + 34, y - 10, RGB["rust0"], 2)
    _disc(c, x - 2, y - 2, 8, RGB["ink1"], ring=True)
    # the empty cricket cage, door open
    _rect(c, x + 26, y - 6, 6, 6, RGB["ash0"])
    _rect(c, x + 27, y - 5, 4, 4, RGB["ink0"])


def spokes(c, p, ox, t):
    """A fallen wheel close to camera: rim and spokes cut the frame into wedges."""
    cx, cy, r = p["pos"][0] - ox, p["pos"][1], p.get("r", 110)
    col = _C(p, "color", "ink0")
    _disc(c, cx, cy, r, col, ring=True)
    _disc(c, cx, cy, r - 1, col, ring=True)
    _disc(c, cx, cy, r - 2, col, ring=True)
    _disc(c, cx, cy, r * 0.13, col)
    for k in range(p.get("n", 8)):
        a = 2 * np.pi * k / p.get("n", 8) + p.get("angle", 0.2)
        _line(c, cx, cy, cx + np.cos(a) * r, cy + np.sin(a) * r, col, p.get("thick", 4))


def trench(c, p, ox, t):
    """The compost trench: dark earth and straw, two bare grey feet sticking out."""
    x, y, w = p["pos"][0] - ox, p["pos"][1], p.get("width", 80)
    _rect(c, x - w / 2, y - 3, w, 5, RGB["ink1"])
    rng = np.random.default_rng(3)
    for k in range(int(w)):
        if rng.random() < 0.4:
            _put(c, x - w / 2 + k, y - 3 - rng.integers(0, 2), RGB["sky1"])
    if p.get("feet", True):
        fx = x + p.get("feet_x", 10)
        s = p.get("size", 1)
        for d in (0, 4 * s):
            _rect(c, fx + d, y - 5 * s, 2 * s, 4 * s, RGB["ash3"])
            _rect(c, fx + d, y - 6 * s, 3 * s, 2 * s, RGB["ash3"])


def lantern(c, p, ox, t):
    """A lantern hung from the gate iron: frame, glass, a flame; pair it with a light."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    s = p.get("size", 1)
    _line(c, x, y - 6 * s, x, y - 3 * s, RGB["ink1"])
    _rect(c, x - 2 * s, y - 3 * s, 5 * s, 6 * s, RGB["ink1"])
    _rect(c, x - 1 * s, y - 2 * s, 3 * s, 4 * s, RGB["ember2"])
    _put(c, x, y - 1 * s, RGB["flame"])


def moths(c, p, ox, t):
    """Moths ticking at a light: a few pale pixels darting in a tight orbit."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    rng = np.random.default_rng(p.get("seed", 5))
    for i in range(p.get("count", 5)):
        a, b = rng.uniform(1.5, 4), rng.uniform(0, 6)
        r = rng.uniform(3, p.get("radius", 9))
        _put(c, x + np.cos(t * a + b) * r + np.sin(t * 9 + i) * 1.2, y + np.sin(t * a * 1.3 + b) * r * 0.7, _C(p, "color", "bone"))


def flies(c, p, ox, t):
    """Flies walking and darting on a pane or over a body."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    sx, sy = p.get("spread", [20, 12])
    rng = np.random.default_rng(p.get("seed", 6))
    for i in range(p.get("count", 4)):
        ph = rng.uniform(0, 6)
        jump = int(t * rng.uniform(0.4, 1.2) + ph)
        r2 = np.random.default_rng(jump * 31 + i)
        _put(c, x + r2.uniform(-sx / 2, sx / 2) + np.sin(t * 6 + ph), y + r2.uniform(-sy / 2, sy / 2), _C(p, "color", "ink0"))


def tent(c, p, ox, t):
    """The column's silk tent, lit from inside: glowing walls, shadows of the people
    in it thrown huge on the silk. shadows: [[x, size], ...]; `still` stops them swaying."""
    x, y, w, h = p["rect"]
    x -= ox
    _fill_poly(c, [(x, y + h), (x, y + h * 0.25), (x + w / 2, y), (x + w, y + h * 0.25), (x + w, y + h)], _C(p, "color", "ash4"))
    H, W = c.shape[:2]
    _dither_rect(c, x, y + h * 0.25, w, h * 0.75, _C(p, "glow", "ember2"), p.get("glow_amount", 0.25))
    for i, (sx, size) in enumerate(p.get("shadows", [])):
        sway = 0 if p.get("still") else np.sin(t * 0.7 + i * 2) * 2
        hx = x + sx - p["rect"][0] + sway
        hr = 7 * size
        base = y + h
        _rect(c, hx - hr, base - hr * 2.4, hr * 2, hr * 2.4, _C(p, "shadow", "ash1"))
        _disc(c, hx, base - hr * 2.4 - hr * 0.8, hr * 0.9, _C(p, "shadow", "ash1"))
    _line(c, x + w / 2, y, x + w / 2, y + h, _C(p, "seam", "ash2"))


def candles(c, p, ox, t):
    """Candles on saucers in pools of wax on a camp table."""
    for i, x in enumerate(p.get("xs", [])):
        y = p.get("y", 120)
        _rect(c, x - ox - 3, y, 7, 1, RGB["ash4"])
        _rect(c, x - ox - 1, y - 4, 2, 4, RGB["bone"])
        fl = 1 if np.sin(t * 11 + i * 3) > 0 else 0
        _put(c, x - ox, y - 5 - fl, RGB["flame"])
        _put(c, x - ox, y - 6 - fl, RGB["ember2"])


def coats(c, p, ox, t):
    """Six silk coats on six hooks, hung exactly level."""
    x0, y = p["pos"][0] - ox, p["pos"][1]
    for k in range(p.get("n", 6)):
        x = x0 + k * p.get("gap", 22)
        _put(c, x + 4, y - 2, RGB["ink1"])
        _fill_poly(c, [(x, y), (x + 9, y), (x + 11, y + 30), (x - 2, y + 30)], _C(p, "color", "ash3"))
        _line(c, x + 4, y, x + 4, y + 30, RGB["ash2"])


def table(c, p, ox, t):
    """A table laid for n: bread boards, no bread."""
    x, y, w = p["pos"][0] - ox, p["pos"][1], p.get("width", 120)
    _rect(c, x - w / 2, y, w, 3, _C(p, "color", "rust0"))
    _rect(c, x - w / 2, y, w, 1, RGB["rust1"])
    _rect(c, x - w / 2 + 3, y + 3, 3, 26, RGB["rust0"])
    _rect(c, x + w / 2 - 6, y + 3, 3, 26, RGB["rust0"])
    n = p.get("n", 6)
    for k in range(n):
        bx = x - w / 2 + 8 + k * (w - 16) / max(1, n - 1)
        _rect(c, bx - 4, y - 1, 8, 1, RGB["ash3"])


def slate(c, p, ox, t):
    """The bond-board: black slate, family names and tally strokes washed to chalk ghosts.
    `wet` adds a drip running down from the bottom edge."""
    x, y, w, h = p["rect"]
    x -= ox
    _rect(c, x - 2, y - 2, w + 4, h + 4, RGB["rust0"])
    _rect(c, x, y, w, h, _C(p, "color", "ink2"))
    rng = np.random.default_rng(p.get("seed", 21))
    rows = int(h / p.get("row", 8))
    for r in range(rows):
        yy = y + 3 + r * p.get("row", 8)
        nw = rng.integers(int(w * 0.25), int(w * 0.5))
        for k in range(int(nw)):
            if rng.random() < 0.5:
                _put(c, x + 3 + k, yy + rng.integers(0, 2), _C(p, "ghost", "ash0"))
        for k in range(rng.integers(2, 9)):  # tally strokes
            _line(c, x + w * 0.6 + k * 3, yy - 1, x + w * 0.6 + k * 3, yy + 2, _C(p, "ghost", "ash0"))
    if p.get("wet"):
        _dither_rect(c, x, y, w, h, RGB["ash0"], 0.08)


def ring(c, p, ox, t):
    """An iron ring at wrist height, the stone under it stained dark."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    s = p.get("size", 1)
    _dither_rect(c, x - 6 * s, y + 2 * s, 12 * s, 26 * s, RGB["ink1"], 0.5)
    _rect(c, x - s, y - 2 * s, 2 * s, 3 * s, RGB["ink1"])
    _disc(c, x, y + 4 * s, 4 * s, _C(p, "color", "rust0"), ring=True)
    _disc(c, x, y + 4 * s, 4 * s - 1, _C(p, "color", "rust0"), ring=True)
    if p.get("drip"):  # a drip gathering and falling
        u = (t % 1.6) / 1.6
        dy = 0 if u < 0.6 else (u - 0.6) * 60 * s
        _put(c, x, y + 9 * s + dy, RGB["cold2"])


def smokeline(c, p, ox, t):
    """A smouldering smoke line lying flat along a field edge, gnats lifting off it."""
    H, W = c.shape[:2]
    y = p.get("y", 140)
    x0, x1 = p.get("x", [0, 320])
    col = _C(p, "color", "ash3")
    for x in range(int(x0 - ox), int(x1 - ox)):
        if 0 <= x < W:
            thick = 2 + 2 * np.sin(x * 0.07 + t * 0.6)
            for k in range(int(thick)):
                yy = int(y - k + np.sin(x * 0.11 - t) * 1.5)
                if 0 <= yy < H and threshold(1, 1, x, yy)[0, 0] < 0.55 - k * 0.1:
                    c[yy, x] = col
            if np.sin(x * 0.3 + t * 2) > 0.9:
                _put(c, x, y - 4 - int((t * 9 + x) % 20), RGB["ember1"])


def scent(c, p, ox, t):
    """Auk's scent view: two dithered trails splitting at his feet, rust and moss."""
    H, W = c.shape[:2]
    x0, y0 = p["pos"][0] - ox, p["pos"][1]
    grow = min(1.0, t / p.get("grow", 1.5))
    for k, (col, dx, wob) in enumerate(((p.get("a", "rust1"), -1, 0.7), (p.get("b", "moss1"), 1, 1.1))):
        for i in range(int(110 * grow)):
            f = i / 110
            x = x0 + dx * f * p.get("reach", 140) + np.sin(f * 9 * wob + t * 1.5) * 6 * f
            y = y0 - f * p.get("rise", 50)
            w = 3 + 6 * (1 - f)
            for j in range(-int(w), int(w) + 1):
                xx, yy = int(x + j), int(y)
                if 0 <= xx < W and 0 <= yy < H and threshold(1, 1, xx, yy)[0, 0] < 0.6 * (1 - abs(j) / (w + 1)):
                    c[yy, xx] = RGB[col]


def feet(c, p, ox, t):
    """A ring of bare feet stopped on the same step at the edge of the light (low, close)."""
    xs = p.get("xs", list(range(10, 320, 34)))
    y = p.get("y", 170)
    s = p.get("size", 3)
    col = _C(p, "color", "ash2")
    for x in xs:
        for d in (0, 5 * s):
            _rect(c, x - ox + d, y - 9 * s, 3 * s, 9 * s, col)
            _rect(c, x - ox + d, y - 2 * s, 5 * s, 2 * s, col)
            _rect(c, x - ox + d, y - 9 * s, 3 * s, 1, RGB["ash3"])
    if p.get("edge"):  # the edge of the ember light on the cobbles
        _dither_rect(c, 0, y, c.shape[1], 3, RGB["ember0"], 0.5)


def broomheads(c, p, ox, t):
    """Cobble-level insert: three broom heads sweeping into frame and out in one stroke."""
    period = p.get("period", 1.4)
    u = (t % period) / period
    x = -80 + 380 * (0.5 - 0.5 * np.cos(np.pi * u)) if p.get("moving", True) else p.get("x", 160)
    for k in range(p.get("n", 3)):
        bx, by = x + k * 70 - ox, p.get("y", 160) - k * 2
        _line(c, bx + 6, by - 24, bx + 26, by - 90, RGB["rust0"], 3)
        _fill_poly(c, [(bx - 10, by), (bx + 22, by), (bx + 14, by - 22), (bx, by - 22)], RGB["ash3"])
        for j in range(-8, 22, 3):
            _line(c, bx + j, by, bx + j + 2, by - 18, RGB["ash2"])


def hand(c, p, ox, t):
    """A thin child's hand coming out of a slot, palm up, the nails split. `cake` puts a
    cricket-meal cake on the palm. Insert scale: the hand is ~60 px long."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    s = p.get("size", 1.0)
    col = _C(p, "color", "ash3")
    dark = RGB["ash1"]
    _line(c, x - 70 * s, y + 4 * s, x, y, col, int(7 * s))  # the forearm, thin as a twig
    _fill_poly(c, [(x - 4 * s, y - 4 * s), (x + 14 * s, y - 6 * s), (x + 16 * s, y + 6 * s), (x - 2 * s, y + 8 * s)], col)
    for k in range(4):  # fingers, slightly curled
        fy = y - 4 * s + k * 3.2 * s
        _line(c, x + 15 * s, fy, x + 27 * s, fy - 3 * s + k * s, col, int(2.4 * s))
        _put(c, x + 27 * s, fy - 3 * s + k * s, RGB["ash5"])
        _put(c, x + 26 * s, fy - 3 * s + k * s, RGB["ink2"])  # the split nail
    _line(c, x + 2 * s, y - 6 * s, x + 12 * s, y - 13 * s, col, int(2.6 * s))  # thumb
    _line(c, x, y + 6 * s, x + 14 * s, y + 5 * s, dark, 1)
    if p.get("cake"):
        _fill_poly(c, [(x + 2 * s, y - 8 * s), (x + 16 * s, y - 9 * s), (x + 17 * s, y - 2 * s), (x + 3 * s, y - 1 * s)], RGB["rust1"])
        for k in range(6):
            _put(c, x + (4 + k * 2) * s, y - (5 + (k % 2)) * s, RGB["rust0"])


def eye_slot(c, p, ox, t):
    """A woman's eye and mouth in a peep slot cut in mud, nothing else of her."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    w, h = p.get("w", 160), p.get("h", 50)
    _rect(c, x - w / 2, y - h / 2, w, h, RGB["ink0"])
    blink = int(t * 12) % 41 in (0, 1)
    ex, ey = x - w * 0.18, y - h * 0.12
    if not blink:
        _fill_poly(c, [(ex - 14, ey), (ex, ey - 6), (ex + 14, ey), (ex, ey + 5)], RGB["ash3"])
        _disc(c, ex + 2, ey, 4.5, RGB["ink1"])
        _put(c, ex + 3, ey - 2, RGB["bone"])
    else:
        _line(c, ex - 14, ey, ex + 14, ey, RGB["ash1"], 2)
    _dither_rect(c, x - w / 2, y - h / 2, w, h, RGB["ash0"], 0.12)
    talk = p.get("talk", True) and np.sin(t * 9) > 0
    mx, my = x + w * 0.12, y + h * 0.3
    _line(c, mx - 12, my, mx + 12, my, RGB["ash1"], 2)
    if talk:
        _rect(c, mx - 7, my + 1, 14, 3, RGB["ink1"])
    # the rough edge of the slot
    _rect(c, x - w / 2 - 4, y - h / 2 - 4, w + 8, 4, _C(p, "wall", "ash1"))
    _rect(c, x - w / 2 - 4, y + h / 2, w + 8, 4, _C(p, "wall", "ash1"))


def bowl(c, p, ox, t):
    """Insert from above: a clay bowl of water, a face reflected and broken by drinking lips;
    `dry` fills it with a crust of dead gnats instead."""
    x, y, r = p["pos"][0] - ox, p["pos"][1], p.get("r", 50)
    _disc(c, x, y, r, RGB["rust0"])
    _disc(c, x, y, r - 1, RGB["rust1"], ring=True)
    _disc(c, x, y, r * 0.86, _C(p, "water", "cold1") if not p.get("dry") else RGB["ink2"])
    H, W = c.shape[:2]
    if p.get("dry"):
        rng = np.random.default_rng(4)
        for _ in range(int(r * r * 0.8)):
            a, d = rng.uniform(0, 6.28), rng.uniform(0, r * 0.84)
            _put(c, x + np.cos(a) * d, y + np.sin(a) * d, RGB["ink0"] if rng.random() < 0.6 else RGB["ash1"])
        return
    sky = _C(p, "sky", "sky2")
    _disc(c, x - r * 0.3, y - r * 0.35, r * 0.25, sky)
    if p.get("face", True):  # the reflected face: hood, the dark of it, a pale cheek and beard
        ripple = np.sin(t * 6) * 3
        _disc(c, x + ripple, y, r * 0.42, RGB["ink1"])
        _disc(c, x + 3 + ripple, y + 2, r * 0.25, RGB["ash1"])
        for k in range(5):
            _put(c, x + ripple + k * 2 - 4, y + r * 0.3, RGB["ash2"])
    for k in range(3):  # rings out from the lips
        rr = (t * 14 + k * r * 0.3) % (r * 0.85)
        _disc(c, x + 4, y + 8, rr, _C(p, "ring_color", "cold2"), ring=True)


def forearm(c, p, ox, t):
    """Auk's bare forearm, close: scars laddered from the wrist up under the sleeve."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    _line(c, x - 150, y + 20, x + 100, y - 10, RGB["ash1"], 34)
    _fill_poly(c, [(x + 80, y - 40), (x + 170, y - 60), (x + 180, y + 40), (x + 90, y + 50)], RGB["ink2"])  # the sleeve
    _line(c, x + 80, y - 40, x + 90, y + 50, RGB["ink1"], 2)
    for k in range(p.get("scars", 12)):
        sx = x - 120 + k * 17
        sy = y + 22 - k * 2.0
        _line(c, sx, sy, sx + 6, sy + 22, RGB["ash3"], 2)
        _line(c, sx + 1, sy + 1, sx + 7, sy + 23, RGB["ash0"], 1)


def cord(c, p, ox, t):
    """The silk cord with a knot per name; `tie` animates fingers pulling the newest tight."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    n = p.get("knots", 8)
    pts = [(x - 150 + k * 300 / 40, y + np.sin(k * 0.4) * 6) for k in range(41)]
    for a, b in zip(pts, pts[1:]):
        _line(c, a[0], a[1], b[0], b[1], _C(p, "color", "ash4"), 3)
    for k in range(n):
        kx, ky = pts[int(4 + k * 32 / max(1, n))]
        _disc(c, kx, ky + 1, 4, _C(p, "color", "ash4"))
        _disc(c, kx + 1, ky + 2, 2, RGB["ash2"])
    if p.get("tie"):
        u = (t % 1.2) / 1.2
        fx = pts[36][0] + 8 + u * 10
        for side in (-1, 1):
            _line(c, fx - 30, y + side * 26, fx, y + side * 6, RGB["ash2"], 8)
            _disc(c, fx + 2, y + side * 6, 5, RGB["ash2"])


def clamp(c, p, ox, t):
    """A bone-handled clamp on a cut length of copper wire, hanging on a nail."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    s = p.get("size", 1.0)
    _rect(c, x - 2 * s, y - 2 * s, 4 * s, 4 * s, RGB["ink1"])  # the nail
    sw = np.sin(t * 0.8) * 2
    _line(c, x, y, x - 6 * s + sw, y + 40 * s, RGB["rust1"], max(1, int(2 * s)))  # copper
    _line(c, x - 6 * s + sw, y + 40 * s, x - 3 * s + sw, y + 60 * s, RGB["rust1"], max(1, int(2 * s)))
    jx, jy = x - 3 * s + sw, y + 60 * s
    _fill_poly(c, [(jx - 4 * s, jy), (jx + 4 * s, jy), (jx + 3 * s, jy + 14 * s), (jx - 3 * s, jy + 14 * s)], RGB["ash1"])
    _line(c, jx - 5 * s, jy + 14 * s, jx - 8 * s, jy + 40 * s, RGB["bone"], max(1, int(5 * s)))
    _line(c, jx + 3 * s, jy + 14 * s, jx + 6 * s, jy + 40 * s, RGB["bone"], max(1, int(5 * s)))


def leads(c, p, ox, t):
    """The rig's own bone-handled leads hanging from Auk's frame (match for the clamp)."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    s = p.get("size", 1.0)
    _rect(c, x - 40 * s, y - 70 * s, 18 * s, 180 * s, RGB["ink1"])  # the iron pole
    for k in range(2):
        lx = x + k * 30 * s
        sw = np.sin(t * 0.8 + k) * 2
        _line(c, x - 22 * s, y - 40 * s + k * 10, lx + sw, y + 30 * s, RGB["ink2"], max(1, int(2 * s)))
        _fill_poly(c, [(lx - 4 * s + sw, y + 30 * s), (lx + 4 * s + sw, y + 30 * s), (lx + 3 * s + sw, y + 44 * s), (lx - 3 * s + sw, y + 44 * s)], RGB["ash1"])
        _line(c, lx - 5 * s + sw, y + 44 * s, lx - 8 * s + sw, y + 70 * s, RGB["bone"], max(1, int(5 * s)))
        _line(c, lx + 3 * s + sw, y + 44 * s, lx + 6 * s + sw, y + 70 * s, RGB["bone"], max(1, int(5 * s)))


def boots(c, p, ox, t):
    """Insert: a pair of boots on stairs; `steps` climbs n stairs then stops dead."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    n, period = p.get("climb", 3), p.get("period", 0.6)
    k = min(n, int(t / period))
    for j in range(5):
        _rect(c, -10 + j * 70 - ox * 0, y - j * 22 + 30, 400, 22, RGB["ash2"] if j % 2 else RGB["ash1"])
        _rect(c, -10 + j * 70, y - j * 22 + 30, 400, 1, RGB["ash3"])
    bx, by = 30 + k * 70, y - k * 22 + 30
    for side, dx in ((0, 0), (1, 26)):
        lift = 8 if (t % period) / period < 0.5 and k < n and side == k % 2 else 0
        _rect(c, bx + dx, by - 40 - lift, 14, 40, RGB["ash0"])
        _rect(c, bx + dx, by - 12 - lift, 26, 12, RGB["rust0"])
        _rect(c, bx + dx, by - 12 - lift, 26, 1, RGB["rust1"])


def faces(c, p, ox, t):
    """The stack of carved faces on the iron pole, close, lit from inside; frost on the housings.
    Light runs up the stack when `light` is [t0, t1]."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    s = p.get("size", 1.0)
    n = p.get("n", 5)
    _rect(c, x - 5 * s, y - 200 * s, 10 * s, 400 * s, RGB["ink1"])
    t0, t1 = p.get("light", [-1, 0])
    for k in range(n):
        fy = y - k * 34 * s
        lit = t >= t0 + (t1 - t0) * k / max(1, n)
        w, h = 34 * s, 28 * s
        _rect(c, x - w / 2, fy - h / 2, w, h, RGB[("rust1", "ash1", "rust0", "ash2", "rust1")[k % 5]])
        _rect(c, x - w / 2, fy - h / 2, w, 2, RGB["ash4"])
        for ex in (-0.22, 0.22):
            col = RGB["ember2"] if lit else RGB["ink0"]
            _rect(c, x + ex * w - 2 * s, fy - 3 * s, 4 * s, 3 * s, col)
        _line(c, x - 4 * s, fy + 7 * s, x + 4 * s, fy + 7 * s, RGB["ink1"], max(1, int(2 * s)))
        if lit:
            _dither_rect(c, x - w / 2, fy + 4 * s, w, h / 2 - 4 * s, RGB["ember0"], 0.4)
        rng = np.random.default_rng(k)
        for _ in range(int(6 * s)):  # frost on the housing
            if np.sin(t * 2 + rng.uniform(0, 6)) > 0:
                _put(c, x + rng.uniform(-w / 2, w / 2), fy - h / 2 + rng.uniform(0, 3), RGB["bone"])


def line(c, p, ox, t):
    """A straight or bent line: a rope, a pole, a crack. `creep` slides a texture along it."""
    pts = [(x - ox, y) for x, y in p["points"]]
    col = _C(p, "color", "ink1")
    for a, b in zip(pts, pts[1:]):
        _line(c, a[0], a[1], b[0], b[1], col, p.get("thick", 1))
    if p.get("creep"):  # fibres moving along a hauled rope
        (x0, y0), (x1, y1) = pts[0], pts[-1]
        L = max(1.0, np.hypot(x1 - x0, y1 - y0))
        for k in range(int(L / 6)):
            f = ((k * 6 + t * p["creep"]) % L) / L
            _put(c, x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, _C(p, "fibre", "ash3"))


def back(c, p, ox, t):
    """A long dark back breaking the surface far out, once, and sliding under."""
    x, y = p["pos"][0] - ox, p["pos"][1]
    t0, dur = p.get("at", 0.3), p.get("dur", 1.4)
    u = (t - t0) / dur
    if not 0 <= u <= 1:
        return
    L = p.get("length", 40)
    h = np.sin(np.pi * u) * p.get("height", 4)
    xs = np.arange(int(L))
    for k in xs:
        f = k / L
        hh = h * np.sin(np.pi * f) * (1 if f > u * 0.6 else 0.4)
        if hh >= 0.5:
            _rect(c, x + k - L / 2 + u * 10, y - hh, 1, hh, _C(p, "color", "ink0"))
    _line(c, x - L / 2 - 4, y, x + L / 2 + 14, y, _C(p, "wake", "cold2"))


DRAW = {f.__name__: f for f in (line, back,
    slab, poly, haze, stripes, water, levee, fields, stubble, reeds, willow, frost, sun, stars,
    wall, waterstone, town, wheel, gear, chain, pegs, tripod, awning, fountain, facades, bench, cobbles,
    crates, quern, grate, steps, body, sheets, cart, spokes, trench, lantern, moths, flies, tent, candles,
    coats, table, slate, ring, smokeline, scent, feet, broomheads, hand, eye_slot, bowl, forearm, cord,
    clamp, leads, boots, faces)}
EMISSIVE = {"lantern", "candles", "sun"}
