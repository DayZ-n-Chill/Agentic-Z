# DayZ 1.30 and aircraft on CarScript

What DayZ 1.30 changed under a plane or helicopter that inherits `CarScript`: the light, battery and event mask code moved, while the native `HelicopterScript` stayed empty.

The 1.30 change notes do not list aircraft as affected; everything here changes because the base class is `CarScript`. Every line was opened on the 1.30 scripts on `P:\`. The ground vehicle side of the same update is in `dayz-1-30-vehicles.md`.

## The native helicopter class is still empty

`HelicopterScript extends HelicopterAuto` registers only `POSTSIMULATE`, and its `EOnPostSimulate` and engine hooks are empty. From `P:\scripts\4_world\entities\vehicles\helicopterscript.c:4` to `:13`:

```c
class HelicopterScript extends HelicopterAuto
{
	void HelicopterScript()
	{
		SetEventMask(EntityEvent.POSTSIMULATE);
	}

	override void EOnPostSimulate(IEntity other, float timeSlice)
	{
	}
```

Do not move a flying `CarScript` aircraft onto it expecting a flight model. `helicopters.md` has the two bases side by side.

## Lines a 1.29 mod still cites

A mod written for 1.29 carries line numbers that no longer match. Where they point now:

| What | 1.29 line | 1.30 line |
|---|---|---|
| `SetEventMask` calls in the `CarScript` constructor | `carscript.c:325` and `:326` | `P:\scripts\4_world\entities\vehicles\carscript.c:207` and `:208` |
| `EOnPostSimulate` | `carscript.c:948` | `carscript.c:807` |
| `OnDriverExit` and its gear check | `carscript.c:1207` to `:1215` | `carscript.c:940` to `:948` |
| Empty `OnDriverExit` in `Transport` | `transport.c:161` | `P:\scripts\3_game\vehicles\transport.c:224` |

## Lights and battery

An aircraft that still overrides `CreateFrontLight` or subclasses `CarLightBase` compiles, but against an obsolete method that vanilla no longer calls on that path: `CreateFrontLight` carries `[Obsolete("1.30: use VehicleLightsComponent instead")]` (`P:\scripts\4_world\entities\vehicles\carscript.c:2944` and `:2945`). Vanilla cars register light profiles with `m_LightsComponent.RegisterLight` instead. From `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:21` and `:22`:

```c
		m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Offroad_02LightProfileFront()));
		m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new Offroad_02LightProfileRear()));
```

- `ForceUpdateLightsStart` and `ForceUpdateLightsEnd` are `[Obsolete("1.30: no replacement")]` (`carscript.c:2805` to `:2809`). Delete those calls from any parked beam code.
- `NeedElectricitySourceDevice()` (`P:\scripts\3_game\vehicles\transport.c:821`) replaces `IsVitalCarBattery`, now `[Obsolete("1.30: use Transport.NeedElectricitySourceDevice")]` (`carscript.c:2811` and `:2812`). An aircraft with a magneto can return `false`, as the vanilla motorbike does (`P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c:34` to `:37`).
- The vehicle light toggle input is `UAToggleVehicleLights`, set by `ToggleVehicleLightsActionInput` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849` to `:855`). `UAToggleHeadlight` is the head torch. Custom flight `UA*` inputs are unaffected.
- The LM_Planes headlight, a `CarLightBase` child such as `LM_TigermothFrontLight` (`aviation-effects-and-lights.md`), is the older pattern. Keep it in a mod that already ships it; write new work as a `VehicleLightProfileBase` child with a `VehicleLightBase`.

## Wreck scripts with no model

`StaticObj_Wreck_Chinook` (`P:\scripts\4_world\entities\building\wrecks\wreck_chinook.c:1`) and `StaticObj_Wreck_Mi24_TK` (`P:\scripts\4_world\entities\building\wrecks\wreck_mi24_tk.c:1`) exist in script and play `ParticleList.SMOKING_HELI_WRECK` when not on a dedicated server. No config class and no `.p3d` of either name is under `P:\DZ\`: a search for `chinook` and `mi24` file names, and for both class names in every `config.cpp`, finds none. Whether a later build ships them is unverified, so do not make a config depend on them as placeable wrecks.

## Moving an aircraft to 1.30

1. Check every `carscript.c` and `transport.c` line number the mod or its notes cite against `P:\`.
2. Replace `CreateFrontLight` and `CreateRearLight` with `m_LightsComponent.RegisterLight` and a `VehicleLightProfileBase` child.
3. Delete `ForceUpdateLightsStart` and `ForceUpdateLightsEnd`.
4. Override `NeedElectricitySourceDevice`, and the getters beside it, instead of `IsVitalCarBattery`.
5. Bind the cockpit light toggle to `UAToggleVehicleLights` if it should use the vanilla light action.
6. Keep the custom `UA*` flight axes.
7. Do not switch the base class to `HelicopterScript`.
