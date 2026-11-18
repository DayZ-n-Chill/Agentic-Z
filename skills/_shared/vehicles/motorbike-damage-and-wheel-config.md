# Motorbike damage zones and wheel classes

How the vanilla `Motorbike_01_ColorBase` lays out its `DamageSystem`, which materials each zone swaps as it takes damage, and what its wheel classes and ruined wheels set. In this file `config.cpp` alone means `P:\DZ\vehicles\singletrack\config.cpp`. The base class and the side by side key values of both bikes are in `motorbike-config-contract.md`.

## Global health

The `DamageSystem` runs from `P:\DZ\vehicles\singletrack\config.cpp:400` to `:989`. `GlobalHealth` has `hitpoints = 1000` and empty `healthLevels[]` at 1.0, 0.7, 0.5, 0.3 and 0.0.

## Damage zones

| Zone | `displayName` | `fatalInjuryCoef` | Component and memory point | Health | `transferToGlobalCoef` | Passes damage to (coefficient) | Slots (coefficient) |
|---|---|---|---|---|---|---|---|
| `Chassis` | `$STR_CfgVehicleDmg_Chassis0` | `-1` | `dmgZone_chassis` | 1000 | `0` | | None |
| `Fender` | `$STR_CfgVehicleDmg_Fender0` | `-1` | `dmgZone_fender` | 200 | `0` | | None |
| `Engine` | `$STR_CfgVehicleDmg_Engine0` | `0.001` | `dmgZone_engine`, also a memory point | 1000 | `1` | | `SparkPlug` (`0.03`) |
| `Front` | `$STR_Motorbike_Front0` | `-1` | `dmgZone_front`, also a memory point | 700 | `0` | `Engine` (`0.75`), `Fender` (`0.6`), `Chassis` (`0.8`) | `Motorbike_01_Wheel_1` (`0.5`) |
| `Reflector_1_1` | `$STR_CfgVehicleDmg_Reflector0` | `-1` | `dmgZone_lights_1_1`, also a memory point | 10 | `0` | `Front` (`1.0`) | `Reflector_1_1` (`1.0`) |
| `Back` | `$STR_Motorbike_Back0` | `-1` | `dmgZone_back`, also a memory point | 1000 | `0` | `Engine` (`0.05`), `FuelTank` (`0.3`) | `Motorbike_01_Wheel_2` (`0.1`) |
| `FuelTank` | `$STR_CfgVehicleDmg_FuelTank0` | `-1` | `dmgZone_fuelTank` | 400 | `0` | | None |

## Materials by damage level

