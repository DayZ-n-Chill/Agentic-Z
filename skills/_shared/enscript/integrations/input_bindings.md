# Custom Input Bindings

A custom keybind has three parts: an `inputs.xml` that declares the input and its default key, a `CfgMods` line in `config.cpp` that points the game at that file, and script that reads the input through the `UAInput` API. The bound input then shows in **Options → Controls** like a vanilla one.

The script API is vanilla: `UAInput` and `UAInputAPI` in `P:\scripts\3_game\inputapi\uainput.c`, and `Input` in `P:\scripts\3_game\tools\input.c`. Vanilla ships no `inputs.xml` of its own on `P:\`; the file format below is the one shipped mods use, for example `Inputs\inputs.xml` inside `P:\Mods\@AutoCarFlip\Addons\HB_FlipVehicle.pbo` and `data\Inputs.xml` inside `P:\Mods\@AreaTitles\Addons\AreaTitles.pbo`.

## Contents

- [inputs.xml: declaring custom inputs](#inputsxml-declaring-custom-inputs)
- [config.cpp: registering inputs.xml](#configcpp-registering-inputsxml)
- [Reading input in script](#reading-input-in-script)
- [UAInput API Reference](#uainput-api-reference)
- [Axis / Mouse Input](#axis--mouse-input)
- [Restricting Input by Context](#restricting-input-by-context)
- [Silent-fail traps: "my keybind does nothing"](#silent-fail-traps-my-keybind-does-nothing)

---

## inputs.xml: declaring custom inputs

```xml
<?xml version="1.0" encoding="UTF-8"?>
<modded_inputs>
    <inputs>
        <actions>
            <input name="UAMyModOpenMenu" loc="MyMod: Open menu" />
            <input name="UAMyModHoldRepair" loc="MyMod: Repair (hold)" />
        </actions>
    </inputs>
    <preset>
        <!-- default keys; players can rebind them under Controls -->
        <input name="UAMyModOpenMenu">
            <btn name="kF7"/>
        </input>
        <input name="UAMyModHoldRepair">
            <btn name="kF8"/>
        </input>
    </preset>
