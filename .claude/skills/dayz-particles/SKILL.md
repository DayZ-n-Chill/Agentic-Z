---
name: dayz-particles
description: >
  DayZ particle effects system for Enforce Script modding. Covers the FULL
  pipeline: .ptc particle files (PLAIN TEXT, creatable programmatically),
  .emat material files (PLAIN TEXT, Particle/ParticleSprite shaders),
  .edds textures (standard DDS renamed), GUID reference system, vanilla material
  library (11 materials with GUIDs). Script API: legacy Particle, ParticleSource
  (native), ParticleManager (10k pool), SEffectManager wrapper, ParticleList
  registration. 277 vanilla effects catalog. Includes .ptc 56-property reference,
  .emat 12-property reference, device integration patterns (OnVarSync toggle,
  cleanup, overload sparks, generator smoke, sprinkler). Use for: creating custom
  particles WITHOUT Workbench, playing particles on objects, device lifecycle,
  SyncVar-driven toggle, EmitorParam tuning, Wiggle API. Consult BEFORE writing
  ANY particle code. Use alongside enforce-script-reference and dayz-model-pipeline.
---

# DayZ Particle Effects — Complete Modding Reference

## CRITICAL: .ptc AND .emat ARE PLAIN TEXT

DayZ particle files (.ptc) and material files (.emat) are plain text configs,
not binary. Custom particles can be created programmatically without Workbench.

| Layer | Format | Creatable? | Purpose |
|---|---|---|---|
| `.ptc` | Plain text config | YES | Particle effect (emitters, physics, curves) |
| `.emat` | Plain text config | YES | Material (texture ref, blend mode, color) |
| `.edds` | Standard DDS renamed | YES | Billboard sprite texture |
| `.meta` | Plain text (GUIDs) | Workbench only | NOT needed for mod runtime |

All particles are CLIENT-ONLY. Server controls state via SyncVars; client
creates/destroys particles in response.

---

## .ptc FILE FORMAT (verified from 9 vanilla files)

One EffectDef with one or more EmitorDef blocks. Each emitter is an independent
particle stream. Simplest particle (debug_dot): 1 emitter, 478 bytes. Complex
fire (fire_small_camp_01): 6 emitters (glow + flames + burst + short + sparks + smoke).

```
EffectDef {
 Emitors {
  EmitorDef <name> {
   ShapeType Point
   MaxNum 10
   BirthRate 5
   Material "{GUID}path/to/material.emat"
   SizeMultiplier 0.5
   Velocity 2
   LifeTime 1.5
   Color {
    0 1 0.8 0.3 1 0.7 0.5 0.25
   }
   Alpha {
    0 0 0.2 1 1 0
   }
   Repeat 1
  }
 }
}
```

### Property categories (56 total — full list in references/ptc-format-reference.md)

**Shape & emission:** ShapeType (Point/Box/Ellipse), ShapeSize (x y z),
ConeAngle (yaw pitch roll deg), MaxNum, BirthRate, BirthRateRND, Offset (x y z)

**Visual:** Material ("{GUID}path.emat"), SizeMultiplier, SizeRND,
BillboardingType (Full), CenterY (-1=bottom, 0=center), StretchMultiplier

**Motion:** Velocity, VelocityRND, AirResistance, AirResistanceRND,
GravityMultiply, GravityMultiplyRND, Wind (0-1), Spring, Restitution,
VelAngle (0/1), VelAffect (0-1)

**Lifetime:** LifeTime (seconds), LifeTimeRND, EffectTime (cycle duration),
Repeat (0=one-shot auto-deletes, 1=loop MUST stop manually)

**Animation:** AnimOnce, AnimFPS, LifetimeByAnim, RandomFrame

**Rotation:** RandomRotDir, RotMultiplier, RandomAngle

**Curves (keyframe pairs: time value time value ...):**
Color { t r g b t r g b }, Alpha { t a t a },
Size { t s t s }, RotationSpeed { t s t s }

**Master curves (modulate over EffectTime):**
ColorMast, AlphaMast, SizeMast, BRateMast, VelocityMast, AirResistanceMast

---

## .emat MATERIAL FORMAT (verified from 8 vanilla materials)

### Shader: `Particle` (fire, sparks, water, most particles)
```
Particle {
 AlbedoMap "{GUID}Graphics/Particles/sprites/texture.edds"
 Color 0 0 0 1
 Emissive 1 1 1 0
 BlendMode Additive_AlphaModulate
 Sort translucent
 Softness 2
 TileU 4
 TileV 2
}
```

### Shader: `ParticleSprite` (steam, flares, glow billboards)
```
ParticleSprite {
 AlbedoMap "{GUID}Graphics/Particles/sprites/texture.edds"
 Color 0.95 0.95 0.95 1
 Diffuse 0.95 0.95 0.95 1
 Ambient 0.59 0.59 0.59 1
 Softness 2
}
```

