# config.cpp and addon structure

The config side of a generated model: folder layout, `$PBOPREFIX$`, the `CfgVehicles` class, proxy attachment classes, a material file, and packing. The classes themselves are config work (`dayz-config-specialist`); this file says what the model needs from them. Lines that cite `P:\` were opened and confirmed; the examples with `my_addon` and `LFPG_` names are the source mod's own and not checked on `P:\`.

## Addon folder structure

In Agentic-Z the source folder is `workspace/<ModName>/` and `/dayz-build-pbo` packs it to `P:\Mods\@<ModName>\Addons\`; the layout inside the folder is the same as below.

```
@MyMod/
└── addons/
    └── my_addon.pbo          ← Packed from:

my_addon/                      ← Source folder
├── $PBOPREFIX$                ← Contains: my_addon (path prefix for the PBO)
├── config.cpp                 ← Game configuration
├── model.cfg                  ← Skeleton & animation definitions
├── data/
│   ├── my_object.p3d          ← The model
│   ├── textures/
│   │   ├── my_texture_co.paa  ← Diffuse/color texture
│   │   ├── my_texture_nohq.paa ← Normal map
│   │   └── my_texture_smdi.paa ← Specular map
│   └── materials/
│       └── my_material.rvmat  ← Material definition
```

## $PBOPREFIX$

A text file (no extension) containing a single line with the PBO prefix path:
```
my_addon
```
This determines how paths resolve inside the PBO. If prefix is `my_addon`, then
`my_addon\data\my_object.p3d` is the in-game path to the model.

## config.cpp — Basic Structure

```cpp
class CfgPatches
{
    class my_addon
    {
        units[] = {"MyObject"};           // Classes defined in this addon
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Data"};   // Dependencies
    };
};

class CfgVehicles
{
    // Parent class — almost all DayZ placeable objects inherit from one of these:
    // - HouseNoDestruct — buildings, static structures
    // - Inventory_Base — items, placeable objects
    // - ItemBase — smaller items
    
    class HouseNoDestruct;  // External class declaration
    
    class MyObject: HouseNoDestruct
    {
        scope = 2;                                    // 2 = public, visible in-game
        displayName = "My Electrical Panel";
        descriptionShort = "An electrical panel for LF_PowerGrid";
        model = "my_addon\data\my_object.p3d";       // Path to model
        
        // Animation sources for script-controlled animations
        class AnimationSources
        {
            class switch_source
            {
                source = "user";
                initPhase = 0;
                animPeriod = 0.5;
            };
            class indicator_source
            {
                source = "user";
                initPhase = 0;
                animPeriod = 0.3;
            };
        };
        
        // For buildings with doors
        class Doors
        {
            class Door1
            {
                displayName = "Panel Door";
                component = "door1";                  // named component in the View Geometry LOD (see below)
                soundPos = "door1_soundPos";          // Memory LOD point
                initPhase = 0;
                initOpened = 0.3;
                soundOpen = "DoorWoodThinOpen_SoundSet";
                soundClose = "DoorWoodThinClose_SoundSet";
            };
        };
        
        // Damage system (if destructible)
        class DamageSystem
        {
            class DamageZones
            {
                class Zone_Door1
                {
                    class Health
                    {
                        hitpoints = 200;
                        healthLevels[] =
                        {
                            {1.0, {}},    // Pristine
                            {0.7, {}},    // Worn
                            {0.5, {}},    // Damaged
                            {0.3, {}},    // Badly damaged
                            {0.0, {}}     // Ruined
                        };
                    };
                    componentNames[] = {"door1"};     // Fire Geometry component
                    fatalInjuryCoef = -1;
                };
            };
        };
        
