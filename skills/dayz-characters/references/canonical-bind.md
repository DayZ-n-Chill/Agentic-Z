# The canonical bind: why a rig that looks fine at rest deforms under animation

Covers what the engine binds a character mesh against, the three ways a mesh can miss that bind, the infected bind and its shorter bone list, why a Blender pose test proves nothing, the mirrored-mesh fault, and the offline checks that do hold.

How to read the marks: a `P:\` path with a line number was opened and checked in vanilla. "Giant infected build" marks a result measured on a custom giant infected test build, with the date; those results cannot be checked on `P:\`.

## The invariant

The engine skins the mesh against the canonical bind of its own skeleton (the shared rig's bone positions), not a bind derived from your mesh (giant infected build, in game, 2026-06-24). The inherited vanilla animations deform correctly only when the mesh matches that bind in three ways:

- **Scale.** About vanilla size; the rig's `Male_body` is about 1.8 m. A mesh baked oversize is bound against the 1.8 m positions, limbs swing from the wrong pivots, and the result is gross deformation under animation, not just foot sliding. The giant infected build at 2.277 m (about 1.27 times) did this; rescaling to about 1.8 m removed the catastrophic deformation.
- **Orientation and handedness.** Facing the same way as the rig, and not mirrored. A 180 degree error about the vertical makes the character face and walk backward and deform. A mirror makes limbs fling (see "The mesh can be left and right mirrored against the skeleton" below). The export map `(x, z, -y)` shipped backward; `(-x, z, y)` turned it round but mirrored it. Both have determinant +1. The map that gets facing and side right is the determinant -1 map `(x, z, y)`, Rule 12 of the dayz-model-pipeline skill (corrected 2026-10-01; derivation in `references/character-rigging.md` section 6).
- **Proportions and joint positions.** The mesh's anatomical elbow, knee, shoulder and wrist must sit at the canonical bone positions. A generated mesh has its own proportions. A uniform scale fit (`references/character-rigging.md` section 1) keeps canonical proportions but cannot match a mesh with other proportions, so bones land off the anatomy and limbs overextend and stretch under animation. That needs a proportion conform (section 3 there), not just the arm angle conform.

**The tell: fine at rest, breaks only when animating.** At the bind pose the skinned output equals the rest mesh whatever the weights are, so "looks right standing" proves nothing about the bind. Only an animation, or a deform test that poses real bone transforms, shows a scale, orientation or proportion mismatch.

**Offline diagnostic.** Per bone, measure the distance from the bone head to the weighted centroid of its vertices. A large distance means the bone does not sit on the anatomy it drives, and that limb will deform. Giant infected build: `LeftUpLeg` 0.33 m against a 0.22 m bone length, hands 0.20 m against 0.06 m.

## An infected binds to `hermit_newbindpose.xob`, a shorter bone list than the player's

Infected do not skin against the player rig. `ZombieBase`, which every infected class inherits, carries an `enfanimsys` block (`P:\DZ\characters\zombies\config.cpp:71`) that sets:

| Key | Value | Line |
|---|---|---|
| `meshObject` | `dz\characters\zombies\z_hermit_m.xob` | `P:\DZ\characters\zombies\config.cpp:73` |
| `graphname` | `dz\anims\workspaces\infected\infected_main\infected.agr` | `P:\DZ\characters\zombies\config.cpp:74` |
| `defaultinstance` | `dz\anims\workspaces\infected\infected_main\infected_main.asi` | `P:\DZ\characters\zombies\config.cpp:75` |
| `skeletonName` | `hermit_newbindpose.xob` | `P:\DZ\characters\zombies\config.cpp:76` |

The player's block names `player_testing.xob` instead (`skeletonName` at `P:\DZ\characters\data\config.cpp:158`).

Counting `<bone` entries per skeleton in `P:\DZ\anims\cfg\skeletons.anim.xml`:

| Skeleton | Starts at | Bones |
|---|---|---|
| `hermit_newbindpose.xob` | `P:\DZ\anims\cfg\skeletons.anim.xml:2` | 95 |
| `player_testing.xob` | `P:\DZ\anims\cfg\skeletons.anim.xml:110` | 172 |

Comparing the two name lists (case ignored), 81 player bones are missing from the infected list and 4 infected bones are missing from the player list (`character_nulls`, `floor_feet`, `floor_fingers`, `lookat`). The 81 are:

- the face rig: 34 `face_*` bones plus `eyeleft` and `eyeright`;
- the finger base bones `lefthandring`, `lefthandpinky`, `righthandring` and `righthandpinky` (the infected list keeps the numbered joints, for example `LeftHandRing1` at `P:\DZ\anims\cfg\skeletons.anim.xml:54`);
- the IK helpers (`lefthandik`, `righthandik`, `righthandik_helper`, `rightaimik_helper`, `lefthandiktarget`, the `*forearmdirection*` and `*handorigin` bones);
- every weapon bone (`weapon_bone_01` to `weapon_bone_06`, `weapon_root`, `magazine`, `trigger`, `bolt`, the bullet bones, the holsters) and the two camera helpers;
- six other helpers: `lefttoebase_end`, `righttoebase_end`, `marker`, `opponent`, `universal1` and `universal2`.

What follows for a custom infected:

- A mesh that carries weights on bones the infected bind lacks (face, finger bases, IK) is resolved wrong at run time and deforms, including at idle, because the infected graph's default pose is not your A-pose. Conform and weight the mesh to the 95-bone list. The other route is to override `skeletonName` and `meshObject` in `enfanimsys` to `player_testing.xob` to bring the missing bones back; this is a known fix for headgear and face stretch on infected (the config mechanism is the block above; the result is not checked on `P:\` and was not tested in game).
- Do not confuse the bone catalogs. The Enfusion `enfanimsys` bind (infected 95 bones, player 172) is a different layer from the skeleton a model's `model.cfg` declares (about 159 bones in a debinarized vanilla infected, as measured for the giant infected build). "Match the canonical bind" means the `.xob` the engine binds, not just the `model.cfg` skeleton. A mesh weighted to the full player bone list can still deform on an infected for this reason alone.
- Weights outside the 95 are a quick triage, not the whole answer. Compare the mesh's weighted bones with the 95 names parsed from `skeletons.anim.xml`. The giant infected build had all 42 of its weighted bones inside the 95 and still deformed: its fault was mesh against skeleton proportion (bone heads 0.10 to 0.22 m off the anatomy), not missing bones.

Since 1.30 the infected bind is unchanged. `infected.agr` is still the graph the block names, now an index over `.agf` subgraphs (`references/dayz-1-30-characters.md`), and the bone index rule changed (`references/character-rigging.md`, last section).

## The Blender deform test is a false gate

Only the game, or Buldozer, validates deformation (giant infected build, 2026-06-24). This was the most expensive lesson of that build.

Posing the imported rig FBX armature in Blender and measuring edge stretch does not reproduce the engine's deformation. Over three rebuilds (new weights, a thin-plate-spline conform, a depth-preserving conform) the Blender edge stretch fell from 34 times to 6 times while the in-game deformation stayed unchanged and broken, odd at idle and when animating. That was a false green three times over, and about 12 offline iterations that produced no in-game improvement.

- **Why it lies.** The engine skins against its own skeleton: its bind and inverse bind matrices, and the skeleton your `model.cfg` declares. It does not use the rig FBX armature you posed in Blender. When your `model.cfg` skeleton hierarchy or the mesh's authored rest pose differs from vanilla even slightly, the engine deforms wrong however clean the Blender pose test renders.
- **"Odd at rest and idle too" means a bind or skeleton mismatch, not weights.** At the true bind pose linear blend skinning returns the rest mesh whatever the weights are. When the character looks wrong while barely moving, the engine's bind is not your mesh's: the `model.cfg` skeleton is wrong, or the rest pose is not the engine bind. New weights will not fix it.
- **Ground truth is a debinarized vanilla character** (a model under `P:\DZ\characters\zombies\`, through an external ODOL to MLOD converter; this repo ships none). Its mesh is authored in the engine bind pose, with the exact selection structure and a `model.cfg` the engine accepts. Copy its `model.cfg` skeleton as it is and conform and weight your mesh against its bind. Do not hand-write a 114-bone hierarchy and assume it matches; on the giant infected build it did not. Limit: the debinarized model is reliable for the skeleton, named selections, `model.cfg` wiring and weights, not for visual LOD vertex positions, which the conversion corrupts for character bodies. For positions use the `Male_body` of the rig FBX (see "The vanilla body route" below).
- **Valid deform gates, in order:** an in-game spawn, which is the real one; then Buldozer, Bohemia's model viewer, which uses real engine skinning. The Blender armature pose test is good only for "does a limb move at all".
- **What did hold up offline:** the winding gate (`references/winding-gate.md`), the scale factor taken from the armature span, the orientation check, and looking at the rest pose from the side. A thin-plate-spline conform to near-coplanar bone midpoint targets flattened the mesh to paper, 2D in game, and the flat side view sat in the render folder a whole build cycle before anyone looked at it. Always look at the side and depth render of the rest pose.

## The mesh can be left and right mirrored against the skeleton

The root cause behind about eight sessions of "arm bind" trouble on the giant infected build (2026-06-25).

After the build's `model.cfg` skeleton was made to match a debinarized vanilla infected's byte for byte (159 bones, `isDiscrete=0`, exact parents and order, which restored the leg chain `leftupleg`, `propthighleft`, `leftleg`), the legs walked but the arms still flung back and up, the same at idle and when animating. The rest arms were a sane A-pose, so it was not pose or proportion. The whole mesh was reflected in X relative to the skeleton's left and right: the geometry of a `left*` selection sat where the canonical `right*` bone lives, so the inherited animation drove it about a pivot roughly two limb widths away, and the long lever swung the limb off even under tiny idle motion.

Root cause, found 2026-10-01: the reflection was the export map itself. Blender is right-handed and DayZ is left-handed, so every determinant +1 map (`(x, z, -y)`, `(-x, z, y)`) mirrors the mesh, and the face reversal it then needs hides the mirror. A generated or GLB mesh that went through a reflection and then had its winding reversed to render right side out is prone to this, and a 180 degree turn about Y can leave a reflection behind.

**The test, offline and decisive.** Debinarize a vanilla male, read the embedded skeleton bones and the visual LOD's per-vertex bone references, and compute each bone's vertex X relative to the spine centre. Vanilla puts `left*` on +X and `right*` on -X, the same across shoulder, hip and arm (use bones with many vertices; pelvis and hand centroids are noisy). The opposite side means mirrored. The conversion adds only the bounding centre and reverses winding; it does not negate an axis, so the comparison holds. One trap: a vanilla ODOL's named selections carry the bone names with empty vertex lists; the real membership is the per-vertex bone reference pairs, mapped through the sub-skeleton table to the skeleton bone index.

**The fix, two options; prefer the second.**

- **Swap the left and right selection names** in every LOD (`leftarm` with `rightarm`, all sub-bones and fingers, and the `l*` and `r*` memory points). Geometry, winding and normals stay byte-identical; only which bone each side binds to changes. It is the lowest risk and reversible. It leaves the mesh visually mirrored, which is fine for a symmetric humanoid; an off-centre detail lands on the mirror side.
- **Undo the reflection in the geometry:** negate X on all vertices, reverse the winding, and drop the swap. The mesh is then properly handed. It is a bigger change (run the winding gate and check the facing again), but it can also clear a side effect of the reflection: single-sided faces culled from grazing angles the upright animation never reaches, for example a ragdoll corpse that goes invisible from one angle. The swap alone leaves the reflection, so that culling can persist. On a `(-x, z, y)` export with reversed faces, undoing the reflection gives the Rule 12 positions and face order: `(x, z, y)` with the faces back in Blender order (Rule 12 also negates the normals). With the Blender source, export it again that way instead of patching the `.p3d`. The Rule 12 export was checked in game on a character (2026-10-02, `references/character-rigging.md` section 6); the patch was not.

## When conform and new weights stall: the vanilla body route

Case: the giant infected build (a generated infected at about 1.2 times, added 2026-06-28): correct shape at rest, limbs overextend at the shoulders and arms when animated.

1. When the mesh does not match the skeleton, conforming and weighting again have a ceiling. They cut the deformation by about 30 to 45 % and never remove it; the geometry stays far from the pivots.
2. The robust way out is to rebuild on a vanilla, well-rigged body, which has zero deformation by construction, and graft only the distinctive parts onto it (the torso hole, the look and texture, the baked scale). Use this when conform and new weights stall.
3. To get an editable vanilla body with positions and weights, use the `Male_body` of the rig FBX in Blender, not the ODOL to MLOD converter. The conversion corrupts visual LOD positions of character bodies (a bounding box that is not human, a span about 2.5 times the height); the ODOL's per-vertex bone references carry the weights but the positions are garbage. The FBX gives correct human positions and clean vertex groups (measured: `Male_body` 7,499 vertices, bounding box 1.4 by 0.28 by 1.8, none without a weight, at most 4 influences). Extract with `import_scene.fbx`, take the mesh whose name contains `body`, read `matrix_world @ v.co` and `v.groups`, and take bone heads from the armature (`bone.head_local`).
4. Reading weights back from an MLOD with py3d needs the constructor form; see "Reading weights back" in `references/character-rigging.md` section 6.

## Offline deform judge: hierarchical skinning with the canonical bind

The deformation under animation of a mesh rigged to the character skeleton can be judged offline, with no in-game build and no real animation clip, by a canonical hierarchical linear blend skinning: `v' = sum(w_i * G_i * B_i^-1 * v)`. The bind `B_i = T(head_i)` uses the real bone heads (the ones the engine uses: Memory LOD pivots, or a bone table derived from the rig). `G_i` is forward kinematics over the real `model.cfg` hierarchy (`skeletonBones[]`), rotating each bone about its own head and passing the motion to its children. This reproduces the real overextension (bones far from the anatomy make long arcs when rotated) that an in-game build takes hours to show. (Added 2026-07-14.)

