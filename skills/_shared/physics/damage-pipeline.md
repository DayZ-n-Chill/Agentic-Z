# Damage pipeline

Covers what happens after a contact decides to deal damage: the calls that deal and read damage, the order of the `EEHitBy` callbacks, damage zones, bleeding, shock and the hit animation. When and how hard a vehicle hits a player (`RegisterTransportHit`) is in `contact.md`; this file starts where that one calls `ProcessDirectDamage`.

The flow is: a source calls `ProcessDirectDamage` (native), the engine applies the `CfgAmmo` class's `DamageApplied` values to the target's zones, then calls `EEHitBy` on the server, and the script side adds shock, bleeding and the hit animation. Armor and clothing reduce the damage inside the engine before `EEHitBy`; the armor keys are in the wearables pack (`skills/_shared/wearables/references/protection-and-insulation.md`).

## Dealing damage

`ProcessDirectDamage(int damageType, EntityAI source, string componentName, string ammoName, vector modelPos, float damageCoef = 1.0, int flags = 0)` is on `Object` (`P:\scripts\3_game\entities\object.c:1138`).

- `componentName` is the damage zone, not a model component. The vanilla doc says "which 'DamageZone' was hit (NOT a component name, actually!)" (`P:\scripts\3_game\entities\object.c:1132`). An empty string is the global zone.
- `damageCoef` multiplies every damage value of the ammo class.
- `flags` takes `ProcessDirectDamageFlags`: `ALL_TRANSFER` (the default), `NO_ATTACHMENT_TRANSFER`, `NO_GLOBAL_TRANSFER` and `NO_TRANSFER`, which is both (`P:\scripts\3_game\entities\object.c:1-7`).
- `damageType` takes `DamageType`: `CLOSE_COMBAT`, `FIRE_ARM`, `EXPLOSION`, `STUN` and `CUSTOM` (`P:\scripts\3_game\damagesystem.c:10-17`). `STUN` is marked "unused atm" in the only script that names it (`P:\scripts\4_world\plugins\pluginbase\pluginadminlog.c:293`). The doc comment and `RegisterTransportHit` use the engine names `DT_CUSTOM` and the like (`P:\scripts\3_game\entities\object.c:1130`, `P:\scripts\3_game\entities\entityai.c:4153`).

The other ways in, all on `DamageSystem` (`P:\scripts\3_game\damagesystem.c:20-25`):

| Call | Use |
|---|---|
| `CloseCombatDamage(source, target, componentIndex, ammo, worldPos, flags)` and `CloseCombatDamageName(..., componentName, ...)` | Melee hits by component |
| `ExplosionDamage(source, directHitObject, ammo, worldPos, damageType)` | Damage in the radius the ammo defines; vanilla passes `null` as the direct hit, for example `"Explosion_40mm_Ammo"` (`P:\scripts\3_game\dayzgame.c:3781`), and destructibles call it from `DealExplosionDamage` (`P:\scripts\3_game\effects\destructioneffects\destructioneffectbase.c:50-52`) |
| `ResetAllZones(entity)` | Health, Shock and Blood to their maximum on every zone (`P:\scripts\3_game\damagesystem.c:138`) |

`GetDamageZoneMap` and `GetDamageZoneFromComponentName` turn a component into a zone name (`P:\scripts\3_game\damagesystem.c:27`, `:76`). There is no `ProcessIndirectDamage` and no global `DealDamage` in script.

Area damage triggers deal damage the same way, with the default ammo `"MeleeDamage"` (`P:\scripts\4_world\classes\areadamage\areadamage.c:30`; `P:\scripts\4_world\classes\areadamage\areadamagenew\damagecomponents\areadamagecomponent.c:21`).

## Reading and setting health directly

These skip the ammo system, so no `EEHitBy`, hit animation or bleeding follows. All on `Object` in `P:\scripts\3_game\entities\object.c`:

