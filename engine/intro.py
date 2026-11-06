"""The intro card: the same opening on every episode.

    intro: {episode: 1, title: "Here"}          # in an episode's timeline.yaml

render.py puts it in front of the first scene as `s00_intro`. The show title
and the act colours come from assets/show.yaml. It runs INTRO_LENGTH seconds
on the full 320x180 frame (no text band):

    0.0  black
    0.8  a night ridge dithers in, the rig planted on it, dead
    2.2  its faces light one by one, oldest capture to newest (the valve first)
    6.0  the valve is lit; the show title dithers in            <- the sting hits here
    7.6  the episode number and name dither in under it
   11.0  everything dithers to black; the episode cuts in at 12.0

Sound is not built yet. STING marks the window the score will fill: the
sting starts out of the black, swells under the faces and hits with the
title. render.py writes it to out/<ep>/cues.yaml for the audio pass.
"""
from pathlib import Path

import numpy as np
import yaml

from . import textfont
from .dither import mask
from .palette import RGB
from .scene import Scene

INTRO_LENGTH = 12.0
FADE_IN = (0.8, 2.4)
LIGHTS_FROM, LIGHTS_TO = 2.2, 5.8   # every face is lit by LIGHTS_TO, however many
TITLE_AT, TITLE_FADE = 6.0, 0.8
EPISODE_AT, EPISODE_FADE = 7.6, 0.6
FADE_OUT = (11.0, 12.0)
STING = {"start": 0.8, "hit": TITLE_AT, "end": FADE_OUT[1]}

RIG_X, RIG_Y = 92, 170          # where the rig is planted (its foot)
TEXT_CX = 222                   # centre line of the lettering

NUMBERS = ("Zero One Two Three Four Five Six Seven Eight Nine Ten Eleven Twelve Thirteen Fourteen "
           "Fifteen Sixteen Seventeen Eighteen Nineteen Twenty").split()


def show(path=None):
    path = Path(path or Path(__file__).resolve().parents[1] / "assets/show.yaml")
    return yaml.safe_load(open(path))


def _words(n):
    if n <= 20:
        return NUMBERS[n]
    return f"Twenty-{NUMBERS[n - 20].lower()}"


def spec(intro, show_data=None):
    """The intro as a scene spec for the engine: backdrop, the big rig, its light."""
    s = show_data or show()
    ep = int(intro.get("episode", 1))
    region = intro.get("region") or next(
        (a["region"] for a in s.get("acts", []) if a["episodes"][0] <= ep <= a["episodes"][1]), "river")
    faces = s.get("faces", {})
    return {
        "id": "s00_intro",
        "duration": INTRO_LENGTH,
        "band": 0,
        "backdrop": {"region": region, "time": "night", "seed": 131,
                     "props": [{"type": "moon", "pos": [292, 26], "r": 5, "halo": 16, "glow": 0.35,
                                "layer": -1, "parallax": 0}]},
        "weather": {"type": "motes", "density": 0.25},
        "actors": [{"id": "rig", "sprite": "rig_big", "state": "dark", "path": [[RIG_X, RIG_Y]]}],
        "lights": [],
        "intro": {"episode": ep, "title": intro.get("title", ""), "show": s["title"],
                  "faces": int(intro.get("faces", faces.get(ep, faces.get("default", 12))))},
    }


def _scaled(m, k):
    return m.repeat(k, 0).repeat(k, 1)


def _carved(c, m, k, x, y, amt, hi="bone_hi", body="bone", low="ash4"):
    """Lettering blown up k times, each source pixel lit on top and shaded at the
    bottom like a cut, with an ink outline and drop shadow; dithered in by `amt`."""
    big = _scaled(m, k)
    h, w = big.shape
    H, W = c.shape[:2]
    if x < 1 or y < 1 or x + w + 2 > W or y + h + 2 > H or amt <= 0:
        return
    show_ = big & mask(amt, h, w, x, y)
    edge = np.zeros((h + 3, w + 3), dtype=bool)  # outline all round, shadow down-right
    for dy, dx in ((0, 1), (2, 1), (1, 0), (1, 2), (2, 2), (3, 3), (2, 3), (3, 2)):
        edge[dy:dy + h, dx:dx + w] |= show_
    region = c[y - 1:y + h + 2, x - 1:x + w + 2]
    region[edge] = RGB["ink0"]
    rows = np.arange(h)[:, None] % k
    col = np.where(rows == 0, 1, np.where(rows == k - 1, 3, 2))
    col = np.broadcast_to(col, (h, w))
    tgt = c[y:y + h, x:x + w]
    for v, name in ((1, hi), (2, body), (3, low)):
        tgt[show_ & (col == v)] = RGB[name]


