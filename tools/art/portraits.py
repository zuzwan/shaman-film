#!/usr/bin/env python3
"""Close-shot sprites: faces in three-quarter view, and the rig inserts.

    python tools/art/portraits.py          # writes auk_close, teal_close, rig_face, hands_crank

Faces are built from one parametric head (`face`): skull, brow, two eyes, nose,
mouth, ear, with expression parameters (eyes, brow, mouth, gaze). Auk adds
lines, a beard, a scar and the hood; Teal adds hair, a scarf and a strap.
Both face right at three-quarter, light from the front-right. Used at zoom 1
over a `plain` backdrop; anchors at the bottom centre.

States (both): idle(4: breath and a blink) speak(4) glare(1) flinch(1)
               look_down(1) look_away(2) closed(1) grim(1)
rig_face: dark(1) lit(2) flare(2) wake(3)    hands_crank: crank(8)
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raster import Canvas, write_sprite  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "assets/sprites"


def expr(**k):
    e = dict(eyes=1.0, brow=0.0, mouth="closed", gaze=0.0, bob=0, lids=0.0, breath=0)
    e.update(k)
    return e


def face(c, ox, oy, k, e):
    """A three-quarter head in a 64x80 box at (ox, oy). k: colours and age. e: expression."""
    skin, dark, light = k["skin"], k["skin_dark"], k["skin_light"]
    oy += e["bob"]

    def P(pts):
        return [(ox + x, oy + y) for x, y in pts]
    # skull: an egg, jaw forward-right; lit from the right
    skull = [(18, 8), (30, 2), (44, 3), (54, 10), (58, 22), (58, 36), (55, 50), (49, 62), (40, 72), (28, 76), (19, 70), (13, 56), (10, 40), (11, 24)]
    c.poly(P(skull), skin, shade=(dark, skin, (1, -0.15), 2.5))
    # light on the forehead, cheekbone and the bridge of the nose
    c.poly(P([(40, 8), (52, 12), (56, 24), (50, 20), (42, 14)]), light, shade=(skin, light, (1, -1), 2))
    c.poly(P([(46, 40), (55, 38), (56, 46), (50, 50)]), light, shade=(skin, light, (1, 0), 2))
    # the hollow under the cheekbone and the temple
    c.poly(P([(40, 48), (52, 52), (48, 62), (38, 60)]), dark, shade=(dark, skin, (0.4, 1), 2))
    c.poly(P([(16, 24), (26, 22), (24, 40), (14, 44)]), dark, shade=(dark, skin, (1, 0), 2))
    # ear, far side
    c.poly(P([(8, 34), (13, 30), (16, 36), (15, 46), (10, 46)]), skin)
    c.poly(P([(10, 36), (13, 34), (13, 42)]), dark)
    # brow ridge and the shadow under it
    by = -e["brow"] * 2
    c.stroke(ox + 22, oy + 30 + by * 0.5, ox + 36, oy + 27 + by, dark, 2)
    c.stroke(ox + 40, oy + 27 + by, ox + 54, oy + 29 + by * 0.5, dark, 2)
    if k.get("heavy_brow"):
        c.stroke(ox + 40, oy + 26 + by, ox + 54, oy + 28 + by * 0.5, "ink1", 1)
    # eyes: near (right) and far (left); open amount from the expression
    for (cx, cy, w, hmax) in ((46, 35, 6, 3), (27, 36, 3, 2)):
        h = max(0, int(round(hmax * e["eyes"])))
        if h == 0:  # shut: a line
            c.stroke(ox + cx - w, oy + cy, ox + cx + w, oy + cy, "ink0", 1)
            continue
        white = k.get("white", "ash3")
        c.ellipse(ox + cx, oy + cy, w, h, white)
        c.stroke(ox + cx - w, oy + cy - h, ox + cx + w, oy + cy - h, dark, 1)  # the lid
        ix = cx + e["gaze"] * (w - 2)
        iw = 3 if w > 4 else 2
        c.rect(ox + ix - 1, oy + cy - 1, iw, 3 if h > 1 else 2, "ink0")
        if w > 4:
            c.put(ox + ix - 1, oy + cy - 1, "ink1")
            c.put(ox + ix + 1, oy + cy - 1, "bone")  # the glint
        else:
            c.put(ox + ix, oy + cy - 1, "ash3")
        if e["lids"] > 0:  # heavy lids: the top of the eye hidden by skin
            c.rect(ox + cx - w, oy + cy - h, 2 * w + 1, max(1, int(e["lids"] * h)), skin)
    # the near eye's socket shadow, and crow's feet with age
    c.stroke(ox + 39, oy + 38, ox + 52, oy + 38, dark, 1)
    if k.get("age", 0) > 0.5:
        c.stroke(ox + 53, oy + 33, ox + 57, oy + 31, dark, 1)
        c.stroke(ox + 53, oy + 37, ox + 57, oy + 39, dark, 1)
        c.stroke(ox + 24, oy + 16, ox + 46, oy + 14, dark, 1)   # forehead lines
        c.stroke(ox + 28, oy + 20, ox + 44, oy + 19, dark, 1)
    # nose: bridge from the brow to a tip forward-right, a nostril, a wing
    c.stroke(ox + 42, oy + 30, ox + 52, oy + 44, dark, 1)
    c.stroke(ox + 44, oy + 32, ox + 53, oy + 44, light, 1)
    c.poly(P([(50, 42), (58, 44), (57, 49), (49, 50)]), skin)
    c.put(ox + 54, oy + 48, "ink0"); c.put(ox + 55, oy + 48, "ink0")
    c.stroke(ox + 49, oy + 50, ox + 56, oy + 50, dark, 1)
    # mouth
    my = 58
    if e["mouth"] == "closed":
        c.stroke(ox + 38, oy + my, ox + 52, oy + my - 1, "ink0", 1)
        c.stroke(ox + 40, oy + my + 1, ox + 50, oy + my + 1, dark, 1)
    elif e["mouth"] == "grim":
        c.stroke(ox + 37, oy + my + 1, ox + 52, oy + my - 1, "ink0", 1)
        c.stroke(ox + 36, oy + my, ox + 37, oy + my + 2, "ink0", 1)
    else:
        h = {"small": 2, "open": 4, "wide": 6}[e["mouth"]]
        c.poly(P([(38, my - 1), (52, my - 2), (51, my + h), (39, my + h)]), "ink0")
        if h >= 4:
            c.stroke(ox + 41, oy + my, ox + 49, oy + my, "ash3", 1)  # teeth
    # the fold from the nose to the mouth, with age; chin shadow
    if k.get("age", 0) > 0.3:
        c.stroke(ox + 49, oy + 51, ox + 52, oy + 62, dark, 1)
    c.stroke(ox + 36, oy + 68, ox + 46, oy + 70, dark, 1)


def neck_shoulders(c, ox, oy, k, width=96):
    """Neck and the top of the shoulders, below the head box."""
    skin, dark = k["skin"], k["skin_dark"]
    c.poly([(ox + 22, oy + 66), (ox + 44, oy + 70), (ox + 42, oy + 84), (ox + 20, oy + 84)], skin, shade=(dark, skin, (1, 0), 2))
    coat = k["coat"]
    c.poly([(0, oy + 100), (ox + 12, oy + 82), (ox + 30, oy + 80), (ox + 52, oy + 84), (width, oy + 98), (width, oy + 128), (0, oy + 128)], coat,
           shade=(k["coat_dark"], coat, (1, -0.3), 2.5))


# ---------------------------------------------------------------- Auk
AUK = dict(skin="ash1", skin_dark="ash0", skin_light="ash2", white="ash2", age=1.0, heavy_brow=True,
           coat="ink1", coat_dark="ink0")


def auk(e):
    W, H = 96, 128
    c = Canvas(W, H)
    ox, oy = 18, 14
    neck_shoulders(c, ox, oy, AUK, W)
    # the cloak's collar and the hood's back, behind the head
    c.poly([(ox - 12, oy + 100), (ox - 8, oy + 20), (ox + 10, oy - 6), (ox + 40, oy - 10), (ox + 60, oy + 4), (ox + 56, oy + 60), (ox + 50, oy + 96)],
           "ink1", shade=("ink0", "ink1", (-0.4, -1), 2))
    face(c, ox, oy, AUK, e)
    # scar: from the brow down across the near cheek
    for i, (x, y) in enumerate([(50, 28), (49, 33), (48, 39), (47, 45), (46, 50)]):
        c.put(ox + x, oy + y + e["bob"], "blood1" if i % 2 else "blood0")
        c.put(ox + x + 1, oy + y + e["bob"], "ash0")
    # stubble and beard: grey strands down from the jaw, over the collar
    bob = e["bob"]
    beard = [(28, 54), (40, 62), (52, 60), (56, 66), (54, 80), (46, 92), (34, 96), (24, 90), (18, 76), (20, 62)]
    c.poly([(ox + x, oy + y + bob) for x, y in beard], "ash1", shade=("ash0", "ash1", (0.3, 1), 2))
    rng = [(23, 64), (29, 70), (36, 76), (44, 72), (50, 68), (27, 80), (34, 86), (41, 82), (48, 78), (31, 90), (38, 92), (44, 88), (22, 72), (52, 74)]
    for i, (x, y) in enumerate(rng):
        c.stroke(ox + x, oy + y + bob, ox + x + (1 if i % 3 else -1), oy + y + 6 + bob, ("ash2", "ash3", "ash0")[i % 3], 1)
    for x in range(22, 56, 3):  # stubble on the cheek
        c.put(ox + x + (x // 3) % 2, oy + 50 + (x % 5) + bob, "ash0")
    # the mouth over the beard
    if e["mouth"] in ("small", "open", "wide"):
        h = {"small": 2, "open": 4, "wide": 6}[e["mouth"]]
        c.poly([(ox + 38, oy + 57 + bob), (ox + 52, oy + 56 + bob), (ox + 51, oy + 58 + h + bob), (ox + 39, oy + 58 + h + bob)], "ink0")
    else:
        c.stroke(ox + 38, oy + 58 + bob, ox + 52, oy + 57 + bob, "ink0", 1)
    # the hood: a heavy cowl over the head, its opening edge down the front of the face
    hood = [(ox - 10, oy + 104), (ox - 10, oy + 30), (ox - 4, oy + 2), (ox + 16, oy - 14), (ox + 46, oy - 16), (ox + 66, oy - 4),
            (ox + 70, oy + 14), (ox + 60, oy + 8), (ox + 50, oy + 0), (ox + 36, oy - 2), (ox + 24, oy + 4), (ox + 16, oy + 14),
            (ox + 12, oy + 30), (ox + 14, oy + 50), (ox + 20, oy + 66), (ox + 24, oy + 84), (ox + 14, oy + 104)]
    c.poly(hood, "ink1", shade=("ink0", "ink1", (-0.5, -1), 2))
    # the inside of the hood, in shadow, along the opening
    c.poly([(ox + 16, oy + 14), (ox + 24, oy + 4), (ox + 36, oy - 2), (ox + 50, oy + 0), (ox + 60, oy + 8), (ox + 56, oy + 12),
            (ox + 46, oy + 6), (ox + 32, oy + 6), (ox + 22, oy + 16), (ox + 18, oy + 30), (ox + 20, oy + 50), (ox + 26, oy + 66),
            (ox + 30, oy + 84), (ox + 24, oy + 84), (ox + 20, oy + 66), (ox + 14, oy + 50), (ox + 12, oy + 30)], "ink0")
    # folds in the cowl, and the rim light along its ridge
    for (x0, y0), (x1, y1) in [((ox + 2, oy + 10), (ox - 4, oy + 60)), ((ox + 12, oy - 4), (ox + 6, oy + 30)), ((ox - 6, oy + 70), (ox - 8, oy + 100)),
                               ((ox + 22, oy + 76), (ox + 18, oy + 100))]:
        c.stroke(x0, y0, x1, y1, "ink0", 1)
    for x, y in [(ox + 16, oy - 13), (ox + 24, oy - 15), (ox + 36, oy - 16), (ox + 48, oy - 15), (ox + 58, oy - 10), (ox + 64, oy - 4), (ox + 68, oy + 4)]:
        c.put(x, y, "ash1"); c.put(x + 1, y + 1, "ash0")
    # the staff's fork at the right edge
    c.stroke(ox + 74, oy - 14, ox + 74, oy + 114, "rust0", 3)
    c.stroke(ox + 75, oy - 14, ox + 75, oy + 114, "rust1", 1)
    c.stroke(ox + 74, oy - 10, ox + 70, oy - 18, "rust0", 2); c.stroke(ox + 74, oy - 10, ox + 78, oy - 18, "rust0", 2)
    for yy in (oy + 20, oy + 48, oy + 76):
        c.stroke(ox + 72, yy, ox + 77, yy + 1, "ash0", 1)
    c.outline("ink0")
    return c


# ---------------------------------------------------------------- Teal
TEAL = dict(skin="ash2", skin_dark="ash1", skin_light="ash3", white="ash3", age=0.0,
            coat="ash0", coat_dark="ink2")


def teal(e):
    W, H = 88, 128
    c = Canvas(W, H)
    ox, oy = 14, 16
    neck_shoulders(c, ox, oy, TEAL, W)
    # pack strap and the scarf wound at the neck
    c.poly([(ox + 2, oy + 128), (ox + 14, oy + 128), (ox + 44, oy + 86), (ox + 36, oy + 84)], "rust0")
    c.put(ox + 24, oy + 110, "ash3"); c.put(ox + 25, oy + 110, "ash3")
    c.poly([(ox + 10, oy + 76), (ox + 50, oy + 78), (ox + 58, oy + 86), (ox + 54, oy + 96), (ox + 36, oy + 100), (ox + 8, oy + 94), (ox + 4, oy + 84)],
           "rust1", shade=("rust0", "rust1", (1, -0.5), 2))
    c.stroke(ox + 12, oy + 84, ox + 50, oy + 86, "rust0", 1)
    c.stroke(ox + 10, oy + 90, ox + 46, oy + 93, "rust0", 1)
    c.poly([(ox + 2, oy + 90), (ox + 10, oy + 92), (ox + 2, oy + 112), (ox - 6, oy + 110)], "rust1")  # the loose end
    # hair behind the head
    bob = e["bob"]
    c.poly([(ox + 6, oy + 50 + bob), (ox + 4, oy + 20 + bob), (ox + 14, oy - 2 + bob), (ox + 34, oy - 8 + bob), (ox + 54, oy - 2 + bob),
            (ox + 62, oy + 14 + bob), (ox + 58, oy + 40 + bob), (ox + 50, oy + 24 + bob), (ox + 20, oy + 30 + bob), (ox + 14, oy + 52 + bob)],
           "ink1", shade=("ink0", "ink1", (0.4, -1), 2))
    face(c, ox, oy, TEAL, e)
    # hair over the forehead: messy locks, some across the far eye
    locks = [[(14, 4), (30, -2), (48, 0), (58, 12), (56, 20), (48, 12), (40, 16), (30, 12), (22, 20), (16, 28), (12, 22)],
             [(20, 16), (28, 10), (30, 22), (24, 30)], [(40, 6), (48, 8), (52, 18), (44, 14)], [(12, 26), (18, 30), (14, 44), (8, 40)]]
    for i, lk in enumerate(locks):
        c.poly([(ox + x, oy + y + bob) for x, y in lk], "ink1" if i else "ink1", shade=("ink0", "ink2", (0.5, -1), 2))
    for x, y, col in [(24, 2, "ash0"), (36, -4, "ash0"), (50, 4, "ash0"), (18, 12, "ink0"), (44, 10, "ash0"), (30, 8, "ink0"), (56, 16, "ash0")]:
        c.put(ox + x, oy + y + bob, col)
    # a smear of dirt on the cheek, a chapped lip
    for x, y in [(50, 46), (52, 48), (49, 49)]:
        c.put(ox + x, oy + y + bob, "ash1")
    c.outline("ink0")
    return c


# ---------------------------------------------------------------- states
def face_states(builder):
    return {
        "idle": [builder(expr()), builder(expr(breath=1, bob=-1)), builder(expr(bob=-1)), builder(expr(eyes=0))],
        "speak": [builder(expr(mouth="small")), builder(expr(mouth="open", bob=-1)), builder(expr(mouth="wide")), builder(expr(mouth="small", bob=-1))],
        "glare": [builder(expr(brow=-1, lids=0.4, mouth="grim"))],
        "flinch": [builder(expr(eyes=0, brow=1, mouth="grim", bob=2))],
        "look_down": [builder(expr(gaze=0, lids=0.6, bob=3, brow=0.2))],
        "look_away": [builder(expr(gaze=-1)), builder(expr(gaze=-1, bob=-1))],
        "closed": [builder(expr(eyes=0, bob=1))],
        "grim": [builder(expr(mouth="grim", brow=-0.5))],
    }


# ---------------------------------------------------------------- rig face
def rig_face(state="dark", frame=0):
    W, H = 96, 72
    c = Canvas(W, H)
    # planks: three boards, grain, the carved wolf, lit from the top left
    for i, (y0, y1) in enumerate(((10, 30), (30, 50), (50, 64))):
        c.poly([(8, y0), (88, y0), (88, y1), (8, y1)], "rust1", shade=("rust0", "rust1", (-0.5, -1), 2))
        c.stroke(8, y0, 88, y0, "blood4" if i == 0 else "rust0", 1)
        c.stroke(8, y1 - 1, 88, y1 - 1, "ink1", 1)
    for x in (14, 27, 44, 61, 75, 84):
        c.stroke(x, 13, x + 2, 28, "rust0", 1); c.stroke(x - 3, 33, x - 1, 48, "rust0", 1); c.stroke(x + 1, 52, x + 2, 62, "rust0", 1)
    for y in (4, 66):  # steel bands, riveted
        c.rect(0, y, 96, 5, "ash1")
        c.stroke(0, y, 95, y, "ash2", 1)
        c.stroke(0, y + 4, 95, y + 4, "ash0", 1)
        for x in range(5, 96, 12):
            c.put(x, y + 1, "ash3"); c.put(x + 1, y + 2, "ash3"); c.put(x, y + 3, "ash0")
    for ex in (18, 64):  # ears cut into the top board
        c.poly([(ex, 26), (ex + 9, 12), (ex + 16, 26)], "ink0")
        c.poly([(ex + 3, 25), (ex + 9, 15), (ex + 13, 25)], "rust0", shade=("blood0", "rust0", (0, -1), 2))
    c.poly([(34, 50), (62, 50), (66, 58), (48, 63), (30, 58)], "ink0")  # muzzle
    c.poly([(37, 52), (59, 52), (62, 57), (48, 60), (34, 57)], "rust0", shade=("blood0", "rust0", (0, -1), 2))
    c.stroke(40, 58, 56, 58, "ink0", 1)
    for x in (40, 46, 52, 58):
        c.put(x, 61, "ash2")
    lens = {"dark": ("ink0", "ink1", "ash0"), "lit": ("ember0", "ember1", "ember2"), "flare": ("ember1", "ember2", "flame"),
            "wake": ("ink0", "ember0", "ember1")}[state]
    for cx in (28, 68):
        c.ring(cx + 0.5, 38.5, 9.5, "ash2", 2)
        c.ring(cx + 0.5, 38.5, 10.5, "ash0", 1)
        c.ring(cx + 0.5, 38.5, 8.5, "ash3", 1)
        c.ellipse(cx + 0.5, 38.5, 7.5, 7.5, lens[0], shade=(lens[0], lens[1], (0.5, 0.5), 1.5))
        if state == "dark":
            c.stroke(cx - 4, 34, cx - 2, 33, "ash1", 1)
        elif state == "wake":
            if frame >= 1:
                c.put(cx, 38, lens[2]); c.put(cx - 1, 39, lens[1])
            if frame >= 2:
                c.put(cx + 1, 38, lens[2]); c.put(cx, 37, lens[1]); c.put(cx + 3, 41, lens[1])
        else:
            fl = frame % 2
            c.put(cx + fl, 38, lens[2]); c.put(cx - 1 + fl, 39, lens[2]); c.put(cx, 37, lens[1]); c.put(cx + 3 - fl, 41, lens[2] if fl else lens[1])
            c.put(cx - 3, 36, lens[1])
        for rx, ry in ((cx - 9, 29), (cx + 9, 29), (cx - 9, 48), (cx + 9, 48)):
            c.put(rx, ry, "ash3"); c.put(rx + 1, ry + 1, "ash0")
    if state == "flare":
        for y in range(26, 52):
            for x in range(10, 86):
                dx = min(abs(x - 28), abs(x - 68))
                d = ((dx / 11) ** 2 + ((y - 38) / 9) ** 2) ** 0.5
                if d < 2.0 and c.get(x, y) in ("rust0", "rust1", "ink1", "blood0") and ((x * 7 + y * 3 + frame * 5) % 11) / 11 < (2.0 - d) * 0.7:
                    c.put(x, y, "ember0" if d > 1.4 else "ember1")
    # cable in from the left, clamped to the band, a lead to the near lens
    c.stroke(0, 14, 8, 14, "ash0", 2)
    c.stroke(0, 12, 0, 24, "ash0", 2)
    c.rect(6, 11, 5, 7, "ink1"); c.put(8, 14, "ash2")
    c.stroke(10, 15, 19, 30, "ash0", 1)
    c.outline("ink0")
    return c


# ---------------------------------------------------------------- hands on the crank
def hands_crank(frame=0, n=8):
    W, H = 80, 48
    c = Canvas(W, H)
    # the rig's foot: mast, base plate, the wheel with spokes
    c.rect(66, 0, 7, 44, "ink2"); c.stroke(66, 0, 66, 44, "ink1", 1); c.stroke(72, 0, 72, 44, "ash0", 1)
    c.rect(60, 44, 20, 3, "ink1")
    wx, wy = 52, 24
    c.ring(wx + 0.5, wy + 0.5, 10.5, "ash2", 2)
    c.ring(wx + 0.5, wy + 0.5, 11.5, "ash0", 1)
    a = frame * 2 * math.pi / n
    for i in range(4):
        sa = a + i * math.pi / 2
        c.stroke(wx, wy, wx + math.cos(sa) * 9, wy + math.sin(sa) * 9, "ash1", 1)
    c.ring(wx + 0.5, wy + 0.5, 3.5, "ash2", 1)
    c.put(wx, wy, "ash3")
    hx, hy = wx + math.cos(a) * 8, wy + math.sin(a) * 8
    c.stroke(wx, wy, hx, hy, "ash3", 2)
    c.rect(hx - 1, hy - 2, 4, 4, "rust1"); c.put(hx, hy - 2, "blood3")
    # the near forearm from the left edge to the fist on the handle: sleeve, wrist, fist with knuckles
    sx0, sy0 = 0, hy + 12
    c.stroke(sx0, sy0, hx - 12, hy + 2, "ink1", 9)
    c.stroke(sx0, sy0 - 3, hx - 14, hy - 1, "ink2", 2)  # the sleeve's lit edge
    for i in range(3):  # folds at the elbow
        c.stroke(8 + i * 4, sy0 - 4, 10 + i * 4, sy0 + 4, "ink0", 1)
    c.stroke(hx - 14, hy + 1, hx - 6, hy, "ash1", 7)
    c.ellipse(hx - 2, hy, 6, 4.5, "ash1", shade=("ash0", "ash2", (-0.3, -1), 2))
    for i in range(4):
        c.put(hx - 6 + i * 2.5, hy - 4, "ash2"); c.put(hx - 6 + i * 2.5, hy - 3, "ash0")
    c.stroke(hx - 7, hy + 1, hx + 2, hy + 1, "ash0", 1)
    c.stroke(hx - 7, hy + 3, hx + 1, hy + 3, "ash0", 1)
    c.put(hx + 3, hy - 1, "ash2")  # the thumb over the handle
    # the far hand steadying the mast, higher up
    c.stroke(0, 8, 26, 12, "ink1", 9)
    c.stroke(0, 4, 24, 8, "ink2", 1)
    c.stroke(26, 12, 60, 14, "ash1", 8)
    for i in range(4):
        c.stroke(46 + i * 4, 10, 46 + i * 4, 18, "ash0", 1)
    c.stroke(28, 9, 56, 11, "ash2", 1)
    c.outline("ink0")
    return c


if __name__ == "__main__":
    write_sprite(OUT / "auk_close.yaml", "auk_close",
                 "# Auk in close-up, three-quarter, generated by tools/art/portraits.py. Face right; zoom 1, plain backdrop.\n"
                 "# idle breathes and blinks; speak cycles the mouth; glare, flinch, look_down, look_away, closed, grim.",
                 (48, 127), 4, face_states(auk))
    write_sprite(OUT / "teal_close.yaml", "teal_close",
                 "# Teal in close-up, three-quarter, generated by tools/art/portraits.py. Face right; zoom 1, plain backdrop.\n"
                 "# idle breathes and blinks; speak cycles the mouth; glare, flinch, look_down, look_away, closed, grim.",
                 (44, 127), 4, face_states(teal))
    write_sprite(OUT / "rig_face.yaml", "rig_face",
                 "# One face-housing of the rig, insert size, generated by tools/art/portraits.py.\n"
                 "# dark: dead glass. wake: the filaments come up over three frames. lit: burning. flare: a capture.",
                 (48, 71), 4, {"dark": [rig_face("dark")], "wake": [rig_face("wake", i) for i in range(3)],
                               "lit": [rig_face("lit", 0), rig_face("lit", 1)], "flare": [rig_face("flare", 0), rig_face("flare", 1)]})
    write_sprite(OUT / "hands_crank.yaml", "hands_crank",
                 "# Auk's hands on the rig's crank, insert size, generated by tools/art/portraits.py. crank: 8 frames.",
                 (40, 47), 8, {"crank": [hands_crank(i) for i in range(8)]})
    print("wrote auk_close, teal_close, rig_face, hands_crank")
