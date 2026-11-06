"""Sound effects, synthesised in code like the pictures: no samples, no voice.

Every scene can carry a `sound` block; shots can carry `sfx` (times relative to
the shot's start). Beds loop under the whole scene, events land at a time:

    sound:
      bed: [crickets, river: 0.6]          # name or {name: gain}
      events:
        - {at: 0.4, fx: ratchet, n: 3}
        - {at: 3.0, fx: valve}
        - {at: 9.5, fx: silence, fade: 0.4}  # the beds stop dead ("not even the crickets")
    shots:
      - {duration: 2, sfx: [{at: 0.2, fx: bar_drop}]}

Footsteps are automatic: every actor in a walk, run or haul cycle steps on its
contact frames (boots, or bare feet for hosts), louder the closer the shot. Turn
off with `steps: false` on the actor or the scene.

Everything is mono at 48 kHz, mixed per scene to out/<ep>/audio/<id>.wav, then
concatenated and muxed under the picture. Music is not here: the score is cut
to the cue sheet (out/<ep>/cues.yaml) after picture lock.

Filters are done in the frequency domain (numpy FFT), so beds of any length
are cheap and nothing depends on scipy.
"""
import wave
import zlib
from pathlib import Path

import numpy as np

SR = 48000


# ------------------------------------------------------------------ building blocks
def _rng(seed):
    return np.random.default_rng(seed)


def noise(n, seed=0):
    return _rng(seed).standard_normal(n)


