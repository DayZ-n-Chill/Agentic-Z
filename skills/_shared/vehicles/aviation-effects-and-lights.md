# Aircraft lights and spray effects

How a scripted aircraft builds its navigation lights, its headlight, and the water spray of a seaplane.

The examples come from LM_Planes (Workshop `3730564764`), whose scripts are the source; they are mod practice, not vanilla, except where a `P:\` line is cited.

## Navigation lights

One `PointLightBase` child per light, created at a memory point and attached to the aircraft:

```c
class MyMod_NavLightLeft extends PointLightBase {};  // red wing tip
class MyMod_NavLightRight extends PointLightBase {}; // green wing tip
class MyMod_NavLightTail extends PointLightBase {};  // white tail

protected void CreateNavLights()
{
    vector lightPos = m_CachedLightWingLeft; // memory point light_wing_left
    m_NavLightLeft = MyMod_NavLightLeft.Cast(ScriptedLightBase.CreateLight(MyMod_NavLightLeft, lightPos));
    m_NavLightLeft.AttachOnObject(this, lightPos);
    // the same for the right and tail lights
}

protected void SetNavLightsVisible(bool visible)
{
    if (m_NavLightLeft) m_NavLightLeft.SetEnabled(visible);
    // the same for the right and tail lights
}
```

The vanilla pieces: `PointLightBase` (`P:\scripts\4_world\entities\scriptedlightbase\pointlightbase.c:1`), `CreateLight` (`P:\scripts\4_world\entities\scriptedlightbase.c:227`) and `AttachOnObject` (`:127`). DayZ 1.30 did not change any of them. In LM_Planes the three classes are `LlamaPlaneScript_NavLightLeft`, `LlamaPlaneScript_NavLightRight` and `LlamaPlaneScript_NavLightTail`; search for those names to read the original.

## Headlights

LM_Planes gives each aircraft a `CarLightBase` child and returns it from `CreateFrontLight`:

```c
class MyMod_PlaneFrontLight extends CarLightBase
{
    void MyMod_PlaneFrontLight()
    {
        m_SegregatedBrightness = 6;
        m_SegregatedRadius = 60;
        m_SegregatedAngle = 80;
        m_SegregatedColorRGB = Vector(0.9, 0.9, 1);
        m_AggregatedBrightness = 10;
        m_AggregatedRadius = 85;
        m_AggregatedAngle = 90;
        m_AggregatedColorRGB = Vector(0.9, 0.9, 1);
        FadeIn(0.3);
        SetFadeOutTime(0.25);
        SegregateLight();
    }
}
```

That is the pre 1.30 pattern. Since 1.30 a vanilla headlight is a `VehicleLightBase` (`P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\vehiclelightbase.c:1`), set up by a `VehicleLightProfileBase` child and registered with `m_LightsComponent.RegisterLight(...)`. The old per car classes are marked obsolete: `CivilianSedanFrontLight` carries `[Obsolete("use VehicleLightBase and VehicleLightProfileBase instead")]` (`P:\scripts\4_world\entities\scriptedlightbase\spotlightbase\carlightbase\civiliansedanfrontlight.c:1`). Keep the `CarLightBase` version in a mod that already ships it and write new work the 1.30 way; the steps are in `aviation-dayz-1-30.md`.

## Seaplane spray

LM_Planes builds the spray from its own `EffectSeaplaneWaterBase`, a child of the vanilla `EffectParticle` (`P:\scripts\3_game\effects\effectparticle.c:4`):

| Class | Emitters |
|---|---|
| `EffectSeaplaneWaterFront` | Up to 9 |
| `EffectSeaplaneWaterBack` | 5 |
| `EffectSeaplaneWaterSide` | 3 |

- An `enum ESeaplaneSpeed` holds three speed states: slow, medium and fast.
- `UpdateSpeedState(speed)` turns emitters on and off as the speed changes, and `Update()` blends the intensity between states.
- A timer (`m_PosUpdateTimer`) refreshes the memory point positions with `CoordToParent`.

The same classes suit boats, amphibious vehicles and hovercraft. Creating them at the `ptcfxfront`, `ptcfxback`, `ptcfxside1` and `ptcfxside2` memory points and destroying them on every path is in `aviation-seaplanes.md`; the particle file formats are in `/dayz-particles`.