| Call | Line | Notes |
|---|---|---|
| `IsDamageDestroyed()` | `:981` | Health is 0 or less |
| `GetHealth(zone, type)`, `GetHealth01`, `GetMaxHealth` | `:994`, `:1001`, `:1008` | Empty zone is global; empty type is the main health |
| `SetHealth(zone, type, value)`, `AddHealth`, `DecreaseHealth` | `:1015`, `:1027`, `:1034` | `AddHealth` with a negative value subtracts |
| `SetHealth01`, `SetHealthMax`, `SetHealthLevel` | `:1100`, `:1105`, `:1087` | Script helpers over `SetHealth` |
| `GetHealthLevel(zone)` | `:1171` | 0 pristine to 4 ruined (`STATE_PRISTINE` to `STATE_RUINED`, `P:\scripts\3_game\constants.c:909-913`) |

The health types are `"Health"`, `"Blood"` and `"Shock"`. Vanilla reads a player's global blood from the zone `"GlobalHealth"` (`P:\scripts\4_world\entities\manbase\playerbase.c:5599`). `MiscGameplayFunctions.DealAbsoluteDmg(item, dmg)` is a helper that calls `DecreaseHealth(dmg, false)` for tools that wear with use (`P:\scripts\4_world\static\miscgameplayfunctions.c:1730-1732`).

## The callbacks, in order

| Callback | Runs | Source |
|---|---|---|
| `EEHitBy(TotalDamageResult damageResult, int damageType, EntityAI source, int component, string dmgZone, string ammo, vector modelPos, float speedCoef)` | On the server, after the engine applied the damage | `P:\scripts\3_game\entities\entityai.c:1143` |
| `EEHitByRemote(damageType, source, component, dmgZone, ammo, modelPos)` | "called only on the client who caused the hit"; no damage result | `P:\scripts\3_game\entities\entityai.c:1152-1153` |
| `EEHealthLevelChanged(oldLevel, newLevel, zone)` | When a zone changes health level; ruined on the global zone calls `OnDamageDestroyed(oldLevel)`, then `AttemptDestructionBehaviour` | `P:\scripts\3_game\entities\entityai.c:1043`, `:1058`, `:1066` |
| `EEKilled(Object killer)` | On the server at death; fires `m_OnKilledInvoker` | `P:\scripts\3_game\entities\entityai.c:1104-1107` |
| `EEDelete(EntityAI parent)` | When the entity leaves the world | `P:\scripts\3_game\entities\entityai.c:946` |

`TotalDamageResult` gives `GetDamage(zoneName, healthType)` and `GetHighestDamage(healthType)` (`P:\scripts\3_game\damagesystem.c:1-5`).

For a player, each override calls `super` first, so the bodies run in this order:

1. `EntityAI.EEHitBy` fires `m_OnHitByInvoker` (`P:\scripts\3_game\entities\entityai.c:1143-1146`). Subscribe to it instead of overriding when you only need to listen.
2. `DayZPlayerImplement.EEHitBy` resets `m_TransportHitRegistered` and picks the hit or death animation (`P:\scripts\4_world\entities\dayzplayerimplement.c:1563-1567`).
3. `PlayerBase.EEHitBy` (`P:\scripts\4_world\entities\manbase\playerbase.c:1255`) starts bleeding (`:1292`), turns shock into health damage when the ammo's `DamageApplied transferShockToDamage` is 1 (`:1313-1314`), checks broken legs on the leg and foot zones (`:1324`) and forces a shock sync (`m_ShockHandler.CheckValue(true)`, `:1376`).

Items take their own branch: `ItemBase.EEHitBy` damages a random cargo item or attachment of clothing, containers and tents (`P:\scripts\4_world\entities\itembase.c:1450-1455`).

