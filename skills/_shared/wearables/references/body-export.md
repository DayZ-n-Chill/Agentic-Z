# Exporting a rigged body to `.p3d`

Covers writing a body rigged in Blender (`body-rigging.md`) to an MLOD `.p3d` with py3d, so its vertex groups become weighted named selections: the axis map, winding and normals, the py3d rules, the offline checks and the chiral check in game. Why the body still deforms after a clean export is in `canonical-bind.md`.

The route that works headless is a direct write with the py3d DayZ fork in `scripts/tools/py3d/`; no Object Builder window is needed, and py3d carries the weights faithfully. Blender and py3d behaviour is tool knowledge, not checked on `P:\`; results from a test infected body were measured in Blender or in game. This repo ships no script for the dump, the build or the offline check; write them from the steps below.

## Dump from Blender

`mesh.calc_loop_triangles()` handles quads and n-gons. Per mesh, dump the world space vertices (`matrix_world @ v.co`), the triangles (loop triangle vertex indices), the UV per loop, the normal per corner (`mesh.corner_normals[loop].vector`, turned by `matrix_world.to_3x3()`) and a dense vertices by bones weight matrix from `v.groups`. Save it as `.npz`. Confirm the weights sum to 1.0 and no vertex is without a weight before going on.

## The export map

Map `(x, y, z)` in Blender to `(x, z, y)` in DayZ, determinant -1, for every point and normal of every LOD and for the bone and memory points.

- The rig in Blender is a body that is not mirrored: front -Y, anatomical left +X, Z up. `LeftArm` head x = +0.16; `LeftToeBase` head 0.135 m in -Y from `LeftFoot`; `Male_body` vertices weighted to `LeftArm` at x = +0.22, toe vertices at y = -0.10 (measured with both FBX importers).
- The armature's `matrix_world` is a rotation of +90 degrees about X, and its inverse `(x, z, -y)` returns to the FBX file's own frame: Y up, front +Z, left +X. That frame is right handed; read as DayZ numbers, which are left handed, it is a mirrored body facing backwards.
- The DayZ bind is a body that is not mirrored in a left handed frame: front -Z, left +X (the worn frame in `worn-models.md`).
- So Blender to DayZ is `(x, z, -y)` then `z` to `-z`, which is `(x, z, y)`: front -Y goes to -Z and left stays on +X. Every determinant +1 map lands the body mirrored. In game, `(x, z, -y)` makes a body face and walk backward, and `(-x, z, y)` turns it round but leaves it mirrored, with the limbs flinging back and up until the left and right selections are swapped.

## Winding and normals

Do not reverse the faces. Under `(x, z, y)` the Blender face order lands in the MLOD convention by itself (cross product inward), and the shading normals are negated because MLOD stores them inward. The old "reverse every visual face" was right only under a determinant +1 map, where it hid the mirror.

- With py3d 1.8.0 or newer, build the model from the Blender space dump and call `py3d.blender_to_dayz(model)` once, before adding anything built in DayZ space. It maps every LOD, memory points included, keeps the face order and negates the normals.
- By hand: `P3D.transform(((1, 0, 0), (0, 0, 1), (0, 1, 0)))` maps points and normals and reverses every face because the determinant is negative; reverse them back and negate the normal pool.
- `py3d.BLENDER_TO_DAYZ` is the old `(x, z, -y)`, deprecated in 1.8.0 and kept as `py3d.ROT_X_NEG90`. It is not for this export.
- Gate winding and normals with the offline winding gate `check_dayz_winding.py` (it ships with `/dayz-model-tools`) or the winding check of `/dayz-p3d-audit`. A double sided Blender preview never shows DayZ's single sided culling. Never compare winding against a debinarized vanilla model: the converter's winding handling inverts the comparison.

## Building the model with py3d

- **Lowercase selection names.** Vanilla `.p3d` selections are lowercase (`leftarm`, `pelvis`, `spine3`); Blender groups are mixed case, so call `.lower()` on them.
- **Same objects for keys.** Alias `points = lod.points` before creating any `Face(lod.points, ...)` or `Vertex(...)`, and use `lod.new_selection(name)`. Selection point and face keys must be the very objects in `lod.points` and `lod.faces`, or their weight is silently dropped or `write()` raises "foreign key".
- **Weight bytes.** py3d stores a weight `w` between 0 and 1 as `round((1 - w) * 255) + 1`; on reading, byte 1 is 1.0 and bytes 2 to 255 are `1 - (b - 1) / 255`. Below about 0.002 this overflows to 256 and raises `ValueError: bytes must be in range`. Clamp: `w >= 0.995` becomes the integer 1, `0.005 <= w < 0.995` stays a float, and `w < 0.005` is dropped.
- **No empty selections.** A twist or helper bone whose every weight fell below the cutoff gives an empty selection. Skip any bone selection with no members.
- **No mass on the visual LOD.** Set `point.mass = None` there; mass belongs only on the Geometry LOD.
- **Internal geometry.** A ribcage or similar is merged into the same visual LOD point and face pool, and its spine selections merge by name with the body's. How to weight it is in `body-uv-bake.md`, section "Weighting internal geometry".
- **Hidden selection.** Add a `camo` selection holding every body point and face for `hiddenSelectionsTextures[]`; vanilla infected declare exactly that (`hiddenSelections[]` at `P:\DZ\characters\zombies\config.cpp:96`). An internal mesh with its own texture gets a second one. Selections that are not bones (`camo`, proxies) are ignored by the skeleton.
- **Reading weights back.** Read an MLOD with `py3d.P3D(open(path, 'rb'))`, which fills `selection.points = {Point: weight}`. An old debinarized MLOD may keep the selection names with empty `.points`.

The selections in the `.p3d` must be a subset of `skeletonBones[]` in `model.cfg`, or the mesh explodes. A misnamed bone logs `Bone X doesn't exist in skeleton ...` in the RPT and that bone does not animate. Which skeleton name vanilla models carry is in `worn-models.md`, section "Skeleton: `DayzTemporarySkeleton`".

