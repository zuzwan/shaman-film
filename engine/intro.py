"""The intro: the show's title card, then a small episode card, on every episode.

    intro: {episode: 3}                  # in an episode's timeline.yaml

render.py puts it in front of the first scene as `s00_intro`. The title, the
card's style and the act colours come from assets/show.yaml. Full 320x180
frame, no text band, INTRO_LENGTH seconds:

    0.0  black
    0.6  the card builds (each style its own way)
    4.5  the title lands                                  <- the sting hits here
    8.0  dither to black
    9.0  "Episode Three", small, on black
   12.0  the episode cuts in

Styles (all share the carved lettering in engine/titlefont.py):
    swarm   dusk over the act's country; a cloud of gnats gathers into the
            letters and they set into carved bone. The insect economy.
    ember   letters cut into dark planks; an ember runs along their inline
            like a fuse and leaves them burning. The capture's light.
    plate   an old almanac plate: aged paper, ruled frame, a frieze of insects,
            the title stamped in ink with an ember inline.

Sound is not built yet. STING marks the window the score will fill; render.py
writes it to out/<ep>/cues.yaml for the audio pass.
"""
from pathlib import Path

import numpy as np
import yaml

from . import textfont, titlefont
from .dither import mask, threshold
from .palette import RGB
from .scene import Scene

INTRO_LENGTH = 12.0
BUILD = (0.6, 4.5)            # the card builds; the title lands at the end
TITLE_OUT = (8.0, 8.8)
EPISODE = (9.0, 11.6)         # the episode card, dithered in and out
STING = {"start": BUILD[0], "hit": BUILD[1], "end": TITLE_OUT[1]}

NUMBERS = ("Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen "
           "Fifteen Sixteen Seventeen Eighteen Nineteen Twenty").split()


def show(path=None):
    path = Path(path or Path(__file__).resolve().parents[1] / "assets/show.yaml")
    return yaml.safe_load(open(path))


def words(n):
    return NUMBERS[n] if n <= 20 else f"Twenty-{NUMBERS[n - 20].lower()}"


def _ease(f):
    f = min(max(f, 0.0), 1.0)
    return f * f * (3 - 2 * f)


def _shift(m, dy, dx):
    return titlefont._shift(m, dy, dx)


def _erode(m, k=1):
    for _ in range(k):
        m = m & _shift(m, 1, 0) & _shift(m, -1, 0) & _shift(m, 0, 1) & _shift(m, 0, -1)
    return m


def inline(m):
    """An engraved line running inside each stroke, two pixels in from the edge."""
    inner = _erode(m, 2)
    return inner & ~_erode(inner, 1)


# small insect emblems for ornament, drawn facing right
INSECTS = {
    "moth": ["#...#...#", "##..#..##", "###.#.###", "####.####", ".##.#.##.", "..#.#.#..", ".#.....#."],
    "cricket": ["........#.#", ".......#...", "..#####....", ".#######.#.", "##########.", ".#.#..#.#..", "#..#..#..#."],
    "bee": ["...#.#...", "....#....", ".##.#.##.", "#########", ".#.#.#.#.", "..#####..", "...#.#..."],
    "beetle": ["..#...#..", "...###...", "..#####..", ".###.###.", ".###.###.", ".###.###.", "..##.##.."],
}


def _bitmap(rows):
    return np.array([[ch == "#" for ch in r] for r in rows], dtype=bool)


def _paint(c, m, x, y, col, amount=1.0):
    h, w = m.shape
    H, W = c.shape[:2]
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    sub = m[y0 - y:y1 - y, x0 - x:x1 - x]
    if amount < 1:
        sub = sub & (threshold(y1 - y0, x1 - x0, x0, y0) < amount)
    c[y0:y1, x0:x1][sub] = RGB[col]


