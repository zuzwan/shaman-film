"""Region presets: the look of each part of the world, by time of day.

A scene's backdrop can name a region and a time, then override anything:

    backdrop: {region: uplands, time: dusk, seed: 4, props: [...]}

`angle: low | high | skyline | eye` (or a raw `shift` in pixels) moves the
horizon for low and high camera angles; see ANGLES.

The preset fills sky, ridge layers, ground, and suggests weather. Keys the
scene sets win. Regions follow the world doc: river country, uplands, coast,
glass towns, interior. Night is shared blue in every region, tinted by the
region's darkest tones so places still differ after dark.
"""
import copy

# ridge layer shape: (y, amp, rough, parallax), far to near
_SHAPES = {
    "flat":   [(118, 6, 0.5, 0.15), (132, 5, 0.5, 0.35), (144, 3, 0.45, 0.6)],
    "hills":  [(112, 16, 0.55, 0.15), (126, 12, 0.6, 0.35), (140, 8, 0.5, 0.6)],
    "peaks":  [(96, 40, 0.62, 0.12), (120, 22, 0.6, 0.3), (138, 10, 0.55, 0.55)],
    "sea":    [(120, 3, 0.4, 0.1), (134, 1, 0.3, 0.3), (146, 6, 0.6, 0.6)],
    "skyline": [(114, 22, 0.35, 0.15), (130, 14, 0.4, 0.35), (142, 6, 0.5, 0.6)],
}

REGIONS = {
    # mills, grain, bonded labor: ochre haze over flat brown fields
    "river": {
        "shape": "flat",
        "day":   {"sky": ["sky3", "sky2", "sky1"], "layers": ["ash4", "ash3", "rust0"], "ground": ["rust0", "ash0"]},
        "dusk":  {"sky": ["sky1", "rust1", "ember0"], "layers": ["rust1", "rust0", "ink2"], "ground": ["ink2", "rust0"]},
        "night": {"sky": ["night0", "night1", "night2"], "layers": ["night2", "night1", "ink2"], "ground": ["ink1", "rust0"]},
        "weather": {"type": "ash", "density": 0.25, "wind": 0.2},
    },
    # cisterns, fungus cellars, pious and poor: mauve dusk over slate peaks
    "uplands": {
        "shape": "peaks",
        "day":   {"sky": ["mauve4", "mauve3", "ash4"], "layers": ["mauve3", "mauve2", "ash1"], "ground": ["ash0", "ash1"]},
        "dusk":  {"sky": ["mauve2", "mauve3", "mauve4"], "layers": ["mauve1", "mauve0", "ink1"], "ground": ["ink1", "mauve0"]},
        "night": {"sky": ["night0", "mauve0", "night2"], "layers": ["night2", "mauve0", "ink1"], "ground": ["ink0", "mauve0"]},
        "weather": {"type": "snow", "density": 0.3, "wind": 0.5},
    },
    # shellfish, kelp, salt: sea-teal and bone-white salt
    "coast": {
        "shape": "sea",
        "day":   {"sky": ["tide4", "ash5", "bone"], "layers": ["tide3", "tide2", "ash1"], "ground": ["ash2", "bone"]},
        "dusk":  {"sky": ["tide1", "tide2", "tide3"], "layers": ["tide2", "tide1", "ink1"], "ground": ["ink1", "tide1"]},
        "night": {"sky": ["night0", "tide0", "tide1"], "layers": ["tide1", "tide0", "ink0"], "ground": ["ink0", "tide0"]},
        "weather": {"type": "rain", "density": 0.3, "wind": 0.6},
    },
    # ruins of old cities, mined for salvage: rust-red sky, black skyline
    "glass": {
        "shape": "skyline",
        "day":   {"sky": ["blood3", "blood4", "sky2"], "layers": ["blood2", "blood1", "ink1"], "ground": ["ink1", "blood0"]},
        "dusk":  {"sky": ["blood1", "blood2", "blood3"], "layers": ["blood1", "blood0", "ink0"], "ground": ["ink0", "blood0"]},
        "night": {"sky": ["night0", "blood0", "blood1"], "layers": ["blood0", "ink1", "ink0"], "ground": ["ink0", "ink1"]},
        "weather": {"type": "ash", "density": 0.6, "wind": 0.35},
    },
    # unpeopled, wildlife returning, the Fold: wet green, fireflies at night
    "interior": {
        "shape": "hills",
        "day":   {"sky": ["fern4", "ash4", "ash5"], "layers": ["fern3", "fern2", "fern1"], "ground": ["fern1", "fern2"]},
        "dusk":  {"sky": ["fern2", "fern3", "sky2"], "layers": ["fern2", "fern1", "fern0"], "ground": ["fern0", "fern1"]},
        "night": {"sky": ["night0", "fern0", "night1"], "layers": ["fern1", "fern0", "ink0"], "ground": ["ink0", "fern0"]},
        "weather": {"type": "motes", "density": 0.4, "wind": 0.1},
    },
}


# Camera angle as a horizon shift (pixels; + moves the horizon down = more sky).
# Actors keep the y you give them, so put feet on the shifted ground line:
# ground y = 152 + shift.
ANGLES = {"eye": 0, "low": 22, "skyline": 14, "high": -34}


def expand(backdrop, weather=None):
    """Return (backdrop, weather) with the region preset filled in under the scene's own keys."""
    name = backdrop.get("region")
    if not name:
        return backdrop, weather
    R = REGIONS[name]
    look = R[backdrop.get("time", "day")]
    shape = _SHAPES[backdrop.get("shape", R["shape"])]
    base = {
        "sky": look["sky"],
        "horizon": 130,
        "layers": [{"color": col, "y": y, "amp": amp, "rough": r, "parallax": p}
                   for col, (y, amp, r, p) in zip(look["layers"], shape)],
        "ground": {"color": look["ground"][0], "y": 152, "speckle": look["ground"][1]},
    }
    shift = backdrop.get("shift", ANGLES.get(backdrop.get("angle", "eye"), 0))
    if backdrop.get("angle") == "skyline":  # one hard ridge, figures stand on its crest
        base["layers"] = base["layers"][:2]
    for L in base["layers"]:
        L["y"] += shift
    base["ground"]["y"] += shift
    base["horizon"] += shift
    out = copy.deepcopy(base)
    out.update({k: v for k, v in backdrop.items() if k not in ("region", "time", "shape", "angle", "shift")})
    if weather is None and backdrop.get("weather", True) is not False:
        weather = dict(R["weather"])
    return out, weather
