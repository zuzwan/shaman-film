"""Scene renderer: one timeline entry -> a sequence of RGB frames.

Draw order: backdrop, lights (behind actors), actors by depth, weather,
captions, transitions. Everything is in screen pixels at the base resolution;
upscaling happens only in FFmpeg, with nearest-neighbour.

Shots. A scene may be cut into shots, for action and conversation:

    shots:
      - {duration: 1.2}                                     # the scene as written
      - {duration: 0.4, camera: {zoom: 3, focus: [150, 150]},
         set: {auk: {state: strike}}, fx: [{type: speedlines, kind: radial, center: [150, 150]}]}
      - {duration: 0.17, fx: [{type: impact, bg: bone, fg: ink0}]}

Each shot is the scene's spec with the shot's keys laid over it: `camera`
merges, `set` patches actors by their `id`, anything else replaces. Actor
time, paths and animation restart at each shot; weather, fire and subtitle
cards run on the scene's clock across the cuts.

Camera: `pan`, `zoom` (a number, or [from, to]), `focus` (screen point the
zoom centres on; whole-number zooms stay pixel-crisp), `shake` (amplitude in
pixels, or {amp, decay}).
"""
import copy

import numpy as np

from . import fx, regions, sprites, subtitles
from .backdrops import Backdrop
from .dither import mask, threshold
from .font import CH, text_mask, wrap
from .palette import RGB, nearest

