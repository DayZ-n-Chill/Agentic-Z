# Pattern: Persistence (OnStoreSave / OnStoreLoad)

DayZ persists entity data through a positional binary stream. Fields are written and read in **strict order**. Adding new fields requires a version guard at the read site.

The hooks are `void OnStoreSave(ParamsWriteContext ctx)` and `bool OnStoreLoad(ParamsReadContext ctx, int version)` on `EntityAI` (`P:\scripts\3_game\entities\entityai.c:2910` and `:2978`), overridden by `ItemBase` (`P:\scripts\4_world\entities\itembase.c:3190` and `:3089`) and `PlayerBase` (`P:\scripts\4_world\entities\manbase\playerbase.c:7353` and `:7408`). The full contract (what vanilla already saves, the load hook order, what `false` means) is in [`../../persistence/save-load-contract.md`](../../persistence/save-load-contract.md); this file is the short pattern.

---

## Version Guard Pattern

```c
// Version constant: bump when adding new saved fields
const int MYMOD_ITEM_SAVE_VERSION = 2;

class MyMod_CustomCanteen : Bottle_Base // P:\scripts\4_world\entities\itembase\edible_base\bottle_base.c:7
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
    // Never read more bytes than were written: it corrupts the stream.
    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version))
            return false;

        int myVersion;
        if (!ctx.Read(myVersion))
            return false;

        // v1 fields: always present since version 1
        if (!ctx.Read(m_IsContaminated))
            return false;

        // v2 fields: only present in saves written at version >= 2
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

Same pattern. `version` is the storage version the save was written with (`GAME_STORAGE_VERSION`, `P:\scripts\3_game\global\game.c:5`), not the game version and not yours, so write your own version first. See [`../../persistence/versioning-and-migration.md`](../../persistence/versioning-and-migration.md) for why and for the upgrade paths.

Adding saved fields to `PlayerBase` breaks loading on a server that already has saves, and again if the mod is removed. Ship it only on a fresh server, or use CF ModStorage (see `versioning-and-migration.md`, "Adding saved fields to a vanilla class").

```c
modded class PlayerBase
{
    static const int MYMOD_PLAYER_SAVE_VERSION = 1;
    protected int m_MyMod_Points;

    override void OnStoreSave(ParamsWriteContext ctx)
    {
        super.OnStoreSave(ctx);
        ctx.Write(MYMOD_PLAYER_SAVE_VERSION);
        ctx.Write(m_MyMod_Points);
    }

    override bool OnStoreLoad(ParamsReadContext ctx, int version)
    {
        if (!super.OnStoreLoad(ctx, version))
            return false;

        int myVersion;
        if (!ctx.Read(myVersion))
            return false;

        if (!ctx.Read(m_MyMod_Points))
            return false;

        return true;
    }
}
```

---

## CF ModStorage Alternative

If you use Community Framework, prefer `CF_OnStoreSave` / `CF_OnStoreLoad` to avoid touching the vanilla stream. They are declared on CF's modded `ItemBase` (`4_World\CommunityFramework\Entities\ItemBase.c:42` inside `P:\Mods\@CF\Addons\scripts.pbo`), and `CF_ModStorageMap` has `Get(string)` and `Contains(string)` (`3_Game\CommunityFramework\ModStorage\CF_ModStorageMap.c:5` and `:15`):

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
| Write your own version header | Never rely on the `version` param alone: it is the game's storage version (`game.c:5`), not yours |
| Read = exact mirror of write | Any difference = corrupted stream; the load fails |
| New fields at the END | Never insert between existing fields |
| Return `false` means the record failed to load | What the engine then does is not visible in script, so treat it as losing the object (`save-load-contract.md`). Only return false if the stream is genuinely broken |
| Test with fresh save AND upgrade from old save | Both paths must work before shipping |
