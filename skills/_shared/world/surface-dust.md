# Surface dust

Where a world's dust effects come from: dust falling from ceilings, ambient ground and cloud dust driven by wind, kickup dust, and dust behind vehicles scaled by their weight. The `SurfaceInfo` particle getters and the `ParticleList` constants are in `dayz-particles/references/dayz-1-30-particles.md`; writing `.ptc` and `.emat` files is `/dayz-particles`.

## The surface decides

Every dust effect reads the `SurfaceInfo` of the ground under it. A custom `CfgSurfaces` class that should raise kickup, wheel or ceiling dust fills those config entries, or the getters return `ParticleList.NONE` (`P:\scripts\3_game\surfaceinfo.c:47`). Surface thickness is `GetThickness()` (`surfaceinfo.c:31`).

In new code call `SurfaceInfo.GetByName(...).GetStepParticleId()` and pass a `SurfaceInfo` to `SelectFromSurface`. `Surface.GetStepsParticleID` and `EffWheelSmoke.SetSurface` are obsolete (`P:\scripts\4_world\static\surface.c:64` and `:65`; `P:\scripts\4_world\entities\effects\wheelsmoke.c:32` and `:33`; the replacement is at `wheelsmoke.c:5`), and a mod that still calls them gets the obsolete warning.

## Dust from ceilings

`DustEffectCeilingHandlerBase.OnStepUpdate` (`P:\scripts\4_world\classes\dust\dusteffectceilinghandler.c:25` to `:41`) runs when the surface's `GetCeilingDustParticleId()` is above 0. It counts steps and, every 4 to 8 steps by default (`RANGE_MIN_DEFAULT`, `RANGE_MAX_DEFAULT`, `dusteffectceilinghandler.c:3` and `:4`), lowers the position by `GetThickness()` and spawns the effect. A thickness of -1 means "not defined" and falls back to 0.4 m (`FLOOR_THICKNESS_DEFAULT`, `:5`, `:66` to `:72`).

| Variant | Call | Source |
|---|---|---|
| Local | `SEffectManager.PlayInWorld` | `dusteffectceilinghandler.c:79` to `:88` |
| Synced | `SEffectManager.CreateParticleServer` with `ParticleEffecterParameters("CeilingDustEffecter", ...)` | `:95` to `:99` |

## Ground, cloud and kickup dust

`DustEffectManager` reads `GetWorldData().GetDustEffectsSettings()` (`P:\scripts\4_world\classes\dust\dusteffectsmanager.c:81`; the getter is at `P:\scripts\3_game\worlddata.c:548`). Nasdara turns both effects on in `SetupDustEffects` (`P:\scripts\4_world\classes\worlds\nasdara.c:152` to `:169`): ground dust from wind strength 8 at distance 30, cloud dust from wind strength 5 at distance 16. A custom world that wants them fills the same settings in its own world data class.

Kickup dust is `DustKickupEffects`, with the sound set `KickupDustEffect_SoundSet` (`P:\scripts\3_game\dustkickupeffects.c:43` to `:45`).

## Dust behind vehicles

- `VehicleVFXComponent.PlayEffectData` finds the ground with `g_Game.GetSurface` and passes its `SurfaceInfo` on (`P:\scripts\4_world\entities\vehicles\components\vehiclevfxcomponent.c:177` to `:186`).
- `EffVehicleDust.SelectFromSurface` uses `GetVehicleDustParticleId()` (`P:\scripts\4_world\entities\effects\vehicledust.c:25` to `:35`). Its `ParticleParamsOverride` scales `LIFETIME`, `VELOCITY`, `SIZE` and `AIR_RESISTANCE` by speed and a weight coefficient (`vehicledust.c:5` to `:23`).
- `EffWheelContact.SelectFromSurface` uses `GetWheelContactParticleId` and `GetWheelContactSoundSetName` (`P:\scripts\4_world\entities\effects\effwheelcontact.c:25` to `:28`).

The weight coefficient comes from `GetWeightCoef()`:

| Class | Value | Source (class, then `GetWeightCoef`) |
|---|---|---|
| `Transport` (default) | 1.0 | `P:\scripts\3_game\vehicles\transport.c:68`, `:475` |
| `Offroad_02` | 1.5 | `P:\scripts\4_world\entities\vehicles\inheritedcars\offroad_02.c:1`, `:133` |
| `Truck_01_Base` | 2.0 | `P:\scripts\4_world\entities\vehicles\inheritedcars\truck_01_base.c:1`, `:120` |
| `Motorbike_01_ColorBase` | 0.5 | `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_01.c:1`, `:87` |
| `Motorbike_02_ColorBase` | 0.75 | `P:\scripts\4_world\entities\vehicles\inheritedmotorbikes\motorbike_02.c:1`, `:77` |

No vanilla motorbike uses 0.25. A custom vehicle overrides `GetWeightCoef` to scale its own dust; the vehicle class itself belongs to the vehicles pack (`_shared/vehicles/`).
