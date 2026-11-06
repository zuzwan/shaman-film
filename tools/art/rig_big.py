#!/usr/bin/env python3
"""Generate assets/sprites/rig_big.yaml: the rig at big size (zoom-3 scale, 128 px).

The same object as tools/art/rig.py, drawn three times larger so the faces read
as carved animals: two columns of seven housings on a salvaged mast, riveted
steel bands between rows, a crown of copper coil, a caged valve and a fan of
dead antenna rods worn like feathers, and at the foot the spike, base plate,
crank wheel and clamp leads. Auk's rig: 14 slots, 12 carved, 2 blank (bottom
right, raw pale wood).

Faces follow continuity.md: slot 1 (top left) is the cricket from Auk's
apprenticeship, read left to right, top down, to the twelfth worn smooth by his
thumb; 13 is the otter (ep 3) and 14 is Auk himself (ep 24). Slots 13 and 14
sit on the bottom row and are raw pale wood until they are cut.

States
  dark          a dead rig, a carved pole (12 faces)
  hum (2)       charged: 12 faces glowing, valve lit
  fF_N          F faces carved (12, 13 or 14), the first N glowing in capture
                order. The intro card climbs these, oldest face to newest.

    python tools/art/rig_big.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raster import Canvas, write_sprite  # noqa: E402

W, H = 52, 128
CX = 25                 # mast centre
FW, FH = 15, 10         # one face housing
ROW = FH + 2            # housing + steel band
TOP = 26                # first band
COLS = (CX - 2 - FW, CX + 3)   # x of left and right housings


def _carve_base(c, x, y, k):
    """The block of wood: lit from the top left, a carved rim, grain."""
    c.poly([(x, y), (x + FW, y), (x + FW, y + FH), (x, y + FH)], "rust1", shade=("rust0", "rust1", (-1, -0.6), 2))
    for gx in (x + 3, x + 9, x + 12):
        c.line(gx, y + 1 + (k % 2), gx + 1, y + FH - 2, "rust0")


def _eyes(c, pts, col, lit, size=2):
    """Eye sockets: size 1 (a pinhole), 2, or 3 (round lenses)."""
    for ex, ey in pts:
        o = -1 if size == 3 else 0
        c.rect(ex + o, ey + o, size, size, "ink0")
        if not lit:
            continue
        if size == 1:
            c.put(ex, ey, col)
        elif size == 2:
            c.put(ex, ey, col); c.put(ex + 1, ey, "ember1")
            c.put(ex, ey + 1, "ember1"); c.put(ex + 1, ey + 1, "ember0")
        else:
            c.rect(ex - 1, ey - 1, 3, 3, "ember0")
            c.put(ex, ey, col); c.put(ex - 1, ey - 1, "ember1")


def _ears(c, xs, y, w, h, col="rust1", inner="blood1"):
    for ex in xs:
        c.poly([(ex, y + 2), (ex + w / 2, y + 2 - h), (ex + w, y + 2)], col)
        if inner and h > 3:
            c.line(ex + w / 2, y + 3 - h + 2, ex + w / 2, y + 1, inner)


def face(c, x, y, kind, lit, k=0):
    """One carved face, FW x FH at (x, y); features may break the housing's edge.
    Auk's faces (continuity.md): cricket, dog, hare, mole, eel, fox, goat, rat,
    cat, pig, horse, a twelfth worn smooth by his thumb; 13 the otter (ep 3);
    14 Auk himself (ep 24)."""
    m = x + FW // 2
    e2 = "flame" if lit == 2 else "ember2"
    L, R = (m - 5, y + 3), (m + 3, y + 3)
    if kind == "blank":
        c.poly([(x, y), (x + FW, y), (x + FW, y + FH), (x, y + FH)], "ash3", shade=("ash2", "ash3", (-1, -0.6), 2))
        c.line(x + 4, y + 2, x + 5, y + FH - 2, "ash2"); c.line(x + 10, y + 1, x + 11, y + FH - 3, "ash2")
        return
    _carve_base(c, x, y, k)
    if kind == "cricket":
        for sx, d in ((m - 2, -1), (m + 2, 1)):  # long feelers swept back over the band
            c.line(sx, y + 1, sx + 5 * d, y - 4, "ash3"); c.put(sx + 6 * d, y - 4, "ash3")
        c.line(m - 3, y + 8, m - 1, y + 9, "ash4"); c.line(m + 3, y + 8, m + 1, y + 9, "ash4")  # mandibles
        c.line(m, y + 5, m, y + 7, "rust0")
        _eyes(c, [(m - 4, y + 4), (m + 4, y + 4)], e2, lit, 3)
    elif kind in ("dog", "fox"):
        if kind == "dog":  # ears folded down the sides
            for ex in (x - 1, x + FW - 2):
                c.rect(ex, y + 1, 3, 6, "rust0"); c.line(ex + 1, y + 2, ex + 1, y + 6, "ink1")
        else:
            _ears(c, (x + 1, x + FW - 6), y - 1, 5, 6)
        c.poly([(m - 3, y + 5), (m + 3, y + 5), (m + 2, y + 9), (m - 2, y + 9)], "rust0")
        c.rect(m - 1, y + 5, 3, 1, "ink0")
        c.line(m - 2, y + 8, m + 2, y + 8, "ink0")
        if kind == "fox":
            c.put(m - 1, y + 9, "ash4"); c.put(m + 1, y + 9, "ash4")
            c.line(x + 1, y + 6, m - 4, y + 9, "ash4"); c.line(x + FW - 2, y + 6, m + 4, y + 9, "ash4")
        _eyes(c, [L, R], e2, lit)
    elif kind == "hare":
        for ex in (m - 4, m + 2):
            c.rect(ex, y - 5, 3, 6, "rust1"); c.line(ex + 1, y - 4, ex + 1, y, "blood1")
        c.put(m, y + 6, "ink0"); c.line(m - 1, y + 7, m + 1, y + 7, "ink0")
        c.rect(m - 1, y + 8, 3, 1, "ash4")
        _eyes(c, [L, R], e2, lit)
    elif kind == "mole":
        c.ellipse(m + 0.5, y + 6.5, 3, 2.5, "blood2")  # the bare snout
        c.put(m - 1, y + 6, "ink0"); c.put(m + 1, y + 6, "ink0")
        for dx in (-6, -5, -4, 4, 5, 6):  # digging claws below
            c.line(m + dx, y + 8, m + dx, y + 10, "ash4")
        _eyes(c, [(m - 4, y + 3), (m + 4, y + 3)], e2, lit, 1)
    elif kind == "eel":
        c.poly([(x + 3, y), (x + FW - 3, y), (x + FW - 2, y + FH), (x + 2, y + FH)], "rust0")
        c.poly([(x + 4, y), (x + FW - 4, y), (x + FW - 3, y + FH - 1), (x + 3, y + FH - 1)], "rust1")
        for dx in range(-3, 4, 2):  # fin crest
            c.put(m + dx, y - 1, "ash3")
        c.line(m - 2, y + 8, m + 2, y + 8, "ink0"); c.line(m + 2, y + 8, m + 3, y + 7, "ink0")
        c.line(x + 3, y + 6, x + 3, y + 8, "ink1"); c.line(x + FW - 4, y + 6, x + FW - 4, y + 8, "ink1")  # gills
        _eyes(c, [(m - 3, y + 3), (m + 2, y + 3)], e2, lit)
    elif kind == "goat":
        for sx, d in ((x + 2, -1), (x + FW - 3, 1)):  # horns curving back
            c.line(sx, y + 1, sx + d, y - 3, "ash4"); c.line(sx + d, y - 3, sx + 3 * d, y - 4, "ash4")
        c.poly([(m - 2, y + 5), (m + 2, y + 5), (m + 1, y + 9), (m - 1, y + 9)], "rust0")
        c.line(m, y + 9, m, y + 12, "ash3"); c.put(m - 1, y + 11, "ash3")  # beard
        c.line(m - 6, y + 4, m - 3, y + 4, "ink0"); c.line(m + 3, y + 4, m + 6, y + 4, "ink0")  # slot pupils
        if lit:
            c.line(m - 5, y + 4, m - 4, y + 4, e2); c.line(m + 4, y + 4, m + 5, y + 4, e2)
    elif kind == "rat":
        for ex in (x, x + FW - 4):
            c.disc(ex + 2, y + 0.5, 2.2, "rust1"); c.put(ex + 2, y + 1, "blood1")
        c.poly([(m - 3, y + 5), (m + 3, y + 5), (m, y + 10)], "rust0")
        c.put(m, y + 9, "ink0")
        for wy in (y + 6, y + 8):
            c.line(x + 1, wy, m - 3, y + 7, "ash3"); c.line(x + FW - 2, wy, m + 3, y + 7, "ash3")
        _eyes(c, [(m - 4, y + 3), (m + 3, y + 3)], e2, lit)
    elif kind == "cat":
        _ears(c, (x + 1, x + FW - 5), y - 1, 4, 5)
        c.put(m, y + 6, "ink0"); c.line(m - 2, y + 8, m, y + 7, "ink0"); c.line(m, y + 7, m + 2, y + 8, "ink0")
        for wy in (y + 6, y + 8):
            c.line(x + 1, wy, m - 3, y + 7, "ash2"); c.line(x + FW - 2, wy, m + 3, y + 7, "ash2")
        _eyes(c, [(m - 4, y + 3), (m + 2, y + 3)], e2, lit)
    elif kind == "pig":
        for ex, d in ((x + 1, 1), (x + FW - 5, -1)):  # ears flopped forward
            c.poly([(ex, y), (ex + 4, y), (ex + 2 + d, y + 3)], "rust0")
        c.ellipse(m + 0.5, y + 6.5, 3.5, 2.5, "blood2")
        c.put(m - 1, y + 6, "ink0"); c.put(m + 1, y + 6, "ink0")
        c.line(m - 2, y + 9, m + 2, y + 9, "ink0")
        _eyes(c, [(m - 6, y + 3), (m + 4, y + 3)], e2, lit)
    elif kind == "horse":
        c.poly([(m - 4, y), (m + 4, y), (m + 3, y + FH), (m - 3, y + FH)], "rust1", shade=("rust0", "rust1", (-1, 0), 2))
        _ears(c, (m - 5, m + 2), y - 2, 3, 4, inner=None)
        c.line(m - 1, y, m + 1, y + 2, "ink1"); c.line(m, y, m - 1, y + 3, "ink1")  # forelock
        c.put(m - 2, y + 8, "ink0"); c.put(m + 2, y + 8, "ink0")
        c.line(m - 2, y + 10, m + 2, y + 10, "ink0")
        _eyes(c, [(m - 6, y + 4), (m + 5, y + 4)], e2, lit)
    elif kind == "worn":  # rubbed smooth by a thumb: only the eye dents are left
        c.poly([(m - 4, y + 3), (m + 5, y + 2), (m + 5, y + 8), (m - 4, y + 8)], "blood2", shade=("rust1", "blood2", (1, -1), 2))
        _eyes(c, [(m - 4, y + 4), (m + 3, y + 4)], e2, lit, 1)
        return
    elif kind == "otter":
        for ex in (x + 2, x + FW - 4):
            c.rect(ex, y, 2, 2, "rust1")
        c.poly([(m - 4, y + 5), (m + 4, y + 5), (m + 3, y + 9), (m - 3, y + 9)], "rust0")
        c.rect(m - 1, y + 5, 3, 1, "ink0")
        for wy in (y + 6, y + 8):
            c.line(x + 1, wy, m - 4, y + 7, "ash3"); c.line(x + FW - 2, wy, m + 4, y + 7, "ash3")
        _eyes(c, [(m - 4, y + 3), (m + 2, y + 3)], e2, lit)
        c.line(m - 4, y + 9, m + 4, y + 9, "blood1")  # the mouth Teal cut, his blood in it
    elif kind == "man":  # face 14: Auk, carved by Teal, raw wood still pale at the cuts
        c.poly([(x, y), (x + FW, y), (x + FW, y + FH), (x, y + FH)], "ash3", shade=("ash2", "ash3", (-1, -0.6), 2))
        c.line(m - 5, y + 2, m - 2, y + 2, "ink1"); c.line(m + 2, y + 2, m + 5, y + 2, "ink1")  # brows
        c.line(m, y + 3, m - 1, y + 7, "ink1"); c.put(m, y + 7, "ink1")                   # nose
        c.line(m - 3, y + 9, m + 3, y + 9, "ink0")                                          # mouth
        c.line(m + 4, y + 4, m + 5, y + 8, "rust1"); c.put(m + 4, y + 9, "rust1")             # the hooked scar
        _eyes(c, [(m - 4, y + 4), (m + 2, y + 4)], e2, lit)
        return
    # a carved brow line across every animal, catching the top-left light
    c.line(x + 2, y + 1, x + 5, y + 1, "blood4")


# The fourteen slots in capture order, read left to right, top down (slot 1 at
# the top left). Faces 13 and 14 sit on the bottom row and start blank.
SLOTS = ["cricket", "dog", "hare", "mole", "eel", "fox", "goat", "rat", "cat", "pig", "horse", "worn",
         "otter", "man"]


def build(filled=12, lit=0, glow=1):
    """`filled` faces carved, the first `lit` of them glowing; the valve lights with the first."""
    valve = lit > 0
    c = Canvas(W, H)
    # antenna rods fanned like feathers, all dead
    for i, ang in enumerate((-3, -2, -1, 0, 1, 2, 3)):
        top = 1 + abs(ang)
        c.line(CX + ang, 13, CX + ang * 4, top, "ash2" if i % 2 else "ash1")
        c.put(CX + ang * 4, top, "ash3")
    # copper coil
    for yy, half in ((14, 5), (16, 6), (18, 6), (20, 5)):
        c.line(CX - half, yy, CX + half, yy, "rust1")
        c.put(CX - half, yy, "blood4"); c.put(CX + half, yy, "rust0")
        c.line(CX - half + 1, yy + 1, CX + half - 1, yy + 1, "rust0")
    # valve under its cage
    c.ellipse(CX + 0.5, 11.5, 2.5, 3, "ember1" if valve else "cold1")
    if valve:
        c.put(CX, 11, "flame"); c.put(CX + 1, 10, "ember2")
    else:
        c.put(CX - 1, 10, "cold2")
    for cy in (9, 12):
        c.line(CX - 3, cy, CX + 3, cy, "ash1")
    c.line(CX - 3, 9, CX - 3, 14, "ash1"); c.line(CX + 3, 9, CX + 3, 14, "ash1")
    # the mast
    c.rect(CX - 2, 22, 5, 7 * ROW + 6, "ink2")
    c.line(CX - 2, 22, CX - 2, 22 + 7 * ROW + 5, "ash0")
    for r in range(7):
        y = TOP + r * ROW
        # riveted band
        c.rect(COLS[0] - 1, y, COLS[1] + FW - COLS[0] + 2, 2, "ash1")
        c.line(COLS[0] - 1, y, COLS[1] + FW, y, "ash2")
        for rx in range(COLS[0] + 1, COLS[1] + FW, 5):
            c.put(rx, y, "ash3")
        for s in (0, 1):
            n = r * 2 + s
            kind = SLOTS[n] if n < filled else "blank"
            face(c, COLS[s], y + 2, kind, (2 if glow == 2 else 1) if n < lit else 0, k=r + s)
    yb = TOP + 7 * ROW
    c.rect(COLS[0] - 1, yb, COLS[1] + FW - COLS[0] + 2, 2, "ash1")
    c.line(COLS[0] - 1, yb, COLS[1] + FW, yb, "ash2")
    # cable loop down the left side, plugged into three bands
    for yy in range(TOP + 4, yb - 2):
        c.put(COLS[0] - 4 + (1 if yy % 14 < 7 else 0), yy, "ash0")
    for py in (TOP + 4, TOP + 3 * ROW, yb - 3):
        c.line(COLS[0] - 4, py, COLS[0] - 1, py, "ink1")
    # clamp leads off the right edge, bone handles
    c.line(COLS[1] + FW + 1, TOP + 6, COLS[1] + FW + 4, TOP + 40, "ink1")
    c.line(COLS[1] + FW + 1, TOP + 10, COLS[1] + FW + 3, TOP + 46, "ink1")
    c.rect(COLS[1] + FW + 3, TOP + 41, 2, 3, "bone"); c.rect(COLS[1] + FW + 2, TOP + 47, 2, 3, "ash4")
    # foot: spike, base plate, crank wheel and battery
    c.rect(CX - 2, yb + 2, 5, 8, "ink2")
    c.rect(CX - 8, yb + 4, 6, 7, "rust0"); c.line(CX - 8, yb + 4, CX - 3, yb + 4, "blood4")  # wax-sealed battery
    c.rect(CX - 7, yb + 3, 2, 1, "ash4")
    wx, wy = CX + 8, yb + 7
    c.ring(wx + 0.5, wy + 0.5, 4.6, "ash2", 1.5)
    c.line(wx - 4, wy, wx + 4, wy, "ash1"); c.line(wx, wy - 4, wx, wy + 4, "ash1")
    c.put(wx, wy, "ash3")
    c.line(wx, wy, wx + 3, wy - 5, "ash3"); c.rect(wx + 3, wy - 7, 2, 2, "rust1")
    c.line(CX - 10, H - 4, CX + 13, H - 4, "ink1")
    c.poly([(CX - 2, H - 4), (CX + 3, H - 4), (CX, H - 1)], "ink1")
    c.rim("ash3", of={"ash1", "ash2", "ink2"}, direction=(-1, -1))
    c.outline("ink0")
    return c


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2] / "assets/sprites/rig_big.yaml"
    states = {"dark": [build(12, 0)], "hum": [build(12, 12, 1), build(12, 12, 2)]}
    for f in (12, 13, 14):
        for n in range(f + 1):
            states[f"f{f}_{n}"] = [build(f, n)]
    write_sprite(out, "rig_big",
                 "# The rig at big size (zoom 3, the scale of <name>_big figures), generated by\n"
                 "# tools/art/rig_big.py (see its docstring). States: dark, hum (2), and fF_N:\n"
                 "# F faces carved (12, 13, 14), the first N glowing. The intro card climbs these.",
                 (CX, H - 1), 3, states)
    print(out)
