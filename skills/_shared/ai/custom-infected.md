# Custom infected

What a custom infected class gets for behaviour by inheriting the vanilla chain, what its new model has to keep for the AI to work, why a bigger body does not reach further, and what 1.30 changed for infected.

This file is the config and behaviour side. The mesh, rig, bake and export of a new body go to `dayz-animation-specialist` and the art team (`_shared/wearables/references/body-rigging.md`); how a creature class is tied to its graph is in `creature-animation.md`.

## Inherit the chain, never rebuild it

The vanilla chain, all in `P:\DZ\characters\zombies\config.cpp`:

| Class | Parent | Line |
|---|---|---|
| `DayZInfected` | `DZ_LightAI` | `:21` |
| `ZombieBase` | `DayZInfected` | `:24` |
| `ZombieFemaleBase` | `ZombieBase` | `:419` |
| `ZombieMaleBase` | `ZombieBase` | `:549` |
| `ZmbM_HermitSkinny_Base`, a hidden model class (`scope=0`, `model`, `hiddenSelectionsMaterials[]`) | `ZombieMaleBase` | `:679` |
| `ZmbM_HermitSkinny_Beige`, a visible texture variant (`scope=2`, `hiddenSelectionsTextures[]`) | `ZmbM_HermitSkinny_Base` | `:905` |

A custom infected follows the same two levels: a hidden base with the model and material, then one visible class per texture. The addon that defines the chain is `DZ_Characters_Zombies` (`P:\DZ\characters\zombies\config.cpp:3`).

```cpp
class CfgPatches
{
    class MyMod_Infected
    {
        units[] = { "MyMod_Zmb" };
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = { "DZ_Characters_Zombies" };
    };
};
class CfgVehicles
{
    class ZombieMaleBase;
    class MyMod_Zmb_Base: ZombieMaleBase
    {
        scope = 0;
        model = "\MyMod\infected\mymod_zmb.p3d";
        hiddenSelectionsMaterials[] = { "MyMod\infected\data\mymod_zmb.rvmat" };
    };
    class MyMod_Zmb: MyMod_Zmb_Base
    {
        scope = 2;
        hiddenSelectionsTextures[] = { "MyMod\infected\data\mymod_zmb_co.paa" };
    };
};
```

`dayz-config-specialist` writes the `config.cpp`; this pack says what it must inherit. A new behaviour template on top of it is in `behaviour-config.md`, section "Making your own variant".

The config is the cheap part. Skeleton, animations and AI come free through the inherited blocks below. Rigging a new mesh to the infected skeleton is the real cost of the project, and a bigger body has to be baked into the mesh and checked in game.

Inherit the infected chain, never an animal. The infected commands, the mind states and `DayZInfectedType` belong to `DayZInfected` (`creatures.md`), and an `AnimalBase` child gets the animal ones instead.

## What a child class inherits

A class under `ZombieMaleBase` or `ZombieFemaleBase` that redeclares none of these keeps vanilla behaviour. All lines are in `P:\DZ\characters\zombies\config.cpp`.

| Block or key | What it gives | Line |
|---|---|---|
| `aiAgentTemplate` | The behaviour template: `Infected` on `ZombieBase`, then `InfectedFemale` and `InfectedMale` on the sex bases | `:160`, `:423`, `:553` |
| `class enfanimsys` | The graph, its instance, the bind skeleton and `startnode="MasterControl"`: every animation the commands play | `:71` |
| `class InputController` | `movementSpeedMapping[]`, the speeds behind idle, walk, run and sprint | `:79` |
| `class AttackActions` | The attack ammo and distances the script type reads | `:436` |
| `class DamageZones` | Health, armour and `componentNames[]` per zone | `:206` |
| `attackSounds`, `spottedSounds`, `chaseSounds`, `idleSounds` | The voice sets | `:92` |

To change how the creature sees, hears or alerts, add a template and point `aiAgentTemplate` at it (`behaviour-config.md`). To change what it does each step, use the command handler hooks (`creatures.md`).

## What the new model has to keep

- **Damage zone components.** Each zone lists the model's component names, for example `componentNames[]` with `Head` and `Neck` (`P:\DZ\characters\zombies\config.cpp:239`). A remodelled body keeps taking zone damage as long as its Fire Geometry has the components the inherited zones name.
- **Hit components other AI aim at.** `DayZInfectedType.RegisterHitComponentsForAI` (`P:\scripts\3_game\entities\dayzinfectedtype.c:25`) registers `Head`, `LeftArm`, `Torso`, `RightArm`, `LeftLeg` and `RightLeg` with a weight each, sets the default hit component to `Torso` (`m_DefaultHitComponent` at `:30`) and the default hit position to `Spine1` (`m_DefaultHitPositionComponent` at `:32`). These are zone names, so a class that inherits `DamageZones` unchanged needs nothing more.
- **Bones named in config.** `ZombieBase` lists the bones its attachment proxies ride on (`BoneNames[]` at `P:\DZ\characters\zombies\config.cpp:48`) and the memory points for steps, aim and camera (`memoryPointLStep` at `:118` and the keys after it). A custom model needs those bones as selections and those points in its Memory LOD, or it must override the keys.

## A bigger body does not reach further

