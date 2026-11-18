# Car parts and engine start

How a car's attachments, cargo and fuel are declared, how wheels and doors are wired as items with their slots and proxies, and why an engine will not start.

Examples come from two working third-party configs, not vanilla: a four-wheel-drive car built from scratch ("the example 4x4") and a quadbike mod ("the reference quad"). The rest of the car's config is in `vehicle-config-and-modelcfg.md`.

## Attachments, cargo and fuel

```cpp
fuelCapacity=65; fuelConsumption=15;
attachments[]={ "CarBattery","Reflector_1_1","Reflector_2_1","CarRadiator","SparkPlug",
    "MyMod_Driver_Door","MyMod_CoDriver_Door","MyMod_Hood","MyMod_Trunk",
    "MyMod_Wheel_1_1","MyMod_Wheel_1_2","MyMod_Wheel_2_1","MyMod_Wheel_2_2","MyMod_Sparewheel" };
class Cargo { itemsCargoSize[]={10,50}; allowOwnedCargoManipulation=1; openable=0; };
class GUIInventoryAttachmentsProps
{
    class Engine  { name="$STR_attachment_Engine0";  icon="set:dayz_inventory image:cat_vehicle_engine";  attachmentSlots[]={"CarBattery","CarRadiator","SparkPlug"}; };
    class Body    { name="$STR_attachment_Body0";    icon="set:dayz_inventory image:cat_vehicle_body";    attachmentSlots[]={"Reflector_1_1","Reflector_2_1","MyMod_Driver_Door","MyMod_CoDriver_Door","MyMod_Hood","MyMod_Trunk","MyMod_Sparewheel"}; };
    class Chassis { name="$STR_attachment_Chassis0"; icon="set:dayz_inventory image:cat_vehicle_chassis"; attachmentSlots[]={"MyMod_Wheel_1_1","MyMod_Wheel_1_2","MyMod_Wheel_2_1","MyMod_Wheel_2_2"}; };
};
```

An `ObstacleGenerator` block (a cylinder shape) carves the road-block volume; it is optional. Engine start rules are below and in `fluids-and-engine.md`.

## Wheels and doors as items

Wheels and doors are separate items fitted into slots. Each needs the item class, the slot and, to be drawn while fitted, a proxy.

A wheel item (example 4x4):

```cpp
class CarWheel;
class MyMod_Wheel: CarWheel
{
    scope=2; displayName="MyMod Wheel"; model="\MyMod\proxy\MyMod_Wheel.p3d"; weight=15000;
    inventorySlot[]={"MyMod_Wheel_1_1","MyMod_Wheel_1_2","MyMod_Wheel_2_1","MyMod_Wheel_2_2","MyMod_Sparewheel"};
    radius=0.451; width=0.142;
    radiusByDamage[]={0,0.451, 0.3,0.3, 0.9998,0.25, 0.9999,0.2};
    tyreOffroadResistance=0.75; tyreGrip=0.8; tyreRollResistance=0.015;
    rotationFlags=8; repairableWithKits[]={6}; repairCosts[]={30};
};
```

`tyreGrip` and `tyreRollResistance` set the feel: the reference quad uses 2.8 and 0.015, the example 4x4 0.8 and 0.015. `radius` must agree with the wheel model's Memory points (`vehicle-geometry-and-mass.md`) or the wheel never touches the ground.

