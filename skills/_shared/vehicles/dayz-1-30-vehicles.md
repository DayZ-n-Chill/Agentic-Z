# DayZ 1.30: vehicle script and config changes

What DayZ 1.30 changed for cars, trucks and boats beyond the class tree: lights and light profiles, electricity, horn, the get-in condition, boats, `speedGeoms`, ruined wheels and tyre fields, and a 1.29 to 1.30 migration checklist.

> Status: `class-hierarchy.md` carries the short 1.30 summary (the `Motorbike` sibling and the component refactor); this file holds the rest of the 1.30 vehicle contract. Every `[EXACT]` block was copied by the notes' author from an extraction of DayZ 1.30 Experimental (the `exp\...` paths, 2026-09-17) or read on the build the entry names (1.30.164014 Exp, 1.30.164078, 1.30.164200); in-game results were measured on the third-party mods named in each entry (LFQuad, Arma2Quad) and were not repeated here. A citation written with its full `P:\` path was opened on the vanilla data of this repo. A citation without `P:\` keeps the line number the note was written with, for the DayZ build that entry names, and is not yet checked on `P:\`: Grep for the symbol before relying on the number. Where they were opened, the notes' `carscript.c`, `actiongetintransport.c`, `actionswitchlights.c`, `actioninput.c`, `boat.c`, `inventoryitem.c` and `vehiclelightbase.c` numbers matched this repo's `P:\` (a 1.30 build); the `transport.c` numbers sit 3 to 9 lines lower on `P:\` than written (`:821` for `:830`, `:475` for `:478`, `:672` for `:675`, `:236` for `:239`), and the config numbers differ because `P:\DZ` holds the unpacked `config.cpp` (singletrack `:258` for `:230`, water `:41` for `:59`). Tags such as SP-205 or LL-464 are the notes' own lesson numbers, and `[EXACT]`, `[DESIGN]` and `[CLAIM-...]` are the notes' own evidence labels. Paths such as `<vehicle-import>\...` point into those mods' work folders, which are not part of this repo. "Invariant N", "preflight #N" and "#N" mean the numbered invariants; `skills/dayz-vehicles/SKILL.md` lists which file holds each number. Car and truck authoring that still talks about 1.29 (`CarLightBase`, `CreateFrontLight`, `ForceUpdateLightsStart`) is marked as such in the other pack files.

## Vanilla anchors checked on `P:\`

- `NeedElectricitySourceDevice` returns `true` by default: `P:\scripts\3_game\vehicles\transport.c:821`.
- `GetWeightCoef` returns 1.0 by default: `P:\scripts\3_game\vehicles\transport.c:475`.
- `CanGetIn` returns `true` by default: `P:\scripts\3_game\vehicles\transport.c:672`.
- `ETransportFluid` is declared at `P:\scripts\3_game\vehicles\transport.c:52`.
- `BoatFluid` is that enum under another name: `P:\scripts\3_game\vehicles\boat.c:13`.
- `LightToggle` is native on `Transport`: `P:\scripts\3_game\vehicles\transport.c:236`.
- The switch action calls `LightToggle`: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:64`.
- `ToggleVehicleLightsActionInput` binds `UAToggleVehicleLights`: `P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849`.
- `HasGangedTailAndBrakeLights` returns `false` by default: `P:\scripts\4_world\entities\vehicles\carscript.c:468`.
- `ForceUpdateLightsStart` is an empty obsolete stub: `P:\scripts\4_world\entities\vehicles\carscript.c:2806`.
- `CarScript` registers `ActionVehicleHornShort`: `P:\scripts\4_world\entities\vehicles\carscript.c:2319`.
- The get-in condition calls `CanGetIn` first: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:36`.
- The get-in condition calls `CanReachSeatFromDoors` with 1.0: `P:\scripts\4_world\classes\useractionscomponent\actions\interact\actiongetintransport.c:64`.
- The front profile writes `m_FlaresVisible = false`: `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\vehiclelightprofilebase.c:53`.
- `GetRuinedReplacement` is declared at `P:\scripts\4_world\entities\core\inherited\inventoryitem.c:215`.
- `speedGeomActivation` is 0.29 on the first vanilla motorbike: `P:\DZ\vehicles\singletrack\config.cpp:258`.
- `NoiseBoatEngine` has `strength=30`: `P:\DZ\vehicles\water\config.cpp:41`.
- `Land_Wreck_Truck01_Aban1_Cistern` extends `Well`: `P:\scripts\4_world\entities\building\wrecks\wreck_truck01_aban1_cistern.c:1`.
- `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE` is 32: `P:\scripts\4_world\entities\manbase\dayzplayer\dayzplayercameras.c:20`.
- No file under `P:\scripts` declares or calls `ToggleHeadlights` (Grep, 2026-11-17), and `P:\DZ\vehicles\wheeled\offroadhatchback\offroadhatchback.p3d` reads ODOL version 56, as the two claims below say.

