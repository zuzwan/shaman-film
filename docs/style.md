# Style brief

Drawn from drew's references (`reference/` in the project library) and the
world doc (`descriptive references/`). This is what the engine aims at.

## What the references share
- **Dark values, one light.** Most frames are 80% shadow with a single source:
  a torch, a lantern, a fire, a moon (images-4, 5, 10, 11, 19, download.jpg).
  Light is the composition. Use one key light per shot.
- **Small figures in big places.** Cloaked figures are a tenth of the frame or
  less, seen from behind or in profile (images-2, 3, 5, 13, 21). Wide shots are
  the default; close shots are the exception and need their own larger sprites.
- **Ruins and dead trees as the vocabulary.** Arches, broken walls, bare
  branching trees, towers on rock. Props in `engine/props.py` cover arches,
  dead trees, moons and fire.
- **Each place has its own color.** The references swing from ochre haze to
  mauve dusk to cobalt night to crimson sky. drew's call (2026-11-05): a mix of
  muted base and strong per-place color, so that shots don't all look like the
  same place and the journey reads.

## Regions (engine/regions.py)
| Region | World | Palette | Default weather |
| --- | --- | --- | --- |
| river | mills, grain, bonded labor, the Survey strongest | ochre sky, brown fields | light ash |
| uplands | cisterns, fungus cellars, restitution towns | mauve dusk, slate peaks | snow |
| coast | shellfish, kelp, salt | sea-teal, salt white | rain |
| glass | ruins of old cities, salvage crews | rust-red sky, black skyline | heavy ash |
| interior | unpeopled, wildlife returning, the Fold | wet green | glowing insects |

Night is blue everywhere, tinted by the region's darkest ramp.

## World rules that touch the picture
- **No ordinary birds or bats.** The Quiet took them; never draw them as
  background life. Insects fill the air instead: `motes` (glowing insects) and
  `swarm` (locusts) are weather types.
- **Fantastical birds are predators.** drew's call (2026-11-05): the Quiet hit
  ordinary birds only. Any fantastical bird is carnivorous and a threat, closer
  to a gryphon than a songbird. Stage them as danger: big, rare, lit from below
  or against the sky.
- **Creatures.** Everyday animals of the Americas plus beings from the
  Americas' folklore and myth share the world (wendigo-type, Appalachian
  horrors, and others). The world bible avoids closed or sacred beings.
- **The rig** is salvage that reads a dying nervous system, heavy and finite.
  It is a machine on a handcart, not a tower. Ember is reserved for it, fire, and
  the capture.
- **The shaman** is old and hunched, with a ragged cloak and a forked staff. Capture
  scars are not readable at this scale; show them in close shots.
- **The apprentice** is upright, carries the pack and the lantern, and is the
  one who talks to towns.
- **The Survey** has pale coats and brimmed caps, and travels as a column:
  chainmen, clerks, guards.
- **The Fold** looks like a devout farming community. Its hosts share one sprite
  and one gait, so put them in step with no phase offsets. The sameness is the tell.
