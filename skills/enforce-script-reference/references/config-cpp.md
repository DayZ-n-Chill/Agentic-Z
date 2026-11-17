# config.cpp Patterns for DayZ Mods

## Structure Overview

Every DayZ mod needs a `config.cpp` defining its classes and dependencies.

```
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
            class worldScriptModule
            {
                value = "";
                files[] = { "MyMod/scripts/4_World" };
            };
            class missionScriptModule
            {
                value = "";
                files[] = { "MyMod/scripts/5_Mission" };
            };
            class gameScriptModule
            {
                value = "";
                files[] = { "MyMod/scripts/3_Game" };
            };
        };
    };
};
```

## CfgVehicles — Entity Definitions

### Basic Item (Inventory_Base)

```
class CfgVehicles
{
    class Inventory_Base;

    class MyMod_Device: Inventory_Base
    {
        scope = 2;                    // 2 = visible in-game, 0 = hidden
        displayName = "$STR_MYMOD_DEVICE";
        descriptionShort = "$STR_MYMOD_DEVICE_DESC";
        model = "\MyMod\data\mydevice\mydevice.p3d";
        weight = 500;                 // grams
        itemSize[] = { 3, 3 };        // inventory slots (width, height)
        rotationFlags = 17;           // rotation in inventory
        storageCategory = 1;          // enables persistence
        hiddenSelections[] = { "camo", "light_led" };
        hiddenSelectionsTextures[] = { "\MyMod\data\mydevice\texture.paa" };
        hiddenSelectionsMaterials[] = { "\MyMod\data\mydevice\material.rvmat" };

        class AnimationSources
        {
            class led_state
            {
                source = "user";
                animPeriod = 0.01;
                initPhase = 0;
            };
        };
    };
};
```

### Kit Item (Deployable)

```
class CfgVehicles
{
    class Inventory_Base;

    // In config a kit inherits from Inventory_Base, as vanilla kits do
    // (FenceKit, P:\DZ\gear\camping\config.cpp:2955).
    // DeployableContainer_Base is a script class only
    // (P:\scripts\4_world\entities\itembase\container_base.c:32); no vanilla
    // config declares it. A kit that named it as its config parent was
    // invisible in game (measured in game twice).
    class MyMod_Device_Kit: Inventory_Base
    {
        scope = 2;
        displayName = "$STR_MYMOD_DEVICE_KIT";
        descriptionShort = "$STR_MYMOD_DEVICE_KIT_DESC";
        model = "\MyMod\data\kits\kit_box.p3d";
        weight = 800;
        itemSize[] = { 2, 2 };
        rotationFlags = 17;

        // Kit placement configuration. Not vanilla: no config under P:\DZ and
        // no script under P:\scripts reads `class Placement` or `deployableModel`,
        // so only the mod's own script reads these values.
        class Placement
        {
            // If kit and deployed model are different:
            deployableModel = "\MyMod\data\mydevice\mydevice.p3d";
            // If same model (camera/door controller pattern): omit deployableModel
        };

        // hiddenSelections for kit appearance
        hiddenSelections[] = { "camo" };
        hiddenSelectionsTextures[] = { "\MyMod\data\kits\kitboxtexture.paa" };
        hiddenSelectionsMaterials[] = { "\MyMod\data\kits\kit_box.rvmat" };
    };
};
```

### Important config.cpp Rules

