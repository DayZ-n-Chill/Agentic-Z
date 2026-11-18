# Device example: switch box and lit screen

A complete device with a toggle switch, a push button, a hinged cover and a coloured LED, as `model.cfg`, `config.cpp` and script, plus the two ways to light a screen and why they must not be combined. The keys are explained in `device-model-cfg.md` and the patterns in `device-animation-patterns.md`.

## model.cfg

```cpp
class CfgSkeletons
{
    class MyMod_SwitchBox_Skeleton
    {
        isDiscrete = 1;
        skeletonBones[] = {"switch", "", "button", "", "cover", "", "led_indicator", ""};
    };
};

class CfgModels
{
    class Default;
    class MyMod_SwitchBox: Default
    {
        skeletonName = "MyMod_SwitchBox_Skeleton";
        sections[] = {"led_green", "led_red", "led_blue"};
        class Animations
        {
            class switch_toggle { type = "rotation";    source = "switch_state"; selection = "switch";        axis = "switch_axis";      minValue = 0; maxValue = 1; angle0 = "rad -30"; angle1 = "rad 30"; };
            class button_press  { type = "translation"; source = "button_state"; selection = "button";        axis = "button_axis";      minValue = 0; maxValue = 1; offset0 = 0; offset1 = 0.005; };
            class cover_hinge   { type = "rotation";    source = "cover_state";  selection = "cover";         axis = "cover_hinge_axis"; minValue = 0; maxValue = 1; angle0 = 0; angle1 = "rad 120"; };
            class led_hide      { type = "hide";        source = "led_state";    selection = "led_indicator"; minValue = 0; maxValue = 1; hideValue = 0.5; };
        };
    };
};
```

The button's 0.005 is 5 mm only on a 1 m `button_axis` (`device-model-cfg.md`, "Memory axes").

## config.cpp

`SetObjectTexture` changes only selections listed in `hiddenSelections[]`; index 0 here is `led_green`.

```cpp
class CfgVehicles
{
    class HouseNoDestruct;
    class MyMod_SwitchBox: HouseNoDestruct
    {
        model = "MyMod\data\switchbox.p3d";
        displayName = "Switch box";
        hiddenSelections[] = {"led_green", "led_red", "led_blue"};
        hiddenSelectionsTextures[] = {"MyMod\data\led_green.paa", "MyMod\data\led_red.paa", "MyMod\data\led_blue.paa"};
        class AnimationSources
        {
            class switch_state { source = "user"; initPhase = 0; animPeriod = 0.4; };
            class button_state { source = "user"; initPhase = 0; animPeriod = 0.15; };
            class cover_state  { source = "user"; initPhase = 0; animPeriod = 1.0; };
            class led_state    { source = "user"; initPhase = 0; animPeriod = 0.2; };
        };
    };
};
```

## Script

These methods belong in the object's own script class. `SetObjectTexture(int index, string texture_name)` is a method of the object and takes the hidden selection index (`P:\scripts\3_game\entities\entityai.c:2881`). `CreateObjectEx` needs its flags argument and returns an `Object` to cast (`P:\scripts\3_game\global\game.c:703`). Enforce Script has no ternary operator (`_shared/enscript/patterns/language_workarounds.md`). The full script, with net sync, is `dayz-script-specialist` work.

```c
// Spawning one, server side
MyMod_SwitchBox box = MyMod_SwitchBox.Cast(GetGame().CreateObjectEx("MyMod_SwitchBox", position, ECE_PLACE_ON_SURFACE));

void ToggleSwitch()
{
    if (GetAnimationPhase("switch_state") < 0.5)
    {
        SetAnimationPhase("switch_state", 1.0);
        SetObjectTexture(0, "MyMod\data\led_green.paa");
    }
    else
    {
        SetAnimationPhase("switch_state", 0.0);
        SetObjectTexture(0, "MyMod\data\led_red.paa");
    }
}

void PressButton()
{
    SetAnimationPhase("button_state", 1.0);
    GetGame().GetCallQueue(CALL_CATEGORY_SYSTEM).CallLater(ReleaseButton, 100);
}

void ReleaseButton()
{
    SetAnimationPhase("button_state", 0.0);
}

void OpenCover()
{
    SetAnimationPhase("cover_state", 1.0);   // opens over 1 second
}

// Phase 0 shows the LED, phase 1 hides it (hideValue 0.5)
void SetLEDActive(bool active)
{
    if (active)
        SetAnimationPhase("led_state", 0.0);
    else
        SetAnimationPhase("led_state", 1.0);
}
```

## Lighting a screen

A device that shows an emissive screen when on and a black one when off has two ways to do it. Use one.

Slide a cover away. The model holds a `screen` selection with the emissive texture and a `HideScreen` selection with a black texture a hair in front of it. A translation moves the cover out of view when the device is on:

```cpp
// model.cfg
class HideScreen
{
    type = "translation";
    source = "HideScreen";
    selection = "HideScreen";
    axis = "HideScreen_axis";      // 1 m long, so 0.5 is half a metre
    minValue = 0;
    maxValue = 1;
    offset0 = 0;
    offset1 = 0.5;
};
```

```cpp
// config.cpp: an always on variant starts with the cover away, a powered one starts covered
class MyMod_Device_Admin: Inventory_Base
{
    class AnimationSources { class HideScreen { source = "user"; initPhase = 1; animPeriod = 0.3; }; };
};
class MyMod_Device: Inventory_Base
{
    class AnimationSources { class HideScreen { source = "user"; initPhase = 0; animPeriod = 0.3; }; };
};
```

```c
// in OnVariablesSynchronized
if (m_MyMod_Powered)
    SetAnimationPhase("HideScreen", 1.0);    // cover away, screen lit
else
    SetAnimationPhase("HideScreen", 0.0);    // cover back, screen black
```

Swap the material. Change the screen face's `.rvmat` through `hiddenSelections`. This works for a plain coloured LED, but a textured screen renders black when the replacement `.rvmat` uses procedural `#(argb,...)color(...)` stages, with no error. For a single coloured dot, use `hiddenSelections` with Normal or Basic shader materials (`_shared/vehicles/emissive-led-materials.md`).

Pick the cover when the lit look needs a real texture such as a logo or a UI image; pick the swap for a single colour. Never list an animated selection in `hiddenSelections[]` as well, because the engine then both swaps the material and moves the part, and one of the two effects usually breaks.