        // Bounding override (if animated parts extend beyond default sphere)
        bounding = "bounding_box";   // Named selection in Memory LOD (not checked on P:\, see below)
    };
};
```

Checked against vanilla:

- `component` names the door's component in the View Geometry LOD: the engine finds a door from the view geometry component index (`GetDoorIndex`, `P:\scripts\3_game\entities\building.c:27` to `:28`). The source wrote "Fire Geometry component name" here; `_shared/animation/animation-sources.md` has the full `class Doors` table.
- `componentNames[]` in a damage zone lists Fire Geometry selections, as written (`_shared/models/lods.md`, Fire Geometry).
- Vanilla door sounds are plain sound names such as `soundOpen="doorWoodTwinOpen"` (`P:\DZ\structures\residential\config.cpp:7367`). The `DoorWoodThinOpen_SoundSet` names in the example are not vanilla; reuse a vanilla name until the mod has its own sounds.
- `bounding` is a real config key, but vanilla gear sets it to `"BSphere"` (`P:\DZ\gear\camping\config.cpp:44`). A memory selection name as its value, and the wiki's "opened volume so raycasts follow the open door", are not shown by any vanilla file read here.

Since 1.30 (official changelog) house based classes may set `disableSimulation = 1;` so the building does not tick. The script side is `DisableSimulation` and `GetIsSimulationDisabled` on `Entity` (`P:\scripts\3_game\entities\entity.c:3` to `:6`). The config key itself was not found in any vanilla 1.30 config (unverified). See `dayz-1-30-model-pipeline.md`.

## config.cpp for DayZ buildings

Buildings inherit from `HouseNoDestruct` (`P:\DZ\data\config.cpp:3119`). The class name follows the pattern
`land_modelname` so the engine links the config to a model placed on the map; vanilla does the same: `Land_HouseBlock_3F_Corner1` for `houseblock_3f_corner1.p3d` (`P:\DZ\structures\residential\config.cpp:7341`). The automatic link itself is engine behavior that no script shows.

```cpp
class land_my_building: HouseNoDestruct
{
    scope = 2;
    model = "my_addon\data\my_building.p3d";
    // ... rest of config
};
```

The `land_` prefix + model name (without .p3d) creates the automatic link.

## config.cpp for Inventory Items / Placeable Objects

```cpp
class CfgVehicles
{
    class Inventory_Base;
    
    class LFPG_SolarPanel: Inventory_Base
    {
        scope = 2;
        displayName = "Solar Panel";
        descriptionShort = "A solar panel for electrical generation";
        model = "my_addon\data\solar_panel.p3d";
        weight = 5000;                    // Weight in grams
        itemSize[] = {5, 5};             // Inventory slot size
        rotationFlags = 16;               // Inventory rotation; vanilla camping gear uses 2 (P:\DZ\gear\camping\config.cpp:84)
        
