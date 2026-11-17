# Flight input bindings

How LM_Planes registers its flight inputs in `Inputs.xml` (shown with a `MyPlane` placeholder tag), its keyboard and Xbox scheme, the stringtable and `config.cpp` tie-in, and aircraft variants in one config. The traps that make a custom vehicle input read zero are in `skills/_shared/vehicles/aviation-inputs-and-actions.md`; the `inputs.xml` format itself is in `skills/_shared/enscript/integrations/input_bindings.md`.

Third-party mod behaviour, not vanilla: patterns read in the LM_Planes mod (Workshop `3730564764`), whose files are not in this repo. Not yet checked on `P:\` except where a `P:\` path is cited. Use it to learn the pattern and write the mod's own code.

## XML registration

In `scripts/data/Inputs.xml`:

```xml
<modded_inputs>
    <inputs>
        <actions>
            <input name="UAMyPlanePitchForward" loc="myplane_pitch_forward"/>
            <!-- ... 11 actions total -->
        </actions>
        <sorting name="myplane" loc="myplane_controls">
            <input name="UAMyPlanePitchForward"/>
            <!-- groups inputs in keybind menu under "myplane_controls" category -->
        </sorting>
        <exclude name="MyPlane_Controls">
            <!-- excludes these inputs from default vanilla binding conflicts -->
        </exclude>
    </inputs>
    <preset>
        <input name="UAMyPlanePitchForward">
            <btn name="kW"/>
            <btn name="x1LeftThumbUp"/>
        </input>
        <!-- ... -->
    </preset>
</modded_inputs>
```

## Standard aviation binding scheme

| Action | Keyboard | Xbox |
|---|---|---|
| Pitch forward (nose down) | W | LeftThumb Up |
| Pitch back (nose up) | S | LeftThumb Down |
| Roll left | A | LeftThumb Left |
| Roll right | D | LeftThumb Right |
| Rudder left | Q | Shoulder Left (LB) |
| Rudder right | E | Shoulder Right (RB) |
| Throttle up | LShift | Trigger Right (RT) |
| Throttle down | LCtrl | Trigger Left (LT) |
| Toggle mode (Air/Ground) | G | LeftThumb click |
| Free look | LAlt | RightThumb click |
| Shoot (weapons) | Space | A |

Key prefix convention: `k` for keyboard (`kW`, `kSpace`, `kLShift`, `kLControl`, `kLMenu`), `x1` for Xbox (`x1LeftThumbUp`, `x1A`, `x1ShoulderLeft`, `x1TriggerRight`). Vanilla declares the button names in `P:\bin\constants.xml`: `kW` at `P:\bin\constants.xml:475` and `x1LeftThumbUp` at `P:\bin\constants.xml:660`.

## Stringtable + config.cpp tie-in

`Stringtable.csv` defines display strings for each `loc="..."` key. LM_Planes sets all 13 locales to identical English (no real i18n) — pragmatic, leaves the structure ready for translation later.

`config.cpp` root references the XML:

```cpp
class CfgMods {
    class LM_Planes {
        inputs = "LM_Planes/scripts/data/Inputs.xml";
        // ...
    };
};
```

## Multi-aircraft variants in one config

```cpp
class CfgVehicles {
    class LM_Tigermoth: CarScript { /* base biplane */ };
    class LM_Tigermoth_MK2: CarScript { /* sport variant, top wing removed */ };
    class LM_Tigermoth_MK3: CarScript { /* seaplane variant with Buoyancy */ };
};
```

Family of variants share `LM_Planes\LM_Tigermoth\*.p3d` directory but each has its own model file. Reduces config duplication while allowing visual + behavior differences.
