# Rules for a generated model

The rules every generated model must meet, and the LOD resolution values they use. Other files point at a rule by its heading here.

What vanilla models carry is cited from `P:\`. Winding, the axis map and the engine symptoms were measured on mod models, in game or offline; vanilla models on `P:\` are binarized, so those cannot be checked there.

## LOD resolution values

A LOD's resolution value is its type. The Tier 2 table is in `_shared/conventions/assets.md`, and what vanilla carries, with counts, is in `lods.md`. The values the generator writes:

| LOD | Resolution | Used for |
|---|---|---|
| Visual 0 (full detail) | `0.0` | Drawing |
| Visual 1, 2, 3 | `1.0`, `4.0`, `8.0` | Drawing at distance |
| Shadow volume, near and far | `10000.0`, `11000.0` | Only when asked for (below) |
| Geometry | `1.0e13` | Physics and the cursor raycast |
| Memory | `1.0e15` | Named points and axes |
| LandContact | `2.0e15` | Ground contact points |
| Roadway | `3.0e15` | Walkable surface |
| Hitpoints | `5.0e15` | Hit zones |
| View Geometry | `6.0e15` | Action cursor and occlusion |
| Fire Geometry | `7.0e15` | Bullets |

- Visual values only need to rise. The generator spaces them 0, 1, 4, 8; most vanilla models use 1, 2, 3, 4 (`P:\DZ\gear\camping\wooden_case.p3d`). Either works. The special values were read from the header of that same model.
- Never use `2e13` for Fire Geometry or `3e13` for View Geometry, as some Arma era guides say: the engine does not treat a LOD at those values as Fire or View Geometry. `4e13` is a real DayZ type, GeoPhys, carried by 8 vanilla models, and `2e13` is the buoyancy LOD of the vanilla boat (`lods.md`).
- A wrong value means the engine does not see the LOD as that type. When you edit an older model that already works, keep its values unless you have a checked reason to change them.

## Collision LODs

### Convex collision components

Every component of Geometry, Fire Geometry and View Geometry is convex and closed and named `ComponentNN`. A concave component breaks collision.

### Mass only on Geometry

Give the Geometry components mass, at least 10 so a character collides with them. Fire Geometry and View Geometry take no mass: a mass entry on any LOD but Geometry breaks the binarized centre of mass (`py3d-assembly-rules.md`, "Mass only on the Geometry LOD"; `named-properties.md`).

Fire Geometry thickness matters as well: glass that is too thick becomes bulletproof.

### `autocenter=0` on every collision LOD

Measured on mod models: without `autocenter=0` on Fire Geometry, View Geometry, Roadway, Hitpoints or LandContact, the engine recentres that LOD on its bounding box and moves it away from the visual mesh by half its height, typically 20 to 25 cm in Y. Bullets pass through, a stacking hologram falls to the ground, and the action cursor misses the object. Find it with `lod.properties.get("autocenter") != "0"` on any collision LOD; fix it with `lod.properties["autocenter"] = "0"` on all of them and write the file back.

Vanilla does not need it everywhere. 2,730 of the 8,256 models under `P:\DZ\` store an `autocenter` property (value `0` in 2,723), and 2,169 store it once: in `P:\DZ\gear\camping\wooden_case.p3d` and `P:\DZ\gear\books\book_kniga.p3d` that copy is in Geometry only, while `P:\DZ\gear\camping\fence.p3d` stores it once per LOD, seven times. Setting it on every collision LOD is this pipeline's safe default for placed objects, not an engine rule. Which models need the property at all (placed objects, not kits) is in `named-properties.md`; follow that file where the two differ.

### A penetration material on every collision face

Give every collision face a penetration `.rvmat`: `face.material = "dz\\data\\data\\penetration\\<surface>.rvmat"`, for example `wood_desk`, `metalplate` or `plastic` (each under `P:\DZ\data\data\penetration\` with its `.bisurf`). The `.bisurf` sets penetration, deflection and damage. Without it the `ObjIntersectFire` raycast hits the geometry but finds no surface: bullets pass through and there is no footstep sound. The wooden case stores `dz\data\data\penetration\wood_desk.rvmat` (`P:\DZ\gear\camping\wooden_case.p3d`). An empty `face.material` on any collision face is a failure, and `/dayz-p3d-audit` reports it (`dayz-p3d-audit/references/p3d-killers.md`).

### The per component winding check

After export, check every collision component for faces wound outward. Comparing the cross product with the stored normal (the audit's Check A) is not enough: it returns `UNIFORM_NON_FLIPPED` whenever the two agree, right or wrong.

- **Before you check.** Every non proxy face belongs to a `ComponentNN`, every component is closed and convex, and no face is degenerate. Short of that the check proves nothing.
- **The check.** For each non proxy face, `outward = face_centroid - component_centroid` and `cross_n = normalize(cross(v1-v0, v2-v0))`. `dot(outward, cross_n) < 0` is right. A face above zero is wound outward, and `ObjIntersectFire` treats it as a back face and misses it. Read every face, not most.
- **Symptoms**, all three at once: bullets pass through, the hologram falls to the ground when stacking, and nothing can be placed on top.
- **The fix.** `face.vertices.reverse()` on the faces that read outward and only those, `proxy:*` faces excluded, with their stored normals set as `p3d-killers.md` section 1 says. A component wound outward reads outward on every face and is reversed whole; a healthy component in the same LOD is left alone. Never reverse a collision LOD to match the visual LOD (`dayz-p3d-audit/references/winding-absolute-check.md`). The visual LOD has its own test, because its stored normals drive lighting while its winding drives culling.
- **What runs it.** Nothing in this pipeline, and not `audit_p3d.py`. `check_face_winding` in `py3d-shape-checks.md` compares winding with stored normals on `model.lods[0]` only, which is Check A's question; on a model whose first LOD is Memory it finds nothing. The loop under "When to reverse faces" in `py3d-axis-map.md` reverses every face of every LOD, which is right only to undo a reversal of the whole model. Measured offline on 2 m test boxes: reversing every face of a LOD with one healthy and one outward component moves the fault onto the healthy one.

## Visual LODs, memory and selections

- **Shadow LOD.** It must be slightly smaller than the visual LOD, or the object looks fully shaded. No vanilla model has one (no resolution from 10000 to 19999 in the headers of the 8,256 models under `P:\DZ\`), so add one only when the user asks (`lods.md`).
- **Memory points** are single vertices, never edges or faces. An animation axis is exactly two points.
- **Named selections match across LODs**: the same name in the visual, Geometry, Fire Geometry and View Geometry LODs wherever the part must move or be found.
- **Texture paths end in `.paa`**, never `.png` or `.tga`. Generate `.png`, then convert with `/dayz-pack-texture`.
- **Visible faces need a real `.paa`.** A procedural `#(argb,...)` face texture binarizes to section flags `0x0000C000` and the engine never draws that section, while drawn sections carry `0x0002C000` (opaque) or `0x0002C100` (alpha). Check it in the section table of the packed ODOL, not in the MLOD (`_shared/vehicles/animation-bake-and-odol-sections.md`, "Check new geometry by its ODOL section").
- **`model.cfg` class names match file names**: `class MyMod_Object` for `MyMod_Object.p3d`.
- **Read every `.p3d` back with py3d** after writing it.

