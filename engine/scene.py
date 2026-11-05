"""Scene renderer: one timeline entry -> a sequence of RGB frames.

Draw order: backdrop, lights (behind actors), actors by depth, weather,
captions, transitions. Everything is in screen pixels at the base resolution;
upscaling happens only in FFmpeg, with nearest-neighbour.
"""
import numpy as np

from . import sprites
from .backdrops import Backdrop
from .dither import mask, threshold
from .font import CH, text_mask, wrap
from .palette import RGB
from .weather import Weather


def ease(f, kind="smooth"):
    f = min(max(f, 0.0), 1.0)
    if kind == "linear":
        return f
    return f * f * (3 - 2 * f)


def lerp_path(path, f):
    """Position along a polyline of [x, y] points at fraction f (0..1)."""
    pts = np.array(path, dtype=float)
    if len(pts) == 1:
        return pts[0]
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    total = seg.sum() or 1.0
    d = f * total
    for i, L in enumerate(seg):
        if d <= L or i == len(seg) - 1:
            return pts[i] + (pts[i + 1] - pts[i]) * (d / L if L else 0)
        d -= L


class Scene:
    def __init__(self, spec, cfg):
        self.spec, self.cfg = spec, cfg
        self.W, self.H = cfg["resolution"]
        self.fps = cfg["fps"]
        self.duration = spec["duration"]
        self.n_frames = int(round(self.duration * self.fps))
        cam = spec.get("camera", {})
        self.pan = cam.get("pan", [0, 0])
        self.zoom = cam.get("zoom", [1, 1])
        self.cam_ease = cam.get("ease", "smooth")
        extent = abs(self.pan[1] - self.pan[0]) + 16
        self.backdrop = Backdrop(spec.get("backdrop", {}), self.W, self.H, extent)
        w = spec.get("weather")
        self.weather = Weather(w, self.W, self.H) if w else None
        self.actors = spec.get("actors", [])
        self.lights = spec.get("lights", [])
        self.captions = spec.get("captions", [])

    # -- camera ---------------------------------------------------------
    def camera(self, t):
        f = ease(t / self.duration, self.cam_ease)
        cam_x = self.pan[0] + (self.pan[1] - self.pan[0]) * f
        z = self.zoom[0] + (self.zoom[1] - self.zoom[0]) * f
        return cam_x, z

    # -- layers ---------------------------------------------------------
    def _draw_light(self, c, L, t, cam_x):
        px = L.get("parallax", 1.0)
        cx = L["pos"][0] - cam_x * px
        cy = L["pos"][1]
        r = L.get("radius", 10)
        inten = L.get("intensity", 0.6)
        if "pulse" in L:  # seconds per cycle
            inten *= 0.55 + 0.45 * (0.5 + 0.5 * np.cos(2 * np.pi * t / L["pulse"]))
        x0, x1 = int(cx - r), int(cx + r) + 1
        y0, y1 = int(cy - r), int(cy + r) + 1
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(self.W, x1), min(self.H, y1)
        if xa >= xb or ya >= yb:
            return
        yy, xx = np.mgrid[ya:yb, xa:xb]
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        amount = np.clip(1 - d, 0, 1) ** 2 * inten
        on = threshold(yb - ya, xb - xa, xa, ya) < amount
        c[ya:yb, xa:xb][on] = RGB[L.get("color", "ember0")]

    def _draw_actor(self, c, a, t, cam_x):
        spr = sprites.load(a["sprite"])
        t0, t1 = a.get("t", [0, self.duration])
        if not (t0 <= t <= t1):
            return
        f = ease((t - t0) / max(1e-6, t1 - t0), a.get("ease", "linear"))
        x, y = lerp_path(a.get("path", [[0, 0]]), f)
        px = a.get("parallax", 1.0)
        rgb, alpha = spr.frame(a.get("state", "idle"), t - t0, a.get("flip", False))
        ax, ay = spr.anchor
        if a.get("flip"):
            ax = alpha.shape[1] - 1 - ax
        sprites.blit(c, rgb, alpha, int(round(x - cam_x * px)) - ax, int(round(y)) - ay)

    def _draw_captions(self, c, t):
        for cap in self.captions:
            t0, t1 = cap["t"]
            if not (t0 <= t <= t1):
                continue
            fade = cap.get("fade", 0.6)
            amt = min(1.0, (t - t0) / fade if fade else 1, (t1 - t) / fade if fade else 1)
            lines = wrap(cap["text"], cap.get("width", 56))
            base_y = cap.get("y", self.H - 14 - (len(lines) - 1) * (CH + 3))
            for i, line in enumerate(lines):
                m = text_mask(line)
                h, w = m.shape
                x = (self.W - w) // 2
                y = base_y + i * (CH + 3)
                show = m & mask(amt, h, w, x, y)
                shadow = np.zeros((h + 1, w + 1), dtype=bool)
                shadow[1:, 1:] = show
                c[y:y + h + 1, x:x + w + 1][shadow] = RGB["ink0"]
                c[y:y + h, x:x + w][show] = RGB[cap.get("color", "bone")]

    def _transition(self, c, t):
        amt = 0.0
        for key, edge in (("transition_in", 0), ("transition_out", 1)):
            tr = self.spec.get(key)
            if not tr:
                continue
            dur = tr.get("duration", 1.0)
            dt = t if edge == 0 else self.duration - t
            if dt < dur:
                amt = max(amt, 1 - dt / dur)
        if amt > 0:
            c[mask(amt, self.H, self.W)] = RGB[self.spec.get("fade_color", "ink0")]

    # -- frame ----------------------------------------------------------
    def render(self, t):
        cam_x, z = self.camera(t)
        c = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        self.backdrop.draw(c, cam_x)
        for L in self.lights:
            self._draw_light(c, L, t, cam_x)
        for a in sorted(self.actors, key=lambda a: a.get("parallax", 1.0)):
            self._draw_actor(c, a, t, cam_x)
        if self.weather:
            self.weather.draw(c, t, cam_x)
        if z != 1:
            c = self._zoom(c, z)
        self._draw_captions(c, t)
        self._transition(c, t)
        return c

    def _zoom(self, c, z):
        """Centre zoom by nearest-neighbour resampling. Keep zooms small and slow."""
        H, W = self.H, self.W
        ys = ((np.arange(H) - H / 2) / z + H / 2).astype(int).clip(0, H - 1)
        xs = ((np.arange(W) - W / 2) / z + W / 2).astype(int).clip(0, W - 1)
        return c[ys][:, xs]

    def frames(self):
        for i in range(self.n_frames):
            yield i, self.render(i / self.fps)
