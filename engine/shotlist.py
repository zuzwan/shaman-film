"""The shot vocabulary: names from the script's SHOT lines turned into camera,
backdrop and fx defaults. Explicit keys on the shot always win.

    shots:
      - {shot: "close · low · auk · push-in", duration: 1.2}
      - {shot: {size: medium, angle: over-shoulder, subject: teal, move: track}}

The same vocabulary is what tools/script2timeline.py writes, so a script line
    SHOT: close · low · Auk · push-in · 2s
lands here unchanged. See docs/shots.md for the catalogue.

size    extreme-wide | wide | medium | close | insert
angle   eye | low | high | skyline | over-shoulder | pov | framed
move    static | pan-left | pan-right | push-in | pull-out | track | shake
subject an actor id: the camera focuses on (and `track` follows) that actor
"""
import copy

SIZES = {
    "extreme-wide": {"zoom": 1, "bars": 16},
    "wide": {"zoom": 1},
    "medium": {"zoom": 2},
    "close": {"zoom": 3},
    "insert": {"zoom": 4},
}
ANGLE_SHIFT = {"low": "low", "high": "high", "skyline": "skyline", "eye": "eye"}
FRAMING = {  # foreground props a named angle adds (layer front)
    "over-shoulder": [{"type": "shoulder", "side": "left", "layer": "screen", "rim": "ink2"}],
    "framed": [{"type": "doorway", "rect": [64, 14, 192, 166], "layer": "front", "rim": "ink2"}],
}
PAN = 36  # pixels a pan covers in one shot


def parse(shot):
    """'close · low · auk · push-in' -> dict. Words are matched loosely, in any order."""
    if isinstance(shot, dict):
        return dict(shot)
    out = {}
    for part in [p.strip().lower() for p in str(shot).replace("|", "·").replace(",", "·").split("·")]:
        if not part:
            continue
        key = part.replace(" ", "-")
        if key in SIZES:
            out["size"] = key
        elif key in ANGLE_SHIFT or key in FRAMING:
            out["angle"] = key
        elif key in ("static", "pan-left", "pan-right", "push-in", "pull-out", "track", "shake"):
            out["move"] = key
        elif part.endswith("s") and part[:-1].replace(".", "").isdigit():
            out["hold"] = float(part[:-1])
        elif part.endswith("f") and part[:-1].isdigit():
            out["hold_frames"] = int(part[:-1])
        else:
            out.setdefault("subject", part.split()[0])  # 'auk draws the knife' -> auk
    return out


def resolve(shot, base, fps=12, unit=1):
    """Return `shot` with camera/backdrop/fx defaults from its `shot` vocabulary filled in."""
    if "shot" not in shot:
        return shot
    v = parse(shot["shot"])
    out = {k: copy.deepcopy(x) for k, x in shot.items() if k != "shot"}
    cam = dict(out.get("camera", {}))
    bd = dict(out.get("backdrop", {}))
    fx = list(out.get("fx", []))
    props = None

    size = SIZES.get(v.get("size", "wide"), SIZES["wide"])
    z = size["zoom"]
    if "bars" in size:
        fx.append({"type": "bars", "size": size["bars"]})

    ids = {a.get("id") for a in base.get("actors", [])}
    subj = v.get("subject") if v.get("subject") in ids else None
    if subj:
        cam.setdefault("focus_on", subj)

    ang = v.get("angle", "eye")
    if ang in ANGLE_SHIFT and ang != "eye":
        bd.setdefault("angle", ang)
    if ang == "pov":
        fx.append({"type": "vignette", "inner": 0.45, "amount": 1.0})
    if ang in FRAMING:
        framing = copy.deepcopy(FRAMING[ang])
        for p in framing:
            if "rect" in p:
                p["rect"] = [v * unit for v in p["rect"]]
        props = list(base.get("backdrop", {}).get("props", [])) + framing
        if ang == "over-shoulder":
            z = max(z, 2)

    move = v.get("move", "static")
    pan0 = base.get("camera", {}).get("pan", [0, 0])[0]
    if move == "pan-left":
        cam.setdefault("pan", [pan0 + PAN * unit / 2, pan0 - PAN * unit / 2])
    elif move == "pan-right":
        cam.setdefault("pan", [pan0 - PAN * unit / 2, pan0 + PAN * unit / 2])
    elif move == "push-in":
        cam.setdefault("zoom", [z, z + 1])
    elif move == "pull-out":
        cam.setdefault("zoom", [z + 1, z])
    elif move == "track" and subj:
        cam.setdefault("follow", subj)
    elif move == "shake":
        cam.setdefault("shake", {"amp": 3 * unit, "decay": 1.0})
    cam.setdefault("zoom", z)

    if "hold" in v:
        out.setdefault("duration", v["hold"])
    elif "hold_frames" in v:
        out.setdefault("duration", v["hold_frames"] / fps)
    out["camera"] = cam
    if bd:
        out["backdrop"] = bd
    if props is not None:
        out.setdefault("backdrop", {})["props"] = props
    if fx:
        out["fx"] = fx
    return out