class Intro(Scene):
    key_times = (1.6, 4.0, 6.4, 9.0)  # the contact sheet: ridge in, faces lighting, title, episode
    def __init__(self, intro, cfg, show_data=None):
        sp = spec(intro, show_data)
        self.info = sp.pop("intro")
        super().__init__(sp, cfg)

    @property
    def step(self):
        return (LIGHTS_TO - LIGHTS_FROM) / self.info["faces"]

    def _lit_at(self, t):
        n = int((t - LIGHTS_FROM) / self.step) + 1 if t >= LIGHTS_FROM else 0
        return max(0, min(self.info["faces"], n))

    def render(self, t, frame=None):
        n = self._lit_at(t)
        rig = self.actors[0]
        rig["state"] = f"f{self.info['faces']}_{n}"
        # the rig's own glow: grows with each face, kicks as a face catches and when the title lands
        caught = t - (LIGHTS_FROM + (n - 1) * self.step)  # how long ago the newest face lit
        kick = 0.25 if n and caught < 1.5 / self.fps else 0.0
        if TITLE_AT <= t < TITLE_AT + 0.6:
            kick = max(kick, 0.4 * (1 - (t - TITLE_AT) / 0.6))
        self.lights[:] = [{"pos": [RIG_X, RIG_Y - 62], "radius": 30 + 2 * n, "color": "ember0",
                           "intensity": 0.06 * n ** 0.8 + kick, "flicker": True}] if n else []
        c = super().render(t, frame)
        # in and out of black, dithered
        a0, a1 = FADE_IN
        b0, b1 = FADE_OUT
        vis = min(1.0, max(0.0, (t - a0) / (a1 - a0)), max(0.0, (b1 - t) / (b1 - b0)))
        if vis < 1:
            c[~mask(vis, self.H, self.W)] = RGB["ink0"]
        out = min(1.0, max(0.0, (b1 - t) / (b1 - b0)))
        # the show title, two lines, carved at 3x
        words = self.info["show"].split()
        lines = [" ".join(words[:len(words) // 2 + len(words) % 2]), " ".join(words[len(words) // 2 + len(words) % 2:])] \
            if len(words) > 1 and textfont.width(self.info["show"]) * 3 > 150 else [self.info["show"]]
        lines = [ln for ln in lines if ln]
        amt = min(out, max(0.0, (t - TITLE_AT) / TITLE_FADE))
        y = 52 if len(lines) > 1 else 64
        for ln in lines:
            m = textfont.text_mask(ln)[:6]  # capitals and x-height; titles have no descenders
            _carved(c, m, 3, TEXT_CX - m.shape[1] * 3 // 2, y, amt)
            y += 6 * 3 + 7
        # a rule, then the episode: number in ash, name in bone at 2x
        amt = min(out, max(0.0, (t - EPISODE_AT) / EPISODE_FADE))
        if amt > 0:
            ry = y + 3
            rule = np.zeros((1, 64), dtype=bool); rule[:] = True
            sel = rule & mask(amt, 1, 64, TEXT_CX - 32, ry)
            c[ry:ry + 1, TEXT_CX - 32:TEXT_CX + 32][sel] = RGB["ember0"]
            num = textfont.text_mask(f"Episode {_words(self.info['episode'])}")
            _carved(c, num, 1, TEXT_CX - num.shape[1] // 2, ry + 8, amt, hi="ash4", body="ash4", low="ash4")
            if self.info["title"]:
                tm = textfont.text_mask(self.info["title"])
                k = 2 if tm.shape[1] * 2 <= 180 else 1
                _carved(c, tm, k, TEXT_CX - tm.shape[1] * k // 2, ry + 22, amt)
        return c
