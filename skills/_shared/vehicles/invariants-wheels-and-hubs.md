# Wheel, hub and axle checks

Where wheel hubs live in the model, how wheel proxies line up with them, hub height against tyre radius, which way a wheel faces, and why every axle must be listed in an `Axles` override.

The `CarScript` base names each wheel's hub with `wheelHub="wheel_1_1_damper_land"` and its three siblings (`P:\DZ\vehicles\wheeled\config.cpp:297`). The vanilla sedan numbers below come from a debinarized copy of `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d`, which py3d cannot read directly, so they are not checked on `P:\`. Other cases were measured on mod vehicles (imported cars, a helicopter, quads ported from Arma 2).

## Hubs belong in the Geometry LOD

`wheelHub` resolves against the Geometry LOD (resolution `1e13`, a hub box of about 0.20 m) and the Memory LOD (`1e15`, one point), not against the visual `wheel_X_Y` selection. A port that leaves the hubs anywhere else does not spawn:

```text
ENTITY       : Load entity type '<Class>'
PHYSICS   (E): Won't simulate, wheel wheel_1_1_damper_land has no proper selection in geometry
```

`CreateObjectEx` returns null; the vehicle is not just wrong, it is absent.

| Model | `*_damper_land` in Geometry | LandContact LOD |
|---|---|---|
| A working test quad | 4, with faces and their `componentNN` | None |
| The vanilla sedan | 4 | None |
| A second working quad mod | 4 | None |
| A quad ported from Arma 2, which failed to spawn | 0 | Present, holding all four, each 1 point and 0 faces |

An Arma 2 MLOD has a LandContact LOD, and a port leaves the contact points there because the names match. A selection with one point and no faces cannot carry a `componentNN` either. Moving the four names onto geometry that already existed in the Geometry LOD, without adding a face, was enough: the quad spawned with four wheels. The `componentNN` rule itself is in `invariants-get-in-and-seats.md`; this is where it applies.

Before any game session, check that every `wheelHub` the config names exists in the Geometry LOD, with faces and both tags. Take the hub list from the model's own config, not from a hand-written list.

In a port the only geometry belonging to a wheel is often the whole wheel (0.198 by 0.599 by 0.599 m) instead of a hub box (0.20 by 0.22 by 0.22 m). Using it is honest, since inventing a small box changes the Geometry LOD's mass, but it leaves a collision component about three times larger on two axes. If the suspension behaves strangely or the vehicle feels anchored after the fix, suspect that size first.

## Hub height against the mounted tyre

Work out hub height from the radius of the wheel you mount, not the rip's rim. One coupe used the source rim's 0.3637 while mounting `CivSedanWheel` with `radius=0.34` (`P:\DZ\vehicles\wheeled\config.cpp:4762` to `:4778`): a 2.4 cm mismatch, the same order as its damper rest of -4.3 and -5.6 cm ("wheels slightly up"). That link is a hypothesis with numbers, not confirmed in game. Check on day one that the hub radius equals the mounted wheel's radius, or write down why not.

Vanilla parks the hub above the tyre radius, not level with it. The sedan's `wheel_*_damper_land` sits at +0.3627 against `radius=0.34` (`config.cpp:4778`), so hub height minus radius is +0.0227. A ported quad had its hubs at +0.3231 with a wheel of `radius=0.350149`, so -0.0271. The sign is the diagnosis: negative puts the wheels under the terrain at spawn and the settling suspension lifts the body, which looks to a player like a sync bug that "spawns sunk and fixes itself when someone gets on". Measured offline; the in-game confirmation is pending.

- Check the config `radius` against the wheel mesh first: measure the outer radius in the plane perpendicular to the spin axis (0.3501 and 0.3502 on that quad, so the config was right and the hub was wrong).
- Fix the origin, not the hubs. Moving the whole model keeps every body to hub relation, so the settled pose stays and only the spawn pose moves. Raising the hubs alone changes ride height and breaks a pose already accepted.
- Measure whether LODs are re-centred instead of assuming it. On that quad 10 of 12 LODs lacked `autocenter=0`, with bounding box centres 0.62 to 1.63 m off the origin, and the model still rendered aligned, so a global move was safe.

A hitch felt only by the driver comes from collision, not scripts: the driver's client solves the physics while a passenger interpolates, so smooth motion seen by a passenger proves nothing. Working cars use the tyre's PhysX sphere plus a small `wheel_*_damper_land` Geometry box (about 0.20 by 0.22 by 0.22 m) and no LandContact LOD. Require hub height minus mounted tyre radius to exceed both `Suspension.travelMaxUp` and `travelMaxDown`. A wheel-sized hub, or LandContact points left at the tyre plane, can strike the terrain on every bump. `ObstacleGenerator { carve=1; }` and visual face count do not explain it.

