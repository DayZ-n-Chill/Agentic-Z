# Custom infected: what the AI inherits and what a new body changes

What a custom infected class gets for behaviour by inheriting the vanilla chain, what its new model has to keep for the AI to work, why a bigger body does not reach further, and the 1.30 changes to infected behaviour.

The mesh, rig, bake and export of a new body are art work for dayz-animation-specialist and the art team, not this pack; how a creature class is tied to its animation graph is in `creature-animation.md`. This file is the config and behaviour side. Facts that cannot be checked on `P:\` are marked as such.

## The config: inherit, do not rebuild

The vanilla chain, all in `P:\DZ\characters\zombies\config.cpp`:

| Class | Parent | Line |
|---|---|---|
| `DayZInfected` | `DZ_LightAI` | `P:\DZ\characters\zombies\config.cpp:21` |
| `ZombieBase` | `DayZInfected` | `P:\DZ\characters\zombies\config.cpp:24` |
| `ZombieFemaleBase` | `ZombieBase` | `P:\DZ\characters\zombies\config.cpp:419` |
| `ZombieMaleBase` | `ZombieBase` | `P:\DZ\characters\zombies\config.cpp:549` |
| `ZmbM_HermitSkinny_Base`, a hidden model class (`scope=0`, `model`, `hiddenSelectionsMaterials[]`) | `ZombieMaleBase` | `P:\DZ\characters\zombies\config.cpp:679` |
| `ZmbM_HermitSkinny_Beige`, a visible texture variant (`scope=2`, `hiddenSelectionsTextures[]`) | `ZmbM_HermitSkinny_Base` | `P:\DZ\characters\zombies\config.cpp:905` |

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

The `config.cpp` itself is written by dayz-config-specialist; this pack says what it must inherit. A new behaviour template on top of it is in `behaviour-config.md`, "Making your own variant".

| Part of the job | Cost |
|---|---|
| Config that inherits `ZombieMaleBase` or `ZombieFemaleBase` | Trivial |
| Skeleton, animations and AI | Free, through the inherited blocks below |
| Rigging a new mesh to the infected skeleton | The real cost of the project (art side) |
| A bigger body | Baked into the mesh, kept near vanilla size, checked in game (section below) |

## What a child class inherits

A class under `ZombieMaleBase` or `ZombieFemaleBase` that redeclares none of these keeps vanilla behaviour unchanged. All lines are in `P:\DZ\characters\zombies\config.cpp`.

| Block or key | What it gives | Where |
|---|---|---|
| `aiAgentTemplate` | The behaviour template: `Infected` on `ZombieBase`, then `InfectedFemale` and `InfectedMale` on the sex bases | `P:\DZ\characters\zombies\config.cpp:160`, `:423`, `:553` |
| `class enfanimsys` | The animation graph, its instance, the bind skeleton and `startnode="MasterControl"`: every infected animation the commands play | `P:\DZ\characters\zombies\config.cpp:71` |
| `class InputController` | `movementSpeedMapping[]`, the speeds behind idle, walk, run and sprint | `P:\DZ\characters\zombies\config.cpp:79` |
| `class AttackActions` | The attack ammo and distances the script type reads | `P:\DZ\characters\zombies\config.cpp:436` |
| `class DamageZones` | Health, armour and `componentNames[]` per zone | `P:\DZ\characters\zombies\config.cpp:206` |
| `attackSounds`, `spottedSounds`, `chaseSounds`, `idleSounds` | The voice sets | `P:\DZ\characters\zombies\config.cpp:92` |

To change how the creature sees, hears or alerts, add a template and point `aiAgentTemplate` at it (`behaviour-config.md`). To change what it does each step, use the command handler hooks (`creatures.md`).

Inherit the infected chain, never an animal. The reason is visible in vanilla script: the infected commands, the mind states and `DayZInfectedType` belong to `DayZInfected` (`creatures.md`), and an `AnimalBase` child gets the animal ones instead.

## What the new model has to keep

- **Damage zone components.** Each zone lists the model's component names, for example `componentNames[]` with `Head` and `Neck` at `P:\DZ\characters\zombies\config.cpp:239`. A remodelled body keeps taking zone damage as long as its Fire Geometry still has the named components the inherited zones list.
- **Hit components other AI aim at.** `DayZInfectedType.RegisterHitComponentsForAI` (`P:\scripts\3_game\entities\dayzinfectedtype.c:25`) registers `Head`, `LeftArm`, `Torso`, `RightArm`, `LeftLeg` and `RightLeg` with a weight each, sets the default hit component to `Torso` (`m_DefaultHitComponent` at `:30`) and the default hit position to `Spine1` (`m_DefaultHitPositionComponent` at `:32`). These are zone names from the block above, so a class that inherits `DamageZones` unchanged needs nothing more.
- **Bones named in config.** `ZombieBase` lists the bones its attachment proxies ride on (`BoneNames[]` at `P:\DZ\characters\zombies\config.cpp:48`) and the memory points for steps, aim and camera (`memoryPointLStep` at `P:\DZ\characters\zombies\config.cpp:118` and the keys after it). A custom model needs those bones as selections and those points in its Memory LOD, or it must override the keys.

## A bigger body does not reach further

- Attack distances are fixed numbers, not read from the model. The chase attacks register at 2.4 m (`RegisterAttack` with `DayZInfectedAttackGroupType.CHASE` at `P:\scripts\3_game\entities\dayzinfectedtype.c:72`) and the fight attacks at 1.7 m and 1.4 m (`DayZInfectedAttackGroupType.FIGHT` at `P:\scripts\3_game\entities\dayzinfectedtype.c:80` and `:86`). Config adds `minDistance` and `distance` per attack under `AttackActions`. A larger mesh keeps these numbers unless the mod changes them.
- Scaling at run time is not an option. `SetScale` exists on every entity (`P:\scripts\1_core\proto\enentity.c:448`), but it does not work reliably on entities and the collision box does not follow it (not checkable on `P:\`). Size is baked into the mesh by the art side.
- A baked oversize also deforms under the inherited animations, because the engine binds against a body of vanilla size. A mesh at about 1.27 times vanilla size deformed grossly and had to be scaled back (measured in game). Departures up to about 1.1 times may pass with only foot sliding; a body that is truly bigger and still deforms cleanly would need its own skeleton with a scaled bind, which no shipped example shows. There is no character `scale` key in `CfgVehicles`, and the Object Spawner's `scale` is for static objects only (not checkable on `P:\`).
- Check in game for any body that is not vanilla sized: foot contact, door clipping, melee and hit range, and whether it still paths through doorways.

## 1.30: new classes, a new mind state, new attacks

`P:\` holds 1.30 only, so that the classes, mind state and clips below are new in 1.30 rather than older is not checkable on `P:\`. That they exist in 1.30 is checked at the lines cited.

**Female military infected.** Config classes and their templates:

| Class | Parent | Template | Where |
|---|---|---|---|
| `ZmbF_SoldierNormal_Base` | `ZombieFemaleBase` | `InfectedMSoldier` (`aiAgentTemplate` at `P:\DZ\characters\zombies\config.cpp:11123`) | `P:\DZ\characters\zombies\config.cpp:11119` |
| `ZmbF_ArmyOfficer` | `ZmbF_SoldierNormal_Base` | `InfectedSoldier_Officer` (`aiAgentTemplate` at `P:\DZ\characters\zombies\config.cpp:11358`) | `P:\DZ\characters\zombies\config.cpp:11354` |
| `ZmbF_eastSoldier_Base` | `ZmbF_usSoldier_normal_Base` | Inherited from its parent | `P:\DZ\characters\zombies\config.cpp:11577` |
| `ZmbF_SoldierNormal` (`scope=2`) | `ZmbF_SoldierNormal_Base` | Inherited | `P:\DZ\characters\zombies\config.cpp:11346` |
| `ZmbF_eastSoldier_Normal_Navy` (`scope=2`) | `ZmbF_eastSoldier_Base` | Inherited | `P:\DZ\characters\zombies\config.cpp:11799` |
| `ZmbF_eastSoldier_Heavy_Navy` (`scope=2`) | `ZmbF_eastSoldier_Normal_Navy` | Inherited | `P:\DZ\characters\zombies\config.cpp:11807` |

`ZmbF_eastSoldier_Base` has the US female soldier base as its config parent (`ZmbF_usSoldier_normal_Base: ZombieFemaleBase` at `P:\DZ\characters\zombies\config.cpp:10801`), not `ZombieFemaleBase` directly. A custom female military infected inherits one of these soldier bases, or `ZombieFemaleBase`; it never needs its own AI driver.

In script, `ZmbF_SoldierNormal_Base` and `ZmbF_eastSoldier_Base` extend `ZombieFemaleBase` and return true from `IsZombieMilitary()` (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:139` and `:147`), and so does `Zmbf_IonSoldier_Normal_1` (`:155`). `IsZombieMilitary()` is declared on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:744`) and returns false on `ZombieBase` (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:113`). A custom military infected gets the flag by giving its own script class the same override.

