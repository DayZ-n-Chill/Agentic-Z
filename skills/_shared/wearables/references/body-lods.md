# LODs of a new body

Covers which LODs a new humanoid body (a custom infected, survivor or NPC) needs, how to model a hole one can see through, such as a torso cavity, and why size cannot come from a scale call.

The rig, weights and export of the visual LOD are in `body-rigging.md` and `body-export.md`. The class, the inherited AI and the damage zones the model must keep are in `_shared/ai/custom-infected.md`. LOD types and resolution values in general are in `_shared/models/lods.md` and the table in `_shared/conventions/assets.md` (View Geometry `6.0e+15`, Fire Geometry `7.0e+15`); use those DayZ values, not the Arma 3 ones. The "Working example" column was built on a test infected about 1.2 times vanilla size with a see-through torso, and checked in Blender and in game, not on `P:\`.

## The LODs

| LOD | What it holds | Working example |
|---|---|---|
| Visual | The rendered mesh, skinned by bone selections (`body-export.md`), with any hole or other detail | One visual LOD with the body and an internal ribcage in one point and face pool |
| Geometry | Closed and convex, mass at least 10 | One hull with the named property `class = "man"`, not skinned; `man` is a vanilla value of `class` (`_shared/models/named-properties.md`) |
| Fire Geometry | What bullets hit; its component names are the ones the inherited `DamageZones` list (`componentNames[]` with `Head` and `Neck` at `P:\DZ\characters\zombies\config.cpp:239`) | Skinned to the bones, with a `dmgzone_spine` selection and the vanilla penetration material `P:\DZ\data\data\penetration\meatbones.rvmat` on its faces |
| View Geometry, LandContact | As for any model (`_shared/models/lods.md`) | Both present |
| Memory | The bones and points the inherited config names (`_shared/ai/custom-infected.md`, section "What the new model has to keep"; `_shared/models/memory-points.md`) | Points built from the rig's bone positions |

Stage every vanilla file a LOD names, such as the penetration `.rvmat` above, into the build, or binarize embeds it empty (`worn-models.md`, section "Build").

## A hole one can see through

- **Visual.** Model an inner tunnel: a closed surface whose faces look into the hole. It is the most robust route. The other is double sided geometry, each face twice, once per direction. A per face "both sides" flag is no route: Binarize drops the MLOD face flags, and faces flagged `0x20000` stay see-through in game (measured on vehicles, `_shared/vehicles/rip-textures-and-materials.md`).
- **Geometry.** It must be closed and convex, and a torso with a hole is not convex. Split it into convex pieces as numbered `ComponentXX` selections, or keep the collision solid and ignore the hole. The collision LOD does not have to match the visual LOD.
- **Fire Geometry.** Keep it solid unless shots should pass through the hole, which needs more components for little gain. With a solid Fire Geometry, bullets that cross the visual hole still hit. That is a design decision; tell the user.
- **Damage zones.** A remodelled torso keeps taking zone damage as long as the components the zones list are still in the model (`_shared/ai/custom-infected.md`).
- **Weighting the cavity.** Thin internal geometry (ribs, a spine) defeats automatic weights; weight it by height along the spine (`body-uv-bake.md`, section "Weighting internal geometry"). Envelope weighting suits the cavity better than a transfer from a solid body (`body-rigging.md`, section "Bind with automatic weights").

## Size is baked into the mesh

- `GetScale` and `SetScale` exist on every entity (`P:\scripts\1_core\proto\enentity.c:447` and `:448`), but they do not work on characters and the collision box does not follow a scale (**engine**).
- There is no character `scale` key in `CfgVehicles`. The only route is to bake the size into the mesh on the same skeleton, and to build Geometry and Fire Geometry at that size so collision matches.
- How far a baked size may move from vanilla before the inherited animations deform it is in `canonical-bind.md` and `_shared/ai/custom-infected.md`, section "A bigger body does not reach further".

## Order of work

1. Mesh: generated or edited from a humanoid base, conformed to the rig's proportions (`body-rigging.md`, section "Conform the mesh to the bind pose"), with any hole modelled as a tunnel.
2. Rig and weight it at its final baked size (`body-rigging.md`), then export it (`body-export.md`).
3. LODs as in the table: Visual, a solid convex Geometry, Fire Geometry, View Geometry, LandContact, Memory.
4. Unwrap and bake (`body-uv-bake.md`), then the textures and `.rvmat` (`_shared/textures/`).
5. Config under `ZombieMaleBase` or `ZombieFemaleBase` (`_shared/ai/custom-infected.md`) and a `model.cfg` with the character skeleton.
6. Run the offline winding gate (`check_dayz_winding.py` in `/dayz-model-tools`), build with `/dayz-build-pbo`, then test in game with `/dayz-launch-test`: animations, foot sliding, collision, hits, spawning.
