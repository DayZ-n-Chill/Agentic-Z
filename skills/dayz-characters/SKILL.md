---
name: dayz-characters
description: "Guides importing and authoring DayZ humanoids on the vanilla character bases (infected, survivors, human NPCs): rigging a custom mesh to the vanilla skeleton, bind pose, weights, baked scale, UV and normal bake, character LODs, config inheritance, the survivor ragdoll and in-game deformation, and runs an offline winding and normal gate on the source .p3d. Use for a custom zombie, infected, survivor or NPC, a giant infected, or when a character mesh explodes, stretches, has spiky vertices, faces backward, is mirrored, renders inside-out or see-through, is lit inverted, slides its feet or does not animate."
argument-hint: "<model.p3d> [--py3d <py3d-folder>]"
---

<!-- skill-dir-note -->
> **Path note:** `<skill-dir>` in commands below is the absolute path of this skill's folder. When the agent loads this skill the harness exposes the skill's base directory; substitute it before running. Sibling skills are reached via `<skill-dir>\..\dayz-X\`.

# /dayz-characters

Custom humanoids in DayZ (infected, survivors, human NPCs) are built by reusing the vanilla character chain, not from `EntityAI`. A class that inherits `ZombieMaleBase` or `ZombieFemaleBase` gets the skeleton, every infected animation and the AI driver through inherited config, so the only thing to author is a new mesh. The real cost of the project is one step: rigging that mesh to the vanilla character skeleton so the inherited animations deform it correctly.

This skill is the character layer. It holds the rig workflow, the bind rules, the character bake traps, the config recipe and one script, an offline gate that catches an inside-out or wrongly lit model before a build. Generic model, texture, animation and build work belongs to the skills and packs named in the table below.

Follow `skills/_shared/dayz-conventions.md`. The gate script reads one source file and starts no DayZ tool, so it does not run `/dayz-preflight`; packing and in-game testing go through `/dayz-build-pbo` and `/dayz-launch-test`, which do.

## How to run the winding gate

Run it on the source MLOD after building the `.p3d` and before every pack:

```cmd
python "<skill-dir>\check_dayz_winding.py" path\to\model.p3d
python "<skill-dir>\check_dayz_winding.py" path\to\model.p3d --py3d path\to\py3d
```

| Exit | Meaning |
|---|---|
| 0 | PASS: every closed shell of every visual LOD is wound inward and its stored normals agree. A PASS that left open or flat parts unscored says so |
| 1 | A model defect, with the fix printed in order: winding first, then normals |
| 2 | Invalid input, a binarized ODOL file, a py3d that is not the DayZ fork, or a LOD with nothing measurable |

The gate needs the py3d DayZ fork, which lives at `scripts/tools/py3d/` in this repo. A PASS cannot see a mirrored export; check that on an asymmetric feature in game. Details, limits and the measured results: `references/winding-gate.md`.

Outside an agent session, `scripts\dayz\check-winding.bat` runs `check_dayz_winding.py` with the same arguments.

## Who owns each stage

| Stage | Owner | Notes |
|---|---|---|
| Generate or model the mesh | The ai-3d-to-dayz skill, or an external generator | Multi-view input and an A-pose or T-pose help the rig |
| Retopology to a low-poly manifold mesh | The ai-3d-to-dayz and dayz-model-pipeline skills | Generated retopology leaves non-manifold spots; clean them |
| Rig to the character skeleton | This skill | The expensive step: `references/character-rigging.md` |
| UV unwrap, normal and AO bake | This skill, with the dayz-texture-pipeline skill | Character traps: `references/character-uv-bake.md` |
| Textures `_co`, `_nohq`, `_smdi` and the `.rvmat` | The dayz-texture-pipeline skill; `skills/_shared/textures/` | |
| Character LODs | This skill, with the dayz-model-pipeline skill; `skills/_shared/models/lods.md` | `references/custom-infected-recipe.md` section 5 |
| `config.cpp` inheritance and `model.cfg` | This skill | `references/custom-infected-recipe.md` section 1 |
| Animation graph, skeleton deep dive, new clips | The dayz-animation-pipeline skill | Its `references/player-skeleton.md` is the bone catalog |
| Worn clothing on the character | The dayz-clothing skill; `skills/_shared/wearables/` | `references/worn-clothing-skeleton.md` |
| Winding and normal gate | This skill, then `/dayz-p3d-audit` | Before every pack |
| Pack and binarize | `/dayz-build-pbo` | |
| In-game test | `/dayz-launch-test`, `/dayz-gate` | Animations, foot sliding, collision, hits, spawning |

Vehicles and aircraft are other domains (the dayz-vehicles and dayz-aviation skills).

## Rules that decide the outcome

Each is explained, with the measurement behind it, in the reference named.

1. **The engine binds against its own canonical bind, not your mesh.** The mesh has to match it in scale (about 1.8 m), in orientation and handedness, and in joint positions. A mesh that is fine at rest and breaks only when animating has missed one of the three. `references/canonical-bind.md`
2. **An infected binds to `hermit_newbindpose.xob`, 95 bones, not the player's 172.** `ZombieBase` names it in `enfanimsys` (`skeletonName` at `P:\DZ\characters\zombies\config.cpp:76`). Weight a custom infected to that list, which has no face rig, finger base, IK or weapon bones. `references/canonical-bind.md`
3. **A Blender pose test is not a deform gate.** It showed a clean result three times while the game stayed broken. Only an in-game spawn or Buldozer validates deformation; odd at idle as well as in motion means a bind or skeleton mismatch, not weights. `references/canonical-bind.md`
4. **Export from Blender with `(x, y, z)` to `(x, z, y)`, faces in Blender order, normals negated.** Every determinant +1 map mirrors the mesh, and reversing the faces afterwards hides the mirror. With py3d 1.8.0 or newer that is one call, `py3d.blender_to_dayz()`. `references/character-rigging.md` section 6
5. **Bake the armature scale before automatic weights.** Otherwise every vertex lands on `Pelvis`. Then at most 4 influences per vertex, no vertex without a weight, and no vertex weighted to both a left and a right bone. `references/character-rigging.md` sections 1 to 4
6. **Size is baked into the mesh, and it fights the bind.** Runtime scaling does not work on characters. A mesh far from vanilla size deforms under animation; about 1.27 times was already too much. `references/custom-infected-recipe.md` section 3
7. **Inheriting the vanilla animation block is free; shipping new character animations is not.** Not checkable on `P:\`: only one mod that changes player or creature animation graphs can be loaded at a time. Warn the user before a plan ships custom character animations. `references/custom-infected-recipe.md` section 1
8. **Worn clothing compiles with the skeleton name `DayzTemporarySkeleton`.** With `OFP2_ManSkeleton` it renders as a rigid block above the player. `references/worn-clothing-skeleton.md`
9. **A survivor body keeps its `ragdoll` line (1.30).** `SurvivorBase` binds `DZ/characters/bodies/human.ragdoll` (`ragdoll` at `P:\DZ\characters\data\config.cpp:160`). `references/character-ragdoll.md`

## Quick triage

| Symptom | Likely cause | Where |
|---|---|---|
| Posing the rig moves nothing; the mesh will not deform | Armature scale not applied before bone-heat, so the weights collapsed onto `Pelvis` | `references/character-rigging.md` section 1 |
| The whole mesh explodes in game | A named selection that is not in `skeletonBones[]`, or the wrong skeleton name | `references/character-rigging.md` section 6; check the `model.cfg` skeleton |
| Spiky or pinched vertices | Vertices without a weight, or a selection with no weight | `references/character-rigging.md` section 4 |
| `Bone X doesn't exist in skeleton ...` in the RPT | A bone name typo (casing, underscore) | The bone catalog of the dayz-animation-pipeline skill |
| Limbs lag or float during animations | Mesh not in the canonical bind A-pose, or baked-scale drift | `references/character-rigging.md` section 3; `references/custom-infected-recipe.md` section 3 |
| Animations do not play at all | Not inheriting `ZombieMaleBase` and its `enfanimsys`, or the animation wall | `references/custom-infected-recipe.md` section 1 |
| A bigger character whose collision is wrong | Scaled at run time instead of baked | `references/custom-infected-recipe.md` section 3 |
| The character faces or walks backward | Determinant +1 export `(x, z, -y)`: it sends the rig front to +Z, and the bind faces -Z | Export again with `(x, z, y)`, not `(-x, z, y)`, which turns it round but mirrors it. `references/character-rigging.md` section 6 |
| Limbs overextend or stretch under animation, fine at rest | Mesh scale or proportions differ from the canonical bind | `references/canonical-bind.md`; proportion conform in `references/character-rigging.md` section 3 |
| Deforms wrong in game although the Blender pose test looked clean | The Blender armature is not the engine skeleton; the pose test is a false gate | `references/canonical-bind.md`; gate in game or in Buldozer |
| Looks wrong at rest and idle, not only when walking | Bind or skeleton mismatch (`model.cfg` not equal to vanilla, or rest pose not the engine bind), not weights | `references/canonical-bind.md`: copy a debinarized vanilla infected's `model.cfg` skeleton and match its bind |
| The skeleton matches vanilla, the rest pose is a sane A-pose, and a limb still flings back or up, at idle and in motion | The mesh is left and right mirrored against the skeleton: `left*` geometry sits where the `right*` bone is. Cause: a determinant +1 export map | `references/canonical-bind.md`, "The mesh can be left and right mirrored". Export again with `(x, z, y)`, or undo the reflection; swapping the selection names only relabels the mirror |
| A custom infected deforms even at idle; the mesh was rigged to the full player skeleton | An infected binds to the 95-bone `hermit_newbindpose.xob`, with no face, finger base or IK bones | `references/canonical-bind.md`: weight to the 95-bone list, or override `skeletonName` in `enfanimsys` |
| A corpse or ragdoll goes invisible from one angle | Single-sided faces of a reflected mesh, culled at grazing angles the upright animation never reaches | Undo the reflection (negate X and reverse the winding; with the Blender source, export again with `(x, z, y)`). A selection swap alone leaves it |
| The whole mesh renders flat, like paper | A conform or warp collapsed the depth, for example a thin-plate-spline conform to near-coplanar bone midpoints | Conform in X and Z only and keep Y; always look at the side render of the rest pose. `references/case-log.md` |
| In-game colour is "camo" or black and grey facet noise, and stays without `_nohq` | A corrupt high to low bake: the noise is in the `_co` texture, not the normal map | Open the baked `_co` image and look. `references/character-uv-bake.md` section 2 |
| Green, grey or brown patches that survive replacing `_co` entirely and removing `_nohq` | The `.rvmat`, not the textures. On the giant infected build the landscape photo `env_land_co.paa` showed on the body and the fix was in the `.rvmat`. Do not conclude from this that an environment map must use `uvSource="none"`: vanilla infected materials sample that texture in `Stage7` with `uvSource="tex"` (`P:\DZ\characters\zombies\data\hermit.rvmat:74`). Suspect the texture sitting in the wrong stage for the shader | Compare the `.rvmat` stage by stage with a vanilla one that uses the same shader (`skills/_shared/textures/rvmat-stages.md`), and convert each stage's texture to PNG with ImageToPAA to look at it. A Blender preview of `_co` plus normal map hides the other stages. First prove the mesh clean with a clay render of the `.p3d` geometry with no textures |
| Solid, but dark on the sunlit side and lit in the shade | First suspect: shading normals stored outward (the old determinant +1 recipe, or an export by Rule 12 of the dayz-model-pipeline skill whose normals were negated back). Rule out the material and `_nohq` too | Run the gate, or read the stored sign with the absolute winding check of dayz-p3d-audit (agreement near 0 % means normals against the winding). If the normals point outward, negate the normal pool. `references/winding-gate.md` |
| Textures on the inside; the model is see-through from outside | The faces are not in the MLOD inward order: a determinant +1 map without a face reversal, or a determinant -1 map with one. Double-sided previews hide this | Export with Rule 12: `(x, z, y)`, faces in Blender order, normals negated. `references/character-rigging.md` section 6 |
| Worn item floats above the player as a rigid block, or breaks into rigid pieces | Skeleton name `OFP2_ManSkeleton` in the clothing `model.cfg`, or a mesh built facing +Z | `references/worn-clothing-skeleton.md` |

