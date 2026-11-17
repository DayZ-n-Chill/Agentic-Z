# Custom infected recipe: config, size, torso hole and LODs

Covers how to add a custom infected that reuses the vanilla skeleton, animations and AI with a new mesh only: the config inheritance, why "bigger" has to be baked into the mesh, a see-through hole, the character LODs, and what each part costs.

How to read the marks: a `P:\` path with a line number was opened and checked in vanilla. Statements about engine behaviour come from Bohemia's wiki or feedback tracker (linked), from named community sources, or from the LFInfectedBig project; none of those can be checked on `P:\`.

The recipe was first worked out for a request for "a slightly larger infected with a hole in the torso" (2026-06-23) and then applied end to end on LFInfectedBig (`references/case-log.md`).

## 1. Config: inherit, do not rebuild

The vanilla chain in `P:\DZ\characters\zombies\config.cpp`:

| Class | Parent | Line |
|---|---|---|
| `DayZInfected` | `DZ_LightAI` | `P:\DZ\characters\zombies\config.cpp:21` |
| `ZombieBase` | `DayZInfected` | `P:\DZ\characters\zombies\config.cpp:24` |
| `ZombieFemaleBase` | `ZombieBase` | `P:\DZ\characters\zombies\config.cpp:419` |
| `ZombieMaleBase` | `ZombieBase` | `P:\DZ\characters\zombies\config.cpp:549` |
| `ZmbM_HermitSkinny_Base` (a model) | `ZombieMaleBase` | `P:\DZ\characters\zombies\config.cpp:679` |
| `ZmbM_HermitSkinny_Beige` (a texture variant, `scope=2`) | `ZmbM_HermitSkinny_Base` | `P:\DZ\characters\zombies\config.cpp:905` |

Skeleton, animations and AI come with the inheritance. `ZombieBase` holds the `enfanimsys` block (`P:\DZ\characters\zombies\config.cpp:71`) that names the animation graph, the instance and the bind skeleton, and its `aiAgentTemplate` (`P:\DZ\characters\zombies\config.cpp:160`) names the behaviour template. A child that does not redeclare them gets every infected animation and the AI driver for free. `references/canonical-bind.md` lists the block's values.

Minimal config, following the two-level vanilla pattern above (a hidden base with the model and materials, then one visible class per texture):

```cpp
class CfgPatches
{
    class MyMod_Infected
    {
        units[] = { "MyZ" };
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = { "DZ_Characters_Zombies" };
    };
};
class CfgVehicles
{
    class ZombieMaleBase;
    class MyZ_Base: ZombieMaleBase
    {
        scope = 0;
        model = "\MyMod\infected\myz.p3d";
        hiddenSelectionsMaterials[] = { "MyMod\infected\data\myz.rvmat" };
    };
    class MyZ: MyZ_Base
    {
        scope = 2;
        hiddenSelectionsTextures[] = { "MyMod\infected\data\myz_co.paa" };
    };
};
```

`DZ_Characters_Zombies` is the vanilla addon that defines these classes (`P:\DZ\characters\zombies\config.cpp:3`).

| Character type | Inherit | What it gives | Notes |
|---|---|---|---|
| Infected, male | `ZombieMaleBase` | Character skeleton, infected animation graph, AI | Community rule from the PvZmoD mod's workshop discussion: a custom infected inherits `ZombieBase`, never `AnimalBase` |
| Infected, female | `ZombieFemaleBase` | The same, female proportions | |
| Infected, female military (1.30) | `ZmbF_SoldierNormal_Base` | Female soldier AI template | See `references/dayz-1-30-characters.md` |
| Survivor or human NPC | `SurvivorMale_Base` or `SurvivorFemale_Base` | Character skeleton, player animations | Not built by the source project. The class tree and body parts are in `skills/_shared/wearables/references/characters.md`; vanilla has no human AI (`skills/_shared/ai/patrols-and-guards.md`) |

Spawning is the same as for any infected: the server's Central Economy files (events, infected territories, `types.xml`). The entries the server lead needs are listed in `skills/_shared/ai/spawning-and-performance.md`. Infected behaviour and the 1.30 mind state are in `skills/_shared/ai/custom-infected.md`.

**The animation wall.** Reported by the source project and the community, not checkable on `P:\`: only one mod that modifies player or creature animations can be loaded at a time, and loading two crashes the client or server. A character that ships new animations therefore conflicts with every other animation mod on the server. A reskin that inherits the vanilla `enfanimsys` does not hit this. Warn the user whenever a plan ships custom character animations. The dayz-animation-pipeline skill covers the wall and the tooling around it.

## 2. Rigging: the real cost

Everything about the rig is in `references/character-rigging.md`; the facts that decide the plan:

- The mesh must use the exact vanilla bone names as its selection names. Animations are keyed to those names.
- "Bones" in `model.cfg` are named vertex selections, not an armature. Deformation is per-vertex weights on selections named like the bones.
- Typical failures: a selection without weights gives pinched or stretched vertices; a selection name that is not in `skeletonBones[]` makes the mesh explode.
- Vanilla infected models are binarized, so a new mesh has to be authored and rigged.

## 3. Size: runtime scaling is broken, bake it into the mesh

"Make it bigger or smaller" has no config or script path.

- The engine exposes `SetScale` and `GetScale` on every entity (`P:\scripts\1_core\proto\enentity.c:447`), but Bohemia's feedback tracker reports them broken on entities (<https://feedback.bistudio.com/T140705>), and the collision box does not follow a scale (DayZ Modders Discord, April 2026).
- The Object Spawner's `scale` is for static objects only, not characters or AI (<https://community.bistudio.com/wiki/DayZ:Object_Spawner>). There is no per-axis scale and no character `scale` key in `CfgVehicles`.
- The only route is to bake the size into the mesh on the same skeleton. Geometry and collision LODs scale together, so collision matches.

The cost is larger than foot sliding. Vanilla animations assume vanilla bone lengths, and the engine binds against the canonical bind of about 1.8 m (`references/canonical-bind.md`), so a baked oversize deforms the mesh under animation. LFInfectedBig at about 1.27 times deformed grossly; rescaling to about 1.8 m removed the catastrophic deformation (in game, 2026-06-24). Small departures, up to about 1.1 times, may pass with only foot sliding and IK drift. The first estimate of this recipe ("about 1.2 times is subtle and probably acceptable, 2 times breaks badly") did not survive that test at 1.27 times. A character that is truly bigger and still deforms cleanly is unsolved here: it would need a custom skeleton with a scaled bind, not a scaled mesh. No shipped example of a clean giant infected was found.

Check in game: foot contact, door clipping, melee and hit range, AI pathing. If limbs distort under animation, the size is fighting the bind.

## 4. A see-through hole in the torso

- **Visual.** Model an interior tunnel (a closed surface whose faces look into the hole). It is the most robust. Alternatives: the "both sides" face flag, or double-sided geometry. Bohemia's wiki gives the flag as `0x00000020` (<https://community.bohemia.net/wiki/P3D_Point_and_Face_Flags>); the source project's own notes gave `0x20000` for "no backface culling". The two were never reconciled, so check the flag in Object Builder before relying on it.
- **Collision (Geometry LOD).** It must be "closed and convex" (<https://community.bohemia.net/wiki/Validating_Geometries>). A torso with a hole is not convex. Either split it into convex pieces as numbered `ComponentXX` selections, or take the simple route and leave the collision solid, ignoring the hole. The collision LOD does not have to match the visual LOD. Mass at least 10.
- **Fire Geometry.** Solid unless shots should pass through (more components for little gain). With solid collision, bullets that cross the visual hole still hit. That is a design decision; tell the user.
- **Damage zones.** They are config driven: each zone lists the model's component names, for example `componentNames[]` with `Head` and `Neck` at `P:\DZ\characters\zombies\config.cpp:239`. A remodelled torso keeps working as long as the named selections and components the config expects are still in the model.

## 5. Character LODs

- **Visual.** The rendered mesh, with the hole or other detail.
- **Geometry.** Closed and convex, as above; mass at least 10. LFInfectedBig used one hull with the named property `class = "man"`, not skinned.
- **Fire Geometry.** LFInfectedBig skinned it to the bones, with a `dmgzone_spine` selection and the vanilla penetration material `P:\DZ\data\data\penetration\meatbones.rvmat` on its faces.
- **View Geometry, LandContact, Memory.** As for any model (`skills/_shared/models/lods.md`, `skills/_shared/models/memory-points.md`). LFInfectedBig built its Memory points from the bone positions.

Use the DayZ LOD resolution values, not the Arma 3 ones: the table is in `skills/_shared/conventions/assets.md` (View Geometry `6.0e+15`, Fire Geometry `7.0e+15`).

## 6. What each part costs

| Part | Difficulty |
|---|---|
| Config (inherit `ZombieMaleBase`) | Trivial |
| Reusing skeleton, animations and AI | Free, through the inherited `enfanimsys` |
| Visual hole with solid collision | Low risk |
| Rigging the custom mesh to the character skeleton | Medium to hard; the real cost of the project |
| "Bigger" | Bake it into the mesh, keep it near vanilla size, and verify the animations in game |

## 7. Plan, in order

1. Mesh: generated from a reference image or edited from a humanoid base, conformed to the rig's proportions, with the hole modelled as a tunnel.
2. Rig it to the character skeleton with the official Bohemia rig, automatic weights and cleanup (`references/character-rigging.md`).
3. Bake any size change into the mesh. LODs: Visual with the hole, solid convex Geometry, Fire Geometry, Memory.
4. Texture to `_co`, `_nohq` and `_smdi` (`skills/_shared/textures/suffixes-and-sizes.md`; the bake is in `references/character-uv-bake.md`).
5. Config: a `_Base` class under `ZombieMaleBase` plus one variant; a `model.cfg` with the character skeleton.
6. Run the winding gate (`references/winding-gate.md`), build with `/dayz-build-pbo`, then test in game with `/dayz-launch-test`: animations, foot sliding, collision, hits, spawning.

## Sources outside `P:\`

- Bohemia wiki: Model Config (<https://community.bistudio.com/wiki/Model_Config>), LOD (<https://community.bohemia.net/wiki/LOD>), Validating Geometries, P3D Point and Face Flags, DayZ Object Spawner (links above).
- Bohemia repositories: the official rig in `BohemiaInteractive/DayZ-Misc`; config driven damage zones in the `Test_Building` sample of `BohemiaInteractive/DayZ-Samples`.
- Feedback tracker T140705 on `SetScale`.
- A community copy of the character skeleton's `model.cfg` in the DayZ Epoch mod repository (`EpochModTeam/DayZ-Epoch`, `SQF/dayz_code/anim/model.cfg`).
- Workshop examples of custom infected: Skeleton Zombies (item 1865458192) and the PvZmoD discussion (item 2051775667).
- DayZ Modders Discord threads on rigging, scaling and convex geometry.
