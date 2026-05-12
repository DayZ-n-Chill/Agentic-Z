# Reference: PlayerBase API

`PlayerBase` extends `ManBase` → `DayZCreature` → `DayZCreatureAI` → `Human`. Most modding targets `PlayerBase` directly from `Scripts/4_World/`.

---

## Vital Stats

```c
PlayerBase player = PlayerBase.Cast(identity.GetPlayer());

// Health / Vital Values
float health    = player.GetHealth("", "Health");     // 0..100
float blood     = player.GetHealth("", "Blood");
float energy    = player.GetStatEnergy().Get();       // kcal
float water     = player.GetStatWater().Get();        // ml
float stamina   = player.GetStatStamina().Get();      // 0..100
float heatLevel = player.GetStatHeatComfort().Get();
float shock     = player.GetHealth("", "Shock");

// Set values (server only)
player.SetHealth("", "Health", 100.0);
player.GetStatEnergy().Set(2000.0);
player.GetStatWater().Set(2500.0);
```

---

## Identity and Position

```c
PlayerIdentity id  = player.GetIdentity();
string uid         = id.GetId();             // Steam/Xbox UID
string name        = id.GetName();
string ip          = id.GetIpAddress();

vector pos         = player.GetPosition();
vector ori         = player.GetOrientation(); // yaw/pitch/roll degrees
vector aim         = player.GetAimPosition(); // crosshair world position
```

---

## Inventory Helpers

```c
// Hands
EntityAI inHands = player.GetHeldEntity();
bool hasItem     = player.GetItemInHands() != null;

// Walk the full inventory
for (int i = 0; i < player.GetInventory().GetSlotCount(); i++)
{
    EntityAI item = player.GetInventory().GetSlotItem(i);
}

// Check if player has an item type anywhere in inventory
bool has = player.HasItemOfType("Knife");
```

---

## Movement and Action State

```c
bool isInVehicle  = player.IsInVehicle();
bool isAlive      = player.IsAlive();
bool isUnconscious= player.IsUnconscious();
bool isRestrained = player.IsRestrained();
bool isBleeding   = player.IsBleeding();
bool isOnGround   = player.IsItemInHands();  // wrong name — use physic check
bool isSprinting  = player.IsSprinting();
bool isCrawling   = player.IsCrawling();

// Teleport
player.SetPosition(vector pos);
player.SetOrientation(vector orientation);
```

---

## Agents and Modifiers (Disease/Condition System)

```c
// Add agent (disease/symptom source)
player.GetAgents().AddAgent(eAgents.SALMONELLA_BACTERIA, 1000);

// Remove agent
player.GetAgents().RemoveAgent(eAgents.SALMONELLA_BACTERIA);

// Check agent level
int salmLevel = player.GetAgents().GetAgentLevel(eAgents.SALMONELLA_BACTERIA);

// Add modifier (visible symptom/status effect)
player.GetSymptomsManager().AddModifier(eModifiers.MDF_POISONED);
player.GetSymptomsManager().RemoveModifier(eModifiers.MDF_POISONED);
bool hasMod = player.GetSymptomsManager().HasModifier(eModifiers.MDF_POISONED);
```

---

## NetSync on PlayerBase

```c
modded class PlayerBase
{
    int m_MyMod_SyncedValue;

    override void Init()
    {
        super.Init();
        RegisterNetSyncVariableInt("m_MyMod_SyncedValue", 0, 9999);
    }

    // Server
    void SetSyncedValue(int val)
    {
        m_MyMod_SyncedValue = val;
        SetSynchDirty();
    }

    // Client callback
    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();
        // m_MyMod_SyncedValue is now up-to-date
    }
}
```

---

## RPC to/from a Player

```c
// Server → client player
GetGame().RPCSingleParam(player, MY_RPC, new Param1<int>(1), true, player.GetIdentity());

// Client → server (null recipient)
GetGame().RPCSingleParam(localPlayer, MY_RPC, new Param1<int>(1), true, null);
```

---

## Server-side Useful Methods

```c
player.Message(player, "You received an item!");   // chat bubble above head
player.MessageAction("Inventory full.");           // centre-screen action msg
player.MessageStatus("Admin message.");            // status area

player.SpawnEntityOnGroundBelow("SurvivorM_Jeans", player.GetPosition());
player.CreateInInventory("Apple");

// Kill / revive
player.SetHealth("", "Health", 0.0);
// No built-in revive — set all vitals back and call SetHealth 100
```