This does not contradict the false gate above. The Blender armature, the Blender deform test and a single-pivot rotation are false gates because they bind again to positions that are not canonical. Sorted:

- False: the Blender armature, the Blender deform test, a single-pivot rotation.
- Holds: hierarchical skinning with the bind at the canonical heads and the `model.cfg` hierarchy.
- Required with it: a synthetic negative control. Build a capsule dummy centred exactly on each bone segment, weighted 100 % to that bone. Under the same pose it must bend clean. If the judge breaks the control too, the judge over-reports and is useless. The control turns "reproduces the deformation" into "tells good from bad".

Report two axes together. A conform judge needs (1) reduced overextension under animation (edge stretch) and (2) rest pose silhouette kept (the mean radius of a region's vertices to the head to tail axis of its dominant bone, original against conformed). Optimizing only the first lets silhouette distortion through: in a blind comparison the user's eye caught an arm thickness difference (original 0.140 m, variant A 0.124 m, variant B 0.113 m) that all three offline metrics missed.

Limits:

- With the bind taken as bone head positions, the judge assumes a bind with identity rotation. It reproduced a wrongly proportioned mesh's deformation (checked against the game) but it is not faithful to a rig whose bind has real bone orientations, such as a vanilla body: the kinematic chain explodes (edge stretch above 400 times). To validate a well-rigged body offline, use forward kinematics with full bind matrices, or deform in Blender with the native armature after reconciling the bind matrix that the FBX import otherwise breaks.
- It is an offline prefilter shown to tell good from bad (the negative control, and the false green case above). It is not validated in numbers against the engine. The final gate is still the user's eye in game, and the case that produced it had not been confirmed in game when this was written.

This repo ships no judge script; build one from the method above.
