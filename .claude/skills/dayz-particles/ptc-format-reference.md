# .ptc File Format Reference — Complete Property Catalog

Verified from 9 vanilla particle files. Properties are per-emitter unless noted.
All values are space-separated. Curves use keyframe pairs: `time value [time value ...]`.

---

## STRUCTURE

```
EffectDef {
 MinFPS 30                           ← optional, EffectDef-level
 Emitors {
  EmitorDef <emitter_name> {
   <property> <value(s)>
   Color { <keyframes> }             ← curve block
  }
  EmitorDef <emitter_name_2> { ... } ← multiple emitters supported
 }
}
```

---

## COMPLETE PROPERTY TABLE

### Shape & Emission

| Property | Type | Default | Description |
|---|---|---|---|
| `ShapeType` | string | Point | Emission shape: `Point`, `Box`, `Ellipse` |
| `ShapeSize` | vec3 | 0 0 0 | Dimensions of emission shape (x y z meters) |
| `ConeAngle` | vec3 | 0 0 0 | Emission cone spread (yaw pitch roll degrees) |
| `MaxNum` | int | — | Maximum simultaneous alive particles |
| `BirthRate` | float | — | Particles emitted per second |
| `BirthRateRND` | float | 0 | Random variance on BirthRate |
| `BirthRateVel` | float | 0 | Birth rate multiplied by velocity |
| `Offset` | vec3 | 0 0 0 | Local position offset from parent (x y z) |
| `Angles` | vec3 | 0 0 0 | Initial emission rotation (pitch yaw roll) |

### Visual

| Property | Type | Default | Description |
|---|---|---|---|
| `Material` | string | — | GUID+path to .emat: `"{GUID}path.emat"` |
| `SizeMultiplier` | float | 1 | Base scale of particle billboard |
| `SizeRND` | float | 0 | Random size variance |
| `BillboardingType` | string | (engine default) | `Full` = always face camera |
| `CenterX` | float | 0 | Horizontal pivot offset |
| `CenterY` | float | 0 | Vertical pivot (-1=bottom, 0=center, 1=top) |
| `ScaleX` | float | 1 | Non-uniform X scale |
| `ScaleY` | float | 1 | Non-uniform Y scale |
| `StretchMultiplier` | float | 0 | Velocity-based stretching (0=none, 1=full) |
| `StreakFullUV` | int | 0 | Stretch UV along streak (0/1) |
| `Sort` | string/int | 0 | Render order: `0`, `translucent`, `overlay` |
| `LOD` | int | 0 | Level of detail threshold |

### Motion

| Property | Type | Default | Description |
|---|---|---|---|
| `Velocity` | float | 0 | Initial speed (negative=toward parent) |
| `VelocityRND` | float | 0 | Random velocity variance |
| `VelAngle` | int | 0 | Align rotation to velocity direction (0/1) |
| `VelAffect` | float | 0 | Velocity influence on direction (0-1) |
| `AirResistance` | float | 0 | Drag (higher=slower for smoke) |
| `AirResistanceRND` | float | 0 | Random air resistance variance |
| `GravityMultiply` | float | 0 | Gravity influence (0=float, 1=earth gravity) |
| `GravityMultiplyRND` | float | 0 | Random gravity variance |
| `Wind` | float | 0 | Wind influence (0=ignore, 1=full) |
| `Spring` | float | 0 | Spring-back force toward origin |
| `Restitution` | float | 0 | Bounce factor on collision |
| `RandomAngle` | int | 0 | Start at random angle (0/1) |

### Lifetime

| Property | Type | Default | Description |
|---|---|---|---|
| `LifeTime` | float | — | Base lifetime in seconds |
| `LifeTimeRND` | float | 0 | Random lifetime variance |
| `LifetimeShortening` | float | 0 | Reduce lifetime over effect time |
| `EffectTime` | float | — | Total effect cycle duration (master curves use this) |
| `Repeat` | int | 0 | **0=one-shot** (auto-deletes), **1=loop** (MUST stop manually!) |

### Animation

| Property | Type | Default | Description |
|---|---|---|---|
| `AnimOnce` | int | 0 | Play sprite animation once (0/1) |
| `AnimFPS` | float | 0 | Sprite animation framerate |
| `LifetimeByAnim` | int | 0 | Tie lifetime to animation length (0/1) |
| `RandomFrame` | int | 0 | Start at random frame (0/1) |

### Rotation

| Property | Type | Default | Description |
|---|---|---|---|
| `RandomRotDir` | int | 0 | Randomize rotation direction (0/1) |
| `RotMultiplier` | float | 0 | Rotation speed multiplier (degrees/sec) |

### Curves (per-particle lifetime: 0.0 = birth, 1.0 = death)

| Curve | Format | Description |
|---|---|---|
| `Color` | `{ t R G B [t R G B ...] }` | Color over lifetime (RGB 0-1) |
| `Alpha` | `{ t A [t A ...] }` | Opacity over lifetime (0-1) |
| `Size` | `{ t S [t S ...] }` | Scale over lifetime (multiplied by SizeMultiplier) |
| `RotationSpeed` | `{ t S [t S ...] }` | Rotation speed over lifetime |

### Master Curves (over EffectTime, modulate ALL emitters)

