# Mod structure

How a mod declares its script modules in `CfgMods`, hides a library from the mod list, splits into a parent and feature mods, and registers custom inputs with keys that do not fight vanilla. Building and sound set config is in `buildings-and-sound-config.md`; RPC and input scripting in `rpc-and-input-patterns.md`; vehicle helpers in `vehicle-script-helpers.md`.

These patterns come from shipped third-party mods. A line citing `P:\` was checked against vanilla; the rest are reported practice.

## Script modules sit inside `class defs`

Every mod's script modules go inside `class defs` under `CfgMods.<Mod>`, for a root mod and a feature mod alike. Vanilla does this for Sakhal (`P:\DZ\data_sakhal\config.cpp:14` to `:28`). Modules placed directly under `CfgMods.<Mod>` are not loaded.

## Hiding a library from the mod list

```cpp
class CfgMods
{
    class MyMod_Lib
    {
        dir = "MyMod_Lib";
        picture = "";
        action = "";
        hideName = 1;
        hidePicture = 1;
        name = "";
        version = "1.0";
        extra = 0;
        type = "mod";
        dependencies[] = { "Game", "World", "Mission" };
        class defs { /* script modules as usual */ };
    };
};
```

`hideName` and `hidePicture` keep a library that players never interact with out of the in-game mod list.

## A parent mod with feature mods

The parent registers shared scripts and inputs and has no entities; each feature mod requires the parent, never the other way round. Players can then switch a feature off without breaking the root.

```cpp
class CfgPatches
{
    class MyMod
    {
        units[] = {};
        requiredAddons[] = { "DZ_Data" };
    };
    class MyMod_FeatureX
    {
        units[] = { "MyMod_Entity1", "MyMod_Entity2" };
        requiredAddons[] = { "DZ_Data", "MyMod" };
    };
};
class CfgMods
{
    class MyMod
    {
        class defs
        {
            class gameScriptModule  { files[] = { "MyMod/scripts/3_Game" }; };
            class worldScriptModule { files[] = { "MyMod/scripts/4_World" }; };
        };
    };
    class MyMod_FeatureX
    {
        class defs
        {
            class worldScriptModule { files[] = { "MyMod_FeatureX/scripts/4_World" }; };
        };
    };
};
```

In a real mod each `CfgPatches` and `CfgMods` block sits in its own addon's `config.cpp`; they are shown together here.

## Custom inputs

Declare inputs in an XML file and point `CfgMods` at it with `inputs = "MyMod/scripts/data/Inputs.xml";`.

```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<modded_inputs>
    <inputs>
        <actions>
            <input name="UAMyModAction1" loc="mymod_action1_loc"/>
            <input name="UAMyModAction2" loc="mymod_action2_loc"/>
        </actions>
        <sorting name="mymod" loc="mymod_controls_category">
            <input name="UAMyModAction1"/>
            <input name="UAMyModAction2"/>
        </sorting>
        <exclude name="MyMod_Controls">
            <input name="UAMyModAction1"/>
        </exclude>
    </inputs>
    <preset>
        <input name="UAMyModAction1">
            <btn name="kSpace"/>
            <btn name="x1A"/>
        </input>
    </preset>
</modded_inputs>
```

| Section | Purpose |
|---|---|
| `<actions>` | Input names and their stringtable keys |
| `<sorting>` | Groups inputs under a heading in the keybind menu |
| `<exclude>` | A group of inputs switched off while the exclude is active (`UAInputAPI.ActivateExclude`, `P:\scripts\3_game\inputapi\uainput.c:239`) |
| `<preset>` | Default keys, one or more `<btn>` per input |

Input names start with `UA`, for User Action. Keyboard keys start with `k` (`kSpace`, `kLShift`, `kLControl`, `kLMenu`, `kW`); controller buttons start with `x1`: `x1A`, `x1B`, `x1ShoulderLeft` and `Right`, `x1TriggerLeft` and `Right`, `x1LeftThumbUp`, `Down`, `Left` and `Right`, the same four for `x1RightThumb`, and `x1ThumbLeft` and `Right` for a stick click (all in `P:\bin\*.xml` presets). An exclude that reaches `inventory` kills mouse look; see `action-and-input-rules.md`, section "Excludes that kill mouse look".

## Keys to leave alone

| Keys | Vanilla use |
|---|---|
| W, A, S, D | Movement |
| Q, E | Lean |
| Mouse | Aim and look |
| F | Pick up and interact |
| Left Shift, Left Ctrl | Sprint and crouch |
| Space | Jump and climb, `UAGetOver` |
| G, V, H, M | Throw and drop (`UAThrowitem`, `UADropItem`), view (`UAPersonView`), horn (`UACarHorn`), map (`UAMapToggle`), all in `P:\bin\preset_x1mousekey.xml` |
| Left Alt (`kLMenu`) | Free look, `UALookAround` and `UALookAroundToggle`, same file |
| F1 to F11 | Gesture and emote slots (`UAGestureSlot01` onward at `P:\bin\preset_x1mousekey.xml:418` to `:449`, `EmoteGreeting` and the other emotes from `:453`) |

Good candidates are J, K, B, N and the numpad. Check `preset_x1mousekey.xml` for the key before taking it, and see `action-and-input-rules.md` for keys admin mods use.
