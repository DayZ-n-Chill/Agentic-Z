# Helicopters

What vanilla gives you for helicopters, what it does not, and how to build a flyable one on the native base classes with your own code.

## What vanilla ships

Vanilla has the classes but no flyable helicopter. No vanilla `CfgVehicles` class uses `HelicopterScript`, and no vanilla script class extends it (Grep `P:\DZ` and `P:\scripts` for `HelicopterScript`).

| Layer | Class | Where | What it has |
|---|---|---|---|
| Native script | `Helicopter extends Transport` | `P:\scripts\3_game\vehicles\helicopter.c:9` | Nothing beyond `Transport`. |
| Native script | `HelicopterAuto extends Helicopter` | `helicopter.c:14` | Auto hover helicopter: `IsEngineOn()`, `EngineStart()`, `EngineStop()`, `IsAutohoverOn()`, `AutohoverOn()`, `AutohoverOff()` (`:17` to `:32`). |
| Script | `HelicopterScript extends HelicopterAuto` | `P:\scripts\4_world\entities\vehicles\helicopterscript.c:4` | Sets the `POSTSIMULATE` event mask; empty `EOnPostSimulate`, `OnBeforeEngineStart` (server only, returns `true`), `OnEngineStart`, `OnEngineStop` (`:6` to `:34`). |
| Native config | `Helicopter: Air` | `P:\bin\config.cpp:1563` | `simulation="helicopter"` (`:1568`), pilot view limits in `ViewPilot`, rotor selections and speeds, `class RotorLibHelicopterProperties` (`:1673`). |
| Native config | `Air: Transport` | `P:\bin\config.cpp:1507` | `fuelCapacity=1000`, `maxSpeed=400`, marker lights. |

`P:\bin\config.cpp` has no config class named `HelicopterAuto`. The `Helicopter` config class carries old rotor selection names from earlier engines (`selectionHRotorStill="velka vrtule staticka"`, `:1609`), so redeclare every selection and memory point your model uses rather than relying on the inherited ones.

## What is missing, and who writes it

Everything a player needs beyond auto hover is yours to write in the mod's own code. Never copy it from another mod.

| Need | Where it comes from |
|---|---|
| Seats and get in | `class Crew` in config as for cars (`attachments-and-crew.md`), plus `GetAnimInstance`, `GetSeatAnimationType`, `CrewCanGetThrough` and `CanReachSeatFromDoors` overrides. `Transport` errors or returns `false` without them (`class-hierarchy.md`). `VehicleAnimInstances` has no helicopter entry (`P:\scripts\4_world\entities\vehicles\vehicleaniminstances.c:1`); reuse an existing one. |
| Camera | `Get3rdPersonCameraType()` errors in `Transport` (`P:\scripts\3_game\vehicles\transport.c:698`) and `HelicopterScript` does not override it. Return `DayZPlayerCameras.DAYZCAMERA_3RD_VEHICLE` as `CarScript` does (`carscript.c:2232`). |
| Engine rules | Override `OnBeforeEngineStart` for fuel, battery or parts checks. `HelicopterScript` has no fluid or part logic. |
| Flight input | Script calls `AutohoverOn()` and `AutohoverOff()`; any control beyond the native simulation is new script, which goes to dayz-script-specialist through the config lead. |
| Actions | `HelicopterScript` registers no actions. Add get in and get out the way `CarScript.SetActions` does (`carscript.c:2313`). |
| Damage | A `DamageSystem` written fresh; none of the `CarScript` zone logic applies. |

## Starting point

```cpp
// config.cpp
class CfgVehicles
{
    class Helicopter;
    class MyMod_Heli: Helicopter
    {
        scope = 2;
        displayName = "MyMod helicopter";
        model = "\MyMod\data\heli.p3d";
    };
};
```

```c
// scripts/4_World/MyMod/Vehicles/MyMod_Heli.c
class MyMod_Heli extends HelicopterScript
{
    override int GetAnimInstance()
    {
        return VehicleAnimInstances.HATCHBACK;
    }

    override int GetSeatAnimationType(int posIdx)
    {
        if (posIdx == 0)
            return DayZPlayerConstants.VEHICLESEAT_DRIVER;

        return DayZPlayerConstants.VEHICLESEAT_CODRIVER;
    }

    override int Get3rdPersonCameraType()
    {
        return DayZPlayerCameras.DAYZCAMERA_3RD_VEHICLE;
    }
}
```

Unverified until tested in game: that the `helicopter` simulation on this config parent creates a `HelicopterAuto` native object, which `requiredAddons[]` entry the native `Helicopter` class needs (it lives in the engine's own `P:\bin\config.cpp`, not in a `DZ_` addon), and how the native hover handles mass and rotor values. Report these as unverified to the config lead and have the in-game test spawn, enter, start and hover the helicopter before calling it done.
