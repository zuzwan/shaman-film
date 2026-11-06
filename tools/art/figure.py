#!/usr/bin/env python3
"""Pose-driven character generator: one skeleton, many costumes, two sizes.

    python tools/art/figure.py              # writes every character at wide and medium size
    python tools/art/figure.py auk teal     # just these

Characters are a costume over a shared side-view skeleton. Poses are joint
angles (degrees: 0 hangs straight down, + swings forward); walk and run cycles
are formulas, so every character gets the same full set of moves:

    idle(4) walk(8) run(6) turn(2) talk(4) crouch(2) kneel(1) sit(2) point(1)
    look_back(1) windup(1) strike(2) hit(2) stagger(2) down(1)
    + per character: crank(4, Auk), carry (Teal with the rig), lunge (raider)

Sizes: wide (26 px tall, the stage figure), medium (56 px, for zoom-2 shots;
drawn sharp, with a face) and big (78 px, for zoom-3 shots). Named <name>,
<name>_med and <name>_big; the engine picks by zoom when an actor has `med`.
Everything faces right; the actor flips. Light comes from the front-right.
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from raster import Canvas, write_sprite  # noqa: E402

HD = True  # the hyper-detailed style: every fill is textured by its material (engine/texture.py)


def texturize(c, k, H, seed=0):
    """Retone the figure's fills by material: cloth, wool, skin, hair, leather, wood."""
    import numpy as np
    from engine import texture
    from engine.palette import RGB
    kinds = {}
    hide = k.get("skull")
    for key, kind in (("coat", "hair" if hide else "cloth"), ("cloak", "wool"), ("hood", "wool"), ("trousers", "cloth"),
                      ("skin", "skin"), ("hair", "hair"), ("beard", "hair"), ("boots", "leather"), ("pack", "leather"),
                      ("scarf", "wool"), ("staff", "wood"), ("mask", "cloth"), ("cap", "cloth"), ("helmet", "leather"),
                      ("plate", "leather"), ("satchel", "leather")):
        col = k.get(key)
        if isinstance(col, str) and col not in kinds:
            kinds[col] = kind
    rgb = np.zeros((c.h, c.w, 3), np.uint8)
    names = np.empty((c.h, c.w), object)
    for y in range(c.h):
        for x in range(c.w):
            v = c.px[y][x]
            if v is not None:
                rgb[y, x] = RGB[v]
                names[y, x] = v
    amp = 0.55 if H < 40 else 0.95
    for col, kind in kinds.items():
        m = names == col
        if m.any():
            texture.texture(rgb, m, kind, 0, 0, seed=seed + hash(kind) % 97, amp=amp)
    back = {tuple(int(v) for v in RGB[n]): n for n in RGB}
    for y in range(c.h):
        for x in range(c.w):
            if names[y, x] is not None:
                c.px[y][x] = back.get(tuple(int(v) for v in rgb[y, x]), names[y, x])

OUT = Path(__file__).resolve().parents[2] / "assets/sprites"

# proportions, as fractions of standing height
PROP = dict(hip=0.47, torso=0.28, neck=0.05, head_r=0.105, thigh=0.24, shin=0.23, foot=0.07,
            upper=0.17, fore=0.16, sh_w=0.17, hip_w=0.14, leg_t=0.082, arm_t=0.062)

DARK = {"ink1": "ink0", "ink2": "ink1", "ash0": "ink2", "ash1": "ash0", "ash2": "ash1", "ash3": "ash2",
        "ash4": "ash3", "rust1": "rust0", "rust0": "blood0", "bone": "ash4", "ash5": "ash4", "fern2": "fern1"}
LIGHT = {"ink0": "ink1", "ink1": "ink2", "ink2": "ash0", "ash0": "ash1", "ash1": "ash2", "ash2": "ash3",
         "ash3": "ash4", "ash4": "ash5", "rust0": "rust1", "rust1": "blood3", "bone": "bone_hi", "fern2": "fern3"}


def rad(d):
    return d * math.pi / 180


# ------------------------------------------------------------------ poses
def pose(**k):
    base = dict(lean=0, hipF=0, kneeF=0, hipB=0, kneeB=0, shF=5, elF=10, shB=-5, elB=10,
                head=0, look=1, lift=0.0, breath=0.0, speed=0.0, squash=1.0, hip_y=None, spread=0.0)
    base.update(k)
    return base


def walk(i, n=8, amp=26, speed=0.5):
    p = 2 * math.pi * i / n
    return pose(hipF=amp * math.sin(p), hipB=amp * math.sin(p + math.pi),
                kneeF=42 * max(0.0, math.cos(p)), kneeB=42 * max(0.0, math.cos(p + math.pi)),
                shF=-amp * 0.7 * math.sin(p), shB=amp * 0.7 * math.sin(p),
                elF=15 + 20 * max(0.0, -math.sin(p)), elB=15 + 20 * max(0.0, math.sin(p)),
                lean=4, speed=speed)


