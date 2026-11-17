# DayZ 1.30: what changed for humanoid characters

Covers the 1.30 changes that touch custom infected and survivors: new infected classes, the infected animation graph format, the cower mind state, new attack clips, human skinning, surrender, and the sandstorm protection that worn gear gives a humanoid.

How to read the marks: every `P:\` line was opened and checked on a 1.30 install. Statements about 1.29 and about Bohemia's migration advice come from the 1.30 experimental modding changelog and cannot be checked on `P:\`. "Design note" marks advice, not a vanilla fact.

The mesh, rig and LOD rules in the rest of this skill still hold. This file is the 1.30 overlay.

## Infected class additions

The inherit path is unchanged: `DZ_LightAI`, `DayZInfected`, `ZombieBase`, then `ZombieMaleBase` or `ZombieFemaleBase`, then the variants.

Female military classes in `P:\DZ\characters\zombies\config.cpp`:

| Class | Parent | Line | Sets |
|---|---|---|---|
| `ZmbF_SoldierNormal_Base` | `ZombieFemaleBase` | `P:\DZ\characters\zombies\config.cpp:11119` | `model` `ZmbF_SoldierNormal.p3d`, `aiAgentTemplate="InfectedMSoldier"` (`:11123`) |
| `ZmbF_SoldierNormal` | `ZmbF_SoldierNormal_Base` | `P:\DZ\characters\zombies\config.cpp:11346` | `scope=2` |
| `ZmbF_ArmyOfficer` | `ZmbF_SoldierNormal_Base` | `P:\DZ\characters\zombies\config.cpp:11354` | `model` `ArmyOfficer_fat_f.p3d`, `aiAgentTemplate="InfectedSoldier_Officer"` (`:11358`) |
| `ZmbF_eastSoldier_Base` | `ZmbF_usSoldier_normal_Base` | `P:\DZ\characters\zombies\config.cpp:11577` | Its config parent is the US female soldier base (`:10801`), not `ZombieFemaleBase` directly |
| `ZmbF_eastSoldier_Normal_Navy` | `ZmbF_eastSoldier_Base` | `P:\DZ\characters\zombies\config.cpp:11799` | `scope=2` |
| `ZmbF_eastSoldier_Heavy_Navy` | `ZmbF_eastSoldier_Normal_Navy` | `P:\DZ\characters\zombies\config.cpp:11807` | `scope=2` |

Script bases, in `P:\scripts\4_world\entities\creatures\infected\`:

- `ZmbF_SoldierNormal_Base` and `ZmbF_eastSoldier_Base` extend `ZombieFemaleBase` and override `IsZombieMilitary()` to return true (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:139` and `:147`). So does `Zmbf_IonSoldier_Normal_1` (`:155`).
- Nasdara male bases start at `ZmbM_takiCitizenUrbanA_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiemalebase.c:160`).
- Nasdara female bases run from `ZmbF_takiCitizenUrbanA_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:163`) to `ZmbF_takiOilRigWorker_Base` (`P:\scripts\4_world\entities\creatures\infected\zombiefemalebase.c:188`).

Design note: inherit `ZombieFemaleBase`, or one of these soldier bases, for a custom female military infected. Do not invent a parallel AI driver.

## Infected animation graph: an `.agr` index over `.agf` subgraphs

Up to 1.29 (changelog), `graphname` in `enfanimsys` pointed at one monolithic infected `.agr`.

Since 1.30 the path is the same, `dz\anims\workspaces\infected\infected_main\infected.agr` (`graphname` at `P:\DZ\characters\zombies\config.cpp:74`), but the file is now Enfusion text with the root `AnimSrcGraph` (`P:\DZ\anims\workspaces\infected\infected_main\infected.agr:1`) that lists subgraph files. The subgraphs are `.agf` files with the root `AnimSrcGraphFile` (`P:\DZ\anims\workspaces\infected\infected_main\locomotion.agf:1`).

The list, at `P:\DZ\anims\workspaces\infected\infected_main\infected.agr:430`:

```
 GraphFilesResourceNames {
  "{055B14354B447015}DZ/anims/workspaces/infected/infected_main/Locomotion.agf" "{809A284592397198}DZ/anims/workspaces/infected/infected_main/Combat.agf" "{A3A83C5CD5FE35F3}DZ/anims/workspaces/infected/infected_main/Interaction.agf"
 }
```

