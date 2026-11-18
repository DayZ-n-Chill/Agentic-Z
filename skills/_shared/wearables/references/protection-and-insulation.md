# Protection and insulation

Covers how warm a wearable keeps the player, how wet it gets, how much damage it stops, what it filters, and how it is repaired.

## Insulation: `heatIsolation`

`heatIsolation` is read into the item type at `P:\scripts\4_world\entities\itembasetype.c:84`. `MiscGameplayFunctions.GetCurrentItemHeatIsolation` (`P:\scripts\4_world\static\miscgameplayfunctions.c:1363`) multiplies it by a wetness factor and a health factor.

| Wetness (`GetWet()`) | Factor | Where |
|---|---|---|
| Dry, below `STATE_DAMP` (0.05) | 1.0 | `P:\scripts\3_game\constants.c:821` |
| Damp, from 0.05 | 0.9 | `:822` |
| Wet, from `STATE_WET` (0.25) | 0.5 | `:823` |
| Soaking wet, from `STATE_SOAKING_WET` (0.5) | 0.1 | `:824` |
| Drenched, from `STATE_DRENCHED` (0.8) | returns -0.15 outright | `:825` |

The wetness states are at `P:\scripts\3_game\constants.c:933` to `:937`.

| Health level | Factor | Where |
|---|---|---|
| Pristine | 1.0 | `P:\scripts\3_game\constants.c:827` |
| Worn | 0.9 | `:828` |
| Damaged | 0.8 | `:829` |
| Badly damaged | 0.5 | `:830` |
| Ruined | 0.0 | `:831` |

The inspect menu labels the result (`P:\scripts\5_mission\gui\inspectmenunew.c:456`) with the thresholds `HEATISO_THRESHOLD_BAD` 0.2, `_LOW` 0.4, `_MEDIUM` 0.6 and `_HIGH` 0.8 (`P:\scripts\3_game\constants.c:1014` to `:1017`). Above 0.8 shows as the best label.

Vanilla values to compare with: `TShirt_ColorBase` 0.1 (`P:\DZ\characters\tops\config.cpp:2263`), `UKAssVest_ColorBase` 0.5 (`P:\DZ\characters\vests\config.cpp:892`), `PlateCarrierVest` 0.8 (`:52`).

## Wetness: `varWetMax`

`varWetMax` is the most wetness the item can reach (`P:\scripts\4_world\entities\itembasetype.c:71`). A T-shirt uses 1 (`P:\DZ\characters\tops\config.cpp:2262`). The plate carrier uses 0.49 (`P:\DZ\characters\vests\config.cpp:51`), which keeps it below the soaking wet state at 0.5, so its wetness factor never drops below 0.5.

The item type reads `varWetInit`, `varWetMin` and `varWetMax` together (`P:\scripts\4_world\entities\itembasetype.c:69` to `:71`). `ItemBase.GetWetMax` returns the type's value (`P:\scripts\4_world\entities\itembase.c:3726`), and a new item starts at `m_VarWetInit` (`P:\scripts\4_world\entities\itembase.c:165`).

### How fast it soaks and dries: `EnvironmentWetnessIncrements`

The item type also reads a class `EnvironmentWetnessIncrements` with two subclasses, `Soaking` and `Drying` (`P:\scripts\4_world\entities\itembasetype.c:124` to `:137`). The defaults sit on `Inventory_Base` and are inherited by every item unless a class declares its own block (`P:\DZ\data\config.cpp:3191`):

| Subclass | Key | Default |
|---|---|---|
| `Soaking` | `parentWithLiquid` | 1 |
| `Soaking` | `wetParent` | 0.005 |
| `Drying` | `player` | 0.00029 |
| `Drying` | `ground` | 0.00011 |
| `Drying` | `playerHeatSource` | 0.0035 |
| `Drying` | `groundHeatSource` | 0.0018 |

`temperaturePerQuantityWeight` is read the same way and defaults to 1.0 (`P:\scripts\4_world\entities\itembasetype.c:117`).

### Wetting clothes on purpose

DayZ 1.30 added actions that wet worn clothing to cool the player.

- Washing the head wets each worn slot by a fixed amount. `ActionWashHeadWettingClothesBase` holds two maps, one for washing from a container and one for washing at a water surface (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheadwettingclothesbase.c:13` to `:22` and `:31` to `:40`). From a container, `InventorySlots.HEADGEAR` and `MASK` get 0.24, `BODY` 0.12, `VEST` 0.08, `LEGS`, `ARMBAND` and `HIPS` 0.06, `GLOVES`, `FEET` and `BACK` 0.04. At a surface, `HEADGEAR` gets 0.12 and `GLOVES` 0.24; the rest are the same.
- The same action lowers the `eAgents.EYES_IRRITATION` agent and the player's thermal bias: it calls `GetThermalBiasHandler().Add` with minus `THERMAL_BIAS_WASH_HEAD_DECREMENT` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheadwettingclothesbase.c:54`). The constant is 0.175, and `THERMAL_BIAS_WASH_HEAD_TEMPORARY_RESISTANCE_TIME` is 30.0 (`P:\scripts\3_game\playerconstants.c:203` and `:204`).
- `ActionWetClothingInHandsWater` wets a clothing item held in hands. Its `ActionCondition` needs `IsClothing()` and `GetWet()` below `GetWetMax()` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwetclothinginhandswater.c:20`), and it targets water through `CCTLiquid` (`:17`).
- Washing the head from a bottle is not blocked when the bottle is frozen: `ActionWashHeadItemContinuous.ActionCondition` only refuses `LIQUID_GASOLINE` and does not call `GetIsFrozen()` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheaditemcontinuous.c:32`). This is a known issue in 1.30.

These two constants are the only tie to heat stroke covered here. Do not treat washing the head as a full heat stroke API.

