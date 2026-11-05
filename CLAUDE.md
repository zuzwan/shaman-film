# Shaman film: engine rules

A serialized pixel-art film, drawn entirely by code. Every session working
here inherits these rules. Change them only when drew says so.

## Format (locked)
- Base resolution 320x180, upscaled x6 to 1920x1080 with nearest-neighbour, in FFmpeg only.
- 12 fps. Animation cycles run slower (sprites declare their own `fps`, usually 2 to 6).
- Palette: `engine/palette.py` only. Never write hex anywhere else. A muted base (ash,
  sky, cold, rust, moss), a night blue, and one ramp per region of the world
  (mauve uplands, tide coast, blood glass towns, fern interior). `ember` is
  reserved for rig lights, fire, and the capture.
- Every scene sets `backdrop.region` and `time` (`engine/regions.py`) so places
  look different as the journey moves. See `docs/style.md` for the full brief.
- No birds or bats on screen, ever (the world lost them). Insects fill the air.
- No alpha blending and no anti-aliasing. Tones mix only by Bayer dithering (`engine/dither.py`).
  Fades, glows, captions and transitions all dither.
- Captions: the 3x5 pixel font in `engine/font.py`, uppercase, bone with an ink drop shadow.
  Sparse narration; one line on screen at a time where possible.

## Layout
- `engine/` the reusable engine. Most review effort goes here.
- `assets/sprites/*.yaml` ASCII sprites (format documented in `engine/sprites.py`).
  Draw facing right; actors flip. A sprite enters the library only after its
  contact sheet (`python tools/lineup.py <name>`) is approved.
- `episodes/<ep>/timeline.yaml` one episode as data: scenes with duration, backdrop,
  camera, weather, actors, lights, captions, transitions. Edit this, not prose.
- `out/` renders (gitignored).

## Loop
1. `python render.py episodes/<ep> --keys` for key frames + `out/<ep>/contact.png` (seconds).
2. Review the contact sheet, adjust the timeline or sprites.
3. `python render.py episodes/<ep> --scene <id>` for one clip, then the full episode.
4. Tag each approved cut in git (`ep01-cut1`, ...).

## Not built yet
Audio (score, effects, narration mux), scene-to-scene
cross transitions, close-shot (larger) sprites, a capture animation for the rig.