def run(i, n=6):
    p = 2 * math.pi * i / n
    return pose(hipF=48 * math.sin(p), hipB=48 * math.sin(p + math.pi),
                kneeF=85 * max(0.0, math.cos(p)) + 10, kneeB=85 * max(0.0, math.cos(p + math.pi)) + 10,
                shF=-45 * math.sin(p), shB=45 * math.sin(p), elF=80, elB=80,
                lean=18, lift=0.05 * max(0.0, math.sin(2 * p)), speed=1.0, head=-4)


POSES = {
    "idle": [pose(), pose(breath=1), pose(), pose(lean=-2, hipB=4, kneeB=6, shF=8)],
    "turn": [pose(), pose(squash=0.45, shF=0, shB=0)],
    "talk": [pose(shF=35, elF=60, head=2), pose(shF=50, elF=40, head=0, breath=1), pose(shF=40, elF=75, head=-3), pose(shF=25, elF=55, head=1)],
    "crouch": [pose(hipF=55, kneeF=105, hipB=55, kneeB=105, lean=28, shF=40, elF=70, shB=35, elB=70, head=-6),
               pose(hipF=55, kneeF=105, hipB=55, kneeB=105, lean=26, shF=44, elF=66, shB=35, elB=70, head=-4, breath=1)],
    "kneel": [pose(hipF=88, kneeF=88, hipB=0, kneeB=90, lean=12, shF=30, elF=50, shB=10, elB=30, head=-8)],
    "sit": [pose(hipF=82, kneeF=28, hipB=82, kneeB=28, lean=10, shF=45, elF=60, shB=40, elB=60, head=-4),
            pose(hipF=82, kneeF=28, hipB=82, kneeB=28, lean=12, shF=45, elF=60, shB=40, elB=60, head=-6, breath=1)],
    "point": [pose(shF=92, elF=0, lean=3, head=2)],
    "look_back": [pose(look=-1, lean=-3, shF=0, shB=0)],
    "windup": [pose(lean=-10, shF=-70, elF=-20, shB=25, elB=30, hipF=-12, hipB=14, kneeB=10, head=4)],
    "strike": [pose(lean=24, hipF=46, kneeF=8, hipB=-28, kneeB=4, shF=82, elF=-5, shB=-45, elB=20, head=-2, speed=0.6),
               pose(lean=28, hipF=50, kneeF=6, hipB=-30, kneeB=6, shF=90, elF=-5, shB=-50, elB=20, head=-2, speed=0.6)],
    "hit": [pose(lean=-24, hipF=22, kneeF=4, hipB=-12, kneeB=10, shF=-30, elF=-70, shB=-30, elB=-70, head=-14),
            pose(lean=-32, hipF=28, kneeF=8, hipB=-16, kneeB=14, shF=-20, elF=-60, shB=-40, elB=-70, head=-20)],
    "stagger": [pose(lean=-14, hipF=-10, kneeF=20, hipB=30, kneeB=20, shF=-20, elF=40, shB=20, elB=40, head=-8),
                pose(lean=-18, hipF=22, kneeF=20, hipB=-6, kneeB=14, shF=10, elF=50, shB=-20, elB=40, head=-10)],
    "down": [pose(lean=86, hipF=-82, kneeF=14, hipB=-70, kneeB=36, shF=60, elF=30, shB=-20, elB=10, head=-30, hip_y=0.1)],
}
POSES["rear"] = [pose(lean=-12, shF=-150, elF=-25, shB=-150, elB=-25, head=12, hipF=-6, hipB=6)]
POSES["walk"] = [walk(i) for i in range(8)]
POSES["run"] = [run(i) for i in range(6)]
POSES["crank"] = [pose(lean=12, shF=40 + 18 * math.cos(2 * math.pi * i / 4), elF=55 - 35 * math.sin(2 * math.pi * i / 4),
                       shB=30, elB=50, hipF=6, hipB=-6, kneeB=6, head=-10) for i in range(4)]
POSES["lunge"] = [pose(lean=30, hipF=55, kneeF=10, hipB=-35, kneeB=8, shF=95, elF=-5, shB=-30, elB=40, head=-4, speed=0.8),
                  pose(lean=34, hipF=58, kneeF=6, hipB=-38, kneeB=6, shF=100, elF=-5, shB=-35, elB=40, head=-6, speed=0.8)]


