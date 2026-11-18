# Networking and sync

How state reaches clients: synced variables, which server calls replicate on their own, why client-only visual writes get overwritten, and how to tell the sides apart during load. RPCs are in `rpc-routing.md` and `rpc-manager-and-cf.md`; saving and files in `persistence-and-files.md`. The short checked patterns are `../patterns/netsync.md`, `../patterns/rpc.md` and `../patterns/persistence.md`.

## The mechanisms

The server has authority. State moves through:

| Mechanism | Direction | File |
|---|---|---|
| Synced variables | Server to every client, automatically | this file |
| `ScriptRPC` and `RPCSingleParam` | Either way, by hand | `rpc-routing.md` |
| `OnStoreSave` and `OnStoreLoad` | Server to disk, across restarts | `persistence-and-files.md` |
| Inventory commands | Their own juncture path, not synced variables | `dayz-1-30-inventory.md` |

## Synced variables

Register them in the constructor, or in an `InitItemVariables()` override (`PlayerBase` uses `Init()`), never in `EEInit`:

```c
class MyMod_Device extends ItemBase
{
    bool m_PoweredNet;
    int m_LoadPercent;
    float m_Temperature;

    void MyMod_Device()
    {
        RegisterNetSyncVariableBool("m_PoweredNet");
        RegisterNetSyncVariableInt("m_LoadPercent", 0, 100);
        RegisterNetSyncVariableFloat("m_Temperature", 0.0, 200.0, 2);
    }
}
```

| Call | Sends |
|---|---|
| `RegisterNetSyncVariableBool(string varName)` | One bit |
| `RegisterNetSyncVariableInt(string varName, int min, int max)` | An int packed to its range |
| `RegisterNetSyncVariableFloat(string varName, float min = 0, float max = 0, int precision = 1)` | A float packed to its range |

`precision` is the number of digits kept after the decimal point, not a bit count, and `min == max` turns packing off (`P:\scripts\3_game\entities\entityai.c:2853` to `:2861`). Vanilla calls `RegisterNetSyncVariableFloat` with `2` for the effect area radius and heights (`P:\scripts\4_world\classes\contaminatedarea\effectarea.c:99` to `:101`) and `5` for an animation phase between 0 and 1 (`P:\scripts\4_world\entities\building\underground\entrance\land_underground_entrance.c:76`).

Write synced variables on the server only, then call `SetSynchDirty()`, or clients never see the change:

```c
void SetPowered(bool state)
{
    #ifdef SERVER
    m_PoweredNet = state;
    SetSynchDirty();
    #endif
}
```

Code that must also run in single player, where `SERVER` is not defined, checks `GetGame().IsServer()` instead.

On the client, `OnVariablesSynchronized()` fires when any registered variable changes. It does not say which, so call `super` and check every field you care about.

## What replicates without custom sync

Measured in game with a probe mod, from a dedicated server to a client already connected:

| Server call | Seen on the client | Declared |
|---|---|---|
| `SetObjectMaterial(int, string)` | Yes | `P:\scripts\3_game\entities\entityai.c:2884` |
| `SetObjectTexture(int, string)` | Yes | `entityai.c:2881` |
| `SetAnimationPhase(string, float)` | Yes, fractional phases too | `P:\scripts\3_game\entities\entity.c:15` |
| `SetPosition(vector)` | Yes | `P:\scripts\3_game\entities\object.c:294` |
| `SetScale(float)` | No | `P:\scripts\1_core\proto\enentity.c:448` |

Sync scale yourself, for example with `RegisterNetSyncVariableFloat` (`entityai.c:2861`), and apply it on the client. Raise `precision` when values such as `1.25` must survive packing, or pass equal minimum and maximum for no packing. Scale changes collision too: identical probe boxes at scale 1 and 0.5 gave vertical ray distances of 0.2018 m and 0.1018 m.

Unverified: a client that joins later, and objects placed in the map. Animation results depend on the model: `Barrel_ColorBase` drives its two caps from one phase with `SetAnimationPhase` on `Lid` and `Lid2` (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:148` to `:154`), and phase 0.5 showed both. `GetAnimationPhase` read straight after a write returned the old value.

## Client-only visual writes get overwritten

`SetObjectTexture` or `SetSimpleHiddenSelectionState` written only on the owning client is overwritten when the server sends the object again; on a drop, a liquid's colour went back to its config colour while the display name stayed (measured in game on DayZ 1.30). Write the visuals on the server as well, only when what is visible changes, keyed to the state that owns them, and have the client reapply them in `EEItemLocationChanged`. Vanilla writes visuals on the server too: `ChemLight.CreateLight` calls `SetObjectMaterial` with the comment "must be server side!" (`P:\scripts\4_world\entities\itembase\chemlight.c:68`).

## Side checks during load

Reported, not checked on `P:\`:

| Call | During load | After load |
|---|---|---|
| `GetGame().IsServer()` | True even on the client | True on the server |
| `GetGame().IsClient()` | Not reliable on the client | True on the client |
| `GetGame().IsDedicatedServer()` | False on the client | False on the client |
| `GetGame().IsMultiplayer()` | True | True |

During load use `IsDedicatedServer()` for the server and `!IsDedicatedServer()` for the client; vanilla calls it the robust check, "valid much sooner" (`P:\scripts\3_game\global\game.c:1121` to `:1125`). For offline and single player support `IsServer()` is the right check, since there the client is also the server.
