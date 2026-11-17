# DayZ 1.30 changes for aircraft on CarScript

What DayZ 1.30 changed underneath a plane or helicopter that inherits `CarScript`: the vehicle light, horn, battery and event mask contract moved, while the native `HelicopterScript` stayed empty. Every line below was opened on `P:\`, which holds the 1.30 scripts; line numbers a 1.29 mod or note carries are given beside them.

The 1.30 change notes do not list aviation as affected. This file is what still changes for an aircraft because its base class is `CarScript`.

## The native helicopter class is still empty

True up to 1.29 and since 1.30. `HelicopterScript extends HelicopterAuto` (`P:\scripts\4_world\entities\vehicles\helicopterscript.c:4`) registers only `POSTSIMULATE` and has an empty `EOnPostSimulate` plus empty engine hooks:

```c
// P:\scripts\4_world\entities\vehicles\helicopterscript.c, lines 4 to 13
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

Do not move a flying `CarScript` child onto it expecting a flight model. `skills/_shared/vehicles/helicopters.md` has the two bases side by side.

## Line drift in CarScript and Transport

| What | 1.29 line | 1.30 line on `P:\` |
|---|---|---|
| `SetEventMask` calls in the `CarScript` constructor | `carscript.c:325-326` | `P:\scripts\4_world\entities\vehicles\carscript.c:207-208` |
| `EOnPostSimulate` | `carscript.c:948` | `P:\scripts\4_world\entities\vehicles\carscript.c:807` |
| `OnDriverExit` and its gear check | `carscript.c:1207-1215` | `P:\scripts\4_world\entities\vehicles\carscript.c:940-948` |
| Empty `OnDriverExit` in `Transport` | `transport.c:161` | `P:\scripts\3_game\vehicles\transport.c:224` |

```c
// P:\scripts\4_world\entities\vehicles\carscript.c, lines 207 to 208
		SetEventMask(EntityEvent.POSTSIMULATE);
		SetEventMask(EntityEvent.POSTFRAME);
```

## Lights, battery and ForceUpdateLights

A `CarScript` aircraft that still overrides `CreateFrontLight` or subclasses `CarLightBase` compiles against an obsolete method (`CreateFrontLight` is at `P:\scripts\4_world\entities\vehicles\carscript.c:2945`, under an `[Obsolete("1.30: use VehicleLightsComponent instead")]` attribute), but the override is no longer the path vanilla uses. Vanilla cars register light profiles:

```c
// P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c, lines 21 to 22
		m_LightsComponent.RegisterLight("Front", new VehicleLightData(new Offroad_02LightProfileFront()));
		m_LightsComponent.RegisterLight("Rear", new VehicleLightData(new Offroad_02LightProfileRear()));
```

- `ForceUpdateLightsStart` and `ForceUpdateLightsEnd` are `[Obsolete("1.30: no replacement")]` (`P:\scripts\4_world\entities\vehicles\carscript.c:2805-2809`). A parked beam recipe that copies those two calls is a 1.29 pattern; delete the calls on 1.30.
- Electricity: `NeedElectricitySourceDevice()` (`P:\scripts\3_game\vehicles\transport.c:821`) replaces `IsVitalCarBattery`, which is now `[Obsolete("1.30: use Transport.NeedElectricitySourceDevice")]` (`P:\scripts\4_world\entities\vehicles\carscript.c:2811-2812`). An aircraft with a magneto can return `false`, as the vanilla motorbike does: `NeedElectricitySourceDevice` in `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c:34-37`.
- The vehicle light toggle input is `UAToggleVehicleLights`, set by `ToggleVehicleLightsActionInput` (`P:\scripts\4_world\classes\useractionscomponent\actioninput.c:849-855`). `UAToggleHeadlight` is the head torch. Custom flight `UA*` bindings are unchanged.
- An LM_Planes style `class LM_TigermothFrontLight extends CarLightBase` (`effects-and-lights.md`) is the 1.29 community pattern. Keep it for existing mods; new 1.30 work uses a `VehicleLightProfileBase` child with `VehicleLightBase`.

## Wreck scripts without models

`StaticObj_Wreck_Chinook` (`P:\scripts\4_world\entities\building\wrecks\wreck_chinook.c:1`) and `StaticObj_Wreck_Mi24_TK` (`P:\scripts\4_world\entities\building\wrecks\wreck_mi24_tk.c:1`) exist in the scripts and play `ParticleList.SMOKING_HELI_WRECK` when not on a dedicated server. No config class and no `.p3d` with either name is on `P:\DZ\` (checked by searching `P:\DZ\` for `chinook` and `mi24` file names and for the two class names in every `config.cpp`). Whether a later build ships them is unverified, so do not make a config depend on those class names as placeable wrecks until a model exists.

## Migration checklist for a CarScript aircraft

1. Check every `carscript.c` and `transport.c` line number the mod or its notes cite against `P:\`.
2. Replace `CreateFrontLight` and `CreateRearLight` with `m_LightsComponent.RegisterLight` plus a `VehicleLightProfileBase` child.
3. Delete `ForceUpdateLightsStart` and `ForceUpdateLightsEnd`.
4. Override `NeedElectricitySourceDevice` (and the getters beside it) instead of `IsVitalCarBattery`.
5. Bind the cockpit light toggle to `UAToggleVehicleLights` if it should use the vanilla light action.
6. Keep the custom `UA*` flight axes; they are independent of the vehicle light rename.
7. Do not switch the entity base to `HelicopterScript`.

The ground vehicle side of the same migration is in the vehicle pack (`skills/_shared/vehicles/README.md`).