# What stands behind the swarm card. The title owns the middle of the frame
# (about x 60-260, y 50-125), so scenery keeps to the horizon, the edges and
# the foreground. Pick one with `scenery:` in assets/show.yaml.
SCENERY = {
    "plain": {},
    # river country at dusk: mill chimneys on the horizon, each with its smoke line
    "mills": {"props": [
        {"type": "moon", "pos": [276, 112], "r": 9, "halo": 26, "glow": 0.45, "color": "blood4",
         "halo_color": "blood3", "maria": 0, "layer": -1, "parallax": 0},
        {"type": "ruin", "pos": [22, 140], "width": 18, "height": 22, "arches": 1, "seed": 2, "color": "ink2", "layer": 0},
        {"type": "smoke", "pos": [30, 119], "height": 70, "lean": 0.5, "color": "ash3", "seed": 1, "spread": 11, "layer": 0},
        {"type": "ruin", "pos": [138, 141], "width": 14, "height": 14, "arches": 1, "seed": 5, "color": "ink2", "layer": 0},
        {"type": "smoke", "pos": [144, 128], "height": 36, "lean": 0.9, "color": "ash2", "seed": 2, "spread": 8, "layer": 0},
        {"type": "ruin", "pos": [282, 142], "width": 20, "height": 26, "arches": 1, "seed": 7, "color": "ink2", "layer": 0},
        {"type": "smoke", "pos": [292, 117], "height": 75, "lean": 0.4, "color": "ash3", "seed": 3, "spread": 11, "layer": 0},
        {"type": "gnats", "pos": [80, 168], "columns": 2, "spread": 60, "height": 34, "count": 26, "seed": 4},
        {"type": "gnats", "pos": [236, 170], "columns": 2, "spread": 50, "height": 30, "count": 22, "seed": 9},
        {"type": "grass", "height": 9, "color": "ink0", "seed": 3, "layer": "front"}]},
    # a dead orchard framing the card, marsh lights low in the rows
    "orchard": {"props": [
        {"type": "moon", "pos": [160, 150], "r": 11, "halo": 30, "glow": 0.4, "color": "blood4",
         "halo_color": "blood3", "maria": 0, "layer": -1, "parallax": 0},
        {"type": "tree", "pos": [92, 150], "height": 26, "seed": 21, "color": "ink2", "thick": 1, "depth": 5, "layer": 1},
        {"type": "tree", "pos": [214, 150], "height": 24, "seed": 22, "color": "ink2", "thick": 1, "depth": 5, "layer": 1},
        {"type": "tree", "pos": [128, 152], "height": 18, "seed": 23, "color": "ink2", "thick": 1, "depth": 4, "layer": 1},
        {"type": "tree", "pos": [22, 178], "height": 120, "seed": 11, "color": "ink0", "thick": 5, "depth": 7},
        {"type": "tree", "pos": [300, 178], "height": 110, "seed": 12, "color": "ink0", "thick": 5, "depth": 7},
        {"type": "wanderlight", "pos": [160, 160], "count": 3, "spread": [160, 10], "color": "ash4", "seed": 2},
        {"type": "gnats", "pos": [160, 166], "columns": 3, "spread": 140, "height": 30, "count": 24, "seed": 3},
        {"type": "grass", "height": 12, "color": "ink0", "seed": 5, "layer": "front"}]},
    # the glass towns on the skyline: broken arcades against a low sun, gnats rising
    "towers": {"props": [
        {"type": "moon", "pos": [196, 128], "r": 13, "halo": 34, "glow": 0.5, "color": "blood4",
         "halo_color": "blood3", "maria": 0, "layer": -1, "parallax": 0},
        {"type": "ruin", "pos": [0, 150], "width": 46, "height": 70, "arches": 2, "seed": 3, "color": "ink1", "layer": 0},
        {"type": "ruin", "pos": [52, 146], "width": 30, "height": 30, "arches": 2, "seed": 4, "color": "ink2", "layer": 0},
        {"type": "ruin", "pos": [120, 146], "width": 40, "height": 22, "arches": 3, "seed": 6, "color": "ink2", "layer": 0},
        {"type": "ruin", "pos": [230, 146], "width": 34, "height": 34, "arches": 2, "seed": 8, "color": "ink2", "layer": 0},
        {"type": "ruin", "pos": [272, 152], "width": 48, "height": 82, "arches": 3, "seed": 9, "color": "ink1", "layer": 0},
        {"type": "gnats", "pos": [160, 170], "columns": 4, "spread": 220, "height": 44, "count": 30, "seed": 6}]},
    # a camp far off on the plain: a fire, its smoke, two sitting, the dead tree they chose
    "camp": {"props": [
        {"type": "tree", "pos": [252, 156], "height": 50, "seed": 4, "color": "ink1", "thick": 2, "depth": 6},
        {"type": "fire", "pos": [232, 156], "size": 0.6},
        {"type": "smoke", "pos": [232, 148], "height": 90, "lean": 0.45, "color": "ash3", "seed": 5, "spread": 10},
        {"type": "grass", "height": 10, "color": "ink0", "seed": 8, "layer": "front"}],
        "actors": [{"sprite": "auk", "state": "sit", "path": [[247, 157]], "flip": True, "breathe": 4},
                   {"sprite": "teal", "state": "sit", "path": [[216, 158]], "breathe": 3, "phase": 1.1}],
        "lights": [{"pos": [232, 152], "radius": 22, "color": "ember0", "intensity": 0.55, "flicker": True}]},
}


