"""ASCII sprite format.

A sprite is a YAML file in assets/sprites/:

    name: wanderer
    anchor: [5, 17]        # pixel in the grid that sits on the actor's position (feet)
    fps: 6                 # animation rate for every state
    legend:                # grid char -> palette name; '.' is always transparent
      k: ink0
      r: ash2
    states:
      idle:
        - |
          ..kkk..
          ...
      walk: [ frame, frame, ... ]

All frames in a sprite share one grid size. Facing is handled by the actor
(`flip: true`), so draw every sprite facing right.
"""
from pathlib import Path

import numpy as np
import yaml

from .palette import RGB

_CACHE = {}


class Sprite:
    def __init__(self, data):
        self.name = data["name"]
        self.anchor = tuple(data.get("anchor", [0, 0]))
        self.fps = data.get("fps", 6)
        legend = data["legend"]
        self.states = {}
        for state, frames in data["states"].items():
            self.states[state] = [self._parse(f, legend, state) for f in frames]

    def _parse(self, text, legend, state):
        rows = [r for r in text.strip("\n").split("\n")]
        w = max(len(r) for r in rows)
        rgb = np.zeros((len(rows), w, 3), dtype=np.uint8)
        alpha = np.zeros((len(rows), w), dtype=bool)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch in ". ":
                    continue
                if ch not in legend:
                    raise ValueError(f"{self.name}/{state}: char {ch!r} not in legend")
                rgb[y, x] = RGB[legend[ch]]
                alpha[y, x] = True
        return rgb, alpha

    def frame(self, state, t, flip=False):
        frames = self.states[state]
        rgb, alpha = frames[int(t * self.fps) % len(frames)]
        if flip:
            return rgb[:, ::-1], alpha[:, ::-1]
        return rgb, alpha


def load(name, root="assets/sprites"):
    if name not in _CACHE:
        with open(Path(root) / f"{name}.yaml") as f:
            _CACHE[name] = Sprite(yaml.safe_load(f))
    return _CACHE[name]


def blit(canvas, rgb, alpha, x, y):
    """Paste a sprite with its top-left at integer (x, y), clipped to the canvas."""
    H, W = canvas.shape[:2]
    h, w = alpha.shape
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + w), min(H, y + h)
    if x0 >= x1 or y0 >= y1:
        return
    sa = alpha[y0 - y:y1 - y, x0 - x:x1 - x]
    canvas[y0:y1, x0:x1][sa] = rgb[y0 - y:y1 - y, x0 - x:x1 - x][sa]
