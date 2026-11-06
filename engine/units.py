"""Density. Timelines are always written in the base grid (320 x 180); `unit: 2`
in a timeline renders the same scene on a 640 x 360 grid (upscaled x3 instead of
x6), with every sprite, texture and prop drawn with twice the pixels. The
engine multiplies the timeline's pixel values by the unit here, once, before a
scene is built; everything after that works in rendered pixels.

Keys that are seconds, ratios, counts, seeds or colours are left alone."""
import copy

_CAMERA = ("pan", "focus", "focus_lift", "follow_offset")
_ACTOR = ("path", "bob", "lift")
_PROP = ("pos", "x", "y", "width", "height", "rect", "spread", "radius", "halo", "thick",
         "length", "points", "path", "size", "step", "from", "to")
_LIGHT = ("pos", "radius", "offset")
_BACKDROP = ("horizon", "shift")


def _mul(v, u):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v * u
    if isinstance(v, list):
        return [_mul(x, u) for x in v]
    return v


def _keys(d, keys, u):
    for k in keys:
        if k in d:
            d[k] = _mul(d[k], u)


def _actor(a, u):
    _keys(a, _ACTOR, u)
    if isinstance(a.get("light"), dict):
        _keys(a["light"], _LIGHT, u)


def _backdrop(b, u):
    _keys(b, _BACKDROP, u)
    for L in b.get("layers", []):
        _keys(L, ("y", "amp"), u)
    if isinstance(b.get("ground"), dict):
        _keys(b["ground"], ("y",), u)
    for p in b.get("props", []):
        _keys(p, _PROP, u)


def _fx(f, u):
    if f.get("type") == "speedlines":
        _keys(f, ("center", "inner"), u)
    elif f.get("type") == "bars":
        _keys(f, ("size",), u)


def _shot(s, u):
    """A scene, shot or panel body: the keys they share."""
    if "camera" in s:
        _keys(s["camera"], _CAMERA, u)
        sh = s["camera"].get("shake")
        if isinstance(sh, (int, float)) and not isinstance(sh, bool):
            s["camera"]["shake"] = sh * u
        elif isinstance(sh, dict):
            _keys(sh, ("amp",), u)
    for a in s.get("actors", []):
        _actor(a, u)
    for patch in s.get("set", {}).values():
        _actor(patch, u)
    if "backdrop" in s:
        _backdrop(s["backdrop"], u)
    for f in s.get("fx", []):
        _fx(f, u)
    for L in s.get("lights", []):
        _keys(L, _LIGHT, u)


def scale_scene(spec, unit):
    """A deep copy of a scene spec with its pixel values multiplied by `unit`."""
    if unit == 1:
        return spec
    s = copy.deepcopy(spec)
    _keys(s, ("band",), unit)
    _shot(s, unit)
    for sh in s.get("shots", []):
        _shot(sh, unit)
    for p in s.get("panels", []):
        _keys(p, ("rect", "window"), unit)
        _shot(p, unit)
    return s