- Attack distances are fixed numbers, not read from the model. The chase attacks register at 2.4 m (`RegisterAttack` with `DayZInfectedAttackGroupType.CHASE` at `P:\scripts\3_game\entities\dayzinfectedtype.c:72`) and the fight attacks at 1.7 m and 1.4 m (`DayZInfectedAttackGroupType.FIGHT` at `:80` and `:86`). Config adds `minDistance` and `distance` per attack under `AttackActions`. A larger mesh keeps these numbers unless the mod changes them.
- Scaling at run time is no route. `SetScale` exists on every entity (`P:\scripts\1_core\proto\enentity.c:448`), but it does not work reliably on characters and the collision box does not follow it (engine behaviour, not checked on `P:\`). Size is baked into the mesh by the art side.
- A baked oversize also deforms under the inherited animations, because the engine binds against a body of vanilla size. A test infected at about 1.27 times vanilla size deformed grossly and had to be scaled back (measured in game). Up to about 1.1 times may pass with only foot sliding. A body that is truly bigger and still deforms cleanly needs its own skeleton with a scaled bind, and no vanilla example shows one. There is no character `scale` key in `CfgVehicles`, and the Object Spawner's `scale` is for static objects only (not checked on `P:\`).
- Check any body that is not vanilla sized in game: foot contact, door clipping, melee and hit range, and whether it still paths through doorways.

## What 1.30 changed for infected

`P:\` holds 1.30 only, so the classes and clips below are checked to exist in 1.30; that they are new in 1.30 is not checked on `P:\`.

**Female military infected.** Config classes and their templates, all in `P:\DZ\characters\zombies\config.cpp`:

| Class | Parent | Template | Line |
|---|---|---|---|
| `ZmbF_SoldierNormal_Base` | `ZombieFemaleBase` | `InfectedMSoldier` (`:11123`) | `:11119` |
| `ZmbF_ArmyOfficer` | `ZmbF_SoldierNormal_Base` | `InfectedSoldier_Officer` (`:11358`) | `:11354` |
| `ZmbF_eastSoldier_Base` | `ZmbF_usSoldier_normal_Base` | Inherited | `:11577` |
| `ZmbF_SoldierNormal` (`scope=2`) | `ZmbF_SoldierNormal_Base` | Inherited | `:11346` |
| `ZmbF_eastSoldier_Normal_Navy` (`scope=2`) | `ZmbF_eastSoldier_Base` | Inherited | `:11799` |
| `ZmbF_eastSoldier_Heavy_Navy` (`scope=2`) | `ZmbF_eastSoldier_Normal_Navy` | Inherited | `:11807` |

`ZmbF_eastSoldier_Base` has the US female soldier base as its config parent (`ZmbF_usSoldier_normal_Base: ZombieFemaleBase` at `:10801`). A custom female military infected inherits one of these soldier bases, or `ZombieFemaleBase`; it never needs its own AI driver.

In script, `ZmbF_SoldierNormal_Base` and `ZmbF_eastSoldier_Base` extend `ZombieFemaleBase` and return true from `IsZombieMilitary()` (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:139` and `:147`), and so does `Zmbf_IonSoldier_Normal_1` (`:155`). `IsZombieMilitary()` is declared on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:744`) and returns false on `ZombieBase` (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:113`). A custom military infected gets the flag by giving its own script class the same override.

**Nasdara classes.** They are plain children of the sex bases, from `ZmbM_takiCitizenUrbanA_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiemalebase.c:160`) and `ZmbF_takiCitizenUrbanA_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:163`) onward; the female list ends at `ZmbF_takiOilRigWorker_Base` (`:188`).

**`MINDSTATE_COWER`.** The mind state list gains `MINDSTATE_COWER` after `MINDSTATE_FIGHT` (`P:\scripts\3_game\entities\dayzinfected.c:18`). How `ZombieBase` reacts to it and what a mod has to handle are in `creatures.md`, section "Infected mind states".

**Heavy running attacks.** Two clips ship in `P:\DZ\anims\anm\infected\attacks\erected\`: `z_erc_run_attackl_heavy.anm` and `z_erc_run_attackr_heavy.anm`. A mod that replaces the infected combat graph should expect them.

**A split graph.** `graphname` still names `infected.agr` (`P:\DZ\characters\zombies\config.cpp:74`), which is now an index over three sub graphs, `Locomotion.agf`, `Combat.agf` and `Interaction.agf` (`GraphFilesResourceNames` at `P:\DZ\anims\workspaces\infected\infected_main\infected.agr:430`). A custom infected graph made for 1.29 has to be opened and saved again in Workbench 1.30; that conversion is not tested and not checked on `P:\`.

## Limits to tell the user

- **One animation graph mod at a time.** Loading two mods that change player or creature graphs crashes the client or server (reported, not checked on `P:\`). A custom infected that inherits the vanilla `enfanimsys` is not affected; one that ships its own graph conflicts with every other animation mod on the server.
- **No ragdoll on infected.** The infected block sets no `ragdoll` key (`enfanimsys` at `P:\DZ\characters\zombies\config.cpp:71` to `:78`); survivors bind one in 1.30 (`ragdoll` at `P:\DZ\characters\data\config.cpp:160`).
- **Spawning** goes through the server's economy files or a scripted spawner (`spawning-and-performance.md`).