A ruined plastic explosive does not go off. `ExplosivesBase.EEKilled` calls `InitiateExplosion()` (`P:\scripts\4_world\entities\explosivesbase.c:72-77`), but `Plastic_Explosive.EEKilled` overrides it without `super`, with the comment "do not call super from ExplosivesBase" (`P:\scripts\4_world\entities\explosivesbase\plastic_explosive.c:27-32`). It explodes only from `OnActivatedByItem`, when armed and triggered by its paired remote detonator, and that path returns early once the charge is already ruined (`:236-258`). `InitiateExplosion()` is `protected` (`P:\scripts\4_world\entities\explosivesbase.c:172`), so a mod that wants a shot charge to blow reaches it from a `modded class Plastic_Explosive`, for example in its own `EEKilled`. No `Detonate` method exists in the scripts.

## Hit zones

- A zone is a class under `DamageSystem` `DamageZones` in config. Its `componentNames[]` lists the model selections it covers, and `transferToZonesNames[]`, `transferToZonesCoefs[]` and `Health` `transferToGlobalCoef` pass damage on. Script reads only `transferToGlobalCoef`, in a repair helper marked "hack; mirrors current config setup" (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionrepairtent.c:155`, `:167`). How a model's selections must match `componentNames[]` is in `collision-lods.md`.
- The player's zones are `Head`, `Brain`, `Torso`, the arms, hands, legs and feet (`class DamageZones`, `P:\DZ\characters\data\config.cpp:421`; `Brain` at `:501`, `Torso` at `:572`). `Head` lists `"dmgZone_head"` (`:488-491`).
- `fatalInjuryCoef` is set per zone, 0.1 on `Head` and 1 on `Brain` (`P:\DZ\characters\data\config.cpp:492`, `:570`). No script reads it; what the engine does with it is not visible.
- Script names zones in a few places: `"Brain"` marks a headshot kill (`P:\scripts\4_world\entities\dayzplayerimplement.c:1592`), `"Torso"` and `"Head"` allow the full body hit animation (`:1512`), and the arms are the upper bleeding sources in `m_BleedingSourcesUp` (`P:\scripts\4_world\entities\manbase\playerbase.c:545`, `:549`).

## Bleeding and shock

- `BleedingSourcesManagerServer.ProcessHit` (`P:\scripts\4_world\classes\bleedingsources\bleedingsourcesmanagerserver.c:167`) reads the ammo's `DamageApplied bleedThreshold` and `type` (`:170`, `:171`) and rolls `BleedChanceData.CalculateBleedChance` (`:177`). The source types are `eBleedingSourceType` (`P:\scripts\4_world\classes\bleedingsources\bleedingsource.c:1`). Get the manager with `GetBleedingManagerServer()` (`P:\scripts\4_world\entities\manbase\playerbase.c:2973`).
- `ShockHandler` (`P:\scripts\4_world\classes\shockhandler.c:1`) has `Update` (`:44`), `GetCurrentShock` (`:82`), `SetShock` (`:92`) and `CheckValue` (`:106`). `PlayerBase` holds it as `m_ShockHandler` with no getter (`P:\scripts\4_world\entities\manbase\playerbase.c:99`).
- `GiveShock(shock)` is `AddHealth("", "Shock", shock)` (`P:\scripts\4_world\entities\manbase\playerbase.c:3947-3949`). Unconsciousness follows from `m_ShouldBeUnconscious` (`P:\scripts\4_world\entities\dayzplayerimplement.c:125`).

## The hit animation

`EvaluateDamageHitAnimation` reads the ammo's `hitAnimation` (`P:\scripts\4_world\entities\dayzplayerimplement.c:1528`). For `DamageType.CUSTOM`, 1 plays the full body animation (`:1529-1530`); otherwise there is no animation unless the ammo is `"HeatDamage"` and the player is not swimming or in a vehicle (`:1531`).

`TransportHit` is the vanilla ammo that gives damage by speed with a hit animation: `class TransportHit: MeleeDamage` with `hitAnimation=1`, `doPhxImpulse=1`, and `DamageApplied` `Health` 1, `Blood` 0, `Shock` 0 (`P:\DZ\weapons\melee\config.cpp:52-72`). A mod that wants other blood or shock values defines its own `CfgAmmo` class with the same shape.
