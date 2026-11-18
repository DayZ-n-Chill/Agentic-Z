# Troubleshooting a generated model

Symptom, root cause and fix for the failures this pipeline produces most. Rule numbers refer to `generated-model-rules.md`. The causes and fixes were found on generated models tested in game and are not checked on `P:\`, except where a row cites a vanilla file. For a model that has no collision or no actions, run `/dayz-p3d-audit` first and follow its decision tree; this table covers what the generator got wrong.

## Orientation, faces and winding

| Symptom | Root cause | Fix |
|---|---|---|
| Model spawns sideways or upside down | The Z up to Y up conversion was not applied | Apply Rule 12's conversion, `(x,y,z)→(x,z,y)` plus negated normals, faces in their original order, to FBX and Blender geometry and to a GLB or glTF brought through Blender alike. A glTF read without Blender is Y up and takes the map that `axes-and-winding.md` ("GLB and glTF imports") derives. |
| Textures render on the inside of faces (the outside is invisible) | The winding does not match the measured recipe, for example faces reversed after the det=-1 map, as the former GLB path did | FBX, Blender, and a GLB or glTF brought through Blender: apply `(x,z,y)` plus negated normals, faces in their original order (Rule 12). A glTF read without Blender: bake node transforms, reverse mirrored instances, then apply its own det=-1 map. Verify with `check_face_winding` and the offline gates, and check chirality on an asymmetric feature. |
| Check A reads UNIFORM_NON_FLIPPED | Nothing by itself. Check A compares the cross product with the stored normals and cannot tell inward from outward (Rule 18): a correct Rule 12 export reads UNIFORM_NON_FLIPPED (both inward), and so does an inside out one with both outward, for example py3d `P3D.transform()` with the det<0 map, which reversed every face, with the flip back skipped | Decide with a direction check: the absolute winding check of `/dayz-p3d-audit` (signed volume by winding, negative is the production sign) or the per component outward check (Rule 18). Only when it reports the cross product on the wrong side: reverse those faces and negate their normals (both point away from the side meant to be seen: killer 1, Rule 12), then check again. See "Reading Check A" below for the cases. |
| Bullets pass through, the hologram falls to the ground when stacking, and items cannot be placed on top, all three at once | Rule 18: the cross product is outward on the collision LODs (the faces are not in the MLOD inward order of Rule 12). Check A cannot detect this; use the per component outward check | Run Rule 18's per component check on Geometry, View Geometry and Fire Geometry and reverse only the non proxy faces it reads outward, with their stored normals set as killer 1's **Fix** says; never a whole LOD to match the Visual LOD. Rule 18 scores closed, convex components only: for a Roadway LOD's walkable faces use item 4 of the absolute winding check instead (production reads `cross_Y < 0` from above). Leave the Visual LOD untouched. Verify that the check then reads every face inward in every component. |

### Reading Check A

Never reverse on the Check A label alone: on a correct export that yields UNIFORM_FLIPPED and an inside out model.

- **On a collision component** the wrong side is outward, and only the faces Rule 18 reads outward are reversed, never the whole LOD (killer 1).
- **On a Visual LOD**, first turn back the faces wound against their neighbours (Check B: `dayz-p3d-audit/references/winding-diagnostics.md`, "From Check B to fix"; py3d reports them as `WARN_WINDING_EDGE_INCOHERENT`). Then read the signed volume of each closed shell, never the sum over the LOD. Its wrong side is the side meant to be seen, so a negative signed volume is right for a solid seen from outside and a positive one for a room seen from inside (item 4 of the absolute winding check, `dayz-p3d-audit/references/winding-absolute-check.md`). An open or double sided Visual part is not resolved by this sign.
- **Every face of every LOD** only to undo a reversal of the whole model (the skipped flip back named in the cause column).

History of these two rows: *(Corrected 2026-10-02: the Check A row used to reverse every face whenever Check A read UNIFORM_NON_FLIPPED. Aligned 2026-10-02 with Rule 18 and item 4 of the absolute winding check: it then read "Only when it reports the cross product OUTWARD: reverse every face AND negate the normals (Rule 12: both inward), then check again." Read literally, that sentence reversed a closed Visual room seen from inside (signed volume +8 to -8), kept 100 % agreement and left py3d with no winding finding, measured offline 2026-10-03 with py3d 1.9.0 on a synthetic 2 m box. The Check B step and the reading per shell follow the order py3d's winding findings give for a Visual LOD (`_winding_steps` in py3d, `scripts/tools/py3d`): a face turned with its normal inside a closed solid left that solid's signed volume negative (-8 to -5.33) at 100 % agreement, and only py3d's `WARN_WINDING_EDGE_INCOHERENT` saw it, measured the same way. The three symptoms row used to say "Reverse vertex order on Geometry/Roadway/ViewGeometry/FireGeometry".)*

## Textures and materials

| Symptom | Root cause | Fix |
|---|---|---|
| Textures look like TV static | `random()` per pixel instead of coherent noise | Use OpenSimplex FBM with multi layer compositing (`_shared/textures/procedural-textures.md`) |
| Textures look flat or artificial | A single noise layer, no wear or variation | Add 5 to 6 layers: base, flow, grain, micro, wear, sparse details |
| Textures appear stretched or misaligned | UVs not generated or exported wrongly | Run Smart UV Project in Blender before export and verify the UV layer exists |
| Normal map looks inverted | DirectX against OpenGL convention | DayZ `_nohq` maps use the DirectX convention (green pointing down); Blender bakes OpenGL, so flip the green channel of a Blender bake. This is tool knowledge, not stated by a file on `P:\` |
| Damage shows only as a color tint, not as visible cracks or wear | The `_damage.rvmat` `Stage3` uses a procedural `color()` instead of the vanilla overlay texture | Use the vanilla overlay as the wooden case does (`_shared/textures/rvmat-mod-patterns.md`, "Damage that shows as cracks and wear") |

## Geometry, collision and LODs

| Symptom | Root cause | Fix |
|---|---|---|
| Model too polygonal or angular | No modifiers applied (bevel, subdivision) | Add Bevel (width 0.002, 3 segments) and Subdivision (level 2) before export |
| Collision doesn't work | Geometry LOD is not convex | Geometry LOD components must be convex hulls (Rule 1) |
| Character walks through the object | Geometry LOD components have no mass | Set a mass of at least 10 on the Geometry components (Rule 2) |
| `.p3d` file corrupt, or it crashes Object Builder | Inconsistent vertex and face data | Always read the `.p3d` back with py3d after writing (Rule 11) |
| LOD not recognized by the engine | Wrong resolution value | Check the LOD resolution table: the values must be exact |
| Bullets pass through the object | No penetration `.rvmat` on the collision LOD faces | Set `face.material = "dz\\data\\data\\penetration\\wood_desk.rvmat"` (or the fitting one) on every face in Geometry, Fire Geometry, View Geometry, Hitpoints and Roadway. Verify by listing the strings of the `.p3d` and looking for `penetration` (Rule 17) |
| Hologram falls to the ground when stacking on the object; items can't be placed on top | `autocenter=0` named property missing on the collision LODs | Add `lod.properties["autocenter"] = "0"` to all collision LODs (Fire, View, Roadway, Hitpoints, LandContact), not just Geometry. Without it the engine recenters the LOD on its bounding box, moving the collision mesh about 20 to 25 cm from the visual (Rule 16, with what vanilla stores) |

## Animation and attachments

| Symptom | Root cause | Fix |
|---|---|---|
| Animation doesn't play | Axis memory points missing or misnamed | Verify that 2 memory points exist in the Memory LOD under the axis name (`_shared/animation/model-cfg-device-examples.md`) |
| Attachment appears in the inventory but is invisible on the model | One of the three proxy parts is missing | Needed: proxy face and selection in the parent, the proxy `.p3d`, and the `CfgNonAIVehicles` class (Rule 14) |

## Vehicles

These rows point at vehicle material. The detail is in the vehicles pack (`_shared/vehicles/README.md`) and in `dayz-p3d-audit/references/vehicle-checks.md` (killers 11 to 13); vehicle work goes to `dayz-vehicle-specialist`.

| Symptom | Root cause | Fix |
|---|---|---|
| Vehicle launches or bounces at spawn, then is deleted (`!finite or outside world coords`) | A `#Mass#` tag on a LOD other than the Geometry LOD (often all zeros, written by py3d for `point.mass = 0.0`): binarize bakes that LOD's mass, so the ODOL has its centre of mass at `(0,0,0)` and zero inertia, and the vehicle spawns below ground | Strip `#Mass#` from every LOD except Geometry (`point.mass = None`, never `0.0`), then check the binarized centre of mass ("Mass only on the Geometry LOD" in `py3d-assembly-rules.md`; the correction under killer 13 in `dayz-p3d-audit/references/vehicle-checks.md`). Building Geometry as many convex components with mass on all of them and `autocenter=0` is construction practice (killer 13), not the fix for this symptom |
| Vehicle steers but does not roll, or sinks (`contact=0`) | Wheel hub inside the chassis hull, or the wheel proxy's Memory anatomy incomplete | Wheel wells in Geometry so the hubs sit outside the hull; the wheel proxy `.p3d` needs its five Memory points (killers 11 and 12; Rule 19) |
| Vehicle floats, rides too low, or its belly scrapes | Wheel vertical placement: tire bottom below the origin, chassis floor below the wheel centre | Raise wheels and chassis floor to the ride height triple together (killer 12) |
| Engine won't start, or drowns at spawn | Missing `CarBattery` or `SparkPlug` attachments, or a missing `drown_engine` memory point | The "won't start" rows of `_shared/vehicles/vehicle-config-and-modelcfg.md`, and the in-game Diag menu (Win+Alt, then Game, Vehicles, Simulation) |
| `unknown animation source damper`, or wheels don't spin or steer | The wiring between `model.cfg` and config is broken (`AnimationSources`, the `animRotation`, `animTurn` and `animDamper` sources) | "The wiring chain" in `_shared/vehicles/vehicle-config-and-modelcfg.md` |
