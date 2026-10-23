# Research map: wearables specialist

Private research map. Anchors point into vanilla data on `P:\`. Items marked **knowledge** are not verifiable from vanilla files on `P:\`.

| # | Topic | What the specialist needs to know | Verify at |
|---|---|---|---|
| 1 | Script class hierarchy | `Clothing_Base` then `Clothing`, then slot bases (`Top_Base`, `Pants_Base`, `Shoes_Base`, `Gloves_Base`, `HeadGear_Base`, `Mask_Base`, `Glasses_Base`, `Vest_Base`, `Backpack_Base`). | `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:977`; `P:\scripts\4_world\entities\itembase\clothing_base.c:4`, `:165`-`:204` |
| 2 | Inventory slots | `CfgSlots` defines slot names (`Slot_Headgear` and others); player config lists which slots the body accepts. | `P:\scripts\config.cpp:11`, `:38`; `P:\DZ\characters\data\config.cpp:275` |
| 3 | `inventorySlot[]` and `itemInfo[]` | Which slot an item goes into and its classification. | `P:\DZ\characters\tops\config.cpp:2249`, `:2253` |
| 4 | Male and female models | `ClothingTypes` with `male=`/`female=` p3d. | `P:\DZ\characters\tops\config.cpp:2334`-`2337` |
| 5 | Proxies | `CfgNonAIVehicles` proxy classes such as `ProxyHeadgear_DZ` tie slots to body proxies. | `P:\DZ\characters\data\config.cpp:10657`, `:10685` |
| 6 | Hidden selections and retextures | `hiddenSelections[]`; `HiddenSelectionsData` script helper. | `P:\DZ\characters\tops\config.cpp:2269`; `P:\scripts\3_game\hiddenselectionsdata.c:1` |
| 7 | Cargo | `itemSize[]` and `itemsCargoSize[]`. | `P:\DZ\characters\tops\config.cpp:2259`, `:2260` |
| 8 | Heat isolation and wetness | `heatIsolation`, `varWetMax`; environment wet factors. | `P:\DZ\characters\tops\config.cpp:2262`, `:2263`; `P:\scripts\3_game\constants.c:821`; `P:\scripts\3_game\entities\entityai.c:2169`; `P:\scripts\4_world\classes\environment\environment.c:293` |
| 9 | Visibility to AI | `visibilityModifier` summed by the player. | `P:\DZ\characters\tops\config.cpp:2265`; `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:996`; `P:\scripts\4_world\entities\manbase\playerbase.c:5423` |
| 10 | Repair | `repairableWithKits[]`. | `P:\DZ\characters\tops\config.cpp:2266` |
| 11 | Damage system | Item health levels in `DamageSystem`. | `P:\DZ\characters\tops\config.cpp:2276` |
| 12 | Armor | `GlobalArmor` with `Projectile` and `Melee` blocks on vests and helmets. | `P:\DZ\characters\vests\config.cpp:114`, `:116`, `:131` |
| 13 | Vest attachments | Plate carrier `attachments[]` for pouches and holsters. | `P:\DZ\characters\vests\config.cpp:24`, `:30`; `P:\scripts\4_world\entities\itembase\clothing\platecarriervest.c:1` |
| 14 | Hair and head hiding | `headSelectionsToHide[]`; player hides hair selections on attach. | `P:\DZ\characters\headgear\config.cpp:84`; `P:\scripts\4_world\entities\manbase\playerbase.c:1514`, `:2614` |
| 15 | Attach/detach rules | `CanPutAsAttachment` blocks conflicting items (for example mask with helmet). | `P:\scripts\4_world\entities\itembase.c:3`, `:4150`; `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:322` |
| 16 | Attach/detach events | `EEItemAttached`, `OnWasAttached`, `OnWasDetached`, `EEItemLocationChanged`. | `P:\scripts\3_game\entities\entityai.c:1159`, `:976`, `:1864` |
| 17 | Texture swap on attach | `SwitchItemSelectionTexture` (gloves, sleeves). | `P:\scripts\3_game\entities\entityai.c:1195` |
| 18 | Clothing sounds | `soundAttType` and `AnimEvents`/`SoundWeapon` for pickup and drop sounds. | `P:\DZ\characters\tops\config.cpp:2268`, `:2339`, `:2341` |
| 19 | Helmets | `HelmetBase`. | `P:\scripts\4_world\entities\itembase\clothing\helmetbase.c:2` |
| 20 | Masks and gas masks | `MaskBase`, `GasMask`, filters, filter quantity. | `P:\scripts\4_world\entities\itembase\clothing\maskbase.c:2`; `...\clothing\gasmask.c:1`; `...\clothing\gasmask_filter.c:1`; `P:\scripts\4_world\classes\playermodifiers\modifiers\mask.c:71`; config `P:\DZ\characters\masks\config.cpp:21` |
| 21 | Protection levels | `GetProtectionLevel` against chemicals and dust. | `P:\scripts\4_world\classes\playermodifiers\modifiers\conditions\areaexposure.c:123`; `...\sandstormexposure.c:138` |
| 22 | Headtorch and NVG | Powered clothing, NVG status update. | `P:\scripts\4_world\entities\itembase\clothing\headtorch_colorbase.c:1`; `P:\scripts\4_world\entities\itembase\nvgoggles.c:1`; `...\clothing\nvgheadstrap.c:1`; `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:1001` |
| 23 | Burlap sack (restraint headgear) | Special case for headgear that blinds the wearer. | `P:\scripts\4_world\entities\itembase\clothing\burlapsackcover.c:1` |
| 24 | Backpacks | Config example `TaloonBag_ColorBase`. | `P:\DZ\characters\backpacks\config.cpp:47` |
| 25 | Weight updates | `SetWeightDirty` on attach changes. | `P:\scripts\3_game\entities\entityai.c:1039` |
| 26 | Zombie loadouts | Zombie configs reference clothing slots. | `P:\DZ\characters\zombies\config.cpp:140` |
| 27 | Model requirements | Clothing must be skinned to the vanilla skeleton (Object Builder selections, `*_m`/`*_f`, ground and worn models). **knowledge**. | `P:\DZ\characters\tops\tshirt_m.p3d` (vanilla reference) |
