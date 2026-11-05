"""Ordered (Bayer) dithering: the only way tones blend. No alpha, no anti-aliasing."""
import numpy as np

BAYER4 = (np.array([[0, 8, 2, 10],
                    [12, 4, 14, 6],
                    [3, 11, 1, 9],
                    [15, 7, 13, 5]], dtype=np.float32) + 0.5) / 16.0


def threshold(h, w, ox=0, oy=0):
    """Tiled Bayer threshold map, optionally offset so it stays locked to the world."""
    ys = (np.arange(h)[:, None] + oy) % 4
    xs = (np.arange(w)[None, :] + ox) % 4
    return BAYER4[ys, xs]


def mask(amount, h, w, ox=0, oy=0):
    """Boolean mask where `amount` (scalar or HxW array, 0..1) is 'on'."""
    return threshold(h, w, ox, oy) < amount