# ------------------------------------------------------------------ skeleton
def joints(p, prop, H):
    """World joints in pixels, y down, feet on y=0 (negative above). Facing right."""
    thigh, shin = prop["thigh"] * H, prop["shin"] * H

    def leg_drop(hip, knee):
        return thigh * math.cos(rad(hip)) + shin * math.cos(rad(hip - knee))
    hip_y = p["hip_y"] * H if p["hip_y"] is not None else max(leg_drop(p["hipF"], p["kneeF"]), leg_drop(p["hipB"], p["kneeB"]))
    hip_y += p["lift"] * H
    J = {}
    J["hip"] = (0.0, -hip_y)
    lean = rad(p["lean"])
    tl = prop["torso"] * H + p["breath"] * 0.015 * H
    J["shoulder"] = (J["hip"][0] + math.sin(lean) * tl, J["hip"][1] - math.cos(lean) * tl)
    nk = prop["neck"] * H
    hl = rad(p["lean"] * 0.6 + p["head"] * 0.3)
    J["neck"] = (J["shoulder"][0] + math.sin(hl) * nk, J["shoulder"][1] - math.cos(hl) * nk)
    hr = prop["head_r"] * H
    J["head"] = (J["neck"][0] + math.sin(hl) * hr * 1.05, J["neck"][1] - math.cos(hl) * hr * 1.05)
    for side in ("F", "B"):
        h, k = rad(p["hip" + side]), rad(p["knee" + side])
        knee = (J["hip"][0] + math.sin(h) * thigh, J["hip"][1] + math.cos(h) * thigh)
        foot = (knee[0] + math.sin(h - k) * shin, knee[1] + math.cos(h - k) * shin)
        J["knee" + side], J["foot" + side] = knee, foot
        s, e = rad(p["sh" + side]), rad(p["el" + side])
        up, fo = prop["upper"] * H, prop["fore"] * H
        elbow = (J["shoulder"][0] + math.sin(s) * up, J["shoulder"][1] + math.cos(s) * up)
        hand = (elbow[0] + math.sin(s + e) * fo, elbow[1] + math.cos(s + e) * fo)
        J["elbow" + side], J["hand" + side] = elbow, hand
    return J


