# Script changes in DayZ 1.30

What changed for Enforce Script in DayZ 1.30, what breaks in a mod written for 1.29, and what to write instead. Inventory changes are in `dayz-1-30-inventory.md` and action system changes in `dayz-1-30-actions.md`.

The citations are to the 1.30 scripts on `P:\`. A later 1.30 build can move a line; find the symbol by name (see `../references/game_builds.md`).

## What breaks in a 1.29 mod

| 1.29 code | What happens in 1.30 | Write instead | Where |
|---|---|---|---|
| `override void OnCEUpdate()` | Obsolete and empty; central economy work never runs | `OnCEIterate(float currentTime, float elapsedTime)` | below |
| `modded class DayZPlayerInventory` overriding `ProcessInputData` | Not called in retail, and the modded class does not compile | Watch finished moves in `ItemBase.EEItemLocationChanged`; no moddable way to reject a command is known | `dayz-1-30-inventory.md` |
| `TakeEntityToCargo*`, `TakeEntityAsAttachment*` | Obsolete | The `Target*` takes | `dayz-1-30-inventory.md` |
| `ActionFillBottleBase` | Obsolete and missing from `RegisterActions` | `ActionObtainLiquidBase` | `dayz-1-30-actions.md` |
| `ItemBase.m_ItemActionOverrides` | Compile error | `EntityAI.OverrideActionAnimation` | `dayz-1-30-actions.md` |
| `World.Is3rdPersonDisabled()` | Obsolete; `VEHICLES_ONLY` is not a bool | `GetThirdPersonViewMode()` | below |
| Hard coded `UA_AM_*` numbers | `UA_AM_INIT = 14` moved the later values | The constants | `dayz-1-30-actions.md` |
| Hand moves on a surrendered player | `HandGuardIsNotSurrendered` rejects them | | `dayz-1-30-inventory.md` |
| `GetNoiseReductionByWeather()` | Still compiles, obsolete; AI damping is native | `GetNoiseReductionByWeatherEx(object)` for a HUD | below |
| Storage version `142` | Now `144` | `GAME_STORAGE_VERSION` | below |
| A recipe that replaces its ingredient | No longer copies the ingredient's health | Set `m_ResultInheritsHealth` | `dayz-1-30-actions.md` |
| Fill and drink targets on `CCTWaterSurfaceEx` | Replaced | `CCTLiquid` | `dayz-1-30-actions.md` |
| `override void Update()` on `ActionTargetsCursor` | Compile error | `Update(bool fullUpdate = true)` | `dayz-1-30-actions.md` |
| `v.Cross(w)` | Gone in the 1.30 stable release | The three lines inline | below |

## Central economy tick

`EntityAI.OnCEUpdate()` had no time arguments in 1.29. In 1.30 it is an empty `[Obsolete("1.30: Use OnCEIterate(float currentTime, float elapsedTime) instead")]` (`P:\scripts\3_game\entities\entityai.c:4924`), and the live tick is:

```c
void OnCEIterate(float currentTime, float elapsedTime)   // P:\scripts\3_game\entities\entityai.c:3904
{
	ProcessVariables(elapsedTime);
	ConstructionBasic constructionComponent = GetConstructionBasic();
	if (constructionComponent && ConstructionBasic.CanConstructionDecay() && GetAllowDamage())
		constructionComponent.ProcessConstructionDecay(elapsedTime);
}
```

Rename the override to `OnCEIterate(float currentTime, float elapsedTime)` and call `super.OnCEIterate(currentTime, elapsedTime)`.

## Storage version

`static int GAME_STORAGE_VERSION = 144;` (`P:\scripts\3_game\global\game.c:5`); 1.29 had `142`. `CGame` still passes it to `StorageVersion` (`:50`). Never compare `g_Game.SaveVersion()` against a hard coded `142`. The stream layout is in `_shared/persistence/dayz-1-30-persistence.md`.

## Third person view

`proto native ThirdPersonMode GetThirdPersonViewMode();` (`P:\scripts\3_game\global\world.c:177`) replaces `Is3rdPersonDisabled()`, now `[Obsolete]` (`:291`). Vanilla's obsolete message spells it "thrid". The enum is `DISABLED`, `ENABLED`, `VEHICLES_ONLY` (`:301`). Compare against `ThirdPersonMode.ENABLED` or `VEHICLES_ONLY`, never treat it as a bool.

## Weather noise

Both methods still exist. `GetNoiseReductionByWeather()` is `[Obsolete("Use Weather.GetNoiseReductionByWeatherEx instead!")]` (`P:\scripts\3_game\weather.c:454`), and `GetNoiseReductionByWeatherEx(notnull Object object)` is itself obsolete: "1.30: AI noise dampening is now done natively via AIParams config parameters. Kept for HUD and old mods." (`:407`). Vanilla still calls the `Ex` version from `NoiseAIEvaluate` (`P:\scripts\4_world\static\sensesaievaluate.c:23`). Use it only for a HUD.

## Vector, array and enum helpers

`vector.Cross(vector v)` is on `P:\` (`P:\scripts\1_core\proto\enconvert.c:239` to `:246`), in the 1.30 experimental and early builds. No script of the 1.30 stable release declares it, and 1.29 never had it, so a call has nothing to bind to there. Write its body inline:

```c
float x = a[1] * b[2] - a[2] * b[1];
float y = a[2] * b[0] - a[0] * b[2];
float z = a[0] * b[1] - a[1] * b[0];
vector cross = Vector(x, y, z);
```

- `array<T> Slice(int from, int to)` (`P:\scripts\1_core\proto\enscript.c:720`) includes `to`: it loops while `i <= to && i < Count()`.
- `typename.EnumFlagsToString` is at `enconvert.c:614`; `EnumTools.EnumFlagsToString` (`:704`) forwards to it.

## Run once, render frames and simulation

- `class DoOnce` keeps a static `map<string, bool>` (`P:\scripts\3_game\doonce.c:1`). `DoOnce.Run(string key, Class target, string fnName, Param params = null)` (`:12`) calls `g_Game.GameScript.CallFunctionParams` once per key (`:21` to `:27`).
- `proto native bool IsFirstRenderFrame();` (`P:\scripts\3_game\dayzplayer.c:1186`) is true on the first player tick of a render frame. Vanilla's comment: below 30 FPS the player can tick several times in one frame, and work with no visible effect can skip the extra ticks.
- `DisableSimulation(bool disable)` and `GetIsSimulationDisabled()` (`P:\scripts\3_game\entities\entity.c:3`) are not new; 1.29 had them.

## Migration checklist

- `OnCEIterate(currentTime, elapsedTime)` with `super`.
- Inventory: watch finished moves through `ItemBase.EEItemLocationChanged`; use the `Target*` takes.
- `AddAction(ActionObtainLiquidBase)`; `EntityAI.OverrideActionAnimation` for item and target.
- Info actions: `InitInfoData` and `CanBeStarted()` returning false; `new CCTLiquid(mask, ...)`; `GetPlayerHeadPosition`.
- `GetThirdPersonViewMode() == ThirdPersonMode.ENABLED`; a weather HUD reads `GetNoiseReductionByWeatherEx(object)`.
- No `vector.Cross`; `array.Slice` and `EnumFlagsToString` are available; client catch up with `IsFirstRenderFrame()`; storage version `144`.
- Recipes with `m_ResultReplacesIngredient` set `m_ResultInheritsHealth`; bind `UAToggleVehicleLights` and `UAUICodeLock*`; never hard code `UA_AM_*`.
