"""Procedural backdrops built from parallax layers.

A backdrop spec in a timeline:

    backdrop:
      sky: [sky3, sky2, sky1]      # top -> horizon, dithered between steps
      seed: 3
      layers:                      # far to near
        - {color: ash3, y: 112, amp: 14, rough: 0.55, parallax: 0.2}
        - {color: ash1, y: 128, amp: 10, rough: 0.6,  parallax: 0.45}
      ground: {color: ash0, y: 150, speckle: ash1}

`y` is the ridge baseline, `amp` the height variation in pixels, `parallax`
how fast the layer scrolls relative to the camera (0 = fixed, 1 = world).
"""
import numpy as np

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
    def __init__(self, spec, W, H, pan_extent=640):
        self.W, self.H, self.spec = W, H, spec
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

    def draw(self, canvas, cam_x):
        W, H = self.W, self.H
        canvas[:] = self.sky
        ys = np.arange(H)[:, None]
        for L, heights in self.layers:
            off = int(round(cam_x * L.get("parallax", 0.5)))
            off = max(0, min(off, len(heights) - W))
            h = heights[off:off + W][None, :]
            canvas[ys >= h] = RGB[L["color"]]
        g = self.ground
        if g:
            region = canvas[g["y"]:]
            region[:] = RGB[g["color"]]
            if g.get("speckle"):
                ox = int(round(cam_x))
                rng = np.random.default_rng(7)
                noise = rng.random((H, W + 2048))
                gh = H - g["y"]
                sl = noise[:gh, ox % 2048: ox % 2048 + W]
                # sparser toward the horizon, denser at the bottom
                density = np.linspace(0.04, 0.22, gh)[:, None]
                region[sl < density] = RGB[g["speckle"]]
