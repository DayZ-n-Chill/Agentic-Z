# Closing first-person gaps in the View Pilot

How to close gaps in a fairing or cockpit through which the seated rider sees the ground: black membranes that only the View Pilot LOD (resolution 1100) carries, placed behind everything the steering sweeps, and tested with the bars turned. Measured in game and offline on a motorbike mod derived from `Motorbike_02_ColorBase` (`P:\DZ\vehicles\singletrack\config.cpp:1404`). How the View Pilot is assembled is in `view-pilot-assembly.md`.

## Where the closures go

On a model with a View Pilot, a fix for something only the seat sees goes in resolution 1100 alone. This narrows the see-through rules of `_shared/models/axes-and-winding.md` and `skills/dayz-p3d-audit/references/winding-absolute-check.md` for faults seen from the seat. An exterior gap closure (`visual-gates-and-winding.md`) is seen from every angle and is double-sided in the gap; a View Pilot closure is seen only from the seat. It is single-sided on purpose: the rim tuck below relies on the culled side, and a twin would double its cost in an 1100 with little room. It sits behind the steering sweep because the bars and fork move through the rider's line of sight.

Measured in game: closures that were then double-sided, and first-person inverted twins in LOD 0, showed from outside as black slivers, one of them hiding the intake. A build without both lost the slivers; since it removed both together, it does not say which caused them. With both in the 1100 LODs only, close shots from outside were clean, and in first person the closures covered the large gaps.

The vanilla bikes ship no View Pilot (read from their binarized models, not checked in game; `motorbike-vanilla-p3d-anatomy.md`), so the 1100 has to be added. Seat-only geometry of a proxied part goes in that part's own 1100, because first person draws each referenced proxy's 1100, or its finest visual LOD when it has none (`view-pilot-and-first-person.md`); the mod's engine proxy got an 1100 for its inverted twins.

## How to generate the closures

Find the gaps offline with a rasteriser, from each measured or offset eye and pitch: a gap is enclosed, at least 40 px at half resolution, centred in the cockpit, with at least 20 percent of its rim on fixed parts. Give each gap a membrane whose depth is filled smoothly from its rim, wound so the engine draws it towards that eye. Calibrate that winding on a face seen in game (`rip-geometry-and-winding.md`, and the self-check in `visual-metrics-and-viewer.md`). Pixel counts here are at half resolution (1920 by 1080) unless stated. The points on steering sweep depth, rim tuck and outline come from faults seen in game; the point on testing with the steering turned comes from offline renders only.

### Test with the steering turned

Closures that leave the steering intact with the bars straight can hide the fork once the bars turn. Offline, such a set covered 247,420 px over 48 views (12 eyes at pitch -50, bars at 10 and 20 degrees each way), up to about 8,000 px in one view. A check with the bars straight, offline or in game, does not show it; this fault was not checked in game.

### Put the membrane behind the steering sweep, ray by ray

In each pixel keep the membrane at least 2 cm deeper than the deepest point of the sweep there: bars, fork and front wheel over full lock (20 degrees each way on that bike), suspension at rest, the depth map widened by 4 px. Then drop any face with a vertex, edge midpoint or centre within 6 mm of the sweep. From the eye that made it, a gap's ray meets no fixed part, so the membrane hides only the ground there. From other eyes it can still cover fixed parts (one cleanup pass removed 111 such faces, 18,824 px); the rim cleanup below handles them. Behind the sweep, a gap that showed mottling reads as plain black in game.

Two alternatives fail:

- Trimming the membrane where the sweep passes fails either way. The thin strips left behind stack up in the same gap, one per eye and pitch: in game they show as mottling, and stacked strips can make the generator refuse patches (52 in one run). Refusing patches that cover less than half their gap leaves the gaps the steering crosses open: 108 refused, 55,884 px open over 36 views, against 4,012 for the closures they would replace. Placed behind the sweep instead, the half-coverage guard never fires.
- Pushing single vertices back along their rays lets triangles cross the steering: in game the top clamp, controls and grips vanish behind black fragments, while an offline check that counts only ground seen through gaps still passes. Count closure pixels in front of parts as well as open pixels (`visual-gates-and-winding.md`, `rip-panel-open-rim.md`).

