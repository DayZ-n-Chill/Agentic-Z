# Slots and cargo

Covers the slot a wearable goes into, how much it holds, what attaches to it, and the rules that stop two items being worn together.

## Slots the player has

Slots are defined in `CfgSlots` at `P:\scripts\config.cpp:11`. The class name is `Slot_<name>`, and items refer to the `name` value.

| Slot class | `name` | Where |
|---|---|---|
| `Slot_Headgear` | `Headgear` | `P:\scripts\config.cpp:38` |
| `Slot_Mask` | `Mask` | `:45` |
| `Slot_Eyewear` | `Eyewear` | `:51` |
| `Slot_Gloves` | `Gloves` | `:72` |
| `Slot_Armband` | `Armband` | `:78` |
| `Slot_Vest` | `Vest` | `:84` |
| `Slot_Body` | `Body` | `:90` |
| `Slot_Back` | `Back` | `:96` |
| `Slot_Hips` | `Hips` | `:102` |
| `Slot_Legs` | `Legs` | `:108` |
| `Slot_Feet` | `Feet` | `:114` |

The survivor's `InventoryEquipment` `playerSlots[]` lists the slots a body accepts, at `P:\DZ\characters\data\config.cpp:264` inside `SurvivorBase` (`:122`). It also holds `Slot_Shoulder` and `Slot_Melee` for long items.

Slots on gear itself, such as `VestHolster` (`P:\scripts\config.cpp:183`), `VestPouch` (`:189`), `VestBackpack` (`:195`) and `VestGrenadeA` to `VestGrenadeD` (`:2639` to `:2657`), are also in `CfgSlots`.

## Slot keys on the item

| Key | What it does | Vanilla example |
|---|---|---|
| `inventorySlot[]` | Slot names the item fits. | `{"Vest"}` at `P:\DZ\characters\vests\config.cpp:39` |
| `itemInfo[]` | Classification, `"Clothing"` plus the slot. | `{"Clothing","Vest"}` at `:43` |
| `itemSize[]` | Width and height the item takes in cargo. | `{5,5}` at `:49` |
| `itemsCargoSize[]` | Width and height of its own cargo grid. Slots held is width times height. | `{4,4}` on `SmershVest` at `:565` |
| `attachments[]` | Slot names other items attach to. | Plate carrier at `:30` |
| `quickBarBonus` | Extra quick bar slots while worn. | `1` on `PlateCarrierVest` at `:50`, `2` on `SmershVest` at `:566` |
| `weight` | Item weight. | `12000` on `PlateCarrierVest` at `:48` |

Tier 2 rule: when you change a parent's `inventorySlot`, redeclare the whole array with `=`, never `+=` (`.claude/skills/_shared/conventions/config.md`).

### Cargo or attachments

A wearable holds items in one of two ways, and the request decides which.

- **Own cargo.** Set `itemsCargoSize[]`. A request for "holds six items" is a grid of six cells, such as `{3,2}`. `TShirt_ColorBase` uses `{3,3}` (`P:\DZ\characters\tops\config.cpp:2260`), `TaloonBag_ColorBase` uses `{6,5}` (`P:\DZ\characters\backpacks\config.cpp:72`).
- **Attachments.** The vanilla plate carrier has no `itemsCargoSize[]` at all. Its storage is the `PlateCarrierPouches` item in the `VestPouch` slot, a `Container_Base` with `itemsCargoSize[]={5,3}` (`P:\DZ\gear\containers\config.cpp:646` and `:658`). An item made this way needs its own class and the `Container_Base` rules in `.claude/skills/_shared/container-base.md`.

Say which way you chose in the report, so the in-game check uses `cargo` or `attach` to match.

### Clothing inside clothing

`Clothing.CanPutInCargoClothingConditions` (`P:\scripts\4_world\entities\itembase\clothing_base.c:38`) refuses to put a clothing item that holds items into another item's cargo, except an underground stash. It also refuses to put clothing into a clothing item that is itself inside another clothing item. The one exception is the Smersh bag on the Smersh vest (`SmershException`, `:73`). Do not promise a wearable that stores other filled clothing.

## Wearing two items together

Headgear, masks and eyewear can block each other with three config flags, read by `EntityAI.InitLegacySlotExclusionValuesDerived` (`P:\scripts\3_game\entities\entityai.c:4419`).

| Key | Effect | Vanilla example |
|---|---|---|
| `noHelmet=1` | In the mask or eyewear slot, blocks headgear. | `GasMask` at `P:\DZ\characters\masks\config.cpp:47` |
| `noMask=1` | In the headgear or eyewear slot, blocks a mask. | Read at `entityai.c:4438` |
| `noEyewear=1` | In the headgear or mask slot, blocks eyewear. | `GasMask` at `P:\DZ\characters\masks\config.cpp:48` |
| `noNVStrap=1` | In the headgear or mask slot, blocks the NVG head strap. | `Mich2001Helmet` at `P:\DZ\characters\headgear\config.cpp:8404` |

Script classes can add more exclusions; `Mask_Base` adds one for shaving (`P:\scripts\4_world\entities\itembase\clothing_base.c:186`).

## Visibility to AI

`visibilityModifier` is read by `Clothing_Base` (`P:\scripts\4_world\entities\core\inherited\inventoryitem.c:983`). `PlayerBase.CalculateVisibilityForAI` (`P:\scripts\4_world\entities\manbase\playerbase.c:5405`) averages it over ten slots, counting each empty slot as 1. Lower values make the wearer harder to notice. Vanilla colors differ here: `UKAssVest_Black` uses `0.69999999` and `UKAssVest_Camo` uses `0.5` (`P:\DZ\characters\vests\config.cpp:1014` and `:1041`).
