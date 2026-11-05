"""Particle weather. Deterministic in time: frame t always looks the same.

    weather: {type: ash, density: 0.6, wind: 0.3}

Types: ash (slow drifting flakes), snow, rain.
"""
import numpy as np

from .palette import RGB

_KINDS = {
    #        count  fall px/s  near/far colors       streak
    "ash":  (260, 9.0,  ("ash4", "ash3"), 0),
    "snow": (320, 16.0, ("bone", "ash4"), 0),
    "rain": (240, 160., ("cold2", "cold1"), 3),
}


class Weather:
    def __init__(self, spec, W, H, seed=11):
        self.W, self.H = W, H
        count, self.fall, self.colors, self.streak = _KINDS[spec["type"]]
        n = int(count * spec.get("density", 0.5))
        self.wind = spec.get("wind", 0.0)
        rng = np.random.default_rng(seed)
        self.x0 = rng.uniform(0, W, n)
        self.y0 = rng.uniform(0, H, n)
        self.depth = rng.uniform(0.3, 1.0, n)     # 1 = near
        self.phase = rng.uniform(0, 6.28, n)

    def draw(self, canvas, t, cam_x):
        W, H = self.W, self.H
        d = self.depth
        y = (self.y0 + t * self.fall * d) % H
        sway = np.sin(t * 0.9 + self.phase) * 1.5 * (self.streak == 0)
        x = (self.x0 + t * self.wind * 30 * d + sway - cam_x * d) % W
        near = d > 0.65
        for sel, col in ((~near, self.colors[1]), (near, self.colors[0])):
            xi, yi = x[sel].astype(int), y[sel].astype(int)
            canvas[yi, xi] = RGB[col]
            for s in range(1, self.streak + 1):
                yy = (yi - s) % H
                xx = (xi - int(round(self.wind * s))) % W
                canvas[yy, xx] = RGB[col]
