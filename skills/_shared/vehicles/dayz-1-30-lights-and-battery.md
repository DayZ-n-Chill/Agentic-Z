# DayZ 1.30 lights, battery and horn

How a 1.30 car registers its lights, what the light toggle and the driver seat do to the light state, which profile fields are dead, how a car declares its battery, and where the horn, effect scale and ganged rear bulbs moved.

Every line cites the 1.30 scripts on `P:\` unless it is marked 1.29. In-game results were measured on test quads and are mod behaviour. The rest of the 1.30 changes are indexed in `dayz-1-30-vehicles.md`.

## Lights: VehicleLightBase and profiles

On 1.29 a car subclassed `CarLightBase` or `CarRearLightBase` and overrode `CreateFrontLight` and `CreateRearLight`. On 1.30 those two are `[Obsolete("1.30: use VehicleLightsComponent instead")]` (`P:\scripts\4_world\entities\vehicles\carscript.c:2936` to `:2948`), and the vanilla per car light classes remain only as obsolete wrappers. From `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\carlightbase\civiliansedanfrontlight.c:1`:

```c
[Obsolete("use VehicleLightBase and VehicleLightProfileBase instead")]
class CivilianSedanFrontLight extends CarLightBase
```

The live light is `VehicleLightBase : SpotLightBase` (`P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightbase.c:1`). Its settings live on a `VehicleLightProfileBase` (`P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightprofiles\vehiclelightprofilebase.c:1` to `:14`). Register them with `m_LightsComponent.RegisterLight` in the vehicle's constructor, as `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:21` and `:22` does:

```c
		m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Offroad_02LightProfileFront()));
		m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new Offroad_02LightProfileRear()));
```

`ActionSwitchLights` returns `ToggleVehicleLightsActionInput` from `GetInputType()` (`P:\scripts\4_world\classes\useractionscomponent\actions\interact\vehicles\actionswitchlights.c:16` to `:18`), which binds `UAToggleVehicleLights` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849` to `:855`). Head torches still bind `UAToggleHeadlight` through `ToggleLightsActionInput` (`actioninput.c:776` to `:782`). A custom car that calls `SetInput("UAToggleHeadlight")` for its lights never fires `ActionSwitchLights`.

LEDs that are not headlights, glow or a real light through `PointLightBase`, are unchanged; see `emissive-leds-and-dynamic-lights.md`.

## The driver seat no longer turns lights off

Measured on 1.30 diag builds with `DIAG_DEVELOPER` prints in a test quad, server and client: `OnDriverEnter` and `OnDriverExit` run on both sides; the `Transport.LightToggle()` that `ActionSwitchLights.OnExecuteServer` calls has changed `LightIsOn()` on the server by the time it returns (off before, on after); and when the driver gets out with the lights on, `LightIsOn()` stays true on server and client. A 1.29 workaround that relights the headlights after the driver leaves finds nothing to fix, and one keyed on `!LightIsOn()` never runs. A second quad mod dropped its own parked beam on this basis and measured the same with an `OnDriverExit` print: lights on and engine on, on server and client, with the beam still lighting the ground beside the parked quad.

## The front lens flare switches off for good

The 1.30 front profile turns its lens flare off once both bulbs have lit together, and never turns it back on. `VehicleLightProfileFront.ApplyAggregatedValues()` writes `m_FlaresVisible = false` on the profile (`vehiclelightprofilebase.c:49` to `:54`); `VehicleLightBase.AggregateLight()` calls it and applies the flag, and `SegregateLight()` applies the stored flag without restoring it or calling `ApplySegregatedValues()` (`vehiclelightbase.c:26` to `:53`). There is one profile per vehicle, kept by its `VehicleLightData` when the light is recreated (`P:\scripts\4_world\entities\vehicles\components\vehiclelightscomponent.c:13` to `:25` and `:83` to `:94`). So after the first two bulb state, a headlight left with one bulb shows no flare for the rest of the vehicle's life, even after switching the lights off and on. 1.29 set the flare on in every `CarLightBase.SegregateLight()` (1.29 `CarLightBase.c:38` to `:46`). No vanilla 1.30 profile overrides either method, so vanilla cars behave the same.

To restore it, keep a `ref` to the front profile and set `m_FlaresVisible = true` in an `UpdateLightsClient` override, before `super`, when `m_HeadlightsState` is `LEFT` or `RIGHT`. Seen in game with that fix: one bulb after two, twice, gave a front crop of the headlights with mean brightness 43.08 and 43.09 and no black pixel, against 14.99 with half the crop black for two bulbs. There was no control run without the fix.

## Profile fields 1.30 never reads

