# View Pilot LOD and first person

What a seated player actually sees: the View Pilot LOD at resolution 1100, the proxies it references, how to trim it safely, and two traps of an offline first-person viewer.

The View Pilot LOD of a vanilla car sits inside its binarized model (`P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`), which py3d cannot read, so the facts below were measured on test vehicles, offline and in game, not on vanilla.

## Seated players see the 1100 copy

A car with a View Pilot LOD (resolution 1100) draws that copy of its geometry for seated players, not LOD 0. Any geometry, UV or selection change that must show from the seat (screen UV remaps, marker quads, interior fixes) goes into both resolution 0 and resolution 1100. Patching only LOD 0 looks fine from outside and unchanged from the seat, which reads as "the fix did nothing". Geometry meant only for the seated view, such as first-person gap closures, goes into 1100 alone.

## What the engine draws in first person

The engine draws the main model's 1100 plus every proxy that 1100 references. Each proxy adds its own 1100 when it has one, and its finest visual LOD otherwise. So asking whether a chunk file has a 1100 is the wrong question: a test car's shell 1100 listed 11 proxies, including all four body chunks, which ship only resolution 0 and were therefore drawn whole.

To hide something from first person only, give that part its own 1100 without the geometry. A part with only a visual LOD is drawn entire as soon as the parent's View Pilot references it.

## Trimming the View Pilot safely

- Run a trim for driver visibility against the complete assembled car, attachments included. On a test car a classifier that dropped "every face no seated eye sees front-facing" ran over the shell and interior only. With the doors missing, the body sheet around the door opening was visible from the seat, read as back-facing, and was cut: 73 faces gone, a missing strip where the body meets each door. The same classifier had marked the rear lights removable until one more occluder was added. One occluder short is enough to fail.
- Cabin materials inside body chunks are an import mistake, and they are what puts junk in front of the driver: on that car, 269 cabin metal faces in one body chunk and 18 headliner faces in another. The View Pilot only made them visible. Keep each material family in its own part and check for presence, not visibility; a leak outside the driver's view today is in view after the next pose change.

A check that catches all three compares:

| Check | What it looks for |
|---|---|
| Structure | Faces of a declared structural selection that are in the visual LOD but not in the 1100. Key faces by rounded coordinates so the check survives AddonBuilder reordering. |
| Occlusion | A fan of rays from the driver's eye over the scene first person really draws, against a per-car list of materials that must not be seen. |
| Containment | Each material family against the parts allowed to hold it; the longest prefix wins, so one declared exception does not weaken its family. |

Prove it fails on the broken build and passes on the fixed one. Two habits: a list of banned materials that is too broad shows up as the check failing on things the driver rightly sees overhead (here 10.9% of sight lines); and a deliberate exception, such as a console screen in the shell, is declared, not handled by loosening the rule.

Budgets and presence checks do not catch this. A face budget counts 1100's faces and a coverage check only sees that it exists; nothing compares a model's 1100 with its own LOD 0. A LOD edited by hand outside the builder has no check of its own, which is where silent cuts happen.

## Collapsed UVs in far LODs

A decimated LOD can keep every texture and material path and still draw wrong because its UVs collapsed. On a test quad the far LODs lost the body texture while the path count was clean. Only a count of UV area per texture found it: LODs 2 to 4 had body faces with zero UV area throughout (LOD 2: body1 1.827 of 1.827, body3 1.706 of 1.706, body2 2.618 of 2.650, metal 880 of 880), and LODs 5 and 6 named only `metal_co`. Measured in game on DayZ 1.30. A View Pilot made from a decimated LOD inherits the fault.

When a vehicle looks different from afar or from the seat, count UV area per texture on every visual LOD and on 1100 and 1200 before touching textures or materials. Fix it by transferring UVs from the intact LOD, then count again.

## Textures for the seated view

- A tiny 8 by 8 DXT PAA is invalid: its mip chain goes below 4 pixels and the engine draws the grey fallback (measured in game).
- For a flat colour in a config texture slot, use a procedural texture instead of a file, as vanilla does on a truck door: `#(argb,8,8,3)color(0.521569,0.427451,0.054902,1.0,co)` (`P:\DZ\vehicles\wheeled\config.cpp:18183`).

## Two traps of an offline first-person viewer

Neither was caught by an automatic check; both were found by eye.

- Draw what the engine draws: the 1100 of each part plus every proxy the 1100 references, as above. A viewer that left out proxies shipping only resolution 0 hid the roll cage it was built to judge. Read the parent's 1100 proxy list, then for each part pick 1100 if present and the finest visual otherwise. Never hardcode the resolution, because a part gains an 1100 the moment you cut something from it.
- DayZ model space is left handed; Three.js and a simple numpy raycaster are right handed. Raw coordinates draw the car mirrored, driver on the wrong side, which spoils every left or right judgement. Negate display X and swap one pair of triangle vertices so the winding survives, and keep ids, bounding boxes and ray metrics in true model space, because the `.p3d` edit reads those. Assert one asymmetric fact on screen, for example that the centreline projects to the right of the driver's eye, and stop the build if it fails.