## Where the neighbouring 1.30 material is

Migration of a 1.29 *car* mod also lives in `skills/dayz-motorbikes/references/vehicle-1.30-refactor.md`. Two-wheel work stays in the `dayz-motorbikes` skill. Aviation that inherits `CarScript` is in `skills/dayz-aviation/references/dayz-1-30-aviation.md` of the `dayz-aviation` skill. The class tree and the `CarScript` component refactor are in `class-hierarchy.md`; the light material paths and hidden selection order are in `lights.md`.

## What 1.30 changes (cars / trucks / boats)

| Topic | Until 1.29 | Since 1.30 | Cite |
|---|---|---|---|
| Transport children | `Car` + `Boat` | third sibling `Motorbike` (`simulation = "motorbike"`) | `exp\bin\bin\config.cpp:1054-1059`, `Motorbike.c:30` |
| Headlights | subclass `CarLightBase` + `CreateFrontLight`/`CreateRearLight` | `VehicleLightBase` + `VehicleLightProfileBase` registered on `m_LightsComponent` | `VehicleLightBase.c:1`, `CivilianSedanFrontLight.c:1`, `Offroad_02.c:21-22` |
| Battery vital | `IsVitalCarBattery` / `IsVitalTruckBattery` | `NeedElectricitySourceDevice` / `GetElectricitySourceDevice` / `GetElectricitySourceDeviceType` | `Transport.c:830-842`, `CarScript.c:2811-2817` |
| Horn actions | `ActionCarHornShort`/`Long` | `ActionVehicleHornShort`/`Long`; `CarHorn*ActionInput` are empty aliases | `CarScript.c:2319-2320`, `ActionCarHorn.c:1,69-70,213-214`, `ActionInput.c:757-758,773-774` |
| Light toggle input | `UAToggleHeadlight` (`ToggleLightsActionInput`) | vehicle lights use `UAToggleVehicleLights` (`ToggleVehicleLightsActionInput`) | `ActionSwitchLights.c:16-18`, `ActionInput.c:776-782,849-855`, `bin\constants.xml:90-91` |
| Forced light refresh | `ForceUpdateLightsStart`/`End` | `[Obsolete("1.30: no replacement")]` — delete the calls | `CarScript.c:2805-2809` |
| Headlight toggle | `CarScript.ToggleHeadlights()`, called by `ActionSwitchLights` | **deleted**, with no `[Obsolete]` stub; the action calls the native `Transport.LightToggle()` | 1.29 `CarScript.c:2088`; 1.30.164200 `transport.c:239`, `actionswitchlights.c:64` |
| Script module path | `files[] = {"Mod\scripts\4_world"}` (backslashes) loaded | the same LFQuad path loaded nothing on 1.30.164200; forward slashes load | measured in game, below the table |
| Ruined wheel swap | a `switch` over the vanilla wheel names; a mod wheel was never swapped | every wheel class is swapped for `<class>_Ruined`, and a missing one raises an error | 1.29 `InventoryItem.c:214-248`; 1.30.164200 `inventoryitemtype.c:17-46`; section 11 |
| Fluids | `CarFluid` / isolated `BoatFluid` | `enum ETransportFluid`; `BoatFluid : ETransportFluid {}` | `Transport.c:52-63`, `Boat.c:13` |
| Boat speedo | listed as Car-only | `Boat.GetSpeedometer` + `GetSpeedometerAbsolute` | `Boat.c:42-56` |
| Get-in | `IsAreaAtDoorFree` | `CanGetIn()` then `IsAreaAtDoorFreeDiag`; script **does** call `CanReachSeatFromDoors` | `ActionGetInTransport.c:36,54,64`, `Transport.c:675-678` |
| VFX scale | — | `GetWeightCoef()` (default 1.0) | `Transport.c:478-481` |
| Ganged rear bulbs | — | `HasGangedTailAndBrakeLights()` (default false) | `CarScript.c:468-471,2061-2094` |
| High-speed geom | changelog only | config `speedGeomActivation` + `speedGeoms[]` | `vehicles_singletrack\config.cpp:230-231`; changelog MODDING |
| Motorbike 3PP camera | — | `DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` | `DayZPlayerCameras.c:20,63` — detail in `skills/dayz-motorbikes/references/rider-animation.md` |

[EXACT][CLAIM-ODOL-V56-130] Vanilla P3Ds on 1.30 Exp are ODOL **v56** (1.29 stable: v54); read the P3D header (bytes 4-7) before any extraction or parity tooling on a new build — a v54 reader fails with `ValueError: subsection not found`. [DESIGN] Preflight: on a new build, run a positive control with the previous build's reader before starting vehicle parity work. Measured headers: `Motorbike_01`/`Motorbike_02` and `offroadhatchback` read 56 on 1.30.164014 Exp; the 1.29 `offroadhatchback.p3d` reads 54 and converts cleanly. Full motorbike anatomy tables read from the v56 binaries: `skills/dayz-motorbikes/references/vanilla-p3d-anatomy.md`. An external ODOL->MLOD converter needs a v56-capable reader for 1.30 vanilla models.

