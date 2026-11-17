# Effects and lights

Navigation lights, headlights and seaplane water spray on an aircraft.

Third-party mod behaviour (LM_Planes, Workshop `3730564764`), not vanilla. Not yet checked on `P:\` except where a `P:\` path is cited. Use it to learn the pattern and write the mod's own code.

## Navigation lights

```cpp
class LlamaPlaneScript_NavLightLeft  extends PointLightBase { /* red wing tip */ };
class LlamaPlaneScript_NavLightRight extends PointLightBase { /* green wing tip */ };
class LlamaPlaneScript_NavLightTail  extends PointLightBase { /* white tail */ };

// In LlamaPlaneScript:
protected void CreateNavLights()
{
    vector lightPos = m_CachedLightWingLeft;  // from memory point light_wing_left
    m_NavLightLeft = LlamaPlaneScript_NavLightLeft.Cast(ScriptedLightBase.CreateLight(LlamaPlaneScript_NavLightLeft, lightPos));
    m_NavLightLeft.AttachOnObject(this, lightPos);
    // ... right, tail
}

protected void SetNavLightsVisible(bool visible)
{
    if (m_NavLightLeft) m_NavLightLeft.SetEnabled(visible);
    // ...
}
```

The vanilla pieces: `PointLightBase` at `P:\scripts\4_world\entities\scriptedlightbase\pointlightbase.c:1`, `CreateLight` at `P:\scripts\4_world\entities\scriptedlightbase.c:227` and `AttachOnObject` at `P:\scripts\4_world\entities\scriptedlightbase.c:127`. Navigation lights built this way are the same in 1.29 and 1.30.

## Headlights

LM_Planes gives each aircraft a `CarLightBase` child and returns it from `CreateFrontLight`:

```cpp
class LM_TigermothFrontLight extends CarLightBase
{
    void LM_TigermothFrontLight()
    {
        m_SegregatedBrightness  = 6;  m_SegregatedRadius  = 60; m_SegregatedAngle  = 80;
        m_SegregatedColorRGB    = Vector(0.9, 0.9, 1);
        m_AggregatedBrightness  = 10; m_AggregatedRadius  = 85; m_AggregatedAngle  = 90;
        m_AggregatedColorRGB    = Vector(0.9, 0.9, 1);
        FadeIn(0.3); SetFadeOutTime(0.25); SegregateLight();
    }
}
```

- **Up to 1.29:** community `CarScript` aircraft subclass `CarLightBase` as above and override `CreateFrontLight`.
- **Since 1.30:** vanilla vehicle headlights are a `VehicleLightBase` (`P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightbase.c:1`) configured by a `VehicleLightProfileBase` child and registered with `m_LightsComponent.RegisterLight(...)`. The old per-car classes are marked obsolete: `CivilianSedanFrontLight` carries `[Obsolete("use VehicleLightBase and VehicleLightProfileBase instead")]` at `P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\carlightbase\civiliansedanfrontlight.c:1`. Keep the `CarLightBase` pattern for a mod that already ships it and write new work the 1.30 way; the full migration is in `dayz-1-30-aviation.md`.

## Seaplane water spray

Three emitter classes per position (Front with at most 9 emitters, Back with 5, Side with 3) extend LM_Planes's own `EffectSeaplaneWaterBase : EffectParticle` (vanilla `EffectParticle` is at `P:\scripts\3_game\effects\effectparticle.c:4`). Speed states (Slow, Medium, Fast) come from an `enum ESeaplaneSpeed`. `UpdateSpeedState(speed)` enables and disables emitters as the speed changes, and `Update()` lerps the intensity between states. The memory point positions are refreshed on a timer (`m_PosUpdateTimer`) with `CoordToParent`. The same classes work for boats, amphibious vehicles and hovercraft.

How the effects are created at the `ptcfxfront`, `ptcfxback`, `ptcfxside1` and `ptcfxside2` memory points and cleaned up on every destruction path is in `aerodynamics-and-flight-physics.md` ("Water effect attachment via memory points" and "Triple cleanup hook pattern").
