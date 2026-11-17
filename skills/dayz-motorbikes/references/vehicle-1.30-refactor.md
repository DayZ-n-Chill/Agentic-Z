# Vehicle refactor in DayZ 1.30 (1.29 to 1.30 migration guide)

How DayZ 1.30 restructured the vehicle scripts: `CarScript` split into components, duties moved up to `Transport`, and what an existing car mod has to change. Short citations: `config.cpp:N` is `P:\DZ\vehicles\singletrack\config.cpp`, and a bare script file name is the file of that name under `P:\scripts\` (`motorbike_01.c` and `motorbike_02.c` are the ones in `4_world\entities\vehicles\inheritedmotorbikes\`). Line numbers match the 1.30 data on `P:\` at the time of writing; when a line has moved, Grep for the symbol. In this file `wheeled\config.cpp` is `P:\DZ\vehicles\wheeled\config.cpp`. Statements about 1.29, including the line counts against it, are not yet checked on `P:\`, which holds only the 1.30 data.

---

## 1. Responsibility Decomposition in CarScript and Transport

In DayZ 1.30, `carscript.c` (-1155 / +877 lines against 1.29) ceases to be a self-contained monolith:
- **Moved to `transport.c` (+438 lines against 1.29)**:
  - Unified fluids definition: `enum ETransportFluid` (`transport.c:52-63`), from which `CarFluid`, `BoatFluid`, and `MotorbikeFluid` inherit.
  - Physics collision caching and handling: `m_ContactCache`, `m_MomentumPrevTick`, `m_VelocityPrevTick`, `m_dmgContactCoef`, `m_VehicleContactDamageCoef`, `m_CrewContactDamageCoef` (`transport.c:90-96`).
  - Impact callback: `OnContact(...)` (`transport.c:315`).
  - Electrical source detection: `NeedElectricitySourceDevice()`, `GetElectricitySourceDevice()`, `GetElectricitySourceDeviceType()` (`transport.c:821-834`; default returns `true`, `null`, and `""`).
  - Vital parts check with callback: `CheckVitalItemCallback(...)` and virtual declaration `PartsHealthCheck()` (`transport.c:420, 437`).
- **Moved to modular components (`P:\scripts\4_world\entities\vehicles\components\`)**:
  - Lights and reflectors -> `VehicleLightsComponent`.
  - Horn and AI acoustic noise -> `VehicleHornComponent`.
  - Exhaust, radiator, and wheel dust particles -> `VehicleVFXComponent`.

---

## 2. Removed and Obsolete-Marked Methods

`carscript.c` includes an explicit `//! DEPRECATED` section (`P:\scripts\4_world\entities\vehicles\carscript.c:2760-2981`):

| Obsolete Method in 1.30 | Official Code Annotation | Corrective Action in Mod |
|---|---|---|
| `CreateFrontLight()` | `[Obsolete("1.30: use VehicleLightsComponent instead")]` | Register `VehicleLightProfileFront` in `m_LightsComponent`. |
| `CreateRearLight()` | `[Obsolete("1.30: use VehicleLightsComponent instead")]` | Register `VehicleLightProfileRear` in `m_LightsComponent`. |
| `IsVitalCarBattery()` | `[Obsolete("1.30: use Transport.NeedElectricitySourceDevice")]` | Override `NeedElectricitySourceDevice()`, `GetElectricitySourceDevice()` and `GetElectricitySourceDeviceType()` (Step 4). |
| `IsVitalTruckBattery()` | `[Obsolete("1.30: use Transport.NeedElectricitySourceDevice")]` | Override `NeedElectricitySourceDevice()`, `GetElectricitySourceDevice()` and `GetElectricitySourceDeviceType()` (Step 4). |
| `IsScriptedLightsOn()` | `[Obsolete("1.30: use Transport.LightIsOn")]` | Invoke `LightIsOn()`. |
| `CarPartsHealthCheck()` | `[Obsolete("1.30: use Transport::PartsHealthCheck instead")]` | Rename signature to `override protected void PartsHealthCheck()`. |
| `CheckVitalItem(bool, int)` | `[Obsolete("1.30: use Transport::CheckVitalItemCallback instead")]` | Use `CheckVitalItemCallback(...)`. |
| `OnBeforeSwitchLights()` | `[Obsolete("1.30: no replacement")]` | Remove prior logic; control is immediate in components. |
| `ForceUpdateLightsStart/End()` | `[Obsolete("1.30: no replacement")]` | Remove manual lights synchronization. |
| `BrakesRearLight()`, etc. | `[Obsolete("1.30: use VehicleLightsComponent instead")]` | Use `m_LightsComponent.SetLightTypeAndMode(...)`. |
| `ToggleHeadlights()` | none: **deleted**, not in this section | Remove the override; it no longer compiles. |

