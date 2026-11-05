"""The locked palette. Every pixel on screen comes from this table.

Muted, ash-weighted ramps for The Road register. The only saturated color
family is `ember`, reserved for rig lights, fire and the capture.
Change values here, never inline hex in scenes or sprites.
"""
import numpy as np

PALETTE = {
    # ink: silhouettes, deepest shadow
    "ink0": "#0d0c0b", "ink1": "#1a1816", "ink2": "#26231f",
    # ash: the world's base ramp, warm grey
    "ash0": "#3a3631", "ash1": "#4f4a43", "ash2": "#6a645b",
    "ash3": "#878076", "ash4": "#a39c90", "ash5": "#bfb8aa",
    # bone: highlights, captions
    "bone": "#d6cfbf", "bone_hi": "#e8e2d4",
    # sky: sick ochre-grey overcast
    "sky0": "#5b5548", "sky1": "#7a715d", "sky2": "#9a8f75", "sky3": "#b5aa8c",
    # cold: night, water, steel
    "cold0": "#2e3338", "cold1": "#444b52", "cold2": "#626a70",
    # rust and moss: dead machinery, dead growth
    "rust0": "#4a2e22", "rust1": "#6e4330",
    "moss0": "#3a3d2c", "moss1": "#555a3f",
    # ember: the only saturated accent
    "ember0": "#8a2e1c", "ember1": "#c4502a", "ember2": "#e08a4a",
}


def rgb(name):
    h = PALETTE[name].lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)


RGB = {k: rgb(k) for k in PALETTE}