The Nasdara classes are plain children of the sex bases: `ZmbM_takiCitizenUrbanA_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiemalebase.c:160`) and `ZmbF_takiCitizenUrbanA_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:163`) onward; the female list ends at `ZmbF_takiOilRigWorker_Base` (`:188`).

**`MINDSTATE_COWER`.** The mind state list gains `MINDSTATE_COWER` after `MINDSTATE_FIGHT` (`P:\scripts\3_game\entities\dayzinfected.c:18`). How `ZombieBase` reacts to it and what a mod has to handle are in `creatures.md`, section "Infected mind states".

**Heavy running attacks.** Two new clips ship in `P:\DZ\anims\anm\infected\attacks\erected\`: `z_erc_run_attackl_heavy.anm` and `z_erc_run_attackr_heavy.anm`. A mod that replaces the infected combat graph should expect them.

**The animation graph is split.** `graphname` still names `infected.agr` (`P:\DZ\characters\zombies\config.cpp:74`), which is now an index over three subgraph files, `Locomotion.agf`, `Combat.agf` and `Interaction.agf` (`GraphFilesResourceNames` at `P:\DZ\anims\workspaces\infected\infected_main\infected.agr:430`). A custom infected graph made for 1.29 has to be opened and saved again in Workbench 1.30; that conversion is not tested and not checkable on `P:\`.

## Limits to tell the user

- **One animation graph mod at a time.** Not checkable on `P:\`: loading two mods that change player or creature animation graphs crashes the client or server. A custom infected that inherits the vanilla `enfanimsys` is not affected; one that ships its own graph conflicts with every other animation mod on the server.
- **No ragdoll file on infected.** The infected block sets no `ragdoll` key (`enfanimsys` at `P:\DZ\characters\zombies\config.cpp:71` to `:78`); survivors bind one in 1.30 (`ragdoll` at `P:\DZ\characters\data\config.cpp:160`).
- **Spawning** goes through the server's Central Economy files or a scripted spawner (`spawning-and-performance.md`).
