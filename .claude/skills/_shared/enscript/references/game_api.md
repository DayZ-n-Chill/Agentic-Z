# Reference: Game, World, and Mission API

Core global accessors and their most-used methods.

---

## GetGame()

Returns the `CGame` singleton. Available in all script layers.

```c
CGame game = GetGame();

// Time
float time     = game.GetTime();           // milliseconds since server start
string timeStr = game.GetTimeString();     // "HH:MM"

// Utilities
game.IsMissionHost();    // true if this machine is the server
game.IsServer();         // same as IsMissionHost() in most contexts
game.IsClient();         // true on game clients
game.IsMultiplayer();

// Spawn / delete
EntityAI ent = game.CreateObject("Apple", pos, false, true);
// params: className, position, forceGround, spawnPrecise
game.ObjectDelete(ent);  // schedule for deletion at end of tick

// Schedule a delayed call (server or client)
game.CallLater(MyFunc, delayMs, repeat, param1, param2);
// repeat = false → call once; true → call every delayMs until you cancel
// Cancel:
game.CallLaterCancel(MyFunc);  // NOT reliable for anonymous-style calls

// Input / UI
UIManager ui = game.GetUIManager();

// RPC (see references/erpc_defines.md for ID lists)
game.RPC(target, rpc_type, params, guaranteed, recipient);
game.RPCSingleParam(target, rpc_type, param, guaranteed, recipient);
```

---

## GetWorld() / GetGame().GetWorld()

Returns `World`. Used for world-space queries.

```c
World world = GetGame().GetWorld();

// Ray / collision queries
float      groundY = world.GetSurfaceY(x, z);
string     surface = world.GetSurfaceType(pos);
bool       isUnder = world.IsUnderRoofEx(pos, 5.0);  // 5 m check radius

// Object at position
array<Object> objects = new array<Object>();
world.GetObjectsAtPosition3D(pos, radius, objects, null);

// Time of day
float daytime = world.GetDayTime();    // 0..1 fraction of 24 h
```

---

## GetMission() / MissionBase

Returns the active `MissionBase` (cast to `MissionServer` on server).

```c
MissionBase mbase = GetMission();
MissionServer ms  = MissionServer.Cast(mbase);

// Spawn a player loot set
ms.SetRandomHealth(item, 1, 100);

// PlayerIdentity → PlayerBase
PlayerBase player = ms.GetPlayerByUID("76561198000000000");
// (CF exposes easier helpers; vanilla requires iteration)
```

---

## CallLater — Scheduling

```c
// Script/3_Game method — callable from any entity or non-entity context
GetGame().CallLater(
    handler,        // function reference: this.OnTick or MyGlobalFunc
    delayMs,        // milliseconds to wait
    repeat,         // false = once, true = every delayMs
    arg1, arg2      // optional params passed to handler
);

// Entity-scope timer (cleaner for per-entity work)
ref Timer m_Timer = new Timer(CALL_CATEGORY_SYSTEM);
m_Timer.Run(interval, this, "OnTimerTick", null, repeat);
m_Timer.Stop();
```

---

## CreateObject / Spawn API

```c
// Simple create at position
EntityAI ent = GetGame().CreateObject("Mag_AKM_Drum75Rnd", spawnPos, false, true);

// Create with orientation
EntityAI ent2 = GetGame().CreateObjectEx(
    "SurvivorM_Jeans",   // className
    spawnPos,
    ECE_PLACE_ON_SURFACE | ECE_LOCAL   // flags
);
ent2.SetOrientation("0 0 0");

// ECE flags (bitmask)
// ECE_LOCAL           — don't replicate (debug / server-side ghost)
// ECE_PLACE_ON_SURFACE — snap Y to terrain
// ECE_OBJECT_SWAP     — replace an existing object
```

---

## Print / Debug Logging

```c
Print("My message");                // goes to script_*.log
PrintFormat("Value: %1", myVar);    // formatted

// Only at Workbench (stripped in release)
#ifdef DEVELOPER
    Print("[DEBUG] " + debugInfo);
#endif
```

---

## ⚠️ `ConfigGet*` path is space-separated, NOT dotted

Config-lookup errors are silent unless you check the return; the path format is **space-separated**, not dot-notation:

```c
// CORRECT
string out_str;
GetGame().ConfigGetText("CfgVehicles ClassName displayName", out_str);
float disp = GetGame().ConfigGetFloat("CfgWeapons ClassName fireMode " + i + " dispersion");

// WRONG — silently returns nothing / 0.0
GetGame().ConfigGetText("CfgVehicles.ClassName.displayName", out_str);
```

The engine returns `CONFIG_NOT_FOUND` on a bad path but doesn't raise — always check the out value or function return for success.

---

## ⚠️ `GetScreenPos` z-component for "behind camera" check

`GetGame().GetScreenPos(worldPos)` returns valid `x`,`y` even when the world position is behind the camera. The `z` component tells you which side:

```c
vector screenPos = GetGame().GetScreenPos(targetWorldPos);
if (screenPos[2] <= 0)
{
    // behind camera — hide the marker
    m_Marker.Show(false);
    return;
}
m_Marker.Show(true);
m_Marker.SetPos(screenPos[0], screenPos[1]);
```

Without the `z` check, your compass marker / objective indicator jitters around the screen edges when you turn away from the target.