The three files `combat.agf`, `interaction.agf` and `locomotion.agf` sit next to it in `P:\DZ\anims\workspaces\infected\infected_main\`.

**Migration.** A custom infected workspace made for 1.29 cannot be dropped in as it is. Bohemia's stated process is to open the old graph in Workbench 1.30 and save the workspace again; they note the converter was not tested (changelog).

**The animation wall** (one loaded animation graph mod, `references/custom-infected-recipe.md`) still applies to new graphs. Inheriting the vanilla `enfanimsys` still avoids it.

## `MINDSTATE_COWER`

`DayZInfectedConstants` gains `MINDSTATE_COWER` after `MINDSTATE_FIGHT` (`P:\scripts\3_game\entities\dayzinfected.c:18`). `ZombieBase` holds the calm idle pose while cowering: the `MINDSTATE_COWER` case at `P:\scripts\4_world\entities\creatures\infected\zombiebase.c:475` calls `SetIdleState(0)`, under a comment that names sandstorm cowering. Design note: custom infected AI that switches on the mind state must handle this value, or the infected falls through the switch. More on mind states: `skills/_shared/ai/creatures.md` and `skills/_shared/ai/custom-infected.md`.

## New infected attack clips

Two heavy running attacks ship as binary clips: `P:\DZ\anims\anm\infected\attacks\erected\z_erc_run_attackl_heavy.anm` (25,534 bytes) and `P:\DZ\anims\anm\infected\attacks\erected\z_erc_run_attackr_heavy.anm` (25,264 bytes). Design note: a custom infected that replaces the combat `.agf` should expect these heavy run attack sources in vanilla 1.30.

## Human skinning: no `Lard`

Up to 1.29 (changelog, and the source project's 1.29 extract), the `Skinning` class of `SurvivorBase` included a `Lard` entry. In 1.30 `class Skinning` (`P:\DZ\characters\data\config.cpp:167`) holds only `Steaks`, `Guts`, `Bones` and `BloodInfectionSettings` (`:169` to `:187`). A recipe or mod that expects `Lard` from a human body no longer gets it.

## Surrender (no dummy item)

- `Man.IsSurrendered()` is declared at `P:\scripts\3_game\entities\man.c:67`.
- `PlayerBase.SetSurrenderState(bool newState)` is at `P:\scripts\4_world\entities\manbase\playerbase.c:2116`.
- `EmoteManager.ForceSurrenderState` is marked `[Obsolete("1.30: Use PlayerBase::SetSurrenderState instead")]` at `P:\scripts\4_world\classes\emotemanager.c:1255`.

Do not detect surrender by the class name of an item in the hands. Ask `IsSurrendered()`.

## Sandstorm protection and head gear against the sun

These sit on worn clothing, but they act on the humanoid that wears it.

- `DEF_DUST_PARTICLE_BREATH = 3` and `DEF_DUST_PARTICLE_EYES = 4` (`P:\scripts\3_game\constants.c:549` and `:550`).
- The airborne solid agents are `SILICOSIS = 512` and `EYES_IRRITATION = 1024` in `eAgents` (`P:\scripts\3_game\enums\eagents.c:14` and `:15`).
- In `PluginTransmissionAgents`, the `AGT_AIRBOURNE_SOLID` case (`P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:414`) reads protection with `GetProtectionLevelCachedEquipment`: `DEF_DUST_PARTICLE_BREATH` on the mask category for silicosis, and `DEF_DUST_PARTICLE_EYES` on eyewear, mask and night vision for eye irritation (`:420` to `:433`). The helper is at `P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:577`.
- `HeadGearProtectionAgainstSun()` in `Environment` reads the heat isolation of the item in the `HEADGEAR` slot (`P:\scripts\4_world\classes\environment\environment.c:2037`).
- Heat path: `HeatComfortMdfr` feeds `ThermalBiasHandler` (`P:\scripts\4_world\classes\playermodifiers\modifiers\heatcomfortmdfr.c:42`). `HeatStrokeMdfr` has four stage thresholds, `STAGE_THRESHOLDS` `{0.0, 0.4, 0.6, 0.85}` (`P:\scripts\4_world\classes\playermodifiers\modifiers\diseases\heatstroke.c:4`), used by `HeatStrokePhase1Mdfr` to `HeatStrokePhase4Mdfr` in the same file. The dust diseases are `SilicosisMdfr` and `IrritatedEyesMdfr` (`silicosis.c` and `irritatedeyes.c` in the same folder).

Design note: a custom mask or helmet for a humanoid must carry those protection types, or the sandstorm agents ignore it. Clothing slot and protection rules are in `skills/_shared/wearables/references/protection-and-insulation.md` and the dayz-clothing skill.

## Bone indices

See the last section of `references/character-rigging.md`. In short: the changelog says the 250-bone cap is gone and the XML `index` is unused; names must match the `.xob`.

## Checklist for a 1.30 character mod

- Keep inheriting `ZombieMaleBase` or `ZombieFemaleBase`, or a 1.30 female soldier base.
- Custom infected workspace saved again in Workbench 1.30.
- A replaced survivor body keeps or overrides the `ragdoll` path (`references/character-ragdoll.md`).
- Nothing expects `Lard` from human `Skinning`.
- Masks and eyewear carry the dust protection types when the character should resist sandstorms.
- Infected AI patches handle `MINDSTATE_COWER`.
- No hand-written bone `index` values in `skeletons.anim.xml`.
- `EmoteManager.ForceSurrenderState` replaced by `PlayerBase.SetSurrenderState` and `IsSurrendered`.
