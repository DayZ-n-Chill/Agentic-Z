# Canonical bind

Why a body that looks fine at rest deforms under animation: what the engine binds a character mesh against, the three ways a mesh misses that bind, the infected bind and its shorter bone list, the mirrored mesh fault, the vanilla body route, and the offline checks that hold. The rigging steps are in `body-rigging.md`, the export in `body-export.md`.

Results from a custom test infected body were measured in game and cannot be checked on `P:\`.

## What the engine binds against

The engine skins the mesh against the canonical bind of its own skeleton, the shared rig's bone positions, not a bind taken from your mesh (measured in game). The inherited vanilla animations deform correctly only when the mesh matches that bind three ways:

- **Scale.** About vanilla size; the rig's `Male_body` is about 1.8 m. A mesh baked oversize is bound against the 1.8 m positions, the limbs swing from the wrong pivots, and it deforms badly under animation, not only with foot sliding. A test infected at 2.277 m (about 1.27 times) did this, and scaling it to about 1.8 m removed the worst of it. A bigger animated character that still deforms cleanly needs its own skeleton with a scaled bind, which no vanilla example shows.
- **Facing and handedness.** Facing the same way as the rig and not mirrored. A 180 degree error about the vertical makes the character face and walk backward and deform; a mirror makes limbs fling (below). The map that gets both right is `(x, z, y)` (`body-export.md`, section "The export map").
- **Proportions and joint positions.** The mesh's elbow, knee, shoulder and wrist must sit at the canonical bone positions. A uniform scale keeps the canonical proportions but cannot match a mesh with its own, so bones land off the anatomy and limbs overextend under animation. That needs a proportion conform (`body-rigging.md`, section "Conform the mesh to the bind pose").

The tell is a body fine at rest that breaks only when animating. At the bind pose the skinned output equals the rest mesh whatever the weights are, so "looks right standing" proves nothing about the bind.

To check offline, measure per bone the distance from the bone head to the weighted centroid of its vertices. A large distance means the bone does not sit on the anatomy it drives, and that limb will deform. On the test infected `LeftUpLeg` gave 0.33 m against a 0.22 m bone, and the hands 0.20 m against 0.06 m.

## Survivors and infected bind to different skeletons

`SurvivorBase` names `player_testing.xob` (`skeletonName` at `P:\DZ\characters\data\config.cpp:158`; the whole block is in `characters.md`). Infected do not skin against the player rig. `ZombieBase` carries its own `enfanimsys` block (`P:\DZ\characters\zombies\config.cpp:71`):

| Key | Value | Line |
|---|---|---|
| `meshObject` | `dz\characters\zombies\z_hermit_m.xob` | `P:\DZ\characters\zombies\config.cpp:73` |
| `graphname` | `dz\anims\workspaces\infected\infected_main\infected.agr` | `:74` |
| `defaultinstance` | `dz\anims\workspaces\infected\infected_main\infected_main.asi` | `:75` |
| `skeletonName` | `hermit_newbindpose.xob` | `:76` |

Counting `<bone` entries per skeleton in `P:\DZ\anims\cfg\skeletons.anim.xml`:

| Skeleton | Starts at | Bones |
|---|---|---|
| `hermit_newbindpose.xob` | `:2` | 95 |
| `player_testing.xob` | `:110` | 172 |

With case ignored, 81 player bones are missing from the infected list, and 4 infected bones are missing from the player list (`character_nulls`, `floor_feet`, `floor_fingers`, `lookat`). The 81 are:

- the face rig: 34 `face_*` bones plus `eyeleft` and `eyeright`;
- the finger base bones `lefthandring`, `lefthandpinky`, `righthandring` and `righthandpinky` (the infected list keeps the numbered joints, for example `LeftHandRing1` at `P:\DZ\anims\cfg\skeletons.anim.xml:54`);
- the IK helpers (`lefthandik`, `righthandik`, `righthandik_helper`, `rightaimik_helper`, `lefthandiktarget`, the `*forearmdirection*` and `*handorigin` bones);
- every weapon bone (`weapon_bone_01` to `weapon_bone_06`, `weapon_root`, `magazine`, `trigger`, `bolt`, the bullet bones, the holsters) and the two camera helpers;
- six other helpers: `lefttoebase_end`, `righttoebase_end`, `marker`, `opponent`, `universal1` and `universal2`.

What follows for a custom infected body:

- A mesh with weights on bones the infected bind lacks (face, finger bases, IK) is resolved wrong at run time and deforms, even at idle. Conform and weight it to the 95 bone list. The other route is to override `skeletonName` and `meshObject` in `enfanimsys` to `player_testing.xob`; it is a known community fix for headgear and face stretch on infected, not checked on `P:\` and not tested in game.
- Do not confuse the two bone lists. The `enfanimsys` bind (95 bones on infected, 172 on the player) is a different layer from the skeleton a model's `model.cfg` declares (about 159 bones in a debinarized vanilla infected). Match the `.xob` the engine binds, not only the `model.cfg` skeleton.
- Weights outside the 95 are a quick first check, not the whole answer. The test infected had all 42 of its weighted bones inside the 95 and still deformed, because its bone heads sat 0.10 to 0.22 m off the anatomy.

## The Blender deform test is a false gate

Only the game, or Buldozer, proves deformation. Posing the rig FBX armature in Blender and measuring edge stretch does not reproduce what the engine does: on the test infected, new weights and two different conforms brought the Blender stretch from 34 times down to 6 times while the body in game stayed just as broken, at idle and when animating.

- **Why it misleads.** The engine skins against its own skeleton, with its bind and inverse bind matrices and the skeleton your `model.cfg` declares. It never uses the FBX armature you posed in Blender.
- **Odd at rest and at idle means a bind or skeleton mismatch, not weights.** When the character looks wrong while barely moving, the `model.cfg` skeleton is wrong or the rest pose is not the engine bind. New weights will not fix it.
- **The reference is a debinarized vanilla character**, a model under `P:\DZ\characters\zombies\` run through an external ODOL to MLOD converter (this repo ships none). Copy its `model.cfg` skeleton exactly and conform and weight your mesh to its bind. Never hand write a 114 bone hierarchy and assume it matches. The debinarized model is reliable for the skeleton, named selections, `model.cfg` wiring and weights, but not for the visual LOD vertex positions of character bodies, which the conversion corrupts.
- **Deform gates, in order:** a spawn in game, which is the real one; then Buldozer, which uses the engine's own skinning. The Blender pose test only answers "does a limb move at all".
- **Offline checks that do hold:** the winding gate, the scale factor taken from the armature span, the facing check, and a side view of the rest pose.

## The mesh can be left and right mirrored

A body whose `model.cfg` skeleton matches a debinarized vanilla infected exactly (159 bones, `isDiscrete=0`, the same parents and order, which keeps the leg chain `leftupleg`, `propthighleft`, `leftleg`) can still fling its arms back and up, the same at idle and when animating. The cause is a mesh reflected in X against the skeleton: the geometry of a `left*` selection sits where the canonical `right*` bone lives, so the animation drives it about a pivot roughly two limb widths away.

The reflection comes from the export map. Blender is right handed and DayZ is left handed, so every determinant +1 map (`(x, z, -y)`, `(-x, z, y)`) mirrors the mesh, and the face reversal it then needs hides the mirror.

**The test, offline.** On your own MLOD, take each bone selection's vertex X relative to the spine centre. The DayZ bind puts `left*` on +X and `right*` on -X, the same across shoulder, hip and arm (use bones with many vertices), and the front on -Z. The opposite side means mirrored. Check the front too, because a mirror plus a 180 degree turn also puts `left*` on +X. Take the +X reference from the worn frame (`worn-models.md`) or from the rig's `Male_body` (vertices weighted to `LeftArm` at x = +0.22), never from the visual LOD of a debinarized vanilla model.

**The fix.** Two options; prefer the second.

- **Swap the left and right selection names** in every LOD (`leftarm` with `rightarm`, all sub bones and fingers, and the `l*` and `r*` memory points). Geometry, winding and normals stay the same. The mesh stays visually mirrored, which is fine for a symmetric humanoid, but an off-centre detail lands on the wrong side.
- **Undo the reflection in the geometry:** negate X on every vertex, reverse the winding and drop the swap. This also clears a side effect of the reflection, single sided faces culled from angles the upright animation never shows, such as a ragdoll corpse that goes invisible from one side. With the Blender source, export again with `(x, z, y)` instead of patching the `.p3d`; that export is checked in game (`body-export.md`, section "Chiral check in game"), the patch is not.

## When conform and new weights stall

A body with the right shape at rest whose shoulders and arms overextend when animated:

1. When the mesh does not match the skeleton, conforming and weighting again cut the deformation by about 30 to 45 % and never remove it.
2. The robust way out is to rebuild on a vanilla, well rigged body, which has no deformation by construction, and graft only the distinctive parts onto it: a torso hole, the look and texture, the baked scale.
3. For an editable vanilla body with positions and weights, use the rig FBX's `Male_body` in Blender, not the ODOL to MLOD converter, which corrupts the visual LOD positions of character bodies (a bounding box that is not human, a span about 2.5 times the height). `Male_body` has correct positions and clean groups: 7,499 vertices, a box of 1.406 by 0.390 by 1.799 m (the world size `autofit-on-official-rig.md` measures), none without a weight, at most 4 influences. Import with `import_scene.fbx`, take the mesh whose name contains `body`, read `matrix_world @ v.co` and `v.groups`, and take bone heads from the armature (`bone.head_local`).
4. Read weights back from an MLOD with the py3d constructor (`body-export.md`, section "Building the model with py3d").

## Judging deformation offline

Deformation under animation can be judged offline with hierarchical linear blend skinning against the canonical bind: `v' = sum(w_i * G_i * B_i^-1 * v)`. The bind `B_i = T(head_i)` uses the real bone heads (Memory LOD pivots, or a bone table taken from the rig), and `G_i` is forward kinematics over the real `model.cfg` hierarchy (`skeletonBones[]`), turning each bone about its own head and passing the motion to its children. It shows the overextension that otherwise takes a build and a game session to see.

This does not contradict the false gate above. The Blender armature, its pose test and any single pivot rotation bind again to positions that are not canonical; hierarchical skinning with the bind at the canonical heads and the `model.cfg` hierarchy does not.

- Run it with a negative control: a capsule centred on each bone segment, weighted 100 % to that bone. Under the same pose it must bend cleanly; if the judge breaks the control too, it over-reports and is useless.
- Report two things together: less overextension under animation (edge stretch), and the rest silhouette kept (the mean radius of a region's vertices to its main bone's axis, original against conformed). Tuning only the first lets silhouette changes through: by eye an arm of 0.140 m against variants of 0.124 m and 0.113 m was obvious, and none of three offline numbers caught it.
- With the bind taken as bone head positions, the judge assumes no bind rotation. It is not faithful to a rig whose bind has real bone orientations, such as a vanilla body, where the chain explodes (edge stretch above 400 times); use full bind matrices there.
- It is a filter before the game, not checked in numbers against the engine. The final gate is still the eye in game. This repo ships no judge script; build one from the method above.