A 1.29 light cannot carry these values over through a profile:

- `m_DaylightVisible` and `m_CastShadow` are only assigned (`vehiclelightprofilebase.c:4`, `:5`, `:36`, `:91` and `:92`), and every `VehicleLightBase` is created with daylight visibility and shadows on (`vehiclelightbase.c:10` to `:19`). A 1.29 rear light that switched both off now shows in daylight and casts shadows, as the vanilla rear lights do.
- `m_FadeInTime` is set by the vanilla profiles and read nowhere.
- `m_FadeOutTime` is read only by the brake and reverse setters (`vehiclelightbase.c:66` and `:81`), with a default of 0.25 s where 1.29's `CarRearLightBase` used 0.1 s (1.29 `CarRearLightBase.c:41` and `:52`). Combined brake and reverse sets a 1 s fade out on both builds (1.29 `CarScript.c:2349` to `:2353`; `vehiclelightscomponent.c:183` to `:185`).
- In 1.29 the method `CarRearLight()` of `CarRearLightBase` (1.29 `CarRearLightBase.c:9`) is not that class's constructor, so the defaults it set never applied. Port the values the 1.29 subclass set itself.

## Battery: NeedElectricitySourceDevice

`Transport` declares the three methods with defaults `true`, `null` and `""` (`P:\scripts\3_game\vehicles\transport.c:821` to `:834`), and `ActionSwitchLights.ActionCondition` reads them (`actionswitchlights.c:38` to `:46`). `Offroad_02` overrides all three (`offroad_02.c:73` to `:88`):

```c
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

A magneto or kickstart bike returns `false` from `NeedElectricitySourceDevice()` (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c:34` to `:37`).

A battery car that does not override the three methods has no battery as far as 1.30 knows, even with one fitted. `CarScript.GetBattery()` casts the `null` the default returns (`carscript.c:2437` to `:2440`), and three things follow:

- `CheckOperationalRequirements` adds `NO_BATTERY` (`carscript.c:1768` to `:1774`), so the engine never starts.
- `OnBeforeLightOn` refuses (`carscript.c:1841` to `:1851`).
- `ActionSwitchLights` never offers itself to the driver (`actionswitchlights.c:38` to `:43`).

The 1.29 way, overriding `IsVitalCarBattery` or `IsVitalTruckBattery`, still compiles and does nothing (`carscript.c:2811` to `:2821`).

## Horn

`CarScript.SetActions()` registers `ActionVehicleHornShort` and `ActionVehicleHornLong` (`carscript.c:2313` to `:2321`). `ActionCarHornShort` and `ActionCarHornLong` are marked `[Obsolete("replaced by ActionVehicleHornShort")]` and `[Obsolete("replaced by ActionVehicleHornLong")]` (`P:\scripts\4_world\classes\useractionscomponent\actions\continuous\vehicles\actioncarhorn.c:69` and `:70`, `:213` and `:214`). The empty aliases `CarHornShortActionInput : VehicleHornShortActionInput {}` and its long twin (`actioninput.c:757` and `:758`, `:773` and `:774`) keep old type names compiling; the logic is on the `VehicleHorn*` parent. Register the sounds on `m_HornComponent` in the constructor, as `offroad_02.c:33` and `P:\scripts\4_world\entities\vehicles\inheritedcars\truck_01_base.c:25` and `:26` do.

## Effect scale and ganged rear bulbs

`GetWeightCoef()` returns 1.0 on `Transport` (`transport.c:475` to `:478`). Vanilla overrides it: `Truck_01_Base` 2.0 (`truck_01_base.c:120` to `:123`), `Offroad_02` 1.5 (`offroad_02.c:133` to `:136`), `Motorbike_01` 0.5 (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:87` to `:90`), `Motorbike_02` 0.75 (`motorbike_02.c:77` to `:80`). `CarScript` feeds it to its effect float modifiers (`carscript.c:720` and `:793`). `MotorbikeScript` has no value of its own and passes `GetWeightCoef()` to its dust and wheel contact effects (`P:\scripts\4_world\entities\vehicles\motorbikescript.c:646` and `:720`).

`HasGangedTailAndBrakeLights()` returns `false` on `CarScript` (`carscript.c:468` to `:471`). When it returns true, the reverse and position material swaps do not turn the brake selection off (`carscript.c:2061` to `:2094`). `Offroad_02` returns true (`offroad_02.c:68` to `:71`). `MotorbikeScript` has its own copy, also `false` (`motorbikescript.c:169` to `:172`), and both vanilla bikes override it to true (`motorbike_01.c:28`; `motorbike_02.c:29`). One later 1.30 build was reported without those two overrides; not checked on `P:\`.
