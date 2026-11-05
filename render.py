#!/usr/bin/env python3
"""Render an episode (or one scene) from its timeline.

    python render.py episodes/ep00_test                 # every scene + episode cut
    python render.py episodes/ep00_test --scene s01     # one scene
    python render.py episodes/ep00_test --keys          # key frames + contact sheet only, no video

Outputs go to out/<episode>/:
    scenes/<id>.mp4        one clip per scene, upscaled with nearest-neighbour
    keys/<id>_<n>.png      key frames for review
    contact.png            every scene's key frames on one sheet
    <episode>.mp4          the scenes concatenated
"""
import argparse
import subprocess
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

from engine.scene import Scene

KEYS_PER_SCENE = 4


def ffmpeg_writer(path, W, H, fps, scale):
    return subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
        "-vf", f"scale={W * scale}:{H * scale}:flags=neighbor",
        "-c:v", "libx264", "-crf", "14", "-preset", "medium", "-tune", "animation",
        "-pix_fmt", "yuv420p", str(path)], stdin=subprocess.PIPE)


def render_scene(spec, cfg, out, keys_only=False):
    scene = Scene(spec, cfg)
    W, H = cfg["resolution"]
    key_idx = set(np.linspace(0, scene.n_frames - 1, KEYS_PER_SCENE).astype(int))
    proc = None if keys_only else ffmpeg_writer(out / "scenes" / f"{spec['id']}.mp4", W, H, cfg["fps"], cfg["scale"])
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
    args = ap.parse_args()

    ep = Path(args.episode)
    tl = yaml.safe_load(open(ep / "timeline.yaml"))
    cfg = {"resolution": tl.get("resolution", [320, 180]), "fps": tl.get("fps", 12), "scale": tl.get("scale", 6)}
    out = Path("out") / ep.name
    for sub in ("scenes", "keys"):
        (out / sub).mkdir(parents=True, exist_ok=True)

    scenes = [s for s in tl["scenes"] if not args.scene or s["id"].startswith(args.scene)]
    rows = []
    for spec in scenes:
        print(f"rendering {spec['id']} ({spec['duration']}s)")
        rows.append((spec["id"], render_scene(spec, cfg, out, args.keys)))
    contact_sheet(rows, cfg, out / "contact.png")
    print(f"contact sheet: {out / 'contact.png'}")

    if not args.keys and not args.scene:
        lst = out / "concat.txt"
        lst.write_text("".join(f"file 'scenes/{s['id']}.mp4'\n" for s in tl["scenes"]))
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                        "-i", str(lst), "-c", "copy", str(out / f"{ep.name}.mp4")], check=True)
        print(f"episode cut: {out / (ep.name + '.mp4')}")


if __name__ == "__main__":
    main()
