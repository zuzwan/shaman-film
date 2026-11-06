#!/usr/bin/env python3
"""Turn a script in the plan's scene format into a draft timeline.yaml.

    python tools/script2timeline.py script.md episodes/ep01          # writes episodes/ep01/timeline.yaml
    python tools/script2timeline.py "EP01 script.docx" episodes/ep01

Scene format (one block per scene; header fields optional, any order):

    ### EP01 / SC03: The incorporated town
    Region: river · Time: dusk · Weather: light ash
    Where: a mill town's empty square
    Who: shaman, apprentice, three Fold hosts
    Shot: wide
    Action: they walk in from the road.

    NARRATION: The town had given itself over a month before.
    APPRENTICE: Where is everyone?
    HOST (all three at once): Here.
    SOUND: wind, a mill wheel turning with no one at it

Shot lists. A `SHOT:` line starts a shot; the cards after it play over that shot:

    SHOT: wide · eye · the square · static
    NARRATION: The town had given itself over a month before.
    SHOT: close · low · Auk · push-in · 2s
    SHAMAN: Here.
    SHOT: insert · eye · the rig's face · static · 6f

    size · angle · subject and action · camera move · hold (seconds or frames; omit for
    auto = long enough to read the shot's cards). Vocabulary in docs/shots.md and
    engine/shotlist.py. The subject's first word, if it is a cast name (Auk, Teal, rig),
    becomes the shot's focus.

The draft fills region, time, weather, cast and every card in order with
automatic timing. Where, Action and Sound go into `notes` for the hand pass on
camera and blocking (every Action line is kept, in order; one inside a shot is
also noted on that shot). Unknown names stay as speakers and are listed at the
end so sprites can be planned.
"""
import re
import sys
import zipfile
from pathlib import Path

import yaml

REGIONS = {"river": "river", "river country": "river", "uplands": "uplands", "upland": "uplands",
           "coast": "coast", "glass": "glass", "glass town": "glass", "glass towns": "glass",
           "interior": "interior", "refuge": "interior"}
TIMES = {"day": "day", "morning": "day", "noon": "day", "afternoon": "day", "dawn": "dusk",
         "dusk": "dusk", "evening": "dusk", "sunset": "dusk", "night": "night", "midnight": "night"}
WEATHER = [("locust", {"type": "swarm", "density": 0.8, "wind": 0.6}),
           ("swarm", {"type": "swarm", "density": 0.8, "wind": 0.6}),
           ("insect", {"type": "motes", "density": 0.5, "wind": 0.1}),
           ("firefl", {"type": "motes", "density": 0.5, "wind": 0.1}),
           ("snow", {"type": "snow", "density": 0.4, "wind": 0.4}),
           ("rain", {"type": "rain", "density": 0.35, "wind": 0.5}),
           ("heavy ash", {"type": "ash", "density": 0.8, "wind": 0.35}),
           ("light ash", {"type": "ash", "density": 0.25, "wind": 0.2}),
           ("ash", {"type": "ash", "density": 0.5, "wind": 0.3}),
           ("none", "none"), ("clear", "none")]
SPRITES = {"shaman": "auk", "auk": "auk", "apprentice": "teal", "teal": "teal", "rig": "rig", "chainman": "chainman",
           "clerk": "clerk", "guard": "guard", "surveyor": "chainman", "host": "fold_host",
           "fold host": "fold_host", "fold": "fold_host"}
NAMES = {"auk": "shaman", "shaman": "shaman", "teal": "apprentice", "apprentice": "apprentice", "rig": "rig"}
# SOUND: lines -> ambience beds (engine/audio.py BEDS). Events (a bar dropping, a ratchet)
# are cut by hand against the picture; the draft lists the line in notes.sound.
SOUND_BEDS = [("cricket", "crickets"), ("river", "river"), ("wind", "wind"), ("gnat", "gnats"),
              ("flies", "flies"), ("fly ", "flies"), ("wheel", "wheel"), ("moth", "moths"), ("beetle", "beetles"),
              ("rope", "rope"), ("silk", "silk"), ("smoke", "fire"), ("crackl", "fire"), ("humming", "hum"),
              ("race", "race"), ("ford", "ford"), ("quern", "querns"), ("gear", "gear"), ("rig", "rig")]
NUMBERS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "a few": 3, "several": 4}
SCENE_RE = re.compile(r"^#{2,4}\s*(.+)$")
SHOT_RE = re.compile(r"^SHOT\s*:\s*(.+)$")          # the shot list: upper case only
HEAD_SHOT_RE = re.compile(r"^Shot\s*:\s*(.+)$")     # the scene header's one-line shot idea: a note
LINE_RE = re.compile(r"^([A-Z][A-Z .'\-]+?)\s*(\(([^)]*)\))?\s*:\s*(.+)$")