## The Blender to DayZ map

Blender Z up to DayZ Y up is a reflection. Map every point and normal of every LOD through `(x,y,z)` to `(x,z,y)`, keep the face order and negate the normals; `py3d.blender_to_dayz(model)` does all three. FBX through Blender and GLB or glTF through Blender take the same map. The rule per source, the in-game results and the chirality check are in `axes-and-winding.md`.

## Attachments and proxies

### The three parts of an attachment

An attached item shows only when all three exist: a proxy face and selection in the parent's visual LODs, the proxy `.p3d` that the selection names, and a `CfgNonAIVehicles` class that ties the slot to the proxy model. With one missing the attachment is there in the inventory but invisible. Vanilla's plank proxy class is `Proxysingle_plank` (`P:\DZ\gear\camping\config.cpp:13405`). Since 1.30 also put the proxy triangle in View Geometry, so a dedicated server does not fall back to the parent's origin (`dayz-1-30-models.md`). More in `memory-and-selections-authoring.md`, `model-config-and-packing.md` and `proxies.md`.

### Proxy names

A proxy selection is `proxy:<path to the proxy model>.NNN`, with a three digit index; its face sets the attached model's position and facing. Write the path without `.p3d` (`memory-and-selections-authoring.md`). Vanilla stores both forms: of 17,891 proxy names in the models under `P:\DZ\`, 147 keep `.p3d` (for example in `P:\DZ\structures\military\airfield\mil_aircraftshelter.p3d`). Index `001` is the most common and `000` appears 529 times; `P:\DZ\gear\camping\fence.p3d` uses both.

