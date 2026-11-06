"""Tiny raster kit for drawing larger sprites in code, then saving them as the
ASCII sprite format. Shapes fill with palette names; `shade` fills with a
dithered ramp so large areas get form instead of flat colour.

Used by the generators in tools/art/ (rig, portraits, inserts). The YAML they
write is the source of truth afterwards; re-run a generator only to redo art.
"""
import math

import numpy as np

BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [[None] * w for _ in range(h)]

    def put(self, x, y, col):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = col

    def get(self, x, y):
        return self.px[y][x] if 0 <= x < self.w and 0 <= y < self.h else None

    def line(self, x0, y0, x1, y1, col):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n):
            f = i / max(1, n - 1)
            self.put(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, col)

    def rect(self, x, y, w, h, col):
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.put(xx, yy, col)

    def _inside_poly(self, pts, x, y):
        inside = False
        for i in range(len(pts)):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % len(pts)]
            if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0) + x0:
                inside = not inside
        return inside

    def poly(self, pts, col, shade=None):
        """Fill a polygon. `shade` = (dark, light, (dx, dy)) dithers from dark to
        light along the direction (dx, dy) across the shape's bounds."""
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1, y0, y1 = int(min(xs)), int(max(xs)) + 1, int(min(ys)), int(max(ys)) + 1
        for y in range(y0, y1):
            for x in range(x0, x1):
                if self._inside_poly(pts, x + 0.5, y + 0.5):
                    self.put(x, y, self._shade(col, shade, x, y, x0, x1, y0, y1))

    def ellipse(self, cx, cy, rx, ry, col, shade=None):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if ((x + 0.5 - cx) / rx) ** 2 + ((y + 0.5 - cy) / ry) ** 2 <= 1:
                    self.put(x, y, self._shade(col, shade, x, y, cx - rx, cx + rx, cy - ry, cy + ry))

    def ring(self, cx, cy, r, col, thick=1):
        for y in range(int(cy - r) - 1, int(cy + r) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if r - thick <= d <= r:
                    self.put(x, y, col)

    @staticmethod
    def _shade(col, shade, x, y, x0, x1, y0, y1):
        if not shade:
            return col
        dark, light, (dx, dy) = shade
        fx = (x - x0) / max(1, x1 - x0 - 1)
        fy = (y - y0) / max(1, y1 - y0 - 1)
        f = fx * dx + fy * dy
        f = (f - min(0, dx) - min(0, dy)) / max(1e-6, abs(dx) + abs(dy))
        return light if BAYER[y % 4, x % 4] < f else dark

    def outline(self, col, of=None):
        """Draw a 1px outline around every non-empty pixel (or pixels of colour `of`)."""
        add = []
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is None:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        v = self.get(x + dx, y + dy)
                        if v is not None and v != col and (of is None or v in of):
                            add.append((x, y))
                            break
        for x, y in add:
            self.px[y][x] = col

    def to_rows(self, legend):
        """ASCII rows using `legend` (palette name -> char)."""
        return ["".join("." if v is None else legend[v] for v in row) for row in self.px]


def auto_legend(canvases):
    """Assign one character per palette name used, stable across frames."""
    names = sorted({v for c in canvases for row in c.px for v in row if v is not None})
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return {n: chars[i] for i, n in enumerate(names)}


def write_sprite(path, name, header, anchor, fps, states):
    """states: {state: [Canvas, ...]}"""
    cans = [c for fr in states.values() for c in fr]
    leg = auto_legend(cans)
    lines = [header.rstrip(), f"name: {name}", f"anchor: {list(anchor)}", f"fps: {fps}", "legend:"]
    lines += [f"  {ch}: {nm}" for nm, ch in leg.items()]
    lines.append("states:")
    for st, frames in states.items():
        lines.append(f"  {st}:")
        for c in frames:
            lines.append("    - |")
            lines += ["      " + r for r in c.to_rows(leg)]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
