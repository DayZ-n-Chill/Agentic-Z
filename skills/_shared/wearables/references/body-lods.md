# The LODs of a new body, and a see-through hole

Covers which LODs a new humanoid body (a custom infected, survivor or NPC) needs, how each was built on a working custom infected, how to model a hole one can see through (a torso cavity), and why size cannot come from a scale call.

How to read the marks: a `P:\` path with a line number was opened and checked in vanilla. A fact marked **Measured** was measured on the giant infected test build (a custom infected at about 1.2 times vanilla size with a see-through torso cavity), in Blender or in game, and cannot be checked on `P:\`. A note marked **engine** describes behavior no vanilla file shows.

The rig, the weights and the export of the visual LOD are in `body-rigging.md`. The class, the inherited AI and the damage zones the model must keep are in `skills/_shared/ai/custom-infected.md`. LOD types and their resolution values in general are in `skills/_shared/models/lods.md` and the table in `skills/_shared/conventions/assets.md` (View Geometry `6.0e+15`, Fire Geometry `7.0e+15`); use those DayZ values, not the Arma 3 ones.

## The LODs

| LOD | What it holds | On the giant infected build (**Measured**) |
|---|---|---|
| Visual | The rendered mesh, skinned by bone selections (`body-rigging.md` section 6), with any hole or other detail | One visual LOD with the body and an internal ribcage in one point and face pool |
| Geometry | Closed and convex, mass at least 10 | One hull with the named property `class = "man"`, not skinned. `man` is a vanilla value of `class` (`skills/_shared/models/named-properties.md`) |
| Fire Geometry | What bullets hit; its component names are the ones the inherited `DamageZones` list (`componentNames[]` with `Head` and `Neck` at `P:\DZ\characters\zombies\config.cpp:239`) | Skinned to the bones, with a `dmgzone_spine` selection and the vanilla penetration material `P:\DZ\data\data\penetration\meatbones.rvmat` on its faces |
| View Geometry, LandContact | As for any model (`skills/_shared/models/lods.md`) | Both present |
| Memory | The bones and points the inherited config names (`skills/_shared/ai/custom-infected.md`, "What the new model has to keep"; `skills/_shared/models/memory-points.md`) | Points built from the bone positions of the rig |

Stage every vanilla file a LOD names (the penetration `.rvmat` above) into the build, or binarize embeds it empty (`worn-models.md`, "Build").

## A hole one can see through

- **Visual.** Model an interior tunnel: a closed surface whose faces look into the hole. It is the most robust route. The alternative is double-sided geometry, each face twice, once per direction. A per-face "both sides" flag is no route: Binarize drops the MLOD face flags, and faces flagged `0x20000` stayed see-through in game (**Measured** on vehicles, `skills/_shared/vehicles/rip-import.md`, the single-sided interior entry).
- **Geometry.** It must be closed and convex, and a torso with a hole is not convex. Either split it into convex pieces as numbered `ComponentXX` selections, or keep the collision solid and ignore the hole. The collision LOD does not have to match the visual LOD.
- **Fire Geometry.** Keep it solid unless shots should pass through the hole, which needs more components for little gain. With a solid Fire Geometry, bullets that cross the visual hole still hit. That is a design decision; tell the user.
- **Damage zones.** A remodelled torso keeps taking zone damage as long as the components the zones list are still in the model (`skills/_shared/ai/custom-infected.md`).
- **Weighting the cavity.** Thin internal geometry (ribs, a spine) defeats automatic weights; weight it by height along the spine (`body-uv-bake.md`, section 7). Envelope weighting suited the cavity better than a weight transfer from a solid body (`body-rigging.md`, section 2).

## Size is baked into the mesh

- `GetScale` and `SetScale` exist on every entity (`P:\scripts\1_core\proto\enentity.c:447` and `:448`), but **engine:** they do not work on characters, and the collision box does not follow a scale.
- There is no character `scale` key in `CfgVehicles`. The only route is to bake the size into the mesh on the same skeleton; Geometry and Fire Geometry are built at that size too, so collision matches.
- How far a baked size may move from vanilla before the inherited animations deform it is in `canonical-bind.md` and `skills/_shared/ai/custom-infected.md`, "A bigger body does not reach further".

## Order of work

1. Mesh: generated or edited from a humanoid base, conformed to the rig's proportions (`body-rigging.md` section 3), with any hole modelled as a tunnel.
2. Rig and weight it (`body-rigging.md`), at its final baked size.
3. LODs as in the table above: Visual, a solid convex Geometry, Fire Geometry, View Geometry, LandContact, Memory.
4. Unwrap and bake (`body-uv-bake.md`), then the textures and `.rvmat` (`skills/_shared/textures/`).
5. Config under `ZombieMaleBase` or `ZombieFemaleBase` (`skills/_shared/ai/custom-infected.md`) and a `model.cfg` with the character skeleton.
6. Run the offline winding gate (`check_dayz_winding.py` in `/dayz-model-tools`), build with `/dayz-build-pbo`, then test in game with `/dayz-launch-test`: animations, foot sliding, collision, hits, spawning.