def shape(x, lo=None, hi=None, tilt=0.0):
    """Band-limit a signal in the frequency domain; `tilt` dB/octave above 100 Hz (pink = -3)."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    g = np.ones_like(f)
    if lo:
        g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 4)
    if hi:
        g *= 1 / np.sqrt(1 + (f / hi) ** 4)
    if tilt:
        g *= (np.maximum(f, 100) / 100) ** (tilt / 6.02)
    y = np.fft.irfft(X * g, len(x))
    return y / (np.abs(y).max() + 1e-9)


def env(n, attack=0.005, decay=0.1, sustain=0.0, curve=4.0):
    """Attack then exponential decay; durations in seconds."""
    t = np.arange(n) / SR
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    d = np.exp(-np.maximum(t - attack, 0) / max(decay, 1e-4) * (curve / 4))
    return a * (sustain + (1 - sustain) * d)


def tone(freq, dur, phase=0.0, vib=0.0, vib_rate=5.0):
    t = np.arange(int(dur * SR)) / SR
    f = freq * (1 + vib * np.sin(2 * np.pi * vib_rate * t)) if np.isscalar(freq) else freq
    return np.sin(2 * np.pi * np.cumsum(np.broadcast_to(f, t.shape)) / SR + phase)


def lfo(n, rate, depth=1.0, seed=0, smooth=True):
    """Slow random wobble 1 +/- depth, for beds that must not loop audibly."""
    k = max(4, int(n / SR * rate) + 4)
    pts = _rng(seed).uniform(-1, 1, k)
    x = np.interp(np.linspace(0, k - 3, n), np.arange(k), pts)
    return 1 + depth * x


def _n(dur):
    return max(1, int(dur * SR))


# ------------------------------------------------------------------ beds (looping ambience)
def bed_wind(n, seed=1):
    return shape(noise(n, seed), 80, 900, -2) * lfo(n, 0.3, 0.6, seed) * 0.5


def bed_river(n, seed=2):
    x = shape(noise(n, seed), 120, 2500, -3) * lfo(n, 0.5, 0.25, seed)
    return x * 0.45


def bed_race(n, seed=3):  # the millrace roaring under the mill
    return shape(noise(n, seed), 60, 4000, -1.5) * lfo(n, 2, 0.15, seed) * 0.8


def bed_ford(n, seed=4):
    x = shape(noise(n, seed), 400, 5000, -2) * lfo(n, 6, 0.6, seed)
    return x * 0.35


def bed_crickets(n, seed=5, count=5, base=4200):
    out = np.zeros(n)
    t = np.arange(n) / SR
    r = _rng(seed)
    for i in range(count):
        f = base * r.uniform(0.85, 1.15)
        rate = r.uniform(2.5, 4.5)  # chirps per second
        pulses = (np.sin(2 * np.pi * 30 * t + i) > 0.2).astype(float)  # three-pulse syllables
        chirp = (np.sin(2 * np.pi * rate * t + r.uniform(0, 6)) > 0.55).astype(float)
        out += np.sin(2 * np.pi * f * t) * pulses * chirp * r.uniform(0.3, 1.0) * lfo(n, 0.2, 0.5, seed + i)
    return shape(out, 2500, 9000) * 0.25


def bed_barn(n, seed=6):  # thousands of crickets in crates: a wall of chirp
    return (bed_crickets(n, seed, 14, 4600) * 1.6 + shape(noise(n, seed), 3500, 7000) * 0.12)


def bed_gnats(n, seed=7):
    t = np.arange(n) / SR
    whine = np.zeros(n)
    r = _rng(seed)
    for i in range(6):
        f = r.uniform(500, 900) * lfo(n, 1.5, 0.04, seed + i)
        whine += np.sin(2 * np.pi * np.cumsum(f) / SR) * lfo(n, 0.7, 0.8, seed + 10 + i).clip(0)
    return shape(whine, 300, 3000) * 0.08


def bed_flies(n, seed=8):
    t = np.arange(n) / SR
    f = 190 * lfo(n, 3, 0.15, seed)
    buzz = np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR))
    gate = (lfo(n, 0.8, 1.0, seed + 1) > 1.1).astype(float)
    gate = np.convolve(gate, np.ones(2400) / 2400, "same")
    return shape(buzz, 150, 2000) * gate * 0.12


def bed_wheel(n, seed=9, near=False):  # the mill wheel: slosh of each paddle, a slow creak
    t = np.arange(n) / SR
    out = shape(noise(n, seed), 150, 2500, -2) * (0.35 + 0.65 * (np.sin(2 * np.pi * 0.9 * t) > 0.4)) * 0.4
    period = 2.6
    for k in range(int(n / SR / period) + 1):
        s = int(k * period * SR)
        cr = _creak(1.1, seed + k, 70 if near else 90)
        out[s:s + len(cr)] += cr[: n - s] * (0.5 if near else 0.25)
    return out * (1.0 if near else 0.5)


def bed_room(n, seed=10):  # room tone: the faintest air
    return shape(noise(n, seed), 60, 600, -3) * 0.05


def bed_marsh(n, seed=11):
    return bed_crickets(n, seed, 8, 3600) * 1.2 + bed_wind(n, seed) * 0.4


def bed_querns(n, seed=12):  # twelve querns as one quern: a grinding rhythm, one beat
    t = np.arange(n) / SR
    grit = shape(noise(n, seed), 100, 1800, -2)
    beat = 0.25 + 0.75 * np.clip(np.sin(2 * np.pi * 0.62 * t), 0, 1) ** 2
    return grit * beat * 0.6


def bed_gear(n, seed=13):  # the great shaft and gear turning, nothing coupled: a tooth knock in time
    out = shape(noise(n, seed), 40, 400, -3) * 0.15
    for k in range(int(n / SR / 0.45) + 1):
        s = int(k * 0.45 * SR)
        hit = knock(0.12, 140, seed + k) * 0.5
        out[s:s + len(hit)] += hit[: n - s]
    return out


def bed_moths(n, seed=14):  # moths ticking on lantern glass
    out = np.zeros(n)
    r = _rng(seed)
    t = 0.0
    while t < n / SR:
        t += r.exponential(0.35)
        s = int(t * SR)
        tk = tick(0.01, 5000) * r.uniform(0.2, 0.6)
        out[s:s + len(tk)] += tk[: max(0, n - s)]
    return out


def bed_beetles(n, seed=15):
    out = np.zeros(n)
    r = _rng(seed)
    t = 0.0
    while t < n / SR:
        t += r.exponential(0.06)
        s = int(t * SR)
        tk = tick(0.004, r.uniform(2500, 6000)) * r.uniform(0.05, 0.25)
        out[s:s + len(tk)] += tk[: max(0, n - s)]
    return out


def bed_rope(n, seed=16):  # the haul rope creaking, the haulers grunting in time
    out = np.zeros(n)
    period = 1.8
    for k in range(int(n / SR / period) + 1):
        s = int(k * period * SR)
        cr = _creak(0.9, seed + k, 55)
        out[s:s + len(cr)] += cr[: n - s] * 0.6
        g = grunt(0.35, seed + k)
        s2 = s + int(0.15 * SR)
        out[s2:s2 + len(g)] += g[: max(0, n - s2)] * 0.5
    return out + bed_river(n, seed) * 0.5


def bed_silk(n, seed=17):  # wet silk snapping in the wind
    out = bed_wind(n, seed) * 0.6
    r = _rng(seed)
    t = 0.0
    while t < n / SR:
        t += r.uniform(0.6, 2.2)
        s = int(t * SR)
        sn = snap(0.12, seed + int(t * 10))
        out[s:s + len(sn)] += sn[: max(0, n - s)] * r.uniform(0.3, 0.7)
    return out


def bed_fire(n, seed=18):  # a smoke line smouldering: crackle
    out = shape(noise(n, seed), 200, 1500) * 0.08
    r = _rng(seed)
    t = 0.0
    while t < n / SR:
        t += r.exponential(0.12)
        s = int(t * SR)
        tk = tick(0.006, r.uniform(1500, 4000)) * r.uniform(0.1, 0.4)
        out[s:s + len(tk)] += tk[: max(0, n - s)]
    return out


def bed_hum(n, seed=19):  # Bett humming, a few notes over and over, no words
    notes = [220, 247, 262, 247, 220, 196, 220, 0]
    out = np.zeros(n)
    per = 0.55
    for k in range(int(n / SR / per) + 1):
        f = notes[k % len(notes)]
        if not f:
            continue
        s = int(k * per * SR)
        L = int(per * SR * 1.05)
        x = tone(f, L / SR, vib=0.006) + 0.35 * tone(f * 2, L / SR) + 0.15 * tone(f * 3, L / SR)
        x *= env(L, 0.06, 0.6, 0.6)
        x = shape(x, 150, 1400)
        out[s:s + L] += x[: max(0, n - s)] * 0.25
    return out


def bed_rig(n, seed=20):  # the lit rig: a low valve hum with a slow beat
    t = np.arange(n) / SR
    x = tone(55, n / SR) * 0.5 + tone(110.7, n / SR) * 0.3 + tone(165, n / SR) * 0.1
    x *= 0.8 + 0.2 * np.sin(2 * np.pi * 0.33 * t)
    return x * 0.18 + shape(noise(n, seed), 2000, 6000) * 0.01


BEDS = {"wind": bed_wind, "river": bed_river, "race": bed_race, "ford": bed_ford, "crickets": bed_crickets,
        "barn": bed_barn, "gnats": bed_gnats, "flies": bed_flies, "wheel": bed_wheel,
        "wheel_near": lambda n, seed=9: bed_wheel(n, seed, near=True), "room": bed_room, "marsh": bed_marsh,
        "querns": bed_querns, "gear": bed_gear, "moths": bed_moths, "beetles": bed_beetles, "rope": bed_rope,
        "silk": bed_silk, "fire": bed_fire, "hum": bed_hum, "rig": bed_rig}


# ------------------------------------------------------------------ events
def tick(dur, freq):
    n = _n(dur)
    return np.sin(2 * np.pi * freq * np.arange(n) / SR) * env(n, 0.0005, dur / 3)


def knock(dur=0.12, freq=180, seed=0):
    """Wood on wood: a damped tone and a click."""
    n = _n(dur)
    x = tone(freq, dur) * env(n, 0.001, dur / 4) + shape(noise(n, seed), 800, 5000) * env(n, 0.0005, 0.006) * 0.6
    return x


def _creak(dur, seed=0, base=80):
    """Wood under strain: a stick-slip pulse train with a wandering rate."""
    n = _n(dur)
    rate = base * lfo(n, 4, 0.35, seed)
    ph = np.cumsum(rate) / SR
    pulses = (np.diff(np.floor(ph), prepend=0) > 0).astype(float)
    body = shape(pulses + noise(n, seed) * 0.02, 200, 2400)
    return body * np.sin(np.linspace(0, np.pi, n)) ** 0.7


def creak(dur=0.8, seed=0, base=80):
    return _creak(dur, seed, base)


def ratchet(n=3, seed=0, gap=0.5):
    """A crank's ratchet: a run of clicks per turn, n turns."""
    out = np.zeros(_n(n * gap + 0.3))
    for k in range(n):
        for j in range(7):
            s = int((k * gap + j * 0.045) * SR)
            c = knock(0.03, 1800 + 200 * (j % 2), seed + j) * (0.6 + 0.4 * (j == 6))
            out[s:s + len(c)] += c
    return out