</modded_inputs>
```

- The root is `<modded_inputs>`, with `<inputs><actions>` for the declarations and `<preset>` for default keys.
- `loc` is the label shown in Controls (a string or a stringtable key).
- Key names follow the `k` + key form of the shipped example (`<btn name="kF6">`).
- An empty `<preset>` is fine: the input exists and players bind it themselves, as `@AreaTitles` does.

---

## config.cpp: registering inputs.xml

The game finds the file through the `inputs` entry of your `CfgMods` class. The path starts at your PBO prefix:

```cpp
class CfgMods
{
    class MyMod
    {
        dir    = "MyMod";
        type   = "mod";
        inputs = "MyMod/data/inputs.xml";
        // ... defs / script modules ...
    };
};
```

Both mods named above use this form: `inputs = "HB_FlipVehicle/Inputs/inputs.xml"` and `inputs="AreaTitles/data/Inputs.xml"` in their `config.cpp`.

---

## Reading input in script

Read inputs on the client, once per frame. Vanilla does it in `MissionGameplay.OnUpdate(float timeslice)` (`P:\scripts\5_mission\mission\missiongameplay.c:287`), for example `GetUApi().GetInputByID(UAVoiceModifierHelper).LocalValue()` (:359). A custom input has no `UA...` ID constant, so look it up by name with `GetUApi().GetInputByName(string)` (`uainput.c:218`, `GetUApi()` at :279):

```c
modded class MissionGameplay
{
    override void OnUpdate(float timeslice)
    {
        super.OnUpdate(timeslice);

        if (!MyMod_ShouldProcessInput())
            return;

        UAInput openMenu = GetUApi().GetInputByName("UAMyModOpenMenu");
        if (openMenu && openMenu.LocalPress())
            MyMod_ToggleMenu();

        UAInput holdRepair = GetUApi().GetInputByName("UAMyModHoldRepair");
        if (holdRepair && holdRepair.LocalHold())
            MyMod_OnHoldRepair(timeslice);   // every frame while held
    }

    void MyMod_ToggleMenu()
    {
        // open or close your menu; send an RPC if the server must know
    }

    void MyMod_OnHoldRepair(float dt)
    {
        // client feedback only; the real repair runs server-side, e.g. as an action
    }
}
```

`MissionGameplay` exists only on clients, so this code never runs on a dedicated server. Do not poll in `PlayerBase.OnScheduledTick`: that tick drives the server-side modifiers and notifiers (`P:\scripts\4_world\entities\manbase\playerbase.c:3007-3016`).

`OnKeyPress(int key)` (`missiongameplay.c:742`) gives raw `KeyCode` values. It ignores the player's bindings, so use it only for debug keys.

---

## UAInput API Reference

All on `UAInput` in `P:\scripts\3_game\inputapi\uainput.c`:

| Call | Returns | Line |
|---|---|---|
| `LocalValue()` | `float`: the analog value (0 or 1 for a key) | :58 |
| `LocalPress()` | `bool`: pressed this frame | :60 |
| `LocalRelease()` | `bool`: released this frame | :61 |
| `LocalHold()` | `bool`: held | :62 |
| `LocalHoldBegin()` | `bool`: the hold started this frame | :63 |
| `LocalClick()`, `LocalDoubleClick()` | `bool` | :65, :64 |
| `Supress()` | Suppress the press event for the next frame (vanilla spelling) | :84 |
| `Lock()`, `Unlock()`, `IsLocked()` | Turn the input off and on again | :88, :89, :87 |
| `ForceDisable(bool bEnable)`, `ForceEnable(bool bEnable)` | Force the input off or on | :94, :93 |

`Input` (`GetGame().GetInput()`, `P:\scripts\3_game\global\game.c:728`) has the same reads by ID or name: `LocalValue_ID(int action, bool check_focus = true)` and `LocalValue(string action, bool check_focus = true)` (`P:\scripts\3_game\tools\input.c:50-51`), plus `LocalPress(string action, ...)`, used as `input.LocalPress("UAUIBack", false)` in `P:\scripts\5_mission\gui\digitalcodelockui.c:375`.

---

## Axis / Mouse Input

Read an axis through its input, as vanilla does for the spectator camera (`P:\scripts\4_world\entities\dayzspectator.c:39-40`):

```c
float yaw   = GetUApi().GetInputByID(UAAimLeft).LocalValue() - GetUApi().GetInputByID(UAAimRight).LocalValue();
float pitch = GetUApi().GetInputByID(UAAimDown).LocalValue() - GetUApi().GetInputByID(UAAimUp).LocalValue();
```

There is no `UAMouseX` input in vanilla; the aim inputs carry the mouse and the stick.

---

## Restricting Input by Context

Skip your inputs while a menu or the chat is open, or the player is dead. Each check below exists in vanilla. Put the method in the same `modded class MissionGameplay` as `OnUpdate` above:

```c
bool MyMod_ShouldProcessInput()
{
    UIManager ui = GetGame().GetUIManager();

    // Any menu open (inventory, map, pause, ...): GetMenu(), P:\scripts\3_game\tools\uimanager.c:59
    if (ui.GetMenu())
        return false;

    // Chat input open: IsMenuOpen(int id), uimanager.c:154; MENU_CHAT_INPUT = 17, constants.c:192
    if (ui.IsMenuOpen(MENU_CHAT_INPUT))
        return false;

    // Controls disabled by the game: Mission.IsControlDisabled(), gameplay.c:792,
    // overridden in missiongameplay.c:1119 (true while an input exclude is active)
    if (IsControlDisabled())
        return false;

    // IsAlive(), P:\scripts\3_game\entities\object.c:517
    PlayerBase player = PlayerBase.Cast(GetGame().GetPlayer());
    if (!player || !player.IsAlive())
        return false;

    return true;
}
```

`MENU_*` constants are in `P:\scripts\3_game\constants.c` (for example `MENU_INGAME = 9` at :184). There is no `MenuID` enum in vanilla.

---

## Silent-fail traps: "my keybind does nothing"

A keybind needs all three parts. A wrong part gives no log error; the input just never fires.

1. **The root tag and layout of `inputs.xml`.** It must be `<modded_inputs>` with `<inputs><actions><input name=... loc=.../>`. An `<Inputs>`/`<Input>` file with `<Devices>` and `<Category>` is not this format and is ignored.
2. **The `inputs` path in `CfgMods`.** It is relative to the PBO prefix (`MyMod/data/inputs.xml`), and the `CfgMods` class must be in a PBO that loads.
3. **The name in script.** `GetInputByName` must use the exact `name` from `inputs.xml`. A typo returns `null`, which the `if (openMenu && ...)` guard above turns into "does nothing".

Also check the read: `LocalPress` is one frame on key-down, `LocalRelease` one frame on key-up, `LocalHold` every frame while held.
