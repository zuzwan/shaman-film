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

Foreground framing: give a prop `layer: front` and it draws over the actors
(use parallax above 1, e.g. 1.6, so it slides faster than the world):
      - {type: trunk, pos: [20, 180], width: 22, layer: front, parallax: 1.6}
      - {type: grass, y: 180, height: 16, layer: front, parallax: 1.5, seed: 2}
      - {type: doorway, rect: [70, 20, 180, 150], layer: front}   # the "framed" / pov shot
      - {type: branches, x: 0, width: 140, depth: 40, layer: front, parallax: 1.3, seed: 5}
      - {type: shoulder, side: left, layer: screen}               # over-the-shoulder: a dark head and shoulder
`layer: screen` props are pinned to the frame and drawn after the camera zoom.

The Survey's map (an insert on a `plain` backdrop with paper-coloured sky stops):
      - {type: contours, pos: [160, 90], rings: 6, step: 9, color: ash2, seed: 1}
      - {type: route, points: [[40, 150], [90, 120], [150, 96]], color: blood2, progress: [0.5, 3.0], dash: 3}
      - {type: marker, pos: [150, 96], label: SALT, color: ink1}
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


def trunk(c, p, ox, t):
    """A tree trunk close to camera: a dark vertical band with a bark rim."""
    H, W = c.shape[:2]
    x = int(p["pos"][0] - ox)
    w = int(p.get("width", 20))
    col, rim = RGB[p.get("color", "ink0")], RGB[p.get("rim", "ink2")]
    rng = np.random.default_rng(p.get("seed", 0))
    wob = np.cumsum(rng.integers(-1, 2, H)).clip(-2, 2)
    for y in range(H):
        x0, x1 = max(0, x + wob[y]), min(W, x + w + wob[y])
        if x0 < x1:
            c[y, x0:x1] = col
            if 0 <= x1 - 1 < W and y % 5 != 0:
                c[y, x1 - 1] = rim


def grass(c, p, ox, t):
    """Tufts along the bottom of frame, swaying a little."""
    H, W = c.shape[:2]
    rng = np.random.default_rng(p.get("seed", 0))
    base, hmax = p.get("y", H), p.get("height", 14)
    col = RGB[p.get("color", "ink0")]
    span = W + 400
    for _ in range(int(span / 2)):
        gx = rng.uniform(0, span)
        h = rng.uniform(hmax * 0.3, hmax)
        lean = rng.uniform(-0.4, 0.4) + np.sin(t * 1.4 + gx * 0.05) * 0.15
        x0 = (gx - ox) % span - 200
        if -10 < x0 < W + 10:
            _line(c, x0, base, x0 + lean * h, base - h, col)
    c[min(H - 1, base - 2):base] = col


def doorway(c, p, ox, t):
    """Everything dark except an opening: shoot through a door, window or ruin arch."""
    H, W = c.shape[:2]
    x, y, w, h = p["rect"]
    x -= ox
    col = RGB[p.get("color", "ink0")]
    m = np.ones((H, W), dtype=bool)
    yy, xx = np.mgrid[0:H, 0:W]
    inside = (xx >= x) & (xx < x + w) & (yy >= y) & (yy < y + h)
    if p.get("arch", True):  # round the top of the opening
        r = w / 2
        cx, cy = x + r, y + r
        inside &= (yy >= cy) | ((xx - cx) ** 2 + (yy - cy) ** 2 <= r * r)
    m &= ~inside
    c[m] = col
    if p.get("rim"):  # light catching the edge of the frame
        edge = m & ~np.roll(m, 1, axis=1)
        c[edge] = RGB[p["rim"]]


def branches(c, p, ox, t):
    """Dead branches hanging into the top of frame, close to camera."""
    rng = np.random.default_rng(p.get("seed", 0))
    col = RGB[p.get("color", "ink0")]
    x0, width, depth = p.get("x", 0) - ox, p.get("width", 120), p.get("depth", 40)

    def br(x, y, ang, length, thick, d):
        if d == 0 or length < 2:
            return
        a = ang + np.sin(t * 0.9 + d) * 0.02
        x1, y1 = x + np.cos(a) * length, y + np.sin(a) * length
        _line(c, x, y, x1, y1, col, max(1, thick))
        for _ in range(2):
            br(x1, y1, a + rng.uniform(-0.7, 0.7), length * rng.uniform(0.5, 0.75), thick - 1, d - 1)

    br(x0, -2, rng.uniform(0.15, 0.5), width * 0.45, 3, 6)
    br(x0 + width * 0.3, -2, rng.uniform(0.9, 1.3), depth * 0.6, 2, 5)