def valve(dur=2.0, seed=0):
    """A valve warming: a low hum fading up with a rising whistle of filament."""
    n = _n(dur)
    t = np.arange(n) / SR
    up = np.clip(t / dur, 0, 1) ** 1.5
    x = tone(55, dur) * 0.5 + tone(110 + 4 * up, dur) * 0.3
    x += tone(800 + 600 * up, dur) * 0.03
    return x * up * 0.6


def bar_drop(seed=0):
    """A bar dropped back into its iron brackets: a thud and a clank."""
    a = knock(0.25, 90, seed) * 0.9
    b = np.zeros_like(a)
    cl = shape(noise(_n(0.2), seed), 1500, 7000) * env(_n(0.2), 0.0005, 0.04)
    cl += (tone(1300, 0.2) + tone(2170, 0.2) * 0.6) * env(_n(0.2), 0.0005, 0.06) * 0.5
    b[int(0.03 * SR):int(0.03 * SR) + len(cl)] += cl[: len(b) - int(0.03 * SR)]
    return a + b * 0.6


def thud(seed=0, freq=60, dur=0.4):
    n = _n(dur)
    return tone(freq * np.linspace(1.4, 1, n), dur) * env(n, 0.002, dur / 4) + shape(noise(n, seed), 50, 400) * env(n, 0.001, 0.05) * 0.5


