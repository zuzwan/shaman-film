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

The draft fills region, time, weather, cast and every card in order with
automatic timing. Where, Shot, Action and Sound go into `notes` for the
hand pass on camera and blocking. Unknown names stay as speakers and are
listed at the end so sprites can be planned.
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
SPRITES = {"shaman": "shaman", "apprentice": "apprentice", "rig": "rig", "chainman": "chainman",
           "clerk": "clerk", "guard": "guard", "surveyor": "chainman", "host": "fold_host",
           "fold host": "fold_host", "fold": "fold_host"}
NUMBERS = {"two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "a few": 3, "several": 4}
SCENE_RE = re.compile(r"^#{2,4}\s*(.+)$")
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
    out = []
    for i, spr in enumerate(actors):
        x = 160 + (i - (n - 1) / 2) * 22
        a = {"sprite": spr, "state": "hum" if spr == "rig" else "idle", "path": [[round(x), 162]]}
        if x > 160:
            a["flip"] = True
        out.append(a)
    return out


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
        if m := re.match(r"^(where|shot|action)\s*:\s*(.+)$", line, re.I):
            cur["notes"][m.group(1).lower()] = m.group(2).strip()
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
            if who == "SOUND":
                cur["notes"].setdefault("sound", []).append(said)
            elif who == "NARRATION":
                cur["cards"].append({"narration": said})
            else:
                card = {"speaker": who.lower(), "text": said}
                if note:
                    card["note"] = note
                cur["cards"].append(card)
                speakers.add(who.lower())
            continue
        # anything else continues the previous card (wrapped paragraphs)
        if cur["cards"]:
            last = cur["cards"][-1]
            k = "narration" if "narration" in last else "text"
            last[k] = f"{last[k]} {line}"
    for s in scenes:
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