[EXACT][CLAIM-VEH-TOGGLEHEADLIGHTS-REMOVED-130] `CarScript.ToggleHeadlights()` is the one light member that 1.30 deleted instead of marking `[Obsolete]`. 1.29 declares it at `CarScript.c:2088` and calls it from `ActionSwitchLights.c:75` and `CarScript.c:834, 3061`; no script of 1.30.164014 Exp, 1.30.164078 or 1.30.164200 declares or calls it, and the switch action toggles the native state with `Transport.LightToggle()` (1.30.164200 `transport.c:239`, `actionswitchlights.c:64`). So a 1.29 car whose script says `override void ToggleHeadlights()` overrides a method that no longer exists, which Enforce refuses to compile: the `4_World` module fails and the game or server does not start with the mod. Measured on the 1.30.164200 DayZDiag server on 2026-10-26, with the LFQuad v1.0.0 scripts and only their module path fixed: `lfquad.c(166): Function 'ToggleHeadlights' is marked as override, but there is no function with this name in the base class`, then `Can't compile "World" script module!` and `ENGINE (F): Crashed`. The `[Obsolete]` members of this table are the opposite case: they compile and are never called. Resolve every `override` against the target build before shipping (migration checklist, item 0).

[EXACT][CLAIM-VEH-SCRIPT-PATH-SLASH-130] A 1.29 script module path written with backslashes can load nothing on 1.30, and say nothing. The LFQuad v1.0.0 `CfgMods` declares `dir = "LFQuad"` and `worldScriptModule` `files[] = {"LFQuad\scripts\4_world"}`, which loaded on 1.29. On the 1.30.164200 DayZDiag server that mod's `World` module came out with 2332 files and CRC32 `c08a388f`, the same as a run without the mod, with and without `-filePatching`: the quad ran as a bare `CarScript`, and the `ToggleHeadlights` compile error above never showed. With `files[] = {"LFQuad/scripts/4_world"}` the module loaded 2337 files, the mod's five scripts (measured 2026-10-26). `@DayZ_MCP`, whose paths use forward slashes, loaded in the same runs. Write module paths with forward slashes, and compare the script log's `Module: World; loaded Nx files` line with a run without the mod: scripts that never load never fail to compile either. This reverses the 1.29 advice of `vehicle-structural-parity.md` (script binding).

## 1. Lights: `VehicleLightBase` + profiles (not `CarLightBase`)

(until 1.29: subclass `CarLightBase` / `CarRearLightBase` and override `CreateFrontLight`/`CreateRearLight`.)