def shoulder(c, p, ox, t):
    """The back of a hooded head and a shoulder in silhouette, filling a lower corner."""
    H, W = c.shape[:2]
    col = RGB[p.get("color", "ink0")]
    left = p.get("side", "left") == "left"
    hx = int(p.get("x", 64 if left else W - 64))
    hy = int(p.get("y", 98))
    r = int(p.get("radius", 32))
    yy, xx = np.mgrid[0:H, 0:W]
    head = ((xx - hx) / r) ** 2 + ((yy - hy) / (r * 1.1)) ** 2 <= 1
    hood = (abs(xx - hx) <= (yy - (hy - r * 1.25)) * 1.7) & (yy >= hy - r * 1.25) & (yy <= hy)  # a soft hood peak
    sy = hy + r * 0.8
    if left:
        body = (yy >= sy + np.maximum(0, xx - hx) * 0.45) & (xx <= hx + r * 2.2)
    else:
        body = (yy >= sy + np.maximum(0, hx - xx) * 0.45) & (xx >= hx - r * 2.2)
    m = head | hood | body
    c[m] = col
    if p.get("rim"):  # a little light on the edge, so it reads as a figure not a hole
        edge = m & ~np.roll(m, -1 if left else 1, axis=1)
        c[edge] = RGB[p["rim"]]


def contours(c, p, ox, t):
    """Map contour rings: wobbly closed loops around a summit."""
    cx, cy = p["pos"][0] - ox, p["pos"][1]
    rng = np.random.default_rng(p.get("seed", 0))
    col = RGB[p.get("color", "ash2")]
    k = rng.integers(2, 5, 3)
    ph = rng.uniform(0, 6.28, 3)
    sq = p.get("squash", 0.6)
    for i in range(1, int(p.get("rings", 5)) + 1):
        r = i * p.get("step", 8)
        prev = None
        for a in np.linspace(0, 2 * np.pi, int(12 + r * 1.2)):
            wob = 1 + 0.12 * np.sin(k[0] * a + ph[0]) + 0.08 * np.sin(k[1] * a + ph[1]) + 0.05 * np.sin(k[2] * a + ph[2])
            x, y = cx + np.cos(a) * r * wob, cy + np.sin(a) * r * wob * sq
            if prev:
                _line(c, prev[0], prev[1], x, y, col)
            prev = (x, y)


def route(c, p, ox, t):
    """A dashed line along `points`, drawn progressively between `progress: [t0, t1]`."""
    pts = [(x - ox, y) for x, y in p["points"]]
    col = RGB[p.get("color", "blood2")]
    dash = p.get("dash", 3)
    t0, t1 = p.get("progress", [0, 0])
    f = 1.0 if t1 <= t0 else min(1.0, max(0.0, (t - t0) / (t1 - t0)))
    seg = [np.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1)]
    total = sum(seg) or 1
    budget = f * total
    d = 0.0
    for (x0, y0), (x1, y1), L in zip(pts, pts[1:], seg):
        if budget <= 0:
            break
        n = int(L) + 1
        for i in range(n):
            if d > budget:
                break
            if dash and int(d) % (dash * 2) < dash:
                g = i / max(1, n - 1)
                _put(c, int(round(x0 + (x1 - x0) * g)), int(round(y0 + (y1 - y0) * g)), col)
            d += L / max(1, n - 1)
    if 0 < f < 1 and p.get("pen", True):  # the pen's tip
        x, y = _along(pts, seg, f)
        c[max(0, int(y) - 1):int(y) + 2, max(0, int(x) - 1):int(x) + 2] = RGB[p.get("pen_color", "ink0")]


def _along(pts, seg, f):
    d = f * sum(seg)
    for (x0, y0), (x1, y1), L in zip(pts, pts[1:], seg):
        if d <= L or L == seg[-1]:
            g = d / L if L else 0
            return x0 + (x1 - x0) * g, y0 + (y1 - y0) * g
        d -= L
    return pts[-1]


def marker(c, p, ox, t):
    """A town on the map: a small square and a 3x5 label above it."""
    from .font import text_mask
    x, y = int(p["pos"][0] - ox), int(p["pos"][1])
    col = RGB[p.get("color", "ink1")]
    c[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = col
    if p.get("label"):
        m = text_mask(str(p["label"]).upper())
        h, w = m.shape
        lx, ly = x - w // 2, y - h - 3
        H, W = c.shape[:2]
        if 0 <= lx and lx + w <= W and 0 <= ly and ly + h <= H:
            c[ly:ly + h, lx:lx + w][m] = col


EMISSIVE = {"fire", "eyes", "wanderlight"}
DRAW = {"moon": moon, "tree": tree, "ruin": ruin, "fire": fire,
        "eyes": eyes, "wanderlight": wanderlight, "presence": presence,
        "trunk": trunk, "grass": grass, "doorway": doorway, "branches": branches,
        "shoulder": shoulder, "contours": contours, "route": route, "marker": marker}


def draw(c, props, cam_x, t):
    for p in props:
        DRAW[p["type"]](c, p, cam_x * p.get("parallax", 1.0), t)
