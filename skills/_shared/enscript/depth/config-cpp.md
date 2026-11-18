# Mod config.cpp

What a script mod's `config.cpp` declares: `CfgPatches`, the script modules in `CfgMods`, item and kit classes, the item keys script reads, hidden selections, the matching `model.cfg` and `$PBOPREFIX$`.

## Patches and script modules

```cpp
class CfgPatches
{
    class MyMod
    {
        units[] = { "MyMod_Device", "MyMod_Device_Kit" };
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = { "DZ_Data", "DZ_Scripts" };
    };
};

class CfgMods
{
    class MyMod
    {
        type = "mod";
        dependencies[] = { "Game", "World", "Mission" };
        class defs
        {
            class gameScriptModule    { value = ""; files[] = { "MyMod/scripts/3_Game" }; };
            class worldScriptModule   { value = ""; files[] = { "MyMod/scripts/4_World" }; };
            class missionScriptModule { value = ""; files[] = { "MyMod/scripts/5_Mission" }; };
        };
    };
};
```

`3_Game` compiles first, then `4_World`, then `5_Mission`. A later module can use an earlier one's classes, never the reverse; what goes where is in `script-layers.md`.

## Rules for every class

| Rule | Why |
|---|---|
| `scope = 2` to show in public lists and tools that filter on it; `scope = 1` still lets script create the class; `scope = 0` hides it | Vanilla gives `LargeTentClutterCutter` `scope = 1` (`P:\DZ\gear\camping\config.cpp:1454` to `:1456`) and creates it with `CreateObjectEx` (`P:\scripts\4_world\entities\itembase\tentbase\largetent.c:140`) |
| List every class in `units[]` | The engine tolerates a patch without it (`DZ_data_aiconfigs` has an empty body, `P:\DZ\data\aiconfigs\config.cpp:3` to `:5`), but `/dayz-lint` warns |
| `requiredAddons[]` names every addon your classes inherit from | |
| Forward declare a parent (`class Inventory_Base;`) before using it | |
| Close every class with `};` and leave no comma after the last array element | |
| Write each class name with the same case everywhere | Whether config lookups ignore case is not checked on `P:\` |

## A basic item

```cpp
class CfgVehicles
{
    class Inventory_Base;
    class MyMod_Device: Inventory_Base
    {
        scope = 2;
        displayName = "$STR_MYMOD_DEVICE";
        descriptionShort = "$STR_MYMOD_DEVICE_DESC";
        model = "\MyMod\data\mydevice\mydevice.p3d";
        weight = 500;
        itemSize[] = { 3, 3 };
        rotationFlags = 17;
        storageCategory = 1;
        hiddenSelections[] = { "camo", "light_led" };
        hiddenSelectionsTextures[] = { "\MyMod\data\mydevice\texture.paa" };
        hiddenSelectionsMaterials[] = { "\MyMod\data\mydevice\material.rvmat" };
        class AnimationSources
        {
            class led_state { source = "user"; animPeriod = 0.01; initPhase = 0; };
        };
    };
};
```

`weight` is in grams and `itemSize[]` is width and height in inventory cells.

## A kit

In config a kit inherits from `Inventory_Base`, as vanilla kits do (`FenceKit`, `P:\DZ\gear\camping\config.cpp:2955`). `DeployableContainer_Base` is a script class only (`P:\scripts\4_world\entities\itembase\container_base.c:32`); no vanilla config declares it, and a kit that named it as its config parent was invisible in game (measured in game).

```cpp
class MyMod_Device_Kit: Inventory_Base
{
    scope = 2;
    displayName = "$STR_MYMOD_DEVICE_KIT";
    model = "\MyMod\data\kits\kit_box.p3d";
    weight = 800;
    itemSize[] = { 2, 2 };
    rotationFlags = 17;
    class Placement
    {
        deployableModel = "\MyMod\data\mydevice\mydevice.p3d";   // omit when kit and device share a model
    };
    hiddenSelections[] = { "camo" };
    hiddenSelectionsTextures[] = { "\MyMod\data\kits\kitboxtexture.paa" };
};
```

`class Placement` and `deployableModel` are not vanilla: no config under `P:\DZ` and no script under `P:\scripts` reads them, so only the mod's own script uses these values.

## Item keys script reads

In DayZ 1.30 `ItemBaseType` reads these keys from the item's `CfgVehicles` class when the type is built (`P:\scripts\4_world\entities\itembasetype.c:55` to `:138`). Values a 1.29 mod kept on the script instance may now be cached per type, so put them in config.

| Key | Effect | Source |
|---|---|---|
| `headSelectionsToHide`, `hideSelectionsByinventorySlot` | Selections hidden when worn | `itembasetype.c:55` to `:138` |
| `varWetMax`, `varWetInit`, `varWetMin` | Wetness range | same |
| `quickBarBonus`, `itemModelLength`, `itemAttachOffset`, `temperaturePerQuantityWeight` | Item behaviour values | same |
| `EnvironmentWetnessIncrements` | Soaking (`parentWithLiquid`, `wetParent`) and drying (`player`, `ground`, `playerHeatSource`, `groundHeatSource`) | same |
| `compatibleLocks`, `lockType` | Lock matching | same |
| `canBeSplit` | The stack can be split and combined | `itembasetype.c:58` and `:59`; used at `P:\scripts\4_world\entities\itembase.c:183` |
| `quantityBar` | Shows a bar instead of a count | `itembasetype.c:74` |
| `canBeDigged` | The item can be buried | `itembasetype.c:94`; `ItemBase.CanBeDigged()` at `itembase.c:924` to `:927` |
| `heavyItem` | Taking it to hands plays the full body heavy pick up, `CMD_ACTIONFB_PICKUP_HEAVY` | `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakematerialtohands.c:114` to `:122` |

Vanilla gear also sets `absorbency` and `lootTag[]`, which no script reads; their engine meaning is not covered here. Vanilla spells `hideSelectionsByinventorySlot` with a lower case `i`; keep that spelling.

## Inventory groups and slots

- `GUIInventoryAttachmentsProps` is resolved by `TypeAttachmentGroupsDataHolder` (`P:\scripts\3_game\entities\typeattachmentgroupdataholders.c:39`) under weapons, magazines and vehicles. The vicinity category reaches 1.5 m (`P:\scripts\5_mission\gui\inventorynew\inherited\attachmentcategoriesrow.c:764`).
- Rebuilding slots: `CfgSlots` in `P:\scripts\config.cpp:2915` declares `Slot_RB_LvL1_Log` (`name = "RB_LvL1_Log"`, `stackMax = 15`) and the level 1 to 3 plank, nail, sheet, brick, wire and mortar slots, plus level 1 and 2 rope and stick. Also present: `Slot_Att_CodeLock*`, `Slot_Att_CombinationLock*_Wood` and `_Metal`, `Slot_NBC*`, and the motorbike wheel and shield slots.
- A duplicate member inside one class fails the binarizer in DayZ 1.30 (see `skills/dayz-build-pbo/references/dayz-1-30-pbo-build.md`).

## Hidden selections

Declare the selections in config, one texture and one material per index:

```cpp
hiddenSelections[] = { "camo", "light_led", "screen" };
hiddenSelectionsTextures[] = { "\MyMod\data\mydevice\texture.paa", "", "\MyMod\data\mydevice\screen.paa" };
hiddenSelectionsMaterials[] = { "\MyMod\data\mydevice\material.rvmat", "\MyMod\data\mydevice\led_off.rvmat", "\MyMod\data\mydevice\screen.rvmat" };
```

Swap them from script by index:

```c
SetObjectMaterial(1, "\MyMod\data\mydevice\led_on.rvmat");    // index 1, light_led
SetObjectTexture(0, "\MyMod\data\mydevice\texture_alt.paa");  // index 0, camo
```

The index is the position in `hiddenSelections[]`, and each name must match a selection in the model exactly. An empty texture string leaves that slot for script to fill.

## The model.cfg side

```cpp
class CfgModels
{
    class MyMod_Device
    {
        sectionsInherit = "";
        sections[] = { "camo", "light_led", "screen" };
        class Animations
        {
            class led_state
            {
                type = "rotation";
                source = "led_state";
                selection = "light_led";
                axis = "led_axis";
                memory = 1;
                minValue = 0;
                maxValue = 1;
                angle0 = 0;
                angle1 = 0.01;
            };
        };
    };
};
```

A rotation of 0.01 is enough to switch a state the model shows by animation.

## `$PBOPREFIX$`

Put a `$PBOPREFIX$` file at the mod root holding the prefix on one line, with no trailing newline:

```text
MyMod
```

Without it, model, texture and material paths that start `\MyMod\...` do not resolve at runtime.

## Folder layout

```text
MyMod/
  config.cpp
  $PBOPREFIX$
  scripts/
    3_Game/      shared helpers, settings, data classes
    4_World/     entity scripts, device logic, actions
    5_Mission/   UI, menus, HUD
  data/          models, textures, materials
  gui/layouts/   .layout files
```
