# Ripped cars split into proxies

How to bring in a car ripped from a racing game when it is split into proxy submodels and has doors, hood and trunk that open: the transform, how to split it, what the rips ship for doors, the visual check before a build, and the order of work.

A car built the vanilla way, not from a rip, uses the rest of this pack (`README.md`) and `/dayz-p3d-audit`. Facts about the rips were measured on several ripped cars; they are not checked on `P:\`.

## What to settle before any geometry

The vanilla car to compare against is the sedan, script class `CivilianSedan : CarScript` (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:1`). Carry over its memory points by name; the engine, for one, reads the fuel position from `refill` (`P:\scripts\3_game\vehicles\transport.c:112`).

| Question | Answer for a ripped car |
|---|---|
| Axes and units | The net transform is `DayZ = (-Fx, Fy + Y0, -Fz)` in metres, with no axis swap and a determinant of +1, so it keeps the winding. Measure `Y0` for each car (`Y0 = contact - hub + lift`); never copy it from another car. |
| One model or proxies | A host shell carries the structural LODs. Visual parts too heavy for one LOD, and the attachments, go in as proxy submodels. Never fall back to one big model without saying so. |
| Moving parts | Doors, hood, trunk and wheels keep their own identity, their measured pivot and their item, slot and proxy wiring. Never merge them into the shell. |
| Whose frame rules | The sedan's frame rules for structure; the source's frame rules for the imported visuals. Test every conversion against anchors it did not produce: a part checked against a point made by the same transform always passes. |
| What the sedan is for | A debinarized sedan is a structural reference, not something to clone: its per-vertex mass comes back empty and some proxies warn, so do not copy mass from it or claim full parity with it. |

## What the rips ship for doors

From a library of 651 rips:

- A door container covers one side, and it can be either side. One car ships only `doorlf`, another only `doorRF_a`, and a third mixes sides (`doorLF_a`, `doorLF_b`, `doorLR_b`, `doorRF_a`). Do not assume the left front when you classify parts, count doors or build the mirrored door.
- Variants `_a` and `_b` of one door are alternatives, such as removable doors. Pick one and leave the other out, with the reason written down.
- A jamb, handle or door card with no `door<side>_<x>` panel means the door is part of the body. It is not another naming scheme: the panel that could open does not exist in the rip.

## Classifying the parts without Blender

The classification viewer, a Three.js page over a GLB export, lets the user review which parts are kept, dropped or movable by clicking, and collects the changes for a headless Blender script to apply. It only advises; the `.blend` file stays the source. It ships with `/dayz-model-tools`; the steps and the data it expects are in `rip-classify-viewer.md`.

## The user looks before the build

Automatic checks of names, face counts, hashes and matrices cannot see a colour or which way a proxy faces. On a ripped car that passed all of them, the user found four faults in minutes in a viewer:

- 64% of the car in one material and the whole interior in another: with no material map, 37 named parts (badges, mirrors, exhaust, jambs, skirts, underbody, suspension arms) went to the body paint.
- All four wheel proxies with the identity matrix, the same frame on both sides. Vanilla writes two mirrored frames, one per side; one frame with mirrored anchors mounts one side backwards.
- The 176 mm vanilla sedan wheel instead of the car's own wheel.
- A body colour nobody had checked.

A render of loose grey parts shows none of these. Three rules make the check worth having:

1. Render the car assembled, with its materials: shell, chunks, interior, removable parts in their proxies and wheels in theirs, in the colours of the `.rvmat` files that ship. Floating doors and inverted rims only show on the assembled car.
2. Tie the verdict to the files. Record a hash of every file that was looked at and hash them again before the build. Rebuilding a part makes the verdict stale, and the build waits until someone looks again.
3. No verdict means no pass. A verdict that covers fewer files than the car has now is a fail: a part nobody saw was not approved.

Only the user gives the verdict. An agent that records it in the user's name makes the check worthless.

Two traps in the render:

- DayZ is left handed and Three.js is right handed, so passing coordinates through unchanged mirrors the car. A mirrored car looks right until you read a badge; brand text is the check.
- Proxy placement is `vertices @ effective_frame.T + anchor`, where `effective_frame` is the MLOD proxy convention frame times the raw proxy frame (**model knowledge**). Guessing the placement from the proxy triangle by eye puts each door a metre away from the car.

## Symptoms

Each known failure of a car built this way has its own file: `get-in-guards.md`, `wheel-simulation-wiring.md`, `binarize-dropped-textures.md`, `attachment-proxies.md` and `vehicle-door-mechanisms.md`. Any other symptom needs its own diagnosis.

## Order of work

1. Confirm the car is a rip, split into proxies, with moving parts. Otherwise use `rip-import.md` or the rest of this pack.
2. Measure `Y0` for this car and write down the transform, the source revision and the sedan used for comparison.
3. The user classifies the parts in Blender or in the viewer.
4. Import with the transform, recording which source part each output part came from. Every kept or movable part must appear in some output part, and every dropped part needs a reason; source and output counts do not have to match.
5. Run the offline checks (`rip-import.md`), then the user's visual check, then the in-game test.
6. If one of the known symptoms appears, open only its file.

## Import habits

- Run headless Blender with `--python-exit-code 1`. Without it Blender exits 0 even when the Python script fails, and a failed step reads as done.
- Use absolute paths when the work spans the import folder and the `P:\` drive. A relative path resolves in only one of them and fails with `can't open file ... No such file or directory`.
- Match parts by name per door or panel group, ignoring Blender's `.NNN` suffixes, and check that no dropped part was imported anyway.
- Start each new car's profile from the minimum: the source, the anchors, the measured transform and the mounted wheel radius. Keys copied from another car's profile carry that car's fixes and break the next one (`rip-profile-schema.md`).

On Linux the steps are the same; what changes is in `_shared/linux-proton.md`. Building, testing and publishing the mod follow `skills/dayz-launch-test/references/mod-loop.md`.