def read_text(path):
    p = Path(path)
    if p.suffix.lower() == ".docx":
        xml = zipfile.ZipFile(p).read("word/document.xml").decode()
        paras = re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)
        out = []
        for para in paras:
            text = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", para))
            style = re.search(r'<w:pStyle w:val="Heading\d"', para)
            out.append(("### " + text) if style and not text.startswith("#") else text)
        return "\n".join(out)
    return p.read_text()


def scene_id(title, n):
    m = re.search(r"SC\s*0*(\d+)", title, re.I)
    num = int(m.group(1)) if m else n
    slug = re.sub(r"[^a-z0-9]+", "_", title.split(":", 1)[-1].lower()).strip("_")[:24]
    return f"sc{num:02d}_{slug}" if slug else f"sc{num:02d}"


def parse_cast(who):
    actors, unknown = [], []
    for part in re.split(r",|\band\b", who):
        part = part.strip().lower()
        if not part:
            continue
        count = 1
        for word, k in NUMBERS.items():
            if part.startswith(word + " "):
                count, part = k, part[len(word) + 1:]
        if m := re.match(r"(\d+)\s+(.*)", part):
            count, part = int(m.group(1)), m.group(2)
        key = re.sub(r"(es|s)$", "", part).replace("the ", "").strip()
        sprite = next((v for k, v in SPRITES.items() if key == k or key.endswith(k)), None)
        if sprite:
            actors += [sprite] * count
        else:
            unknown.append(part)
    return actors, unknown


def place(actors):
    """Stand the cast in a loose row centre stage, facing the middle."""
    n = len(actors)
    out, seen = [], {}
    ids = {"auk": "auk", "teal": "teal", "rig": "rig"}
    for i, spr in enumerate(actors):
        x = 160 + (i - (n - 1) / 2) * 22
        a = {"sprite": spr, "state": "hum" if spr == "rig" else "idle", "path": [[round(x), 162]], "breathe": 3}
        if spr != "rig":
            a["med"] = spr + "_med"
        base = ids.get(spr, spr)
        seen[base] = seen.get(base, 0) + 1
        a["id"] = base if seen[base] == 1 else f"{base}{seen[base]}"
        if x > 160:
            a["flip"] = True
        out.append(a)
    return out


def parse_shot(text, ids):
    """'close · low · Auk draws the knife · push-in · 2s' -> a shot dict for the timeline."""
    from engine import shotlist
    parts = [p.strip() for p in text.replace("|", "·").replace(",", "·").split("·") if p.strip()]
    v = shotlist.parse(" · ".join(parts))
    words = [v.get("size", "wide"), v.get("angle", "eye")]
    subj = v.get("subject")
    if subj:
        key = NAMES.get(subj, subj)
        key = {"shaman": "auk", "apprentice": "teal"}.get(key, key)
        if key in ids:
            words.append(key)
    words.append(v.get("move", "static"))
    shot = {"shot": " · ".join(words), "cards": []}
    if "hold" in v:
        shot["duration"] = v["hold"]
    elif "hold_frames" in v:
        shot["duration"] = round(v["hold_frames"] / 12, 3)
    subject_text = next((p for p in parts if p.split()[0].lower() not in
                         set(shotlist.SIZES) | set(shotlist.ANGLE_SHIFT) | set(shotlist.FRAMING)
                         | {"static", "pan-left", "pan-right", "push-in", "pull-out", "track", "shake"}
                         and not re.match(r"^\d+(\.\d+)?[sf]$", p)), None)
    if subject_text and len(subject_text.split()) > 1:  # 'Auk draws the knife', not just 'Auk'
        shot["note"] = subject_text
    return shot


def finish_shots(scene):
    """Give each shot a duration (its hold, or the time its cards take) and pin the
    first card of each shot to the shot's start. Cards stay scene-level."""
    from engine.subtitles import total_time
    if not scene.get("shots"):
        return
    t = 0.0
    cards = []
    for shot in scene["shots"]:
        own = shot.pop("cards")
        if "duration" not in shot:
            shot["duration"] = round(max(1.5, total_time(own, 0.3, 0.8)), 2) if own else 2.0
        if own:
            own[0]["at"] = round(t + 0.3, 2)
            cards += own
        t += shot["duration"]
    scene["cards"] = cards


