"""Subtitle cards: narration and dialogue, video-game style.

A scene lists cards in order; the engine times them unless told otherwise:

    cards:
      - {narration: "The town had given itself over a month before."}
      - {speaker: apprentice, text: "Where is everyone?"}
      - {speaker: the fold, note: "all three at once", text: "Here.", hold: 2.5}

Per card, optional: `at` (start time, s), `hold` (seconds fully shown),
`cps` (typing speed). Defaults: text types on at 40 characters/s, then holds
for its reading time, characters / 15 + 1 s, with a short gap between cards.

Narration: centred low on screen, no box, outlined in ink.
Dialogue: a dithered dark box along the bottom with the speaker's name tag in
their color (assets/speakers.yaml) and the line in bone.
"""
from pathlib import Path

import numpy as np
import yaml

from . import textfont as tf
from .dither import mask
from .palette import RGB

TYPE_CPS = 40.0     # typing speed, characters per second
READ_CPS = 15.0     # reading speed for the hold
READ_PAD = 1.0      # extra hold, seconds
GAP = 0.3           # between cards
FADE = 0.25         # dither-out at the end of a card
MARGIN = 14         # box inset from the frame edge
_SPEAKERS = None


def speakers():
    global _SPEAKERS
    if _SPEAKERS is None:
        p = Path("assets/speakers.yaml")
        _SPEAKERS = yaml.safe_load(p.read_text()) if p.exists() else {}
    return _SPEAKERS


def normalise(card):
    """Accept the short forms {narration: text} and {name: text}."""
    if "narration" in card:
        return {**card, "kind": "narration", "text": card["narration"]}
    return {**card, "kind": "line"}


def paginate(cards, W, band):
    """Split cards whose wrapped text would overflow the available lines into pages."""
    max_lines = max(1, (band - 14) // tf.LINE) if band else 3
    out = []
    for c in cards:
        c = normalise(c)
        lines = tf.wrap(c["text"], W - 2 * MARGIN - 12)
        if len(lines) <= max_lines or "at" in c:
            out.append(c)
            continue
        for i in range(0, len(lines), max_lines):
            out.append({**c, "text": " ".join(lines[i:i + max_lines])})
    return out


def schedule(cards, start=0.6, W=320, band=0):
    """Give every card absolute times: t0 (appears), t_typed (fully typed), t1 (gone)."""
    out, t = [], start
    for c in paginate(cards, W, band):
        t0 = c.get("at", t)
        n = len(c["text"])
        typed = t0 + n / c.get("cps", TYPE_CPS)
        hold = c.get("hold", n / READ_CPS + READ_PAD)
        t1 = typed + hold
        out.append({**c, "t0": t0, "t_typed": typed, "t1": t1})
        t = t1 + GAP
    return out


def total_time(cards, start=0.6, tail=1.0, W=320, band=0):
    s = schedule(cards, start, W, band)
    return (s[-1]["t1"] + tail) if s else 0.0


def _outline(m):
    """1px ink outline around a text mask (8 neighbours)."""
    o = np.zeros((m.shape[0] + 2, m.shape[1] + 2), dtype=bool)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            o[dy:dy + m.shape[0], dx:dx + m.shape[1]] |= m
    return o


def _blit(c, m, x, y, col, vis=1.0):
    H, W = c.shape[:2]
    h, w = m.shape
    if x >= W or y >= H or x + w <= 0 or y + h <= 0:
        return
    xa, ya = max(0, x), max(0, y)
    xb, yb = min(W, x + w), min(H, y + h)
    sub = m[ya - y:yb - y, xa - x:xb - x]
    if vis < 1:
        sub = sub & mask(vis, yb - ya, xb - xa, xa, ya)
    c[ya:yb, xa:xb][sub] = RGB[col]


def _visible_text(text, n):
    """First n characters, but never break the wrap: wrapping is done on the full text."""
    return text[:max(0, int(n))]


def draw(c, sched, t, band=0):
    H, W = c.shape[:2]
    for card in sched:
        if not (card["t0"] <= t <= card["t1"]):
            continue
        n = (t - card["t0"]) * card.get("cps", TYPE_CPS)
        vis = min(1.0, (card["t1"] - t) / FADE)
        if card["kind"] == "narration":
            _draw_narration(c, card, n, vis, W, H, band)
        else:
            _draw_line(c, card, n, vis, W, H, band)


def _lines_progress(lines, n):
    """Split the typed character count across already-wrapped lines."""
    out = []
    for ln in lines:
        take = max(0, min(len(ln), int(n)))
        out.append(ln[:take])
        n -= len(ln) + 1
    return out


def _draw_narration(c, card, n, vis, W, H, band=0):
    lines = tf.wrap(card["text"], W - 2 * MARGIN - 12)
    shown = _lines_progress(lines, n)
    if band:  # centred vertically in the band
        y0 = H - band + (band - (len(lines) * tf.LINE - 3)) // 2 - 1
    else:
        y0 = H - MARGIN - (len(lines) - 1) * tf.LINE - 6
    for full, part in zip(lines, shown):
        if part:
            x = (W - tf.width(full)) // 2   # centre on the full line so typing doesn't slide
            m = tf.text_mask(part)
            _blit(c, _outline(m), x - 1, y0 - 1, "ink0", vis)
            _blit(c, m, x, y0, card.get("color", "bone"), vis)
        y0 += tf.LINE


def _draw_line(c, card, n, vis, W, H, band=0):
    spk = speakers().get(card.get("speaker", "").lower(), {})
    name = spk.get("name", card.get("speaker", "").title()) if spk else card.get("speaker", "").title()
    if card.get("note"):
        name = f"{name} ({card['note']})"
    pad = 6
    bw = W - 2 * MARGIN
    lines = tf.wrap(card["text"], bw - 2 * pad)
    if band:  # the box fills the band; its name tag rides up onto the picture's edge
        by, bh = H - band + 5, band - 9
        bx = MARGIN
    else:
        bh = len(lines) * tf.LINE + 2 * pad + 2
        bx, by = MARGIN, H - MARGIN - bh
    # box: dithered dark fill, 1px border, a little name tag sitting on its top edge
    fill = mask(0.85 * vis, bh, bw, bx, by)
    c[by:by + bh, bx:bx + bw][fill] = RGB["ink0"]
    border = np.zeros((bh, bw), dtype=bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    _blit(c, border, bx, by, "ash1", vis)
    if name:
        nm = tf.text_mask(name)
        tw = nm.shape[1] + 6
        tag = np.ones((tf.H + 3, tw), dtype=bool)
        _blit(c, tag, bx + 6, by - tf.H + 1, "ink0", vis)
        tagb = np.zeros_like(tag)
        tagb[0, :] = tagb[:, 0] = tagb[:, -1] = True
        _blit(c, tagb, bx + 6, by - tf.H + 1, "ash1", vis)
        _blit(c, nm, bx + 9, by - tf.H + 3, spk.get("color", "ash4") if spk else "ash4", vis)
    y = by + pad + 2 if not band else by + (bh - (len(lines) * tf.LINE - 3)) // 2 + 1
    for part in _lines_progress(lines, n):
        if part:
            _blit(c, tf.text_mask(part), bx + pad, y, "bone", vis)
        y += tf.LINE
