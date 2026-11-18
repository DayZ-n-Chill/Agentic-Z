# Protection and insulation

Covers how warm a wearable keeps the player, how wet it gets, how much damage it stops, what it filters, and how it is repaired.

## Insulation: `heatIsolation`

`heatIsolation` is read into the item type at `P:\scripts\4_world\entities\itembasetype.c:84`. `MiscGameplayFunctions.GetCurrentItemHeatIsolation` (`P:\scripts\4_world\static\miscgameplayfunctions.c:1363`) multiplies it by a wetness factor and a health factor.

| Wetness (`GetWet()`) | Factor | Where |
|---|---|---|
| Dry, below `STATE_DAMP` (0.05) | 1.0, `ENVIRO_ISOLATION_WETFACTOR_DRY` | `P:\scripts\3_game\constants.c:821` |
| Damp, from 0.05 | 0.9 | `:822` |
| Wet, from `STATE_WET` (0.25) | 0.5 | `:823` |
| Soaking wet, from `STATE_SOAKING_WET` (0.5) | 0.1 | `:824` |
| Drenched, from `STATE_DRENCHED` (0.8) | returns -0.15 outright | `:825` |

The wetness states `STATE_DRENCHED` to `STATE_DRY` are at `P:\scripts\3_game\constants.c:933` to `:937`. The factors are applied at `P:\scripts\4_world\static\miscgameplayfunctions.c:1372` to `:1420`.

| Health level | Factor | Where |
|---|---|---|
| Pristine | 1.0, `ENVIRO_ISOLATION_HEALTHFACTOR_PRISTINE` | `P:\scripts\3_game\constants.c:827` |
| Worn | 0.9 | `:828` |
| Damaged | 0.8 | `:829` |
| Badly damaged | 0.5 | `:830` |
| Ruined | 0.0 | `:831` |

The inspect menu labels the result (`P:\scripts\5_mission\gui\inspectmenunew.c:456`) with the thresholds `HEATISO_THRESHOLD_BAD` 0.2, `_LOW` 0.4, `_MEDIUM` 0.6 and `_HIGH` 0.8 (`P:\scripts\3_game\constants.c:1014` to `:1017`). Above 0.8 shows as the best label.

Vanilla values to compare with: `TShirt_ColorBase` (`P:\DZ\characters\tops\config.cpp:2244`) 0.1 (`:2263`), `UKAssVest_ColorBase` (`P:\DZ\characters\vests\config.cpp:866`) 0.5 (`:892`), `PlateCarrierVest` (`:24`) 0.8 (`:52`). `Inventory_Base` defaults `heatIsolation` to 0 (`P:\DZ\data\config.cpp:3190`), so a wearable that leaves the key out gives no warmth.

## Wetness: `varWetMax`

`varWetMax` is the most wetness the item can reach (`P:\scripts\4_world\entities\itembasetype.c:71`). A T-shirt uses 1 (`P:\DZ\characters\tops\config.cpp:2262`). The plate carrier uses 0.49 (`P:\DZ\characters\vests\config.cpp:51`), which keeps it below the soaking wet state at 0.5, so its wetness factor never drops below 0.5.

The item type reads `varWetInit`, `varWetMin` and `varWetMax` together (`P:\scripts\4_world\entities\itembasetype.c:69` to `:71`). `ItemBase.GetWetMax` returns the type's value (`P:\scripts\4_world\entities\itembase.c:3726`), and a new item starts at `m_VarWetInit` (`P:\scripts\4_world\entities\itembase.c:165`).

### How fast it soaks and dries: `EnvironmentWetnessIncrements`

The item type also reads a class `EnvironmentWetnessIncrements` with two subclasses, `Soaking` and `Drying` (`P:\scripts\4_world\entities\itembasetype.c:124` to `:137`). The defaults sit on `Inventory_Base` (`P:\DZ\data\config.cpp:3162`) and are inherited by every item unless a class declares its own block (`:3191` to `:3205`):

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