# The low sun in each scenery becomes a pale disc by day and the moon by night;
# smoke and gnats lighten after dark so they still read against the sky.
_SKY_DISC = {"day": {"color": "ash5", "halo_color": "sky3", "glow": 0.3},
             "night": {"color": "moon", "halo_color": "night3", "maria": 4, "glow": 0.35}}


def _at_time(sc, time):
    import copy
    sc = copy.deepcopy(sc)
    for p in sc.get("props", []):
        if p["type"] == "moon" and time in _SKY_DISC:
            p.update(_SKY_DISC[time])
            if time == "night":
                p["pos"] = [p["pos"][0], max(30, p["pos"][1] - 90)]
                p["r"] = min(p.get("r", 8), 7)
        if time == "night" and p["type"] in ("gnats",):
            p["color"] = "ash2"
        if time == "night" and p["type"] == "smoke":
            p["color"] = "night3"
    return sc


class Layout:
    """Where the lettering sits: THE over SHAMAN, centred, with rules and a device."""

    def __init__(self, title, W=320, H=180):
        parts = title.split()
        self.small = " ".join(parts[:-1]) if len(parts) > 1 else ""
        self.big = parts[-1]
        self.m = titlefont.mask(self.big, 1.0)
        self.ms = titlefont.mask(self.small, 0.42, spacing=6) if self.small else None
        h = self.m.shape[0] + (self.ms.shape[0] + 6 if self.small else 0) + 16
        self.y_small = (H - h) // 2 - 2
        self.y = self.y_small + (self.ms.shape[0] + 6 if self.small else 0)
        self.x = (W - self.m.shape[1]) // 2
        self.xs = (W - self.ms.shape[1]) // 2 if self.small else 0
        self.W, self.H = W, H
        # a full-frame mask of the big word, for effects that work in screen space
        self.full = np.zeros((H, W), dtype=bool)
        self.full[self.y:self.y + self.m.shape[0], self.x:self.x + self.m.shape[1]] = self.m
        if self.small:
            self.full[self.y_small:self.y_small + self.ms.shape[0], self.xs:self.xs + self.ms.shape[1]] |= self.ms
        self.rule_y = self.y + self.m.shape[0] + 8

    def ornament(self, c, col, amount=1.0, hi=None):
        """Rules either side of the small word, and a rule with a diamond device under the big one."""
        W = self.W
        if self.small:
            ry = self.y_small + self.ms.shape[0] // 2
            for x0, x1 in ((self.x + 2, self.xs - 7), (self.xs + self.ms.shape[1] + 6, self.x + self.m.shape[1] - 2)):
                line = np.ones((1, x1 - x0), dtype=bool)
                _paint(c, line, x0, ry, col, amount)
                _paint(c, line, x0, ry + 2, col, amount)
                for ex in (x0, x1 - 1):
                    _paint(c, _bitmap([".#.", "###", ".#."]), ex - 1, ry, col, amount)
        y = self.rule_y
        half = self.m.shape[1] // 2 - 10
        cx = W // 2
        for x0, x1 in ((cx - half, cx - 8), (cx + 8, cx + half)):
            _paint(c, np.ones((1, x1 - x0), dtype=bool), x0, y, col, amount)
        dev = _bitmap(["...#...", "..###..", ".##.##.", "##.#.##", ".##.##.", "..###..", "...#..."])
        _paint(c, dev, cx - 3, y - 3, col, amount)
        if hi:
            _paint(c, _bitmap(["#"]), cx, y, hi, amount)


