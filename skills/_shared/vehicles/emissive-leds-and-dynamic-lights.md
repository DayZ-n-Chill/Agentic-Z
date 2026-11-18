# Emissive LEDs and dynamic lights

How to make an LED change colour and glow from script (a hidden selection, one `.rvmat` per state, a swap with `SetObjectMaterial`) and how to make it also light the scene with a `PointLightBase` on a memory point.

The `.rvmat` for each state, the shader choice and the black LED checklist are in `emissive-led-materials.md`. Since DayZ 1.30 a car's headlights, brake and reverse lights do not use this pattern: they are `VehicleLightBase` entities registered on the lights component (`dayz-1-30-lights-and-battery.md`). A car's light material paths and hidden selection order are in `lights.md`, and the dashboard backlight swap (`dashboardMatOn`, `dashboardMatOff`) in `materials-and-selections.md`.

An LED touches three places: the `.p3d` model, the `.rvmat` and its textures, and Enforce Script.

## The model and config

The engine swaps a material at runtime only on a named hidden selection. In Object Builder select the LED faces and put them in their own selection, such as `led_panel`, or `led_1`, `led_2` for several independent LEDs.

Register the selection in `config.cpp`. The config parent is `Inventory_Base` (`P:\DZ\data\config.cpp:3162`); `ItemBase` is only the script class, and a config that inherits it fails with an undefined base class.

```cpp
class Inventory_Base;
class MyMod_LedBox: Inventory_Base
{
    hiddenSelections[] = {"led_panel"};                              // index 0 in script
    hiddenSelectionsTextures[] = {"MyMod\data\led_off_co.paa"};      // default, off
    hiddenSelectionsMaterials[] = {"MyMod\data\led_off.rvmat"};
};
```

With several LEDs, list them in the same order in all three arrays. The index script uses is the array position, so an off-by-one puts the material on the wrong selection.

## Swap the material from script

`SetObjectTexture` (`P:\scripts\3_game\entities\entityai.c:2881`) and `SetObjectMaterial` (`:2884`) change a hidden selection by index. Call them wherever the state changes. When only the server changes the state, sync it and have every client re-apply the material in `OnVariablesSynchronized`.

```c
// scripts/4_World/MyMod/Entities/MyMod_LedBox.c
class MyMod_LedBox extends ItemBase
{
    void SetLedColor(string colorType)
    {
        if (colorType == "RED")
        {
            SetObjectTexture(0, "MyMod/data/led_red_co.paa");
            SetObjectMaterial(0, "MyMod/data/led_red_on.rvmat");
        }
        else if (colorType == "BLUE")
        {
            SetObjectTexture(0, "MyMod/data/led_blue_co.paa");
            SetObjectMaterial(0, "MyMod/data/led_blue_on.rvmat");
        }
        else
        {
            SetObjectTexture(0, "MyMod/data/led_off_co.paa");
            SetObjectMaterial(0, "MyMod/data/led_off.rvmat");
        }
    }
}
```

## Glow is not light

A material with a high `emmisive[]` glows on screen, but it lights nothing: in a dark room the walls and the player stay dark. To make the LED light the scene, create a dynamic light from script and attach it to a memory point so it follows the object.

`CreateLight` is a static method of `ScriptedLightBase` (`P:\scripts\4_world\entities\scriptedlightbase.c:227`), `AttachOnMemoryPoint` is at `:165`, and `PointLightBase` extends `ScriptedLightBase` (`P:\scripts\4_world\entities\scriptedlightbase\pointlightbase.c:1`).

```c
PointLightBase m_LedLight;

void TurnOnRealLight(vector colorRGB)
{
    if (!m_LedLight)
    {
        m_LedLight = PointLightBase.Cast(ScriptedLightBase.CreateLight(PointLightBase, GetPosition()));
        m_LedLight.AttachOnMemoryPoint(this, "led_memory_position");  // memory point in the .p3d
        m_LedLight.SetDiffuseColor(colorRGB[0], colorRGB[1], colorRGB[2]);
        m_LedLight.SetRadiusTo(2.0);
    }
}

void TurnOffRealLight()
{
    if (m_LedLight)
    {
        m_LedLight.FadeOut(0.2);
        m_LedLight = null;
    }
}
```

Turn the light off in `EEDelete` too, or a removed object leaves its light behind.

## Steps

1. Put the LED faces in their own named selection in Object Builder.
2. Add the selection to `hiddenSelections[]` with a default texture and material.
3. Write one `.rvmat` per state, with `emmisive[]` above 1 for each "on" state (`emissive-led-materials.md`).
4. Swap texture and material with `SetObjectTexture` and `SetObjectMaterial`, and re-apply on clients after sync.
5. If the LED must light the scene, attach a `PointLightBase` to a memory point.

## Related

- The 3D viewer (`scripts/tools/dayz-3d-viewer/`) previews emissive materials; its `.rvmat` reader takes the `emmisive` key.
- `_shared/ui/` when a menu drives the LED state.
- `_shared/enscript/depth/` for `SyncVars` and `OnVariablesSynchronized`.
