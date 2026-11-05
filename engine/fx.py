"""Action effects for fights: speed lines, impact frames, flashes, shake.

Used through a scene's or a shot's `fx` list:

    fx:
      - {type: speedlines, kind: radial, center: [160, 120], inner: 26, color: bone, density: 60}
      - {type: speedlines, kind: horizontal, color: ash4, density: 40}
      - {type: impact, bg: bone, fg: ink0}       # flat colour frame, figures in silhouette
      - {type: impact, bg: ink0, fg: ember1}     # the negative version
      - {type: flash, color: bone, amount: 0.5}  # dithered flash over the picture
      - {type: bars, size: 18}                   # letterbox bars that close in for a beat

Lines are re-drawn at random every frame, as in hand-drawn anime action,
but deterministically, so frame N always looks the same.
"""
import numpy as np

from .dither import mask
from .palette import RGB


def _line(c, x0, y0, x1, y1, col):
    H, W = c.shape[:2]
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    xs = np.round(np.linspace(x0, x1, n)).astype(int)
    ys = np.round(np.linspace(y0, y1, n)).astype(int)
    ok = (xs >= 0) & (xs < W) & (ys >= 0) & (ys < H)
    c[ys[ok], xs[ok]] = col


def speedlines(c, spec, frame, actor_mask):
    H, W = c.shape[:2]
    rng = np.random.default_rng(frame * 7919 + spec.get("seed", 0))
    col = RGB[spec.get("color", "bone")]
    n = int(spec.get("density", 50))
    keep = c.copy()
    if spec.get("kind", "radial") == "radial":
        cx, cy = spec.get("center", [W / 2, H / 2])
        inner = spec.get("inner", 28)
        outer = np.hypot(W, H)
        for _ in range(n):
            a = rng.uniform(0, 2 * np.pi)
            r0 = inner + rng.uniform(0, 40)
            _line(c, cx + np.cos(a) * r0, cy + np.sin(a) * r0,
                  cx + np.cos(a) * outer, cy + np.sin(a) * outer, col)
    else:  # horizontal streaks across the frame
        for _ in range(n):
            y = rng.integers(0, H)
            x0 = rng.uniform(-40, W)
            L = rng.uniform(20, 120)
            _line(c, x0, y, x0 + L, y, col)
    if spec.get("behind", True) and actor_mask is not None:  # figures stay in front of their lines
        c[actor_mask] = keep[actor_mask]


def impact(c, spec, actor_mask):
    c[:] = RGB[spec.get("bg", "bone")]
    if actor_mask is not None:
        c[actor_mask] = RGB[spec.get("fg", "ink0")]


def flash(c, spec, frame):
    H, W = c.shape[:2]
    c[mask(spec.get("amount", 0.5), H, W, frame % 4, 0)] = RGB[spec.get("color", "bone")]


def bars(c, spec, top=0):
    """Letterbox bars. `top` skips rows the text band will crop off the picture."""
    s = int(spec.get("size", 18))
    c[top:top + s] = RGB["ink0"]
    if not top:  # with a text band, the band itself is the bottom bar
        c[c.shape[0] - s:] = RGB["ink0"]


def apply(c, fx_list, frame, actor_mask, top=0):
    for f in fx_list:
        kind = f["type"]
        if kind == "speedlines":
            speedlines(c, f, frame, actor_mask)
        elif kind == "impact":
            impact(c, f, actor_mask)
        elif kind == "flash":
            flash(c, f, frame)
        elif kind == "bars":
            bars(c, f, top)
        else:
            raise ValueError(f"unknown fx type {kind!r}")


def shake_offset(spec, t, duration, frame):
    """Camera shake: random integer offset each frame, decaying across the shot."""
    if not spec:
        return 0, 0
    amp = spec if isinstance(spec, (int, float)) else spec.get("amp", 3)
    decay = 1.0 if isinstance(spec, (int, float)) else spec.get("decay", 1.0)
    k = amp * (1 - decay * min(1.0, t / max(duration, 1e-6)))
    if k < 0.5:
        return 0, 0
    rng = np.random.default_rng(frame * 31337)
    return int(round(rng.uniform(-k, k))), int(round(rng.uniform(-k, k)))
