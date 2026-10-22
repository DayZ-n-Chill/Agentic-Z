# Pattern: NetSync (Server → Client Variable Sync)

NetSync is the primary mechanism for pushing server-side state to clients. Variables are registered once when the entity is built and the engine handles serialization; the client receives updated values in `OnVariablesSynchronized()`.

The API is declared on `EntityAI` in `P:\scripts\3_game\entities\entityai.c` (`RegisterNetSyncVariableBool` :2832, `RegisterNetSyncVariableBoolSignal` :2840, `RegisterNetSyncVariableInt` :2850, `RegisterNetSyncVariableFloat` :2861, `RegisterNetSyncVariableObject` :2869, `SetSynchDirty` :3064, `OnVariablesSynchronized` :3069).

---

## Registration

Register in the class constructor. `ItemBase` and `EntityAI` have no `Init()` to override, so an `override void Init()` on an item does not compile.

```c
class MyMod_Lamp : ItemBase
{
    int   m_MyState;
    bool  m_IsActive;
    float m_Progress;

    void MyMod_Lamp()
    {
        // Integer: min and max quantize the value (min == max means no quantization)
        RegisterNetSyncVariableInt("m_MyState", 0, 255);

        // Boolean
        RegisterNetSyncVariableBool("m_IsActive");

        // Float: min, max and the number of digits after the decimal point
        RegisterNetSyncVariableFloat("m_Progress", 0.0, 1.0, 2);
    }
}
```

Vanilla does the same: `BaseBuildingBase()` registers six variables in its constructor (`P:\scripts\4_world\entities\itembase\basebuildingbase.c:38-48`) and `Edible_Base()` registers its food stage there (`P:\scripts\4_world\entities\itembase\edible_base.c:25-31`).

The other vanilla place is an `InitItemVariables()` override, which the `EntityAI` constructor calls (`P:\scripts\3_game\entities\entityai.c:236` and :257). `Barrel_ColorBase` registers there after `super.InitItemVariables()` (`P:\scripts\4_world\entities\itembase\barrel_colorbase.c:9-21`).

`PlayerBase` is the exception: it has its own `Init()`, called from its constructor (`P:\scripts\4_world\entities\manbase\playerbase.c:359-364`), and registers its variables there (:558 onwards). A `modded class PlayerBase` can register in an `override void Init()` after `super.Init()`, or in its constructor.

---

## Sending an Update (Server)

After modifying a synced variable, call `SetSynchDirty()`. It only sets a flag that the entity wants to be synchronized, and only on the server in multiplayer (comment at `entityai.c:3063`), so one call per change is enough. **Never call it every frame.**

```c
void MyMod_SetState(int newState)
{
    if (!GetGame().IsServer())
        return;
    m_MyState = newState;
    SetSynchDirty();
}
```

---

## Receiving (Client)

`OnVariablesSynchronized()` is "called on clients after receiving synchronization data from server" (`entityai.c:3066-3069`).

```c
override void OnVariablesSynchronized()
{
    super.OnVariablesSynchronized(); // MUST call super

    // All registered variables are now up-to-date
    if (m_IsActive)
        ApplyActiveVisuals();
    else
        ClearActiveVisuals();
}
```

---

## Bitfield Pattern: Multiple Booleans in One Int

Packing several flags into one `RegisterNetSyncVariableInt` sends one value instead of many. Vanilla does this for the player's bleeding sources (`RegisterNetSyncVariableInt("m_BleedingBits")`, `playerbase.c:565`) and persistent flags (:558).

```c
enum MyMod_SyncFlags
{
    IS_POISONED  = 1,   // bit 0  (1 << 0)
    IS_EXHAUSTED = 2,   // bit 1  (1 << 1)
    HAS_SHIELD   = 4,   // bit 2  (1 << 2)
    // up to bit 30 for a 32-bit int
}

modded class PlayerBase
{
    int m_MyMod_Flags;

    override void Init()
    {
        super.Init();
        RegisterNetSyncVariableInt("m_MyMod_Flags");
    }

    // Server: set a flag
    void MyMod_SetFlag(int flag, bool value)
    {
        if (value)
            m_MyMod_Flags |= flag;
        else
            m_MyMod_Flags &= ~flag;
        SetSynchDirty();
    }

    // Client: decode
    override void OnVariablesSynchronized()
    {
        super.OnVariablesSynchronized();
        bool isPoisoned  = (m_MyMod_Flags & MyMod_SyncFlags.IS_POISONED)  != 0;
        bool isExhausted = (m_MyMod_Flags & MyMod_SyncFlags.IS_EXHAUSTED) != 0;
    }
}
```

---

## Limits and Gotchas

| Rule | Detail |
|---|---|
| Register when the entity is built | Constructor, `InitItemVariables()`, or `PlayerBase.Init()`; see Registration above |
| `SetSynchDirty()` is entity-level | One call per entity update is enough regardless of how many variables changed |
| Client-only code in `OnVariablesSynchronized` | Never do server work here |
| `RegisterNetSyncVariableObject` | Syncs only when the object has a network ID, and does not handle the object despawning on the client (`entityai.c:2864-2869`) |
| `RegisterNetSyncVariableBoolSignal` | Sent when true, then becomes false again: a one-shot signal (`entityai.c:2834-2840`) |
| NetSync is **eventual** | Don't assume the client has the latest value immediately after `SetSynchDirty()` |