class Intro(Scene):
    key_times = (2.0, 3.6, 5.0, 7.5, 10.2)

    def __init__(self, intro, cfg, show_data=None):
        s = show_data or show()
        ep = int(intro.get("episode", 1))
        region = intro.get("region") or next(
            (a["region"] for a in s.get("acts", []) if a["episodes"][0] <= ep <= a["episodes"][1]), "river")
        self.style = intro.get("style", s.get("style", "swarm"))
        self.ep = ep
        self.scenery = intro.get("scenery", s.get("scenery", "plain"))
        self.time = intro.get("time", s.get("time", "dusk"))
        sc = _at_time(SCENERY[self.scenery], self.time)
        self.gnat = "ash3" if self.time == "night" else "ink1"
        sp = {"id": "s00_intro", "duration": INTRO_LENGTH, "band": 0,
              "backdrop": {"region": region, "time": self.time, "seed": 131, "angle": "low",
                           "props": sc.get("props", [])},
              "weather": sc.get("weather", "none"),
              "actors": sc.get("actors", []), "lights": sc.get("lights", [])}
        super().__init__(sp, cfg)
        self.L = Layout(s["title"], self.W, self.H)
        self.inl = inline(self.L.full)
        rng = np.random.default_rng(131)
        # swarm: one gnat for (most of) the letter pixels, plus a few that never settle
        ys, xs = np.nonzero(self.L.full)
        keep = rng.random(len(xs)) < 0.55
        self.tx, self.ty = xs[keep].astype(float), ys[keep].astype(float)
        n = len(self.tx)
        self.sx = rng.uniform(-60, 40, n); self.sy = rng.uniform(20, 160, n)
        self.ph = rng.uniform(0, 6.28, n); self.rad = rng.uniform(4, 22, n)
        self.t0 = rng.uniform(1.4, 3.2, n) + (self.tx / self.W) * 0.6
        self.free = rng.uniform(0, 1, (60, 4))
        # ember: fuse order runs left to right with a ragged front
        self.fuse = (np.arange(self.W)[None, :] + rng.integers(0, 6, (self.H, self.W))) / (self.W + 6)
        self.sparks = rng.uniform(0, 1, (80, 4))
        yy, xx = np.mgrid[0:self.H, 0:self.W]
        dist = np.full((self.H, self.W), 99.0)
        ly, lx = np.nonzero(self.L.full)
        for dy in range(-4, 5):  # distance to the nearest letter pixel, out to 4 px
            for dx in range(-4, 5):
                d = (dx * dx + dy * dy) ** 0.5
                if d <= 4:
                    sh = _shift(self.L.full, dy, dx)
                    dist[sh] = np.minimum(dist[sh], d)
        self.halo = dist < 4.5
        self.halo_amt = np.clip(1 - dist / 4.5, 0, 1)
        self.paper = self._paper(rng)
        self.planks = self._planks(rng)

    # -- backgrounds ----------------------------------------------------
    def _planks(self, rng):
        H, W = self.H, self.W
        c = np.zeros((H, W, 3), np.uint8)
        c[:] = RGB["rust0"]
        t = threshold(H, W)
        yy, xx = np.mgrid[0:H, 0:W]
        for y0 in range(0, H, 22):
            off = rng.uniform(0, 6.28)  # long grain along the board, bending round a knot
            kx, ky = rng.uniform(20, W - 20), y0 + rng.uniform(6, 16)
            knot = 6.0 * np.exp(-(((xx - kx) / 14) ** 2 + ((yy - ky) / 5) ** 2))
            grain = np.sin(yy * 1.7 + off + 0.8 * np.sin(xx / 41 + off) + knot)
            band = (yy >= y0) & (yy < y0 + 22)
            c[band & (grain > 0.9)] = RGB["blood1"]
            c[band & (grain < -0.93)] = RGB["ink2"]
            c[yy == y0] = RGB["ink1"]
            c[yy == y0 + 1] = RGB["blood1"]
            for nx in (rng.integers(10, W - 10, 2) if y0 + 6 < H else []):
                c[y0 + 4, nx] = RGB["ash2"]; c[y0 + 5, nx] = RGB["ash0"]
        # darken toward the edges, by dither
        d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        c[t < np.clip(d - 0.55, 0, 1) * 1.6] = RGB["ink1"]
        c[t < np.clip(d - 0.95, 0, 1) * 2.5] = RGB["ink0"]
        return c

    def _paper(self, rng):
        H, W = self.H, self.W
        c = np.zeros((H, W, 3), np.uint8)
        c[:] = RGB["bone"]
        t = threshold(H, W)
        yy, xx = np.mgrid[0:H, 0:W]
        blot = sum(np.sin(xx / s1 + p) * np.sin(yy / s2 + q) for s1, s2, p, q in rng.uniform([7, 5, 0, 0], [23, 17, 6, 6], (5, 4)))
        c[t < np.clip(blot / 4, 0, 1) * 0.5] = RGB["ash5"]
        d = np.maximum(abs(xx - W / 2) / (W / 2), abs(yy - H / 2) / (H / 2))
        c[t < np.clip(d - 0.7, 0, 1) * 2.4] = RGB["ash4"]
        c[t < np.clip(d - 0.9, 0, 1) * 4] = RGB["ash3"]
        return c

    # -- styles ---------------------------------------------------------
    def _swarm(self, t, frame):
        c = super().picture(t, frame)
        L = self.L
        land = BUILD[1]
        f = np.clip((t - self.t0) / (land - 0.2 - self.t0), 0, 1)
        e = f * f * (3 - 2 * f)
        cxw = 40 + 60 * min(1.0, t / 4)  # the cloud drifts in from the left
        wx = self.sx + cxw + self.rad * np.cos(self.ph + t * 2.3)
        wy = self.sy * 0.6 + 30 + self.rad * 0.6 * np.sin(self.ph * 1.3 + t * 2.9)
        px = np.round(wx + (self.tx - wx) * e).astype(int)
        py = np.round(wy + (self.ty - wy) * e).astype(int)
        settle = _ease((t - (land - 0.3)) / 0.8)
        if settle < 1:
            ok = (px >= 0) & (px < self.W) & (py >= 0) & (py < self.H)
            on = ok & (np.round(self.ph * 3 + frame) % 5 != 0)
            c[py[on], px[on]] = RGB[self.gnat]
        if t >= land - 0.3:
            titlefont.carve(c, L.m, L.x, L.y, settle)
            if L.small:
                titlefont.carve(c, L.ms, L.xs, L.y_small, settle, shadow=1)
            c[self.inl & (threshold(self.H, self.W) < settle)] = RGB["ash3"]
            L.ornament(c, "bone", _ease((t - land - 0.4) / 0.8), hi="ink1")
        # gnats that never settle keep working the air over the letters
        for i, (a, b, p, q) in enumerate(self.free):
            x = int(L.x + a * L.m.shape[1] + 18 * np.sin(t * (1 + b) + p * 6))
            y = int(L.y - 10 + q * 60 + 8 * np.cos(t * (1.5 + a) + p * 4))
            if 0 <= x < self.W and 0 <= y < self.H and (frame + i) % 4:
                c[y, x] = RGB[self.gnat]
        return c

    def _ember(self, t, frame):
        c = self.planks.copy()
        L, H, W = self.L, self.H, self.W
        land = BUILD[1]
        front = (t - 1.0) / (land - 1.0)  # 0 -> 1 across the screen
        cut = L.full & (self.fuse < front + 0.06)
        if cut.any():
            # a cut, not a raised letter: dark floor, shadow on the top-left wall, light on the bottom-right
            c[cut] = RGB["ink1"]
            c[cut & ~_shift(cut, 1, 1)] = RGB["ink0"]
            c[cut & ~_shift(cut, -1, -1)] = RGB["rust1"]
        burning = self.inl & (self.fuse < front)
        tip = self.inl & (self.fuse >= front - 0.03) & (self.fuse < front)
        # the burning letters light the wood round them, by dither
        lit = np.clip((min(t, land + 1) - 1.0) / (land - 1.0), 0, 1)
        if lit > 0:
            near = self.halo & (self.fuse < front) & ~cut
            c[near & (threshold(H, W) < self.halo_amt * lit * 0.6)] = RGB["rust1"]
            c[near & (threshold(H, W, 2, 1) < self.halo_amt * lit * 0.25)] = RGB["blood2"]
            c[cut & (self.fuse < front) & (threshold(H, W) < 0.5)] = RGB["blood0"]
        if t < land:
            c[burning] = RGB["ember1"]
            c[burning & (threshold(H, W) < 0.3)] = RGB["ember0"]
            c[tip] = RGB["flame"]
            c[_shift(tip, 0, 1) & cut] = RGB["ember2"]
        else:
            k = t - land
            if k < 2 / self.fps:
                c[self.inl] = RGB["flame"]
            else:
                pulse = 0.6 + 0.4 * np.sin(k * 2.2)
                c[self.inl] = RGB["ember1"]
                c[self.inl & (threshold(H, W) < pulse * 0.6)] = RGB["ember2"]
                c[self.inl & (threshold(H, W, 1, 2) < pulse * 0.12)] = RGB["flame"]
            # a cut ornament after the title lands
            L.ornament(c, "ink0", _ease((k - 0.5) / 0.8), hi="ember1")
        # sparks lift off the burning front
        fx = int(min(1.0, max(0.0, front)) * W) if t < land + 1.5 else None
        for i, (a, b, p, q) in enumerate(self.sparks):
            life = (t * (0.8 + a) + p) % 1.0
            if t < 1.0 or (fx is None and life > 0.5):
                continue
            base_x = fx if fx is not None else int(L.x + q * L.m.shape[1])
            x = int(base_x - 4 + 10 * b + 6 * np.sin(life * 7 + p * 9))
            y = int(L.y + 30 - life * (40 + 30 * q))
            if 0 <= x < W and 0 <= y < H:
                c[y, x] = RGB["flame" if life < 0.3 else "ember2" if life < 0.6 else "ember0"]
        return c

    def _plate(self, t, frame):
        c = self.paper.copy()
        L, H, W = self.L, self.H, self.W
        land = BUILD[1]
        # the ruled frame draws itself round from the top left
        f = _ease((t - 0.6) / 1.4)
        per = 2 * (W - 16) + 2 * (H - 16)
        for inset, col in ((8, "ink1"), (11, "ink2")):
            x0, y0, x1, y1 = inset, inset, W - 1 - inset, H - 1 - inset
            n = int(f * per)
            pts = ([(x, y0) for x in range(x0, x1)] + [(x1, y) for y in range(y0, y1)] +
                   [(x, y1) for x in range(x1, x0, -1)] + [(x0, y) for y in range(y1, y0, -1)])
            for x, y in pts[:n]:
                c[y, x] = RGB[col]
        if f >= 1:
            for cx, cy in ((9, 9), (W - 10, 9), (9, H - 10), (W - 10, H - 10)):
                _paint(c, _bitmap(["..#..", ".###.", "##.##", ".###.", "..#.."]), cx - 2, cy - 2, "ink1")
        # a frieze of insects along the top and bottom, arriving one by one
        kinds = ["moth", "cricket", "bee", "beetle"]
        slots = list(range(26, W - 26, 24))
        for j, x in enumerate(slots):
            at = 1.4 + j * 0.16
            if t < at:
                continue
            k = kinds[j % 4]
            bm = _bitmap(INSECTS[k])
            a = _ease((t - at) / 0.3)
            _paint(c, bm, x - bm.shape[1] // 2, 17, "ink2", a)
            _paint(c, bm[::-1, ::-1], x - bm.shape[1] // 2, H - 17 - bm.shape[0], "ink2", a)
        # the title is stamped: a bone flash, a jolt, then ink with an ember inline
        if t >= land:
            k = t - land
            if k < 1 / self.fps:
                c[L.full] = RGB["bone_hi"]
            else:
                titlefont.carve(c, L.m, L.x, L.y, 1.0, ramp=("ink2", "ink1", "ink0"), edge_hi="ash1",
                                edge_lo="ink0", outline="ink0", shadow=1)
                if L.small:
                    titlefont.carve(c, L.ms, L.xs, L.y_small, 1.0, ramp=("ink2", "ink1", "ink0"), edge_hi="ash1",
                                    edge_lo="ink0", outline="ink0", shadow=1)
                c[self.inl & (threshold(H, W) < _ease((k - 0.4) / 1.0))] = RGB["blood3"]
                L.ornament(c, "ink1", _ease((k - 0.6) / 0.8), hi="blood3")
            if k < 2 / self.fps:  # the jolt of the stamp
                c = np.roll(c, 1, axis=0)
        return c

    # -- the frame ------------------------------------------------------
    def picture(self, t, frame):
        if t >= TITLE_OUT[1]:
            return self._episode_card(t)
        c = {"swarm": self._swarm, "ember": self._ember, "plate": self._plate}[self.style](t, frame)
        vis = min(1.0, max(0.0, (t - 0.0) / BUILD[0]), max(0.0, (TITLE_OUT[1] - t) / (TITLE_OUT[1] - TITLE_OUT[0])))
        if vis < 1:
            c[~(threshold(self.H, self.W) < vis)] = RGB["ink0"]
        return c

    def _episode_card(self, t):
        c = np.zeros((self.H, self.W, 3), np.uint8)
        c[:] = RGB["ink0"]
        a0, a1 = EPISODE
        amt = min(1.0, max(0.0, (t - a0) / 0.5), max(0.0, (a1 - t) / 0.5))
        if amt <= 0:
            return c
        m = textfont.text_mask(f"Episode {words(self.ep)}")
        x, y = (self.W - m.shape[1]) // 2, self.H // 2 - 3
        _paint(c, m, x, y, "ash4", amt)
        for x0, x1 in ((x - 34, x - 8), (x + m.shape[1] + 8, x + m.shape[1] + 34)):
            _paint(c, np.ones((1, x1 - x0), dtype=bool), x0, y + 2, "ash1", amt)
        return c

    def render(self, t, frame=None):
        frame = int(round(t * self.fps)) if frame is None else frame
        return self.picture(t, frame)
