# Pattern: NetSync (Server → Client Variable Sync)

NetSync is the primary mechanism for pushing server-side state to clients. Variables are registered once in `Init()` and the engine handles serialization; the client receives updated values in `OnVariablesSynchronized()`.

---

## Registration

Call `RegisterNetSyncVariable*()` in `Init()` **after** `super.Init()`.

```c
override void Init()
{
    super.Init();

    // Integer — optional min/max bounds reduce bandwidth
    RegisterNetSyncVariableInt("m_MyState", 0, 255);

    // Boolean
    RegisterNetSyncVariableBool("m_IsActive");

    // Float — specify precision (decimal places) to control bandwidth
    RegisterNetSyncVariableFloat("m_Progress", 0.0, 1.0, 2); // 2 d.p.
}
```

---

## Sending an Update (Server)

After modifying a synced variable, call `SetSynchDirty()`. The engine batches and sends on the next network tick — **never call it every frame**.

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

## Bitfield Pattern — Multiple Booleans in One Int

Packing multiple flags into a single `RegisterNetSyncVariableInt` saves bandwidth and variable slots (there is a cap per entity).

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
| Register only in `Init()` | Late registration causes silent failure |
| `SetSynchDirty()` is entity-level | One call per entity update is enough regardless of how many variables changed |
| Client-only code in `OnVariablesSynchronized` | Never do server work here |
| Max ~32 synced variables per entity | Use bitfields to stay under the limit |
| NetSync is **eventual** | Don't assume the client has the latest value immediately after `SetSynchDirty()` |