# ------------------------------------------------------------------ drawing
class Figure:
    def __init__(self, costume, H):
        self.k = costume
        self.H = H
        self.prop = dict(PROP, **costume.get("prop", {}))
        self.W = int(H * costume.get("canvas_w", 1.6)) + 4
        self.HH = int(H * costume.get("canvas_h", 1.22)) + 4
        self.ax = self.W // 2 - int(H * 0.12)
        self.ay = self.HH - 2
        self.med = H >= 40

    # pixel coordinates of a joint
    def px(self, pt, p):
        x, y = pt
        return self.ax + x * p["squash"], self.ay + y

    def limb(self, c, a, b, col, t, p):
        x0, y0 = self.px(a, p)
        x1, y1 = self.px(b, p)
        c.stroke(x0, y0, x1, y1, col, t)

    def draw(self, p):
        k, H = self.k, self.H
        c = Canvas(self.W, self.HH)
        J = joints(p, self.prop, H)
        leg_t, arm_t = self.prop["leg_t"] * H, self.prop["arm_t"] * H
        coat, trousers = k["coat"], k.get("trousers", k["coat"])
        skin = k.get("skin", "ash1")
        far_coat, far_tr = DARK.get(coat, "ink0"), DARK.get(trousers, "ink0")
        hands_col = k.get("gloves", skin)
        # far arm, far leg
        if k.get("arms", True):
            self.limb(c, J["shoulder"], J["elbowB"], far_coat, arm_t, p)
            self.limb(c, J["elbowB"], J["handB"], far_coat if k.get("sleeves", True) else DARK.get(skin, "ink1"), arm_t * 0.9, p)
            self.hand(c, J["handB"], DARK.get(hands_col, "ink1"), p)
        self.leg(c, J, "B", far_tr, DARK.get(k.get("boots", "ink0"), "ink0"), leg_t, p)
        # body
        if k.get("pack"):
            self.pack(c, J, p)
        if k.get("cloak"):
            self.cloak(c, J, p)
        self.torso(c, J, p)
        # near leg
        self.leg(c, J, "F", trousers, k.get("boots", "ink0"), leg_t, p)
        if k.get("cloak"):
            self.cloak_front(c, J, p)
        # head
        self.head(c, J, p)
        # near arm and what it holds
        if k.get("arms", True):
            self.limb(c, J["shoulder"], J["elbowF"], coat, arm_t, p)
            self.limb(c, J["elbowF"], J["handF"], coat if k.get("sleeves", True) else skin, arm_t * 0.9, p)
            if self.med and k.get("sleeves", True):
                ex, ey = self.px(J["elbowF"], p)
                wx, wy = self.px(J["handF"], p)
                c.disc(wx + (ex - wx) * 0.18, wy + (ey - wy) * 0.18, arm_t * 0.5, DARK.get(coat, "ink0"))  # cuff
            self.hand(c, J["handF"], hands_col, p)
        self.props(c, J, p)
        if k.get("rim"):
            c.rim(k["rim"], of=k.get("rim_of"))
        if HD:
            texturize(c, k, H, seed=self.H)
        c.outline("ink0")
        return c

    def hand(self, c, pt, col, p):
        x, y = self.px(pt, p)
        r = max(0.6, self.H * 0.03)
        c.disc(x, y, r, col)

    def leg(self, c, J, side, col, boot, t, p):
        hip, knee, foot = J["hip"], J["knee" + side], J["foot" + side]
        self.limb(c, hip, knee, col, t, p)
        self.limb(c, knee, foot, col, t * 0.9, p)
        if self.med and side == "F":
            kx, ky = self.px(knee, p)
            c.put(kx + 1, ky - 1, LIGHT.get(col, "ash0"))
        # boot: a short foot pointing the way the shin leans
        fx, fy = self.px(foot, p)
        fl = self.prop["foot"] * self.H
        if boot:
            c.stroke(fx - fl * 0.2, fy, fx + fl, fy, boot, t * 0.9)
            if self.med:
                kx, ky = self.px(knee, p)
                c.stroke(fx + (kx - fx) * 0.3, fy + (ky - fy) * 0.3, fx, fy, boot, t * 0.95)  # the boot's shaft
                c.stroke(fx - 1, fy - t * 0.6, fx + fl * 0.3, fy - t * 0.6, LIGHT.get(boot, "ink1"), 1)

    def torso(self, c, J, p):
        k, H = self.k, self.H
        sw, hw = self.prop["sh_w"] * H, self.prop["hip_w"] * H
        sx, sy = self.px(J["shoulder"], p)
        hx, hy = self.px(J["hip"], p)
        lean = rad(p["lean"])
        # perpendicular to the spine
        nx, ny = math.cos(lean), math.sin(lean)
        pts = [(sx - nx * sw, sy - ny * sw), (sx + nx * sw * 0.9, sy + ny * sw * 0.9),
               (hx + nx * hw, hy + ny * hw), (hx - nx * hw, hy - ny * hw)]
        if k.get("longcoat"):  # skirt of the coat hangs past the hips
            drop = H * 0.22
            sway = p["speed"] * H * 0.08
            pts = pts[:2] + [(hx + nx * hw * 1.2, hy + ny * hw + drop), (hx - nx * hw * 1.3 - sway, hy - ny * hw + drop)]
        c.poly(pts, k["coat"], shade=(DARK.get(k["coat"], "ink0"), k["coat"], (1, -0.2), 3) if self.med else None)
        if self.med:
            # a seam down the front, the collar, a belt unless a cloak covers it
            c.stroke(sx + nx * sw * 0.5, sy + ny * sw * 0.5, hx + nx * hw * 0.7, hy + ny * hw * 0.7, DARK.get(k["coat"], "ink0"), 1)
            if not k.get("hood"):
                c.poly([(sx - nx * sw * 0.5, sy - 1), (sx + nx * sw * 0.8, sy - 1), (sx + nx * sw * 0.6, sy + H * 0.05), (sx - nx * sw * 0.3, sy + H * 0.05)],
                       LIGHT.get(k["coat"], "ash1"))
            if not k.get("cloak") and not k.get("longcoat") and k.get("belt", "ink0"):
                c.stroke(hx - nx * hw * 1.05, hy - ny * hw - 1, hx + nx * hw * 1.05, hy + ny * hw - 1, k.get("belt", "ink0"), 1.5)
                c.put(hx + nx * hw * 0.4, hy - 1, "ash3")  # buckle
            if k.get("plate"):
                c.poly([(sx - nx * sw * 0.6, sy + 1), (sx + nx * sw * 0.7, sy + 1), (hx + nx * hw * 0.8, hy - 2), (hx - nx * hw * 0.6, hy - 2)],
                       k["plate"], shade=(DARK.get(k["plate"], "ash0"), LIGHT.get(k["plate"], "ash3"), (1, -0.5)))
            if k.get("belt"):
                c.stroke(hx - nx * hw, hy - ny * hw - 1, hx + nx * hw, hy + ny * hw - 1, k["belt"], 1.5)
            if k.get("strap"):  # pack strap across the chest
                c.stroke(sx - nx * sw * 0.8, sy, hx + nx * hw * 0.9, hy, k["strap"], max(1, H * 0.025))
        elif k.get("plate"):
            c.poly([(sx - nx * sw * 0.4, sy + 1), (sx + nx * sw * 0.6, sy + 1), (hx + nx * hw * 0.7, hy - 1), (hx - nx * hw * 0.4, hy - 1)], k["plate"])

    def cloak(self, c, J, p):
        """Behind the figure: the cloak from the shoulders to the hem, swinging back with speed."""
        k, H = self.k, self.H
        sx, sy = self.px(J["shoulder"], p)
        hem = self.ay - H * 0.03
        sway = p["speed"] * H * 0.16 + p["spread"] * H
        flutter = math.sin(p["hipF"] * 0.1) * H * 0.02
        back = sx - self.prop["sh_w"] * H * 1.1
        pts = [(back, sy - H * 0.02), (sx + self.prop["sh_w"] * H * 0.6, sy),
               (sx + self.prop["sh_w"] * H * 0.5, hem), (back - sway + flutter, hem), (back - sway * 0.8, (sy + hem) / 2)]
        col = k["cloak"]
        c.poly(pts, col, shade=(DARK.get(col, "ink0"), col, (1, -0.3)) if self.med else None)
        if self.med:  # folds
            for i in range(3):
                fx0 = back + (sx - back) * (0.3 + i * 0.25)
                c.stroke(fx0, sy + H * 0.12, fx0 - sway * 0.5 - H * 0.03 * i, hem - 1, DARK.get(col, "ink0"), 1)

    def cloak_front(self, c, J, p):
        """The front panel, over the near leg, ragged at the hem."""
        k, H = self.k, self.H
        sx, sy = self.px(J["shoulder"], p)
        hx, hy = self.px(J["hip"], p)
        hem = self.ay - H * 0.05
        fw = self.prop["sh_w"] * H * 0.75
        pts = [(sx + fw * 0.2, sy + H * 0.03), (sx + fw, sy + H * 0.05), (hx + fw * 1.05, hem), (hx - fw * 0.2 + p["speed"] * H * 0.05, hem)]
        col = k["cloak"]
        c.poly(pts, col, shade=(col, LIGHT.get(col, "ash0"), (1, 0)) if self.med else None)
        # ragged hem
        for i in range(int(fw * 1.4)):
            if i % 3 == 0:
                c.put(hx - fw * 0.2 + i, hem, None)
                c.put(hx - fw * 0.2 + i, hem - 1, None)

    def pack(self, c, J, p):
        k, H = self.k, self.H
        sx, sy = self.px(J["shoulder"], p)
        lean = rad(p["lean"])
        bx = sx - self.prop["sh_w"] * H * 0.9 - math.cos(lean) * H * 0.05
        by = sy + H * 0.02
        if k["pack"] == "rig":  # the rig bundle on Teal's back: a wrapped pole taller than her
            c.stroke(bx, by - H * 0.42, bx - H * 0.08, by + H * 0.3, "ink2", H * 0.11)
            for i in range(5):
                yy = by - H * 0.36 + i * H * 0.14
                c.stroke(bx - H * 0.06, yy, bx + H * 0.04, yy, "ash0", 1)
            c.put(bx, by - H * 0.44, "ember0")  # the antenna tip
        else:
            c.ellipse(bx, by + H * 0.08, H * 0.07, H * 0.13, k["pack"], shade=(DARK.get(k["pack"], "ink0"), k["pack"], (1, 0)) if self.med else None)
            if self.med:
                c.stroke(bx - H * 0.05, by - H * 0.02, bx + H * 0.05, by - H * 0.02, LIGHT.get(k["pack"], "ash1"), 1)
                c.stroke(bx - H * 0.07, by + H * 0.15, bx + H * 0.06, by + H * 0.15, DARK.get(k["pack"], "ink0"), 1)

    def head(self, c, J, p):
        k, H = self.k, self.H
        hx, hy = self.px(J["head"], p)
        r = self.prop["head_r"] * H
        look = p["look"]
        skin = k.get("skin", "ash1")
        if k.get("skull"):
            self.skull(c, hx, hy, r, look, p)
            return
        # the head, a touch longer than round; hair or hood behind
        if k.get("hair"):
            c.ellipse(hx - look * r * 0.15, hy - r * 0.1, r * 1.05, r * 1.1, k["hair"],
                      shade=(DARK.get(k["hair"], "ink0"), k["hair"], (0.5, -1)) if self.med else None)
        c.ellipse(hx, hy, r * 0.92, r, skin, shade=(DARK.get(skin, "ink1"), skin, (look, 0)) if self.med else None)
        if k.get("hair"):  # hair over the top and the back of the head
            c.poly([(hx - look * r, hy - r * 0.2), (hx - look * r * 0.9, hy - r * 1.1), (hx, hy - r * 1.25),
                    (hx + look * r * 0.8, hy - r * 1.0), (hx + look * r * 0.95, hy - r * 0.4), (hx + look * r * 0.4, hy - r * 0.5),
                    (hx - look * r * 0.3, hy - r * 0.3)], k["hair"],
                   shade=(DARK.get(k["hair"], "ink0"), k["hair"], (0.4 * look, -1)) if self.med else None)
        if self.med and k.get("hair"):
            for i, (ox, oy) in enumerate(((-0.7, -0.9), (-0.2, -1.15), (0.4, -1.0), (-0.95, -0.4))):
                c.put(hx + look * r * ox, hy + r * oy, LIGHT.get(k["hair"], "ash0") if i % 2 else DARK.get(k["hair"], "ink0"))
        if self.med and not k.get("hood") and not k.get("helmet"):
            c.put(hx - look * r * 0.05, hy, DARK.get(skin, "ink1"))  # ear
        # face
        ex, ey = hx + look * r * 0.45, hy - r * 0.15
        if self.med:
            c.rect(ex - 1, ey, 3, 2, "ink0")
            c.put(ex + look * 0.5, ey, "bone")
            c.stroke(hx + look * r * 0.85, hy - r * 0.05, hx + look * r * 1.02, hy + r * 0.25, DARK.get(skin, "ink1"), 1)  # nose
            c.stroke(hx + look * r * 0.5, hy + r * 0.5, hx + look * r * 0.85, hy + r * 0.5, "ink0", 1)  # mouth
            c.stroke(hx + look * r * 0.3, ey - 2, hx + look * r * 0.8, ey - 2, DARK.get(skin, "ink1"), 1)  # brow
        else:
            c.put(ex, ey, "ink0")
        if k.get("beard"):
            c.poly([(hx + look * r * 0.2, hy + r * 0.4), (hx + look * r * 0.95, hy + r * 0.3), (hx + look * r * 0.8, hy + r * 1.5),
                    (hx + look * r * 0.2, hy + r * 1.7), (hx - look * r * 0.1, hy + r * 1.0)], k["beard"],
                   shade=(DARK.get(k["beard"], "ash0"), k["beard"], (0, 1)) if self.med else None)
        if k.get("mask"):  # cloth over the lower face
            c.poly([(hx - look * r * 0.9, hy + r * 0.05), (hx + look * r * 1.0, hy + r * 0.05), (hx + look * r * 0.9, hy + r * 0.9),
                    (hx - look * r * 0.8, hy + r * 1.1)], k["mask"])
        if k.get("hood"):
            self.hood(c, hx, hy, r, look, p)
        if k.get("cap"):
            c.poly([(hx - look * r * 1.0, hy - r * 0.55), (hx + look * r * 1.3, hy - r * 0.55), (hx + look * r * 0.9, hy - r * 0.9),
                    (hx + look * r * 0.3, hy - r * 1.2), (hx - look * r * 0.9, hy - r * 1.05)], k["cap"])
        if k.get("helmet"):
            c.poly([(hx - look * r * 1.05, hy + r * 0.2), (hx - look * r * 1.0, hy - r * 0.7), (hx - look * r * 0.3, hy - r * 1.25),
                    (hx + look * r * 0.6, hy - r * 1.2), (hx + look * r * 1.05, hy - r * 0.5), (hx + look * r * 1.1, hy - r * 0.1)], k["helmet"],
                   shade=(DARK.get(k["helmet"], "ash0"), LIGHT.get(k["helmet"], "ash3"), (0.6, -1)) if self.med else None)
            c.stroke(hx - look * r * 1.0, hy - r * 0.1, hx + look * r * 1.1, hy - r * 0.1, DARK.get(k["helmet"], "ash0"), 1)
        if k.get("scarf"):
            self.scarf(c, J, p)

    def hood(self, c, hx, hy, r, look, p):
        k, H = self.k, self.H
        col = k["hood"]
        pts = [(hx - look * r * 1.35, hy + r * 1.3), (hx - look * r * 1.3, hy - r * 0.2), (hx - look * r * 0.7, hy - r * 1.25),
               (hx + look * r * 0.5, hy - r * 1.4), (hx + look * r * 1.25, hy - r * 0.7), (hx + look * r * 1.05, hy - r * 0.1),
               (hx + look * r * 0.55, hy - r * 0.3), (hx + look * r * 0.3, hy + r * 0.9), (hx + look * r * 0.4, hy + r * 1.4)]
        c.poly(pts, col, shade=(DARK.get(col, "ink0"), col, (-0.3 * look, -1)) if self.med else None)
        # the shadow inside the hood, over the brow
        c.poly([(hx + look * r * 0.05, hy - r * 0.6), (hx + look * r * 0.9, hy - r * 0.45), (hx + look * r * 0.8, hy - r * 0.15),
                (hx + look * r * 0.1, hy - r * 0.05)], "ink0")
        if self.med:
            c.stroke(hx - look * r * 0.9, hy - r * 0.9, hx - look * r * 1.1, hy + r * 1.0, DARK.get(col, "ink0"), 1)

    def scarf(self, c, J, p):
        k, H = self.k, self.H
        nx, ny = self.px(J["neck"], p)
        col = k["scarf"]
        c.stroke(nx - H * 0.08, ny + H * 0.025, nx + H * 0.07, ny + H * 0.025, col, max(1.5, H * 0.065))
        # the tail hangs down the back and lifts with speed
        tail = H * 0.22
        ang = rad(-150 + 60 * p["speed"] + math.sin(p["hipF"] * 0.08) * 10)
        tx, ty = nx - H * 0.07, ny + H * 0.04
        ex, ey = tx + math.sin(ang) * tail, ty - math.cos(ang) * tail
        c.stroke(tx, ty, ex, ey, col, max(1, H * 0.04))
        if self.med:
            c.put(ex, ey, DARK.get(col, "ink0"))
            c.put(nx + H * 0.02, ny + H * 0.025, DARK.get(col, "ink0"))  # the knot

    def skull(self, c, hx, hy, r, look, p):
        """The gaunt's head: a stag's skull, muzzle forward, black sockets, antlers."""
        k, H = self.k, self.H
        pts = [(hx - look * r * 0.9, hy - r * 0.6), (hx + look * r * 0.3, hy - r * 0.8), (hx + look * r * 1.6, hy + r * 0.2),
               (hx + look * r * 1.7, hy + r * 0.6), (hx + look * r * 0.6, hy + r * 0.8), (hx - look * r * 0.5, hy + r * 0.6),
               (hx - look * r * 1.0, hy)]
        c.poly(pts, "ash3", shade=("ash2", "bone", (0.4 * look, -1)))
        c.rect(hx + look * r * 0.1, hy - r * 0.25, max(1, r * 0.35), max(1, r * 0.3), "ink0")
        c.put(hx + look * r * 1.4, hy + r * 0.45, "ink0")
        if p.get("eyes"):
            c.put(hx + look * r * 0.2, hy - r * 0.15, "ember2")
        if self.med:
            c.stroke(hx + look * r * 0.5, hy + r * 0.6, hx + look * r * 1.3, hy + r * 0.5, "ash1", 1)  # the jaw line
            for i in range(3):
                c.put(hx + look * r * (0.7 + i * 0.3), hy + r * 0.75, "ash1")
        for side in (-1, 1):
            bx, by = hx + side * r * 0.5, hy - r * 0.7
            t = max(1, H * 0.02)
            c.stroke(bx, by, bx + side * r * 0.9, by - r * 1.2, "ash2", t)
            c.stroke(bx + side * r * 0.9, by - r * 1.2, bx + side * r * 1.8, by - r * 1.6, "ash2", t)
            c.stroke(bx + side * r * 0.45, by - r * 0.6, bx + side * r * 0.3, by - r * 1.5, "ash2", t)
            c.stroke(bx + side * r * 1.1, by - r * 1.25, bx + side * r * 1.1, by - r * 2.1, "ash2", t)
            for ex, ey in ((bx + side * r * 1.8, by - r * 1.6), (bx + side * r * 0.3, by - r * 1.5), (bx + side * r * 1.1, by - r * 2.1)):
                c.put(ex, ey, "ash3")

    def props(self, c, J, p):
        k, H = self.k, self.H
        fx, fy = self.px(J["handF"], p)
        if k.get("staff"):  # held upright in the near hand, slanting with the pose
            ang = rad(k.get("staff_angle", 6) + max(-40, min(40, p["shF"])) * 0.12)
            fx += k.get("staff_forward", 0.0) * H * max(0.0, 1 - abs(p["shF"]) / 40) * 2  # clear of the body when the arm hangs
            L = H * 1.1
            top = (fx - math.sin(ang) * L * 0.72, fy - math.cos(ang) * L * 0.72)
            bot = (fx + math.sin(ang) * L * 0.28, fy + math.cos(ang) * L * 0.28)
            c.stroke(top[0], top[1], bot[0], bot[1], k["staff"], max(1, H * 0.035))
            fl = H * 0.08
            c.stroke(top[0], top[1], top[0] - fl * 0.6, top[1] - fl, k["staff"], max(1, H * 0.03))
            c.stroke(top[0], top[1], top[0] + fl * 0.6, top[1] - fl, k["staff"], max(1, H * 0.03))
            if self.med:
                c.stroke(top[0] + 1, top[1], bot[0] + 1, bot[1], LIGHT.get(k["staff"], "rust1"), 1)
                for i in range(2):
                    yy = fy - H * 0.2 + i * H * 0.12
                    c.stroke(fx - 1, yy, fx + 2, yy, "ash0", 1)  # bindings
        if k.get("knife"):
            ang = rad(p["shF"] + p["elF"] - 90)
            L = H * 0.22
            c.stroke(fx, fy, fx + math.cos(ang) * L, fy + math.sin(ang) * L, "ash3", max(1, H * 0.03))
        if k.get("spear"):
            L = H * 1.3
            ang = rad(-8 + p["shF"] * 0.3)
            top = (fx + math.sin(ang) * L * 0.75, fy - math.cos(ang) * L * 0.75)
            bot = (fx - math.sin(ang) * L * 0.25, fy + math.cos(ang) * L * 0.25)
            c.stroke(top[0], top[1], bot[0], bot[1], "rust0", max(1, H * 0.035))
            c.stroke(top[0], top[1], top[0] + math.sin(ang) * H * 0.12, top[1] - math.cos(ang) * H * 0.12, "ash3", max(1, H * 0.05))
        if k.get("pole"):  # the chainman's ranging pole, red and white
            L = H * 1.2
            for i in range(6):
                y0 = fy - L * 0.7 + i * L / 6
                c.stroke(fx + H * 0.05, y0, fx + H * 0.05, y0 + L / 6, "blood3" if i % 2 else "ash5", max(1, H * 0.035))
        if k.get("lantern"):
            ly = fy + H * 0.12
            c.stroke(fx, fy, fx, ly - H * 0.05, "ash0", 1)
            c.rect(fx - H * 0.04, ly - H * 0.06, max(2, H * 0.08), max(2, H * 0.1), "ash0")
            c.rect(fx - H * 0.025, ly - H * 0.045, max(1, H * 0.05), max(1, H * 0.07), "ember2")
            c.put(fx, ly - H * 0.03, "flame")
        if k.get("satchel"):
            hx, hy = self.px(J["hip"], p)
            c.rect(hx - H * 0.1, hy - H * 0.04, max(2, H * 0.12), max(2, H * 0.1), k["satchel"])


