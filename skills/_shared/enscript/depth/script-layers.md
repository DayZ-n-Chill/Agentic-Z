# Script layers

Which script module a class belongs in, what each module can see, how HUD code bridges from `4_World` to `5_Mission`, and the layer mistakes that compile and then silently do nothing.

## The five modules

DayZ compiles the modules in this order. A mod's `CfgMods` `defs` normally declares the last three; the key names are reported, not checked on `P:\`.

| Folder | Module key | Typical mod use |
|---|---|---|
| `1_Core` | `engineScriptModule` | Engine utilities and enums; rarely needed |
| `2_GameLib` | `gameLibScriptModule` | Rarely used by mods |
| `3_Game` | `gameScriptModule` | `DayZGame`, RPC IDs, constants, shared data |
| `4_World` | `worldScriptModule` | `PlayerBase`, `ItemBase`, entities, actions |
| `5_Mission` | `missionScriptModule` | `MissionServer`, `MissionGameplay`, HUD, startup hooks |

Each layer sees its own classes and every lower layer's, never a higher one. Naming a higher type is a compile error: `3_Game` code that names `PlayerBase`, which lives in `4_World`, gets `Undefined type 'PlayerBase'`. Accept a lower base such as `Man` or `Object` in the lower layer and `Class.CastTo` from `4_World` up.

## What each layer can name

| Layer | Purpose | Can name | Cannot name |
|---|---|---|---|
| `3_Game` | Data, enums, config, utilities | The engine core, `GetGame()`, and the classes in `1_core` to `3_game` | `PlayerBase`, `ItemBase`, world logic, mission classes |
| `4_World` | Entities, actions, items, world logic | All of `3_Game`, plus `PlayerBase`, `ItemBase`, `MissionBaseWorld` (`P:\scripts\4_world\classes\missionbaseworld.c:1`), and Dabs `ScriptView` and `ViewController` (they need Dabs Framework, `DF_Scripts`) | `MissionGameplay`, `IngameHud`, `Chat`, `InGameMenu` |
| `5_Mission` | Client presentation, HUD, menus, mission hooks | Everything below, plus `MissionGameplay` (`P:\scripts\5_mission\mission\missiongameplay.c:1`), `MissionServer` (`P:\scripts\5_mission\mission\missionserver.c:5`), `IngameHud` (`P:\scripts\5_mission\gui\ingamehud.c:1`), `Chat` (`P:\scripts\5_mission\gui\chat\chat.c:14`), `ChatInputMenu` and `InGameMenu` (`P:\scripts\5_mission\gui\ingamemenu.c:1`) | Nothing; it is the top |

`Widget` is declared in `1_core` (`P:\scripts\1_core\proto\enwidgets.c:107`), and `EntityAI` (`P:\scripts\3_game\entities\entityai.c:115`), `UIManager` (`P:\scripts\3_game\tools\uimanager.c:1`), `UIScriptedMenu` (`P:\scripts\3_game\tools\uiscriptedmenu.c:66`), `Hud` (`P:\scripts\3_game\gameplay.c:637`), `Mission` (`:685`) and `Transport` (`P:\scripts\3_game\vehicles\transport.c:68`) in `3_game`. So `3_Game` code can name widgets, `EntityAI`, `UIManager` and `UIScriptedMenu`.

## What goes where

| Layer | Put here |
|---|---|
| `3_Game` | Enums, constants, defines; data classes for config and serialization; pure string, maths and file helpers; RPC ID enums; logging |
| `4_World` | Device entities (`ItemBase` and `Inventory_Base` descendants); actions; entity logic such as a power graph, networking and saving; kits and hologram overrides; server device controllers; Dabs views and controllers; UI panels that need neither `IngameHud` nor `MissionGameplay` |
| `5_Mission` | `modded class MissionGameplay` and `MissionServer`; HUD overlays that follow the HUD's visibility; chat integration; compass, GPS map and player list overlays; notifications tied to game state; widgets that stay on screen; any UI that asks the mission whether a menu is open |

Rule of thumb: if it draws on the HUD and must hide when the HUD hides, it belongs in `5_Mission`. A mod can keep every file in `4_World`, but one with 15 pure UI files there and one in `5_Mission` will have to move them to add HUD features.

## Bridging HUD code

Keep the logic in a `4_World` singleton and let a `5_Mission` bridge make the mission-only checks and pass the result down:

```c
// scripts/4_World/MyMod/MyMod_PhoneHUD.c
class MyMod_PhoneHUD
{
    static ref MyMod_PhoneHUD s_Instance;
    protected Widget m_Root;

    static void Init() { s_Instance = new MyMod_PhoneHUD(); }
    static MyMod_PhoneHUD Get() { return s_Instance; }
    void Show(bool visible) { m_Root.Show(visible); }
    void UpdateFrame() { }
}

// scripts/5_Mission/MyMod/MyMod_MissionGameplay.c
modded class MissionGameplay
{
    override void OnInit()
    {
        super.OnInit();
        MyMod_PhoneHUD.Init();
    }

    override void OnUpdate(float timeslice)
    {
        super.OnUpdate(timeslice);
        IngameHud hud = IngameHud.Cast(GetGame().GetMission().GetHud());
        bool hudVisible = hud && hud.MyMod_IsHudVisible();
        MyMod_PhoneHUD.Get().Show(hudVisible);
        if (hudVisible)
            MyMod_PhoneHUD.Get().UpdateFrame();
    }
}
```

The `4_World` class never names `IngameHud`. `MyMod_IsHudVisible()` is a helper the mod adds to `IngameHud` with a `modded class`. Vanilla's own `IngameHud.IsHudVisible()` is a stub that returns false (`P:\scripts\5_mission\gui\ingamehud.c:1313`); the live state comes from `GetHudVisibility()` (`:876`), which returns an `IngameHudVisibility` (`P:\scripts\5_mission\gui\ingamehudvisibility.c:33`). Build the helper on that.

## Layer mistakes

- Never name `MissionGameplay` or `IngameHud` from `4_World`; it does not compile.
- Never put entity logic in `5_Mission`: entity classes live in `4_World`, and a `modded class` belongs in the module of the class it changes. The server does load `5_Mission`, since `MissionServer` lives there.
- A `modded class` must sit in its class's own module: `modded class Transport`, a `3_game` class, written in `4_World` fails with `Unknown type 'Transport'`.
- Never declare `modded class MissionServer`, `MissionGameplay` or `Chat` outside `5_Mission`. The compile may pass, depending on parse order, but the override never binds to the live instance, so `OnInit`, `OnMissionStart`, `OnMissionLoaded` and `InvokeOnConnect` never fire from your code, with no error. If a `Print("hooked")` in your override never reaches `script_*.log` although the server loads the mission, check the folder: `missionScriptModule` loads only `Scripts/5_Mission/`. Move the file there, for example `Scripts/5_Mission/MyMod_MissionServer.c`.
- The `modded class` chain has no order you can rely on. It follows the `requiredAddons` compile order, not the `-mod=` or `-servermod=` string (measured on a DayZ 1.30 server; see `skills/dayz-launch-test/references/dayz-1-30-server-measured.md`, section on mod load order). Undo another mod's change from an event that runs after it, such as `EEInit()` after the constructor chain, never by assuming your layer is outermost.