## Armor: `DamageSystem`

- `GlobalHealth` `Health` holds `hitpoints` and `healthLevels[]`. Each level pairs a health fraction with the `.rvmat` files to show at that level, one per visual material. The plate carrier has 225 hitpoints (`P:\DZ\characters\vests\config.cpp:67`); a T-shirt has 50 and lists a worn and a ground material per level (`P:\DZ\characters\tops\config.cpp:2276` onward).
- `GlobalArmor` holds one class per damage source, each with `Health`, `Blood` and `Shock` `damage` values. `Clothing_Base` sets `Projectile`, `Melee` and `FragGrenade` to 1 (`P:\DZ\data\config.cpp:3463` to `:3510`). Armored items add an `Infected` class as well, as the plate carrier does (`P:\DZ\characters\vests\config.cpp:146`). The plate carrier lowers `Projectile` `Health` to 0.3 and `Shock` to 0.6 (`P:\DZ\characters\vests\config.cpp:114` to `:130`).
- **Engine:** an armor value multiplies the damage of that type that reaches the wearer, so lower means more protection. Confirm a new value in game.
- A color variant that redeclares `DamageSystem` must inherit each level (`class DamageSystem: DamageSystem`, `class GlobalHealth: GlobalHealth`, `class Health: Health`), as `PlateCarrierVest_Black` does at `P:\DZ\characters\vests\config.cpp:209` to `:213`. Leave it out when the color only changes textures.

## Filters: the `Protection` class

`ItemBase.GetProtectionLevel(int type, bool consider_filter = false, int system = 0)` (`P:\scripts\4_world\entities\itembase.c:4073`) reads `CfgVehicles <type> Protection <entry>` (`:4099`). It returns 0 when the item is ruined or out of quantity.

| `type` constant | Config entry | Where |
|---|---|---|
| `DEF_BIOLOGICAL` = 1 | `biological` | `P:\scripts\3_game\constants.c:547` |
| `DEF_CHEMICAL` = 2 | `chemical` | `:548` |
| `DEF_DUST_PARTICLE_BREATH` = 3 | `dust_particle_breath` | `:549` |
| `DEF_DUST_PARTICLE_EYES` = 4 | `dust_particle_eyes` | `:550` |

Vanilla `GasMask` sets all four to 1 (`P:\DZ\characters\masks\config.cpp:134`); `NioshFaceMask` sets `biological=0.75` and `dust_particle_breath=1` (`:256`). Masks with a filter slot override the call to read the filter instead, as `GP5GasMask` does with the `GasMaskFilter` slot (`P:\scripts\4_world\entities\itembase\clothing\gp5gasmask.c:13`). That is script work for the script team.

### Masks with a filter slot

On the two cartridge masks the protection sits on the filter, not on the mask.

- `GP5GasMask` and `AirborneMask` both declare `attachments[]` with `"GasMaskFilter"` (`P:\DZ\characters\masks\config.cpp:855` and `:984`). Their `Protection` class holds only `dust_particle_eyes=1` (`P:\DZ\characters\masks\config.cpp:951` and `:1084`). The keys `biological` and `dust_particle_breath` are left out, not set to 0. Before 1.30 both masks also set `biological=1` and `dust_particle_breath=1` (from the 1.29 files, which are not on `P:\`).
- The filter item is `GasMask_Filter` (`P:\DZ\gear\consumables\config.cpp:4295`), which goes in the `GasMaskFilter` slot and sets `biological`, `chemical` and `dust_particle_breath` to 1 in its `Protection` class (`:4324`). The masks addon also defines `GP5GasMask_Filter` with `scope=0` for the same slot (`P:\DZ\characters\masks\config.cpp:1107`). There is no class named `FilterBase`.
- With a filter attached, `GetProtectionLevel` on the mask returns 1.0 for `DEF_DUST_PARTICLE_EYES` and the filter's level for every other type. With no filter it falls through to `super`, which reads the mask's own `Protection` class. A destroyed mask returns 0 (`P:\scripts\4_world\entities\itembase\clothing\gp5gasmask.c:13` to `:28`). `AirborneMask` has the same override (`P:\scripts\4_world\entities\itembase\clothing\airbornemask.c:18`).
- The sealed `GasMask` has no filter slot and keeps full passive protection in its own `Protection` class (`P:\DZ\characters\masks\config.cpp:134`).

A mod mask that works with cartridges attaches `GasMaskFilter` and does not rely on `biological` on the mask itself. A copy of the GP5 that hardcodes `biological` on the mask, or leaves out the `GasMaskFilter` attachment, does not behave like the vanilla 1.30 masks.

## Repair: `repairableWithKits[]` and `repairCosts[]`

`repairableWithKits[]` lists kit types and `repairCosts[]` the cost for each, in the same order. A kit's type is its `repairKitType`.

| Type | Kit | Where |
|---|---|---|
| 1 | `WeaponCleaningKit` | `P:\DZ\gear\tools\config.cpp:1016` |
| 2 | `SewingKit` | `:1108` |
| 3 | `LeatherSewingKit` | `:1203` |
| 4 | `Whetstone` | `:5552` |
| 5 | `DuctTape` | `P:\DZ\gear\consumables\config.cpp:259` |
| 7 | `ElectronicRepairKit` | `P:\DZ\gear\tools\config.cpp:5365` |
| 8 | `EpoxyPutty` | `:5459` |
| 10 | `Blowtorch` | `:6173` |

Cloth uses duct tape and a sewing kit (`{5,2}` on `TShirt_ColorBase`, `P:\DZ\characters\tops\config.cpp:2266`). The plate carrier uses the leather sewing kit and epoxy putty (`{3,8}`, `P:\DZ\characters\vests\config.cpp:53`).
