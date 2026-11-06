"""Procedural backdrops built from parallax layers.

A backdrop spec in a timeline:

    backdrop:
      sky: [sky3, sky2, sky1]      # top -> horizon, dithered between steps
      seed: 3
      layers:                      # far to near
        - {color: ash3, y: 112, amp: 14, rough: 0.55, parallax: 0.2}
        - {color: ash1, y: 128, amp: 10, rough: 0.6,  parallax: 0.45}
      ground: {color: ash0, y: 150, speckle: ash1}
      props: [...]                 # see engine/props.py; `layer: N` slots a prop
                                   # after ridge N (-1 = behind all ridges)

`y` is the ridge baseline, `amp` the height variation in pixels, `parallax`
how fast the layer scrolls relative to the camera (0 = fixed, 1 = world).
"""
import numpy as np

from . import props, texture
from .dither import mask
from .palette import RGB


def _ridge(n, amp, rough, rng):
    """1D midpoint-displacement heights, length n."""
    size = 1
    while size < n:
        size *= 2
    h = np.zeros(size + 1)
    h[0], h[-1] = rng.uniform(-1, 1, 2)
    step, scale = size, 1.0
    while step > 1:
        half = step // 2
        for i in range(half, size, step):
            h[i] = (h[i - half] + h[i + half]) / 2 + rng.uniform(-scale, scale)
        step, scale = half, scale * rough
    h = h[:n]
    h = (h - h.min()) / max(1e-6, np.ptp(h))
    return h * amp


class Backdrop:
    def __init__(self, spec, W, H, pan_extent=640, textured=False):
        self.W, self.H, self.spec = W, H, spec
        self.textured = spec.get("texture", textured)  # the hyper-detailed style: every fill retoned by noise
        rng = np.random.default_rng(spec.get("seed", 0))
        self.sky = self._sky(spec.get("sky", ["sky3", "sky2", "sky1"]))
        self.layers = []
        for L in spec.get("layers", []):
            n = W + int(pan_extent * L.get("parallax", 0.5)) + 8
            heights = L["y"] - _ridge(n, L.get("amp", 10), L.get("rough", 0.55), rng)
            self.layers.append((L, heights.astype(int)))
        self.ground = spec.get("ground")

    def _sky(self, stops):
        """Vertical gradient through palette stops, Bayer-dithered."""
        W, H = self.W, self.H
        out = np.zeros((H, W, 3), dtype=np.uint8)
        horizon = self.spec.get("horizon", int(H * 0.75))
        seg = max(1, horizon // (len(stops) - 1)) if len(stops) > 1 else H
        for y in range(H):
            pos = min(y / seg, len(stops) - 1 - 1e-6)
            i, f = int(pos), pos - int(pos)
            a, b = RGB[stops[i]], RGB[stops[min(i + 1, len(stops) - 1)]]
            row = mask(f, 1, W, 0, y)[0]
            out[y] = np.where(row[:, None], b, a)
        return out

    def draw(self, canvas, cam_x, t=0.0):
        """Sky, then ridge layers and ground, with each prop slotted in by its `layer`.

        A prop's `layer: N` draws it just after ridge layer N (-1 = right after the
        sky, behind every ridge). Props without a layer are drawn later by
        `draw_props`, in front of the ground and behind actors.
        """
        W, H = self.W, self.H
        all_props = self.spec.get("props", [])
        canvas[:] = self.sky
        if self.textured:
            texture.texture(canvas, np.ones((H, W), bool), "cloud", cam_x * 0.05, 0, seed=11, amp=0.35)
        self._props(canvas, [p for p in all_props if p.get("layer") == -1], cam_x, t)
        if self.spec.get("plain"):  # flat or two-tone ground for inserts and close-ups
            return
        ys = np.arange(H)[:, None]
        for i, (L, heights) in enumerate(self.layers):
            off = int(round(cam_x * L.get("parallax", 0.5)))
            off = max(0, min(off, len(heights) - W))
            h = heights[off:off + W][None, :]
            m = ys >= h
            canvas[m] = RGB[L["color"]]
            if self.textured:
                # ridges: rock noise, lighter along the crest, fading with distance
                crest = np.clip((ys - h) / 6.0, 0, 1)
                texture.retone(canvas, m, texture.field("rock", H, W, off, 0, seed=20 + i) * (0.6 + 0.4 * i) + (1 - crest) * 0.35, amp=0.9)
            self._props(canvas, [p for p in all_props if p.get("layer") == i], cam_x, t)
        g = self.ground
        if g:
            region = canvas[g["y"]:]
            region[:] = RGB[g["color"]]
            if self.textured:
                gh = H - g["y"]
                m = np.zeros((H, W), bool)
                m[g["y"]:] = True
                depth = np.linspace(0.3, 1.0, gh)[:, None].repeat(W, 1)
                f = texture.field("earth", gh, W, cam_x, g["y"], seed=5) * depth
                full = np.zeros((H, W), np.float32)
                full[g["y"]:] = f
                texture.retone(canvas, m, full, amp=1.3)
            if g.get("speckle"):
                ox = int(round(cam_x))
                rng = np.random.default_rng(7)
                noise = rng.random((H, W + 2048))
                gh = H - g["y"]
                sl = noise[:gh, ox % 2048: ox % 2048 + W]
                # sparser toward the horizon, denser at the bottom
                density = np.linspace(0.04, 0.22, gh)[:, None]
                region[sl < density] = RGB[g["speckle"]]

    _PROP_TEXTURE = {"tree": "bark", "trunk": "bark", "ruin": "stone", "presence": None, "moon": None}

    def _props(self, canvas, plist, cam_x, t):
        """Draw props; in the textured style each solid prop is retoned by its material."""
        if not self.textured:
            props.draw(canvas, plist, cam_x, t)
            return
        for p in plist:
            kind = self._PROP_TEXTURE.get(p["type"], "rock" if p["type"] in ("grass",) else None)
            if kind is None:
                props.draw(canvas, [p], cam_x, t)
                continue
            before = canvas.copy()
            props.draw(canvas, [p], cam_x, t)
            changed = (canvas != before).any(-1)
            texture.texture(canvas, changed, kind, cam_x * p.get("parallax", 1.0), 0, seed=p.get("seed", 0) + 40, amp=1.1)

    def draw_props(self, canvas, cam_x, t, emissive=False):
        """Front props. Emissive ones (fire) are drawn in a second pass, after lights."""
        props.draw(canvas, [p for p in self.spec.get("props", []) if "layer" not in p
                            and (p["type"] in props.EMISSIVE) == emissive], cam_x, t)

    def draw_front(self, canvas, cam_x, t):
        """Foreground framing props (`layer: front`), over the actors."""
        props.draw(canvas, [p for p in self.spec.get("props", []) if p.get("layer") == "front"], cam_x, t)

    def draw_screen(self, canvas, t):
        """Props pinned to the frame (`layer: screen`): drawn after the zoom, so a
        shoulder or a hand stays in its corner however the camera punches in."""
        props.draw(canvas, [p for p in self.spec.get("props", []) if p.get("layer") == "screen"], 0, t)