# ------------------------------------------------------------------ costumes
COSTUMES = {
    "auk": dict(coat="ink2", trousers="ink1", boots="ink0", skin="ash1", cloak="ink1", hood="ink2", beard="ash2",
                staff="rust0", rim="ash0", rim_of={"ink1", "ink2"}, prop=dict(torso=0.26, head_r=0.1), hunch=10,
                staff_forward=0.1,
                states=["idle", "walk", "run", "turn", "talk", "crouch", "kneel", "sit", "point", "look_back",
                        "windup", "strike", "hit", "stagger", "down", "crank"]),
    "teal": dict(coat="ash0", trousers="ink2", boots="ink1", skin="ash2", hair="ink1", scarf="rust1", pack="rust0",
                 strap="rust0", lantern=False, rim="ash1", rim_of={"ash0"}, prop=dict(head_r=0.11, thigh=0.23, shin=0.22),
                 states=["idle", "walk", "run", "turn", "talk", "crouch", "kneel", "sit", "point", "look_back",
                         "windup", "strike", "hit", "stagger", "down"]),
    "teal_lantern": dict(base="teal", lantern=True, states=["idle", "walk", "run", "look_back"]),
    "teal_rig": dict(base="teal", pack="rig", states=["idle", "walk", "run", "crouch", "look_back", "hit", "stagger"]),
    "raider": dict(coat="rust0", trousers="ink1", boots="ink0", skin="ash1", hair="ink0", mask="rust1", knife=True,
                   belt="ink0", rim="rust1", rim_of={"rust0"},
                   states=["idle", "walk", "run", "turn", "crouch", "point", "look_back", "windup", "lunge", "hit", "stagger", "down"]),
    "chainman": dict(coat="ash2", trousers="ash1", boots="ink1", skin="ash2", cap="ash1", pole=True, rim="ash3", rim_of={"ash2"},
                     states=["idle", "walk", "run", "turn", "talk", "crouch", "kneel", "point", "look_back", "hit", "down"]),
    "clerk": dict(coat="ash3", trousers="ink2", boots="ink1", skin="ash2", hair="ash0", longcoat=True, satchel="rust0",
                  rim="ash4", rim_of={"ash3"},
                  states=["idle", "walk", "turn", "talk", "sit", "point", "look_back", "hit", "stagger"]),
    "guard": dict(coat="ink2", trousers="ink1", boots="ink0", skin="ash1", helmet="ash2", plate="ash1", spear=True,
                  rim="ash0", rim_of={"ink2"},
                  states=["idle", "walk", "run", "turn", "crouch", "point", "look_back", "windup", "strike", "hit", "stagger", "down"]),
    "fold_host": dict(coat="ash2", trousers="ash2", boots=None, skin="ash2", hair="ash0", rim="ash3", rim_of={"ash2"},
                      states=["idle", "walk", "turn", "talk", "kneel", "sit", "point", "look_back", "hit", "down"]),
    "gaunt": dict(coat="ink1", trousers="ink1", boots=None, skin="ink1", sleeves=False, gloves="ink1", skull=True,
                  prop=dict(hip=0.5, torso=0.3, thigh=0.26, shin=0.27, upper=0.27, fore=0.3, sh_w=0.1, hip_w=0.07,
                            leg_t=0.045, arm_t=0.035, head_r=0.085, foot=0.03),
                  canvas_w=1.5, canvas_h=1.35, scale=2.0, rim="ink2", rim_of={"ink1"},
                  states=["idle", "walk", "run", "turn", "crouch", "look_back", "rear", "lunge", "hit", "stagger", "down"]),
}
GAUNT_STATES = {"walk": "stalk"}  # renamed on write