Custom slots are registered once in `CfgSlots` (vanilla slots such as `CarBattery` need nothing). Names are `<side>_<axle>`, as on vanilla (the truck's front axle holds `Truck_01_Wheel_1_1` and `Truck_01_Wheel_2_1`, `P:\DZ\vehicles\wheeled\config.cpp:18589` and `:18594`):

```cpp
class CfgSlots
{
    class Slot_MyMod_Wheel_1_1 { name="MyMod_Wheel_1_1"; displayName="Front Left Wheel"; selection="wheel_1_1"; ghostIcon="wheel"; };
};
```

The example 4x4's config has no `CfgSlots` block for its wheel slots; whether they are defined elsewhere in that mod or registered by the engine is not checked, so register custom slots.

The proxy that draws the part while fitted (`attachment-proxies.md` has the naming rule):

```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;
    class ProxyVehiclePart: ProxyAttachment { scope=2; simulation="ProxyInventory"; autocenter=0; animated=0; shadow=1; reversed=0; };
    class ProxyMyMod_Wheel: ProxyVehiclePart { model="\MyMod\proxy\MyMod_Wheel.p3d"; inventorySlot[]={"MyMod_Wheel_1_1","MyMod_Wheel_2_1"}; };
};
```

Doors are `CarDoor` items (`class MyMod_Door: CarDoor`) with their own `model=` (the example 4x4 ships `Landrover_Driver_Door`, `Landrover_CoDriver_Door`, `Landrover_Hood` and `Landrover_Trunk`, each with `model="\Landrover\proxy\<Door>.p3d"`), `inventorySlot`, `hiddenSelections` and a `DamageZones` block with `Window` and `Doors` zones. The opening animation lives in `model.cfg` and `AnimationSources`, not on the item.

## Engine won't start

| Symptom | Likely cause | Fix |
|---|---|---|
| Engine cranks but never runs | Battery or plug slot missing or empty | `CarBattery` and `SparkPlug` (often `CarRadiator`) in `attachments[]` and fitted in game |
| Won't start even with a spark plug | Every `IsVital*` defaults to true (`P:\scripts\3_game\vehicles\transport.c:404` to `:417` for plugs and fuel tank; `P:\scripts\4_world\entities\vehicles\carscript.c:2201` to `:2209` for belt and radiator), so a bare `CarScript` also demands a glow plug (`carscript.c:1783`) | Petrol: return false from `IsVitalGlowPlug()` (`P:\scripts\4_world\entities\vehicles\inheritedcars\civiliansedan.c:370`). Diesel: return false from `IsVitalSparkPlug()` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:415`). Declare only the plug you use. |
| Engine drowns at spawn | No `drown_engine` memory point, so it sits at 0,0,0 | Add it at the engine |
| `unknown animation source damper` | Damper source missing | Add all four (`vehicle-config-and-modelcfg.md`, section "`AnimationSources`") |
| Revs with no torque or stalls oddly | `torqueCurve[]` does not start and end at 0 Nm, or rpm bands out of order | Start and end the curve at 0; keep `rpmIdle < rpmMin < rpmClutch < rpmRedline` |
| Steers but wheels do not spin | `animRotation` not wired in `model.cfg`, or no `wheel_X_Y_axis` | `vehicle-modelcfg-animations.md` |

Every simulation value can be watched live in the diag game: hold Win and Alt for the diag menu, then Game, Vehicles, Simulation.

`OnDebugSpawn` must create parts by class name, not slot name. Vanilla wheel and door slots differ from their classes: `HatchbackWheel` fills `NivaWheel_1_1` (`P:\DZ\vehicles\wheeled\config.cpp:853` to `:862`), `HatchbackDoors_Driver` fills `NivaDriverDoors` (`:908` to `:917`); only engine parts such as `CarBattery` and `SparkPlug` share a name with their slot. Vanilla calls `GetInventory().CreateInInventory("HatchbackWheel")` (`P:\scripts\4_world\entities\vehicles\inheritedcars\offroadhatchback.c:472` to `:475`) and fills fluids with `FillUpCarFluids()` (`carscript.c:2561`), which fills fuel, coolant and oil; call it, or add `Fill(CarFluid.FUEL, GetFluidCapacity(CarFluid.FUEL))` and `COOLANT` when `IsVitalRadiator()`. Pass the class (`MyMod_Wheel_Front`), never the slot (`MyMod_Wheel_1_1`). `OnDebugSpawn` does not run when a headless test mission creates the car (measured in game), so attach parts by hand there, or "no wheels, won't start" is a false result.
