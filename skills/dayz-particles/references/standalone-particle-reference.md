# Layered effects, modulation curves and the old cloudlet format

How a large effect (explosion, impact, fireball) is built from several emitters, how the `Mast` curves shape it over time, how script turns single emitters on and off, and how the old class based `CfgCloudlets` particles map onto `.ptc`. The multi emitter examples come from a third-party mod, LM_Planes (Steam Workshop item 3730564764, three `.ptc` files: `PLANES_EX`, `PLANES_IMPACT`, `PLANES_BOOM`). Facts about that mod are not checked on `P:\`; every fact about vanilla cites its file.

The property tables for `.ptc` and `.emat` are in `ptc-format-reference.md` and `emat-format-reference.md`; this file only adds what they do not cover.

## Contents

- [Two particle formats](#two-particle-formats)
- [Emitter shapes](#emitter-shapes)
- [Materials to reuse](#materials-to-reuse)
- [Emitter properties worth knowing](#emitter-properties-worth-knowing)
- [Curves over a particle's life](#curves-over-a-particles-life)
- [Mast curves: an envelope over the whole effect](#mast-curves-an-envelope-over-the-whole-effect)
- [Layering emitters](#layering-emitters)
- [Useful tricks](#useful-tricks)
- [Registering the effects](#registering-the-effects)
- [Playing them from script](#playing-them-from-script)
- [Turning single emitters on and off](#turning-single-emitters-on-and-off)
- [Mistakes to avoid](#mistakes-to-avoid)
- [Converting from CfgCloudlets](#converting-from-cfgcloudlets)
- [DayZ 1.30](#dayz-130)
- [Related skills](#related-skills)

---

## Two particle formats

Current DayZ particles are `.ptc` text files: one `EffectDef` holding `EmitorDef` blocks. The older, class based format lives in config as `CfgCloudlets`, and vanilla still ships such a config (`P:\DZ\data\data\particleeffects\config.cpp:47`). Some older mods carry both. Write new effects as `.ptc`.

Layout rules of a `.ptc`:

- Indentation is spaces, one or two per level.
- There is no `class` keyword and there are no semicolons. A property is a name and its values separated by spaces.
- There are no commas in a list: `ShapeSize 0.5 0 0.5` is three numbers.
- Every `EmitorDef` sits inside `EffectDef { Emitors { ... } }`, never directly under `EffectDef`.

The order LM_Planes writes the properties of an emitter in:

```
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

`ColorMast` and `AlphaMast` are optional.

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

## Materials to reuse

A `Material` line is a GUID in braces followed by the path of the `.emat`:

```
Material "{00BEA27443975BEB}Graphics/Particles/materials/smoke/smoke_anim_02.emat"
```