def expand(name):
    k = dict(COSTUMES[name])
    if "base" in k:
        base = expand(k.pop("base"))
        states = k.pop("states")
        base.update(k)
        base["states"] = states
        return base
    return k


def build(name, H):
    k = expand(name)
    H = int(H * k.get("scale", 1.0))
    fig = Figure(k, H)
    states = {}
    for st in k["states"]:
        frames = []
        for p in POSES[st]:
            p = dict(p)
            if name == "gaunt":
                p["eyes"] = st in ("lunge", "rear", "look_back")
                p["lean"] += 8
                p["shF"] += 10 if st in ("idle", "walk") else 0
            if k.get("hunch"):
                p["lean"] += k["hunch"]
                p["head"] -= 6
            frames.append(fig.draw(p))
        states[GAUNT_STATES.get(st, st) if name == "gaunt" else st] = frames
    return fig, states


SIZES = {"": 26, "_med": 56, "_big": 78}  # wide, zoom-2 and zoom-3 shots
NAMES = {"auk": "auk", "teal": "teal"}  # file names equal costume names


def main(names):
    names = names or [n for n in COSTUMES]
    for name in names:
        for suffix, H in SIZES.items():
            fig, states = build(name, H)
            out = OUT / f"{name}{suffix}.yaml"
            fps = 6 if suffix == "" else 8
            if name == "gaunt":
                fps = 4
            write_sprite(out, f"{name}{suffix}",
                         f"# {name}{suffix}: generated by tools/art/figure.py (pose-driven; edit the costume or\n"
                         f"# the poses there and re-run). Faces right. States: {', '.join(states)}.",
                         (fig.ax, fig.ay), fps, states)
            print(out.name, f"{fig.W}x{fig.HH}", sum(len(v) for v in states.values()), "frames")


if __name__ == "__main__":
    main(sys.argv[1:])
