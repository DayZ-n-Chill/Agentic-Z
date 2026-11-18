# The .ptc layout and the old cloudlet format

How a `.ptc` file is laid out, which emitter shapes vanilla uses, and how the old class based `CfgCloudlets` particles map onto `.ptc`. Every key is in `ptc-format-reference.md`; how to stack emitters into a large effect is in `layered-effects.md`.

## Contents

- [Two particle formats](#two-particle-formats)
- [Emitter shapes](#emitter-shapes)
- [Converting from CfgCloudlets](#converting-from-cfgcloudlets)

## Two particle formats

Current DayZ particles are `.ptc` text files: one `EffectDef` holding `EmitorDef` blocks. The older, class based format lives in config as `CfgCloudlets`, and vanilla still ships such a config (`P:\DZ\data\data\particleeffects\config.cpp:47`). Some older mods carry both. Write new effects as `.ptc`.

Layout rules of a `.ptc`:

- Indentation is spaces, one or two per level.
- There is no `class` keyword and no semicolon. A property is a name and its values separated by spaces.
- A list has no commas: `ShapeSize 0.5 0 0.5` is three numbers.
- Every `EmitorDef` sits inside `EffectDef { Emitors { ... } }`, never directly under `EffectDef`.

The order in which the plane effects of `layered-effects.md` write the properties of an emitter (`ColorMast` and `AlphaMast` are optional):

```text
EffectDef {
 Emitors {
  EmitorDef <named_emitter_1> {
   ShapeType <Point|Box|Ellipse|Cone|Sphere|OnSphere>
   ShapeSize <x> <y> <z>
   ConeAngle <a> <b> <c>
   MaxNum <int>
   BirthRate <float>
   BirthRateRND <float>
   Angles <a> <b> <c>
   Material "{GUID}path/to/material.emat"
   SizeMultiplier <float>
   SizeRND <float>
   RandomRotDir <0|1>
   RotMultiplier <float>
   VelAngle <float>
   RandomAngle <0|1>
   Sort <int>
   Velocity <float>
   VelocityRND <float>
   VelAffect <float>
   Wind <0|1>
   AnimOnce <0|1>
   AnimFPS <int>
   LifetimeByAnim <0|1>
   LifeTime <float>
   LifeTimeRND <float>
   Color { <keyframes...> }
   Alpha { <keyframes...> }
   RotationSpeed { <keyframes...> }
   Size { <keyframes...> }
   EffectTime <float>
   ColorMast { ... }
   AlphaMast { ... }
  }
  EmitorDef <named_emitter_2> { ... }
 }
}
```

## Emitter shapes

Vanilla `.ptc` files use six values for `ShapeType`:

| Value | Vanilla example |
|---|---|
| `Point` | `P:\graphics\particles\blood_surface_drops.ptc:4` |
| `Box` | `P:\graphics\particles\birds_01.ptc:5` |
| `Ellipse` | `P:\graphics\particles\building_destruction_brick.ptc:5` |
| `Cone` | `P:\graphics\particles\contaminated_area_gas_shell.ptc:52` |
| `Sphere` | `P:\graphics\particles\blood_bleeding_01.ptc:4` |
| `OnSphere` | `P:\graphics\particles\fireworks_amazing_anim.ptc:239` |

## Converting from CfgCloudlets

Vanilla still defines class based particles in `CfgCloudlets`, with keys such as `interval`, `cloudletDuration` and `cloudletShape` (`P:\DZ\data\data\particleeffects\config.cpp:47`). The mapping below is not checked on `P:\`:

| Old (`CfgCloudlets`) | New (`.ptc`) |
|---|---|
| `class CloudletShape;` declaration | Implied by `ShapeType` |
| `class MyEffect: CloudletShape { ... }` | `EffectDef { Emitors { EmitorDef name { ... } } }` |
| `interval = 0.01;` | `BirthRate 100` (one divided by the interval) |
| `cloudletDuration = 2;` | `LifeTime 2` |
| `cloudletShape = "..."` | `Material "{GUID}path.emat"` |
| One array per animated attribute | `Color { ... }` and `Alpha { ... }` keyframe blocks |
| Nested `class Color { ... }` | The same data written as keyframes on one line |

A full conversion usually means rewriting the effect; the two structures are too different to translate line by line.

The DayZ 1.30 changes (`ParticleParamsOverrideData` for vehicle dust, the `IsHeadlessOrDedicatedServer` client check) are in `dayz-1-30-particles.md`. They do not change the `EffectDef` and `EmitorDef` syntax.