def step(seed=0, bare=False, surface="earth"):
    """One footstep. Boots on earth, grit, cobbles or planks; bare feet are a soft pat."""
    n = _n(0.12)
    if bare:
        return shape(noise(n, seed), 80, 900) * env(n, 0.003, 0.025) * 0.35
    hi = {"earth": 1200, "grit": 4000, "cobbles": 3000, "planks": 1500}.get(surface, 1500)
    x = shape(noise(n, seed), 60, hi) * env(n, 0.002, 0.03)
    if surface == "planks":
        x += knock(0.12, 160, seed) * 0.5
    if surface == "grit":
        x += shape(noise(n, seed + 1), 2000, 8000) * env(n, 0.01, 0.06) * 0.4
    return x * 0.6


def splash(seed=0, dur=0.5, size=1.0):
    n = _n(dur)
    return shape(noise(n, seed), 300 / size, 6000) * env(n, 0.005, dur / 4) * 0.8


def pour(dur=2.0, seed=0):
    n = _n(dur)
    gurgle = 1 + 0.6 * np.sin(2 * np.pi * np.cumsum(9 * lfo(n, 3, 0.3, seed)) / SR)
    return shape(noise(n, seed), 400, 3500) * gurgle * env(n, 0.05, dur, 0.7) * 0.4


def drip(seed=0):
    n = _n(0.15)
    f = np.linspace(900, 1700, n)
    return tone(f, 0.15) * env(n, 0.001, 0.02) * 0.5


def sweep(seed=0, dur=0.45):
    """A broom stroke across cobbles."""
    n = _n(dur)
    return shape(noise(n, seed), 1200, 9000) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.5