| Curve | Format | Description |
|---|---|---|
| `ColorMast` | `{ t R G B }` | Master color modulation |
| `AlphaMast` | `{ t A }` | Master alpha modulation |
| `SizeMast` | `{ t S }` | Master size modulation |
| `BRateMast` | `{ t R }` | Master birth rate modulation |
| `VelocityMast` | `{ t V }` | Master velocity modulation |
| `AirResistanceMast` | `{ t A }` | Master air resistance modulation |
| `RotationSpeedMast` | `{ t S }` | Master rotation speed modulation |

### EffectDef-level Properties

| Property | Type | Description |
|---|---|---|
| `MinFPS` | int | Minimum FPS threshold for particle quality |

---

## VANILLA EXAMPLES (annotated)

### Simplest: debug_dot.ptc (1 emitter, 478 bytes)

```
EffectDef {
 Emitors {
  EmitorDef power {
   ConeAngle 0 0 0             ← no spread, single direction
   MaxNum 1                     ← only 1 particle at a time
   BirthRate 1                  ← 1 per second
   Offset 0 0.04 0             ← slightly above origin
   Material "{CB7AF4FD8ACBFDFC}Graphics/Particles/materials/glow/glow1.emat"
   CenterY 0
   ScaleX 1
   SizeMultiplier 0.1           ← tiny dot
   StretchMultiplier 0
   VelAngle 0
   BillboardingType Full        ← always faces camera
   Velocity 0                   ← stationary
   VelocityRND 0
   AirResistance 0
   LifeTime 15                  ← lives 15 seconds
   LifeTimeRND 0
   Color {
    0 1 0 0 1 1 0 0             ← red at birth, red at death
   }
   Alpha {
    0 1 1 0                     ← fully visible, fades at end
   }
   EffectTime 0.5
   Repeat 0                     ← one-shot, auto-deletes
  }
 }
}
```

### Electric sparks: electro_shortc2.ptc (1 emitter, 1078 bytes)

```
EffectDef {
 Emitors {
  EmitorDef sparksrandom2 {
   ShapeType Ellipse             ← emit from ellipse surface
   ShapeSize 1 0 1               ← 1m radius disk
   ConeAngle 360 45 0            ← hemisphere spread
   MaxNum 300                    ← many simultaneous sparks
   BirthRate 0                   ← no steady birth...
   BirthRateRND 10               ← ...but random bursts up to 10/s
   Velocity 5                    ← fast initial speed
   VelocityRND 0.312
   AirResistance 1               ← quick slowdown
   GravityMultiply 1             ← affected by gravity (fall)
   GravityMultiplyRND 0.5
   Material "{009C2EBAACD2D72A}Graphics/Particles/materials/fire/sparks1.emat"
   SizeMultiplier 0.05           ← tiny sparks
   StretchMultiplier 1.01        ← stretch along velocity
   VelAngle 1                    ← align to velocity
   LifeTime 0.5
   LifeTimeRND 0.5               ← 0-1 second lifetime
   Color {                       ← yellow→orange→dark
    0 1 0.96 0.4 0.52 0.81 0.32 0.2 1 0 0 0
   }
   Alpha {
    0 1 0.65 0.76 1 0            ← bright start, fade out
   }
   Size {
    0 1 1 1                      ← constant size
   }
   EffectTime 0.5
   Repeat 0                      ← ONE-SHOT: auto-deletes
  }
 }
}
```

### Generator smoke: smoke_small_generator_01.ptc (1 emitter, 663 bytes)

```
EffectDef {
 Emitors {
  EmitorDef emitor1 {
   ShapeType Box
   ShapeSize 0.3 0 0.3           ← small emission area
   MaxNum 40
   BirthRate 20
   BirthRateRND 2
   Angles 0 0 75                 ← angled emission
   Material "{008E25684854DAB8}Graphics/Particles/materials/smoke/steam_small_cook_01.emat"
   SizeMultiplier 3              ← large smoke puffs
   RandomRotDir 1
   RotMultiplier 45              ← spinning smoke
   Velocity 3                    ← upward speed
   VelocityRND 0.5
   Wind 1                        ← affected by wind
   AnimFPS 30
   LifeTime 1
   LifeTimeRND 1                 ← 0-2 second lifetime
   Color {                       ← dark gray smoke
    0 0.24 0.24 0.24 1 0.07 0.06 0.05
   }
   Alpha {
    0 0 0.09 0.22 1 0            ← fade in, fade out
   }
   RotationSpeed {
    0 0 1 1                      ← accelerating rotation
   }
   Size {
    0 0.12 1 1                   ← grows over lifetime
   }
  }
 }
}
```

### Water jet difference: water_jet vs water_jet_weak

Only two properties change between the strong and weak variants:
- `SizeMultiplier`: 1.0 → 0.3
- `SizeRND`: 0.5 → 0.15

Everything else (MaxNum, BirthRate, Velocity, Color, Alpha) is identical.
This demonstrates that creating variants is trivial — clone and tweak.

### Complex fire: fire_small_camp_01.ptc (6 emitters, 4357 bytes)

Emitter roles:
1. `glows` — soft glow halo (glow1.emat, Repeat 1)
2. `fire_middle` — main animated flame (fire_medium_camp_02.emat, Repeat 1)
3. `fire_middle_burst` — occasional burst flame (fire_medium_camp_04.emat, Repeat 1)
4. `fire_middle_short` — short-lived flame particles (fire_flame_01.emat)
5. `sparks_small` — small flying sparks (sparks1.emat)
6. `smoke_middle` — rising smoke column (smoke_anim_02.emat)

Key insight: complex effects are built by layering simple emitters.
Each emitter handles one visual aspect independently.