- Washing the head wets each worn slot by a fixed amount. `ActionWashHeadWettingClothesBase` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheadwettingclothesbase.c:1`) holds two maps, one for washing from a container and one for washing at a water surface (`:13` to `:22` and `:31` to `:40`). From a container, `InventorySlots.HEADGEAR` and `MASK` get 0.24, `BODY` 0.12, `VEST` 0.08, `LEGS`, `ARMBAND` and `HIPS` 0.06, `GLOVES`, `FEET` and `BACK` 0.04. At a surface, `HEADGEAR` gets 0.12 and `GLOVES` 0.24; the rest are the same.
- The same action lowers the `eAgents.EYES_IRRITATION` agent and the player's thermal bias, on the server when it finishes (`OnFinishProgressServer`, `P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheadwettingclothesbase.c:49`). It adds minus `THERMAL_BIAS_WASH_HEAD_DECREMENT` through `GetThermalBiasHandler().Add` only while the handler's temporary resistance is 0, then sets that resistance to `THERMAL_BIAS_WASH_HEAD_TEMPORARY_RESISTANCE_TIME` (`:56` to `:60`), so washing again within that time does not cool the player further. The constant is 0.175 and the time 30.0 (`P:\scripts\3_game\playerconstants.c:203` and `:204`). An action cut short applies the bias and the wetness scaled by its progress (`OnEndServer`, `actionwashheadwettingclothesbase.c:65` to `:73`).
- `ActionWetClothingInHandsWater` wets a clothing item held in hands. Its `ActionCondition` needs `IsClothing()` and `GetWet()` below `GetWetMax()` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwetclothinginhandswater.c:20`), and it targets water through `CCTLiquid` (`:17`).
- Washing the head from a bottle is not blocked when the bottle is frozen: `ActionWashHeadItemContinuous.ActionCondition` only refuses `LIQUID_GASOLINE` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\actionwashheaditemcontinuous.c:32` to `:39`), and its item condition `CCINotRuinedAndEmpty` checks only ruin and quantity (`:23`), so nothing calls `GetIsFrozen()`. That Bohemia lists this as a known 1.30 issue is not checked on `P:\`.

These two constants are the only tie to heat stroke covered here. Do not treat washing the head as a full heat stroke API.

## Armor: `DamageSystem`

- `GlobalHealth` `Health` holds `hitpoints` and `healthLevels[]`. Each level pairs a health fraction with the `.rvmat` files to show at that level, one per visual material. The plate carrier has 225 hitpoints (`P:\DZ\characters\vests\config.cpp:67`); a T-shirt has 50 and lists a worn and a ground material per level (`P:\DZ\characters\tops\config.cpp:2276` onward).
- `GlobalArmor` holds one class per damage source, each with `Health`, `Blood` and `Shock` `damage` values. `Clothing_Base` sets `Projectile`, `Melee` and `FragGrenade` to 1 (`P:\DZ\data\config.cpp:3463` to `:3510`). Armored items add an `Infected` class as well, as the plate carrier does (`P:\DZ\characters\vests\config.cpp:146`). The plate carrier lowers `Projectile` `Health` to 0.3 and `Shock` to 0.6 (`P:\DZ\characters\vests\config.cpp:114` to `:130`).
- **Engine:** an armor value multiplies the damage of that type that reaches the wearer, so lower means more protection. Confirm a new value in game.
- A color variant that redeclares `DamageSystem` must inherit each level (`class DamageSystem: DamageSystem`, `class GlobalHealth: GlobalHealth`, `class Health: Health`), as `PlateCarrierVest_Black` does at `P:\DZ\characters\vests\config.cpp:209` to `:213`. Leave it out when the color only changes textures.

## Filters: the `Protection` class

`ItemBase.GetProtectionLevel(int type, bool consider_filter = false, int system = 0)` (`P:\scripts\4_world\entities\itembase.c:4077`) reads `CfgVehicles <type> Protection <entry>` (`:4103`). It returns 0 when the item is ruined, or has quantity and that quantity is 0 (`:4079` and `:4080`); an unknown `type` reads `biological`.

| `type` constant | Config entry | Where |
|---|---|---|
| `DEF_BIOLOGICAL` = 1 | `biological` | `P:\scripts\3_game\constants.c:547` |
| `DEF_CHEMICAL` = 2 | `chemical` | `:548` |
| `DEF_DUST_PARTICLE_BREATH` = 3 | `dust_particle_breath` | `:549` |
| `DEF_DUST_PARTICLE_EYES` = 4 | `dust_particle_eyes` | `:550` |

Vanilla `GasMask` sets all four to 1 (`P:\DZ\characters\masks\config.cpp:134`); `NioshFaceMask` sets `biological=0.75` and `dust_particle_breath=1` (`:256`). Masks with a filter slot override the call to read the filter instead, as `GP5GasMask` does with the `GasMaskFilter` slot (`P:\scripts\4_world\entities\itembase\clothing\gp5gasmask.c:13`). That is script work for the script team.

### Which items the game asks

Airborne agents read protection only from worn items whose script class reports a cached equipment category. `GetCachedEquipmentCategory()` returns `NONE` on every entity (`P:\scripts\3_game\entities\entityai.c:322` to `:325`); `Mask_Base` returns `MASK` and `Glasses_Base` returns `EYEWEAR` (`P:\scripts\4_world\entities\itembase\clothing_base.c:176` and `:196`).

| Agent | Protection type | Categories asked | Where |
|---|---|---|---|
| Chemical gas (`AGT_AIRBOURNE_CHEMICAL`) | `DEF_CHEMICAL` | `MASK` | `P:\scripts\4_world\plugins\pluginbase\plugintransmissionagents.c:405` to `:410` |
| Silicosis (sandstorm) | `DEF_DUST_PARTICLE_BREATH` | `MASK` | `:420` to `:425` |
| Eye irritation (sandstorm) | `DEF_DUST_PARTICLE_EYES` | `EYEWEAR`, `MASK`, `NVG` | `:427` to `:432` |

`GetProtectionLevelCachedEquipment` adds up the level of every matching attachment, to a depth of 2 (`:577` to `:594`). A mod mask whose config parent is plain `Clothing`, with no script class under `Mask_Base`, has category `NONE`, so its `Protection` class is never read and it stops no gas or dust. Inherit a vanilla mask (or give the script class a `Mask_Base` parent) for the protection to count. A helmet with a visor reports its own category by override, as `DirtBikeHelmet_ColorBase` does (`P:\scripts\4_world\entities\itembase\clothing\helmetbase\dirtbikehelmet_colorbase.c:3`).

### Masks with a filter slot

On the two cartridge masks the protection sits on the filter, not on the mask.

- `GP5GasMask` and `AirborneMask` both declare `attachments[]` with `"GasMaskFilter"` (`P:\DZ\characters\masks\config.cpp:855` and `:984`). Their `Protection` class holds only `dust_particle_eyes=1` (`P:\DZ\characters\masks\config.cpp:951` and `:1084`). The keys `biological` and `dust_particle_breath` are left out, not set to 0. Before 1.30 both masks also set `biological=1` and `dust_particle_breath=1` (from the 1.29 files, which are not on `P:\`).
- The filter item is `GasMask_Filter` (`P:\DZ\gear\consumables\config.cpp:4295`), which goes in the `GasMaskFilter` slot and sets `biological`, `chemical` and `dust_particle_breath` to 1 in its `Protection` class (`:4324`). It has a quantity of 150 (`varQuantityInit` and `varQuantityMax`, `:4309` and `:4311`), and the base `GetProtectionLevel` returns 0 for an item with quantity at 0, so a spent filter protects nothing. The masks addon also defines `GP5GasMask_Filter` with `scope=0` for the same slot (`P:\DZ\characters\masks\config.cpp:1107`). There is no class named `FilterBase`.
- With a filter attached, `GetProtectionLevel` on the mask returns 1.0 for `DEF_DUST_PARTICLE_EYES` and the filter's level for every other type. With no filter it falls through to `super`, which reads the mask's own `Protection` class. A destroyed mask returns 0 (`P:\scripts\4_world\entities\itembase\clothing\gp5gasmask.c:13` to `:28`). `AirborneMask` has the same override (`P:\scripts\4_world\entities\itembase\clothing\airbornemask.c:18` to `:33`) and also reports itself as both `MASK` and `EYEWEAR` (`:3` to `:6`).
- The sealed `GasMask` has no filter slot and keeps full passive protection in its own `Protection` class (`P:\DZ\characters\masks\config.cpp:134`).

A mod mask that works with cartridges attaches `GasMaskFilter` and does not rely on `biological` on the mask itself. A copy of the GP5 that hardcodes `biological` on the mask, or leaves out the `GasMaskFilter` attachment, does not behave like the vanilla 1.30 masks.

## Repair: `repairableWithKits[]` and `repairCosts[]`

`repairableWithKits[]` lists kit types and `repairCosts[]` the cost for each, in the same order. A kit's type is its `repairKitType`. `PluginRepairing.GetKitRepairCost` matches the kit's type against the list and takes the cost at the same index (`P:\scripts\4_world\plugins\pluginbase\pluginrepairing.c:143` to `:161`); a type missing from the list costs 0.

- One repair raises the item one health level and takes the cost from the kit's quantity; a kit with less quantity left than the cost is emptied (`pluginrepairing.c:29` to `:84`).
- An item repairs to pristine only when `CanBeRepairedToPristine()` returns true, and it returns false on every object unless a script class overrides it (`P:\scripts\3_game\entities\object.c:1356`). So clothing repairs no higher than worn (`pluginrepairing.c:43` to `:48`).

| Type | Kit | `repairKitType` line |
|---|---|---|
| 1 | `WeaponCleaningKit` | `P:\DZ\gear\tools\config.cpp:1016` |
| 2 | `SewingKit` | `:1108` |
| 3 | `LeatherSewingKit` | `:1203` |
| 4 | `Whetstone` | `:5552` |
| 5 | `DuctTape` | `P:\DZ\gear\consumables\config.cpp:259` |
| 7 | `ElectronicRepairKit` | `P:\DZ\gear\tools\config.cpp:5365` |
| 8 | `EpoxyPutty` | `:5459` |
| 10 | `Blowtorch` | `:6173` |

The line is the kit's `repairKitType`; the class starts a few lines above it (`WeaponCleaningKit` at `tools\config.cpp:998`, `DuctTape` at `consumables\config.cpp:241`, `ElectronicRepairKit` at `tools\config.cpp:5348`).

Cloth uses duct tape and a sewing kit (`{5,2}` with costs `{30,25}` on `TShirt_ColorBase`, `P:\DZ\characters\tops\config.cpp:2266` and `:2267`). The plate carrier uses the leather sewing kit and epoxy putty (`{3,8}` with costs `{75,50}`, `P:\DZ\characters\vests\config.cpp:53` and `:54`).