### All .emat properties (12):
AlbedoMap (texture GUID+path), Color (RGBA 0-1), Diffuse (RGBA),
Ambient (RGBA), Emissive (RGBA, self-glow), BlendMode (Additive_AlphaModulate
or numeric), Sort (translucent/overlay/0), Softness (0-2, edge blending),
TileU/TileV (sprite sheet cols/rows), CameraBlendFar (distance fade),
BidirLightScale (bidirectional lighting)

Full reference with examples: `references/emat-format-reference.md`

---

## GUID REFERENCE SYSTEM

Resources reference each other via `{HEXGUID}relative/path.ext`.

- **Vanilla→vanilla**: GUIDs embedded, engine resolves by GUID first
- **Mod .ptc→vanilla .emat**: USE vanilla GUID+path (mandatory, verified)
- **Mod .emat→vanilla .edds**: USE vanilla GUID+path (safe)
- **Mod .ptc→mod .emat**: path-only may work (needs in-game testing)
- **.meta files NOT needed** for mod runtime loading

---

## VANILLA MATERIAL LIBRARY (11 GUIDs mapped)

Reference these in custom .ptc to reuse vanilla visuals:

| GUID | Short name | Visual type |
|---|---|---|
| `{CB7AF4FD8ACBFDFC}` | glow/glow1.emat | Soft glow dot |
| `{009C2EBAACD2D72A}` | fire/sparks1.emat | Bright spark point |
| `{0B829A150C6A13E5}` | fire/sparks_06.emat | Spark strip (8-tile) |
| `{853257EDA4B1E35D}` | fire/fire_flame_01.emat | Fire flame billboard |
| `{3E6CE4D61F8AC71F}` | fire/fire_medium_camp_02.emat | Medium fire anim |
| `{83BCB6516091DB01}` | fire/fire_medium_camp_04.emat | Fire burst anim |
| `{62F13B8B540EBC80}` | fire/fireball_1.emat | Fireball |
| `{00BEA27443975BEB}` | smoke/smoke_anim_02.emat | Animated smoke puff |
| `{008E25684854DAB8}` | smoke/steam_small_cook_01.emat | Steam/vapor cloud |
| `{8FE2383D6913E098}` | enviroment/water_splash_01_NoEm.emat | Water splash |
| `{D29B53088A5A3911}` | smoke/smoke_dust_01_W.emat | White dust/mist |

All paths prefixed with `Graphics/Particles/materials/`.

---

## THREE SCRIPT API LAYERS

### 1. Legacy `Particle` (scripts/3_Game/Particles/Particle.c)
Creates `#particlesourceenf` child entity. EOnFrame lifetime tracking.
Auto-deletes non-looping particles. Used by FireplaceBase, torches, cooking.

### 2. `ParticleSource` extends Particle (ParticleSource.c)
Native C++ backed. No EOnFrame. Auto-destroy flags: ON_END, ON_STOP, ALL, NONE.
StopParticleFlags: `NONE = 0` (no-op; default `StopParticle()` already does gradual fade), IMMEDIATE, PAUSE (freeze visible).

### 3. `ParticleManager` pool (ParticleManager.c)
Global instance via `ParticleManager.GetInstance()` — 10000 pool, client only,
returns null on dedicated server. Pre-allocates+reuses ParticleSource objects.
Mods can also `new ParticleManager(settings)` to instantiate their own pools
(the test framework does this); GetInstance() is the global, not a hard singleton.

### Wrapper: `SEffectManager`
PowerGenerator pattern: `SEffectManager.PlayOnObject(effect, parent, pos, ori)`.
Cleanup: `SEffectManager.DestroyEffect(m_Smoke)`.

Full API signatures: `references/script-api-reference.md`

---

## API QUICK REFERENCE

```
// Static create+play
Particle p = Particle.PlayOnObject(ID, parent, localPos, localOri, forceWorldRot);
Particle p = Particle.PlayInWorld(ID, worldPos);
// ParticleManager.GetInstance() returns null on dedicated server — always guard.
ParticleManager pm = ParticleManager.GetInstance();
ParticleSource ps;
if (pm) ps = pm.PlayOnObject(ID, parent, localPos);

// Instance control
p.PlayParticle(optionalNewId);
p.StopParticle(flags);  // StopParticleFlags: NONE, IMMEDIATE, PAUSE
p.Stop();               // legacy alias
p.IsParticlePlaying();
p.ResetParticle();      // ParticleSource only
p.RestartParticle();    // reset+play
p.DisableAutoDestroy(); // ParticleSource only

// Parameter tuning (-1 = all emitters)
p.SetParameter(emitter, EmitorParam.AIR_RESISTANCE, 3.0);
p.ScaleParticleParamFromOriginal(EmitorParam.SIZE, 0.5);

// Wiggle
p.SetWiggle(randomAngle, randomInterval);
p.StopWiggle();
```