# Colors a light may paint with, by its key color. Warm light stays warm.
LIGHT_RAMPS = {
    "ember0": ["blood0", "rust0", "blood1", "rust1", "ember0", "blood2", "ember1"],
    "ember1": ["rust1", "ember0", "blood3", "ember1", "ember2"],
    "ember2": ["ember1", "ember2", "blood4", "flame"],
    "moon": ["night1", "night2", "night3", "cold1", "cold2", "ash4", "moon"],
    "night3": ["night1", "night2", "night3", "cold1", "cold2"],
}
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
    def __init__(self, spec, cfg, clock_offset=0.0, frame_offset=0):
        self.spec, self.cfg = spec, cfg
        self.W, self.H = cfg["resolution"]
        self.fps = cfg["fps"]
        self.clock_offset, self.frame_offset = clock_offset, frame_offset
        self.band = spec.get("band", cfg.get("band", 0))
        self.shots = []
        if spec.get("shots"):
            t = 0.0
            for shot in spec["shots"]:
                sub = Scene(merge_shot(spec, shot), cfg, clock_offset + t, frame_offset + int(round(t * self.fps)))
                self.shots.append((t, sub))
                t += sub.duration
            if spec.get("duration", "auto") == "auto":
                spec = {**spec, "duration": t}
        self.cards = subtitles.schedule(spec.get("cards", []), spec.get("cards_start", 0.6), self.W, self.band)
        dur = spec.get("duration", "auto")
        if dur == "auto":  # long enough to read every card
            dur = max(spec.get("min_duration", 3.0), subtitles.total_time(spec.get("cards", []),
                      spec.get("cards_start", 0.6), spec.get("tail", 1.2), self.W, self.band))
        self.duration = float(dur)
        self.n_frames = int(round(self.duration * self.fps))
        cam = spec.get("camera", {})
        self.pan = cam.get("pan", [0, 0])
        z = cam.get("zoom", [1, 1])
        self.zoom = z if isinstance(z, list) else [z, z]
        self.focus = cam.get("focus")
        self.shake = cam.get("shake")
        self.cam_ease = cam.get("ease", "smooth")
        extent = abs(self.pan[1] - self.pan[0]) + 16
        bd, w = regions.expand(spec.get("backdrop", {}), spec.get("weather"))
        self.backdrop = Backdrop(bd, self.W, self.H, extent)
        self.weather = Weather(w, self.W, self.H) if w and w != "none" else None
        self.actors = spec.get("actors", [])
        self.fx = spec.get("fx", [])
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
        if L.get("flicker"):  # firelight: irregular, changes a few times a second
            k = int(t * 8)
            inten *= 0.8 + 0.2 * np.sin(k * 12.9898 + L["pos"][0]) * np.sin(k * 4.1414)
        x0, x1 = int(cx - r), int(cx + r) + 1
        y0, y1 = int(cy - r), int(cy + r) + 1
        xa, ya = max(0, x0), max(0, y0)
        xb, yb = min(self.W, x1), min(self.H, y1)
        if xa >= xb or ya >= yb:
            return
        yy, xx = np.mgrid[ya:yb, xa:xb]
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
        amount = np.clip(1 - d, 0, 1) ** 1.5 * inten
        # Light washes each pixel toward its color, snaps the result to the light's
        # ramp (warm colors only, so no grey halos), and dithers between the lit
        # and unlit pixel by strength.
        region = c[ya:yb, xa:xb]
        col = RGB[L.get("color", "ember0")].astype(np.float32)
        ramp = L.get("ramp", LIGHT_RAMPS.get(L.get("color", "ember0"), [L.get("color", "ember0")]))
        sel = amount > 0.03
        lit_target = region[sel].astype(np.float32)
        lit_target = lit_target + (col - lit_target) * (0.25 + 0.5 * amount[sel, None])
        lit = nearest(np.clip(lit_target, 0, 255), ramp)
        on = threshold(yb - ya, xb - xa, xa, ya)[sel] < amount[sel] * 1.6
        px = region[sel]
        px[on] = lit[on]
        region[sel] = px

    def actor_pos(self, a, t):
        """World position of an actor at time t, or None when it is off stage."""
        t0, t1 = a.get("t", [0, self.duration])
        if not (t0 <= t <= t1):
            return None
        f = ease((t - t0) / max(1e-6, t1 - t0), a.get("ease", "linear"))
        return lerp_path(a.get("path", [[0, 0]]), f)

    def _draw_actor(self, c, a, t, cam_x, amask=None):
        if a.get("hidden"):
            return
        spr = sprites.load(a["sprite"])
        pos = self.actor_pos(a, t)
        if pos is None:
            return
        x, y = pos
        t0 = a.get("t", [0])[0] + a.get("phase", 0.0)
        px = a.get("parallax", 1.0)
        at = a["freeze"] if "freeze" in a else t - t0   # freeze: hold one moment of the cycle
        rgb, alpha = spr.frame(a.get("state", "idle"), at, a.get("flip", False))
        if a.get("tint"):  # solid silhouette, e.g. the white hit-flash
            rgb = np.broadcast_to(RGB[a["tint"]], rgb.shape)
        ax, ay = spr.anchor
        if a.get("flip"):
            ax = alpha.shape[1] - 1 - ax
        bx, by = int(round(x - cam_x * px)) - ax, int(round(y)) - ay
        sprites.blit(c, rgb, alpha, bx, by)
        if amask is not None:
            sprites.blit_mask(amask, alpha, bx, by)

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
    def picture(self, t, frame):
        """The image above the text band: world, lights, weather, camera and fx."""
        if self.shots:
            for start, sub in reversed(self.shots):
                if t >= start - 1e-9:
                    return sub.picture(t - start, frame)
        cam_x, z = self.camera(t)
        clock = t + self.clock_offset  # the scene's clock, continuous across cuts
        c = np.zeros((self.H, self.W, 3), dtype=np.uint8)
        amask = np.zeros((self.H, self.W), dtype=bool)
        self.backdrop.draw(c, cam_x, clock)
        self.backdrop.draw_props(c, cam_x, clock)
        for a in sorted(self.actors, key=lambda a: a.get("parallax", 1.0)):
            self._draw_actor(c, a, t, cam_x, amask)
        for L in self.lights:  # after actors, so firelight falls on the figures too
            self._draw_light(c, L, clock, cam_x)
        for a in self.actors:  # lights carried by actors, e.g. a lantern
            if "light" in a and not a.get("hidden") and (pos := self.actor_pos(a, t)) is not None:
                dx, dy = a["light"].get("offset", [0, 0])
                if a.get("flip"):
                    dx = -dx
                L = dict(a["light"], pos=[pos[0] + dx, pos[1] + dy], parallax=a.get("parallax", 1.0))
                self._draw_light(c, L, clock, cam_x)
        self.backdrop.draw_props(c, cam_x, clock, emissive=True)  # flames sit on top of their own light
        if self.weather:
            self.weather.draw(c, clock, cam_x)
        if z != 1:
            c = self._zoom(c, z)
            amask = self._zoom(amask, z)
        fx.apply(c, self.fx, frame, amask, top=self.cfg.get("band", 0))
        dx, dy = fx.shake_offset(self.shake, t, self.duration, frame)
        if dx or dy:
            c = np.roll(c, (dy, dx), axis=(0, 1))
        return c

    def render(self, t, frame=None):
        frame = int(round(t * self.fps)) if frame is None else frame
        c = self.picture(t, frame)
        if self.band:  # lift the picture, cropping empty sky, and open a black text band below
            c = np.concatenate([c[self.band:], np.zeros((self.band, self.W, 3), np.uint8)])
            c[self.H - self.band:] = RGB["ink0"]
        self._transition(c, t)
        self._draw_captions(c, t)
        subtitles.draw(c, self.cards, t, self.band)
        return c

    def _zoom(self, c, z):
        """Zoom about `focus` (default: centre) by nearest-neighbour resampling.

        Whole-number zooms keep every source pixel the same size; fractional
        zooms work but make uneven pixels, so keep those small and slow."""
        H, W = self.H, self.W
        fx_, fy_ = self.focus or (W / 2, H / 2)
        # keep the crop inside the frame so the edges never smear
        hw, hh = W / (2 * z), H / (2 * z)
        cx = min(max(fx_, hw), W - hw)
        cy = min(max(fy_, hh), H - hh)
        ys = np.floor((np.arange(H) + 0.5) / z + cy - hh).astype(int).clip(0, H - 1)
        xs = np.floor((np.arange(W) + 0.5) / z + cx - hw).astype(int).clip(0, W - 1)
        return c[ys][:, xs]

    def frames(self):
        for i in range(self.n_frames):
            yield i, self.render(i / self.fps, i)


def merge_shot(spec, shot):
    """The scene's spec with one shot laid over it (see module docstring)."""
    base = {k: v for k, v in spec.items()
            if k not in ("shots", "cards", "captions", "transition_in", "transition_out", "duration", "id")}
    out = copy.deepcopy(base)
    for k, v in shot.items():
        if k == "camera":
            out["camera"] = {**base.get("camera", {}), **v}
        elif k == "set":
            for a in out.get("actors", []):
                if a.get("id") in v:
                    a.update(v[a["id"]])
        else:
            out[k] = copy.deepcopy(v)
    out.setdefault("duration", 1.0)
    out["band"] = 0  # the parent scene owns the text band
    return out