## Check before you write

Character config and bone names are easy to half-remember. Before writing a class name, a base, a property or a named selection, look it up in vanilla (`P:\DZ\characters\`, with the infected in `P:\DZ\characters\zombies\config.cpp`) or in the reference that cites it. Bone names must match the vanilla list exactly: check them against `P:\DZ\anims\cfg\skeletons.anim.xml` or the rig FBX, never from memory.

Each reference says at its top how to read its marks. In short: a `P:\` path with a line number was opened and checked; a result marked with a test build (the giant infected build, the worn armour build) was measured in Blender or in game on that build and cannot be checked on `P:\`; Blender, py3d and changelog statements are marked as such.

## DayZ 1.30

- **What changed.** `SurvivorBase` binds a `.ragdoll` file. The infected `.agr` is an index over `.agf` subgraphs. New female military and Nasdara infected classes. A new mind state, `MINDSTATE_COWER`. Human `Skinning` no longer gives `Lard`. Sandstorm protection through `DEF_DUST_PARTICLE_BREATH` and `DEF_DUST_PARTICLE_EYES`.
- **What breaks.** Custom infected animation workspaces made for 1.29. Recipes that expect human `Lard`. `EmoteManager.ForceSurrenderState` still works but is marked obsolete (`P:\scripts\4_world\classes\emotemanager.c:1255`); use `PlayerBase.SetSurrenderState` and `IsSurrendered`.
- **Migration.** Keep inheriting `ZombieMaleBase` or `ZombieFemaleBase`, or a 1.30 female soldier base. Save a custom infected workspace again in Workbench 1.30. Keep or override the `ragdoll` path when replacing a survivor body. Write no bone `index` values in `skeletons.anim.xml`.

Details and the vanilla lines: `references/dayz-1-30-characters.md`, `references/character-ragdoll.md`.

## References

| Question | File |
|---|---|
| How do I rig a custom mesh to the vanilla skeleton in Blender and export it with weights? What does the chiral in-game check look like? | `references/character-rigging.md` |
| Why does my rig deform under animation when it looks fine at rest? What does an infected bind to? Why is the Blender pose test not a gate? Is my mesh mirrored? How do I judge deformation offline? | `references/canonical-bind.md` |
| Which class do I inherit, how do I make it bigger, how do I model a see-through hole, which LODs does a character need, what does each part cost? | `references/custom-infected-recipe.md` |
| How do I unwrap and bake normal and AO maps for a rigged character without rainbow noise, black blotches or dark AO? | `references/character-uv-bake.md` |
| What does the winding gate read, how do I apply its fixes, what does a PASS not cover? | `references/winding-gate.md` |
| How is the 1.30 survivor ragdoll bound and what is in `human.ragdoll`? | `references/character-ragdoll.md` |
| What did 1.30 change for infected and survivors? | `references/dayz-1-30-characters.md` |
| Why does my worn clothing float or explode, and which skeleton name and frame does a worn model need? | `references/worn-clothing-skeleton.md` |
| Which failure taught which rule? What was tried on a real import? | `references/case-log.md` |
| What changes on Linux? | `references/linux-notes.md` |

Related packs: survivor classes, body parts and the character list are in `skills/_shared/wearables/references/characters.md`; infected behaviour, mind states and a custom infected's AI are in `skills/_shared/ai/custom-infected.md` and `skills/_shared/ai/creatures.md`. For the whole mod loop (config, signing, a local server, the Workshop) use the dayz-mod-dev skill together with `/dayz-build-pbo` and `/dayz-launch-test`.