### Tuck the rim under fixed parts by centimetres

Put the rim behind the deepest fixed point of its grid cell. A rim only 6 mm behind each pixel cuts panels seen edge-on between grid vertices: in game a ragged black edge and a row of light teeth; offline 3,097 px (full resolution) of closure in front of a fixed part from the eye of that capture. Three changes clear it: the rim 2 cm behind the deepest fixed point of its cell, the depth smoothed only backwards (an edge-on wall faces away from the next eye and is not drawn), and a cleanup that removes any closure face more than 3 mm in front of any fixed part. With all three, offline showed 4 px in front of fixed parts over 12 eyes at pitch -50, and in game the edge read clean.

### Trace the outline smoothly

Trace the outline with marching squares on a smoothed mask, with interpolated crossings. Membranes built from whole grid cells give stepped edges in game. With marching squares, exactly horizontal or vertical edges fell from 53 to 14 percent of the outline and turns over 60 degrees from 43 to 14 percent, and no steps showed in game.

### Use matte black

Use a near-black procedural colour, specular 0 and an SMDI with no level or gloss, since membranes behind the sweep have steep faces a glossy material might light in pale bands. Matte and glossy were not compared side by side; in game the matte closures read as plain black.

### Keep them in step with LOD 0

The closures are computed against LOD 0 and live in the 1100, so regenerate them from the final LOD 0 whenever the 1100 is assembled, and again after any re-seed, merge or LOD 0 edit. List them in any 1100 count or containment check as a class present in the 1100 and absent from LOD 0 (`view-pilot-assembly.md`), and keep them out of any step that makes the 1100 double-sided (`visual-gates-and-winding.md`, `rip-import.md`), which would draw the edge-on walls the rim tuck relies on hiding. These two points are suggestions, not measured.

## Generate from every eye the rider can have

On that bike the first-person eye changed with the character, between runs of one character, and with the pitch within a run: one eye went from 7.6 cm off-centre at pitch -50 to 4.7 cm on the other side at -65. With the head turned aside at yaw 0 it sat about 9 cm off-centre (8.7 cm at pitch -50, up to 9.4 cm). Log the eye of every run (`skills/dayz-launch-test/references/vehicle-first-person-eye.md`, "Log the eye in every run").

The final set had 23 eyes: two logged in game, each also moved 3 cm up, down, forward and back; three more, two logged in game and one recovered from a screenshot (`skills/dayz-p3d-audit/references/winding-absolute-check.md`); copies 9 cm to each side of the highest and lowest logged eye, and 4.5 and 9 cm of a third; and the off-centre eye with its mirror. No offset combines two axes. Each eye looked at pitch -35, -50 and -65, yaw 0.

Counting only enclosed gaps of at least 40 px centred in the cockpit with at least 40 percent fixed rim, 526 px stayed open over the 69 views, against 70,261 for the closures they replaced, and no closure stood in front of a fixed or turned part (checked at pitch -50 only). In game, at pitch -50 with the bars straight, two characters were clean over three runs, one with the head 7.6 cm off-centre. An eye set is a sample, not a bound: moving one measured eye 12 cm sideways, to 10.5 cm off-centre, found 10 px of closure more than 3 mm in front of a fixed part offline at pitch -50, not shown to be visible in game.

## What the offline check cannot see

- Its renderer drops every glass face, so "any fixed part" leaves out the windscreen; whether a closure stands in front of it or behind it in the rider's view was not measured. Geometry close to a pane has read in game as a painted-over window (a black band 0 to 1 mm behind the glass, `visual-gates-and-winding.md`) and as an artefact on the glass (skirts within 5 cm of a pane, the closest 6.1 mm, `rip-panel-open-rim.md`). Keep about 8 mm of clearance to transparent glass.
- It samples points on faces instead of rasterising them as the engine does, and its gap detector closes slits up to about 2 px wide (about 4 px of the capture) and keeps only enclosed gaps, so a 2 to 3 px line like the one seen in game is never counted.
- Fixed and turned parts were checked at pitch -50 and yaw 0 only, and since the in-game eye moves with the pitch, real eye and pitch pairs fall between the sampled ones.
- No in-game first-person capture with the bars turned was judged. The in-game capture stays the last word.