---

## REGISTERING CUSTOM PARTICLES

### Mod file structure
```
MyMod/
  data/particles/
    mymod_water_spray.ptc
    mymod_overload_sparks.ptc
  data/particles/materials/         ← optional custom materials
    mymod_blue_water.emat
  scripts/3_Game/
    MyMod_ParticleList.c
```

### Registration (3_Game layer)
```
modded class ParticleList
{
    static const int MYMOD_WATER_SPRAY = RegisterParticle(
        "MyMod/data/particles/", "mymod_water_spray");
    static const int MYMOD_OVERLOAD_SPARKS = RegisterParticle(
        "MyMod/data/particles/", "mymod_overload_sparks");
};
```

### AddonBuilder filter (include .ptc .emat .edds)
```
*.emat;*.edds;*.meta;*.ptc;*.c;*.imageset;*.layout;*.ogg;*.json;*.xml;*.paa;*.rvmat
```

---

## INTEGRATION PATTERNS — example mod (summary)

Full code: `references/integration-patterns.md`

**Pattern A** — FireplaceBase helpers: `MyMod_PlayParticle(out Particle, id, pos)` /
`MyMod_StopParticle(out Particle)` with null-safety and server guard.

**Pattern B** — SyncVar toggle: server sets state→SetSynchDirty, client
creates/destroys in MyMod_OnVarSync.

**Pattern C** — One-shot sparks: non-looping (Repeat 0) particles auto-delete,
no cleanup needed. Use for overload events.

**Pattern D** — SEffectManager wrapper: for combining particle+sound. Cleanup
ONLY via SEffectManager.DestroyEffect().

**Pattern E** — Runtime parameter tuning: SetParameter for AIR_RESISTANCE,
ScaleParticleParamFromOriginal for SIZE.

**Cleanup contract**: EVERY device with looping particles MUST clean up in
EEDelete + MyMod_OnPowerCut + destructor.

---

## PITFALLS AND HARD RULES

1. **Particles are CLIENT-ONLY.** Wrap in `#ifndef SERVER`.
2. **Looping particles (Repeat 1) NEVER end.** MUST Stop() + null ref.
3. **Stop() is gradual.** Use StopParticleFlags.IMMEDIATE for instant removal.
4. **ObjectDelete(particle)** valid for ParticleSource with DisableAutoDestroy().
5. **Render distance ~200m.** Engine limit, no workaround.
6. **Duplicate filenames** across mods: use unique prefixes (e.g. `mymod_`).
7. **ParticleManager.GetInstance()** returns null on server. Always null-check.
8. **SEffectManager.DestroyEffect()** is the ONLY safe Effect cleanup.
9. **AIR_RESISTANCE** controls smoke rise. FireplaceBase adjusts for ceilings.
10. **force_world_rotation=true** for smoke/steam that should always rise up.
11. **.meta files NOT needed** for mod runtime.
12. **GUIDs mandatory** when referencing vanilla .emat/.edds from mod .ptc.
13. **.ptc is PLAIN TEXT.** Can be generated by Python scripts, no Workbench needed.
14. **EffectTime + Repeat** interact: EffectTime is the master curve cycle, Repeat
    loops the entire effect. One-shot (Repeat 0) plays once for EffectTime duration.

---

## VANILLA PARTICLE CATALOG — KEY CATEGORIES

Full catalog: `references/vanilla-particle-catalog.md` (277 entries).

### Electricity
`POWER_GENERATOR_SMOKE` (1 emitter, loop), `BARBED_WIRE_SPARKS` (1 emitter, one-shot)

### Water
`WATER_JET` (2 emitters, loop), `WATER_JET_WEAK` (2 emitters, loop),
`WATER_SPILLING`, `DROWNING_BUBBLES`

### Fire
`CAMP_SMALL_FIRE` (6 emitters), `CAMP_STOVE_FIRE`, `BONFIRE_FIRE`

### Smoke/Steam
`CAMP_SMALL_SMOKE` (1 emitter), `CAMP_STEAM_2END`, `EVAPORATION`, `SPOOKY_MIST`

### Environment
`ENV_SWARMING_FLIES`, `SMOKING_HELI_WRECK`, `HOTPSRING_WATERVAPOR`,
`GEYSER_NORMAL`, `GEYSER_STRONG`, `VOLCANO`

---

## REFERENCE FILES

- `references/vanilla-particle-catalog.md` — 277 vanilla particles by category
- `references/integration-patterns.md` — 5 device-integration code patterns
- `references/ptc-format-reference.md` — 56-property .ptc reference with vanilla examples
- `references/emat-format-reference.md` — .emat format, both shader types, all 12 properties
- `references/script-api-reference.md` — Particle/ParticleSource/ParticleManager signatures