You rarely need your own `.emat`. These vanilla materials cover most explosion, impact and smoke work. Each one exists under `P:\graphics\particles\materials\`, and the GUID is the one vanilla `.ptc` files write most often for it. The use column says how LM_Planes uses the material.

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

Copy a GUID from a vanilla `.ptc` under `P:\graphics\particles\` that uses the material. The GUID is not what makes the reference resolve: vanilla writes `smoke_anim_02.emat` with two different GUIDs, `{00BEA27443975BEB}` in the bonfire (`P:\graphics\particles\fire_bonfire.ptc:217`) and `{0BEA27443975BE0B}` in the failing hatchback engine (`P:\graphics\particles\hatchback_engine_failing.ptc:11`), and both effects play. The path is what must be right. The source notes for this file listed only the second GUID.

## Emitter properties worth knowing

Every property is in `ptc-format-reference.md`. These notes add how the properties are used when layering an effect. The notes marked LM_Planes are observations from that mod.

### Spawn volume

- `ShapeType`: the volume particles are born in (see the six values above).
- `ShapeSize <x> <y> <z>`: the size of that volume.
- `ConeAngle <a> <b> <c>`: the opening angles of the emission cone.
- `Offset <x> <y> <z>`: moves the spawn point away from the owner's position. A negative Y lowers it.
- `CenterX` and `CenterY`: the pivot of the sprite, from 0 to 1 in the LM_Planes notes.

### How many particles

- `MaxNum`: the most particles alive at once. LM_Planes note: do not let an emitter reach it, or it stops emitting.
- `BirthRate`: particles per second. `BirthRateRND` adds a random spread.
- `BirthRateVel`: ties the birth rate to the owner's speed, which gives a smoke trail behind a moving object. It is a number, not a switch: vanilla blood uses `BirthRateVel 100` (`P:\graphics\particles\blood_bleeding_01.ptc:8`).

### Lifetime

- `LifeTime`: seconds a particle lives. `LifeTimeRND` adds a random spread.
- `EffectTime`: how long the emitter runs before it stops spawning.
- `LifetimeByAnim`: with 1, a particle dies when its sprite animation ends.

### Sprite animation

- `AnimFPS`: the playback speed of the sprite sheet. For a material with one frame, LM_Planes writes `AnimFPS 999` with `AnimOnce 1`; vanilla does the same in the oil fire (`P:\graphics\particles\fire_oil1.ptc:131`).
- `AnimOnce`: 1 plays the sheet once, 0 loops it while the particle lives.
- `RandomFrame`: 1 starts each particle on a random frame, so particles of one emitter do not look the same.

### Starting motion

- `Velocity` and `VelocityRND`: starting speed and its random spread.
- `VelAffect`: how much of the owner's velocity the particle takes over, from 0 (none) to 1 (all).
- `VelAngle`, `RandomAngle`, `RandomRotDir`, `RotMultiplier`: starting direction and rotation.

### Forces

- `Wind`: whether wind moves the particle.
- `AirResistance` and `AirResistanceRND`: drag. LM_Planes uses about `0.05`.
- `GravityMultiply`: how strongly gravity pulls. A negative value makes the particle rise, which is how smoke climbs. LM_Planes uses `-0.05`; vanilla birds use `GravityMultiply -0.1` (`P:\graphics\particles\birds_01.ptc:25`).

### Draw order

- `Sort`: the render order. LM_Planes note: a higher number draws later, on top.

## Curves over a particle's life

`Color`, `Alpha`, `Size` and `RotationSpeed` are keyframe lists read over the life of each particle, from 0 (birth) to 1 (death).

```
Alpha {
 0 0 0.31101 0.24684 1 0
}
```

This reads: alpha 0 at birth, 0.24684 at 31 percent of the life, 0 at death. The particle fades in and then out.

A `Color` keyframe is four numbers, time then red, green and blue:

```
Color {
 0 1 1 1   1 0.9187 0.8938 0.8813
}
```

White at birth, a warm white at death. A long curve puts one keyframe on each line:

```
Color {
 0 0.8353 0.3133 0.008
 0.2115 0.1647 0.008 0.008
 0.2159 0 0 0
 0.2925 0.0201 0.0201 0.0201
}
```

## Mast curves: an envelope over the whole effect

A curve whose name ends in `Mast` is laid over the base curve and runs over the time of the effect, not the life of one particle:

- `AlphaMast` multiplies alpha.
- `SizeMast` changes size.
- `RotationSpeedMast` changes rotation.
- `BRateMast` changes the birth rate, so the spawn rate rises and falls.
- `VelocityMast` changes speed.
- `AirResistanceMast` changes drag.

The base curve sets the normal behaviour and the `Mast` curve adds the envelope. Uses seen in LM_Planes: smoke that pulses (`AlphaMast`), an explosion whose spawn rate ramps up and then down (`BRateMast`), debris that starts fast and slows (`VelocityMast`).

## Layering emitters

A real effect stacks emitters with different timing, size and material. The three LM_Planes effects:

### PLANES_EX, a bomb explosion with 4 emitters

- `short`: a short smoke burst. `Box` shape, `smoke_anim_02`, `LifeTime 0.5`.
- `short_spark`: quick sparks. `Box` shape, `sparks_05`, `LifeTime 0.1`, `AnimOnce 1`.
- `long_light`: lingering light smoke. `Ellipse` shape, `smoke_anim_02`, a half sphere cone of `90 -90 90`.
- `long_dark`: lingering dark smoke. `Ellipse` shape, larger and slower to fade.

### PLANES_IMPACT, a ground impact with 12 emitters

Grouped in three clusters named by emitter prefix: `explo_fire` (3 emitters), `explo_dust` (7, among them small and large rings and emitters aimed up and aimed the opposite way) and `explo_debris` with sparks (3).

### PLANES_BOOM, an aircraft fireball with 7 emitters

`fire_anim_small`, `fire_anim_root`, `fire_anim`, `fire_anim_Rot`, `red_smoke`, `red_smoke_large` and `sparks`. It leans on `Mast` curves for its movement.

The rule behind all three: keep each emitter small and give it one job (first flash, secondary debris, lingering smoke, sparks). Different `LifeTime` values per layer make the effect unfold in stages.

## Useful tricks

| Trick | What it gives |
|---|---|
| `GravityMultiply -0.05` | Smoke that rises |
| `AnimFPS 999` with `AnimOnce 1` | A material with one still frame, with no frame stepping |
| `RandomFrame 1` | Each particle of an emitter starts on a different frame |
| `ConeAngle 90 -90 90` | Emission over a half sphere, an expanding shell. Vanilla uses it for coolant steam (`P:\graphics\particles\hatchback_coolant_overheated.ptc:42`) |
| `ShapeType Ellipse` with a `ConeAngle` | A sphere or dome shaped shell |
| `Offset 0 -0.83 0` | A lower spawn point, so an explosion sits partly in the ground |
| `BirthRateVel` above 0 | A birth rate that grows with the owner's speed, for trails |
| One material on several emitters | Different `LifeTime`, size and `Velocity` give different layers at no extra texture cost |

## Registering the effects

The mod registers its three files in a modded `ParticleList`, in the `3_Game` script module:

```
// LM_Planes, scripts/3_Game/ParticleList.c
modded class ParticleList
{
    static const int PLANES_EX = RegisterParticle("LM_Planes/graphics/", "PLANES_EX");
    static const int PLANES_IMPACT = RegisterParticle("LM_Planes/graphics/", "PLANES_IMPACT");
    static const int PLANES_BOOM = RegisterParticle("LM_Planes/graphics/", "PLANES_BOOM");
}
```

- The first argument is the mod folder that holds the file, with a slash at the end.
- The second is the file name without `.ptc`.
- Each call returns the ID to store in a `static const int`.
- `RegisterParticle(string root_path, string file_name)` lowercases both arguments (`P:\scripts\3_game\particles\particlelist.c:452`), so the upper case names this mod uses work, but lower case names with the mod prefix are the convention in this skill (`SKILL.md`, "Registering custom particles").

## Playing them from script

One shot at a world position, as LM_Planes does when a plane hits the ground. `EOnContact` is the vanilla contact event (`P:\scripts\1_core\proto\enentity.c:213`) and `Particle.PlayInWorld` the vanilla factory (`P:\scripts\3_game\particles\particle.c:174`). `m_PlaneMode` and `PlaneMode` belong to the mod.

```
override void EOnContact(IEntity other, Contact extra)
{
    if (m_PlaneMode == PlaneMode.PLANE_MODE_AIR && GetVelocity(this).Length() > 30)
    {
        Particle p = Particle.PlayInWorld(ParticleList.PLANES_IMPACT, extra.Position);
    }
}
```

Through an `EffectParticle`, so the manager owns it:

```
EffectParticle eff = new EffectParticle();
eff.SetParticleID(ParticleList.PLANES_BOOM);
eff.SetAutodestroy(true);
SEffectManager.PlayInWorld(eff, GetPosition());
```

- The ID setter is `SetParticleID(int id)` (`P:\scripts\3_game\effects\effectparticle.c:327`). The source notes wrote `SetParticle(ParticleList.PLANES_BOOM)`, but vanilla `SetParticle` takes a `Particle` object, not an ID (`P:\scripts\3_game\effects\effectparticle.c:138`).
- `SetAutodestroy` is declared on `Effect` (`P:\scripts\3_game\effect.c:242`).
- `SEffectManager.PlayInWorld` takes the effect and a position (`P:\scripts\3_game\effectmanager.c:47`).
- The source notes opened the snippet with `import "EffectParticle";`. Enforce Script has no such statement; leave it out.

## Turning single emitters on and off

An effect can react to the game by switching emitters. The mod's seaplane water effect copies the vanilla boat wake:

```
// LM_Planes pattern. GetPlaneSpeed() is the mod's own method.
class EffectSeaplaneWaterFront : EffectBoatWaterBase
{
    void EffectSeaplaneWaterFront()
    {
        SetParticleState(ParticleList.PLANES_SEAPLANE_FRONT);
    }