## Proxies against hubs

A faithful import and correctly placed pieces are different things. When a script assembles a model, each piece goes to a computed anchor (centroid, bounding box centre, a reference point); if that anchor is off, pieces sit wrong while every import check passes. On one car the 28 wheel proxies sat -0.240 m in X from their Memory hubs; on a helicopter, import fidelity was 12 of 12 within `3.2e-7` m and the seat anchor was still 583 mm off the source mesh.

Before calling an assembly good, measure every proxy's anchor against its real reference (the matching Memory point, or the source mesh position) and require the difference to be about zero. Fidelity, digest and structural diffs compare a piece with itself, not with where it belongs. Fix the single anchor; changing the pipeline transform moves everything that was already right. `autocenter=0` is a real, separate requirement (without it the engine re-centres LODs and moves collision 20 to 25 cm from the visual, `_shared/models/generated-model-rules.md`), but it does not cause or cure this; adding it to 18 proxy LODs on one car changed nothing.

The visual `wheel_X_Y` selection is the proxy's own triangle under a second name: on two cars it had the same centroid and bounding box as its `proxy:<path>.NNN` selection, and vanilla shows it as one face too.

- A check "proxy anchor to companion centroid equals 0" measures only the triangle's size: 0.131757 m for a 0.339 by 0.204 triangle, 0.000745 m for py3d's canonical `scale=0.001`, while against the real hub both read 0.000000 m. Point it at `wheel_X_Y_damper_land`.
- Triangle size bakes no scale. The frame comes from unit vectors (`derive_proxy_frame` in `scripts/tools/py3d/py3d/__init__.py`), and the sedan's binarized proxy matrix is orthonormal (each of `aside`, `up`, `dir` of length 1.000000). A 1 mm triangle and a 0.34 m one place the same wheel; a car shipped on `scale=0.001`. Do not "fix" a small triangle.
- The sedan puts the hub 0.106334 to 0.107333 m inboard of the wheel proxy, all of it in X. A hub on the proxy (0 m) is tighter than vanilla, not a defect.
- Split a difference by axis before tying it to another open problem. A 0.1318 m offset looked like a 0.136 m track error, but it was entirely in Y and Z (X exactly 0.000000 on all four wheels) while the track error was entirely in X.
- Read a check's verdict on the product from a run without its planted failures, then repeat it on a known-good model. Planted failures (turned or stripped models) interleave with product rows and read as product faults.

## Which way the wheel faces

A symmetric bounding box cannot tell; it passes before and after a 180 degree turn. Split the wheel's points by the sign of the mesh's shortest axis and compare the smallest radius in the perpendicular plane: the closed outer face reaches the hub (radius about 0), the open inner side starts near the rim. For a wheel whose axle runs along X, turn a reversed side by 180 degrees about Y, `(x, y, z)` to `(-x, y, -z)`, moving points and stored normals together. Calibrate which side is which on a wheel already known to mount correctly, never on the candidate, then repeat the measurement on the wheel extracted from the deployed PBO.

Measure the axle in the `.p3d` before setting the sign of a wheel's `angle1`; an offline check predicts reversed spin without a game session (`build-packaging-and-debug.md`, sections "ODOL and MLOD read model.cfg differently" and "Wheel spin direction lives in model.cfg").

## List every axle in an `Axles` override

A derived class that redeclares `class Axles: Axles` and lists one axle loses the other entirely, not just its values. Three drivetrain variants that declared only `class Rear: Rear` reported 2 wheels against 4 on the control in game, sat nose down (pitch -7 to -10 degrees against -0.3) and would not move; the player saw "the front wheels are buried and they do not turn". Add `class Front: Front {};` to each.

In the same override, `Clutch`, `Engine`, `Gearbox` and `Steering` were inherited without being declared, and those variants kept them. Inheritance works for children the engine looks up by name; it does not for children it enumerates, whose names are free, such as the axles under `Axles`. Vanilla lists both `Front` and `Rear` in every override, for example the `RearDrive` template (`config.cpp:494` to `:510`) and `OffroadHatchback` (`:1431` to `:1466`), so copying vanilla hides the gap.

Nothing offline catches it: `CfgConvert` parses the config without complaint and the script linter says nothing. Count what should be there in the engine, the wheel count of the spawned test vehicle, before handing a build to a person; a test setup that reports "fixture not ready" usually means exactly this.