def snap(dur=0.12, seed=0):  # wet cloth snapping
    n = _n(dur)
    return shape(noise(n, seed), 200, 3000) * env(n, 0.002, 0.03)


def grunt(dur=0.35, seed=0):
    """A man's effort sound, wordless: voiced buzz through a formant, no speech."""
    n = _n(dur)
    f0 = 95 * (1 + 0.1 * np.sin(np.linspace(0, np.pi, n)))
    buzz = np.sign(np.sin(2 * np.pi * np.cumsum(f0) / SR)) + noise(n, seed) * 0.3
    return shape(buzz, 120, 900) * np.sin(np.linspace(0, np.pi, n)) ** 1.5 * 0.5


def retch(seed=0):
    out = np.zeros(_n(1.4))
    for k, (s, d) in enumerate(((0.0, 0.3), (0.45, 0.5), (1.0, 0.3))):
        g = grunt(d, seed + k) * 1.2 + shape(noise(_n(d), seed), 300, 2500) * np.sin(np.linspace(0, np.pi, _n(d))) * 0.4
        out[int(s * SR):int(s * SR) + len(g)] += g
    return out


def breath(dur=3.0, seed=0, rate=0.3):
    """Breathing: filtered noise in slow swells (Teal asleep; Pim too fast at night)."""
    n = _n(dur)
    t = np.arange(n) / SR
    sw = np.clip(np.sin(2 * np.pi * rate * t), 0, 1) ** 2
    return shape(noise(n, seed), 300, 2000) * sw * 0.18


def gear_tick(seed=0):
    return knock(0.08, 220, seed) * 0.7


def peg(seed=0):  # a tally peg pushed into a board
    return knock(0.06, 900, seed) * 0.6


def knot(seed=0):  # silk pulled tight
    n = _n(0.15)
    return shape(noise(n, seed), 2000, 7000) * np.sin(np.linspace(0, np.pi, n)) * 0.25


def feet_many(seed=0, count=30, spread=0.12):
    """Many bare feet on cobbles together: one step, a crowd thick."""
    out = np.zeros(_n(0.4))
    r = _rng(seed)
    for k in range(count):
        s = int(abs(r.normal(0, spread / 3)) * SR)
        x = step(seed + k, bare=True) * r.uniform(0.4, 1.0)
        out[s:s + len(x)] += x[: len(out) - s]
    return out * 0.5


def settle(seed=0):
    """Something heavy settling in the alders: a low weight shift and a branch giving."""
    out = thud(seed, 45, 0.8) * 0.7
    cr = _creak(0.6, seed, 40) * 0.5
    out[int(0.15 * SR):int(0.15 * SR) + len(cr)] += cr
    return out


def splash_surface(seed=0):  # a long back breaking the river surface, far off
    n = _n(2.0)
    return shape(noise(n, seed), 100, 1200) * np.sin(np.linspace(0, np.pi, n)) ** 2 * 0.35


def sting(seed=0, dur=4.0):
    """The title hit: a low drum, a struck plate, a long ember tail."""
    n = _n(dur)
    x = thud(seed, 42, 1.4)
    x = np.pad(x, (0, n - len(x)))
    plate = sum(tone(f, dur) * a for f, a in ((233, 0.5), (349, 0.3), (467, 0.25), (622, 0.15)))
    x += plate * env(n, 0.002, 1.2) * 0.35
    x += shape(noise(n, seed), 1500, 6000) * env(n, 0.001, 0.3) * 0.15
    return x


def swell(dur=3.0, seed=0):
    """A rising swarm of gnats for the title build."""
    n = _n(dur)
    up = np.linspace(0, 1, n) ** 2
    return bed_gnats(n, seed) * 6 * up + shape(noise(n, seed), 200, 2000) * up * 0.1


def hoes(seed=0, n=6, period=0.9):  # hoes knocking shoulders in one rhythm
    out = np.zeros(_n(n * period + 0.3))
    for k in range(n):
        s = int(k * period * SR)
        x = knock(0.1, 260, seed + k) * 0.5
        out[s:s + len(x)] += x
    return out