(since 1.30:) `CreateFrontLight`/`CreateRearLight` are `[Obsolete("1.30: use VehicleLightsComponent instead")]` (`CarScript.c:2936-2948`). Vanilla `*FrontLight` classes stay on disk as obsolete wrappers:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\ScriptedLightBase\SpotLightBase\CarLightBase\CivilianSedanFrontLight.c:1-4
[Obsolete("use VehicleLightBase and VehicleLightProfileBase instead")]
class CivilianSedanFrontLight extends CarLightBase
{
	void CivilianSedanFrontLight()
```

The live light entity is `VehicleLightBase : SpotLightBase` (`VehicleLightBase.c:1`). Parameters live on `VehicleLightProfileBase` (`VehicleLightProfiles\VehicleLightProfileBase.c:1-14`). Register in the vehicle ctor:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\InheritedCars\Offroad_02.c:21-22
		m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Offroad_02LightProfileFront()));
		m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new Offroad_02LightProfileRear()));
```

`ActionSwitchLights` now uses `ToggleVehicleLightsActionInput` and `transport.LightToggle()`:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\Vehicles\ActionSwitchLights.c:16-18
	override typename GetInputType()
	{
		return ToggleVehicleLightsActionInput;
	}
```

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\ActionInput.c:849-855
class ToggleVehicleLightsActionInput : DefaultActionInput
{
	ref ActionTarget targetNew;
	
	void ToggleVehicleLightsActionInput(PlayerBase player)
	{
		SetInput("UAToggleVehicleLights");
```

Headgear torches still bind `UAToggleHeadlight` (`ToggleLightsActionInput` at `ActionInput.c:776-782`). A custom car that `SetInput("UAToggleHeadlight")` for vehicle lights will not fire `ActionSwitchLights`.

[DESIGN] LEDs that are not vehicle headlights (bloom vs real light via `PointLightBase`) are unchanged; see `emissive-leds-and-dynamic-lights.md`.

[EXACT][CLAIM-VEH-LIGHTS-EXIT-130] What the native light state does around the driver seat, measured on 1.30.164200 with `DIAG_DEVELOPER` prints in the LFQuad (2026-10-26, Exp and stable DayZDiag, server and client): `OnDriverEnter` and `OnDriverExit` run on both sides; the `Transport.LightToggle()` called by `ActionSwitchLights.OnExecuteServer` has changed `LightIsOn()` on the server by the time it returns (`wasOn=0`, then `lightIsOnAfter=1`); and when the driver gets out with the lights on, `LightIsOn()` stays true on the server and on the client. A 1.29 workaround that relights the headlights after the driver leaves (the LFQuad had one) finds nothing to fix on 1.30, and one keyed on `!LightIsOn()` never shows. Arma2Quad v1.0.1 dropped its own parked beam on the strength of this and measured the same with an `OnDriverExit` print (stable DayZDiag, 2026-10-26): `driver exit server=1 lightIsOn=1 engine=1` on the server and `server=0 lightIsOn=1 engine=1` on the client, the beam still lighting the ground with the player standing next to the quad.

[EXACT][CLAIM-VEH-FRONT-FLARE-STICKY-130] The 1.30 front profile switches its lens flare off for good once both bulbs have lit as one. `VehicleLightProfileFront.ApplyAggregatedValues()` writes `m_FlaresVisible = false` on the profile (1.30.164200 `vehiclelightprofilebase.c:49-54`); `VehicleLightBase.AggregateLight()` calls it and applies the flag, and `SegregateLight()` applies the stored flag without restoring it or calling `ApplySegregatedValues()` (`vehiclelightbase.c:26-53`). The profile is one object per vehicle, kept by its `VehicleLightData` when the light is created again (`vehiclelightscomponent.c:13-25,83-94`), so after the first two-bulb state a headlight left with one bulb shows no flare for the rest of the vehicle's life, also after switching the lights off and on. 1.29 set the flare on in every `CarLightBase.SegregateLight()` (1.29 `CarLightBase.c:38-46`). No vanilla 1.30 profile overrides either method, so the vanilla cars behave the same. The fix Arma2Quad v1.0.1 ships keeps a `ref` to its front profile and sets `m_FlaresVisible = true` in an `UpdateLightsClient` override, before `super`, when `m_HeadlightsState` is `LEFT` or `RIGHT`. Seen in game with it (stable 1.30.164200 DayZDiag, 2026-10-26): one bulb after two, twice, gave a front crop of the headlights with mean brightness 43.08 and 43.09 and no black pixel, against 14.99 with half the crop black for two bulbs; there was no control run without the fix.

[EXACT][CLAIM-VEH-LIGHT-PROFILE-UNREAD-130] Some profile fields are never read on 1.30.164200, so a 1.29 light cannot carry them over through a profile. `m_DaylightVisible` and `m_CastShadow` are only assigned (`vehiclelightprofilebase.c:4-5,36,91-92`), and every `VehicleLightBase` is created with daylight visibility and shadows on (`vehiclelightbase.c:10-19`): a 1.29 rear light that switched both off now shows in daylight and casts shadows, as the vanilla rear lights do. A profile's `m_FadeInTime` is assigned by the vanilla profiles and read nowhere. `m_FadeOutTime` is read, but only by the brake and reverse setters (`vehiclelightbase.c:66,81`), with a default of 0.25 s where 1.29's `CarRearLightBase` hard-coded 0.1 s (1.29 `CarRearLightBase.c:41,52`); the combined brake and reverse state sets a 1 s fade-out on both builds (1.29 `CarScript.c:2349-2353`, 1.30.164200 `vehiclelightscomponent.c:183-185`). And in 1.29 the method `CarRearLight()` of `CarRearLightBase` (1.29 `CarRearLightBase.c:9`) is not that class's constructor, so the defaults it sets never applied: port the values the 1.29 subclass set itself.

## 2. Electricity: `NeedElectricitySourceDevice` (not `IsVital*Battery`)

```c
// [EXACT] exp\scripts\scripts\3_Game\Vehicles\Transport.c:830-843
	bool NeedElectricitySourceDevice()
	{
		return true;
	}
	
	EntityAI GetElectricitySourceDevice()
	{
		return null;
	}
	
	string GetElectricitySourceDeviceType()
	{
		return "";
	}
```

`ActionSwitchLights.ActionCondition` consults that trio (`ActionSwitchLights.c:38-46`). Vanilla Offroad_02:

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\InheritedCars\Offroad_02.c:73-88
	override bool NeedElectricitySourceDevice()
	{
		return true;
	}
	
	override EntityAI GetElectricitySourceDevice()
	{
		super.GetElectricitySourceDevice();
		
		return GetInventory().FindAttachment(CarBattery.SLOT_ID);
	}
	
