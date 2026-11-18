# DayZ 1.30 wheels

How 1.30 swaps a ruined wheel for its `_Ruined` twin, what a mod wheel needs so the swap works without errors, and the four tyre fields every 1.30 wheel declares.

Every line cites the 1.30 scripts and config on `P:\` unless it is marked 1.29. In-game results were measured on two quad mods and are mod behaviour. The rest of the 1.30 changes are indexed in `dayz-1-30-vehicles.md`.

## The _Ruined twin

1.29 picked a ruined wheel's replacement with a `switch` over the vanilla wheel names (1.29 `InventoryItem.c:214` to `:248`), so a mod wheel stayed as it was and nothing was logged. 1.30 derives the name. When the first entity of a wheel type is created, `CarWheelType.SetReplacementTypes()` takes `<class>_Ruined` as its ruined type, or the intact name for a `_Ruined` class, and calls `ErrorEx` when that config class does not exist (`P:\scripts\4_world\entities\core\inherited\inventoryitemtype.c:17` to `:46`). `CarWheel.EEHealthLevelChanged()` then swaps a wheel that reaches `STATE_RUINED` for that class through `ReplaceWheelLambda` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:220` to `:248`).

Give each wheel a config class that inherits the intact wheel, with the ruined tyre values:

```cpp
class MyMod_Wheel_Front_Ruined: MyMod_Wheel_Front
{
	scope = 2;
	radius = 0.224;
	tyreOffroadResistance = 0.1;
	tyreGrip = 0.4;
	tyreRollResistance = 0.32;
	tyreRoughness = 0.2;
	tyreLongitudinalFriction = 0.25;
	tyreLateralFriction = 4.95;
};
```

and a script class that extends `CarWheel_Ruined`, as vanilla does for its own wheels (`inventoryitem.c:449` to `:468`):

```c
class MyMod_Wheel_Front_Ruined extends CarWheel_Ruined {};
```

Vanilla also registers the two handed carry profile of each ruined class (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:892` and `:893`). A mod that registers its wheels in `ModItemRegisterCallbacks.RegisterHeavy` adds the `_Ruined` names there too.

On a 1.30 diag server and client, a test quad without the twins raised, for the first front and the first rear wheel of each session, `[CarWheelType::SetReplacementTypes] :: [ERROR] :: No config class entry for wheel entity '<class>_Ruined'` as a `Virtual Machine Exception`, on both sides. With the twins there was none. Both classes spawned with their own script class (`entities_query` reports it as `classname`; an intact wheel with no script class of its own reads `CarWheel`), and each fitted the slots of its own axle and was refused by the other's. The swap itself was not seen: no test tool sets an item's health, and a grenade 1.5 m from a loose wheel took it only to 97 percent.

`PlayWheelExlosionSound()` picks the burst sound by vanilla class name (`inventoryitem.c:297` to `:320`), so a mod wheel bursts silently unless its `_Ruined` class overrides that method. Vanilla spells the method `Exlosion`; keep that spelling.

## A 1.29 mod that already had twins

A 1.29 mod that shipped `_Ruined` twins and returned them from overrides of `CarWheel.GetRuinedReplacement()` and `CarWheel_Ruined.GetReplacement()` still compiles on 1.30. Both methods remain and now return the names `SetReplacementTypes()` derived (`inventoryitem.c:215` to `:218` and `:342` to `:345`), which are the names those overrides return anyway.

A second quad mod dropped its four overrides and kept empty script classes, as vanilla does. In game on a 1.30 diag build its four wheel classes reported their own script class in `entities_query`, no `SetReplacementTypes` error was logged, each ruined wheel fitted the two slots of its own axle and was refused by the other's, and the fitted ruined wheels showed their own torn tyre models through their proxies.

## The four new tyre fields

Every vanilla 1.30 car wheel declares `tyreType`, `tyreRoughness`, `tyreLongitudinalFriction` and `tyreLateralFriction`; a 1.29 wheel does not.

| Wheel | `tyreType` | `tyreRoughness` | `tyreLongitudinalFriction` | `tyreLateralFriction` |
|---|---|---|---|---|
| Intact car wheels | `0` | `1` | 0.85 to 1.5 | 0.95 to 1.8 |
| Truck double wheel | | | 2.5 | 2.8 |
| Ruined car wheels | | 0.2 | 0.25 or 0.35 | 4.95 |

`HatchbackWheel` is an intact example (`P:\DZ\vehicles\wheeled\config.cpp:874` to `:880`), and its ruined twin drops to `0.35` and `4.95` (`:905` and `:906`); the truck's double wheel is at `:18147` and `:18148`. Motorbike wheels do not follow these ranges; their values are in `motorbike-damage-and-wheel-config.md`.

Measured on two test quads, each with a manual gearbox and the `Offroad_02_Wheel` set (`0`, `1`, `1.5`, `1.8`), driven through the test bridge:

- The first reached 46 km/h in about 4.6 s and 71 km/h in 8.4 s on grass, and turned about 77 degrees in 2.8 s at full lock and 40 km/h without rolling over.
- The second reached 34 to 39 km/h in 2.8 s, turned about 65 degrees in 2.3 s at full lock and 38 to 47 km/h without rolling over, and stopped from about 38 km/h in about 1.6 s.
