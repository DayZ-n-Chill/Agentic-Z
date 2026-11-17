# Vehicle class hierarchy

Which config parent and script class a new car, boat or helicopter starts from, which addon it requires, and which script overrides it cannot skip.

## The two trees

Every vehicle exists twice: once as a config class in `CfgVehicles` and once as a script class with the same name. The config tree sets the native simulation through `simulation=`; the script tree adds DayZ behavior.

| Kind | Config parent | `simulation` | Script chain |
|---|---|---|---|
| Car | `CarScript: Car` (`P:\DZ\vehicles\wheeled\config.cpp:236`) | `"car"` (`P:\bin\config.cpp:1429`) | `Transport` (`P:\scripts\3_game\vehicles\transport.c:66`), `Car` (`car.c:87`), `CarScript` (`P:\scripts\4_world\entities\vehicles\carscript.c:94`) |
| Boat | `BoatScript: Boat` (`P:\DZ\vehicles\water\config.cpp:17`) | `"boat"` (`P:\bin\config.cpp:1455`) | `Transport`, `Boat` (`P:\scripts\3_game\vehicles\boat.c:28`), `BoatScript` (`P:\scripts\4_world\entities\vehicles\boatscript.c:41`) |
| Helicopter | `Helicopter: Air` (`P:\bin\config.cpp:1563`) | `"helicopter"` (`P:\bin\config.cpp:1568`) | `Transport`, `Helicopter` (`P:\scripts\3_game\vehicles\helicopter.c:9`), `HelicopterAuto` (`:14`), `HelicopterScript` (`P:\scripts\4_world\entities\vehicles\helicopterscript.c:4`) |

`Transport` itself is `class Transport: All` with `simulation="transport"` (`P:\bin\config.cpp:1404`). Motorbikes also branch from `Transport` (`P:\bin\config.cpp:1481`, `P:\scripts\3_game\vehicles\motorbike.c`); they have their own files in this pack (`motorbikes.md`).

## Vanilla cars to inherit from

All of these are in `P:\DZ\vehicles\wheeled\config.cpp` and each has a script class of the same name in `P:\scripts\4_world\entities\vehicles\inheritedcars\`.

| Class | Line | Notes |
|---|---|---|
| `OffroadHatchback` | `:1250` | Two doors, hood, trunk, spare wheel; `DRIVE_AWD`; spark plug. |
| `CivilianSedan` | `:5113` | Four doors (`CivSedanCargo1Doors`, `CivSedanCargo2Doors`); spark plug. |
| `Hatchback_02` | `:9486` | |
| `Sedan_02` | `:13960` | |
| `Truck_01_Base` | `:18429` | `scope=0`; six wheels, `DRIVE_642`. |
| `Offroad_02` | `:20899` | Four doors (`Offroad_02_Door_1_1` to `_2_2`), `DRIVE_AWD`, automatic gearbox, glow plug; `fuelCapacity=115` (`:20980`). |

`RearDrive`, `FrontDrive`, `AllDrive` and `TruckDrive` (`:437`, `:533`, `:629`, `:734`) are drivetrain templates on `CarScript` with no model. The vanilla cars above inherit `CarScript` directly.

For a boat, the only vanilla boat is `Boat_01_ColorBase: BoatScript` (`P:\DZ\vehicles\water\config.cpp:47`, script `P:\scripts\4_world\entities\vehicles\inheritedboats\boat_01.c:1`).

## Addons to require

| Parent comes from | `requiredAddons[]` entry | Defined at |
|---|---|---|
| Any car or car part in wheeled | `DZ_Vehicles_Wheeled` | `P:\DZ\vehicles\wheeled\config.cpp:3` |
| `BoatScript`, `Boat_01_ColorBase` | `DZ_Vehicles_Water` | `P:\DZ\vehicles\water\config.cpp:3` |
| Shared parts (`GlowPlug`, `SparkPlug`, batteries) | `DZ_Vehicles_Parts` | `P:\DZ\vehicles\parts\config.cpp:3` |
| A redeclared vanilla `CfgSlots` class | `DZ_Scripts` | `P:\scripts\config.cpp:3` |

## Two ways to make a car

1. **Variant of a vanilla car** (new texture, bigger tank, retuned engine, same model). Inherit the vanilla class in config, for example `class MyMod_Offroad_02_Long: Offroad_02`. The vanilla script class already implements every override, so no script class is strictly needed; add one (`class MyMod_Offroad_02_Long extends Offroad_02 {}`) only when the behavior changes.
2. **New model.** Inherit `CarScript` (or the closest vanilla car if its seats and doors match) and write a script class with the same name. The overrides below are mandatory.

## Overrides a new vehicle must implement

`Transport` reports an error when these are not overridden (`P:\scripts\3_game\vehicles\transport.c`):

| Method | Line | Default |
|---|---|---|
| `int GetAnimInstance()` | `:662` | `Error("GetAnimInstance() not implemented")` |
| `int GetSeatAnimationType(int posIdx)` | `:682` | `Error(...)`, returns `0` |
| `int Get3rdPersonCameraType()` | `:698` | `Error(...)`; `CarScript` already overrides it (`carscript.c:2232`), so does `BoatScript` (`boatscript.c:200`) |

These return `false` by default, so a vehicle without them cannot be entered or moved around in (`transport.c`):

| Method | Line |
|---|---|
| `bool CrewCanGetThrough(int posIdx)` | `:724` |
| `bool CanReachSeatFromSeat(int currentSeat, int nextSeat)` | `:733` |
| `bool CanReachDoorsFromSeat(string pDoorsSelection, int pCurrentSeat)` | `:751` |

`CarScript` overrides `CanReachSeatFromDoors` with a distance check against a door condition memory point (`carscript.c:2177`). `BoatScript` overrides the seat and door checks itself (`boatscript.c:205` to `:220`).

`GetAnimInstance()` returns a value from `VehicleAnimInstances` (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`): `CIVVAN`, `V3S`, `SEDAN`, `HATCHBACK`, `BUS`, `S120`, `MULTICAR`, `GOLF`, `HMMWV`, `ZODIAC`, `MOTO1`, `MOTO2`. There is no helicopter entry. `GetSeatAnimationType` returns a `DayZPlayerConstants.VEHICLESEAT_*` value per crew index, as `Offroad_02` does (`inheritedcars\offroad_02.c:138`).