def fx_event(name, e, seed):
    """One event by name -> mono samples."""
    if name == "ratchet":
        return ratchet(e.get("n", 3), seed, e.get("gap", 0.5))
    if name == "valve":
        return valve(e.get("dur", 2.0), seed)
    if name == "creak":
        return creak(e.get("dur", 0.8), seed, e.get("base", 80))
    if name == "bar_drop":
        return bar_drop(seed)
    if name == "thud":
        return thud(seed, e.get("freq", 60), e.get("dur", 0.4))
    if name == "step":
        return step(seed, e.get("bare", False), e.get("surface", "earth"))
    if name == "splash":
        return splash(seed, e.get("dur", 0.5), e.get("size", 1.0))
    if name == "surface":
        return splash_surface(seed)
    if name == "pour":
        return pour(e.get("dur", 2.0), seed)
    if name == "drip":
        return drip(seed)
    if name == "sweep":
        return sweep(seed, e.get("dur", 0.45))
    if name == "snap":
        return snap(0.12, seed)
    if name == "grunt":
        return grunt(e.get("dur", 0.35), seed)
    if name == "retch":
        return retch(seed)
    if name == "breath":
        return breath(e.get("dur", 3.0), seed, e.get("rate", 0.3))
    if name == "gear_tick":
        return gear_tick(seed)
    if name == "peg":
        return peg(seed)
    if name == "knot":
        return knot(seed)
    if name == "feet_many":
        return feet_many(seed, e.get("count", 30))
    if name == "settle":
        return settle(seed)
    if name == "sting":
        return sting(seed, e.get("dur", 4.0))
    if name == "swell":
        return swell(e.get("dur", 3.0), seed)
    if name == "hoes":
        return hoes(seed, e.get("n", 6), e.get("period", 0.9))
    if name == "knock":
        return knock(e.get("dur", 0.12), e.get("freq", 180), seed)
    if name == "tick":
        return tick(e.get("dur", 0.01), e.get("freq", 3000))
    if name in BEDS:  # a bed played as a one-off for `dur` seconds
        n = _n(e.get("dur", 2.0))
        x = BEDS[name](n, seed)
        fade = min(n // 4, _n(0.3))
        x[:fade] *= np.linspace(0, 1, fade)
        x[-fade:] *= np.linspace(1, 0, fade)
        return x
    raise ValueError(f"unknown sound effect: {name}")


# ------------------------------------------------------------------ mixing a scene
WALK_STATES = {"walk": 8, "run": 6, "haul": 8, "carry": 8, "stalk": 8}
BARE = ("fold_host", "host_", "gaunt")


def _items(lst):
    """[a, {b: 0.5}] -> [(a, 1.0), (b, 0.5)]"""
    out = []
    for it in lst or []:
        if isinstance(it, dict):
            out += list(it.items())
        else:
            out.append((it, 1.0))
    return out


def _steps(spec, t0, dur, fps, zoom, seed, surface):
    """Footstep events for walking actors in one shot (scene-time seconds)."""
    from . import sprites
    ev = []
    if spec.get("steps") is False:
        return ev
    for i, a in enumerate(spec.get("actors", [])):
        st = a.get("state", "idle")
        if st not in WALK_STATES or a.get("hidden") or a.get("steps") is False or "freeze" in a:
            continue
        try:
            spr = sprites.load(a["sprite"])
        except FileNotFoundError:
            continue
        cyc_fps = a.get("fps", spr.fps)
        nfr = len(spr.states.get(st, [0])) or WALK_STATES[st]
        a0, a1 = a.get("t", [0, dur])
        a1 = min(a1, dur)
        phase = a.get("phase", 0.0)
        contact = nfr // 2  # two footfalls per cycle
        tt = a0
        k = 0
        while tt < a1:
            ft = int((tt - a0 + phase) * cyc_fps)
            if ft % contact == 0:
                bare = any(a["sprite"].startswith(b) for b in BARE)
                g = a.get("step_gain", 1.0) * (0.35 + 0.25 * min(zoom, 3)) * (0.7 if bare else 1.0)
                ev.append({"at": t0 + tt, "fx": "step", "bare": bare, "surface": a.get("surface", surface), "gain": g,
                           "seed": seed + i * 101 + k})
                tt = a0 + (ft + 1) / cyc_fps - phase + 1e-6
                k += 1
            else:
                tt = a0 + (ft + 1) / cyc_fps - phase + 1e-6
    return ev


def scene_events(spec, scene, fps):
    """Every event in a scene, on the scene clock, including shot sfx and footsteps."""
    snd = spec.get("sound", {}) or {}
    surface = snd.get("surface", "earth")
    events = [dict(e) for e in snd.get("events", [])]
    seed = zlib.crc32(spec.get("id", "").encode()) % 10000
    if scene.shots:
        for start, sub in scene.shots:
            sspec = sub.spec
            for e in sspec.get("sfx", []) or []:
                events.append(dict(e, at=start + e.get("at", 0.0)))
            z = sub.zoom[0] if hasattr(sub, "zoom") else 1
            if snd.get("steps", True):
                events += _steps(sspec, start, sub.duration, fps, z, seed + int(start * 10), surface)
    else:
        for e in spec.get("sfx", []) or []:
            events.append(dict(e))
        if snd.get("steps", True):
            events += _steps(spec, 0.0, scene.duration, fps, scene.zoom[0], seed, surface)
    return events


def mix_scene(spec, scene, fps):
    """Render one scene's sound to a mono float array of exactly its length."""
    n = int(round(scene.n_frames / fps * SR))
    out = np.zeros(n)
    snd = spec.get("sound", {}) or {}
    seed = zlib.crc32(spec.get("id", "").encode()) % 10000
    beds = np.zeros(n)
    for name, gain in _items(snd.get("bed")):
        beds += BEDS[name](n, seed + len(name)) * gain
    # a bed can be cut: {at, fx: silence, fade}
    for e in snd.get("events", []):
        if e.get("fx") == "silence":
            s = int(e["at"] * SR)
            f = max(1, int(e.get("fade", 0.3) * SR))
            ramp = np.linspace(1, 0, min(f, max(0, n - s)))
            beds[s:s + len(ramp)] *= ramp
            beds[s + len(ramp):] = 0
    out += beds * snd.get("bed_gain", 0.6)
    for i, e in enumerate(scene_events(spec, scene, fps)):
        if e.get("fx") == "silence":
            continue
        x = fx_event(e["fx"], e, e.get("seed", seed + i * 7))
        s = int(e["at"] * SR)
        if s >= n:
            continue
        x = x[: n - s] * e.get("gain", 1.0)
        out[s:s + len(x)] += x
    # soften the head and tail so cuts do not click; transitions also fade the sound
    for key, edge in (("transition_in", 0), ("transition_out", 1)):
        tr = spec.get(key)
        f = int((tr.get("duration", 1.0) if tr else 0.02) * SR)
        f = min(f, n // 2)
        if f:
            ramp = np.linspace(0, 1, f)
            if edge == 0:
                out[:f] *= ramp
            else:
                out[-f:] *= ramp[::-1]
    return out


def intro_sound(n, sting_window):
    """The title card: gnats swarm in, the sting lands as the letters set, a tail under the episode card."""
    out = np.zeros(n)
    s0, hit = sting_window["start"], sting_window["hit"]
    sw = swell(hit - s0 + 0.1, 3)
    a = int(s0 * SR)
    out[a:a + len(sw)] += sw[: n - a] * 0.8
    st = sting(4, 6.0)
    b = int(hit * SR)
    out[b:b + len(st)] += st[: n - b]
    out += bed_wind(n, 5) * 0.15
    f = int(0.5 * SR)
    out[-f:] *= np.linspace(1, 0, f)
    return out


def write_wav(path, x, peak=0.89):
    """Mono float -> 16-bit WAV. Scenes are not normalised one by one (that would
    change the level at every cut); a fixed gain and a soft clip keep them even."""
    y = np.tanh(x * 0.9) * peak
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