	override string GetElectricitySourceDeviceType()
	{
		return "CarBattery";
	}
```

Magneto/kickstart bikes override `NeedElectricitySourceDevice()` to `false` (`Motorbike_02.c:31-34`).

[EXACT][CLAIM-VEH-NO-BATTERY-DEFAULT-130] A battery car that does not override the three methods has no battery as far as 1.30 is concerned, with one attached. `Transport` answers `true`, `null` and `""` (1.30.164200 `transport.c:830-843`), and `CarScript.GetBattery()` casts that `null` (`carscript.c:2437-2440`). Three things follow:
- `CheckOperationalRequirements` adds `NO_BATTERY` (`carscript.c:1768-1774`), so the engine never starts;
- `OnBeforeLightOn` refuses (`carscript.c:1841-1851`);
- `ActionSwitchLights` never offers itself to the driver (`actionswitchlights.c:38-43`).

The 1.29 way, overriding `IsVitalCarBattery` or `IsVitalTruckBattery`, still compiles and has no effect (`carscript.c:2811-2821`). Source-verified on 1.30.164200 while porting the LFQuad, 2026-10-26.

## 3. Horn

`CarScript.SetActions()` registers `ActionVehicleHornShort`/`Long` (`CarScript.c:2313-2321`). `ActionCarHornShort`/`Long` are `[Obsolete("replaced by ActionVehicleHornShort/Long")]` (`ActionCarHorn.c:69-70,213-214`). Empty aliases `CarHornShortActionInput : VehicleHornShortActionInput {}` (`ActionInput.c:757-758,773-774`) exist so old typenames still compile; logic lives on the VehicleHorn* parent. Register sounds on `m_HornComponent` in the ctor (`Offroad_02.c:33` pattern; trucks at `Truck_01_Base.c:25-26`).

## 4. `GetWeightCoef` and `HasGangedTailAndBrakeLights`

```c
// [EXACT] exp\scripts\scripts\3_Game\Vehicles\Transport.c:478-481
	float GetWeightCoef()
	{
		return 1.0;
	}
	
```

Vanilla overrides (verified): `Truck_01_Base` → `2.0` (`Truck_01_Base.c:120-123`); `Offroad_02` → `1.5` (`Offroad_02.c:133-136`); `Motorbike_01` → `0.5` (`Motorbike_01.c:84-87`); `Motorbike_02` → `0.75` (`Motorbike_02.c:74-77`). `CarScript` feeds the coef into VFX float modifiers (`CarScript.c:720,793`). Digest M claimed motorbikes return `0.25` from `MotorbikeScript.c:661`; that line *uses* `GetWeightCoef()`, it does not return 0.25.

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Vehicles\CarScript.c:468-471
	bool HasGangedTailAndBrakeLights()
	{
		return false;
	}
```

When true, reverse/position material swaps do not turn the brake selection off (`CarScript.c:2061-2094`). Offroad_02 overrides it to `true` (`Offroad_02.c:68-71`). The bikes are `MotorbikeScript`, which has its own copy, also `false` (`MotorbikeScript.c:169-172`): until 1.30.164078 both vanilla bikes overrode it to `true` (1.30.164078 `motorbike_01.c:28` / `motorbike_02.c:29`), and on 1.30.164200 neither does.

## 5. Get-in (1.30 condition)

(until 1.29: four gates ending at `IsAreaAtDoorFree` + a claim that script never calls `CanReachSeatFromDoors`.)

(since 1.30:) `ActionGetInTransport.ActionCondition` also requires `transport.CanGetIn()` (default `true` on `Transport`, `Transport.c:675-678`) and `IsAreaAtDoorFreeDiag(crewIndex)` (`ActionGetInTransport.c:36,54`). Gate 4 **is** invoked from script:

```c
// [EXACT] exp\scripts\scripts\4_World\Classes\UserActionsComponent\Actions\Interact\ActionGetInTransport.c:54-66
		if (!transport.CrewCanGetThrough(crewIndex) || !transport.IsAreaAtDoorFreeDiag(crewIndex))
			return false;
		
		array<string> selections = new array<string>();
		transport.GetActionComponentNameList(componentIndex, selections);
		int selectionCount = selections.Count();
		vector playerPosition = player.GetPosition();
		
		for (int i = 0; i < selectionCount; ++i)
		{
			if (transport.CanReachSeatFromDoors(selections[i], playerPosition, 1.0))
				return true;
		}
```

The 1 m third argument is therefore observable: vanilla script passes `1.0` (`ActionGetInTransport.c:64`). The 2026-09-07 "engine-native only" reading is false on this build. The measured LFQuad2 cost of changing `GetDoorConditionPointFromSelection` still stands as a 1.29 lesson.

*(Corrected 2026-10-26: the "until 1.29" note at the top of this section is wrong about 1.29, and so was the "engine-native only" reading there.)* [EXACT][CLAIM-VEH-GETIN-REACH-129] 1.29's `ActionGetInTransport.ActionCondition` already ended with the same `CanReachSeatFromDoors(selections[i], player.GetPosition(), 1.0)` loop (1.29 `ActionGetInTransport.c:73`), and `CarScript.CanReachSeatFromDoors` reads the same in both builds. The condition gained only two things in 1.30:
- `CanGetIn()`, default `true` (1.30.164200 `transport.c:675-678`);
- the `IsAreaAtDoorFreeDiag` wrapper, which returns `IsAreaAtDoorFree` unless the DiagMenu toggle `TRANSPORT_FREESPACE_DISABLED` is on (`transport.c:910-924`).

`Start` also keeps its order: it runs `super.Start`, where `OnStartServer`/`OnStartClient` fire, before `StartCommand_Vehicle` (1.29 `ActionGetInTransport.c:82-91`, 1.30.164200 `actiongetintransport.c:71-104`). A mod that adjusts the player in those two hooks, such as a bilateral get-in, sees the same sequence on both builds.

[EXACT][CLAIM-VEH-GETIN-ONE-SIDED-130] The side a rider can get on from is set by the door condition point. `CarScript.CanReachSeatFromDoors` measures the player's distance on the ground plane to the memory point that `GetDoorConditionPointFromSelection(selection)` names (1.30.164200 `carscript.c:2177-2199`), and the action passes 1.0 m (`actiongetintransport.c:64`); it tests horizontal distance only, not the side the player is on. Arma2Quad v1.0.1 has no `seat_con_*` points and returns its approach points `pos_driver` and `pos_codriver`, both at model X -0.82, on the left of the shared bench. On the stable 1.30.164200 DayZDiag (2026-10-28, with `@SurvivorAnims`), next to the left point both seats answered `available=1` in `query_get_in_condition`, the cursor showed `ActionGetInTransport` and the action seated the player; at the same point mirrored to the right both seats answered `first_block="unreachable"` and the cursor showed no action. This is shown for Arma2Quad at the positions tested, not for every vehicle. A get-in check from one side says nothing about the other: run it from both sides, for each seat (dayz-mcp-verify skill, `references/acceptance-ladder.md`, R3b).

## 6. Boats

```c
// [EXACT] exp\scripts\scripts\3_Game\Vehicles\Boat.c:12-13
//!	Type of vehicle's fluid. (native, do not change or extend)
enum BoatFluid : ETransportFluid {}
```

```c
// [EXACT] exp\scripts\scripts\3_Game\Vehicles\Boat.c:42-56
	//!	Returns the current speed of the vehicle in km/h.
	float GetSpeedometer()
	{
		vector transform[4];
		GetTransform(transform);

		float velocity = GetVelocity(this).InvMultiply3(transform)[2];
		return velocity * 3.6;
	}
	
	//! Returns the current speed of the vehicle in km/h. Value is absolute
	float GetSpeedometerAbsolute()
	{
		return Math.AbsFloat(GetSpeedometer());
	}
```

`BoatScript.GetHeatComfortOverride()` at `BoatScript.c:256-259`. Config AI noise `NoiseBoatEngine { strength = 30; }` at `exp\vehicles_water\DZ\vehicles\water\config.cpp:59-63`. `ActionFillFuel` talks to `Transport` via `ETransportFluid.FUEL` (digest M; re-verify that action file if you override fill).

## 7. `speedGeomActivation` / `speedGeoms`

[CHANGELOG] Official MODDING notes: hide named components when travelling at speed to prevent ground snags. Vanilla motorbikes:

```cpp
// [EXACT] exp\vehicles_singletrack\DZ\vehicles\singletrack\config.cpp:230-231
		speedGeomActivation = 0.29;
		speedGeoms[] = {"geotohide"};
```

`Motorbike_02` uses `0.27` (`config.cpp:736-737`). The C++ filter itself is not in Enforce [UNVERIFIED]. Cars/trucks in this extraction were not found declaring the pair [UNVERIFIED] — copy the motorbike pattern only if a high-speed geom snag is measured.

## 8. Wreck cisterns as `Well`

```c
// [EXACT] exp\scripts\scripts\4_World\Entities\Building\Wrecks\Wreck_Truck01_Aban1_Cistern.c:1-2
class Land_Wreck_Truck01_Aban1_Cistern : Well {}
class Land_Wreck_Truck01_Aban1_Cistern_DE : Land_Wreck_Truck01_Aban1_Cistern {}
```

`Land_Wreck_Truck01_Aban2_Cistern` is the same pattern (`Wreck_Truck01_Aban2_Cistern.c`). They drink as wells, not as vehicle wrecks.

Chinook / Mi24 wreck *scripts* exist (`Wreck_Chinook.c:1-24`, `Wreck_Mi24_TK.c:1-11`) with no matching `.p3d` in `structures_wrecks` listings this build — aviation-adjacent; see aviation 1.30 note.

## 9. Motorbike camera (pointer)

`DAYZCAMERA_3RD_VEHICLE_MOTORBIKE = 32` (`DayZPlayerCameras.c:20,63`); class `DayZPlayerCamera3rdPersonVehicleMotorbike` at `DayZPlayerCameraVehicles.c:239` with `CONST_SPRING_SMOOTHTIME_YAW = 0.5`, `CONST_YAW_LAG_REVERSE = 0.3`, `UP_ANGLE_CAP = 10` (`:243-258`). Do not duplicate that contract here — open `skills/dayz-motorbikes/references/rider-animation.md` §2.

## 10. Line-number drift inside these notes (1.29 cites)

The field notes cited these symbols at their 1.29 lines; they now cite the 1.30 lines (same symbols, new lines). The 1.29 column is for copies of the notes written before 1.30:

| Symbol | until 1.29 (notes) | since 1.30 |
|---|---|---|
| `CarScript` ctor `SetEventMask(POSTSIMULATE/POSTFRAME)` | `carscript.c:325-326` | `CarScript.c:207-208` |
| `CarScript.EOnPostSimulate` | `carscript.c:948` | `CarScript.c:807` |
| `CarScript.OnDriverExit` gear-stop | `carscript.c:1207-1215` | `CarScript.c:940-948` |
| `Transport.OnDriverExit` empty body | `transport.c:161` | `Transport.c:227` |
| `ForceUpdateLightsStart`/`End` | `carscript.c:535-536`, `:2981/:2990` | `[Obsolete]` at `CarScript.c:2805-2809`; no replacement |

## 11. Wheels: a `_Ruined` twin and the 1.30 tyre fields

[EXACT][CLAIM-VEH-RUINED-WHEEL-CLASS-130] 1.29 picked a ruined wheel's replacement with a `switch` over the vanilla wheel names (1.29 `InventoryItem.c:214-248`), so a mod wheel stayed as it was and nothing was logged. 1.30 derives the name. When the first entity of a wheel type is created, `CarWheelType.SetReplacementTypes()` takes `<class>_Ruined` as its ruined type, or the intact name for a `_Ruined` class, and calls `ErrorEx` when that config class does not exist (1.30.164200 `inventoryitemtype.c:17-46`). `CarWheel.EEHealthLevelChanged()` then swaps a wheel that reaches `STATE_RUINED` for that class through `ReplaceWheelLambda` (`inventoryitem.c:220-248`). The vanilla pattern is a config class that inherits the intact wheel and a script class that extends `CarWheel_Ruined`:

```cpp
// config.cpp, LFQuad v1.0.1 (the rear wheel is the same)
class LFQuad_Wheel_Front_Ruined: LFQuad_Wheel_Front
{
	scope = 2;
	radius = 0.224;
	tyreOffroadResistance = 0.1;
	tyreGrip = 0.4;
	tyreRollResistance = 0.32;
	tyreRoughness = 0.2;
	tyreLongitudinalFriction = 0.25;
	tyreLateralFriction = 4.95;
};
```

```c
// scripts/4_world, as vanilla does at inventoryitem.c:450-468
class LFQuad_Wheel_Front_Ruined extends CarWheel_Ruined {};
```

Vanilla also registers the two-handed carry profile of each ruined class (`dayzplayercfgbase.c:892-893`), so a mod that registers its wheels in `ModItemRegisterCallbacks.RegisterHeavy` adds the `_Ruined` names there. Measured on the 1.30.164200 DayZDiag server and client (LFQuad, 2026-10-26): without the twins, the first front and the first rear wheel of a session each raised `[CarWheelType::SetReplacementTypes] :: [ERROR] :: No config class entry for wheel entity 'LFQuad_Wheel_Front_Ruined'` (then the rear one) as a `Virtual Machine Exception`, on both sides. With them there was none; both classes spawned with their own script class (`entities_query` reports it as `classname`, and the intact wheel, which has no script class of its own, reads `CarWheel`), and each fitted the slots of its own axle and was refused by the other's. The swap itself was not seen: no test tool sets an item's health, and an RGD5 1.5 m from a loose wheel took it only to 97 %. `PlayWheelExlosionSound()` chooses the burst sound by vanilla class name (`inventoryitem.c:297-320`), so a mod wheel bursts silently unless its `_Ruined` class overrides that method.

Every vanilla 1.30 car wheel also declares `tyreType`, `tyreRoughness`, `tyreLongitudinalFriction` and `tyreLateralFriction`, which a 1.29 wheel does not (values and ranges: `skills/dayz-motorbikes/references/vehicle-1.30-refactor.md`, section 3). The LFQuad took the `Offroad_02_Wheel` set (0, 1, 1.5, 1.8). A copy of that build with a manual gearbox, driven through the MCP bridge on 1.30.164200, reached 46 km/h in about 4.6 s and 71 km/h in 8.4 s on grass, and turned about 77 degrees in 2.8 s at full lock and 40 km/h without rolling over.

[EXACT][CLAIM-VEH-RUINED-OVERRIDES-REDUNDANT-130] A 1.29 mod that already shipped `_Ruined` twins and returned them from overrides of `CarWheel.GetRuinedReplacement()` and `CarWheel_Ruined.GetReplacement()` still compiles on 1.30: both methods remain and now read the names `SetReplacementTypes()` derived (`inventoryitem.c:215-218`, `:342-345`), which are the names such overrides return. Arma2Quad v1.0.1 dropped its four overrides and kept empty script classes, the way vanilla declares its wheels (`inventoryitem.c:449-468`). In game on the stable 1.30.164200 DayZDiag (2026-10-26) its four wheel classes reported their own script class in `entities_query`, no `SetReplacementTypes` error was logged, each ruined wheel fitted the two slots of its own axle and was refused by the other's, and the mounted ruined wheels drew their own torn-tyre models through their proxies. A copy with a manual gearbox and the `Offroad_02_Wheel` tyre set reached 34 to 39 km/h in 2.8 s, turned about 65 degrees in 2.3 s at full lock and 38 to 47 km/h without rolling over, and stopped from about 38 km/h in about 1.6 s.

## Migration checklist (1.29 car → 1.30)

0. Resolve every `override` of the car's scripts against the 1.30 class chain, class by class and not by method name. A method 1.30 deleted (`ToggleHeadlights`) fails the module's compile; an `[Obsolete]` one compiles and is never called. [EXACT][CLAIM-VEH-OVERRIDE-RESOLVE-130] On 2026-10-26 the script validator (`scripts/tools/dayz-script-validator/`), with `--vanilla-root` on the 1.30.164200 tree, returned PASS with 0 errors on the LFQuad v1.0.0 scripts, which override `ToggleHeadlights`. A class-chain resolver over the same tree reported that override as missing and three others as `[Obsolete]`, and it resolved all 211 overrides of the vanilla `inheritedcars` folder without a finding.
1. Delete overrides of `ToggleHeadlights` (deleted in 1.30) / `CreateFrontLight` / `CreateRearLight` / `IsVitalCarBattery` / `IsVitalTruckBattery` / `CarPartsHealthCheck` / `ForceUpdateLightsStart`/`End`.
2. Instantiate / keep `m_LightsComponent`, `m_HornComponent`, `m_VFXComponent` (already constructed on `CarScript` in 1.30).
3. `RegisterLight("Front"|"Rear", new VehicleLightData(new YourProfile()))` and `RegisterSound(VehicleHornMode.SHORT/LONG, "...")`.
4. Override `NeedElectricitySourceDevice` + getters if the vehicle needs a battery; return false for magneto. Without the getters a battery car reports `NO_BATTERY` with a battery attached (section 2).
5. Bind vehicle light action to `UAToggleVehicleLights`, not `UAToggleHeadlight`.
6. `SetActions` / `AddAction(ActionVehicleHornShort/Long)` — not `ActionCarHorn*`.
7. Override `GetWeightCoef` if dust/exhaust scale is wrong; override `HasGangedTailAndBrakeLights` if brake+tail share a bulb.
8. If get-in vanished, implement `CanGetIn()` and check `IsAreaAtDoorFreeDiag` plus `CanReachSeatFromDoors` from the action.
9. Fluid fill uses `ETransportFluid` / `GetFluidCapacityScript` on `Transport`.
10. Re-verify every `carscript.c:NNNN` cite in this pack against the 1.30 file before shipping.
11. Write the `CfgMods` script module paths with forward slashes, and check the script log's `Module: World; loaded Nx files` line against a run without the mod (the path claim below the table).
12. Give every wheel class a `<class>_Ruined` config twin and a script class extending `CarWheel_Ruined`, and register the twins in `RegisterHeavy` if the intact wheels are registered there (section 11).
13. Declare the four 1.30 tyre fields on every wheel (section 11).
14. [DESIGN] Before porting a published mod, hash the PBO players run (the Workshop item) against the release or tree you port. Measured case, 2026-10-26: the Arma2Quad Workshop item 3799875083 carried an earlier tuning than its GitHub v1.0.0 (suspension twice as stiff, clutch 140 against 180, steering animation ±30 against ±45 degrees, the opposite wheel spin, no Central Economy full tank), so a port of the release also changes the handling Workshop players know.
15. A front profile that should keep the 1.29 single-bulb lens flare needs the `UpdateLightsClient` restore of section 1; a 1.29 parked-headlights workaround has nothing left to fix on 1.30 (section 1, the driver-exit claim).
