#!/usr/bin/env python3
"""Render an episode (or one scene) from its timeline.

    python render.py episodes/ep00_test                 # every scene + episode cut
    python render.py episodes/ep00_test --scene s01     # one scene
    python render.py episodes/ep00_test --keys          # key frames + contact sheet only, no video

Outputs go to out/<episode>/:
    scenes/<id>.mp4        one clip per scene, upscaled with nearest-neighbour
    keys/<id>_<n>.png      key frames for review
    contact.png            every scene's key frames on one sheet
    scenes/<id>.mkv        the same, lossless at base resolution (the master the cut is built from)
    audio/<id>.wav         the scene's sound effects (engine/audio.py)
    <episode>.mp4          the scenes concatenated, upscaled x6 (1080p), with sound
    <episode>_youtube.mp4  with --youtube: upscaled x8 (1440p), 24 fps, H.264 high + AAC stereo,
                           faststart; YouTube gives 1440p uploads its better codec
    cues.yaml              the cue sheet for the score: every scene's start and end on the
                           episode clock, the intro sting, and each scene's `music` note

A timeline with `intro: {episode: 1, title: "Here"}` opens on the show's
intro card (engine/intro.py, title from assets/show.yaml).
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from engine import audio
from engine.intro import STING, Intro
from engine.scene import Scene

KEYS_PER_SCENE = 4


def master_writer(path, W, H, fps):
    """Lossless RGB at base resolution: every cut and every export is upscaled from this."""
    return subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-c:v", "libx264rgb", "-crf", "0", "-preset", "veryfast", str(path)], stdin=subprocess.PIPE)


def export(master, wav, path, W, H, scale, fps_out=None, youtube=False):
    """Upscale a lossless master with nearest-neighbour and mux its sound."""
    vf = f"scale={W * scale}:{H * scale}:flags=neighbor,format=yuv420p"
    if fps_out:
        vf += f",fps={fps_out}"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(master), "-i", str(wav), "-vf", vf,
           "-c:v", "libx264", "-tune", "animation", "-pix_fmt", "yuv420p"]
    if youtube:  # YouTube's recommended upload: high profile, closed GOP of half the frame rate, faststart
        cmd += ["-preset", "slow", "-crf", "16", "-profile:v", "high", "-bf", "2", "-g", str((fps_out or 12) // 2),
                "-c:a", "aac", "-b:a", "384k", "-ac", "2", "-ar", "48000", "-movflags", "+faststart"]
    else:
        cmd += ["-preset", "medium", "-crf", "14", "-c:a", "aac", "-b:a", "192k", "-ac", "2", "-movflags", "+faststart"]
    subprocess.run(cmd + ["-shortest", str(path)], check=True)


def render_scene(spec, cfg, out, keys_only=False, scene=None):
    scene = scene or Scene(spec, cfg)
    W, H = cfg["resolution"]
    key_idx = set(np.linspace(0, scene.n_frames - 1, KEYS_PER_SCENE).astype(int))
    if scene.shots:  # one key per shot, from its middle: the contact sheet reads as the shot list
        key_idx = {min(scene.n_frames - 1, int((st + sub.duration * 0.6) * cfg["fps"])) for st, sub in scene.shots}
    if getattr(scene, "key_times", None):  # a scene can name its own review moments
        key_idx = {min(scene.n_frames - 1, int(t * cfg["fps"])) for t in scene.key_times}
    # with subtitles, also key the moment each card is fully typed: that's what gets reviewed
    for card in scene.cards:
        key_idx.add(min(scene.n_frames - 1, int((card["t_typed"] + 0.3) * cfg["fps"])))
    proc = None if keys_only else master_writer(out / "scenes" / f"{spec['id']}.mkv", W, H, cfg["fps"])
    if not keys_only:  # the scene's sound, mixed to its exact length
        snd = audio.intro_sound(int(round(scene.n_frames / cfg["fps"] * audio.SR)), STING) if spec["id"] == "s00_intro" \
            else audio.mix_scene(spec, scene, cfg["fps"])
        audio.write_wav(out / "audio" / f"{spec['id']}.wav", snd)
    keys = []
    for i, frame in scene.frames():
        if proc:
            proc.stdin.write(frame.tobytes())
        if i in key_idx:
            p = out / "keys" / f"{spec['id']}_{len(keys)}.png"
            Image.fromarray(frame).resize((W * 3, H * 3), Image.NEAREST).save(p)
            keys.append((i / cfg["fps"], frame))
        elif keys_only and i > max(key_idx):
            break
    if proc:
        proc.stdin.close()
        proc.wait()
    return keys


def contact_sheet(rows, cfg, path):
    """rows: [(scene_id, [(t, frame), ...])] -> one PNG, a row per scene at 2x."""
    from PIL import ImageDraw
    W, H = cfg["resolution"]
    s, pad, label = 2, 6, 14
    cols = max(len(k) for _, k in rows)
    sheet = Image.new("RGB", (pad + cols * (W * s + pad), pad + len(rows) * (H * s + pad + label)), (20, 19, 17))
    d = ImageDraw.Draw(sheet)
    for r, (sid, keys) in enumerate(rows):
        y = pad + r * (H * s + pad + label)
        for c, (t, frame) in enumerate(keys):
            x = pad + c * (W * s + pad)
            d.text((x, y), f"{sid}  t={t:.1f}s", fill=(190, 184, 170))
            sheet.paste(Image.fromarray(frame).resize((W * s, H * s), Image.NEAREST), (x, y + label))
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--scene", help="render only scenes whose id starts with this")
    ap.add_argument("--keys", action="store_true", help="key frames and contact sheet only")
    ap.add_argument("--youtube", action="store_true", help="also export the 1440p YouTube upload copy")
    ap.add_argument("--from-masters", action="store_true", help="skip rendering; re-cut and export from existing masters")
    args = ap.parse_args()

    ep = Path(args.episode)
    tl = yaml.safe_load(open(ep / "timeline.yaml"))
    cfg = {"resolution": tl.get("resolution", [320, 180]), "fps": tl.get("fps", 12), "scale": tl.get("scale", 6),
           "band": tl.get("band", 0)}
    out = Path("out") / ep.name
    for sub in ("scenes", "keys", "audio"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    # the intro card (engine/intro.py) goes in front of the first scene as s00_intro
    intro = None
    if tl.get("intro"):  # the title card's time of day matches the first scene
        first = (tl["scenes"][0].get("backdrop", {}) if tl["scenes"] else {}).get("time")
        intro = Intro({"opens_on": first, **tl["intro"]}, cfg)
    order = ([intro.spec] if intro else []) + tl["scenes"]
    scenes = [s for s in order if not args.scene or s["id"].startswith(args.scene)]
    W, H = cfg["resolution"]
    rows = []
    if not args.from_masters:
        for spec in scenes:
            print(f"rendering {spec['id']}", flush=True)
            rows.append((spec["id"], render_scene(spec, cfg, out, args.keys, intro if intro and spec is intro.spec else None)))
        contact_sheet(rows, cfg, out / "contact.png")
        print(f"contact sheet: {out / 'contact.png'}")
    if args.scene and not args.keys:  # a reviewable clip of each scene rendered, with sound
        for spec in scenes:
            sid = spec["id"]
            export(out / "scenes" / f"{sid}.mkv", out / "audio" / f"{sid}.wav", out / "scenes" / f"{sid}.mp4", W, H, cfg["scale"])
            print(f"clip: {out / 'scenes' / (sid + '.mp4')}")

    write_cues(order, intro, cfg, out)
    if not args.keys and not args.scene:
        lst = out / "concat.txt"
        lst.write_text("".join(f"file 'scenes/{s['id']}.mkv'\n" for s in order))
        master = out / f"{ep.name}_master.mkv"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(master)], check=True)
        wav = out / f"{ep.name}.wav"
        audio.write_wav(wav, np.concatenate([read_wav(out / "audio" / f"{s['id']}.wav") for s in order]), peak=1.0)
        loudnorm(wav)
        export(master, wav, out / f"{ep.name}.mp4", W, H, cfg["scale"])
        print(f"episode cut: {out / (ep.name + '.mp4')}")
        if args.youtube:
            yt = out / f"{ep.name}_youtube_1440p.mp4"
            export(master, wav, yt, W, H, 8, fps_out=24, youtube=True)
            print(f"youtube copy: {yt}")


LOUDNESS = -20.0  # LUFS, integrated, for the whole episode; true peak -1.5 dB. YouTube turns down, never up.


def loudnorm(wav):
    """Bring the whole episode to LOUDNESS with one linear gain (two-pass loudnorm, so the
    quiet scenes stay quiet relative to the loud ones; nothing is compressed)."""
    import json
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af",
                        f"loudnorm=I={LOUDNESS}:TP=-1.5:LRA=20:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = json.loads(r.stderr[r.stderr.rindex("{"):r.stderr.rindex("}") + 1])
    tmp = wav.with_suffix(".norm.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
                    f"loudnorm=I={LOUDNESS}:TP=-1.5:LRA=20:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                    f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
                    "-ar", "48000", str(tmp)], check=True)
    tmp.replace(wav)
    print(f"loudness: {m['input_i']} -> {LOUDNESS} LUFS")


def read_wav(path):
    import wave
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float64) / 32767 / 0.89


def write_cues(order, intro, cfg, out):
    """The cue sheet for the score: scene timings on the episode clock and each scene's music note."""
    t, scenes = 0.0, []
    for spec in order:
        sc = intro if intro and spec is intro.spec else Scene(spec, cfg)
        d = sc.n_frames / cfg["fps"]
        row = {"id": spec["id"], "start": round(t, 3), "end": round(t + d, 3)}
        if spec.get("title"):
            row["title"] = spec["title"]
        if spec.get("music"):
            m = spec["music"]
            row["music"] = {k: (round(v + t, 3) if k in ("in", "out", "hit") and isinstance(v, (int, float)) else v)
                            for k, v in m.items()}
        scenes.append(row)
        t += d
    cues = {"fps": cfg["fps"], "length": round(t, 3), "scenes": scenes}
    if intro:
        cues["intro_sting"] = STING
    (out / "cues.yaml").write_text(yaml.safe_dump(cues, sort_keys=False, allow_unicode=True, width=110))


if __name__ == "__main__":
    main()
