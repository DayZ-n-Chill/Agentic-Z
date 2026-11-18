# Script layers: what goes in 3_Game, 4_World and 5_Mission

Which script module a class belongs in, what each module can see, the bridge pattern for HUD code, and the layer mistakes that compile and then silently do nothing. Class locations cited as `P:\...:N` were checked on `P:\`; the worked example sorts the files of a large power-grid mod, and measured results name the build they were measured on.

## The five modules

DayZ compiles the script modules in this order (the last three keys are the ones a mod's `CfgMods` `defs` normally declares; the key names are not checked on `P:\`):

| Folder | Module key | Typical mod use |
|---|---|---|
| `1_Core` | `engineScriptModule` | Engine utilities and enums; rarely needed by content mods |
| `2_GameLib` | `gameLibScriptModule` | Rarely used by mods |
| `3_Game` | `gameScriptModule` | `DayZGame`, RPC IDs, constants, shared data |
| `4_World` | `worldScriptModule` | `PlayerBase`, `ItemBase`, entities, actions |
| `5_Mission` | `missionScriptModule` | `MissionServer`, `MissionGameplay`, HUD, boot hooks |

The rule that matters: a lower layer cannot name a type that exists only in a higher layer (a compile error). Symptom: `Undefined type 'PlayerBase'` when `3_Game` code names `PlayerBase`, which lives in `4_World`. Workaround: accept a lower base (`Man`, `Object`) in the lower layer and `Class.CastTo` in `4_World` or above.

A mod's scripts load in the order 3, 4, 5. Each layer can use classes from its own layer and every lower one, never a higher one.

## Layer rules

| Layer | Purpose | Can use | Cannot use |
|---|---|---|---|
| **3_Game** | Data, enums, configs, data classes, utilities | The engine core, `GetGame()`, and the classes vanilla declares in `1_core` to `3_game` | `PlayerBase`, `ItemBase`, world logic, mission classes |
| **4_World** | Entities, actions, items, world logic | Everything in `3_Game`, plus `PlayerBase`, `ItemBase`, `MissionBaseWorld` (`P:\scripts\4_world\classes\missionbaseworld.c:1`), and Dabs MVC (`ScriptView` and `ViewController`, which need Dabs Framework, `DF_Scripts`) | `MissionGameplay`, `IngameHud`, `Chat`, `InGameMenu` |
| **5_Mission** | Client presentation, HUD, menus, mission hooks | Everything in 3 and 4, plus `MissionGameplay` (`P:\scripts\5_mission\mission\missiongameplay.c:1`), `MissionServer` (`P:\scripts\5_mission\mission\missionserver.c:5`), `IngameHud` (`P:\scripts\5_mission\gui\ingamehud.c:1`), `Chat` (`P:\scripts\5_mission\gui\chat\chat.c:14`), `ChatInputMenu`, `InGameMenu` (`P:\scripts\5_mission\gui\ingamemenu.c:1`) | Nothing: it is the top layer |

Checked on `P:\`: `Widget` is declared in `1_core` (`P:\scripts\1_core\proto\enwidgets.c:107`), and `EntityAI` (`P:\scripts\3_game\entities\entityai.c:115`), `UIManager` (`P:\scripts\3_game\tools\uimanager.c:1`), `UIScriptedMenu` (`P:\scripts\3_game\tools\uiscriptedmenu.c:66`), `Hud` (`P:\scripts\3_game\gameplay.c:637`), `Mission` (`P:\scripts\3_game\gameplay.c:685`) and `Transport` (`P:\scripts\3_game\vehicles\transport.c:68`) are declared in `3_game`. So `3_Game` code can name widgets, `EntityAI`, `UIManager` and `UIScriptedMenu`; what it cannot name are the `4_world` and `5_mission` classes.

## What goes where

**3_Game**: shared data that server and client both need without world context.

- Enums, constants, defines
- Data classes (configs, serialization helpers)
- Pure utility functions (string, math, file)
- RPC ID enums
- Telemetry and logging

**4_World**: anything that works with world entities.

- Device entities (`ItemBase` and `Inventory_Base` descendants)
- Actions (`ActionBase` descendants)
- Entity logic (an electrical graph, networking, persistence)
- Kit classes, hologram overrides
- Device controllers (server logic)
- Dabs `ScriptView` and `ViewController` classes
- Pure UI panels that do not need `IngameHud` or `MissionGameplay`

**5_Mission**: client presentation that needs mission level access.

- `modded class MissionGameplay` and `modded class MissionServer`
- HUD overlays that follow the HUD's visibility
- `modded class Chat` or chat integration
- Compass, GPS minimap, player list overlays
- A notification system tied to game state
- Phone or ATM HUD elements (widgets that stay on screen)
- Any UI that must know through the mission whether a menu is open

## The bridge pattern

Keep the logic in `4_World` and expose it through a singleton. Call it from a `5_Mission` bridge:

```
// 4_World: singleton with static access
class MyMod_PhoneHUD {
    static ref MyMod_PhoneHUD s_Instance;
    protected Widget m_Root;
    
