# Episode 1 pilot: what it took, and what the loop should change

The pilot (`episodes/ep01`, "Here") is the template for the production loop. It is
cut straight from `storyboard/episodes/ep01.md`: 26 scenes, about 160 shots, every
card from the script, 12 min 30 s with the intro. These notes are for the loop: what
had to be built for this episode, what will have to be built again for each new
episode, and what to change in the engine and the process.

## Numbers

| | |
|---|---|
| Length | 12:30 (intro 0:12 + 26 scenes). The target is ~10 min; ep01 has 74 cards, and the reading time sets the length. |
| Render | ~8.5 min for the whole episode on 4 cores (frames ~6 min, the 1440p export ~2 min) |
| Files | `ep01.mp4` 1080p 60 MB · `ep01_youtube_1440p.mp4` 78 MB · lossless 320x180 master 27 MB |
| Season | 24 episodes at this rate is roughly 2 to 3 GB of finished files |

## What was built for ep01

- **Cast** (`tools/art/figure.py`): Ida, Hask, Pim (with slate, and with lantern), Bett,
  haulers, hosts with brooms / hoes / buckets, the host boy, and `auk_rig` (Auk carrying
  the open rig: the iron pole, the face stack above his head, the crown of antenna rods).
  New poses: doze, sit_doze, haul, sweep, grind, carry, drink, look_up.
- **Sets** (`engine/sets.py`, ~60 props): walls with gates, arches and peep slots, water
  stones and bowls, the levee and flooded fields, water (river, ford, millrace), the mill
  wheel and the great gear, facades with pinned-back doors (and the sitters at night),
  cobbles, the trestle and awning, the Survey tripod, crates and querns, the grate and
  the drowned body, laundry, the handcart, the trench, lanterns, moths, flies, the silk
  tent with its shadows, candles, the bond-board and ring, the smoke line, Auk's scent
  view, and inserts: the child's hand, the woman's eye in the slot, the bowl (reflection
  or dead gnats), Auk's scarred forearm, the knotted cord, the clamp and the rig's leads.
- **Sound** (`engine/audio.py`): every effect is synthesised (no samples). 21 ambience
  beds (crickets, river, millrace, ford, wheel, gnats, flies, querns, gear, moths,
  beetles, rope and haulers, wet silk, smoke, Bett's humming, the rig's valve hum...)
  and ~25 events (ratchet, valve, creaks, bar drop, steps, splashes, pour, drip, broom,
  retch, breath, tally pegs, many bare feet, the title sting...). Footsteps are automatic
  from the walk cycles. The episode is normalised to -20 LUFS.
- **Music cue sheet**: `out/ep01/cues.yaml` has every scene's start and end on the episode
  clock, the intro sting window, and 11 `music` notes (1M1 to 1M11) with mood and hit
  points, for scoring after picture lock.

## Engine changes made during the pilot

1. Shots can carry their own `cards`; a shot without a duration lasts as long as its
   cards take to read. (Before, every card needed a hand-computed `at`.)
2. A shot on a `plain` backdrop is an insert: drawn at its own size (no zoom) and showing
   no scene actors unless it lists them. Framing props (doorway, shoulder) are not added
   over a close or insert on a plain backdrop.
3. A shot's subject is looked up in the shot's own actors too (focus and track used to
   miss anyone who wasn't in the scene's cast list).
4. `render.py` writes a lossless master per scene and builds every export from it, mixes
   sound per scene, writes the cue sheet, and has `--youtube` and `--from-masters`.
5. The contact sheet takes one key per shot, so it reads as the shot list.
6. `tools/script2timeline.py`: the scene header's `Shot:` line was being read as a shot
   (it now goes to notes); `SOUND:` lines now draft the scene's ambience beds.

## What the loop should change

1. **Sets per act, ahead of time.** Most of the pilot's time went into set pieces, not
   cutting. Hollin's sets will carry ep02 to ep06 (river country) with small additions,
   but each act needs a set pass before its first episode: uplands (cisterns, fungus
   cellars), glass towns, the interior. Do it as one batch per act.
2. **Cast registry.** New named characters need a costume before their episode. Keep a
   list of who appears in which episode (from continuity.md) and build costumes a few
   episodes ahead.
3. **Close-ups for the recurring cast.** Only Auk and Teal have portraits; Ida, Pim and
   Hask close-ups are their large body sprites, which read as medium shots. If they
   recur, they need faces (the portrait pipeline can make them).
4. **Length.** 74 cards made 12.5 min. If ~10 min matters, the scripts should aim at
   ~60 cards, or holds can be trimmed (the reading-time rule is chars / 15 + 1 s).
5. **The rig face.** `rig_face` is one generic face; the script asks for the hare. Faces
   per animal (12, then 13, then 14) would help the cold opens and the captures.
6. **Auk with and without the rig.** Walking, he carries it (`auk_rig`); when it is planted,
   he is the old `auk` sprite, which has a staff. Decide whether Auk has a staff at all.
7. **Script SOUND lines are good enough to draft beds automatically**, but events (a bar
   dropping, a ratchet) still have to be placed by hand against the picture. Writing the
   event as its own line (`SFX: bar drops, at the end of the shot`) would let the
   converter place it.
8. **Review loop.** Review was key frames (one per shot) per batch of scenes, then the
   whole episode. For the automated loop, drew reviews the contact sheet and the 1080p
   cut; tagging a cut (`ep01-cut1`) publishes it.

## Delivery

- `python render.py episodes/ep01 --youtube` makes both files in `out/ep01/`.
- Pushing a tag `epNN-cutN` runs `.github/workflows/release-episode.yml`, which renders
  the episode on GitHub and attaches the YouTube copy, the 1080p cut and the cue sheet to
  a Release. Video never goes into git history.
- The YouTube copy is 2560x1440 (x8 nearest-neighbour, so every pixel is an exact 8x8
  block) at 24 fps (each frame doubled; YouTube handles 24 better than 12), H.264 high,
  AAC 384 kbps stereo, faststart. YouTube gives 1440p uploads a better codec than 1080p,
  which keeps the dithering from smearing.