        class AnimationSources
        {
            // ...
        };
    };
};
```

## CfgNonAIVehicles — Proxy Attachment Definitions

Required for items to render visually when attached to another object.
Without this, the attachment is logically present but invisible on the 3D model.

This works together with the proxy system (`_shared/models/proxies.md`):
1. Parent p3d has proxy face + selection in visual LODs (see `memory-and-selections.md`), and since 1.30 in View Geometry too (`dayz-1-30-model-pipeline.md`)
2. A proxy .p3d exists at the referenced path (see `py3d-direct-generation.md`)
3. **This config entry** maps inventory slots to the proxy model

Vanilla writes it the same way: `class ProxyAttachment;` is declared at `P:\DZ\gear\camping\config.cpp:13386` and `Proxysingle_plank` maps the plank slots to its model at `:13405`.

```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;    // External class — MUST be declared or causes
                              // "Undefined base class" build error

    class ProxyMySlot : ProxyAttachment
    {
        scope = 2;
        inventorySlot[] = {"CarBattery", "TruckBattery"};   // Vanilla slot names
        model = "\MyAddon\data\MySlot.p3d";                  // Proxy p3d: "Proxy" + this basename = the class name
    };
};
```

**Key rules:**
- `class ProxyAttachment;` forward declaration is MANDATORY — without it AddonBuilder fails
- `inventorySlot[]` must match the slot names used in `attachments[]` of the parent CfgVehicles class
- `model` path must point to the proxy .p3d file that exists in the addon
- Class name must be `Proxy` followed by the basename of `model`, compared case-insensitively
  (`MySlot.p3d` -> `ProxyMySlot`). A class named otherwise draws nothing and logs nothing, also
  for an inventory slot: measured in game on the LFQuad3 mod, whose three inventory slots drew
  nothing until its proxy classes were renamed (the `rip-vehicle-import` skill's invisible
  attachment cookbook, rule (d)). Check it in `config.cpp` before measuring any proxy frame
- Class name (`ProxyMySlot`) must be unique across all loaded addons, so the proxy basename must be too
- Multiple slots can point to the same proxy .p3d
- For vanilla slots (CarBattery, TruckBattery, SparkPlug, etc.), no CfgSlots entry needed

**Common pattern for LFPowerGrid Battery Adapter:**
```cpp
class CfgNonAIVehicles
{
    class ProxyAttachment;
    class ProxyLFPG_BatterySlot : ProxyAttachment
    {
        scope = 2;
        inventorySlot[] = {"CarBattery", "TruckBattery"};
        model = "\LFPowerGrid\data\battery_adapter\LFPG_BatterySlot.p3d";
    };
};
```

**On an item, a slot added to the vanilla `ProxyBattery_Car` drew nothing** (measured in game
2026-10-04 on one LFPowerGrid item, slot and battery; a third-party measurement, not repeatable from `P:\`). On an
`ItemBase`-derived flag whose slot `LFPG_FlagBattery` held a `CarBattery`, the slot was added with
`inventorySlot[] +=` to `ProxyBattery_Car`, the class of the vanilla proxy
`\dz\vehicles\parts\battery_car.001`. That class derives from `ProxyPart`, a vehicle part class
(`ProxyBattery_Car` at `P:\DZ\vehicles\parts\config.cpp:1145`; `ProxyPart`, with `simulation="ProxyInventory"` and
`reversed=1`, at `:1125` to `:1135`), and it never drew the battery,
in three layouts, each adding to the one before: the proxy in LOD 0; the proxy inside a named
selection called like the slot, which the slot's `CfgSlots` `selection` names, as `civiliansedan`
holds `battery_car.001` inside its `battery` selection; and copies of the proxy in the Geometry,
View and Fire LODs, the only LODs where `battery_charger.p3d` carries it. A class of the item's own
drew it: `class ProxyLFPG_FlagBattery : ProxyAttachment` with `inventorySlot[] = {"LFPG_FlagBattery"}`,
its own minimal proxy p3d `LFPG_FlagBattery.p3d` at `model`, and the proxy face in LOD 0, the
mechanism of the vanilla flag's `ProxyDZ_Flag: ProxyAttachment` (`P:\DZ\gear\camping\config.cpp:13595`) on that item. In one build with
both proxies 0.35 m apart, the battery appeared at the item's own. For an item, write a
`ProxyAttachment` class of your own, as above, rather than adding the slot to a vanilla vehicle
part's. Not measured: whether a `ProxyAttachment` proxy orients the item as a vehicle part's
`reversed = 1` does (claim: CLAIM-ITEM-PROXY-OWN-ATTACHMENT-CLASS).

## Texture & Material Configuration

### .rvmat (material) file format

A Super shader material has seven stages in a fixed order. The source showed three stages with the specular map in `Stage3`; vanilla puts the macro map there and the specular map in `Stage5` (`P:\DZ\gear\camping\data\wooden_case.rvmat`, the layout below), so a three stage file in the source's order feeds the wrong map to the shader. The stage by stage reference is `_shared/textures/rvmat-stages.md`.

```cpp
ambient[] = {1.0, 1.0, 1.0, 1.0};
diffuse[] = {1.0, 1.0, 1.0, 1.0};
forcedDiffuse[] = {0.0, 0.0, 0.0, 1.0};
emmisive[] = {0.0, 0.0, 0.0, 1.0};    // For glowing parts (LEDs etc)
specular[] = {0.3, 0.3, 0.3, 1.0};
specularPower = 80;
PixelShaderID = "Super";
VertexShaderID = "Super";

