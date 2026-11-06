# Shot catalogue

What a `SHOT:` line in a script can ask for, and what the engine does with it.
A scene without SHOT lines is one wide shot: a figure walking left to right in
front of a backdrop. That is the thing to avoid. Cut every scene into shots;
change size and angle at least every few seconds; put something between the
camera and the figures.

    SHOT: size · angle · subject and action · camera move · hold

Hold is `2s` or `6f` (frames at 12 fps), or left out, in which case the shot
lasts as long as its cards take to read. The subject's first word, when it is
a cast name (Auk, Teal, rig), becomes the focus of the shot. Words can come in
any order; anything not in the lists below is treated as the subject.

Test reels: `episodes/ep00_shots` (one scene per entry here) and
`episodes/ep00_fights` (one scene per fight type).

## Size

| word | what it is | engine |
|---|---|---|
| `extreme-wide` | figures tiny against the land; the journey, the scale of a place | zoom 1, letterbox bars |
| `wide` | the stage: figures full height, the set around them | zoom 1 |
| `medium` | waist up; conversation, a reaction, the moment before a blow | zoom 2 on the subject |
| `close` | the face, the hands, the thing on the ground | zoom 3, or a close sprite (`auk_close`, `teal_close`) on a `plain` backdrop |
| `insert` | one object filling the frame: a rig face, a hand on a crank, a map | zoom 4, or an insert sprite (`rig_face`, `hands_crank`) |

Every character exists at three sizes (`auk`, `auk_med`, `auk_big`). Give the
actor `med: auk_med` and a medium or close shot draws the sharp figure over
the zoomed set. Close and insert sprites (`auk_close`, `teal_close`, `rig_face`,
`hands_crank`) are drawn at close scale and used at zoom 1 over a plain backdrop.

## Angle

| word | what it is | engine |
|---|---|---|
| `eye` | level, the default | — |
| `low` | horizon drops, the figure towers; menace, the rig | horizon shifts down 22 px (feet at y 174) |
| `high` | looking down a slope or from a window; small people, long roads | horizon shifts up 34 px (feet at y 118) |
| `skyline` | the glass towns, black against the sky | two ridge layers, horizon 14 px down |
| `over-shoulder` | a dark head and shoulder in the corner; who is being talked to | screen-pinned `shoulder` prop, zoom 2 |
| `pov` | what she sees: edges dark, the frame unsteady | `vignette` fx; add `shake` for breath |
| `framed` | through a doorway, a window, an arch; the watcher outside | `doorway` prop over everything |

Foreground props (`layer: front`, parallax above 1) make any angle deeper:
`trunk`, `grass`, `branches`, `doorway`. Screen-pinned props (`layer: screen`)
stay put under any zoom.

## Move

| word | what it is | engine |
|---|---|---|
| `static` | held; the default, and most shots | — |
| `pan-left`, `pan-right` | the camera turns across the set | pan 36 px over the shot |
| `push-in` | slow move toward the subject; dread, decision | zoom from size to size + 1 |
| `pull-out` | the reverse; aftermath, loneliness | zoom from size + 1 to size |
| `track` | the camera walks with the subject | `follow` the actor; near trunks slide past faster |
| `shake` | impact, a blow landing, the rig firing | decaying random offset |

`depth-walk` is not a move but a pattern: three cuts of the same figure
coming toward camera at scale 1, 2 and 3, instead of a slide across frame.
`ep00_shots` scene 8.

## Pages and inserts

- `panels`: a manga page. Each panel is a sub-shot in a rectangle on a black
  page, landing one after another with a one-frame white pop. For the
  moment before a fight (his eye, its skull, her breath) or for a run (feet,
  the look back, the one behind). Rects are laid out on the visible picture,
  320 x 140 with the text band.
- `map`: the Survey's map as an insert. A `plain` backdrop with paper sky
  stops, `contours`, a `route` that inks itself over a few seconds, and
  `marker` towns with labels. `ep00_shots` scene 10.
- `cutaway`: an insert of something else in the scene (the rig face, the
  fire, eyes in the trees) between two shots of the figures. A half-second
  is enough.

## Fights

Rare, short, brutal; the long part is the stillness before and after. The
cuts do the violence. Every fight is a few of these beats in order:

| beat | what it is | how it is cut |
|---|---|---|
| `standoff` | neither moves; snow, breath, eyes | extreme-wide hold, a panel page of eyes, a hold, one flash |
| `ambush` | the threat is already in frame, behind what is nearest the camera | a front prop hides the attacker; whip pan with horizontal speed lines; a flinch insert |
| `chase` | the camera runs with her | `track` with horizontal lines; a page of feet, the look back, the one behind; the end comes from off frame |
| `creature` | seen before it is understood | eyes in the dark, a slow stalk in wide, a page (skull, his glare, the rig face), then the lunge |
| `clash` | the exchange itself | 3 to 6 frames: radial lines, impact frame (flat bone, figures in ink), its negative, white tint and shake |
| `aftermath` | the long hold | slow push-in or pull-out, vignette, a card, nothing moving |
| `capture` | not a fight, a ritual with teeth | wide, hands on the crank, the rig face dark then lit, the thing held, the flare, the impact, a long hum |

Reference cuts: `episodes/ep00_fight` (the first clash), `episodes/ep00_fights`
(standoff, ambush, creature, chase, capture).

## Animation depth

Figures should never be statues. On any actor: `breathe: 3` lifts the torso a
pixel for half of every three seconds; `bob: 1` bounces a walk; `fps` runs a
cycle faster or slower than drawn; `phase` offsets it so two figures are not
in step. Every character has the full move set (`tools/art/figure.py`): idle,
walk, run, turn, talk, crouch, kneel, sit, point, look_back, windup, strike,
hit, stagger, down; the faces have idle, speak, glare, flinch, look_down,
look_away, closed and grim. `episodes/ep00_cast` is the reel.
