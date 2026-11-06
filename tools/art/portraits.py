#!/usr/bin/env python3
"""Generate the close-shot sprites: faces and hands for punch-ins.

    python tools/art/portraits.py            # writes assets/sprites/{auk_close,teal_close,rig_face,hands_crank}.yaml

All face right. Anchors sit at the bottom centre so `path` places the chin
line; use them in shots with `zoom: 1` and a `plain` backdrop, or over a
dark set at zoom 1 (they are already close-shot scale).

auk_close    64x72  hooded profile, scar, beard, one lit eye.  idle(2) speak(3) glare(1)
teal_close   56x72  young, hair, scarf, pack strap.            idle(2) speak(3) flinch(1)
rig_face     80x64  one carved housing: lens eyes, band rivets, cable. dark(1) lit(2) flare(2)
hands_crank  72x44  Auk's hands turning the rig's crank.        crank(4)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raster import Canvas, write_sprite  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / "assets/sprites"


# ---------------------------------------------------------------- Auk
def auk(frame=0, speak=0, glare=False):
    W, H = 64, 72
    c = Canvas(W, H)
    b = 1 if frame % 2 else 0  # breath
    # cloak: a hunched mass, flat, with light only along the top of the shoulders
    c.poly([(0, 50 + b), (22, 44 + b), (50, 48 + b), (64, 58), (64, 72), (0, 72)], "ink1")
    c.poly([(0, 50 + b), (22, 44 + b), (50, 48 + b), (52, 52 + b), (22, 48 + b), (0, 54 + b)], "ink1",
           shade=("ink1", "ash0", (0, -1)))
    for x in range(2, 50, 6):  # ragged weave
        c.put(x, 60 + (x // 6) % 3, "ink0")
    # the hood's inside: black, so the face sits in shadow
    c.poly([(16, 14), (46, 12), (50, 30), (46, 46 + b), (18, 48 + b)], "ink0")
    # face in profile, pushed forward out of the dark; nose and chin clear the hood edge
    face = [(31, 18), (40, 18), (45, 24), (47, 30), (51, 35), (50, 38), (46, 39), (48, 43), (45, 48), (38, 52), (31, 52)]
    c.poly(face, "ash1")
    c.poly([(31, 18), (36, 18), (37, 52), (31, 52)], "ash0")      # the cheek side in shadow
    c.poly([(36, 18), (40, 18), (42, 24), (38, 26)], "ink0")       # brow shadow
    c.line(36, 24, 40, 24, "ash0"); c.line(37, 25, 39, 25, "ash0")  # brow ridge
    c.line(45, 25, 48, 30, "ash2"); c.line(49, 31, 51, 35, "ash2")  # nose bridge, lit
    c.line(47, 36, 50, 36, "ash0")                                   # nostril
    c.line(44, 40, 47, 40, "ink0")                                   # under the nose
    my = 44 + (speak > 0)
    c.line(42, my, 47, my, "ink0")                                   # mouth
    if speak == 2:
        c.line(43, my + 1, 46, my + 1, "ink0")
    c.rect(38, 28, 6, 3, "ink0")                                     # eye socket
    if glare:
        c.rect(39, 28, 5, 3, "ash3"); c.put(41, 29, "ink0")
    else:
        c.put(42, 29, "bone" if frame % 3 != 2 else "ash2")
    c.line(43, 32, 39, 42, "blood0"); c.put(41, 36, "blood1")        # scar
    c.line(35, 31, 33, 33, "ash0")                                   # crow's foot
    # beard: ragged and grey, hanging under the chin into the cloak
    c.poly([(34, 46), (46, 46 + speak), (48, 52), (44, 62), (36, 64), (30, 56)], "ash1",
           shade=("ash0", "ash1", (0, 1)))
    for x, y in [(36, 50), (41, 55), (38, 60), (44, 50), (33, 54)]:
        c.put(x, y, "ash2")
    for x, y in [(40, 48), (35, 58), (43, 58)]:
        c.put(x, y, "ink1")
    # the hood: angular cowl, flat colour, folds and a rim light along its ridge
    hood = [(10, 48 + b), (8, 26), (12, 10), (26, 2), (42, 4), (54, 16), (52, 30), (46, 46 + b), (36, 50 + b), (20, 52 + b)]
    cowl = Canvas(W, H)
    cowl.poly(hood, "ink1")
    # cut the opening: everything right of the front edge, below the brow, shows the face
    opening = [(42, 17), (52, 17), (56, 50 + b), (36, 50 + b), (40, 30)]
    for y in range(H):
        for x in range(W):
            if cowl.px[y][x] and not cowl._inside_poly(opening, x + 0.5, y + 0.5):
                c.put(x, y, "ink1")
    for (x0, y0), (x1, y1) in [((18, 8), (30, 4)), ((14, 24), (22, 12)), ((12, 40), (16, 22)), ((46, 10), (50, 16))]:
        c.line(x0, y0, x1, y1, "ink0")                              # folds
    for x, y in [(26, 2), (30, 2), (36, 3), (42, 4), (46, 7), (50, 11), (53, 15)]:
        c.put(x, y, "ash1")                                          # rim light on the ridge
    c.line(44, 18, 42, 24, "ash0")                                   # the opening's lit edge
    # the forked staff at the right edge
    c.rect(58, 0, 2, 72, "rust0")
    c.line(58, 6, 55, 0, "rust0"); c.line(59, 6, 62, 0, "rust0")
    c.put(59, 20, "rust1"); c.put(59, 40, "rust1")
    c.outline("ink0")
    return c


# ---------------------------------------------------------------- Teal
def teal(frame=0, speak=0, flinch=False):
    W, H = 56, 72
    c = Canvas(W, H)
    breath = 1 if frame % 2 else 0
    # jacket and the pack strap across it
    c.poly([(0, 50 + breath), (20, 44 + breath), (40, 46 + breath), (56, 54), (56, 72), (0, 72)], "ash0",
           shade=("ink1", "ash0", (1, -0.3)))
    c.poly([(8, 72), (14, 72), (34, 46 + breath), (28, 46 + breath)], "rust0")
    c.put(30, 50 + breath, "ash3")  # buckle
    # scarf: a wound band at the neck
    c.poly([(16, 40 + breath), (40, 40 + breath), (44, 48 + breath), (38, 52 + breath), (14, 50 + breath)], "rust1",
           shade=("rust0", "rust1", (1, 0)))
    c.line(18, 45 + breath, 40, 44 + breath, "rust0")
    # neck
    c.poly([(24, 34), (36, 34), (37, 42 + breath), (23, 42 + breath)], "ash1", shade=("ash0", "ash2", (1, 0)))
    # head: a rounder young face, chin pulled in a little when flinching
    fx = -2 if flinch else 0
    face = [(20, 8), (30, 6), (38 + fx, 10), (41 + fx, 18), (41 + fx, 26), (39 + fx, 31), (36 + fx, 35), (30, 38), (22, 36), (18, 28), (18, 14)]
    c.poly(face, "ash2", shade=("ash1", "ash3", (1, 0.1)))
    # hair: messy, dark, falling over the brow
    c.poly([(16, 12), (20, 4), (30, 1), (40, 3), (44, 9), (42 + fx, 16), (36, 12), (28, 11), (22, 16), (17, 20)], "ink1",
           shade=("ink0", "ink1", (0.5, -1)))
    for x, y in [(24, 3), (31, 2), (37, 5), (21, 8), (40, 11), (18, 16)]:
        c.put(x, y, "ash0")
    c.line(42 + fx, 14, 44 + fx, 20, "ink1")  # a lock over the ear
    # eye, brow, nose, mouth
    c.line(32 + fx, 16, 38 + fx, 15, "ink1")
    if flinch:
        c.line(33 + fx, 19, 37 + fx, 19, "ink0")  # shut tight
    else:
        c.rect(33 + fx, 18, 4, 3, "ink0")
        c.put(35 + fx, 19, "bone" if frame % 3 != 2 else "ash3")
    c.line(39 + fx, 20, 41 + fx, 26, "ash1")
    c.put(40 + fx, 27, "ash0")
    my = 31 + (speak > 0)
    c.line(35 + fx, my, 38 + fx, my, "ink0")
    if speak == 2:
        c.put(37 + fx, my + 1, "ink0")
    # cheek light
    c.put(37 + fx, 24, "ash3"); c.put(38 + fx, 25, "ash3")
    c.outline("ink0")
    return c


# ---------------------------------------------------------------- rig face
def rig_face(state="dark", frame=0):
    W, H = 80, 64
    c = Canvas(W, H)
    # the housing: three planks, lit from the top left, grain lines
    for i, (y0, y1) in enumerate(((8, 26), (26, 44), (44, 58))):
        c.poly([(6, y0), (74, y0), (74, y1), (6, y1)], "rust1", shade=("rust0", "rust1", (-0.6, -1)))
        c.line(6, y0, 74, y0, "blood4" if i == 0 else "rust0")
        c.line(6, y1 - 1, 74, y1 - 1, "ink1")
    for x in (12, 23, 38, 52, 63, 70):  # grain
        c.line(x, 12, x + 1, 24, "rust0"); c.line(x - 2, 30, x, 41, "rust0")
    # steel bands top and bottom with rivets
    for y in (3, 59):
        c.rect(0, y, 80, 4, "ash1")
        c.line(0, y, 79, y, "ash2")
        for x in range(4, 80, 11):
            c.put(x, y + 1, "ash3"); c.put(x, y + 2, "ash0")
    # carved wolf: ears cut into the top plank, muzzle grooves on the lower
    for ex in (16, 56):
        c.poly([(ex, 20), (ex + 8, 9), (ex + 14, 20)], "ink0")
        c.poly([(ex + 3, 19), (ex + 8, 12), (ex + 11, 19)], "rust0")
    c.poly([(30, 44), (50, 44), (54, 52), (40, 57), (26, 52)], "ink0")  # muzzle
    c.poly([(33, 46), (47, 46), (49, 51), (40, 54), (31, 51)], "rust0", shade=("rust0", "rust1", (0, -1)))
    c.line(36, 52, 44, 52, "ink0")
    for x in (34, 40, 46):
        c.put(x, 55, "ash2")  # teeth
    # the two lens eyes: brass ring, glass, a filament
    lens = {"dark": ("ink0", "ink1", "ash0"), "lit": ("ember0", "ember1", "ember2"), "flare": ("ember1", "ember2", "flame")}[state]
    for cx in (24, 56):
        c.ring(cx + 0.5, 32.5, 7.5, "ash2", 2)
        c.ring(cx + 0.5, 32.5, 8.5, "ash0", 1)
        c.ellipse(cx + 0.5, 32.5, 5.6, 5.6, lens[0], shade=(lens[0], lens[1], (0.5, 0.5)))
        if state == "dark":
            c.put(cx - 2, 30, "ash1")  # a reflection on dead glass
        else:
            fl = frame % 2
            c.put(cx + fl, 32, lens[2]); c.put(cx - 1 + fl, 33, lens[2])
            c.put(cx, 31, lens[1])
            c.put(cx + 3, 35, lens[2] if fl else lens[1])
        for rx, ry in ((cx - 7, 25), (cx + 7, 25), (cx - 7, 40), (cx + 7, 40)):
            c.put(rx, ry, "ash3")  # lens mount screws
    if state == "flare":  # the housing itself lights: dithered flame bleeding into the wood
        for y in range(22, 44):
            for x in range(10, 70):
                dx = min(abs(x - 24), abs(x - 56))
                d = ((dx / 9) ** 2 + ((y - 32) / 7) ** 2) ** 0.5
                if d < 1.9 and c.get(x, y) in ("rust0", "rust1", "ink1") and ((x * 7 + y * 3 + frame * 5) % 11) / 11 < (1.9 - d) * 0.7:
                    c.put(x, y, "ember0" if d > 1.3 else "ember1")
    # cable in from the left, clamped to the band; a lead to the eye
    c.rect(0, 12, 6, 2, "ash0")
    c.line(0, 11, 0, 20, "ash0")
    c.rect(4, 10, 4, 6, "ink1")
    c.put(5, 12, "ash2")
    c.line(8, 13, 16, 25, "ash0")
    c.outline("ink0")
    return c


# ---------------------------------------------------------------- hands on the crank
def hands_crank(frame=0):
    W, H = 72, 44
    c = Canvas(W, H)
    import math
    # the rig's foot: mast and base plate at right
    c.rect(60, 0, 6, 40, "ink2")
    c.rect(56, 40, 16, 3, "ink1")
    wx, wy = 48, 22
    c.ring(wx + 0.5, wy + 0.5, 9.5, "ash2", 2)
    c.ring(wx + 0.5, wy + 0.5, 3.5, "ash1", 1)
    c.put(wx, wy, "ash3")
    a = frame * math.pi / 2
    hx, hy = wx + math.cos(a) * 7, wy + math.sin(a) * 7
    c.line(wx, wy, hx, hy, "ash3")
    # the handle, and the fist around it
    c.rect(hx - 1, hy - 1, 3, 3, "rust1")
    # forearm from the left edge, sleeve then wrist, to the fist
    sleeve = [(0, hy - 7 + 10), (0, hy + 6 + 10), (hx - 14, hy + 5), (hx - 14, hy - 5)]
    c.poly([(sx, min(43, max(0, sy))) for sx, sy in sleeve], "ink1", shade=("ink0", "ink1", (0, -1)))
    c.poly([(hx - 15, hy - 4), (hx - 6, hy - 4), (hx - 6, hy + 4), (hx - 15, hy + 4)], "ash1", shade=("ash0", "ash2", (0, -1)))
    c.ellipse(hx - 2, hy, 5, 4, "ash1", shade=("ash0", "ash2", (-0.3, -1)))
    for i in range(3):  # knuckles
        c.put(hx - 5 + i * 2, hy - 3, "ash2")
    c.line(hx - 6, hy + 1, hx + 1, hy + 1, "ash0")
    # the second hand steadying the mast
    c.poly([(0, 2), (18, 2), (24, 6), (24, 14), (16, 16), (0, 14)], "ink1", shade=("ink0", "ink1", (0, -1)))
    c.poly([(24, 5), (40, 5), (60, 8), (60, 16), (40, 17), (24, 15)], "ash1", shade=("ash0", "ash2", (0.4, -1)))
    for i in range(4):
        c.line(44 + i * 4, 8, 44 + i * 4, 15, "ash0")
    c.outline("ink0")
    return c


if __name__ == "__main__":
    write_sprite(OUT / "auk_close.yaml", "auk_close",
                 "# Auk in close-up, generated by tools/art/portraits.py. Face right; zoom 1.\n"
                 "# idle breathes and blinks, speak cycles the mouth, glare widens the eye.",
                 (32, 71), 4, {"idle": [auk(0), auk(1), auk(2)], "speak": [auk(0, 1), auk(1, 2), auk(0, 1), auk(1, 0)],
                               "glare": [auk(0, 0, True)]})
    write_sprite(OUT / "teal_close.yaml", "teal_close",
                 "# Teal in close-up, generated by tools/art/portraits.py. Face right; zoom 1.\n"
                 "# idle breathes and blinks, speak cycles the mouth, flinch shuts the eyes and pulls the chin in.",
                 (28, 71), 4, {"idle": [teal(0), teal(1), teal(2)], "speak": [teal(0, 1), teal(1, 2), teal(0, 1), teal(1, 0)],
                               "flinch": [teal(0, 0, True)]})
    write_sprite(OUT / "rig_face.yaml", "rig_face",
                 "# One face-housing of the rig, insert size, generated by tools/art/portraits.py.\n"
                 "# dark: dead glass. lit: the filaments burn. flare: the housing takes a capture.",
                 (40, 63), 4, {"dark": [rig_face("dark")], "lit": [rig_face("lit", 0), rig_face("lit", 1)],
                               "flare": [rig_face("flare", 0), rig_face("flare", 1)]})
    write_sprite(OUT / "hands_crank.yaml", "hands_crank",
                 "# Auk's hands on the rig's crank, insert size, generated by tools/art/portraits.py.\n"
                 "# crank: four frames of the wheel turning; run at the sprite fps or faster with `fps`.",
                 (36, 43), 6, {"crank": [hands_crank(i) for i in range(4)]})
    print("wrote auk_close, teal_close, rig_face, hands_crank")
