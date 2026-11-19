# Flight input bindings

How a plane mod registers its flight inputs in `Inputs.xml`, which keyboard and gamepad keys it binds by default, and how the stringtable and `config.cpp` tie in.

The scheme comes from LM_Planes (Workshop `3730564764`), whose files are the source; it is mod practice, not vanilla, except where a `P:\` line is cited. The `inputs.xml` format itself is in `_shared/enscript/integrations/input_bindings.md`, and the faults that make a custom input read zero are in `aviation-inputs-and-actions.md`.

## Registering the inputs

In `scripts/data/Inputs.xml`, with a `MyPlane` tag:

```xml
<modded_inputs>
    <inputs>
        <actions>
            <input name="UAMyPlanePitchForward" loc="myplane_pitch_forward"/>
            <!-- eleven actions in all -->
        </actions>
        <sorting name="myplane" loc="myplane_controls">
            <!-- shows these inputs together in the key binding menu -->
            <input name="UAMyPlanePitchForward"/>
        </sorting>
        <exclude name="MyPlane_Controls">
            <!-- while script has called GetUApi().ActivateExclude("MyPlane_Controls"), these inputs read zero -->
        </exclude>
    </inputs>
    <preset>
        <input name="UAMyPlanePitchForward">
            <btn name="kW"/>
            <btn name="x1LeftThumbUp"/>
        </input>
    </preset>
</modded_inputs>
```

Vanilla's own exclude groups start at `P:\bin\specific.xml:81`.

## Default keys

| Action | Keyboard | Gamepad |
|---|---|---|
| Pitch forward, nose down | W | Left stick up |
| Pitch back, nose up | S | Left stick down |
| Roll left | A | Left stick left |
| Roll right | D | Left stick right |
| Rudder left | Q | Left shoulder |
| Rudder right | E | Right shoulder |
| Throttle up | Left Shift | Right trigger |
| Throttle down | Left Ctrl | Left trigger |
| Switch air and ground mode | G | Left stick click |
| Free look | Left Alt | Right stick click |
| Fire weapons | Space | A |

Button names start with `k` for keyboard (`kW`, `kSpace`, `kLShift`, `kLControl`, `kLMenu`) and `x1` for the gamepad (`x1LeftThumbUp`, `x1A`, `x1ShoulderLeft`, `x1TriggerRight`). Vanilla declares them in `P:\bin\constants.xml`: `kW` at `:475` and `x1LeftThumbUp` at `:660`.

## Stringtable and config

`Stringtable.csv` gives the display text for each `loc="..."` key. LM_Planes fills all 13 language columns with the same English text, which leaves the structure ready for real translations.

The root mod's `CfgMods` class points at the file:

```cpp
class CfgMods
{
    class MyMod_Planes
    {
        inputs = "MyMod_Planes/scripts/data/Inputs.xml";
    };
};
```

## Variants in one config

A family of variants sits in one `CfgVehicles`, each with its own model file in a shared folder:

```cpp
class CfgVehicles
{
    class MyMod_Biplane: CarScript { /* the base biplane */ };
    class MyMod_Biplane_Sport: CarScript { /* top wing removed */ };
    class MyMod_Biplane_Float: CarScript { /* seaplane, with class Buoyancy */ };
};
```

LM_Planes does this for the Tigermoth MK1, MK2 and MK3 under `LM_Planes\LM_Tigermoth\`. Floats are in `aviation-seaplanes.md`.