Every zone except `FuelTank` lists its materials in `RefTexsMats[]` and swaps them through `healthLevels[]` the same way: the plain material at 1.0 and 0.7, the `_damage` material at 0.5 and 0.3, and the `_destruct` material at 0.0. All paths are under `dz\vehicles\singletrack\motorbike_01\data\`. `FuelTank` has empty levels.

| Zone | `RefTexsMats[]` |
|---|---|
| `Chassis` | `motorbike_01_colorized.rvmat`, `motorbike_01_noncolorized.rvmat` |
| `Fender` | `motorbike_01_fender.rvmat` |
| `Engine` | `motorbike_01_noncolorized.rvmat` |
| `Front` | `motorbike_01_colorized.rvmat` |
| `Reflector_1_1` | `motorbike_01_colorized.rvmat`, `motorbike_01_noncolorized.rvmat`, `motorbike_01_lights.rvmat`, `motorbike_01_glass.rvmat` |
| `Back` | `motorbike_01_colorized.rvmat`, `motorbike_01_noncolorized.rvmat`, `motorbike_01_wheel.rvmat`, `motorbike_01_lights.rvmat`, `motorbike_01_lights_rear_brake.rvmat` |

One exception: at 0.0 the `Reflector_1_1` glass takes `"hidden"` instead of a `_destruct` material, so the glass disappears when the reflector is ruined. A zone's levels look like this, from `Fender`:

```cpp
healthLevels[] = {{1.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender.rvmat"}},{0.7,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender.rvmat"}},{0.5,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender_damage.rvmat"}},{0.3,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender_damage.rvmat"}},{0.0,{"dz\vehicles\singletrack\motorbike_01\data\motorbike_01_fender_destruct.rvmat"}}};
```

## Inventory groups

`GUIInventoryAttachmentsProps` (`config.cpp:955` to `:988`) sorts the slots into three groups:

| Group | `name` | `icon` | `attachmentSlots[]` |
|---|---|---|---|
| `Engine` | `$STR_attachment_Engine0` | `set:dayz_inventory image:cat_vehicle_engine` | `SparkPlug` |
| `Body` | `$STR_attachment_Body0` | `set:dayz_inventory_additional image:motorcycle_body` | `Reflector_1_1` |
| `Chassis` | `$STR_attachment_Chassis0` | `set:dayz_inventory_additional image:motorcycle_chassis` | `Motorbike_01_Wheel_1`, `Motorbike_01_Wheel_2` |

## Wheel classes

From `config.cpp:154` to `:219`. Each wheel has a `_Ruined` child with a smaller radius, a wider contact and almost no grip:

```cpp
class Motorbike_01_Wheel_1: MotorbikeWheel
{
    scope = 2;
    displayName = "$STR_MotorbikeWheel0";
    descriptionShort = "$STR_MotorbikeWheel1";
    model = "\DZ\vehicles\singletrack\Motorbike_01\proxy\Motorbike_01_wheel_1.p3d";
    inventorySlot[] = {"Motorbike_01_Wheel_1"};
    rotationFlags = 8;
    radius = 0.29;
    width = 0.06;
    tyreType = 1;
    tyreOffroadResistance = 0.7;
    tyreRollResistance = 0.01;
    tyreGrip = 0.85;
    tyreRoughness = 1.0;
    tyreLongitudinalFriction = 0.85;
    tyreLateralFriction = 3.0;
};
class Motorbike_01_Wheel_1_Ruined: Motorbike_01_Wheel_1
{
    model = "\DZ\vehicles\singletrack\Motorbike_01\proxy\Motorbike_01_wheel_1_ruined.p3d";
    radius = 0.22;
    width = 0.2;
    tyreOffroadResistance = 0.02;
    tyreRollResistance = 0.7;
    tyreGrip = 0.25;
    tyreRoughness = 1.0;
    tyreLongitudinalFriction = 0.5;
    tyreLateralFriction = 0.5;
};
class Motorbike_01_Wheel_2: MotorbikeWheel
{
    scope = 2;
    displayName = "$STR_MotorbikeWheel0";
    descriptionShort = "$STR_MotorbikeWheel1";
    model = "\DZ\vehicles\singletrack\Motorbike_01\proxy\Motorbike_01_wheel_2.p3d";
    inventorySlot[] = {"Motorbike_01_Wheel_2"};
    rotationFlags = 8;
    radius = 0.29;
    width = 0.14;
    tyreType = 1;
    tyreOffroadResistance = 0.7;
    tyreRollResistance = 0.008;
    tyreGrip = 0.85;
    tyreRoughness = 1.0;
    tyreLongitudinalFriction = 0.85;
    tyreLateralFriction = 6.0;
};
class Motorbike_01_Wheel_2_Ruined: Motorbike_01_Wheel_2
{
    model = "\DZ\vehicles\singletrack\Motorbike_01\proxy\Motorbike_01_wheel_2_ruined.p3d";
    radius = 0.22;
    width = 0.2;
    tyreOffroadResistance = 0.02;
    tyreRollResistance = 0.8;
    tyreGrip = 0.35;
    tyreRoughness = 0.5;
    tyreLongitudinalFriction = 0.5;
    tyreLateralFriction = 0.5;
};
```

The rear wheel is more than twice as wide as the front (0.14 m against 0.06 m) and has twice the lateral friction (6.0 against 3.0). Each wheel model also needs a proxy class in `CfgNonAIVehicles` (`config.cpp:2316` to `:2350`); see `motorbike-forward-contract.md`.
