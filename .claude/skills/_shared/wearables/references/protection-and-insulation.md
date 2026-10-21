# Protection and insulation

Covers how warm a wearable keeps the player, how wet it gets, how much damage it stops, what it filters, and how it is repaired.

## Insulation: `heatIsolation`

`heatIsolation` is read into the item type at `P:\scripts\4_world\entities\itembasetype.c:84`. `MiscGameplayFunctions.GetCurrentItemHeatIsolation` (`P:\scripts\4_world\static\miscgameplayfunctions.c:1355`) multiplies it by a wetness factor and a health factor.

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

## Armor: `DamageSystem`

- `GlobalHealth` `Health` holds `hitpoints` and `healthLevels[]`. Each level pairs a health fraction with the `.rvmat` files to show at that level, one per visual material. The plate carrier has 225 hitpoints (`P:\DZ\characters\vests\config.cpp:67`); a T-shirt has 50 and lists a worn and a ground material per level (`P:\DZ\characters\tops\config.cpp:2276` onward).
- `GlobalArmor` holds one class per damage source (`Projectile`, `Melee`, `Infected`, `FragGrenade`), each with `Health`, `Blood` and `Shock` `damage` values. `Clothing_Base` sets them all to 1 (`P:\DZ\data\config.cpp:3442` onward). The plate carrier lowers `Projectile` `Health` to 0.3 and `Shock` to 0.6 (`P:\DZ\characters\vests\config.cpp:114` to `:130`).
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