## Checking the export offline

Compare with a debinarized vanilla character. The models under `P:\DZ\characters\zombies\` are ODOL, so this needs an external ODOL to MLOD converter, which this repo does not ship. Check that:

- the file reads back;
- every bone selection name is in the vanilla bone set, with no orphan selections;
- no point is without a bone weight and no vertex has more than 4 influences;
- the bounding box is Y up with vanilla like proportions;
- about 0 % of faces are flipped, and fractional weights are present and read back;
- the `left*` centroids sit on +X and the front on -Z (toe and face vertices in -Z from the foot and neck). "Left and right on opposite X" alone also passes a mirrored export, and facing plus side rule out a determinant +1 map only while the left and right selections were never swapped by hand.

## Chiral check in game

Winding gates, the bounding box and the facing test cannot see a mirror once the left and right selections have been swapped. This test can.

1. Export the character with `(x, z, y)`, faces in Blender order, negated normals and no left and right swap. Add one marker: an "F" in relief on the chest, weighted 100 % to `spine3`. Build the old recipe once more with the same marker as the control.
2. Spawn both and a vanilla character with the same yaw, and put the camera in front of them.
3. Pass: the new build faces the camera like the vanilla one, no limb flings back or up over 30 s of idle and one attack, the "F" reads correctly, and an off-centre detail sits on the side it has in Blender (the character's left is screen right when it faces you). The control shows the "F" mirrored and the detail on the other side.
4. The lit side of the body is bright.

Measured on the test infected, rebuilt three ways from one dump with the "F":

| Build | Result |
|---|---|
| The export rule through `py3d.blender_to_dayz()` | Solid, "F" reads correctly, lit like a vanilla infected and the player |
| The same with the normals turned back outward | Solid, "F" reads correctly, lit inverted |
| The old determinant +1 recipe | Solid, "F" mirrored, lit inverted |

Binarize gives all three builds vanilla's winding, but only the build with inward normals keeps vanilla's relation between stored normals and winding in the ODOL (agreement 0.2 %, vanilla infected 0.3 to 0.4 %, the outward builds 99.8 %). So store the normals inward. With AI on, the export rule build walked about 18 m and attacked the player with its limbs in place, the same moves a vanilla `ZmbM_SoldierNormal` makes; a static build kept its limbs in place over about 80 s of idle.

## Bone indices since 1.30

Up to 1.29, `skeletons.anim.xml` gave each bone a numeric `index`, and 250 was treated as a hard global cap. Bohemia's 1.30 modding changelog says the 250 bone limit is gone, the global bone index comes from the bone name instead of the XML, and most of that XML is unused: only the `lod` attribute is read, plus bones missing inside the `.xob` (changelog, not checked on `P:\`).

What `P:\` shows:

- The `hermit_newbindpose.xob` block still has leftover `index` values, for example `Pelvis` with `index = "10"` (`P:\DZ\anims\cfg\skeletons.anim.xml:8`). Never copy those numbers into a custom skeleton.
- Later skeletons name bones only. Their one `index` is `EntityPosition` with `index = "0"`, for example in `ovis_gmelini_skeleton.xob` (`:988`) and `canis_familiaris_dobermann_skeleton.xob` (`:1049`).

## Symptom to cause

| Symptom | Likely cause | Read |
|---|---|---|
| The whole mesh explodes in game | A named selection that is not in `skeletonBones[]`, or the wrong skeleton name | "Building the model with py3d"; the `model.cfg` skeleton |
| `Bone X doesn't exist in skeleton ...` in the RPT | A bone name typo (case, underscore) | `P:\DZ\anims\cfg\skeletons.anim.xml` |
| Faces and walks backward, proportions fine | Export with `(x, z, -y)`, which sends the rig's front to +Z | Export again with `(x, z, y)`, not `(-x, z, y)` |
| A limb flings back or up at idle; rest pose fine, skeleton matches vanilla | Mirrored export (any determinant +1 map) | `canonical-bind.md`, section "The mesh can be left and right mirrored" |
| A corpse goes invisible from one angle | Single sided faces of a reflected mesh | Undo the reflection (`canonical-bind.md`); a selection swap alone leaves it |
| Textures on the inside, see-through from outside | Faces not in the MLOD inward order: a determinant +1 map without a face reversal, or a determinant -1 map with one | "Winding and normals" |
| Solid, but dark on the sunlit side and lit in the shade | Normals stored outward; rule out the material and `_nohq` too | "Winding and normals"; the winding gate or `/dayz-p3d-audit` (agreement near 0 % means normals against the winding) |
| Colour in game is "camo" or black and grey facet noise, and stays without `_nohq` | A corrupt bake of the colour map | `body-uv-bake.md`, section "Bake from the pose before the conform" |
| Green, grey or brown patches that survive replacing `_co` and removing `_nohq` | A texture in the wrong `.rvmat` stage for the shader; vanilla infected sample the environment texture in `Stage7` (`P:\DZ\characters\zombies\data\hermit.rvmat:74`) | Compare stage by stage with a vanilla `.rvmat` of the same shader (`_shared/textures/rvmat-stages.md`); prove the mesh with a clay render first |
