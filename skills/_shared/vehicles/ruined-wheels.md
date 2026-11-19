# Ruined wheels

How a mod wheel swaps to its ruined model, which script and config it needs on DayZ 1.29 and 1.30, why no repair rule is needed, and how to size and seal a flat tyre model.

Measured in game on a test vehicle: the swap, the model, the slots, the in-hands pose and driving work; the sealed rim was checked offline only. The 1.30 pattern and its game runs are in `dayz-1-30-wheels.md`, section "The _Ruined twin".

## The swap is script

Declaring `MyMod_Wheel_Ruined` in `CfgVehicles` and shipping the ruined model is not enough. `CarWheel.EEHealthLevelChanged` does the swap (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:220` to `:248`) and asks `GetRuinedReplacement()` for the class to swap to.

On DayZ 1.30 the name is derived. `GetRuinedReplacement()` returns the type that `CarWheelType.SetReplacementTypes()` set when the first wheel of the class was created, `<class>_Ruined`, and that call logs an error when the config class is missing (`inventoryitem.c:215` to `:218`; `P:\scripts\4_world\entities\core\inherited\inventoryitemtype.c:17` to `:46`). A 1.30 mod wheel needs the `_Ruined` config class and an empty script class that extends `CarWheel_Ruined`. For a class whose name already contains `_Ruined`, the type returns the class's own name (`inventoryitemtype.c:22` to `:26`). Only `CarWheel`, `CarWheel_Ruined`, `MotorbikeWheel` and `MotorbikeWheel_Ruined` skip the check (`inventoryitemtype.c:12` to `:15`); the vanilla comment says each scripted base class creates a type of itself, so a mod's own scripted wheel base class with no `_Ruined` config twin logs the error too. The swap runs only when the wheel drops to ruined after `m_Initialized` is set, and replaces it with `InventoryMode.SERVER` (`inventoryitem.c:224` to `:245`).

On DayZ 1.29 `GetRuinedReplacement()` is a switch over seven vanilla class names (HatchbackWheel, CivSedanWheel, Hatchback_02_Wheel, Sedan_02_Wheel, Truck_01_Wheel, Truck_01_WheelDouble, Offroad_02_Wheel; 1.29 behaviour, not on `P:\`, which holds 1.30). Anything else returns `""` and the handler does nothing, so the wheel reaches zero health in its healthy model. Override it on each leaf class:

```c
class MyMod_Wheel_Front extends CarWheel
{ override string GetRuinedReplacement() { return "MyMod_Wheel_Front_Ruined"; } }
class MyMod_Wheel_Front_Ruined extends CarWheel_Ruined
{ override string GetReplacement() { return "MyMod_Wheel_Front"; } }
```

On 1.30 these overrides still compile and return the same names. Keep them on the leaf, never on a shared base that the ruined class also inherits, or a ruined wheel names its own class as the replacement for itself. Never use `modded class CarWheel`; it reaches every vehicle's wheels on the server.

## The ruined model needs its own proxy

A proxy ties one model file to the slots it may fill, so without one the engine cannot draw the ruined mesh once the attachment is replaced. Vanilla declares one per destroyed wheel, `inventorySlot[]` copied from the healthy proxy and only `model=` changed (`P:\DZ\vehicles\wheeled\config.cpp:23981`, `:24035`, `:24076`, `:24094` and `:24187`). Vanilla does not always match class to file name (`ProxyHatchback_02_Wheel_destroyed` draws `Hatchback_02_ruined.p3d`, `:24187` to `:24189`; `ProxyOffroad_02_Wheel_ruined` draws `Offroad_02_Wheel_destroyed.p3d`, `:24327` to `:24329`), but in a mod a mismatch crashed the client on the swap at speed, so keep them matched (`attachment-proxies.md`).

## Repair needs no config

The engine already refuses to repair a ruined wheel. The kit-in-hands action targets only objects that are not ruined (`m_ConditionTarget = new CCTNonRuined(...)`, `P:\scripts\4_world\classes\useractionscomponent\actions\singleuse\actionrepairwithtoolfromhands.c:13`), and the tyre kit recipe caps the wheel's damage level below ruined (`m_MaxDamageIngredient[1] = 3`, `P:\scripts\4_world\classes\recipes\recipes\repairwithtirekit.c:19`).

`PluginRepairing.CanRepair` is not that gate: in its check (`P:\scripts\4_world\plugins\pluginbase\pluginrepairing.c:96`) `&&` binds before `||`, so an item whose `CanBeRepairedToPristine()` returns false (the default, `P:\scripts\3_game\entities\object.c:1356`, which `CarWheel` keeps) passes it while ruined. An inherited `repairableWithKits[]` on the ruined class does no harm. Do not build a mechanism to block what the engine already refuses.

`GetReplacement()` is for diagnostics only: its one caller is under `#ifdef DIAG_DEVELOPER` (`inventoryitem.c:350` to `:366`, the debug "fix the whole car"), live in the diag game and compiled out of retail. Implement it for parity; it is not repair.

## The in-hands pose

Register the heavy in-hands IK for the ruined leaf classes too, or a ruined wheel taken in hands falls back to the one-handed pose; the profile is looked up by exact class. Vanilla registers all seven ruined car wheels (`P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercfgbase.c:876`, `:884`, `:886`, `:893`, `:903`, `:913`, `:923`) and on 1.30 the four ruined motorbike wheels (`:933`, `:935`, `:937`, `:939`), reusing the healthy `.anm` where no ruined pose exists.

## Sizing a flat tyre

A modelled flat tyre is usually collapsed over one sector, not all round. On a test vehicle the distance from the axis to the lowest point was 0.276 m, but the outer envelope sampled every 10 degrees had a median of 0.3275 and a peak of 0.3588 (measured offline on the mesh); that single number would have sunk the intact rubber up to 83 mm into the ground at other angles. Measure `max(hypot(y, z))` per angle bin and pick from the upper middle; the minima are the tears, where no rubber touches the ground anyway. Set every entry of `radiusByDamage[]` to the same value, or the inherited healthy curve gives the ruined wheel its smallest entry.

## Sealing the rim

Geometry inherited from the healthy wheel is one sided, and the tear exposes the back of the rim, so the player sees through the wheel. Per-face flags cannot fix it: binarize drops them (`skills/dayz-p3d-audit/references/winding-diagnostics.md`). Duplicate only the exposed part with reversed twins. On a test vehicle, `radius < 0.18` picked exactly 302 faces in both the healthy and the ruined mesh, which made the cut a boundary of the mesh rather than a guess. `py3d.LOD.make_double_sided()` doubles the whole LOD; reuse its normal pool deduplication with a face filter.

Check it with a ray test that culls before the depth test: when two coincident twins tie on distance and either faces the camera, the pixel is drawn. A checker that just takes the nearest hit reports the fix as a regression. Offline over 14 directions, the healthy wheel showed 0 see-through hits, the delivered ruined model 1361, and the patched one 0; not yet looked at in game.
