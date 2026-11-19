# Aircraft script performance

How a scripted aircraft keeps its per-tick cost down: skip animation calls that change nothing, run each update at the rate it needs, cache input lookups, and move cockpit detail into proxy models.

The patterns come from LM_Planes (Workshop `3730564764`), whose scripts are the source; they are mod practice, not vanilla, except where a `P:\` line is cited.

## Skip animation calls that change nothing

`SetAnimationPhase` is a native call (`P:\scripts\3_game\entities\entity.c:15`). Remember the last phase sent and call it again only when the value has moved past a small threshold:

```c
protected float m_LastPitchAnim = -999.0;
protected const float ANIM_THRESHOLD = 0.015;

protected void UpdateControlSurfaceAnimations(float dt)
{
    float pitchPhase = m_PitchSmooth;
    if (Math.AbsFloat(pitchPhase - m_LastPitchAnim) >= ANIM_THRESHOLD)
    {
        SetAnimationPhase(ANIM_ELEVATOR_1, pitchPhase);
        SetAnimationPhase(ANIM_ELEVATOR_2, pitchPhase);
        m_LastPitchAnim = pitchPhase;
    }
}
```

Do the same for roll, rudder and gear retraction. Control surfaces hold still most of the time, so most calls are skipped.

## Run each update at its own rate

| Update | Interval | Why |
|---|---|---|
| `UpdateAllDials` | 100 ms (10 Hz) | Faster dial movement is not visible |
| Network sync, pilot flying | 33 ms (30 Hz), `GetSyncInterval()` | Others need a smooth path |
| Network sync, idle | 100 ms (10 Hz), `GetSyncIntervalIdle()` | Nothing is moving |
| Flight physics | Every `EOnSimulate` | Anything slower is unstable |

## Look up inputs once

Look up each `UAInput` by name on the first `OnInput` and keep the reference, instead of a string lookup every input frame. `GetInputByName` is vanilla (`P:\scripts\3_game\inputapi\uainput.c:218`).

```c
protected UAInput m_InputPitchBack;
protected UAInput m_InputPitchFwd;

protected void CacheInputActions()
{
    m_InputPitchBack = GetUApi().GetInputByName("UAMyModPlanePitchBack");
    m_InputPitchFwd  = GetUApi().GetInputByName("UAMyModPlanePitchForward");
    m_InputsCached = true;
}

override void OnInput(float dt)
{
    if (!m_InputsCached) CacheInputActions();
    float pitchInput = m_InputPitchFwd.LocalValue() - m_InputPitchBack.LocalValue();
}
```

LM_Planes caches twelve inputs this way. Input names must match `inputs.xml` and the stringtable; see `aviation-input-bindings.md`.

## Cockpit detail in proxy models

Keep the main `<Aircraft>.p3d` a low poly shell with every LOD, and put the detail in separate proxy models it references by `proxy:\path` (one proxy per LOD, numbered `.001`):

| Proxy model | Holds |
|---|---|
| `proxy/*_detail_cockpit.p3d`, `*_detail_controls.p3d`, `*_detail_engine.p3d` | High poly cockpit, controls and engine |
| `proxy/*_details.p3d` | Detail for the whole airframe |
| `proxy/*_door_X_Y.p3d` | Doors that come off (the Z37) |

The high poly proxies load only when the camera is close, so a detailed cockpit costs nothing from far away.
