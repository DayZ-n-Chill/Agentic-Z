# Layered effects

How a large effect (an explosion, an impact, a fireball) is built from several emitters, which properties matter when you layer them, and how the `Mast` curves shape the whole effect over time. The `.ptc` layout and the old `CfgCloudlets` format are in `ptc-layout-and-cloudlets.md`; registering, playing and switching emitters from script is in `effects-from-script.md`. Every property is listed in `ptc-format-reference.md`.

The worked examples are three effects of a plane mod, `PLANES_EX`, `PLANES_IMPACT` and `PLANES_BOOM`. They are the mod's own effects, so what this file says about them is read from the mod and not checked on `P:\`; every fact about vanilla cites its file.

## Contents

- [Layering emitters](#layering-emitters)
- [Materials to reuse](#materials-to-reuse)
- [Properties that matter when layering](#properties-that-matter-when-layering)
- [Curves over a particle's life](#curves-over-a-particles-life)
- [Mast curves: an envelope over the whole effect](#mast-curves-an-envelope-over-the-whole-effect)
- [Useful tricks](#useful-tricks)
- [Mistakes to avoid](#mistakes-to-avoid)

## Layering emitters

A real effect stacks emitters with different timing, size and material. Keep each emitter small and give it one job (the first flash, flying debris, lingering smoke, sparks); different `LifeTime` values per layer make the effect unfold in stages.

| Effect | Emitters | How it is built |
|---|---|---|
| `PLANES_EX`, a bomb explosion | 4 | `short`: a short smoke burst (`Box`, `smoke_anim_02`, `LifeTime 0.5`). `short_spark`: quick sparks (`Box`, `sparks_05`, `LifeTime 0.1`, `AnimOnce 1`). `long_light`: lingering light smoke (`Ellipse`, `smoke_anim_02`, a half sphere cone of `90 -90 90`). `long_dark`: lingering dark smoke (`Ellipse`, larger and slower to fade). |
| `PLANES_IMPACT`, a ground impact | 12 | Three clusters named by emitter prefix: `explo_fire` (3), `explo_dust` (7, among them small and large rings and emitters aimed up and aimed the opposite way) and `explo_debris` with sparks (3). |
| `PLANES_BOOM`, an aircraft fireball | 7 | `fire_anim_small`, `fire_anim_root`, `fire_anim`, `fire_anim_Rot`, `red_smoke`, `red_smoke_large` and `sparks`. It leans on `Mast` curves for its movement. |

## Materials to reuse

You rarely need your own `.emat`. These vanilla materials cover most explosion, impact and smoke work. Each exists under `P:\graphics\particles\materials\`, and the GUID is the one vanilla `.ptc` files write most often for it. The last column says how the plane effects use it.

| GUID | Path under `Graphics/Particles/materials/` | Use |
|---|---|---|
| `{00BEA27443975BEB}` | `smoke/smoke_anim_02.emat` | General smoke, short and long trails |
| `{ADDEE13E78378825}` | `smoke/smoke_cloud_01_b_trans_landmine_01.emat` | Dust cloud of an impact (the dust ring of `PLANES_IMPACT`) |
| `{5784934A1C87961A}` | `smoke/smoke_cloud_01_g_heliwreck_01.emat` | Dark red smoke (the fireball of `PLANES_BOOM`) |
| `{67FEB95AE2ECC2EA}` | `smoke/smoke_dust_01.emat` | General dust |
| `{391690195D614CE5}` | `smoke/smoke_dust_02.emat` | Dust, second look |
| `{84C6C29E227A50FB}` | `smoke/smoke_dust_04.emat` | Dust, fourth look |
| `{70CE85062FA7388F}` | `smoke/smoke_dust_05.emat` | Dust, fifth look |
| `{2E26AC45902AB680}` | `smoke/smoke_dust_06.emat` | Dust, sixth look |
| `{214D9C1A37B3A94A}` | `smoke/smoke_debris_01.emat` | Flying debris chunks |
| `{62F13B8B540EBC80}` | `fire/fireball_1.emat` | Animated fireball |
| `{83BCB6516091DB01}` | `fire/fire_medium_camp_04.emat` | Slower, campfire style fire (the root of the `PLANES_BOOM` fire) |
| `{FF2A8A73FB791A62}` | `fire/sparks_05.emat` | Quick spark |
| `{009C2EBAACD2D72A}` | `fire/sparks1.emat` | General sparks |
| `{0B22CDEBF6A47216}` | `fire/sparks_04.emat` | Sparks, fourth look (debris sparks of `PLANES_IMPACT`) |
| `{D17539339C9F6B0B}` | `weapons/weapon_shot_fnx_02.emat` | Pistol muzzle flash, used as the first fire of an impact |
| `{257D7EAB9142037F}` | `weapons/weapon_shot_fnx_03.emat` | Pistol muzzle flash, second look |

A `Material` line is the GUID in braces followed by the path:

```text
Material "{00BEA27443975BEB}Graphics/Particles/materials/smoke/smoke_anim_02.emat"
```

The path is what makes the reference resolve, not the GUID. Vanilla writes `smoke_anim_02.emat` with two different GUIDs, `{00BEA27443975BEB}` in the bonfire (`P:\graphics\particles\fire_bonfire.ptc:217`) and `{0BEA27443975BE0B}` in the failing hatchback engine (`P:\graphics\particles\hatchback_engine_failing.ptc:11`), and both effects play. Copy the GUID from a vanilla `.ptc` that uses the material, and get the path right.

## Properties that matter when layering

What the plane effects do is read from the mod; vanilla lines are cited.

| Property | What it does when layering |
|---|---|
| `ShapeType`, `ShapeSize <x> <y> <z>` | The volume particles are born in and its size (`ptc-layout-and-cloudlets.md`, "Emitter shapes"). |
| `ConeAngle <a> <b> <c>` | The opening angles of the emission cone. |
| `Offset <x> <y> <z>` | Moves the spawn point off the owner's position; a negative Y lowers it. |
| `CenterX`, `CenterY` | The pivot of the sprite, from 0 to 1 in the plane effects. |
| `MaxNum` | The most particles alive at once. In the plane effects an emitter that reaches it stops emitting, so keep below it. |
| `BirthRate`, `BirthRateRND` | Particles per second and a random spread. |
| `BirthRateVel` | Ties the birth rate to the owner's speed, for a trail behind a moving object. It is a number, not a switch: vanilla blood uses `BirthRateVel 100` (`P:\graphics\particles\blood_bleeding_01.ptc:8`). |
| `LifeTime`, `LifeTimeRND` | Seconds a particle lives, and a random spread. |
| `EffectTime` | How long the emitter runs before it stops spawning. |
| `LifetimeByAnim` | With 1, a particle dies when its sprite animation ends. |
| `AnimFPS`, `AnimOnce` | Playback speed of the sprite sheet; `AnimOnce 1` plays it once, 0 loops it. For a material with one frame write `AnimFPS 999` with `AnimOnce 1`, as the vanilla oil fire does (`P:\graphics\particles\fire_oil1.ptc:131`). |
| `RandomFrame` | 1 starts each particle on a random frame, so particles of one emitter do not look alike. |
| `Velocity`, `VelocityRND` | Starting speed and its random spread. |
| `VelAffect` | How much of the owner's velocity the particle takes over, from 0 (none) to 1 (all). |
| `VelAngle`, `RandomAngle`, `RandomRotDir`, `RotMultiplier` | Starting direction and rotation. |
| `Wind` | Whether wind moves the particle. |
| `AirResistance`, `AirResistanceRND` | Drag; the plane effects use about `0.05`. |
| `GravityMultiply` | How strongly gravity pulls. A negative value makes smoke rise: the plane effects use `-0.05`, and vanilla birds use `GravityMultiply -0.1` (`P:\graphics\particles\birds_01.ptc:25`). |
| `Sort` | Render order; in the plane effects a higher number draws later, on top. |

## Curves over a particle's life

`Color`, `Alpha`, `Size` and `RotationSpeed` are keyframe lists read over the life of each particle, from 0 (birth) to 1 (death).

```text
Alpha {
 0 0 0.31101 0.24684 1 0
}
```

Alpha 0 at birth, 0.24684 at 31 % of the life, 0 at death: the particle fades in and then out.

A `Color` keyframe is four numbers, the time then red, green and blue. White at birth and a warm white at death:

```text
Color {
 0 1 1 1   1 0.9187 0.8938 0.8813
}
```

A long curve puts one keyframe on each line:

```text
Color {
 0 0.8353 0.3133 0.008
 0.2115 0.1647 0.008 0.008
 0.2159 0 0 0
 0.2925 0.0201 0.0201 0.0201
}
```

## Mast curves: an envelope over the whole effect

A curve whose name ends in `Mast` lies over the base curve and runs over the time of the effect, not the life of one particle. The base curve sets the normal behaviour and the `Mast` curve adds the envelope.

| Curve | Changes |
|---|---|
| `AlphaMast` | alpha, as a multiplier |
| `SizeMast` | size |
| `RotationSpeedMast` | rotation |
| `BRateMast` | birth rate, so the spawn rate rises and falls |
| `VelocityMast` | speed |
| `AirResistanceMast` | drag |

Uses in the plane effects: smoke that pulses (`AlphaMast`), an explosion whose spawn rate ramps up and down (`BRateMast`), and debris that starts fast and slows (`VelocityMast`).

## Useful tricks

| Trick | What it gives |
|---|---|
| `GravityMultiply -0.05` | Smoke that rises |
| `AnimFPS 999` with `AnimOnce 1` | A one frame material with no frame stepping |
| `RandomFrame 1` | Each particle of an emitter starts on a different frame |
| `ConeAngle 90 -90 90` | Emission over a half sphere, an expanding shell; vanilla uses it for coolant steam (`P:\graphics\particles\hatchback_coolant_overheated.ptc:42`) |
| `ShapeType Ellipse` with a `ConeAngle` | A sphere or dome shaped shell |
| `Offset 0 -0.83 0` | A lower spawn point, so an explosion sits partly in the ground |
| `BirthRateVel` above 0 | A birth rate that grows with the owner's speed, for trails |
| One material on several emitters | Different `LifeTime`, size and `Velocity` give different layers at no extra texture cost |

## Mistakes to avoid

- Writing your own `.emat` when a vanilla material with its GUID would do. A custom `.emat` does not need Workbench to make a GUID: a mod's own material resolves by path alone (`SKILL.md`, "GUID references").
- Giving a one frame material a low `AnimFPS`. Use `AnimFPS 999` with `AnimOnce 1`.
- Leaving out `RandomFrame` on a group of similar particles. Without it they all show the same frame at the same time and look artificial.
- Putting an `EmitorDef` at the wrong level. It belongs inside `EffectDef { Emitors { ... } }`.

The plane context of these three effects belongs to the aircraft files of the vehicles pack (`_shared/vehicles/README.md`, "Aircraft in depth").
