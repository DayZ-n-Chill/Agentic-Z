# Visual metrics and screenshots

When a complaint about a part's position is only perspective, where to anchor a HUD marker ray, and how to prove a visual metric on a known good part before trusting it.

The cases below were measured offline and in game on test vehicles, a helicopter and a car, not on vanilla models.

## A pose complaint can be perspective

When the user reports that a part on an imported model sits some centimetres off or tilted (a rotor against its ring, a wheel against its arch, a part against its socket), do not write a correcting offset from the screenshot.

1. Measure the deployed model, not the source. Convert the deployed ODOL back to MLOD with an outside converter and measure the part against its reference in engine space: a least-squares circle fit of the ring or arch rim, a plane fit of a blade or wheel disc, the bounding box of a socket. Compare the part's centre and disc normal with the fitted reference.
2. If it measures centred (offset of millimetres, tilt near 0 degrees), the complaint is perspective. A ring with depth along its axis is seen at an angle, so a centred part looks off centre, and the apparent offset changes direction with the camera. Confirm it by recreating the illusion: a flat colour render from the user's camera angle against a straight-on orthographic render.
3. Apply an offset only when the deployed model's measurement calls for it. An offset judged by eye on a model that is already centred moves what was right and costs an in-game cycle to discover.

Bounding box against bounding box never proves containment, because a protrusion is local. On a test helicopter an interior that sat "inside the glass" by bounding box still poked 7.25 cm through the canopy roof; only a grid comparing the interior's top surface with the glass surface cell by cell found it, and the user's eye was right. Measure surface against surface, per cell, before calling a pose complaint perception. A complaint about feel is settled with player data; a complaint about position is settled by measuring the deployed model. Watch the units too: a ring fit of 9.7 mm was once reported as 0.9 mm.

## Anchor a HUD marker ray at the camera

A heading marker drawn by projecting the vehicle origin plus `GetDirection()` times a distance reads skewed sideways against the airframe from any third-person camera off the centre plane. At 300 m the world point projects about 0.2 degrees off the vanishing point while the nearby nose projects about 7 degrees off, so the marker sits left or right of the hull even though the point is exactly on axis.

Anchor the ray at the camera instead. That is the flight director pattern and removes the parallax for every camera, orbiting third person or first person:

```c
vector nose = GetGame().GetCurrentCameraPosition() + veh.GetDirection() * D;
vector screen = GetGame().GetScreenPos(nose);
// draw only when screen[2] > 0
```

`GetCurrentCameraPosition` is declared at `P:\scripts\3_game\global\game.c:731` and `GetScreenPos` at `:963`. Fixed this way in game on a test helicopter.

Two measurement traps:

- A camera offset that reads the same across two boots does not prove a fixed engine offset when the probe fires once: it can just record when the probe fires (the same walk up, the same inherited camera yaw). Settle camera geometry from the vanilla code first. `DayZPlayerCamera3rdPersonVehicle` (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameravehicles.c:18`) pivots at the vehicle origin plus `GetTransportCameraOffset` (`:50`), which by default returns `"0 1.3 0"` (`P:\scripts\3_game\vehicles\transport.c:660` to `:663`).
- A named selection can hold points no face uses: the test helicopter's glass held 357 such points on one side. Count only points that faces reference when comparing sides, or the comparison lies.

## Check a ripped part before rebuilding it

A test car was one step away from rebuilding both doors from the raw rip because the cut mesh looked rotten (many winding passes, 74.7% loose vertices). Measured first, all six visual groups were already in the shipped proxy face for face, every face within 1 mm by centroid: skin 2043, card 3344, handle 1176, speaker 18, mirror 4721, mirror base 1174. Rebuilding would have reproduced the same geometry.

Before re-importing or rebuilding a ripped part:

1. Check completeness by faces, matched by centroid. That ignores vertex order and winding, so it measures presence only. Vertex presence is not enough: a cut can keep every vertex and still drop faces.
2. Measure gaps point to triangle, never centroid to centroid. A door jamb that looked missing read a 17.2 mm median by centroids and 0.7 mm by exact distance (95th percentile 7.1 mm, maximum 16.2 mm, no face beyond 30 mm). It was not a hole, and adding faces there would have fought with skin already present. A large triangle's centroid sits far from a small one even where the surfaces touch.

## An offline visibility check

The same question had cost five in-game cycles; an offline check answers it.

- A face is drawn when its MLOD normal points away from the camera (`rip-geometry-and-winding.md`, section "Game winding is the reverse of MLOD winding"). Calibrate this rule; do not assume it.
- Only drawn opaque triangles block sight. A culled face cannot hide anything, so a plain ray test overstates blocking badly: mirror glass scored 0 of 315 faces visible with raw rays and 238 of 315 once culling was applied to the blockers.
- Every run checks itself on a part confirmed visible in game, and reports itself void otherwise. A visual metric with no self check is not evidence.
- Judge a part only from cameras that can see it. Mirror glass scores 0% from the side and the front three-quarter view, which is right for a rear-facing mirror, and 75.6% from the rear three-quarter view.
- To inspect a seam, render the view with the culling rule and colour the part apart from the body. Both share one material, so one colour per material hides the seam. Blender's viewport culling is a shading setting and does not match the game.

## Traps in fitting and texture checks

- A symmetric part cannot tell a sign or a mirror apart. When fitting the Blender to DayZ transform, a body panel scored 5.5% for both signs of X and read as a pass while measuring nothing, because the panel maps onto itself when mirrored. Report each part's self-mirror score and have symmetric parts abstain. Here only the steering wheel could decide (23.6% against 0.0%), and it showed the import transform is a reflection with a determinant of -1 (`rip-geometry-and-winding.md`). Never take a part's side from its name; decide it with an asymmetric part whose in-game position is known.
- A flat placeholder `_co` texture reads in game as a missing part. A mirror texture was a 16 by 16 DXT1 whose `AVGC` and `MAXC` tags held the same value (RGB 38, 40, 44), so a single near-black colour. Geometry, material and winding were fine and the mirror still looked as if it had no glass. Check the PAA tags first: `AVGC` equal to `MAXC` means a flat texture.
- A fault can survive many winding passes by never entering the set they judge. The mirror's 315 faces were all classed as enclosed, a class the fixer skips, and were also left out of the component count by material. When a fault outlives several passes, first check that its faces are in the set the passes look at.