class Stage1
{
    texture = "my_addon\data\textures\my_texture_nohq.paa";   // Normal map
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {1.0, 0.0, 0.0};
        up[] = {0.0, 1.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};

class Stage2
{
    texture = "#(argb,8,8,3)color(0.5,0.5,0.5,0.5,DT)";      // Detail texture (placeholder)
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {10.0, 0.0, 0.0};                           // 10x tiling for a real detail map
        up[] = {0.0, 10.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};

class Stage3
{
    texture = "#(argb,8,8,3)color(0,0,0,0,MC)";               // Macro map (placeholder)
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {1.0, 0.0, 0.0};
        up[] = {0.0, 1.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};

class Stage4
{
    texture = "#(argb,8,8,3)color(1,1,1,1,AS)";               // Ambient shadow (placeholder, or a _as.paa)
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {1.0, 0.0, 0.0};
        up[] = {0.0, 1.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};

class Stage5
{
    texture = "my_addon\data\textures\my_texture_smdi.paa";   // Specular/gloss map
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {1.0, 0.0, 0.0};
        up[] = {0.0, 1.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};

class Stage6
{
    texture = "#(ai,32,128,1)fresnel(1.61,0.22)";             // Fresnel, as the vanilla wooden case
    uvSource = "none";
};

class Stage7
{
    texture = "dz\data\data\env_land_co.paa";                 // Environment map
    uvSource = "tex";
    class uvTransform
    {
        aside[] = {1.0, 0.0, 0.0};
        up[] = {0.0, 1.0, 0.0};
        dir[] = {0.0, 0.0, 0.0};
        pos[] = {0.0, 0.0, 0.0};
    };
};
```

### Texture naming convention

The full suffix list is in `_shared/conventions/assets.md`; `/dayz-pack-texture` converts a `.png` to `.paa`.

| Suffix | Purpose |
|--------|---------|
| `_co.paa` | Color / diffuse texture |
| `_nohq.paa` | Normal map |
| `_smdi.paa` | Specular / metallic / gloss |
| `_as.paa` | Ambient shadow |
| `_mc.paa` | Macro color (overall tint overlay) |

### Emissive Materials (for LEDs, indicators)
Set `emmisive[]` to non-zero values for parts that should glow.
Can be controlled per-selection using hiddenSelections and hiddenSelectionsMaterials
in config.cpp to swap materials at runtime (e.g., LED on vs LED off).

## Packing into PBO

### Before binarizing: measure each collision LOD (SP-458, added 2026-10-03)

A collision LOD with many pieces can make `binarize` write no ODOL and print no capacity line, so
a three-state bench reads `OTHER_FAIL` (the binarize vertex budget notes in the vehicles pack,
`_shared/vehicles/README.md`, item 3 there). Before Addon Builder or `binarize`, read the points, faces, named selections and
selection bytes of each Geometry, View and Fire LOD with a header reader, and check that every
LOD walks to its `#EndOfFile#` TAGG: a truncated MLOD gives the same `OTHER_FAIL`. The values
known to pass, the boundary and the fix (pieces moved to a second model, none merged or
decimated): `lods-and-geometry.md`, "Collision of a large building with an interior".

### Using Addon Builder (official)

In Agentic-Z run `/dayz-build-pbo <ModName>`: it drives DayZ Tools Addon Builder with binarize on and writes to `P:\Mods\@<ModName>\Addons\`. By hand the steps are:

1. Open Addon Builder (from DayZ Tools on Steam)
2. Set source directory to your addon folder
3. Set destination to `@MyMod\addons\`
4. Check "Binarize" to binarize .p3d and .wrp files
5. Build

### Using Mikero's tools (community)

Not used by Agentic-Z skills; listed because many mods are built this way.

```cmd
rem pboProject binarizes and packs in one step
pboProject -P my_addon
```

### Using BinPBO

An older Bohemia packer, also not used by Agentic-Z skills.

```cmd
BinPBO.exe -SIGN my_addon @MyMod\addons\my_addon.pbo
```

## Testing

In Agentic-Z, `/dayz-launch-test` starts the local server and client with the built mod. By hand:

1. Place the `@MyMod` folder in your DayZ game directory
2. Add `-mod=@MyMod` to launch parameters
3. Use the in-game admin tools or script to spawn the object
4. Verify: visual appearance, collision, bullet interaction, animations, sounds

Since 1.30 (official changelog) `-mod` also accepts an unpacked source folder, not only a packed `@Mod` with PBOs. Pair it with `-cacheP3D=0` or `-cacheP3D=1` and `-resolveFilePatchingUsingEnfusion=0` or `-resolveFilePatchingUsingEnfusion=1`. The 1.30 notes on the build and in-game test side come in with the PBO build and in-game test material of the same import.
