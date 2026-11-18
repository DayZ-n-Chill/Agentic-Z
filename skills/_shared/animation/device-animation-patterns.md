# Device animation patterns

Which `config.cpp` source and which script call drive a device's `model.cfg` animation, and five worked patterns: toggle switch, push button, hinged lid, dial with set positions and drawer. The `model.cfg` keys are in `device-model-cfg.md`; a complete device is in `device-switch-box.md`.

## The config source

Each `user` source lives in `class AnimationSources` of the object's `config.cpp` class (`animation-sources.md`). Script sets its phase.

```cpp
class CfgVehicles
{
    class HouseNoDestruct;
    class MyMod_Device: HouseNoDestruct
    {
        model = "MyMod\data\device.p3d";
        class AnimationSources
        {
            class switch_state { source = "user"; initPhase = 0; animPeriod = 0.5; };
            class button_state { source = "user"; initPhase = 0; animPeriod = 0.1; };
            class cover_open   { source = "user"; initPhase = 0; animPeriod = 0.8; };
        };
    };
};
```

| Key | Meaning |
|---|---|
| `source = "user"` | Script drives it with `SetAnimationPhase`. |
| `initPhase` | The phase at spawn. |
| `animPeriod` | Seconds per unit of phase. With a 0 to 1 range it is the time from 0 to 1; vanilla's fence gate runs 0 to 100 with `animPeriod = 0.018`, about 1.8 seconds a swing (`animation-sources.md`). |
| `sound` | Seen in mod configs, not found in vanilla sources; unverified. |

## Setting the phase from script

`SetAnimationPhase(source, phase)` moves the part over `animPeriod`; `GetAnimationPhase(source)` reads it back (`script-hooks.md`).

The phase is not synced for you. Change the state on the server, keep it in a net synced variable, and set the phase on each client from `OnVariablesSynchronized`, as vanilla's barrel does: `OnVariablesSynchronized` (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:158`) calls `UpdateVisualState` (`:144`), which sets every phase. The two vanilla patterns are in `script-hooks.md`.

## Toggle switch

```cpp
// model.cfg
class switch_on_off
{
    type = "rotation";
    source = "switch_state";
    selection = "switch";
    axis = "switch_axis";
    minValue = 0;
    maxValue = 1;
    angle0 = "rad -22.5";        // off
    angle1 = "rad 22.5";         // on
};
// config.cpp: class switch_state { source = "user"; initPhase = 0; animPeriod = 0.3; };
```

```c
void ToggleSwitch()
{
    if (GetAnimationPhase("switch_state") < 0.5)
        SetAnimationPhase("switch_state", 1.0);
    else
        SetAnimationPhase("switch_state", 0.0);
}
```

## Push button that springs back

A `translation` of 0.003 on a 1 m axis is a 3 mm press (`device-model-cfg.md`, "Memory axes"), with `animPeriod = 0.1`. Script presses, then releases after a delay:

```c
void PressButton()
{
    SetAnimationPhase("button_state", 1.0);
    GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(ReleaseButton, 150);
}

void ReleaseButton()
{
    SetAnimationPhase("button_state", 0.0);
}
```

`CallLater` takes the function itself, then the delay in milliseconds (`P:\scripts\2_gamelib\tools.c:61`). The form with an object and a function name is `CallLaterByName` (`:63`); passing `this, "ReleaseButton"` to `CallLater` matches neither.

## Hinged lid

A `rotation` on a hinge axis, usually vertical, with `angle0 = 0` closed and `angle1 = "rad 90"` open, and `animPeriod = 0.8` for a smooth swing.

## Dial with set positions

`type = "rotationZ"` with `angle1 = "rad 360"`, then script picks a phase per position:

```c
void SetDialPosition(int position)
{
    float phase = position / 4.0;    // 0, 0.25, 0.5, 0.75 for positions 0 to 3
    SetAnimationPhase("dial_state", phase);
}
```

## Drawer

A `translation` on an axis that points the way the drawer slides, 1 m long, with `offset1 = 0.4` for 40 cm of travel and `animPeriod = 0.6`. For a panel sliding 0.2 m along -X, the axis runs from `(0, 0, 0)` to `(-1, 0, 0)` and `offset1 = 0.2`.

## Several animations on one object

Each source is independent, so script can drive a switch, a button and an LED at once. Animations that share one source move together; two doors that open opposite ways use the same source with `angle1 = "rad 90"` on one and `"rad -90"` on the other:

```cpp
class door_left  { type = "rotation"; source = "both_doors"; selection = "door_left";  axis = "door_left_axis";  angle0 = 0; angle1 = "rad 90"; };
class door_right { type = "rotation"; source = "both_doors"; selection = "door_right"; axis = "door_right_axis"; angle0 = 0; angle1 = "rad -90"; };
```

`SetAnimationPhase("both_doors", 0.5)` then moves both halfway.

## Common timing mistakes

| Symptom | Cause | Fix |
|---|---|---|
| Plays instantly | `animPeriod = 0` | Give it a time above 0, such as 0.5. |
| Clients see a different state | Phase set on the server only | Sync the state and set the phase in `OnVariablesSynchronized`. |
| Button stays down | No release call | Queue the release with `CallLater`. |
