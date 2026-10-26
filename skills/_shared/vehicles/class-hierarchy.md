# Vehicle class hierarchy

Which config parent and script class a new car, boat or helicopter starts from, which addon it requires, and which script overrides it cannot skip.

## The two trees

Every vehicle exists twice: once as a config class in `CfgVehicles` and once as a script class with the same name. The config tree sets the native simulation through `simulation=`; the script tree adds DayZ behavior.

| Kind | Config parent | `simulation` | Script chain |
|---|---|---|---|
| Car | `CarScript: Car` (`P:\DZ\vehicles\wheeled\config.cpp:236`) | `"car"` (`P:\bin\config.cpp:1429`) | `Transport` (`P:\scripts\3_game\vehicles\transport.c:66`), `Car` (`car.c:87`), `CarScript` (`P:\scripts\4_world\entities\vehicles\carscript.c:94`) |
| Boat | `BoatScript: Boat` (`P:\DZ\vehicles\water\config.cpp:17`) | `"boat"` (`P:\bin\config.cpp:1455`) | `Transport`, `Boat` (`P:\scripts\3_game\vehicles\boat.c:28`), `BoatScript` (`P:\scripts\4_world\entities\vehicles\boatscript.c:41`) |
| Helicopter | `Helicopter: Air` (`P:\bin\config.cpp:1563`) | `"helicopter"` (`P:\bin\config.cpp:1568`) | `Transport`, `Helicopter` (`P:\scripts\3_game\vehicles\helicopter.c:9`), `HelicopterAuto` (`:14`), `HelicopterScript` (`P:\scripts\4_world\entities\vehicles\helicopterscript.c:4`) |

`Transport` itself is `class Transport: All` with `simulation="transport"` (`P:\bin\config.cpp:1404`). Motorbikes also branch from `Transport` (`P:\bin\config.cpp:1481`, `P:\scripts\3_game\vehicles\motorbike.c`) but are outside this pack.

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
