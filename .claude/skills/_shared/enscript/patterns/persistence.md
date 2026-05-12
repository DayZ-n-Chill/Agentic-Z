# Pattern: Persistence (OnStoreSave / OnStoreLoad)

DayZ persists entity data through a positional binary stream. Fields are written and read in **strict order**. Adding new fields requires a version guard at the read site.

---

## Version Guard Pattern

```c
// Version constant — bump when adding new saved fields
const int MYMOD_ITEM_SAVE_VERSION = 2;

class MyMod_CustomCanteen : Bottle_Base
{
    protected bool  m_IsContaminated; // v1
    protected float m_ContaminationPct; // v2 (added later)

    // ---- SAVE ---------------------------------------------------------------
    // Always call super FIRST, then write your fields in order.
    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);          // vanilla data first

        ctx.Write(MYMOD_ITEM_SAVE_VERSION); // version header
        ctx.Write(m_IsContaminated);        // v1 field
        ctx.Write(m_ContaminationPct);      // v2 field
    }

    // ---- LOAD ---------------------------------------------------------------
    // Read in the SAME ORDER as written.
    // Never read more bytes than were written — it corrupts the stream.
    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version))
            return false;

        int myVersion;
        if (!ctx.Read(myVersion))
            return false;

        // v1 fields — always present since version 1
        if (!ctx.Read(m_IsContaminated))
            return false;

        // v2 fields — only present in saves written at version >= 2
        if (myVersion < 2)
        {
            m_ContaminationPct = 0.0; // default
            return true;
        }

        if (!ctx.Read(m_ContaminationPct))
            return false;

        return true;
    }
}
```

---

## PlayerBase Persistence

Same pattern; `version` parameter is the **game version** integer (e.g., 129 = game v1.29):

```c
modded class PlayerBase
{
    protected int m_MyMod_Points;

    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);
        ctx.Write(m_MyMod_Points);
    }

    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version))
            return false;

        // Guard against saves made before this mod existed
        // Use the game version when you shipped this field
        if (version < 129)
            return true;

        if (!ctx.Read(m_MyMod_Points))
            return false;

        return true;
    }
}
```

---

## CF ModStorage Alternative

If you use Community Framework, prefer `CF_OnStoreSave` / `CF_OnStoreLoad` to avoid touching the vanilla stream:

```c
modded class ItemBase
{
    override void CF_OnStoreSave(CF_ModStorageMap storage)
    {
        super.CF_OnStoreSave(storage);
        CF_ModStorage ctx = storage.Get("MyMod");
        ctx.Write(m_MyValue);
    }

    override bool CF_OnStoreLoad(CF_ModStorageMap storage)
    {
        if (!super.CF_OnStoreLoad(storage))
            return false;
        if (!storage.Contains("MyMod"))
            return true;
        CF_ModStorage ctx = storage.Get("MyMod");
        if (!ctx.Read(m_MyValue)) return false;
        return true;
    }
}
```

---

## Rules

| Rule | Detail |
|---|---|
| `super.*` FIRST on save, check return on load | Breaking this corrupts the entire entity's save data |
| Write your own version header | Never rely on the `version` param alone — it's the game version, not yours |
| Read = exact mirror of write | Any difference = corrupted stream → entity deleted by server |
| New fields at the END | Never insert between existing fields |
| Return `false` means "delete this entity" | Only return false if the stream is genuinely broken |
| Test with fresh save AND upgrade from old save | Both paths must work before shipping |
