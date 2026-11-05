"""The locked palette. Every pixel on screen comes from this table.

Muted, ash-weighted ramps for The Road register. The only saturated color
family is `ember`, reserved for rig lights, fire and the capture. `night`
is a deep blue ramp for moonlit scenes (references: images-5, 11, 19, 21).
Each region of the world has its own ramp (see engine/regions.py), so
environments change color as the journey moves.
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
    # night: moonlit blue, darkest to the moon itself
    "night0": "#101420", "night1": "#1a2132", "night2": "#28334a",
    "night3": "#3d4c66", "moon": "#c8cdd2",
    # region ramps: each region of the world owns one, so the color tells you
    # where the journey is. Darkest to lightest.
    # uplands: thin cold air, mauve dusk over slate (ref images-3)
    "mauve0": "#2e2532", "mauve1": "#4a3a4b", "mauve2": "#6e5668", "mauve3": "#9a7a8c",
    "mauve4": "#c4a2ae",
    # coast: kelp, salt water, sea-teal (ref images-10, 13)
    "tide0": "#122226", "tide1": "#1c383b", "tide2": "#2e5856", "tide3": "#4f817a",
    "tide4": "#8fb3a6",
    # glass towns: ruined cities under a rust-red sky (ref images-6, 7, 12)
    "blood0": "#24110f", "blood1": "#45201b", "blood2": "#6e2f24", "blood3": "#9c4630",
    "blood4": "#c27a52",
    # interior: wet forest, recovering green (ref images-17, 20)
    "fern0": "#141c16", "fern1": "#1f2d22", "fern2": "#34472f", "fern3": "#566a3f",
    "fern4": "#8b9a5a",
    # ember: the only saturated accent
    "ember0": "#8a2e1c", "ember1": "#c4502a", "ember2": "#e08a4a",
    "flame": "#f0c878",  # fire core only
}


def rgb(name):
    h = PALETTE[name].lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.uint8)


RGB = {k: rgb(k) for k in PALETTE}


PAL_ARRAY = np.array(list(RGB.values()), dtype=np.int16)


def nearest(rgb, names=None):
    """Snap an (..., 3) array of colors to the nearest palette entries,
    optionally only among `names`."""
    pal = PAL_ARRAY if names is None else np.array([RGB[n] for n in names], dtype=np.int16)
    flat = rgb.reshape(-1, 3).astype(np.int32)
    d = ((flat[:, None, :] - pal[None, :, :]) ** 2).sum(-1)
    return pal[d.argmin(1)].astype(np.uint8).reshape(rgb.shape)