    override void Update(float timeSlice = 0)
    {
        super.Update(timeSlice);

        float speed = GetPlaneSpeed();
        UpdateSpeedState(GetParticle(), speed);
    }

    override protected void UpdateSpeedState(Particle ptc, float speed)
    {
        // Emitter 0 is the slow wake, 1 the medium one, 2 the fast one.
        EnableEmitor(ptc, 0, speed > 5.0);
        EnableEmitor(ptc, 1, speed > 15.0);
        EnableEmitor(ptc, 2, speed > 30.0);
    }
}
```

What vanilla provides for this:

- `EnableEmitor(Particle ptc, int id, bool enable)` is a protected method of `EffectBoatWaterBase`, not of `EffectParticle` (`P:\scripts\4_world\entities\effects\boatwatereffects.c:306`). It sets `BIRTH_RATE` and `BIRTH_RATE_RND` of one emitter to zero, or back to the values of the `.ptc`. Extend `EffectBoatWaterBase` as above, or copy the method into your own `EffectParticle` subclass. The source notes extended `EffectParticle` directly, which has no such method.
- The current particle of an effect is `GetParticle()` (`P:\scripts\3_game\effects\effectparticle.c:166`). The source notes called `GetCurrentParticle()`, which vanilla does not have.
- `UpdateSpeedState(Particle ptc, float speed)` is the hook the vanilla front wake overrides (`P:\scripts\4_world\entities\effects\boatwatereffects.c:24`).
- `Update(float timeSlice = 0)` is declared on `EffectBoatWaterBase` too (`P:\scripts\4_world\entities\effects\boatwatereffects.c:325`). `EffectParticle` has no `Update` to override, so the source notes' `override void Update` on an `EffectParticle` subclass does not compile. Nothing calls it for you: the vanilla boat calls `Update` on each water effect every frame (`P:\scripts\4_world\entities\vehicles\boatscript.c:815`), and a plane has to do the same.

## Mistakes to avoid

1. Do not write your own `.emat` unless you must. Vanilla materials with their GUIDs cover most effects. (The source notes add that a custom `.emat` needs Workbench to create a GUID; `SKILL.md`, "GUID references", shows that a mod's own material resolves by path alone.)
2. Do not give a single frame material a low `AnimFPS`. Use `AnimFPS 999` with `AnimOnce 1`.
3. Do not forget `RandomFrame` on a group of similar particles. Without it they all show the same frame at the same time and look artificial.
4. Do not put an `EmitorDef` at the wrong level. It belongs inside `EffectDef { Emitors { ... } }`.

## Converting from CfgCloudlets

Vanilla still defines class based particles in `CfgCloudlets`, with keys such as `interval`, `cloudletDuration` and `cloudletShape` (`P:\DZ\data\data\particleeffects\config.cpp:47`). The mapping below is from the source notes and is not yet checked on `P:\`:

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

## DayZ 1.30

The 1.30 changes (`ParticleParamsOverrideData` for vehicle dust, the `IsHeadlessOrDedicatedServer` client check) are in `dayz-1-30-particles.md`. They do not change the `EffectDef` and `EmitorDef` syntax described here.

## Related skills

- The plane and seaplane context of `PLANES_EX`, `PLANES_IMPACT` and `PLANES_BOOM` belongs to the dayz-aviation skill.
- `modded class` rules and the Enforce Script language are in `skills/_shared/enscript/patterns/modded_class.md` and the enforce-script-reference skill.
