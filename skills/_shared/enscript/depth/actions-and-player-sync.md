# Actions and player sync internals

How vanilla registers actions and measures their reach, and how player stamina, synced modifiers, stats and agents travel to the client. Recipes, the energy manager and the damage path are in `../references/api_recipes_energy_damage.md`.

## How actions are registered

- `AddAction(typename)` in `SetActions()` registers one shared instance per action class, looked up through `ActionManagerBase.GetAction` and filed under its input type, so many actions share one input type (`P:\scripts\4_world\entities\itembase.c:255` to `:290`). There are no actions per item instance and no way to register one while the game runs.

## How far an action reaches

- `CCTCursor` measures from the hit point of the `ObjIntersectView` raycast, which needs a View Geometry LOD. `CCTObject` measures from the target's `GetPosition()`. If an action doesn't appear and the model has no View Geometry, check that LOD first (`_shared/physics/collision-lods.md`).
- Since 1.30, `CCTCursor` and `CCTCursorInherited` also measure from `MiscGameplayFunctions.GetPlayerHeadPosition`, which is the stance height, not the `Head` bone: the `distanceHead` test (`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctcursor.c:35` and `:36`), `fromPlayerHead` (`P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctcursorinherited.c:28` to `:32`), and `GetPlayerHeadPosition` itself (`P:\scripts\4_world\static\miscgameplayfunctions.c:776`). Up to 1.29 the distance came from the hit point or `GetPosition()`, often through the `Head` bone.
- `CCTLiquid` is new in 1.30 (constructor at `P:\scripts\4_world\classes\useractionscomponent\targetconditionscomponents\cctliquid.c:37`) and replaces `CCTWaterSurfaceEx` in the vanilla fill, drink and wash actions. The `Can()` signature of a custom target condition is unchanged.

## Stamina

Stamina reaches the client through a sync juncture, `SJ_STAMINA`, not through `SetSynchDirty` (`SyncStamina`, `P:\scripts\4_world\classes\staminahandler.c:831` to `:839`). For a custom stamina cost, use `DepleteStaminaEx` (`staminahandler.c:1144`). The pushing values already exist: `EStaminaModifiers.PUSH_CAR` (`P:\scripts\3_game\enums\estaminamodifiers.c:13`) and `EStaminaConsumers.PUSH` (`P:\scripts\3_game\enums\estaminaconsumers.c:12`).

## Synced modifier bits

`eModifierSyncIDs` uses nine bits, `0x1` to `0x100`; `MODIFIER_SYNC_PARTICLE_EYES` is `0x80` and `MODIFIER_SYNC_HEAT_STROKE` is `0x100` (`P:\scripts\4_world\classes\playermodifiers\modifiersmanager.c:2` to `:12`). Bits `0x200` to `0x80000000` are free for a mod's synced modifiers, so at most 32 modifiers sync in all. An older game version used only seven bits and older mods took `0x80` or `0x100`; both are vanilla bits now, so move a mod off them.

`ModifiersManager.Init()` hard codes the modifier list (`modifiersmanager.c:90`). Add a custom modifier from a `modded class ModifiersManager`.

## Player stats

`PlayerStatsPCO` stores stats by position. 1.30 added `THERMAL_BIAS = 11` to `EPlayerStats_v130` (`P:\scripts\4_world\classes\playerstats\playerstatspco.c:312` to `:326`; `EPlayerStats_current` at `:356`). A custom stat in a `modded PlayerStatsPCO_current` needs an index above 11. A mod stat at 11, valid on 1.29 where the last index was 10, now collides with `THERMAL_BIAS` and corrupts the saved stats.

## Agents

There is no `CfgAgents` config class anywhere under `P:\scripts`. Agents are script classes registered with `RegisterAgent` in `PluginTransmissionAgents` (`P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:22`).
