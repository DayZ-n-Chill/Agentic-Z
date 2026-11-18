# Fixing a generated model

Which cause and which fix go with the faults a generated model shows most often. The rules named here are headings of `generated-model-rules.md`. The causes were found on generated mod models tested in game and are not checked on `P:\` unless a row cites a vanilla file. For a model with no collision or no actions, run `/dayz-p3d-audit` first and follow its decision tree; this file covers what the generator got wrong.

## Orientation and winding

| Symptom | Cause | Fix |
|---|---|---|
| The model spawns on its side or upside down | The Z up to Y up map was not applied | Apply "The Blender to DayZ map": `(x,y,z)` to `(x,z,y)`, normals negated, face order kept, for FBX, Blender geometry, and GLB or glTF brought through Blender. A glTF read without Blender is Y up and takes the map `axes-and-winding.md` derives for it |
| Textures show on the inside of faces and the outside is invisible | The winding does not match the map, for example faces reversed after the reflection | Apply the map with the face order kept. For glTF read without Blender: bake node transforms, reverse mirrored instances, then its own reflection. Check with the offline checks and on an asymmetric feature in game |
| Check A reads `UNIFORM_NON_FLIPPED` | Nothing by itself: Check A compares the cross product with the stored normals and cannot tell inward from outward. A correct export reads it (both inward), and so does an inside out one with both outward | Decide with a direction check: the absolute winding check of `/dayz-p3d-audit` (signed volume, negative is right) or "The per component winding check". Fix only what it reports, as below |
| Bullets pass through, the hologram falls when stacking, and nothing can be placed on top, all at once | Faces wound outward on the collision LODs; Check A cannot see it | Run "The per component winding check" on Geometry, View Geometry and Fire Geometry and reverse only the non proxy faces it reads outward, with their normals set as `dayz-p3d-audit/references/p3d-killers.md` section 1 says. For Roadway's walkable faces use the absolute winding check instead (right reads `cross_Y < 0` from above). Leave the visual LOD alone and check again |

## Reading Check A

Never reverse faces on the Check A label alone; on a correct export that turns it inside out.

- **Collision component.** The wrong side is outward. Reverse only the faces the per component check reads outward, never the whole LOD.
- **Visual LOD.** First turn back the faces wound against their neighbours (Check B, `dayz-p3d-audit/references/winding-diagnostics.md`, "From Check B to fix"; py3d reports them as `WARN_WINDING_EDGE_INCOHERENT`). Then read the signed volume of each closed shell, never the sum over the LOD: negative for a solid seen from outside, positive for a room seen from inside (`dayz-p3d-audit/references/winding-absolute-check.md`). Open and double sided parts are not settled by the sign. Measured offline on 2 m test boxes: reversing a closed room seen from inside keeps 100% agreement and leaves py3d silent, and a face turned together with its normal inside a solid keeps the solid's volume negative and is caught only by `WARN_WINDING_EDGE_INCOHERENT`.
- **Every face of every LOD.** Only to undo a reversal of the whole model, such as `P3D.transform()` with a negative determinant map whose flip back was skipped.

## Textures and materials

| Symptom | Cause | Fix |
|---|---|---|
| Textures look like TV static | `random()` per pixel instead of coherent noise | OpenSimplex FBM in several layers (`_shared/textures/procedural-textures.md`) |
| Textures look flat or artificial | One noise layer, no wear | 5 or 6 layers: base, flow, grain, micro, wear, sparse detail |
| Textures stretch or sit wrong | UVs missing or exported wrong | Run Smart UV Project before export and check the UV layer exists |
| The normal map looks inverted | Blender bakes green up; DayZ `_nohq` is green down | Flip green on a Blender bake. This is tool knowledge, not stated by a file on `P:\` |
| Damage shows only as a tint, not cracks or wear | `Stage3` of the `_damage.rvmat` uses a procedural `color()` instead of the vanilla overlay | Use the vanilla overlay as the wooden case does (`_shared/textures/rvmat-mod-patterns.md`, "Damage that shows wear, not only a tint") |

## Geometry, collision and LODs

| Symptom | Cause | Fix |
|---|---|---|
| The model looks blocky | No bevel or subdivision | Bevel (width 0.002, 3 segments) and Subdivision (level 2) before export |
| Collision does not work | A Geometry component is not convex | "Convex collision components" |
| A character walks through it | Geometry components have no mass | At least 10 on the Geometry components ("Mass only on Geometry") |
| The `.p3d` is corrupt or crashes Object Builder | Vertex and face data disagree | Read every `.p3d` back with py3d after writing |
| The engine ignores a LOD | Wrong resolution value | "LOD resolution values"; the values must be exact |
| Bullets pass through | No penetration `.rvmat` on the collision faces | Set one on every face of Geometry, Fire Geometry, View Geometry, Hitpoints and Roadway, then look for `penetration` in the strings of the `.p3d` ("A penetration material on every collision face") |
| The stacking hologram falls to the ground; nothing can be placed on top | `autocenter=0` missing on the collision LODs | Add it to Fire Geometry, View Geometry, Roadway, Hitpoints and LandContact as well as Geometry ("`autocenter=0` on every collision LOD") |

## Animation and attachments

| Symptom | Cause | Fix |
|---|---|---|
| An animation does not play | Axis points missing or misnamed | Two Memory points under the axis name (`_shared/animation/device-model-cfg.md`) |
| The attachment is in the inventory but invisible | One of the three proxy parts is missing | "The three parts of an attachment" |

## Vehicles

The detail is in the vehicles pack (`_shared/vehicles/README.md`) and in `dayz-p3d-audit/references/vehicle-checks.md`; vehicle work goes to `dayz-vehicle-specialist`.

| Symptom | Cause | Fix |
|---|---|---|
| The vehicle launches or bounces at spawn, then is deleted (`!finite or outside world coords`) | A `#Mass#` tag on a LOD other than Geometry, often all zeros from py3d writing `point.mass = 0.0`. Binarize bakes that LOD's mass, so the ODOL has its centre of mass at `(0,0,0)`, zero inertia, and the vehicle spawns below ground | Strip `#Mass#` from every LOD but Geometry (`point.mass = None`, never `0.0`) and check the binarized centre of mass (`py3d-assembly-rules.md`, "Mass only on the Geometry LOD"). Many convex Geometry components, all with mass and `autocenter=0`, is good practice but not the fix for this |
| It steers but does not roll, or sinks (`contact=0`) | Wheel hubs inside the chassis hull, or the wheel proxy's Memory points incomplete | Wheel wells in Geometry so the hubs sit outside the hull, and the five points of "Wheel proxy memory points" |
| It floats, rides too low or scrapes its belly | Wheels placed wrong: tyre bottom below the origin, chassis floor below the wheel centre | Raise the wheels and the chassis floor to the ride height together (`vehicle-checks.md`) |
| The engine does not start, or drowns at spawn | No `CarBattery` or `SparkPlug`, or no `drown_engine` memory point | The "won't start" rows of `_shared/vehicles/vehicle-parts-and-start.md`, and the Diag menu (Win+Alt, then Game, Vehicles, Simulation) |
| `unknown animation source damper`, or wheels do not spin or steer | Broken wiring between `model.cfg` and config (`AnimationSources`, `animRotation`, `animTurn`, `animDamper`) | "How the three files wire together" in `_shared/vehicles/vehicle-config-crew-lights-sounds.md` |