    static void Init() { s_Instance = new MyMod_PhoneHUD(); }
    static MyMod_PhoneHUD Get() { return s_Instance; }
    
    void Show(bool visible) { m_Root.Show(visible); }
    void UpdateFrame() { /* render logic */ }
}

// 5_Mission: bridge calls into the 4_World singleton
modded class MissionGameplay {
    override void OnInit() {
        super.OnInit();
        MyMod_PhoneHUD.Init();
    }
    
    override void OnUpdate(float timeslice) {
        super.OnUpdate(timeslice);
        // HUD visibility needs IngameHud (5_Mission only):
        IngameHud hud = IngameHud.Cast(GetGame().GetMission().GetHud());
        bool hudVisible = hud && hud.MyMod_IsHudVisible();
        MyMod_PhoneHUD.Get().Show(hudVisible && playerAlive);
        if (hudVisible)
            MyMod_PhoneHUD.Get().UpdateFrame();
    }
}
```

The `5_Mission` bridge does the `IngameHud` check and passes the result (a `bool`) down to `4_World`. The `4_World` class never names `IngameHud`.

`MyMod_IsHudVisible()` in the example stands for a helper the mod adds to `IngameHud` with a `modded class`; it is not vanilla. In the vanilla scripts on `P:\`, `IngameHud.IsHudVisible()` is a stub that returns `false` (`P:\scripts\5_mission\gui\ingamehud.c:1313`), and the live state is behind `GetHudVisibility()` (`P:\scripts\5_mission\gui\ingamehud.c:876`), which returns an `IngameHudVisibility` (`P:\scripts\5_mission\gui\ingamehudvisibility.c:33`). Build the helper on that object.

## Mistakes to avoid

- Do not name `MissionGameplay` from `4_World`: it will not compile, or will crash.
- Do not name `IngameHud` from `4_World`: the class is not available in that layer.
- Do not put entity logic in `5_Mission`: entity classes live in `4_World`, and a `modded class` belongs to the module of the class it modifies. (The server does load `5_Mission`; `MissionServer` lives there.)
- Do not keep every file in `4_World` when part of them is pure UI. One large mod had 109 files in `4_World` and 1 in `5_Mission` while 15 were pure UI: it works, but it limits later HUD features.
- The `modded class` chain has no order you can rely on. It follows the `requiredAddons` compile order, not the `-mod=` or `-servermod=` string (measured on a 1.30 server). Undo another mod's change from an event that runs after it (`EEInit()` runs after the constructor chain), never by assuming your layer is outermost; `skills/dayz-launch-test/references/dayz-1-30-server-measured.md`, section 7, has the detail. In the same way `modded class Transport` (a `3_game` class, `P:\scripts\3_game\vehicles\transport.c:68`) written in `4_World` fails with `Unknown type 'Transport'`: mod a class in its own module.
- Do not declare `modded class MissionServer`, `modded class MissionGameplay` or `modded class Chat` in `4_World`. They are mission layer classes. The compile may pass silently (depending on parse order), but the override is never bound to the live instance, so hooks such as `OnInit`, `OnMissionStart`, `OnMissionLoaded` and `InvokeOnConnect` never fire from your code. Symptom: no log output, no error, nothing happens.

  How to detect it: you wrote `modded class MissionServer { override void OnInit() { Print("hooked"); ... } }` and the `Print` never appears in `script_*.log` although the server reaches mission load. Check which layer the file is in. The `missionScriptModule` entry of `CfgMods` in `config.cpp` loads only `Scripts/5_Mission/`; a file anywhere else cannot mod `MissionServer`.

  Fix: put the file in `Scripts/5_Mission/` (for example `Scripts/5_Mission/MyMod_MissionServer.c`). The same goes for any class that exists only in the mission module.

## Example: sorting the files of a power-grid mod

Files that are fine in `4_World` (tied to entities, or with no need of the mission): `SorterView`, `BTCAtmView`, `SorterController`, `BTCAtmController`, `DeviceInspector`, `CameraViewport`, `SearchlightController`, `DoorController`, `RemoteController`.

Files that should move to `5_Mission` when HUD features are added:

- `MyMod_CableHUD.c`, if it needs the HUD visibility check
- `MyMod_TankHUD.c`, if it needs the HUD visibility check
- Later: a phone HUD, a notification overlay, compass markers, a minimap widget

Rule of thumb: if it draws on the HUD (always visible, not a menu that pops up) and must hide when the HUD hides, it belongs in `5_Mission`.
