# Changes in DayZ 1.30 for clothing and gear

Covers what DayZ 1.30 changed in the config and script contract around wearables, what that breaks in a mod written for 1.29, and a checklist for moving such a mod over. The worn model itself (skeleton, frame, weights; see `worn-models.md`) did not change.

`P:\` holds the 1.30 files, so every 1.30 fact below cites the line on `P:\`. A statement about 1.29 comes from the 1.29 game files, which are not on `P:\`; each one is marked "(1.29, not on `P:\`)" and cannot be checked there.

## What changed, and where it is described

| Change | Described in |
|---|---|
| NBC clothing lists a second slot (`NBCHead`, `NBCTop`, `NBCPants`, `NBCBoots`, `NBCGloves`) | `slots-and-cargo.md`, "NBC slots" |
| Nine backpack bases take the NBC pack in the new `NBCBag` slot | `slots-and-cargo.md`, "`NBCBag` on backpacks" |
| Protection of the GP5 and Airborne masks moved to the filter | `protection-and-insulation.md`, "Masks with a filter slot" |
| Head hiding and wetness values are read on the item type | Below, and `models-and-proxies.md`, "An item that fits two slots" |
| Wash head and wet clothing actions | `protection-and-insulation.md`, "Wetting clothes on purpose" |
| Shoes take less inventory space | Below |
| `WaterPouch_*` config classes renamed `Waterskin_*` | Below |
| Armband from a flag no longer needs an empty flag | Below |
| New regional clothing scripts with no config | Below |

Before 1.30, an NBC base listed only its regular slot, for example `NBCHoodBase` with `{"Headgear"}`, and `TaloonBag_ColorBase` listed `{"Chemlight","WalkieTalkie","Backpack_1"}` (1.29, not on `P:\`).

## Values read on the item type

`ItemBaseType` reads `headSelectionsToHide` and `hideSelectionsByinventorySlot` once per type (`P:\scripts\4_world\entities\itembasetype.c:105` to `:113`), next to `varWetMax` (`:71`), `temperaturePerQuantityWeight` (`:117`) and the `EnvironmentWetnessIncrements` maps (`:124` to `:137`). `ItemBase` reads them back from the type: `GetHeadHidingSelection` and `HidesSelectionBySlot` (`P:\scripts\4_world\entities\itembase.c:4518` and `:4523`), `GetWetMax` (`:3722`), and the starting wetness from `m_VarWetInit` (`P:\scripts\4_world\entities\itembase.c:165`).

The config keys are not new. In 1.29 `ItemBase` parsed `headSelectionsToHide` and `hideSelectionsByinventorySlot` on each item instance, and there was no `ItemBaseType` script file (1.29, not on `P:\`). A mod's config needs no change for this; script that read the old `ItemBase` members directly does.

## Shoes: `itemSize[]`

Most footwear went from four cells wide to three, and several boots also lost a row. Not every shoe changed: `LeatherShoes_ColorBase` is still `{4,2}`. All lines are in `P:\DZ\characters\shoes\config.cpp`; the 1.29 column is from the 1.29 file (not on `P:\`).

| Class | Class line | 1.29 | 1.30 | `itemSize[]` line |
|---|---|---|---|---|
| `AthleticShoes_ColorBase` | `:786` | `{4,2}` | `{3,2}` | `:800` |
| `HikingBoots_ColorBase` | `:974` | `{4,4}` | `{3,3}` | `:988` |
| `HikingBootsLow_ColorBase` | `:1135` | `{4,3}` | `{3,2}` | `:1149` |
| `Wellies_ColorBase` | `:1316` | `{4,4}` | `{3,4}` | `:1330` |
| `WorkingBoots_ColorBase` | `:1501` | `{4,3}` | `{3,3}` | `:1515` |
| `JungleBoots_ColorBase` | `:1692` | `{4,4}` | `{3,3}` | `:1706` |
| `DressShoes_ColorBase` | `:1885` | `{4,2}` | `{3,2}` | `:1899` |
| `MilitaryBoots_ColorBase` | `:2077` | `{4,4}` | `{3,3}` | `:2091` |
| `CombatBoots_ColorBase` | `:2273` | `{4,4}` | `{3,3}` | `:2287` |
| `JoggingShoes_ColorBase` | `:2466` | `{4,2}` | `{3,2}` | `:2480` |
| `Sneakers_ColorBase` | `:3028` | `{4,2}` | `{3,2}` | `:3042` |
| `Ballerinas_ColorBase` | `:3311` | `{4,2}` | `{3,2}` | `:3325` |
| `TTSKOBoots` | `:3570` | `{4,4}` | `{3,3}` | `:3585` |
| `MedievalBoots` | `:3654` | `{4,3}` | `{3,4}` | `:3669` |
| `TraditionalBoots_ColorBase` | `:3799` | `{4,4}` | `{3,4}` | `:3817` |
| `ColdOperationBoots_ColorBase` | `:3963` | `{4,4}` | `{3,4}` | `:3977` |

Unchanged or smaller already: `LeatherShoes_ColorBase` `{4,2}` (`P:\DZ\characters\shoes\config.cpp:2669`), `NBCBootsBase` `{2,2}` (`P:\DZ\characters\shoes\config.cpp:3207`) and `FeetCover_Improvised` `{2,2}` (`P:\DZ\characters\shoes\config.cpp:3473`).

A shoe mod balanced against the old width of four now takes more grid space than vanilla footwear.

## Waterskin (was WaterPouch)

The config classes are now `Waterskin_ColorBase` (`P:\DZ\gear\drinks\config.cpp:474`) and `Waterskin_Natural` (`P:\DZ\gear\drinks\config.cpp:595`). In 1.29 they were `WaterPouch_ColorBase` and `WaterPouch_Natural` (1.29, not on `P:\`).

- The old script class remains as an empty stub, `class WaterPouch_ColorBase: Bottle_Base{};` (`P:\scripts\4_world\entities\itembase\gear\drinks\waterpouch_colorbase.c:1`). The behavior is in `waterskin_colorbase.c` in the same folder.
- The sound classes under `AnimEvents` keep their old names, for example `WaterPouch_in_B` with `WaterPouch_in_B_SoundSet` (`P:\DZ\gear\drinks\config.cpp:557`).
- Values on `Waterskin_ColorBase`: model `\dz\gear\drinks\waterskin.p3d`, `lootCategory` `"Crafted"`, `hiddenSelections[]` `{"camoground"}`, `weight` 250, `itemSize[]` `{2,4}`, `repairableWithKits[]` `{3}` with `repairCosts[]` `{25}`, `destroyOnEmpty` 0, `varQuantityDestroyOnMin` 0, `varLiquidTypeInit` 512, `varTemperatureFreezePoint` and `varTemperatureThawPoint` -200, `varTemperatureMax` 120, `varQuantityInit` 0, `varQuantityMin` 0, `varQuantityMax` 1250 and `temperaturePerQuantityWeight` 4 (`P:\DZ\gear\drinks\config.cpp:478` to `:498`).
- Which liquids it accepts is the `liquidContainerType` mask on the same class (`P:\DZ\gear\drinks\config.cpp:491`): `"1 + 2 + 4 + 8 + 16 + 32 + 64 + 128 + 256 + 512 + 1024 + 2048 + 4096 + 8192 + 16384 + 32768 + 65536  + 131072 + 262144 + 524288 + 2097152 + 4194304 - (1 + 2 + 4 + 8 + 16 + 32 + 64 + 128 + 256) - 32768"`. Copy the expression as it is when a custom skin should take the same liquids.
- Crafting: two `TannedLeather` (`m_IngredientAddQuantity[0] = -2`) and a `LeatherSewingKit` that loses 10 quantity give a `Waterskin_Natural` (`P:\scripts\4_world\classes\recipes\recipes\craftwaterskin.c:26` to `:44`).
- Taking apart: a `Waterskin_ColorBase` is destroyed and a cutting tool loses 12 health (`m_IngredientAddHealth[1] = -12`) to give one `TannedLeather`. The tool list includes `Jambiya`, `Scimitar`, `DonerKnife`, `BrickTrowel` and `Akinaka`. `CanDo` is `return ingredients[0].IsEmpty();`, so the skin must be empty (`P:\scripts\4_world\classes\recipes\recipes\decraftwaterskin.c:26` to `:90`).

`CreateObject("WaterPouch_Natural")` and recipes that name `WaterPouch_*` fail in 1.30, because the config class is gone. If a 1.29 world still stores `WaterPouch_Natural`, a mod can add an alias. This alias is a suggestion; vanilla 1.30 does not have it:

```cpp
class Waterskin_Natural;
class WaterPouch_Natural: Waterskin_Natural { scope = 1; };
```

## Armband from a flag

`CraftArmbandFlag.CanDo` now only refuses a flag that is attached to something: `return !ingredients[0].GetInventory().IsAttachment();` (`P:\scripts\4_world\classes\recipes\recipes\craftarmbandflag.c:103` to `:105`). In 1.29 it was `return ingredients[0].IsEmpty();` (1.29, not on `P:\`). The tool list also has `Jambiya`, `Scimitar`, `DonerKnife` and `Akinaka` (`P:\scripts\4_world\classes\recipes\recipes\craftarmbandflag.c:42` and `:59` to `:61`). A mod that overrides this recipe must not assume the flag is empty.

## Regional clothing scripts with no config

Script classes exist under `P:\scripts\4_world\entities\itembase\clothing\` for a set of garments (the Nasdara or Badlands set: kameez, shalwar, pakol, dust goggles and others) that have no class in any `config.cpp` under `P:\DZ`:

| Script class | Parent | File |
|---|---|---|
| `DustGoggles_ColorBase` | `Glasses_Base` | `dustgoggles_colorbase.c` |
| `FNOJacket` | `Top_Base` | `fnojacket.c` |
| `FNOPants` | `Pants_Base` | `fnopants.c` |
| `KameezShirt_ColorBase` | `Top_Base` | `kameez_colorbase.c` |
| `LeatherHipPack_ColorBase` | `Belt_Base` | `leatherhippack_colorbase.c` |
| `LinenVest_ColorBase` | `Vest_Base` | `linenvest_colorbase.c` |
| `PakolHat_ColorBase` | `HeadGear_Base` | `pakolhat_colorbase.c` |
| `PoliceShortSleeveShirt_ColorBase` | `Top_Base` | `policeshortsleeveshirt_colorbase.c` |
| `RobeVest_ColorBase` | `Vest_Base` | `robevest_colorbase.c` |
| `SandalsShoes_ColorBase` | `Shoes_Base` | `sandals_colorbase.c` |
| `MensShalwarPants_ColorBase` | `Pants_Base` | `mensshalwarpants_colorbase.c` |
| `WomensShalwarPants_ColorBase` | `Pants_Base` | `womensshalwarpants_colorbase.c` |
| `ShortSleeveShirt_ColorBase` | `Top_Base` | `shortsleeveshirt_colorbase.c` |
| `TurbanHat_ColorBase` | `HeadGear_Base` | the turban hat file |

Their insulation, cargo, `ClothingTypes` paths and models are not in the vanilla data on `P:\`, so do not state them. Treat these as content of a DLC or regional release until a config for them appears, and do not inherit from them in a mod that must load on the base game.

`LeatherHipPack_ColorBase` can be put in cargo only while it is empty, and it takes attachments only while it is not itself in cargo (`P:\scripts\4_world\entities\itembase\clothing\leatherhippack_colorbase.c:3` to `:20`).

## What breaks for a 1.29 clothing or gear mod

1. NBC clothing that lists only the regular slot cannot be layered with regular headgear, tops, pants, shoes or gloves.
2. A custom backpack without `"NBCBag"` cannot take the NBC pack.
3. A copy of the GP5 or Airborne mask that hardcodes `biological` on the mask, or leaves out `attachments[] = {"GasMaskFilter"}`, does not match the filter-based protection of 1.30.
4. `CreateObject("WaterPouch_Natural")` and recipes naming `WaterPouch_*` fail; the class is `Waterskin_Natural`.
5. Shoe mods still four cells wide take more grid space than vanilla 1.30 footwear.
6. Two-slot headgear that leaves out `headSelectionsToHide[]` or `hideSelectionsByinventorySlot` clips or hides the wrong part of the head.

## Migration checklist

- [ ] NBC pieces: `inventorySlot[]` includes the matching `NBC*` slot.
- [ ] Backpacks that should carry the NBC pack: `attachments[]` includes `"NBCBag"`.
- [ ] Filter masks: `attachments[] = {"GasMaskFilter"}`; biological protection comes from `GasMask_Filter`, not from the mask's `Protection` class.
- [ ] The clothing class declares `headSelectionsToHide[]`, `varWetMax` and, when it should soak or dry at its own rate, `EnvironmentWetnessIncrements`.
- [ ] `WaterPouch_*` replaced with `Waterskin_*` (with the alias above only if an old world needs it).
- [ ] Shoe `itemSize[]` checked again if it was balanced against a width of four.
- [ ] An armband-from-flag recipe does not assume `IsEmpty()`.
- [ ] The in-game test is unchanged: spawn, equip, move.

## What 1.30 did not change

- `ClothingTypes` with `male` and `female`, and the camo `hiddenSelections[]`.
- The canonical worn frame (-Z chest, +X the anatomical left, +Y up).
- The skeleton name `DayzTemporarySkeleton` and the 159-pair `model.cfg` template.
- The in-game test: spawn, equip, move.