[EXACT] Two rows of this table are easy to get wrong when moving a 1.29 vehicle to 1.30 (the 1.30 lines below were read on `P:\`).
- `ToggleHeadlights()` is not in the `DEPRECATED` section because 1.30 deleted it: `carscript.c` on `P:\` has no such method (1.29 declared it in `CarScript`). In 1.30 `ActionSwitchLights` calls the native `Transport.LightToggle()` instead (`actionswitchlights.c:64`; declared at `transport.c:236`). An `override` of it stops the module from compiling.
- For the battery rows, overriding `NeedElectricitySourceDevice()` to return `true` is not enough: that is already the default (`transport.c:821-824`). What a battery car needs is `GetElectricitySourceDevice()`, because the default `null` (`transport.c:826-829`) reaches `CarScript` through `GetBattery()` (`carscript.c:2437-2440`) and makes it report `NO_BATTERY` with a battery attached (`carscript.c:1768-1774`).

More on 1.30 cars: `skills/_shared/vehicles/dayz-1-30-vehicles.md`.

---

## 3. New Tyre Physics Parameters in config.cpp

In DayZ 1.30, all car wheel classes (`HatchbackWheel`, `CivSedanWheel`, `Offroad_02_Wheel`, etc.) incorporate four new physical parameters, absent in 1.29 (example in `HatchbackWheel`: `P:\DZ\vehicles\wheeled\config.cpp:874-880`):
- `tyreType = 0;`: Tyre type identifier.
- `tyreRoughness = 1.0;` (pristine) / `0.2;` (ruined): Ground surface roughness.
- `tyreLongitudinalFriction = 0.85 - 1.5;` (`2.5` in `Truck_01_WheelDouble`, `wheeled\config.cpp:18147`): longitudinal grip during acceleration and braking. On ruined wheels it drops to `0.25 - 0.35`.
- `tyreLateralFriction = 0.95 - 1.8;` (`2.8` in `Truck_01_WheelDouble`, `wheeled\config.cpp:18148`): lateral skid resistance. On ruined rims it rises to `4.95` across all wheels; that this mimics metal on asphalt is an interpretation [UNVERIFIED].

> **Cars only.** These ranges come from `vehicles_wheeled`; motorbike wheels (`P:\DZ\vehicles\singletrack\config.cpp`) do not follow them: `tyreType = 1` (`:167, 200, 1033, 1065`); pristine `tyreLateralFriction` 3.0-7.0 (`:173, 206, 1038, 1070`) and ruined 0.5 (`:185, 218, 1049, 1081`), meaning it drops when ruined rather than rising; pristine `tyreLongitudinalFriction` 0.85-1.8 (`:172, 205, 1037, 1069`) and ruined 0.5 (`:184, 217, 1048, 1080`); Motorbike_02 wheels do not declare `tyreRoughness` (`:1019-1082`). For a bike, start from `:154-219` (Motorbike_01) or `:1019-1082` (Motorbike_02).

---

## 4. Restructuring of Offroad_02 (Bohemia's Reference Example)

1. **Dual door selection (`hiddenSelections`)**:
   `Offroad_02` doors now differentiate exterior and interior panels:
   `hiddenSelections[] = {"texture_roof_ext","texture_roof_int"};` (`wheeled\config.cpp:20587-20601`).
   The `Doors` damage zone includes dual `.rvmat` arrays in `RefTexsMats[]` and `healthLevels[]`.
2. **Front impact zone adjustment**:
   In `DamageZones -> Front`, `"dmgZone_bumper_1"` is removed (on `P:\` the `Offroad_02` class, from `wheeled\config.cpp:20899` on, has no `dmgZone_bumper_1`; that 1.29 had it is not yet checked on `P:\`); whether this is to avoid parasitic damage when hitting the bumper is an interpretation [UNVERIFIED].
3. **New beige variants**:
   `Offroad_02_Beige` and `_BeigeRust` parts are introduced (`wheeled\config.cpp:22394, 23441`; they do not exist in 1.29).

---

## 5. Migration Checklist for a Car Mod from 1.29 to 1.30

Follow this step-by-step list to update an existing car:

- [EXACT] **Step 1: Remove obsolete light factories**:
  Delete any implementation of `override CarLightBase CreateFrontLight()` and `override CarRearLightBase CreateRearLight()`, and any override of `ToggleHeadlights()`, which 1.30 deleted (section 2).
- [EXACT] **Step 2: Register lighting profiles**:
  Create your profile derived from `VehicleLightProfileFront` / `VehicleLightProfileRear` and register it in the vehicle constructor:
  ```c
  m_LightsComponent.RegisterLight("Front", new VehicleLightData(new MyCarLightProfileFront()));
  m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new MyCarLightProfileRear()));
  ```
- [EXACT] **Step 3: Register horn in component**:
  In the constructor, replace `m_CarHornShortSoundName` with:
  ```c
  m_HornComponent.RegisterSound(VehicleHornMode.SHORT, "MyCar_Horn_Short_SoundSet");
  m_HornComponent.RegisterSound(VehicleHornMode.LONG,  "MyCar_Horn_Long_SoundSet");
  ```
- [EXACT] **Step 4: Update electrical supply**:
  Replace `IsVitalCarBattery()` and `IsVitalTruckBattery()` with the new `Transport` API:
  ```c
  override bool NeedElectricitySourceDevice() { return true; }
  override EntityAI GetElectricitySourceDevice() { return GetInventory().FindAttachment(CarBattery.SLOT_ID); }
  override string GetElectricitySourceDeviceType() { return "CarBattery"; }
  ```
- [EXACT] **Step 5: Rename signatures and collision data access**:
  - If you had `protected void CarPartsHealthCheck()`, change it to `override protected void PartsHealthCheck()`.
  - If you were reading `data[0].impulse`, update it to `data[0].m_Impulse`: it is a public member of `VehicleContactData` (`transport.c:1144-1148`), and `CarContactData` remains as an empty subclass (`carscript.c:53`).
- [EXACT] **Step 6: Update horn actions**:
  Verify that your vehicle actions register `ActionVehicleHornShort` and `ActionVehicleHornLong` instead of the legacy `ActionCarHorn*`.
- [DESIGN] **Step 7: Add modern friction in wheel config.cpp**:
  Ensure that your mod's wheels define `tyreRoughness`, `tyreLongitudinalFriction`, and `tyreLateralFriction`.

---

## 6. Claims in 1.29 Guides That Become False in 1.30

| Common claim in 1.29 guides | Reality in DayZ 1.30 | Evidence citation |
|---|---|---|
| *"To add lights to a car you must override `CreateFrontLight()` and create a `CarLightBase`"* | **FALSE**. Those methods are deprecated (`[Obsolete]`). The engine does not invoke them; you must create a `VehicleLightProfileBase` and register it in `m_LightsComponent`. | `carscript.c:2937-2945` and `vehiclelightscomponent.c:61-64` |
| *"The horn is scripted with `SetCarHornState(ECarHornState)` and `ActionCarHorn`"* | **HALF TRUE**. `SetCarHornState` still works: it is a live method outside the deprecated section, it passes the call to `m_HornComponent.SetMode`, and vanilla `OnAction` still calls it. Only the `ActionCarHorn*` classes are obsolete (`[Obsolete("replaced by ActionVehicleHornBase")]`); cars now register `ActionVehicleHornShort/Long`. | `carscript.c:2481-2487`, `carscript.c:2661-2669`, `actioncarhorn.c:1-2`, `carscript.c:2319-2320`, and `vehiclehorncomponent.c:41-53` |
| *"The battery is validated with `IsVitalCarBattery()`"* | **FALSE**. Obsolete method with no effect on starting. `Transport.NeedElectricitySourceDevice()` is consulted now. | `carscript.c:2811-2817` and `transport.c:821` |
| *"Engine parts checking is scripted in `CarPartsHealthCheck()`"* | **FALSE**. The signature was absorbed by `transport.c` and renamed to `PartsHealthCheck()`. | `transport.c:437`, `carscript.c:2121`, and `carscript.c:2976-2979` |
| *"Collision impulses are read in `data[0].impulse`"* | **FALSE**. The field is now `m_Impulse`, public, in the base class `VehicleContactData`; `CarContactData` is an empty subclass. No `impulse` member exists, so `.impulse` should not compile [UNVERIFIED: not compiled]. | `transport.c:1144-1148` and `carscript.c:53` |
| *"Exhaust smoke is controlled directly via `m_exhaustFx`"* | **FALSE**. Manual FX variables are obsolete. The entire particle pipeline is managed in `VehicleVFXComponent`. | `carscript.c:477-478` (`m_VFXComponent.PlayEffect`) and `carscript.c:2760, 2779` (`m_exhaustFx` remains in the `//! DEPRECATED` section) |
| *"Vehicle animation graphs are inaccessible `.agr` binary files"* | **FALSE**. In 1.30, `vehicles.agf` is shipped as editable Enfusion structured text. (corrected 2026-09-28) It was already false in 1.29, so it is not a 1.29 truth that 1.30 broke: 1.29 ships the vehicle sub-graph as the text `Vehicles.agr` in the old `$AnimGraph 7` format, and 1.30 changed the syntax. | `P:\DZ\anims\workspaces\player\player_main\vehicles.agf:1-3655`; line 1 of the 1.29 `Vehicles.agr` (1.29 is not on `P:\`) |
| *"Bailing out while moving always uses the unique 8 km/h threshold of cars"* | **FALSE**. Dedicated thresholds exist: 8 km/h for cars, 5 km/h for boats, and 10 km/h for motorbikes (`MOTO_JUMPOUT_THRESHOLD`). | `actiongetouttransport.c:34-36` |