## Wheels

### Wheel proxy memory points

A wheel proxy `.p3d` needs five points in its Memory LOD: `ce_center`, `ce_radius`, `boundingbox_min`, `boundingbox_max` and `invview`. PhysX builds the wheel collider from them; without them it falls back to the proxy's Geometry LOD, often a hub cube of about 0.20 m on generated wheels. Then `wheelPresent=N` but `contact=0`, the suspension ray misses the ground once the body lifts more than about 10 cm, the bounce grows, and the log ends with `Will delete object with !finite or outside world coords`. Measured on a mod quad whose wheels bounced, and matched against the vanilla cars: Y vertical and radial, X along the axle, Z radial with min and max deliberately swapped. Copy the points as they are and scale them; do not undo the Z swap. The full anatomy is in `dayz-p3d-audit/references/vehicle-checks.md` and `_shared/vehicles/vehicle-structural-parity.md`. Write them with the py3d in `scripts/tools/py3d/`, which guards the old py3d 1.0.0 write traps (`_shared/py3d-mlod-notes.md`).

### The wheel slot selection in Fire Geometry

For PhysX to seat a wheel (`WheelCountPresent()>0`), the selection named by `CfgSlots <wheel slot> selection` must exist in the body's Fire Geometry and hold the wheel proxy faces, not only in the visual LODs. Use one name for all three roles: visual proxy selection, Fire Geometry proxy selection and `CfgSlots` `selection`. With it only in the visual LODs the slot works as inventory but the wheel never simulates: `WheelCountPresent()=0` while `WheelCount()=N`, no traction, no spin, steering still animates, and no log error. Measured on a mod quad that reported `wheelPresent=0`. The offline check is in `dayz-p3d-audit/references/vehicle-checks.md`; the mechanism is in `_shared/enscript/depth/vehicle-scripting.md`.

- Item attachment proxies (a battery, a headlight) can stay in the visual LODs; wheel and suspension slot proxies also go in Fire Geometry at the same positions.
- Vanilla agrees: on the four cars checked each wheel proxy name is stored 7 to 9 times in a model with 5 to 7 visual LODs, and `P:\DZ\vehicles\wheeled\civiliansedan\civiliansedan.p3d` stores `sedanwheel.001` 7 times with 6 visual LODs.
- On that quad, adding the missing Fire Geometry proxies was needed but did not alone make the wheels roll; something else was also wrong. Add them, and keep looking if the wheel still does not simulate.

## Parts inside other parts

Recompute a part derived from a container's shape (a liquid surface, a layer of contents in a tray) from each LOD's simplified container, never from the full detail one, or it pokes through the simpler walls. Check that every vertex of the inner part lies inside that LOD's wall at its height, with a render of the LOD chain read from the `.p3d`, plus a deliberate leak as a control. This is a pipeline rule, not checked in game.
