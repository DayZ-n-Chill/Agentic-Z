# Model config and packing

What a new model needs from `config.cpp`, how its addon folder is laid out, and how it is packed and tested. The classes themselves are config work for `dayz-config-specialist`; this file says what the model asks of them. The proxy classes that make attachments show are in `proxy-attachment-config.md`, and the material file in `model-material-file.md`.

Lines that cite `P:\` are checked there. Examples with `my_addon` and `PM_` names (a power grid mod) are mod examples.

## Addon folder

In this repo the source folder is `workspace/<ModName>/`, and `/dayz-build-pbo` packs it to `P:\Mods\@<ModName>\Addons\`. Inside the folder the layout is:

```text
my_addon/                       source folder, packed to @MyMod/addons/my_addon.pbo
  $PBOPREFIX$                   one line: my_addon
  config.cpp                    game configuration
  model.cfg                     skeleton and animations
  data/
    my_object.p3d               the model
    textures/
      my_texture_co.paa         colour
      my_texture_nohq.paa       normal map
      my_texture_smdi.paa       specular
    materials/
      my_material.rvmat         material
```

`$PBOPREFIX$` is a text file with no extension holding one line, the path prefix of the PBO. With the prefix `my_addon`, the model's path in game is `my_addon\data\my_object.p3d`.

## The class for a placed object

```cpp
class CfgPatches
{
    class my_addon
    {
        units[] = {"MyObject"};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data"};
    };
};

class CfgVehicles
{
    class HouseNoDestruct;

    class MyObject: HouseNoDestruct
    {
        scope = 2;                                   // public, can be spawned
        displayName = "My Electrical Panel";
        descriptionShort = "An electrical panel for a power grid mod";
        model = "my_addon\data\my_object.p3d";

        class AnimationSources                       // phases set from script
        {
            class switch_source    { source = "user"; initPhase = 0; animPeriod = 0.5; };
            class indicator_source { source = "user"; initPhase = 0; animPeriod = 0.3; };
        };

        class Doors                                  // only for an object with doors
        {
            class Door1
            {
                displayName = "Panel Door";
                component = "door1";                 // View Geometry component
                soundPos = "door1_soundPos";         // Memory LOD point
                initPhase = 0;
                initOpened = 0.3;
                soundOpen = "doorWoodTwinOpen";
                soundClose = "doorWoodTwinClose";
            };
        };

        class DamageSystem                           // only if it can be damaged
        {
            class DamageZones
            {
                class Zone_Door1
                {
                    class Health
                    {
                        hitpoints = 200;
                        healthLevels[] = {{1.0, {}}, {0.7, {}}, {0.5, {}}, {0.3, {}}, {0.0, {}}};
                    };
                    componentNames[] = {"door1"};    // Fire Geometry selection
                    fatalInjuryCoef = -1;
                };
            };
        };
    };
};
```

Almost every placed object derives from `HouseNoDestruct` (buildings and fixed structures) or `Inventory_Base` (items and placeable objects). `ItemBase` is a script class only: no vanilla `config.cpp` defines it, so never use it as a config parent.

What the vanilla files show about the keys above:

- `component` names the door's component in the View Geometry LOD: the engine finds a door from the view geometry component index (`GetDoorIndex`, `P:\scripts\3_game\entities\building.c:27` and `:28`). It is not a Fire Geometry name. The full `class Doors` table is in `_shared/animation/animation-sources.md`.
- `componentNames[]` in a damage zone lists Fire Geometry selections (`lods.md`, "Fire Geometry").
- Vanilla door sounds are plain sound names such as `soundOpen="doorWoodTwinOpen"` (`P:\DZ\structures\residential\config.cpp:7367`). Reuse a vanilla name until the mod has sounds of its own.
- `bounding` is a real key, but vanilla gear sets it to `"BSphere"` (`P:\DZ\gear\camping\config.cpp:44`). No vanilla file read here gives it a memory selection name, or shows a volume that makes ray casts follow an open door, so `bounding = "<selection>"` from modelling guides is unverified.
- Since 1.30 (official changelog) a house class may set `disableSimulation = 1;` so the building does not tick. The script side is `DisableSimulation` and `GetIsSimulationDisabled` on `Entity` (`P:\scripts\3_game\entities\entity.c:3` to `:6`). The key itself is in no vanilla 1.30 config, so it is unverified; see `dayz-1-30-models.md`.

## A building

A building derives from `HouseNoDestruct` (`P:\DZ\data\config.cpp:3119`) and is named `Land_` plus the model's file name, so the engine links the config to a model placed on the map. Vanilla does the same: `Land_HouseBlock_3F_Corner1` for `houseblock_3f_corner1.p3d` (`P:\DZ\structures\residential\config.cpp:7341`). The link itself is engine behaviour that no script shows.

```cpp
class Land_MyMod_Building: HouseNoDestruct
{
    scope = 2;
    model = "my_addon\data\mymod_building.p3d";
};
```

## An item or placeable object

```cpp
class CfgVehicles
{
    class Inventory_Base;

    class PM_SolarPanel: Inventory_Base
    {
        scope = 2;
        displayName = "Solar Panel";
        descriptionShort = "A solar panel for electrical generation";
        model = "my_addon\data\solar_panel.p3d";
        weight = 5000;               // grams
        itemSize[] = {5, 5};         // inventory cells
        rotationFlags = 16;          // vanilla camping gear uses 2
        class AnimationSources {};
    };
};
```

Vanilla camping gear sets `rotationFlags=2` (`P:\DZ\gear\camping\config.cpp:84`).

## Packing

Before Binarize, measure each collision LOD of a model with many collision pieces: past a limit Binarize writes no ODOL and prints no reason, and a truncated MLOD fails the same way. The figures and the fix are in `building-collision-limits.md`.

In this repo run `/dayz-build-pbo <ModName>`: it drives Addon Builder from DayZ Tools with binarize on and writes to `P:\Mods\@<ModName>\Addons\`. By hand:

1. Open Addon Builder from DayZ Tools.
2. Set the source folder to the addon folder.
3. Set the destination to `@MyMod\addons\`.
4. Tick "Binarize" so `.p3d` and `.wrp` files are binarized.
5. Build.

Two other packers are common in mods and not used by this repo's skills: pboProject, which binarizes and packs in one step (`pboProject -P my_addon`), and the older BinPBO (`BinPBO.exe -SIGN my_addon @MyMod\addons\my_addon.pbo`).

## Testing

In this repo `/dayz-launch-test` starts the local server and client with the built mod. By hand: put `@MyMod` in the game folder, add `-mod=@MyMod` to the launch line, spawn the object with admin tools or script, and check its look, collision, bullet hits, animations and sounds.

Since 1.30 (official changelog) `-mod` also takes an unpacked source folder, not only a packed `@Mod`. Pair it with `-cacheP3D=0` or `-cacheP3D=1` and `-resolveFilePatchingUsingEnfusion=0` or `=1`. The 1.30 build and test notes are in `skills/dayz-build-pbo/references/dayz-1-30-pbo-build.md` and `skills/dayz-launch-test/references/dayz-1-30.md`.
