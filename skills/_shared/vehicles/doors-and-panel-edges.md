# Door edges and panel hinges

Why an imported door shows a missing edge when it opens, how to measure that edge against a vanilla door and close it by script, and what a hood or trunk needs that a door rig gets wrong.

The numbers below were measured offline on two imported cars (a sports coupe and a sedan from third-party mods), not on vanilla, and are not checked on `P:\`. The see-through rim of an imported panel and the face for face completeness check are in `rip-panel-open-rim.md`.

## Imported doors have no end caps

A ripped door arrives as two open shells, the outer skin and the inner card, with nothing closing the leading and trailing edges. The source game never showed that edge, so it was never modelled. Every DayZ door opens, so every imported door shows it. Assume the caps are missing until you measure them.

On the coupe, both doors, at the two ends of the door's long axis:

| End | Faces along the axis | Cap area | A real cap, height times thickness |
|---|---|---|---|
| Leading | 125 | 25 cm² | about 710 cm² |
| Trailing | 62 | 17 cm² | about 710 cm² |

That is 3.5 and 2.4 percent of a real cap, and what is there is paint folded over the skin edge. The door is 77 mm thick at both ends.

Quick check for any car with opening doors: slice the door at both ends of its long axis, add up the area of faces whose normal runs along that axis, and compare with height times thickness. Under about 30 percent means the caps are missing. This only detects absence; use free edge length (next section) to judge a fix.

Measure a part in the state where it is exposed. With the door shut the body covers the edge, so every check run on the shut car passes while the defect sits on the open door. Collect a door verdict only with the door open, and ask for a screenshot that shows it open. The caps are new geometry: winding or normal fixes cannot create a surface that was never there. When an edge reads as "nothing at all" rather than wrong colour or shading, suspect a missing surface before a flipped one.

## Measure free edge length against a vanilla door

The control is one vanilla door, `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedandoors_driver.p3d`. It is binarized (ODOL version 56), so debinarize it to MLOD first with an ODOL to MLOD converter; this repo ships none, and `scripts/tools/dayz-odol-strict` expects the same outside tool.

Measure free edge length in a band at each end of the long axis, across every visual LOD and the View Pilot LOD (res 1100). With a 6 percent band:

| End | Vanilla | Coupe import |
|---|---|---|
| Front (A pillar) | 0 mm | 673 mm |
| Rear (B pillar) | 612 mm | 627 mm |

With an 8 percent band over the full perimeter, vanilla reads 0 mm front and about 502 mm rear, the import 743 mm and 598 mm. In game both ends of the import show the defect: vanilla having free edge at the rear does not mean it stays exposed.

- Free edge on a door perimeter is normal. The perimeter is a closed loop of about 4.4 m (outer skin and glass) on vanilla too, so a check on total free edge fails a healthy door.
- Do not judge by cap area against height times thickness. It assumes constant thickness and sheet metal over the full height; on a frameless coupe door the upper half is glass, and the band reads the curve of the bend as thickness. That rule asked for about 710 cm² where the real shape allows about 640 cm², and only over part of the height.

Three fixes were measured and do not close the edge:

- Making the front band double sided: 0 pixels changed in a render with correct culling. The see-through edge is not a one-sided face problem.
- A folded lip copied from vanilla: it moves the free edge without removing it, and at 2 mm depth body vertices already sit inside it (the door to jamb gap is 0.7 mm).
- Bridging the outer skin to the inner card: the two edges do not line up. Only 6 of 13 height strips have both edges, with gaps of 121 to 218 mm, so an automatic bridge makes a twisted wall.

The cause to check on the next car: the outer skin and the inner card are separate meshes that do not touch. On the coupe the inner card (plastic and black trim materials) stops 108 mm short of the front edge, which the paint skin reaches.

## Close the edge by script

A band added around the perimeter by script reaches vanilla parity on both doors, across the visual LODs and View Pilot. A band of constant 5 mm depth fails because it is too shallow for a gap of about 77 mm, not because of its facing: its quads render the same with culling on and off.

- Find the true free edge: count each edge's use across all faces of the LOD and keep skin edges used once. Counting only within the skin material marks edges covered by glass or trim as free, and the band then crosses them.
- Measure depth per edge vertex: cast a ray inward along the thickness axis and use 90 percent of the distance to the first wall, clamped to 8 to 60 mm, and 60 mm where no wall lies within 150 mm. The real gap runs from 10 to 135 mm, so any constant is wrong on half the perimeter.
- Keep it watertight: one extruded point per welded edge vertex, shared by neighbouring quads. Extruding per edge with different depths leaves slits.
- Winding: the stored normal points out of the edge, opposite the geometric winding, which is the convention on every visual LOD face of both doors. "Out of the edge" is the part of (edge midpoint minus skin centroid) perpendicular to the edge, with the thickness component set to zero.
- Always compare with the vanilla door on the same metric. The edge render went from 15.0 to 25.4 percent drawn surface against 26.8 percent on vanilla; a sweep of rays along the long axis gives 65.7 percent clean rays against 68.8 percent on vanilla. A fixed threshold without the control fails healthy doors, because most rays legitimately pass outside the silhouette.
- Render the edge in two scenes: the assembled car with doors shut, to catch a regression from outside, and the door alone, which stands in for the open door where the complaint lives.

## Hoods and trunks are not doors

These numbers are model geometry measured offline on the sedan import; the rig changes are not checked in game. A rig written for doors makes assumptions that are false for a hood and a trunk.

1. The hinge edge differs per role. A door hinges on its front edge (minus Z), so door rigs band over the lowest Z. A hood hinges on its rear edge, by the windscreen (plus Z), and a trunk on its front edge (minus Z). Measured: the hood hinge sits 12 mm from the panel's highest Z, the trunk hinge 4 mm from its lowest. The hood's front edge, where a door rig would band, is 1.16 m from the real hinge. Declare the hinge edge per role.
2. Tilt is measured against the role's own axis. The hood and trunk axes sit at 89.81 and 88.84 degrees from plus Y, because they run sideways (plus X). A "tilt against Y" check forbids them outright.
3. The opening sign is silent. With a sideways axis `axis[1]` is about zero, so the usual `if axis[1] < 0: axis = -axis` lets noise pick the sign. Take the direction from the declared angle, and check it physically: the free edge, opposite the hinge, must rise when the panel opens. A check on movement size alone passes with the sign reversed. That check only re-derives its own maths; it never asks the engine. In DayZ 1.30 the two passing rows were the hood and trunk opening downward (free edge lift +1.4021 m and +0.8393 m), and on a vertical hinge the rule does not apply, since a door does not rise (its side roles read 0, 0, -0.0506 and -0.0506). Let offline checks decide the axis, the face set and the per-side sign split, then fix the opening direction with one in-game look per car and record it. With the signs split per side, one look settles all six panels: all six reversed means the convention is flipped, mixed means a role was split wrong. Write N/A where the rule does not apply.
4. The axis check does not prove the role holds the right parts. The axis is fitted on the one part that declares the hinge, so adding a jamb, a body panel or a headlight to the role moves the axis by less than a degree and both checks still pass. Add a separate check: the largest distance from any role face to the axis against a declared radius, and the face count against the part list.
5. Before writing a `+x` or `-x` side rule, measure whether faces lie on the x=0 plane. A centroid rule drops them from both sides and they vanish from the car. On the sedan none of 18 candidate parts did, but that is one car, not a format rule. A whole part needs no side rule if the selector defaults to all faces.
6. A hood usually has glass and a trunk does not. Code that needs both a body and a glass box aborts on the trunk, and on the hood it can class headlight glass as a window, with a window damage zone and glass hit material. Make the glass box optional and the body or glass class declared data, not a name prefix.
7. Item mass does not carry over from a door. One global `geometry_mass_kg` gives a hood a door's weight.

Vanilla ships the sedan's hood and trunk as their own models: `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedanhood.p3d` and `P:\DZ\vehicles\wheeled\civiliansedan\proxy\sedantrunk.p3d`.
