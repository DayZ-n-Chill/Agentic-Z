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

## NBC slots

Since DayZ 1.30 the NBC suit has slots of its own, so its pieces can be worn together with regular clothing. `CfgSlots` holds six of them.

| Slot class | `name` | Ghost icon | Where |
|---|---|---|---|
| `Slot_NBCBag` | `NBCBag` | `back` | `P:\scripts\config.cpp:3115` |
| `Slot_NBCHead` | `NBCHead` | `headgear` | `:3121` |
| `Slot_NBCTop` | `NBCTop` | `body` | `:3127` |
| `Slot_NBCGloves` | `NBCGloves` | `gloves` | `:3133` |
| `Slot_NBCPants` | `NBCPants` | `legs` | `:3139` |
| `Slot_NBCBoots` | `NBCBoots` | `feet` | `:3145` |

Each vanilla NBC clothing base lists the regular slot first and its NBC slot second.

| Class | `inventorySlot[]` | Where |
|---|---|---|
| `NBCHoodBase` | `"Headgear"`, `"NBCHead"` | `P:\DZ\characters\headgear\config.cpp:7493` |
| `NBCJacketBase` | `"Body"`, `"NBCTop"` | `P:\DZ\characters\tops\config.cpp:7576` |
| `NBCPantsBase` | `"Legs"`, `"NBCPants"` | `P:\DZ\characters\pants\config.cpp:4458` |
| `NBCBootsBase` | `"Feet"`, `"NBCBoots"` | `P:\DZ\characters\shoes\config.cpp:3191` |
| `NBCGloves_ColorBase` | `"Gloves"`, `"NBCGloves"` | `P:\DZ\characters\gloves\config.cpp:1212` |

A mod NBC piece that lists only the regular slot cannot be layered with regular headgear, tops, pants, shoes or gloves.

`NBCPantsBase` also declares `ContinuouActions[]` with `"AT_WRING_CLOTHES"` (`P:\DZ\characters\pants\config.cpp:4454`). The key is spelled that way in the vanilla file; copy the vanilla spelling if you copy the block.

### `NBCBag` on backpacks

Some backpacks take the NBC pack as an attachment, and not all of them. Nine vanilla bases list `"NBCBag"` in `attachments[]`, after `"Chemlight"`, `"WalkieTalkie"` and `"Backpack_1"`, all in `P:\DZ\characters\backpacks\config.cpp`:

| Class | Class line | `"NBCBag"` line |
|---|---|---|
| `TaloonBag_ColorBase` | `:47` | `:62` |
| `TortillaBag` | `:208` | `:224` |
| `DryBag_ColorBase` | `:861` | `:876` |
| `HuntingBag` | `:1050` | `:1066` |
| `MountainBag_ColorBase` | `:1245` | `:1260` |
| `AssaultBag_ColorBase` | `:2890` | `:2905` |
| `Attack2Bag_ColorBase` | `:3054` | `:3069` |
| `CoyoteBag_ColorBase` | `:3218` | `:3233` |
| `AliceBag_ColorBase` | `:3370` | `:3385` |

`SmershBag` lists only `"Chemlight"` and `"WalkieTalkie"` (`P:\DZ\characters\backpacks\config.cpp:1424`), and `ChildBag_ColorBase` stops at `"Backpack_1"` (`P:\DZ\characters\backpacks\config.cpp:1553`). The courier, improvised, leather sack, sling and army pouch bases in the same file have no `"NBCBag"` either. A mod backpack that should carry the NBC pack needs `"NBCBag"` in its own `attachments[]`.

The pack itself is scripted as `NBCPack_ColorBase`, a `Container_Base` that never shows the cargo of its attachments and refuses an attachment that still holds cargo (`P:\scripts\4_world\entities\itembase\gear\containers\containers.c:83`), with the colors `NBCPack_Grey`, `NBCPack_White` and `NBCPack_Yellow` at `:105` to `:107`. No `config.cpp` under `P:\DZ` defines an `NBCPack` class, so the pack's `inventorySlot[]`, cargo size and model path are not known from vanilla data; do not state them.

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

Tier 2 rule: when you change a parent's `inventorySlot`, redeclare the whole array with `=`, never `+=` (`skills/_shared/conventions/config.md`).

### Cargo or attachments

A wearable holds items in one of two ways, and the request decides which.

- **Own cargo.** Set `itemsCargoSize[]`. A request for "holds six items" is a grid of six cells, such as `{3,2}`. `TShirt_ColorBase` uses `{3,3}` (`P:\DZ\characters\tops\config.cpp:2260`), `TaloonBag_ColorBase` uses `{6,5}` (`P:\DZ\characters\backpacks\config.cpp:72`).
- **Attachments.** The vanilla plate carrier has no `itemsCargoSize[]` at all. Its storage is the `PlateCarrierPouches` item in the `VestPouch` slot, a `Container_Base` with `itemsCargoSize[]={5,3}` (`P:\DZ\gear\containers\config.cpp:646` and `:658`). An item made this way needs its own class and the `Container_Base` rules in `skills/_shared/container-base.md`.

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