def convert(text, episode):
    scenes, cur, unknown_cast, speakers = [], None, set(), set()
    for raw in text.splitlines():
        line = raw.strip().replace(" ", " ")
        if not line:
            continue
        if m := SCENE_RE.match(line):
            cur = {"id": scene_id(m.group(1), len(scenes) + 1), "title": m.group(1).strip(),
                   "duration": "auto", "backdrop": {"region": "river", "time": "day"},
                   "actors": [], "cards": [], "notes": {}}
            scenes.append(cur)
            continue
        if cur is None:
            continue
        low = line.lower()
        if re.match(r"^(region|time|weather)\s*:", low):
            for field in re.split(r"[·|;]", line):
                if ":" not in field:
                    continue
                k, v = (s.strip() for s in field.split(":", 1))
                k, v = k.lower(), v.lower()
                if k == "region":
                    cur["backdrop"]["region"] = REGIONS.get(v, cur["backdrop"]["region"])
                    if v not in REGIONS:
                        cur["notes"]["region_unmatched"] = v
                elif k == "time":
                    cur["backdrop"]["time"] = TIMES.get(v, "day")
                elif k == "weather":
                    w = next((w for key, w in WEATHER if key in v), None)
                    if w is not None:
                        cur["weather"] = w
            continue
        if m := HEAD_SHOT_RE.match(line):
            cur["notes"]["shot"] = m.group(1).strip()
            continue
        if m := SHOT_RE.match(line):
            ids = {a["id"] for a in cur["actors"]}
            cur.setdefault("shots", []).append(parse_shot(m.group(1), ids))
            continue
        if m := re.match(r"^(where|action)\s*:\s*(.+)$", line, re.I):
            key, val = m.group(1).lower(), m.group(2).strip()
            if key == "action":
                cur["notes"].setdefault("action", []).append(val)
                if cur.get("shots"):
                    cur["shots"][-1]["note"] = (cur["shots"][-1].get("note", "") + " — " + val).strip(" —")
            else:
                cur["notes"][key] = val
            continue
        if m := re.match(r"^who\s*:\s*(.+)$", line, re.I):
            actors, unknown = parse_cast(m.group(1))
            cur["actors"] = place(actors)
            unknown_cast.update(unknown)
            if unknown:
                cur["notes"]["cast_without_sprites"] = ", ".join(unknown)
            continue
        if m := LINE_RE.match(line):
            who, note, said = m.group(1).strip(), m.group(3), m.group(4).strip()
            target = cur["shots"][-1]["cards"] if cur.get("shots") else cur["cards"]
            if who == "SOUND":
                cur["notes"].setdefault("sound", []).append(said)
                beds = cur.setdefault("sound", {}).setdefault("bed", [])
                for key, bed in SOUND_BEDS:
                    if key in said.lower() and bed not in beds:
                        beds.append(bed)
            elif who == "NARRATION":
                target.append({"narration": said})
            else:
                card = {"speaker": who.lower(), "text": said}
                if note:
                    card["note"] = note
                target.append(card)
                speakers.add(who.lower())
            continue
        # anything else continues the previous card (wrapped paragraphs)
        target = cur["shots"][-1]["cards"] if cur.get("shots") else cur["cards"]
        if target:
            last = target[-1]
            k = "narration" if "narration" in last else "text"
            last[k] = f"{last[k]} {line}"
    for s in scenes:
        finish_shots(s)
        if not s["notes"]:
            del s["notes"]
    tl = {"episode": episode, "resolution": [320, 180], "scale": 6, "fps": 12, "band": 40, "scenes": scenes}
    if scenes:
        scenes[0]["transition_in"] = {"duration": 1.0}
        scenes[-1]["transition_out"] = {"duration": 1.5}
    return tl, sorted(unknown_cast), sorted(speakers)


class _Dumper(yaml.SafeDumper):
    pass


def _list(dumper, data):
    # short lists of numbers or points read better inline: [138, 162], [[138, 162]]
    flat = all(isinstance(v, (int, float)) for v in data)
    points = all(isinstance(v, list) and all(isinstance(x, (int, float)) for x in v) for v in data)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=bool(data) and (flat or points))


def _dict(dumper, data):
    # actors and small settings inline; scenes, cards and notes stay block style
    def simple(v):
        if isinstance(v, bool) or isinstance(v, (int, float)):
            return True
        if isinstance(v, str):
            return len(v) <= 30
        if isinstance(v, list):
            return all(isinstance(x, (int, float)) or
                       (isinstance(x, list) and all(isinstance(y, (int, float)) for y in x)) for x in v)
        return False
    inline = len(data) <= 5 and all(simple(v) for v in data.values()) and not ({"text", "narration"} & set(data))
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items(), flow_style=inline)


_Dumper.add_representer(list, _list)
_Dumper.add_representer(dict, _dict)


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out_dir = sys.argv[1], Path(sys.argv[2])
    tl, unknown, spk = convert(read_text(src), out_dir.name)
    out_dir.mkdir(parents=True, exist_ok=True)
    header = (f"# Draft generated from {Path(src).name} by tools/script2timeline.py.\n"
              "# Hand pass still to do: camera, actor paths, props, lights. `notes` is ignored by the renderer.\n")
    (out_dir / "timeline.yaml").write_text(header + yaml.dump(tl, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=110))
    print(f"{len(tl['scenes'])} scenes -> {out_dir / 'timeline.yaml'}")
    if unknown:
        print("cast with no sprite yet:", ", ".join(unknown))
    from engine.subtitles import speakers
    missing = [s for s in spk if s not in speakers()]
    if missing:
        print("speakers not in assets/speakers.yaml:", ", ".join(missing))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    main()
