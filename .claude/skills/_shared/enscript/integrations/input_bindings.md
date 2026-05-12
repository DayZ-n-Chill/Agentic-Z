# Custom Input Bindings

DayZ input is driven by the `inputs.xml` file inside your mod's PBO and the `UAInput` / `Input` API at runtime. Custom keybinds appear in **Options → Controls** just like vanilla bindings.

---

## inputs.xml — Declaring Custom Actions

Place `inputs.xml` at the root of your mod's data folder (same level as `config.cpp`):

```xml
<!-- MyMod/inputs.xml -->
<Inputs>

    <!-- A toggle-style key action (fires once on press) -->
    <Input name="UAMyMod_OpenMenu" >
        <Devices>
            <Device type="keyboard">
                <Key code="KeyCode.KC_END" />
            </Device>
        </Devices>
        <IsToggle>0</IsToggle>         <!-- 0 = momentary, 1 = toggle -->
        <ShortLabel>Open Menu</ShortLabel>
        <LongLabel>Open MyMod Menu</LongLabel>
        <Category>32</Category>         <!-- 32 = "Gameplay" section in UI -->
    </Input>

    <!-- A hold action (continuous while held) -->
    <Input name="UAMyMod_HoldRepair" >
        <Devices>
            <Device type="keyboard">
                <Key code="KeyCode.KC_HOME" />
            </Device>
        </Devices>
        <IsToggle>0</IsToggle>
        <ShortLabel>Repair (hold)</ShortLabel>
        <LongLabel>Hold to repair item in hands</LongLabel>
        <Category>32</Category>
    </Input>

</Inputs>
```

---

## Reading Input in Script (MissionGameplay / Player)

### Polling from MissionGameplay.OnKeyPress

```c
modded class MissionGameplay
{
    override void OnKeyPress(int key)
    {
        super.OnKeyPress(key);

        if (key == KeyCode.KC_END)
        {
            // Toggle menu visibility
            UIMenuPanel menuPanel = GetGame().GetUIManager().GetMenu();
            if (!GetGame().GetUIManager().IsMenuOpen(MenuID.MYMOD_INVENTORY))
                GetGame().GetUIManager().EnterScriptedMenu(MenuID.MYMOD_INVENTORY, null);
            else
                GetGame().GetUIManager().Back();
        }
    }
}
```

### Polling from PlayerBase via UAInput

```c
modded class PlayerBase
{
    override void OnScheduledTick(float deltaTime)
    {
        super.OnScheduledTick(deltaTime);

        // Client-only input polling; never run on server
        if (GetGame().IsServer())
            return;

        UAInput uaInput = GetUApi().GetInputByName("UAMyMod_OpenMenu");
        if (!uaInput)
            return;

        // LocalPress fires exactly once per press cycle
        if (uaInput.LocalPress())
        {
            MyMod_OnOpenMenuPressed();
            return;
        }

        UAInput holdInput = GetUApi().GetInputByName("UAMyMod_HoldRepair");
        if (holdInput && holdInput.LocalHold())
        {
            // Fires every tick while held; add accumulation yourself
            MyMod_OnHoldRepair(deltaTime);
        }
    }

    private void MyMod_OnOpenMenuPressed()
    {
        // Trigger a client-side menu; can also send RPC to server
    }

    private void MyMod_OnHoldRepair(float dt)
    {
        // Client feedback; actual repair triggered server-side via action
    }
}
```

---

## UAInput API Reference

```c
UAInput ua = GetUApi().GetInputByName("UAMyMod_OpenMenu");

ua.LocalPress()     // bool – true on first frame of press (one-shot)
ua.LocalRelease()   // bool – true on first frame of release
ua.LocalHold()      // bool – true every frame while held
ua.LocalValue()     // float – analog value (0..1 for axes, 0/1 for keys)
ua.SuppressNextFrame()  // stop the input from propagating this frame
```

---

## Axis / Mouse Input

For custom mouse or gamepad axis polling:

```c
// Mouse delta since last frame
float mx = GetGame().GetInput().GetActionValue(UAMouseX);
float my = GetGame().GetInput().GetActionValue(UAMouseY);
```

---

## Restricting Input by Context

Inputs should only fire when appropriate. Guard with context checks:

```c
bool ShouldProcessInput()
{
    // Don't capture keys in scripted menus
    if (GetGame().GetUIManager().IsMenuOpen(MenuID.SELECT_RESPAWN))
        return false;

    // Don't capture when chat is open
    if (GetGame().GetMission().IsChatInputActive())
        return false;

    // Don't capture on a dead player
    PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
    if (!player || !player.IsAlive())
        return false;

    return true;
}
```

---

## config.cpp: Declaring the inputs.xml

Reference the file in `CfgPatches` so the engine loads it:

```cpp
class CfgPatches
{
    class MyMod_Core
    {
        units[]    = {};
        weapons[]  = {};
        requiredVersion  = 0.1;
        requiredAddons[] = { "DZ_Scripts" };
    };
};

// Tell the engine where your inputs live
class CfgMods
{
    class MyMod
    {
        dir    = "MyMod";
        inputs = "inputs.xml";
    };
};
```

---

## ⚠️ Silent-fail traps — "my keybind does nothing"

Custom keybinds require a specific 3-piece setup. Missing any one piece results in *"keybind does nothing"* with **no log error** — the engine silently drops the action.

1. **`inputs.xml` root tag.** Some builds (and the `<modded_inputs>` variant for overriding existing actions) require a specific root tag. Wrong root tag = silently ignored. The simpler bindings-only form looks like:

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <modded_inputs>
       <action name="UAMyModToggleHud" preset="default">
           <key name="KC_F4"/>
       </action>
   </modded_inputs>
   ```

   Use this form when you only need to bind a key to an action; use the full `<Inputs>` form above when you need to declare a new action with labels and devices.

2. **`config.cpp` must register the file.** The path is backslash-escaped relative to PBO prefix:

   ```cpp
   class CfgMods
   {
       class MyMod
       {
           inputs = "MyMod\\inputs.xml";   // backslash-escaped
       };
   };
   ```

3. **Script reads via the right call.** `LocalPress` fires once on key-down; `LocalRelease` fires once on key-up; `LocalHold` fires every frame while held. Using `LocalRelease` when you meant `LocalPress` is a silent failure with no log warning.

All three pieces must align. If any are wrong: no log error, no engine warning, the keybind just doesn't fire.