1. **`scope`** — Creation by script works with `scope = 1`: [EXACT] vanilla gives `LargeTentClutterCutter` `scope = 1` (`P:\dz\gear\camping\config.cpp:1454-1456`) and creates it from script with `CreateObjectEx` (`P:\scripts\4_world\entities\itembase\tentbase\largetent.c:140`). Exposure in public lists/tools that filter by scope 2 needs `scope = 2`. `scope = 0` hides them.
2. **`units[]`** — List all your classes here. The engine tolerates a patch class without it (vanilla `DZ_data_aiconfigs` has an empty body, `P:\DZ\data\aiconfigs\config.cpp:3-5`); `/dayz-lint` reports the missing array as a warning.
3. **`requiredAddons[]`** — Must include addons your classes inherit from.
4. **Forward declare parent classes** — `class Inventory_Base;` before using as parent.
5. **Semicolons after closing braces** — Every `};` needs the semicolon.
6. **No trailing comma in arrays** — Last element must not have comma.
7. **Case** — Write a class name with the same case everywhere. Whether config lookups are case-sensitive is not yet checked on `P:\`.

8. **`ItemBaseType` keys (1.30)** — script reads these from the item's `CfgVehicles` class at type construction (`P:\scripts\4_world\entities\itembasetype.c:55-138`): `headSelectionsToHide`, `hideSelectionsByinventorySlot`, `varWetMax` / `varWetInit` / `varWetMin`, `quickBarBonus`, `itemModelLength`, `itemAttachOffset`, `temperaturePerQuantityWeight`, `EnvironmentWetnessIncrements` (Soaking `parentWithLiquid`/`wetParent`, Drying `player`/`ground`/`playerHeatSource`/`groundHeatSource`), `compatibleLocks`, `lockType`. Instance fields that 1.29 mods stored on the item may now be type-cached — put the values in config, not only on the script instance.
8a. **More item flags read by script (1.30.164289).** `canBeSplit` (stack can be split and combined; `P:\scripts\4_world\entities\itembasetype.c:58-59`, used in `P:\scripts\4_world\entities\itembase.c:183`), `quantityBar` (show a quantity bar instead of a count; `P:\scripts\4_world\entities\itembasetype.c:74`), `canBeDigged` (can be buried; `P:\scripts\4_world\entities\itembasetype.c:94`, `ItemBase.CanBeDigged()` `P:\scripts\4_world\entities\itembase.c:924-927`) and `heavyItem` (taking it to hands plays the full-body heavy pick-up, `CMD_ACTIONFB_PICKUP_HEAVY`; `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiontakematerialtohands.c:114-122`). All paths under `scripts/4_World/`. Vanilla gear also sets `absorbency` and `lootTag[]`, which no script reads; their engine meaning is not documented here.
9. **`GUIInventoryAttachmentsProps`** — resolved by `TypeAttachmentGroupsDataHolder` (`P:\scripts\3_game\entities\typeattachmentgroupdataholders.c:39`) under weapons / magazines / vehicles. Vicinity category reach is a 1.5 m dome (`P:\scripts\5_mission\gui\inventorynew\inherited\attachmentcategoriesrow.c:764`).
10. **Rebuilding slots `RB_LvL*`** — `CfgSlots` in `P:\scripts\config.cpp:2915` (`Slot_RB_LvL1_Log`, `name = "RB_LvL1_Log"`, `stackMax = 15`) plus LvL1/2/3 plank/nail/sheet/brick/wire/mortar and LvL1/2 rope/stick. Also new: `Slot_Att_CodeLock*`, `Slot_Att_CombinationLock*_Wood/Metal`, `Slot_NBC*`, motorbike wheel/shield slots. Duplicate members inside one class now fail the binarizer (see `references/dayz-1-30-pbo-build.md` in the `dayz-build-pbo` skill).

### hiddenSelections System

hiddenSelections allow runtime texture/material swaps:

```
// In config.cpp — declare selections
hiddenSelections[] = { "camo", "light_led", "screen" };
hiddenSelectionsTextures[] = {
    "\MyMod\data\mydevice\texture.paa",   // [0] camo
    "",                                           // [1] light_led (set by script)
    "\MyMod\data\mydevice\screen.paa"      // [2] screen
};
hiddenSelectionsMaterials[] = {
    "\MyMod\data\mydevice\material.rvmat",
    "\MyMod\data\mydevice\led_off.rvmat",
    "\MyMod\data\mydevice\screen.rvmat"
};
```

```
// In script — swap material at runtime
string rvmatOn = "\MyMod\data\mydevice\led_on.rvmat";
int selIndex = 1;  // light_led
SetObjectMaterial(selIndex, rvmatOn);

// Swap texture at runtime
string texAlt = "\MyMod\data\mydevice\texture_alt.paa";
int texIndex = 0;  // camo
SetObjectTexture(texIndex, texAlt);
```

**Critical**: The index in `SetObjectMaterial`/`SetObjectTexture` corresponds to the position in the `hiddenSelections[]` array. The selection name in the p3d model must match exactly.

### model.cfg for Animations

```
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
                angle1 = 0.01;  // minimal rotation for state change
            };
        };
    };
};
```

## $PBOPREFIX$ File

Required at mod root for DayZ to resolve baked p3d paths to correct PBO namespace:

```
// File: $PBOPREFIX$
// Content (single line, no trailing newline):
MyMod
```

Without this file, all model/texture/material paths that reference `\MyMod\...` will fail to resolve at runtime.

## Script Module Organization

```
MyMod/
├── config.cpp
├── $PBOPREFIX$
├── scripts/
│   ├── 3_Game/       ← Shared utilities, settings, data classes
│   ├── 4_World/      ← Entity scripts, device logic, actions
│   └── 5_Mission/    ← UI code, menus, HUD overlays
├── data/             ← Models, textures, materials
└── gui/
    └── layouts/      ← .layout UI files
```

**Loading order matters**: 3_Game loads first, then 4_World, then 5_Mission. Classes in 4_World can use 3_Game classes but not vice versa.
