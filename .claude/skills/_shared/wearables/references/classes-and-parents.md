# Classes and parents

Covers the clothing class tree in config and in script, how to pick the closest vanilla parent, and which addon each parent comes from.

## Config side

Every vanilla wearable inherits `Clothing`, which inherits `Clothing_Base`, which inherits `Inventory_Base`.

- `Clothing_Base` is defined at `P:\DZ\data\config.cpp:3442` with `scope=0`, `simulation="clothing"`, `itemInfo[]={"Clothing"}` and `visibilityModifier=1`. Its `GlobalArmor` sets every damage value to 1.
- Each clothing addon redeclares `class Clothing_Base;` and `class Clothing: Clothing_Base {};` before its own classes, for example `P:\DZ\characters\vests\config.cpp:20` and `:21`.
- Vanilla wearables then inherit `Clothing` directly (`class PlateCarrierVest: Clothing` at `P:\DZ\characters\vests\config.cpp:24`). The slot type comes from `inventorySlot[]`, not from a config base class.

Survivor body parts are the exception: `MaleTorso_Base` inherits `Inventory_Base` (`P:\DZ\characters\tops\config.cpp:28`). See `characters.md`.

## Script side

The script tree is separate from the config tree, and it is where slot behavior lives.

| Script class | Parent | Where |
|---|---|---|
| `Clothing_Base` | `ItemBase` | `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:977` |
| `Clothing` | `Clothing_Base` | `P:\scripts\4_world\entities\itembase\clothing_base.c:4` |
| `Belt_Base`, `Backpack_Base`, `Gloves_Base`, `HeadGear_Base`, `Pants_Base`, `Shoes_Base`, `Top_Base`, `Vest_Base` | `Clothing` | `P:\scripts\4_world\entities\itembase\clothing_base.c:164` to `:204` |
| `Glasses_Base` | `Clothing`, adds the glasses exclusion | `P:\scripts\4_world\entities\itembase\clothing_base.c:166` |
| `Mask_Base` | `Clothing`, adds the shaving exclusion in the mask slot | `P:\scripts\4_world\entities\itembase\clothing_base.c:184` |
| `HelmetBase` | `HeadGear_Base` | `P:\scripts\4_world\entities\itembase\clothing\helmetbase.c:2` |
| `MaskBase` (gas masks with filters) | `Mask_Base` | `P:\scripts\4_world\entities\itembase\clothing\maskbase.c:2` |

`typedef Clothing ClothingBase;` at `P:\scripts\4_world\entities\itembase\clothing_base.c:206` means script that names `ClothingBase` means `Clothing`.

Each vanilla wearable has a script class with the same name as its config class. Examples: `class PlateCarrierVest: Vest_Base` at `P:\scripts\4_world\entities\itembase\clothing\platecarriervest.c:1`, and every color of the UK assault vest at `P:\scripts\4_world\entities\itembase\clothing\ukassvest_colorbase.c:1` to `:6`.

**Engine:** a mod config class with no script class of its own uses the script class of its nearest config parent. So a config only retexture of `PlateCarrierVest` still behaves as a `PlateCarrierVest`. Add a script class (`class MyMod_Carrier extends PlateCarrierVest {}` in `4_World`) only when the item needs new behavior; that work goes to the script team.

## Picking the parent

1. Find the vanilla item that is closest in slot, shape and behavior. Grep `inventorySlot` and the item name in the matching folder under `P:\DZ\characters\` (`tops`, `pants`, `shoes`, `gloves`, `headgear`, `masks`, `glasses`, `vests`, `backpacks`, `belts`).
2. Prefer the `_ColorBase` class when vanilla has one (`UKAssVest_ColorBase` at `P:\DZ\characters\vests\config.cpp:866`). It holds the shared values, has no `scope=2`, and each color only sets `scope=2` and its textures (`:1011` onward).
3. Read the parent's whole config class before inheriting, and cite it as `path:line`.
4. Check the parent's script class too. Special behavior, such as the plate carrier changing its health when an infected wears it (`P:\scripts\4_world\entities\itembase\clothing\platecarriervest.c:3`), comes with the parent.

## Addon for `requiredAddons[]`

Name the addon that defines the parent, so the mod loads after it.

| Parent folder | Addon | Where |
|---|---|---|
| `characters\tops` | `DZ_Characters_Tops` | `P:\DZ\characters\tops\config.cpp:3` |
| `characters\pants` | `DZ_Characters_Pants` | `P:\DZ\characters\pants\config.cpp:3` |
| `characters\shoes` | `DZ_Characters_Shoes` | `P:\DZ\characters\shoes\config.cpp:3` |
| `characters\gloves` | `DZ_Characters_Gloves` | `P:\DZ\characters\gloves\config.cpp:3` |
| `characters\headgear` | `DZ_Characters_Headgear` | `P:\DZ\characters\headgear\config.cpp:3` |
| `characters\masks` | `DZ_Characters_Masks` | `P:\DZ\characters\masks\config.cpp:3` |
| `characters\glasses` | `DZ_Characters_Glasses` | `P:\DZ\characters\glasses\config.cpp:3` |
| `characters\vests` | `DZ_Characters_Vests` | `P:\DZ\characters\vests\config.cpp:3` |
| `characters\backpacks` | `DZ_Characters_Backpacks` | `P:\DZ\characters\backpacks\config.cpp:3` |
| `characters\belts` | `DZ_Characters_Belts` | `P:\DZ\characters\belts\config.cpp:3` |
| `characters\data` (survivors, proxies) | `DZ_Characters` | `P:\DZ\characters\data\config.cpp:3` |
| `gear\containers` (vest pouches such as `PlateCarrierPouches` at `:646`) | `DZ_Gear_Containers` | `P:\DZ\gear\containers\config.cpp:3` |

## Minimal example

```cpp
class CfgPatches
{
    class MyMod_Wearables
    {
        units[] = {"MyMod_Carrier_Black", "MyMod_Carrier_Green", "MyMod_Carrier_Tan"};
        weapons[] = {};
        requiredVersion = 0.1;
        requiredAddons[] = {"DZ_Characters_Vests"};
    };
};
class CfgVehicles
{
    class PlateCarrierVest;
    class MyMod_Carrier_ColorBase: PlateCarrierVest
    {
        scope = 0;
        displayName = "Carrier";
        model = "\MyMod\data\carrier_g.p3d";
        hiddenSelections[] = {"camoGround", "camoMale", "camoFemale"};
        class ClothingTypes
        {
            male = "\MyMod\data\carrier_m.p3d";
            female = "\MyMod\data\carrier_f.p3d";
        };
    };
    class MyMod_Carrier_Black: MyMod_Carrier_ColorBase
    {
        scope = 2;
        hiddenSelectionsTextures[] = {"\MyMod\data\carrier_black_co.paa", "\MyMod\data\carrier_black_co.paa", "\MyMod\data\carrier_black_co.paa"};
    };
};
```

The model and texture paths start with the mod's `$PBOPREFIX$`. The other colors follow the same shape as `MyMod_Carrier_Black`.
