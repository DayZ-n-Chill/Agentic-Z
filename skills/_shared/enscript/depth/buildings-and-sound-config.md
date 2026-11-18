# Building doors, damage zones and sound sets

How a static building declares animated doors, how it stays indestructible while its doors take damage, which keys a `CfgSoundSets` entry uses, and which model details need no script. Mod structure is in `mod-structure-patterns.md`.

## Doors on a building

A building on `HouseNoDestruct` lists its doors in `class Doors`. Vanilla's airfield headquarters is the model to copy (`Land_Mil_Airfield_HQ`, `P:\DZ\structures\military\config.cpp:22`; its doors from `:26`):

```cpp
class Land_MyMod_Building: HouseNoDestruct
{
    scope = 1;
    model = "MyMod\MyBuilding\MyBuilding.p3d";
    class Doors
    {
        class Door1
        {
            displayName = "Door 1";
            component = "door1";
            soundPos = "door1_action";
            animPeriod = 1;
            initPhase = 0;
            initOpened = 0.3;
            soundOpen = "doorMetalSmallOpen";
            soundClose = "doorMetalSmallClose";
            soundLocked = "doorMetalSmallRattle";
            soundOpenABit = "doorMetalSmallOpenABit";
        };
    };
};
```

| Key | Meaning |
|---|---|
| `component` | The door's selection in the model |
| `soundPos` | Memory point the door sounds play from |
| `animPeriod` | Seconds to open or close; vanilla uses 1, a large door can take longer |
| `initOpened` | Starting state, `0` closed and `1` open; vanilla also uses values between, such as `0.3` and `0.7` (`:35`, `:47`), which read as a chance to start open (unverified in game) |
| `soundOpen`, `soundClose`, `soundLocked`, `soundOpenABit` | Sound sets; vanilla families include `doorMetalSmall*` and `doorWoodTwin*` (`:36` to `:52`) |

`scope = 1` keeps the building out of tools that list only `scope = 2`; script and the terrain can still place it. The door animation and model side is in `_shared/animation/building-doors.md`.

## An indestructible building with damageable doors

`Land_Mil_Airfield_HQ` sets every damage type to zero in `GlobalArmor` (`P:\DZ\structures\military\config.cpp:194`) and gives each door zone `transferToGlobalCoef=0` (`:249`), so the building cannot die while its doors take damage:

```cpp
class DamageSystem
{
    class GlobalHealth { class Health { hitpoints = 10000; }; };
    class GlobalArmor
    {
        class Projectile { class Health { damage = 0; }; class Blood { damage = 0; }; class Shock { damage = 0; }; };
        class Melee      { class Health { damage = 0; }; class Blood { damage = 0; }; class Shock { damage = 0; }; };
    };
    class DamageZones
    {
        class Door1
        {
            class Health { hitpoints = 10000; transferToGlobalCoef = 0; };
            componentNames[] = { "door1" };
            fatalInjuryCoef = -1;
            class ArmorType
            {
                class Projectile { class Health { damage = 2; }; class Blood { damage = 0; }; class Shock { damage = 0; }; };
                class Melee      { class Health { damage = 2.5; }; class Blood { damage = 0; }; class Shock { damage = 0; }; };
            };
        };
    };
};
```

`GlobalArmor` blocks damage to the building, each zone's `ArmorType` lets its door take damage, and `transferToGlobalCoef = 0` keeps that damage from reaching the building's health. Vanilla also zeroes `FragGrenade` in `GlobalArmor`; add every damage type your server uses.

## Sound set keys

Vanilla's rifle shot base set shows the keys (`Rifle_Shot_Base_SoundSet`, `P:\DZ\sounds\hpp\config.cpp:323687`):

| Key | Meaning | Vanilla examples |
|---|---|---|
| `sound3DProcessingType` | 3D processing profile | `WeaponMediumShot3DProcessingType`, `Vehicle_Ext_3DProcessingType`, `character3DProcessingType` |
| `distanceFilter` | Filter over distance | `weaponShotDistanceFreqAttenuationFilter`, `softVehiclesDistanceFreqAttenuationFilter` |
| `volumeCurve` | Volume over distance | `RifleShotCurve`, `vehicleEngineAttenuationCurve`, `characterAttenuationCurve` |
| `volumeFactor` | Volume multiplier | `0.8` on rifle shots |
| `occlusionFactor`, `obstructionFactor` | 0 to 1, how much geometry and obstacles damp it | `0.6` on rifle shots |
| `spatial` | 1 for a positioned 3D sound | `1` |
| `loop` | 0 or 1 | `0` for a shot, `1` for an engine |
| `doppler` | 0 or 1 | `0` |
| `positionOffset[]` | Offset from the owner, as a vector | `{0,0,0.3}` |
| `soundShaders[]` | The sound shaders it plays | |
| `soundShadersLimit`, `soundObjectsLimit` | How many may play at once | `2` and `2` (`:323698` and `:323699`) |

The full sound pack is `_shared/audio-fx/`.

## Details that need no script

Purely visual parts, such as seats nobody sits in, doors nobody opens or engine dressing, can be proxies with no matching `pos_*` memory points or `seat_*` selections. The engine draws them by LOD and no script is involved.

Doors that come off as inventory attachments use the vanilla `CarDoor` base, a `Doors` damage zone and `attachments[]`; the engine shows and hides them on attach and detach. The vehicle side is in `_shared/vehicles/`.