## Worked example: variant of a vanilla car

```cpp
class CfgPatches
{
    class MyMod_Vehicles
    {
        units[] = {"MyMod_Offroad_02_Long"};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Vehicles_Wheeled"};
    };
};
class CfgVehicles
{
    class Offroad_02;
    class MyMod_Offroad_02_Long: Offroad_02
    {
        scope = 2;
        displayName = "Long range offroad";
        fuelCapacity = 160;
    };
};
```

Only the changed key is written; the simulation, crew and damage zones come from `Offroad_02`.

## Siblings, not parent and child

`Car`, `Boat` and `Motorbike` are siblings directly under `Transport` (`P:\scripts\3_game\vehicles\car.c:87`, `P:\scripts\3_game\vehicles\boat.c:28`, `P:\scripts\3_game\vehicles\motorbike.c:30`). `Transport` owns crew, get-in, flip and fuel; `Car` owns wheels, brakes and `CarFluid`; `Boat` owns the propeller, buoyancy and `BoatFluid`. A truck is a plain `CarScript` config with three axles and double wheels, not a new class (`Truck_01_Base` above). `MotorbikeScript` extends `Motorbike`, not `CarScript` (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:53`). Boats, truck double wheels and ATV slots are in `vehicle-types-boat-truck.md`.

## A config parent is not a script parent

When the config says `class X: OffroadHatchback` but the script says `class X extends MyBase` with `MyBase extends CarScript`, none of the script overrides of `OffroadHatchback` reach `X`: they live in `inheritedcars\offroadhatchback.c`, which `X` never inherits. Every hostile default listed under "Overrides a new vehicle must implement" then applies again, plus `IsVitalGlowPlug` (see `fluids-and-engine.md`). Diff your class method by method against the parent car's script file and repeat every override. Field notes: invariant 20 in `invariants-get-in-and-seats.md`.

## What DayZ 1.30 changed in the tree and in `CarScript`

Opened on this repo's `P:\`, which is a 1.30 build. The port blockers in detail, lights, horn, fluids, boats and the line drift between 1.29 and 1.30 are in `dayz-1-30-vehicles.md`.

- A third sibling exists: `class Motorbike: Transport` with `simulation="motorbike"` (`P:\bin\config.cpp:1481-1486`), scripted by `MotorbikeScript`. Two-wheel work goes to the motorbike files of this pack.
- `CarScript` is built around three components: `VehicleLightsComponent`, `VehicleHornComponent` and `VehicleVFXComponent` (`P:\scripts\4_world\entities\vehicles\carscript.c:187-189`).
- These old overrides are marked `[Obsolete]`. A 1.29 mod that overrides one still compiles, but the override is no longer called, so check each against the 1.30 file before shipping:

| Obsolete member | Line in `carscript.c` | Use instead |
|---|---|---|
| `CreateRearLight`, `CreateFrontLight` | `:2938`, `:2945` | `VehicleLightsComponent` |
| `IsVitalCarBattery`, `IsVitalTruckBattery` | `:2812`, `:2818` | `Transport.NeedElectricitySourceDevice` (`P:\scripts\3_game\vehicles\transport.c:821`) |
| `CarPartsHealthCheck` | `:2977` | `PartsHealthCheck` (`P:\scripts\3_game\vehicles\transport.c:437`; `CarScript` override at `P:\scripts\4_world\entities\vehicles\carscript.c:2121`) |
| `ForceUpdateLightsStart`, `ForceUpdateLightsEnd` | `:2806`, `:2809` | Nothing; the attribute says "no replacement". |

- `ToggleHeadlights` is gone from `P:\scripts\4_world\entities\vehicles\carscript.c` with no `[Obsolete]` stub, so a mod class that still declares `override void ToggleHeadlights()` stops the `4_World` compile.
- A car reports `NO_BATTERY` with a battery attached unless it overrides the electricity source methods: `CheckOperationalRequirements` asks `NeedElectricitySourceDevice` and then `GetBattery` (`P:\scripts\4_world\entities\vehicles\carscript.c:1768-1773`), and the `Transport` defaults are `true` for `NeedElectricitySourceDevice` and `null` for `GetElectricitySourceDevice` (`P:\scripts\3_game\vehicles\transport.c:821-829`). `CivilianSedan` overrides `GetElectricitySourceDevice` to return the `CarBattery` attachment (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:64-68`).
- Every wheel class needs a `<class>_Ruined` twin in config: without one the wheel type raises `No config class entry for wheel entity` when its first wheel is created (`P:\scripts\4_world\entities\core\inherited\inventoryitemtype.c:34-36`, where `m_RuinedType` is looked up).
- The horn actions are `ActionVehicleHornShort` and `ActionVehicleHornLong` (`P:\scripts\4_world\entities\vehicles\carscript.c:2319-2320`).
- Contact data is `VehicleContactData` with `m_Impulse` (`P:\scripts\3_game\vehicles\transport.c:1144-1148`), read in `CheckContactCache` as `data[0].m_Impulse` (`P:\scripts\4_world\entities\vehicles\carscript.c:1291`).
- Wheel classes carry `tyreRoughness`, `tyreLongitudinalFriction` and `tyreLateralFriction` (`P:\DZ\vehicles\wheeled\config.cpp:878-880`).
- `GetWeightCoef` is `1.0` in `Transport` (`P:\scripts\3_game\vehicles\transport.c:475-477`), `2.0` on `Truck_01_Base` (`P:\scripts\4_world\entities\vehicles\inheritedcars\truck_01_base.c:120-122`) and `1.5` on `Offroad_02` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:133-135`). `MotorbikeScript` only passes `GetWeightCoef()` to its dust effect (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:646`); it does not define a value.
- `HasGangedTailAndBrakeLights` is `false` in `CarScript` (`P:\scripts\4_world\entities\vehicles\carscript.c:468-470`) and `true` on `Offroad_02` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:68-70`), so switching the reverse light does not switch its brake selection off (`P:\scripts\4_world\entities\vehicles\carscript.c:2061`).
- The vehicle light key is `UAToggleVehicleLights`, set in `ToggleVehicleLightsActionInput` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849-855`); `UAToggleHeadlight` is the head torch (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:782`).
- Get-in calls `CanGetIn`, then `CrewCanGetThrough` with `IsAreaAtDoorFreeDiag`, and does call `CanReachSeatFromDoors` from script with a distance of `1.0` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36`, `:54`, `:64`).

Reported on a 1.30 port of a third-party quad (LFQuad, 1.30.164200) and not reproduced here: a script module path written with backslashes in `CfgMods` loaded none of the mod's scripts, with no error.
