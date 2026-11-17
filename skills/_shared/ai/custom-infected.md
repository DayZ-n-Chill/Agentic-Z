# Custom infected: what the AI inherits and what a new body changes

What a custom infected class gets for behaviour by inheriting the vanilla chain, what its new model has to keep for the AI to work, why a bigger body does not reach further, and the 1.30 changes to infected behaviour.

The model, rig and export side of a custom infected is the `/dayz-characters` skill, and how a creature class is tied to its animation graph is in `creature-animation.md`. This file is the behaviour side. Facts that cannot be checked on `P:\` are marked as such.

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
- A baked oversize also deforms under the inherited animations, because the engine binds against a body of vanilla size. A mesh at about 1.27 times vanilla size deformed grossly and had to be scaled back (measured in game).
- Check in game for any body that is not vanilla sized: foot contact, door clipping, melee and hit range, and whether it still paths through doorways.

## 1.30: new classes, a new mind state, new attacks

**Female military infected.** Config classes and their templates:

| Class | Parent | Template | Where |
|---|---|---|---|
| `ZmbF_SoldierNormal_Base` | `ZombieFemaleBase` | `InfectedMSoldier` (`aiAgentTemplate` at `P:\DZ\characters\zombies\config.cpp:11123`) | `P:\DZ\characters\zombies\config.cpp:11119` |
| `ZmbF_ArmyOfficer` | `ZmbF_SoldierNormal_Base` | `InfectedSoldier_Officer` (`aiAgentTemplate` at `P:\DZ\characters\zombies\config.cpp:11358`) | `P:\DZ\characters\zombies\config.cpp:11354` |
| `ZmbF_eastSoldier_Base` | `ZmbF_usSoldier_normal_Base` | Inherited from its parent | `P:\DZ\characters\zombies\config.cpp:11577` |

In script, `ZmbF_SoldierNormal_Base` and `ZmbF_eastSoldier_Base` extend `ZombieFemaleBase` and return true from `IsZombieMilitary()` (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:139` and `:147`). `IsZombieMilitary()` is declared on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:744`) and returns false on `ZombieBase` (`P:\scripts\4_world\entities\creatures\infected\zombiebase.c:113`). A custom military infected gets the flag by giving its own script class the same override.

The Nasdara classes are plain children of the sex bases: `ZmbM_takiCitizenUrbanA_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiemalebase.c:160`) and `ZmbF_takiCitizenUrbanA_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:163`) onward.

**`MINDSTATE_COWER`.** The mind state list gains `MINDSTATE_COWER` after `MINDSTATE_FIGHT` (`P:\scripts\3_game\entities\dayzinfected.c:18`). The engine AI stops the creature, and `ZombieBase` holds the calm idle pose: the `MINDSTATE_COWER` case at `P:\scripts\4_world\entities\creatures\infected\zombiebase.c:475` calls `SetIdleState(0)`, under a comment that names sandstorm cowering. A mod that switches on the mind state in `HandleMindStateChange` or in its own hooks must handle the new value, or the creature falls through the switch. The other states are in `creatures.md`.

**Heavy running attacks.** Two new clips ship in `P:\DZ\anims\anm\infected\attacks\erected\`: `z_erc_run_attackl_heavy.anm` and `z_erc_run_attackr_heavy.anm`. A mod that replaces the infected combat graph should expect them.

**The animation graph is split.** `graphname` still names `infected.agr` (`P:\DZ\characters\zombies\config.cpp:74`), which is now an index over three subgraph files, `Locomotion.agf`, `Combat.agf` and `Interaction.agf` (`GraphFilesResourceNames` at `P:\DZ\anims\workspaces\infected\infected_main\infected.agr:430`). A custom infected graph made for 1.29 has to be opened and saved again in Workbench 1.30; that conversion is not tested and not checkable on `P:\`.

## Limits to tell the user

- **One animation graph mod at a time.** Not checkable on `P:\`: loading two mods that change player or creature animation graphs crashes the client or server. A custom infected that inherits the vanilla `enfanimsys` is not affected; one that ships its own graph conflicts with every other animation mod on the server.
- **No ragdoll file on infected.** The infected block sets no `ragdoll` key (`enfanimsys` at `P:\DZ\characters\zombies\config.cpp:71` to `:78`); survivors bind one in 1.30 (`ragdoll` at `P:\DZ\characters\data\config.cpp:160`).
- **Spawning** goes through the server's Central Economy files or a scripted spawner (`spawning-and-performance.md`).
